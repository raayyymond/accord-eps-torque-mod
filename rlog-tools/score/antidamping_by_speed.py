# -*- coding: utf-8 -*-
"""AT WHAT SPEED DOES THE ANTI-DAMPING ACTUALLY LIVE?  This decides whether V247 can work at all.

FactorC's speed dead zone is X[0] = 2240 counts = 35 km/h with Y[0] = 0, and zero x anything = 0.
So BELOW 35 km/h the whole damper product is ZERO no matter what FactorE does -- and V247 only opens
FactorE. If the ratchet lives at low speed, V247 is INERT there and the build is aimed wrong.
"""
import glob
import os
import sys

import numpy as np
from scipy import signal

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BAND = (6.0, 9.5)
MIN_COH = 0.60
BINS = [(0, 10), (10, 20), (20, 35), (35, 50), (50, 70), (70, 200)]
FACTORC_KNEE_KMH = 2240 / 64.0


def windows(path):
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cs_rate', 'cc_lat', 'cs_v'} <= set(z.files):
        return []
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    r = np.asarray(z['cs_rate'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    v = np.abs(np.asarray(z['cs_v'], float))[:n] * 3.6
    if len(q) < n or len(r) < n or len(v) < n:
        return []
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = BAND[0] / (fs / 2), BAND[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    w = int(2.0 * fs)
    out = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        cxy = np.mean(qq * np.conj(rr))
        coh = float(np.abs(cxy) ** 2 / max(den * float(np.mean(np.abs(qq) ** 2)), 1e-30))
        if coh < MIN_COH:
            continue
        out.append((float(np.median(v[sl])), float((cxy / den).real)))
    return out


def main():
    print('=' * 80)
    print('  WHERE DOES THE 6-9 Hz ANTI-DAMPING LIVE, BY VEHICLE SPEED?')
    print('=' * 80)
    print('\n  FactorC dead zone: Y[0] = 0 below %.0f km/h -> the damper product is ZERO there,'
          % FACTORC_KNEE_KMH)
    print('  no matter what FactorE does. V247 only opens FactorE.\n')
    rows = []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        try:
            rows += windows(p)
        except Exception:
            continue
    if not rows:
        print('  nothing measurable.')
        return
    V = np.array([x[0] for x in rows])
    Z = np.array([x[1] for x in rows])
    print('  %-14s %9s %12s %11s' % ('speed bin', 'windows', 'Re(Z) median', 'frac Re<0'))
    print('  ' + '-' * 50)
    for lo, hi in BINS:
        m = (V >= lo) & (V < hi)
        if m.sum() < 10:
            print('  %-14s %9d %12s %11s' % ('%d-%d km/h' % (lo, hi), m.sum(), '--', '--'))
            continue
        tag = '%d-%d km/h' % (lo, hi)
        mark = '  <== damper DEAD here' if hi <= FACTORC_KNEE_KMH else ''
        print('  %-14s %9d %12.2f %10.3f%s'
              % (tag, m.sum(), np.median(Z[m]), (Z[m] < 0).mean(), mark))
    print('  ' + '-' * 50)
    below = V < FACTORC_KNEE_KMH
    print('\n  windows BELOW the FactorC knee (%.0f km/h): %d of %d = %.1f %%'
          % (FACTORC_KNEE_KMH, below.sum(), len(V), 100 * below.mean()))
    if below.sum() > 10:
        print('     their Re(Z) median: %+.2f' % np.median(Z[below]))
    print('     ABOVE the knee:       %d windows, Re(Z) median %+.2f'
          % ((~below).sum(), np.median(Z[~below])))
    print('\n  READING')
    if below.mean() > 0.5:
        print('  => MOST of the measured anti-damping is BELOW the FactorC knee, where the damper is')
        print('     structurally ZERO. V247 cannot act there and the build is aimed wrong.')
    else:
        print('  => %.0f %% of the measured anti-damping is ABOVE the knee, where the damper is live'
              % (100 * (~below).mean()))
        print('     and V247 can act. The low-speed remainder needs FactorC opened as well.')


if __name__ == '__main__':
    main()
