# -*- coding: utf-8 -*-
"""Does the drive card's POWER analysis still hold now that it demands HANDS-ON?

The card's detection thresholds were computed on ALL engaged windows -- which are overwhelmingly
hands-OFF (1606 vs 21).  Having just changed the card to require hands ON, the promises in it may
no longer be supported.  Recompute the same endpoints on HANDS-ON 15 s windows only.

If hands-on power is materially worse, the card is promising something the drive cannot deliver and
must say so instead.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, WIN, NPS = 100.0, int(15 * 100), 512
CTRL = (30.0, 40.0)
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']
ENDPOINTS = [((6.5, 11.0), 'RATCHET 6.5-11 Hz', 0.260),
             ((15.0, 25.0), 'GRIND 15-25 Hz', 0.058),
             ((0.5, 3.0), 'LKAS 0.5-3 Hz', 0.846)]


def win15(handson):
    out = []
    for tag in ROUTES:
        p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
        if not os.path.exists(p):
            continue
        z = np.load(p, allow_pickle=True)
        if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq', 'cs_press')):
            continue
        lat = np.asarray(z['cc_lat']).astype(float)
        kmh = np.asarray(z['cs_v']).astype(float) * 3.6
        tq = np.asarray(z['cs_tq']).astype(float)
        pr = np.asarray(z['cs_press']).astype(float)
        n = min(len(lat), len(kmh), len(tq), len(pr))
        lat, kmh, tq, pr = lat[:n], kmh[:n], tq[:n], pr[:n]
        ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(tq)
        if handson is not None:
            ok &= (pr > 0.5) if handson else (pr <= 0.5)
        d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
        for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if (j - i) >= WIN and np.std(tq[i:i + WIN]) > 0:
                out.append(tq[i:i + WIN])
    return out


def bp(x, lo, hi):
    f, P = signal.welch(x - x.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
    m = (f >= lo) & (f <= hi)
    tr = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    return float(tr(P[m], f[m]))


for label, hs in (('ALL engaged (what the card was sized on)', None),
                  ('HANDS-ON engaged (what the card now asks for)', True)):
    W = win15(hs)
    print('')
    print('=== %s : %d continuous 15 s windows' % (label, len(W)))
    if len(W) < 4:
        print('    ** TOO FEW TO CHARACTERISE. The card cannot promise a threshold here. **')
        continue
    for (lo, hi), nm, pred in ENDPOINTS:
        v = np.array([bp(w, lo, hi) / max(bp(w, *CTRL), 1e-30) for w in W])
        v = v[np.isfinite(v) & (v > 0)]
        if len(v) < 4:
            print('    %-20s too few finite' % nm)
            continue
        sd = float(np.std(np.log10(v), ddof=1))
        det = 10 ** (1.96 * sd)
        margin = (1.0 / pred) / det
        print('    %-20s n=%-3d log10 sd %.3f   detect@1 %6.2fx   predicted %.3fx   %s'
              % (nm, len(v), sd, det, pred,
                 'ANSWERABLE (margin %.2fx)' % margin if margin >= 1
                 else 'NOT answerable (margin %.2fx)' % margin))
print('')
print('=> If HANDS-ON power is materially worse, the card must say what one hands-on pass can and')
print('   cannot answer -- otherwise it promises a result the drive will not deliver.')
