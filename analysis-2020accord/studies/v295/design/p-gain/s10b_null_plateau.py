# -*- coding: utf-8 -*-
"""s10b_null_plateau.py -- the NULL distribution of s10's plateau read: r71b's REAL tap (V294 on the car), regressed on
V294's own march in each 20 s window on idx 0-8 frames, divided by the whole-drive baseline.  A live candidate must
read outside this band.  ANALYSIS ONLY."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa
import plib as P
from s6_attribution import regress, windows
d = P.load()
tk, j = d["tick_tap"], d["j100"]
y = d["T_tap"].astype(float)
ok = d["ho"][j] & (np.abs(y) < 2300)
F = d["T1k_null"][tk]; R = d["T1k_live"][tk] - F
idx_t = d["idx"][j]
base = regress(y, F, R, ok & (idx_t < 9))[0][0]
pr = []
for m in windows(None, j, ok):
    mm = m & (idx_t < 9)
    if mm.sum() >= 150:
        pr.append(regress(y, F, R, mm)[0][0] / base)
pr = np.array(pr)
print("NULL plateau ratio (real V294 tap), per 20 s window: median %.3f [p2.5 %.3f, p97.5 %.3f] min %.3f max %.3f n %d (baseline %.3f)"
      % (np.median(pr), np.percentile(pr, 2.5), np.percentile(pr, 97.5), pr.min(), pr.max(), len(pr), base))
