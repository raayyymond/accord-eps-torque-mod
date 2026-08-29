# -*- coding: utf-8 -*-
"""The section is a TEXTBOOK notch and its parameters SEPARATE.  Design it directly.

Collapsing the decompiled form:

    H(z) = C_B4 * [ (1-C_AC) + (C_B0-C_A8) z ] / (z^2 + C_A8 z + C_AC)  +  C_B4
         = C_B4 * ( z^2 + C_B0 z + 1 ) / ( z^2 + C_A8 z + C_AC )

Three facts fall straight out, and they make the optimiser I ran unnecessary:

  1. the NUMERATOR is z^2 + C_B0 z + 1, whose roots have product 1 => the zeros are ALWAYS
     exactly on the unit circle => this is ALWAYS a true notch, at angle theta with
     2 cos(theta) = -C_B0.   f_notch = theta/(2*pi) * FS.   ** C_B0 ALONE sets it. **
  2. the DENOMINATOR z^2 + C_A8 z + C_AC is set by C_A8/C_AC ALONE => pole damping is
     INDEPENDENT of the notch frequency.  No trade-off between them at all.
  3. DC gain = C_B4 * (2 + C_B0) / (1 + C_A8 + C_AC) => C_B4 sets it exactly.

So: put the notch ON the ratchet, choose REAL well-damped poles, and solve C_B4 for unity DC.
My earlier optimiser found a 27 Hz notch with a low-pass skirt doing the work at 8.64 Hz --
that was it fighting a structure it did not understand.
"""
import struct
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 1000.0
FLY = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
V172 = dict(C_A8=-1.44508553, C_AC=0.460833013, C_B0=-1.97093439, C_B4=0.548481286)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', float(x)))[0]


def H(c, f):
    z = np.exp(2j * np.pi * np.asarray(f, float) / FS)
    return c['C_B4'] * (z ** 2 + c['C_B0'] * z + 1) / (z ** 2 + c['C_A8'] * z + c['C_AC'])


def design(f_notch, p1, p2):
    """Notch at f_notch, real poles at p1 and p2, DC gain exactly 1."""
    th = 2 * np.pi * f_notch / FS
    C_B0 = f32(-2 * np.cos(th))
    C_A8 = f32(-(p1 + p2))
    C_AC = f32(p1 * p2)
    C_B4 = f32((1 + C_A8 + C_AC) / (2 + C_B0))
    return dict(C_A8=C_A8, C_AC=C_AC, C_B0=C_B0, C_B4=C_B4)


print('verify the collapsed form against the flying coefficients:')
for f in (8.64, 21.0, 55.23):
    print('   %6.2f Hz  |H| %.6f' % (f, abs(H(FLY, f))))
print('   (55.23 Hz should be the notch: matches the -43.9 dB found by full-band scan)\n')

CANDS = [('notch 8.64, poles 0.90/0.60', 8.64, 0.90, 0.60),
         ('notch 8.64, poles 0.93/0.75', 8.64, 0.93, 0.75),
         ('notch 9.20, poles 0.90/0.60', 9.20, 0.90, 0.60),
         ('notch 9.20, poles 0.95/0.80', 9.20, 0.95, 0.80)]
print('%-30s %-9s %-9s %-9s %-9s %-9s %s'
      % ('design', 'DC', '3 Hz', '5 Hz', '8.64 Hz', '21 Hz', 'pole r'))
print('%-30s %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f %.4f'
      % ('FLYING (today)', abs(H(FLY, 0.5)), abs(H(FLY, 3)), abs(H(FLY, 5)),
         abs(H(FLY, 8.64)), abs(H(FLY, 21)), max(abs(np.roots([1, FLY['C_A8'], FLY['C_AC']])))))
print('%-30s %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f %.4f'
      % ('V172 (built)', abs(H(V172, 0.5)), abs(H(V172, 3)), abs(H(V172, 5)),
         abs(H(V172, 8.64)), abs(H(V172, 21)), max(abs(np.roots([1, V172['C_A8'], V172['C_AC']])))))
best = None
for nm, fn, p1, p2 in CANDS:
    c = design(fn, p1, p2)
    r = np.roots([1, c['C_A8'], c['C_AC']])
    print('%-30s %-9.4f %-9.4f %-9.4f %-9.4f %-9.4f %.4f'
          % (nm, abs(H(c, 0.5)), abs(H(c, 3)), abs(H(c, 5)),
             abs(H(c, 8.64)), abs(H(c, 21)), max(abs(r))))
    if nm.startswith('notch 8.64, poles 0.90'):
        best = (nm, c, r)

nm, c, r = best
print('\nCHOSEN: %s' % nm)
for k in ('C_A8', 'C_AC', 'C_B0', 'C_B4'):
    print('   %-5s %+0.9g   raw %08X' % (k, c[k], struct.unpack('<I', struct.pack('<f', c[k]))[0]))
print('   poles %s   real %s' % (np.round(r, 5), bool(np.max(np.abs(np.imag(r))) < 1e-9)))
fs = np.arange(0.5, 499, 0.25)
g, g0 = np.abs(H(c, fs)), np.abs(H(FLY, fs))
print('   min |H| %.6f at %.2f Hz (%.1f dB)'
      % (g.min(), fs[int(np.argmin(g))], 20 * np.log10(max(g.min(), 1e-12))))
print('   largest gain INCREASE vs flying: %.3fx at %.1f Hz'
      % ((g / g0).max(), fs[int(np.argmax(g / g0))]))
print('\n   across the ratchet band (7-11 Hz), vs flying and vs V172:')
for f in (7, 8, 8.64, 9.5, 10.5, 11):
    print('     %5.2f Hz   flying %.4f   V172 %.4f   CHOSEN %.4f'
          % (f, abs(H(FLY, f)), abs(H(V172, f)), abs(H(c, f))))
