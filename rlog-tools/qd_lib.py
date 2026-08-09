#!/usr/bin/env python3
"""Shared instrument for the V86 ~8 Hz DAMPING re-score.

WHY A NEW FILE AND NOT `C31.q_of`:  `C31.q_of` walks out from the peak only while the spectrum is
MONOTONE DECREASING, so on any noisy spectrum it stops at the first wiggle and returns f0/binwidth.
It returns Q ~ 28.7 on white noise.  Nothing here calls it.

WHAT THIS MEASURES.  For a self-sustained limit cycle the LINEWIDTH is not the modal damping -- it
is the phase-coherence time.  Both are reported, kept apart, each with its own instrument floor:

  q_app  = f0 / FWHM (floor-subtracted half-power)   bounded above by the WINDOW; comparable ONLY
                                                     between windows of the SAME length T
  q_max  = f0 / (1.4416 / T)                         the Hann main-lobe floor for that T
  tau_env, duty, burst_s, cv                         envelope/amplitude-relaxation observables --
                                                     1-3 s timescales, NOT window-limited
"""
import numpy as np
from scipy.signal import butter, filtfilt, hilbert

HANN_FWHM = 1.4416          # Hann main-lobe FWHM in fs/N units for a pure tone
FLO, FHI = 5.0, 11.0
PAD = 16


def contiguous_runs(mask, t, min_n, max_gap=0.05):
    """Contiguous runs of `mask` with no sample gap > max_gap.  SEGMENT-AGNOSTIC on purpose: the
    per-segment caches are consecutive slices of ONE drive and the boundary dt is ~0.0098 s."""
    idx = np.flatnonzero(np.asarray(mask, bool))
    if not len(idx):
        return []
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > max_gap:
            if prev - s + 1 >= min_n:
                out.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        out.append((s, prev + 1))
    return out


def hires_spec(x, fs, pad=PAD):
    """Zero-padded Hann periodogram.  Linear detrend removes the manoeuvre, not the line."""
    x = np.asarray(x, float)
    n = len(x)
    r = np.arange(n)
    c = np.polyfit(r, x, 1)
    x = x - (c[0] * r + c[1])
    X = np.abs(np.fft.rfft(x * np.hanning(n), n=n * pad)) ** 2
    f = np.fft.rfftfreq(n * pad, 1.0 / fs)
    return f, X


def _cross(f, P, j, level, direction):
    """Linear-interpolated frequency where P crosses `level` walking `direction` from index j."""
    i = j
    while 0 < i < len(P) - 1 and P[i] > level:
        i += direction
    if P[i] > level:
        return None                                   # never crossed inside the array
    a, b = i, i - direction
    if P[b] == P[a]:
        return f[a]
    w = (level - P[a]) / (P[b] - P[a])
    return f[a] + w * (f[b] - f[a])


def linewidth(x, fs, flo=FLO, fhi=FHI, floor_sub=True, pad=PAD):
    """(f0, fwhm, q_app, q_max, prom, floor) for the strongest line in [flo,fhi].

    FLOOR SUBTRACTION is not cosmetic: with the floor left in, a weak line's half-power points sit
    ON the floor and FWHM is set by the floor level rather than the line -- biasing Q DOWN in
    exactly the arm with less signal.  `floor` = median power in [flo,fhi] excluding +-0.6 Hz.
    """
    f, P = hires_spec(x, fs, pad)
    m = (f >= flo) & (f <= fhi)
    T = len(x) / fs
    wl = HANN_FWHM / T
    if not m.any():
        return dict(f0=np.nan, fwhm=np.nan, q_app=np.nan, q_max=np.nan, prom=np.nan, T=T, wl=wl)
    idx = np.flatnonzero(m)
    j = int(idx[np.argmax(P[idx])])
    f0, P0 = float(f[j]), float(P[j])
    far = m & (np.abs(f - f0) > 0.6)
    floor = float(np.median(P[far])) if far.any() else 0.0
    prom = P0 / floor if floor > 0 else np.inf
    Q = P - floor if floor_sub else P
    level = (P0 - floor) / 2.0 if floor_sub else P0 / 2.0
    lo = _cross(f, Q, j, level, -1)
    hi = _cross(f, Q, j, level, +1)
    base = dict(f0=f0, q_max=float(f0 / wl), prom=float(prom), floor=floor, P0=P0,
                T=float(T), wl=float(wl))
    if lo is None or hi is None:
        return dict(base, fwhm=np.nan, q_app=np.nan)
    fw = float(hi - lo)
    return dict(base, fwhm=fw, q_app=float(f0 / fw) if fw > 0 else np.nan,
                flo_x=float(lo), fhi_x=float(hi))


def envelope_stats(x, fs, fc, half=1.5, thresh_k=1.0, maxlag_s=6.0):
    """Amplitude-relaxation observables.  NOT window-limited -- they live on 1-3 s timescales.

    tau_env : e-folding lag of the envelope-fluctuation autocorrelation.  For dA/dt = mu.A-beta.A^3
              the linearised relaxation is 1/(2.mu), i.e. it reads the STABILITY MARGIN directly.
    duty    : fraction of time the envelope exceeds thresh_k x its own median
    burst_s : mean duration of a contiguous excursion above that threshold
    cv      : envelope coefficient of variation -- small for a hard cycle, large for intermittent
    """
    x = np.asarray(x, float)
    b = butter(2, [max(fc - half, 0.5), fc + half], btype="band", fs=fs)
    env = np.abs(hilbert(filtfilt(*b, x)))
    e = env - env.mean()
    n = len(e)
    d = float(np.sum(e * e))
    med = float(np.median(env))
    out = dict(env_p50=med, env_p99=float(np.percentile(env, 99)),
               cv=float(np.std(env) / med) if med > 0 else np.nan)
    if d <= 0 or n < 8:
        return dict(out, tau_env=np.nan, duty=np.nan, burst_s=np.nan, n_burst=0)
    maxlag = min(n - 1, int(maxlag_s * fs))
    ac = np.array([np.sum(e[:n - L] * e[L:]) / d for L in range(maxlag)])
    tau = np.nan
    below = np.flatnonzero(ac < np.exp(-1.0))
    if len(below):
        k = int(below[0])
        if k == 0:
            tau = 0.0
        else:
            w = (ac[k - 1] - np.exp(-1.0)) / (ac[k - 1] - ac[k])
            tau = (k - 1 + w) / fs
    hot = env > thresh_k * med
    runs, i = [], 0
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j + 1]:
                j += 1
            runs.append((j - i + 1) / fs)
            i = j + 1
        else:
            i += 1
    return dict(out, tau_env=float(tau) if np.isfinite(tau) else np.nan,
                duty=float(hot.mean()), burst_s=float(np.mean(runs)) if runs else np.nan,
                n_burst=len(runs))


def block_boot(vals, units, stat=np.median, nboot=4000, rng=None):
    """Cluster bootstrap over `units` (= blk).  Same convention as v86_freq_test.block_boot."""
    rng = rng or np.random.default_rng(0)
    vals = np.asarray(vals, float)
    ok = np.isfinite(vals)
    vals, units = vals[ok], np.asarray(units)[ok]
    if len(vals) < 3:
        return dict(pt=float(stat(vals)) if len(vals) else np.nan, lo=np.nan, hi=np.nan,
                    n=int(len(vals)), nblk=int(len(set(units.tolist()))) if len(vals) else 0)
    g = {}
    for v, u in zip(vals, units):
        g.setdefault(u, []).append(v)
    keys = list(g)
    draws = np.array([stat(np.concatenate([g[keys[i]] for i in
                                           rng.integers(0, len(keys), len(keys))]))
                      for _ in range(nboot)])
    return dict(pt=float(stat(vals)), lo=float(np.percentile(draws, 2.5)),
                hi=float(np.percentile(draws, 97.5)), n=int(len(vals)), nblk=len(keys))


def _stratval(rs, key, stat, weights, vbins):
    if vbins is None or weights is None:
        v = [r[key] for r in rs if np.isfinite(r.get(key, np.nan))]
        return stat(v) if v else np.nan
    num = den = 0.0
    for i, (lo, hi) in enumerate(vbins):
        m = [r[key] for r in rs if lo <= r["v"] < hi and np.isfinite(r.get(key, np.nan))]
        if not m or weights[i] == 0:
            continue
        num += weights[i] * stat(m)
        den += weights[i]
    return num / den if den > 0 else np.nan


def boot_ratio(A, B, key, nboot=4000, rng=None, stat=np.median, weights=None, vbins=None):
    """Ratio A/B of (speed-stratified) medians, each arm cluster-bootstrapped over blk."""
    rng = rng or np.random.default_rng(0)

    def grp(rs):
        g = {}
        for r in rs:
            if np.isfinite(r.get(key, np.nan)):
                g.setdefault(r["blk"], []).append(r)
        return g

    gA, gB = grp(A), grp(B)
    kA, kB = list(gA), list(gB)
    flatA = [r for k in kA for r in gA[k]]
    flatB = [r for k in kB for r in gB[k]]
    if len(kA) < 2 or len(kB) < 2:
        return dict(ratio=np.nan, lo=np.nan, hi=np.nan, nA=len(flatA), nB=len(flatB),
                    blkA=len(kA), blkB=len(kB), ndraw=0)
    pA = _stratval(flatA, key, stat, weights, vbins)
    pB = _stratval(flatB, key, stat, weights, vbins)
    draws = []
    for _ in range(nboot):
        ra = [r for i in rng.integers(0, len(kA), len(kA)) for r in gA[kA[i]]]
        rb = [r for i in rng.integers(0, len(kB), len(kB)) for r in gB[kB[i]]]
        a, b = (_stratval(ra, key, stat, weights, vbins),
                _stratval(rb, key, stat, weights, vbins))
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            draws.append(a / b)
    draws = np.asarray(draws)
    if not len(draws):
        return dict(A=pA, B=pB, ratio=np.nan, lo=np.nan, hi=np.nan, nA=len(flatA), nB=len(flatB),
                    blkA=len(kA), blkB=len(kB), ndraw=0)
    return dict(A=float(pA), B=float(pB), ratio=float(pA / pB) if pB else np.nan,
                lo=float(np.percentile(draws, 2.5)), hi=float(np.percentile(draws, 97.5)),
                nA=len(flatA), nB=len(flatB), blkA=len(kA), blkB=len(kB), ndraw=len(draws))


def did(A, B, C, key, nboot=4000, rng=None, stat=np.median, weights=None, vbins=None):
    """DIFFERENCE-IN-DIFFERENCES in log: (A/B) / (B/C).  A=V86, B=V86B (same-alpha control), C=V85.

    B/C is the SAME-ALPHA pair -- both carry 0xC40D4 = 573 -- so it is the empirical route-to-route
    noise floor.  A/B is the single-variable contrast.  The DiD divides the effect by the floor.
    """
    rng = rng or np.random.default_rng(0)

    def grp(rs):
        g = {}
        for r in rs:
            if np.isfinite(r.get(key, np.nan)):
                g.setdefault(r["blk"], []).append(r)
        return g

    G = [grp(A), grp(B), grp(C)]
    K = [list(g) for g in G]
    flat = [[r for k in K[i] for r in G[i][k]] for i in range(3)]
    if min(len(k) for k in K) < 2:
        return dict(did=np.nan, lo=np.nan, hi=np.nan, blk=[len(k) for k in K])
    pts = [_stratval(f, key, stat, weights, vbins) for f in flat]
    draws = []
    for _ in range(nboot):
        vs = []
        for i in range(3):
            rr = [r for j in rng.integers(0, len(K[i]), len(K[i])) for r in G[i][K[i][j]]]
            vs.append(_stratval(rr, key, stat, weights, vbins))
        if all(np.isfinite(v) and v > 0 for v in vs):
            draws.append((vs[0] / vs[1]) / (vs[1] / vs[2]))
    draws = np.asarray(draws)
    eff = (pts[0] / pts[1]) / (pts[1] / pts[2]) if pts[1] and pts[2] else np.nan
    return dict(did=float(eff), lo=float(np.percentile(draws, 2.5)) if len(draws) else np.nan,
                hi=float(np.percentile(draws, 97.5)) if len(draws) else np.nan,
                vals=[float(p) for p in pts], n=[len(f) for f in flat],
                blk=[len(k) for k in K], ndraw=len(draws))


# ---------------------------------------------------------------------------------------------
#  SYNTHETIC LINES for the power study -- the two physical readings of the ~8 Hz feature
# ---------------------------------------------------------------------------------------------
def resonance(n, fs, f0, q, rng):
    """Noise-driven 2nd-order mode.  poles r=exp(-pi.f0/(Q.fs)), theta=2.pi.f0/fs => FWHM=f0/Q."""
    if not np.isfinite(q):
        ph = rng.uniform(0, 2 * np.pi)
        return np.sin(2 * np.pi * f0 * np.arange(n) / fs + ph)
    r = np.exp(-np.pi * f0 / (q * fs))
    th = 2 * np.pi * f0 / fs
    a1, a2 = 2 * r * np.cos(th), -r * r
    e = rng.standard_normal(n + 2000)
    y = np.zeros(n + 2000)
    for i in range(2, n + 2000):
        y[i] = a1 * y[i - 1] + a2 * y[i - 2] + e[i]
    return y[2000:]


def diffusing_tone(n, fs, f0, q, rng):
    """Coherent tone with a Wiener phase.  Lorentzian FWHM = sigma^2/(2.pi) Hz => sigma^2=2.pi.f0/Q."""
    if not np.isfinite(q):
        return np.sin(2 * np.pi * f0 * np.arange(n) / fs + rng.uniform(0, 2 * np.pi))
    fwhm = f0 / q
    step = np.sqrt(2 * np.pi * fwhm / fs)
    ph = np.cumsum(step * rng.standard_normal(n)) + rng.uniform(0, 2 * np.pi)
    return np.sin(2 * np.pi * f0 * np.arange(n) / fs + ph)


def inject(bed, fs, f0, q, prom_target, fam, rng):
    """Add a synthetic line to a real manual window, amplitude solved so the measured prominence
    lands on `prom_target`.  Solved in closed form: prominence is linear in injected POWER."""
    s = (resonance if fam == "mode" else diffusing_tone)(len(bed), fs, f0, q, rng)
    s = s / (np.std(s) or 1.0)
    base = linewidth(bed, fs)
    # bisect on amplitude -- 12 steps is ample, the map is monotone
    lo, hi = 1e-3, 1e4
    for _ in range(14):
        mid = np.sqrt(lo * hi)
        p = linewidth(bed + mid * s, fs)["prom"]
        if p < prom_target:
            lo = mid
        else:
            hi = mid
    a = np.sqrt(lo * hi)
    return bed + a * s, base
