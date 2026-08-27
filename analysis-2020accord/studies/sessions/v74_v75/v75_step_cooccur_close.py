#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_cooccur_close.py -- the two derived numbers the co-occurrence result turns on.

  A. THE UNITS WINDOW. For which command-scale k does V75's pair (cmd + 594) exceed the 4762
     governor ceiling while V74's (cmd + 450) does NOT? If that window is razor-thin, the
     mechanism is fine-tuned and that is itself evidence about its plausibility.
  B. EPISODE-LEVEL SIGN TEST on the AT-RAIL TRANSITION RATE (the headline quantity), plus the
     "how much help does each build need from the other 9 lanes" figure.
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
import sys
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

W = 1.0 / 100.0009
RAIL, GOV = 4096.0, 4762.0
STEP = {"V74": 450, "V75": 594}
BUILDS = [("V74", 400), ("V75", 200)]

D = L.load_route()
n = len(D["t"])
r_cts = np.abs(np.trunc(np.rint(D["rate_f"] * 10.0) * 2048.0 / 3477.0).astype(np.int64))
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, _, _ = L.mode_masks(D["cc_lat"], D["t"])
cmd = np.abs(D["e4tq"])
at_rail = (cmd >= RAIL - 0.5) | (np.abs(np.r_[0.0, np.diff(D["e4tq"])]) >= 122.5)


def blocks(mask):
    m = mask & np.r_[True, np.diff(D["seg"]) == 0]
    idx = np.flatnonzero(m)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > 1)
    return [r for r in np.split(idx, brk + 1) if len(r)]


def transitions(mask, entry):
    out = []
    for b in blocks(mask):
        occ = (r_cts[b] >= entry).astype(np.int8)
        for k in np.flatnonzero(np.diff(occ) != 0) + 1:
            out.append(int(b[k]))
    return np.array(sorted(out), dtype=int)


print("=" * 100)
print("A.  THE UNITS WINDOW -- where does this mechanism DISCRIMINATE between the two builds?")
print("=" * 100)
lo = (GOV - STEP["V75"]) / RAIL          # V75 binds above this scale
hi = (GOV - STEP["V74"]) / RAIL          # V74 binds above this scale
print(f"  At openpilot's rail (|cmd| = {RAIL:.0f}) and a full relay reversal:")
print(f"    V74 pair = {RAIL:.0f} + {STEP['V74']} = {RAIL+STEP['V74']:.0f}   "
      f"headroom to the {GOV:.0f} ceiling: {GOV-RAIL-STEP['V74']:.0f} counts")
print(f"    V75 pair = {RAIL:.0f} + {STEP['V75']} = {RAIL+STEP['V75']:.0f}   "
      f"headroom to the {GOV:.0f} ceiling: {GOV-RAIL-STEP['V75']:.0f} counts")
print(f"    => V75 needs only {GOV-RAIL-STEP['V75']:.0f} counts of help from the other 9 lanes "
      f"where V74 needs {GOV-RAIL-STEP['V74']:.0f} -- a "
      f"{(GOV-RAIL-STEP['V74'])/(GOV-RAIL-STEP['V75']):.2f}x reduction in required help.")
print(f"\n  Command-scale k for which V75 binds but V74 does NOT: "
      f"k in ({lo:.4f}, {hi:.4f}]  -- a window {100*(hi-lo)/lo:.1f}% wide.")
print(f"    k <= {lo:.4f}: NEITHER binds (openpilot+damper alone never reaches the ceiling)")
print(f"    k >  {hi:.4f}: BOTH bind (the mechanism stops discriminating)")
print("  ⇒ this mechanism separates V74 from V75 only if the bus->gp-0x6b98 scale sits inside a")
print("    3.5%-wide band around 1.0. That is fine-tuning, and it is unverified. [ASSUMPTION]")

print("\n" + "=" * 100)
print("B.  EPISODE-LEVEL SIGN TEST on AT-RAIL TRANSITION RATE, and the absolute counts")
print("=" * 100)
eps = L.episodes(D["cc_lat"], D["t"])
print(f"  {'ep':>3s} {'sec':>7s} | {'V74 tr':>7s} {'V74@rail':>9s} {'V75 tr':>7s} {'V75@rail':>9s}"
      f" | {'V74 r/s':>8s} {'V75 r/s':>8s} {'dir':>5s}")
ups = downs = ties = 0
for i, ee in enumerate(eps):
    m = np.zeros(n, bool)
    m[ee] = True
    m &= in26
    secs = float(m.sum()) * W
    row = {}
    for bn, entry in BUILDS:
        ti = transitions(m, entry)
        row[bn] = (len(ti), int(at_rail[ti].sum()) if len(ti) else 0)
    a = row["V74"][1] / max(secs, 1e-9)
    b = row["V75"][1] / max(secs, 1e-9)
    d = "UP" if b > a else ("DOWN" if b < a else "TIE")
    ups += b > a
    downs += b < a
    ties += b == a
    print(f"  {i:3d} {secs:7.1f} | {row['V74'][0]:7d} {row['V74'][1]:9d} {row['V75'][0]:7d} "
          f"{row['V75'][1]:9d} | {a:8.4f} {b:8.4f} {d:>5s}")
tot = ups + downs
p = 2 * sum(comb(tot, k) for k in range(max(ups, downs), tot + 1)) / 2 ** tot if tot else float("nan")
print(f"\n  {ups} UP / {downs} DOWN / {ties} TIE.  two-sided sign test on the {tot} informative "
      f"episodes: p = {min(p,1.0):.4f}")

m = in26
for bn, entry in BUILDS:
    ti = transitions(m, entry)
    nr = int(at_rail[ti].sum())
    print(f"  {bn}: {len(ti):4d} engaged transitions, {nr:4d} at a rail, "
          f"{nr/(m.sum()*W):.4f}/s  ({nr/max(len(ti),1)*100:.1f}% of its transitions)")
t4 = transitions(m, 400)
t2 = transitions(m, 200)
print(f"\n  ABSOLUTE: V75/V74 at-rail transition ratio = "
      f"{int(at_rail[t2].sum())/max(int(at_rail[t4].sum()),1):.2f}x")
print(f"  PER TRANSITION: P(at rail | transition) V74 {at_rail[t4].mean():.3f} vs "
      f"V75 {at_rail[t2].mean():.3f}  -> V74 is {'HIGHER' if at_rail[t4].mean()>at_rail[t2].mean() else 'LOWER'}")
print(f"\n  🛑 V74 flew 1,011 s with {int(at_rail[t4].sum())} at-rail engaged plateau transitions and "
      f"NEVER FAULTED.")
