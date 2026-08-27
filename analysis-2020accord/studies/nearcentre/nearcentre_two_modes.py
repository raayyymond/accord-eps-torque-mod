#!/usr/bin/env python3
"""DOES THE NEAR-ZERO PREFERENCE SEPARATE THE RATCHET FROM GRIND #1?  Corpus replication of D3.

`D3-microratchet` measured, on route 59 alone (span 25-75 deg, n = 27/31/15 windows by |mid| bin):
      |mid|        0-15    15-60    60+
      6-9 Hz       2552    4695    3127     -> PEAKS OFF ZERO
      18-22 Hz     2557    2451    1122     -> DECLINES MONOTONICALLY FROM ZERO
and separately showed that the MOVEMENT band-pass I found for grind #1 is SHARED by the ratchet
(both peak in span 25-75 deg, collapse 7.8x vs 6.1x). That retires `span` as a discriminator -- it
is a shared EXCITATION condition -- and promotes `|mid|` to the only conditional in the battery on
which the two modes behave differently.

🛑 THAT CLAIM RESTS ON 73 WINDOWS OF ONE ROUTE. This file re-runs exactly it on all 14 routes with
the identical instrument, per arm, so it can be confirmed, refuted, or called underpowered. If it
holds, the two modes have different loop closures and the angle-domain lever is grind-#1-specific.

★ THE DECISION STATISTIC is the RATIO OF RATIOS -- (near/far in 18-22) / (near/far in 6-9) -- taken
per bootstrap draw so its CI is honest. A ratio of two separately-quoted marginals is not a
difference test (kit rule 5), and that error has already been published and retracted here once.

Usage: python studies/nearcentre/nearcentre_two_modes.py [ep|blk] -> writes _scratch/out/_nearcentre_two_modes.json
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

SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
MD3 = [(0.0, 15.0), (15.0, 60.0), (60.0, 1e9)]          # D3's bins, so the numbers line up
MD3N = ["0-15", "15-60", "60+"]
MD5 = [(0.0, 5.0), (5.0, 15.0), (15.0, 45.0), (45.0, 120.0), (120.0, 1e9)]
MD5N = ["0-5", "5-15", "15-45", "45-120", "120+"]

store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["amid"] = abs(0.5 * (r["a_max"] + r["a_min"]) - c)
        r["sb"] = G.binof(r["span"], SP)
        r["m3"] = G.binof(r["amid"], MD3)
        r["m5"] = G.binof(r["amid"], MD5)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
ORDER = ["POOLED", "V72/r59", "stock pool", "V62+V65", "V69/r4f", "V71B/r54", "V71C/r58",
         "V61 (kill)", "V67+V68", "V70/r50"]
# p-p, so the numbers are directly comparable to D3's (they quote peak-to-peak).
BANDS = [("e_6-9", "6-9 Hz ratchet"), ("e_18-22", "18-22 Hz grind #1")]


def eps_of(rs, key):
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    out = [G.col(v, key) for v in ep.values()]
    out = [x[np.isfinite(x)] for x in out]
    return [x for x in out if len(x)]


# ------------------------------------------------------------------ ss1 the two ladders ----------
N.hdr("ss1  ★★★ THE |mid| LADDER FOR BOTH MODES, at matched movement (span 25-75 deg)")
print("  Engaged creep. Values are median PEAK-TO-PEAK counts (2 x the p99 envelope amplitude),")
print("  the same units D3 quotes. D3's route-59 row is reproduced here from the same cache.\n")
lad = {}
for slab, ss in (("span 25-75", [3]), ("span 25-200", [3, 4])):
    print(f"  --- {slab} deg p-p per 2.56 s")
    print(f"      {'arm':<12} {'band':<20} " + " ".join(f"{n:>16}" for n in MD3N))
    for k in ORDER:
        rs = [r for r in ARM.get(k, []) if r["sb"] in ss]
        if len(rs) < 10:
            print(f"      {k:<12} {'(both)':<20} *** n={len(rs)} UNDERPOWERED")
            continue
        for key, blab in BANDS:
            cells = []
            for i in range(3):
                c = [r for r in rs if r["m3"] == i]
                v = 2 * G.col(c, key)
                v = v[np.isfinite(v)]
                nb = len({r[G.EPKEY] for r in c})
                lad[f"{slab}|{k}|{key}|{MD3N[i]}"] = dict(
                    n=len(c), nb=nb, med=float(np.median(v)) if len(v) else np.nan)
                cells.append(f"{'--':>16}" if not len(v)
                             else (f"{np.median(v):>7.0f}~n{len(c):<3}" if len(c) < 6 or nb < 3
                                   else f"{np.median(v):>8.0f}n{len(c):<3}").rjust(16))
            print(f"      {k:<12} {blab:<20} " + " ".join(cells))
        print()
OUT["ladders"] = lad

# ------------------------------------------------------------------ ss2 ratio of ratios ----------
N.hdr("ss2  ★★★ THE DECISION STATISTIC -- (near/far in 18-22) / (near/far in 6-9), paired per draw")
print("  near = |mid| < 15 deg, far = |mid| >= 60 deg, both inside span 25-200 deg.")
print("  Each bootstrap draw resamples the SAME episodes for both bands, so the ratio of ratios is")
print("  a genuine WITHIN-WINDOW difference test and not a comparison of two marginals.")
print("  > 1 means the near-zero preference is STRONGER for grind #1 than for the ratchet.\n")
print(f"  {'arm':<12} {'nNear/nFar':>12} {'units':>7} | {'6-9 near/far':>19} | "
      f"{'18-22 near/far':>19} | {'ratio of ratios':>21}")
rr = {}
for k in ORDER:
    rs = [r for r in ARM.get(k, []) if r["sb"] in (3, 4)]
    A = [r for r in rs if r["amid"] < 15.0]
    B = [r for r in rs if r["amid"] >= 60.0]
    uA, uB = len({r[G.EPKEY] for r in A}), len({r[G.EPKEY] for r in B})
    if len(A) < 5 or len(B) < 5 or uA < 2 or uB < 2:
        print(f"  {k:<12} {str(len(A)) + '/' + str(len(B)):>12} {str(uA) + '/' + str(uB):>7} "
              f"| *** EMPTY / UNDERPOWERED")
        rr[k] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB, underpowered=True)
        continue
    epA = {}
    epB = {}
    for r in A:
        epA.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        epB.setdefault(r[G.EPKEY], []).append(r)
    pa, pb = list(epA.values()), list(epB.values())
    d = {key: np.full(NBOOT, np.nan) for key, _ in BANDS}
    dq = np.full(NBOOT, np.nan)
    for i in range(NBOOT):
        ia = RNG.integers(0, len(pa), len(pa))
        ib = RNG.integers(0, len(pb), len(pb))
        sa = [r for j in ia for r in pa[j]]
        sb = [r for j in ib for r in pb[j]]
        vals = {}
        for key, _ in BANDS:
            va, vb = G.col(sa, key), G.col(sb, key)
            va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
            if len(va) and len(vb) and np.median(vb) > 0:
                vals[key] = float(np.median(va) / np.median(vb))
                d[key][i] = vals[key]
        if len(vals) == 2 and vals["e_6-9"] > 0:
            dq[i] = vals["e_18-22"] / vals["e_6-9"]
    pts = {}
    for key, _ in BANDS:
        va, vb = G.col(A, key), G.col(B, key)
        pts[key] = float(np.median(va[np.isfinite(va)]) / np.median(vb[np.isfinite(vb)]))
    q = pts["e_18-22"] / pts["e_6-9"]
    rr[k] = dict(nA=len(A), nB=len(B), uA=uA, uB=uB,
                 r69=pts["e_6-9"], r69lo=float(np.nanpercentile(d["e_6-9"], 2.5)),
                 r69hi=float(np.nanpercentile(d["e_6-9"], 97.5)),
                 r18=pts["e_18-22"], r18lo=float(np.nanpercentile(d["e_18-22"], 2.5)),
                 r18hi=float(np.nanpercentile(d["e_18-22"], 97.5)),
                 q=float(q), qlo=float(np.nanpercentile(dq, 2.5)),
                 qhi=float(np.nanpercentile(dq, 97.5)))
    e = rr[k]
    flag = ""
    if np.isfinite(e["qlo"]) and e["qlo"] > 1.0:
        flag = "  ★ SEPARATES"
    elif np.isfinite(e["qhi"]) and e["qlo"] <= 1.0 <= e["qhi"]:
        flag = "  (CI spans 1)"
    print(f"  {k:<12} {str(len(A)) + '/' + str(len(B)):>12} {str(uA) + '/' + str(uB):>7} | "
          f"{e['r69']:>6.2f} [{e['r69lo']:>5.2f},{e['r69hi']:>5.2f}] | "
          f"{e['r18']:>6.2f} [{e['r18lo']:>5.2f},{e['r18hi']:>5.2f}] | "
          f"{e['q']:>6.2f} [{e['qlo']:>5.2f},{e['qhi']:>6.2f}]{flag}")
OUT["ratio_of_ratios"] = rr

# ------------------------------------------------------------------ ss3 prominence -----------------
N.hdr("ss3  THE SAME TEST ON PROMINENCE -- a broadband lift cannot move a peak/local-floor ratio")
print("  If both ladders are really one broadband envelope moving together, prominence kills both.\n")
print(f"  {'arm':<12} {'band':<20} " + " ".join(f"{n:>15}" for n in MD3N))
pro = {}
for k in ORDER:
    rs = [r for r in ARM.get(k, []) if r["sb"] in (3, 4)]
    if len(rs) < 10:
        continue
    for key, blab in (("p_6-9", "6-9 Hz ratchet"), ("p_18-22", "18-22 Hz grind #1")):
        cells = []
        for i in range(3):
            c = [r for r in rs if r["m3"] == i]
            v = G.col(c, key)
            v = v[np.isfinite(v)]
            pro[f"{k}|{key}|{MD3N[i]}"] = dict(n=len(c),
                                               med=float(np.median(v)) if len(v) else np.nan)
            cells.append(f"{'--':>15}" if not len(v)
                         else f"{np.median(v):>8.1f}(n{len(c)})".rjust(15))
        print(f"  {k:<12} {blab:<20} " + " ".join(cells))
    print()
OUT["prominence"] = pro

# ------------------------------------------------------------------ ss4 fine |mid| ---------------
N.hdr("ss4  THE FINE |mid| LADDER, pooled -- where exactly does each mode live on the angle axis?")
print("  span 25-200 deg, engaged creep, median p-p counts. `frac` is that bin's share of exposure.\n")
rs = [r for r in ARM["POOLED"] if r["sb"] in (3, 4)]
print(f"  {'band':<20} " + " ".join(f"{n:>15}" for n in MD5N))
fine = {}
for key, blab in BANDS:
    cells = []
    for i in range(5):
        c = [r for r in rs if r["m5"] == i]
        v = 2 * G.col(c, key)
        v = v[np.isfinite(v)]
        fine[f"{key}|{MD5N[i]}"] = dict(n=len(c), med=float(np.median(v)) if len(v) else np.nan)
        cells.append(f"{'--':>15}" if not len(v)
                     else f"{np.median(v):>8.0f}(n{len(c)})".rjust(15))
    print(f"  {blab:<20} " + " ".join(cells))
print(f"  {'exposure share':<20} " + " ".join(
    f"{100 * sum(1 for r in rs if r['m5'] == i) / len(rs):>14.1f}%" for i in range(5)))
OUT["fine"] = fine

(HERE.parent / "_scratch/out/_nearcentre_two_modes.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_two_modes.json'}")
