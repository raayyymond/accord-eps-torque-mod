#!/usr/bin/env python3
r"""GENERIC route extractor -- the 427 tap is READ FROM THE IMAGE, never hand-typed.

    python rlog-tools/decode/extract_route_generic.py --check V228
    python rlog-tools/decode/extract_route_generic.py <route_id> <rlog_prefix> <nseg> <build>

WHY THIS EXISTS
---------------
Every drive so far got its own hand-written extractor -- 49 of them, 4 KB to 37 KB, each repeating the
same wrapper with two numbers changed. The two numbers are the CAN-427 tap's SOURCE and SHIFT, and they
are exactly where a per-route file goes wrong, because the kit's own record says:

    "CAN 427 carries a DIFFERENT VARIABLE PER BUILD -- source + shift move on nearly every build
     (V94 gp-0x6b26 sar1 vs V96-99 gp-0x6b70 sar6 = 32x apart). Never pool a 427 percentile across
     routes; decode from the image first."

Hand-typing a tap that moves per build is a standing invitation to mis-scale a whole drive by 32x. So
this file does not accept them as arguments at all: it DERIVES them from the build's own image.

    source displacement : gp - (hw2 at 0x55DF2, decoded the same way can427_source_per_build.py does)
    shift               : byte at 0x55E10, low 5 bits
    wire scale          : 2**shift / 5.0     (sar3 -> 8/5, sar4 -> 16/5, sar1 -> 2/5)

A COPIED DOCSTRING IS A REAL HAZARD HERE. extract_r24.py -- the newest hand-written extractor, for the
route the CAR is on -- still opens "Cache routes 22 and 23" and gives extract_r22_r23.py as its usage,
because it was copied and the header was not updated. That is harmless until someone reads it to learn
which build a route belongs to.

--check <BUILD> prints the tap this build will use and exits, so the tap can be verified BEFORE a drive
rather than discovered wrong afterwards.
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
if _roots:
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
import argparse
import glob
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OFF_SRC, OFF_SHIFT = 0x55DF2, 0x55E10
PACKER_DIV = 5.0                      # fixed in the 427 packer; the 2**shift is the build-dependent part


def firmware_root():
    return os.environ.get("ACCORD_FIRMWARE_ROOT",
                          "C:/Users/dudei/Desktop/Projects/accord-firmwares")


def image_for(build):
    tag = build.lower()
    pats = ["%s/analysis-2020accord/_%s_*plain_image.bin" % (firmware_root(), tag)]
    for p in pats:
        g = [f for f in glob.glob(p) if "SUPERSEDED" not in os.path.basename(f)]
        if g:
            assert len(g) == 1, "%s: %d live images, expected 1" % (build, len(g))
            return g[0]
    raise SystemExit("  no live image for %s under %s" % (build, firmware_root()))


def decode_tap(build):
    """Read the 427 source displacement and shift straight out of the build's image."""
    path = image_for(build)
    b = open(path, "rb").read()
    hw2 = struct.unpack_from("<H", b, OFF_SRC)[0]
    # gp-relative displacement, same decode the verifier uses
    disp = hw2 - 0x10000 if hw2 >= 0x8000 else hw2
    shift = b[OFF_SHIFT] & 0x1F
    return {
        "image": os.path.basename(path),
        "hw2": hw2,
        "disp": disp,
        "gp_off": -disp if disp < 0 else disp,
        "shift": shift,
        "wire_scale": (2.0 ** shift) / PACKER_DIV,
    }


def show(build):
    t = decode_tap(build)
    print("=" * 92)
    print("  CAN-427 TAP FOR %s -- decoded from the image, not typed" % build.upper())
    print("=" * 92)
    print("  image        %s" % t["image"][:70])
    print("  0x%05X hw2   0x%04X  -> gp-0x%04X" % (OFF_SRC, t["hw2"], t["gp_off"]))
    print("  0x%05X shift %d      -> sar %d" % (OFF_SHIFT, t["shift"], t["shift"]))
    print("  wire scale   2**%d / %.0f = %.4f raw counts per wire LSB"
          % (t["shift"], PACKER_DIV, t["wire_scale"]))
    print()
    print("  \u21d2 pass this build tag to the extractor and it will use exactly these values.")
    print("  \u26a0 a 427 percentile from this route may NOT be pooled with a route whose tap differs.")
    return t


def extract(route, prefix, nseg, build):
    t = decode_tap(build)
    show(build)
    import extract_r7d as R7D
    import decode_v84_probe_r6d as D
    cache = "analysis-2020accord/_scratch/cache/r%s" % route
    D.ROUTES[route] = (prefix, nseg, cache, "r%ss" % route, "r%s" % route, build.upper())
    if hasattr(R7D, "ROUTE_DEF"):
        R7D.ROUTE_DEF[route] = D.ROUTES[route]
    R7D.WIRE_SCALE[route] = t["wire_scale"]
    R7D.WIRE_SOURCE[route] = "gp-0x%04X sar%d (%s tap, decoded from image)" % (
        t["gp_off"], t["shift"], build.upper())
    print()
    print("  extracting route %s: %d segments, %s" % (route, nseg, prefix))
    R7D.extract_route(route)
    f = os.path.join("analysis-2020accord", "_scratch", "cache", "r%s" % route, "r%s.npz" % route)
    print("  cache %s: %s" % (f, "WRITTEN" if os.path.exists(f) else "MISSING -- extraction failed"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="BUILD", help="print the 427 tap for a build and exit")
    ap.add_argument("args", nargs="*", help="<route_id> <rlog_prefix> <nseg> <build>")
    a = ap.parse_args()
    if a.check:
        show(a.check)
        raise SystemExit(0)
    if len(a.args) != 4:
        raise SystemExit("  usage: extract_route_generic.py <route_id> <rlog_prefix> <nseg> <build>\n"
                         "     or: extract_route_generic.py --check <BUILD>")
    extract(a.args[0], a.args[1], int(a.args[2]), a.args[3])
