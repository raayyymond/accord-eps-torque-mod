#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_rolling_null.py -- CORRECTED nulls for the two paired statistics.

🛑 The split-half null in studies/sessions/v74_v75/v75_step_rolling.py §6 is MIS-SPECIFIED and is retracted here.
   It compared COUNTS between two DISJOINT halves of the episode set. Counts scale with exposure,
   so a 4-vs-5 episode split has enormous exposure variance -- that null ([0.227, 2.533]) measures
   how unequal two random halves of a route are, NOT the noise on a PAIRED contrast.
   V74 and V75 are replayed on the SAME frames; the contrast is deterministic and paired. The right
   null splits episodes, forms the V75/V74 RATIO inside each half, and takes the ratio-of-ratios.
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

RNG = np.random.default_rng(20260806)
W = 1.0 / 100.0009
BREAKEVEN = 1.0 / 3.0

D = L.load_route()
n = len(D["t"])
r_cts = np.abs(np.trunc(np.rint(D["rate_f"] * 10.0) * 2048.0 / 3477.0).astype(np.int64))
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, _, _ = L.mode_masks(D["cc_lat"], D["t"])


def blocks(mask):
    m = mask & np.r_[True, np.diff(D["seg"]) == 0]
    idx = np.flatnonzero(m)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > 1)
    return [r for r in np.split(idx, brk + 1) if len(r)]


def stats_for(idxset, entry):
    """(n windows >1/3 at 30 ms, n transitions, seconds) inside one episode."""
    m = np.zeros(n, bool)
    m[idxset] = True
    m &= in26
    nw = ntr = 0
    secs = 0.0
    for b in blocks(m):
        occ = (r_cts[b] >= entry).astype(np.int8)
        secs += len(b) * W
        if len(occ) >= 3:
            c = np.cumsum(np.r_[0, occ.astype(np.int64)])
            d = (c[3:] - c[:-3]) / 3.0
            nw += int((d > BREAKEVEN).sum())
        ntr += int((np.abs(np.diff(occ)) == 1).sum())
    return nw, ntr, secs


eps = L.episodes(D["cc_lat"], D["t"])
per = [(stats_for(e, 400), stats_for(e, 200)) for e in eps]
print("=" * 100)
print("PER-EPISODE, engaged.  (win = 30 ms rolling windows >1/3 duty; tr = plateau transitions)")
print("=" * 100)
print(f"  {'ep':>3s} {'sec':>7s} | {'V74 win':>8s} {'V75 win':>8s} {'ratio':>6s} | "
      f"{'V74 tr':>7s} {'V75 tr':>7s} {'ratio':>6s} | {'V74 tr/s':>9s} {'V75 tr/s':>9s}")
for i, ((w4, t4, s4), (w2, t2, s2)) in enumerate(per):
    rw = w2 / w4 if w4 else float("nan")
    rt = t2 / t4 if t4 else float("nan")
    print(f"  {i:3d} {s4:7.1f} | {w4:8d} {w2:8d} {rw:6.2f} | {t4:7d} {t2:7d} {rt:6.2f} | "
          f"{t4/max(s4,1e-9):9.4f} {t2/max(s2,1e-9):9.4f}")


def boot_ratio(get_num, get_den, label, B=20000):
    pt = sum(get_num(p) for p in per) / max(sum(get_den(p) for p in per), 1e-9)
    bs = []
    for _ in range(B):
        pk = RNG.integers(0, len(per), len(per))
        a = sum(get_num(per[i]) for i in pk)
        b = sum(get_den(per[i]) for i in pk)
        if b:
            bs.append(a / b)
    bs = np.array(bs)
    # PAIRED split-half null: split episodes, form the RATIO in each half, ratio-of-ratios.
    nl = []
    for _ in range(B):
        pm = RNG.permutation(len(per))
        h1, h2 = pm[: len(per) // 2], pm[len(per) // 2:]

        def rat(h):
            a = sum(get_num(per[i]) for i in h)
            b = sum(get_den(per[i]) for i in h)
            return a / b if b else np.nan
        a, b = rat(h1), rat(h2)
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            nl.append(a / b)
    nl = np.array(nl)
    print(f"\n  {label}")
    print(f"    POINT {pt:.3f}   episode bootstrap 95% CI "
          f"[{np.percentile(bs,2.5):.3f}, {np.percentile(bs,97.5):.3f}]")
    print(f"    PAIRED split-half null (ratio-of-ratios, should straddle 1.0): median "
          f"{np.median(nl):.3f}  [{np.percentile(nl,2.5):.3f}, {np.percentile(nl,97.5):.3f}]")
    clears = np.percentile(bs, 2.5) > np.percentile(nl, 97.5)
    print(f"    CLEARS ITS OWN NULL: {clears}")
    return pt, bs, nl


print("\n" + "=" * 100)
print("CORRECTED NULLS")
print("=" * 100)
boot_ratio(lambda p: p[1][0], lambda p: p[0][0],
           "V75/V74 -- 30 ms rolling windows above 1/3 plateau duty  [PROXY]")
boot_ratio(lambda p: p[1][1], lambda p: p[0][1],
           "V75/V74 -- PLATEAU TRANSITIONS (entries + exits)")

t4 = sum(p[0][1] for p in per)
t2 = sum(p[1][1] for p in per)
s = sum(p[0][2] for p in per)
print(f"\n  absolute transition rates, engaged: V74 {t4/s:.4f}/s ({t4} in {s:.1f} s)   "
      f"V75 {t2/s:.4f}/s ({t2} in {s:.1f} s)")
print(f"  n episodes with V74 transitions > 0: {sum(1 for p in per if p[0][1])} of {len(per)}")
print(f"  n episodes with V75 transitions > 0: {sum(1 for p in per if p[1][1])} of {len(per)}")
