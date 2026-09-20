# -*- coding: utf-8 -*-
"""Exact algebraic re-arrangement of v282cmp.band_H so that a cell's |H| is a SUM over windows.

band_H computes, over the band bins, H = sum_bin w_bin * (|Pxy_bin| / Pxx_bin) / sum_bin w_bin with
w_bin = Pxx_bin.  With equal-length windows the length weights are constant, so

    H   = sum_bin |Pxy_bin|      / sum_bin Pxx_bin
    coh = sum_bin |Pxy_bin|^2/Pyy_bin / sum_bin Pxx_bin

where Pxy_bin, Pxx_bin, Pyy_bin are the SUMS over the pooled windows.  Magnitudes are still averaged,
never phasors, because the |.| is inside the bin sum and only the per-bin cross spectra are pooled
across windows -- which is what band_H does.

`assert_equivalent()` checks this against the shared band_H on real windows and must pass.
"""
import numpy as np
from scipy import signal

import dflib as D
import v282cmp as C

FS = C.FS


def win_spec(w, f1, f2, W):
    """Per-window band-bin cross spectra, identical to what band_H's welch/csd produce."""
    x = w["x"].astype(float); y = w["y"].astype(float)
    xs, ys = x - x.mean(), y - y.mean()
    f, pxx = signal.welch(xs, FS, nperseg=W, noverlap=W // 2)
    _, pyy = signal.welch(ys, FS, nperseg=W, noverlap=W // 2)
    _, pxy = signal.csd(xs, ys, FS, nperseg=W, noverlap=W // 2)
    s = (f >= f1) & (f < f2)
    return pxx[s] * W, pyy[s] * W, pxy[s] * W, f[s]


def pool(specs):
    """Pooled band metrics for a set of windows.

    H    -- the shared band_H gain: sum|Pxy| / sum Pxx  (magnitudes averaged, never phasors)
    coh  -- input-power-weighted band coherence
    NE   -- NORMALISED COMPLEX TRACKING ERROR: sqrt( sum|Y-X|^2 / sum|X|^2 ) in the band, i.e. the
            in-band RMS of (achieved - desired) over the in-band RMS of desired.  This is the
            operator's "match the model's desired lateral acceleration as closely as" made
            quantitative: it penalises gain error, PHASE LAG and unexplained motion together, which
            a gain alone does not.  NE = 0 is perfect; NE = 1 means the error is as big as the demand.
    NEc  -- the part of NE from the COHERENT transfer being wrong (gain and/or phase):
            sum Pxx |Pxy/Pxx - 1|^2 / sum Pxx
    NEi  -- the part from achieved motion the demand does NOT explain: sum Pyy(1-coh_bin) / sum Pxx
            (NE^2 = NEc^2 + NEi^2 exactly; asserted in _check())
    R    -- sqrt(sum Pyy / sum Pxx), the raw in-band amplitude ratio
    ph   -- power-weighted phase of Pxy in degrees, and the equivalent lag at the band centre
    """
    if not specs:
        return None
    Pxx = sum(s[0] for s in specs)
    Pyy = sum(s[1] for s in specs)
    Pxy = sum(s[2] for s in specs)
    fa = specs[0][3] if len(specs[0]) > 3 else None
    den = float(np.sum(Pxx))
    if den <= 0:
        return None
    Pxxs = np.maximum(Pxx, 1e-30)
    H = float(np.sum(np.abs(Pxy)) / den)
    cohb = np.abs(Pxy) ** 2 / np.maximum(Pxxs * Pyy, 1e-30)
    coh = float(np.sum(np.abs(Pxy) ** 2 / np.maximum(Pyy, 1e-30)) / den)
    NE2 = float(np.sum(Pxx + Pyy - 2.0 * np.real(Pxy)) / den)
    Hc = Pxy / Pxxs
    NEc2 = float(np.sum(Pxxs * np.abs(Hc - 1.0) ** 2) / den)
    NEi2 = float(np.sum(Pyy * (1.0 - cohb)) / den)
    ph = float(np.degrees(np.angle(np.sum(Pxy))))
    return dict(H=H, coh=coh, n=len(specs), NE=float(np.sqrt(max(NE2, 0.0))),
                NEc=float(np.sqrt(max(NEc2, 0.0))), NEi=float(np.sqrt(max(NEi2, 0.0))),
                R=float(np.sqrt(np.sum(Pyy) / den)), ph=ph,
                Pxx=Pxx, Pyy=Pyy, Pxy=Pxy, fa=fa,
                fc=(None if fa is None else float(np.average(fa, weights=Pxxs))),
                lag=(None if fa is None else
                     -np.radians(ph) / (2 * np.pi * float(np.average(fa, weights=Pxxs)))))


def _check(ws, f1, f2, W):
    """NE^2 must equal NEc^2 + NEi^2 to machine precision."""
    r = pool([win_spec(w, f1, f2, W) for w in ws])
    assert abs(r["NE"] ** 2 - (r["NEc"] ** 2 + r["NEi"] ** 2)) < 1e-9 * max(r["NE"] ** 2, 1e-9), r
    return r


def assert_equivalent(ws, f1, f2, W, tol=1e-9):
    a = C.band_H([(w["x"].astype(float), w["y"].astype(float)) for w in ws], f1, f2)
    b = pool([win_spec(w, f1, f2, W) for w in ws])
    assert abs(a["H"] - b["H"]) < tol and abs(a["coh"] - b["coh"]) < tol, (a, b)
    return a["H"], b["H"], a["coh"], b["coh"]
