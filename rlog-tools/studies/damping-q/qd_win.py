#!/usr/bin/env python3
"""Windowing + per-window scoring shared by `studies/damping-q/qd_score.py` and `studies/damping-q/qd_power.py`.

Split out so the power study can reuse the EXACT windows the verdict is computed on, rather than
re-deriving them (and drifting).  Nothing here has side effects on import.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import qd_lib as Q                                                       # noqa: E402

ROUTES = {"V86": "r6f", "V86B": "r70", "V85": "r6e"}
ALPHA = {"V86": 286, "V86B": 573, "V85": 573}          # 0xC40D4
VBINS = [(0.5, 1.5), (1.5, 2.78), (2.78, 5.0)]
VLO, VHI = 0.5, 5.0
VCAP = 6.0                                             # no sample in a kept window above this
CIRC = 2.0805
SIG = "tq"                                             # 0x18F word0 -- the bar-torque line
_CACHE = {}


def load(route):
    if route not in _CACHE:
        z = np.load(ROOT / f"_cache_{route}" / f"{route}.npz", allow_pickle=True)
        d = {k: np.asarray(z[k]) for k in
             ("t", SIG, "cs_v", "cc_lat", "seg", "cs_gear", "cs_press", "ang", "rate_f")}
        d["fs"] = 1.0 / np.median(np.diff(d["t"]))
        _CACHE[route] = d
    return _CACHE[route]


def windows(build, nw, engaged=True, speed=True, sig=SIG):
    """Windows are cut from the ENGAGED run without a per-sample speed mask, then FILTERED on the
    window's own speed.  Masking per-sample would chop V85's 304 s engaged run into <20 s pieces
    and destroy the very resolution this test needs; filtering whole windows does not."""
    d = load(ROUTES[build])
    fs = d["fs"]
    t, x, v = d["t"], np.asarray(d[sig], float), d["cs_v"]
    lat = np.asarray(d["cc_lat"], float) > 0.5
    m = lat if engaged else ~lat
    hop = nw // 2
    out = []
    for a, b in Q.contiguous_runs(m, t, nw):
        for j0 in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + j0, a + j0 + nw)
            seg = x[sl]
            if not np.all(np.isfinite(seg)):
                continue
            vv = v[sl]
            vmed = float(np.median(vv))
            if speed and not (VLO <= vmed < VHI and vv.max() <= VCAP):
                continue
            out.append(dict(build=build, x=seg, fs=fs, t0=float(t[sl][0]),
                            v=vmed, vlo=float(vv.min()), vhi=float(vv.max()),
                            run=f"{a}", blk=f"{a}:{(j0 // 1024)}", nw=nw))
    return out


def order_clean(rs, orders=(1, 2, 3, 4), guard=0.8):
    """TARGETED wheel-order veto: drop a window only if an order lands within `guard` Hz of the
    line that window actually measured.

    NOT `v86_freq_test.order_clean`, deliberately.  That rule vetoes any order anywhere in the
    5-12 Hz SEARCH band, which at CIRC=2.0805 removes every window above 2.60 m/s (order 4) --
    the whole 2.78-5.0 m/s bin and half of 1.5-2.78.  It is right for a free argmax search and
    wrong for a linewidth measured at a known peak, where only orders sitting ON the peak (or
    inside the +-0.6 Hz floor-exclusion annulus) can contaminate it."""
    keep = []
    for r in rs:
        f0 = r.get("f0", np.nan)
        if not np.isfinite(f0):
            continue
        if any(abs(k * r["v"] / CIRC - f0) < guard for k in orders):
            r["order_hit"] = True
            continue
        keep.append(r)
    return keep


def score(rs, fc_hint=7.79):
    for r in rs:
        r.update(Q.linewidth(r["x"], r["fs"]))
        fc = r["f0"] if np.isfinite(r.get("f0", np.nan)) else fc_hint
        # duty at 1.0x the median is IDENTICALLY ~0.5 by construction -- 1.5x and 2.0x are not
        e15 = Q.envelope_stats(r["x"], r["fs"], fc, thresh_k=1.5)
        e20 = Q.envelope_stats(r["x"], r["fs"], fc, thresh_k=2.0)
        r.update(e15)
        r["duty20"], r["burst20_s"] = e20["duty"], e20["burst_s"]
        r["q_frac"] = r["q_app"] / r["q_max"] if np.isfinite(r.get("q_app", np.nan)) else np.nan
    return rs


def shared_weights(arms):
    c = [np.array([sum(1 for r in rs if lo <= r["v"] < hi) for lo, hi in VBINS], float)
         for rs in arms]
    st = np.vstack(c)
    w = np.min(st, axis=0)
    return np.where(np.all(st > 0, axis=0), w, 0.0), [x.tolist() for x in c]
