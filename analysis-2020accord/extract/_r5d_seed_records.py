#!/usr/bin/env python3
"""Seed `_scratch/data/_cache_r5d_records.pkl` from route 5a's pickle + the ONE new build.

`_r5d_lib.records()` rebuilds every build in `ORDER_5D` from scratch (~13 routes of periodograms).
Route 5a's pickle already holds all of them under the identical instrument and the identical fs
stamp, so the only thing that has to be computed here is `V74/r5d` itself.

🛑 The reuse is only legitimate because the window pipeline is byte-identical: `_r5d_lib` re-exports
`_r4f_lib.install_fs` and adds NOTHING to `_grind2_lib.wrecs`. The stamp is asserted, not assumed,
and every reused build is re-checked for the keys `_r5d_lib.records()` would have written.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r5d_lib as L  # noqa: E402

SRC = ROOT / "_scratch/data/_cache_r5a_records.pkl"
DST = L.PKL

L.install_fs()
stamp = "lattice" if L.USE_LATTICE_FS else "legacy"

with open(SRC, "rb") as fh:
    store = pickle.load(fh)
assert store.get("__fs__") == stamp, f"fs stamp drift: {store.get('__fs__')} vs {stamp}"

missing = [b for b in L.ORDER_5D if b != "V74/r5d" and b not in store]
assert not missing, f"route 5a's pickle is missing {missing}"

# every reused build must already carry the augmentations `records()` applies
for b in L.ORDER_5D:
    if b == "V74/r5d":
        continue
    r = store[b][0]
    for k in ("e_6-9", "e_18-22", "e_24-28", "vb", "rpm"):
        assert k in r, f"{b} windows lack `{k}` -- the pipelines are NOT identical"

print(f"reusing {len(L.ORDER_5D) - 1} builds from {SRC.name}")
rs = G.wrecs("V74/r5d")
print(f"V74/r5d: {len(rs)} raw windows")
store["V74/r5d"] = R47.augment(rs)
R4F._add_rpm("V74/r5d", store["V74/r5d"])
for r in store["V74/r5d"]:
    r["vb"] = L.vbin(r["v"])
L.R5A._add_mode("V74/r5d", store["V74/r5d"])      # NaN by construction on this route
L._add_probe("V74/r5d", store["V74/r5d"])

nd = np.array([r["damp"] for r in store["V74/r5d"]], float)
print(f"  damp duty over windows: finite {np.isfinite(nd).sum()}/{len(nd)}  "
      f"mean {np.nanmean(nd):.4f}")
assert np.isfinite(nd).mean() > 0.95, "the probe channel did not attach"
assert np.isnan(store["V74/r5d"][0]["mode"]), "mode must be NaN on route 5d"

store["__fs__"] = stamp
with open(DST, "wb") as fh:
    pickle.dump(store, fh)
print(f"wrote {DST}")
