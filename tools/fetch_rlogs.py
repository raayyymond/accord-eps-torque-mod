#!/usr/bin/env python3
"""Pull openpilot rlogs off the comma device over SSH.

Read-only on the remote side: this tool never deletes, moves or writes anything on
the device. It only runs ``find`` / ``tar cf -`` and copies bytes down. The device
sits at ~90% disk, so nothing here may add to it.

It fetches ONE file per segment -- ``rlog.zst`` (or ``qlog.zst`` with --kind). The
camera files that share the segment directory (``fcamera``/``ecamera``/``dcamera.hevc``,
``qcamera.ts``) are ~114 MB per segment and are never wanted here. That is enforced
by ``find -name rlog.zst`` at enumeration, so a camera file cannot enter a transfer
even by accident -- it is a filter, not a convention.

Files land under the kit's existing naming convention, which downstream extractors
glob on::

    {dongle}_{route}--{segment}--rlog.zst
    e.g. 75604b0a432fdc89_00000077--7411859c54--12--rlog.zst

Usage examples
--------------
  # what is on the device, newest first
  python tools/fetch_rlogs.py --list

  # the newest route, in full
  python tools/fetch_rlogs.py --latest 1

  # the three newest routes, but show the plan only
  python tools/fetch_rlogs.py --latest 3 --dry-run

  # a named route (either form is accepted)
  python tools/fetch_rlogs.py --route 00000077--7411859c54
  python tools/fetch_rlogs.py --route 75604b0a432fdc89/00000077--7411859c54

  # qlogs instead (much smaller, enough for a quick census)
  python tools/fetch_rlogs.py --latest 1 --kind qlog

  # no ~/.ssh/config alias available -- address the device directly
  python tools/fetch_rlogs.py --host 10.0.0.167 --user comma \
      --key ~/.ssh/id_ed25519_personal --list

  # first contact from a machine that has never seen this device
  python tools/fetch_rlogs.py --accept-new-hostkey --list

Re-runs are idempotent: a local file that already exists with the exact remote byte
size is skipped, so interrupted fetches can simply be re-run.

Host keys -- normally you can ignore this
-----------------------------------------
No host-key flags are needed in normal use; plain ``ssh comma`` works and so does
this tool with no extra arguments.

It matters only WHEN THE DEVICE IS REIMAGED. An AGNOS reflash regenerates every SSH
host key, after which ssh refuses to connect with "REMOTE HOST IDENTIFICATION HAS
CHANGED" until the stale entry is cleared. That happened once, on 2026-08-10, and
was resolved by the operator authorising ``ssh-keygen -R <ip>``; it will happen
again on the next reimage. This tool detects that specific failure and prints the
exact remediation (including the stale known_hosts line number) rather than a bare
exit-255 -- see ``hostkey_hint()``.

It deliberately will NOT clear the entry for you: a changed host key is
indistinguishable from an interception until a human confirms the device is theirs,
and known_hosts is the operator's security control. ``--known-hosts PATH`` is the
escape hatch for working against a pinned key without touching the real file, e.g.
while waiting for that authorisation. Note that ``--accept-new-hostkey`` does NOT
cover this case -- per ssh_config(5) it accepts keys for UNKNOWN hosts and still
refuses a host whose key has CHANGED.

Sorting note (this bit matters)
-------------------------------
Routes are ordered by the newest *log file* mtime, NOT by the segment directory
mtime. The device bumps directory mtimes long after a drive (preview.png is written
by the uploader), so on 2026-08-10 routes 74/75/76 carried a 17:57 directory mtime
while their logs were from 10:13 -- newer-looking than route 77, which was actually
the most recent drive. Directory mtime is a trap; file mtime is not.

Timestamps are still not perfectly ordered: the device starts logging before it has
a GPS/NTP time fix, so an occasional route carries a skewed clock (on 2026-08-10,
route 71 timestamped newer than route 72). The leading route counter IS monotonic,
so ``--sort route`` is the tie-breaker when mtimes look implausible.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import defaultdict

DEFAULT_HOST = "comma"
DEFAULT_REMOTE_DIR = "/data/media/0/realdata"
DEFAULT_DEST = os.path.join("analysis-2020accord", "rlogs")
DONGLE_PARAM = "/data/params/d/DongleId"

# "00000077--7411859c54--12" -> route "00000077--7411859c54", segment 12
SEGDIR_RE = re.compile(r"^(?P<route>.+)--(?P<seg>\d+)$")

# Pulled out of ssh's stderr so the remediation names the real host and file.
CHANGED_HOST_RE = re.compile(r"Host key for ([^\s]+) has changed")
OFFENDING_RE = re.compile(r"Offending [A-Z0-9]+ key in ([^\s:]+):(\d+)")


def hostkey_hint(stderr: str, host_fallback: str) -> str:
    """Explain a changed host key and print the EXACT command that fixes it.

    Deliberately does not offer to fix it automatically: known_hosts is the
    operator's security control, and a changed key is indistinguishable from an
    interception until a human confirms the device is theirs.
    """
    m = CHANGED_HOST_RE.search(stderr)
    target = m.group(1) if m else host_fallback
    off = OFFENDING_RE.search(stderr)
    where = f"\n  The stale entry is {off.group(1)} line {off.group(2)}." if off else ""

    return f"""
The device's SSH host key CHANGED. ssh refused to connect.{where}

  This is expected after an AGNOS reflash/reimage -- the device regenerates all of
  its host keys. It is also exactly what a man-in-the-middle looks like, so this
  tool will NOT paper over it for you.

  FIRST verify the box is really the comma device. From a shell you trust:
      ssh-keyscan -t ed25519 {target}          # note the key
      ssh -o UserKnownHostsFile=/tmp/probe_kh -o StrictHostKeyChecking=accept-new \\
          {target} 'cat /data/params/d/DongleId'
  A matching dongle id is strong evidence it is your device and not an impostor.

  THEN drop the stale entry and reconnect once interactively to accept the new key:
      ssh-keygen -R {target}

  Or, without touching your real known_hosts at all, pin the key to a scratch file:
      ssh-keyscan -t ed25519 {target} > /tmp/comma_known_hosts
      python tools/fetch_rlogs.py --known-hosts /tmp/comma_known_hosts --list

  NOTE: --accept-new-hostkey does NOT help here. Per ssh_config(5), accept-new adds
  keys for hosts that are UNKNOWN; it still refuses a host whose key has CHANGED.
  It is for a fresh machine with an empty known_hosts, not for this failure.
"""


# --------------------------------------------------------------------------- #
# ssh plumbing
# --------------------------------------------------------------------------- #

class DeviceError(RuntimeError):
    """The device could not be reached, or refused to answer."""


def ssh_base(args) -> list[str]:
    """Common ssh/scp options. Kept identical between enumerate and transfer."""
    opts = [
        "-o", f"ConnectTimeout={args.connect_timeout}",
        "-o", "BatchMode=yes",
    ]
    if args.key:
        # IdentitiesOnly stops the agent from offering other keys first and
        # burning MaxAuthTries before this one is tried.
        opts += ["-i", args.key, "-o", "IdentitiesOnly=yes"]
    if args.accept_new_hostkey:
        opts += ["-o", "StrictHostKeyChecking=accept-new"]
    elif args.known_hosts:
        # Pin to an explicit file; still strict, just not the user's known_hosts.
        opts += ["-o", "StrictHostKeyChecking=yes"]
    if args.known_hosts:
        opts += ["-o", f"UserKnownHostsFile={args.known_hosts}"]
    for extra in args.ssh_opt:
        opts += ["-o", extra]
    return opts


def ssh_target(args) -> str:
    """`host` from ~/.ssh/config, or an explicit `user@host` that bypasses it."""
    return f"{args.user}@{args.host}" if args.user else args.host


def run_ssh(args, remote_cmd: str, timeout: int = 180) -> str:
    """Run one command on the device, return stdout. Raises DeviceError on failure."""
    cmd = ["ssh"] + ssh_base(args) + [ssh_target(args), remote_cmd]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise DeviceError("`ssh` was not found on PATH.")
    except subprocess.TimeoutExpired:
        raise DeviceError(f"ssh timed out after {timeout}s running: {remote_cmd}")
    if proc.returncode != 0:
        raise DeviceError(_explain_ssh_failure(proc.returncode, proc.stderr, args))
    return proc.stdout


def _explain_ssh_failure(rc: int, stderr: str, args) -> str:
    err = (stderr or "").strip()
    msg = f"ssh failed (exit {rc}):\n{err}"
    low = err.lower()
    if "has changed" in low or "host key verification failed" in low:
        msg += "\n" + hostkey_hint(err, args.host)
    elif "no matching host key" in low or "unknown host key" in low:
        msg += ("\n\nThe host is not in known_hosts. Either connect once interactively "
                "to accept it, or re-run with --accept-new-hostkey (which is safe for a "
                "host you have never seen, and refuses a host whose key has CHANGED).")
    elif "permission denied" in low:
        msg += (f"\n\nThe key was rejected by {ssh_target(args)}. Check that the key "
                f"offered (--key, or IdentityFile in ~/.ssh/config) is the one whose "
                f"public half is in the device's ~/.ssh/authorized_keys.")
    elif ("connection refused" in low or "no route to host" in low
          or "timed out" in low or "could not resolve" in low):
        msg += (f"\n\n{ssh_target(args)} did not answer. Is the device powered, awake, on "
                f"the same network, and still at that address? Override it without "
                f"editing ~/.ssh/config using:  --host <ip> --user comma --key <path>")
    return msg


# --------------------------------------------------------------------------- #
# enumeration
# --------------------------------------------------------------------------- #

def get_dongle(args) -> str:
    if args.dongle:
        return args.dongle
    out = run_ssh(args, f"cat {DONGLE_PARAM} 2>/dev/null || true", timeout=60).strip()
    if not out:
        raise DeviceError(
            f"Could not read the dongle id from {DONGLE_PARAM}. Pass --dongle explicitly.")
    return out.split()[0]


def enumerate_logs(args) -> dict[str, dict[int, tuple[str, int, float]]]:
    """One ssh round-trip for the whole inventory.

    Returns {route: {segment: (remote_path, size_bytes, mtime_epoch)}}.
    """
    fname = f"{args.kind}.zst"
    remote = (
        f"find {shlex.quote(args.remote_dir)} -maxdepth 2 -type f "
        f"-name {shlex.quote(fname)} -printf '%p\\t%s\\t%T@\\n'"
    )
    out = run_ssh(args, remote, timeout=args.list_timeout)

    routes: dict[str, dict[int, tuple[str, int, float]]] = defaultdict(dict)
    skipped = 0
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 3:
            skipped += 1
            continue
        path, size_s, mtime_s = parts
        segdir = os.path.basename(os.path.dirname(path))
        m = SEGDIR_RE.match(segdir)
        if not m:
            skipped += 1
            continue
        try:
            routes[m.group("route")][int(m.group("seg"))] = (
                path, int(size_s), float(mtime_s))
        except ValueError:
            skipped += 1
    if skipped:
        print(f"  note: {skipped} path(s) did not parse as a segment dir; ignored.")
    if not routes:
        raise DeviceError(
            f"No {fname} files found under {args.remote_dir}. "
            f"Is --remote-dir right for this device?")
    return routes


def route_mtime(segs: dict[int, tuple[str, int, float]]) -> float:
    """Newest LOG mtime in the route -- deliberately not the directory mtime."""
    return max(v[2] for v in segs.values())


def sort_routes_newest_first(routes, how: str = "mtime") -> list[str]:
    """Newest first. 'route' sorts on the monotonic leading counter instead of the
    clock, which is the honest key when the device logged before its time fix."""
    if how == "route":
        return sorted(routes, key=lambda r: (r.split("--")[0], r), reverse=True)
    return sorted(routes, key=lambda r: (route_mtime(routes[r]), r), reverse=True)


# --------------------------------------------------------------------------- #
# naming / planning
# --------------------------------------------------------------------------- #

def local_name(dongle: str, route: str, seg: int, kind: str) -> str:
    return f"{dongle}_{route}--{seg}--{kind}.zst"


def normalise_route(raw: str) -> str:
    """Accept '00000077--7411859c54' or '75604b0a432fdc89/00000077--7411859c54'."""
    return raw.strip().strip("/").split("/")[-1]


def build_plan(args, dongle, routes, wanted):
    """Return (todo, skipped, missing_routes).

    todo/skipped are lists of dicts: route, seg, remote, size, dest.
    """
    todo, skipped, missing = [], [], []
    for route in wanted:
        if route not in routes:
            missing.append(route)
            continue
        for seg in sorted(routes[route]):
            remote, size, _ = routes[route][seg]
            dest = os.path.join(args.dest, local_name(dongle, route, seg, args.kind))
            rec = {"route": route, "seg": seg, "remote": remote,
                   "size": size, "dest": dest}
            if os.path.exists(dest) and os.path.getsize(dest) == size:
                skipped.append(rec)
            else:
                todo.append(rec)
    return todo, skipped, missing


# --------------------------------------------------------------------------- #
# transfer
# --------------------------------------------------------------------------- #

def fetch_batch_tar(args, batch) -> set[str]:
    """Stream a batch of files down in ONE ssh call via `tar cf -`.

    Read with Python's tarfile so the members can be renamed to the kit convention
    on the way out; no local tar binary is required. Returns the set of remote paths
    that landed successfully.
    """
    rel = [os.path.relpath(r["remote"], args.remote_dir).replace(os.sep, "/")
           for r in batch]
    by_rel = {p: r for p, r in zip(rel, batch)}

    remote_cmd = (f"tar cf - -C {shlex.quote(args.remote_dir)} "
                  + " ".join(shlex.quote(p) for p in rel))
    cmd = ["ssh"] + ssh_base(args) + [ssh_target(args), remote_cmd]

    landed: set[str] = set()
    # stderr to a real file: a full stderr pipe would deadlock the stdout stream.
    with tempfile.TemporaryFile() as errf:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf)
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
                for member in tf:
                    if not member.isfile():
                        continue
                    rec = by_rel.get(member.name.lstrip("./"))
                    if rec is None:
                        continue
                    src = tf.extractfile(member)
                    if src is None:
                        continue
                    tmp = rec["dest"] + ".part"
                    with open(tmp, "wb") as dst:
                        while True:
                            chunk = src.read(1 << 20)
                            if not chunk:
                                break
                            dst.write(chunk)
                    if os.path.getsize(tmp) == rec["size"]:
                        os.replace(tmp, rec["dest"])
                        landed.add(rec["remote"])
                        print(f"    + {os.path.basename(rec['dest'])} "
                              f"({rec['size'] / 1e6:.1f} MB)")
                    else:
                        os.remove(tmp)
                        print(f"    ! size mismatch on {os.path.basename(rec['dest'])}; "
                              f"will retry via scp")
        except (tarfile.TarError, OSError) as exc:
            print(f"    ! tar stream failed ({exc}); falling back to scp for the rest")
        finally:
            if proc.stdout:
                proc.stdout.close()
            proc.wait()
            if proc.returncode not in (0, None) and len(landed) < len(batch):
                errf.seek(0)
                err = errf.read().decode("utf-8", "replace").strip()
                if err:
                    print(f"    ! remote tar stderr: {err.splitlines()[0]}")
    return landed


def fetch_one_scp(args, rec) -> bool:
    """Single-file fallback. Verifies size before accepting."""
    tmp = rec["dest"] + ".part"
    cmd = ["scp"] + ssh_base(args) + [f"{ssh_target(args)}:{rec['remote']}", tmp]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=args.scp_timeout)
    except subprocess.TimeoutExpired:
        print(f"    ! scp timed out on {os.path.basename(rec['dest'])}")
        _unlink(tmp)
        return False
    except (OSError, FileNotFoundError) as exc:
        print(f"    ! could not run scp: {exc}")
        return False
    if proc.returncode != 0:
        print(f"    ! scp failed on {os.path.basename(rec['dest'])}: "
              f"{(proc.stderr or '').strip().splitlines()[-1] if proc.stderr else ''}")
        _unlink(tmp)
        return False
    # scp can exit 0 without leaving the file where we asked; never let that raise.
    if not os.path.exists(tmp):
        print(f"    ! scp exited 0 but wrote nothing for "
              f"{os.path.basename(rec['dest'])}")
        return False
    if os.path.getsize(tmp) != rec["size"]:
        print(f"    ! size mismatch after scp on {os.path.basename(rec['dest'])}")
        _unlink(tmp)
        return False
    os.replace(tmp, rec["dest"])
    print(f"    + {os.path.basename(rec['dest'])} ({rec['size'] / 1e6:.1f} MB) [scp]")
    return True


def _unlink(path):
    try:
        os.remove(path)
    except OSError:
        pass


def fetch_all(args, todo) -> tuple[list, list]:
    """Batch via tar, then retry stragglers individually. Returns (ok, failed)."""
    remaining = {r["remote"]: r for r in todo}
    ok: list = []

    if not args.no_tar:
        for i in range(0, len(todo), args.batch):
            batch = [r for r in todo[i:i + args.batch] if r["remote"] in remaining]
            if not batch:
                continue
            print(f"  streaming batch {i // args.batch + 1} "
                  f"({len(batch)} file(s), {sum(r['size'] for r in batch) / 1e6:.0f} MB)...")
            for path in fetch_batch_tar(args, batch):
                ok.append(remaining.pop(path))

    for attempt in range(1, args.retries + 1):
        if not remaining:
            break
        print(f"  scp pass {attempt} for {len(remaining)} remaining file(s)...")
        for path, rec in list(remaining.items()):
            if fetch_one_scp(args, rec):
                ok.append(remaining.pop(path))
        if remaining and attempt < args.retries:
            time.sleep(2)

    return ok, list(remaining.values())


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #

def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} GB"


def print_listing(routes, order, dongle, args, limit):
    print(f"\nDevice {args.host}  dongle {dongle}  dir {args.remote_dir}")
    print(f"{len(routes)} route(s), {sum(len(s) for s in routes.values())} "
          f"{args.kind} segment(s)\n")
    print(f"  {'ROUTE':<24} {'SEGS':>4} {'SPAN':>7} {'BYTES':>9}  "
          f"{'NEWEST LOG (local)':<19}  LOCAL")
    print("  " + "-" * 88)
    for route in order[:limit]:
        segs = routes[route]
        nums = sorted(segs)
        total = sum(v[1] for v in segs.values())
        newest = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(route_mtime(segs)))
        have = sum(
            1 for s in nums
            if os.path.exists(os.path.join(
                args.dest, local_name(dongle, route, s, args.kind))))
        span = f"{nums[0]}-{nums[-1]}" if len(nums) > 1 else str(nums[0])
        tag = "complete" if have == len(nums) else (f"{have}/{len(nums)}" if have else "-")
        print(f"  {route:<24} {len(nums):>4} {span:>7} {fmt_bytes(total):>9}  "
              f"{newest:<19}  {tag}")
    if len(order) > limit:
        print(f"  ... and {len(order) - limit} older route(s); "
              f"raise --list-limit to see them")
    print()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Fetch openpilot rlogs from the comma device over SSH (read-only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/fetch_rlogs.py --list\n"
               "  python tools/fetch_rlogs.py --latest 1\n"
               "  python tools/fetch_rlogs.py --route 00000077--7411859c54\n"
               "  python tools/fetch_rlogs.py --latest 2 --dry-run\n")
    p.add_argument("--list", action="store_true",
                   help="enumerate routes on the device, newest first; transfer nothing")
    p.add_argument("--latest", type=int, metavar="N", nargs="?", const=1,
                   help="fetch the N newest routes (default 1)")
    p.add_argument("--route", action="append", default=[], metavar="ROUTEID",
                   help="fetch a named route; repeatable. Accepts 'ROUTE' or "
                        "'DONGLE/ROUTE'")
    p.add_argument("--segments", metavar="SPEC",
                   help="restrict to these segments, e.g. '0-5,12' (applies to every "
                        "selected route)")
    p.add_argument("--dry-run", action="store_true",
                   help="show what would be fetched and the byte totals; transfer nothing")
    p.add_argument("--dest", default=DEFAULT_DEST, help=f"local dir (default {DEFAULT_DEST})")
    p.add_argument("--kind", default="rlog", choices=("rlog", "qlog"),
                   help="which log to pull (default rlog)")
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"ssh host: a ~/.ssh/config alias or a bare IP "
                        f"(default {DEFAULT_HOST})")
    p.add_argument("--user", help="ssh user, e.g. 'comma'. Give this with --host <ip> "
                                  "and --key to bypass ~/.ssh/config entirely")
    p.add_argument("--key", metavar="PATH",
                   help="private key to authenticate with (implies IdentitiesOnly=yes)")
    p.add_argument("--accept-new-hostkey", action="store_true",
                   help="auto-accept the host key if the host is UNKNOWN. Per "
                        "ssh_config(5) this still REFUSES a host whose key has CHANGED, "
                        "so it does not bypass a reflashed device -- see the error text")
    p.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR,
                   help=f"remote route dir (default {DEFAULT_REMOTE_DIR})")
    p.add_argument("--dongle", help="override the dongle id (default: read from device)")
    p.add_argument("--known-hosts", metavar="PATH",
                   help="use this known_hosts file instead of the default, still "
                        "strict. Not needed in normal use -- it is for working "
                        "against a pinned key after a device reimage changes the "
                        "host key, without editing the real known_hosts")
    p.add_argument("--ssh-opt", action="append", default=[], metavar="OPT",
                   help="extra -o option for ssh/scp; repeatable")
    p.add_argument("--no-tar", action="store_true",
                   help="disable the batched tar stream; use per-file scp only")
    p.add_argument("--batch", type=int, default=25,
                   help="files per tar stream (default 25)")
    p.add_argument("--retries", type=int, default=2,
                   help="scp retry passes for stragglers (default 2)")
    p.add_argument("--connect-timeout", type=int, default=15)
    p.add_argument("--list-timeout", type=int, default=180)
    p.add_argument("--scp-timeout", type=int, default=600)
    p.add_argument("--list-limit", type=int, default=15,
                   help="rows to show in --list (default 15)")
    p.add_argument("--sort", default="mtime", choices=("mtime", "route"),
                   help="newest-first key: log mtime (default) or the monotonic "
                        "route counter (immune to pre-GPS clock skew)")
    return p.parse_args(argv)


def parse_segspec(spec: str) -> set[int]:
    out: set[int] = set()
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            lo, hi = piece.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(piece))
    return out


def main(argv=None) -> int:
    args = parse_args(argv)

    if not args.list and args.latest is None and not args.route:
        args.list = True
        print("(no action given -- showing --list; use --latest N or --route ROUTEID "
              "to fetch)")

    try:
        dongle = get_dongle(args)
        print(f"Enumerating {args.kind}s on {args.host}:{args.remote_dir} ...")
        routes = enumerate_logs(args)
    except DeviceError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2

    order = sort_routes_newest_first(routes, args.sort)

    if args.list:
        print_listing(routes, order, dongle, args, args.list_limit)
        if args.latest is None and not args.route:
            return 0

    wanted: list[str] = []
    if args.latest is not None:
        wanted += order[:max(0, args.latest)]
    for raw in args.route:
        r = normalise_route(raw)
        if r not in wanted:
            wanted.append(r)
    if not wanted:
        return 0

    os.makedirs(args.dest, exist_ok=True)
    todo, skipped, missing = build_plan(args, dongle, routes, wanted)

    if args.segments:
        keep = parse_segspec(args.segments)
        todo = [r for r in todo if r["seg"] in keep]
        skipped = [r for r in skipped if r["seg"] in keep]

    for r in missing:
        print(f"\nWARNING: route {r} is not on the device. Closest by name:")
        near = [x for x in order if x.split("--")[0] == r.split("--")[0]] or order[:3]
        for n in near[:3]:
            print(f"    {n}")

    todo_bytes = sum(r["size"] for r in todo)
    skip_bytes = sum(r["size"] for r in skipped)
    print(f"\nSelected {len(wanted)} route(s): {', '.join(wanted)}")
    print(f"  already local, skipping : {len(skipped):>4} file(s)  {fmt_bytes(skip_bytes)}")
    print(f"  to fetch                : {len(todo):>4} file(s)  {fmt_bytes(todo_bytes)}")
    print(f"  destination             : {os.path.abspath(args.dest)}")

    if args.dry_run:
        print("\n--dry-run: nothing transferred. Would fetch:")
        for r in todo:
            print(f"    {r['remote']}  ->  {os.path.basename(r['dest'])}  "
                  f"({fmt_bytes(r['size'])})")
        return 0

    if not todo:
        print("\nNothing to do -- everything selected is already present locally.")
        return 0

    t0 = time.time()
    ok, failed = fetch_all(args, todo)
    dt = max(time.time() - t0, 1e-6)
    got = sum(r["size"] for r in ok)

    print(f"\n{'=' * 60}")
    print(f"Fetched {len(ok)}/{len(todo)} file(s), {fmt_bytes(got)} in {dt:.1f}s "
          f"({got / dt / 1e6:.1f} MB/s)")
    if skipped:
        print(f"Skipped {len(skipped)} already-present file(s) ({fmt_bytes(skip_bytes)})")
    if failed:
        print(f"\nFAILED {len(failed)} file(s) -- re-run the same command to retry:")
        for r in failed:
            print(f"    {r['remote']}")
        return 1
    print("All requested files are present locally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
