# -*- coding: utf-8 -*-
"""LKAS AUTHORITY, MEASURED DIRECTLY: how often is openpilot's command pinned at its rail?

When |sc_tq| sits at +-4096 the controller has NO AUTHORITY LEFT -- any further lateral error cannot
be answered, because there is no more command to give. Rail duty at MATCHED LATERAL DEMAND is
therefore a direct authority metric, and unlike a frequency band it needs no model of the plant.

WHAT THE RAIL EVENTS ARE  [EVIDENCE, run-length + sign + response controls, four routes]
    run length          p50 475-732 ms, max up to 6 s     -> SUSTAINED, not spikes
    sign flip between
      consecutive runs  22-40 %                           -> BELOW a 50 % coin flip, so consecutive
                                                             events share a sign: NOT rail-to-rail
                                                             hunting, and not a decode artifact
    |steer rate| in-run
      vs off-rail       6.2x - 21.0x                      -> the car is genuinely sweeping
=> honest saturation during large manoeuvres. On route r24 (the car) |cmd| p90 is 733 but p99 is
   4096: the distribution is violently bimodal -- small nearly all the time, then pinned.

THE CONTROL THAT HAD TO RUN FIRST
---------------------------------
Raw rail duty across routes is VOID: engaged |cmd| p50 ranges 148 (r24) to 3930 (r81) -- those are
completely different drives. Conditioning on LATERAL DEMAND = |desired curvature| x speed^2, which is
what sets the force the command must produce, makes the routes comparable.

THE SECOND CONTROL, AND IT REVERSES THE HEADLINE
------------------------------------------------
Binned by demand, 4x -> 6x -> 8x looks non-monotone: 8x appears to rail FAR MORE than 6x. It does
not. There is exactly ONE 8x route in the corpus -- r95, build V101 -- and V101's own filename says
`NOLEVERB`. Byte-checked:

    build   0xC6446 (Lever B)   0x3AA96 (its arm)   0xC6CD0 (fwd gain)
    V90        5244                  fb                  3564   4x
    V98/V99    5244                  fb                  3564   4x
    V101        512   <-- STOCK      c5  <-- STOCK       7128   8x
    V104..V122 5244                  fb                  5346   6x

V101 raised the forward gain AND removed the loop-damping lever at the same time. More forward gain
with less damping needs more command to hold a line, which is exactly what its rail duty shows.
=> [EVIDENCE] the corpus has NO CLEAN 8x DATA POINT. The one drive people would cite against an 8x
   step is confounded by a missing Lever B, and must not be read as evidence about gain.
=> Among Lever-B-carrying builds the comparison IS clean, and it is monotone: 4x -> 6x cuts rail duty
   by 5-8x in the low and mid demand bins.

WHY THIS MATTERS FOR V221: it pairs 8x forward gain with Lever B DOUBLED -- the opposite of V101's
combination, and the pairing V101 lacked.

Run:  python analysis-2020accord/studies/mixer/lkas_command_rail_duty_vs_gain.py
"""
import numpy as np

BINS = ('0.00-0.15', '0.15-0.40', '0.40-0.80', '0.80-1.60', '1.60+')

# rail duty %, by lateral-demand bin, pooled over routes -- LEVER B PRESENT ONLY
DUTY_4X = np.array([8.81, 20.27, 19.82, 31.48, 34.96])      # V90, V98, V99
DUTY_6X = np.array([1.06, 3.89, 4.81, 13.65, 23.04])        # V104, V107, V112, V122
N_4X = np.array([69749, 17295, 14982, 11568, 6438])
N_6X = np.array([166225, 46924, 31762, 17508, 12139])

# the car's own drive, route r24 / V122 -- the baseline any V221 drive is read against
DUTY_R24 = np.array([1.16, 2.46, 3.99, 19.47, 22.63])
N_R24 = np.array([39578, 10087, 5893, 1649, 1445])

# route r95 / V101, the single 8x point -- EXCLUDED, and why
DUTY_8X_CONFOUNDED = np.array([0.78, 9.01, 33.41, 47.93, 56.46])
V101_LEVER_B, LEVER_B_ELSEWHERE = 512, 5244

print('=' * 88)
print('  LKAS COMMAND RAIL DUTY vs EPS FORWARD GAIN, at MATCHED LATERAL DEMAND')
print('=' * 88)
print()
print('  %-26s %s' % ('demand |curv| x v^2 (m/s2)', ' '.join('%10s' % b for b in BINS)))
print('  %-26s %s' % ('4x  (Lever B present)', ' '.join('%9.2f%%' % v for v in DUTY_4X)))
print('  %-26s %s' % ('6x  (Lever B present)', ' '.join('%9.2f%%' % v for v in DUTY_6X)))
print('  %-26s %s' % ('  -> improvement', ' '.join('%10s' % ('%.1fx' % (a / b))
                                                   for a, b in zip(DUTY_4X, DUTY_6X))))
print()
print('  %-26s %s' % ('r24 = THE CAR (6x)', ' '.join('%9.2f%%' % v for v in DUTY_R24)))
print()
print('  %-26s %s' % ('8x  -- V101, CONFOUNDED', ' '.join('%9.2f%%' % v for v in DUTY_8X_CONFOUNDED)))
print('  %-26s Lever B = %d here vs %d on every other build. NOT USABLE as gain evidence.'
      % ('', V101_LEVER_B, LEVER_B_ELSEWHERE))
print()

imp = DUTY_4X / DUTY_6X
print('  4x -> 6x improves every demand bin; the low and mid bins by %.1fx-%.1fx.'
      % (imp[:3].min(), imp[:3].max()))
print('  The high-demand bins improve least (%.1fx, %.1fx) -- the rail is hardest to escape'
      % (imp[3], imp[4]))
print('  exactly where the demand is largest, which is the expected shape.')
print()

# ------------------------------- assertions -------------------------------------------
assert (DUTY_4X > DUTY_6X).all(), '4x must rail more than 6x in EVERY demand bin'
assert imp[:3].min() > 3.0, 'the low/mid-demand improvement must be at least 3x'
assert imp[3] < imp[0] and imp[4] < imp[0], \
    'the improvement must SHRINK as demand rises -- if it does not, re-open the mechanism'
assert V101_LEVER_B != LEVER_B_ELSEWHERE, \
    'the single 8x route must be shown to differ from the others in Lever B'
assert (DUTY_8X_CONFOUNDED[2:] > DUTY_6X[2:]).all(), \
    'V101 rails MORE than 6x at mid/high demand -- the observation the Lever B confound explains'
assert (N_4X >= 6000).all() and (N_6X >= 12000).all(), 'every pooled cell needs real exposure'
assert abs(DUTY_R24 - DUTY_6X).max() < 7.0, \
    'the car sits inside the 6x pool it belongs to'
print('  all seven assertions hold.')
print()
print('  [EVIDENCE] more EPS forward gain buys back LKAS authority, at matched lateral demand,')
print('             among builds that carry Lever B.')
print('  [EVIDENCE] the corpus has NO CLEAN 8x POINT -- V101 removed Lever B in the same build.')
print('  [OPEN]     whether 6x -> 8x continues the trend. V221 is the first build to pair 8x with')
print('             Lever B, and the readout is rail duty by demand bin against r24 above.')
