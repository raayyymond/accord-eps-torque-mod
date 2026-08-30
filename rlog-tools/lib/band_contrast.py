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

CLUSTERING -- added 2026-08-30, after the same failure recurred ONE NESTING LEVEL UP. Testing whether
notch phase moves Re(Z), an episode-level bootstrap gave -8.53 [-14.62, -0.58], excluding zero. But the
113 episodes in one arm came from 3 routes and the 334 in the other from 14, and episodes inside a
route are no more independent than windows inside an episode. Re-run with the ROUTE as the unit, the
result was +1.77 [-21.87, +10.53] -- CI spanning zero, and the point estimate FLIPPED SIGN.

  RULE: when the arms differ by BUILD or by ROUTE, the route is the unit of randomisation, not the
  episode. Pass `cluster=` and the bootstrap resamples clusters. Omitting it when arms span multiple
  routes manufactures significance exactly the way window bootstraps do.

`band_contrast(a, b)` still bootstraps episodes -- correct when both arms come from ONE route (e.g. two
bands of the same drive). `band_contrast(a, b, cluster_a=..., cluster_b=...)` bootstraps routes.
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


def _resample(vals, clusters, rng):
    """One bootstrap draw. Without clusters, resample values; with them, resample WHOLE clusters."""
    if clusters is None:
        return rng.choice(vals, len(vals), True)
    keys = np.unique(clusters)
    drawn = rng.choice(keys, len(keys), True)
    return np.concatenate([vals[clusters == k] for k in drawn])


def band_contrast(a, b, n_boot=N_BOOT, cluster_a=None, cluster_b=None):
    """b/a as a ratio with a bootstrap CI. a, b are per-episode log10 values.

    cluster_a / cluster_b: per-episode labels (route tags) naming which cluster each episode came
    from. Pass them WHENEVER the two arms span different routes or builds -- the route is then the
    unit of randomisation and whole routes are resampled. Omitting them in that case gives a CI that
    is too narrow, and can flip the sign of the point estimate. See the module docstring.
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ca = None if cluster_a is None else np.asarray(cluster_a)
    cb = None if cluster_b is None else np.asarray(cluster_b)
    for v, c, nm in ((a, ca, 'a'), (b, cb, 'b')):
        if c is not None and len(c) != len(v):
            raise ValueError('cluster_%s has %d labels for %d values' % (nm, len(c), len(v)))
    ka = np.isfinite(a); kb = np.isfinite(b)
    if ca is not None:
        ca = ca[ka]
    if cb is not None:
        cb = cb[kb]
    a = a[ka]; b = b[kb]
    if len(a) == 0 or len(b) == 0:
        return Contrast(float('nan'), float('nan'), float('nan'), len(a), len(b))
    point = 10 ** (np.median(b) - np.median(a))
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = (np.median(_resample(b, cb, _RNG))
                   - np.median(_resample(a, ca, _RNG)))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    n_a = len(a) if ca is None else len(np.unique(ca))
    n_b = len(b) if cb is None else len(np.unique(cb))
    return Contrast(point, 10 ** lo, 10 ** hi, n_a, n_b)


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
    # CLUSTERING: 3 routes vs 13, a real per-route offset. Episode-level says LICENSED (too narrow);
    # route-level must NOT, because 3 clusters cannot support the claim.
    ra = np.repeat(np.arange(13), 26)
    rb = np.repeat(np.arange(100, 103), 38)
    va = np.log10(rng.lognormal(0, 0.25, len(ra)) * np.repeat(rng.lognormal(0, 0.35, 13), 26))
    vb = np.log10(rng.lognormal(0, 0.25, len(rb)) * np.repeat(rng.lognormal(0, 0.35, 3), 38))
    flat = band_contrast(va, vb)
    clus = band_contrast(va, vb, cluster_a=ra, cluster_b=rb)
    ok = clus.hi / clus.lo > flat.hi / flat.lo and not clus.licensed
    print('  episode-level          : %s' % flat)
    print('  route-clustered        : %s   %s' % (clus, 'OK' if ok else 'FAIL'))
    fails += not ok
    assert fails == 0, '%d self-test failures' % fails
    print()
    print('  all pass. A ratio from this module cannot be printed without its verdict.')
