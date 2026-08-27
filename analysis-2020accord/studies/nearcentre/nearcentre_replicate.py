#!/usr/bin/env python3
"""REPLICATION of the conditional that the corpus ACTUALLY supports, plus the power accounting.

`studies/nearcentre/nearcentre_final.py` ss1/ss2 found the operator's angle conditional does not survive, and that the
live conditional is a BAND-PASS IN MANOEUVRE RATE. A conditional that shows on one route is a route
artefact (kit rule), so this replicates the rate band on every arm that can carry it, and states
the exposure and the P(0) for every cell that cannot.

ss1  THE RATE BAND, PER ARM -- engaged creep, median e_18-22 by manoeuvre-rate bin.
ss2  ENGAGEMENT AT NEAR CENTRE -- the exposure behind the pooled 35x, arm by arm, with P(0).
ss3  UNDERPOWERED CELLS -- P(observe 0 windows | the arm had this cell at the pooled rate).

Usage: python studies/nearcentre/nearcentre_replicate.py [ep|blk] -> writes _scratch/out/_nearcentre_replicate.json
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

RE = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 64.0), (64.0, 1e9)]
RN = ["0-4", "4-16", "16-32", "32-64", "64+"]
store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["a_c"] = r["a_mean"] - c
        r["absa"] = abs(r["a_c"])
        r["rb"] = G.binof(r["rate_lp"], RE)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]

# ------------------------------------------------------------------ ss1 the rate band -------------
N.hdr("ss1  ★★★ THE RATE BAND-PASS, REPLICATED PER ARM -- engaged creep, median e_18-22")
print("  Manoeuvre rate = mean |lowpass(rate_c, 3 Hz)|, so the 21 Hz grind is not in its own axis.")
print("  `peak/floor` is the arm's own max bin over its own 0-4 bin -- a within-arm statistic that")
print("  needs no cross-route matching. A route artefact cannot produce it on 6 independent arms.\n")
print(f"  {'arm':<12} " + " ".join(f"{n:>16}" for n in RN) + f"{'peak/floor':>12}")
rep = {}
for k in ["POOLED"] + list(N.ARMS):
    rs = ARM[k]
    row, cells = [], []
    for i in range(len(RN)):
        c = [r for r in rs if r["rb"] == i]
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
    f0 = row[0]["med"]
    pk = max((d["med"] for d in row if np.isfinite(d["med"]) and not d["thin"]), default=np.nan)
    rep[k] = dict(bins=row, peak_over_floor=float(pk / f0) if f0 and np.isfinite(f0) else np.nan)
    print(f"  {k:<12} " + " ".join(cells)
          + (f"{pk / f0:>12.2f}" if f0 and np.isfinite(f0) and np.isfinite(pk)
             else f"{'--':>12}"))
print("\n  `~` = thin (< 8 windows or < 3 units). `peak/floor` uses only NON-thin bins.")
OUT["rate_band"] = rep

# ------------------------------------------------------------------ ss2 engagement at centre ------
N.hdr("ss2  ★★ ENGAGEMENT AT NEAR CENTRE -- the exposure behind the pooled effect")
print("  |a_c| < 5 deg, v < 20 km/h. Reported RAW (no stratification) so the exposure is legible,")
print("  and again inside the low-rate cell so 'openpilot moves the wheel and the driver doesn't'")
print("  cannot be the whole story.\n")
print(f"  {'arm':<12} {'nEng':>6} {'nMan':>6} {'medEng':>9} {'medMan':>8} {'raw ratio':>10} | "
      f"{'rate<4: nE':>11} {'nM':>5} {'medE':>8} {'medM':>8} {'ratio':>7}")
eg = {}
for k in ["POOLED"] + list(N.ARMS):
    names = N.LADDER if k == "POOLED" else N.ARMS[k]
    rs = [r for n in names for r in store[n] if r["v"] < N.CREEP and abs(r["a_c"]) < 5.0]
    A = [r for r in rs if r["eng"] == 1]
    B = [r for r in rs if r["eng"] == 0]
    lo = [r for r in rs if r["rate_lp"] < 4.0]
    A2 = [r for r in lo if r["eng"] == 1]
    B2 = [r for r in lo if r["eng"] == 0]

    def md(x):
        v = G.col(x, "e_18-22")
        v = v[np.isfinite(v)]
        return float(np.median(v)) if len(v) else np.nan
    eg[k] = dict(nE=len(A), nM=len(B), medE=md(A), medM=md(B),
                 nE_lo=len(A2), nM_lo=len(B2), medE_lo=md(A2), medM_lo=md(B2))
    rr = md(A) / md(B) if md(B) else np.nan
    r2 = md(A2) / md(B2) if md(B2) else np.nan
    print(f"  {k:<12} {len(A):>6} {len(B):>6} {md(A):>9.0f} {md(B):>8.1f} {rr:>10.1f} | "
          f"{len(A2):>11} {len(B2):>5} {md(A2):>8.0f} {md(B2):>8.1f} {r2:>7.1f}")
OUT["engagement"] = eg

# ------------------------------------------------------------------ ss3 P(0) for empty cells ------
N.hdr("ss3  🛑 THE EMPTY CELLS, PRICED -- P(observe 0) under the pooled occupancy rate")
print("  For each arm and the cell 'engaged creep, |a_c| < 5, manoeuvre rate >= 16 deg/s', the")
print("  pooled occupancy is q = (windows in cell) / (engaged-creep windows). Under a binomial with")
print("  that q, P(0 | n) = (1-q)^n is the chance the arm would show zero PURELY from exposure.")
print("  An arm with a large P(0) is EMPTY, not null -- it never had the chance to disagree.\n")
pool = ARM["POOLED"]
cellsel = lambda r: r["absa"] < 5.0 and r["rate_lp"] >= 16.0
q = sum(1 for r in pool if cellsel(r)) / len(pool)
print(f"  pooled occupancy q = {q:.4f}  ({sum(1 for r in pool if cellsel(r))} / {len(pool)})\n")
print(f"  {'arm':<12} {'n eng-creep':>12} {'observed in cell':>17} {'expected':>9} {'P(0 | n)':>10}")
p0 = {}
for k in list(N.ARMS):
    rs = ARM[k]
    obs = sum(1 for r in rs if cellsel(r))
    pz = float((1 - q) ** len(rs))
    p0[k] = dict(n=len(rs), obs=obs, exp=q * len(rs), p0=pz)
    print(f"  {k:<12} {len(rs):>12} {obs:>17} {q * len(rs):>9.1f} {pz:>10.4f}"
          + ("   <-- EMPTY BY EXPOSURE, NOT A NULL" if obs == 0 else ""))
OUT["p_zero"] = p0

(HERE.parent / "_scratch/out/_nearcentre_replicate.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_replicate.json'}")
