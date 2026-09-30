# -*- coding: utf-8 -*-
"""ADV-A a8: (1) restart-pulse DURATION (ms with |T - T_pre| above 50/150/300 T) at zero command and at the worst
lane, 100/300/1500 deg/s, 1-tick bail, V294 vs V295; (2) where the route's |trim| > 300 T dwell sits (speed band,
hands-on/off) -- from a7's saved traces."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a4_restart as R  # noqa: E402

J = R.J
for rate in (100.0, 300.0, 1500.0):
    for nm in ("v294", "v295"):
        r = R.run(J[nm], rate, "boot", bail_len=1, want_trace=True)
        dev = np.abs(r["trace"] - r["T_pre"][None, :])
        zc = [k for k, l in enumerate(R.lanes) if l[0] == 0]
        jw = int(np.argmax(dev.max(axis=0)))
        z = max(zc, key=lambda k: dev[:, k].max())
        print("rate %6.1f %s: zero-cmd peak %d, ms > 50/150/300: %d/%d/%d | worst lane idx %d peak %d, ms > 50/150/300: %d/%d/%d"
              % (rate, nm, dev[:, z].max(), np.sum(dev[:, z] > 50), np.sum(dev[:, z] > 150), np.sum(dev[:, z] > 300),
                 R.lanes[jw][0], dev[:, jw].max(), np.sum(dev[:, jw] > 50), np.sum(dev[:, jw] > 150), np.sum(dev[:, jw] > 300)))

d = dict(np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz"))
tr = dict(np.load(os.path.join(HERE, "_a7_traces.npz")))
n = len(tr["T4"])
eng = np.repeat(d["eng"], 10)[:n]; v1k = np.repeat(d["v"], 10)[:n]; bar1k = np.repeat(d["bar"], 10)[:n]
press = np.repeat(d["cs_pressed"] > 0.5, 10)[:n]
hon = eng & (press | (np.abs(bar1k) >= 400))
for nm, T in (("V294", tr["T4"]), ("V295", tr["T5"])):
    trim = T.astype(int) - tr["TF"].astype(int)
    big = eng & (np.abs(trim) > 300)
    print("%s |trim| > 300: total %.3f s ; hands-on %.3f s ; by band: %s ; episodes (>= 1 ms runs): %d"
          % (nm, big.sum() / 1000, (big & hon).sum() / 1000,
             ", ".join("%s %.3f" % (b, (big & (v1k >= lo) & (v1k < hi)).sum() / 1000)
                       for b, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10), ("10-15", 10, 15), ("15+", 15, 99))),
             int(np.sum(np.diff(np.r_[0, big.astype(int)]) == 1))))
