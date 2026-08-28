#!/usr/bin/env python3
r"""Cache for route 21 -- the drive AFTER route 1e (V107).  Build identity UNKNOWN at write time.

WHY THIS EXISTS
---------------
Route 21 (18 segments) sat uncached on disk, newer than route 1e.  V108 flew and V111 flew, and the
operator could not upload logs for V108 at the time -- so route 21 is one of those two, and the
extractor must DECIDE which rather than assume.

🛑 THE DISCRIMINATOR IS THE 427 TAP ITSELF, and it is unambiguous:
      V108 / V109 : source gp-0x6c2c, `sar 5`   ->  0x55DF2 = d4 93, 0x55E10 = a5
      V111        : source gp-0x6abc, `sar 3`   ->  0x55DF2 = 44 95, 0x55E10 = a3
`gp-0x6abc` is the RAW resolver rate (signed, unfiltered, 4.7121 ct per column deg/s) and `gp-0x6c2c`
is the filtered ACCELERATION -- utterly different distributions.  At sar 3 the wire ceiling is
`|gp-0x6abc| = 1636` (= 347 deg/s); at sar 5 on gp-0x6c2c it is a much smaller quantity.  The report
below prints the wire distribution so the identity can be read off, and it does NOT guess.

WHAT THE ANSWER BUYS
--------------------
If route 21 IS V111, the tap is `|gp-0x6abc|` and it settles the two open questions at once:
  1. **The relay input amplitude.**  GATE 2 showed the knee `0xC40BC` only bites BELOW ~200-400
     counts (describing-function ratio 0.96-0.99 above ~400).  The measured distribution decides
     whether the ratchet knee is a lever at all.
  2. **Whether the alpha2 friction story is big enough.**  `accord-v111-flew-alpha2-is-the-only-delta`
     records the hole plainly: `gp-0x6b26` clamps at +-511 against a +-20,000 residual, so the term
     is <= 2.6 % of range and doubling its friction component may be far too small to explain the
     operator's lost steering rate.

Usage:
    python decode/extract_r21.py
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

PREFIX = "75604b0a432fdc89_00000021--489af1e5b7"
NSEG = 18
ROUTE = "21"

# same 6-tuple shape as extract_r7d.ROUTE_DEF
D.ROUTES[ROUTE] = (PREFIX, NSEG, f"analysis-2020accord/_scratch/cache/r{ROUTE}",
                   f"r{ROUTE}s", f"r{ROUTE}", "UNKNOWN-V108-or-V111")
if hasattr(R7D, "ROUTE_DEF"):
    R7D.ROUTE_DEF[ROUTE] = D.ROUTES[ROUTE]

# The tap report needs these two registries; without them extract_route() raises KeyError AFTER the
# cache has already been written.  Registered for BOTH candidate builds so the report is honest:
# if route 21 is V111 the source is gp-0x6abc at sar 3 (1 wire ct = 8/5 = 1.6 raw counts);
# if it is V108/V109 the source is gp-0x6c2c at sar 5 (1 wire ct = 32/5 = 6.4 raw counts).
# The DISTRIBUTION decides which -- see identify().
R7D.WIRE_SCALE[ROUTE] = 8.0 / 5.0
R7D.WIRE_SOURCE[ROUTE] = "UNKNOWN: gp-0x6abc sar3 (V111) or gp-0x6c2c sar5 (V108/V109)"
if ROUTE not in getattr(R7D, "PROBE_MEANING", {}):
    try:
        R7D.PROBE_MEANING[ROUTE] = R7D.PROBE_MEANING["7d"]
    except Exception:
        pass

RATE_SCALE = 4.7121          # counts per column deg/s, via gp-0x6ac0 (same quantity as gp-0x6abc)


def identify(z):
    """Read the build identity off the 427 wire distribution.  Do not guess."""
    print("\n" + "=" * 88)
    print("  BUILD IDENTITY FROM THE 427 TAP -- read, not assumed")
    print("=" * 88)
    key = next((k for k in ("mag427", "ab_mt", "probe") if k in z), None)
    if key is None:
        print("  no 427 magnitude channel in the cache -- cannot identify")
        return
    w = np.asarray(z[key]).astype(float)
    w = w[np.isfinite(w)]
    if not len(w):
        print("  427 channel present but empty")
        return
    q = np.percentile(w, [50, 90, 99, 99.9])
    print(f"  channel `{key}`  n={len(w)}  p50 {q[0]:.0f}  p90 {q[1]:.0f}  p99 {q[2]:.0f} "
          f"p99.9 {q[3]:.0f}  max {w.max():.0f}   (10-bit field, ceiling 1023)")
    print(f"  duty at ceiling (>=1023): {np.mean(w >= 1023):.6f}")
    print("\n  IF THIS IS V111 the wire is |gp-0x6abc| at sar 3:")
    print(f"     1 wire count = {(1 << 3) / 5.0:.2f} raw = {(1 << 3) / 5.0 / RATE_SCALE:.3f} deg/s")
    print(f"     => p50 {q[0] * 1.6 / RATE_SCALE:6.1f} deg/s   p99 {q[2] * 1.6 / RATE_SCALE:6.1f} deg/s"
          f"   max {w.max() * 1.6 / RATE_SCALE:6.1f} deg/s")
    print("\n  THE GATE-2 QUESTION -- the knee only bites BELOW ~200-400 RAW counts:")
    raw = w * 1.6
    for thr, lab in ((50, "knee 600 corner"), (100, "knee 1200"), (200, "knee 2400"),
                     (400, "knee 4800 -- above this a raise does ~nothing")):
        print(f"     duty(|gp-0x6abc| >= {thr:4d}) = {np.mean(raw >= thr):.4f}   [{lab}]")
    print("\n  (wire >= 31) AND NOT (>= 125) is EXACTLY the population a knee 600->2400 raise")
    print(f"  would affect:  duty = {np.mean((w >= 31) & (w < 125)):.4f}")


def main():
    print(f"  extracting route {ROUTE}: {NSEG} segments, prefix {PREFIX}", flush=True)
    R7D.extract_route(ROUTE)
    f = ROOT / "analysis-2020accord" / "_scratch" / "cache" / f"r{ROUTE}" / f"r{ROUTE}.npz"
    if not f.exists():
        print(f"  no cache written at {f}")
        return
    z = dict(np.load(f, allow_pickle=True))
    print(f"\n  cache written: {f}  ({f.stat().st_size / 1e6:.0f} MB, {len(z)} fields)")
    identify(z)


if __name__ == "__main__":
    main()
