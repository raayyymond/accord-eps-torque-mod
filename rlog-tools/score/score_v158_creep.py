# -*- coding: utf-8 -*-
"""SCORE V158 -- the damper build -- WITH AN EPISODE BOOTSTRAP.

WHY THIS EXISTS RATHER THAN REUSING score_v133_creep.py
--------------------------------------------------------
The V158 pre-registration told the operator to reuse `score_v133_creep.py`.  That script's
contrast, guard and refusal logic are all sound and are reproduced here.  Its BOOTSTRAP is not:

    def boot(e, m, i, k=8000, seed=0):
        d = [np.median(rng.choice(e[:, i], len(e))) / ... for _ in range(k)]

`rng.choice(e[:, i], len(e))` resamples INDIVIDUAL WINDOWS.  The windows overlap by NW//2 and are
drawn from a handful of contiguous engaged/manual stretches, so they are strongly correlated and
nothing like `len(e)` independent draws.  That is a WINDOW bootstrap, and this kit has a standing
rule against exactly it:

    "Bootstrap over EPISODES, not windows -- window bootstraps manufacture significance;
     get a split-half null BEFORE quoting any ratio."   (feedback-episodes-not-windows)

A window bootstrap makes the CI too narrow in proportion to the windows-per-episode ratio, which on
a typical creep drive is 5-20x.  Scoring the V158 drive with it could turn a null into a "result".

WHAT THIS SCORER DOES DIFFERENTLY
----------------------------------
1. EPISODE BOOTSTRAP.  Windows are clustered into episodes -- maximal runs of consecutive,
   same-arm windows -- and the bootstrap resamples EPISODES with replacement, pooling their
   windows.  That is the resampling unit the data actually supports.
2. PRIMARY BAND 6-9 Hz.  V158 is a DAMPER build and the ratchet is 6-9 Hz.  18-22 Hz (grind #1)
   is kept as a secondary, since Lever B is unchanged between V122 and V158 and should NOT move.
3. PER-WINDOW SPEED CENSUS, printed.  A moving wheel order manufactures band differences; without
   the census a speed imbalance is invisible.
4. A --null SELF-TEST that split-halves ONE arm against itself.  Same firmware, same arm, so the
   honest answer is a CI spanning 1.0.  If it does not, the pipeline is manufacturing significance
   and NOTHING from a real run may be believed.

USAGE
    python rlog-tools/score/score_v158_creep.py <route> [<route> ...]
    python rlog-tools/score/score_v158_creep.py --null <route>

CACHE PAIRING -- the kit-wide defect, avoided here
   `z["t"] == z["raw14_t"][1:]` and `z["probe"] == z["raw14_b4"][1:]` in ALL caches.  Pairing `t`
   with `raw14_b4` reads the cave byte ~10 ms early = 28 deg of phase error at 7.79 Hz.  This
   scorer uses only `cc_lat`, `cs_v` and `cs_rate`, which are not part of that trap.

🛑 WITHIN-DRIVE ONLY.  The between-build noise floor on this endpoint is 20-36x.  This scores an
ENGAGED-vs-MANUAL contrast inside ONE drive.  Do NOT rank builds against each other with it; the
operator's report is the only instrument with that resolution.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS, NW = 100.0, 256
RATCHET = (6.0, 9.0)         # PRIMARY -- what V158's damper targets
GRIND = (18.0, 22.0)         # SECONDARY -- Lever B's band, unchanged V122->V158
CTL = (30.0, 40.0)           # negative control
CREEP = (1.0, 24.0)          # km/h
CTL_GUARD = (0.5, 2.0)
MIN_EPISODES = 4             # per arm; below this an episode bootstrap is meaningless


def windows(tag):
    """Return (E, M) arrays of [ratchet, grind, control, speed, window_index]."""
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
    for wi, a in enumerate(range(0, n - NW, NW // 2)):
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
        row = (P[(f >= RATCHET[0]) & (f <= RATCHET[1])].sum(),
               P[(f >= GRIND[0]) & (f <= GRIND[1])].sum(),
               P[(f >= CTL[0]) & (f <= CTL[1])].sum(), sp, wi)
        (E if eng else M).append(row)
    return np.array(E), np.array(M)


def episodes(A):
    """Group rows into maximal runs of CONSECUTIVE window indices -- the resampling unit."""
    if len(A) == 0:
        return []
    order = np.argsort(A[:, 4])
    A = A[order]
    out, cur = [], [0]
    for i in range(1, len(A)):
        if A[i, 4] == A[i - 1, 4] + 1:
            cur.append(i)
        else:
            out.append(A[cur])
            cur = [i]
    out.append(A[cur])
    return out


def speed_match(E, M):
    if len(E) < 15 or len(M) < 15:
        return None
    lo = max(np.percentile(E[:, 3], 15), np.percentile(M[:, 3], 15))
    hi = min(np.percentile(E[:, 3], 85), np.percentile(M[:, 3], 85))
    if hi <= lo:
        return None
    e = E[(E[:, 3] >= lo) & (E[:, 3] <= hi)]
    m = M[(M[:, 3] >= lo) & (M[:, 3] <= hi)]
    return (e, m, lo, hi) if len(e) >= 15 and len(m) >= 15 else None


def boot_episodes(e_eps, m_eps, col, k=8000, seed=0):
    """Resample EPISODES with replacement, pool their windows, take the median ratio."""
    rng = np.random.default_rng(seed)
    ev = np.concatenate([ep[:, col] for ep in e_eps])
    mv = np.concatenate([ep[:, col] for ep in m_eps])
    point = np.median(ev) / max(np.median(mv), 1e-30)
    d = []
    for _ in range(k):
        ei = rng.integers(0, len(e_eps), len(e_eps))
        mi = rng.integers(0, len(m_eps), len(m_eps))
        a = np.concatenate([e_eps[j][:, col] for j in ei])
        b = np.concatenate([m_eps[j][:, col] for j in mi])
        d.append(np.median(a) / max(np.median(b), 1e-30))
    return point, np.percentile(d, 2.5), np.percentile(d, 97.5)


def census(e, m, lo, hi):
    print('  speed census (km/h), the guard against a wheel-order artefact:')
    for nm, A in (('engaged', e), ('manual ', m)):
        q = np.percentile(A[:, 3], [10, 50, 90])
        print('     %s n=%3d  p10 %5.1f  p50 %5.1f  p90 %5.1f' % (nm, len(A), q[0], q[1], q[2]))
    d = abs(np.median(e[:, 3]) - np.median(m[:, 3]))
    print('     median speed gap %.2f km/h  %s'
          % (d, 'OK' if d < 1.0 else 'WARNING -- arms are not speed-matched'))


def run(tag):
    w = windows(tag)
    if w is None:
        return
    r = speed_match(*w)
    if r is None:
        print('  %s: NOT SCOREABLE -- needs >=15 ENGAGED and >=15 MANUAL creep windows at a matched'
              ' speed.  Drive the same low-speed stretch engaged AND manual.' % tag)
        return
    e, m, lo, hi = r
    e_eps, m_eps = episodes(e), episodes(m)
    print('\n=== %s : ENGAGED/MANUAL at creep, speed-matched %.0f-%.0f km/h ===' % (tag, lo, hi))
    print('  %d engaged windows in %d episodes | %d manual windows in %d episodes'
          % (len(e), len(e_eps), len(m), len(m_eps)))
    if len(e_eps) < MIN_EPISODES or len(m_eps) < MIN_EPISODES:
        print('  🛑 NOT SCOREABLE -- an episode bootstrap needs >=%d episodes per arm.' % MIN_EPISODES)
        print('     You have %d/%d.  More WINDOWS does not help; you need more separate engaged and'
              % (len(e_eps), len(m_eps)))
        print('     manual STRETCHES.  Alternate engaged and manual several times over the loop.')
        return
    census(e, m, lo, hi)
    pr, lr, hr = boot_episodes(e_eps, m_eps, 0)
    pg, lg, hg = boot_episodes(e_eps, m_eps, 1)
    pc, lc, hc = boot_episodes(e_eps, m_eps, 2)
    print('  6-9 Hz   RATCHET  (primary)  %6.2f [%5.2f, %6.2f]' % (pr, lr, hr))
    print('  18-22 Hz grind  (secondary)  %6.2f [%5.2f, %6.2f]' % (pg, lg, hg))
    print('  30-40 Hz CONTROL             %6.2f [%5.2f, %6.2f]' % (pc, lc, hc))
    if not (CTL_GUARD[0] <= pc <= CTL_GUARD[1]):
        print('  🛑 CONTROL GUARD FAILED (%.2f outside [%.1f, %.1f]) -- the contrast is a GLOBAL'
              % (pc, CTL_GUARD[0], CTL_GUARD[1]))
        print('     activity difference, not a damping result.  NOTHING may be read from it.')
        return
    print('  ✅ control is flat -- the contrast is band-specific')
    if lr <= 1.0 <= hr:
        print('  => 6-9 Hz CI spans 1.0: NOT RESOLVED.  That is "cannot resolve", NOT "unchanged".')
    else:
        print('  => 6-9 Hz engaged excess is resolved at this sample size.')
    print('  🛑 The OPERATOR\'S report is the primary endpoint.  This is a supporting instrument, and')
    print('     the between-build floor on it is 20-36x -- do not rank V158 against V122 with it.')


def null(tag):
    """Split ONE arm against itself: same firmware, same arm => the CI must span 1.0."""
    w = windows(tag)
    if w is None:
        return
    for nm, A in (('engaged', w[0]), ('manual', w[1])):
        eps = episodes(A)
        if len(eps) < 2 * MIN_EPISODES:
            print('  %s %s: only %d episodes, need >=%d for a split-half null'
                  % (tag, nm, len(eps), 2 * MIN_EPISODES))
            continue
        a, b = eps[0::2], eps[1::2]
        for col, band in ((0, '6-9 Hz'), (2, '30-40 Hz')):
            p, lo, hi = boot_episodes(a, b, col)
            ok = lo <= 1.0 <= hi
            print('  %s %-7s %-9s split-half %5.2f [%5.2f, %5.2f]  %s'
                  % (tag, nm, band, p, lo, hi,
                     'OK spans 1.0' if ok else '🛑 DOES NOT SPAN 1.0 -- pipeline is manufacturing significance'))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--null' in sys.argv[1:]:
        for t in args:
            null(t)
    elif not args:
        print(__doc__)
    else:
        for t in args:
            run(t)
