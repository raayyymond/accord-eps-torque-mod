# -*- coding: utf-8 -*-
"""WHERE does engagement cross from SUPPRESSING to AMPLIFYING? That constrains the mechanism.

Last round, speed-matched: engaged/manual PSD ratio is 0.79 at 3.9 Hz but 33x at 8.4 Hz and still
>1 at 25 Hz.  So the engaged loop's contribution is STABILISING at low frequency and
DESTABILISING above some crossover f_c.

f_c is a hard constraint: whatever element is responsible must have its phase crossover / corner
there.  Locate f_c with a bootstrap CI over WINDOWS (not frequency bins -- bin bootstraps
manufacture significance, per [[feedback-episodes-not-windows]] the resampling unit must be the
episode/window).
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']


def windows(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq', 'cs_press')):
        return []
    lat = np.asarray(z['cc_lat']).astype(float)
    kmh = np.asarray(z['cs_v']).astype(float) * 3.6
    tq = np.asarray(z['cs_tq']).astype(float)
    pr = np.asarray(z['cs_press']).astype(float)
    n = min(len(lat), len(kmh), len(tq), len(pr))
    lat, kmh, tq, pr = lat[:n], kmh[:n], tq[:n], pr[:n]
    ok = np.isfinite(tq) & (kmh >= 1.0) & (kmh < 60.0)
    out = []
    for i in range(0, n - NPS, NPS // 2):
        s = slice(i, i + NPS)
        if not ok[s].all() or np.std(tq[s]) <= 0:
            continue
        if not (lat[s] > 0.5).all() and not (lat[s] <= 0.5).all():
            continue
        f, P = signal.welch(tq[s] - tq[s].mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        hands = float(np.mean(pr[s] > 0.5))
        out.append(((lat[s] > 0.5).all(), float(np.mean(kmh[s])), P, f, hands))
    return out


W = [w for t in ROUTES for w in windows(t)]
f = W[0][3]
HANDS_ON = float(os.environ.get('HANDS','-1'))
if HANDS_ON >= 0:
    W = [w for w in W if (w[4] > 0.8 if HANDS_ON > 0.5 else w[4] < 0.2)]
    print('HANDS-%s subset: %d windows' % ('ON' if HANDS_ON>0.5 else 'OFF', len(W)))
E = [w for w in W if w[0]]
M = [w for w in W if not w[0]]
print('windows: engaged %d  manual %d' % (len(E), len(M)))
BINS = np.array([1, 5, 10, 15, 20, 30, 45, 60.0])


def matched_ratio(E, M, rng):
    ei, mi = [], []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        e = [k for k, w in enumerate(E) if lo <= w[1] < hi]
        m = [k for k, w in enumerate(M) if lo <= w[1] < hi]
        n = min(len(e), len(m))
        if n == 0:
            continue
        ei += list(rng.choice(e, n, replace=True))
        mi += list(rng.choice(m, n, replace=True))
    if len(ei) < 20:
        return None
    Pe = np.median(np.asarray([E[k][2] for k in ei]), 0)
    Pm = np.median(np.asarray([M[k][2] for k in mi]), 0)
    return Pe / np.maximum(Pm, 1e-30)


def crossover(r):
    """lowest frequency in 2-20 Hz where the ratio crosses 1.0 upward"""
    m = (f >= 2.0) & (f <= 20.0)
    ff, rr = f[m], r[m]
    for i in range(len(rr) - 1):
        if rr[i] < 1.0 <= rr[i + 1]:
            t = (1.0 - rr[i]) / (rr[i + 1] - rr[i])
            return ff[i] + t * (ff[i + 1] - ff[i])
    return np.nan


rng = np.random.default_rng(7)
pt = matched_ratio(E, M, rng)
fc = crossover(pt)
print('point estimate: crossover at %.2f Hz' % fc)
print('')
print('  ratio through the crossover region:')
for fr in (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.4, 12.0, 20.0):
    k = np.argmin(np.abs(f - fr))
    print('    %5.2f Hz   %8.3f %s' % (f[k], pt[k], '<-- crosses 1.0' if abs(f[k] - fc) < 0.3 else ''))

boot = []
for s in range(400):
    r = matched_ratio(E, M, np.random.default_rng(1000 + s))
    if r is None:
        continue
    c = crossover(r)
    if np.isfinite(c):
        boot.append(c)
boot = np.asarray(boot)
lo, hi = np.percentile(boot, [2.5, 97.5])
print('')
print('bootstrap over WINDOWS (n=%d): crossover 95%% CI [%.2f, %.2f] Hz' % (len(boot), lo, hi))
print('')
print('WHAT MUST HAVE ITS CORNER THERE  (elements on the ENGAGED path, from the images):')
import math
for nm, cal, a_over in (('accel EMA alpha 0xC40DC (car=8)', 8, 64.0),
                        ('accel EMA alpha 0xC40DC (Honda=22)', 22, 64.0),
                        ('Path-2 sum EMA 0xC63AC (=102)', 102, 1024.0)):
    a = cal / a_over
    print('   %-38s fc = %6.2f Hz' % (nm, -math.log(1 - a) * 1000.0 / (2 * math.pi)))
print('   %-38s fc = %6.2f Hz' % ('flying biquad pole (0.7966)',
                                  -math.log(0.7966) * 1000.0 / (2 * math.pi)))
print('')
print('=> any element whose corner is FAR from the measured crossover cannot be the phase')
print('   rotation that turns suppression into amplification.')
