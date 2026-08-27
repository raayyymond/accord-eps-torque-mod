#!/usr/bin/env python3
r"""Adjudicate the X/Y axis assignment EMPIRICALLY, against V72's flown gp-0x69a4 probe.

Two competing readings of the slot fill at 0x39014..0x390b6:
  MINE    X[] <- gp-0x642e <- gp-0x3714 (field B) ;  Y[] <- gp-0x6442 <- 0.388*(A - 0.091*B)
  SWAPPED X[] <- field A                          ;  Y[] <- field B          (the raw ROM pair)

V72 (route 59, 87,940 frames) flew `bit6 = gp-0x69a4 >= 512` and `bit5 = gp-0x69a4 >= 1024`.
Measured: bit6 = 200 frames, bit5 = 0.  Whichever reading reproduces that is the right one.
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
import sys, glob
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run_clip_duty as RC
from assist_map_mirror import stage_382d8, build_map, lane, _lerp_u16

_SW = {}


def map_swapped(mode, speed_cnt, angle_10deg, armed=False):
    """The team-lead / red-team reading: the raw ROM pair IS the map. X = field A, Y = field B."""
    key = (mode, int(speed_cnt) // 16, armed)
    m = _SW.get(key)
    if m is None:
        sc = (int(speed_cnt) // 16) * 16
        A, B = stage_382d8(mode, sc)
        Xs = [0] * 10
        Ys = [0] * 10
        Xs[1:10] = A[1:9] + [8192]        # 9 seeds; index 9 = the cal ceiling, as in the real build
        Ys[1:10] = B[1:9] + [B[8]]
        m = build_map(Xs, Ys, RC.g69a0_of(sc, armed))
        _SW[key] = m
    return m


def load59():
    segs = [s for s in sorted(glob.glob(str(HERE.parent / '_scratch/cache/r59' / 'r59s*.npz')))
            if 'events' not in s and 'rpm' not in s]
    C = {k: [] for k in ('b6', 'b5', 'eng', 'tq', 'v', 'ang')}
    for s in segs:
        z = np.load(s, allow_pickle=True)
        C['b6'].append(np.asarray(z['b6_a512'], float))
        C['b5'].append(np.asarray(z['b5_a1024'], float))
        C['eng'].append(np.asarray(z['cc_lat'], float) > 0.5)
        C['tq'].append(np.asarray(z['tq'], float))
        C['v'].append(np.abs(np.asarray(z['cs_v'], float)))
        C['ang'].append(np.abs(np.asarray(z['cs_ang'], float)))
    return {k: np.concatenate(v) for k, v in C.items()}


def main():
    C = load59()
    n = len(C['b6'])
    Ts = np.rint(C['tq'] * 1.024).astype(int)
    kmh = C['v'] * 3.6
    print('V72 / route 59 : %d frames, engaged %d' % (n, C['eng'].sum()))
    print('MEASURED ON-CAR :  bit6 (a>=512) = %d frames   bit5 (a>=1024) = %d frames'
          % (int(np.nansum(C['b6'])), int(np.nansum(C['b5']))))
    print()
    for nm, fn in (('MINE     (X = field B via gp-0x642e)', RC.map_for),
                   ('SWAPPED  (X = field A, raw ROM pair)', map_swapped)):
        aq = np.zeros(n, int)
        for i in range(n):
            X, Y, Z, S = fn(26 if C['eng'][i] else 24, kmh[i] * 64.0, C['ang'][i] * 10.0, False)
            aq[i] = lane(int(Ts[i]), X, Y, Z, S)['a_q10']
        n6, n5 = int((aq >= 512).sum()), int((aq >= 1024).sum())
        ov = int(np.nansum(C['b6'][aq >= 512])) if n6 else 0
        print('%-38s  a: p50=%5d p95=%5d max=%5d   PREDICTS bit6=%6d  bit5=%6d   overlap=%d/200'
              % (nm, np.percentile(aq, 50), np.percentile(aq, 95), aq.max(), n6, n5, ov))
        print('%-38s  bit6 error factor vs measured 200: %s'
              % ('', ('%.1fx TOO MANY' % (n6 / 200.0)) if n6 > 200 else
                 ('%.2fx' % (n6 / 200.0)) if n6 else 'ZERO (predicts none)'))


if __name__ == '__main__':
    main()
