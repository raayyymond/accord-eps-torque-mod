#!/usr/bin/env python3
r"""DOES CUTTING 6-9 Hz HELP OR HURT?  The damping-band floor, tested against non-rectified Re(Z).

WHAT IS AT STAKE.  The notch is the kit's one frequency-selective device, and it is FORBIDDEN from the
6-10 Hz band by a "damping-band floor" -- a build-time gate requiring |H| at 6-9 Hz to stay at or above
stock's 0.9344.  Its justification is that the lane is a REAL DAMPER there, measured as phase
cos -0.918 / -0.989 / -0.629 on 3/3 routes.

\U0001f6d1 BUT THAT PHASE CAME FROM CAN 427, AND FUN_00055d80 RECTIFIES 427.  Rectification destroys
phase at f0 -- that is established, and it is why every damps-vs-pumps sign taken from 427 is in doubt.
Meanwhile the SYSTEM measures anti-damped at 6-9 Hz (Re(Z) = -58 engaged vs -0.81 manual, 31/31 routes)
on `tq` and `cs_rate`, which are NOT rectified.

So the floor may be protecting something that is not there.  If it is, the notch -- the strongest and
best-understood lever in the kit -- could be aimed at the ratchet instead of at 22-30 Hz.

THE TEST, using only trusted data.  Flown builds carry DIFFERENT biquad coefficients.  Compute each
build's |H(7.79 Hz)| from its own `0xC60A8..0xC60B4` floats and regress against its measured
coherence-gated Re(Z) at 6-9 Hz:

    more cut at 7.79 Hz  ->  LESS anti-damping   =>  the floor is WRONG; cutting there HELPS
    more cut at 7.79 Hz  ->  MORE anti-damping   =>  the floor is RIGHT and rests on something real
    no relation                                  =>  the corpus cannot answer it and the floor stands
                                                     on its original (suspect) evidence

\U0001f6d1 CONFOUNDED like every cross-build comparison here: builds differ in more than the biquad, and
there is one route per build.  A SCREEN.  But it is a screen using a trusted instrument against a gate
whose own evidence is not trusted, which is exactly the situation where a screen is worth running.

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

import cmath
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

BQ = 0xC60A8            # a1, a2, b1, c4 as four float32
FS = 1000.0
F_RATCHET = 7.79
F_GRIND = 25.0


def biquad(build):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    p = p or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
    if not p:
        return None
    im = open(p[0], 'rb').read()
    if struct.unpack_from('<H', im, 0xC646C)[0] != 891:
        return None
    return struct.unpack_from('<ffff', im, BQ)


def mag(coeffs, f):
    """|H(f)| for c4*(1 + b1 z^-1 + z^-2)/(1 + a1 z^-1 + a2 z^-2)."""
    a1, a2, b1, c4 = coeffs
    z = cmath.exp(2j * cmath.pi * f / FS)
    num = c4 * (1 + b1 / z + 1 / (z * z))
    den = 1 + a1 / z + a2 / (z * z)
    if abs(den) < 1e-12:
        return float('nan')
    return abs(num / den)


def main():
    print('=' * 88)
    print('  DOES CUTTING 6-9 Hz HELP OR HURT?  the damping-band floor vs non-rectified Re(Z)')
    print('=' * 88)
    print()
    print('  %-6s %-6s %10s %10s %12s' % ('route', 'build', '|H|@7.79', '|H|@25', 'Re(Z) 6-9'))
    print('  ' + '-' * 54)
    rows = []
    for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
        b = BUILD[r]
        c = biquad(b)
        z = rez(r)
        if c is None or z is None:
            continue
        h8, h25 = mag(c, F_RATCHET), mag(c, F_GRIND)
        if not (np.isfinite(h8) and np.isfinite(h25)):
            continue
        rows.append((b, h8, h25, z[0]))
        print('  %-6s %-6s %10.4f %10.4f %12.2f' % (r, b, h8, h25, z[0]))
    print('  ' + '-' * 54)
    if len(rows) < 6:
        print('\n  too few builds.')
        return
    h = np.array([x[1] for x in rows])
    v = np.array([x[3] for x in rows])
    print('\n  distinct |H|@7.79 values: %s' % sorted({round(x, 4) for x in h}))
    if len({round(x, 4) for x in h}) < 2:
        print('\n  \U0001f6d1 EVERY FLOWN BUILD HAS THE SAME |H| AT 7.79 Hz -- there is NO CONTRAST, so')
        print('     this corpus CANNOT test the damping-band floor. That is not a null result: it')
        print('     means the floor has never been tested against a trusted instrument, and its')
        print('     original evidence came from the rectified channel.')
        return
    rho = stats.spearmanr(h, v)
    print('  Spearman rho(|H|@7.79, Re(Z)) = %+.3f   p %.4f   n=%d'
          % (rho.correlation, rho.pvalue, len(rows)))
    print()
    if rho.pvalue >= 0.05:
        print('  => NO RELATION. The corpus cannot adjudicate the floor; it stands on its original')
        print('     (rectified-channel) evidence, which remains in doubt.')
    elif rho.correlation > 0:
        print('  => MORE CUT AT 7.79 Hz GOES WITH LESS ANTI-DAMPING. The floor looks WRONG, and the')
        print('     notch could be aimed at the ratchet. This would be the strongest lever available.')
    else:
        print('  => MORE CUT AT 7.79 Hz GOES WITH MORE ANTI-DAMPING. The floor is protecting')
        print('     something real after all, and 6-10 Hz stays closed.')


if __name__ == '__main__':
    main()
