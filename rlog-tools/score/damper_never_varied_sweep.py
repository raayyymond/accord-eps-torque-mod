#!/usr/bin/env python3
r"""THE COMPLEMENT OF THE CENSUS: damper cells that have NEVER VARIED, priced by ARITHMETIC.

WHY THIS EXISTS.  The FDR cell census regressed every cal cell that DIFFERS between flown images
against the 6-9 Hz anti-damping, and found only the gain and Lever B.  But a correlation census is
blind to any cell that is byte-identical everywhere -- there is nothing to correlate.  V247's lever
(FactorE's rate dead zone) was exactly such a cell: stock in all 18 flown builds, and worth ~7.5x at
the ratchet operating point.  **So the census's null was never evidence about never-varied cells.**

This sweeps the complement.  It cannot use statistics -- there is no variation -- so it prices each
cell by the lane's own arithmetic at the MEASURED operating point:

    damper_magnitude = seed * (B/1024) * (C/1024) * (D/1024) * (E/1024),  clamped to the ceiling
    sign             = -sign(gp-0x6abe)                                   (so the phase is damping)

    at the ratchet:  speed ~ 5120 counts (80 km/h),  motor rate gp-0x6ac0 = 99 counts [94,113]
    requirement:     Re(Z) = -65 at the measured 0.86 deg/s band amplitude is ~56 counts of torque

Each factor is a plain Q10 multiplier, so its leverage is LINEAR and computable exactly.

\U0001f6d1 WHAT THIS IS NOT.  A cell having headroom does NOT make it safe to move.  More damping costs
LKAS authority (it opposes openpilot's own steering), and a damper large enough to matter can change
loop behaviour at frequencies other than the one it was aimed at -- GATE 2.  This ranks HEADROOM, not
desirability, and nothing here should be built before V247 has flown and shown the direction works.

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
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMGDIR = os.path.join(FW, 'analysis-2020accord')
MODE_ENG, MODE_MAN = 26, 24
PTR = {'FactorB': (0xC9CCC, 4), 'FactorC': (0xC9E9C, 4), 'FactorD': (0xC9DB4, 5),
       'FactorE': (0xC9F84, 4), 'ceiling': (0xC77A0, 2)}
SPEED_OP = 5120.0        # counts, ~80 km/h -- engaged cruising
RATE_OP = 99.0           # gp-0x6ac0 in-burst, measured on-car [94,113]
SEED = 1024.0            # gp-0x698a, MIN-clamped to <= 1024
REQUIREMENT = 56.0       # counts, from Re(Z) = -65 at the measured 0.86 deg/s band amplitude
FLOWN = ['V90', 'V91', 'V94', 'V96', 'V97', 'V98', 'V99', 'V100', 'V101', 'V102',
         'V103', 'V104', 'V105', 'V106', 'V107', 'V111', 'V112', 'V122']


def image(b):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % b.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    p = p or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % b.lower()))
    if not p:
        return None
    im = open(p[0], 'rb').read()
    return im if struct.unpack_from('<H', im, 0xC646C)[0] == 891 else None


def rec(im, ptr, mode, npt):
    b = struct.unpack_from('<I', im, ptr + mode * 4)[0]
    X = [struct.unpack_from('<h', im, b + 2 + 2 * i)[0] for i in range(npt)]
    Y = [struct.unpack_from('<h', im, b + 2 + 2 * npt + 2 * i)[0] for i in range(npt)]
    return b, X, Y


def lerp(v, X, Y):
    if v <= X[0]:
        return float(Y[0])
    for i in range(len(X) - 1):
        if v < X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (v - X[i]) / (X[i + 1] - X[i])
    return float(Y[-1])


def main():
    print('=' * 88)
    print('  NEVER-VARIED DAMPER CELLS, PRICED BY ARITHMETIC AT THE RATCHET OPERATING POINT')
    print('=' * 88)

    base = image('V122')
    if base is None:
        print('  no readable base image.')
        return

    # which damper records have varied across the flown corpus?
    varied = {}
    for name, (ptr, npt) in PTR.items():
        seen = set()
        for b in FLOWN:
            im = image(b)
            if im is None:
                continue
            _, X, Y = rec(im, ptr, MODE_ENG, npt)
            seen.add((tuple(X), tuple(Y)))
        varied[name] = len(seen) > 1

    print('\n  has each damper record VARIED across the %d flown builds?' % len(FLOWN))
    for name in PTR:
        print('     %-9s %s' % (name, 'VARIED (census could see it)' if varied[name]
                                else 'NEVER VARIED -- invisible to the census'))

    _, BX, BY = rec(base, *PTR['FactorB'][:1], MODE_ENG, PTR['FactorB'][1]) if False else \
        rec(base, PTR['FactorB'][0], MODE_ENG, PTR['FactorB'][1])
    _, CX, CY = rec(base, PTR['FactorC'][0], MODE_ENG, PTR['FactorC'][1])
    _, DX, DY = rec(base, PTR['FactorD'][0], MODE_ENG, PTR['FactorD'][1])
    _, EX, EY = rec(base, PTR['FactorE'][0], MODE_ENG, PTR['FactorE'][1])
    _, KX, KY = rec(base, PTR['ceiling'][0], MODE_ENG, PTR['ceiling'][1])

    B = lerp(RATE_OP, BX, BY)         # B/D indices are not the rate axis, but both are FLAT
    C = lerp(SPEED_OP, CX, CY)
    D = lerp(RATE_OP, DX, DY)
    E = lerp(RATE_OP, EX, EY)
    ceil_now = KY[0]                  # kickback index is 0 in ordinary driving -> clamps to Y[0]

    def magnitude(b=B, c=C, d=D, e=E):
        return min(SEED * (b / 1024) * (c / 1024) * (d / 1024) * (e / 1024), ceil_now)

    now = magnitude()
    print('\n  the damper at the ratchet operating point (speed %.0f counts, rate %.0f counts):'
          % (SPEED_OP, RATE_OP))
    print('     FactorB %7.1f   FactorC %7.1f   FactorD %7.1f   FactorE %7.1f   ceiling %d'
          % (B, C, D, E, ceil_now))
    print('     magnitude = %.1f counts        REQUIREMENT to cancel Re(Z) = -65 is ~%.0f counts'
          % (now, REQUIREMENT))
    print('     headroom to the ceiling: %.1fx' % (ceil_now / max(now, 1e-9)))

    print('\n  WHAT EACH NEVER-VARIED FACTOR IS WORTH, one at a time:')
    print('  %-34s %10s %10s %9s' % ('lever', 'new mag', 'vs now', 'vs req'))
    print('  ' + '-' * 68)
    E247 = lerp(RATE_OP, [12, EX[1], EX[2], EX[3]], [EY[0], EY[2], EY[2], EY[3]])
    cands = [
        ('V247: FactorE X[0]=12, Y[1]:=Y[2]', magnitude(e=E247)),
        ('FactorB flat 1024 -> 2048', magnitude(b=2048)),
        ('FactorD flat 1024 -> 2048', magnitude(d=2048)),
        ('FactorC Y[2] %d -> %d (:=Y[3])' % (CY[2], CY[3]), magnitude(c=float(CY[3]))),
        ('V247 + FactorB 2048', magnitude(b=2048, e=E247)),
        ('V247 + FactorB 2048 + FactorD 2048', magnitude(b=2048, d=2048, e=E247)),
    ]
    for lab, val in cands:
        print('  %-34s %10.1f %9.1fx %8.0f%%' % (lab, val, val / max(now, 1e-9),
                                                 100 * val / REQUIREMENT))
    print('  ' + '-' * 68)
    print('\n  READING')
    print('  FactorB and FactorD are FLAT Q10 gains at unity -- pure multipliers with linear leverage')
    print('  and no shape to corrupt. They have NEVER been moved, so the census was blind to them, and')
    print('  they sit behind the same ceiling that leaves V247 %.0fx of headroom.'
          % (ceil_now / max(magnitude(e=E247), 1e-9)))
    print('\n  \U0001f6d1 HEADROOM IS NOT PERMISSION. More damping costs LKAS authority (it opposes')
    print('     openpilot\'s own steering: %.0f counts is %.1f%% of the 3072 forward clamp), and a large'
          % (magnitude(e=E247), 100 * magnitude(e=E247) / 3072))
    print('     damper can change loop behaviour away from the band it was aimed at -- GATE 2.')
    print('     BUILD NOTHING HERE until V247 has flown and shown the direction works.')


if __name__ == '__main__':
    main()
