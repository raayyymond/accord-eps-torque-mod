#!/usr/bin/env python3
r"""HAS THIS CELL ALREADY BEEN PROBED?  ASK BEFORE DESIGNING A PROBE OR A THRESHOLD.

WHY THIS EXISTS
---------------
Twice in one session the answer to a load-bearing question was already sitting in the cache:

  * the b26 rail-duty question -- r77 (V90) had flown the identical tap at the identical scale;
  * the notch-gate question -- gp-0x6C2C had been probed by V107-V110 (r1b, r1e) and the notch
    lane gp-0x6B86 by V104-V106 (ra4-ra6), while four builds were being designed around them.

Both times the lesson was written down as a note and both times it had to be rediscovered.  A note
is not a check.  This is the check.

WHAT IT DOES
------------
Reads the 427 probe tap (displacement at 0x55DF2) and the packer sar (0x55E10) out of EVERY build
image, matches them to the cached routes via each route's probe_build, and reports -- for a cell
you name -- whether it has ever flown, on which route, at what scale, and CRUCIALLY whether that
route's probe CLIPPED.

    wire = min((|x| * 5) >> sar, 0x3FF)   =>   x = wire * 2^sar / 5
    the probe saturates at |x| = 1023 * 2^sar / 5, and ANY reading at that value is a LOWER BOUND

The clip check is the point.  gp-0x6C2C on r1e looked like a clean answer until the saturation
fraction showed 3.2 % of engaged frames pinned at the rail, against a threshold 7.8x higher.

USAGE
-----
    python analysis-2020accord/verify/probe_census.py              # full census
    python analysis-2020accord/verify/probe_census.py 0x6C2C       # one cell (gp-relative)
"""
import glob
import os
import re
import struct
import sys

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMGDIR = os.path.join(ROOT, "analysis-2020accord")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "_scratch", "cache")

TAP_ADDR, SAR_ADDR = 0x55DF2, 0x55E10
NAMES = {
    0x6B26: "b26 inertia term",
    0x6ADA: "r24 pump-lane mirror",
    0x6ADC: "r26 pump-lane mirror",
    0x6C24: "notch GATE mirror (binary, cannot clip)",
    0x6B86: "notch lane (FUN_000352b4 output)",
    0x6C2C: "DETECTOR INPUT (vs cal 0xC620A = 12800)",
    0x6B98: "FOC integrator",
    0x6B94: "aggregator output",
    0x6B70: "residual",
    0x6BBE: "viscous + DC pedestal",
    0x6B4C: "11-slot assist sum",
    0x67FA: "state gate",
    0x6AF0: "reader #3 output",
    0x6ABC: "(the default V111+ tap)",
    0x6C18: "(the legacy pre-V32 tap)",
}


def images():
    out = {}
    for p in sorted(glob.glob(os.path.join(IMGDIR, "**", "*plain_image.bin"), recursive=True)):
        if "SUPERSEDED" in p:
            continue
        m = re.search(r"_v(\d+[a-z]?)_", os.path.basename(p))
        if not m:
            continue
        b = open(p, "rb").read()
        if len(b) <= SAR_ADDR:
            continue
        tap = struct.unpack_from("<H", b, TAP_ADDR)[0]
        disp = (0x10000 - tap) if tap > 0x8000 else 0
        out["V" + m.group(1).upper()] = (disp, b[SAR_ADDR] & 0x1F)
    return out


def routes():
    try:
        import numpy as np
    except ImportError:
        return {}
    out = {}
    if not os.path.isdir(CACHE):
        return out
    for t in sorted(os.listdir(CACHE)):
        f = os.path.join(CACHE, t, "%s.npz" % t)
        if not os.path.exists(f):
            continue
        try:
            z = np.load(f, allow_pickle=True)
        except Exception:
            continue
        pb = str(np.atleast_1d(z["probe_build"])[0]) if "probe_build" in z.files else "?"
        out[t] = pb
    return out


def clip_stats(tag, sar):
    try:
        import numpy as np
    except ImportError:
        return None
    f = os.path.join(CACHE, tag, "%s.npz" % tag)
    if not os.path.exists(f):
        return None
    z = np.load(f, allow_pickle=True)
    if "ab_mt" not in z.files:
        return None
    mt = np.abs(np.asarray(z["ab_mt"]).astype(float))
    lat = np.asarray(z["cc_lat"]).astype(float) if "cc_lat" in z.files else None
    n = len(mt) if lat is None else min(len(mt), len(lat))
    mt = mt[:n]
    m = (lat[:n] > 0.5) if lat is not None else slice(None)
    x = mt[m]
    if x.size < 100:
        return None
    scale = (1 << sar) / 5.0
    return dict(n=x.size, p50=float(x.mean() * 0 + __import__("numpy").percentile(x, 50)) * scale,
                mx=float(x.max()) * scale, clip=float((x >= 0x3FF).mean()),
                sat=0x3FF * scale)


def main():
    imgs = images()
    rts = routes()
    build2route = {}
    for t, pb in rts.items():
        for b in re.findall(r"V\d+[A-Za-z]?", pb.upper()):
            build2route.setdefault(b, []).append(t)
    want = None
    if len(sys.argv) > 1:
        want = int(sys.argv[1], 16) & 0xFFFF
    by = {}
    for b, (d, s) in imgs.items():
        by.setdefault(d, []).append((b, s))
    print("=" * 96)
    print("  427 PROBE CENSUS -- which cells have already flown, and did the probe CLIP?")
    print("=" * 96)
    for d in sorted(by):
        if want is not None and d != want:
            continue
        blds = by[d]
        flown = [(b, s) for b, s in blds if b in build2route]
        print("\n  gp-0x%04X  %s" % (d, NAMES.get(d, "unknown")))
        print("      builds: %s" % " ".join(b for b, _ in blds[:16]))
        if not flown:
            print("      \U0001f6d1 NEVER FLOWN -- no cached route carries this tap")
            continue
        for b, s in flown:
            for t in build2route[b]:
                st = clip_stats(t, s)
                if st is None:
                    print("      %s / %-4s sar %d   (no usable ab_mt)" % (b, t, s))
                    continue
                warn = ("  \U0001f6d1 CLIPPED on %.1f%% -- max is a LOWER BOUND" % (100 * st["clip"])
                        if st["clip"] > 0.001 else "  (unclipped)")
                print("      %s / %-4s sar %d  n=%6d  p50 %8.0f  max %8.0f  saturates at %8.0f%s"
                      % (b, t, s, st["n"], st["p50"], st["mx"], st["sat"], warn))
    print("\n" + "=" * 96)
    print("  Before designing a probe, or a build that depends on a THRESHOLD, check here first.")
    print("  And read the CLIP column: a censored maximum cannot rule a threshold out.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
