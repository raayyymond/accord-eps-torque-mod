#!/usr/bin/env python3
r"""THE 83.5 Hz COMB SCORE -- the kit's first quantitative endpoint for the low-speed grinding.

WHAT IT MEASURES
----------------
On V107 (route 1e) the operator's low-speed grinding has a measured spectral signature: an
**~83.5 Hz harmonic series five harmonics deep** (82 / 172 / 254 / 328 / 414 Hz), engagement-gated,
p = 0.000 against a null that includes the grid search.  See
`memory/accord/mechanism/accord-the-lowspeed-grind-is-an-83hz-harmonic-series.md`.

    comb score = mean engaged-minus-manual excess (dB) over the first K harmonics of f0,
                 matched speed, hands-off, WITHIN one drive.

🛑 WHY IT IS COMPARABLE ACROSS DRIVES WHEN A dB LEVEL IS NOT.  Absolute cabin level differs 3-12x
between drives, so no raw dB may be compared route to route.  The comb score is itself an
engaged-MINUS-manual quantity computed inside a single drive, so the cabin gain cancels before any
cross-route comparison happens.  That is the whole reason this statistic exists.

🛑 THE CONTROL IS NOT OPTIONAL, AND THE GRID SEARCH MUST BE INSIDE IT.  The null is an
engaged-vs-engaged random split at the same sample sizes, with the SAME f0 grid search run on every
draw.  Scoring the real data with a search and the null without one inflates the result -- that is
the failure this design exists to avoid.

THE PRE-REGISTERED V109 ENDPOINT
--------------------------------
V109 cuts `0xC40DC` (alpha2) so the `gp-0x6b26` lane loses 34 % at 100 Hz and 39 % at 200 Hz.

    comb score drops toward the null  =>  that lane FEEDS the series; alpha2/knee is the lever
    comb score unchanged              =>  it does not; alpha2 is DEAD for this symptom

Both sentences were written before the V109 drive.  Neither is a hedge.

Usage:
    python score/comb_score.py 1e              # score one route
    python score/comb_score.py 1e 97 a6        # compare across the gain ladder
    python score/comb_score.py 1e --draws 400  # heavier null
"""
# --- PATH BOOTSTRAP -------------------------------------------------------
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_roots, _c = [], _here
while True:
    if _os.path.isfile(_os.path.join(_c, ".pkgroot")):
        _roots.append(_c)
    _n = _os.path.dirname(_c)
    if _n == _c:
        break
    _c = _n
_top = _os.path.dirname(_roots[0])
for _e in sorted(_os.listdir(_top)):
    _cand = _os.path.join(_top, _e)
    if _os.path.isfile(_os.path.join(_cand, ".pkgroot")) and _cand not in _roots:
        _roots.append(_cand)
_p = []
for _r in _roots:
    _p.append(_r)
    for _b, _ds, _fs in _os.walk(_r):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_here", "_roots", "_c", "_n", "_top", "_e", "_cand", "_p",
           "_r", "_b", "_ds", "_fs", "_x", "_v"):
    globals().pop(_v, None)
# --------------------------------------------------------------------------
import sys
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "analysis-2020accord" / "_scratch" / "cache"

F_LO, F_HI = 40.0, 500.0     # the band the comb lives in
GRID = np.arange(40.0, 180.0, 0.25)
K_HARM = 6                   # harmonics scored
HALFWIDTH = 6.0              # Hz around each harmonic; ~1.5 bins at 3.91 Hz/bin
VMAX_MPH = 10.0              # the operator's symptom is BELOW ten mph
TQ_THR = 1200.0              # D3 hands-off: rolling-median |cs_tq| over 0.5 s


def _rollmed(x, w):
    n = len(x)
    o = np.full(n, np.nan)
    if n < w:
        return o
    m = np.median(sliding_window_view(np.abs(x), w), axis=1)
    o[w // 2:w // 2 + len(m)] = m
    return o


def load(route):
    c = CACHE / f"r{route}"
    sp, can = c / f"r{route}_spec.npz", c / f"r{route}.npz"
    if not sp.exists() or not can.exists():
        return None
    z = np.load(sp, allow_pickle=True)
    S, f, ts = np.asarray(z["S"]), np.asarray(z["f"]), np.asarray(z["t"])
    y = np.load(can, allow_pickle=True)
    need = ["cc_lat", "cs_v", "t", "cs_tq"]
    if any(k not in y.files for k in need):
        return None
    a = {k: np.asarray(y[k]).astype(float) for k in need}
    n = min(len(v) for v in a.values())
    a = {k: v[:n] for k, v in a.items()}
    dt = float(np.median(np.diff(a["t"])))
    ho = _rollmed(a["cs_tq"], max(3, int(round(0.5 / dt)) | 1)) < TQ_THR
    idx = np.clip(np.searchsorted(a["t"] - a["t"][0], ts), 0, n - 1)
    mph = a["cs_v"][idx] * 2.23694
    tag = str(np.asarray(y["probe_build"]).ravel()[0]) if "probe_build" in y.files else "?"
    return dict(S=S, f=f, mph=mph, lat=a["cc_lat"][idx], ho=ho[idx], tag=tag)


def _comb(excess, fb, f0):
    vals = []
    for k in range(1, K_HARM + 1):
        fc = k * f0
        if fc > fb[-1]:
            break
        s = (fb >= fc - HALFWIDTH) & (fb <= fc + HALFWIDTH)
        if s.any():
            vals.append(excess[s].max())
    return np.mean(vals) if len(vals) >= 4 else -99.0


def _excess(S, A, B, band):
    num = np.maximum(np.median(S[A], 0), 1e-30)
    den = np.maximum(np.median(S[B], 0), 1e-30)
    return (10 * np.log10(num / den))[band]


def score(route, draws=200, seed=20260827):
    d = load(route)
    if d is None:
        print(f"  r{route}: no spectrogram or no CAN cache")
        return None
    rng = np.random.default_rng(seed)
    band = (d["f"] >= F_LO) & (d["f"] <= F_HI)
    fb = d["f"][band]
    e = np.flatnonzero(np.isfinite(d["mph"]) & (d["lat"] > 0.5) & d["ho"] & (d["mph"] < VMAX_MPH))
    m = np.flatnonzero(np.isfinite(d["mph"]) & (d["lat"] < 0.5) & (d["mph"] < VMAX_MPH)
                       & (d["mph"] > 1.0))
    if len(e) < 300 or len(m) < 300:
        print(f"  r{route} ({d['tag']}): thin -- {len(e)} engaged / {len(m)} manual frames")
        return None
    real = _excess(d["S"], e, m, band)
    sc = np.array([_comb(real, fb, x) for x in GRID])
    best, best_sc = GRID[np.argmax(sc)], sc.max()
    # NULL: engaged-vs-engaged, SAME sizes, SAME grid search inside every draw
    # 🛑 Arm size: DISJOINT halves of the engaged frames, each capped at len(m).  The earlier
    # version drew A=e[:len(m)] and B=e[len(m):2*len(m)] and broke out when len(e) < 2*len(m) --
    # which is MOST routes -- silently producing ZERO draws and a nan null.  A grid-searched score
    # with no null is guaranteed positive and means nothing.  Smaller null arms make the null
    # NOISIER than the real comparison, so this errs conservative (harder to beat), never lenient.
    half = min(len(m), len(e) // 2)
    null = []
    if half >= 150:
        for _ in range(draws):
            p = rng.permutation(len(e))
            A, B = e[p[:half]], e[p[half:2 * half]]
            r2 = _excess(d["S"], A, B, band)
            null.append(max(_comb(r2, fb, x) for x in GRID))
    null = np.array(null)
    if not len(null):
        print(f"  r{route} ({d['tag']}): NULL UNAVAILABLE -- only {len(e)} engaged frames, "
              f"cannot form two disjoint arms of >=150.  A grid-searched score without a null is "
              f"meaningless; NOT reporting one.")
        return None
    p95 = np.percentile(null, 95)
    pval = float(np.mean(null >= best_sc)) if len(null) else np.nan
    print(f"  r{route:<4s} {d['tag']:<12s} f0 {best:6.2f} Hz   score {best_sc:+6.3f} dB   "
          f"null p95 {p95:+.3f} max {null.max() if len(null) else float('nan'):+.3f}   "
          f"p {pval:.3f}   ({len(e)} eng / {len(m)} man, {len(null)} draws)")
    for k in range(1, K_HARM + 1):
        fc = k * best
        if fc > fb[-1]:
            break
        s = (fb >= fc - HALFWIDTH) & (fb <= fc + HALFWIDTH)
        if s.any():
            print(f"        {k}x {fc:7.1f} Hz  {real[s].max():+6.2f} dB  "
                  f"(bin {fb[s][np.argmax(real[s])]:.1f})")
    return dict(route=route, tag=d["tag"], f0=best, score=best_sc, p95=p95, p=pval)


if __name__ == "__main__":
    args = sys.argv[1:]
    draws = 200
    if "--draws" in args:
        i = args.index("--draws")
        draws = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    if not args:
        args = ["1e"]
    print("THE 83.5 Hz COMB SCORE -- engaged minus manual, matched speed, hands-off, WITHIN drive.")
    print("Null = engaged-vs-engaged split with the SAME grid search inside every draw.\n")
    out = [score(r, draws=draws) for r in args]
    out = [o for o in out if o]
    if len(out) > 1:
        print("\n  SUMMARY")
        print("  %-6s %-12s %8s %9s %9s %7s" % ("route", "build", "f0 Hz", "score dB", "p95", "p"))
        for o in out:
            print("  %-6s %-12s %8.2f %9.3f %9.3f %7.3f"
                  % (o["route"], o["tag"], o["f0"], o["score"], o["p95"], o["p"]))
        print("\n  🛑 Compare SCORES, never raw dB: the score is engaged-minus-manual computed")
        print("     inside each drive, so cabin gain (3-12x between drives) has already cancelled.")
