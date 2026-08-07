#!/usr/bin/env python3
"""Is the manual-arm damper firing the MODE FALL-LAG shadow, or a genuine stock mode-24 damper?

H1  the mode-selector fall lag exceeds V73's 2.0798 s, so those frames are still mode 26 (V74's
    EDITED engaged column) and the stock-table prediction is untouched.
H2  the mode really is 24 there and stock mode-24 FactorC is NOT structurally zero below 35 km/h.

The discriminating question the cache can answer: outside the shadow of a disengagement edge, does
manual driving ever fire bit7 -- and in particular, does manual driving at COMPARABLE steering rate,
far from an edge, fire it?  H2 predicts yes; H1 predicts no.
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CACHE, PFX, SEGS = "_cache_r5d", "r5ds", list(range(17))
KNEE = 35.0 / 3.6

T, V, D, LAT, RC, SEG, TSF = [], [], [], [], [], [], []
for s in SEGS:
    d = dict(np.load(f"{CACHE}/{PFX}{s}.npz"))
    t, lat = d["t"], d["cc_lat"] > 0.5
    # seconds since the most recent latActive FALL (inf if never engaged in this segment)
    tsf = np.full(len(t), np.inf)
    falls = [i + 1 for i in np.flatnonzero(np.diff(lat.astype(int)) == -1)]
    for f in falls:
        m = np.arange(len(t)) >= f
        tsf[m] = np.minimum(tsf[m], t[m] - t[f])
    T.append(t); V.append(d["cs_v"]); D.append(d["damp_nz"] > 0.5); LAT.append(lat)
    RC.append(np.abs(d["rate_c"])); SEG.append(np.full(len(t), s)); TSF.append(tsf)
t, v, dmp, lat, rc, seg, tsf = map(np.concatenate, (T, V, D, LAT, RC, SEG, TSF))

man = ~lat
print("=" * 88)
print("MANUAL-ARM bit7, as a function of TIME SINCE DISENGAGEMENT")
print("=" * 88)
print(f"  {'window since FALL':>22} {'n':>8} {'bit7 n':>8} {'duty':>9}")
for lo, hi in ((0, 1), (1, 2), (2, 2.08), (2.08, 3), (3, 4), (4, 6), (6, 10), (10, 30),
               (30, 1e9), (1e9, np.inf)):
    m = man & (tsf >= lo) & (tsf < hi)
    lbl = "never engaged" if lo >= 1e9 else f"{lo:g}-{hi:g} s"
    if m.any():
        print(f"  {lbl:>22} {m.sum():>8} {int(dmp[m].sum()):>8} {100.0*dmp[m].mean():>8.4f}%")
    else:
        print(f"  {lbl:>22} {m.sum():>8} {'-':>8} {'--':>9}")

far = man & (tsf > 6.0)
print(f"\n  MANUAL, >6 s clear of any disengagement edge: n={far.sum()} "
      f"({far.sum()/100.0:.1f} s), bit7 fires {int(dmp[far].sum())} "
      f"({100.0*dmp[far].mean():.5f}%)")
print(f"  ... of which below 35 km/h: n={(far & (v < KNEE)).sum()}, "
      f"bit7 {int(dmp[far & (v < KNEE)].sum())}")
print(f"  ... of which at or above  : n={(far & (v >= KNEE)).sum()}, "
      f"bit7 {int(dmp[far & (v >= KNEE)].sum())}")

print("\n--- the confound check: is there comparable STEERING RATE far from an edge? -----------")
burst = man & (tsf >= 2.08) & (tsf < 6) & dmp
print(f"  the burst (manual, 2.08-6 s after FALL, bit7 set): n={burst.sum()}  "
      f"|rate_c| p50={np.median(rc[burst]):.1f} p90={np.percentile(rc[burst],90):.1f} "
      f"max={rc[burst].max():.1f}  v={v[burst].min():.2f}..{v[burst].max():.2f} m/s")
thr = np.percentile(rc[burst], 10) if burst.any() else np.nan
cmp_ = far & (v < KNEE) & (rc >= thr)
print(f"  MANUAL far-from-edge, sub-35 km/h, |rate_c| >= {thr:.0f} (the burst's p10): "
      f"n={cmp_.sum()} ({cmp_.sum()/100.0:.1f} s), bit7 fires {int(dmp[cmp_].sum())}")
for q in (50, 90, 99, 99.9, 100):
    print(f"    |rate_c| p{q} over MANUAL far-from-edge sub-35: "
          f"{np.percentile(rc[far & (v < KNEE)], q):.1f}")
print(f"  ==> H2 requires bit7 to fire in that population. It fires "
      f"{int(dmp[cmp_].sum())} times.")

print("\n--- ENGAGED-arm rate dependence, for contrast (V74's EDITED column) ------------------")
for lo, hi in ((0, 10), (10, 25), (25, 50), (50, 100), (100, 1e9)):
    m = lat & (rc >= lo) & (rc < hi) & (v < KNEE)
    if m.any():
        print(f"  |rate_c| {lo:>4}-{hi:<6g} sub-35 ENGAGED: n={m.sum():>7} "
              f"duty {100.0*dmp[m].mean():>7.3f}%")
