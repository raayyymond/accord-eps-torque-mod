#!/usr/bin/env python3
"""D4 shared: cache `r47_orchestrator_checks._windows` rows for every pool ONCE.

Nothing numeric is added -- the rows are exactly what `studies/sessions/r58/r58_grind2.py` / `studies/sessions/r58/r58_r54_highrate_4049.py`
build, so every count stays comparable to the corpus. Only two derived keys are attached, both
already established: `idx` (rate index at PEAK |rate_c|) and `eff` (sustained driver effort).
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import r47_orchestrator_checks as R47  # noqa: E402
from _r31_common import sustained  # noqa: E402

PKL = ROOT / "_scratch/data/_d4_rows.pkl"
CPD = 4.7121
CREEP = (0.3, 4.0)
HWY = 14.0

POOLS = {
    "Kd=0     (V61 r31)":                     ["_scratch/cache/r31"],
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "Kd=gated (V67 r47 + V68 r4e)":           ["_scratch/cache/r47", "_scratch/cache/v68"],
    "Kd=4x<50 (V69 r4f)":                     ["_scratch/cache/r4f"],
    "Kd=2x<50 (V70 r50)":                     ["_scratch/cache/r50"],
    "V71B r54  r26 x2 UNGATED":               ["_scratch/cache/r54"],
    "V71C r58  both arms GATED":              ["_scratch/cache/r58"],
    "V72 r59  BOTH lanes UNGATED  ***":       ["_scratch/cache/r59"],
}
SKIP = {"_scratch/cache/r54": ("r54s10", "r54s11"),
        "_scratch/cache/r58": ("r58s12", "r58s13", "r58s14", "r58s15"),
        "_scratch/cache/r50": ("r50s0",),
        "_scratch/cache/r59": ("r59s12", "r59s13", "r59s14")}
REF = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
NEW = "V72 r59  BOTH lanes UNGATED  ***"
RB = [(0.0, 400.0), (400.0, 1400.0), (1400.0, 1e9)]
RNAMES = ["plateau", "knee", "HIGH-RATE"]


def rows(rebuild=False):
    if PKL.exists() and not rebuild:
        with open(PKL, "rb") as fh:
            return pickle.load(fh)
    out = {}
    for name, caches in POOLS.items():
        r = []
        for c in caches:
            rr = R47._windows(c, name, lambda v: True)
            r += [x for x in rr if not any(s in str(x["ep"][0]) for s in SKIP.get(c, ()))]
        for x in r:
            x["idx"] = CPD * x["ratemax"]
            x["eff"] = float(np.median(np.abs(sustained(np.asarray(x["raw"], float), x["fs"]))))
            x["rb"] = next(i for i, (lo, hi) in enumerate(RB) if lo <= x["idx"] < hi)
            x.pop("raw", None)          # 2.56 s of raw torque per window is 100 MB of pickle
        out[name] = r
    with open(PKL, "wb") as fh:
        pickle.dump(out, fh)
    return out


def secs(rs):
    return len(rs) * R47.WIN_S / 2.0


def bursts(rs, key="40-49"):
    return int(sum(1 for r in rs if r[key] > R47.BURST))


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)
