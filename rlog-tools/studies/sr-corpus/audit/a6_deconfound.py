# -*- coding: utf-8 -*-
"""A6 -- THE decisive test: is there an ANGLE trend at FIXED SPEED, in steady-state windows?"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
rows = []
for t in TAGS:
    g = A.grid(A.load(t))
    ok = (np.abs(g["rate"]) < 25) & (g["v"] > 3.0) & np.isfinite(g["denom"]) & g["calok"] & (np.abs(g["sa_deg"]) > 2)
    W = int(0.6 * A.FS); i = 0
    while i < len(ok) - W:
        if not ok[i]:
            i += 1; continue
        j = i
        while j < len(ok) and ok[j]:
            j += 1
        k = i
        while k + W <= j:
            sl = slice(k, k + W)
            sa = g["sa_deg"][sl]; v = g["v"][sl]
            if np.ptp(sa) < 0.5 * abs(np.mean(sa)) and np.ptp(v) < 0.5 * abs(np.mean(v)) and abs(np.mean(sa)) > 2:
                r = float(np.mean(g["cfac"][sl] * g["sa"][sl]) / np.mean(g["denom"][sl]))
                rk = float(np.mean(g["cfac_kin"][sl] * g["sa"][sl]) / np.mean(g["denom"][sl]))
                rows.append((t, abs(float(np.mean(sa))), float(np.mean(v)), r, rk, float(np.mean(g["eng"][sl]))))
                k += W
            else:
                k += 10
        i = j
R = np.array([[x[1], x[2], x[3], x[4], x[5]] for x in rows])
good = np.isfinite(R[:, 2]) & (R[:, 2] > 5) & (R[:, 2] < 40)
R = R[good]
print("=" * 112)
print("A6  STEADY-STATE sR  vs  |angle|  AT FIXED SPEED.  0.6 s flat windows, all 5 routes pooled,")
print("    engaged or manual.  cell = median sR / n windows.  The angle effect is REAL only if the")
print("    COLUMNS fall down the page.  If only the ROWS move, it is the understeer term, not the rack.")
print("=" * 112)
VB = [(4, 7), (7, 10), (10, 14), (14, 19), (19, 40)]
AB = [(2, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 400)]
print("   %-9s %s" % ("|sa| deg", "".join("%16s" % ("v %d-%d" % v) for v in VB)))
for lo, hi in AB:
    cells = []
    for vlo, vhi in VB:
        m = (R[:, 0] >= lo) & (R[:, 0] < hi) & (R[:, 1] >= vlo) & (R[:, 1] < vhi)
        cells.append("%16s" % ("%.2f / %d" % (np.median(R[m, 2]), m.sum()) if m.sum() >= 4 else "--"))
    print("   %-9s %s" % ("%d-%d" % (lo, hi), "".join(cells)))
print()
print("   Same, KINEMATIC curvature factor (1/L, understeer term removed entirely):")
print("   %-9s %s" % ("|sa| deg", "".join("%16s" % ("v %d-%d" % v) for v in VB)))
for lo, hi in AB:
    cells = []
    for vlo, vhi in VB:
        m = (R[:, 0] >= lo) & (R[:, 0] < hi) & (R[:, 1] >= vlo) & (R[:, 1] < vhi)
        cells.append("%16s" % ("%.2f / %d" % (np.median(R[m, 3]), m.sum()) if m.sum() >= 4 else "--"))
    print("   %-9s %s" % ("%d-%d" % (lo, hi), "".join(cells)))
print()
print("   MARGINALS (bicycle model): angle effect at fixed speed vs speed effect at fixed angle")
for vlo, vhi in VB:
    m = (R[:, 1] >= vlo) & (R[:, 1] < vhi)
    if m.sum() < 15:
        continue
    lo_a = m & (R[:, 0] < 10); hi_a = m & (R[:, 0] >= 20)
    if lo_a.sum() >= 4 and hi_a.sum() >= 4:
        print("     v %2d-%2d : |sa|<10 -> %.2f (n=%3d) ; |sa|>=20 -> %.2f (n=%3d) ;  ANGLE effect %+.2f" % (
            vlo, vhi, np.median(R[lo_a, 2]), lo_a.sum(), np.median(R[hi_a, 2]), hi_a.sum(),
            np.median(R[hi_a, 2]) - np.median(R[lo_a, 2])))
for lo, hi in ((2, 10), (20, 400)):
    m = (R[:, 0] >= lo) & (R[:, 0] < hi)
    lo_v = m & (R[:, 1] < 10); hi_v = m & (R[:, 1] >= 14)
    if lo_v.sum() >= 4 and hi_v.sum() >= 4:
        print("     |sa| %3d-%3d : v<10 -> %.2f (n=%3d) ; v>=14 -> %.2f (n=%3d) ;  SPEED effect %+.2f" % (
            lo, hi, np.median(R[lo_v, 2]), lo_v.sum(), np.median(R[hi_v, 2]), hi_v.sum(),
            np.median(R[hi_v, 2]) - np.median(R[lo_v, 2])))
