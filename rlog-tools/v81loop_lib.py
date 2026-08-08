#!/usr/bin/env python3
"""Shared instruments for the V81 / route-67 OUTER-LOOP LIMIT-CYCLE test (H1).

H1: the highway instability is a limit cycle of openpilot's own OUTER lateral loop, closing
through an EPS that will not deliver the commanded angle rate.  The alternatives are
A (EPS-internal cycle that openpilot echoes), B (tyre / wheel order) and C (the engaged-only
damper's relay characteristic).

🛑 Three measurement hazards this file exists to remove, each of which would otherwise produce a
   confidently-wrong PHASE and therefore a confidently-wrong causal verdict:

 ZOH      `_cache_r67x`'s `tq` column is the 0x18F torsion bar HELD-LAST onto the 0x14A grid.
          A zero-order hold of a 100 Hz signal onto another 100 Hz grid carries a mean delay of
          half the hold age -- up to 5 ms, which is 45 deg at 25 Hz.  `native_bar()` recovers each
          held value's OWN 0x18F arrival time from `raw18_t`, so the hold delay is removed rather
          than being read as plant lag.  (`sc_tq` and the openpilot columns are `_grid` = LINEAR
          interpolation, which is phase-preserving; only the held columns need this.)

 CLOCK    `sendcan` and `can` logMonoTime come from different daemons but the SAME device
          monotonic clock, so the command->bar offset that survives is physical bus + ECU latency,
          not an artefact.  It is still an offset: quote lag against the pure-delay fit, never as
          an absolute causal arrow on its own.

 FS       `1/median(dt)` reads 100.1-101.4 Hz against a true 100.000 Hz grid.  `fs_run()` uses the
          mean rate over a gap-free stretch, which is the estimator the record demands.

 ALIAS    fs = 100 Hz => Nyquist 50 Hz.  Every line f is indistinguishable from 100-f and 100+f.
          Any identification here must state that, and any phase read at f must be checked for
          robustness against reading the line as 100-f.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / "_cache_r67x"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

FS_NOM = 100.0          # the true CAN grid; confirmed per-run by fs_run()
NFFT = 256              # 2.56 s, 0.39 Hz bins -- the kit's standard
HOP = 128


# ---------------------------------------------------------------- loading -----------------------
def load_route():
    """The whole-route npz, which carries the NATIVE-timestamp arrays the per-segment files drop."""
    return np.load(CACHE / "r67.npz", allow_pickle=True)


def load_seg(s):
    return dict(np.load(CACHE / f"r67xs{s}.npz", allow_pickle=True))


def native_18f(d, cols=("tq",)):
    """(t_18f, {col: values}) on the 0x18F frames' OWN arrival times -- the ZOH delay removed.

    🛑 EVERY column the extractor builds from `last18` -- `tq`, `rate_f`, `sca`, `sstat`, `slow3`
    -- lives on the 0x18F clock, NOT on the 0x14A row clock it is stored against.  Resampling one
    of them as if it were a 0x14A sample misplaces it by up to a full 10 ms frame.  That is 99 deg
    at 27.5 Hz, and it shows up as `rate` failing to lead `ang` by the 90 deg a derivative owes it.

    `extract_r67_v81` holds the last 0x18F frame at each 0x14A row, so the frame current at row i
    is `searchsorted(raw18_t, t14[i]) - 1` and its true timestamp is that entry.  De-duplicating on
    that index recovers one (time, value) tuple per 0x18F frame that was ever current; frames that
    were never current (two 0x18F between consecutive 0x14A) are absent, and `drop` quotes that
    loss rather than assuming it away.
    """
    t14 = np.asarray(d["t"], float)
    r18 = np.asarray(d["raw18_t"], float)
    idx = np.searchsorted(r18, t14, side="right") - 1
    ok = idx >= 0
    idx = idx[ok]
    keep = np.ones(len(idx), bool)
    keep[1:] = idx[1:] != idx[:-1]
    drop = 1.0 - keep.sum() / max(len(np.unique(idx)), 1)
    vals = {c: np.asarray(d[c], float)[ok][keep] for c in cols}
    return r18[idx[keep]], vals, float(drop)


def native_bar(d):
    """(t_bar, tq, drop) -- the torsion bar alone. Thin wrapper over `native_18f`."""
    t, v, drop = native_18f(d, ("tq",))
    return t, v["tq"], drop


# ---------------------------------------------------------------- rate / lattice ----------------
def fs_run(t):
    """Mean rate over the longest gap-free stretch. 🛑 NOT 1/median(dt) -- see the module docstring."""
    t = np.asarray(t, float)
    if len(t) < 3:
        return FS_NOM
    dt = np.diff(t)
    med = float(np.median(dt))
    ok = dt < 2.5 * med
    best, cur, s0, bs = 0, 0, 0, 0
    for i, g in enumerate(ok):
        if g:
            cur += 1
            if cur > best:
                best, bs = cur, s0
        else:
            cur, s0 = 0, i + 1
    if best < 10:
        return 1.0 / med
    a, b = bs, bs + best
    return float(best / (t[b] - t[a]))


def runs_of(mask, t, minlen, maxgap=0.05):
    """Contiguous runs of `mask` with no sample gap over `maxgap`, at least `minlen` long."""
    m = np.asarray(mask, bool)
    t = np.asarray(t, float)
    brk = np.zeros(len(m), bool)
    brk[1:] = np.diff(t) > maxgap
    out, i, n = [], 0, len(m)
    while i < n:
        if not m[i]:
            i += 1
            continue
        j = i + 1
        while j < n and m[j] and not brk[j]:
            j += 1
        if j - i >= minlen:
            out.append((i, j))
        i = j
    return out


def lattice(t0, t1, fs=FS_NOM):
    n = int(np.floor((t1 - t0) * fs)) + 1
    return t0 + np.arange(n) / fs


def resamp(tau, t, v):
    """Linear interpolation onto `tau` -- phase-preserving to first order, unlike a hold."""
    t = np.asarray(t, float)
    v = np.asarray(v, float)
    good = np.isfinite(t) & np.isfinite(v)
    if good.sum() < 2:
        return np.full(len(tau), np.nan)
    return np.interp(tau, t[good], v[good])


# ---------------------------------------------------------------- spectra -----------------------
def _win(n):
    return np.hanning(n) + 1e-12


def segs_of(x, nfft=NFFT, hop=HOP):
    for i in range(0, len(x) - nfft + 1, hop):
        yield i


def welch_cross(x, y, fs, nfft=NFFT, hop=HOP, detrend=True):
    """(f, Pxx, Pyy, Pxy, nseg). Hann, 50% overlap, linear detrend per segment.

    Pxy = E[X* Y]: a POSITIVE phase angle(Pxy) means y LEADS x.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    w = _win(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    Pxx = np.zeros(len(f))
    Pyy = np.zeros(len(f))
    Pxy = np.zeros(len(f), complex)
    n = 0
    r = np.arange(nfft, dtype=float)
    for i in segs_of(x, nfft, hop):
        xs, ys = x[i:i + nfft], y[i:i + nfft]
        if not (np.isfinite(xs).all() and np.isfinite(ys).all()):
            continue
        if detrend:
            xs = xs - np.polyval(np.polyfit(r, xs, 1), r)
            ys = ys - np.polyval(np.polyfit(r, ys, 1), r)
        X = np.fft.rfft(xs * w)
        Y = np.fft.rfft(ys * w)
        Pxx += np.abs(X) ** 2
        Pyy += np.abs(Y) ** 2
        Pxy += np.conj(X) * Y
        n += 1
    if n == 0:
        return f, None, None, None, 0
    return f, Pxx / n, Pyy / n, Pxy / n, n


def coherence(Pxx, Pyy, Pxy):
    den = Pxx * Pyy
    return np.where(den > 0, np.abs(Pxy) ** 2 / np.where(den > 0, den, 1.0), np.nan)


def coh_bias(nseg):
    """E[coh^2] under the NULL for `nseg` independent Welch segments = 1/nseg.

    With 50% Hann overlap the segments are not independent; the effective count is ~1.5x lower,
    so this is an OPTIMISTIC floor.  The surrogate null in `surrogate_coh` is the one to quote.
    """
    return 1.0 / max(nseg, 1)


def prom_spectrum(f, P, halfwin=6.0, exclude=1.5):
    """P over its own local median floor -- the kit's standard prominence, so a broadband driver
    push cannot pass as a line."""
    f = np.asarray(f, float)
    D = np.abs(f[:, None] - f[None, :])
    M = (D <= halfwin) & (D > exclude) & (f[None, :] > 0.3)
    M[M.sum(1) < 5] = False
    A = np.where(M, P[None, :], np.nan)
    with np.errstate(all="ignore"):
        fl = np.nanmedian(A, axis=1)
    R = np.where(fl > 0, P / np.where(fl > 0, fl, 1.0), np.nan)
    R[~np.isfinite(fl)] = np.nan
    R[0] = R[-1] = np.nan
    return R


def locate(f, P, lo, hi, R=None):
    """(f0, prominence) of the most PROMINENT line in [lo,hi], parabolic-refined in log power."""
    if R is None:
        R = prom_spectrum(f, P)
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, R, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), float(R[j])
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(f[j] + np.clip(dl, -0.5, 0.5) * (f[1] - f[0])), float(R[j])


def band_env(x, fs, lo, hi):
    """p99 of the analytic band envelope, leakage-controlled (detrend + Hann, central 60%)."""
    x = np.asarray(x, float)
    n = len(x)
    r = np.arange(n, dtype=float)
    tp = np.hanning(n) + 1e-3
    y = (x - np.polyval(np.polyfit(r, x, 1), r)) * tp
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(n, 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    a = np.abs(np.fft.irfft(H, n=n))
    return float(np.percentile((a / tp)[int(0.2 * n):int(0.8 * n)], 99))


# ---------------------------------------------------------------- surrogates --------------------
def surrogate_coh(x, y, fs, nfft=NFFT, hop=HOP, nsur=200, rng=None, band=None):
    """Circular-shift null for band-max coherence. Shifts break the cross-timing but keep BOTH
    marginal spectra exactly, so the null carries the same colour as the data.

    🛑 Shifts are applied WITHIN one contiguous run only -- the record contains a case where
    pooling runs manufactured coherence 0.5 out of splice discontinuities.
    """
    rng = rng or np.random.default_rng(0xC0FFEE)
    n = len(x)
    lo, hi = band or (0.0, fs / 2)
    out = []
    for _ in range(nsur):
        s = int(rng.integers(int(0.1 * n), int(0.9 * n)))
        f, Pxx, Pyy, Pxy, ns = welch_cross(x, np.roll(y, s), fs, nfft, hop)
        if ns == 0:
            continue
        C = coherence(Pxx, Pyy, Pxy)
        m = (f >= lo) & (f <= hi)
        out.append(float(np.nanmax(C[m])))
    return np.array(out)


# ---------------------------------------------------------------- bootstrap ---------------------
def boot_episodes(units, stat, nboot=2000, rng=None):
    """Resample EPISODES with replacement. 🛑 A window bootstrap manufactures significance and has
    retracted three claims in this kit -- `units` must be whole episodes, never windows."""
    rng = rng or np.random.default_rng(0xBEEF)
    k = len(units)
    if k < 2:
        return np.array([np.nan, np.nan])
    vals = []
    for _ in range(nboot):
        pick = [units[i] for i in rng.integers(0, k, k)]
        v = stat(pick)
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return np.array([np.nan, np.nan])
    return np.percentile(vals, [2.5, 97.5])


def circ_mean_ci(ang, w=None, nboot=4000, rng=None):
    """(mean angle, lo, hi) in RADIANS for a set of per-episode phase estimates, weighted.

    Circular, because a phase near +-pi averaged linearly is meaningless.
    """
    rng = rng or np.random.default_rng(0x5EED)
    ang = np.asarray(ang, float)
    w = np.ones(len(ang)) if w is None else np.asarray(w, float)
    ok = np.isfinite(ang) & np.isfinite(w) & (w > 0)
    ang, w = ang[ok], w[ok]
    if len(ang) == 0:
        return np.nan, np.nan, np.nan
    z = np.sum(w * np.exp(1j * ang)) / np.sum(w)
    mu = float(np.angle(z))
    if len(ang) < 2:
        return mu, np.nan, np.nan
    bs = []
    for _ in range(nboot):
        i = rng.integers(0, len(ang), len(ang))
        bs.append(np.angle(np.sum(w[i] * np.exp(1j * ang[i])) / np.sum(w[i])))
    d = np.angle(np.exp(1j * (np.array(bs) - mu)))
    lo, hi = np.percentile(d, [2.5, 97.5])
    return mu, mu + lo, mu + hi


def wrap(a):
    return np.angle(np.exp(1j * np.asarray(a, float)))
