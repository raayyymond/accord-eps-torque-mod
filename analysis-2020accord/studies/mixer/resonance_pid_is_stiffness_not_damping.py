# -*- coding: utf-8 -*-
"""AT 7.79 Hz THE RESONANCE PID IS ALMOST PURE PROPORTIONAL -- i.e. STIFFNESS, not damping.

Having priced whether V227's bound binds, the next question is what the lane DOES at the ratchet's
frequency. That is computable from the same cals, and the answer changes what V227 should be expected
to do.

    out = 0.25*err + 2*d(err) + I/32           (from the shifts, Kout = unity)
    I accumulates 0.0957*err per ms

For a sinusoidal err of amplitude A at f, sampled at 1 kHz:

    P term   0.25*A                     at    0 deg
    D term   2 * (2*pi*f/1000) * A      at  +90 deg
    I term   (0.0957/(2*pi*f/1000))*A/32 at  -90 deg      (an integrator: magnitude falls as 1/f)

At f = 7.79 Hz that is P 0.2500, D 0.0979, I 0.0612 -- and D and I are ANTIPHASE, so they largely
cancel, leaving 0.0367 of net lead against 0.2500 of in-phase term.

    => |out| = 0.2527 * A  at  +8.4 deg

--------------------------------------------------------------------------------------------------
WHY THAT MATTERS
--------------------------------------------------------------------------------------------------
`err` is a TORQUE error (gp-0x4f60 minus the reference), so a response IN PHASE WITH err is a
stiffness-like term acting on that error, not a damping term acting on velocity. Only the +90 deg
part behaves like damping against a torque that leads velocity, and at 7.79 Hz that part is
0.0367/0.2527 = 14.5 % of the lane's output.

=> [EVIDENCE, from the cals] at the ratchet's frequency this lane is ~85 % stiffness-like and ~15 %
   lead. Raising its authority mostly buys STIFFER TRACKING OF THE TORQUE ERROR, which is not the
   same thing as damping the mechanical mode -- and stiffening a loop around a lightly-damped
   resonance is a recognised way to make the resonance MORE prominent, not less.

=> CONSEQUENCE FOR V227: the "more authority might damp the ratchet" reading was optimistic. The
   honest expectation is that V227 mostly increases a stiffness-like term, and the case for it is now
   "this is the one lane never scored, and the drive settles it", NOT "this should damp it".

=> AND THE INTEGRATOR IS ONLY 24 % OF THE OUTPUT at 7.79 Hz (0.0612 of 0.2527), partially cancelling
   D. So V227's anti-windup effect -- letting the integrator run longer -- moves the phase by a small
   amount, LESS than the earlier note implied. Both of V227's mechanisms are weaker at the ratchet
   frequency than they look at DC.

🛑 THIS DOES NOT RETIRE V227. The lane is still the one nobody has scored, the arithmetic above is
open-loop and says nothing about what the closed loop does with it, and a 15 % lead component acting
through an unknown plant transfer can still matter. It DOES mean V227 must be described as an
EXPERIMENT rather than as a candidate fix.

Run:  python analysis-2020accord/studies/mixer/resonance_pid_is_stiffness_not_damping.py
"""
import numpy as np

KP, KI, KD, KOUT = 256, 98, 2048, 1024
FS = 1000.0
P = (KP / 1024.0) * (KOUT / 1024.0)                      # 0.25, in phase with err
D_COEFF = (KD / 1024.0) * (KOUT / 1024.0)                # 2, multiplies d(err)
I_STEP = KI / 1024.0                                     # per-sample integrator gain


def terms(f):
    w = 2 * np.pi * f / FS
    return P, D_COEFF * w, (I_STEP / w) / 32.0


print('=' * 90)
print('  THE RESONANCE PID AT THE RATCHET FREQUENCY -- stiffness or damping?')
print('=' * 90)
print()
print('  %8s %10s %10s %10s %12s %10s %14s'
      % ('f (Hz)', 'P (0deg)', 'D (+90)', 'I (-90)', '|out|/A', 'phase', 'lead fraction'))
rows = {}
for f in (2.0, 5.0, 7.79, 12.0, 20.0):
    p, d, i = terms(f)
    quad = d - i
    mag = float(np.hypot(p, quad))
    ph = float(np.degrees(np.arctan2(quad, p)))
    rows[f] = (p, d, i, mag, ph, abs(quad) / mag)
    print('  %8.2f %10.4f %10.4f %10.4f %12.4f %9.1f%s %13.1f%%'
          % (f, p, d, i, mag, ph, 'deg', 100 * abs(quad) / mag))
print()
p, d, i, mag, ph, lead = rows[7.79]
print('  at 7.79 Hz: D and I are ANTIPHASE and largely cancel (%.4f vs %.4f), leaving %.4f of net'
      % (d, i, d - i))
print('  lead against %.4f in phase with err => the lane is %.1f%% stiffness-like.'
      % (p, 100 * (1 - lead)))
print('  the INTEGRATOR is %.0f%% of the output magnitude -- so V227\'s anti-windup effect is'
      % (100 * i / mag))
print('  smaller at 7.79 Hz than at DC, where an integrator dominates.')

# --------------------------------- assertions -----------------------------------------
assert rows[7.79][5] < 0.25, 'the lead fraction at the ratchet must be small -- that is the finding'
assert rows[7.79][2] < rows[7.79][1], 'I must be SMALLER than D at 7.79 Hz, so they partly cancel'
# the integrator equals P at (I_STEP/32)/P rad/sample -- find it rather than assume a band
f_cross = (I_STEP / 32.0 / P) * FS / (2 * np.pi)
print('  the integrator equals the P term at %.2f Hz, and is below it everywhere above that --'
      % f_cross)
print('  i.e. it dominates only BELOW the LKAS command band, never at the ratchet.')
assert 1.5 < f_cross < 2.5, 'the I/P crossover must sit near 2 Hz'
assert f_cross < 7.79, 'and well below the ratchet, which is why I is minor there'
assert rows[20.0][1] > rows[20.0][2] * 5, 'D must dominate I well above the ratchet'
assert abs(rows[7.79][3] - 0.2527) < 0.005, 'the 7.79 Hz magnitude must land where the docstring says'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] at 7.79 Hz the lane is ~85 % stiffness-like; raising it buys stiffer tracking')
print('             of a torque error, which is not damping of the mechanical mode.')
print('  [NOTE]     open-loop only. It does NOT retire V227 -- it reclassifies it from candidate fix')
print('             to experiment on the one lane nobody has scored.')
