# -*- coding: utf-8 -*-
"""RETRACTION: my own "cutting apparent inertia raises loop gain broadband" does not survive.

Earlier this session I concluded, from a CREEP-MATCHED (i.e. SPEED-matched) analysis over 9 routes,
that cutting apparent inertia raises engaged loop gain BROADBAND -- every band tracking the dose
together at corr -0.85 / -0.75 / -0.57 / -0.79. It was already flagged as carried by one drive
(perm p 0.0087 -> 0.2486 without r7d) and confounded with build order (dose vs build number +0.750).

I then established, separately, that SPEED-MATCHING A RATE-DRIVEN SIGNAL MANUFACTURES AN EFFECT. And
gp-0x6b26 is -K*alpha -- acceleration feedback, which is rate-driven. So my own conclusion was built
on the estimator I had just shown to be wrong for this class of signal, and it gets re-run.

RE-RUN: windows classified by their own median |steering rate| (spread cap p90/p50 <= 3), each window
normalised WITHIN ITSELF against the 30-40 Hz control band.

    |rate| bin   routes   corr(log dose, band ratio)              perm p
                          ratchet 6-9   mid 9-12   grind 15-22
    0-3            5         +0.478      +0.735      +0.230      0.46 / 0.19 / 0.75
    3-8            5         +0.539      +0.705      +0.530      0.36 / 0.19 / 0.37
    8-20           6         +0.262      +0.553      +0.606      0.53 / 0.19 / 0.29

TWO THINGS KILL IT.

1. 🛑 r7d IS ABSENT FROM EVERY BIN. It has 1,084 engaged frames total -- not enough for 8 windowed
   spectra in any rate bin. r7d is the ONLY route at the low dose (0.250) and it carried the entire
   association in the original analysis. So THE RATE-MATCHED INSTRUMENT CANNOT TEST THE LOW-DOSE END
   AT ALL, which is exactly where the effect was claimed.

2. 🛑 THE SIGN FLIPS. Over the doses that CAN be tested (1.000-3.964) every correlation is POSITIVE
   -- higher dose, MORE band ratio -- against the original's uniformly NEGATIVE. None is significant
   (every p >= 0.19), so this is not a counter-claim; it is evidence that the original number was
   ESTIMATOR-DEPENDENT rather than a property of the car.

=> [RETRACTED] "cutting apparent inertia raised engaged loop gain broadband" is withdrawn as an
   inference. It was one drive, confounded with build order, measured on the wrong axis, and
   sign-unstable when the axis is corrected.
=> [STANDS] the DESCRIPTION of r7d itself -- a sustained engagement-gated ~31 Hz line, in-loop,
   absent from the command, broadband across bands. That is an observation of one drive and does not
   depend on the corpus regression.
=> [STANDS] the build consequence, because it never rested on this: V214-V217 restored the damper to
   the car's own value, which is justified by "match the flown image", not by a dose-response.

Run:  python analysis-2020accord/studies/mixer/inertia_dose_broadband_lift_retracted.py
"""
import numpy as np

# rate-matched re-run: bin -> (n_routes, corr per band, perm p per band)
RM = {
    '0-3':  (5, [0.478, 0.735, 0.230], [0.4610, 0.1938, 0.7450]),
    '3-8':  (5, [0.539, 0.705, 0.530], [0.3623, 0.1895, 0.3735]),
    '8-20': (6, [0.262, 0.553, 0.606], [0.5290, 0.1938, 0.2883]),
}
ORIGINAL = [-0.853, -0.747, -0.574, -0.790]     # speed-matched, all four bands, all NEGATIVE
ORIG_P_ALL, ORIG_P_NO_R7D = 0.0087, 0.2486
R7D_ENGAGED_FRAMES, WINDOWS_NEEDED = 1084, 8

print('=' * 92)
print('  RETRACTION -- the inertia-dose broadband lift, re-run on the rate-matched instrument')
print('=' * 92)
print()
print('  original (speed-matched, 9 routes): corr %s -- all NEGATIVE'
      % ' '.join('%+.3f' % c for c in ORIGINAL))
print('    already weak: perm p %.4f -> %.4f without r7d' % (ORIG_P_ALL, ORIG_P_NO_R7D))
print()
print('  %-8s %8s   %-34s %s' % ('rate bin', 'routes', 'corr(log dose, ratio)', 'perm p'))
for k, (n, c, p) in RM.items():
    print('  %-8s %8d   %-34s %s'
          % (k, n, ' '.join('%+7.3f' % x for x in c), ' '.join('%6.3f' % x for x in p)))
print()
print('  r7d: %d engaged frames total, needs %d windows in a rate bin -- ABSENT FROM ALL OF THEM.'
      % (R7D_ENGAGED_FRAMES, WINDOWS_NEEDED))
print('  It is the only route at dose 0.250 and it carried the original association entirely.')

# --------------------------------- assertions -----------------------------------------
assert all(c < 0 for c in ORIGINAL), 'the original must be recorded as uniformly negative'
assert all(x > 0 for _, c, _ in RM.values() for x in c), \
    'the rate-matched re-run must be uniformly POSITIVE -- the sign flip is the point'
assert all(x >= 0.15 for _, _, p in RM.values() for x in p), \
    'and none of it significant, so this is NOT a counter-claim'
assert ORIG_P_NO_R7D > 0.05, 'the original already died without its single low-dose route'
assert R7D_ENGAGED_FRAMES < 2000, \
    'r7d must be shown to lack the exposure a windowed spectrum needs'
print()
print('  all five assertions hold.')
print('  [RETRACTED] the broadband loop-gain inference from inertia dose.')
print('  [STANDS]    the description of r7d itself, and the build decision, which never rested on it.')
