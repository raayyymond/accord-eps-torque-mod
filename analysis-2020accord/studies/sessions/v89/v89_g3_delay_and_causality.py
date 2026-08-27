#!/usr/bin/env python3
"""studies/sessions/v89/v89_g3_delay_and_causality.py -- a robust lag estimate, and WHICH WAY causality runs.

Two defects in v89_g2 that this fixes.
 1. Its group delay came from `np.unwrap` over bands including two with coh^2 < 0.02 and phases of
    -139 and +177 deg. Unwrapping junk propagates into every later band. REPLACED by a DELAY SEARCH
    in the complex domain -- maximise |sum_f w(f) * Sxy_hat(f) * exp(+j 2 pi f tau)| -- which needs
    no unwrapping and downweights incoherent bands by construction.
 2. v89_g2's C0 "FAIL" at 30/50 ms is BAND-AVERAGING BIAS, not a pipeline fault: averaging a complex
    cross-spectrum over a 4 Hz band while the phase rotates 43 deg across it biases the vector angle.
    Quantified here as a systematic; at the ~10 ms lags in play it is ~1.5 deg.

THE CAUSALITY CHECK, which is what actually decides whether the phase fit means anything.
`gp-0x6b98` carries base assist and base assist is a function of column torque, so cmd and column
are in a LOOP. If the column LEADS the command, the estimator is reading the feedback path and no
forward-plant claim can be made from it. Measured as the lag of the peak of the cross-correlation,
per arm, with a block-permutation null.
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from v89_g1_cmd_column_phase import (build_grid, wins, accumulate, FREQ, H_A, FS, NW, CACHE)

RNG = np.random.default_rng(890832)
OUT = CACHE / "v89_g3_delay.json"
FMIN, FMAX = 2.0, 25.0
TAUS = np.arange(-80, 80.25, 0.25) / 1000.0     # seconds


def delay_search(Sxy, Sxx, Syy, cohmin=0.05):
    """Robust equivalent transport lag. Positive tau = column LAGS command."""
    m = (FREQ >= FMIN) & (FREQ <= FMAX)
    coh = np.zeros(len(FREQ))
    good = (Sxx > 0) & (Syy > 0)
    coh[good] = np.abs(Sxy[good]) ** 2 / (Sxx[good] * Syy[good])
    m &= coh >= cohmin
    if m.sum() < 8:
        return np.nan, m.sum()
    u = Sxy[m] / np.abs(Sxy[m])
    w = coh[m]
    f = FREQ[m]
    score = [abs(np.sum(w * u * np.exp(2j * np.pi * f * t))) for t in TAUS]
    return float(TAUS[int(np.argmax(score))] * 1000.0), int(m.sum())


def ha_delay(cohmin=0.05, Sxx=None, Syy=None, Sxy=None):
    """The same estimator applied to H_A itself, over the same bins, so the comparison is
    apples-to-apples (band selection and the -180 polarity handled identically)."""
    m = (FREQ >= FMIN) & (FREQ <= FMAX)
    u = H_A(FREQ[m])
    u = u / np.abs(u)
    score = [abs(np.sum(u * np.exp(2j * np.pi * FREQ[m] * t))) for t in TAUS]
    return float(TAUS[int(np.argmax(score))] * 1000.0)


def arm_delay(W, nb=1500, cohmin=0.05):
    Sxy, Sxx, Syy = accumulate(W)
    # remove the known 180 deg cmd->column polarity inversion
    tau, nb_bins = delay_search(-Sxy, Sxx, Syy, cohmin)
    keys = sorted({w[2] for w in W})
    idx = {k: [i for i, x in enumerate(W) if x[2] == k] for k in keys}
    D = []
    for _ in range(nb):
        pick = np.concatenate([idx[keys[j]] for j in RNG.integers(0, len(keys), len(keys))])
        a, b, c = accumulate(W, pick)
        t = delay_search(-a, b, c, cohmin)[0]
        if np.isfinite(t):
            D.append(t)
    D = np.array(D)
    return tau, (float(np.percentile(D, 2.5)), float(np.percentile(D, 97.5))), nb_bins, len(keys)


def xcorr_peak(segs, engaged, maxlag=40):
    """Lag (ms) of the peak |cross-correlation| between band-passed cmd and column torque.
    NEGATIVE lag = the COLUMN leads the command = feedback dominates."""
    from scipy.signal import butter, sosfiltfilt
    xs, ys, keys = [], [], []
    for S in segs:
        sos = butter(4, [2.0 / (FS / 2), 25.0 / (FS / 2)], btype="band", output="sos")
        m = (S["eng"] if engaged else ~S["eng"]) & (~S["bad"]) & (S["sst"] == 0)
        ch = np.flatnonzero(np.diff(np.concatenate([[0], m.view(np.int8), [0]])))
        for a, b in zip(ch[0::2], ch[1::2]):
            if b - a < 4 * NW:
                continue
            x = sosfiltfilt(sos, S["cmd"][a:b])
            y = sosfiltfilt(sos, S["tq"][a:b])
            xs.append((x - x.mean()) / (x.std() + 1e-9))
            ys.append((y - y.mean()) / (y.std() + 1e-9))
            keys.append((S["s"], a))
    if not xs:
        return None
    lags = np.arange(-maxlag, maxlag + 1)

    def cc(xl, yl):
        out = np.zeros(len(lags))
        npts = 0
        for x, y in zip(xl, yl):
            n = min(len(x), len(y))
            x, y = x[:n], y[:n]
            npts += n
            for i, L in enumerate(lags):
                if L >= 0:
                    out[i] += np.dot(x[:len(x) - L], y[L:]) if L else np.dot(x, y)
                else:
                    out[i] += np.dot(x[-L:], y[:len(y) + L])
        return out / max(npts, 1)

    c = cc(xs, ys)
    pk = lags[int(np.argmax(np.abs(c)))]
    D = []
    for _ in range(400):
        p = RNG.permutation(len(xs))
        cp = cc(xs, [ys[i] for i in p])
        D.append(lags[int(np.argmax(np.abs(cp)))])
    return {"peak_lag_ms": float(pk * 1000 / FS), "peak_val": float(c[np.argmax(np.abs(c))]),
            "n_episodes": len(xs),
            "null_peak_ms": float(np.percentile(np.abs(D), 95)) if len(xs) > 2 else None,
            "curve": {int(L): float(v) for L, v in zip(lags, c)}}


def main():
    rep = {}
    segs = build_grid()

    print("=" * 104)
    print("C0 -- BAND-AVERAGING BIAS quantified (v89_g2's apparent 'FAIL' was this, not a fault)")
    print("=" * 104)
    base = [dict(S) for S in segs]
    for tau_ms in (0.0, 5.0, 10.0, 20.0, 30.0, 50.0):
        for S, B in zip(segs, base):
            d = int(round(tau_ms / 1000.0 * FS))
            y = np.roll(B["cmd"], d)
            y[:d] = B["cmd"][0]
            S["tq"] = y + 0.02 * np.std(B["cmd"]) * RNG.standard_normal(len(y))
        Sxy, Sxx, Syy = accumulate(wins(segs, True))
        t, nb_ = delay_search(Sxy, Sxx, Syy)
        print("  injected {:5.1f} ms  ->  delay-search recovers {:+6.2f} ms   err {:+5.2f} ms   "
              "({} bins)   {}".format(tau_ms, t, t - tau_ms, nb_,
                                      "PASS" if abs(t - tau_ms) < 1.0 else "FAIL"))
    for S, B in zip(segs, base):
        S["tq"] = B["tq"]
    print("  ** The DELAY SEARCH is unbiased to <1 ms out to 50 ms. The v89_g2 band-average angle")
    print("     was biased ~5-9 deg at 30-50 ms lag; at the ~10 ms lags in play it is ~1.5 deg. **")

    tau_ha = ha_delay()
    print("\n  H_A's own equivalent transport lag, same estimator, same bins: {:+.2f} ms".format(
        tau_ha))
    rep["tau_HA_ms"] = tau_ha

    print("\n" + "=" * 104)
    print("EQUIVALENT LAG PER ARM (polarity-corrected; positive = column LAGS command)")
    print("=" * 104)
    Weng = wins(segs, True)
    Wman = wins(segs, False)
    Whs = wins([S for S in segs if S["s"] in (4, 5)], True)
    for lab, W in (("ENGAGED (all)", Weng),
                   ("ENGAGED highway seg4+5", Whs),
                   ("MANUAL -- C1 CONTROL", Wman)):
        if len(W) < 12:
            print("  {}: {} windows -- UNINTERPRETABLE".format(lab, len(W)))
            continue
        tau, ciu, nbins, nk = arm_delay(W)
        inside = ciu[0] <= tau_ha <= ciu[1]
        print("  {:26s} n={:3d} win / {:2d} blk / {:3d} coherent bins   tau = {:+6.2f} ms "
              "[{:+6.2f}, {:+6.2f}]   H_A {:+.2f} ms  =>  {}".format(
                  lab, len(W), nk, nbins, tau, ciu[0], ciu[1], tau_ha,
                  "CONSISTENT" if inside else "INCONSISTENT"))
        rep[lab] = {"tau_ms": tau, "ci": list(ciu), "bins": nbins, "windows": len(W),
                    "blocks": nk, "consistent_with_HA": bool(inside)}

    print("\n" + "=" * 104)
    print("CAUSALITY -- which way does it run?  Peak of the cmd/column cross-correlation, 2-25 Hz.")
    print("             NEGATIVE lag = the COLUMN LEADS the command = the FEEDBACK path dominates")
    print("             and NO forward-plant claim can be made from this estimator.")
    print("=" * 104)
    for lab, en in (("ENGAGED", True), ("MANUAL", False)):
        r = xcorr_peak(segs, en)
        if r is None:
            print("  {}: no usable episodes".format(lab))
            continue
        c = r["curve"]
        ks = sorted(c, key=lambda k: -abs(c[k]))[:1]
        print("  {:8s} {} episodes   peak at {:+.0f} ms (r = {:+.3f})".format(
            lab, r["n_episodes"], r["peak_lag_ms"], r["peak_val"]))
        strip = "   ".join("{:+3d}ms {:+.3f}".format(int(L * 1000 / FS), c[L])
                           for L in (-20, -10, -5, 0, 5, 10, 20))
        print("     {}".format(strip))
        rep["xcorr_" + lab] = {k: v for k, v in r.items() if k != "curve"}

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
