# -*- coding: utf-8 -*-
"""A FLOWN, SLOPE-CONTROLLED LADDER ON THE COULOMB RELAY KNEE -- and it shows NOTHING.

Identifying route r21 as V111 (its cache label said "UNKNOWN-V108-or-V111") exposed a ladder nobody
had noticed, and it is the controlled experiment the record's headline for this cell never had:

    build  route  0xC40BC  0xC40D2   slope       saturation onset
    V111   r21       600      204   0.003984      50 counts
    V112   r22      1800      612   0.003984     150 counts
    V122   r24      3000     1020   0.003984     250 counts   <- THE CAR

**Same unsaturated slope, three saturation onsets, all flown**, and V111 -> V112 is a TRUE
single-variable pair: exactly 2 cells, 4 payload bytes, nothing else. Contrast the record's
"de-relaying made the ratchet 2.3x worse", which moved the knee 10x while holding k1 -- so the slope
fell 10x at the same time and the two effects are not separable there.

--------------------------------------------------------------------------------------------------
THE RESULT: NO KNEE EFFECT IS VISIBLE, AND THE CONTROL BAND IS WHY WE KNOW
--------------------------------------------------------------------------------------------------
log2(engaged / manual) band power in cs_rate, |steering rate| 0-5, 2 s Welch windows:

    onset  build  n_eng    ratchet 6-9   mid 9-12   grind 15-22   ctl 30-40
      50   V111   34163       1.353        1.850       1.835        0.825
     150   V112   10054       1.868        3.720       1.870        1.171
     250   V122   29530       1.489        2.226       1.561        1.036

=> NON-MONOTONE in every symptom band -- the middle onset is the highest -- and the CONTROL BAND
   MOVES WITH THEM (0.825 -> 1.171 -> 1.036, the same ordering). A band-specific lever cannot do
   that. What is visible is route-to-route difference, not the knee.

=> [EVIDENCE] no measurable effect of the relay knee on the symptom bands across a slope-controlled,
   three-point flown ladder.

⊕ THIS AGREES WITH THE ARITHMETIC. The friction curve at these three settings is IDENTICAL below the
   lowest onset, because the slope is held; they differ only ABOVE 50 / 150 / 250 counts of rate. The
   ratchet lives at 1-13 deg/s, far below all three. Two independent lines, same conclusion:
   V222 restoring the knee 600 -> 3000 should NOT change the symptom bands, and does not.

--------------------------------------------------------------------------------------------------
🛑 A METHOD LIMIT THAT KILLED THREE QUARTERS OF THE MEASUREMENT
--------------------------------------------------------------------------------------------------
RATE-GATING AND WELCH ARE INCOMPATIBLE. Gating on an instantaneous rate fragments the signal into
pieces far shorter than a spectral window, so the 5-15, 15-30 and 30-60 rate bands returned ZERO
usable windows on all three routes. Only the slowest band survived, and only because the wheel is
mostly slow.

So the honest reading is: this is a WEAK instrument that found nothing, not a strong instrument that
proved nothing. To test the knee properly one would need windows selected by SUSTAINED rate, or a
within-frame cave rung rather than a spectrum. Last tick's lesson -- match on the firmware's own axis
-- collides here with a spectral estimator that needs contiguity, and the collision is the finding.

Run:  python analysis-2020accord/studies/mixer/relay_knee_flown_ladder_null.py
"""
import numpy as np

ONSET = np.array([50, 150, 250])
BUILD = ('V111', 'V112', 'V122')
ROUTE = ('r21', 'r22', 'r24')
N_ENG = np.array([34163, 10054, 29530])
RATCHET = np.array([1.353, 1.868, 1.489])
MID = np.array([1.850, 3.720, 2.226])
GRIND = np.array([1.835, 1.870, 1.561])
CTL = np.array([0.825, 1.171, 1.036])
RATE_BANDS_USABLE, RATE_BANDS_TRIED = 1, 4

print('=' * 92)
print('  RELAY KNEE -- three flown builds, same slope, three saturation onsets')
print('=' * 92)
print()
print('  %-6s %-6s %7s %8s %12s %10s %12s %10s'
      % ('route', 'build', 'onset', 'n_eng', 'ratchet 6-9', 'mid 9-12', 'grind 15-22', 'ctl 30-40'))
for i in range(3):
    print('  %-6s %-6s %7d %8d %12.3f %10.3f %12.3f %10.3f'
          % (ROUTE[i], BUILD[i], ONSET[i], N_ENG[i], RATCHET[i], MID[i], GRIND[i], CTL[i]))
print()
print('  ordering by onset:  ratchet %s   ctl %s'
      % (list(np.argsort(RATCHET)), list(np.argsort(CTL))))
print('  the control band shares the symptom bands\' ordering -> route difference, not a lever.')
print()
print('  usable rate bands: %d of %d -- rate-gating fragments the signal below a spectral window.'
      % (RATE_BANDS_USABLE, RATE_BANDS_TRIED))

# --------------------------------- assertions -----------------------------------------
for nm, v in (('ratchet', RATCHET), ('mid', MID), ('grind', GRIND)):
    assert not (np.diff(v) > 0).all() and not (np.diff(v) < 0).all(), \
        '%s must be NON-monotone in onset -- a monotone band would be a real dose-response' % nm
assert np.argmax(CTL) == np.argmax(RATCHET) == np.argmax(GRIND), \
    'the control band must peak on the SAME route as the symptom bands -- that is what makes this ' \
    'a route difference rather than a band-specific effect'
assert RATE_BANDS_USABLE < RATE_BANDS_TRIED, \
    'the rate-gating limit must stay recorded: most bands yielded no usable spectral windows'
assert len(set(ONSET)) == 3 and ONSET.max() / ONSET.min() == 5, \
    'the ladder must span 5x in onset, or it is not a dose-response worth calling one'
print()
print('  all assertions hold.')
print('  [EVIDENCE] no knee effect on the symptom bands, on a slope-controlled 3-point flown ladder.')
print('  [AGREES]   with the arithmetic: the three settings are identical below 50 counts of rate,')
print('             and the ratchet lives at 1-13 deg/s, far below all three onsets.')
print('  [LIMIT]    a WEAK instrument that found nothing, not a strong one that proved nothing.')
