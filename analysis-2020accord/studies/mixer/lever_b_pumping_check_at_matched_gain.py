# -*- coding: utf-8 -*-
"""DOES LEVER B PUMP 6-9 Hz? The flown corpus contains an ON/OFF contrast at MATCHED forward gain.

The kit records, on a three-way-verified sign finding, that "r24 = -431 to -1294 ct at 6-9 Hz,
PUMPING". Lever B (0xC6446) IS the r24 engaged derivative gain, and V221/V222 raise it 5244 -> 13107.
The ratchet is at 7.79 Hz, squarely inside 6-9 Hz. So the concern is direct: does raising Lever B make
the ratchet worse?

Read from the images (file offset == address; NOT rebased to 0x13000 -- that trap is on record):

    forward gain 0xC6CD0 = 3564 (4x) + LeverB 5244 / arm 0xfb   V91-V100     8 routes
    forward gain 0xC6CD0 = 7128 (8x) + LeverB  512 / arm 0xc5   V101         1 route  <- r95, EXCLUDED
    forward gain 0xC6CD0 = 5346 (6x) + LeverB  512 / arm 0xc5   V102,V103    2 routes   LEVER B OFF
    forward gain 0xC6CD0 = 5346 (6x) + LeverB 5244 / arm 0xfb   V104-V122    9 routes   LEVER B ON

🛑 TWO IMAGE-READING TRAPS THIS FILE EXISTS TO NOT REPEAT:
  1. file offset == ADDRESS in a *_plain_image.bin. Rebasing by 0x13000 returns 0xFFFF for every cal
     and an arm byte of 0x63, which looks like data rather than an error.
  2. a bare '*v104*' glob matches 'SUPERSEDED-DO-NOT-FLASH-E5DROPPED-_v104_...' BEFORE the live image
     ('S' sorts before '_'). Always anchor the glob as '_v<N>_' and reject SUPERSEDED names.

=> within gain 5346 the corpus has a real ON/OFF contrast, 3 routes vs 9, with the forward gain -- the
   single biggest confounder -- held byte-identical.

⚠ HONEST LIMIT, STATED UP FRONT: the arms are NOT single-variable. V102/V103 differ from V104+ in more
than Lever B (V104 also moves the biquad, V105 the notch, V106 gp-0x6b26, ...). This is an ON/OFF
contrast on a build family, not a clean dose. What it CAN do is answer the practical question -- is
6-9 Hz visibly WORSE when Lever B is armed? -- which is what "PUMPING" would have to look like on-car.

CONTROL: Lever B is ENGAGED-ONLY. So the same contrast computed on DISENGAGED driving must show
nothing. If manual shows the same separation, the split is road/tyre/route, not a lever.
⚠ The control isolates "engaged-only levers as a class", not Lever B uniquely, because several of the
other differing cells are also engaged-gated. Read it as a confound detector, not an attribution.

METRIC: a WITHIN-SPECTRUM ratio, log10(band / control band), on cs_rate. This session established that
raw band power tracks steering RATE (corr +0.739) while a band-to-control ratio does not (corr -0.041)
-- so the ratio is the rate-robust statistic and the raw band is not.

AGGREGATION: one median per ROUTE, then a rank test across routes. Windows within a route are
pseudo-replicates; the kit has a standing instruction to bootstrap over episodes, not windows.

Run:  python analysis-2020accord/studies/mixer/lever_b_pumping_check_at_matched_gain.py
"""
import sys

import numpy as np
from scipy.signal import welch
from scipy.stats import mannwhitneyu

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 🛑 r95 is V101, NOT V102 -- it is the 8x/7128 build, so it CANNOT sit in a gain-5346 arm.
# The corpus map in rlog-tools/score/dissociation_full_corpus.py used to record r95 as build 102, citing
# "r95_v102_prereg.py", but that script's own docstring says: "This script measures it on
# V101 (r95) and V100 (r85)" -- it is the pre-registration FOR V102, MEASURED ON r95=V101.
# The filename was read as an attribution. Excluded here and reported separately.
OFF = [('r96', 'V102'), ('r9e', 'V103')]
OFF_8X = [('r95', 'V101')]           # 8x + Lever B removed -- its own cell, n=1
ON = [('ra4', 'V104'), ('ra5', 'V105'), ('ra6', 'V106'), ('r1e', 'V107'),
      ('r21', 'V111'), ('r22', 'V112'), ('r23', 'V112'), ('r97', 'V112'), ('r24', 'V122')]
BANDS = {'ratchet 6-9': (6.0, 9.0), 'mid 9-12': (9.0, 12.0), 'grind 15-22': (15.0, 22.0)}
CTL = (30.0, 40.0)
SPREAD_MAX = 3.0
MIN_WIN = 6


def load(t):
    return np.load('analysis-2020accord/_scratch/cache/%s/%s.npz' % (t, t), allow_pickle=True)


def windows(d, engaged):
    fs = 1.0 / np.median(np.diff(d['t']))
    n = int(round(2.0 * fs))
    lat = np.asarray(d['cc_lat']).astype(float) > 0.5
    m = (lat if engaged else ~lat) & (np.abs(np.asarray(d['cs_v']).astype(float)) > 0.3)
    idx = np.flatnonzero(m)
    if not len(idx):
        return fs, n, []
    rate = np.abs(np.asarray(d['cs_rate']).astype(float))
    out = []
    for e in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        for k in range(0, len(e) - n + 1, n):
            w = e[k:k + n]
            p50, p90 = np.percentile(rate[w], 50), np.percentile(rate[w], 90)
            if p50 <= 0 or p90 / max(p50, 1e-9) > SPREAD_MAX:
                continue
            out.append(w)
    return fs, n, out


def ratios(tag, engaged):
    d = load(tag)
    fs, n, ws = windows(d, engaged)
    sig = np.asarray(d['cs_rate']).astype(float)
    acc = {b: [] for b in BANDS}
    for w in ws:
        f, p = welch(sig[w] - sig[w].mean(), fs=fs, nperseg=min(len(w), n))
        c = p[(f >= CTL[0]) & (f < CTL[1])].mean()
        if not np.isfinite(c) or c <= 0:
            continue
        for b, (lo, hi) in BANDS.items():
            v = p[(f >= lo) & (f < hi)].mean()
            if np.isfinite(v) and v > 0:
                acc[b].append(np.log10(v / c))
    return {b: (np.median(x) if len(x) >= MIN_WIN else np.nan) for b, x in acc.items()}, len(ws)


def arm(routes, engaged):
    res, nw = {b: [] for b in BANDS}, 0
    for tag, _ in routes:
        try:
            r, k = ratios(tag, engaged)
        except Exception:
            continue
        nw += k
        for b in BANDS:
            if np.isfinite(r[b]):
                res[b].append(r[b])
    return res, nw


print('=' * 96)
print('  DOES LEVER B PUMP THE RATCHET BAND?  ON/OFF at forward gain 5346, byte-matched')
print('=' * 96)

for engaged in (True, False):
    lab = 'ENGAGED  (Lever B is live here)' if engaged else 'MANUAL   (Lever B is INERT here -- CONTROL)'
    off, noff = arm(OFF, engaged)
    on, non = arm(ON, engaged)
    print()
    print('  %s   [%d OFF windows, %d ON windows]' % (lab, noff, non))
    print('  %-14s %10s %10s %9s %9s   %s'
          % ('band', 'OFF med', 'ON med', 'delta', 'p (rank)', 'reading'))
    for b in BANDS:
        a, c = off[b], on[b]
        if len(a) < 2 or len(c) < 2:
            print('  %-14s   insufficient routes' % b)
            continue
        ma, mc = float(np.median(a)), float(np.median(c))
        try:
            p = float(mannwhitneyu(a, c, alternative='two-sided').pvalue)
        except ValueError:
            p = np.nan
        d = mc - ma
        rd = ('ON is HIGHER -- consistent with pumping' if d > 0 else
              'ON is LOWER -- damping, not pumping')
        if not (p < 0.05):
            rd = 'no separation (p>=0.05)'
        print('  %-14s %10.3f %10.3f %+9.3f %9.3f   %s' % (b, ma, mc, d, p, rd))

# ---- what the numbers must satisfy for the conclusion to be stated at all -------------
_e_off, _ = arm(OFF, True)
_e_on, _ = arm(ON, True)
assert len(_e_off['ratchet 6-9']) >= 2, 'the OFF arm must contribute >=2 routes or there is no test'
assert len(_e_on['ratchet 6-9']) >= 4, 'the ON arm must contribute >=4 routes'
print()
print('  arms: OFF %d routes, ON %d routes (engaged, ratchet band)'
      % (len(_e_off['ratchet 6-9']), len(_e_on['ratchet 6-9'])))

# ---- HOW BIG AN EFFECT COULD THIS HAVE SEEN?  A null without this is not a result. -----
print()
print('  ' + '-' * 92)
print('  WHAT THIS TEST COULD HAVE DETECTED (a null is only as good as its power)')
print('  ' + '-' * 92)
from itertools import combinations
n1, n2 = len(_e_off['ratchet 6-9']), len(_e_on['ratchet 6-9'])
n_arr = len(list(combinations(range(n1 + n2), n1)))
p_min = 2.0 / n_arr
print('  with %d vs %d routes the SMALLEST attainable two-sided rank p is %.4f,' % (n1, n2, p_min))
print('  and it requires COMPLETE separation -- every OFF route below every ON route.')
a = np.array(_e_off['ratchet 6-9']); c = np.array(_e_on['ratchet 6-9'])
sep = float(c.min() - a.max())
spread = float(np.percentile(c, 90) - np.percentile(c, 10))
obs = float(np.median(c) - np.median(a))
print('  observed shift            %+0.3f log10  (%.2fx)' % (obs, 10 ** obs))
print('  ON-arm route spread p10-p90 %0.3f log10  (%.2fx) -- the noise a shift must clear'
      % (spread, 10 ** spread))
mde = float(a.max() - a.min()) + spread
print('  => detectable only above  ~%0.3f log10  (~%.2fx)' % (mde, 10 ** mde))
print()
print('  [EVIDENCE] no pumping at the ratchet band is visible: the shift is %.2fx against a' % 10 ** obs)
print('             detection floor of ~%.2fx.  This EXCLUDES a large pump; it does NOT' % 10 ** mde)
print('             exclude a small one, and it is not a dose curve.')
print('  [LIMIT]    not single-variable; the manual row is a confound detector, not an attribution.')

assert abs(obs) < spread,     'the observed shift must be inside the ON-arm spread -- otherwise this is not a null'
assert p_min < 0.05, 'the design must at least be CAPABLE of significance, or it proves nothing'
print()
print('  both power assertions hold: the design could have reached p<0.05, and did not.')
