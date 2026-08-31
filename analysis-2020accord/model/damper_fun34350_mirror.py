#!/usr/bin/env python3
r"""FUN_00034350 -> gp-0x6bd0, THE BASE-ASSIST DAMPER, MIRRORED IN INTEGER PYTHON FROM THE DECOMPILE.

WHY THIS FILE EXISTS.  The golden model does NOT implement this lane -- `assist_shaping_lanes` takes
`damping_6bd0` as a SUPPLIED input defaulting to 0, and every FactorB/FactorC/FactorE reference in the
four modules is a COMMENT.  That gap did not matter while the damper was untouched; it matters now,
because V247 and V248 both act on it and their "90 % / 181 % of requirement" figures came from a hand
LERP.  This mirrors the real arithmetic so those numbers rest on the decompiled chain and on the actual
bytes in the images, not on my calculation.

THE CHAIN, address by address (all Q10, all integer, V850 is little-endian):

    mode      = *(u8)(gp+0x63fd)                       24 DISENGAGED / 26 ENGAGED on this car (row 11)
    seed      = gp-0x698a                              MIN-clamped to <= 1024   ("FactorA")
    FactorB   = LERP(idx, 0xC9CCC[mode])               flat 1024 in all 34 records
    FactorC   = LERP(speed gp-0x6a5e, 0xC9E9C[mode])   speed dead zone: X[0]=2240, Y[0]=0
    FactorD   = LERP(idx, 0xC9DB4[mode])               flat 1024, 5 points
    FactorE   = LERP(rate  gp-0x6ac0, 0xC9F84[mode])   RATE dead zone: X[0]=60, Y[0]=0
    ceiling   = LERP(gp-0x6ac2, 0xC77A0[mode])         512 floor; gp-0x6ac2 is a kickback detector and
                                                       reads 0 in ordinary same-sign driving
    magnitude = seed * B/1024 * C/1024 * D/1024 * E/1024,  clamped to ceiling
    gp-0x6bd0 = -sign(gp-0x6abe) * magnitude           0x3469E-0x346A2: cmp r0,r11 / ble / subr r0,r8

TWO GATES THAT ZERO OR BYPASS IT, byte+decompile confirmed:
    FactorC:  if (gp-0x6a5e > 0x7d00) or (gp-0x67f4 != 1)  ->  FactorC forced to UNITY 0x400
    FactorE:  if not (gp-0x6ac0 < 0x32c9 and gp-0x6abe + 13000 <= 0x6590)  ->  the WHOLE term is 0

\U0001f6d1 LERP SEMANTICS THAT ARE EASY TO GET WRONG, and the record has been burned by both:
  * below X[0] the LERP clamps FLAT to Y[0] with a STRICT <=, so idx == X[0] clamps too;
  * above X[n-1] it clamps to Y[n-1];
  * `n` is NEVER read by the evaluator -- each factor's length is PINNED by hardcoded immediates
    (B/C/E = 4, D = 5, ceiling = 2), so adding a breakpoint is a CODE edit, not a cal edit.

Record layout: [npt u16][X i16 * npt][Y i16 * npt], Y at base + 2 + 2*npt.

Run this file directly to price the flown car against V247 and V248 from the real images.
"""
import os
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PTR_B, PTR_C, PTR_D, PTR_E, PTR_K = 0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0
NPT = {PTR_B: 4, PTR_C: 4, PTR_D: 5, PTR_E: 4, PTR_K: 2}
MODE_ENGAGED, MODE_MANUAL = 26, 24
SEED_MAX = 1024


def _u32(img, a):
    return struct.unpack_from('<I', img, a)[0]


def _i16(img, a):
    return struct.unpack_from('<h', img, a)[0]


def record(img, ptr, mode):
    """[npt][X*npt][Y*npt] -> (X, Y). npt is PINNED by immediates, not read from the record."""
    n = NPT[ptr]
    b = _u32(img, ptr + mode * 4)
    X = [_i16(img, b + 2 + 2 * i) for i in range(n)]
    Y = [_i16(img, b + 2 + 2 * n + 2 * i) for i in range(n)]
    return X, Y


def lerp(idx, X, Y):
    """Truncating LERP with flat clamps at both ends. STRICT <= at the bottom."""
    if idx <= X[0]:
        return Y[0]
    for i in range(len(X) - 1):
        if idx < X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (idx - X[i]) // (X[i + 1] - X[i])
    return Y[-1]


def damper(img, mode, speed, rate, seed=SEED_MAX, kickback=0,
           voter_ok=True, rate_signed=None):
    """gp-0x6bd0 magnitude. Returns (magnitude, {factor: value}) for inspection."""
    if rate_signed is None:
        rate_signed = rate

    # GATE: FactorE's validity/kickback window -- failing it zeroes the WHOLE term, not just FactorE
    if not (rate < 0x32c9 and rate_signed + 13000 <= 0x6590):
        return 0, {'gate': 'FactorE validity window FAILED -> whole term 0'}

    B = lerp(rate, *record(img, PTR_B, mode))
    # GATE: FactorC forced to unity above 0x7d00 or on an implausible voter
    if speed > 0x7d00 or not voter_ok:
        C = 0x400
    else:
        C = lerp(speed, *record(img, PTR_C, mode))
    D = lerp(rate, *record(img, PTR_D, mode))
    E = lerp(rate, *record(img, PTR_E, mode))
    ceiling = lerp(kickback, *record(img, PTR_K, mode))

    mag = seed
    for f in (B, C, D, E):
        mag = mag * f // 1024
    return min(mag, ceiling), {'B': B, 'C': C, 'D': D, 'E': E, 'ceiling': ceiling}


def _demo():
    FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                        r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
    import glob
    d = os.path.join(FW, 'analysis-2020accord')
    SPEED, RATE = 5120, 99          # ~80 km/h; gp-0x6ac0 in-burst, measured on-car [94,113]
    REQ = 56.0                      # counts, from Re(Z) = -65 at the measured 0.86 deg/s amplitude
    print('=' * 84)
    print('  FUN_00034350 MIRRORED -- the damper at the ratchet operating point')
    print('=' * 84)
    print('\n  speed %d counts (~%.0f km/h)   rate gp-0x6ac0 = %d counts   seed %d (max)'
          % (SPEED, SPEED / 64, RATE, SEED_MAX))
    print('  requirement to cancel Re(Z) = -65:  ~%.0f counts\n' % REQ)
    print('  %-8s %7s %7s %7s %7s %9s %11s %9s'
          % ('build', 'B', 'C', 'D', 'E', 'ceiling', 'magnitude', 'vs req'))
    print('  ' + '-' * 72)
    for tag in ('v122', 'v241', 'v246', 'v247', 'v248'):
        p = [q for q in glob.glob(os.path.join(d, '_%s_*_plain_image.bin' % tag))
             if 'DO-NOT-FLASH' not in os.path.basename(q)]
        if not p:
            continue
        img = open(p[0], 'rb').read()
        if struct.unpack_from('<H', img, 0xC646C)[0] != 891:
            continue
        mag, f = damper(img, MODE_ENGAGED, SPEED, RATE)
        if 'gate' in f:
            print('  %-8s %s' % (tag.upper(), f['gate']))
            continue
        print('  %-8s %7d %7d %7d %7d %9d %11d %8.0f%%'
              % (tag.upper(), f['B'], f['C'], f['D'], f['E'], f['ceiling'], mag, 100 * mag / REQ))
    print('  ' + '-' * 72)
    print('\n  and the MANUAL record (mode 24) on the same builds, which must not move:')
    for tag in ('v122', 'v247', 'v248'):
        p = [q for q in glob.glob(os.path.join(d, '_%s_*_plain_image.bin' % tag))
             if 'DO-NOT-FLASH' not in os.path.basename(q)]
        if not p:
            continue
        img = open(p[0], 'rb').read()
        mag, _ = damper(img, MODE_MANUAL, SPEED, RATE)
        print('     %-8s manual damper = %d counts' % (tag.upper(), mag))


if __name__ == '__main__':
    _demo()
