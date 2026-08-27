#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_fault_tables.py -- dump the damping-chain factor tables straight out of the images.

Layout PROVEN from the decompile of FUN_00034350 (stock code.bin), not assumed:

  FactorB  ptr array 0xC9CCC   rec: X@+2,+4,+6,+8   Y@+0xA,+0xC,+0xE,+0x10   (4 pts)
  FactorC  ptr array 0xC9E9C   rec: X@+2,+4,+6,+8   Y@+0xA,+0xC,+0xE,+0x10   (4 pts)
  FactorD  ptr array 0xC9DB4   rec: X@+2..+0xA      Y@+0xC..+0x14            (5 pts)
  FactorE  ptr array 0xC9F84   rec: X@+2,+4,+6,+8   Y@+0xA,+0xC,+0xE,+0x10   (4 pts)
  Ceiling  ptr array 0xC77A0   rec: X@+2,+4         Y@+6,+8                  (2 pts)

Each record's +0 halfword is dumped too (unread by the LERP; likely a point count).
All reads LITTLE-ENDIAN (V850 is LE).
"""
import os, struct, sys

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
A = os.path.join(ROOT, "analysis-2020accord")
IMAGES = {
    "stock": os.path.join(A, "stock_fw_dump", "code.bin"),
    "v74":   os.path.join(A, "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    "v75":   os.path.join(A, "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    "v76":   os.path.join(A, "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"),
}

PTR = {"B": 0xC9CCC, "C": 0xC9E9C, "D": 0xC9DB4, "E": 0xC9F84, "CEIL": 0xC77A0}
NPTS = {"B": 4, "C": 4, "D": 5, "E": 4, "CEIL": 2}


def u16(b, a):
    return b[a] | (b[a + 1] << 8)


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def load(n):
    with open(IMAGES[n], "rb") as f:
        return f.read()


def rec_addr(img, which, mode):
    return u32(img, PTR[which] + mode * 4)


def read_rec(img, which, mode):
    """Return (rec_addr, hdr, X list, Y list) exactly as the LERP indexes them."""
    base = rec_addr(img, which, mode)
    n = NPTS[which]
    hdr = u16(img, base + 0)
    X = [u16(img, base + 2 + 2 * i) for i in range(n)]
    Y = [u16(img, base + 2 + 2 * n + 2 * i) for i in range(n)]
    return base, hdr, X, Y


def dump(modes=(24, 25, 26, 27), whichs=("B", "C", "D", "E", "CEIL"),
         builds=("stock", "v74", "v75")):
    imgs = {b: load(b) for b in builds}
    for which in whichs:
        print("\n" + "=" * 100)
        print("FACTOR %s   ptr array 0x%X   %d points" % (which, PTR[which], NPTS[which]))
        print("=" * 100)
        for mode in modes:
            print("  mode %d:" % mode)
            for b in builds:
                base, hdr, X, Y = read_rec(imgs[b], which, mode)
                mono = all(X[i] < X[i + 1] for i in range(len(X) - 1))
                dups = [i for i in range(len(X) - 1) if X[i] == X[i + 1]]
                print("    %-6s rec=0x%05X hdr=%-5d X=%-34s Y=%-34s  strict_incr=%s%s"
                      % (b, base, hdr, X, Y, mono,
                         "  DUP_AT=%s" % dups if dups else ""))


if __name__ == "__main__":
    modes = tuple(int(x) for x in sys.argv[1].split(",")) if len(sys.argv) > 1 else tuple(range(34))
    dump(modes=modes)
