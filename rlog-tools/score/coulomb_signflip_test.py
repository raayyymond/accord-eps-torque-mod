# -*- coding: utf-8 -*-
"""THE decisive Coulomb test: does ratchet-band torque spike at RATE SIGN CHANGES?

Coulomb friction OPPOSES motion, so it flips sign when the rate crosses zero, producing a torque
STEP.  A rate-proportional or loop effect has no such feature.

The control has to be matched: at a zero-crossing |rate| is small BY DEFINITION, so comparing
crossings against all other samples would just re-measure the low-rate regime.  The right control is
samples that DWELL at similarly low |rate| WITHOUT changing sign.

    CROSS   : rate changes sign between consecutive samples
    DWELL   : |rate| below the same threshold, no sign change within +-W samples
    => if Coulomb, the 5-12 Hz torque envelope is HIGHER at CROSS than at DWELL.
    => the 15-25 Hz grind band is the negative control; it should show no such preference.
"""
import os, sys, glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 100.0
W = 5


def env(x, lo, hi):
    b, a = signal.butter(2, [lo / (FS / 2), hi / (FS / 2)], btype='band')
    y = signal.filtfilt(b, a, x)
    return np.abs(signal.hilbert(y))


cr, dw, crg, dwg = [], [], [], []
nroute = 0
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try:
        z = np.load(p, allow_pickle=True)
    except Exception:
        continue
    if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq', 'cs_rate')):
        continue
    lat = np.asarray(z['cc_lat']).astype(float)
    kmh = np.asarray(z['cs_v']).astype(float) * 3.6
    tq = np.asarray(z['cs_tq']).astype(float)
    rt = np.asarray(z['cs_rate']).astype(float)
    n = min(len(lat), len(kmh), len(tq), len(rt))
    lat, kmh, tq, rt = lat[:n], kmh[:n], tq[:n], rt[:n]
    ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(tq) & np.isfinite(rt)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if (j - i) < 400:
            continue
        s, r = tq[i:j], rt[i:j]
        if np.std(s) <= 0:
            continue
        er, eg = env(s, 5.0, 12.0), env(s, 15.0, 25.0)
        sg = np.sign(r)
        chg = np.zeros(len(r), bool)
        chg[1:] = (sg[1:] != sg[:-1]) & (sg[1:] != 0) & (sg[:-1] != 0)
        thr = np.percentile(np.abs(r), 40)
        low = np.abs(r) <= thr
        near = np.convolve(chg.astype(float), np.ones(2 * W + 1), 'same') > 0
        dwell = low & ~near
        if chg.sum() < 5 or dwell.sum() < 5:
            continue
        cr.append(np.median(er[chg])); dw.append(np.median(er[dwell]))
        crg.append(np.median(eg[chg])); dwg.append(np.median(eg[dwell]))
        nroute += 1
cr, dw, crg, dwg = map(np.array, (cr, dw, crg, dwg))
print('%d engaged-creep episodes with both CROSS and DWELL samples' % nroute)
print('')


def boot(a, b, n=4000):
    idx = np.random.default_rng(0).integers(0, len(a), (n, len(a)))
    r = np.array([np.median(a[k]) / max(np.median(b[k]), 1e-30) for k in idx])
    return np.percentile(r, [2.5, 97.5])


for nm, a, b in (('RATCHET 5-12 Hz', cr, dw), ('GRIND 15-25 Hz  (control)', crg, dwg)):
    ratio = np.median(a) / max(np.median(b), 1e-30)
    lo, hi = boot(a, b)
    verdict = ('CROSS > DWELL' if lo > 1.0 else
               'CROSS < DWELL' if hi < 1.0 else 'no difference')
    print('%-26s cross %8.2f   dwell %8.2f   ratio %5.2f  [%.2f, %.2f]   %s'
          % (nm, np.median(a), np.median(b), ratio, lo, hi, verdict))
print('')
print('=> Coulomb predicts the RATCHET ratio > 1 with the GRIND control at ~1.')
print('   Both > 1 equally would mean the crossing itself excites everything (not Coulomb-specific).')
