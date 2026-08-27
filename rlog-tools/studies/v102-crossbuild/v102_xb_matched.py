#!/usr/bin/env python3
r"""V100 (r85, 4x) vs V101 (r95, 8x) -- the MATCHED contrast.

The pooled contrast in `studies/v102-crossbuild/v102_xb_bands.py` is CONFOUNDED and must not be quoted: the r95 engaged
windows carry a median wheel rate of 22.1 deg/s against r85's 7.3, and the excess it produces is
BROADBAND -- it shows up at 2.7-4.4x in the PRE-DECLARED NEGATIVE CONTROL band 32-38 Hz, and
`imu_lat` (the car's actual motion) is 1.00x in every band.  That is exposure, not build.

This file removes the confound three ways and reports all three:
  (S) STRATIFY on (speed x wheel rate) and pool the per-cell log-ratios.
  (C) SHAPE: band contrast = log(bandRMS / 32-38 Hz RMS), which is invariant to how hard the
      operator was steering.  The symptom is a TONE against a floor, not an absolute level.
  (N) NORMALISE by the firmware's own delivered lane: bandRMS(tq) / bandRMS(x6b94).

Bootstrap units: 15 s BLOCKS inside episodes (primary) and whole EPISODES (conservative).  Windows
are never the unit.
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
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
BLOCK_S = 15.0
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
SHOW = ("6-9", "15-22", "18-22", "26-31", "40-49", "32-38")
CTRL = "32-38"


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def unit_of(r, mode):
    if mode == "epi":
        return (r["route"], r["seg"], r["epi"])
    return (r["route"], r["seg"], r["epi"], int(r["t0"] // BLOCK_S))


def pooled_ratio(A, B, key, mode="blk", nboot=4000, seed=1, strat=None):
    """Ratio of medians, block-bootstrapped over `mode` units.  If `strat` is given it is a list of
    (labelA, labelB) window-list pairs and the statistic is the exp(mean of per-cell log ratios),
    weighted by min(nA, nB) -- i.e. stratified so no cell's exposure can drive the answer."""
    rng = np.random.default_rng(seed)

    def group(recs):
        d = {}
        for r in recs:
            v = r.get(key, np.nan)
            if np.isfinite(v):
                d.setdefault(unit_of(r, mode), []).append((v, r))
        return d

    if strat is None:
        cells = [(A, B)]
    else:
        cells = strat
    gA = [group(a) for a, _ in cells]
    gB = [group(b) for _, b in cells]

    def stat(pickA, pickB):
        num, den = [], []
        for ca, cb in zip(pickA, pickB):
            if not ca or not cb:
                continue
            va = np.concatenate(ca)
            vb = np.concatenate(cb)
            if len(va) < 3 or len(vb) < 3:
                continue
            w = min(len(va), len(vb))
            num.append(w * np.log(np.median(va) / np.median(vb)))
            den.append(w)
        if not den:
            return np.nan
        return float(np.exp(sum(num) / sum(den)))

    ptA = [[np.array([x for x, _ in v]) for v in g.values()] for g in gA]
    ptB = [[np.array([x for x, _ in v]) for v in g.values()] for g in gB]
    pt = stat(ptA, ptB)
    out = np.empty(nboot)
    for i in range(nboot):
        pa, pb = [], []
        for lst in ptA:
            pa.append([lst[j] for j in rng.integers(0, len(lst), len(lst))] if lst else [])
        for lst in ptB:
            pb.append([lst[j] for j in rng.integers(0, len(lst), len(lst))] if lst else [])
        out[i] = stat(pa, pb)
    good = out[np.isfinite(out)]
    lo, hi = np.percentile(good, [2.5, 97.5]) if len(good) > 10 else (np.nan, np.nan)
    nu = sum(len(x) for x in ptA), sum(len(x) for x in ptB)
    return dict(ratio=pt, lo=float(lo), hi=float(hi), uA=nu[0], uB=nu[1])


def row(lbl, res, note=""):
    if not np.isfinite(res["ratio"]):
        print("   %-24s        n/a" % lbl)
        return
    print("   %-24s %6.2f x  [%5.2f, %5.2f]   units %3d/%-3d %s"
          % (lbl, res["ratio"], res["lo"], res["hi"], res["uA"], res["uB"], note))


print("building windows ...")
E = {r: L.sel(L.windows(r, NFFT, HOP, engaged=True), vlo=5, vhi=65) for r in ("85", "95")}
M = {r: L.windows(r, NFFT, HOP, engaged=False) for r in ("85", "95")}
for r in ("85", "95"):
    print("   r%s engaged win=%d  15s-blocks=%d  episodes=%d"
          % (r, len(E[r]), len({unit_of(x, 'blk') for x in E[r]}), L.nepi(E[r])))

# add derived keys: band contrast (shape) and the x6b94-normalised transfer
for recs in list(E.values()) + list(M.values()):
    for r in recs:
        for ch in ("tq", "rate_c", "imu_lat"):
            c = r.get(ch + "|" + CTRL, np.nan)
            for bn in L.BANDS:
                v = r.get(ch + "|" + bn, np.nan)
                if np.isfinite(v) and np.isfinite(c) and c > 0:
                    r["shape:" + ch + "|" + bn] = v / c
        for bn in ("3-5", "6-9", "10-15"):
            num = r.get("tq|" + bn, np.nan)
            den = r.get("x6b94|" + bn, np.nan)
            if np.isfinite(num) and np.isfinite(den) and den > 0:
                r["perlane:tq|" + bn] = num / den

# =====================================================================================================
hdr("MATCHING CENSUS -- speed x wheel-rate cells actually populated on BOTH routes")
print("   cell = (speed bin) x (median |wheel rate| bin).  n = windows, u = 15 s blocks.")
CELLS = []
print("   %-14s %-14s %14s %14s" % ("speed", "rate deg/s", "V100 r85 n/u", "V101 r95 n/u"))
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a = L.sel(E["85"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b = L.sel(E["95"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        ua = len({unit_of(x, "blk") for x in a})
        ub = len({unit_of(x, "blk") for x in b})
        mark = ""
        if len(a) >= 5 and len(b) >= 5:
            CELLS.append((a, b))
            mark = "  <-- USED"
        print("   %-14s %-14s %9d/%-4d %9d/%-4d%s"
              % ("%d-%d km/h" % (vlo, vhi), "%d-%d" % (rlo, rhi), len(a), ua, len(b), ub, mark))
print("\n   %d cells are populated on both arms and enter the stratified estimate." % len(CELLS))
print("   Windows in used cells: V100 %d, V101 %d"
      % (sum(len(a) for a, _ in CELLS), sum(len(b) for _, b in CELLS)))

# =====================================================================================================
hdr("CONTROL 1 (redone) -- WITHIN-ROUTE SPLIT-HALF NULL on 15 s blocks, stratified the same way")
for rlbl, route in (("V100 r85", "85"), ("V101 r95", "95")):
    blocks_ = sorted({unit_of(x, "blk") for x in E[route]})
    odd = set(blocks_[1::2])
    cellsA = [([x for x in a if unit_of(x, "blk") in odd],
               [x for x in a if unit_of(x, "blk") not in odd]) for a, _ in CELLS] \
        if route == "85" else \
        [([x for x in b if unit_of(x, "blk") in odd],
          [x for x in b if unit_of(x, "blk") not in odd]) for _, b in CELLS]
    cellsA = [(p, q) for p, q in cellsA if len(p) >= 3 and len(q) >= 3]
    print("  %s  (%d cells survive the split)" % (rlbl, len(cellsA)))
    for ch in ("tq", "rate_c"):
        for bn in ("6-9", "18-22", "32-38"):
            row(ch + " " + bn, pooled_ratio(None, None, ch + "|" + bn, strat=cellsA,
                                            nboot=2000, seed=21))

# =====================================================================================================
hdr("CONTROL 2 (redone) -- LKAS OFF, MATCHED ON WHEEL RATE.  Manual exposure is 0-10 km/h only.")
MC = []
for rlo, rhi in [(0, 2), (2, 8), (8, 25), (25, 120)]:
    a = L.sel(M["85"], vlo=0, vhi=10, rlo=rlo, rhi=rhi)
    b = L.sel(M["95"], vlo=0, vhi=10, rlo=rlo, rhi=rhi)
    print("   rate %3d-%-3d deg/s   V100 n=%3d   V101 n=%3d %s"
          % (rlo, rhi, len(a), len(b), "<-- USED" if len(a) >= 5 and len(b) >= 5 else ""))
    if len(a) >= 5 and len(b) >= 5:
        MC.append((b, a))
if MC:
    print("   V101/V100 with LKAS OFF (the firmware LKAS lane is not running -> must be ~1.0):")
    for ch in ("tq", "rate_c", "imu_lat"):
        for bn in SHOW:
            row(ch + " " + bn, pooled_ratio(None, None, ch + "|" + bn, strat=MC,
                                            nboot=2000, seed=31))
else:
    print("   NO matched LKAS-off cell exists: r85's manual time is manoeuvring (|tq| p50 1184,")
    print("   21 deg/s) and r95's is standing still (|tq| p50 166, 1 deg/s).  THE LKAS-OFF CONTROL")
    print("   IS UNAVAILABLE ON THIS PAIR -- state that, do not fake it.")

# =====================================================================================================
hdr("MEASUREMENT S -- STRATIFIED (speed x rate) V101/V100 band RMS, ENGAGED.  Dose = 2.00x")
for ch in ("tq", "rate_c", "imu_lat", "x6b94"):
    print("\n  channel %s" % ch)
    for bn in L.BANDS:
        k = ch + "|" + bn
        if not any(k in r for r in E["85"]):
            continue
        note = "<-- NEGATIVE CONTROL" if bn == CTRL else ""
        strat = [(b, a) for a, b in CELLS]
        row(bn + "  [15s blocks]", pooled_ratio(None, None, k, strat=strat, nboot=3000, seed=41), note)

# =====================================================================================================
hdr("MEASUREMENT S' -- the same, EPISODE units (conservative; only 6 and 4 episodes exist)")
for ch in ("tq", "rate_c"):
    print("\n  channel %s" % ch)
    for bn in ("6-9", "18-22", "32-38"):
        strat = [(b, a) for a, b in CELLS]
        row(bn + "  [episodes]", pooled_ratio(None, None, ch + "|" + bn, mode="epi",
                                              strat=strat, nboot=3000, seed=43))

# =====================================================================================================
hdr("MEASUREMENT C -- SHAPE.  band RMS / 32-38 Hz RMS.  Invariant to how hard he was steering.")
print("   A ratio > 1 here means the band grew RELATIVE to the broadband floor -- a TONE appearing.")
for ch in ("tq", "rate_c", "imu_lat"):
    print("\n  channel %s" % ch)
    for bn in SHOW:
        if bn == CTRL:
            continue
        strat = [(b, a) for a, b in CELLS]
        row("shape " + bn, pooled_ratio(None, None, "shape:" + ch + "|" + bn, strat=strat,
                                        nboot=3000, seed=51))

# =====================================================================================================
hdr("MEASUREMENT N -- COLUMN TORQUE PER UNIT DELIVERED FIRMWARE TORQUE  tq / x6b94  (<20 Hz only)")
print("   x6b94 IS the firmware's own aggregator output, so this divides out the 2x dose.")
print("   ~1.0 => the plant responded linearly to twice the drive.  >1.0 => the LOOP changed.")
for bn in ("3-5", "6-9", "10-15"):
    strat = [(b, a) for a, b in CELLS]
    row("tq/x6b94 " + bn, pooled_ratio(None, None, "perlane:tq|" + bn, strat=strat,
                                       nboot=3000, seed=61))

print("\n[done]")
