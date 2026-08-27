#!/usr/bin/env python3
"""A DAMPING ESTIMATOR THAT IS NOT WINDOW-LIMITED: phase-drift (coherence-time) Q.

WHY.  The periodogram linewidth needs T >= ~2 x 1.4416/FWHM = 0.37 x Q/f0 x f0 seconds to merely
RESOLVE a line, i.e. ~220 s of unbroken engaged driving for Q=600 at 7.79 Hz.  The Lorentzian
coherence time for the same line is only tau = Q/(pi.f0) = 24.5 s.  A phase-drift estimator works
at T ~ 2-3 tau instead of ~9 tau, so it is ~3-4x more data-efficient -- which is the difference
between "V86B's 36 s run cannot see this" and "it can".

METHOD.  Narrow band-pass around the window's own line -> analytic signal -> unwrapped phase.
The PHASE STRUCTURE FUNCTION  D(lag) = < (phi(t+lag) - phi(t))^2 >  of a Wiener (limit-cycle) phase
is  D = 2.pi.FWHM.lag , a straight line through the origin, while ADDITIVE NOISE contributes a
CONSTANT offset at lag>0.  Fitting D = c + s.lag over a lag range therefore separates the two, and
Q = f0 / (s / (2.pi)).  Samples are envelope-weighted: phase is meaningless where the line is not
present, and the line is bursty (duty 12-23%).

VALIDATION FIRST, then application -- an estimator is worth nothing here until its recovery curve
and its scatter are on the table.

Usage:  python studies/damping-q/qd_phase.py
"""
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
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                       # noqa: E402
import qd_win as W                                                       # noqa: E402

RNG = np.random.default_rng(77900)
F0 = 7.79
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + "\n" + s + "\n" + "=" * 112, flush=True)


def phase_q(x, fs, f0, half=0.6, lag_lo=0.5, lag_hi=6.0, wthresh=0.5):
    """Q from the slope of the envelope-weighted phase structure function."""
    x = np.asarray(x, float)
    b = butter(3, [max(f0 - half, 0.5), min(f0 + half, fs / 2 - 1)], btype="band", fs=fs)
    z = hilbert(filtfilt(*b, x))
    env = np.abs(z)
    ph = np.unwrap(np.angle(z))
    n = len(ph)
    w = (env > wthresh * np.median(env)).astype(float)      # phase is meaningless in the gaps
    lags = np.unique(np.round(np.linspace(lag_lo, lag_hi, 24) * fs).astype(int))
    lags = lags[(lags > 0) & (lags < n - 10)]
    if len(lags) < 6:
        return dict(q_phase=np.nan, slope=np.nan, offset=np.nan, r2=np.nan)
    D, L = [], []
    for k in lags:
        dphi = ph[k:] - ph[:-k]
        ww = w[k:] * w[:-k]
        if ww.sum() < 20:
            continue
        mu = np.sum(ww * dphi) / np.sum(ww)                  # remove the mean frequency offset
        D.append(np.sum(ww * (dphi - mu) ** 2) / np.sum(ww))
        L.append(k / fs)
    if len(D) < 6:
        return dict(q_phase=np.nan, slope=np.nan, offset=np.nan, r2=np.nan)
    D, L = np.asarray(D), np.asarray(L)
    A = np.vstack([np.ones_like(L), L]).T
    coef, *_ = np.linalg.lstsq(A, D, rcond=None)
    off, slope = float(coef[0]), float(coef[1])
    pred = A @ coef
    ss = 1.0 - np.sum((D - pred) ** 2) / max(np.sum((D - D.mean()) ** 2), 1e-12)
    if slope <= 0:
        return dict(q_phase=np.inf, slope=slope, offset=off, r2=float(ss))
    fwhm = slope / (2 * np.pi)
    return dict(q_phase=float(f0 / fwhm), slope=slope, offset=off, r2=float(ss),
                fwhm_phase=float(fwhm))


# ============================================================================================
hdr("F1  VALIDATION -- recover a KNOWN Q from a real manual bed, at the lengths we actually have")
val = {}
for nw, tlab in [(2048, "20.3 s"), (3640, "36.0 s")]:
    bed_pool = [r for b in W.ROUTES for r in W.windows(b, nw, engaged=False)]
    if len(bed_pool) < 3:
        print(f"  T={tlab}: only {len(bed_pool)} manual beds -- widening to engaged-free segments")
    print(f"\n  --- T = {tlab}  (bed n={len(bed_pool)})   periodogram would need "
          f"T >= 0.37 x Q s to resolve; coherence time is Q/(pi.f0) = Q/24.5 s")
    rows = []
    for qt in [30, 60, 120, 250, 500, 1000, np.inf]:
        got, gotl = [], []
        for _ in range(40):
            bed = bed_pool[RNG.integers(0, len(bed_pool))]
            y, _ = Q.inject(np.asarray(bed["x"], float), bed["fs"], F0, qt, 70.0, "cycle", RNG)
            r = phase_q(y, bed["fs"], F0)
            if np.isfinite(r["q_phase"]):
                got.append(r["q_phase"])
            L = Q.linewidth(y, bed["fs"])
            if np.isfinite(L["q_app"]):
                gotl.append(L["q_app"])
        g = np.array(got) if got else np.array([np.nan])
        gl = np.array(gotl) if gotl else np.array([np.nan])
        tau = qt / (np.pi * F0) if np.isfinite(qt) else np.inf
        rows.append(dict(q_true=float(qt), q_phase_med=float(np.median(g)),
                         q_phase_p16=float(np.percentile(g, 16)),
                         q_phase_p84=float(np.percentile(g, 84)),
                         q_line_med=float(np.median(gl)), n=len(g),
                         tau_s=float(tau), T_over_tau=float(nw / 101.1 / tau)))
        print(f"      Q_true {str(qt):>6s} (tau {tau:6.1f} s, T/tau {nw/101.1/tau:5.2f})  ->  "
              f"Q_phase {np.median(g):8.1f} [p16 {np.percentile(g,16):7.1f}, "
              f"p84 {np.percentile(g,84):8.1f}]   |  Q_linewidth {np.median(gl):7.1f}")
    val[tlab] = rows
OUT["validation"] = val

# ============================================================================================
hdr("F2  APPLY to the real engaged windows -- same matched-T design, same blk bootstrap")
res = {}
for nw, tlab in [(1024, "10.1 s"), (2048, "20.3 s")]:
    arms = {}
    for b in W.ROUTES:
        rs = W.order_clean(W.score(W.windows(b, nw)))
        for r in rs:
            r.update(phase_q(r["x"], r["fs"], r["f0"]))
        arms[b] = [r for r in rs if np.isfinite(r.get("q_phase", np.nan))]
    w, counts = W.shared_weights([arms[b] for b in ("V86", "V86B", "V85")])
    print(f"\n  --- T = {tlab}   shared speed weights {w.tolist()}")
    for b in ("V86", "V86B", "V85"):
        rs = arms[b]
        if len(rs) < 2:
            print(f"      {b:5s}  n={len(rs)} -- too few")
            continue
        bb = Q.block_boot([r["q_phase"] for r in rs], [r["blk"] for r in rs], rng=RNG)
        r2 = np.median([r["r2"] for r in rs])
        print(f"      {b:5s} n={bb['n']:3d} blk={bb['nblk']:3d}   Q_phase = {bb['pt']:7.1f} "
              f"[{bb['lo']:7.1f},{bb['hi']:7.1f}]   (structure-fn R2 {r2:.3f})")
    null = Q.boot_ratio(arms["V86B"], arms["V85"], "q_phase", rng=RNG, weights=w, vbins=W.VBINS)
    eff = Q.boot_ratio(arms["V86"], arms["V86B"], "q_phase", rng=RNG, weights=w, vbins=W.VBINS)
    dd = Q.did(arms["V86"], arms["V86B"], arms["V85"], "q_phase", rng=RNG, weights=w,
               vbins=W.VBINS)
    print(f"      NULL  V86B/V85 = {null['ratio']:6.3f} [{null['lo']:6.3f},{null['hi']:6.3f}]"
          f"   (blk {null['blkA']}/{null['blkB']})")
    print(f"      EFF   V86/V86B = {eff['ratio']:6.3f} [{eff['lo']:6.3f},{eff['hi']:6.3f}]"
          f"   (blk {eff['blkA']}/{eff['blkB']})")
    print(f"      DiD            = {dd['did']:6.3f} [{dd['lo']:6.3f},{dd['hi']:6.3f}]")
    res[tlab] = dict(null=null, eff=eff, did=dd,
                     arms={b: dict(n=len(arms[b]),
                                   nblk=len({r['blk'] for r in arms[b]}),
                                   q=float(np.median([r["q_phase"] for r in arms[b]])))
                           for b in ("V86", "V86B", "V85") if arms[b]})
OUT["applied"] = res

json.dump(OUT, open(ROOT / "_scratch/cache/r6f" / "qd_phase.json", "w"), indent=1, default=float)
print("\nwrote _scratch/cache/r6f/qd_phase.json")
