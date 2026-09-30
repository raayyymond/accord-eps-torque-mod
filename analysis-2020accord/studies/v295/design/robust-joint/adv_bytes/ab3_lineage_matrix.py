# -*- coding: utf-8 -*-
"""ab3_lineage_matrix.py -- the fb-former cells and the operand class down EVERY plain image on disk (read from the
IMAGES, not the build scripts): a 0xC63E8, b 0xC63EA, C 0xC62E6, the 0x28FA4 add/subr opcode, the 0x29D76 shl imm,
the live Kp record level, the Kp*b trim-loop product and the high-frequency trim gain (Kp/256)*(8b/1024) that b sets.
ANALYSIS ONLY."""
import glob
import os
import re
import struct

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
imgs = sorted(glob.glob(FW + "*_plain_image.bin")) + [FW + "stock_fw_dump/code.bin"]


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def s16(b, o): return struct.unpack_from("<h", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


rows = {}
for p in imgs:
    b = open(p, "rb").read()
    if len(b) != 0x100000:
        continue
    op = {0xD1C9: "add(sum)", 0xD189: "subr(diff)"}.get(u16(b, 0x28FA4), "?%04x" % u16(b, 0x28FA4))
    hw = u16(b, 0x29D76)
    shl = (hw & 0x1F) if ((hw >> 5) & 0x3F) == 0x16 else None
    kp_rec = u32(b, 0xCB994 + 4 * 7)
    try:
        n = u16(b, kp_rec)
        kpY = [u16(b, kp_rec + 2 + 2 * n + 2 * k) for k in range(n)] if 0 < n < 20 else None
    except Exception:
        kpY = None
    a, bb, C = s16(b, 0xC63E8), u16(b, 0xC63EA), u16(b, 0xC62E6)
    kd_rec = u32(b, 0xCB7D4 + 4 * 7); nk = u16(b, kd_rec)
    kd0 = u16(b, kd_rec + 2 + 2 * nk) if 0 < nk < 20 else 0
    dcl = u16(b, 0xC61B6)
    nm = os.path.basename(p)
    m = re.match(r"(?:SUPERSEDED-DO-NOT-FLASH-)?_?(v\d+[a-z0-9]*)", nm, re.I)
    tag = m.group(1) if m else nm[:20]
    key = (a, bb, C, op, shl, tuple(kpY) if kpY else None, kd0 if dcl else 0)
    rows.setdefault(key, []).append(tag + ("(SUPERSEDED)" if nm.startswith("SUPERSEDED") else ""))

import cmath, math
print("%d images read; distinct (a, b, C, operand, shl, Kp live rec) classes: %d\n" % (len(imgs), len(rows)))
print("%5s %5s %6s %-11s %4s %-26s %-10s %s" % ("a", "b", "C", "operand", "shl", "Kp rec7 Y", "|PID/x|20Hz*", "images"))
for key, tags in sorted(rows.items(), key=lambda kv: kv[1][0]):
    a, bb, C, op, shl, kpY, kd0 = key
    kp0 = kpY[0] if kpY else 0
    import cmath, math
    z1 = cmath.exp(-1j * 2 * math.pi * 20.0 / 1000.0)
    Sx = (bb / 1024.0) / (1 - (a / 1024.0) * z1)
    r26x = (1 - z1) * Sx if op.startswith("subr") else (1 + z1) * Sx
    hf = abs(r26x * (kp0 / 256.0) + (kd0 / 8.0) * (1 - z1) * r26x) if C else 0.0   # |PID out / x| at 20 Hz
    print("%5d %5d %6d %-11s %4s %-26s %-10.2f %s" % (a, bb, C, op, shl, str(list(kpY) if kpY else None)[:26], hf,
                                                     ", ".join(tags[:12]) + (" ...(+%d)" % (len(tags) - 12) if len(tags) > 12 else "")))
z1 = cmath.exp(-1j * 2 * math.pi * 0.02)
print("\n* |PID/x| at 20 Hz = |(Kp/256)*r26/x + (Kd/8)*(1-z^-1)*r26/x|, S counts per x count, exact 1 kHz transfer of the")
print("  fb former (diff: (1-z^-1)S, sum: (1+z^-1)S, S = (b/1024)/(1-(a/1024)z^-1)); Kd counted only when the D clamp != 0;")
print("  zero when C = 0.  Candidate A (a 1011, b 1106, Kp 960, diff, Kd 0): %.3f  (V294 x%.3f)"
      % (abs((1 - z1) * (1106 / 1024.0) / (1 - (1011 / 1024.0) * z1) * 960 / 256.0), 1106 / 567.0))
