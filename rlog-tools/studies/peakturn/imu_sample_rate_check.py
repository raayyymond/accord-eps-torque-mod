# -*- coding: utf-8 -*-
"""A NEW INSTRUMENT FOR GRIND #1: the IMU.

Grind #1 is AUDIBLE and felt -- the operator's V94 report was "it vibrated the entire car".
Every measurement so far has used STEERING RATE, which needs creep exposure the recent
routes do not have. The cache carries imu_vert and imu_lat, which see chassis vibration
directly and are independent of steering exposure entirely.

Two questions:
  1. Do the IMU channels carry usable content in the grind bands at all, or are they
     rate-limited / anti-alias filtered into uselessness?
  2. Does IMU band content track anything -- engagement, build, or the steering-rate
     measure -- well enough to serve as an instrument?

Reported with the sampling rate checked FIRST, because an IMU logged at 20-50 Hz cannot
see 18-22 Hz at all and every number after that would be an alias.
"""
import numpy as np, os
from scipy import signal

ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e',
          'a4', 'a5', 'a6', '1e']
for r in ROUTES[:1]:
    z = np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r), allow_pickle=True)
    print("channels containing 'imu':", [k for k in z.files if 'imu' in k.lower()])
    for k in ('imu_vert', 'imu_lat', 't'):
        if k in z.files:
            a = np.asarray(z[k])
            print("  %-10s len=%-8d dtype=%s  finite=%.3f" % (k, len(a), a.dtype,
                                                              np.isfinite(a.astype(float)).mean()))

print("\n  INFERRED SAMPLE RATE from the length ratio against cs_rate (which is 100 Hz):")
for r in ROUTES:
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        continue
    z = np.load(p, allow_pickle=True)
    if 'imu_vert' not in z.files or 'cs_rate' not in z.files:
        continue
    n_imu = len(np.asarray(z['imu_vert']))
    n_rate = len(np.asarray(z['cs_rate']))
    v = np.asarray(z['imu_vert']).astype(float)
    fin = np.isfinite(v).mean()
    uniq = len(np.unique(v[np.isfinite(v)][:20000]))
    print("   r%-4s  imu %7d   rate %7d   ratio %5.2f  => ~%5.1f Hz   finite %.3f  uniq %d"
          % (r, n_imu, n_rate, n_imu / max(n_rate, 1), 100.0 * n_imu / max(n_rate, 1), fin, uniq))
    if r == ROUTES[-1] or n_imu > 0:
        pass

print("\n  => an IMU below ~50 Hz CANNOT see the 18-22 Hz grind band (Nyquist), and")
print("     anything reported there would be an alias.  Checking one route's spectrum:")
z = np.load('analysis-2020accord/_scratch/cache/r22/r22.npz', allow_pickle=True)
if 'imu_vert' in z.files:
    v = np.asarray(z['imu_vert']).astype(float)
    v = v[np.isfinite(v)]
    n = len(v)
    for fs_guess in (100.0, 50.0, 20.0):
        if n > 512:
            f, P = signal.welch(v - v.mean(), fs_guess, nperseg=min(512, n // 4))
            tot = P.sum()
            b = lambda lo, hi: P[(f >= lo) & (f <= hi)].sum() / tot * 100
            print("     assuming %5.1f Hz:  0.5-3 Hz %5.1f %%   6-9 Hz %5.1f %%   18-22 Hz %5.1f %%   f_max %.1f Hz"
                  % (fs_guess, b(0.5, 3), b(6, 9), b(18, 22), f[-1]))
