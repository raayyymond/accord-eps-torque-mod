#!/usr/bin/env python3
"""IS 5 DEGREES A REAL BOUNDARY, OR JUST WHERE I CUT?  Localisation + fragility of the thin cell.

The separation between the two modes -- grind #1 rises and the ratchet falls on crossing into
|mid| < 5 deg of the sensor zero, ratio of ratios 1.68 [1.14, 2.49] -- rests on **30 windows / 25
blocks pooled**, and `D3-microratchet` has confirmed route 59 contributes ZERO more (P(0 | n=16) =
0.372, empty not null). It is the thinnest cell in the battery and it is carrying a headline. Two
things therefore have to be checked before anyone builds on it, and neither has been:

  ss1  SLIDING THRESHOLD.  A single cut at 5 deg tests one hypothesis with the least data. Sweep the
       boundary t over 2-30 deg and read the ratio-of-ratios as a CURVE. If there is a real boundary
       the curve has a knee; if 5 deg was arbitrary, the curve is flat or monotone and the headline
       is a cherry-pick. This also uses every window instead of 30.
  ss2  SPAN FLOOR.  The 25 deg span floor is what starves the cell. The band-pass is elevated from
       8 deg upward (pooled 461 at span 8-25 vs 1092 at 25-75), so span 8-200 is a defensible
       widening that roughly doubles the 0-5 exposure. If the separation survives it, the headline
       is no longer hostage to 30 windows; if it dies, say so.
  ss3  JACKKNIFE.  Leave-one-arm-out and leave-one-block-out on the ratio of ratios. A result that
       one route or one 10 s block can move is not a result.

Estimator throughout: ratio of ratios computed INSIDE each bootstrap draw on the SAME resampled
episodes, so it is a within-window difference test (kit rule 5).

Usage: python studies/nearcentre/nearcentre_boundary.py [ep|blk] -> writes _scratch/out/_nearcentre_boundary.json
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

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260805)
NBOOT = 4000
OUT = {"epkey": G.EPKEY}
K69, K18 = "e_6-9", "e_18-22"

SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["amid"] = abs(0.5 * (r["a_max"] + r["a_min"]) - c)
        r["sb"] = G.binof(r["span"], SP)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ALL = [r for b in N.LADDER for r in ENGC[b]]


def rr(A, B, nboot=NBOOT):
    """(q, lo, hi, r69, r18) -- ratio of ratios, paired inside each draw."""
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        eb.setdefault(r[G.EPKEY], []).append(r)
    pa, pb = list(ea.values()), list(eb.values())
    if len(pa) < 2 or len(pb) < 2:
        return (np.nan,) * 5
    q = np.full(nboot, np.nan)
    for i in range(nboot):
        sa = [r for j in RNG.integers(0, len(pa), len(pa)) for r in pa[j]]
        sb = [r for j in RNG.integers(0, len(pb), len(pb)) for r in pb[j]]
        v = {}
        for k in (K69, K18):
            xa, xb = G.col(sa, k), G.col(sb, k)
            xa, xb = xa[np.isfinite(xa)], xb[np.isfinite(xb)]
            if len(xa) and len(xb) and np.median(xb) > 0:
                v[k] = np.median(xa) / np.median(xb)
        if len(v) == 2 and v[K69] > 0:
            q[i] = v[K18] / v[K69]
    pt = {}
    for k in (K69, K18):
        xa, xb = G.col(A, k), G.col(B, k)
        xa, xb = xa[np.isfinite(xa)], xb[np.isfinite(xb)]
        pt[k] = float(np.median(xa) / np.median(xb)) if len(xa) and len(xb) else np.nan
    return (float(pt[K18] / pt[K69]) if pt[K69] else np.nan,
            float(np.nanpercentile(q, 2.5)), float(np.nanpercentile(q, 97.5)),
            pt[K69], pt[K18])


# ------------------------------------------------------------------ ss1/ss2 sliding threshold ----
N.hdr("ss1+ss2  ★★★ THE BOUNDARY, SWEPT -- is 5 deg a knee, or the cut that happened to be taken?")
print("  For each threshold t: A = |mid| < t, B = t <= |mid| < 45 (both inside the span window).")
print("  The OUTER edge is held at 45 deg throughout so the comparison arm does not drift into the")
print("  regime where BOTH modes collapse -- that shared collapse is not the thing under test.\n")
sw = {}
for slab, ss in (("span 25-200 (headline)", (3, 4)), ("span 8-200 (widened)", (2, 3, 4)),
                 ("span 8-75", (2, 3))):
    base = [r for r in ALL if r["sb"] in ss]
    print(f"  --- {slab}   n = {len(base)}")
    print(f"      {'t (deg)':>8} {'nA':>5} {'nB':>5} {'uA':>4} {'uB':>4} | {'6-9 A/B':>18} "
          f"{'18-22 A/B':>18} | {'RATIO OF RATIOS':>21}")
    for t in (2, 3, 4, 5, 7, 10, 15, 20, 30):
        A = [r for r in base if r["amid"] < t]
        B = [r for r in base if t <= r["amid"] < 45.0]
        uA, uB = len({r[G.EPKEY] for r in A}), len({r[G.EPKEY] for r in B})
        if len(A) < 5 or len(B) < 5 or uA < 3 or uB < 3:
            print(f"      {t:>8} {len(A):>5} {len(B):>5} {uA:>4} {uB:>4} | *** thin")
            sw[f"{slab}|{t}"] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB, thin=True)
            continue
        q, lo, hi, r69, r18 = rr(A, B)
        sw[f"{slab}|{t}"] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB, q=q, lo=lo, hi=hi,
                                 r69=r69, r18=r18)
        mark = "  ★" if np.isfinite(lo) and lo > 1.0 else ""
        print(f"      {t:>8} {len(A):>5} {len(B):>5} {uA:>4} {uB:>4} | {r69:>18.3f} "
              f"{r18:>18.3f} | {q:>7.2f} [{lo:>5.2f},{hi:>6.2f}]{mark}")
    print()
OUT["sweep"] = sw

# ------------------------------------------------------------------ ss1b the two bands' curves ---
N.hdr("ss1b  THE TWO BANDS SEPARATELY, on a fine |mid| grid -- where each mode's maximum sits")
print("  span 8-200 deg (the widened window, for exposure), engaged creep, median p-p counts.\n")
EDG = [0, 3, 6, 10, 15, 22, 32, 45, 65, 95, 140, 1e9]
NAMES = [f"{EDG[i]:.0f}-{EDG[i + 1]:.0f}" if EDG[i + 1] < 1e8 else f"{EDG[i]:.0f}+"
         for i in range(len(EDG) - 1)]
base = [r for r in ALL if r["sb"] in (2, 3, 4)]
prof = {}
print(f"  {'band':<18} " + " ".join(f"{n:>11}" for n in NAMES))
for key, blab in ((K69, "6-9 ratchet"), (K18, "18-22 grind #1")):
    cells = []
    for i in range(len(NAMES)):
        c = [r for r in base if EDG[i] <= r["amid"] < EDG[i + 1]]
        v = 2 * G.col(c, key)
        v = v[np.isfinite(v)]
        prof[f"{key}|{NAMES[i]}"] = dict(n=len(c), med=float(np.median(v)) if len(v) else np.nan)
        cells.append(f"{'--':>11}" if not len(v) else f"{np.median(v):>11.0f}")
    print(f"  {blab:<18} " + " ".join(cells))
print(f"  {'n windows':<18} " + " ".join(
    f"{sum(1 for r in base if EDG[i] <= r['amid'] < EDG[i + 1]):>11}"
    for i in range(len(NAMES))))
print(f"  {'blocks':<18} " + " ".join(
    f"{len({r[G.EPKEY] for r in base if EDG[i] <= r['amid'] < EDG[i + 1]}):>11}"
    for i in range(len(NAMES))))
print(f"  {'ratio 18-22/6-9':<18} " + " ".join(
    f"{prof[f'{K18}|{n}']['med'] / prof[f'{K69}|{n}']['med']:>11.2f}"
    if np.isfinite(prof[f"{K18}|{n}"]["med"]) and prof[f"{K69}|{n}"]["med"] > 0 else f"{'--':>11}"
    for n in NAMES))
OUT["profile"] = prof

# ------------------------------------------------------------------ ss3 jackknife ----------------
N.hdr("ss3  ★★ FRAGILITY -- leave-one-arm-out and leave-one-block-out on the headline")
print("  Headline = ratio of ratios at t = 5 deg, span 25-200. If one route or one ~10 s block")
print("  moves it materially, it is not a result.\n")
for slab, ss, t in (("span 25-200, t=5", (3, 4), 5.0), ("span 8-200, t=5", (2, 3, 4), 5.0)):
    base = [r for r in ALL if r["sb"] in ss]
    A0 = [r for r in base if r["amid"] < t]
    B0 = [r for r in base if t <= r["amid"] < 45.0]
    q0 = rr(A0, B0, nboot=1500)
    print(f"  --- {slab}   full sample q = {q0[0]:.2f} [{q0[1]:.2f}, {q0[2]:.2f}]  "
          f"(nA={len(A0)}, nB={len(B0)})")
    print(f"      {'left out':<16} {'nA':>4} {'nB':>4} {'q':>7} {'[95% CI]':>16}")
    jk = {}
    for k, names in N.ARMS.items():
        keep = set(names)
        A = [r for r in A0 if r["build"] not in keep]
        B = [r for r in B0 if r["build"] not in keep]
        if len(A) < 5 or len(B) < 5:
            print(f"      {'-' + k:<16} {len(A):>4} {len(B):>4}   *** collapses the cell")
            jk[k] = dict(nA=len(A), nB=len(B), collapses=True)
            continue
        q, lo, hi, _, _ = rr(A, B, nboot=1500)
        jk[k] = dict(nA=len(A), nB=len(B), q=q, lo=lo, hi=hi)
        print(f"      {'-' + k:<16} {len(A):>4} {len(B):>4} {q:>7.2f} [{lo:>6.2f},{hi:>7.2f}]")
    # leave-one-block-out over the A side, which is the thin one
    blocks = sorted({r[G.EPKEY] for r in A0}, key=str)
    qs = []
    for bk in blocks:
        A = [r for r in A0 if r[G.EPKEY] != bk]
        if len(A) < 5:
            continue
        q = rr(A, B0, nboot=400)[0]
        if np.isfinite(q):
            qs.append(q)
    if qs:
        qs = np.array(qs)
        print(f"      leave-one-block-out over the {len(blocks)} A-side blocks: "
              f"q ranges {qs.min():.2f} - {qs.max():.2f} (full {q0[0]:.2f}), "
              f"{int((qs > 1).sum())}/{len(qs)} stay above 1")
        jk["__loo__"] = dict(nblocks=len(blocks), qmin=float(qs.min()), qmax=float(qs.max()),
                             above1=int((qs > 1).sum()), n=len(qs))
    OUT[f"jackknife|{slab}"] = jk
    print()

(HERE.parent / "_scratch/out/_nearcentre_boundary.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_boundary.json'}")
