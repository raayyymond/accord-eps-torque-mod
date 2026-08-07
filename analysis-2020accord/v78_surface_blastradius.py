#!/usr/bin/env python3
"""v78_surface_blastradius.py -- which modes' FactorC/E records moved, WHY, and by which build.

v78_surface_tables.py PART 1b reported 18 changed modes for FactorC and FactorE, including five
DISENGAGED modes (0,1,4,10,12), against the build scripts' "the disengaged column stays byte-stock".
This resolves it: no record ALIASING exists, so those five are LEGACY V72/V73 edits carried forward.
"""
import os
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:\Users\dudei\Desktop\Projects\accord-firmwares")) / "analysis-2020accord"
IMGS = {
    "stock": "stock_fw_dump/code.bin",
    "V71a":  "_v71a_plain_image.bin",
    "V72":   "_v72_plain_image.bin",
    "V73":   "_v73_plain_image.bin",
    "V74":   "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75":   "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
}
FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
THIS_CAR = {24: "MANUAL (this car)", 25: "(this car)", 26: "ENGAGED (this car)", 27: "(this car)"}


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    n = u16(b, base)
    return (list(struct.unpack_from(f"<{n}h", b, base + 2)),
            list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n)))


B = {k: (ROOT / v).read_bytes() for k, v in IMGS.items() if (ROOT / v).exists()}
order = list(B)

for name, arr in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
    print("\n" + "=" * 116)
    print(f"{name}  ptr array 0x{arr:X}")
    print("=" * 116)
    seen = {}
    alias = []
    for m in range(34):
        base = u32(B["stock"], arr + 4 * m)
        if base in seen:
            alias.append((m, seen[base]))
        seen[base] = m
    print("  record aliasing across the 34 modes: " +
          (str(alias) if alias else "NONE - every mode has its own record"))
    print(f"\n  {'mode':>4} {'cls':>3} {'record':>9}  " +
          "  ".join(f"{k:^26}" for k in order) + "   first mover")
    for m in range(34):
        base = u32(B["stock"], arr + 4 * m)
        cls = "ENG" if m in ENGAGED else ("dis" if m in DISENGAGED else " ? ")
        ys = []
        first = "-"
        prev = None
        for k in order:
            x, y = rec(B[k], base)
            s = f"X{x[0]},{x[1]} Y{y[0]},{y[1]}"
            ys.append(f"{str(y):>26}")
            if prev is not None and y != prev and first == "-":
                first = k
            prev = y
        note = THIS_CAR.get(m, "")
        print(f"  {m:>4} {cls:>3} 0x{base:05X}  " + "  ".join(ys) + f"   {first:6s} {note}")
