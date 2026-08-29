# -*- coding: utf-8 -*-
"""Does the ratchet EXIST in MANUAL? This decides whether any engaged-only lever can eliminate it.

Every lever now on the shelf is engaged-only (the inertia dose is m26/27; the biquad is
engaged-gated).  The measured engaged excess at 8.4 Hz is only ~3.6x hands-matched.  So:

  * if MANUAL shows NO significant peak at ~8.4 Hz, engagement is NECESSARY for the ratchet and
    removing the engaged excess could eliminate the symptom;
  * if MANUAL shows a peak too, the ratchet exists without engagement, and an engaged-only lever
    can at best reduce it by the 3.6x excess -- it cannot remove it.

Endpoint: slope-corrected band excess against the route's OWN slope-matched null, the only
validated instrument in the kit.  Hands-ON windows only, so the driver is on the wheel in both
arms and the comparison is fair.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
BAND = (6.5, 11.0)
FIT = [(3.0, 6.0), (12.0, 40.0)]         # fit the power law OUTSIDE the test band
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
        if not (pr[s] > 0.5).all():                  # HANDS-ON only, both arms
            continue
        f, P = signal.welch(tq[s] - tq[s].mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        out.append(((lat[s] > 0.5).all(), P, f))
    return out


W = [w for t in ROUTES for w in windows(t)]
if not W:
    print('no hands-on windows'); sys.exit(0)
f = W[0][2]
E = [w[1] for w in W if w[0]]
M = [w[1] for w in W if not w[0]]
print('HANDS-ON windows:  engaged %d   manual %d' % (len(E), len(M)))

fitm = np.zeros_like(f, bool)
for lo, hi in FIT:
    fitm |= (f >= lo) & (f <= hi)
bandm = (f >= BAND[0]) & (f <= BAND[1])


FIXED_F = 8.40   # FIXED, not argmax: a max-over-band statistic is upward-biased under
                 # bootstrap resampling, which put the point estimate OUTSIDE its own CI.


def excess(P):
    """excess at a FIXED frequency over the power law fitted OUTSIDE the band"""
    good = fitm & (P > 0)
    if good.sum() < 8:
        return np.nan, np.nan
    b, a = np.polyfit(np.log10(f[good]), np.log10(P[good]), 1)
    k = int(np.argmin(np.abs(f - FIXED_F)))
    pred = 10 ** (a + b * np.log10(f[k]))
    return float(P[k] / pred), float(f[k])


def arm(pool, label, rng):
    if len(pool) < 8:
        print('  %-9s too few windows' % label)
        return
    P = np.median(np.asarray(pool), 0)
    e, pf = excess(P)
    bs = []
    for _ in range(400):
        idx = rng.integers(0, len(pool), len(pool))
        v = excess(np.median(np.asarray([pool[k] for k in idx]), 0))[0]
        if np.isfinite(v):
            bs.append(v)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    verdict = ('PEAK PRESENT (CI excludes 1)' if lo > 1.0
               else '** NO significant peak (CI includes 1) **')
    print('  %-9s excess %6.2fx at %5.2f Hz   CI [%.2f, %.2f]   %s'
          % (label, e, pf, lo, hi, verdict))
    return lo, hi, e


print('')
print('slope-corrected band excess in 6.5-11 Hz, power law fitted on 3-6 and 12-40 Hz:')
rng = np.random.default_rng(4)
re_ = arm(E, 'ENGAGED', rng)
rm_ = arm(M, 'MANUAL', rng)

print('')
if rm_ is None or re_ is None:
    print('=> cannot decide with this exposure.')
else:
    mlo, mhi, me = rm_
    if mlo > 1.0:
        print('=> ** THE RATCHET EXISTS IN MANUAL TOO ** (excess %.2fx, CI excludes 1).' % me)
        print('   An ENGAGED-ONLY lever cannot eliminate it -- at best it removes the ~3.6x')
        print('   engaged excess and leaves the manual-level resonance behind.')
        print('   => eliminating the symptom needs a lever that acts in BOTH modes.')
    else:
        print('=> ** NO significant ratchet in MANUAL. ** Engagement is necessary for it, so')
        print('   removing the engaged excess could eliminate the symptom outright.')
        print('   => the engaged-only levers on the shelf are the right family.')
