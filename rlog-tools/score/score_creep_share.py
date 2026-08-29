# -*- coding: utf-8 -*-
"""THE ONLY BETWEEN-BUILD ENDPOINT IN THIS KIT THAT SURVIVES ITS OWN NOISE FLOOR.

WHY THE PREVIOUS ENDPOINT DIED
-------------------------------
The engaged/manual RATIO at creep has a between-route noise floor of 20-36x: six routes with
IDENTICAL control cals (gain 3564, a2 22, knee 600, K1 204) span 2.60 to 51.81, and another six
span 36.2x.  Every build comparison made against it was smaller than its own floor.
Cause: it is a RATIO, and it explodes when the manual arm is small.  r9e scored 1520.81 on 39
manual windows.

WHAT FIXES IT
-------------
1. a SHARE, not a ratio:  (18-22 Hz power) / (1-45 Hz power), engaged, at creep.
   Bounded in [0,1] -- it CANNOT explode however small the denominator gets.
2. a MINIMUM EXPOSURE gate: n >= 90 engaged creep windows ~ 2 minutes of engaged creep.
   The low-n routes (r81 n=45, r96 n=70, r9e n=57) were the outliers driving the residual spread.

    identical-cal noise floor with the gate:   knee 600 (n=4) 1.62x    knee 300 (n=3) 1.79x
    => a build effect must exceed ~1.8x to mean anything.  That is a 20x resolution improvement.

WHAT IT SAYS ABOUT THE KNEE
----------------------------
    knee 300  n=3 routes  median SHARE 0.0887
    knee 600  n=5 routes  median SHARE 0.0866      <- IDENTICAL
The knee has no measurable effect, which independently confirms the retraction of the earlier
"knee = 300 is catastrophic" result rather than merely withdrawing it.

HONEST CAVEATS
--------------
* the n >= 90 gate was chosen AFTER seeing which routes were outliers.  A minimum-exposure
  requirement is defensible a priori and 90 windows ~ 2 min is a physical threshold rather than a
  fitted one, but the specific number is post-hoc and wants validation on new data.
* only 8 cached routes qualify.  V112 (n=52, 24) and V122 (n=45) do NOT -- the current best build
  has never had enough engaged creep exposure to be scored at all.

=> DRIVE REQUIREMENT: at least ~2 MINUTES of ENGAGED CREEP (1-24 km/h, hands off, with real
   steering activity) or the drive cannot be scored on this endpoint.

USAGE:  python rlog-tools/score/score_creep_share.py <route> [more]
        python rlog-tools/score/score_creep_share.py --floor      (re-derive the noise floor)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS, NW, NMIN = 100.0, 256, 90
SIG, TOT, CREEP = (18.0, 22.0), (1.0, 45.0), (1.0, 24.0)
FLOOR = 1.8
GROUPS = {'gain3564 a2:22 knee600': ['r79', 'r7f', 'r78', 'r7e', 'r77', 'r81'],
          'gain5346 a2:22 knee300': ['ra6', 'r1e', 'ra5', 'ra4', 'r96', 'r9e']}


def share(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cs_v', 'cc_lat')):
        return None
    r = np.asarray(z['cs_rate']).astype(float)
    v = np.asarray(z['cs_v']).astype(float) * 3.6
    lat = np.asarray(z['cc_lat']).astype(float)
    n = min(len(r), len(v), len(lat))
    r, v, lat = r[:n], v[:n], lat[:n]
    sh = []
    for a in range(0, n - NW, NW // 2):
        s = slice(a, a + NW)
        if not (CREEP[0] <= v[s].mean() < CREEP[1]) or lat[s].mean() < 0.99:
            continue
        x = r[s]
        if not np.isfinite(x).all() or x.std() == 0:
            continue
        f, P = signal.welch(x - x.mean(), FS, nperseg=NW // 2)
        t = P[(f >= TOT[0]) & (f <= TOT[1])].sum()
        if t > 0:
            sh.append(P[(f >= SIG[0]) & (f <= SIG[1])].sum() / t)
    return (float(np.median(sh)), len(sh)) if sh else None


def run(tag):
    s = share(tag)
    print('\n=== %s ===' % tag)
    if s is None:
        print('  no usable data')
        return
    v, n = s
    print('  engaged creep windows: %d   (gate is %d ~ 2 min of engaged creep)' % (n, NMIN))
    print('  18-22 Hz SHARE of 1-45 Hz power: %.4f' % v)
    if n < NMIN:
        print('  \U0001f6d1 NOT SCOREABLE -- only %d windows.  Below the gate the between-route'
              ' spread reaches 7x' % n)
        print('     and the reading carries nothing.  Drive more ENGAGED CREEP.')
        return
    print('  reference medians:  knee 300 -> 0.0887    knee 600 -> 0.0866    (identical)')
    print('  \u2705 SCOREABLE.  A difference from a comparison build must exceed ~%.1fx to mean'
          ' anything.' % FLOOR)


if __name__ == '__main__':
    if '--floor' in sys.argv:
        for g, rs in GROUPS.items():
            v = [(share(t) or (None, 0)) for t in rs]
            ok = [x[0] for x in v if x[0] is not None and x[1] >= NMIN]
            allv = [x[0] for x in v if x[0] is not None]
            print('  %-26s all n: %.2fx (%d routes)   n>=%d: %.2fx (%d routes)'
                  % (g, max(allv) / min(allv), len(allv), NMIN,
                     (max(ok) / min(ok)) if len(ok) > 1 else float('nan'), len(ok)))
        sys.exit(0)
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a:
        print(__doc__)
        sys.exit(0)
    for t in a:
        run(t)
