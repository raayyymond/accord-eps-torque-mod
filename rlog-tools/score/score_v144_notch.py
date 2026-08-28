# -*- coding: utf-8 -*-
"""SCORE V144 -- DID THE RETUNED NOTCH ACTUALLY RUN?

WHAT V144 DID
-------------
FUN_000352b4 (the only writer of aggregator lane gp-0x6B86) runs a gated second-order FLOAT
section.  Its rate is TASK 1 = 1 kHz (TCB 0xBB928 entry 0x0002214A == FUN_0002214a, the only
caller), so Honda's 19.88 deg notch sat at 55.23 Hz -- useless for an 18-22 Hz grind.
V144 retuned it onto 20 Hz:

    A = -1.94454481  0xC60A8      C = -1.98422940  0xC60B0
    B =  0.96040000  0xC60AC      D =  1.00536370  0xC60B4
    |H| DC = 1.000000 (authority unchanged) | 18 Hz 0.540 | 20 Hz ~0 | 22 Hz 0.540 | peak 1.0258

and repointed the 427 probe onto gp-0x6B86, the lane itself.

    wire = min((|lane| * 5) >> 3, 1023)      =>   lane = (wire << 3) / 5
    427 samples at 49.9 Hz  =>  Nyquist 24.95 Hz, so a 20 Hz null lands DIRECTLY in band.

THE LOAD-BEARING BELIEF THIS TESTS
------------------------------------
The section arms ONLY when cal(0xC649B) == 1 (true on V122, 0 in stock) AND
gp-0x671a >= cal(0xC64FA) = 5, i.e. the hard-reversal counter AT ITS CEILING.  A ratchet IS
repeated reversals, so it should arm -- but this kit has never measured it.

  * a DEEP NULL near 20 Hz            -> the gate OPENS and the retuned notch is RUNNING.
  * lane ACTIVE but NO null           -> the gate stays SHUT.  V144 is inert (not harmful).
                                         Do NOT widen the gate: 0xC64FA has EIGHTEEN readers, ten of them an
                                         unexamined cluster at 0x260BC-0x261A2.  Fall back to V141.
  * lane DEAD                         -> gp-0x6B86 carries nothing; the notch is irrelevant
                                         however it is tuned.  Fall back to V141.

A PRE-V144 ROUTE IS THE CONTROL: Honda's notch sits at 55.23 Hz, which ALIASES to 5.3 Hz at
49.9 Hz sampling.  If a null appears near 5.3 Hz on a pre-V144 route and near 20 Hz on a V144
route, that is the retune working, confirmed against its own before-image.

USAGE:  python rlog-tools/score/score_v144_notch.py <route> [more]
        python rlog-tools/score/score_v144_notch.py <route> --baseline
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS_CAN, SAR = 49.9, 3
NOTCH_HZ = 20.0
HONDA_ALIAS = abs(55.23 - FS_CAN)      # 5.33 Hz -- where Honda's 55.2 Hz notch folds to
NW = 256
DEAD_FRAC = 0.90


def load(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  %s: no cache' % tag)
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('ab_mt', 'cc_lat')):
        print('  %s: missing ab_mt / cc_lat' % tag)
        return None
    pb = str(np.atleast_1d(z['probe_build'])[0]) if 'probe_build' in z.files else '?'
    mt = np.asarray(z['ab_mt']).astype(float)
    lat = np.asarray(z['cc_lat']).astype(float)
    n = min(len(mt), len(lat))
    return pb, mt[:n], lat[:n]


def run(tag, baseline=False):
    r = load(tag)
    if r is None:
        return
    pb, mt, lat = r
    print('\n=== %s  (probe_build %s) ===' % (tag, pb))
    if not baseline and 'V144' not in pb.upper():
        print('  \U0001f6d1 probe_build is %r, not V144 -- the 427 tap is NOT on gp-0x6B86 and the'
              ' biquad is NOT retuned.  Refusing to interpret.' % pb)
        print('     (--baseline looks at the shape anyway; a PRE-V144 route is the control, where'
              ' Honda\'s 55.23 Hz notch should alias to ~%.1f Hz)' % HONDA_ALIAS)
        return
    eng = lat > 0.5
    x = mt[eng]
    x = x[np.isfinite(x)]
    if x.size < 4 * NW:
        print('  only %d engaged frames -- too few' % x.size)
        return
    lane = np.abs(x) * (1 << SAR) / 5.0
    zero = float((np.abs(x) == 0).mean())
    print('  engaged n=%d   lane p50 %.0f  p90 %.0f  p99 %.0f   frac ZERO %.4f'
          % (x.size, *[np.percentile(lane, q) for q in (50, 90, 99)], zero))
    if zero >= DEAD_FRAC:
        print('\n  \U0001f6d1 VERDICT: the lane is DEAD (%.1f %% of engaged frames read zero).'
              % (100 * zero))
        print('     gp-0x6B86 carries nothing, so the notch is irrelevant however it is tuned.')
        print('     FALL BACK to V141 (the pump deadband).  Do NOT spend a build retuning this.')
        return
    f, P = signal.welch(x - x.mean(), FS_CAN, nperseg=NW)
    band = (f > 1.0) & (f < 24.0)
    fb, Pb = f[band], P[band]
    sm = np.convolve(Pb, np.ones(9) / 9.0, mode='same')       # local baseline
    depth = Pb / np.maximum(sm, 1e-30)
    i = depth.argmin()
    print('  spectral minimum at %.2f Hz, %.1f dB below the local baseline'
          % (fb[i], 10 * np.log10(max(depth[i], 1e-30))))
    print('  (V144 predicts a null at %.1f Hz; a PRE-V144 route should null near %.1f Hz,'
          ' where Honda\'s 55.23 Hz folds)' % (NOTCH_HZ, HONDA_ALIAS))
    near = abs(fb[i] - NOTCH_HZ) < 2.5
    deep = 10 * np.log10(max(depth[i], 1e-30)) < -6.0
    print()
    if near and deep:
        print('  ✅ VERDICT: a DEEP null sits on %.1f Hz => the gate OPENS and the retuned notch'
              ' is RUNNING.' % NOTCH_HZ)
        print('     If the operator also reports the grinding gone, the lever is confirmed and the')
        print('     next step is V142 (8x gain) for authority, per the sequencing.')
    elif deep:
        print('  ⚠ VERDICT: a deep null exists but at %.2f Hz, not %.1f.' % (fb[i], NOTCH_HZ))
        print('     If it is near %.1f Hz the biquad did NOT take; re-check the four coefficients.'
              % HONDA_ALIAS)
    else:
        print('  \U0001f6d1 VERDICT: the lane is ACTIVE but there is NO null (best %.1f dB at'
              ' %.2f Hz).' % (10 * np.log10(max(depth[i], 1e-30)), fb[i]))
        print('     => the gate (gp-0x671a >= 5) stays SHUT.  V144 is INERT, not harmful.')
        print('     \U0001f6d1 Do NOT widen the gate: 0xC64FA has 18 READERS')
        print('        including an unexamined 10-reader cluster at 0x260BC.  FALL BACK to V141.')


if __name__ == '__main__':
    bl = '--baseline' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(0)
    for t in args:
        run(t, baseline=bl)
