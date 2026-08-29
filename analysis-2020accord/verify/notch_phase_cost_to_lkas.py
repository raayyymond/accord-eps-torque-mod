# -*- coding: utf-8 -*-
"""
WHAT DOES THE ASSIST-SECTION NOTCH COST THE LKAS BAND?

The notch is the whole point of V195/V196, and it is the one lever on the shelf that sits INSIDE the
LKAS command path.  A notch is never free: to put a deep null at f0 you place poles near the unit
circle, and the poles' skirt extends either side of f0.  If that skirt reaches 1-5 Hz -- where the
LKAS lane actually operates, being a 1-5 Hz low-pass -- then the notch buys grind attenuation by
spending LKAS phase margin, which is the same currency that peak command oscillation is paid in.

That is not a hypothetical.  V184 put the notch at 8 Hz and cost -40.5 degrees.  V195 moved it to
19.75 Hz but ALSO widened it, from r 0.9885 to r 0.9000, and a wider notch has a wider skirt.  The
rule of thumb for the -3 dB notch width is (1-r)*fs/pi, which at r=0.9000 and fs=1000 is about 32 Hz
-- WIDER THAN THE NOTCH CENTRE ITSELF.  So this has to be computed, not assumed.

Everything here is read from the BUILT IMAGES, not from the build scripts, and the stock read is
anchored: stock's numerator must reproduce Honda's 55.226 Hz or the offsets are wrong and the script
refuses to report.

    H(z) = g * (z^2 + b1*z + 1) / (z^2 + a1*z + a2)     fs = 1000 Hz

    0xC60A8 -> a1     0xC60AC -> a2     0xC60B0 -> b1     0xC60B4 -> g
"""
import glob
import os
import struct
import sys

import numpy as np

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMGDIR = os.path.join(ROOT, 'analysis-2020accord')
FS = 1000.0
ADDR = {'a1': 0xC60A8, 'a2': 0xC60AC, 'b1': 0xC60B0, 'g': 0xC60B4}


def pick(pat):
    hits = [f for f in glob.glob(os.path.join(IMGDIR, '*plain_image.bin'))
            if pat.lower() in os.path.basename(f).lower()
            and 'SUPERSEDED' not in os.path.basename(f)]
    if not hits:
        sys.exit('no image matching ' + pat)
    return sorted(hits, key=len)[0]


def coeffs(path):
    b = open(path, 'rb').read()
    return {k: struct.unpack_from('<f', b, a)[0] for k, a in ADDR.items()}


def notch_hz(b1):
    x = -b1 / 2.0
    return float('nan') if abs(x) > 1 else np.arccos(x) * FS / (2 * np.pi)


def resp(c, f):
    z = np.exp(2j * np.pi * f / FS)
    return c['g'] * (z * z + c['b1'] * z + 1) / (z * z + c['a1'] * z + c['a2'])


# ---------------------------------------------------------------------------------------------
STOCK = pick('_v122_')          # V122 is the long-standing byte-stock-biquad reference base
V196 = pick('_v196_')
cs, cv = coeffs(STOCK), coeffs(V196)

print('=' * 92)
print('  WHAT V196 NOTCH COSTS THE LKAS BAND -- read from the built images')
print('=' * 92)
print('  base   ' + os.path.basename(STOCK)[:80])
print('  cand   ' + os.path.basename(V196)[:80])
print()
for nm, c in (('base', cs), ('V196', cv)):
    r = np.sqrt(abs(c['a2']))
    print('  %-5s a1 %+.6f  a2 %+.6f  b1 %+.6f  g %+.6f   notch %6.2f Hz  pole r %.4f'
          % (nm, c['a1'], c['a2'], c['b1'], c['g'], notch_hz(c['b1']), r))

f0s = notch_hz(cs['b1'])
if not (54.0 < f0s < 56.5):
    sys.exit('ANCHOR FAILED: base notch reads %.2f Hz, expected Honda 55.226 -- offsets are wrong'
             % f0s)
print('  [anchor OK] base numerator reproduces Honda 55.226 Hz, so the offsets are right')

# DC gain is pinned to 1 by construction; confirm it rather than assume it
for nm, c in (('base', cs), ('V196', cv)):
    dc = abs(resp(c, 1e-9))
    print('  [check] %-5s DC gain %.6f' % (nm, dc))

print()
print('  f Hz    |H| base   |H| V196    ratio      phase base   phase V196   DELTA phase')
print('  ' + '-' * 86)
worst = (0.0, 0.0)
for f in (0.5, 1, 2, 3, 4, 5, 6, 8, 10, 15, 19.75, 22, 26, 35, 45, 55.226, 70):
    hb, hv = resp(cs, f), resp(cv, f)
    pb, pv = np.degrees(np.angle(hb)), np.degrees(np.angle(hv))
    d = pv - pb
    mark = ''
    if 1 <= f <= 5:
        mark = '  <-- LKAS'
        if abs(d) > abs(worst[1]):
            worst = (f, d)
    elif 15 <= f <= 22:
        mark = '  <-- grind'
    elif abs(f - 55.226) < 0.1:
        mark = '  <-- Honda notch'
    print('  %6.2f  %9.4f  %9.4f  %8.3f    %+8.2f     %+8.2f     %+8.2f%s'
          % (f, abs(hb), abs(hv), abs(hv) / abs(hb), pb, pv, d, mark))

# group delay in the LKAS band, in ms -- the interpretable number for a control loop
fg = np.linspace(0.5, 5.0, 400)
gd = {}
for nm, c in (('base', cs), ('V196', cv)):
    ph = np.unwrap(np.angle(resp(c, fg)))
    gd[nm] = -np.gradient(ph, 2 * np.pi * fg) * 1000.0

print()
print('  GROUP DELAY ACROSS 0.5-5 Hz (ms):  base %+.2f to %+.2f     V196 %+.2f to %+.2f'
      % (gd['base'].min(), gd['base'].max(), gd['V196'].min(), gd['V196'].max()))
print('  ADDED delay at 5 Hz: %+.2f ms' % (gd['V196'][-1] - gd['base'][-1]))

# what it buys, at the grind
fgr = np.linspace(15, 22, 200)
att = np.abs(resp(cv, fgr)) / np.abs(resp(cs, fgr))
print('  GRIND BAND 15-22 Hz: V196/base gain %.4f to %.4f  (min %.1fx attenuation)'
      % (att.min(), att.max(), 1.0 / att.min()))

print()
print('=' * 92)
fw, dw = worst
VERDICT_DEG = 5.0
if abs(dw) <= 2.0:
    print('  VERDICT: the notch is FREE in the LKAS band -- worst added phase %+.2f deg at %.1f Hz.'
          % (dw, fw))
elif abs(dw) <= VERDICT_DEG:
    print('  VERDICT: MINOR cost -- worst added phase %+.2f deg at %.1f Hz, under the 5 deg bar.'
          % (dw, fw))
else:
    print('  VERDICT: THE NOTCH IS EATING LKAS PHASE -- %+.2f deg at %.1f Hz, OVER the 5 deg bar.'
          % (dw, fw))
    print('  => it buys grind attenuation with the same currency that peak command oscillation')
    print('     is paid in.  Narrow it (raise the pole radius) and re-check before flying.')
print('=' * 92)
