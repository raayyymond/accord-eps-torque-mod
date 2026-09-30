# -*- coding: utf-8 -*-
"""ab2b_restart_grid.py -- the restart pulse (one bail tick, then s restarts from 0) at 100 deg/s over demand index x
sign x rate sign, V294 vs A, on MY lane; the pre-registered H-SAFE-3 cap is 2 x V294's 144 T = 288 T.  ANALYSIS ONLY."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab2_lane as AL
c294, cA = AL.cells(), AL.cells(b_override=1106)

def restart(c, X, idx, sgn, pre=3000, post=1500):
    L = AL.Lane(c)
    for _ in range(pre):
        T_ff = L.tick(X, sgn * c["SP"][idx])[0]
    L.tick(X, sgn * c["SP"][idx], bail=True)
    tr = np.array([L.tick(X, sgn * c["SP"][idx])[0] - T_ff for _ in range(post)])
    k = int(np.argmax(np.abs(tr)))
    return abs(int(tr[k])), int(np.sum(np.abs(tr) > 50))

worst = {}
for X in (800, -800):
    for idx in (0, 30, 60, 120, 180, 238, 240):
        for sgn in (1, -1):
            a, b = restart(c294, X, idx, sgn), restart(cA, X, idx, sgn)
            print("x %+5d idx %3d sgn %+d: V294 %4d T (%3d ms>50)  A %4d T (%3d ms>50)  ratio %.2f" % (X, idx, sgn, a[0], a[1], b[0], b[1], b[0] / max(a[0], 1)))
            worst.setdefault("V294", []).append(a[0]); worst.setdefault("A", []).append(b[0])
print("max over grid: V294 %d  A %d ; A cells above the absolute 288 cap: %d of %d" % (max(worst["V294"]), max(worst["A"]), sum(v > 288 for v in worst["A"]), len(worst["A"])))
