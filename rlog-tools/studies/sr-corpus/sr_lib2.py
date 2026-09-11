# -*- coding: utf-8 -*-
"""sr_lib2.py -- the CORRECTED estimator suite, after the adversarial pass.

WHAT CHANGED AND WHY
  1. FREE-INTERCEPT JOINT FIT is now the primary.  `liveParameters.angleOffsetDeg` is a paramsd
     Kalman output estimated JOINTLY WITH A STEER RATIO, so subtracting it makes the estimator
     partly circular.  Fit instead
         radians(steeringAngleDeg_RAW) = sR * u + off,      u = denom / curvature_factor
     estimating sR and off together.  Nothing from paramsd's angle offset enters.
  2. THREE ESTIMATORS, always.  TLS, OLS(y|u), and OLS(u|y) inverted.  They coincide only when the
     noise is small relative to the spread of u; where they disagree the bin is NOT a measurement.
  3. BOOTSTRAP REFUSES thin bins.  A cluster bootstrap over 2 clusters reports a zero-width
     interval, which is worse than no interval.  MIN_CLUSTERS is enforced and `None` is returned.
  4. STEADY-STATE EPISODES.  A ratio is a static relation; a slope through sub-second transits is
     not a measurement of it.  `episodes()` finds windows where |sa| and v are flat and the wheel
     is slow, and reports count / total / longest so a bin can be disqualified on episode length.
  5. LEAD/LAG SWEEP.  A genuine static ratio has a STATIONARY POINT in a +-300 ms shift of the
     angle against the yaw rate.  Monotone sliding means the bin is being carried by transits.
"""
import numpy as np

FS = 100.0
MIN_CLUSTERS = 20          # below this a cluster bootstrap is decorative -- refuse it
MIN_SAMPLES = 200


# ----------------------------------------------------------------------------- estimators
def fit3(u, y, intercept=True):
    """Return dict with tls / ols_y / ols_u_inv slopes (and offsets when intercept=True).

    Model: y = sR*u + off.  With intercept the three estimators are computed on centred data
    and the offset recovered as mean(y) - sR*mean(u)."""
    u = np.asarray(u, np.float64); y = np.asarray(y, np.float64)
    m = np.isfinite(u) & np.isfinite(y)
    u, y = u[m], y[m]
    n = len(u)
    if n < MIN_SAMPLES:
        return None
    if intercept:
        mu, my = u.mean(), y.mean()
        uc, yc = u - mu, y - my
    else:
        mu = my = 0.0
        uc, yc = u, y
    suu = float(uc @ uc); suy = float(uc @ yc); syy = float(yc @ yc)
    if suu <= 0 or suy == 0:
        return None
    ols_y = suy / suu                       # regress y on u  (attenuated by noise in u)
    ols_u = syy / suy                       # regress u on y, inverted (inflated by noise in y)
    tr = suu + syy
    disc = np.sqrt(max((suu - syy) ** 2 + 4.0 * suy * suy, 0.0))
    lam = 0.5 * (tr - disc)
    tls = -suy / (lam - suu)
    out = dict(n=n, tls=float(tls), ols_y=float(ols_y), ols_u=float(ols_u),
               spread=float(abs(ols_u - ols_y)))
    out["off"] = float(my - out["tls"] * mu) if intercept else 0.0
    out["cond"] = float(np.std(uc) / (np.std(yc - out["tls"] * uc) / max(abs(out["tls"]), 1e-9)))
    return out


def moments(u, y, clus):
    """per-cluster (n, Su, Sy, Suu, Suy, Syy) so a bootstrap with intercept is O(n_clusters)."""
    u = np.asarray(u, np.float64); y = np.asarray(y, np.float64)
    uq, inv = np.unique(clus, return_inverse=True)
    nb = len(uq)
    b = lambda w: np.bincount(inv, weights=w, minlength=nb)
    return (np.bincount(inv, minlength=nb).astype(float),
            b(u), b(y), b(u * u), b(u * y), b(y * y))


def _tls_from_moments(N, Su, Sy, Suu, Suy, Syy, intercept=True):
    if intercept:
        suu = Suu - Su * Su / N
        suy = Suy - Su * Sy / N
        syy = Syy - Sy * Sy / N
    else:
        suu, suy, syy = Suu, Suy, Syy
    tr = suu + syy
    disc = np.sqrt(np.maximum((suu - syy) ** 2 + 4.0 * suy * suy, 0.0))
    lam = 0.5 * (tr - disc)
    with np.errstate(divide="ignore", invalid="ignore"):
        return -suy / (lam - suu)


def boot(u, y, clus, nboot=600, seed=1, intercept=True, min_clusters=MIN_CLUSTERS):
    """cluster bootstrap CI, or None when there are too few clusters to mean anything."""
    N, Su, Sy, Suu, Suy, Syy = moments(u, y, clus)
    nb = len(N)
    if nb < min_clusters:
        return None, nb
    rng = np.random.default_rng(seed)
    p = rng.integers(0, nb, size=(nboot, nb))
    s = _tls_from_moments(N[p].sum(1), Su[p].sum(1), Sy[p].sum(1),
                          Suu[p].sum(1), Suy[p].sum(1), Syy[p].sum(1), intercept)
    s = s[np.isfinite(s)]
    if len(s) < nboot // 4:
        return None, nb
    return (float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))), nb


# ----------------------------------------------------------------------------- episodes
def episodes(t, asa, v, rate, lo, hi, flat=0.25, rate_max=25.0, min_s=0.6, max_gap=0.05):
    """Steady-state windows inside the angle band [lo, hi).

    A sample qualifies when |sa| is in band, |rate| < rate_max, and v > 4.  A RUN of qualifying
    samples (contiguous in time to within max_gap) becomes an EPISODE when it lasts >= min_s AND
    |sa| stays inside +-flat of its run median AND v stays inside +-flat of its run median.
    A long run that violates flatness is SPLIT, not discarded: the longest compliant sub-run is
    kept by trimming from the ends.
    Returns (list of (i0, i1) index pairs, mask of qualifying samples).
    """
    q = (asa >= lo) & (asa < hi) & (np.abs(rate) < rate_max) & (v > 4.0) & np.isfinite(asa)
    idx = np.flatnonzero(q)
    if len(idx) == 0:
        return [], q
    brk = np.flatnonzero((np.diff(idx) != 1) | (np.diff(t[idx]) > max_gap))
    starts = np.r_[0, brk + 1]
    ends = np.r_[brk + 1, len(idx)]
    eps = []
    for a, b in zip(starts, ends):
        run = idx[a:b]
        while len(run) > 1:
            dur = t[run[-1]] - t[run[0]]
            if dur < min_s:
                break
            ma, mv = np.median(asa[run]), np.median(v[run])
            oka = np.abs(asa[run] - ma) <= flat * ma
            okv = np.abs(v[run] - mv) <= flat * max(mv, 1e-6)
            ok = oka & okv
            if ok.all():
                eps.append((run[0], run[-1]))
                break
            # trim the longest compliant contiguous stretch
            d = np.diff(np.r_[0, ok.astype(int), 0])
            s2 = np.flatnonzero(d == 1); e2 = np.flatnonzero(d == -1)
            if len(s2) == 0:
                break
            k = int(np.argmax(e2 - s2))
            run = run[s2[k]:e2[k]]
    return eps, q


def episode_stats(t, eps):
    if not eps:
        return dict(n_ep=0, total_s=0.0, longest_s=0.0, med_s=0.0)
    d = np.array([t[b] - t[a] for a, b in eps], float)
    return dict(n_ep=len(eps), total_s=float(d.sum()), longest_s=float(d.max()),
                med_s=float(np.median(d)))


# ----------------------------------------------------------------------------- lead/lag
def leadlag(ang_rad, u_of_shift, shifts_ms, intercept=True):
    """slope vs applied shift.  `u_of_shift` is a callable ms -> u array aligned with ang_rad."""
    out = []
    for s in shifts_ms:
        u = u_of_shift(s)
        r = fit3(u, ang_rad, intercept=intercept)
        out.append(np.nan if r is None else r["tls"])
    return np.asarray(out, float)


def stationary(shifts, vals, edge_frac=0.15):
    """Is there an interior stationary point?  Returns (verdict, argmin/argmax position).

    A static ratio has a plateau/turning point inside the sweep; a transit-carried bin slides
    monotonically.  Test: the extremum of |d slope/d shift| ... simpler and more robust -- check
    whether the slope is monotone across the sweep, and where the turning point sits."""
    v = np.asarray(vals, float)
    s = np.asarray(shifts, float)
    ok = np.isfinite(v)
    if ok.sum() < 5:
        return "insufficient", np.nan, np.nan
    v, s = v[ok], s[ok]
    d = np.diff(v)
    mono = np.all(d > 0) or np.all(d < 0)
    rng = float(v.max() - v.min())
    # turning point = where the curve reverses
    k = int(np.argmax(v)) if v[0] < v[-1] else int(np.argmin(v))
    interior = (k > edge_frac * len(v)) and (k < (1 - edge_frac) * len(v))
    if mono:
        return "MONOTONE (no stationary point)", rng, np.nan
    if interior:
        return "STATIONARY at %+.0f ms" % s[k], rng, float(s[k])
    return "turning point AT THE EDGE", rng, float(s[k])


def _selfcheck():
    rng = np.random.default_rng(3)
    # fit3 recovers a planted slope + offset, and the three estimators agree when noise is small
    n = 50000
    u = rng.uniform(-0.05, 0.05, n)
    off = np.radians(-4.1)
    y = 15.5 * u + off + rng.normal(0, 1e-4, n)
    r = fit3(u, y)
    assert abs(r["tls"] - 15.5) < 0.02 and abs(np.degrees(r["off"]) + 4.1) < 0.02, r
    assert r["spread"] < 0.05, r
    # with heavy noise in u the three estimators must SEPARATE (this is the whole point of #3)
    y2 = 15.5 * (u + rng.normal(0, 0.02, n)) + off
    r2 = fit3(u, y2)
    assert r2["spread"] > 1.0, r2
    # bootstrap refuses too few clusters
    ci, nb = boot(u, y, rng.integers(0, 5, n))
    assert ci is None and nb == 5
    ci, nb = boot(u, y, rng.integers(0, 200, n))
    assert ci is not None and ci[0] < 15.5 < ci[1]
    # episodes: a planted 3 s steady window is found, a 0.2 s transit is not
    t = np.arange(0, 20, 0.01)
    asa = np.full_like(t, 5.0); v = np.full_like(t, 10.0); rate = np.zeros_like(t)
    asa[500:800] = 200.0                      # 3.0 s steady at 200 deg
    asa[1200:1220] = 200.0                     # 0.2 s transit
    eps, _ = episodes(t, asa, v, rate, 150, 250)
    st = episode_stats(t, eps)
    assert st["n_ep"] == 1 and abs(st["longest_s"] - 2.99) < 0.05, st
    return True


if __name__ == "__main__":
    print("sr_lib2 self-check:", _selfcheck())
