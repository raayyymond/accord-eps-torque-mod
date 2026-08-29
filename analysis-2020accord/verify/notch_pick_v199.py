# -*- coding: utf-8 -*-
"""
PICK THE CORRECTED NOTCH, AND SHOW WHY V196's MUST NOT FLY.

Two facts from the record set the frame:

1. `0xC649B` 0->1 ALONE IS INERT -- "the real arm is gp-0x671a >= 5, never observed true across
   255,292 engaged frames on three builds (V64/V67/V68)".  So HONDA SHIPS THIS BIQUAD DORMANT.  The
   car ran H = 1 at every frequency for its whole life until V103 armed it engaged-only on the LKAS
   flag gp-0x6806.  Honda's 55.2 Hz null is therefore not a protection Honda relies on at this
   operating point -- it is a filter for a hard-reversal condition that never occurs.

2. V103's own GATE 2, quoted from the lineage: "|H| <= 1.000032 everywhere 0.1-500 Hz => the filter
   can only REMOVE loop gain, never add it".  That is the gate that licensed arming it at all.

=> the binding constraint is max|H| <= 1.0 over 0-500 Hz, ABSOLUTE.  A filter that satisfies it is
   never worse than the car's own stock behaviour at any frequency.  V196's notch scores 1.7175 and
   FAILS -- it adds loop gain above ~30 Hz, which is precisely what GATE 2 exists to forbid.

The car currently runs armed-Honda when engaged, so the DELTA vs Honda is what the operator would
feel change.  Pick: maximise 18-21 Hz attenuation subject to the absolute gate and a 3 degree cap on
added LKAS-band phase, the currency peak command oscillation is paid in.
"""
import os
import struct

import numpy as np

FS = 1000.0
ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
D = os.path.join(ROOT, 'analysis-2020accord')
HB = open(os.path.join(D, '_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin'),
          'rb').read()
VB = open(os.path.join(D, '_v196_V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE_plain_image.bin'),
          'rb').read()
rd = lambda b: [struct.unpack_from('<f', b, a)[0] for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]
HONDA, V196 = rd(HB), rd(VB)

F = np.concatenate([np.linspace(0.05, 100, 4000), np.linspace(100, 500, 1000)])
GR = (F >= 18) & (F <= 21)
i5 = int(np.argmin(np.abs(F - 5.0)))
FZ = 19.75


def resp(c, f=F):
    a1, a2, b1, g = c
    z = np.exp(2j * np.pi * f / FS)
    return g * (z * z + b1 * z + 1) / (z * z + a1 * z + a2)


def design(fp, r):
    b1 = -2 * np.cos(2 * np.pi * FZ / FS)
    a1 = -2 * r * np.cos(2 * np.pi * fp / FS)
    a2 = r * r
    return [a1, a2, b1, (1 + a1 + a2) / (2 + b1)]


HH = resp(HONDA)
phH = np.degrees(np.angle(HH))


def score(c):
    H = resp(c)
    m = np.abs(H)
    return (m.max(),
            np.degrees(np.angle(H))[i5] - phH[i5],
            1.0 / np.exp(np.mean(np.log(m[GR] / np.abs(HH)[GR]))))


print('=' * 98)
print('  %-26s %10s %14s %16s' % ('design', 'max|H|', 'd phase @5Hz', '18-21Hz atten'))
print('  ' + '-' * 90)
mx, d5, at = score(V196)
print('  %-26s %10.4f %13.2f deg %14.1fx   <-- FAILS the <=1.0 gate' % ('V196 (poles AT zeros)',
                                                                       mx, d5, at))
best = None
for fp in np.arange(6.0, 19.75, 0.05):
    for r in np.arange(0.86, 0.999, 0.0025):
        c = design(fp, r)
        mx, d5, at = score(c)
        if mx > 1.0 or abs(d5) > 3.0:
            continue
        if best is None or at > best[0]:
            best = (at, mx, d5, fp, r, c)

at, mx, d5, fp, r, c = best
print('  %-26s %10.6f %13.2f deg %14.1fx   <-- V199, poles BELOW zeros'
      % ('V199 (poles %.2f Hz)' % fp, mx, d5, at))
print('=' * 98)
print()
print('  V199 SPECIFICATION -- THE FORMULA IS THE SPECIFICATION (float-spec rule)')
print('    zeros  %.6f Hz exactly on the unit circle (a TRUE null)' % FZ)
print('    poles  %.6f Hz   radius %.6f   STABLE (r < 1)' % (fp, r))
print('      b1 = -2*cos(2*pi*%.6f/1000)            = %+.9f' % (FZ, c[2]))
print('      a1 = -2*%.6f*cos(2*pi*%.6f/1000)  = %+.9f' % (r, fp, c[0]))
print('      a2 = %.6f**2                            = %+.9f' % (r, c[1]))
print('      g  = (1+a1+a2)/(2+b1)                       = %+.9f' % c[3])
print('    little-endian float32 bytes:')
for nm, a, v in (('a1', 0xC60A8, c[0]), ('a2', 0xC60AC, c[1]),
                 ('b1', 0xC60B0, c[2]), ('g ', 0xC60B4, c[3])):
    by = struct.pack('<f', np.float32(v))
    print('      0x%05X  %s  %s   round-trip %+.9f'
          % (a, nm, by.hex(), struct.unpack('<f', by)[0]))
print()
print('  RESPONSE, V199 vs the armed-Honda filter the car runs now')
print('    f Hz    |H| Honda   |H| V199    ratio     d phase')
for f in (1, 3, 5, 8, 12, 16, 18, 19.75, 21, 26, 35, 45, 55.226, 70, 120):
    hh, hv = resp(HONDA, f), resp(c, f)
    print('   %6.2f   %9.4f  %9.4f  %8.4f   %+7.2f deg'
          % (f, abs(hh), abs(hv), abs(hv) / abs(hh),
             np.degrees(np.angle(hv)) - np.degrees(np.angle(hh))))
print()
print('  GATE 2 (V103s own): max|H| = %.6f <= 1.0 over 0-500 Hz' % np.abs(resp(c)).max())
print('    => V199 can only REMOVE loop gain, never add it, at EVERY frequency.')
print('    => V196 scores 1.7175 and cannot make that statement.')
