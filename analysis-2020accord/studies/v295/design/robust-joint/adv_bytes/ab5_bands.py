# -*- coding: utf-8 -*-
"""ab5_bands.py -- does the design's LITERAL pre-registered sentence read correctly on the correct image?
  sentence: "c2 within [0.9, 1.1] -> b not live" ; "c1 0.97-1.00 and c2 1.8-2.0 -> trim live and doubled as designed"
  For each window family (as ab4), the fraction of windows where the literal bands give: the RIGHT call, the WRONG
  call, or NO call (a gap), on the real V294 tap and on the synthetic A tap (+stress).  Also: the FF-only identity R^2
  (the flight-attribution style gate, no trim term) on the correct A image vs V294.
ANALYSIS ONLY."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
src = open(os.path.join(HERE, "ab4_observe.py")).read().split("# W1: hands-off frames, consecutive chunks")[0]
exec(src)


def literal(C, truth):
    c1, c2 = C[:, 1], C[:, 2]
    notlive = (c2 >= 0.9) & (c2 <= 1.1)
    doubled = (c1 >= 0.97) & (c1 <= 1.00) & (c2 >= 1.8) & (c2 <= 2.0)
    if truth == "V294":
        right, wrong = notlive, doubled
    else:
        right, wrong = doubled, notlive
    gap = ~(right | wrong)
    return right.mean(), wrong.mean(), gap.mean()


def fam(name, wins, min_frames=100):
    wins = [w for w in wins if len(w) >= min_frames]
    res = {}
    for k in ("V294 real", "A synth", "A stress(zoh)"):
        C = np.array([ols(Y[k][w], (FF[w], TR[w])) for w in wins])
        res[k] = literal(C, "V294" if k.startswith("V294") else "A")
    print("%-58s n=%3d | V294: right %.2f wrong %.2f gap %.2f | A: right %.2f wrong %.2f gap %.2f | A-stress gap %.2f"
          % (name, len(wins), *res["V294 real"], *res["A synth"], res["A stress(zoh)"][2]))


iho = np.flatnonzero(ho)
for sec in (5, 10, 15, 20, 30):
    n = sec * 50
    fam("W1 hands-off %2d s" % sec, [iho[i:i + n] for i in range(0, len(iho) - n + 1, n)])
t_tap = d["t_tap"]
for sec in (15, 30):
    edges = np.arange(t_tap[0], t_tap[-1], sec)
    wins = [np.flatnonzero((t_tap >= a) & (t_tap < a + sec) & eng) for a in edges]
    fam("W2 contiguous %d s, all engaged (>=80%%)" % sec, [w for w in wins if len(w) >= 0.8 * sec * 50])
# FF-only identity R^2 on all engaged frames and hands-off frames
for nm, m in (("all engaged", eng), ("hands-off engaged", ho)):
    for k in ("V294 real", "A synth"):
        y = Y[k][m]
        X1 = np.column_stack([np.ones(m.sum()), FF[m]])
        co, *_ = np.linalg.lstsq(X1, y, rcond=None)
        r = y - X1 @ co
        print("FF-only identity (no trim term), %-18s %-10s: slope %.4f  R^2 %.4f  resid rms %.2f"
              % (nm, k, co[1], 1 - np.var(r) / np.var(y), np.sqrt(np.mean(r ** 2))))
