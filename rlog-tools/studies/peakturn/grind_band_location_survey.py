# -*- coding: utf-8 -*-
"""WHERE IS GRIND #1 NOW?  The operator says it MOVED UP a few firmware versions ago.

Every grind-#1 measurement this session used 18-22 Hz, which is where it was in the V62
era. If it moved, all of those nulls were aimed at the wrong band and mean nothing.

Two questions, in order:
  1. WHERE is the engaged-specific spectral excess on each build, scanning the whole
     visible range rather than assuming a band?
  2. Does that frequency MOVE with build order?  A moving peak is a CLOSED-LOOP POLE and
     is relocatable in firmware -- the opposite of the 7.8 Hz mode, whose f0 was invariant
     to a 2x gain change.

Statistic: engaged-minus-manual log power per frequency bin, WITHIN each route, so road
and exposure differences cancel. cs_rate and imu_vert are both at 100 Hz => visible to
50 Hz. Anything above that is invisible here and must be said so.
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 512
BUILD = [('77', 'V90'), ('78', 'V91'), ('79', 'V92'), ('7e', 'V96'), ('7f', 'V96'),
         ('85', 'V100'), ('95', 'V101'), ('96', 'V102'), ('9e', 'V103'), ('a4', 'V104'),
         ('a5', 'V105'), ('a6', 'V106'), ('1e', 'V107'), ('21', 'V111'), ('22', 'V112'),
         ('23', 'V112'), ('97', 'STOCK')]


def contrast(r, chan):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None, None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in (chan, 'cc_lat', 'cs_v')):
        return None, None
    x, lat, v = [np.asarray(z[k]).astype(float) for k in (chan, 'cc_lat', 'cs_v')]
    eng, man, f = [], [], None
    for a in range(0, len(x) - NW, NW // 2):
        b = a + NW
        if not np.isfinite(x[a:b]).all() or v[a:b].mean() < 1.0:
            continue
        f, P = signal.welch(x[a:b] - x[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        (eng if lat[a:b].mean() > 0.5 else man).append(P)
    if len(eng) < 15 or len(man) < 8:
        return None, None
    E = np.median(np.array(eng), axis=0)
    M = np.median(np.array(man), axis=0)
    return f, 10 * np.log10(np.maximum(E, 1e-30) / np.maximum(M, 1e-30))


for chan in ('cs_rate', 'imu_vert'):
    print("\n=== %s : ENGAGED-minus-MANUAL excess (dB), peak location per build ===" % chan)
    print("  build route   peak 5-48 Hz   excess dB    2nd peak    top-3 bands over 12 Hz")
    for r, b in BUILD:
        f, D = contrast(r, chan)
        if f is None:
            continue
        m = (f >= 5) & (f <= 48)
        ff, dd = f[m], D[m]
        i1 = int(np.argmax(dd))
        hi = ff >= 12
        order = np.argsort(dd[hi])[::-1][:3]
        tops = ', '.join('%.1f Hz %+.1f' % (ff[hi][k], dd[hi][k]) for k in order)
        d2 = dd.copy()
        d2[max(0, i1 - 6):i1 + 7] = -99
        i2 = int(np.argmax(d2))
        print("  %-5s r%-4s   %6.1f Hz     %+6.2f     %5.1f Hz    %s"
              % (b, r, ff[i1], dd[i1], ff[i2], tops))
print("\n  NOTE: cs_rate and imu_vert both sample at 100 Hz => NOTHING above 50 Hz is visible.")
print("  If grind #1 moved above ~48 Hz it CANNOT be seen in this corpus at all.")
