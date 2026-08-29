# -*- coding: utf-8 -*-
"""
PLACE THE NOTCH OVER THE BAND THE GRIND ACTUALLY OCCUPIES -- and over the gain-driven line too.

V195 fitted 19.75 Hz by minimax on cs_rate, then V199 had to NARROW the notch (r 0.9000 -> 0.9675)
to pass the max|H| <= 1.0 gate.  Narrowing shrinks coverage, so the fit is no longer optimal for the
constrained filter: the centre was chosen for a wide notch and kept for a narrow one.

Two things must be covered:
  * THE GRIND, whose per-route peak on cs_rate runs p10 16.33 / median 20.12 / p90 22.15 Hz.
  * THE GAIN-DRIVEN LINE at ~23 Hz.  The record: raising 0xC6CD0 moved the peak 20.3 -> 23.0 Hz and
    "G = 2.7-3.9x at 22-26 Hz", which is why the 8x gain was abandoned three times.

Those are the SAME loop.  The notch sits in it -- motion -> column torque -> sensor -> assist map ->
biquad -> aggregator -> motor -> motion -- so cutting loop gain across 16-23 Hz lowers the
resonance's Q no matter what excites it.  That is the mechanism by which fixing the grind is what
makes LKAS authority affordable, and it argues for covering the WHOLE band rather than one line.

Re-solve (zero, pole, radius) jointly under the same two constraints V199 respects.
"""
import os
import struct

import numpy as np

FS = 1000.0
D = os.path.join(os.environ.get('ACCORD_FIRMWARE_ROOT',
                                'C:/Users/dudei/Desktop/Projects/accord-firmwares'),
                 'analysis-2020accord')
rd = lambda f: [struct.unpack_from('<f', open(os.path.join(D, f), 'rb').read(), a)[0]
                for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]
HONDA = rd('_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin')
V199 = rd('_v199_V199-V196BASE-NOTCH.POLES.BELOW.ZEROS_plain_image.bin')

F = np.concatenate([np.linspace(0.02, 120, 12000), np.linspace(120, 500, 2000)])
i5 = int(np.argmin(np.abs(F - 5.0)))
BAND = (F >= 16.3) & (F <= 23.0)          # the grind's p10-p90 plus the gain-driven line


def resp(c, f=F):
    a1, a2, b1, g = c
    z = np.exp(2j * np.pi * f / FS)
    return g * (z * z + b1 * z + 1) / (z * z + a1 * z + a2)


def design(fz, fp, r):
    b1 = -2 * np.cos(2 * np.pi * fz / FS)
    a1 = -2 * r * np.cos(2 * np.pi * fp / FS)
    return [a1, r * r, b1, (1 + a1 + r * r) / (2 + b1)]


HH = np.abs(resp(HONDA))
phH = np.degrees(np.angle(resp(HONDA)))


def score(c):
    H = resp(c)
    m = np.abs(H)
    return (m.max(),                                    # the GATE
            np.degrees(np.angle(H))[i5] - phH[i5],      # LKAS-loop phase budget
            (m[BAND] / HH[BAND]).max(),                 # WORST leakage in the band -- minimax
            np.exp(np.mean(np.log(m[BAND] / HH[BAND]))))


print('=' * 100)
print('  MINIMAX OVER 16.3-23.0 Hz  (grind p10-p90 on cs_rate, plus the ~23 Hz gain line)')
print('=' * 100)
mx, d5, worst, geo = score(V199)
print('  V199  (zeros 19.75, poles 17.45, r 0.9675)')
print('        max|H| %.6f   phase@5Hz %+.2f   WORST leakage in band %.4f (%.1fx)   geomean %.1fx'
      % (mx, d5, worst, 1 / worst, 1 / geo))

# vectorised: 30k candidates x a 1400-point grid, in chunks
FZ = np.arange(17.0, 23.01, 0.25)
FP = np.arange(6.0, 22.8, 0.25)
RR = np.arange(0.90, 0.996, 0.005)
cand = [(a, b, c2) for a in FZ for b in FP for c2 in RR if b < a - 0.2]
A1 = np.array([-2 * c2 * np.cos(2 * np.pi * b / FS) for a, b, c2 in cand])
A2 = np.array([c2 * c2 for a, b, c2 in cand])
B1 = np.array([-2 * np.cos(2 * np.pi * a / FS) for a, b, c2 in cand])
G = (1 + A1 + A2) / (2 + B1)
Z = np.exp(2j * np.pi * F / FS)
best = None
for s0 in range(0, len(cand), 1500):
    sl = slice(s0, s0 + 1500)
    z = Z[None, :]
    H = (G[sl, None] * (z * z + B1[sl, None] * z + 1)
         / (z * z + A1[sl, None] * z + A2[sl, None]))
    M = np.abs(H)
    mx_ = M.max(axis=1)
    d5_ = np.degrees(np.angle(H[:, i5])) - phH[i5]
    lk = M[:, BAND] / HH[BAND][None, :]
    w_ = lk.max(axis=1)
    g_ = np.exp(np.mean(np.log(lk), axis=1))
    okm = (mx_ <= 1.0000001) & (np.abs(d5_) <= 3.0)
    if not okm.any():
        continue
    j = int(np.argmin(np.where(okm, w_, np.inf)))
    if best is None or w_[j] < best[0]:
        a, b, c2 = cand[s0 + j]
        best = (w_[j], g_[j], mx_[j], d5_[j], a, b, c2,
                [A1[s0 + j], A2[s0 + j], B1[s0 + j], G[s0 + j]])

w, g, m, d, fz, fp, r, c = best
print()
print('  BEST  (zeros %.2f, poles %.2f, r %.4f)' % (fz, fp, r))
print('        max|H| %.6f   phase@5Hz %+.2f   WORST leakage in band %.4f (%.1fx)   geomean %.1fx'
      % (m, d, w, 1 / w, 1 / g))
print()
print('  => worst-case leakage %.1fx better than V199 across the band the grind actually occupies'
      % (worst / w))
print()
print('  f Hz    |H| Honda   |H| V199   |H| best    V199 atten   best atten')
for f in (16.33, 18.0, 20.12, 21.0, 22.15, 23.0, 26.0):
    hh, h9, hb = abs(resp(HONDA, f)), abs(resp(V199, f)), abs(resp(c, f))
    print('   %6.2f   %9.4f  %9.4f  %9.4f   %8.1fx   %9.1fx'
          % (f, hh, h9, hb, hh / max(h9, 1e-9), hh / max(hb, 1e-9)))
print()
print('  SPEC (the formula IS the specification)')
print('    b1 = -2*cos(2*pi*%.6f/1000)        = %+.9f' % (fz, c[2]))
print('    a1 = -2*%.6f*cos(2*pi*%.6f/1000) = %+.9f' % (r, fp, c[0]))
print('    a2 = %.6f**2                        = %+.9f' % (r, c[1]))
print('    g  = (1+a1+a2)/(2+b1)                   = %+.9f' % c[3])
