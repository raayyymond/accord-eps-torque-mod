# -*- coding: utf-8 -*-
"""THE RETRODICTION TEST FAILS: the ABSOLUTE damping/pumping label is withdrawn. Separation stands.

Earlier this session the r24 reconstruction was published with an absolute verdict -- "r24 DAMPS at
6-9 Hz". Its controls passed exactly, but those controls pinned the PIPELINE's internal consistency
(a constructed +90 deg lead reads +90; a viscous torque lands in quadrature). They did NOT pin the
PHYSICAL FRAME: whether r24's output reaches the motor with the same sign as cs_rate. That was flagged
OPEN at the time. This file is the first external check of it, and the check fails.

THE TEST. V88 raised r24 (512 -> 5244) and measured three bands on-car. If the work factor is a real
predictor with the assumed frame, then bands where r24 damps HARDER should be the bands V88 improved
MORE -- i.e. a more negative work factor should pair with a LOWER V88 ratio. That is a positive
correlation between work factor and V88 ratio.

    band          phi(T,rate)   r24 phase   work factor   V88 on-car
    ratchet 6-9      -120.7        +143.9      -0.808        0.859x
    mid 9-12         -150.8        +111.6      -0.368        0.604x
    grind 15-22      +119.8         +16.5      +0.959        0.549x

    corr(work, V88 ratio) = -0.803        the prediction required POSITIVE

V88 helped MOST at 15-22 Hz, which is exactly where the instrument says r24 PUMPS hardest. Flipping
the sign gives +0.803 and retrodicts all three bands. That is what a globally inverted frame looks
like.

WHY THE PHASE MOVES SO MUCH ACROSS THE BANDS -- and why it is not a wrap artefact. From 10.5 to
18.5 Hz phi(T,rate) goes -150.8 -> +119.8, which reads as a jump but is a continuous -89 deg of
additional lag (-150.8 - 89 = -239.8 == +120.2). The plant simply rolls off hard between the bands.
The work factor uses cos(), which is 2*pi-periodic, so wrapping cannot corrupt it either way.

HOW STRONG IS THIS? WEAK -- and it is reported as weak.
  * n = 3 bands, and they are not independent samples of anything.
  * V88 changed FIVE bytes, not only Lever B, so its band ratios are not a clean r24 dose.
  * A single sign is being inferred from three points.
=> This is enough to WITHDRAW the absolute claim. It is NOT enough to assert the opposite. Both
   "r24 DAMPS" and "r24 PUMPS" are now UNRESOLVED in absolute terms.

WHAT SURVIVES, BY DESIGN. Every actionable conclusion was deliberately re-anchored on the SEPARATION
between lanes plus V88's on-car result, with no absolute label anywhere in the chain:
  * r24 and gp-0x6ad4 are 76 deg apart, on opposite sides of the rate axis   [relative]
  * V88 fixes r24's side as the beneficial one                               [on-car]
  * the PID lane is 0.25x r24 in this band                                   [magnitude]
  * V227's ceiling does not bind (47 ct vs 164-341)                          [magnitude]
  * the span cal is 91 % magnitude / 9 % phase, next to a kill-switch        [relative]
  * r24's phase is structurally capped at +149.3 deg                         [relative]
  * delivery lag is bounded at 3.25 ms vs a 77 ms inversion threshold        [relative]
NONE of those use the sign. V222 remains the flight candidate on unchanged grounds.

ALSO WITHDRAWN: the inference that the record's "net PID DAMPS at 6-9 Hz" is a convention flip. If the
frame here is inverted, the record may simply be right.

Run:  python analysis-2020accord/studies/mixer/r24_retrodiction_test_fails.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DEG = u'\N{DEGREE SIGN}'
# (band, centre Hz, measured phi(T,rate), V88 on-car ratio)
BANDS = [('ratchet 6-9', 7.5, -120.7, 0.859),
         ('mid 9-12', 10.5, -150.8, 0.604),
         ('grind 15-22', 18.5, +119.8, 0.549)]


def wrap(a):
    return ((a + 180.0) % 360.0) - 180.0


print('=' * 92)
print('  RETRODICTION TEST vs V88 -- does the work factor predict what the car did?')
print('=' * 92)
print()
print('  %-13s %8s %12s %11s %12s %12s'
      % ('band', 'f_c', 'phi(T,rate)', 'r24 phase', 'work', 'V88 on-car'))
work, v88 = [], []
for name, fc, pt, ratio in BANDS:
    H = 1.0 - np.exp(-1j * 2 * np.pi * fc * 4e-3)
    pr = wrap(pt + np.degrees(np.angle(H)) + 180.0)
    w = float(np.cos(np.radians(pr)))
    work.append(w)
    v88.append(ratio)
    print('  %-13s %7.1fHz %+11.1f%s %+10.1f%s %+11.3f %11.3fx'
          % (name, fc, pt, DEG, pr, DEG, w, ratio))

c = float(np.corrcoef(work, v88)[0, 1])
print()
print('  corr(work factor, V88 ratio) = %+.3f' % c)
print('  the prediction required POSITIVE: harder damping (more negative work) should pair with a')
print('  LOWER V88 ratio, i.e. a bigger on-car improvement.')
print('  flipping the sign of the frame gives %+.3f, which retrodicts all three bands.' % (-c))

assert c < 0, 'if the correlation were positive the absolute label would SURVIVE -- rewrite this file'
assert abs(c) > 0.5, 'a near-zero correlation would be uninformative rather than a failure'
print()
print('  [WITHDRAWN] the ABSOLUTE label. Both "r24 DAMPS" and "r24 PUMPS" are UNRESOLVED.')
print('              The controls pinned the pipeline, not the physical frame.')
print('  [WEAK]      n=3 non-independent bands, and V88 moved 5 bytes not just Lever B. Enough to')
print('              withdraw a claim, NOT enough to assert its opposite.')
print('  [STANDS]    every separation-based result, all of which avoid the sign by construction:')
for line in ('r24 vs gp-0x6ad4 are 76 deg apart, opposite sides',
             'V88 fixes r24 as the beneficial side (on-car)',
             'the PID lane is 0.25x r24; V227 ceiling does not bind',
             'the span cal is a redundant gain knob next to a kill-switch',
             'r24 phase structurally capped; delivery lag bounded at 3.25 ms'):
    print('              * %s' % line)
print('  [STANDS]    the MAGNITUDE correction, which is frame-independent: 187 ct vs 431-1294.')
print('  [UNCHANGED] V222 remains the flight candidate; its case rests on V88, not on a sign.')
print('  [ALSO WITHDRAWN] the claim that the record\'s "net PID DAMPS" is a convention flip.')
