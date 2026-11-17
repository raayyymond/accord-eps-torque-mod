"""Crude plant comparison from MANUAL driving: (1) free return-to-centre: rate vs angle with light hands; (2) holding torque vs angle with the wheel still.
usage: <cache dir> ...  (uses <cache>/_features.npz from census2)"""
import sys, os
import numpy as np
for C in sys.argv[1:]:
    A = dict(np.load(os.path.join(C, "_features.npz")))
    man = ~A["eng"]; mov = A["v"] > 2
    a, r, tq, v = A["ang"], A["rlp"], A["tlp"], A["v"]
    print("==", C)
    for lo, hi in ((2, 8), (8, 14), (14, 30)):
        sp = (v >= lo) & (v < hi)
        m = man & sp & (np.abs(tq) < 300) & (a * r < 0) & (np.abs(a) > 10) & (np.abs(a) < 120)
        if m.sum() > 100:
            k = np.polyfit(np.abs(a[m]), np.abs(r[m]), 1)
            print("  v %2d-%2d light-hands RTC: n %.1f s, |rate| = %.2f*|ang| %+.1f  (i.e. tau ~ %.2f s) | median |rate| at 20-60 deg %.0f deg/s" % (
                lo, hi, m.sum() / 100, k[0], k[1], 1 / max(k[0], 1e-6), np.median(np.abs(r[m & (np.abs(a) > 20) & (np.abs(a) < 60)])) if (m & (np.abs(a) > 20) & (np.abs(a) < 60)).sum() else np.nan))
        else:
            print("  v %2d-%2d light-hands RTC: n %.1f s (too few)" % (lo, hi, m.sum() / 100))
        h = man & sp & (np.abs(r) < 2) & (np.abs(a) > 3) & (np.abs(a) < 90)
        if h.sum() > 100:
            k = np.polyfit(a[h], tq[h], 1)
            print("           still-hold: n %.1f s, tq = %.1f*ang %+.0f (units/deg), corr %.2f" % (h.sum() / 100, k[0], k[1], np.corrcoef(a[h], tq[h])[0, 1]))
