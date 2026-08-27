#!/usr/bin/env python3
r"""Which fork/version was the device running on routes 7d / 77 / 78 / 79, and what car did it think
it was driving?  Read from `initData` and `carParams` in each route's FIRST rlog segment.

WHY IT MATTERS.  If route 7d ran a different fork or branch than r77/r78/r79, every cross-route
comparison in this session carries an openpilot confound.  And `STEER_THRESHOLD` -- the constant
behind `steeringPressed` and therefore behind `steerOverride` -- is keyed on `carFingerprint`, so
the fingerprint has to be read, not assumed.

Usage:  python studies/v91-v94-dose/v94_r7d_fork_version.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import rlog_parse  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
PREF = {"7d": "75604b0a432fdc89_0000007d--83a5c80392",
        "77": "75604b0a432fdc89_00000077--7411859c54",
        "78": "75604b0a432fdc89_00000078--93548c06b3",
        "79": "75604b0a432fdc89_00000079--cb7538ffae"}
FIELDS = ("version", "gitCommit", "gitBranch", "gitRemote", "dirty", "deviceType")


def one(route):
    p = RLOGDIR / f"{PREF[route]}--0--rlog.zst"
    out = {"route": route, "rlog": p.name}
    n = 0
    for evt in rlog_parse.read_messages(p):
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "initData" and "version" not in out:
            d = evt.initData
            for f in FIELDS:
                try:
                    out[f] = str(getattr(d, f))
                except Exception:
                    out[f] = "<absent>"
        elif w == "carParams" and "carFingerprint" not in out:
            c = evt.carParams
            for f in ("carFingerprint", "carName", "fingerprintSource",
                      "steerActuatorDelay", "steerLimitTimer"):
                try:
                    out[f] = str(getattr(c, f))
                except Exception:
                    out[f] = "<absent>"
        if "version" in out and "carFingerprint" in out:
            break
        if n > 60000:
            break
    out["messages_scanned"] = n
    return out


def main():
    res = {r: one(r) for r in ("7d", "77", "78", "79")}
    keys = ["version", "gitBranch", "gitCommit", "gitRemote", "dirty", "carFingerprint",
            "fingerprintSource", "steerActuatorDelay"]
    w = max(len(k) for k in keys) + 2
    print("=" * 110)
    print("  FORK / VERSION, read from initData + carParams in each route's segment 0")
    print("=" * 110)
    print("  " + "field".ljust(w) + "".join(f"{'r' + r:>24}" for r in res))
    for k in keys:
        print("  " + k.ljust(w) + "".join(f"{str(res[r].get(k, '<absent>'))[-23:]:>24}"
                                          for r in res))
    same = {k: len({res[r].get(k) for r in res}) == 1 for k in keys}
    print()
    for k in keys:
        print(f"  {k:<22} IDENTICAL ACROSS ALL FOUR ROUTES: {same[k]}")
    ok = all(same[k] for k in ("version", "gitBranch", "gitCommit", "dirty", "carFingerprint"))
    print()
    print("  ⇒ " + ("✅ SAME FORK, SAME COMMIT, SAME BRANCH, SAME FINGERPRINT ON ALL FOUR ROUTES "
                    "-- the openpilot-version confound is RETIRED."
                    if ok else
                    "🛑 THE ROUTES DID NOT ALL RUN THE SAME OPENPILOT BUILD -- see the rows above; "
                    "every cross-route comparison carries this confound."))
    (ROOT / "analysis-2020accord" / "_scratch/cache/r7d" / "fork_version.json").write_text(
        json.dumps(res, indent=1))
    print("\n  wrote analysis-2020accord/_scratch/cache/r7d/fork_version.json")


if __name__ == "__main__":
    main()
