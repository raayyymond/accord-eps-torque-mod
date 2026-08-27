"""V850 jarl-to-target finder v2 — corrected encoding.

Encoding derived empirically from known instructions:
  jarl reg, disp22:
    hw1 bits 15..11 = 0b11111  (top mask: hw1 & 0xF800 == 0xF800)
    hw1 bits 10..6  = link reg code (for lp=r31, this is 0b11110)
    hw1 bits 5..0   = high 6 bits of disp22 (signed)
    hw2            = low 16 bits of disp22
    target = PC + sign_extend_22(disp_combined)

For our purpose: find every instance where this decodes to target=0xC538.
"""
from __future__ import annotations

from pathlib import Path
import struct
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
DATA = FW.read_bytes()


def find_jarl_to(target: int) -> list[tuple[int, int]]:
    """Find all 4-byte aligned instructions where jarl disp22 = target.
    Returns list of (pc, link_reg_code)."""
    hits = []
    code_ranges = [(0x24, 0xEF72), (0x14810, 0x86242)]
    for code_lo, code_hi in code_ranges:
        for pc in range(code_lo, code_hi - 3, 2):
            disp = target - pc
            if disp & 1:
                continue
            if disp < -(1 << 21) or disp >= (1 << 21):
                continue
            disp22 = disp & 0x3FFFFF  # 22-bit two's complement
            high6 = (disp22 >> 16) & 0x3F
            low16 = disp22 & 0xFFFF

            b0 = DATA[pc]
            b1 = DATA[pc + 1]
            b2 = DATA[pc + 2]
            b3 = DATA[pc + 3]
            hw1 = b0 | (b1 << 8)
            hw2 = b2 | (b3 << 8)

            # hw1 high 5 bits must be 0b11111
            if (hw1 & 0xF800) != 0xF800:
                continue
            if (hw1 & 0x3F) != high6:
                continue
            if hw2 != low16:
                continue

            link_reg_code = (hw1 >> 6) & 0x1F
            hits.append((pc, link_reg_code))
    return hits


def find_jr_to(target: int) -> list[int]:
    """Find jr (no link) targets. Same disp encoding but no link reg.
    jr disp22 encoding: hw1 bits 15..11 = 0b11110, bits 10..6 = 0, bits 5..0 = high6 of disp.
    Actually JR is essentially "jarl r0, disp" — so reg-code field will be 0.
    """
    hits = []
    code_ranges = [(0x24, 0xEF72), (0x14810, 0x86242)]
    for code_lo, code_hi in code_ranges:
        for pc in range(code_lo, code_hi - 3, 2):
            disp = target - pc
            if disp & 1:
                continue
            if disp < -(1 << 21) or disp >= (1 << 21):
                continue
            disp22 = disp & 0x3FFFFF
            high6 = (disp22 >> 16) & 0x3F
            low16 = disp22 & 0xFFFF

            b0 = DATA[pc]; b1 = DATA[pc + 1]
            b2 = DATA[pc + 2]; b3 = DATA[pc + 3]
            hw1 = b0 | (b1 << 8)
            hw2 = b2 | (b3 << 8)

            # jr pattern: 0b11110_00000_DDDDDD
            if (hw1 & 0xFFC0) != 0xF000:
                continue
            if (hw1 & 0x3F) != high6:
                continue
            if hw2 != low16:
                continue
            hits.append(pc)
    return hits


def find_u32_const(target: int) -> list[int]:
    """4-byte aligned u32 equal to target."""
    hits = []
    for off in range(0, len(DATA) - 3, 4):
        if struct.unpack_from("<I", DATA, off)[0] == target:
            hits.append(off)
    return hits


def main():
    for target_name, target in [("SID-lookup-fn-entry 0xC538", 0xC538),
                                  ("0xC534 (preceding jr)", 0xC534),
                                  ("0xC576 (next likely fn entry)", 0xC576),
                                  ("0xC53A (off-by-one)", 0xC53A)]:
        print(f"=== Searching for branches to {target_name} ===")
        jarls = find_jarl_to(target)
        jrs = find_jr_to(target)
        consts = find_u32_const(target)
        print(f"  jarl: {len(jarls)} hits")
        for pc, link in jarls[:20]:
            print(f"    0x{pc:06X}  jarl, link_reg_code=0x{link:02X}")
        print(f"  jr:   {len(jrs)} hits")
        for pc in jrs[:20]:
            print(f"    0x{pc:06X}  jr")
        print(f"  u32 const: {len(consts)} hits")
        for off in consts[:20]:
            print(f"    0x{off:06X}")
        print()


if __name__ == "__main__":
    main()
