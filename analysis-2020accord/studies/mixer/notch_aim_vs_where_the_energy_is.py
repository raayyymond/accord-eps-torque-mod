# -*- coding: utf-8 -*-
"""IS V222's NOTCH AIMED WHERE THE ENERGY IS? Mostly not -- but do NOT retune it. Here is why.

The Re(Z) spectrum puts the anti-damping peak at 9-10 Hz (mean -67.9 over 9-12), roughly 4.8x the
grind band's -14.2. V222's notch is centred at 20.50 Hz. So the obvious question is whether the flight
candidate is aimed 10 Hz off the peak.

WHAT THE NOTCH ACTUALLY DOES, computed from the image floats (a1,a2,b1,c4 at 0xC60A8/AC/B0/B4,
direct-form II, 1 kHz):

    the car (V122)  a1 -1.537200  a2 +0.634620  b1 -1.880800  c4 +0.817310   f0 55.23 Hz, r 0.7966
    V222            a1 -1.905926  a2 +0.916806  b1 -1.983432  c4 +0.656732   f0 20.50 Hz, r 0.9575

    band      V222 / car
    6-9         0.970        <- essentially untouched, which is DELIBERATE (see below)
    9-12        0.924        <- the Re(Z) PEAK, and the notch barely reaches it
    12-15       0.827
    15-22       0.366        <- 2.7x cut: the notch does its job here
    22-30       0.821

=> CONFIRMED GAP: the notch cuts the band with the LEAST anti-damping by 2.7x and the band with the
   MOST by 8 %.

BUT V222 IS NOT BLIND TO THE PEAK -- LEVER B COVERS IT, AND MORE STRONGLY THAN AT THE RATCHET.
r24's transfer is a 4 ms difference, |1-exp(-j*w*0.004)|, which RISES with frequency:
    7.79 Hz  0.1955        10.5 Hz  0.2630  = 1.35x stronger at the Re(Z) peak than at the ratchet.
So the build's broadband lever is best-aimed exactly where the narrowband lever is weakest.

TWO WAYS TO CLOSE THE GAP, AND ONE IS CLEARLY WORSE.

  RE-CENTRING to 13 Hz (keeping r): 9-12 -> 0.460, but 15-22 degrades 0.366 -> 0.807 (the grinding cut
  is surrendered) and 22-30 goes to 1.402 -- a BOOST, in the region that folds into the scored 30-49 Hz
  band. Strictly a trade, and it gives back a measured win. REJECTED.

  WIDENING (same centre, lower pole radius) improves BOTH bands at once, because a wider notch has more
  area under the cut:
      r        6-9      9-12    15-22    22-30
      0.9575   0.970    0.924    0.366    0.821    <- V222 as built
      0.9400   0.941    0.865    0.296    0.714
      0.9200   0.913    0.813    0.254    0.646
      0.9000   0.893    0.780    0.232    0.611
  DC stays exactly 1.000000 at every r, by the construction rule c4 = (1+a1+a2)/(2+b1).

=> AND WIDENING IS STILL REJECTED, FOR NOW. The skirt extends DOWNWARD into 6-9 Hz, which is precisely
   the band where V214-V217 found the notch shelf had been cutting a REAL damper 7.15x below the car --
   a defect discovered only through an ABORTED DRIVE. At r = 0.92 the trade is:

       COST   8.7 % of the 6-9 Hz damper
       BUY    11.0 % deeper 9-12 cut, 11.2 % deeper 15-22 cut

   An 8.7 % encroachment is far smaller than the 7.15x that caused the abort, so this is not the same
   error. But it is the same DIRECTION, on the one band the kit has just spent four builds repairing,
   and it buys ~11 % on a notch that already delivers 2.7x. That is a poor bargain to take BEFORE V222
   has flown even once.

=> RECOMMENDATION: fly V222 as built. If its drive shows residual 9-12 Hz content, r = 0.92 is the
   pre-computed follow-up rung and its coefficients are printed below. Do NOT re-centre.

Run:  python analysis-2020accord/studies/mixer/notch_aim_vs_where_the_energy_is.py
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FS = 1000.0
CAR = (-1.537200, 0.634620, -1.880800, 0.817310)
V222 = (-1.905926, 0.916806, -1.983432, 0.656732)
REZ = {'6-9': -23.5, '9-12': -67.9, '12-15': -51.3, '15-22': -14.2}
BANDS = [('6-9', 6, 9), ('9-12', 9, 12), ('12-15', 12, 15), ('15-22', 15, 22), ('22-30', 22, 30)]


def coef(f0, r):
    w0 = 2 * np.pi * f0 / FS
    b1 = -2 * np.cos(w0)
    a1 = -2 * r * np.cos(w0)
    a2 = r * r
    return a1, a2, b1, (1 + a1 + a2) / (2 + b1)


def resp(c, f):
    a1, a2, b1, c4 = c
    z = np.exp(-1j * 2 * np.pi * f / FS)
    return abs(c4 * (1 + b1 * z + z ** 2) / (1 + a1 * z + a2 * z ** 2))


def band(c, lo, hi):
    return float(np.mean([resp(c, f) / resp(CAR, f) for f in np.arange(lo, hi, 0.25)]))


print('=' * 90)
print('  IS V222\'S NOTCH AIMED WHERE THE ENERGY IS?')
print('=' * 90)
print()
print('  %-8s %12s %14s   %s' % ('band', 'V222 / car', 'Re(Z) weight', 'reading'))
for name, lo, hi in BANDS:
    r = band(V222, lo, hi)
    w = REZ.get(name)
    note = '' if w is None else ('the PEAK -- barely reached' if name == '9-12'
                                 else ('least anti-damping -- cut hardest' if name == '15-22' else ''))
    print('  %-8s %12.3f %14s   %s' % (name, r, ('%.1f' % w) if w else '-', note))

d = 1.0 - np.exp(-1j * 2 * np.pi * np.array([7.79, 10.5]) * 4e-3)
print()
print('  but LEVER B rises with frequency: |H| %.4f at 7.79 Hz -> %.4f at 10.5 Hz = %.2fx'
      % (abs(d[0]), abs(d[1]), abs(d[1]) / abs(d[0])))
print('  => the broadband lever is best-aimed exactly where the narrowband lever is weakest.')

print()
print('  WIDENING (same 20.50 Hz centre) -- improves BOTH target bands, but encroaches on 6-9:')
print('  %8s %9s %9s %9s %9s %9s   %s' % ('r', '6-9', '9-12', '15-22', '22-30', 'DC', 'verdict'))
for r in (0.9575, 0.9400, 0.9200, 0.9000):
    c = coef(20.5, r)
    b69 = band(c, 6, 9)
    v = 'SAFE' if b69 > 0.95 else ('watch' if b69 > 0.90 else 'ENCROACHES')
    print('  %8.4f %9.3f %9.3f %9.3f %9.3f %9.4f   %s%s'
          % (r, b69, band(c, 9, 12), band(c, 15, 22), band(c, 22, 30), resp(c, 0.001), v,
             '  <- V222 as built' if abs(r - 0.9575) < 1e-3 else ''))

print()
print('  RE-CENTRING (keeping V222 sharpness) -- surrenders the grinding cut AND boosts 22-30:')
print('  %8s %9s %9s %9s   %s' % ('f0 Hz', '9-12', '15-22', '22-30', 'verdict'))
for f0 in (20.5, 16.0, 13.0):
    c = coef(f0, 0.9575)
    b2230 = band(c, 22, 30)
    print('  %8.1f %9.3f %9.3f %9.3f   %s'
          % (f0, band(c, 9, 12), band(c, 15, 22), b2230,
             'V222' if f0 == 20.5 else ('BOOSTS 22-30' if b2230 > 1.0 else '')))

c92 = coef(20.5, 0.92)
print()
print('  pre-computed follow-up rung, r = 0.92 (do NOT fly before V222 has flown):')
print('    a1 = %+.8f   a2 = %+.8f   b1 = %+.9f   c4 = %+.8f' % c92)
print('    DC = %.6f  (held at unity by c4 = (1+a1+a2)/(2+b1))' % resp(c92, 0.001))
print('    costs %.1f %% of the 6-9 damper; buys %.1f %% on 9-12 and %.1f %% on 15-22'
      % ((1 - band(c92, 6, 9)) * 100,
         (band(V222, 9, 12) - band(c92, 9, 12)) * 100,
         (band(V222, 15, 22) - band(c92, 15, 22)) * 100))

assert band(V222, 15, 22) < 0.5, 'V222 must genuinely cut the grind band'
assert band(V222, 9, 12) > 0.85, 'and must barely touch 9-12 -- that IS the gap'
assert band(V222, 6, 9) > 0.95, 'and must leave the 6-9 damper alone, which V214-V217 restored'
assert band(coef(13.0, 0.9575), 22, 30) > 1.0, 're-centring must BOOST 22-30, which is why it is out'
assert abs(resp(c92, 0.001) - 1.0) < 1e-4, 'any candidate must hold DC at unity'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] the notch cuts the LEAST anti-damped band 2.7x and the MOST anti-damped band 8 %.')
print('  [MITIGATED] Lever B is 1.35x stronger at the peak than at the ratchet, so V222 is not blind.')
print('  [REJECTED]  re-centring: surrenders a measured grinding win and boosts 22-30 into the fold.')
print('  [DEFERRED]  widening: helps both bands but encroaches on the 6-9 damper V214-V217 restored,')
print('              in the same DIRECTION as the defect that caused an aborted drive. Not before')
print('              V222 flies. Coefficients above if the drive shows residual 9-12 Hz content.')
print('  [LIMIT]     Re(Z) weights carry an unresolved absolute sign; only the SHAPE is used here.')
