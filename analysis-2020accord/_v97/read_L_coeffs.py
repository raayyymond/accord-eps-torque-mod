#!/usr/bin/env python3
"""Byte-read the eight candidate FUN_0003b8f6 coefficients ("L") from stock + flown images.

Owner: close-the-sign agent. Study-only; reads bytes, writes nothing to firmware.

tp = 0xBF000. Offsets are computed in code (never by eye) to dodge the
off-by-0x1000 trap that has recurred five times in this kit.
"""
import os
import struct
import sys

TP = 0xBF000
TP_OFFSETS = [0x50D4, 0x50D8, 0x504C, 0x5050, 0x50BC, 0x50D0, 0x50D2, 0x50D6]

ROOT = os.environ.get(
    "ACCORD_FIRMWARE_ROOT",
    r"C:/Users/dudei/Desktop/Projects/accord-firmwares",
)
A = os.path.join(ROOT, "analysis-2020accord")

IMAGES = [
    ("stock", os.path.join(A, "stock_fw_dump", "code.bin")),
    ("v89-era? v90", os.path.join(A, "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin")),
    ("v92", os.path.join(A, "_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4_plain_image.bin")),
    ("v94", os.path.join(A, "_v94_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1_plain_image.bin")),
    ("v96(on car)", os.path.join(A, "_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin")),
]


def load(p):
    with open(p, "rb") as f:
        return f.read()


def decode(buf, addr):
    b0 = buf[addr]
    b1 = buf[addr + 1]
    u16 = struct.unpack_from("<H", buf, addr)[0]
    s16 = struct.unpack_from("<h", buf, addr)[0]
    u32 = struct.unpack_from("<I", buf, addr)[0]
    f32 = struct.unpack_from("<f", buf, addr)[0]
    return b0, b1, u16, s16, u32, f32


def main():
    addrs = [(TP + off, off) for off in TP_OFFSETS]
    print("tp = 0x%X" % TP)
    for addr, off in sorted(addrs, key=lambda t: t[0]):
        print("  tp+0x%04X -> 0x%05X" % (off, addr))
    print()

    imgs = []
    for tag, path in IMAGES:
        if not os.path.exists(path):
            print("MISSING: %s (%s)" % (tag, path), file=sys.stderr)
            continue
        imgs.append((tag, load(path)))

    hdr = "%-9s %-6s %-6s %-8s %-8s %-12s %-14s" % (
        "addr", "b[0]", "b[1]", "u16", "s16", "u32", "f32")
    for addr, off in sorted(addrs, key=lambda t: t[0]):
        print("=== 0x%05X (tp+0x%04X) ===" % (addr, off))
        print("  image        " + hdr)
        for tag, buf in imgs:
            b0, b1, u16, s16, u32, f32 = decode(buf, addr)
            print("  %-12s 0x%05X %-6d %-6d %-8d %-8d %-12d %-14.6g"
                  % (tag, addr, b0, b1, u16, s16, u32, f32))
        print()

    # Dump the surrounding block so the table structure is visible.
    print("=== raw block 0xC4040..0xC40E0, stock vs v96 ===")
    for tag, buf in imgs:
        if tag not in ("stock", "v96(on car)"):
            continue
        print("-- %s" % tag)
        for base in range(0xC4040, 0xC40E0, 16):
            row = " ".join("%02X" % buf[base + i] for i in range(16))
            print("  0x%05X  %s" % (base, row))
    print()

    # halfword view of the same block, which is how a cal table of s16 reads
    print("=== s16 halfword view 0xC4040..0xC40E0 ===")
    print("  addr     " + "  ".join("%-8s" % t for t, _ in imgs))
    for a in range(0xC4040, 0xC40E0, 2):
        vals = [struct.unpack_from("<h", b, a)[0] for _, b in imgs]
        if len(set(vals)) == 1:
            mark = "  "
        else:
            mark = "* "
        print("%s0x%05X  %s" % (mark, a, "  ".join("%-8d" % v for v in vals)))


if __name__ == "__main__":
    main()
