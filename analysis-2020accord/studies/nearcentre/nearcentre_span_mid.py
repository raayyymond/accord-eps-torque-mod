#!/usr/bin/env python3
"""THE SEPARABLE DECOMPOSITION -- excursion SIZE vs excursion POSITION on the angle axis.

🛑🛑 WHY THE OBVIOUS TEST CANNOT WORK. Measured on the corpus: for a 2.56 s window whose angle
never leaves +/-A deg of the sensor zero, mean |rate| is bounded by ~2A/2.56 = 0.78*A deg/s, and the
observed p95 per bin tracks that bound almost exactly (A=5 -> 3.9 measured vs 3.9 bound; A=15 ->
9.6 vs 11.7; A=45 -> 34.6 vs 35.1; A=100 -> 65.3 vs 78.0). So "the wheel is near centre" and "the
manoeuvre rate is low" are THE SAME MEASUREMENT at this window length, up to a factor of 0.78, and
no amount of stratification can separate them -- `studies/nearcentre/nearcentre_strict.py` ss3 returns 0 shared cells
for exactly this reason, which is arithmetic, not sparsity.

★ THE DECOMPOSITION THAT IS SEPARABLE. Split the window's angle trace into two genuinely
independent numbers:

    span = a_max - a_min                 how much the wheel MOVED   (this is the rate, x 2.56 s)
    mid  = (a_max + a_min)/2 - c         WHERE on the angle axis it moved  (this is the position)

`span` carries the rate; `mid` carries the operator's "near centre". They are geometrically
orthogonal -- a 3 deg wiggle can sit at 0 deg or at 90 deg, and a 200 deg sweep can be centred on
either. So THIS is the operator's conditional, asked in the only form the data can answer:

    AT MATCHED EXCURSION SIZE, DOES IT MATTER WHERE ON THE ANGLE AXIS THE WHEEL IS?

Usage: python studies/nearcentre/nearcentre_span_mid.py [ep|blk] -> writes _scratch/out/_nearcentre_span_mid.json
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
RNG = np.random.default_rng(20260804)
NBOOT = 2000
OUT = {"epkey": G.EPKEY}

SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
SPN = ["0-2", "2-8", "8-25", "25-75", "75-200", "200+"]
MD = [(0.0, 5.0), (5.0, 15.0), (15.0, 45.0), (45.0, 120.0), (120.0, 1e9)]
MDN = ["0-5", "5-15", "15-45", "45-120", "120+"]

store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["mid"] = 0.5 * (r["a_max"] + r["a_min"]) - c
        r["amid"] = abs(r["mid"])
        r["sb"] = G.binof(r["span"], SP)
        r["mb"] = G.binof(r["amid"], MD)
        r["exc"] = (r["e_18-22"] / r["e_24-28"]) if r["e_24-28"] > 0 else np.nan
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
POOL = ARM["POOLED"]

# ------------------------------------------------------------------ ss0 orthogonality -------------
N.hdr("ss0  ARE `span` AND `mid` ACTUALLY SEPARABLE? -- the joint occupancy, engaged creep")
print("  Every cell with real exposure is a case the data can speak to. Compare with")
print("  `studies/nearcentre/nearcentre_strict.py` ss3, where amax x rate had ZERO jointly-occupied cells.\n")
print(f"      {'|mid| \\ span':<12} " + " ".join(f"{n:>9}" for n in SPN) + f"{'ROW':>9}")
for i, mn in enumerate(MDN):
    row = [sum(1 for r in POOL if r["mb"] == i and r["sb"] == j) for j in range(len(SPN))]
    print(f"      {mn:<12} " + " ".join(f"{x:>9}" for x in row)
          + f"{sum(1 for r in POOL if r['mb'] == i):>9}")
print(f"      {'COL':<12} " + " ".join(
    f"{sum(1 for r in POOL if r['sb'] == j):>9}" for j in range(len(SPN))))
sp = G.col(POOL, "span")
md = G.col(POOL, "amid")
print(f"\n      Spearman(span, |mid|) over all 932 windows = "
      f"{np.corrcoef(np.argsort(np.argsort(sp)), np.argsort(np.argsort(md)))[0, 1]:.3f}")

# ------------------------------------------------------------------ ss1 the 2-way ----------------
N.hdr("ss1  ★★★ THE SEPARABLE 2-WAY TABLE -- median e_18-22, pooled engaged creep")
print("  READ ACROSS a row: does grind #1 grow with how much the wheel MOVED?")
print("  READ DOWN a column: at a FIXED amount of movement, does WHERE it happened matter?")
print("  The operator's conditional predicts the TOP of each column is the largest.\n")
tw = {}
for met, fmt in (("e_18-22", "{:>8.0f}"), ("p_18-22", "{:>8.1f}"), ("e18_ang", "{:>8.3f}")):
    print(f"  --- {met}")
    print(f"      {'|mid| \\ span':<12} " + " ".join(f"{n:>14}" for n in SPN) + f"{'ROW ALL':>14}")
    for i, mn in enumerate(MDN):
        cells = []
        for j in range(len(SPN)):
            c = [r for r in POOL if r["mb"] == i and r["sb"] == j]
            v = G.col(c, met)
            v = v[np.isfinite(v)]
            tw[f"{met}|{mn}|{SPN[j]}"] = dict(n=len(c),
                                              med=float(np.median(v)) if len(v) else np.nan)
            cells.append(f"{'--':>14}" if not len(v)
                         else (fmt.format(np.median(v)) + f"(n{len(c)})").rjust(14))
        ra = [r for r in POOL if r["mb"] == i]
        va = G.col(ra, met)
        va = va[np.isfinite(va)]
        cells.append((fmt.format(np.median(va)) + f"(n{len(ra)})").rjust(14)
                     if len(va) else f"{'--':>14}")
        print(f"      {mn:<12} " + " ".join(cells))
    cells = []
    for j in range(len(SPN)):
        c = [r for r in POOL if r["sb"] == j]
        v = G.col(c, met)
        v = v[np.isfinite(v)]
        cells.append((fmt.format(np.median(v)) + f"(n{len(c)})").rjust(14)
                     if len(v) else f"{'--':>14}")
    print(f"      {'COL ALL':<12} " + " ".join(cells) + "\n")
OUT["two_way"] = tw

# ------------------------------------------------------------------ ss2 the contrast --------------
N.hdr("ss2  ★★★ THE OPERATOR'S CONDITIONAL, ASKED SEPARABLY -- |mid| < 15 vs |mid| >= 45")
print("  Stratified on (SPAN bin, v bin, eff bin). The span bin holds the amount of wheel movement")
print("  fixed, so this is 'the same wiggle, near the sensor zero vs far from it'.")
print("  ratio > 1 = MORE grind #1 near centre, which is the operator's report.\n")
print(f"      {'arm':<12} {'nA':>5} {'nB':>5} {'medA':>8} {'medB':>8} {'ratio':>7} "
      f"{'[95% CI]':>17} {'24-28':>7} {'excess':>7} {'cells':>5} {'own null':<14} p")
CELL = lambda r: (r["sb"], r["cell"][1], r["cell"][2])
ct = {}
for k in ["POOLED"] + list(N.ARMS):
    z = N.recell(ARM[k], CELL)
    A = [r for r in z if r["amid"] < 15.0]
    B = [r for r in z if r["amid"] >= 45.0]
    if len(A) < 6 or len(B) < 6:
        print(f"      {k:<12} {len(A):>5} {len(B):>5}  *** UNDERPOWERED")
        ct[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    r18 = G.boot_cellwise(A, B, "e_18-22", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    r24 = G.boot_cellwise(A, B, "e_24-28", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    nl = G.split_half_null(z, "e_18-22", RNG, nrep=200, min_ep=2, min_win=4)
    _, p = G.perm_p(A, B, "e_18-22", RNG, nperm=1500, min_ep=2, min_win=4)
    exc = r18[0] / r24[0] if np.isfinite(r24[0]) and r24[0] > 0 else np.nan
    ins = np.isfinite(nl[1]) and np.isfinite(r18[0]) and nl[1] <= r18[0] <= nl[2]
    ct[k] = dict(nA=len(A), nB=len(B), ratio=float(r18[0]), lo=float(r18[1]), hi=float(r18[2]),
                 ncells=int(r18[3]), r2428=float(r24[0]), excess=float(exc),
                 null=[float(x) for x in nl], inside=bool(ins), p=float(p),
                 medA=float(np.median(G.col(A, "e_18-22"))),
                 medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {k:<12} {len(A):>5} {len(B):>5} {np.median(G.col(A, 'e_18-22')):>8.0f} "
          f"{np.median(G.col(B, 'e_18-22')):>8.0f} {r18[0]:>7.3f} "
          f"[{r18[1]:>7.3f},{r18[2]:>8.3f}] {r24[0]:>7.3f} {exc:>7.3f} {r18[3]:>5} "
          f"[{nl[1]:.2f},{nl[2]:.2f}]".ljust(0) + f"  {'INSIDE' if ins else '*OUT*':<7}{p:.4f}")
OUT["contrast"] = ct

# ------------------------------------------------------------------ ss3 the span ladder -----------
N.hdr("ss3  ★★★ THE SPAN LADDER, PER ARM -- the conditional the corpus DOES support")
print("  `span` = the window's peak-to-peak steering excursion in deg. At 2.56 s this is the")
print("  manoeuvre rate in disguise (rate ~ span / 2.56), but it is the form the operator can")
print("  actually observe: how far the wheel moves inside about two and a half seconds.\n")
print(f"  {'arm':<12} " + " ".join(f"{n:>16}" for n in SPN) + f"{'peak/floor':>11}")
sl = {}
for k in ["POOLED"] + list(N.ARMS):
    row, cells = [], []
    for j in range(len(SPN)):
        c = [r for r in ARM[k] if r["sb"] == j]
        nb = len({r[G.EPKEY] for r in c})
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        if len(c) >= 8 and nb >= 3:
            m, lo, hi = G.boot_median_ci(c, "e_18-22", RNG, nboot=NBOOT)
            row.append(dict(n=len(c), nb=nb, med=float(m), lo=float(lo), hi=float(hi), thin=False))
            cells.append(f"{m:>7.0f}n{len(c):<3}".rjust(16))
        else:
            m = float(np.median(v)) if len(v) else np.nan
            row.append(dict(n=len(c), nb=nb, med=m, thin=True))
            cells.append(f"{'EMPTY':>16}" if not len(v) else f"{m:>6.0f}~n{len(c):<3}".rjust(16))
    ok = [d["med"] for d in row if not d["thin"] and np.isfinite(d["med"])]
    pf = max(ok) / min(ok) if len(ok) >= 2 and min(ok) > 0 else np.nan
    sl[k] = dict(bins=row, peak_over_floor=float(pf))
    print(f"  {k:<12} " + " ".join(cells)
          + (f"{pf:>11.2f}" if np.isfinite(pf) else f"{'--':>11}"))
OUT["span_ladder"] = sl

(HERE.parent / "_scratch/out/_nearcentre_span_mid.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_span_mid.json'}")
