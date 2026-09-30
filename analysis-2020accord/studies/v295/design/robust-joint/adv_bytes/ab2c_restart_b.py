# -*- coding: utf-8 -*-
"""ab2c_restart_b.py -- largest b meeting H-SAFE-3 under each reading, 100 deg/s, over idx x sign x rate sign. ANALYSIS ONLY."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab2_lane as AL
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ab2b_restart_grid.py")).read().split("worst = {}")[0].split("c294, cA =")[0])
def restart(c, X, idx, sgn, pre=2500, post=1200):
    L = AL.Lane(c)
    for _ in range(pre):
        T_ff = L.tick(X, sgn * c["SP"][idx])[0]
    L.tick(X, sgn * c["SP"][idx], bail=True)
    tr = np.array([L.tick(X, sgn * c["SP"][idx])[0] - T_ff for _ in range(post)])
    return int(np.max(np.abs(tr)))
grid = [(X, i, s) for X in (800, -800) for i in (0, 60, 120, 180, 238) for s in (1, -1)]
base = {g: restart(AL.cells(), *g) for g in grid}
for b in (1000, 1040, 1050, 1060, 1080, 1106):
    c = AL.cells(b_override=b)
    v = {g: restart(c, *g) for g in grid}
    print("b %4d: worst %3d T (abs cap 288 %s) ; worst per-point ratio %.3f (cap 2.0 %s) ; worst/worst %.3f"
          % (b, max(v.values()), "PASS" if max(v.values()) <= 288 else "FAIL", max(v[g] / base[g] for g in grid),
             "PASS" if max(v[g] / base[g] for g in grid) <= 2.0 else "FAIL", max(v.values()) / max(base.values())))
