#!/usr/bin/env python3
"""Route `5d` -- two loose ends that decide how the headline is worded.

1. THE CREEP-RESTRICTED STRATIFIED COMPARISON. `studies/sessions/r5d/r5d_bands.py` section 3 stratifies over ALL speeds,
   and section 4's raw creep medians disagree with `studies/sessions/r5d/r5d_duty.py`'s grind-active creep numbers
   (V74 832 vs V73 188 raw; V74 739 vs V73 650 grind-active). Both can be true -- they are different
   exposures -- but the operator's complaint is a CREEP complaint, so the stratified estimator has
   to be run inside creep, where it is the only form that controls the exposure difference.

2. THE MDE OF THE BURST METRICS. `studies/sessions/r5d/r5d_ratchet.py` reported duty/duration ratios with CIs but no MDE,
   so "0.797 [0.54, 1.05]" cannot yet be read as "underpowered" or as "a real absence". Derive it
   from each ratio's own bootstrap spread: MDE = exp(2.80 x sd_log).

Usage:  python studies/sessions/r5d/r5d_creep_close.py   ->  writes _scratch/out/_r5d_creep_close.json
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r5d_lib as L  # noqa: E402  -- registers V73/r5a and V74/r5d into `_grind2_lib.BUILDS`
import d6_events as D  # noqa: E402

L.install_fs()
from d6b_events_fixed import bursts  # noqa: E402

G.EPKEY = "blk"
RNG = np.random.default_rng(9091)
OUT = {}
D.PARKED["V74/r5d"] = [2, 3, 9]

with open(ROOT / "_scratch/data/_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)

# ================================================== 1. creep-restricted stratified ================
N.hdr("1. STRATIFIED V74 vs PREDECESSORS, RESTRICTED TO CREEP -- the operator's own regime")
print("  Cells are re-declared inside creep as (speed x rate x effort), since `_grind2_lib`'s cell")
print("  puts every creep window in one or two speed bins and the stratification would be vacuous.")
print("  🛑 Ratios are quoted against V74's own split-half null computed with the SAME cells.\n")
VB = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.556)]
RB = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 1e9)]
EB = [(0.0, 200.0), (200.0, 800.0), (800.0, 1e9)]


def creep(b):
    o = [dict(r) for r in store[b] if r["eng"] == 1 and r["v"] < 5.556]
    for r in o:
        r["cell"] = (G.binof(r["v"], VB), G.binof(r["rate_lp"], RB), G.binof(r["eff"], EB))
    return o


V74 = creep("V74/r5d")
print(f"  V74 engaged creep: {len(V74)} windows, {len({r['blk'] for r in V74})} blocks, "
      f"{len({r['cell'] for r in V74})} occupied cells")
for key, kl in (("e_6-9", "MICRO RATCHET 6-9"), ("e_18-22", "GRIND #1 18-22"),
                ("e_24-28", "CONTROL 24-28")):
    _, nlo, nhi = G.split_half_null(V74, key, RNG, nrep=250, min_ep=2, min_win=4)
    print(f"\n  --- {kl} ---  V74 split-half null [{nlo:.3f}, {nhi:.3f}]")
    for b in ("V73/r5a", "V72/r59", "V71C/r58", "V67/r47", "V62/r37", "V59/r2c"):
        o = creep(b)
        if len(o) < 12:
            print(f"      vs {b:<10} UNPOWERED (n={len(o)})")
            continue
        pt, lo, hi, nc, na, nb, tab, draws = G.boot_cellwise(V74, o, key, RNG, nboot=1200,
                                                             min_ep=2, min_win=4)
        if not np.isfinite(pt):
            print(f"      vs {b:<10} no shared cell")
            continue
        sd = float(np.nanstd(draws))
        m = float(max(np.exp(2.80 * sd), nhi, 1 / max(nlo, 1e-9)))
        vd = ("WORSE" if lo > nhi else "BETTER" if hi < nlo else
              ("null (underpowered)" if max(pt, 1 / pt) < m else "flat"))
        print(f"      vs {b:<10} {pt:6.3f} [{lo:6.3f}, {hi:6.3f}]  MDE {m:5.2f}  "
              f"{nc:2d} cells  {vd}")
        OUT.setdefault("creep_stratified", {})[f"{key}|{b}"] = dict(
            ratio=pt, lo=lo, hi=hi, mde=m, cells=nc, verdict=vd, null=[nlo, nhi])

# ================================================== 2. MDE of the burst metrics ==================
N.hdr("2. MDE OF THE BURST METRICS -- so a CI containing 1 can be read correctly")
print("  MDE = exp(2.80 x sd_log) of each ratio's own run-bootstrap. A point estimate closer to 1")
print("  than the MDE is UNDERPOWERED; one further from 1 than the MDE and still spanning 1 would")
print("  be a genuine flat.\n")


def load_runs(b, vhi=12.5):
    out = []
    for _, s, a, bb, d, fs in D.runs(b, 0.0, vhi, True, 512):
        out.append(dict(run=(b, s, a), x=np.asarray(d["tq"][a:bb], float), fs=fs))
    return out


def metrics(rs):
    duty, dur, env = {}, {}, {}
    for r in rs:
        e = np.abs(D.analytic(D.bp(r["x"], r["fs"], *D.RATCHET)))
        bs = bursts(e, r["fs"])
        duty.setdefault(r["run"], []).append(sum(j - i for i, j, _ in bs) / max(len(e), 1))
        env.setdefault(r["run"], []).append(float(np.percentile(e, 99)))
        for i, j, _ in bs:
            dur.setdefault(r["run"], []).append((j - i) / r["fs"])
    return duty, dur, env


M = {b: metrics(load_runs(b)) for b in ("V74/r5d", "V73/r5a", "V72/r59", "V59/r2c", "V58/r2b")}


def rr(pa, pb, nb=4000):
    ka, kb = list(pa), list(pb)
    if len(ka) < 2 or len(kb) < 2:
        return (np.nan,) * 4
    dr = np.full(nb, np.nan)
    for i in range(nb):
        x = np.median(np.concatenate([pa[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
        y = np.median(np.concatenate([pb[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
        dr[i] = x / y if y else np.nan
    obs = (np.median(np.concatenate([pa[k] for k in ka])) /
           np.median(np.concatenate([pb[k] for k in kb])))
    sd = float(np.nanstd(np.log(dr[np.isfinite(dr) & (dr > 0)])))
    return float(obs), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), \
        float(np.exp(2.80 * sd))


print(f"  {'metric':<14} {'vs build':<10} {'ratio':>7} {'95% CI':>18} {'MDE':>6}   reading")
for mi, ml in ((0, "burst duty"), (1, "burst dur"), (2, "6-9 env p99")):
    for b in ("V73/r5a", "V72/r59", "V59/r2c", "V58/r2b"):
        pt, lo, hi, m = rr(M["V74/r5d"][mi], M[b][mi])
        rd = ("BETTER" if hi < 1 else "WORSE" if lo > 1 else
              ("underpowered" if max(pt, 1 / pt) < m else "flat (real absence)"))
        print(f"  {ml:<14} {b:<10} {pt:>7.3f} [{lo:>7.3f}, {hi:>7.3f}] {m:>6.2f}   {rd}")
        OUT.setdefault("burst_mde", {})[f"{ml}|{b}"] = dict(ratio=pt, lo=lo, hi=hi, mde=m,
                                                            reading=rd)

with open(ROOT / "_scratch/out/_r5d_creep_close.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_creep_close.json")
