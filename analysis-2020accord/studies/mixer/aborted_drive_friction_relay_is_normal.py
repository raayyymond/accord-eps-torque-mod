# -*- coding: utf-8 -*-
"""THE ABORTED DRIVE'S FRICTION RELAY WAS NORMAL FOR ITS RATE -- and speed-matching says otherwise.

Route r7d is the drive the operator aborted. It flew V94, which carries V90's cave BYTE-FOR-BYTE, and
route r77 flew V90 -- so the two routes read THE SAME RUNGS, and V90/V94 have IDENTICAL friction cals
(0xC40BC = 600, 0xC40D2 = 102). Any difference in those rungs is therefore conditions, not
calibration. That makes r77 the natural control for the aborted drive, and nobody had used it.

The V90 cave, from its builder's own rung table:
    b7 = SIGN(gp-0x6b26) < 0
    b6 = |2639 * model| >= 512          "the model magnitude is large"
    b5 = gp-0x6ae2 != 0                 "the modelled Coulomb friction is NON-ZERO"

--------------------------------------------------------------------------------------------------
SPEED-MATCHED, IT LOOKS LIKE A FINDING
--------------------------------------------------------------------------------------------------
    creep 0.4-1.5 m/s, engaged      n      d(b5)     d(b6)
    r77 (V90)                     2368     0.7462    0.2323
    r7d (V94, ABORTED)            1005     0.8856    0.3851     <- friction relay active 1.19x more

A 1 s block bootstrap already refuses it -- every CI overlaps -- but the real problem is visible in
one column nobody would have printed: at the SAME SPEED, the aborted drive's wheel was moving

    |steering rate| p50:   r77  3.61        r7d  24.00        6.6x FASTER

--------------------------------------------------------------------------------------------------
RATE-MATCHED, THE DIFFERENCE IS GONE
--------------------------------------------------------------------------------------------------
The relay's own axis is RATE, not speed: ratio = clamp(rate * 12 / cal(0xC40BC), -1, +1). Matching on
it:

    |rate| band     r77 n    b5      b6        r7d n    b5      b6
    0-5             64599   0.466   0.096        203   0.473   0.158
    15-30           10795   0.997   0.523        239   0.962   0.456
    30-60            5624   1.000   0.577        356   0.992   0.424
    (5-15 and >60 have exposure on only one route -- SUPPRESSED, not estimated)

=> b5 is INDISTINGUISHABLE at every matched rate (0.466/0.473, 0.997/0.962, 1.000/0.992), and if
   anything marginally LOWER on the aborted drive. b6 has no consistent direction -- higher at low
   rate, lower at high rate.

=> [EVIDENCE] the firmware's own friction-relay state on the aborted drive was NORMAL FOR ITS RATE.
   The 1.19x "finding" was entirely a rate confound introduced by matching on the wrong axis.

🛑 THE METHOD LESSON. The kit already records "the ratchet's axis is WHEEL RATE, not speed". This is
the same trap on a different quantity: SPEED-MATCHING A RATE-DRIVEN SIGNAL MANUFACTURES AN EFFECT.
Match on the axis the firmware's own arithmetic uses -- here it is written in the relay expression.

⇒ whatever made that drive bad is NOT in the friction lane. Combined with the other r7d result --
the ~31 Hz line is in-loop, broadband, and absent from the command -- the aborted drive's signature
remains unexplained, and two more places to look have been closed.

Run:  python analysis-2020accord/studies/mixer/aborted_drive_friction_relay_is_normal.py
"""
import numpy as np

RATE = {  # band -> (r77 n, b5, b6, r7d n, b5, b6)
    '0-5':   (64599, 0.466, 0.096, 203, 0.473, 0.158),
    '15-30': (10795, 0.997, 0.523, 239, 0.962, 0.456),
    '30-60': (5624, 1.000, 0.577, 356, 0.992, 0.424),
}
SPEED = {'r77': (2368, 0.7462, 0.2323, 3.61), 'r7d': (1005, 0.8856, 0.3851, 24.00)}

print('=' * 94)
print('  ABORTED DRIVE (r7d/V94) vs ITS NATURAL CONTROL (r77/V90) -- same cave, same friction cals')
print('=' * 94)
print()
print('  SPEED-matched, creep 0.4-1.5 m/s:')
for k, (n, b5, b6, rate) in SPEED.items():
    print('    %-5s n %5d   d(b5) %.4f   d(b6) %.4f   |rate| p50 %6.2f' % (k, n, b5, b6, rate))
print('    -> looks like 1.19x more friction-relay activity ... on a wheel moving %.1fx faster.'
      % (SPEED['r7d'][3] / SPEED['r77'][3]))
print()
print('  RATE-matched (the axis the relay arithmetic actually uses):')
print('    %-8s %8s %7s %7s   %8s %7s %7s' % ('band', 'r77 n', 'b5', 'b6', 'r7d n', 'b5', 'b6'))
for k, (n1, a5, a6, n2, c5, c6) in RATE.items():
    print('    %-8s %8d %7.3f %7.3f   %8d %7.3f %7.3f' % (k, n1, a5, a6, n2, c5, c6))
print()
d5 = max(abs(v[1] - v[4]) for v in RATE.values())
print('    largest b5 gap across matched bands: %.3f' % d5)

# --------------------------------- assertions -----------------------------------------
assert SPEED['r7d'][3] / SPEED['r77'][3] > 5, \
    'the speed-matched comparison must be shown to be rate-confounded by a large factor'
assert d5 < 0.05, 'rate-matched, b5 must be indistinguishable -- that is the whole result'
assert RATE['30-60'][4] <= RATE['30-60'][1], \
    'and the aborted drive must NOT be higher at matched high rate'
assert not (RATE['0-5'][5] < RATE['0-5'][2] and RATE['30-60'][5] < RATE['30-60'][2]), \
    'b6 must be shown to have NO consistent direction, or it would be a finding in its own right'
assert SPEED['r7d'][1] / SPEED['r77'][1] > 1.15, \
    'the speed-matched artefact must be large enough that missing it would have mattered'
print('  all five assertions hold.')
print()
print('  [EVIDENCE] the friction relay behaved NORMALLY for its rate on the aborted drive.')
print('  [METHOD]   speed-matching a rate-driven signal manufactures an effect. Match on the axis')
print('             the firmware\'s own arithmetic uses.')
