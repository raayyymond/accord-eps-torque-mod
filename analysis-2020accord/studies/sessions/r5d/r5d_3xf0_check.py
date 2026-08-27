#!/usr/bin/env python3
"""Route `5d` -- Falsifier B's ODD-HARMONIC-SERIES check at 3 x f0, requested by team-lead 2026-08-06.

A genuine relay generates the WHOLE odd harmonic series (1x, 3x, 5x, 7x...), not just the 5th. If V74
were exciting a real relay-driven cycle, 3 x f0 (~21-25 Hz for this corpus's f0 range) should ALSO be
elevated, independent of the 5x-f0/42-Hz-line confound this session already found.

🛑 BUT 3 x f0 is not automatically unconfounded either: for this corpus's f0 range (7.15-8.46 Hz),
3 x f0 lands at 21.4-25.4 Hz -- which OVERLAPS grind #1's OWN fundamental (measured 20.1-21.9 Hz in
`studies/sessions/r5d/r5d_tracking_test.py`'s per-build table). A "3xf0 elevated" reading could just as easily be grind #1's
fundamental line bleeding into a narrow anchored search, exactly the same class of artifact as the 5xf0
case. This script reports BOTH the anchored reading (matching what a Falsifier-A/B-style check would
show) AND an independent check of how close 3 x f0 sits to that build's own grind-#1 fundamental, so the
confound risk is visible rather than assumed away.

Usage:  python studies/sessions/r5d/r5d_3xf0_check.py   ->  writes _scratch/out/_r5d_3xf0_check.json
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
RATCHET = (6.0, 9.0)
GRIND1 = (18.0, 22.0)


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


def boot_prom_at(runs, target_lo_hz, target_hi_hz, nfft=2048, nboot=600):
    """Bootstrap CI for prominence of the tallest peak in [lo,hi] Hz (resample runs)."""
    vals = []
    for _ in range(nboot):
        samp = [runs[j] for j in RNG.integers(0, len(runs), len(runs))]
        fr, P, K = avg_spec(samp, nfft)
        if P is None or K < 2:
            continue
        R = G.prom_spectrum(fr, P)
        _, p = G.locate(fr, P, target_lo_hz, target_hi_hz, R=R)
        if np.isfinite(p):
            vals.append(p)
    if len(vals) < 20:
        return np.nan, np.nan
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


L.hdr("FALSIFIER B, ODD-HARMONIC CHECK -- 3 x f0, anchored +/-4 bins (matches studies/sessions/r5d/r5d_ratchet.py's style)")
print("  A genuine relay excites the WHOLE odd series. If 3xf0 is normal while 5xf0 reads high, that")
print("  is evidence AGAINST a relay (the series is incomplete). If 3xf0 is ALSO elevated, that is")
print("  independent support FOR a relay -- UNLESS 3xf0 itself overlaps grind #1's own fundamental,")
print("  which this corpus's f0 range makes a live risk (checked in the last two columns).\n")
print(f"  {'build':<10} {'K':>4} {'f0':>6} {'3xf0':>6} {'prom(3xf0)':>10} {'95%CI':>14} "
      f"{'fgrind1':>8} {'|3xf0-fgrind1|':>14}")
rows = {}
for b in BUILDS:
    rs = load_runs(b, 0.0, 12.5, True)
    fr, P, K = avg_spec(rs, 2048)
    if P is None or K < 2:
        print(f"  {b:<10}    0  -- insufficient")
        continue
    R = G.prom_spectrum(fr, P)
    f0, _ = G.locate(fr, P, *RATCHET, R=R)
    fg1, _ = G.locate(fr, P, *GRIND1, R=R)
    j = int(np.argmin(np.abs(fr - 3 * f0)))
    w = slice(max(0, j - 4), j + 5)
    k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
    f3, p3 = float(fr[k]), float(R[k])
    lo, hi = boot_prom_at(rs, 3 * f0 - 0.3, 3 * f0 + 0.3)
    gap = abs(3 * f0 - fg1)
    rows[b] = dict(f0=f0, f3=f3, prom3=p3, lo=lo, hi=hi, fgrind1=fg1, gap=gap, K=K)
    print(f"  {b:<10} {K:>4} {f0:>6.2f} {3 * f0:>6.2f} {p3:>10.2f} [{lo:>5.2f},{hi:>5.2f}] "
          f"{fg1:>8.2f} {gap:>14.2f}")
OUT["odd_harmonic_3xf0"] = rows

p3s = [v["prom3"] for v in rows.values()]
print(f"\n  🛑 CORPUS SPREAD at 3xf0: {min(p3s):.2f} .. {max(p3s):.2f}, median {np.median(p3s):.2f}.")
if "V74/r5d" in rows:
    v74 = rows["V74/r5d"]
    rank = sorted(p3s, reverse=True).index(v74["prom3"]) + 1
    print(f"  V74/r5d: prom(3xf0) = {v74['prom3']:.3f} [{v74['lo']:.2f},{v74['hi']:.2f}]  "
          f"-- rank {rank} of {len(p3s)} builds (1 = highest)")
    print(f"  V74's 3xf0 ({3 * v74['f0']:.2f} Hz) is {v74['gap']:.2f} Hz from its OWN grind-#1 "
          f"fundamental ({v74['fgrind1']:.2f} Hz) -- {'CLOSE, confound risk' if v74['gap'] < 1.0 else 'well separated, low confound risk for V74 specifically'}")

with open(ROOT / "_scratch/out/_r5d_3xf0_check.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_3xf0_check.json")
