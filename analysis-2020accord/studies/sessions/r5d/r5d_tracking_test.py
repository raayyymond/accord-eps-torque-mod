#!/usr/bin/env python3
"""Route `5d` -- THE TRACKING TEST for the elevated ~40 Hz line, requested by team-lead 2026-08-06.

`studies/sessions/r5d/r5d_falsifiers.py`'s Falsifier B searches for the "5 x f0" peak within +/-4 bins of the PREDICTED
location (5 x that build's own f0). That is a narrow, f0-ANCHORED search -- it cannot by itself tell
a genuine relay harmonic (which should sit at 5 x f0 and MOVE when f0 moves) apart from a fixed,
pre-existing line near ~42 Hz (grind #1's documented 2nd harmonic, memory
`accord/builds/accord-v59-parametric-pump-marginal.md`) that a f0-anchored search will only ever "catch" when 5 x f0
happens to land near it.

This script does the discriminating measurement INSTEAD: an INDEPENDENT, UN-ANCHORED peak search over
a WIDE band (33-47 Hz) for every build, on both the standard engaged v<12.5 arm and the CREEP-only
arm. Then it regresses the found peak's own frequency against (a) 5 x that build's f0 and (b) 2 x that
build's own grind-#1 (18-22 Hz) line frequency, across builds. Per the kit's own retracted-harmonic
lesson (`git 9bd38fc` -- "a ratio is not a tracking test"): a ratio or a single point is not enough,
this is a build-to-build REGRESSION, with a CI on the slope.

  slope(peak vs 5 x f0)      ~= 1  =>  the peak MOVES WITH the ratchet -- genuine relay harmonic.
                             ~= 0  =>  the peak sits at a FIXED frequency regardless of f0.
  slope(peak vs 2 x fgrind1) ~= 1  =>  the peak moves with grind #1 -- consistent with a pre-existing
                                       2nd harmonic of that (largely build-invariant) resonance.

Also checked: is V74's creep-arm elevation present in the MANUAL (byte-stock) creep arm? V74 wrote
only the ENGAGED column, so if manual creep ALSO shows the elevated line, it cannot be the damper.

Usage:  python studies/sessions/r5d/r5d_tracking_test.py   ->  writes _scratch/out/_r5d_tracking_test.json
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5d_lib as L  # noqa: E402
import d6_events as D  # noqa: E402

RNG = np.random.default_rng(20260806)
OUT = {}
D.PARKED["V74/r5d"] = [2, 3, 9]
L.install_fs()
BUILDS = ["V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V69/r4f", "V71B/r54",
          "V71C/r58", "V72/r59", "V73/r5a", "V74/r5d"]
WIDEBAND = (33.0, 47.0)   # independent search, NOT anchored to any build's 5xf0
GRIND1 = (18.0, 22.0)
RATCHET = (6.0, 9.0)


def load_runs(build, vlo=0.0, vhi=12.5, engaged=True):
    out = []
    for _, s, a, b, d, fs in D.runs(build, vlo, vhi, engaged, 512):
        out.append(dict(run=(build, s, a), x=np.asarray(d["tq"][a:b], float), fs=fs))
    return out


def avg_spec(runs, nfft=2048):
    acc, K, fr = None, 0, None
    for r in runs:
        x, fs = r["x"], r["fs"]
        for i in range(0, len(x) - nfft + 1, nfft // 2):
            P = C.periodogram(x[i:i + nfft], fs, nfft, True)
            if P is None:
                continue
            fr = np.fft.rfftfreq(nfft, 1 / fs) if fr is None else fr
            acc = P.copy() if acc is None else acc + P
            K += 1
    return (fr, acc / K, K) if K else (None, None, 0)


def triple(runs, nfft=2048):
    """(f0, fgrind1, wideband_peak_f, wideband_peak_prom, K) -- the wideband peak is UN-ANCHORED."""
    fr, P, K = avg_spec(runs, nfft)
    if P is None or K < 2:
        return (np.nan,) * 4 + (K,)
    R = G.prom_spectrum(fr, P)
    f0, _ = G.locate(fr, P, *RATCHET, R=R)
    fg1, _ = G.locate(fr, P, *GRIND1, R=R)
    fw, pw = G.locate(fr, P, *WIDEBAND, R=R)
    return float(f0), float(fg1), float(fw), float(pw), K


def boot_triple(runs, nfft, nboot=400):
    """Bootstrap the wideband peak freq (resample runs) for a per-build CI."""
    if len(runs) < 3:
        return np.nan, np.nan
    vals = []
    for _ in range(nboot):
        samp = [runs[j] for j in RNG.integers(0, len(runs), len(runs))]
        _, _, fw, _, K = triple(samp, nfft)
        if K >= 2 and np.isfinite(fw):
            vals.append(fw)
    if len(vals) < 20:
        return np.nan, np.nan
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


# ================================================================== 1. per-build triples ===========
L.hdr("1. PER-BUILD: f0, f(grind #1), and the INDEPENDENT wideband (33-47 Hz) peak -- engaged v<12.5")
print("  The wideband peak is NOT anchored to 5 x f0 -- it is the tallest prominence peak found freely")
print("  in [33,47] Hz. If that peak IS the ratchet's 5th harmonic, it should equal 5 x f0. If it is")
print("  grind #1's pre-existing 2nd harmonic, it should sit near a FIXED frequency (~42.19 Hz per the")
print("  V59 record) regardless of f0.\n")
print(f"  {'build':<10} {'K':>4} {'f0':>6} {'5xf0':>6} {'fgrind1':>8} {'2xfg1':>7} "
      f"{'wideband_f':>10} {'wb_prom':>8} {'wb 95%CI':>16}")
rows = {}
for b in BUILDS:
    rs = load_runs(b, 0.0, 12.5, True)
    f0, fg1, fw, pw, K = triple(rs)
    lo, hi = boot_triple(rs, 2048)
    rows[b] = dict(f0=f0, fgrind1=fg1, fw=fw, prom=pw, K=K, wb_lo=lo, wb_hi=hi)
    print(f"  {b:<10} {K:>4} {f0:>6.2f} {5 * f0:>6.2f} {fg1:>8.2f} {2 * fg1:>7.2f} "
          f"{fw:>10.2f} {pw:>8.2f} [{lo:>6.2f},{hi:>6.2f}]")
OUT["engaged_triples"] = rows

# ================================================================== 2. the CREEP arm ================
L.hdr("2. THE SAME TRIPLE ON THE CREEP ARM (v<4 m/s) -- where V74's elevation was largest")
print(f"  {'build':<10} {'K':>4} {'f0':>6} {'5xf0':>6} {'fgrind1':>8} {'2xfg1':>7} "
      f"{'wideband_f':>10} {'wb_prom':>8}")
rows_c = {}
for b in BUILDS:
    rs = load_runs(b, 0.0, 4.0, True)
    f0, fg1, fw, pw, K = triple(rs)
    rows_c[b] = dict(f0=f0, fgrind1=fg1, fw=fw, prom=pw, K=K)
    if K:
        print(f"  {b:<10} {K:>4} {f0:>6.2f} {5 * f0:>6.2f} {fg1:>8.2f} {2 * fg1:>7.2f} "
              f"{fw:>10.2f} {pw:>8.2f}")
    else:
        print(f"  {b:<10}    0  -- insufficient creep exposure at NFFT 2048")
OUT["creep_triples"] = rows_c

# ================================================================== 3. THE TRACKING TEST ============
L.hdr("3. ★★★ THE TRACKING TEST -- regression across builds, engaged v<12.5 arm (larger K, more builds)")
print("  If the wideband peak is a genuine 5th harmonic of the ratchet, peak_f should equal 5*f0 with")
print("  slope 1 as f0 varies build to build. If it is grind #1's fixed 2nd harmonic, slope should be")
print("  ~0 (peak_f constant near ~42 Hz) regardless of 5*f0.\n")


def wls_slope(x, y, nboot=4000):
    """OLS slope/intercept + a build-level bootstrap CI (resample BUILDS, the natural unit here)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 4:
        return dict(n=n, slope=np.nan, intercept=np.nan, slo=np.nan, shi=np.nan, r=np.nan)
    A = np.vstack([x, np.ones(n)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    r = float(np.corrcoef(x, y)[0, 1]) if n > 2 else np.nan
    boots = []
    for _ in range(nboot):
        j = RNG.integers(0, n, n)
        xs, ys = x[j], y[j]
        if len(set(xs.round(6))) < 2:
            continue
        A2 = np.vstack([xs, np.ones(len(xs))]).T
        s2, _ = np.linalg.lstsq(A2, ys, rcond=None)[0]
        boots.append(s2)
    slo, shi = (float(np.nanpercentile(boots, 2.5)), float(np.nanpercentile(boots, 97.5))) \
        if len(boots) > 50 else (np.nan, np.nan)
    return dict(n=n, slope=float(slope), intercept=float(intercept), slo=slo, shi=shi, r=r)


x_5f0 = [rows[b]["f0"] * 5 for b in BUILDS if rows[b]["K"] >= 2]
y_wb = [rows[b]["fw"] for b in BUILDS if rows[b]["K"] >= 2]
x_2g1 = [rows[b]["fgrind1"] * 2 for b in BUILDS if rows[b]["K"] >= 2]
bnames = [b for b in BUILDS if rows[b]["K"] >= 2]

res1 = wls_slope(x_5f0, y_wb)
res2 = wls_slope(x_2g1, y_wb)
print(f"  peak_f vs 5*f0     : slope = {res1['slope']:.3f} [{res1['slo']:.3f}, {res1['shi']:.3f}]  "
      f"intercept = {res1['intercept']:.2f} Hz   r = {res1['r']:.3f}   n = {res1['n']} builds")
print(f"  peak_f vs 2*fgrind1: slope = {res2['slope']:.3f} [{res2['slo']:.3f}, {res2['shi']:.3f}]  "
      f"intercept = {res2['intercept']:.2f} Hz   r = {res2['r']:.3f}   n = {res2['n']} builds")
print(f"\n  raw pairs (build, 5*f0, 2*fgrind1, peak_f):")
for b in bnames:
    print(f"    {b:<10} 5*f0={5 * rows[b]['f0']:6.2f}   2*fg1={2 * rows[b]['fgrind1']:6.2f}   "
          f"peak_f={rows[b]['fw']:6.2f}")
print(f"\n  spread of peak_f across builds: {min(y_wb):.2f} .. {max(y_wb):.2f} Hz "
      f"(sd = {np.std(y_wb):.3f} Hz)")
print(f"  spread of 5*f0 across builds:   {min(x_5f0):.2f} .. {max(x_5f0):.2f} Hz "
      f"(sd = {np.std(x_5f0):.3f} Hz)")
print("  🛑 If peak_f's spread is MUCH SMALLER than 5*f0's spread, the peak cannot be tracking f0 --")
print("  a fixed line has near-zero spread regardless of how much the predictor moves.")
OUT["tracking_5xf0"] = res1
OUT["tracking_2xgrind1"] = res2
OUT["raw_pairs"] = {b: dict(f5=5 * rows[b]["f0"], g2=2 * rows[b]["fgrind1"], peak=rows[b]["fw"])
                    for b in bnames}

# ================================================================== 4. MANUAL creep, V74 only =======
L.hdr("4. ★ IS V74's CREEP ELEVATION PRESENT IN THE MANUAL (BYTE-STOCK) ARM TOO?")
print("  V74 writes ONLY the engaged column (mode 26); mode 24 (manual) is byte-stock. If the ~42 Hz")
print("  elevation appears in manual creep too, it cannot be the damper (Lever E') causing it.\n")
man = load_runs("V74/r5d", 0.0, 4.0, False)
eng = load_runs("V74/r5d", 0.0, 4.0, True)
print(f"  V74 manual creep runs: {len(man)}   V74 engaged creep runs: {len(eng)}")
for lab, rs in (("manual", man), ("engaged", eng)):
    f0, fg1, fw, pw, K = triple(rs)
    print(f"    {lab:<8} K={K:>3}  f0={f0:>6.2f}  5xf0={5 * f0:>6.2f}  wideband_f={fw:>6.2f}  "
          f"wideband_prom={pw:>6.2f}")
    OUT.setdefault("manual_vs_engaged_creep", {})[lab] = dict(f0=f0, fw=fw, prom=pw, K=K)

with open(ROOT / "_scratch/out/_r5d_tracking_test.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_tracking_test.json")
