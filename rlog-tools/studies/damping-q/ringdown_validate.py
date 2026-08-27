#!/usr/bin/env python3
r"""RING-DOWN / RESONANCE ESTIMATOR VALIDATION -- the CONTROL, run before any measurement.

WHY THIS FILE EXISTS
  `feedback-run-the-control-before-the-measurement`: `q_of` returns Q = 79.00 on WHITE NOISE, and
  `accord-ringdown-q-needs-a-step-control` records TWO agents independently fitting a BANDPASS
  FILTER'S OWN STEP RESPONSE and reading it as plant damping (Q ~ 7 and Q ~ 10.4 at R2 = 0.987 over
  a 19.5x decay -- both artefacts).  Nothing here is allowed to be quoted until the recovered-vs-true
  table below is printed and the null floor is stated.

WHAT IS UNDER TEST -- four estimators of (f_n, zeta), all fed EXACTLY the same synthetic inputs
  E1 `hilbert_env`   2nd-order Butterworth band-pass + Hilbert envelope + log-linear fit.
                     This is `rlog-tools/studies/stock-baseline/stock_r97_ringdown.py`'s estimator, verbatim in structure.
  E2 `demod`         complex demodulation at f0 + brick-wall LP at B_LP + log-linear fit.
                     This is `rlog-tools/studies/damping-q/r67_ringdown_q2.py`'s estimator.
  E3 `pencil`        matrix-pencil (Hua-Sarkar) pole estimate on the RAW post-edge samples.
                     NO FILTER AT ALL -- structurally immune to the filter-step-response artefact
                     that killed E1/E2 in the record.  This is the candidate replacement.
  E4 `twopole_psd`   2-pole (f_n, zeta, gain) least-squares fit to the Welch auto-spectrum.
                     This is the estimator behind `docs/research/ANALYSIS-2026-08-20-torsion-bar-and-lane-weight.md`
                     (8.162 Hz, Q 10.21).  It is a STEADY-STATE estimator, included so its null
                     floor can be quoted beside the transient ones.

THE THREE NULLS (an estimator that cannot tell these from a real decay is worthless)
  N1 WHITE NOISE            the historically-fatal null.
  N2 PERFECT STEP           a sinusoid that stops DEAD at t0 -- zero plant decay.  Any apparent
                            tau is 100 % filter.  This is the control from
                            `accord-ringdown-q-needs-a-step-control`.
  N3 PHASE-RANDOMISED       same power spectrum as real route data, phase destroyed.  The RIGHT null
                            for a coloured, bursty, non-stationary background
                            (`feedback-run-the-control-before-the-measurement` item 2).

Usage:  python studies/damping-q/ringdown_validate.py            (synthetic only, ~30 s)
        python studies/damping-q/ringdown_validate.py --real 97  (adds the N3 surrogate built from route 0x97 = STOCK)
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

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert, welch

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
RNG = np.random.default_rng(20260821)

# ------------------------------------------------------------------------------------------------
# ESTIMATORS
# ------------------------------------------------------------------------------------------------


def e1_hilbert_env(x, fs, f0, fit_s=1.5, half=1.5, t_start=0.0):
    """stock_r97_ringdown.env + polyfit on log envelope.  `x` starts AT the edge."""
    b = butter(2, [max(f0 - half, 0.5), min(f0 + half, fs / 2 - 0.5)], btype="band", fs=fs)
    e = np.abs(hilbert(filtfilt(*b, np.asarray(x, float))))
    tt = np.arange(len(e)) / fs
    m = (tt >= t_start) & (tt <= t_start + fit_s) & (e > 0)
    if m.sum() < 20:
        return np.nan, np.nan
    c = np.polyfit(tt[m], np.log(e[m]), 1)
    lam = -float(c[0])
    if not np.isfinite(lam) or lam <= 0:
        return np.nan, np.nan
    return f0, lam / (2 * np.pi * f0)


def e2_demod(x, fs, f0, fit_s=1.5, b_lp=4.0, t_start=0.15):
    """r67_ringdown_q2.demod + log-linear fit.  Time resolution tau_filter = 1/(2 pi b_lp)."""
    x = np.asarray(x, float)
    t = np.arange(len(x)) / fs
    z = (x - x.mean()) * np.exp(-2j * np.pi * f0 * t)
    Z = np.fft.fft(z)
    f = np.fft.fftfreq(len(z), 1 / fs)
    Z[np.abs(f) > b_lp] = 0
    e = 2.0 * np.abs(np.fft.ifft(Z))
    m = (t >= t_start) & (t <= t_start + fit_s) & (e > 0)
    if m.sum() < 20:
        return np.nan, np.nan
    sl, _ = np.polyfit(t[m], np.log(e[m]), 1)
    if not np.isfinite(sl) or sl >= 0:
        return np.nan, np.nan
    return f0, (-sl) / (2 * np.pi * f0)


def e3_pencil(x, fs, f_lo=4.0, f_hi=14.0, order=2, pencil_frac=0.4, n_use=None,
              r2_min=0.35):
    """Matrix pencil (Hua & Sarkar 1990) on the RAW samples -- no band-pass, no envelope.

    Returns the (f, zeta) of the pole inside [f_lo, f_hi] with the largest residue.  Because it
    fits e^{s t} directly it cannot mistake a filter's step response for a plant decay: an
    unfiltered perfect step has NO decaying pole to find.
    """
    x = np.asarray(x, float)
    x = x - x.mean()
    if n_use:
        x = x[:n_use]
    N = len(x)
    if N < 40:
        return np.nan, np.nan
    L = int(pencil_frac * N)
    if L < order + 2 or N - L < order + 2:
        return np.nan, np.nan
    # Hankel
    Y = np.lib.stride_tricks.sliding_window_view(x, L + 1)      # (N-L, L+1)
    Y0, Y1 = Y[:, :-1], Y[:, 1:]
    try:
        U, s, Vh = np.linalg.svd(Y0, full_matrices=False)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    M = min(order * 2, int(np.count_nonzero(s > s[0] * 1e-10)))
    if M < 2:
        return np.nan, np.nan
    Us, ss, Vs = U[:, :M], s[:M], Vh[:M]
    # rank-truncated pencil: project onto the M-dim signal subspace
    A = np.diag(1.0 / ss) @ Us.T @ Y1 @ Vs.conj().T
    if not np.all(np.isfinite(A)):
        return np.nan, np.nan
    lam = np.linalg.eigvals(A)
    lam = lam[np.abs(lam) > 1e-12]
    if not len(lam):
        return np.nan, np.nan
    s_pole = np.log(lam.astype(complex)) * fs
    f = np.abs(s_pole.imag) / (2 * np.pi)
    sig = s_pole.real
    ok = (f >= f_lo) & (f <= f_hi) & (sig < 0) & (np.abs(sig) < 2 * np.pi * f)
    if not ok.any():
        return np.nan, np.nan
    # 🛑 SELECT BY RESIDUE, NOT BY MIN ZETA.  Picking the least-damped admissible pole lets a NOISE
    # pole win on a real decay -- that defect gave AUC 0.798 against the perfect-step control in the
    # first run of this file.  Solving the Vandermonde LS for the amplitudes and taking the largest
    # makes the estimator pick the pole that actually carries the energy.
    cand = np.flatnonzero(ok)
    n_ = np.arange(N)
    V = np.power(lam[cand][None, :].astype(complex), n_[:, None])
    try:
        amp, *_ = np.linalg.lstsq(V, x.astype(complex), rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    k = cand[int(np.argmax(np.abs(amp)))]
    zk = -sig[k] / np.sqrt(sig[k] ** 2 + (2 * np.pi * f[k]) ** 2)
    # 🛑 GOODNESS-OF-FIT GATE.  Without it the pencil happily returns a NOISE pole after a perfect
    # step (AUC 0.854 against the step control in run 2 of this file).  `frac` is the share of the
    # segment's variance explained by the SELECTED mode alone; on pure noise it is small.
    j = int(np.flatnonzero(cand == k)[0])
    recon = 2.0 * np.real(amp[j] * np.power(lam[k].astype(complex), n_))
    frac = 1.0 - float(np.sum((x - recon) ** 2)) / max(float(np.sum(x ** 2)), 1e-30)
    if frac < r2_min:
        return np.nan, np.nan
    return float(f[k]), float(zk)


def _twopole(f, fn, z, g):
    r = f / fn
    return g / ((1 - r ** 2) ** 2 + (2 * z * r) ** 2)


def e4_twopole_psd(x, fs, f_lo=4.0, f_hi=14.0, nfft=512):
    """2-pole LS fit to the Welch PSD over [f_lo, f_hi].  A STEADY-STATE estimator."""
    x = np.asarray(x, float)
    if len(x) < nfft:
        nfft = 1 << int(np.floor(np.log2(max(len(x), 8))))
    if nfft < 32:
        return np.nan, np.nan
    f, p = welch(x - x.mean(), fs=fs, nperseg=nfft, noverlap=nfft // 2)
    m = (f >= f_lo) & (f <= f_hi)
    if m.sum() < 8:
        return np.nan, np.nan
    ff, pp = f[m], p[m]
    best, bfn, bz = np.inf, np.nan, np.nan
    for fn in np.linspace(f_lo + 0.2, f_hi - 0.2, 120):
        for z in np.logspace(np.log10(0.002), np.log10(0.6), 90):
            shape = _twopole(ff, fn, z, 1.0)
            g = float(np.dot(shape, pp) / max(np.dot(shape, shape), 1e-30))
            r = float(np.sum((pp - g * shape) ** 2))
            if r < best:
                best, bfn, bz = r, fn, z
    return bfn, bz


ESTIMATORS = {
    "E1 hilbert_env": lambda x, f0: e1_hilbert_env(x, FS, f0),
    "E2 demod": lambda x, f0: e2_demod(x, FS, f0),
    "E3 pencil": lambda x, f0: e3_pencil(x, FS),
    "E4 twopole_psd": lambda x, f0: e4_twopole_psd(x, FS),
}

# ------------------------------------------------------------------------------------------------
# SIGNAL FACTORIES
# ------------------------------------------------------------------------------------------------


def make_ringdown(fn, zeta, dur=4.0, fs=FS, amp=400.0, snr_db=20.0, rng=RNG, pre=1.0):
    """Damped sinusoid starting at t = `pre`.  Returns (whole, post_edge_slice)."""
    n_pre, n_post = int(pre * fs), int(dur * fs)
    t = np.arange(n_post) / fs
    wd = 2 * np.pi * fn * np.sqrt(max(1 - zeta ** 2, 1e-9))
    ring = amp * np.exp(-zeta * 2 * np.pi * fn * t) * np.sin(wd * t)
    # steady oscillation before the edge, at the same amplitude
    tp = np.arange(n_pre) / fs
    pre_sig = amp * np.sin(2 * np.pi * fn * (tp - pre))
    x = np.concatenate([pre_sig, ring])
    nfloor = amp * 10 ** (-snr_db / 20.0)
    x = x + rng.normal(0, nfloor, len(x))
    return x, n_pre


def make_perfect_step(fn, dur=4.0, fs=FS, amp=400.0, snr_db=20.0, rng=RNG, pre=1.0):
    """N2: the oscillation STOPS DEAD.  Zero plant decay.  Any recovered tau is pure filter."""
    n_pre, n_post = int(pre * fs), int(dur * fs)
    tp = np.arange(n_pre) / fs
    x = np.concatenate([amp * np.sin(2 * np.pi * fn * (tp - pre)), np.zeros(n_post)])
    nfloor = amp * 10 ** (-snr_db / 20.0)
    return x + rng.normal(0, nfloor, len(x)), n_pre


def make_white(dur=5.0, fs=FS, amp=400.0, rng=RNG, pre=1.0):
    n = int((dur + pre) * fs)
    return rng.normal(0, amp, n), int(pre * fs)


def phase_randomise(x, rng=RNG):
    """N3: identical power spectrum, destroyed phase."""
    X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    if len(x) % 2 == 0:
        ph[-1] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


# ------------------------------------------------------------------------------------------------
# DRIVERS
# ------------------------------------------------------------------------------------------------

ZETAS = [0.005, 0.010, 0.020, 0.049, 0.100, 0.200]     # 0.049 = the kit's 2026-08-20 torsion-bar value
FN = 8.16                                              # the kit's measured f_n
NREP = 40
OUT: dict = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def recovery_table(snr_db=20.0, dur=4.0):
    hdr("1.  RECOVERY -- damped sinusoid, f_n = %.2f Hz, SNR %.0f dB, %.1f s post-edge, n = %d reps"
        % (FN, snr_db, dur, NREP))
    print("    truth zeta ->  each cell: median recovered zeta  [p10, p90]   (median f_n)")
    print("    %-16s %s" % ("estimator", "".join("%22s" % ("z=%.3f" % z) for z in ZETAS)))
    res = {}
    for name, est in ESTIMATORS.items():
        cells, row = [], {}
        for z in ZETAS:
            zs, fs_ = [], []
            for r in range(NREP):
                rng = np.random.default_rng(1000 + r)
                x, n_pre = make_ringdown(FN, z, dur=dur, snr_db=snr_db, rng=rng)
                seg = x[n_pre:] if name != "E4 twopole_psd" else x
                f_, z_ = est(seg, FN)
                if np.isfinite(z_):
                    zs.append(z_); fs_.append(f_)
            if zs:
                zs = np.array(zs)
                cells.append("%7.4f[%.3f,%.3f]%6.2f" % (np.median(zs), np.percentile(zs, 10),
                                                        np.percentile(zs, 90), np.median(fs_)))
                row["%.3f" % z] = dict(med=float(np.median(zs)),
                                       p10=float(np.percentile(zs, 10)),
                                       p90=float(np.percentile(zs, 90)),
                                       fn=float(np.median(fs_)), n=len(zs))
            else:
                cells.append("%22s" % "-- no fit --")
                row["%.3f" % z] = None
        print("    %-16s %s" % (name, "".join("%22s" % c for c in cells)))
        res[name] = row
    OUT["recovery"] = res

    # monotonicity / ordering score
    print("\n    ORDERING (does the estimator rank the truth?)  Spearman rho of median-recovered vs truth,")
    print("    and the DYNAMIC RANGE it spans across zeta = %.3f -> %.3f:" % (ZETAS[0], ZETAS[-1]))
    for name in ESTIMATORS:
        row = res[name]
        v = [row["%.3f" % z]["med"] if row["%.3f" % z] else np.nan for z in ZETAS]
        v = np.array(v, float)
        ok = np.isfinite(v)
        if ok.sum() < 3:
            print("      %-16s  INSUFFICIENT" % name); continue
        from scipy.stats import spearmanr
        rho = spearmanr(np.array(ZETAS)[ok], v[ok]).statistic
        dr = v[ok][-1] / v[ok][0] if v[ok][0] > 0 else np.nan
        truth_dr = ZETAS[-1] / ZETAS[0]
        print("      %-16s  rho = %+.3f   dynamic range %6.1fx  (truth spans %.0fx)  %s"
              % (name, rho, dr, truth_dr, "OK" if rho > 0.9 and dr > 0.25 * truth_dr else
                 "🛑 COMPRESSED" if rho > 0.9 else "🛑 DOES NOT ORDER"))


def null_table(dur=4.0, snr_db=20.0, real=None):
    hdr("2.  THE NULL FLOOR -- what each estimator returns when there is NOTHING to measure")
    rows = {}

    def bank(maker, label, need_f0=FN):
        vals = {k: [] for k in ESTIMATORS}
        fvals = {k: [] for k in ESTIMATORS}
        for r in range(NREP):
            rng = np.random.default_rng(5000 + r)
            x, n_pre = maker(rng)
            for name, est in ESTIMATORS.items():
                seg = x[n_pre:] if name != "E4 twopole_psd" else x
                f_, z_ = est(seg, need_f0)
                if np.isfinite(z_):
                    vals[name].append(z_); fvals[name].append(f_)
        print("\n    --- %s ---" % label)
        rows[label] = {}
        for name in ESTIMATORS:
            v = np.array(vals[name], float)
            if not len(v):
                print("      %-16s  no fit returned (n=0/%d)  <- refuses the null, GOOD" % (name, NREP))
                rows[label][name] = dict(n=0)
                continue
            print("      %-16s  n=%2d/%d   zeta med %7.4f  [p10 %7.4f, p90 %7.4f]   "
                  "implied Q med %8.1f   f med %6.2f Hz"
                  % (name, len(v), NREP, np.median(v), np.percentile(v, 10),
                     np.percentile(v, 90), 1 / (2 * np.median(v)), np.median(fvals[name])))
            rows[label][name] = dict(n=int(len(v)), med=float(np.median(v)),
                                     p10=float(np.percentile(v, 10)),
                                     p90=float(np.percentile(v, 90)),
                                     q=float(1 / (2 * np.median(v))),
                                     f=float(np.median(fvals[name])))

    bank(lambda rng: make_white(dur=dur, rng=rng), "N1  WHITE NOISE (the historically fatal null)")
    bank(lambda rng: make_perfect_step(FN, dur=dur, snr_db=snr_db, rng=rng),
         "N2  PERFECT STEP -- oscillation stops DEAD, zero plant decay")
    if real is not None:
        t, x = real
        def mk(rng):
            n = int((dur + 1.0) * FS)
            i = rng.integers(0, max(len(x) - n - 1, 1))
            return phase_randomise(x[i:i + n], rng=rng), int(1.0 * FS)
        bank(mk, "N3  PHASE-RANDOMISED REAL DATA (same PSD, destroyed phase)")
    OUT["nulls"] = rows


def separation_test(dur=4.0, snr_db=20.0):
    hdr("3.  SEPARATION -- can the estimator tell a REAL zeta = 0.049 decay from the PERFECT STEP?")
    print("    This is the decisive test.  If the two distributions overlap, the estimator cannot")
    print("    measure the kit's torsion-bar mode at all, no matter how good its R2 is.")
    for name, est in ESTIMATORS.items():
        a, b = [], []
        for r in range(200):
            rng = np.random.default_rng(9000 + r)
            x, n = make_ringdown(FN, 0.049, dur=dur, snr_db=snr_db, rng=rng)
            seg = x[n:] if name != "E4 twopole_psd" else x
            _, z = est(seg, FN)
            if np.isfinite(z):
                a.append(z)
            rng2 = np.random.default_rng(9000 + r)
            y, n2 = make_perfect_step(FN, dur=dur, snr_db=snr_db, rng=rng2)
            seg2 = y[n2:] if name != "E4 twopole_psd" else y
            _, z2 = est(seg2, FN)
            if np.isfinite(z2):
                b.append(z2)
        if len(a) < 10 or len(b) < 10:
            print("    %-16s  data n=%d  step n=%d  -> %s" % (name, len(a), len(b),
                  "STEP REFUSED (good) " if len(b) < 10 else "insufficient"))
            if len(b) < 10 and len(a) >= 10:
                print("      %sperfect separation: the step yields no fit at all, the decay yields "
                      "zeta med %.4f" % (" " * 4, np.median(a)))
            OUT.setdefault("separation", {})[name] = dict(n_data=len(a), n_step=len(b))
            continue
        a, b = np.array(a), np.array(b)
        # AUC (probability a random decay reads MORE damped than a random step -- we want ~1.0 or ~0.0)
        auc = float(np.mean(a[:, None] > b[None, :]))
        print("    %-16s  decay zeta %.4f [%.4f,%.4f]   step zeta %.4f [%.4f,%.4f]   AUC %.3f  %s"
              % (name, np.median(a), np.percentile(a, 10), np.percentile(a, 90),
                 np.median(b), np.percentile(b, 10), np.percentile(b, 90), auc,
                 "SEPARATES" if abs(auc - 0.5) > 0.45 else "🛑 OVERLAPS -- UNUSABLE"))
        OUT.setdefault("separation", {})[name] = dict(
            data_med=float(np.median(a)), step_med=float(np.median(b)), auc=auc,
            n_data=len(a), n_step=len(b))


def duration_sensitivity():
    hdr("4.  HOW MUCH POST-EDGE DATA IS NEEDED?   truth zeta = 0.049, f_n = 8.16 Hz, SNR 20 dB")
    print("    (tau = 1/(zeta*2*pi*f_n) = %.3f s;  a 1/e decay is %.1f cycles)"
          % (1 / (0.049 * 2 * np.pi * FN), 1 / (0.049 * 2 * np.pi)))
    print("    %-16s %s" % ("estimator", "".join("%16s" % ("%.1f s" % d)
                                                 for d in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0))))
    for name, est in ESTIMATORS.items():
        cells = []
        for d in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
            zs = []
            for r in range(30):
                rng = np.random.default_rng(3000 + r)
                x, n = make_ringdown(FN, 0.049, dur=d, snr_db=20.0, rng=rng)
                seg = x[n:] if name != "E4 twopole_psd" else x
                # E1/E2 fit windows must fit inside the segment
                if name == "E1 hilbert_env":
                    _, z = e1_hilbert_env(seg, FS, FN, fit_s=max(d - 0.05, 0.2))
                elif name == "E2 demod":
                    _, z = e2_demod(seg, FS, FN, fit_s=max(d - 0.2, 0.2))
                else:
                    _, z = est(seg, FN)
                if np.isfinite(z):
                    zs.append(z)
            cells.append("%16s" % ("%.4f (n%2d)" % (np.median(zs), len(zs)) if zs else "--"))
        print("    %-16s %s" % (name, "".join(cells)))


def stationary_twopole_control():
    r"""5.  THE CONTROL FOR THE KIT'S OWN 8.162 Hz / Q 10.21 NUMBER.

    `docs/research/ANALYSIS-2026-08-20-torsion-bar-and-lane-weight.md` got f_n = 8.162 Hz, Q = 10.21,
    zeta = 0.0490 from a POOLED 2-POLE FIT TO THE `T_s` AUTO-SPECTRUM at NFFT 512, 100 Hz.  That is
    a STEADY-STATE estimator on a CONTINUOUSLY-DRIVEN system, so the transient nulls above are the
    wrong control for it.  The right one is: drive a 2-pole of KNOWN zeta with white noise, for a
    realistic engaged duration, and fit it with the identical Welch configuration.
    """
    from scipy.signal import lfilter
    hdr("5.  STATIONARY CONTROL for the 2-pole PSD fit -- the estimator behind the kit's "
        "'8.162 Hz, Q 10.21'")
    print("    white-noise-driven 2-pole, f_n = %.2f Hz, 400 s at 100 Hz, Welch NFFT 512 "
          "(the 2026-08-20 configuration)" % FN)
    print("    + a BROADBAND-CONTAMINATION arm: the same mode plus 1/f^2 background at equal band power")
    print("\n    %10s %14s %10s %14s %10s" % ("truth z", "recovered z", "bias", "recovered z (+bg)",
                                              "bias"))
    rows = {}
    for z in ZETAS:
        got, got_bg = [], []
        for r in range(12):
            rng = np.random.default_rng(7000 + r)
            n = int(400 * FS)
            wn = 2 * np.pi * FN / FS
            # discrete 2-pole via impulse-invariant-ish mapping of s^2+2 z wn s + wn^2
            rr = np.exp(-z * wn)
            b = [1.0]
            a = [1.0, -2 * rr * np.cos(wn * np.sqrt(max(1 - z ** 2, 1e-9))), rr ** 2]
            x = lfilter(b, a, rng.normal(0, 1, n))
            x = x / np.std(x) * 400.0
            f_, z_ = e4_twopole_psd(x, FS, nfft=512)
            if np.isfinite(z_):
                got.append(z_)
            # contamination arm: add red noise with equal 4-14 Hz power
            red = np.cumsum(rng.normal(0, 1, n)); red -= red.mean()
            # 🛑 equalise the 4-14 Hz BAND power (an earlier version normalised TOTAL std, which
            # left a 1/f^2 background with negligible in-band power -- i.e. no contamination at all)
            def _bp(y):
                ff, pp = welch(y - y.mean(), fs=FS, nperseg=512, noverlap=256)
                return float(pp[(ff >= 4) & (ff <= 14)].sum())
            red = red * np.sqrt(_bp(x) / max(_bp(red), 1e-30))
            f2, z2 = e4_twopole_psd(x + red, FS, nfft=512)
            if np.isfinite(z2):
                got_bg.append(z2)
        m = np.median(got) if got else np.nan
        mb = np.median(got_bg) if got_bg else np.nan
        print("    %10.4f %14.4f %9.2fx %14.4f %9.2fx" % (z, m, m / z, mb, mb / z))
        rows["%.3f" % z] = dict(rec=float(m), rec_bg=float(mb))
    print("\n    READ THIS AS: the kit's reported zeta = 0.0490 (Q 10.21) is the RECOVERED value.")
    print("    Invert the table to get the TRUTH interval consistent with it.")
    OUT["stationary_2pole"] = rows


def load_real(route):
    import v102_xb_lib as L
    for r, b in (("97", "V9b-STOCK"), ("9e", "V103"), ("96", "V102")):
        if r not in L.ROUTES:
            L.ROUTES[r] = L._mk(r, b, gain=0, clamp=0, leverB=False, idcode=0, bits=b)
    blks = L.all_blocks(route)
    if not blks:
        return None
    blk = max(blks, key=lambda b: len(b["t"]))
    return blk["t"], np.asarray(blk["tq"], float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default=None, help="route hex tag for the N3 surrogate, e.g. 97")
    a = ap.parse_args()
    real = load_real(a.real) if a.real else None
    if a.real:
        print("N3 surrogate source: route 0x%s, longest gap-free block, %d samples (%.1f s) of `tq`"
              % (a.real, len(real[1]), len(real[1]) / FS))
    recovery_table()
    null_table(real=real)
    separation_test()
    duration_sensitivity()
    stationary_twopole_control()
    p = HERE / "_scratch/out/_ringdown_validate.json"
    p.write_text(json.dumps(OUT, indent=1, default=float))
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
