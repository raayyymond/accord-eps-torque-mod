#!/usr/bin/env python3
"""V70 -- exhaustive writer/reader census for gp-0x683c and gp-0x6806, four independent methods.

Load-bearing question: V69 reverts the gate at 0x3AA96 (0xFB -> 0xC5) so the r24 arm at 0xC6446 is
selected by `gp-0x683c != 0` again. If gp-0x683c really has ZERO writers, that arm is structurally
unreachable and V69's r24 gain falls through to the mode-10 LERP surface at every tick.

A null result is the dangerous one, so this runs FOUR methods (see
.claude/agent-memory/firmware-codepath-tracer/reference_v850e2_extended_disp23_encoding_solved.md):
  1. 4-byte disp16 gp-relative scan, per-opcode displacement rules, store-zero INCLUDED
  2. 6-byte disp23 extended-form gp-relative scan (hw2 carries disp[6:0], hw3 carries disp[22:7])
  3. LE32 absolute-address literal scan (catches `mov imm32,reg` + register-indirect)
  4. movhi/movea immediate-pair scan for the absolute address

Usage:  python studies/sessions/v70/v70_gp683c_writer_census.py
"""
import struct
import sys
from pathlib import Path

GP = 0xFEDF8000
R_GP = 4  # gp == r4

ROOT = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMAGES = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "v62": ROOT / "_v62_plain_image.bin",
    "v67": ROOT / "_v67_plain_image.bin",
    "v68": ROOT / "_v68_plain_image.bin",
    "v69": ROOT / "_v69_plain_image.bin",
}
SCAN_LO, SCAN_HI = 0x00000, 0x100000  # whole image: bootloader 0-0xFFFF included on purpose

# op -> (mnemonic, is_store, how the displacement is recovered from hw1/hw2)
OPS = {
    0x38: ("ld.b", False), 0x39: ("ld.h/ld.w", False),
    0x3A: ("st.b", True), 0x3B: ("st.h/st.w", True),
    0x3C: ("ld.bu", False), 0x3D: ("ld.bu", False),
    0x3F: ("ld.hu", False),
}


def disp16_of(op, hw1, hw2):
    """Per-opcode displacement recovery for the 4-byte gp-relative form."""
    if op in (0x38, 0x3A):
        return hw2
    if op in (0x39, 0x3B):
        return hw2 & 0xFFFE if (hw2 & 1) else hw2
    if op in (0x3C, 0x3D):
        return (hw2 & 0xFFFE) | ((hw1 >> 5) & 1)   # LSB lives in hw1 bit 5
    if op == 0x3F:
        return hw2 & 0xFFFE
    return None


def scan_disp16(buf, target_disp_neg):
    """Method 1. Every 4-byte gp-relative access to gp-target_disp_neg."""
    want = (0x10000 - target_disp_neg) & 0xFFFF
    hits = []
    for a in range(SCAN_LO, min(SCAN_HI, len(buf)) - 4, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if (hw1 & 0x1F) != R_GP:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in OPS:
            continue
        reg2 = hw1 >> 11
        mnem, is_store = OPS[op]
        # reg2 == 0 is the ESCAPE to the 6-byte form for LOADS only; for STORES it is `st r0` (= 0).
        if reg2 == 0 and not is_store:
            continue
        hw2 = struct.unpack_from("<H", buf, a + 2)[0]
        if op == 0x39:
            mnem = "ld.w" if (hw2 & 1) else "ld.h"
        if op == 0x3B:
            mnem = "st.w" if (hw2 & 1) else "st.h"
        if disp16_of(op, hw1, hw2) == want:
            hits.append((a, mnem, reg2, is_store, "disp16"))
    return hits


def scan_disp23(buf, target_disp_neg):
    """Method 2. Every 6-byte extended-displacement gp-relative access."""
    want = -target_disp_neg
    hits = []
    for a in range(SCAN_LO, min(SCAN_HI, len(buf)) - 6, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if (hw1 & 0x1F) != R_GP or (hw1 >> 11) != 0:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in OPS:
            continue
        hw2, hw3 = struct.unpack_from("<HH", buf, a + 2)
        disp = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
        if disp & 0x400000:
            disp -= 0x800000
        if disp != want:
            continue
        reg3 = hw2 >> 11
        subop = hw2 & 0xF
        mnem, is_store = OPS[op]
        hits.append((a, f"{mnem}(ext,sub{subop})", reg3, is_store, "disp23"))
    return hits


def scan_le32_literal(buf, abs_addr):
    """Method 3. LE32 literal of the absolute address anywhere in the image."""
    pat = struct.pack("<I", abs_addr)
    out, i = [], buf.find(pat)
    while i >= 0:
        out.append(i)
        i = buf.find(pat, i + 1)
    return out


def scan_movhi_movea(buf, abs_addr):
    """Method 4. movhi hi16 / movea lo16 immediate pair that would materialise abs_addr."""
    lo = abs_addr & 0xFFFF
    hi = (abs_addr >> 16) & 0xFFFF
    if lo & 0x8000:                       # movea sign-extends, so movhi must pre-compensate
        hi = (hi + 1) & 0xFFFF
    hits = []
    for a in range(SCAN_LO, min(SCAN_HI, len(buf)) - 4, 2):
        if struct.unpack_from("<H", buf, a + 2)[0] != hi:
            continue
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if ((hw1 >> 5) & 0x3F) != 0x32:   # movhi
            continue
        # look for a movea with the matching low half within the next 24 bytes
        for b in range(a + 4, min(a + 28, len(buf) - 4), 2):
            hw1b = struct.unpack_from("<H", buf, b)[0]
            if ((hw1b >> 5) & 0x3F) == 0x31 and struct.unpack_from("<H", buf, b + 2)[0] == lo:
                hits.append((a, b))
                break
    return hits


def census(buf, name, disp_neg, label):
    abs_addr = GP - disp_neg
    print(f"\n--- {label}  (gp-0x{disp_neg:04X} = 0x{abs_addr:08X})  image={name}")
    h16 = scan_disp16(buf, disp_neg)
    h23 = scan_disp23(buf, disp_neg)
    lit = scan_le32_literal(buf, abs_addr)
    mhi = scan_movhi_movea(buf, abs_addr)
    all_acc = sorted(h16 + h23)
    writers = [h for h in all_acc if h[3]]
    readers = [h for h in all_acc if not h[3]]
    print(f"    method 1 disp16 : {len(h16)} hit(s)")
    print(f"    method 2 disp23 : {len(h23)} hit(s)")
    print(f"    method 3 LE32   : {len(lit)} literal(s)  {[hex(x) for x in lit[:8]]}")
    print(f"    method 4 movhi  : {len(mhi)} pair(s)     {[(hex(a), hex(b)) for a, b in mhi[:6]]}")
    print(f"    => WRITERS {len(writers)} | READERS {len(readers)}")
    for a, m, r, st, form in all_acc:
        print(f"       0x{a:05X}  {m:16s} r{r:<2d} {'STORE' if st else 'load ':5s} [{form}]")
    return writers, readers


def main():
    imgs = {k: v.read_bytes() for k, v in IMAGES.items()}
    for name in ("stock", "v69"):
        buf = imgs[name]
        w_dead, r_dead = census(buf, name, 0x683C, "gp-0x683c  (V69's gate source, claimed DEAD)")
        w_live, r_live = census(buf, name, 0x6806, "gp-0x6806  (V67/V68's gate source, LKAS engaged)")
        print(f"\n  VERDICT [{name}]: gp-0x683c writers = {len(w_dead)} ;"
              f" gp-0x6806 writers = {len(w_live)}")

    print("\n--- gate instruction bytes at 0x3AA94 (ld.bu -0xNNNN[gp],r15) ---")
    for name, buf in imgs.items():
        raw = buf[0x3AA94:0x3AA98]
        hw1, hw2 = struct.unpack("<HH", raw)
        op = (hw1 >> 5) & 0x3F
        d = disp16_of(op, hw1, hw2)
        print(f"    {name:6s} {raw.hex()}  hw1=0x{hw1:04X} hw2=0x{hw2:04X} op=0x{op:02X} "
              f"reg2=r{hw1 >> 11}  disp=0x{d:04X} => gp-0x{0x10000 - d:04X}")


if __name__ == "__main__":
    sys.exit(main())
