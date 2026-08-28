#!/usr/bin/env python3
r"""Cache routes 22 and 23 -- the first two drives on V112.

WHY THIS EXISTS
---------------
The operator flew V112 (relay knee 600->1800 with K1 612, holding the small-signal gain) and
reported it the best firmware yet: grind #1 now RARE, least ratcheting ever.  Two symptoms remain:

  1. grind #1 still fires occasionally, and he can no longer characterise the trigger --
     "I no longer have an understanding of the kinds of scenarios that illicit grind #1".
     => the trigger must be found in the DATA, not from his report.
  2. a NEW and more specific symptom: "not just ratcheting but ... a FIXED OSCILLATION during the
     peak of a hard curve."  He gave an exact instance: ROUTE 23, SEGMENT 7, 21:46:48.

TAP IDENTITY
------------
V112 = V111 + 0xC40BC/0xC40D2 only, so the 427 tap is V111's, unchanged:
    source gp-0x6abc, `sar 3`   ->  0x55DF2 = 44 95, 0x55E10 = a3
1 wire count = 8/5 = 1.6 raw counts of |gp-0x6abc|; 4.7121 raw counts per column deg/s.

Usage:
    python decode/extract_r22_r23.py
"""
# --- PATH BOOTSTRAP -------------------------------------------------------
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_roots, _c = [], _here
while True:
    if _os.path.isfile(_os.path.join(_c, ".pkgroot")):
        _roots.append(_c)
    _n = _os.path.dirname(_c)
    if _n == _c:
        break
    _c = _n
_top = _os.path.dirname(_roots[0])
for _e in sorted(_os.listdir(_top)):
    _cand = _os.path.join(_top, _e)
    if _os.path.isfile(_os.path.join(_cand, ".pkgroot")) and _cand not in _roots:
        _roots.append(_cand)
_p = []
for _r in _roots:
    _p.append(_r)
    for _b, _ds, _fs in _os.walk(_r):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_here", "_roots", "_c", "_n", "_top", "_e", "_cand", "_p",
           "_r", "_b", "_ds", "_fs", "_x", "_v"):
    globals().pop(_v, None)
# --------------------------------------------------------------------------
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as R7D                                                   # noqa: E402
import decode_v84_probe_r6d as D                                            # noqa: E402

ROUTES = {
    "22": ("75604b0a432fdc89_00000022--00f57626e0", 12),
    "23": ("75604b0a432fdc89_00000023--fc5f268959", 9),
}
RATE_SCALE = 4.7121


def register(route):
    prefix, nseg = ROUTES[route]
    D.ROUTES[route] = (prefix, nseg, f"analysis-2020accord/_scratch/cache/r{route}",
                       f"r{route}s", f"r{route}", "V112")
    if hasattr(R7D, "ROUTE_DEF"):
        R7D.ROUTE_DEF[route] = D.ROUTES[route]
    # V112 carries V111's tap: gp-0x6abc at sar 3
    R7D.WIRE_SCALE[route] = 8.0 / 5.0
    R7D.WIRE_SOURCE[route] = "gp-0x6abc sar3 (V111/V112 tap)"
    if route not in getattr(R7D, "PROBE_MEANING", {}):
        try:
            R7D.PROBE_MEANING[route] = R7D.PROBE_MEANING["7d"]
        except Exception:
            pass


def report(route):
    f = ROOT / "analysis-2020accord" / "_scratch" / "cache" / f"r{route}" / f"r{route}.npz"
    if not f.exists():
        print(f"  no cache at {f}")
        return
    z = dict(np.load(f, allow_pickle=True))
    print(f"\n  r{route}: {f.stat().st_size / 1e6:.0f} MB, {len(z)} fields")
    t = np.asarray(z["t"]).astype(float)
    print(f"    span {t[-1] - t[0]:.1f} s   n={len(t)}")
    for k in ("mag427", "ab_mt", "probe"):
        if k in z:
            w = np.asarray(z[k]).astype(float)
            w = w[np.isfinite(w)]
            if len(w):
                q = np.percentile(w, [50, 95, 99, 99.9])
                print(f"    427 `{k}` p50 {q[0]:.0f} p95 {q[1]:.0f} p99 {q[2]:.0f} "
                      f"p99.9 {q[3]:.0f} max {w.max():.0f}")
                print(f"      as column deg/s (x1.6/{RATE_SCALE}):  p95 {q[1]*1.6/RATE_SCALE:.1f} "
                      f"p99 {q[2]*1.6/RATE_SCALE:.1f} p99.9 {q[3]*1.6/RATE_SCALE:.1f}")
            break
    if "cc_lat" in z:
        lat = np.asarray(z["cc_lat"]).astype(float)
        print(f"    engaged duty {np.mean(lat > 0.5):.4f}")


def main():
    for route in ("22", "23"):
        prefix, nseg = ROUTES[route]
        print(f"\n{'=' * 88}\n  extracting route {route}: {nseg} segments, {prefix}\n{'=' * 88}",
              flush=True)
        register(route)
        R7D.extract_route(route)
        report(route)


if __name__ == "__main__":
    main()
