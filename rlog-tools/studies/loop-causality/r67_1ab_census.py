#!/usr/bin/env python3
"""RAW-CAN census of 0x1AB (427) -- is MOTOR_TORQUE actually zero on the wire, or merely never
decoded by openpilot?

WHY THIS EXISTS
  The kit's memory `honda-op-steeringtorqueeps-always-zero` rests on `carState.steeringTorqueEps`.
  A source audit of the production fork found that the Honda car port never references
  MOTOR_TORQUE / 0x1AB at all and never assigns `ret.steeringTorqueEps` -- so that field may be the
  capnp DEFAULT of an unpopulated slot, saying nothing about the wire. This file goes to the `can`
  stream instead.
  🛑 `_scratch/cache/r67x/r67.npz` stores only `raw1ab_b0` (byte 0). The census below needs all three
  bytes and every `src`, so this re-parses the rlogs rather than reading the cache.

DBC LAYOUT BEING TESTED -- Motorola/big-endian bit numbering (bit 7..0 in byte 0, 15..8 in byte 1,
23..16 in byte 2), so DBC bit n lives at byte n//8, bit n%8:
    MOTOR_TORQUE     1|10@0+   -> byte0 bits[1:0] as the two MSBs, byte1 as the low 8  (10-bit)
    CONFIG_VALID     7|1       -> byte0 bit 7
    CHECKSUM        19|4       -> byte2 bits[3:0]
    COUNTER         21|2       -> byte2 bits[5:4]
    OUTPUT_DISABLED 22|1       -> byte2 bit 6
  ⚠ byte0 bits 6..2 are NOT named by that field list. The kit's own extractor treats byte0 bit 2 as
  "DTC active". Every one of the 24 bits is censused below so nothing is assumed.

THE DISCRIMINATOR the orchestrator asked for: if COUNTER increments and CHECKSUM varies while
MOTOR_TORQUE sits at zero, the gateway is passing a live frame and the zero is the FIRMWARE's.

Usage:  python studies/loop-causality/r67_1ab_census.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
TARGETS = {
    "r67/V81": ("75604b0a432fdc89_00000067--9b3ebbe218", list(range(14))),
    "r65/V76": ("75604b0a432fdc89_00000065--ae43aa0f27", [2, 5, 8]),
}
ADDR = 0x1AB
OUT = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def parse(route, segs):
    """Every 0x1AB frame on every src, plus the covariates needed for the correlation step."""
    from rlog_parse import read_messages

    rows, srcs, dlcs = [], Counter(), Counter()
    cov = {"t": [], "v": [], "lat": [], "tq": [], "sc": [], "ang": []}
    last = {"tq": np.nan, "sc": np.nan, "ang": np.nan}
    t0 = None
    for si, s in enumerate(segs):
        p = RLOGDIR / f"{route}--{s}--rlog.zst"
        if not p.exists():
            continue
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if t0 is None:
                t0 = tm
            if w == "can":
                for m in evt.can:
                    a, src = int(m.address), int(m.src)
                    d = bytes(m.dat)
                    if a == ADDR:
                        srcs[src] += 1
                        dlcs[len(d)] += 1
                        if len(d) >= 3:
                            rows.append((tm - t0, src, s, d[0], d[1], d[2]))
                    elif src == 1 and a == 0x18F and len(d) >= 4:
                        v = (d[0] << 8) | d[1]
                        last["tq"] = (v - 0x10000 if v & 0x8000 else v) * -1.0
                    elif src == 1 and a == 0x14A and len(d) >= 2:
                        v = (d[0] << 8) | d[1]
                        last["ang"] = (v - 0x10000 if v & 0x8000 else v) * -0.1
            elif w == "sendcan":
                for m in evt.sendcan:
                    if int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 2:
                            v = (d[0] << 8) | d[1]
                            last["sc"] = float(v - 0x10000 if v & 0x8000 else v)
            elif w == "carState":
                cov["t"].append(tm - t0)
                cov["v"].append(float(evt.carState.vEgo))
                cov["tq"].append(last["tq"])
                cov["sc"].append(last["sc"])
                cov["ang"].append(last["ang"])
                cov["lat"].append(np.nan)
            elif w == "carControl":
                if cov["lat"]:
                    cov["lat"][-1] = float(bool(evt.carControl.latActive))
        print(f"    seg {s} done, 0x1AB rows {len(rows)}", flush=True)
    return np.array(rows, float), srcs, dlcs, cov


def census(tag, A, srcs, dlcs):
    print(f"\n---- {tag} ----")
    if not len(A):
        print("  🛑 0x1AB NEVER APPEARS on any src. That would be the decisive answer to Q1.")
        OUT[tag] = dict(present=False)
        return None
    print(f"  frames: {len(A)}   src histogram: {dict(srcs)}   DLC histogram: {dict(dlcs)}")
    res = {"present": True, "n": len(A), "srcs": dict(srcs), "dlcs": dict(dlcs)}
    for src in sorted(srcs):
        m = A[:, 1] == src
        t = A[m, 0]
        if len(t) < 10:
            continue
        dt = np.diff(t)
        good = dt[(dt > 0) & (dt < 0.5)]
        # rate over the LONGEST gap-free stretch, not 1/median(dt)
        brk = np.flatnonzero(dt > 0.5)
        bounds = np.concatenate(([0], brk + 1, [len(t)]))
        spans = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
        a, b = max(spans, key=lambda s: s[1] - s[0])
        rate = (b - a - 1) / (t[b - 1] - t[a]) if t[b - 1] > t[a] else np.nan
        print(f"  src {src}: n={int(m.sum())}  span {t[0]:.1f}..{t[-1]:.1f} s  "
              f"longest gap-free stretch {b - a} frames / {t[b - 1] - t[a]:.1f} s  "
              f"=> {rate:.2f} Hz   (1/median(dt) = {1 / np.median(good):.2f} Hz)  "
              f"gaps>0.5 s: {len(brk)}")
        res.setdefault("rate", {})[src] = float(rate)
    return res


def bits(tag, A, res):
    print(f"\n  PER-BIT CENSUS, {tag} -- DBC bit number, byte.bit, duty, and whether it EVER changes")
    b = A[:, 3:6].astype(np.uint8)
    print(f"    {'dbc':>4s} {'byte.bit':>9s} {'duty %':>9s} {'changes':>8s}  {'value(s)':>12s}")
    per = {}
    for byi in range(3):
        for bit in range(7, -1, -1):
            dbc = byi * 8 + bit
            v = (b[:, byi] >> bit) & 1
            duty = 100.0 * v.mean()
            ch = int(np.sum(np.abs(np.diff(v.astype(int))) > 0))
            vals = "constant 0" if duty == 0 else ("constant 1" if duty == 100 else "VARIES")
            print(f"    {dbc:4d} {f'{byi}.{bit}':>9s} {duty:8.3f}% {ch:8d}  {vals:>12s}")
            per[dbc] = dict(byte=byi, bit=bit, duty=duty, changes=ch)
    res["bits"] = per
    ub = [np.unique(b[:, i]).tolist() for i in range(3)]
    print(f"    distinct byte values: byte0 {ub[0][:12]}{'...' if len(ub[0]) > 12 else ''} "
          f"({len(ub[0])})   byte1 ({len(ub[1])})   byte2 ({len(ub[2])})")
    res["uniq_bytes"] = [len(u) for u in ub]
    return b


def fields(tag, A, b, res):
    b0, b1, b2 = b[:, 0], b[:, 1], b[:, 2]
    mt = ((b0 & 0x03).astype(np.uint16) << 8) | b1
    cfg = (b0 >> 7) & 1
    chk = b2 & 0x0F
    cnt = (b2 >> 4) & 0x03
    od = (b2 >> 6) & 1
    print(f"\n  DECODED FIELDS, {tag}")
    print(f"    MOTOR_TORQUE (1|10@0+, 10-bit unsigned)")
    print(f"      min {mt.min():4d}  p50 {int(np.percentile(mt,50)):4d}  p90 "
          f"{int(np.percentile(mt,90)):4d}  p99 {int(np.percentile(mt,99)):4d}  max {mt.max():4d}"
          f"   nonzero {100 * np.mean(mt != 0):.4f}%   distinct {len(np.unique(mt))}")
    h = Counter(int(x) for x in mt)
    print(f"      histogram (top 10): {h.most_common(10)}")
    print(f"      as SIGNED (value - 512): min {int(mt.min()) - 512}  p50 "
          f"{int(np.percentile(mt,50)) - 512}  max {int(mt.max()) - 512}")
    print(f"    CONFIG_VALID    (bit 7)      duty {100 * cfg.mean():7.3f}%  distinct "
          f"{sorted(np.unique(cfg).tolist())}")
    print(f"    OUTPUT_DISABLED (bit 22)     duty {100 * od.mean():7.3f}%  distinct "
          f"{sorted(np.unique(od).tolist())}")
    print(f"    COUNTER         (21|2)       distinct {sorted(np.unique(cnt).tolist())}")
    d = np.diff(cnt.astype(int)) % 4
    print(f"      step histogram (mod 4): {dict(Counter(int(x) for x in d).most_common())}  "
          f"=> increments by 1 on {100 * np.mean(d == 1):.2f}% of consecutive frames")
    print(f"    CHECKSUM        (19|4)       distinct {sorted(np.unique(chk).tolist())}  "
          f"entropy-ish: {len(np.unique(chk))}/16 values, duty of each: "
          f"{dict(Counter(int(x) for x in chk).most_common(6))}")
    res["motor_torque"] = dict(min=int(mt.min()), p50=int(np.percentile(mt, 50)),
                               max=int(mt.max()), nonzero_pct=float(100 * np.mean(mt != 0)),
                               distinct=int(len(np.unique(mt))),
                               hist=[[int(k), int(v)] for k, v in h.most_common(10)])
    res["config_valid"] = float(100 * cfg.mean())
    res["output_disabled"] = float(100 * od.mean())
    res["counter_inc1_pct"] = float(100 * np.mean(d == 1))
    res["checksum_distinct"] = int(len(np.unique(chk)))

    print(f"\n  🛑 THE DISCRIMINATOR:")
    live_frame = (np.mean(d == 1) > 0.9) and (len(np.unique(chk)) > 4)
    mt_zero = np.all(mt == 0)
    if live_frame and mt_zero:
        print("     COUNTER increments and CHECKSUM varies, but MOTOR_TORQUE is IDENTICALLY ZERO.")
        print("     ⇒ the gateway is passing a live, well-formed frame and the ZERO IS THE")
        print("       FIRMWARE'S OWN OUTPUT. openpilot's non-decoding is a SEPARATE, additional")
        print("       fact and does not explain the zero.")
    elif not mt_zero:
        print(f"     MOTOR_TORQUE IS LIVE ON THE WIRE ({100 * np.mean(mt != 0):.3f}% of frames "
              f"non-zero, {len(np.unique(mt))} distinct values).")
        print("     ⇒ openpilot never decodes it, so `carState.steeringTorqueEps` is an")
        print("       UNPOPULATED capnp default. The kit has been blind to a real EPS channel.")
    else:
        print("     Frame does not look live (counter/checksum static) -- read Q1/Q2 first.")
    res["verdict"] = ("firmware_zero" if (live_frame and mt_zero)
                      else "live_on_wire" if not mt_zero else "frame_not_live")
    return mt, cnt, chk, od, cfg


def correlate(tag, A, mt, cov):
    """Does MOTOR_TORQUE move with anything?  Only run when it is not identically zero."""
    if np.all(mt == 0):
        print(f"\n  correlations skipped for {tag}: MOTOR_TORQUE is identically zero.")
        return
    t = A[:, 0]
    ct = np.array(cov["t"], float)
    if len(ct) < 10:
        return
    print(f"\n  MOTOR_TORQUE vs covariates, {tag} (covariates held to the 0x1AB timestamps)")
    lat = np.array(cov["lat"], float)
    lat = np.where(np.isfinite(lat), lat, 0.0)
    for nm, key in (("vEgo", "v"), ("torsion bar |tq|", "tq"), ("LKAS cmd |0x0E4|", "sc"),
                    ("|angle|", "ang"), ("latActive", None)):
        y = lat if key is None else np.array(cov[key], float)
        if key in ("tq", "sc", "ang"):
            y = np.abs(y)
        g = np.interp(t, ct, np.where(np.isfinite(y), y, 0.0))
        m = np.isfinite(g)
        if m.sum() < 50:
            continue
        print(f"    corr(MOTOR_TORQUE, {nm:18s}) = {np.corrcoef(mt[m], g[m])[0,1]:+.4f}")
    if "r67" in tag:
        print("    ⇒ and through the seg-8 ring specifically: see the caller.")


def main():
    for tag, (route, segs) in TARGETS.items():
        hdr(f"PARSING {tag}  ({len(segs)} segments)")
        A, srcs, dlcs, cov = parse(route, segs)
        res = census(tag, A, srcs, dlcs)
        if res is None or not res.get("present"):
            OUT[tag] = res or {"present": False}
            continue
        b = bits(tag, A, res)
        mt, cnt, chk, od, cfg = fields(tag, A, b, res)
        correlate(tag, A, mt, cov)
        OUT[tag] = res
        np.savez_compressed(ROOT / "_scratch/cache/r67x" / f"r1ab_{tag.split('/')[0]}.npz",
                            t=A[:, 0], src=A[:, 1], seg=A[:, 2],
                            b0=A[:, 3], b1=A[:, 4], b2=A[:, 5], motor_torque=mt)
    (ROOT / "_scratch/cache/r67x" / "r67_1ab_census.json").write_text(json.dumps(OUT, indent=1,
                                                                        default=float))
    print(f"\nwrote {ROOT / '_scratch/cache/r67x' / 'r67_1ab_census.json'}")


if __name__ == "__main__":
    main()
