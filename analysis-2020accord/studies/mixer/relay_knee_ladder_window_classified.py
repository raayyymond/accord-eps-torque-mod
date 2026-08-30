# -*- coding: utf-8 -*-
"""THE KNEE LADDER, RE-MEASURED WITH A WORKING RATE-MATCHED INSTRUMENT -- suggestive, not established.

The previous attempt gated SAMPLES on instantaneous rate, which fragments the signal below a spectral
window and killed 3 of 4 rate bands. The fix is to classify WHOLE WINDOWS by their own median rate,
with a within-window spread cap (p90/p50 <= 3.0) so the label means something. That works: 175 / 86 /
148 engaged windows in the slowest bin instead of nothing.

The manual side is still empty at low rate on these routes, so the engaged/manual contrast is
unavailable. Normalising WITHIN each window against the 30-40 Hz control band removes the need for it.
⚠ that control band is itself alias-contaminated from 52-71 Hz -- but identically so on every route,
so as a cross-route NORMALISER it still works. It is not a clean band and no absolute claim rests on it.

    log2(band / ctl 30-40), mean [95 % CI bootstrapped OVER WINDOWS]

    |rate| 0-3        winN   ratchet 6-9            mid 9-12               grind 15-22
    V111 onset  50     175   1.829 [1.658,2.000]    2.079 [1.923,2.238]    1.987 [1.843,2.137]
    V112 onset 150      86   2.023 [1.751,2.313]    3.258 [2.929,3.590]    1.999 [1.763,2.236]
    V122 onset 250     148   1.901 [1.694,2.098]    2.402 [2.209,2.592]    1.748 [1.609,1.887]

    |rate| 3-8         winN
    V111 onset  50      26   3.600 [2.825,4.339]    3.385 [2.673,4.118]    4.133 [3.634,4.649]
    V112 onset 150      25   2.759 [2.222,3.299]    2.847 [2.177,3.537]    3.603 [3.068,4.160]
    V122 onset 250      18   2.577 [1.930,3.152]    2.381 [1.557,3.219]    2.580 [2.025,3.073]

    |rate| 8-20        winN
    V111 onset  50      33   3.792 [3.236,4.375]    3.264 [2.653,3.856]    5.493 [4.936,6.046]
    V112 onset 150       8   2.560 [1.167,3.995]    1.749 [0.688,2.787]    5.449 [4.617,6.272]
    V122 onset 250      10   3.243 [2.214,4.256]    1.686 [0.757,2.798]    2.965 [2.216,3.764]

--------------------------------------------------------------------------------------------------
WHAT LOOKS LIKE A FINDING
--------------------------------------------------------------------------------------------------
In GRIND 15-22 the trend is monotone DECREASING in onset at 3-8 (4.133 / 3.603 / 2.580) and the
V111-vs-V122 CIs are DISJOINT there and again at 8-20 (5.493 vs 2.965). Read alone, that says a
SHARPER relay (smaller knee) carries MORE grind-band energy -- and therefore that V222 restoring the
knee 50 -> 250 would REDUCE it, a benefit not previously credited.

--------------------------------------------------------------------------------------------------
WHY IT IS NOT ESTABLISHED -- ITS OWN CROSS-BAND CHECK REFUSES IT
--------------------------------------------------------------------------------------------------
  1. IT FAILS IN THE LARGEST BIN. At 0-3, where n is 175/86/148, NOTHING is monotone and every
     ratchet CI overlaps. The trend appears only where n is 8-26.
  2. IT IS NOT CONSISTENT ACROSS BANDS. At 8-20 the ratchet band is 3.792 / 2.560 / 3.243 --
     NON-monotone -- while grind is monotone. A knee lever acting on the loop should not sort one
     symptom band and scramble the neighbouring one.
  3. THE MIDDLE BUILD IS HIGHEST in mid 9-12 at 0-3 (3.258, disjoint from both others), which is the
     signature of a route difference, not a dose.
  4. ONSET IS CONFOUNDED WITH BUILD NUMBER and with every other cell that moved; only V111 -> V112 is
     a true 2-cell pair, and V112 -> V122 also moves alpha.
  5. The arithmetic predicts NO effect: with the slope held, all three settings are identical below
     50 counts of rate, and 3-8 deg/s is far below every onset.

=> [BELIEF, WEAK] a possible grind-band trend with the relay knee. [EVIDENCE] it does not survive its
   own cross-band and largest-bin checks, so it is NOT claimed.
=> WHAT WOULD SETTLE IT: the V222 drive itself. V222 sits at onset 250 while the whole V196-V217 shelf
   sat at 50, so if this trend is real the grind band should come out LOWER than those builds predict.
   That is a free, pre-registered read on a drive already planned -- it costs nothing to check.

Run:  python analysis-2020accord/studies/mixer/relay_knee_ladder_window_classified.py
"""
import numpy as np

ONSET = np.array([50, 150, 250])
# rate bin -> band -> (mean, lo, hi) per onset
D = {
    '0-3': {'ratchet': [(1.829, 1.658, 2.000), (2.023, 1.751, 2.313), (1.901, 1.694, 2.098)],
            'mid':     [(2.079, 1.923, 2.238), (3.258, 2.929, 3.590), (2.402, 2.209, 2.592)],
            'grind':   [(1.987, 1.843, 2.137), (1.999, 1.763, 2.236), (1.748, 1.609, 1.887)]},
    '3-8': {'ratchet': [(3.600, 2.825, 4.339), (2.759, 2.222, 3.299), (2.577, 1.930, 3.152)],
            'grind':   [(4.133, 3.634, 4.649), (3.603, 3.068, 4.160), (2.580, 2.025, 3.073)]},
    '8-20': {'ratchet': [(3.792, 3.236, 4.375), (2.560, 1.167, 3.995), (3.243, 2.214, 4.256)],
             'grind':   [(5.493, 4.936, 6.046), (5.449, 4.617, 6.272), (2.965, 2.216, 3.764)]},
}
N_WIN = {'0-3': [175, 86, 148], '3-8': [26, 25, 18], '8-20': [33, 8, 10]}

mono = lambda v: (np.diff(v) < 0).all() or (np.diff(v) > 0).all()
print('=' * 90)
print('  KNEE LADDER, WINDOW-CLASSIFIED -- is any band monotone in the onset?')
print('=' * 90)
print()
print('  %-8s %-9s %6s   %s' % ('rate bin', 'band', 'winN', 'means by onset 50/150/250   monotone?'))
for rb, bands in D.items():
    for b, v in bands.items():
        m = [x[0] for x in v]
        print('  %-8s %-9s %6s   %s   %s'
              % (rb, b, '/'.join(map(str, N_WIN[rb])),
                 ' '.join('%6.3f' % x for x in m), 'YES' if mono(m) else 'no'))
print()
g38, g820 = [x[0] for x in D['3-8']['grind']], [x[0] for x in D['8-20']['grind']]
r820 = [x[0] for x in D['8-20']['ratchet']]
print('  grind IS monotone at 3-8 and 8-20, and V111-vs-V122 CIs are disjoint in both.')
print('  but ratchet at 8-20 is %s -- and the largest bin (0-3, n=175/86/148) sorts NOTHING.'
      % ('monotone' if mono(r820) else 'NOT monotone'))

# --------------------------------- assertions -----------------------------------------
assert mono(g38) and mono(g820), 'the grind trend is what would need explaining if it were real'
assert D['3-8']['grind'][0][1] > D['3-8']['grind'][2][2], 'V111 vs V122 must be disjoint at 3-8'
assert not mono(r820), \
    'the ratchet band at 8-20 must be NON-monotone -- that inconsistency is why this is not claimed'
assert not mono([x[0] for x in D['0-3']['ratchet']]), 'the largest bin must sort nothing'
assert D['0-3']['mid'][1][0] > D['0-3']['mid'][0][0] and D['0-3']['mid'][1][0] > D['0-3']['mid'][2][0], \
    'the MIDDLE onset must be highest in mid 9-12 -- a route signature, not a dose'
assert min(N_WIN['8-20']) < 12, 'the bins where the trend looks strongest must stay flagged as thin'
print()
print('  all six assertions hold.')
print('  [BELIEF, WEAK] a possible grind-band trend with the knee -- NOT claimed.')
print('  [SETTLES IT]   the V222 drive: it sits at onset 250 where the V196-V217 shelf sat at 50.')
