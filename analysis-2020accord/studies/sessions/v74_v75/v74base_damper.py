#!/usr/bin/env python3
"""V74 route 5d -- bit7 (gp-0x6BD0 != 0) duty vs engagement and speed, and the 35 km/h FactorC knee.

The prediction under test: V74's FactorC/FactorE edits write the ENGAGED column only (mode 26), so in
MANUAL (mode 24) the damper is byte-stock, and stock mode-24 FactorC has
    X = [2240, 3840, 5120, 8960] counts = [35, 60, 80, 140] km/h
    Y = [   0,  234,  429,  908]
=> below 35 km/h the manual-arm damper term is structurally ZERO, so bit7 must be clear.

Engagement arms are built TWO ways:
  (a) raw `carControl.latActive`, and
  (b) `_r5d_lib.lever_mask` -- latActive lagged by V73's measured mode-selector lags (1.0209 s rise /
      2.0798 s fall), with the hysteresis band dropped rather than assigned to an arm.
"""
import sys

import numpy as np

sys.path.insert(0, "analysis-2020accord")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE, PFX, SEGS = "_scratch/cache/r5d", "r5ds", list(range(17))
KNEE_MS = 35.0 / 3.6          # 9.7222 m/s -- FactorC stock X[0]
MODE_LAG_RISE_S, MODE_LAG_FALL_S = 1.0209, 2.0798

VB = [0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 9.7222, 11.0, 13.0, 16.0, 20.0, 25.0, 99.0]


def lever_mask(lat, t):
    lat = np.asarray(lat, bool)
    t = np.asarray(t, float)
    on = np.interp(t - MODE_LAG_RISE_S, t, lat.astype(float)) > 0.5
    off = np.interp(t - MODE_LAG_FALL_S, t, lat.astype(float)) > 0.5
    in_force = on & off & lat
    byte_stock = (~on) & (~off) & (~lat)
    return in_force, byte_stock, ~(in_force | byte_stock)


def main():
    T, V, D, LAT, SCA, INF, BST, AMB, SEG = [], [], [], [], [], [], [], [], []
    for s in SEGS:
        d = dict(np.load(f"{CACHE}/{PFX}{s}.npz"))
        t = d["t"]
        lat = d["cc_lat"] > 0.5
        inf, bst, amb = lever_mask(lat, t)
        T.append(t); V.append(d["cs_v"]); D.append(d["damp_nz"] > 0.5)
        LAT.append(lat); SCA.append(d["sca"] == 1)
        INF.append(inf); BST.append(bst); AMB.append(amb)
        SEG.append(np.full(len(t), s))
    t, v, dmp = map(np.concatenate, (T, V, D))
    lat, sca, inf, bst, amb, seg = map(np.concatenate, (LAT, SCA, INF, BST, AMB, SEG))

    print("=" * 92)
    print(f"V74 / route 5d -- damper bit7 duty.  n={len(t)} frames")
    print(f"latActive vs STEER_CONTROL_ACTIVE agree on {100.0*(lat==sca).mean():.4f}% of frames "
          f"({int((lat!=sca).sum())} disagreements)")
    print("=" * 92)

    print("\n--- bit7 duty, whole route and by arm ---------------------------------------------")
    for nm, m in (("ALL", np.ones_like(lat)), ("ENGAGED (latActive)", lat),
                  ("MANUAL (~latActive)", ~lat),
                  ("ENGAGED, lag-corrected (mode 26 in force)", inf),
                  ("MANUAL,  lag-corrected (mode 24 byte-stock)", bst),
                  ("AMBIGUOUS hysteresis band (dropped)", amb)):
        m = m.astype(bool)
        print(f"  {nm:<44} n={m.sum():>7}  {m.sum()/100.0:>7.1f}s  bit7 duty "
              f"{100.0*dmp[m].mean() if m.any() else float('nan'):>7.3f}%")

    print("\n--- 5. bit7 duty vs SPEED, split by arm (lag-corrected) ---------------------------")
    print(f"  {'speed bin (m/s)':>18} {'km/h':>13} | {'MANUAL n':>9} {'duty':>9} | "
          f"{'ENGAGED n':>10} {'duty':>9}")
    for lo, hi in zip(VB[:-1], VB[1:]):
        b = (v >= lo) & (v < hi)
        mm, me = b & bst, b & inf
        f = lambda m: f"{100.0*dmp[m].mean():>8.3f}%" if m.sum() else "       --"
        star = "  <<< 35 km/h KNEE" if abs(lo - KNEE_MS) < 1e-3 else ""
        print(f"  {lo:>8.2f}-{hi:<8.2f} {lo*3.6:>5.1f}-{hi*3.6:<6.1f} | {mm.sum():>9} {f(mm)} | "
              f"{me.sum():>10} {f(me)}{star}")

    print("\n--- THE KNEE TEST: manual arm, below vs above 35 km/h ------------------------------")
    for arm, nm in ((bst, "MANUAL lag-corrected (mode 24)"), (~lat, "MANUAL raw ~latActive")):
        lo_ = arm & (v < KNEE_MS)
        hi_ = arm & (v >= KNEE_MS)
        print(f"  {nm}")
        print(f"    v <  9.722 m/s : n={lo_.sum():>7}  bit7 fires {int(dmp[lo_].sum()):>7} "
              f"({100.0*dmp[lo_].mean() if lo_.any() else float('nan'):.4f}%)")
        print(f"    v >= 9.722 m/s : n={hi_.sum():>7}  bit7 fires {int(dmp[hi_].sum()):>7} "
              f"({100.0*dmp[hi_].mean() if hi_.any() else float('nan'):.4f}%)")

    print("\n  ENGAGED arm, same split (V74 EDITS this column -- expect NO knee):")
    for nm, arm in (("lag-corrected", inf), ("raw latActive", lat)):
        lo_, hi_ = arm & (v < KNEE_MS), arm & (v >= KNEE_MS)
        print(f"    {nm:<14} <35: n={lo_.sum():>6} {100.0*dmp[lo_].mean():.3f}%   "
              f">=35: n={hi_.sum():>6} {100.0*dmp[hi_].mean():.3f}%")

    # sub-knee manual firings, if any -- where exactly?
    bad = bst & (v < KNEE_MS) & dmp
    print(f"\n  sub-35 km/h MANUAL bit7 firings: {int(bad.sum())} frames")
    if bad.any():
        idx = np.flatnonzero(bad)
        # group into runs
        runs, cur = [], [idx[0]]
        for a, b in zip(idx[:-1], idx[1:]):
            if b - a <= 3 and seg[b] == seg[a]:
                cur.append(b)
            else:
                runs.append(cur); cur = [b]
        runs.append(cur)
        print(f"  grouped into {len(runs)} runs; the 15 longest:")
        for r in sorted(runs, key=len, reverse=True)[:15]:
            print(f"    seg{int(seg[r[0]])} t={t[r[0]]:.3f}..{t[r[-1]]:.3f} "
                  f"({len(r)} frames, {len(r)/100.0:.2f}s) v={v[r].min():.2f}..{v[r].max():.2f} m/s")
        print(f"  speed distribution of those frames: "
              f"min={v[bad].min():.2f} p50={np.median(v[bad]):.2f} max={v[bad].max():.2f} m/s")


if __name__ == "__main__":
    main()
