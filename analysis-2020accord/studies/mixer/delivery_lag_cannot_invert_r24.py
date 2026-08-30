# -*- coding: utf-8 -*-
"""CAN DELIVERY LAG INVERT r24? No -- the whole chain lives inside ONE 1 kHz task.

r24's phase sits at +143.6 deg vs rate, 36 deg short of a pure damper. Transport lag ROTATES that,
and at 7.79 Hz every 10 ms is 28 deg, so the question is sharp:

    +13 ms  -> 180 deg   r24 becomes an OPTIMAL damper
    +32 ms  ->  90 deg   r24 does nothing at all
    +51 ms  ->   0 deg   r24 PUMPS

A lag nobody had measured therefore decides whether the kit's best lever helps, is inert, or inverts.
This file tries to measure it, fails honestly, and then bounds it structurally -- which is enough.

ATTEMPT 1 -- MEASURE IT FROM THE WIRE. FAILED, and the failure is itself informative.
Fitting a phase slope from openpilot's command (sc_tq) to steering rate needs coherence. Measured over
6 routes, engaged, the median coherence is:

    0.5-1.5 Hz  0.140      5-6 Hz   0.162
    1.5-3 Hz    0.162      6-9 Hz   0.184
    3-5 Hz      0.181      9-12 Hz  0.234

Nothing clears 0.25. A phase slope fitted through coherence that low is noise, so NO delay estimate is
reported from this route. => the command explains only ~18 % of steering-rate variance at the ratchet,
which independently supports the record's "the EPS generates it" and "a fast vibration cannot be
COMMANDED via LKAS". The null is on the METHOD, not on the lag.

ATTEMPT 2 -- BOUND IT STRUCTURALLY. This succeeds, and the bound is far from the inversion threshold.
The confirmed task map puts the ENTIRE path inside task 1 at 1 kHz: the record scopes 1 kHz to
FUN_0002214a and names "arbitration (FUN_00028ea6), the aggregator (FUN_0003aa2c), shaper, governor".
r24 is formed in the aggregator and delivered through the shaper and governor, all in that same task.

    torque sample -> aggregator -> governor -> shaper       same task invocation, 0 ticks
    the documented chain re-entry (gp-0x6b98 via FUN_0003b8f6)  "one sample later" = 1 tick = 1 ms
    Path 2 reading the previous tick (recorded ordering)         1 tick = 1 ms
    FOC/PWM carrier ~4-8 kHz                                     <= 0.25 ms

=> even charging THREE full ticks plus the carrier, the delivery lag is ~3.25 ms = 9.1 deg at 7.79 Hz.
   Reaching the 51 ms that would inflip r24 to pumping would need ~51 task ticks of delay inside a
   chain that completes within one. That is not a close call.

AND THE SIGN OF THE ERROR IS FAVOURABLE. r24 is 36 deg SHORT of 180, so a small lag rotates it TOWARD
a pure damper, not away. Within the structural bound the work factor can only IMPROVE.

Run:  python analysis-2020accord/studies/mixer/delivery_lag_cannot_invert_r24.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

F = 7.79
PHI_R24 = 143.6
DEG = u'\N{DEGREE SIGN}'
DEG_PER_MS = 360.0 * F / 1000.0
COH = {'0.5-1.5': 0.140, '1.5-3': 0.162, '3-5': 0.181, '5-6': 0.162, '6-9': 0.184, '9-12': 0.234}
COH_MIN = 0.25


def wrap(a):
    return ((a + 180.0) % 360.0) - 180.0


print('=' * 92)
print('  CAN DELIVERY LAG INVERT r24?  (%.2f Hz: %.2f%s per ms)' % (F, DEG_PER_MS, DEG))
print('=' * 92)

print()
print('  ATTEMPT 1 -- measure it from the wire.  command (sc_tq) -> rate coherence, 6 routes:')
for k, v in COH.items():
    print('    %-9s Hz   %.3f %s' % (k, v, '' if v >= COH_MIN else '  below the %.2f floor' % COH_MIN))
best = max(COH.values())
print('    best band %.3f -- nothing clears %.2f => NO delay is fitted from this route.'
      % (best, COH_MIN))
assert best < COH_MIN, 'if coherence cleared the floor, a delay MUST be fitted rather than bounded'
print('    the command explains ~%.0f %% of rate variance at the ratchet, which independently'
      % (100 * COH['6-9']))
print('    supports "the EPS generates it". The null is on the METHOD, not on the lag.')

print()
print('  ATTEMPT 2 -- bound it structurally.  Every stage is inside task 1 at 1 kHz:')
budget = [('aggregator -> governor -> shaper (same invocation)', 0.0),
          ('documented chain re-entry, "one sample later"', 1.0),
          ('Path 2 reads the previous tick', 1.0),
          ('a third tick, charged for safety', 1.0),
          ('FOC/PWM carrier at ~4-8 kHz', 0.25)]
tot = 0.0
for name, ms in budget:
    tot += ms
    print('    %-52s %5.2f ms' % (name, ms))
print('    %-52s %5.2f ms  = %.1f%s' % ('TOTAL, deliberately over-charged', tot, tot * DEG_PER_MS, DEG))

print()
print('  %-28s %10s %10s %10s   %s' % ('scenario', 'lag', 'phase', 'work', 'meaning'))
for name, ms in (('no lag', 0.0), ('structural bound', tot),
                 ('makes r24 OPTIMAL', (180.0 - PHI_R24) / DEG_PER_MS),
                 ('makes r24 INERT', (90.0 - PHI_R24) / DEG_PER_MS % (360.0 / DEG_PER_MS)),
                 ('makes r24 PUMP', (0.0 - PHI_R24) / DEG_PER_MS % (360.0 / DEG_PER_MS))):
    ph = wrap(PHI_R24 + ms * DEG_PER_MS)
    w = float(np.cos(np.radians(ph)))
    tag = 'DAMPS' if w < -0.2 else ('PUMPS' if w > 0.2 else 'inert')
    print('  %-28s %8.1f ms %+9.1f%s %+9.3f   %s' % (name, ms, ph, DEG, w, tag))

ph_b = wrap(PHI_R24 + tot * DEG_PER_MS)
w_b = float(np.cos(np.radians(ph_b)))
w_0 = float(np.cos(np.radians(PHI_R24)))
ms_pump = (0.0 - PHI_R24) / DEG_PER_MS % (360.0 / DEG_PER_MS)

assert w_b < -0.5, 'at the structural bound r24 must still be firmly damping'
assert abs(w_b) > abs(w_0), 'and a small lag must IMPROVE it, since r24 is short of 180 not past it'
assert ms_pump / tot > 10, 'inversion must need an order of magnitude more lag than the bound'
print()
print('  all three assertions hold.')
print('  [EVIDENCE] the structural bound is %.2f ms (%.1f%s). Inversion needs %.0f ms -- %.0fx more,'
      % (tot, tot * DEG_PER_MS, DEG, ms_pump, ms_pump / tot))
print('             i.e. ~%.0f task ticks of delay inside a chain that completes within ONE.'
      % ms_pump)
print('  [EVIDENCE] and the sign is FAVOURABLE: r24 is %.0f%s SHORT of 180%s, so lag inside the bound'
      % (180 - PHI_R24, DEG, DEG))
print('             rotates it TOWARD a pure damper -- work factor %+.3f -> %+.3f.' % (w_0, w_b))
print('  [CLOSES]   delivery lag cannot invert r24, and cannot make it inert. The concern is retired.')
print('  [LIMIT]    a bound, not a measurement. It rests on the task map (1 kHz, confirmed on-car)')
print('             and on the recorded one-tick re-entry, both of which are in the record.')
