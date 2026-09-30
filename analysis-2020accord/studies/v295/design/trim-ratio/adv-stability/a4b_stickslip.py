# -*- coding: utf-8 -*-
"""a4b_stickslip.py -- (d) is the low-speed dwell-then-jump / stick-slip count on light_b / J_hi2 (a4 HOLD at 3.1 m/s:
2 -> 9 and 2 -> 4) robust, or seed noise?  8 seeds x {nominal, light_b, lb_mode20_lo, J_hi2, F_hi, F_lo} x {3.1, 5.0}
m/s, V294 vs b964 on identical seeds (x noise, road torque, planner wander all seeded).  Same code as a4 (a4_core).
Also the 'phantom momentum' check: the trim torque at the instant the wheel sticks, V294 vs b964, vs the static
friction Fs.  Output: a4b_out.txt"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a4_core as N  # noqa: E402

out = open(os.path.join(HERE, "a4b_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


names = ["nominal", "light_b", "lb_mode20_lo", "J_hi2", "F_hi", "F_lo"]
SEEDS = range(8)
for v in (3.1, 5.0):
    secs = 60.0
    tot = {nm: np.zeros((2, 4)) for nm in names}
    per = {nm: [[], []] for nm in names}
    for sd in SEEDS:
        cl = [N.V294] * len(names) + [N.B964] * len(names)
        mm = [N.MEM[k] for k in names] * 2
        B = len(cl)
        rng = np.random.default_rng(100 + sd)
        bb, aa = signal.butter(2, [0.05 / 50, 0.5 / 50], btype="band")
        wander = signal.lfilter(bb, aa, rng.normal(size=int(secs * 100)))
        wander = wander / wander.std() * 0.05
        sp_ = np.repeat(wander[None], B, 0)
        jk = np.gradient(sp_, axis=1) * 100
        r = N.run(cl, mm, v, sp_, jk, N.road(B, int(secs * 1000), 15.0, 200 + sd), secs, seed=300 + sd)
        nn = len(names)
        for j, nm in enumerate(names):
            for c, off in enumerate((0, nn)):
                om = r["om"][j + off:j + off + 1, 500:]
                dj = N.dwell_jumps(om)
                # stick instants on the 1 kHz trace: om goes nonzero -> exactly 0; trim torque = T - T_null is not
                # available here, so read |T| change over the 50 ms after sticking vs Fs as the phantom-momentum proxy
                om1 = r["om1k"][j + off]
                T1 = r["T1k"][j + off].astype(float)
                st = np.flatnonzero((om1[:-1] != 0) & (om1[1:] == 0)) + 1
                st = st[(st > 5000) & (st < len(om1) - 200)]
                rel = [np.max(np.abs(np.diff(T1[s:s + 60]))) * 0 + (np.max(T1[s:s + 60]) - np.min(T1[s:s + 60])) for s in st[:400]]
                per[nm][c].append(dj[0])
                tot[nm][c] += np.array([dj[0], dj[1], len(st), np.median(rel) if rel else 0.0])
    P("v %.1f m/s, %d seeds x 60 s: dwell-then-jump counts per seed V294 | b964 ; mean jump peak ; stick events ; median |dT| in 60 ms after stick" % (v, len(SEEDS)))
    for nm in names:
        a, b = per[nm]
        ta, tb = tot[nm] / len(SEEDS)
        diff = np.array(b) - np.array(a)
        P("  %-12s V294 %s | b964 %s  mean %.1f -> %.1f (paired diff mean %+.2f, sd %.2f, n+ %d / n- %d)  jump pk %.1f -> %.1f  "
          "sticks %.0f -> %.0f  dT60 %.1f -> %.1f" % (nm, a, b, np.mean(a), np.mean(b), diff.mean(), diff.std(ddof=1),
                                                      int((diff > 0).sum()), int((diff < 0).sum()), ta[1], tb[1], ta[2], tb[2], ta[3], tb[3]))
out.close()
