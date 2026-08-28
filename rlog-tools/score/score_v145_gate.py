# -*- coding: utf-8 -*-
"""SCORE V145 -- DOES THE NOTCH'S GATE EVER OPEN?  A BINARY, NOISE-FREE MEASUREMENT.

V144/V145 retune Honda's own notch (FUN_000352b4, lane gp-0x6B86) from 55.2 Hz onto 20 Hz.  The
section arms ONLY when cal(0xC649B)==1 (true) AND gp-0x671a >= cal(0xC64FA)=5.  Whether that
second half ever happens is the load-bearing belief, and it had never been measured.

THE AGGREGATOR ALREADY MIRRORS THE GATE:
    bVar1 = *(byte*)(gp-0x671a) < *(byte*)(tp+0x74fa);        // the gate condition
    sVar7 = bVar1 ? cal(0xC6138)=1 : cal(0xC6136)=0;
    *(short *)(gp - 0x6c24) = sVar7;                          // one gp access image-wide: this write
V145 taps gp-0x6c24 and moves the packer to sar 1, because at sar 3 BOTH values map to wire 0 and
the probe would have been blind.

    wire = min((|x| * 5) >> 1, 1023)      =>   gate SHUT -> wire 2      gate OPEN -> wire 0

The wire is a digital field, so this is exact: the OPEN duty is just the fraction of frames reading
0.  No spectra, no thresholds, no bootstrap.

USAGE:  python rlog-tools/score/score_v145_gate.py <route> [more]
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')
WIRE_SHUT, WIRE_OPEN = 2, 0


def run(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  %s: no cache' % tag)
        return
    z = np.load(p, allow_pickle=True)
    pb = str(np.atleast_1d(z['probe_build'])[0]) if 'probe_build' in z.files else '?'
    print('\n=== %s  (probe_build %s) ===' % (tag, pb))
    if 'V145' not in pb.upper():
        print('  \U0001f6d1 probe_build is %r, not V145 -- the 427 tap is NOT on gp-0x6c24.'
              '  Refusing to interpret.' % pb)
        return
    mt = np.abs(np.asarray(z['ab_mt']).astype(float))
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float) * 3.6
    n = min(len(mt), len(lat), len(v))
    mt, lat, v = mt[:n], lat[:n], v[:n]
    other = float((~np.isin(mt, [WIRE_SHUT, WIRE_OPEN])).mean())
    if other > 0.02:
        print('  \U0001f6d1 %.1f %% of frames are neither %d nor %d -- the tap is not reading the'
              ' gate mirror.  Refusing to interpret.' % (100 * other, WIRE_SHUT, WIRE_OPEN))
        return
    for nm, m in (('ALL', np.ones(n, bool)), ('engaged', lat > 0.5), ('manual', lat < 0.5),
                  ('engaged creep 1-24 km/h', (lat > 0.5) & (v >= 1) & (v < 24))):
        if m.sum() < 200:
            print('  %-24s only %d frames' % (nm, m.sum()))
            continue
        duty = float((mt[m] == WIRE_OPEN).mean())
        print('  %-24s n=%7d   gate OPEN duty %.4f  (%.2f %%)' % (nm, m.sum(), duty, 100 * duty))
    duty = float((mt[(lat > 0.5)] == WIRE_OPEN).mean()) if (lat > 0.5).sum() > 200 else 0.0
    print()
    if duty >= 0.02:
        print('  ✅ VERDICT: the gate OPENS (%.2f %% of engaged frames) => the retuned notch RUNS.'
              % (100 * duty))
        print('     V144/V145 are live builds, not inert ones.  If the operator also reports the')
        print('     grinding gone, the lever is confirmed; next is V142 (8x) for authority.')
    else:
        print('  \U0001f6d1 VERDICT: the gate is effectively SHUT (%.3f %% of engaged frames).'
              % (100 * duty))
        print('     => the retuned notch NEVER RUNS.  V144/V145 are INERT, not harmful.')
        print('     \U0001f6d1 Do NOT widen it: gp-0x671a >= 5 ALSO forces the b26 oscillation branch')
        print('        to -8192, which V127 found rails the inertia term, and gp-0x671a has four')
        print('        external consumers.  FALL BACK to V141 (the pump deadband).')


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a:
        print(__doc__)
        sys.exit(0)
    for t in a:
        run(t)
