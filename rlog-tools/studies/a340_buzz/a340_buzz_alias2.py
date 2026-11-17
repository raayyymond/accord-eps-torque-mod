"""Alias test 2: in buzz windows, correlate the >10 Hz part of d(angle)/dt (0.1 deg LSB -> 10 deg/s LSB) with the >10 Hz part of the
interval-mean rate (rate[k]+rate[k-1])/2. A true sub-Nyquist oscillation gives corr -> +1 when its amplitude is well above 10 deg/s;
a fold of a >50 Hz line gives corr <= 0. Split by amplitude. usage: <cache dir>"""
import sys, os
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs
b, a = signal.butter(4, 10 / 50, "high")
rows = []
for seg, p in segs(sys.argv[1]):
    d = load(p)
    da = np.r_[0, np.diff(d["ang"])] / 0.01
    rm = np.r_[d["rate"][0], (d["rate"][1:] + d["rate"][:-1]) / 2]
    x, y = signal.filtfilt(b, a, da), signal.filtfilt(b, a, rm)
    W = 64
    for i in range(0, len(da) - W, W):
        s = slice(i, i + W)
        if d["v"][s].mean() < 2: continue
        rows.append((d["bz"][s].mean(), np.corrcoef(x[s], y[s])[0, 1], x[s].std() / max(y[s].std(), 1e-6), np.abs(d["ang"][s]).mean(), np.abs(d["rlp"][s]).mean()))
R = np.array(rows)
for lab, m in (("BZ 5-10", (R[:, 0] > 5) & (R[:, 0] < 10)), ("BZ 10-15", (R[:, 0] >= 10) & (R[:, 0] < 15)), ("BZ >=15", R[:, 0] >= 15),
               ("BZ>=10 & |ang|<5", (R[:, 0] >= 10) & (R[:, 3] < 5)), ("BZ>=10 & |ang|>20", (R[:, 0] >= 10) & (R[:, 3] > 20)), ("quiet BZ<2", R[:, 0] < 2)):
    if m.sum() > 2:
        print("  %-20s n=%4d  corr(dang/dt, rate) p25/p50/p75 %s   rms ratio p50 %.2f" % (lab, m.sum(), np.round(np.nanpercentile(R[m, 1], [25, 50, 75]), 2), np.nanmedian(R[m, 2])))
