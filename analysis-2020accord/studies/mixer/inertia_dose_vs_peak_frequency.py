# -*- coding: utf-8 -*-
"""Does the creep-regime peak frequency scale as 1/sqrt(inertia dose)?  NO -- REFUTED.

gp-0x6b26 is -K*alpha (acceleration feedback), which adds APPARENT INERTIA.  A mass-spring
resonance would then give f ~ 1/sqrt(J), i.e. a log-log slope of -0.5 against the 0xD7A5C dose.

Taking the argmax of the 5-45 Hz spectrum over creep-matched engaged episodes appears to CONFIRM it
beautifully:  slope -0.540, corr -0.751, n=9.  That number is an ARTEFACT and this file exists so
nobody re-derives it.

THE CONTROL THAT KILLS IT.  The peaks are BIMODAL -- a 5-12 Hz cluster and a 15-45 Hz cluster -- and
argmax hops between them.  At dose 1.500 two routes sit in each cluster: SAME DOSE, OPPOSITE ANSWERS.
Fitting each band separately:

    LOW  band (5-12 Hz)   corr +0.684  slope +0.061     <- WRONG SIGN, and flat
    HIGH band (15-45 Hz)  corr -0.845  slope -0.159     <- right sign, wrong magnitude

A pure apparent-inertia effect must move BOTH bands at -0.5.  It moves neither.

AND THE HIGH-BAND ASSOCIATION IS CARRIED ENTIRELY BY ONE ROUTE:

    all routes      n=9  corr -0.845  slope -0.159  perm p=0.0089
    WITHOUT r7d     n=8  corr -0.510  slope -0.089  perm p=0.1769   <- not significant

r7d is the ABORTED V94 drive, a single build at an extreme dose (0.250x).  Within-dose spread at
1.500 is 3.13 Hz across four routes, against a 13.67 Hz total range -- route-to-route variation at
FIXED dose is a quarter of the whole claimed effect.

=> [EVIDENCE] The mass-spring / apparent-inertia explanation of the ~31 Hz line is REFUTED by its own
   quantitative prediction.  The 31 Hz line on r7d REMAINS UNEXPLAINED.  Do not re-open this without
   a new drive at a low inertia dose -- the corpus cannot settle it, because only one route has one.

Run:  python analysis-2020accord/studies/mixer/inertia_dose_vs_peak_frequency.py
"""
import numpy as np

# creep-matched (engaged, 0.4 < v < 1.5 m/s), per-route mean Welch spectrum, nperseg 256 @ 100 Hz
TAG = ['r7d', 'r77', 'r81', 'r82', 'r95', 'ra4', 'r22', 'r24', 'r1e']
BLD = ['V94', 'V90', 'V98', 'V99', 'V101', 'V104', 'V112', 'V122', 'V107']
DOSE = np.array([0.250, 1.000, 1.500, 1.500, 1.500, 1.500, 3.576, 3.576, 3.964])
LOW = np.array([6.64, 7.03, 7.81, 7.42, 7.81, 7.42, 7.03, 7.81, 8.59])
HIGH = np.array([30.86, 21.88, 19.92, 19.53, 22.27, 22.66, 19.92, 21.88, 17.19])


def fit(d, y, label):
    c = float(np.corrcoef(np.log(d), np.log(y))[0, 1])
    s = float(np.polyfit(np.log(d), np.log(y), 1)[0])
    rng = np.random.default_rng(0)
    n = 20000
    hits = sum(1 for _ in range(n)
               if abs(np.corrcoef(np.log(d), np.log(rng.permutation(y)))[0, 1]) >= abs(c))
    print('  %-30s n=%d  corr %+.3f  slope %+.3f  perm p=%.4f' % (label, len(d), c, s, hits / n))
    return c, s, hits / n


print('=' * 84)
print('  INERTIA DOSE vs CREEP PEAK FREQUENCY -- the 1/sqrt(J) hypothesis, REFUTED')
print('=' * 84)
print()
print('  %-6s %-6s %8s %8s %8s' % ('route', 'build', 'dose', 'LOW_pk', 'HIGH_pk'))
for t, b, d, lo, hi in zip(TAG, BLD, DOSE, LOW, HIGH):
    print('  %-6s %-6s %8.3f %8.2f %8.2f' % (t, b, d, lo, hi))
print()
fit(DOSE, LOW, 'LOW band 5-12 Hz')
fit(DOSE, HIGH, 'HIGH band 15-45 Hz')
k = [i for i, t in enumerate(TAG) if t != 'r7d']
_, _, p = fit(DOSE[k], HIGH[k], 'HIGH band WITHOUT r7d')
print()
m = DOSE == 1.5
print('  within-dose spread at 1.500x: %.2f Hz over %d routes' % (HIGH[m].max() - HIGH[m].min(), m.sum()))
print('  total across-dose range:      %.2f Hz' % (HIGH.max() - HIGH.min()))
print()
assert abs(np.polyfit(np.log(DOSE), np.log(LOW), 1)[0]) < 0.25, 'LOW band slope must be ~flat'
assert p > 0.05, 'the HIGH band association must NOT survive dropping r7d'
print('  REFUTED, and both refutation conditions are asserted above.')
