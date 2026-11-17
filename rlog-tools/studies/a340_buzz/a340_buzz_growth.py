"""Per-cycle amplitude trajectory from onset (6-sample cycles), normalised by the episode's p90|hr|. usage: <cache dir>"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs
C = sys.argv[1]; T = []
for seg, p in segs(C):
    d = load(p); on = d["bz"] > 4; hr = d["hr"]
    idx = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    for s, e in zip(idx[0::2], idx[1::2]):
        if e - s < 80 or s < 80 or d["v"][s:e].mean() < 2: continue
        amp = np.percentile(np.abs(hr[s:e]), 90)
        k0 = s - 16
        while k0 > s - 60 and np.abs(hr[k0 - 3:k0]).max() > 3: k0 -= 1
        T.append([np.abs(hr[k0 - 12 + 6 * c:k0 - 6 + 6 * c]).max() / amp for c in range(12)])
T = np.array(T)
print("n episodes", len(T)); print("cycle (6 samples, -2..9 rel. onset):", list(range(-2, 10)))
for q in (25, 50, 75): print(" p%d" % q, np.round(np.percentile(T, q, axis=0), 2))
r = np.median(T[:, 3:7], 0); print(" median cycle-to-cycle ratio over cycles 1-4:", np.round(r[1:] / r[:-1], 2))
