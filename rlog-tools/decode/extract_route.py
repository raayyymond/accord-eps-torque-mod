#!/usr/bin/env python3
r"""Cache ANY route from the command line -- no new file per drive.

WHY THIS EXISTS
---------------
Every drive so far has needed its own extractor: `extract_r22_r23.py`, `extract_r24.py`,
`extract_r73.py`, ... Each is a ~125-line copy whose only real content is four values -- the rlog
prefix, the segment count, the build tag, and the probe tap metadata. Everything else is a verbatim
copy of the same PATH BOOTSTRAP, the same registration into `extract_r7d` / `decode_v84_probe_r6d`,
and the same call to `R7D.extract_route()`.

That copying has already gone wrong in the record: `extract_r24.py`'s own docstring still reads
"Cache routes 22 and 23" and "Usage: python decode/extract_r22_r23.py". A stale header is harmless;
a stale WIRE_SCALE or segment count is not, and nothing in the pattern prevents one.

So: the V158 drive should not need a new file. It needs one command.

USAGE
    python rlog-tools/decode/extract_route.py --route 82 \
        --prefix 75604b0a432fdc89_00000082--abcdef1234 --segments 30 --build V158

    optional, only if the build carries a 427 probe whose tap differs from the default:
        --wire-scale 1.6           (wire counts per raw count; V111/V112 tap = 8/5)
        --wire-source "gp-0x6abc sar3"

WHAT IT DOES
    1. registers the route in decode_v84_probe_r6d.ROUTES and extract_r7d.ROUTE_DEF,
       exactly as the per-route files do;
    2. calls extract_r7d.extract_route(), which is the audited extractor -- unchanged;
    3. reports span, engaged duty, and whether the three fields the V158 scorer needs
       (`cc_lat`, `cs_v`, `cs_rate`) are actually present.

Step 3 is the point: it fails LOUDLY at extract time if the cache cannot be scored, rather than
leaving the operator to find out after the drive is over.
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
_top = _os.path.dirname(_roots[0]) if _roots else _os.path.dirname(_here)
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
for _x in _p:
    if _x not in _sys.path:
        _sys.path.insert(0, _x)
# --------------------------------------------------------------------------
import argparse
import sys
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as R7D                                                   # noqa: E402
import decode_v84_probe_r6d as D                                            # noqa: E402

SCORER_FIELDS = ("cc_lat", "cs_v", "cs_rate")


def register(route, prefix, nseg, build, wire_scale=None, wire_source=None):
    D.ROUTES[route] = (prefix, nseg, f"analysis-2020accord/_scratch/cache/r{route}",
                       f"r{route}s", f"r{route}", build)
    if hasattr(R7D, "ROUTE_DEF"):
        R7D.ROUTE_DEF[route] = D.ROUTES[route]
    if wire_scale is not None:
        R7D.WIRE_SCALE[route] = wire_scale
    if wire_source is not None:
        R7D.WIRE_SOURCE[route] = wire_source
    pm = getattr(R7D, "PROBE_MEANING", None)
    if isinstance(pm, dict) and route not in pm and "7d" in pm:
        pm[route] = pm["7d"]


def report(route):
    f = ROOT / "analysis-2020accord" / "_scratch" / "cache" / f"r{route}" / f"r{route}.npz"
    if not f.exists():
        print(f"  ⛔ no cache written at {f}")
        return False
    z = dict(np.load(f, allow_pickle=True))
    print(f"\n  r{route}: {f.stat().st_size / 1e6:.0f} MB, {len(z)} fields")
    if "t" in z:
        t = np.asarray(z["t"]).astype(float)
        if len(t) > 1:
            print(f"    span {t[-1] - t[0]:.1f} s   n={len(t)}")
    if "cc_lat" in z:
        lat = np.asarray(z["cc_lat"]).astype(float)
        print(f"    engaged duty {np.mean(lat > 0.5):.4f}")

    missing = [k for k in SCORER_FIELDS if k not in z]
    if missing:
        print(f"    ⛔ MISSING {missing} -- score_v158_creep.py CANNOT run on this cache.")
        return False
    print(f"    ✅ {list(SCORER_FIELDS)} all present -- scoreable")

    # creep-window feasibility, so a short drive is caught NOW and not after the fact
    lat = np.asarray(z["cc_lat"]).astype(float)
    v = np.asarray(z["cs_v"]).astype(float)
    n = min(len(lat), len(v))
    lat, v = lat[:n], v[:n]
    NW = 256
    ce = cm = 0
    for a in range(0, n - NW, NW // 2):
        s = slice(a, a + NW)
        sp = v[s].mean() * 3.6
        if not (1.0 <= sp < 24.0):
            continue
        if lat[s].mean() > 0.99:
            ce += 1
        elif lat[s].mean() < 0.01:
            cm += 1
    print(f"    creep windows (1-24 km/h): {ce} engaged, {cm} manual")
    if ce < 15 or cm < 15:
        print("    ⛔ NOT SCOREABLE -- need >=15 of EACH. Re-drive: same low-speed loop, engaged")
        print("       AND manual, alternating several times so the episode bootstrap has episodes.")
        return False
    print("    ✅ enough creep windows in both arms")
    return True


def main():
    ap = argparse.ArgumentParser(description="Cache one route and verify it is scoreable.")
    ap.add_argument("--route", required=True, help="short id, e.g. 82 (cache becomes r82)")
    ap.add_argument("--prefix", required=True, help="rlog dongle_route prefix")
    ap.add_argument("--segments", type=int, required=True)
    ap.add_argument("--build", required=True, help="e.g. V158")
    ap.add_argument("--wire-scale", type=float, default=None)
    ap.add_argument("--wire-source", default=None)
    a = ap.parse_args()

    print(f"\n{'=' * 88}\n  extracting route {a.route}: {a.segments} segments, build {a.build}"
          f"\n  {a.prefix}\n{'=' * 88}", flush=True)
    register(a.route, a.prefix, a.segments, a.build, a.wire_scale, a.wire_source)
    R7D.extract_route(a.route)
    ok = report(a.route)
    print(f"\n  next: python rlog-tools/score/score_v158_creep.py --null r{a.route}"
          f"   (must span 1.0)")
    print(f"        python rlog-tools/score/score_v158_creep.py r{a.route}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
