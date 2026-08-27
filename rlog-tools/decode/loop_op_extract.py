#!/usr/bin/env python3
"""Build `_scratch/cache/loop_op/` -- the batch-lattice cache the command<->response causality work runs on.

    python decode/loop_op_extract.py                # all four routes
    python decode/loop_op_extract.py V84/r6d        # one

See `loop_op_lib`'s docstring for why this cache exists rather than reusing `_scratch/cache/r6d` etc.:
the corpus caches build one row per 0x14A frame and carry the 0x18F payload forward by a whole
batch, and they resample `sendcan` onto that foreign lattice with `np.interp`.  Both are fatal to a
phase-slope measurement at 27 Hz.
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
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(routes):
    for r in routes:
        print(f"=== {r}", flush=True)
        segs = L.build_route(r)
        L.save_route(r, segs)
        t = sum(len(d["t"]) for d in segs)
        eng = sum(int((d["cc_lat"] > 0.5).sum()) for d in segs)
        fss = np.array([d["_fs"] for d in segs])
        print(f"    {len(segs)} segs  {t} batches  {t/100:.0f} s  engaged {eng/max(t,1)*100:.1f}%  "
              f"fs {fss.min():.4f}..{fss.max():.4f}")
        # instrument health: how close is the batch lattice to uniform?
        for d in segs[:2]:
            dt = np.diff(d["t"])
            print(f"      seg{d['_seg']} dt p1/p50/p99 = {np.percentile(dt,1)*1e3:.2f}/"
                  f"{np.median(dt)*1e3:.2f}/{np.percentile(dt,99)*1e3:.2f} ms  "
                  f"gaps>15ms: {(dt>0.015).sum()}")
    print(f"\ncache -> {L.CACHE}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a in L.ROUTES]
    main(args or list(L.ROUTES))
