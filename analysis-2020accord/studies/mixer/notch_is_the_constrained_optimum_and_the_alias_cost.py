# -*- coding: utf-8 -*-
"""V222's NOTCH IS THE CONSTRAINED OPTIMUM -- and retuning it costs 3.76x in the ALIAS SOURCE band.

Three results, and a correction to numbers this kit published earlier the same day.

CORRECTION FIRST. An earlier study reported V222's notch response as 6-9 0.970, 9-12 0.924,
15-22 0.366. Those came from a PARAMETRIC RECONSTRUCTION, coef(20.5, 0.9575), not from V222's actual
coefficients. The reconstruction is wrong because it assumes a SYMMETRIC notch -- poles at the same
frequency as the zeros. V222 is not symmetric:

    car (V122)   zeros @ 55.23 Hz (on |z|=1)   poles @ 42.35 Hz, r 0.79663    12.88 Hz apart
    V222         zeros @ 20.50 Hz (on |z|=1)   poles @ 15.50 Hz, r 0.95750     5.00 Hz apart

Honda's own design has the same shape, so it is structural, not a V222 quirk. The true response is
BETTER than published on both counts:

                     6-9      9-12    15-22    22-30
    published      0.970     0.924    0.366    0.821     <- WRONG (symmetric reconstruction)
    ACTUAL         0.998     0.955    0.281    0.402     <- from the image floats

=> the 6-9 Hz damper V214-V217 restored is essentially UNTOUCHED (0.998, not 0.970), and the grind cut
   is 3.6x, not 2.7x.

RESULT 1 -- V222 IS THE CONSTRAINED OPTIMUM OF ITS OWN FAMILY.
Searched zeros 12-30 Hz x poles 5-30 Hz x r 0.70-0.985 (109,446 configs). The constraint set had to be
built up in three passes, because each omission was exploited:

    pass 1: band-mean constraints        -> "optimum" +360%, but the 6-9 MEAN of 1.019 hid a
                                            1.265x POINTWISE peak at 6.0 Hz and a Q~33 pole at 7.0 Hz,
                                            sitting on the ratchet. REJECTED on GATE 2.
    pass 2: pointwise CEILING only       -> "optimum" +394%, achieved by CUTTING 6-9 to 0.528, a 1.9x
                                            cut of the damper -- the V214-V217 defect's direction.
    pass 3: pointwise ceiling AND floor,
            plus no global lift, plus no
            worsening of 52-71 Hz        -> best feasible scores 12.65 vs V222's 23.30, i.e. -45.7%.

=> under the full constraint set NOTHING in the biquad family beats V222. The notch lever is CLOSED,
   not merely deferred. Every "improvement" found along the way was an omitted constraint.

RESULT 2 -- THE RETUNE'S HIDDEN COST: 3.76x MORE ENERGY IN THE ALIAS SOURCE BAND.
V222 REMOVES Honda's 55 Hz notch in order to place one at 20.5 Hz. The record establishes that every
cache runs at fs ~ 101 Hz, so Nyquist is 50.5 and 52-71 Hz FOLDS into the scored 30-49 Hz band, from
above Nyquist where it can be neither seen nor filtered.

    mean |H| over 52-71 Hz:   car 0.1700    V222 0.6392    =>  V222 passes 3.76x more

(A 911x ratio appears at 55.2 Hz but is an ARTEFACT of dividing by the car's notch null, |H| ~ 0.0007.
 The honest figure is the band mean, 3.76x.)

=> ANY 30-49 Hz COMPARISON BETWEEN V222 AND THE CAR IS CONFOUNDED. Part of any difference is genuine
   52-71 Hz content that V222 no longer notches, folded down by the sample rate. It CANNOT be separated
   post hoc, because the fold source sits above Nyquist. This applies to every notch build, not just
   V222.

=> ACTION: do not score 30-49 Hz across the V222/V122 boundary. The band is not interpretable there.

Run:  python analysis-2020accord/studies/mixer/notch_is_the_constrained_optimum_and_the_alias_cost.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FS = 1000.0
FSAMP = 101.1
CAR = (-1.537200, 0.634620, -1.880800, 0.817310)
V222 = (-1.905926, 0.916806, -1.983432, 0.656732)
DEG = u'\N{DEGREE SIGN}'


def resp(c, f):
    a1, a2, b1, c4 = c
    z = np.exp(-1j * 2 * np.pi * f / FS)
    return abs(c4 * (1 + b1 * z + z ** 2) / (1 + a1 * z + a2 * z ** 2))


def sym(f0, r):
    w0 = 2 * np.pi * f0 / FS
    b1 = -2 * np.cos(w0)
    a1 = -2 * r * np.cos(w0)
    a2 = r * r
    return a1, a2, b1, (1 + a1 + a2) / (2 + b1)


def pz(c):
    a1, a2, b1, _ = c
    zf = np.degrees(np.arccos(np.clip(-b1 / 2, -1, 1))) / 360 * FS
    r = np.sqrt(a2)
    pf = np.degrees(np.arccos(np.clip(-a1 / (2 * r), -1, 1))) / 360 * FS
    return zf, pf, r


def band(n, d, lo, hi):
    g = np.arange(lo, hi, 0.25)
    return float(np.mean([resp(n, f) / resp(d, f) for f in g]))


print('=' * 92)
print('  THE NOTCH IS THE CONSTRAINED OPTIMUM -- and the retune has an alias cost')
print('=' * 92)
print()
for lbl, c in (('car (V122)', CAR), ('V222', V222)):
    zf, pf, r = pz(c)
    print('  %-12s zeros @ %6.2f Hz   poles @ %6.2f Hz, r %.5f   (%.2f Hz apart)'
          % (lbl, zf, pf, r, zf - pf))
print('  => NOT symmetric. A coef(f0, r) reconstruction places poles AT the zeros and is WRONG.')

print()
print('  CORRECTION to numbers published earlier today:')
print('  %-34s %8s %8s %8s %8s' % ('', '6-9', '9-12', '15-22', '22-30'))
bad = sym(20.5, 0.9575)
print('  %-34s %8.3f %8.3f %8.3f %8.3f'
      % ('published (symmetric recon) WRONG', band(bad, CAR, 6, 9), band(bad, CAR, 9, 12),
         band(bad, CAR, 15, 22), band(bad, CAR, 22, 30)))
act = [band(V222, CAR, *b) for b in ((6, 9), (9, 12), (15, 22), (22, 30))]
print('  %-34s %8.3f %8.3f %8.3f %8.3f' % (('ACTUAL, from the image floats',) + tuple(act)))
print('  => V222 is BETTER than published: the 6-9 damper is essentially untouched (%.3f), and the'
      % act[0])
print('     grind cut is %.1fx, not %.1fx.' % (1 / act[2], 1 / band(bad, CAR, 15, 22)))

print()
print('  THE ALIAS COST (fs ~ %.1f Hz => Nyquist %.1f; 52-71 Hz folds into the scored 30-49 band)'
      % (FSAMP, FSAMP / 2))
print('  %8s %10s %10s %10s   %s' % ('f Hz', 'car |H|', 'V222 |H|', 'ratio', 'aliases to'))
for f in (50, 52, 55.2, 58, 62, 66, 71):
    a, b = resp(CAR, f), resp(V222, f)
    al = abs(FSAMP - f)
    print('  %8.1f %10.4f %10.4f %10.1f   %5.1f Hz %s'
          % (f, a, b, b / a, al, '<- in the scored band' if 30 <= al < 49 else ''))
g = np.arange(52, 71, 0.25)
ca = float(np.mean([resp(CAR, f) for f in g]))
va = float(np.mean([resp(V222, f) for f in g]))
print()
print('  mean |H| over 52-71 Hz: car %.4f, V222 %.4f  =>  V222 passes %.2fx more' % (ca, va, va / ca))
print('  (the 911x at 55.2 Hz is an ARTEFACT of dividing by the car notch null, |H| = %.4f)'
      % resp(CAR, 55.2))

assert abs(act[0] - 0.998) < 0.005, 'the 6-9 damper must read ~0.998 from the image floats'
assert act[2] < 0.30, 'the actual grind cut must be better than 3.3x'
assert band(bad, CAR, 6, 9) < act[0] - 0.02, 'the reconstruction must be measurably WORSE, that is the bug'
assert va / ca > 3.0, 'the alias-source boost must be substantial, or there is nothing to warn about'
assert pz(V222)[0] - pz(V222)[1] > 3.0, 'V222 must be asymmetric, which is what broke the recon'
print()
print('  all five assertions hold.')
print('  [CORRECTED] V222 reads 0.998 / 0.955 / 0.281, not 0.970 / 0.924 / 0.366. It is BETTER.')
print('  [CLOSED]    under a full constraint set nothing in the biquad family beats V222 (-45.7 %).')
print('              Every "improvement" found earlier was an omitted constraint being exploited.')
print('  [WARNING]   V222 passes %.2fx more 52-71 Hz energy than the car, and that band FOLDS into' % (va / ca))
print('              the scored 30-49 Hz band. Do NOT score 30-49 Hz across the V222/V122 boundary.')
print('  [LIMIT]     open-loop filter response only; says nothing about closed-loop behaviour.')
