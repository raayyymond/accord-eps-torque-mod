# -*- coding: utf-8 -*-
"""THE GOVERNOR RAMP-TIME HYPOTHESIS IS RETIRED -- by the task rate, now that it is known.

The model's `slew_ramp_time_analysis` records the ramp-time story as the leading ratchet hypothesis
and says it was "later CONFIRMED as a real contributor". Its own docstring also says why that
confirmation could never have been quantitative:

    "[OPEN] the wall-clock conversion (task rate contested); cycle counts here are exact,
     milliseconds are deliberately NOT computed."

The task rate is no longer contested -- the kit confirmed the control task at ~1000 Hz. So the
milliseconds ARE computable now, and they retire the hypothesis.

WHICH RATE, AND ON WHAT EVIDENCE (audited 2026-08-30, because this is the whole load-bearing input):
  * The GOVERNOR is in task 1. The confirming record scopes 1 kHz to FUN_0002214a and names its tree
    explicitly -- "arbitration (FUN_00028ea6), the aggregator (FUN_0003aa2c), shaper, GOVERNOR". So
    1000 Hz is the right divisor here, not the assist-shaping rate.
  * 1 kHz stands on ONE route, not two: the ON-CAR dwell (cal 0xC64DF = 100 cycles, observed on the
    bus at 100.00 ms). The kit's second route -- OSTM0CMP=79999 / 80 MHz -- is REFUTED: PCLK is
    40 MHz, and OSTM0 is not the RTOS tick. The conclusion is unaffected (the on-car measurement
    never used that chain) but do not cite the OSTM0 derivation.
  * Task 5's rate is OPEN. The "100 Hz" figure was RETRACTED 2026-08-12 (address-coincidence
    derivation, contradicted by flown gp-0x6bbe telemetry). It does not enter this file's arithmetic,
    and it must not be used as a ZOH veto elsewhere.

    lkas_max = min((setpoint 8192 * gain) >> 15, arb output clamp 4096)
    ramp     = lkas_max / slew_step   cycles, at 1 kHz

    build            gain   lkas_max   fast step   ramp (fast)   slow step   ramp (slow)
    Honda stock       891        222         512       0.4 ms          205       1.1 ms
    V122 (the car)   5346       1336         512       2.6 ms          205       6.5 ms
    V222 / V227      7128       1782         512       3.5 ms          205       8.7 ms

The ratchet is 7.79 Hz -- a 128 ms period. A ramp that completes in 3.5-8.7 ms is 15-37x FASTER than
one ratchet cycle. It cannot build a 7.79 Hz oscillation; on that timescale it is instantaneous.

=> [EVIDENCE] the "V38 made the ramp 4x longer" observation is arithmetically correct and
   operationally irrelevant: 4x of 0.4 ms is 1.7 ms. The invariant was real; its magnitude never was.
   The earlier "confirmed as a real contributor" verdict was reached without a task rate and is
   confounded with V42's state-4 substitution, which the record itself calls the root-cause fix.

--------------------------------------------------------------------------------------------------
🛑 AND DO NOT TOUCH THE CELLS ANYWAY
--------------------------------------------------------------------------------------------------
0xC6206 / 0xC6208 are 512 / 205 in 217 of 219 images. The two exceptions are instructive:

    V45  205 / 205    the FAST step lowered to the slow value -- FALSIFIED on-car
    V40  0xFFFF/0xFFFF  ☠ EPS LAMP + NO POWER STEERING AT IGNITION

The record is explicit that V40's fault IS attributable to these two cells, and that the mechanism was
MAGNITUDE, not direction: 0xFFFF made the slew guard NEVER FIRE -> snap-to-target -> FUN_00016de6(0x1d)
-> hard-fault-eligible with NO DEBOUNCE -> motor off.

That failure mode is a CONTINUUM, not a cliff. The LKAS command is a ~1-5 Hz low-pass, so its natural
per-cycle change at 1 kHz is a few counts; raising the step to any large value makes the guard
functionally inert for normal signals, which is exactly the condition that faulted V40. There is no
demonstrated safe raise, and the ramp arithmetic above says there is nothing to buy.

=> RECOMMENDATION: leave 0xC6206/0xC6208 at 512/205. This closes the governor as a ratchet lever.

Run:  python analysis-2020accord/studies/mixer/governor_ramp_time_retired_by_the_task_rate.py
"""
SETPOINT, ARB_CLAMP = 8192, 4096
FAST, SLOW = 512, 205
FS = 1000.0
RATCHET_HZ = 7.79
BUILDS = [('Honda stock', 891), ('V122 (the car)', 5346), ('V222 / V227', 7128)]

print('=' * 92)
print('  GOVERNOR RAMP TIME AT THE CONFIRMED 1 kHz TASK RATE')
print('=' * 92)
print()
period_ms = 1000.0 / RATCHET_HZ
print('  one ratchet cycle at %.2f Hz = %.1f ms' % (RATCHET_HZ, period_ms))
print()
print('  %-16s %6s %10s %12s %12s' % ('build', 'gain', 'lkas_max', 'ramp fast', 'ramp slow'))
rows = []
for nm, g in BUILDS:
    lk = min((SETPOINT * g) >> 15, ARB_CLAMP)
    rf, rs = lk / FAST, lk / SLOW
    rows.append((nm, g, lk, rf, rs))
    print('  %-16s %6d %10d %9.1f ms %9.1f ms' % (nm, g, lk, rf, rs))
print()
_, _, lk, rf, rs = rows[-1]
print('  the shelf ramps to FULL command in %.1f-%.1f ms -- %.0fx to %.0fx faster than one ratchet'
      % (rf, rs, period_ms / rs, period_ms / rf))
print('  cycle. On that timescale the governor ramp is instantaneous.')

# --------------------------------- assertions -----------------------------------------
assert rs < period_ms / 10, \
    'the SLOW ramp must be an order of magnitude faster than a ratchet cycle -- that is the retirement'
assert rows[0][3] < 1.0, 'and Honda stock must ramp in well under a millisecond'
assert rows[-1][3] / rows[0][3] > 7, \
    'the 8x lengthening must still be real -- the point is that 8x of nothing is nothing'
assert min((SETPOINT * 7128) >> 15, ARB_CLAMP) < ARB_CLAMP, \
    'lkas_max must be set by the gain product, not by the arb clamp, or the scaling argument breaks'
print()
print('  all four assertions hold.')
print('  [EVIDENCE] the ramp-time hypothesis cannot produce a 7.79 Hz ratchet at 1 kHz.')
print('  [SAFETY]   0xC6206/0xC6208 caused an EPS lamp and loss of power steering at ignition when')
print('             set to 0xFFFF. The fault mode is a continuum. Leave them at 512/205.')
