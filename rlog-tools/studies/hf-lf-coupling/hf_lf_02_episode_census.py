#!/usr/bin/env python3
r"""EPISODE CENSUS -- how much CONTIGUOUS highway-engaged material exists, and how fast is it?

An envelope oscillating at 0.3 Hz needs >=10 s of unbroken record per analysis segment.  This file
answers, per route and per arm, whether that material exists BEFORE anything is measured on it,
and it prints the speed distribution inside each episode so the wheel-order trap
(`accord-averaged-spectrum-needs-matched-speed-distributions`) can be checked rather than assumed.

Wheel order 1 = v[m/s] / 2.0805 m  (`_r4f_lib.CIRC`).  At 70-120 km/h that is 9.3-16.0 Hz, so
order 2 is 18.7-32.0 Hz and order 3 is 28.0-48.0 Hz -- i.e. BOTH candidate HF bands sit on a wheel
order at highway speed.  Printed here so no later band claim can skip it.

OUTPUT `rlog-tools/_scratch/out/_hf_lf_episodes.json`
"""
from __future__ import annotations
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

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTE_LABEL = {"97": "STOCK (V9b)", "9e": "V103", "96": "V102 6x", "85": "V100 4x", "95": "V101 8x"}
ROUTES = ["9e", "97", "96", "85", "95"]
KMH = 3.6
CIRC = 2.0805


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def episodes(rt, engaged=True, vlo=70.0, vhi=200.0, minlen=1024):
    """Maximal contiguous runs of (arm AND speed stratum) inside ONE gap-free block."""
    out = []
    for bi, blk in enumerate(L.all_blocks(rt)):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        want = (eng if engaged else ~eng) & (v >= vlo) & (v < vhi)
        idx = np.nonzero(np.diff(want.astype(int)) != 0)[0] + 1
        bounds = [0] + list(idx) + [len(want)]
        for a, b in zip(bounds[:-1], bounds[1:]):
            if not want[a] or (b - a) < minlen:
                continue
            vv = v[a:b]
            out.append(dict(route=rt, seg=blk["_seg"], blk=bi, a=int(a), b=int(b),
                            n=int(b - a), s=float((b - a) / L.FS),
                            t0=float(blk["t"][a]),
                            v_med=float(np.median(vv)), v_min=float(vv.min()),
                            v_max=float(vv.max()),
                            wo1=float(np.median(vv) / KMH / CIRC)))
    return out


def main():
    res = {}
    for rt in ROUTES:
        if not reg(rt):
            continue
        print("\n" + "=" * 100)
        print("ROUTE %s  (%s)" % (rt, ROUTE_LABEL.get(rt, rt)))
        print("=" * 100)
        res[rt] = {}
        for arm, eng in (("ENGAGED", True), ("manual", False)):
            for lab, (lo, hi) in (("hwy>=70", (70.0, 200.0)), ("mid 40-70", (40.0, 70.0)),
                                  ("low<40", (0.0, 40.0))):
                eps = episodes(rt, engaged=eng, vlo=lo, vhi=hi)
                tot = sum(e["s"] for e in eps)
                res[rt]["%s|%s" % (arm, lab)] = eps
                if not eps:
                    print("  %-8s %-10s : none >= 10.24 s" % (arm, lab))
                    continue
                print("  %-8s %-10s : %2d episodes, %6.1f s   longest %5.1f s   "
                      "v med %5.1f [%5.1f-%5.1f] km/h   wheel-order-1 %.1f Hz (o2 %.1f, o3 %.1f)"
                      % (arm, lab, len(eps), tot, max(e["s"] for e in eps),
                         float(np.median([e["v_med"] for e in eps])),
                         min(e["v_min"] for e in eps), max(e["v_max"] for e in eps),
                         float(np.median([e["wo1"] for e in eps])),
                         2 * float(np.median([e["wo1"] for e in eps])),
                         3 * float(np.median([e["wo1"] for e in eps]))))
    (HERE / "_scratch/out/_hf_lf_episodes.json").write_text(json.dumps(res, indent=1))
    print("\nwrote", HERE / "_scratch/out/_hf_lf_episodes.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
