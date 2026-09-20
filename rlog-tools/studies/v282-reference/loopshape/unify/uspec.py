# -*- coding: utf-8 -*-
"""Per-window multi-signal cross-spectral estimator (one Hann-windowed Welch pass, all pairs).

Every auto- and cross-spectrum for a window comes from the SAME blocks of the SAME data, so any
ratio formed from them is a consistent estimate.  Keeping the windows separate (rather than pooling
immediately) is what lets the analysis amplitude-match and route-cluster bootstrap afterwards.
"""
import numpy as np

FS = 100.0


def window_spectra(sigs, nperseg, noverlap=None):
    """sigs: dict name -> 1-D array (same length).  Returns (f, S, nblk, meta) with
    S[(a,b)] = mean over blocks of conj(A)*B  (so S[(a,b)] = Pab in the scipy csd convention)."""
    names = list(sigs)
    L = len(sigs[names[0]])
    n = int(nperseg)
    if L < n:
        return None
    if noverlap is None:
        noverlap = n // 2
    step = n - noverlap
    win = np.hanning(n)
    scale = 1.0 / (FS * (win ** 2).sum())
    starts = list(range(0, L - n + 1, step))
    F = {a: [] for a in names}
    for s in starts:
        for a in names:
            x = np.nan_to_num(sigs[a][s:s + n])
            x = x - x.mean()
            F[a].append(np.fft.rfft(x * win))
    for a in names:
        F[a] = np.array(F[a])
    f = np.fft.rfftfreq(n, 1.0 / FS)
    S = {}
    for ii, a in enumerate(names):
        for b in names[ii:]:
            c = np.mean(np.conj(F[a]) * F[b], axis=0) * scale * 2.0
            S[(a, b)] = c
    return f, S, len(starts)


def get(S, a, b):
    if (a, b) in S:
        return S[(a, b)]
    return np.conj(S[(b, a)])


def pool(specs, weights=None):
    """Power-weighted (by seconds) pool of a list of per-window spectra dicts."""
    if weights is None:
        weights = [1.0] * len(specs)
    out = {}
    W = float(sum(weights))
    for sp, w in zip(specs, weights):
        for k, v in sp.items():
            out[k] = out.get(k, 0.0) + v * w
    return {k: v / W for k, v in out.items()}
