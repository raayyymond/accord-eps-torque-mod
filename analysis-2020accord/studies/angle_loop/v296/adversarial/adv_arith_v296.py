#!/usr/bin/env python
"""
ADVERSARY ARITHMETIC - V296 (ANGLE LOOP C3-rev2).

My brief: re-derive the delivered surface of the BUILT V296 image from scratch and try
to make it FAIL. This script is READ-ONLY. It assembles nothing, relinks nothing, writes
no image/cave/rwd. It only parses bytes that already exist on disk.

DISPOSITIVE FACT (checked by the caller, re-checked here): there is NO V296 built image,
no V296 .rwd and no build_v296_tva.py. So "re-derive the delivered surface from the BUILT
image" has no bytes to read. The only "flight" cave bytes that exist in the repo are
c3b_cave_C3B-P.hex, which the design itself (and two refuters) flag as a KNOWN DEFECT:
spliced +2 B by add_opskip WITHOUT relinking, so the G-table pointer and the freeze-exit
jr are stale. This script confirms that defect FROM THE BYTES (not from the claim), which
is exactly the arithmetic finding that forces "do not flash" on anything built from it.

V850E2 facts used (little-endian):
  mov imm32,reg1  = 6 B, hw1>>5 == 0x31, reg1 = hw1 & 0x1F, imm32 = next 4 B LE.
  jr  disp22      = 4 B, (hw1 & 0xFFC0) == 0x0780, disp = sext22( (hw1&0x3F)<<16 | hw2 ).
                    (verified against the design's own example jr 0x29A5C->0x2A164 = 80 07 08 07)
"""
import hashlib, sys, os

REV2B = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop\c3\rev2B"
FW = r"C:\Users\dudei\Desktop\Projects\accord-firmwares"
CAVE_BASE = 0xC4C00
TABLE_LEN = 42  # design 1.2: "240 B flight = 198 code + 42 table; 238 B score cave"

def load_hex(name):
    with open(os.path.join(REV2B, name)) as f:
        toks = f.read().split()
    return bytes(int(t, 16) for t in toks)

def le(b, off, n):
    return int.from_bytes(b[off:off+n], "little")

def sext(v, bits):
    s = 1 << (bits - 1)
    return (v ^ s) - s

def find_mov_imm32(b):
    """All (offset, reg, imm32) for `mov imm32,reg1`."""
    out = []
    i = 0
    while i + 6 <= len(b):
        hw1 = le(b, i, 2)
        if (hw1 >> 5) == 0x31:
            out.append((i, hw1 & 0x1F, le(b, i+2, 4)))
        i += 2
    return out

def find_jr(b):
    """All (offset, target_abs) for JR disp22, PC = CAVE_BASE+offset."""
    out = []
    i = 0
    while i + 4 <= len(b):
        hw1 = le(b, i, 2)
        if (hw1 & 0xFFC0) == 0x0780:
            hw2 = le(b, i+2, 2)
            disp = sext(((hw1 & 0x3F) << 16) | hw2, 22)
            out.append((i, (CAVE_BASE + i + disp) & 0xFFFFFFFF))
        i += 2
    return out

def diff_regions(a, c):
    """Report the first contiguous region where a and c diverge (prefix/suffix aligned)."""
    p = 0
    while p < min(len(a), len(c)) and a[p] == c[p]:
        p += 1
    sa, sc = len(a), len(c)
    while sa > p and sc > p and a[sa-1] == c[sc-1]:
        sa -= 1; sc -= 1
    return p, a[p:sa], c[p:sc]

def main():
    print("=" * 78)
    print("ADVERSARY ARITHMETIC - V296 - read-only byte confirmation")
    print("=" * 78)

    # ---- 0. the dispositive fact: no built image -----------------------------
    img_dir = os.path.join(FW, "analysis-2020accord")
    rwd_dir = os.path.join(FW, "flashing-2020accord", "rwd")
    imgs = [f for f in os.listdir(img_dir) if "v296" in f.lower()] if os.path.isdir(img_dir) else []
    rwds = [f for f in os.listdir(rwd_dir) if "v296" in f.lower().replace(",", "")] if os.path.isdir(rwd_dir) else []
    script = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\builds\v108_plus\build_v296_tva.py"
    print("\n[0] DISPOSITIVE: does a BUILT V296 image exist to attack?")
    print(f"    v296 plain images : {imgs or 'NONE'}")
    print(f"    v296 .rwd         : {rwds or 'NONE'}")
    print(f"    build_v296_tva.py : {'present' if os.path.exists(script) else 'NONE'}")
    print("    => No built image. 'Re-derive the delivered surface from the BUILT image'")
    print("       has no bytes. Target of the pass does not exist.")

    # ---- 1. the only flight bytes that exist: the KNOWN-DEFECT cave ----------
    flight = load_hex("c3b_cave_C3B-P.hex")
    score  = load_hex("c3b_cave_C3B-P_score.hex")
    fsha = hashlib.sha256(flight).hexdigest()
    ssha = hashlib.sha256(score).hexdigest()
    print("\n[1] The only 'flight' cave bytes in the repo (c3b_cave_C3B-P.hex):")
    print(f"    flight len   = {len(flight)} B   byte-sha256 = {fsha[:12]}  (brief: 240 B / 9a10cdc4ec75)")
    print(f"    score  len   = {len(score)} B   byte-sha256 = {ssha[:12]}")
    print(f"    brief match  = {len(flight)==240 and fsha.startswith('9a10cdc4ec75')}")

    # ---- 2. locate the unrelinked +2 splice ----------------------------------
    off, fa, sc = diff_regions(flight, score)
    print("\n[2] flight-vs-score diff (the op-skip splice):")
    print(f"    first divergence at cave offset 0x{off:X} (abs 0x{CAVE_BASE+off:X})")
    print(f"    flight bytes here : {fa.hex(' ')}  ({len(fa)} B)")
    print(f"    score  bytes here : {sc.hex(' ')}  ({len(sc)} B)")
    print(f"    net length delta  : flight - score = {len(flight)-len(score):+d} B")
    print("    => everything at/after this offset in flight sits +2 B vs where it was linked.")

    # ---- 3. FINDING A1: G-table base pointer is stale (2 B short) -------------
    fmov = find_mov_imm32(flight)
    smov = find_mov_imm32(score)
    # the G-table pointer is the mov imm32 whose value lands in the cave (0xC4Cxx)
    ftab = [(o, r, v) for (o, r, v) in fmov if CAVE_BASE <= v < CAVE_BASE + 0x100]
    stab = [(o, r, v) for (o, r, v) in smov if CAVE_BASE <= v < CAVE_BASE + 0x100]
    f_code_len = len(flight) - TABLE_LEN
    s_code_len = len(score) - TABLE_LEN
    f_table_abs = CAVE_BASE + f_code_len
    s_table_abs = CAVE_BASE + s_code_len
    print("\n[3] FINDING A1 - G-table base pointer vs where the table actually is:")
    print(f"    flight `mov imm32,rN` into cave : {[(hex(o),f'r{r}',hex(v)) for o,r,v in ftab]}")
    print(f"    score  `mov imm32,rN` into cave : {[(hex(o),f'r{r}',hex(v)) for o,r,v in stab]}")
    print(f"    flight: code_len = {f_code_len} B -> table ACTUALLY begins at 0x{f_table_abs:X}")
    print(f"    score : code_len = {s_code_len} B -> table ACTUALLY begins at 0x{s_table_abs:X}")
    if ftab and stab:
        fp = ftab[0][2]; spv = stab[0][2]
        print(f"    flight pointer = 0x{fp:X} ; flight table at 0x{f_table_abs:X} ; delta = {f_table_abs-fp:+d} B")
        print(f"    score  pointer = 0x{spv:X} ; score  table at 0x{s_table_abs:X} ; delta = {s_table_abs-spv:+d} B")
        a1 = (fp == f_table_abs)
        print(f"    => A1 DEFECT CONFIRMED FROM BYTES: {not a1}  "
              f"(flight pointer is {f_table_abs-fp:+d} B off; score pointer is exact)")
        # show the two table bytes the flight cave would MISREAD as table[0..1]
        misread = flight[fp-CAVE_BASE: fp-CAVE_BASE+2]
        print(f"       flight reads table[0] from 0x{fp:X} = last 2 CODE bytes {misread.hex(' ')} "
              f"(not table[0] {flight[f_code_len:f_code_len+2].hex(' ')}); every G entry shifts -2 B.")

    # ---- 4. FINDING A2: freeze-exit jr lands 2 B past 0x29D7E ----------------
    fjr = find_jr(flight)
    sjr = find_jr(score)
    print("\n[4] FINDING A2 - jr exit targets (design 1.2: freeze jr->0x29D7E, op-skip jr->0x2A164):")
    print(f"    flight JRs (off, target): {[(hex(o),hex(t)) for o,t in fjr]}")
    print(f"    score  JRs (off, target): {[(hex(o),hex(t)) for o,t in sjr]}")
    ftargs = {t for _, t in fjr}
    print(f"    freeze target 0x29D7E present in flight? {0x29D7E in ftargs}  "
          f"(stale would be 0x29D80: present? {0x29D80 in ftargs})")
    print(f"    op-skip target 0x2A164 present in flight? {0x2A164 in ftargs}  "
          f"(stale would be 0x2A166: present? {0x2A166 in ftargs})")

    print("\n" + "=" * 78)
    print("VERDICT INPUT: no built image exists; the sole flight-cave bytes are the")
    print("known-defective c3b_cave_C3B-P.hex. Nothing is fit to flash.  -> DO_NOT_FLASH")
    print("=" * 78)

if __name__ == "__main__":
    main()
