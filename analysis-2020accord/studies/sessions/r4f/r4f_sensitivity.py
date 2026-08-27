#!/usr/bin/env python3
"""Does the route-4f headline survive the two estimator choices this session made?

CHOICE 1 -- THE RESAMPLING UNIT. `_grind2_lib.EPKEY` is either "blk" (a ~10.2 s block nested inside
one engagement run; the kit's working default because engagement runs are 30-60 s and a build can
have as few as 5 of them, which makes the split-half null degenerate) or "ep" (one whole contiguous
engagement run; the most conservative unit). Both are run here, and the null is recomputed with the
SAME unit each time, so the ratio is always scored against a floor from the identical estimator.

CHOICE 2 -- THE SAMPLE RATE. This session replaced `1/median(dt)` with the mean rate over the
longest gapless stretch, because the legacy estimator is biased by a ROUTE-DEPENDENT 0.13-1.42%
(r4f 100.13, r37 100.40, r3b 100.67, r35 101.42 against a true 100.000 Hz grid) and that shifts the
frequency axis of one arm relative to the other by up to 0.27 Hz at 21 Hz. The fix was applied to
EVERY build, never to 4f alone -- but a reader is entitled to see it change nothing. Both are run.

Writes `_scratch/out/_r4f_sensitivity.json`.  Usage: python studies/sessions/r4f/r4f_sensitivity.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r4f_lib as L  # noqa: E402

RNG = np.random.default_rng(20260803)
NBOOT, NULLREP = 2000, 250
OUT = {}


def build_store(lattice):
    """Window records for every build under one fs estimator, cached to its own pickle."""
    L.USE_LATTICE_FS = lattice
    L.install_fs(lattice)
    pkl = HERE.parent / (f"_cache_r4f_records{'' if lattice else '_legacyfs'}.pkl")
    L.PKL = pkl
    if pkl.exists():
        with open(pkl, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__fs__") == ("lattice" if lattice else "legacy"):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    return L.records(rebuild=True)


def prep(rs):
    for r in rs:
        a, b = r.get("e_18-22", np.nan), r.get("e_24-28", np.nan)
        r["bandnorm"] = (a / b) if (np.isfinite(a) and np.isfinite(b) and b > 0) else np.nan
        r["cell"] = (r["eng"], G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                     G.binof(r["rate"], G.R_BINS))
    return rs


rows = []
for lattice in (True, False):
    store = build_store(lattice)
    arms = {"V69": [BUILD] if (BUILD := "V69/r4f") else [], "Kd2": L.POOL_KD2,
            "Kd2g": L.POOL_GATED, "Kd1": L.POOL_KD1}
    ENG = {k: prep([r for r in (store.get(n, []) for n in v) for r in r if r["eng"] == 1])
           for k, v in arms.items()}
    for epkey in ("blk", "ep"):
        G.EPKEY = epkey
        for other in ("Kd2", "Kd2g", "Kd1"):
            for key in ("e_18-22", "bandnorm", "e_24-28", "e_1-4"):
                r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(
                    ENG["V69"], ENG[other], key, RNG, nboot=NBOOT)
                nl = G.split_half_null(ENG[other], key, RNG, nrep=NULLREP)
                rows.append(dict(fs=("lattice" if lattice else "legacy"), unit=epkey,
                                 arm=other, key=key, ratio=float(r), lo=float(lo), hi=float(hi),
                                 ncells=int(nc), uA=int(na), uB=int(nb),
                                 null=[float(x) for x in nl]))

L.hdr("SENSITIVITY -- V69/route 4f vs each pool, ENGAGED, under both estimator choices")
print(f"  {'fs est':>8} {'unit':>5} {'arm':>5} {'metric':>10} {'ratio':>7} {'95% CI':>18} "
      f"{'cells':>5} {'units A/B':>10} {'null':>15} {'verdict':>12}")
for r in rows:
    n = r["null"]
    v = ("INSIDE" if (np.isfinite(r["ratio"]) and np.isfinite(n[1]) and n[1] <= r["ratio"] <= n[2])
         else ("OUTSIDE" if np.isfinite(r["ratio"]) else "n/a"))
    print(f"  {r['fs']:>8} {r['unit']:>5} {r['arm']:>5} {r['key']:>10} {r['ratio']:>7.3f} "
          f"[{r['lo']:>7.3f},{r['hi']:>8.3f}] {r['ncells']:>5} {r['uA']:>4}/{r['uB']:<5} "
          f"[{n[1]:>5.2f},{n[2]:>5.2f}] {v:>12}")
OUT["rows"] = rows
(HERE / "_scratch/out/_r4f_sensitivity.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r4f_sensitivity.json'}")
