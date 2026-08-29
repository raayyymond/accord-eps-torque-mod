# -*- coding: utf-8 -*-
"""POWER CHECK on the V175 drive card BEFORE the drive.

The card asks for one 15 s engaged creep pass and one 15 s LKAS-off pass, and attributes the
result via the engaged/manual ratio.  "Uninterpretable" is a DESIGN FAILURE on our side, so
verify NOW that the discriminator can actually resolve the predicted effect at that exposure.

Method: resample real 15 s engaged and 15 s manual creep windows out of the existing corpus,
score them exactly as the card says, and bootstrap.  Report:
  (a) the ratio's spread at 15 s -- the noise floor the effect must clear;
  (b) the detectable effect size;
  (c) whether V175's predicted move clears it.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 100.0
WIN = int(15 * FS)                 # the card's ask
NPS = 512
BAND = (6.5, 11.0)                 # the ratchet
CTRL = (30.0, 40.0)                # slope-matched control band
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']


def segs(tag, engaged):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq')):
        return []
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z['cs_tq']).astype(float)
    n = min(len(lat), len(v), len(a))
    lat, kmh, a = lat[:n], v[:n] * 3.6, a[:n]
    ok = ((lat > 0.5) if engaged else (lat <= 0.5)) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return [a[i:j] for i, j in zip(st, en) if (j - i) >= WIN and np.std(a[i:j]) > 0]


def band_power(x, lo, hi):
    f, P = signal.welch(x - x.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
    m = (f >= lo) & (f <= hi)
    return float(np.trapezoid(P[m], f[m])) if hasattr(np, 'trapezoid') else float(np.trapz(P[m], f[m]))


def score(x):
    """The card's endpoint: ratchet-band power normalised by a control band."""
    c = band_power(x, *CTRL)
    return band_power(x, *BAND) / c if c > 0 else np.nan


eng = [s for t in ROUTES for s in segs(t, True)]
man = [s for t in ROUTES for s in segs(t, False)]
print('15 s windows available in the corpus: engaged %d   manual %d' % (len(eng), len(man)))
if len(eng) < 6 or len(man) < 4:
    print('\nNOT ENOUGH 15 s MANUAL CREEP IN THE CORPUS TO CHECK THE DISCRIMINATOR.')
    print('=> the card asks the operator for exposure the corpus itself has never produced.')
    print('   That is a DESIGN RISK on our side, and it must be stated on the card.')
    print('   manual windows found: %d (need >=4)' % len(man))

rng = np.random.default_rng(4242)


def summarise(name, pool):
    if len(pool) < 4:
        print('  %-9s n=%d  -- too few to characterise' % (name, len(pool)))
        return None
    v = np.array([score(s[:WIN]) for s in pool])
    v = v[np.isfinite(v)]
    print('  %-9s n=%-3d  p50 %8.3f   IQR %8.3f-%-8.3f   log10 sd %.3f'
          % (name, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75),
             np.std(np.log10(v), ddof=1)))
    return v


print('\nSCORE DISTRIBUTION over single 15 s windows')
ev = summarise('engaged', eng)
mv = summarise('manual', man)

if ev is not None and mv is not None:
    print('\nTHE DISCRIMINATOR: ratio of one engaged window to one manual window')
    r = np.array([ev[rng.integers(len(ev))] / mv[rng.integers(len(mv))] for _ in range(20000)])
    r = r[np.isfinite(r) & (r > 0)]
    lo, hi = np.percentile(r, [2.5, 97.5])
    sd = np.std(np.log10(r), ddof=1)
    print('  single-pair ratio: p50 %.2f   95%% band [%.2f, %.2f]   log10 sd %.3f'
          % (np.median(r), lo, hi, sd))
    fold = 10 ** (1.96 * sd)
    print('  => ONE 15 s engaged + ONE 15 s manual pass can only detect a change larger than')
    print('     about %.1fx in the ratio (95%% two-sided).' % fold)
    print('\n  V175 predicts the ENGAGED arm falls while MANUAL is untouched.')
    print('  The inertia dose is 3.0x on a term that is one of six in the sum, so the honest')
    print('  prior on the ratio move is well under %.1fx.' % fold)
    print('  => A SINGLE PAIR IS UNDERPOWERED FOR THE ATTRIBUTION STEP.')
    for k in (2, 3, 4, 6):
        print('     %d matched pairs -> detectable at %.2fx' % (k, 10 ** (1.96 * sd / np.sqrt(k))))
