# -*- coding: utf-8 -*-
"""
RE-PRICE THE 8 Hz RATCHET NOTCH.

V184 put the notch at 8 Hz and was rejected on -40.5 degrees of phase.  That rejection was reasoned
under the belief that the biquad sits in the LKAS COMMAND path, where phase is tracking margin.
Decompiling FUN_000352b4 showed it sits in the BASE POWER-ASSIST path instead: the phase is spent in
the driver-assist loop, so its cost is steering FEEL, not command tracking.  That is a different
currency and the lever deserves re-pricing.

It also matters that the ratchet is TORQUE-dominant (13.5x on cs_tq vs 1.7x on cs_rate) and the
biquad's own input is the torque sensor -- so an 8 Hz notch sits directly in the ratchet's loop.  The
record calls the ratchet a PLANT resonance that "firmware cannot remove, only reduce what excites";
that is true of the mechanical mode, but cutting LOOP GAIN at the resonance lowers its effective Q,
which is a second and different way firmware can attack it.

THE HARD CONSTRAINT: there is ONE biquad and ONE zero pair.  It can serve the grind (19.75 Hz) or the
ratchet (6-9 Hz).  NOT BOTH.  So this prices the swap honestly, including what is given up.
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
V202 = rd('_v202_V202-V199BASE-POLES.15.25.WIDER.SHOULDER_plain_image.bin')

F = np.concatenate([np.linspace(0.02, 120, 12000), np.linspace(120, 500, 2000)])
RAT = (F >= 6.0) & (F <= 9.0)            # the ratchet
GR = (F >= 16.3) & (F <= 23.0)           # the grind, what a swap gives up
i1 = int(np.argmin(np.abs(F - 1.0)))
i3 = int(np.argmin(np.abs(F - 3.0)))
i5 = int(np.argmin(np.abs(F - 5.0)))
Z = np.exp(2j * np.pi * F / FS)


def resp(c, f=None):
    a1, a2, b1, g = c
    z = Z if f is None else np.exp(2j * np.pi * f / FS)
    return g * (z * z + b1 * z + 1) / (z * z + a1 * z + a2)


HH = np.abs(resp(HONDA))
phH = np.degrees(np.angle(resp(HONDA)))

FZ = np.arange(6.0, 9.51, 0.125)
FP = np.arange(2.0, 9.4, 0.125)
RR = np.arange(0.945, 0.9985, 0.0025)
cand = [(a, b, c) for a in FZ for b in FP for c in RR if b < a - 0.1]
A1 = np.array([-2 * c * np.cos(2 * np.pi * b / FS) for a, b, c in cand])
A2 = np.array([c * c for a, b, c in cand])
B1 = np.array([-2 * np.cos(2 * np.pi * a / FS) for a, b, c in cand])
G = (1 + A1 + A2) / (2 + B1)

print('=' * 100)
print('  THE 8 Hz RATCHET NOTCH, RE-PRICED  (%d candidates)' % len(cand))
print('=' * 100)
print('  V202 for reference:  6-9 Hz attenuation %.2fx   phase@5Hz %+.2f   16.3-23 Hz %.1fx'
      % (1 / np.exp(np.mean(np.log(np.abs(resp(V202))[RAT] / HH[RAT]))),
         np.degrees(np.angle(resp(V202)))[i5] - phH[i5],
         1 / np.exp(np.mean(np.log(np.abs(resp(V202))[GR] / HH[GR])))))
print()

rows = {}
for s0 in range(0, len(cand), 1200):
    sl = slice(s0, s0 + 1200)
    z = Z[None, :]
    H = (G[sl, None] * (z * z + B1[sl, None] * z + 1)
         / (z * z + A1[sl, None] * z + A2[sl, None]))
    M = np.abs(H)
    mx = M.max(axis=1)
    ph = np.degrees(np.angle(H))
    d1, d3, d5 = ph[:, i1] - phH[i1], ph[:, i3] - phH[i3], ph[:, i5] - phH[i5]
    rat = np.exp(np.mean(np.log(M[:, RAT] / HH[RAT][None, :]), axis=1))
    gr = np.exp(np.mean(np.log(M[:, GR] / HH[GR][None, :]), axis=1))
    for k in range(H.shape[0]):
        if mx[k] > 1.0000001:
            continue
        for bar in (3, 5, 8, 12, 20, 40):
            if max(abs(d1[k]), abs(d3[k]), abs(d5[k])) <= bar:
                if bar not in rows or rat[k] < rows[bar][0]:
                    rows[bar] = (rat[k], gr[k], d1[k], d3[k], d5[k], cand[s0 + k], mx[k])

print('  budget   6-9 Hz atten   16.3-23 Hz   phase @1/3/5 Hz          zeros  poles  radius')
print('  ' + '-' * 92)
for bar in (3, 5, 8, 12, 20, 40):
    if bar in rows:
        rat, gr, d1, d3, d5, (a, b, c), mx = rows[bar]
        print('  %3d deg  %10.2fx   %8.2fx   %+6.2f %+6.2f %+6.2f   %6.2f %6.2f  %.4f'
              % (bar, 1 / rat, 1 / gr, d1, d3, d5, a, b, c))
print()
if 12 in rows:
    rat, gr, d1, d3, d5, (a, b, c), mx = rows[12]
    Fg = np.linspace(0.5, 5.0, 500)
    gdH = -np.gradient(np.unwrap(np.angle(resp(HONDA, Fg))), 2 * np.pi * Fg) * 1000
    ch = [-2 * c * np.cos(2 * np.pi * b / FS), c * c,
          -2 * np.cos(2 * np.pi * a / FS), 0]
    ch[3] = (1 + ch[0] + ch[1]) / (2 + ch[2])
    gdC = -np.gradient(np.unwrap(np.angle(resp(ch, Fg))), 2 * np.pi * Fg) * 1000
    print('  BEST-AT-12deg added group delay 0.5-5 Hz: %+.2f -> %+.2f ms  (V202 is +3.80 -> +5.52)'
          % ((gdC - gdH)[0], (gdC - gdH)[-1]))
