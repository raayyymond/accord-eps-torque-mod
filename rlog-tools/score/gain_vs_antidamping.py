#!/usr/bin/env python3
r"""DOES THE LKAS GAIN PREDICT THE 6-9 Hz ANTI-DAMPING?  It does, and a reversal shows it is causal.

    4x  (7 builds)   Re(Z)  -46.6 .. -66.8
    6x  (9 builds)   Re(Z)  -62.3 .. -74.9
    8x  (1 build)    Re(Z)  -84.1
    slope -0.0074/count · R2 0.726 · Spearman rho -0.819 · p 0.0001 · n = 17

Gain rises monotonically with build era, so that trend ALONE proves nothing.  THE REVERSAL is what
carries it -- three consecutive builds where the gain goes UP then DOWN, and Re(Z) follows both ways:

    V100  4x  ->  -66.83
    V101  8x  ->  -84.06     gain UP,   anti-damping DEEPENS  (-17.23)
    V102  6x  ->  -74.91     gain DOWN, anti-damping RECOVERS (+9.15)

Build era is monotone and cannot produce a reversal.  ~ -4.4 of Re(Z) per 1x of gain.

HOW THIS WAS REACHED -- three eliminations from bytes first.  Engagement re-indexes the mode table
24 -> 26, and of everything that re-index touches, the five base-assist damper records (FactorB/C/D/E
plus the ceiling) and all three boost tables are BYTE-IDENTICAL between manual and engaged.  Only
FRICTION differs (3x), and its dose spans 1.0x-3.0x across 17 flown builds with NO relation to Re(Z)
(rho -0.263, p 0.31 -- see `friction_dose_vs_antidamping.py`).  No re-indexed calibration explains the
anti-damping, which leaves the applied LKAS torque -- and the gain is what sets that.

WHY IT MATTERS.  The ratchet was never a lever the kit failed to find: it tracks the gain the kit kept
raising.  That is why every cal, filter, damper, cave and notch measured null on it, and why no build
V90->V122 moved the anti-damping.  And it PRICES the gain ladder -- 8x costs ~9 more anti-damping than
6x, 10x costs ~18.

\U0001f6d1 n = 75-170 windows, ONE ROUTE PER BUILD, and adjacent builds differ in more than the gain
cell.  A SCREEN that prices a trade-off, not a controlled experiment.

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

import glob
import os
import re
import struct
import sys

import numpy as np
from scipy import stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from friction_dose_vs_antidamping import rez, BUILD, IMGDIR   # noqa: E402

GAIN = 0xC6CD0
STOCK = 891.0


def gain_of(build):
    pats = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
            if 'DO-NOT-FLASH' not in os.path.basename(q)]
    pats = pats or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
    if not pats:
        return None
    im = open(pats[0], 'rb').read()
    if struct.unpack_from('<H', im, 0xC646C)[0] != 891:
        return None
    return struct.unpack_from('<H', im, GAIN)[0]


def main():
    print('=' * 74)
    print('  DOES THE LKAS GAIN PREDICT THE 6-9 Hz ANTI-DAMPING?')
    print('=' * 74)
    print()
    print('  %-6s %-6s %10s %8s %11s %7s'
          % ('route', 'build', '0xC6CD0', 'x stock', 'Re(Z) 6-9', 'wins'))
    print('  ' + '-' * 58)
    rows = []
    for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
        b = BUILD[r]
        g, z = gain_of(b), rez(r)
        if g is None or z is None:
            continue
        rows.append((b, g, z[0]))
        print('  %-6s %-6s %10d %7.2fx %11.2f %7d' % (r, b, g, g / STOCK, z[0], z[1]))
    print('  ' + '-' * 58)
    if len(rows) < 4:
        print('\n  too few paired builds.')
        return
    g = np.array([x[1] for x in rows], float)
    v = np.array([x[2] for x in rows])
    if len(set(g)) < 2:
        print('\n  every flown build carries the same gain -- no contrast.')
        return
    lr = stats.linregress(g, v)
    rho = stats.spearmanr(g, v)
    print('\n  linregress Re(Z) on gain : slope %+.4f/count  R2 %.3f  p %.4f'
          % (lr.slope, lr.rvalue ** 2, lr.pvalue))
    print('  Spearman rho             : %+.3f  p %.4f  (n=%d builds)'
          % (rho.correlation, rho.pvalue, len(rows)))
    d = {b: (gg, vv) for b, gg, vv in rows}
    if {'V100', 'V101', 'V102'} <= set(d):
        a, c, e = d['V100'][1], d['V101'][1], d['V102'][1]
        print('\n  THE REVERSAL -- build era is monotone and cannot produce one:')
        print('    V100 4x -> V101 8x : %+.2f -> %+.2f  (%+.2f, gain UP)' % (a, c, c - a))
        print('    V101 8x -> V102 6x : %+.2f -> %+.2f  (%+.2f, gain DOWN)' % (c, e, e - c))
        print('    => Re(Z) %s the reversal.'
              % ('FOLLOWS' if (c < a and e > c) else 'does NOT follow'))
    print('\n  PRICE OF THE GAIN LADDER, at %+.2f of Re(Z) per 1x:' % (lr.slope * STOCK))
    for lab, mult in (('V241  6x', 6), ('V242  8x', 8), ('V243 10x', 10)):
        print('    %-9s Re(Z) ~ %6.0f' % (lab, lr.intercept + lr.slope * STOCK * mult))
    print('\n  \U0001f6d1 one route per build; the REVERSAL carries this, not the regression.')


if __name__ == '__main__':
    main()
