#!/usr/bin/env python3
r"""EVERY LANE THAT IS STRUCTURALLY *OFF* AT THE OPERATING POINT.  The pattern that hid the damper.

WHY THIS SWEEP.  Two blind spots produced V247/V249, and neither was a subtle statistical issue:

  * the FDR cell census can only test cells that VARIED across flown builds, and all five base-assist
    damper records are byte-stock in all 18 -- so the census said nothing about them at all;
  * the damper was not weak or mistuned, it was OFF: `FactorC Y[0] = 0` below 35 km/h and
    `FactorE Y[0] = 0` below 60 counts of rate, and zero x anything = 0.

That second point is a MECHANICAL SIGNATURE, not a judgement call:

    a lane whose LERP value at the operating point is a trivial FRACTION of its own range is
    STRUCTURALLY STARVED where the symptom lives -- scaling it is near-vacuous, and only
    reshaping the curve delivers.

🛑 THE FIRST VERSION OF THIS TEST WAS WRONG AND RETURNED ZERO HITS.  It looked for the
operating point BELOW X[0], but FactorE's problem is the opposite: 99 counts sits just PAST the
dead-zone edge of 60, on the first rising segment, where the curve has climbed to only 16 of 927.
"Below the dead zone" misses that entirely; "fraction of the lane's own range" catches it.

This sweeps every pointer-array-referenced LERP record in the calibration region for that signature,
on the ENGAGED mode, and reports which lanes are off at the ratchet's measured operating point.

\U0001f6d1 WHAT A HIT IS AND IS NOT.  A hit means "this lane contributes exactly zero at the operating
point, and scaling it is structurally vacuous".  It does NOT mean the lane is worth opening -- that
needs the lane's SIGN (a lane that pumps is better left off) and its reachable magnitude.  The damper
was worth opening because it opposes the motion BY CONSTRUCTION.  Most lanes will not have that
property, and opening a pumping lane would make the symptom worse.

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
MODE_ENG = 26

# pointer array -> (npt, axis, label, the operating-point value on that axis)
ARRAYS = {
    0xC9CCC: (4, 'rate  gp-0x6ac0', 'damper FactorB', 99),
    0xC9E9C: (4, 'speed gp-0x6a5e', 'damper FactorC', 5120),
    0xC9DB4: (5, 'rate  gp-0x6ac0', 'damper FactorD', 99),
    0xC9F84: (4, 'rate  gp-0x6ac0', 'damper FactorE', 99),
    0xC77A0: (2, 'kickback 6ac2',   'damper ceiling', 0),
    0xCA154: (6, 'speed gp-0x6a5e', 'boost curve',    5120),
    0xCA4F4: (6, 'torque amp',      'boost amp y1',   400),
    0xCA23C: (6, 'torque amp',      'boost amp y4',   400),
    0xCBE74: (3, 'torque',          'friction lane',  400),
    0xC7970: (2, 'voter max',       'assist ceiling', 512),
}


def image(tag):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % tag))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    p = p or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % tag))
    return open(p[0], 'rb').read() if p else None


def record(img, ptr, mode, n):
    b = struct.unpack_from('<I', img, ptr + mode * 4)[0]
    if not (0 < b < len(img) - 2 - 4 * n):
        return None, None, b
    X = [struct.unpack_from('<h', img, b + 2 + 2 * i)[0] for i in range(n)]
    Y = [struct.unpack_from('<h', img, b + 2 + 2 * n + 2 * i)[0] for i in range(n)]
    return X, Y, b


def lerp(v, X, Y):
    """Truncating LERP with flat clamps at both ends -- the evaluator's own semantics."""
    if v <= X[0]:
        return float(Y[0])
    for i in range(len(X) - 1):
        if v < X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (v - X[i]) / (X[i + 1] - X[i])
    return float(Y[-1])


STARVED = 0.05          # under 5 % of the lane's own range == structurally starved


def main():
    print('=' * 92)
    print('  STARVED-LANE SWEEP -- how much of each lane is available at the operating point?')
    print('=' * 92)
    car = image('v122')
    v249 = image('v249')
    if car is None:
        print('  no readable image.')
        return
    print('\n  a lane running at a trivial FRACTION of its own range at the operating point is')
    print('  structurally starved there: scaling it is near-vacuous, only reshaping delivers.\n')
    print('  %-16s %-17s %8s %10s %9s %9s  %s'
          % ('lane', 'axis', 'op pt', 'LERP(op)', 'max|Y|', 'fraction', 'status'))
    print('  ' + '-' * 88)
    hits = []
    for ptr, (n, axis, label, op) in sorted(ARRAYS.items(), key=lambda kv: kv[1][2]):
        X, Y, b = record(car, ptr, MODE_ENG, n)
        if X is None:
            print('  %-16s %-17s  unreadable @0x%05X' % (label, axis, b))
            continue
        v = lerp(op, X, Y)
        mx = max(abs(y) for y in Y) or 1
        fr = abs(v) / mx
        tag = '<== STRUCTURALLY STARVED' if fr < STARVED else ''
        print('  %-16s %-17s %8d %10.1f %9d %8.1f%%  %s' % (label, axis, op, v, mx, 100 * fr, tag))
        if fr < STARVED:
            hits.append((label, ptr, n, op, fr))
    print('  ' + '-' * 88)

    print('\n  STRUCTURALLY STARVED LANES: %d' % len(hits))
    for label, ptr, n, op, fr in hits:
        line = '     %-16s %.1f %% of its range at the operating point' % (label, 100 * fr)
        if v249 is not None:
            X, Y, _ = record(car, ptr, MODE_ENG, n)
            X2, Y2, _ = record(v249, ptr, MODE_ENG, n)
            f2 = abs(lerp(op, X2, Y2)) / (max(abs(y) for y in Y2) or 1)
            line += '  ->  %.1f %% on V249%s' % (100 * f2,
                                                 '' if f2 > fr else '   \U0001f6d1 NOT ADDRESSED')
        print(line)
    if not hits:
        print('     none -- every lane runs at a meaningful fraction of its range here.')
    print('\n  \U0001f6d1 STARVED IS NOT A RECOMMENDATION. It means the lane contributes almost')
    print('     nothing and cannot be scaled into life. Opening it needs the lane SIGN -- the damper')
    print('     was safe because it opposes the motion BY CONSTRUCTION. Opening a lane that PUMPS at')
    print('     6-9 Hz would make the ratchet WORSE.')


if __name__ == '__main__':
    main()
