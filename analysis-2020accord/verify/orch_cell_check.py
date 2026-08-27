#!/usr/bin/env python3
"""Orchestrator's own byte read of the cells this session's levers turn on.  Images, not scripts."""
import struct
from pathlib import Path

R = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
st = (R / "stock_fw_dump" / "code.bin").read_bytes()
v88 = (R / "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256"
            "_plain_image.bin").read_bytes()

CELLS = [
    (0xC61D4, "0xC61D4 mode-2 static cal"),
    (0xC64C8, "0xC64C8 aggregator mode byte"),
    (0xC64C9, "0xC64C9 blend mux"),
    (0xC63AC, "0xC63AC Path-2 IIR coeff"),
    (0xC63A0, "0xC63A0 Path-2 damper weight"),
    (0xC61F6, "0xC61F6 r24 lane deadzone"),
    (0xC40BC, "0xC40BC friction (V85)"),
    (0xC407E, "0xC407E interlock clamp"),
    (0xC6446, "0xC6446 Lever B arm"),
    (0xC6444, "0xC6444 r26 arm"),
]

print(f"{'cell':34s} {'stock u16':>9} {'s16':>7} {'byte':>5}   {'V88 u16':>8} {'byte':>5}")
for a, label in CELLS:
    su = struct.unpack_from("<H", st, a)[0]
    ss = struct.unpack_from("<h", st, a)[0]
    vu = struct.unpack_from("<H", v88, a)[0]
    print(f"{label:34s} {su:9d} {ss:7d} {st[a]:5d}   {vu:8d} {v88[a]:5d}")

# FactorD's own record, read through the mode pointer array, on THIS car's modes.
PTR_FACTORD = 0xC9DB4
print("\nFactorD records via pointer array 0xC9DB4, this car is TVCA4 => modes 24/26:")
for mode in (10, 24, 25, 26, 27):
    base = struct.unpack_from("<I", st, PTR_FACTORD + 4 * mode)[0]
    if not (0 < base < 0x100000):
        print(f"  mode {mode:2d}: pointer 0x{base:08X} out of range")
        continue
    n = struct.unpack_from("<H", st, base)[0]
    if not (1 <= n <= 16):
        print(f"  mode {mode:2d}: npt {n} implausible at 0x{base:05X}")
        continue
    xs = list(struct.unpack_from(f"<{n}h", st, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", st, base + 2 + 2 * n))
    print(f"  mode {mode:2d}: base 0x{base:05X}  n={n}  X={xs}  Y={ys}")
