# -*- coding: utf-8 -*-
"""BAND CONTRAST -- the safe path made the easy path. Never returns a ratio without a CI.

    from band_contrast import band_contrast, episodes
    r = band_contrast(a_episodes, b_episodes)      # -> Contrast(ratio, lo, hi, n_a, n_b, licensed)
    print(r)                                        # refuses to print a bare number

WHY THIS EXISTS, IN ONE PARAGRAPH. On 2026-08-30 an agent wrote a MIN_EPISODES=8 guard into the
pre-registered scorer to stop under-powered comparisons being read as evidence -- and then, within the
hour, bypassed it twice by computing `np.median(A) - np.median(B)` inline, and reported both results as
findings. Both had to be withdrawn: one CI was [-0.331, +0.160], spanning zero, on 7 episodes. The
failure was not carelessness, it was ERGONOMICS: an inline median is three characters, calling the
scorer is a subprocess. This module makes the correct thing the shortest thing.

THE RULE IT ENFORCES, which is the kit's own standing instruction:
    "Bootstrap over EPISODES, not windows -- window bootstraps manufacture significance.
     Get a CI before quoting any ratio."

WHAT IT REFUSES:
  * fewer than MIN_EPISODES per arm  -> licensed=False, and str() says so instead of a number
  * a CI spanning 1.0               -> licensed=False, "licenses NOTHING"
It still returns the numbers, so an caller can inspect them -- it just will not let a bare ratio be
printed as if it meant something.
"""
import numpy as np

MIN_EPISODES = 8
N_BOOT = 5000
EPISODE_S = 20.0
_RNG = np.random.default_rng(20260830)


class Contrast(object):
    """A ratio that knows whether it is licensed. str() refuses to lie."""

    __slots__ = ('ratio', 'lo', 'hi', 'n_a', 'n_b', 'licensed', 'why')

    def __init__(self, ratio, lo, hi, n_a, n_b):
        self.ratio, self.lo, self.hi, self.n_a, self.n_b = ratio, lo, hi, n_a, n_b
        if min(n_a, n_b) < MIN_EPISODES:
            self.licensed, self.why = False, ('under-powered: %d/%d episodes, need %d per arm'
                                              % (n_a, n_b, MIN_EPISODES))
        elif lo <= 1.0 <= hi:
            self.licensed, self.why = False, 'CI spans 1.0 -- licenses NOTHING'
        else:
            self.licensed, self.why = True, 'CI excludes 1.0'

    def __str__(self):
        head = '%.3f  [%.3f, %.3f]  n=%d/%d' % (self.ratio, self.lo, self.hi, self.n_a, self.n_b)
        return head + ('  LICENSED' if self.licensed else '  NOT LICENSED -- ' + self.why)

    __repr__ = __str__


def band_contrast(a, b, n_boot=N_BOOT):
    """b/a as a ratio with an EPISODE-level bootstrap CI. a, b are per-episode log10 values."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) == 0 or len(b) == 0:
        return Contrast(float('nan'), float('nan'), float('nan'), len(a), len(b))
    point = 10 ** (np.median(b) - np.median(a))
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = (np.median(_RNG.choice(b, len(b), True))
                   - np.median(_RNG.choice(a, len(a), True)))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return Contrast(point, 10 ** lo, 10 ** hi, len(a), len(b))


def episodes(values, fs, mask=None, episode_s=EPISODE_S):
    """Split a per-sample series into contiguous fixed-length episode means.

    Episodes, not windows: samples inside one episode are not independent, so resampling windows
    manufactures significance. `mask` (e.g. engaged & moving) is applied BEFORE splitting, and only
    contiguous runs are used.
    """
    v = np.asarray(values, float)
    n = max(2, int(round(episode_s * fs)))
    idx = np.flatnonzero(np.ones(len(v), bool) if mask is None else np.asarray(mask, bool))
    if not len(idx):
        return np.array([])
    out = []
    for run in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        for k in range(0, len(run) - n + 1, n):
            w = v[run[k:k + n]]
            w = w[np.isfinite(w)]
            if len(w):
                out.append(float(w.mean()))
    return np.array(out)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print('=' * 84)
    print('  BAND CONTRAST -- self-test')
    print('=' * 84)
    rng = np.random.default_rng(1)
    fails = 0
    # a real 2x effect, well exposed -> licensed and recovered
    a = np.log10(rng.lognormal(0, 0.3, 40))
    b = np.log10(rng.lognormal(0, 0.3, 40) * 2.0)
    c = band_contrast(a, b)
    ok = c.licensed and c.lo <= 2.0 <= c.hi
    print('  real 2x, n=40/40      : %s   %s' % (c, 'OK' if ok else 'FAIL'))
    fails += not ok
    # no effect -> NOT licensed
    c = band_contrast(np.log10(rng.lognormal(0, 0.3, 40)), np.log10(rng.lognormal(0, 0.3, 40)))
    ok = not c.licensed
    print('  no effect, n=40/40    : %s   %s' % (c, 'OK' if ok else 'FAIL'))
    fails += not ok
    # the real case that caused this module: 7 episodes -> REFUSED regardless of the point estimate
    c = band_contrast(np.log10(rng.lognormal(0, 0.3, 7)), np.log10(rng.lognormal(0, 0.3, 24) * 1.5))
    ok = (not c.licensed) and 'under-powered' in c.why
    print('  7 vs 24 episodes      : %s   %s' % (c, 'OK' if ok else 'FAIL'))
    fails += not ok
    assert fails == 0, '%d self-test failures' % fails
    print()
    print('  all pass. A ratio from this module cannot be printed without its verdict.')
