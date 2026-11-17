"""De-alias test: does the 0x14A ANGLE move the way the buzzing 0x14A RATE says it should?
If the as-sampled 12-18 Hz rate line were the true frequency, its integral (amp ~0.1-0.15 deg) must appear on the angle.
If it is a fold of ~82-88 Hz (or 112-118 Hz), the true angle excursion is 5-8x smaller (~0.02 deg, under the 0.1 deg LSB).
Validation band: 1.5-4 Hz (real steering), where angle and integrated rate must agree.
usage: <cache dir> [<cache dir> ...]"""
import sys, os
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs

bh, ah = signal.butter(4, [11 / 50, 20 / 50], "band")
bl, al = signal.butter(4, [1.5 / 50, 4 / 50], "band")
for C in sys.argv[1:]:
    rows = []
    for seg, p in segs(C):
        d = load(p)
        ang = d["ang"]
        irate = np.cumsum(d["rate"]) * 0.01
        a_h, i_h = signal.filtfilt(bh, ah, ang), signal.filtfilt(bh, ah, irate)
        a_l, i_l = signal.filtfilt(bl, al, ang), signal.filtfilt(bl, al, irate)
        W = 64
        for i in range(0, len(ang) - W, W):
            s = slice(i, i + W)
            if d["v"][s].mean() < 2:
                continue
            rows.append((d["bz"][s].mean(), a_h[s].std(), i_h[s].std(), np.corrcoef(a_h[s], i_h[s])[0, 1],
                         a_l[s].std(), i_l[s].std(), np.corrcoef(a_l[s], i_l[s])[0, 1]))
    R = np.array(rows)
    print("==", C, "windows", len(R))
    bz = R[:, 0]
    for name, m in (("BUZZ  BZ>6", bz > 6), ("quiet BZ<2", bz < 2)):
        r = R[m]
        print("  %-12s n=%4d | 11-20 Hz: angle rms %.3f deg vs integrated-rate rms %.3f deg, ratio p50 %.2f, corr p50 %+.2f" % (
            name, m.sum(), np.median(r[:, 1]), np.median(r[:, 2]), np.median(r[:, 1] / np.maximum(r[:, 2], 1e-6)), np.nanmedian(r[:, 3])))
        mm = r[:, 5] > 0.3  # windows with real 1.5-4 Hz steering
        if mm.sum() > 3:
            print("  %-12s n=%4d | 1.5-4 Hz VALIDATION: angle rms %.3f vs int-rate rms %.3f, ratio p50 %.2f, corr p50 %+.2f" % (
                "", mm.sum(), np.median(r[mm, 4]), np.median(r[mm, 5]), np.median(r[mm, 4] / r[mm, 5]), np.nanmedian(r[mm, 6])))
