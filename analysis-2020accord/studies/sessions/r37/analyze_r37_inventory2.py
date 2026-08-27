#!/usr/bin/env python3
"""V62 route-37 sanity pass: fs, wall-clock anchor, engagement, gear, health flags per segment.

Preface to studies/sessions/r37/analyze_r37_newgrind.py. Nothing here is a conclusion; it exists so every later number
has a stated denominator. Segment 0 is a stale 07:05 boot and is EXCLUDED everywhere downstream.
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
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402

C.CACHE = C.ROOT / "_scratch/cache/r37"
PFX = "r37s"
SEGS = list(range(0, 15))


def main():
    print("seg   n      fs      t_span        wall_t0     v_min..v_max   lat%   sca%   "
          "gear                     sstat!=0  ST==4  ev")
    for s in SEGS:
        f = C.CACHE / f"{PFX}{s}.npz"
        if not f.exists():
            continue
        d = C.load(s, C.CACHE, PFX)
        fs = C.fs_of(d)
        w0 = float(d["wall_t0"][0])
        wstr = time.strftime("%H:%M:%S", time.localtime(w0))
        g = {C.GEAR[int(x)]: int((d["cs_gear"] == x).sum()) for x in np.unique(d["cs_gear"])}
        ev = json.loads((C.CACHE / f"{PFX}{s}_events.json").read_text())
        n4 = int((d["sstat"] == 4).sum())
        nnz = int((d["sstat"] != 0).sum())
        print(f"{s:3d} {len(d['t']):6d} {fs:7.3f}  {d['t'][0]:6.2f}..{d['t'][-1]:6.2f}  {wstr}  "
              f"{d['cs_v'].min():6.2f}..{d['cs_v'].max():6.2f}  "
              f"{100*(d['cc_lat']>0.5).mean():5.1f}  {100*(d['sca']==1).mean():5.1f}  "
              f"{str(g):24s} {nnz:8d} {n4:6d} {len(ev):4d}")

    # ---- event names of interest, with wall clock -------------------------------------------
    print("\nEVENTS (deduped runs) across segs 1-14:")
    KEEP = ("steerSaturated", "controlsMismatch", "steerTempUnavailable", "steerUnavailable",
            "belowSteerSpeed", "steerTimeLimit", "commIssue", "selfdriveLagging",
            "selfdrivedLagging", "preLaneChange", "ldw")
    for s in SEGS[1:]:
        f = C.CACHE / f"{PFX}{s}_events.json"
        if not f.exists():
            continue
        d = C.load(s, C.CACHE, PFX)
        w0 = float(d["wall_t0"][0])
        ev = json.loads(f.read_text())
        runs = {}
        for e in ev:
            nm = e["name"]
            r = runs.setdefault(nm, [e["t"], e["t"], 0])
            r[1] = e["t"]
            r[2] += 1
        for nm, (a, b, n) in sorted(runs.items()):
            flag = "  <<" if any(k.lower() in nm.lower() for k in KEEP) else ""
            print(f"  seg{s:<3d} {nm:34s} n={n:5d}  t {a:6.2f}..{b:6.2f}  "
                  f"wall {time.strftime('%H:%M:%S', time.localtime(w0+a))}"
                  f"..{time.strftime('%H:%M:%S', time.localtime(w0+b))}{flag}")


if __name__ == "__main__":
    main()
