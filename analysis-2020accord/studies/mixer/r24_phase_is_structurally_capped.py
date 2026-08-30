# -*- coding: utf-8 -*-
"""r24 CAN NEVER BE A PURE DAMPER, AND THE SPAN CAL IS NOT A NEW LEVER. Two closures.

Having established (a) that r24's phase vs rate is +143.7 deg and (b) via V88's on-car A/B that r24's
side is the beneficial one, the obvious next question is whether r24 can be rotated CLOSER to a pure
damper (180 deg from rate), and whether the span cal 0xC6C42 -- never moved in this kit's history -- is
the way to do it.

Both answers are no, and both are structural rather than empirical.

CLOSURE 1 -- THE PHASE IS CAPPED BY THE SHAPE OF A FINITE DIFFERENCE.

    r24 = -(cal/1024) * (1 - exp(-j*w*N*0.001)) * T          N = cal(0xC6C42), 1 kHz task
    arg(1 - exp(-j*w*N*dt)) = 90 - (w*N*dt/2)                <= +90 deg, ALWAYS, for any N > 0

The lead a finite difference can contribute is bounded above by +90 deg and only approaches it as
N -> 0, where the gain also -> 0. With torque measured at -120.7 deg and the gp-0x6752 polarity
contributing +180:

    r24 phase = -120.7 + arg(H) + 180  <=  -120.7 + 90 + 180 = +149.3 deg

=> r24 CANNOT reach 180 deg. Its work factor is capped at |cos(149.3)| = 0.860, and at the shipped
   N = 4 it is already 0.806 -- i.e. the lane is at 94 % of its own structural ceiling.
=> at least 14 % of r24's output is REACTIVE at the ratchet no matter what any calibration does.
   Rotating it further would need a transfer with more than 90 deg of lead (a second derivative, or a
   lead-lag network). NO SUCH CAL EXISTS ON THIS LANE.

CLOSURE 2 -- THE SPAN CAL IS A REDUNDANT GAIN KNOB WITH A CLIFF, NOT A PHASE LEVER.

Across the entire usable range N = 1..7 the phase moves only 147.9 -> 139.5 deg, 8.4 deg total, while
the magnitude moves 0.049 -> 0.341, a factor of 7. So the span cal is 91 % magnitude and 9 % phase: it
does the same job as Lever B (0xC6446) and nothing Lever B cannot do.

    N   |H|      phase      work    damping counts (at V222's cal, median |T|)
    4   0.19547  +143.7    -0.806   376.4      <- shipped, and shipped on 218 of 219 images
    7   0.34095  +139.5    -0.760   619.4      = 1.65x, purely from magnitude

And it is the WORSE of the two ways to buy that magnitude:
  * N = 8 SILENTLY ZEROES the lane, killing r24 AND r26 together. The optimum sits ONE STEP from a
    double kill-switch with no fault, no DTC and no symptom other than losing the kit's best lever.
  * N is SHARED with r26, so its blast radius is strictly wider than Lever B's.
  * Lever B has headroom to 65535 (12.5x above the car) with the only bound a +-8192 rail, and no
    neighbouring value does anything catastrophic.

=> RECOMMENDATION: do NOT propose 0xC6C42 as a lever. Buy magnitude with Lever B, which is already the
   plan (V221/V222 -> 13107, V223 -> 26214). This file exists so the span cal is not re-proposed.

Run:  python analysis-2020accord/studies/mixer/r24_phase_is_structurally_capped.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

F = 7.79
W = 2 * np.pi * F
PHI_T = -120.7
DT = 1e-3
CAL_V222 = 13107
T_MED = 186.7
DEG = u'\N{DEGREE SIGN}'


def wrap(a):
    return ((a + 180.0) % 360.0) - 180.0


def lane(N, cal=CAL_V222):
    H = 1.0 - np.exp(-1j * W * N * DT)
    ph = wrap(PHI_T + np.degrees(np.angle(H)) + 180.0)
    w = float(np.cos(np.radians(ph)))
    return abs(H), float(np.degrees(np.angle(H))), ph, w, abs(H) * (-w) * T_MED * cal / 1024.0


print('=' * 94)
print('  r24 PHASE IS STRUCTURALLY CAPPED, AND THE SPAN CAL IS NOT A NEW LEVER')
print('=' * 94)
print()
print('  %3s %9s %10s %11s %9s %14s %9s'
      % ('N', '|H|', 'arg H', 'phase', 'work', 'damping ct', 'vs N=4'))
rows = {}
for N in range(1, 8):
    rows[N] = lane(N)
    m, a, ph, w, dmp = rows[N]
    print('  %3d %9.5f %+9.2f%s %+10.1f%s %+8.3f %14.1f %8s'
          % (N, m, a, DEG, ph, DEG, w, dmp, ''))
base = rows[4][4]
print()
for N in range(1, 8):
    print('    N=%d  damping %7.1f ct   %+5.2fx vs shipped N=4%s'
          % (N, rows[N][4], rows[N][4] / base, '   <- SHIPPED' if N == 4 else ''))

# ---------------------------- closure 1: the cap -----------------------------------------
cap_phase = wrap(PHI_T + 90.0 + 180.0)
cap_work = abs(np.cos(np.radians(cap_phase)))
print()
print('  ' + '-' * 90)
print('  CLOSURE 1 -- the phase is capped by the shape of a finite difference')
print('  ' + '-' * 90)
print('    arg(1 - exp(-j*w*N*dt)) = 90 - w*N*dt/2  <=  +90%s for ANY N > 0' % DEG)
print('    => r24 phase <= %.1f%s + 90%s + 180%s = %+.1f%s   (180%s would be a PURE damper)'
      % (PHI_T, DEG, DEG, DEG, cap_phase, DEG, DEG))
print('    => work factor capped at %.3f; shipped N=4 already achieves %.3f = %.0f%% of the ceiling'
      % (cap_work, abs(rows[4][3]), 100 * abs(rows[4][3]) / cap_work))
print('    => >= %.0f%% of r24 is REACTIVE at the ratchet under ANY calibration.'
      % (100 * (1 - cap_work)))
print('    Rotating further needs >90%s of lead -- a second derivative or a lead-lag. No such cal' % DEG)
print('    exists on this lane.')

# ---------------------------- closure 2: the knob ----------------------------------------
ph_span = abs(rows[1][2] - rows[7][2])
mag_span = rows[7][0] / rows[1][0]
print()
print('  ' + '-' * 90)
print('  CLOSURE 2 -- 0xC6C42 is a redundant GAIN knob with a cliff, not a phase lever')
print('  ' + '-' * 90)
print('    across the whole usable range N=1..7: phase moves %.1f%s, magnitude moves %.1fx'
      % (ph_span, DEG, mag_span))
print('    => %.0f%% magnitude, %.0f%% phase. It does Lever B\'s job and nothing else.'
      % (100 * (1 - ph_span / 90.0), 100 * ph_span / 90.0))
print()
print('    and it is the WORSE way to buy that magnitude:')
print('      * N=8 SILENTLY ZEROES the lane, killing r24 AND r26 -- the optimum N=7 sits ONE STEP')
print('        from a double kill-switch, with no fault and no DTC to announce it')
print('      * N is SHARED with r26 => strictly wider blast radius than Lever B')
print('      * Lever B has 12.5x headroom, bounded only by a +-8192 rail, no dangerous neighbour')

assert rows[4][3] < 0 and abs(rows[4][3]) / cap_work > 0.9, \
    'shipped N=4 must already be within 10% of the structural ceiling -- that is closure 1'
assert ph_span < 10.0, 'the phase must barely move across N, or the span IS a phase lever'
assert mag_span > 5.0, 'the magnitude must move a lot across N, or it is not a gain knob either'
assert rows[7][4] > rows[4][4], 'N=7 must still be the in-range optimum, or the framing is wrong'
print()
print('  all four assertions hold.')
print('  [EVIDENCE] r24 is at 94% of a structural phase ceiling it cannot pass; the span cal moves')
print('             magnitude, not phase, and its optimum is adjacent to a double kill-switch.')
print('  [ACTION]   do NOT propose 0xC6C42. Buy magnitude with Lever B, which is already the plan.')
print('  [LIMIT]    open-loop, and PHI_T = %.1f%s is a measured median; the cap argument is'
      % (PHI_T, DEG))
print('             insensitive to it (the +90%s bound on a difference holds for any input phase).' % DEG)
