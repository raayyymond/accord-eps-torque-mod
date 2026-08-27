#!/usr/bin/env python3
"""Targeted NATIVE-timestamp extraction of route-67 segment 8 only -- the highway-instability
segment. Writes `_scratch/cache/r67x/v81loop_native_s8.npz`. Nothing of r67-analyst's is touched.

WHY, when a cache already exists: the shared cache resamples every channel onto the 0x14A row grid,
and for the one channel that decides the energy-sign test -- the bus ECHO of openpilot's command
(`can` src 129, 0x0E4) -- it does so with a HOLD whose age is unknown.  That echo is the only
direct measurement of L2, the delay from openpilot's sendcan timestamp to the command actually
being on the wire, and at 27.5 Hz a 10 ms error in L2 is 99 deg and flips the sign of the answer.

So this file keeps every message on its OWN arrival timestamps, with no gridding at all:

    sc_*      sendcan src 1   0x0E4    openpilot's decision instant
    ec_*      can     src 129 0x0E4    the same payload, echoed back off the wire  -> L2
    b_*       can     src 1   0x18F    torsion bar + the 8x-fine rate
    a_*       can     src 1   0x14A    angle + coarse rate + the V75/V81 probe byte
    w_*       can     src 1   0x1D0    wheel speeds -> the ORDER VETO, from measured rotation
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
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "analysis-2020accord"))
from compare_v75_v76_v80_grind import KMH, i16be, wheel_speeds_kph  # noqa: E402
from rlog_parse import read_messages  # noqa: E402

ROUTE = "75604b0a432fdc89_00000067--9b3ebbe218"
OUT = HERE.parent / "_scratch/cache/r67x" / "v81loop_native_s8.npz"


def main(segs=(8,)):
    sc_t, sc_v = [], []
    ec_t, ec_v = [], []
    b_t, b_tq, b_rt, b_st, b_sca = [], [], [], [], []
    a_t, a_ang, a_rc, a_pr = [], [], [], []
    w_t, w_v = [], []
    cs_t, cs_v, cs_lat = [], [], []
    for s in segs:
        p = HERE.parent / "analysis-2020accord" / "rlogs" / f"{ROUTE}--{s}--rlog.zst"
        for evt in read_messages(p):
            try:
                which = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if which == "can":
                for m in evt.can:
                    src, addr, d = int(m.src), int(m.address), bytes(m.dat)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        b_t.append(tm); b_tq.append(i16be(d, 0) * -1.0)
                        b_rt.append(i16be(d, 2) * -0.1)
                        b_st.append((d[4] >> 4) & 0xF); b_sca.append((d[4] >> 3) & 1)
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        a_t.append(tm); a_ang.append(i16be(d, 0) * -0.1)
                        a_rc.append(i16be(d, 2) * -1.0); a_pr.append(d[4])
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        ec_t.append(tm); ec_v.append(float(i16be(d, 0)))
                    elif src == 1 and addr == 0x1D0 and len(d) >= 8:
                        w_t.append(tm); w_v.append(wheel_speeds_kph(d))
            elif which == "sendcan":
                for m in evt.sendcan:
                    if int(m.src) == 1 and int(m.address) == 0x0E4:
                        d = bytes(m.dat)
                        if len(d) >= 3:
                            sc_t.append(tm); sc_v.append(float(i16be(d, 0)))
            elif which == "carState":
                cs_t.append(tm); cs_v.append(float(evt.carState.vEgo))
            elif which == "carControl":
                cs_lat.append((tm, float(bool(evt.carControl.latActive))))
        print(f"  seg {s} done", flush=True)

    t0 = min(a_t[0], sc_t[0])
    k = dict(sc_t=np.array(sc_t) - t0, sc_v=np.array(sc_v),
             ec_t=np.array(ec_t) - t0, ec_v=np.array(ec_v),
             b_t=np.array(b_t) - t0, b_tq=np.array(b_tq), b_rt=np.array(b_rt),
             b_st=np.array(b_st, float), b_sca=np.array(b_sca, float),
             a_t=np.array(a_t) - t0, a_ang=np.array(a_ang), a_rc=np.array(a_rc),
             a_pr=np.array(a_pr, float),
             w_t=np.array(w_t) - t0, w_kph=np.array(w_v, float).reshape(-1, 4) * KMH,
             cs_t=np.array(cs_t) - t0, cs_v=np.array(cs_v),
             lat_t=np.array([x[0] for x in cs_lat]) - t0,
             lat_v=np.array([x[1] for x in cs_lat]), t0=np.array([t0]))
    np.savez_compressed(OUT, **k)
    for nm in ("sc", "ec", "b", "a", "w"):
        t = k[nm + "_t"]
        print(f"  {nm:3s} n={len(t):6d}  {t[0]:7.2f}..{t[-1]:7.2f} s  "
              f"mean rate {(len(t) - 1) / (t[-1] - t[0]):7.3f} Hz")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or (8,))
