# -*- coding: utf-8 -*-
"""LEVER B'S INPUT: a span-4 finite difference, a hidden KILL-SWITCH, and a clock bound from a drive.

Lever B multiplies `gp-0x4f62`, the Sensor-B column-torque RATE. If that rate arrived with much phase
lag, Lever B's contribution would stop being damping and become stiffness -- or, past 90 deg, PUMPING.
Nothing in the record had checked that, so this does.

THE PRODUCER, from the decompile of FUN_0007e74a (called by FUN_0007f3f8):

    ring_torque[i] = gp-0x4f60                 # 8-slot ring, i cycles 0..7
    ring_time[i]   = wrapped timestamp (mod 30000)
    N = cal(0xC6C42)                           # the SPAN, in producer samples
    if N < 8:
        dt   = wrap(ring_time[i] - ring_time[i-N])
        rate = ((torque[i] - torque[i-N]) << 1) / dt      if dt >= 1 else 0
    else:
        rate = 0                                          # <-- see the KILL-SWITCH below
    gp-0x4f62 = rate   (lockstep-mirrored to gp-0x4488)

=> it is a FIRST-ORDER FINITE DIFFERENCE OVER N SAMPLES, dividing by the MEASURED dt. The magnitude is
   therefore correct whatever the sample rate; only the PHASE depends on the span in wall-clock time:

       phase lag = 180 * f * N * T   degrees,  T = the producer's sample period

--------------------------------------------------------------------------------------------------
1. THE KILL-SWITCH -- N >= 8 SILENTLY ZEROES THE LANE
--------------------------------------------------------------------------------------------------
The ring has 8 slots, and the code's own guard is `if N < 8 ... else gp-0x4f62 = 0`. So writing 8 or
more to `0xC6C42` forces the torque rate to ZERO, which kills **r24 AND r26 together** -- both read
the same `dtorque`. Lever B would read its full 13107 gain and deliver nothing, and every existing
check would still pass, because they all check the GAIN, not its input.
[EVIDENCE] `0xC6C42` = 4 in all 218 images on disk -- never moved, so this has never bitten. A gate
now asserts it stays < 8, because it is exactly the silent-lever-loss class this kit keeps hitting.

--------------------------------------------------------------------------------------------------
2. A DRIVE BOUNDS AN OPEN CLOCK QUESTION
--------------------------------------------------------------------------------------------------
The facade records this producer's wall-clock rate as OPEN: *"[VERIFIED functions/delay | OPEN
wall-clock Hz]"*, with a clock-tree audit outstanding. But V88 flew this lane and the result bounds it,
because the SIGN of the effect at a known frequency is a phase measurement:

    V88 vs V87, single-variable:   15-22 Hz -> 0.549x     i.e. DAMPING, not pumping

A span-N difference stops damping when its lag reaches 90 deg. At f = 20.5 Hz with N = 4:

    lag(T) = 180 * 20.5 * 4 * T  >= 90 deg   =>   T >= 6.10 ms   =>   producer slower than 164 Hz

=> [EVIDENCE] the producer runs FASTER than ~164 Hz. A 100 Hz ring is EXCLUDED by the flown result:
   it would put the lag at 147.6 deg, cos = -0.844, and Lever B would have PUMPED 15-22 Hz.
   The measured band profile points the same way -- damping is STRONGEST in the highest band
   (6-9 Hz 0.859x, 9-12 Hz 0.604x, 15-22 Hz 0.549x), whereas a lag approaching 90 deg would make the
   effect WEAKEN with frequency.

3. AND AT 1 kHz THERE IS NO LEVER HERE. If the producer runs at the confirmed ~1 kHz control-task
   rate, the lag is 5.6 deg at 7.79 Hz and 14.8 deg at 20.5 Hz -- cos 0.995 and 0.967, i.e. Lever B is
   very nearly pure damping already. Lowering N would buy under half a degree at 7.79 Hz and cost
   noise on a shorter baseline. **N = 4 is left alone.**

Run:  python analysis-2020accord/studies/mixer/lever_b_input_phase_and_killswitch.py
"""
import numpy as np

N = 4
RING_SLOTS = 8
BANDS = {'6-9 Hz': (7.79, 0.859), '9-12 Hz': (10.5, 0.604), '15-22 Hz': (20.5, 0.549)}

lag = lambda f, T: 180.0 * f * N * T


print('=' * 92)
print('  LEVER B\'S INPUT -- span-%d finite difference, kill-switch at N >= %d' % (N, RING_SLOTS))
print('=' * 92)
print()
print('  phase lag and the damping fraction cos(lag), by producer rate:')
print('  %-16s %s' % ('producer rate', '  '.join('%14s' % b for b in BANDS)))
for hz in (1000.0, 500.0, 250.0, 164.0, 100.0):
    T = 1.0 / hz
    cells = []
    for b, (f, _) in BANDS.items():
        L = lag(f, T)
        cells.append('%7.1f deg %+.3f' % (L, np.cos(np.radians(L))))
    print('  %-16s %s' % ('%.0f Hz' % hz, '  '.join(cells)))

f_hi = BANDS['15-22 Hz'][0]
T_crit = 90.0 / (180.0 * f_hi * N)
print()
print('  V88 measured 15-22 Hz at %.3fx -- DAMPING. A span-%d difference stops damping at 90 deg,'
      % (BANDS['15-22 Hz'][1], N))
print('  which at %.1f Hz needs T >= %.2f ms, i.e. a producer SLOWER than %.0f Hz.'
      % (f_hi, 1000 * T_crit, 1.0 / T_crit))
print('  => the producer runs FASTER than %.0f Hz. A 100 Hz ring is EXCLUDED by the flown result.'
      % (1.0 / T_crit))

# --------------------------------- assertions -----------------------------------------
assert N < RING_SLOTS, 'N must stay inside the ring or the lane is zeroed'
assert np.cos(np.radians(lag(f_hi, 1 / 100.0))) < 0, \
    'at 100 Hz the lane would PUMP 15-22 Hz -- that is what the drive excludes'
assert np.cos(np.radians(lag(f_hi, 1 / 1000.0))) > 0.95, \
    'at 1 kHz the lane must be very nearly pure damping'
assert abs(1.0 / T_crit - 164.0) < 1.0, 'the derived bound must land at ~164 Hz'
r = [v for _, v in BANDS.values()]
assert r[0] > r[1] > r[2], \
    'damping must STRENGTHEN with frequency in the measured profile -- a lag near 90 deg would ' \
    'make it weaken, so the profile corroborates a fast producer'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] N >= 8 is a silent kill-switch for r24 AND r26; 0xC6C42 = 4 in all 218 images.')
print('  [EVIDENCE] the flown V88 result excludes a producer slower than ~164 Hz.')
print('  [NOTE]     at ~1 kHz there is no lever here -- N = 4 is already near-ideal phase.')
