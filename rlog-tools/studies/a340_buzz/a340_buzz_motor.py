"""Motor/torque side during buzz: 0x18F torque line coherence with the rate line, and an empirical look at 0x1AB. usage: <cache dir>"""
import sys, os
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs
C = sys.argv[1]
rows = []; M = []
for seg, p in segs(C):
    d = load(p)
    W = 128
    for i in range(0, len(d["t"]) - W, W):
        s = slice(i, i + W)
        if d["v"][s].mean() < 2: continue
        f, Cxy = signal.coherence(d["hr"][s], d["ht"][s], fs=100, nperseg=32)
        _, Pxx = signal.welch(d["hr"][s], fs=100, nperseg=32)
        _, Pxy = signal.csd(d["hr"][s], d["ht"][s], fs=100, nperseg=32)
        k = np.argmax(Pxx * (f > 10))
        rows.append((d["bz"][s].mean(), Cxy[k], np.abs(Pxy[k]) / Pxx[k], np.degrees(np.angle(Pxy[k])), d["ht"][s].std(), f[k], d["req"][s].mean()))
    # 0x1AB on its own 50 Hz clock
    t1 = d["t1ab"]; m = d["m1ab"]; d1 = d["d1ab"]
    def at(x): return np.interp(t1, d["t"], x)
    M.append(np.c_[m, (d1[:, 0] >> 7) & 1, (d1[:, 0] >> 2) & 0x1F, at(np.abs(d["tq"])), at(np.abs(d["cmd"]) if d["has_e4"] else np.zeros_like(d["t"])),
                   at(d["req"].astype(float)), at(d["bz"]), at(np.abs(d["rlp"])), at(d["v"]), d1[:, 2] >> 6 & 1, at(d["tq"]), at(d["ang"])])
R = np.array(rows)
print("== 0x18F torque vs wheel rate at the buzz line (128-sample windows, coherence nperseg 32)")
for lab, m in (("BUZZ BZ>6", R[:, 0] > 6), ("quiet BZ<2", R[:, 0] < 2)):
    r = R[m]
    if len(r) == 0: print("  %-11s n=0" % lab); continue
    print("  %-11s n=%4d coherence p50 %.2f | |tq/rate| p50 %.2f units per deg/s | phase p50 %+.0f deg (IQR %s) | tq HF rms p50 %.1f" % (
        lab, m.sum(), np.median(r[:, 1]), np.median(r[:, 2]), np.median(r[:, 3]), np.round(np.percentile(r[:, 3], [25, 75])), np.median(r[:, 4])))
X = np.vstack(M)
print("== 0x1AB (50 Hz): b0 bit7 unique %s, b0 bits2-6 unique %s, b2 bit6 unique %s" % (np.unique(X[:, 1]), np.unique(X[:, 2])[:10], np.unique(X[:, 9])))
m = X[:, 0]
print("  10-bit field p50/p90/p99/max %s ; fraction nonzero %.2f" % (np.percentile(m, [50, 90, 99, 100]), (m > 0).mean()))
for nm, k in (("|tq|", 3), ("|cmd|", 4), ("req", 5), ("BZ", 6), ("|rate lp|", 7), ("v", 8), ("tq signed", 10), ("ang", 11)):
    print("  corr(field, %-9s) %+.2f" % (nm, np.corrcoef(m, X[:, k])[0, 1]))
for lab, mm in (("engaged buzz", (X[:, 5] > 0.5) & (X[:, 6] > 6)), ("engaged quiet", (X[:, 5] > 0.5) & (X[:, 6] < 2)),
                ("manual buzz", (X[:, 5] < 0.5) & (X[:, 6] > 6)), ("manual quiet moving", (X[:, 5] < 0.5) & (X[:, 6] < 2) & (X[:, 8] > 2))):
    x = m[mm]
    if len(x) > 20:
        print("  %-20s n=%5d field mean %.2f, sample-to-sample |diff| mean %.2f, std %.2f" % (lab, len(x), x.mean(), np.abs(np.diff(x)).mean(), x.std()))
# field vs |tq| bins
for lo, hi in ((0, 300), (300, 1000), (1000, 2000), (2000, 4000), (4000, 99999)):
    mm = (X[:, 3] >= lo) & (X[:, 3] < hi)
    if mm.sum() > 20: print("  |tq| %5d-%5d n=%6d field p50 %.0f p90 %.0f" % (lo, hi, mm.sum(), np.median(m[mm]), np.percentile(m[mm], 90)))
