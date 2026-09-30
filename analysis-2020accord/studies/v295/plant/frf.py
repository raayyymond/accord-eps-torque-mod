# -*- coding: utf-8 -*-
"""frf.py -- pooled cross-spectral estimation over many disjoint stretches (Welch, Hann, 50 % overlap).

Every spectrum is accumulated over all windows of all stretches, so H = S_zy / S_zu is ONE estimate over the pooled
data (not an average of per-stretch H).  Coherences are the pooled magnitude-squared coherences.  A window is used
only if it lies wholly inside one stretch (no window straddles a gap or a mask edge).
"""
import numpy as np
from scipy import signal


def windows(runs, nper, step):
    for a, b in runs:
        for s in range(a, b - nper + 1, step):
            yield s


def cross(series, runs, nper, fs, detrend=True):
    """series: dict name -> 1-D array (same axis).  Returns f, n_windows, S where S[(p, q)] = pooled E[P* Q]."""
    w = signal.get_window("hann", nper)
    U = np.sum(w ** 2) * fs
    names = list(series)
    S = {(p, q): 0.0 for p in names for q in names}
    nw = 0
    for s in windows(runs, nper, nper // 2):
        F = {}
        for k in names:
            x = np.asarray(series[k][s:s + nper], float)
            if detrend:
                x = signal.detrend(x, type="linear")
            F[k] = np.fft.rfft(w * x)
        for p in names:
            for q in names:
                S[(p, q)] = S[(p, q)] + np.conj(F[p]) * F[q]
        nw += 1
    f = np.fft.rfftfreq(nper, 1.0 / fs)
    for key in S:
        S[key] = S[key] / max(nw, 1) / U
    return f, nw, S


def coh(S, p, q):
    return np.abs(S[(p, q)]) ** 2 / (np.real(S[(p, p)]) * np.real(S[(q, q)]) + 1e-300)


def H_iv(S, z, u, y):
    """instrumental-variable transfer u -> y with instrument z: S_zy / S_zu."""
    return S[(z, y)] / S[(z, u)]


def H_dir(S, u, y):
    return S[(u, y)] / S[(u, u)]


def band_avg(f, v, lo, hi):
    m = (f >= lo) & (f < hi)
    return np.mean(v[m]) if m.any() else np.nan
