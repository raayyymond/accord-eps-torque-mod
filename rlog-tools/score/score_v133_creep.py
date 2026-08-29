# -*- coding: utf-8 -*-
"""SCORE V133 ON THE ONE ENDPOINT THAT SURVIVES THIS KIT'S NOISE FLOOR.

THE PROBLEM THIS SOLVES
------------------------
Every BETWEEN-ROUTE endpoint this kit uses is swamped by route variance:
    band amplitude   same-firmware routes span 8x  (0.047-0.389 within one gain group)
    mode frequency   f0 spans 10 Hz within one gain group, vs a ~1.3 Hz predicted dose effect
So a gp-0x6b26 build cannot be scored between routes at all, and the 8x/6x gain-vs-grind test and
the openpilot-compensation test both died on the same wall.

THE FIX: the operator's symptom is ENGAGED-ONLY, so the two arms can come from ONE drive.
An ENGAGED-vs-MANUAL contrast at matched speed inside a single route cancels road, tyres, weather,
alignment and the speed profile -- everything that makes routes incomparable.

IT IS ALREADY VALIDATED ON EXISTING DATA
------------------------------------------
    route  build   speed band      18-22 Hz eng/man        30-40 Hz CONTROL
    r22    V112    5-15 km/h    7.10 [ 2.51, 16.62]      1.12 [0.67, 2.32]   control FLAT
    r24    V122    6-17 km/h    3.88 [ 1.63, 10.08]      0.61 [0.33, 2.82]   control FLAT
  * it is BAND-SPECIFIC on both (signal moves, control does not);
  * and it TRACKS THE OPERATOR: V112 -> V122 nearly halved the engaged excess (7.10 -> 3.88),
    exactly when he reported grinding "better, still ever so slight ... in rare moments".
A statistic that moved with his verdict, within-drive, is the best endpoint this kit has for the
remaining low-speed symptom.

WHAT THE DRIVE MUST CONTAIN -- THIS IS A DRIVE-DESIGN REQUIREMENT, NOT A WISH
------------------------------------------------------------------------------
Both arms must exist AT THE SAME LOW SPEED:
    * ENGAGED creep, 2-10 mph, hands off, with real steering activity;
    * MANUAL creep over the SAME stretch at the SAME speed.
Drive the same low-speed loop twice, once engaged and once manual.  Without both arms this script
has nothing to contrast and will say so rather than guess.

PRE-REGISTERED, BEFORE ANY V133 FLIGHT
----------------------------------------
Primary: ENGAGED/MANUAL 18-22 Hz ratio at creep, speed-matched, vs V122's 3.88 [1.63, 10.08].
    ratio <= 1.6   -> the engaged excess is GONE      => Lever A reproduced
    1.6 - 3.0      -> reduced but present             => partial
    > 3.0          -> unchanged vs V122               => Lever A did NOT reproduce
MANDATORY GUARD: the 30-40 Hz control must stay within [0.5, 2.0].  If the control moves with the
signal the contrast is a global activity difference, not a grind result, and NOTHING may be read
from it -- that is exactly how the b26 relay hypothesis died earlier this session.

USAGE:  python rlog-tools/score/score_v133_creep.py <route> [reference_route]
        python rlog-tools/score/score_v133_creep.py --validate     (reproduces r22 / r24 above)


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
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS, NW = 100.0, 256
SIG = (18.0, 22.0)          # the creep grind band -- dominant at low speed (absolute power 3.849)
CTL = (30.0, 40.0)          # negative control
CREEP = (1.0, 24.0)         # km/h
CTL_GUARD = (0.5, 2.0)
V122_REF = (3.88, 1.63, 10.08)


def windows(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  no cache for %s' % tag)
        return None
    z = np.load(p, allow_pickle=True)
    g = lambda k: np.asarray(z[k]).astype(float) if k in z.files else None
    lat, v, rate = g('cc_lat'), g('cs_v'), g('cs_rate')
    if any(x is None for x in (lat, v, rate)):
        print('  %s: missing cc_lat / cs_v / cs_rate' % tag)
        return None
    n = min(map(len, (lat, v, rate)))
    lat, v, rate = lat[:n], v[:n], rate[:n]
    E, M = [], []
    for a in range(0, n - NW, NW // 2):
        s = slice(a, a + NW)
        sp = v[s].mean() * 3.6
        if not (CREEP[0] <= sp < CREEP[1]):
            continue
        eng, man = lat[s].mean() > 0.99, lat[s].mean() < 0.01
        if not (eng or man):
            continue
        r = rate[s]
        if not np.isfinite(r).all() or r.std() == 0:
            continue
        f, P = signal.welch(r - r.mean(), FS, nperseg=NW // 2)
        row = (P[(f >= SIG[0]) & (f <= SIG[1])].sum(),
               P[(f >= CTL[0]) & (f <= CTL[1])].sum(), sp)
        (E if eng else M).append(row)
    return np.array(E), np.array(M)


def speed_match(E, M):
    if len(E) < 15 or len(M) < 15:
        return None
    lo = max(np.percentile(E[:, 2], 15), np.percentile(M[:, 2], 15))
    hi = min(np.percentile(E[:, 2], 85), np.percentile(M[:, 2], 85))
    if hi <= lo:
        return None
    e = E[(E[:, 2] >= lo) & (E[:, 2] <= hi)]
    m = M[(M[:, 2] >= lo) & (M[:, 2] <= hi)]
    return (e, m, lo, hi) if len(e) >= 15 and len(m) >= 15 else None


def boot(e, m, i, k=8000, seed=0):
    rng = np.random.default_rng(seed)
    d = [np.median(rng.choice(e[:, i], len(e))) / max(np.median(rng.choice(m[:, i], len(m))), 1e-30)
         for _ in range(k)]
    return (np.median(e[:, i]) / max(np.median(m[:, i]), 1e-30),
            np.percentile(d, 2.5), np.percentile(d, 97.5))


def run(tag, quiet=False):
    w = windows(tag)
    if w is None:
        return None
    r = speed_match(*w)
    if r is None:
        print('  %s: NOT SCOREABLE -- needs >=15 ENGAGED and >=15 MANUAL creep windows at a'
              ' matched speed.  Drive the same low-speed stretch engaged AND manual.' % tag)
        return None
    e, m, lo, hi = r
    ps, ls, hs = boot(e, m, 0)
    pc, lc, hc = boot(e, m, 1)
    if not quiet:
        print('\n=== %s : ENGAGED/MANUAL at creep, speed-matched %.0f-%.0f km/h ===' % (tag, lo, hi))
        print('  %d engaged vs %d manual windows' % (len(e), len(m)))
        print('  18-22 Hz  eng/man   %6.2f [%5.2f, %6.2f]' % (ps, ls, hs))
        print('  30-40 Hz  CONTROL   %6.2f [%5.2f, %6.2f]' % (pc, lc, hc))
    ok = CTL_GUARD[0] <= pc <= CTL_GUARD[1]
    if not quiet:
        if not ok:
            print('  🛑 CONTROL GUARD FAILED (%.2f outside [%.1f, %.1f]) -- the contrast is a GLOBAL'
                  % (pc, *CTL_GUARD))
            print('     activity difference, not a grind result.  NOTHING may be read from it.')
        else:
            print('  ✅ control is flat -- the contrast is band-specific')
            print('\n  vs V122 reference %.2f [%.2f, %.2f]:' % V122_REF)
            v = ('GONE -- Lever A reproduced' if ps <= 1.6 else
                 'REDUCED but present -- partial' if ps <= 3.0 else
                 'UNCHANGED vs V122 -- Lever A did NOT reproduce')
            print('     ratio %.2f  =>  %s' % (ps, v))
    return ps, pc, ok


if '--validate' in sys.argv[1:]:
    print('  VALIDATION: reproducing the r22 (V112) and r24 (V122) reference values.')
    print('  Expect ~7.10 and ~3.88 with flat controls; V112 -> V122 should HALVE, tracking the')
    print('  operator\'s "better, rare moments" verdict.')
    for t in ('r22', 'r24'):
        run(t)
else:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    for t in (args or ['r25']):
        run(t)
