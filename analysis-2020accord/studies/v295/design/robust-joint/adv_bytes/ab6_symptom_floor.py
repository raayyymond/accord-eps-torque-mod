# -*- coding: utf-8 -*-
"""ab6_symptom_floor.py -- SECOND METHOD for the symptom band's one-drive noise floor (ab4 used per-event spread).
Block bootstrap on r71b (V294, nothing changed): pool the 100 Hz frames of medium-speed hard turns (engaged, v 5-15
and 5-22 m/s, |desired lat accel| >= 1.0 m/s^2), band-pass the 0x18F wheel rate 1.6-3 Hz (zero-phase, on the whole
route first so edges do not bias), cut into 1 s blocks, draw 15 s / 30 s of blocks WITH replacement, and read the
1.6-3 Hz rms relative to the full pool.  The 5-95 % band is the no-change scatter a single short drive would show.
Compare with the design's predicted direction for A (x0.68..x0.93 over the family, nominal x0.83).
ANALYSIS ONLY."""
import numpy as np
from scipy import signal

KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
d = np.load(KIT + "/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz")
om = np.nan_to_num(d["om"])
sos = signal.butter(4, [1.6, 3.0], btype="band", fs=100.0, output="sos")
ob = signal.sosfiltfilt(sos, om)
v, lad, eng = d["v"], np.abs(d["ctl_la_des"]), d["eng"]
rng = np.random.default_rng(11)
for lo, hi in ((5, 15), (5, 22), (15, 22)):
    m = eng & (v >= lo) & (v < hi) & (lad >= 1.0)
    idx = np.flatnonzero(m)
    blocks = [idx[i:i + 100] for i in range(0, len(idx) - 99, 100)]
    ms = np.array([np.mean(ob[b] ** 2) for b in blocks])
    full = np.sqrt(ms.mean())
    line = "v %2d-%2d m/s: %5.1f s of hard frames (%d blocks), pooled 1.6-3 Hz rate rms %.2f deg/s" % (lo, hi, len(idx) / 100.0, len(blocks), full)
    for sec in (15, 30):
        if len(blocks) < 5:
            break
        draws = np.sqrt(np.array([ms[rng.integers(0, len(ms), sec)].mean() for _ in range(20000)])) / full
        pair = np.sqrt(np.array([ms[rng.integers(0, len(ms), sec)].mean() / ms[rng.integers(0, len(ms), sec)].mean()
                                  for _ in range(20000)]))
        line += " | %d s: vs pool x[%.2f, %.2f], drive-vs-drive x[%.2f, %.2f] (5-95 %%)" % (
            sec, *np.percentile(draws, [5, 95]), *np.percentile(pair, [5, 95]))
    print(line)
print("design's predicted direction for A, hard turn 5-10 m/s: x0.68..x0.93 (nominal x0.83); 15-22: x0.67..x1.03")
