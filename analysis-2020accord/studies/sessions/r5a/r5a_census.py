#!/usr/bin/env python3
"""Route 5a orientation: what each candidate command channel ACTUALLY carries, and the exposure.

Answers, before any hypothesis is tested:
  1. Which bus channel is a COMMAND with a RAIL, and what is that rail numerically?
  2. Exposure census: frames, engaged/manual, per speed bin, per mode, per |angle| bin.
  3. Is the +-0x2000 mixer rail observable at all on this route? (spoiler: no -- state it.)
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

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _r5a_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEGS = list(range(18))
KMH = 1 / 3.6
out = {}

# ------------------------------------------------------------------ 1. channel census ------------
L.hdr("1. CHANNEL CENSUS -- every candidate, whole route, no masking")
acc = {}
for s in SEGS:
    d = L.load_seg(s)
    for k in ("tq", "e4tq", "e4req", "cc_req", "ang", "rate_c", "rate_f", "sca", "sstat", "slow3",
              "cs_v", "cc_lat", "cs_tq", "cs_ang", "mode", "field", "live", "probe", "cs_press"):
        if k in d:
            acc.setdefault(k, []).append(np.asarray(d[k], float))
A = {k: np.concatenate(v) for k, v in acc.items()}
N = len(A["tq"])
print(f"frames {N}   duration {N / 100.0:.1f} s (100 Hz lattice)")
print(f"{'chan':9s} {'min':>9s} {'max':>9s} {'mean':>9s} {'p99|.|':>9s} "
      f"{'!=0':>7s} {'#uniq':>7s}   note")
for k in ("tq", "e4tq", "cc_req", "e4req", "cs_v", "ang", "rate_c", "rate_f", "sca", "sstat",
          "slow3", "mode", "live"):
    a = A[k]
    print(f"{k:9s} {np.nanmin(a):9.2f} {np.nanmax(a):9.2f} {np.nanmean(a):9.3f} "
          f"{np.nanpercentile(np.abs(a), 99):9.2f} {np.mean(np.abs(a) > 1e-9):7.3f} "
          f"{len(np.unique(a[np.isfinite(a)])):7d}")

# ---- the rail of e4tq: is it a hard clip, and at what value? -------------------------------------
L.hdr("1b. IS `e4tq` (openpilot's request) A CLIPPED SIGNAL, AND WHERE IS ITS RAIL?")
e = A["e4tq"]
req = A["e4req"] > 0.5
print(f"e4req (STEER_TORQUE_REQUEST) true in {req.mean() * 100:.2f}% of frames "
      f"({req.sum()} / {N})")
er = e[req]
print(f"while requesting: min {er.min():.0f}  max {er.max():.0f}  "
      f"|.| p50 {np.percentile(np.abs(er), 50):.0f}  p90 {np.percentile(np.abs(er), 90):.0f}  "
      f"p99 {np.percentile(np.abs(er), 99):.0f}")
vals, cnts = np.unique(np.abs(er), return_counts=True)
print("top-12 |e4tq| values while requesting (a hard clip shows as a spike at the max):")
o = np.argsort(-cnts)[:12]
for i in o:
    print(f"   |{vals[i]:8.0f}|  {cnts[i]:7d}  {cnts[i] / len(er) * 100:6.3f}%")
RAIL = float(np.abs(er).max())
at = np.mean(np.abs(er) >= RAIL - 0.5)
near = np.mean(np.abs(er) >= 0.98 * RAIL)
print(f"\nRAIL(e4tq) = {RAIL:.0f}.  at rail {at * 100:.3f}%   within 2% of rail {near * 100:.3f}%")
print("cc_req (carControl.actuators.torque, normalised) at |1.0|: "
      f"{np.mean(np.abs(A['cc_req'][req]) >= 0.999) * 100:.3f}%")
print("⇒ e4tq / cc_req ratio (counts per unit): "
      f"{np.nanmedian(np.abs(er)[np.abs(A['cc_req'][req]) > 0.05] / np.abs(A['cc_req'][req])[np.abs(A['cc_req'][req]) > 0.05]):.1f}")

L.hdr("1c. WHAT IS **NOT** OBSERVABLE ON THIS ROUTE")
print(L.NOT_OBSERVABLE)
print("\n🛑 The +-0x2000 = 8192 clamp is a CODE IMMEDIATE inside FUN_00042af8 acting on an internal")
print("   accumulator. Nothing on the bus carries it. The strongest bus-side test available is")
print("   whether openpilot's REQUEST -- the largest of the four mixer channels -- is itself")
print("   saturated, because a request pinned at its own rail is the only way this route can")
print("   witness 'the command is asking for more than the chain can pass'.")

# ------------------------------------------------------------------ 2. exposure --------------
L.hdr("2. EXPOSURE CENSUS")
eng = A["cc_lat"] > 0.5
v = np.abs(A["cs_v"])
mo = A["mode"]
print(f"engaged {eng.mean() * 100:.2f}%  ({eng.sum()} frames / {eng.sum() / 100:.1f} s)")
print(f"manual  {(~eng).mean() * 100:.2f}%  ({(~eng).sum()} frames / {(~eng).sum() / 100:.1f} s)")
print("\nmode histogram (whole route):")
for m in sorted(set(mo[np.isfinite(mo)])):
    k = mo == m
    print(f"   mode {int(m):2d}: {k.sum():7d} frames  {k.mean() * 100:6.2f}%   "
          f"engaged-within-mode {eng[k].mean() * 100:6.2f}%   v median {np.median(v[k]):5.2f} m/s")
print("\nmode x engagement:")
for m in sorted(set(mo[np.isfinite(mo)])):
    for lbl, msk in (("eng", eng), ("man", ~eng)):
        k = (mo == m) & msk
        if k.sum():
            print(f"   mode {int(m):2d} {lbl}: {k.sum():7d} frames ({k.sum() / 100:7.1f} s)")

VB = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 14), (14, 100)]
print("\nspeed x engagement exposure (m/s):")
print(f"{'v bin':>10s} {'eng s':>9s} {'man s':>9s} {'eng mode10 s':>13s} {'man mode8 s':>12s}")
for lo, hi in VB:
    k = (v >= lo) & (v < hi)
    print(f"{lo:4.0f}-{hi:<5.0f} {(k & eng).sum() / 100:9.1f} {(k & ~eng).sum() / 100:9.1f} "
          f"{(k & eng & (mo == 10)).sum() / 100:13.1f} {(k & ~eng & (mo == 8)).sum() / 100:12.1f}")

AB = [(0, 1), (1, 3), (3, 6), (6, 12), (12, 30), (30, 1e9)]
print("\n|steering angle| x engagement exposure (deg), at creep (0.5 <= v < 4 m/s):")
creep = (v >= 0.5) & (v < 4.0)
aa = np.abs(A["ang"])
for lo, hi in AB:
    k = creep & (aa >= lo) & (aa < hi)
    print(f"  |ang| {lo:5.0f}-{hi:<7.0f} eng {(k & eng).sum() / 100:8.1f} s   "
          f"man {(k & ~eng).sum() / 100:8.1f} s")

# ---- parked / stationary segments ----------------------------------------------------------
print("\nper-segment: frames, engaged %, v median/max, mode set")
park = []
for s in SEGS:
    d = L.load_seg(s)
    vv = np.abs(np.asarray(d["cs_v"], float))
    ee = np.asarray(d["cc_lat"], float) > 0.5
    mm = np.asarray(d["mode"], float)
    ms = sorted({int(x) for x in np.unique(mm)})
    gg = np.median(np.asarray(d["cs_gear"], float)) if "cs_gear" in d else np.nan
    flag = ""
    if vv.max() < 0.3 and ee.mean() < 0.005:
        park.append(s)
        flag = "  <-- PARKED/STATIONARY"
    print(f"  seg {s:2d}  n {len(vv):6d}  eng {ee.mean() * 100:6.2f}%  "
          f"v med {np.median(vv):5.2f} max {vv.max():6.2f}  gear {gg:4.1f}  modes {ms}{flag}")
print(f"\nPARKED candidates: {park}")

out = dict(frames=int(N), rail_e4tq=RAIL, at_rail_frac=float(at), near_rail_frac=float(near),
           eng_frac=float(eng.mean()), parked=park,
           mode_hist={int(m): int((mo == m).sum()) for m in sorted(set(mo[np.isfinite(mo)]))})
with open(ROOT / "_scratch/out/_r5a_census.json", "w") as fh:
    json.dump(out, fh, indent=1)
print("\nwrote _scratch/out/_r5a_census.json")
