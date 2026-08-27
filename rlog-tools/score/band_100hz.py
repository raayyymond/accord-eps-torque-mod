#!/usr/bin/env python3
r"""THE ~100 Hz FIXED-BAND SCORE -- the claim that survived the comb's collapse.

WHY A FIXED BAND AND NOT THE COMB
---------------------------------
`score/comb_score.py` grid-searches `f0`, and that search has two defects that only showed up when
it was finally run against STOCK:
  * a **sub-harmonic ambiguity** -- a comb at `f0` always also scores at `f0/2`, so the fitted `f0`
    is not a frequency identification; and
  * **stock fires too**, so "an engaged comb exists" is not by itself evidence of anything ours.

**This statistic has no search.** The band is fixed in advance at the operator's own words -- *"one
mode… maybe around a hundred hertz"* -- and it is the one place where two INDEPENDENT statistics
already agree that stock is quiet:

    third-octave 100 Hz band   STOCK  -0.03 dB   vs  +1.30 .. +5.62 dB on every gain-modified build
    comb 2nd harmonic at 99 Hz STOCK  -0.14 dB   vs  +1.37 (V107) / +2.05 (V106)

    score = median engaged-minus-manual dB over 90-110 Hz,
            matched speed below 10 mph, hands-off, WITHIN one drive.

🛑 Absolute cabin level differs 3-12x between drives, so no raw dB may be compared route to route.
The score is engaged-MINUS-manual computed inside a single drive, so the cabin gain cancels before
any cross-route comparison. That is why THIS quantity may be laddered and a raw level may not.

🛑 THE NULL IS NOT OPTIONAL. Engaged-vs-engaged random split at matched arm sizes, same band, same
estimator. The scorer REFUSES to report a score it cannot null -- the failure that produced four
`nan` rows and a nearly-published five-route ladder.

CONTROL BANDS run alongside, chosen to bracket without overlapping: 55-75, 130-150, 210-230 Hz.
A cabin-gain or exposure artefact lifts all four together; a real ~100 Hz effect does not.

Usage:
    python score/band_100hz.py 97 85 95 96 9e a4 a5 a6 1e
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

import numpy as np

from comb_score import load, VMAX_MPH          # same loader, same hands-off mask, same speed cap

TARGET = (90.0, 110.0)
CONTROLS = [(55.0, 75.0), (130.0, 150.0), (210.0, 230.0)]
GAIN = {"V9b-STOCK": "1x", "V90": "4x", "V92": "4x", "V100": "4x", "V101": "8x",
        "V102": "6x", "V103": "6x", "V104": "6x", "V105": "6x", "V106": "6x", "V107": "6x"}


def _band_db(S, A, B, f, lo, hi):
    s = (f >= lo) & (f <= hi)
    num = np.median(S[A][:, s], 0)
    den = np.median(S[B][:, s], 0)
    return float(np.median(10 * np.log10(np.maximum(num, 1e-30) / np.maximum(den, 1e-30))))


def score(route, draws=300, seed=20260827):
    d = load(route)
    if d is None:
        return None
    rng = np.random.default_rng(seed)
    e = np.flatnonzero(np.isfinite(d["mph"]) & (d["lat"] > 0.5) & d["ho"] & (d["mph"] < VMAX_MPH))
    m = np.flatnonzero(np.isfinite(d["mph"]) & (d["lat"] < 0.5) & (d["mph"] < VMAX_MPH)
                       & (d["mph"] > 1.0))
    if len(e) < 300 or len(m) < 300:
        print(f"  r{route:<4s} {d['tag']:<12s} thin -- {len(e)} eng / {len(m)} man")
        return None
    half = min(len(m), len(e) // 2)
    if half < 150:
        print(f"  r{route:<4s} {d['tag']:<12s} NULL UNAVAILABLE ({len(e)} eng) -- not reporting")
        return None
    real = {b: _band_db(d["S"], e, m, d["f"], *b) for b in [TARGET] + CONTROLS}
    null = []
    for _ in range(draws):
        p = rng.permutation(len(e))
        null.append(_band_db(d["S"], e[p[:half]], e[p[half:2 * half]], d["f"], *TARGET))
    null = np.array(null)
    p95 = float(np.percentile(null, 95))
    pval = float(np.mean(null >= real[TARGET]))
    g = GAIN.get(d["tag"], "?")
    print("  r%-4s %-11s %-3s  100Hz %+6.2f  [null p95 %+5.2f, p %.3f]   ctl %+6.2f %+6.2f %+6.2f"
          % (route, d["tag"], g, real[TARGET], p95, pval,
             real[CONTROLS[0]], real[CONTROLS[1]], real[CONTROLS[2]]))
    return dict(route=route, tag=d["tag"], gain=g, target=real[TARGET], p95=p95, p=pval,
                ctl=[real[c] for c in CONTROLS], n_e=len(e), n_m=len(m))


if __name__ == "__main__":
    args = sys.argv[1:] or ["97", "85", "95", "96", "9e", "a4", "a5", "a6", "1e"]
    print("THE ~100 Hz FIXED-BAND SCORE -- engaged minus manual, matched speed <10 mph, hands-off,")
    print("WITHIN drive.  NO grid search.  Band fixed in advance at 90-110 Hz.")
    print("Controls: 55-75, 130-150, 210-230 Hz -- an artefact lifts all four together.\n")
    out = [o for o in (score(r) for r in args) if o]
    if len(out) > 1:
        print("\n  LADDER, ordered by gain")
        print("  %-6s %-11s %-4s %9s %9s %8s %9s"
              % ("route", "build", "gain", "100Hz dB", "null p95", "p", "mean ctl"))
        for o in sorted(out, key=lambda x: (x["gain"], x["route"])):
            print("  %-6s %-11s %-4s %9.2f %9.2f %8.3f %9.2f"
                  % (o["route"], o["tag"], o["gain"], o["target"], o["p95"], o["p"],
                     float(np.mean(o["ctl"]))))
        sig = [o for o in out if o["p"] < 0.05]
        print("\n  %d of %d routes clear their own null at p<0.05." % (len(sig), len(out)))
        print("  🛑 The question this answers is NOT 'is there energy at 100 Hz' -- it is")
        print("     'is there MORE when engaged than when the driver does the same thing at the")
        print("     same speed on the same drive'.  Stock is the control that decides ownership.")
