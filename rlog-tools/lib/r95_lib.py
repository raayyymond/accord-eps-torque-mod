#!/usr/bin/env python3
r"""Route 95 (V101 = the 8x LKAS gain) -- shared loader + estimators.

Cache: `analysis-2020accord/_scratch/cache/r95/r95.npz` (whole route, contiguous, NO segment hole --
all five segments 0..4 are on disk).  Per-segment files `r95s0..r95s4.npz`.

🛑 PAIRING: every `v101_b*` column is decoded from `probe`, which lives on the `t` row grid.
   `t`/`probe` are the SAFE pair.  Do NOT pair `t` with `raw14_b4`.

🛑 SIGN CONVENTION (operator-confirmed 2026-08-13): NEGATIVE driver torque AND NEGATIVE steering
   angle = a RIGHT turn; +LKAS command demands NEGATIVE angle.  Channels are stored in NATIVE
   frames.  `lkas_in_angle_frame()` applies the flip ONCE, deliberately.
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1].parent
CACHE = ROOT / "analysis-2020accord" / "_scratch/cache/r95"

_Z = None


def Z():
    global _Z
    if _Z is None:
        _Z = dict(np.load(CACHE / "r95.npz", allow_pickle=True))
    return _Z


def fs():
    return 1.0 / np.median(np.diff(np.asarray(Z()["t"], float)))


def col(k):
    return np.asarray(Z()[k], float)


def engaged():
    return col("cc_lat") > 0.5


def episodes(mask=None):
    """Contiguous engaged runs -> list of (i0, i1) half-open row index pairs."""
    m = engaged() if mask is None else mask
    n = len(m)
    d = np.diff(m.astype(int))
    s = list(np.where(d == 1)[0] + 1)
    e = list(np.where(d == -1)[0] + 1)
    if m[0]:
        s = [0] + s
    if m[-1]:
        e = e + [n]
    return list(zip(s, e))


def lkas_in_angle_frame():
    """openpilot's transmitted LKAS command, SIGN-FLIPPED into the steering-angle frame.

    +LKAS demands NEGATIVE angle, so -sc_tq is the demand expressed the way `ang`/`tq` are.
    """
    return -col("sc_tq")


# --------------------------------------------------------------------------------------
#  Spectral estimators.  Every one operates on CONTIGUOUS runs only -- never across a join.
# --------------------------------------------------------------------------------------
def _runs(mask, min_n):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                out.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        out.append((s, prev + 1))
    return out


def welch(x, mask, FS, nfft=512, ov=2):
    """Hann Welch PSD over contiguous runs of `mask`.  Returns (f, P, K)."""
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    P = np.zeros(len(f))
    K = 0
    step = max(1, nfft // ov)
    for a, b in _runs(mask, nfft):
        for i in range(a, b - nfft + 1, step):
            seg = x[i:i + nfft]
            if not np.all(np.isfinite(seg)):
                continue
            P += np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
            K += 1
    if K == 0:
        return f, np.full(len(f), np.nan), 0
    return f, P / (K * (win ** 2).sum() * FS), K


def coherence(x, y, mask, FS, nfft=256):
    """NON-OVERLAPPING Hann segments so K is the TRUE dof.  Returns (f, coh, phase_deg, K)."""
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    Pxy = np.zeros(len(f), complex)
    Pxx = np.zeros(len(f))
    Pyy = np.zeros(len(f))
    K = 0
    for a, b in _runs(mask, nfft):
        for i in range(a, b - nfft + 1, nfft):
            sx, sy = x[i:i + nfft], y[i:i + nfft]
            if not (np.all(np.isfinite(sx)) and np.all(np.isfinite(sy))):
                continue
            X = np.fft.rfft((sx - sx.mean()) * win)
            Y = np.fft.rfft((sy - sy.mean()) * win)
            Pxy += X * np.conj(Y)
            Pxx += np.abs(X) ** 2
            Pyy += np.abs(Y) ** 2
            K += 1
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-300)
    return f, coh, np.degrees(np.angle(Pxy)), K


def bandpass(x, FS, lo, hi, mask=None):
    """Zero-phase brick-wall band-pass PER CONTIGUOUS RUN.  NaN outside the runs."""
    out = np.full(len(x), np.nan)
    m = np.ones(len(x), bool) if mask is None else mask
    for a, b in _runs(m, 64):
        seg = np.asarray(x[a:b], float)
        if not np.all(np.isfinite(seg)):
            seg = np.nan_to_num(seg, nan=float(np.nanmean(seg)) if np.isfinite(seg).any() else 0.0)
        seg = seg - seg.mean()
        X = np.fft.rfft(seg)
        f = np.fft.rfftfreq(len(seg), 1 / FS)
        X[(f < lo) | (f > hi)] = 0.0
        out[a:b] = np.fft.irfft(X, n=len(seg))
    return out


def band_envelope(x, FS, lo, hi, mask=None):
    """TRUE analytic-signal magnitude in [lo,hi] Hz, computed PER CONTIGUOUS RUN.

    🛑 DEFECT FOUND 2026-08-19 in the kit's shared `_r2b_common.band_envelope` (and in the first
    draft of this one): it built the one-sided spectrum `H[band] = 2*X[band]` and then called
    `np.fft.irfft`, which FORCES A REAL OUTPUT.  `abs()` of that is the RECTIFIED band-passed
    signal times 2 -- it oscillates at 2*omega and its median is a rectification artifact, not an
    amplitude.  (Measured on route 95: env_RMS / signal_RMS was exactly 2.000, and the median was
    494 against an RMS of 1520.)  RATIOS between conditions are unaffected -- 2x cancels -- but any
    envelope-shape work (growth rate, decay tau, ring-down) is WRONG on it.
    The fix is a full complex `ifft`, which is what an analytic signal requires.
    """
    out = np.full(len(x), np.nan)
    m = np.ones(len(x), bool) if mask is None else mask
    for a, b in _runs(m, 64):
        seg = np.asarray(x[a:b], float)
        if not np.all(np.isfinite(seg)):
            seg = np.nan_to_num(seg, nan=float(np.nanmean(seg)) if np.isfinite(seg).any() else 0.0)
        seg = seg - seg.mean()
        N = len(seg)
        X = np.fft.fft(seg)
        f = np.fft.fftfreq(N, 1 / FS)
        H = np.zeros(N, complex)
        sel = (f >= lo) & (f <= hi)                 # POSITIVE frequencies only => analytic
        H[sel] = 2.0 * X[sel]
        out[a:b] = np.abs(np.fft.ifft(H))
    return out


def band_rms(x, FS, lo, hi, mask, sl):
    """RMS of the band-passed signal over slice `sl`.  Scale-correct, unlike an envelope median."""
    bp = bandpass(x, FS, lo, hi, mask=mask)
    v = bp[sl]
    v = v[np.isfinite(v)]
    return float(np.sqrt(np.mean(v ** 2))) if len(v) else float("nan")


def lowpass(x, FS, fc, mask=None):
    """Zero-phase brick-wall low-pass PER CONTIGUOUS RUN.  NaN outside."""
    out = np.full(len(x), np.nan)
    m = np.ones(len(x), bool) if mask is None else mask
    for a, b in _runs(m, 16):
        seg = np.asarray(x[a:b], float)
        mu = np.nanmean(seg)
        seg = np.nan_to_num(seg, nan=mu) - mu
        X = np.fft.rfft(seg)
        f = np.fft.rfftfreq(len(seg), 1 / FS)
        X[f > fc] = 0
        out[a:b] = np.fft.irfft(X, n=len(seg)) + mu
    return out


# --------------------------------------------------------------------------------------
#  Block bootstrap.  🛑 Route 95 has THREE engaged episodes -- an episode bootstrap has 3
#  resample units and cannot produce a usable CI.  We therefore use a MOVING-BLOCK bootstrap
#  on contiguous blocks whose length is stated with every number, and we ALWAYS run the
#  split-half null control first.
# --------------------------------------------------------------------------------------
def blocks_of(mask, FS, block_s):
    """Cut the contiguous runs of `mask` into non-overlapping blocks of block_s seconds."""
    L = int(round(block_s * FS))
    out = []
    for a, b in _runs(mask, L):
        for i in range(a, b - L + 1, L):
            out.append((i, i + L))
    return out


def block_bootstrap(values, weights=None, n_boot=4000, seed=0, stat=np.mean):
    """Bootstrap a statistic over independent blocks.  Returns (point, lo95, hi95)."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v = v[ok]
    if len(v) < 3:
        return float("nan"), float("nan"), float("nan")
    w = None if weights is None else np.asarray(weights, float)[ok]
    rng = np.random.default_rng(seed)
    pt = stat(v) if w is None else float(np.sum(v * w) / np.sum(w))
    bs = np.empty(n_boot)
    for i in range(n_boot):
        j = rng.integers(0, len(v), len(v))
        bs[i] = stat(v[j]) if w is None else float(np.sum(v[j] * w[j]) / np.sum(w[j]))
    return float(pt), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
