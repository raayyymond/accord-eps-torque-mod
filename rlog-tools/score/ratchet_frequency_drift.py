#!/usr/bin/env python3
r"""HAS THE RATCHET'S FREQUENCY DRIFTED?  Firmware palliative vs mechanical cause.

WHY THIS MATTERS MORE THAN ANOTHER BUILD.  The ratchet is REAL CHASSIS MOTION -- confirmed on the IMU,
which is independent of the EPS -- and it is a lightly-damped resonance (Q 14-29) at a speed-invariant
~7.79 Hz.  A resonance has a physical origin: a mass and a stiffness.  So:

    the peak frequency is STABLE across the corpus  =>  a fixed structural property. Firmware damping
                                                        is a legitimate treatment, and V249 is aimed
                                                        at the right thing.

    the peak frequency DRIFTS with time             =>  something is CHANGING -- a bushing, a tie rod,
                                                        a bearing, torsion-bar preload. Firmware
                                                        damping would then be a PALLIATIVE masking a
                                                        mechanical fault, and the operator should be
                                                        told to have the front end inspected rather
                                                        than flashing another build.

`f = (1/2*pi) sqrt(k/m)`, so a 10 % frequency drop is a ~20 % stiffness loss -- well inside what a
worn bushing or a loosening joint produces, and easily visible here.

METHOD.  Per route, take the engaged 6-9.5 Hz band of the torque sensor, Welch it, and locate the peak.
Routes are ordered by build number, which is also their time order.  Reported with a per-route spread so
a drift is distinguishable from estimator noise.

\U0001f6d1 CONFOUNDS.  Speed, tyre pressure and load all shift a chassis resonance slightly, and the
corpus does not control them.  A small scatter proves nothing.  What would be meaningful is a MONOTONE
trend across builds substantially larger than the within-route spread.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import os
import re
import sys

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = {'r77': 'V90', 'r78': 'V91', 'r7d': 'V94', 'r7e': 'V96', 'r7f': 'V96',
         'r80': 'V97', 'r81': 'V98', 'r82': 'V99', 'r85': 'V100', 'r95': 'V101',
         'r96': 'V102', 'r9e': 'V103', 'ra4': 'V104', 'ra5': 'V105', 'ra6': 'V106',
         'r1e': 'V107', 'r21': 'V111', 'r22': 'V112', 'r24': 'V122'}
BAND = (5.5, 10.5)
SEG_S = 20.0


def cache_for(route):
    for p in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
              os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route, route + '.npz')):
        if os.path.exists(p):
            return p
    return None


def peak_freqs(route):
    """Peak frequency inside the ratchet band, one estimate per 20 s engaged segment."""
    p = cache_for(route)
    if not p:
        return None
    z = np.load(p, allow_pickle=True)
    if not {'t', 'tq', 'cc_lat'} <= set(z.files):
        return None
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    if len(q) < n or e.sum() < 5000:
        return None
    fs = 1.0 / np.median(np.diff(t))
    w = int(SEG_S * fs)
    out = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.95:
            continue
        seg = q[sl] - q[sl].mean()
        if seg.std() < 1e-6:
            continue
        f, P = signal.welch(seg, fs, nperseg=min(2048, w))
        m = (f >= BAND[0]) & (f <= BAND[1])
        if m.sum() < 4:
            continue
        out.append(float(f[m][np.argmax(P[m])]))
    return np.array(out) if len(out) >= 3 else None


def main():
    print('=' * 84)
    print('  HAS THE RATCHET FREQUENCY DRIFTED?   stable = structural · drifting = mechanical wear')
    print('=' * 84)
    print()
    print('  %-6s %-6s %8s %9s %9s %9s' % ('route', 'build', 'segs', 'peak Hz', 'IQR', 'spread'))
    print('  ' + '-' * 54)
    rows = []
    for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
        f = peak_freqs(r)
        if f is None:
            continue
        med = float(np.median(f))
        iqr = float(np.percentile(f, 75) - np.percentile(f, 25))
        rows.append((int(re.sub(r'\D', '', BUILD[r])), r, BUILD[r], med, iqr, len(f)))
        print('  %-6s %-6s %8d %9.2f %9.2f %9.2f'
              % (r, BUILD[r], len(f), med, iqr, float(f.max() - f.min())))
    print('  ' + '-' * 54)
    if len(rows) < 6:
        print('\n  too few routes to test for drift.')
        return
    x = np.array([r[0] for r in rows], float)
    y = np.array([r[3] for r in rows])
    lr = stats.linregress(x, y)
    rho = stats.spearmanr(x, y)
    med_iqr = float(np.median([r[4] for r in rows]))
    span = lr.slope * (x.max() - x.min())
    print('\n  across %d routes spanning builds V%d..V%d:' % (len(rows), int(x.min()), int(x.max())))
    print('     median peak      %.2f Hz   (route-to-route sd %.2f)'
          % (float(np.median(y)), float(np.std(y))))
    print('     within-route IQR %.2f Hz   -- the estimator\'s own noise floor' % med_iqr)
    print('     trend            %+.4f Hz per build  =>  %+.2f Hz over the whole span'
          % (lr.slope, span))
    print('     Spearman rho     %+.3f   p %.3f' % (rho.correlation, rho.pvalue))
    print()
    if rho.pvalue < 0.05 and abs(span) > med_iqr:
        print('  \U0001f6d1 A REAL DRIFT: monotone, and larger than the estimator noise floor.')
        print('     A resonance that MOVES is a resonance whose mass or stiffness is CHANGING.')
        print('     Recommend a front-end inspection -- bushings, tie rods, the torsion bar -- before')
        print('     flashing further. Firmware damping would be masking a mechanical fault.')
    else:
        print('  ✅ NO DRIFT. The peak is stable within the estimator\'s own noise, so the resonance is')
        print('     a FIXED STRUCTURAL PROPERTY of the car, not something wearing.')
        print('     => firmware damping is a legitimate treatment, and V249 is aimed at a real and')
        print('        stationary target rather than papering over a developing fault.')


if __name__ == '__main__':
    main()
