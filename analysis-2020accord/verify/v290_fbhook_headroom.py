#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""V290 feedback-operand hook, part 2 (agent `fbhook`, 2026-09-09):
   (1) the ACTUAL max magnitude of the feedback operand r26 from the wire, by running Honda's own
       byte-exact fb-filter mirror on the measured 0x18F rate stream of the two V289 routes;
   (2) int32 headroom of a V289-style Q14 biquad on that operand, with and without a pre-shift;
   (3) RAM context around the candidate free run (what its NEIGHBOURS are, and the gp-0x6AB0 trap).
"""
import os
import struct
import numpy as np
from pathlib import Path

KIT = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
FWROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                             "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
V289 = (FWROOT / "analysis-2020accord" /
        ("_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6"
         "-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"))
img = V289.read_bytes()
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
FB_A, FB_B, FB_CLAMP = u16(0xC63E8), u16(0xC63EA), u16(0xC62E6)
V282_A, V282_B = 923, 1560
print("V289 fb pole: a=%d b=%d ; clamp cal 0xC62E6 = %d" % (FB_A, FB_B, FB_CLAMP))
print("V282 fb pole: a=%d b=%d\n" % (V282_A, V282_B))


def sar(v, n):
    return v >> n if v >= 0 else -((-v + (1 << n) - 1) >> n) if False else (v >> n)


def fb_mirror(x, a, b, clamp):
    """Honda's 0x28F86-0x28FBE, byte-exact. x = int array of gp-0x6a56 raw counts.
       s_new = (a*s >> 10) + (b*x >> 10) ;  r26 = clamp(s + s_new, +-clamp) ; s := s_new"""
    s = 0
    out = np.empty(len(x), dtype=np.int64)
    pre = np.empty(len(x), dtype=np.int64)
    for i, xi in enumerate(x):
        s_new = (a * s >> 10) + (b * int(xi) >> 10)     # sar: python >> on ints IS arithmetic floor
        raw = s + s_new
        pre[i] = raw
        out[i] = max(-clamp, min(clamp, raw))
        s = s_new
    return out, pre


rows = []
for key in ("r62_v289", "r63_v289"):
    p = KIT / "analysis-2020accord/_scratch/cache" / key / (key + ".npz")
    if not p.exists():
        print("MISSING %s" % p)
        continue
    d = np.load(p, allow_pickle=True)
    for fld in ("rate_f", "rate_c"):
        if fld not in d:
            continue
        v = np.asarray(d[fld], dtype=np.float64)
        v = v[np.isfinite(v)]
        print("%s  %-7s n=%7d  min=%10.3f  max=%10.3f  p99.9|.|=%9.3f"
              % (key, fld, len(v), v.min(), v.max(), np.percentile(np.abs(v), 99.9)))
    rows.append((key, d))

print("\n--- gp-0x6a56 in RAW COUNTS from 0x18F (record: 0x18F[2:3] = -gp-0x6a56, 10x finer than 0x14A) ---")
for key, d in rows:
    rf = np.asarray(d["rate_f"], dtype=np.float64)
    rf = rf[np.isfinite(rf)]
    # opendbc STEER_ANGLE_RATE on 0x18F is deg/s; the record says 8 raw counts per deg/s on gp-0x6a56
    x = np.round(-rf * 8.0).astype(np.int64)
    x = np.clip(x, -12000, 12000)          # Honda's own input guard at 0x28F50-58
    print("%s  |x| max = %6d raw counts (%.1f deg/s)   p99.99 = %6d"
          % (key, np.abs(x).max(), np.abs(x).max() / 8.0, int(np.percentile(np.abs(x), 99.99))))
    for tag, (a, b) in (("V282 16.5Hz", (V282_A, V282_B)), ("V289 25Hz", (FB_A, FB_B))):
        r26, pre = fb_mirror(x, a, b, FB_CLAMP)
        nclip = int((np.abs(pre) > FB_CLAMP).sum())
        print("    %-11s  max|r26| post-clamp = %6d   max|pre-clamp| = %8d   ticks at the rail = %d / %d (%.4f %%)"
              % (tag, int(np.abs(r26).max()), int(np.abs(pre).max()), nclip, len(x),
                 100.0 * nclip / max(1, len(x))))

# ---------------------------------------------------------------- headroom
print("\n" + "=" * 100)
print("INT32 HEADROOM of a V289-style Q14 TDF-II notch (b0=16048, b1=a1=-31842, b2=16048, a2=15712)")
B0, B1, B2, A1, A2 = 16048, -31842, 16048, -31842, 15712
CMAX = max(abs(B0), abs(B1), abs(B2), abs(A1), abs(A2))
INT32 = 2 ** 31
for label, xmax in (("V289's own operand S (clamp 0xC61BE)", 15360),
                    ("r26 at the fb clamp 0xC62E6 (V289 value)", FB_CLAMP),
                    ("r26 pre-shifted >>1", FB_CLAMP >> 1),
                    ("r26 pre-shifted >>2", FB_CLAMP >> 2),
                    ("r26 pre-shifted >>3", FB_CLAMP >> 3)):
    bound = CMAX * xmax * 4          # the design's own conservative 4-term bound
    print("  %-42s xmax=%6d  |acc|<= %12d   %s  (margin x%.2f)"
          % (label, xmax, bound, "OK " if bound < INT32 else "OVERFLOW", INT32 / bound))
print("  single product |b1*x| at xmax=%d : %d  (%s)"
      % (FB_CLAMP, abs(B1) * FB_CLAMP, "fits" if abs(B1) * FB_CLAMP < INT32 else "OVERFLOWS"))

print("\n  Q12 coefficient alternative (coeffs >>2, a0 = 2^12):")
for label, xmax in (("r26 unshifted", FB_CLAMP),):
    bound = (CMAX >> 2) * xmax * 4
    print("  %-42s xmax=%6d  |acc|<= %12d   %s  (margin x%.2f)"
          % (label, xmax, bound, "OK " if bound < INT32 else "OVERFLOW", INT32 / bound))

# ---------------------------------------------------------------- RAM context
print("\n" + "=" * 100)
print("RAM CONTEXT around the candidate run, and the gp-0x6AB0 trap")
GP = 0xFEDF8000
MAP = lambda addr: 0x86260 + (addr - 0xFEDF11B0)
print("  boot (.data) image around gp-0x6D74..gp-0x6D2D  (32 bytes either side):")
for m in range(0x6D94, 0x6D0C, -4):
    a = GP - m
    mark = "  <-- candidate" if 0x6D2D <= m <= 0x6D74 else ""
    print("    gp-0x%04X  flash 0x%06X = 0x%08X%s" % (m, MAP(a), struct.unpack_from("<I", img, MAP(a))[0], mark))
print("\n  the gp-0x6AB0 trap (zero gp-relative hits, but NON-ZERO boot data):")
for m in range(0x6AC0, 0x6A9C, -4):
    a = GP - m
    print("    gp-0x%04X  flash 0x%06X = 0x%08X" % (m, MAP(a), struct.unpack_from("<I", img, MAP(a))[0]))
