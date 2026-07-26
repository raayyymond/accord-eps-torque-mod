"""Find all V850 jarl/jr instructions targeting 0xC538 (the SID-lookup function).

V850 jarl encoding (Format V, 32-bit):
  halfword 1: 0b1111_1110_RRRR_RDDD  (where R = link reg, D = high 5 bits of disp22 (signed))
  Actually consulting Renesas: jarl disp22, reg
    bits: 0b1111_1RRR_RR0d_dddd  iiii_iiii_iiii_iiii
    where r = link reg, d_iiii... = 22-bit signed disp (the H bits at bit 0 = always 0)
  Target = PC + sign_extend(disp22), where disp22 is the 21-bit-shifted-by-1.

V850 jr disp22 encoding (Format V):
  bits: 0b1111_1000_0000_0DDD  iiii_iiii_iiii_iiii
  same disp22 structure, no link reg.

Easier approach: for every aligned 2-byte instruction position, decode and
check if it's a jarl/jr/jal/jmp, compute the target, and report matches.
We'll just brute-force decode all 32-bit jarl/jr encodings.
"""
from __future__ import annotations

from pathlib import Path
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
DATA = FW.read_bytes()


def decode_jr_jarl(addr: int) -> tuple[str, int, int] | None:
    """Try to decode the 4-byte instruction at `addr` as jr/jarl.

    V850E2 jarl: 0b1111_111R_RRRR_DDDDD  iiii_iiii_iiii_iii0  (Format V, 32-bit)
      ^ Halfword 1 = 0xF800..0xFFFF range with specific bit pattern
      Actually: jarl is 0b1111_1110_DDDD_DRRR  iiii_iiii_iiii_iii0
      No — let me consult more carefully.

    Per Renesas V850E2 manual Format V (32-bit, branch w/link):
      JARL disp22, regID
        Encoding: 0b 11110 RRRRR 1_DDDDD  iiii_iiii_iiii_iii0
        Halfword1 bits 15..11 = 0b11110, then 5 bits reg2, then 1 bit '1', then 5 bits high disp
        Halfword2 = 16 low disp bits, LSB always 0
      JR disp22 (Format V variant with reg=r0):
        Encoding: 0b 11110 00000 0_DDDDD  iiii_iiii_iiii_iii0
        Same structure with reg=0 and the '1' bit cleared.

    Actually V850E2 simpler: 32-bit branch is encoded across 2 halfwords (LE
    in storage). Easiest is to compute, for every aligned address, whether
    the byte pattern is consistent with a branch to our target.

    Empirically the rizin disasm shows jarl as something like:
       0x000170:  ffff7e07    jarl 0x14aa4, lp
    where bytes 'ff ff 7e 07' encode (PC=0x170, target=0x14aa4, link=lp).
    Let's compute: disp = 0x14aa4 - 0x170 = 0x14934 = 0b1_0100_1001_0011_0100
    21-bit signed disp shifted left 1 = 0b1_0100_1001_0011_0100 (bit 0 = 0)
    Disp split:  high 5 bits = 0b10100 = 0x14;  low 16 bits = 0x9334
    Halfword1: 0b11110 + LP(=0x1F? or 31) + 1 + 0b10100 = ...
    LP is r31 = 0b11111. So halfword1 binary = 11110_11111_1_10100 = 0xFFF4? But the bytes are 'ff ff'
    LE: halfword1 stored as 'ff ff' = 0xFFFF in value... close to my computation but not exact.

    OK I'll just empirically search: take a known jarl from rizin's disasm,
    compute the byte pattern for our target, and search.
    """
    return None


def find_jarl_to(target: int) -> list[tuple[int, str]]:
    """Brute-force: for every 2-byte-aligned position in code, see if the
    bytes encode a jarl/jr to `target`.

    Strategy: for every position, compute what the bytes WOULD be if it were
    a jarl-to-target, then check if they match.

    From the V850E2 manual Format V (long jump/jarl):
      0b 11110 _ TTTTT _ 1 _ TTTTT     iiii_iiii_iiii_iii0   (JARL)
      0b 11110 _ 00000 _ 0 _ TTTTT     iiii_iiii_iiii_iii0   (JR, JR is jarl r0)
    where TTTTT in halfword1 is the link register (or 00000 for JR).
    Halfword1 in the manual diagram:
       bit 15 14 13 12 11 | 10 9 8 7 6 | 5 | 4 3 2 1 0
                1  1  1  1  0 |  R R R R R | 1 |  d d d d d   (jarl)
                                  ^link reg^             ^high 5 bits of disp
    Halfword2: 16 low bits of disp (disp22 = high5 << 16 | low16, with bit 0 always 0).

    Sign-extend disp22 (21-bit signed because bit 0 always 0) and target = PC + disp22.

    For each candidate address `pc`:
      disp22 = target - pc
      if disp22 not in signed 22-bit range: skip
      disp22 must be even (bit 0 == 0)
      high5 = (disp22 >> 16) & 0x1F
      low16 = disp22 & 0xFFFF
      For JR (reg=0):
        halfword1 = 0b11110_00000_0_DDDDD = (0x1E << 11) | high5
                  = 0xF000 | high5
        That's wrong — 0b11110 << 11 = 0xF000, then bits 10..6=0, bit 5=0, bits 4..0=high5
        halfword1 = 0xF000 | high5    (bit 5 = 0 for JR)
      For JARL (reg=R):
        halfword1 = 0xF000 | (R << 6) | (1 << 5) | high5
                  = 0xF000 | (R << 6) | 0x20 | high5

      halfword2 = low16 & 0xFFFE

    Storage is LE, so bytes at pc are:
      [halfword1 & 0xFF, halfword1 >> 8, halfword2 & 0xFF, halfword2 >> 8]

    Check each 2-byte-aligned position; if matches, record it.
    """
    hits = []
    code_ranges = [(0x24, 0xEF72), (0x14810, 0x86242)]
    for code_lo, code_hi in code_ranges:
        for pc in range(code_lo, code_hi - 3, 2):
            disp = target - pc
            if disp & 1:
                continue
            # signed 22-bit range: [-2^21, 2^21-1] = [-2097152, 2097151]
            if disp < -2097152 or disp > 2097151:
                continue
            disp_unsigned = disp & 0x3FFFFE  # 22 bits, bit 0 clear
            high5 = (disp_unsigned >> 16) & 0x1F
            low16 = disp_unsigned & 0xFFFE

            # Read bytes at pc
            if pc + 4 > len(DATA):
                continue
            b0 = DATA[pc]
            b1 = DATA[pc + 1]
            b2 = DATA[pc + 2]
            b3 = DATA[pc + 3]
            actual_hw1 = b0 | (b1 << 8)
            actual_hw2 = b2 | (b3 << 8)

            if actual_hw2 != low16:
                continue
            # Check halfword1: must have bits 15..11 == 0b11110 (value 0x1E in those bits)
            if (actual_hw1 & 0xF800) != 0xF000:
                continue
            # Extract high5, link_reg, and the '1' marker bit
            actual_high5 = actual_hw1 & 0x1F
            link_reg = (actual_hw1 >> 6) & 0x1F
            jarl_bit = (actual_hw1 >> 5) & 0x1
            if actual_high5 != high5:
                continue

            kind = "jarl" if jarl_bit == 1 else "jr"
            if jarl_bit == 0 and link_reg != 0:
                # JR must have reg=0
                continue
            link_name = f"r{link_reg}" if jarl_bit == 1 else ""
            desc = f"{kind} 0x{target:x}" + (f", {link_name}" if link_name else "")
            hits.append((pc, desc))
    return hits


def find_jmp_indirect_to(target: int) -> list[tuple[int, str]]:
    """V850 jmp [rN] is indirect. We can't find a direct address constant in the
    instruction (the address is in rN). To find indirect calls to `target`,
    we'd need to scan for movhi+movea/mov-imm32 that builds `target` into a
    register, followed by a jmp [rN]. Skip for now."""
    return []


def find_call_via_function_pointer(target: int) -> list[int]:
    """Find every aligned 4-byte u32 in the image equal to `target` — that
    catches function-pointer tables and constant pools."""
    hits = []
    import struct
    for off in range(0, len(DATA) - 3, 4):
        v = struct.unpack_from("<I", DATA, off)[0]
        if v == target:
            hits.append(off)
    return hits


def main():
    target = 0xC538
    print(f"=== Searching for direct jarl/jr to 0x{target:X} (SID-lookup function) ===")
    hits = find_jarl_to(target)
    print(f"  Found {len(hits)} direct branches.")
    for pc, desc in hits[:30]:
        print(f"    0x{pc:06X}: {desc}")

    print()
    print(f"=== Searching for 0x{target:X} as a function-pointer constant ===")
    fp_hits = find_call_via_function_pointer(target)
    print(f"  Found {len(fp_hits)} u32 occurrences.")
    for h in fp_hits[:30]:
        print(f"    0x{h:06X}")

    # Also try with off-by-1, off-by-2 since function entry might actually be at C53A or C534
    for cand in (0xC534, 0xC53A, 0xC542, 0xC576):
        hits = find_jarl_to(cand)
        if hits:
            print()
            print(f"=== Bonus: branches to 0x{cand:X}: {len(hits)} ===")
            for pc, desc in hits[:10]:
                print(f"    0x{pc:06X}: {desc}")


if __name__ == "__main__":
    main()
