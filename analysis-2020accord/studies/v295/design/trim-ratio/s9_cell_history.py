# -*- coding: utf-8 -*-
"""s9_cell_history.py -- the on-image record of the cells this lens touches, byte-read (LE) from every
_*_plain_image.bin under ACCORD_FIRMWARE_ROOT/analysis-2020accord: 0xC63EA (fb-lag gain b), 0xC63E8 (pole a),
0xC62E6 (fb clamp C), 0x29D76 (shl imm5), 0x28FA4 (operand opcode), Kp record Y at the live selector 7.
Prints each distinct value set and the images that carry it.  Read-only."""
import glob
import os
from collections import defaultdict

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
files = sorted(glob.glob(os.path.join(ROOT, "analysis-2020accord", "_*_plain_image.bin")))


def u16(b, a):
    return int.from_bytes(b[a:a + 2], "little")


def s16(b, a):
    return int.from_bytes(b[a:a + 2], "little", signed=True)


def kp(b):
    r = int.from_bytes(b[0xCB994 + 28:0xCB994 + 32], "little")
    n = u16(b, r)
    return tuple(u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)) if 0 < n < 16 else None


groups = defaultdict(list)
for f in files:
    b = open(f, "rb").read()
    if len(b) < 0xD0000:
        continue
    key = (u16(b, 0xC63EA), s16(b, 0xC63E8), u16(b, 0xC62E6), u16(b, 0x29D76) & 0x1F,
           {0x0E: "sum", 0x0C: "diff"}.get((u16(b, 0x28FA4) >> 5) & 0x3F, "?"), kp(b))
    groups[key].append(os.path.basename(f).split("_")[1] if "_" in os.path.basename(f) else os.path.basename(f))
print("%d images read" % len(files))
print("%-6s %-6s %-6s %-4s %-5s %-32s %s" % ("b", "a", "C", "shl", "op", "Kp Y (sel 7)", "images"))
for k, v in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
    print("%-6d %-6d %-6d %-4d %-5s %-32s %d: %s" % (k[0], k[1], k[2], k[3], k[4], str(k[5]), len(v),
                                                     ", ".join(v[:12]) + (" ..." if len(v) > 12 else "")))
