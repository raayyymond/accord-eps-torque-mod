#!/usr/bin/env python3
r"""Speed-split PSD of the manual-drive hands-off-engaged 399 torque, to test whether the
vibration frequency depends on road speed (tire/plant hypothesis) and reconcile the manual-drive
12.5 Hz dominance with route b9's 21.5 Hz."""
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
import numpy as np
from analyze_manual_vibration import load_segment, frame_ts, hann, welch, GLOB, FS, DT
import glob

paths = sorted(glob.glob(GLOB))
segs = [load_segment(p) for p in paths]
runs = []
for si, S in enumerate(segs):
    if len(S["t"]) < 200 or len(S["cc_t"]) < 2 or len(S["cs_t"]) < 2:
        continue
    t399, per = frame_ts(S["t"])
    cc_ts = S["cc_t"].astype(float) / 1e9; cs_ts = S["cs_t"].astype(float) / 1e9
    lat = np.interp(t399, cc_ts, S["cc_lat"]) > 0.5
    pressed = np.interp(t399, cs_ts, S["cs_pressed"]) > 0.5
    vego = np.interp(t399, cs_ts, S["cs_vego"])
    ho = lat & (~pressed)
    m = ho.astype(int); edges = np.diff(np.concatenate([[0], m, [0]]))
    for s0, e0 in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
        if e0 - s0 < 128:
            continue
        runs.append(dict(tq=S["tq"][s0:e0].copy(), vego=vego[s0:e0].copy()))

bands = [("stationary-crawl <3 m/s", 0, 3), ("low 3-8 m/s", 3, 8),
         ("mid 8-15 m/s", 8, 15), ("high >15 m/s", 15, 100)]
for name, lo, hi in bands:
    sel = [r for r in runs if lo <= r["vego"].mean() < hi]
    if not sel:
        print(f"{name:26s}: (no runs)"); continue
    f, P, K = welch(sel, "tq", 512)
    b = (f >= 8) & (f <= 30)
    ip = np.where(b)[0][np.argmax(P[b])]
    # also band powers
    def bp(a, c):
        return P[(f >= a) & (f <= c)].sum()
    n = sum(len(r["tq"]) for r in sel)
    print(f"{name:26s}: runs={len(sel):2d} K={K:3d} dur={n/FS:5.0f}s  "
          f"PEAK {f[ip]:5.2f} Hz | band-power 10-15:{bp(10,15):.3g} 15-20:{bp(15,20):.3g} "
          f"20-25:{bp(20,25):.3g} 25-30:{bp(25,30):.3g}")
