# -*- coding: utf-8 -*-
"""SCORE V131's GRIND ENDPOINT against the build the operator last drove.

V131 restores V62's rate lane BYTE-FOR-BYTE (all six cells: arms 0xC643E/0xC6440/0xC6446 and
sars 0x3AB70/0x3AB76/0x3AC20).  V62 measured, on route 37, engaged creep, speed-standardised,
EPISODE-clustered:

    18-22 Hz  V62/V59 = 0.124 [0.036, 0.387]                  =  8x better
    at |rate| 16-32 deg/s = 0.024 [0.016, 0.234]              = 42x better
    30-40 Hz NEGATIVE CONTROL ~ 1.0                           => band-specific, not global

Route 37 is not in this kit's cache, so the comparator here is r24 (V122) -- the build the
operator actually last drove and reported on.  The question this answers is therefore the one
that matters: IS V131 BETTER THAN WHAT YOU LAST DROVE, in the band V62 moved?

METHOD -- deliberately the same as V62's, because the comparison is only meaningful if it is
  * ENGAGED only, and speed-MATCHED between the two routes (a moving speed distribution
    manufactures band ratios -- accord-averaged-spectrum-needs-matched-speed-distributions);
  * bootstrapped over EPISODES, never windows (feedback-episodes-not-windows: window bootstraps
    manufacture significance);
  * reported with a 30-40 Hz NEGATIVE CONTROL.  A ratio that moves in the signal band AND in the
    control band is a global change, not a grind result;
  * stratified by |rate|, because accord-ratchet-axis-is-wheel-rate showed the ratchet's axis is
    WHEEL RATE, not speed.

NULL CONTROL, built in: `--null` scores r22 vs r23, which are BOTH V112.  Same firmware, so
every ratio must come back ~1.0 with a CI spanning 1.  If it does not, the estimator is broken
and no V131 number from it means anything.  Run it whenever this file changes.

USAGE:
    python rlog-tools/score/score_v131_grind.py <new_route> [reference_route]
    python rlog-tools/score/score_v131_grind.py --null


🛑 BETWEEN-BUILD NOISE FLOOR: 20-36x.  Six routes with IDENTICAL control cals
   (gain 3564, a2 22, knee 600, K1 204) span 2.60 to 51.81 = 19.9x; another six span 36.2x.
   => NO comparison of two BUILDS on this endpoint carries information below ~36x.
   This scorer is valid for WITHIN-DRIVE engaged-vs-manual contrast only.  Do NOT use it
   to rank builds against each other; the operator report is the only instrument with the
   resolution to do that.
"""
import os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS, NW = 100.0, 256           # carState timebase; 2.56 s windows
BANDS = [('18-22 Hz  (V62 endpoint)', 18.0, 22.0),
         ('21-26 Hz  (grind #1)', 21.0, 26.0),
         ('6-9 Hz    (ratchet)', 6.0, 9.0),
         ('30-40 Hz  NEG CONTROL', 30.0, 40.0)]
RATE_STRATA = [('all', 0.0, 1e9), ('16-32 deg/s (V62 best cell)', 16.0, 32.0)]


def load(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  no cache for %s' % tag)
        return None
    z = np.load(p, allow_pickle=True)
    g = lambda k: np.asarray(z[k]).astype(float) if k in z.files else None
    d = dict(t=g('t'), rate=g('cs_rate'), lat=g('cc_lat'), v=g('cs_v'))
    if any(x is None for x in d.values()):
        print('  %s: missing a required channel' % tag)
        return None
    return d


def windows(d, vlo, vhi):
    """engaged windows inside a speed band; returns (episode_id, band_shares, |rate| p50)."""
    n = len(d['t'])
    out = []
    ep, last = -1, -10 ** 9
    for a in range(0, n - NW, NW // 2):
        s = slice(a, a + NW)
        if d['lat'][s].mean() < 0.99:
            continue
        vv = d['v'][s].mean() * 3.6
        if not (vlo <= vv < vhi):
            continue
        r = d['rate'][s]
        if not np.isfinite(r).all() or r.std() == 0:
            continue
        f, P = signal.welch(r - r.mean(), FS, nperseg=NW // 2)
        tot = P[(f >= 1) & (f <= 45)].sum()
        if tot <= 0:
            continue
        sh = [P[(f >= lo) & (f <= hi)].sum() / tot for _, lo, hi in BANDS]
        if a - last > NW:                       # a gap => a new episode
            ep += 1
        last = a
        out.append((ep, sh, float(np.percentile(np.abs(r), 50))))
    return out


def boot_ratio(A, B, k=4000, seed=0):
    """episode-clustered bootstrap of median(A)/median(B) per band."""
    if not A or not B:
        return None
    rng = np.random.default_rng(seed)
    ea, eb = sorted({x[0] for x in A}), sorted({x[0] for x in B})
    if len(ea) < 3 or len(eb) < 3:
        return None
    byA = {e: [x[1] for x in A if x[0] == e] for e in ea}
    byB = {e: [x[1] for x in B if x[0] == e] for e in eb}
    nb = len(BANDS)
    pt = [np.median([s[i] for s in (x[1] for x in A)]) /
          max(np.median([s[i] for s in (x[1] for x in B)]), 1e-30) for i in range(nb)]
    draws = np.empty((k, nb))
    for j in range(k):
        sa = [s for e in rng.choice(ea, len(ea)) for s in byA[e]]
        sb = [s for e in rng.choice(eb, len(eb)) for s in byB[e]]
        for i in range(nb):
            mb = np.median([s[i] for s in sb])
            draws[j, i] = np.median([s[i] for s in sa]) / max(mb, 1e-30)
    return pt, np.percentile(draws, 2.5, axis=0), np.percentile(draws, 97.5, axis=0)


def run(new, ref, label=''):
    A, B = load(new), load(ref)
    if A is None or B is None:
        return
    # speed-match on the OVERLAP of the two engaged speed distributions
    def spd(d):
        m = d['lat'] > 0.99
        return np.percentile(d['v'][m] * 3.6, [20, 80]) if m.sum() else (0, 0)
    a20, a80 = spd(A); b20, b80 = spd(B)
    lo, hi = max(a20, b20), min(a80, b80)
    if hi <= lo:
        print('  the two routes do not overlap in engaged speed -- not comparable')
        return
    print('\n=== %s%s vs %s ===' % (label, new, ref))
    print('  speed-matched engaged band: %.0f-%.0f km/h' % (lo, hi))
    for sname, rlo, rhi in RATE_STRATA:
        wa = [w for w in windows(A, lo, hi) if rlo <= w[2] < rhi]
        wb = [w for w in windows(B, lo, hi) if rlo <= w[2] < rhi]
        print('\n  |rate| %-28s  %s n=%d (%d ep)   %s n=%d (%d ep)'
              % (sname, new, len(wa), len({x[0] for x in wa}), ref, len(wb), len({x[0] for x in wb})))
        r = boot_ratio(wa, wb)
        if r is None:
            print('     too few episodes for an episode-clustered bootstrap')
            continue
        pt, cl, ch = r
        for i, (bn, _, _) in enumerate(BANDS):
            mark = ''
            if 'NEG CONTROL' in bn:
                mark = '   <- must stay ~1.0, else the change is GLOBAL not band-specific'
            elif ch[i] < 1.0:
                mark = '   <- IMPROVED'
            elif cl[i] > 1.0:
                mark = '   <- WORSE'
            print('     %-26s ratio %6.3f [%6.3f, %6.3f]%s' % (bn, pt[i], cl[i], ch[i], mark))


args = [a for a in sys.argv[1:] if not a.startswith('--')]
if '--null' in sys.argv[1:]:
    print('  NULL CONTROL: r22 and r23 are BOTH V112 -- every ratio must be ~1.0 with a CI')
    print('  spanning 1.  A ratio that excludes 1 here means the ESTIMATOR is broken.')
    run('r22', 'r23', label='NULL ')
else:
    run(args[0] if args else 'r25', args[1] if len(args) > 1 else 'r24')
