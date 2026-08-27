#!/usr/bin/env python3
"""studies/firmware_scan/scan_gp_accesses.py -- raw-byte census of every gp/tp-relative load and store to a given cell.

This is the REQUIRED SECOND METHOD whenever a reader/writer count or a null result is load-bearing.
`search_instructions` has produced wrong reader/writer sets at least four times in this kit: it scans
only ALREADY-ANALYSED instructions (undercount) and it matches operand SUBSTRINGS, so an address
literal like `jarl 0x00076bd0` collides with `gp-0x6bd0` (over-count).

ENCODINGS COVERED
-----------------
Format VII, 32-bit  (the common one)
    hw1 = [reg2(15:11) | opcode(10:5) | reg1(4:0)]      hw2 = disp16
    opcode 0x38 ld.b   0x39 ld.h/ld.w   0x3A st.b   0x3B st.h/st.w
    * ld.h vs ld.w and st.h vs st.w are selected by hw2 BIT 0 (0 = halfword, 1 = word), so the
      displacement's own bit 0 is forced to 0 -- `hw2 = disp | 1` for the word forms. A scan for the
      bare displacement is BLIND to them. [this is the recorded `hw2 = disp|1` trap]
    * ld.bu / ld.hu (opcode 0x3B / 0x3F with reg2 != 0 semantics on V850E) carry the displacement's
      BIT 0 IN hw1 BIT 5, not in hw2. A naive decode reports false mismatches on a CORRECT build.
      [this is the recorded hw1-bit-5 trap; it cost one session]

Format XIV, 48-bit extended displacement (disp23)
    hw1 = [reg3(15:11) | 000011 11 | reg1(4:0)]-ish, hw2 = disp lower, hw3 = disp upper
    Rather than derive this form from the manual, the scanner brute-forces it: for every 6-byte
    window it reconstructs the 23-bit displacement from the two trailing halfwords under both
    documented packings and reports any hit with reg1 == gp. Every hit is then re-checked for
    instruction-boundary plausibility by the caller -- A BYTE SCAN IS NOT CONFIRMATION.

USAGE
    python studies/firmware_scan/scan_gp_accesses.py 0x683c 0x6446 ...        # gp-relative cell offsets (positive number
                                                        # means gp-0xNNNN, the kit's convention)
"""
import struct
import sys

GP_REG = 4
TP_REG = 5

REGNAME = {0: "r0", 3: "r3(sp)", 4: "gp", 5: "tp", 30: "ep"}


def decode_op(opcode, hw1, hw2):
    """(mnemonic, displacement, is_store) for the Format-VII load/store opcodes, or None.

    !!! EVERY LINE HERE IS A TRAP THIS KIT HAS ALREADY FALLEN INTO. The displacement is NOT simply
    hw2 for most of these:
      * ld.w / st.w  reuse the ld.h / st.h opcode and select WIDTH with hw2 bit 0, so the
        displacement's own bit 0 is forced to 0 and the encoded halfword is `disp | 1`.
      * ld.bu occupies TWO opcode values, 0x3C and 0x3D, because the displacement's bit 0 is
        carried in hw1 BIT 5 -- which is the opcode field's own low bit. Reading hw2 alone puts
        every odd-displacement ld.bu on the WRONG CELL, and reading hw1 bit 5 on an ld.h (where
        it is just part of the opcode) is the mirror-image error.
      * ld.hu (0x3F) is `disp | 1` like ld.w.
    Getting this wrong is how a scan reports "4 writers" for a cell that has none -- the four
    st.b hits for gp-0x683c all carry hw2 = 0x97c5 and therefore address gp-0x683B, one byte away.
    """
    b0 = hw2 & 1
    hw1_b5 = (hw1 >> 5) & 1
    if opcode == 0x38:
        return "ld.b", hw2, False
    if opcode == 0x39:
        return ("ld.w", hw2 & 0xFFFE, False) if b0 else ("ld.h", hw2, False)
    if opcode == 0x3A:
        return "st.b", hw2, True
    if opcode == 0x3B:
        return ("st.w", hw2 & 0xFFFE, True) if b0 else ("st.h", hw2, True)
    if opcode in (0x3C, 0x3D):
        return "ld.bu", (hw2 & 0xFFFE) | hw1_b5, False
    if opcode == 0x3F:
        return "ld.hu", hw2 & 0xFFFE, False
    return None


def load_image(path):
    with open(path, "rb") as fh:
        return fh.read()


def decode_fmt7(img, addr):
    """Return (reg2, mnemonic, disp_u16, is_store, reg1) or None."""
    if addr + 4 > len(img):
        return None
    hw1, hw2 = struct.unpack_from("<HH", img, addr)
    opcode = (hw1 >> 5) & 0x3F
    d = decode_op(opcode, hw1, hw2)
    if d is None:
        return None
    mnem, disp, is_store = d
    return (hw1 >> 11) & 0x1F, mnem, disp, is_store, hw1 & 0x1F


def scan(img, target_disp_u16, base_reg=GP_REG):
    """All Format-VII accesses to one displacement. Scans EVERY byte offset, not just even ones --
    an instruction stream is self-synchronising but a scanner is not, and restricting to even
    offsets silently drops half the search space when a preceding 2-byte instruction shifts parity.
    Odd-offset hits are flagged, never silently kept: a byte scan is not confirmation.
    """
    hits = []
    for addr in range(0, len(img) - 4):
        d = decode_fmt7(img, addr)
        if d is None:
            continue
        reg2, mnem, disp, is_store, reg1 = d
        if reg1 != base_reg or disp != target_disp_u16:
            continue
        hits.append({"addr": addr, "bytes": img[addr:addr + 4].hex(), "op": mnem,
                     "reg2": reg2, "is_store": is_store, "even": addr % 2 == 0})
    return hits


def self_check(img):
    """Pin the decoder against instructions whose identity is established independently.

    Every one of these is quoted in builds/v50_v79/build_v65_tva.py / the V64 build note as Ghidra
    BOUNDARY-CONFIRMED, so a mismatch here means the decoder is wrong, not the firmware.
    """
    cases = [
        (0x453E0, "ld.h", 4, (-0x6B94) & 0xFFFF, 6, False),    # ld.h -0x6b94[gp],r6
        (0x3ACEC, "ld.h", 4, (-0x6B94) & 0xFFFF, 13, False),   # ld.h -0x6b94[gp],r13
        (0x3ACFA, "st.h", 4, (-0x6B94) & 0xFFFF, 12, True),    # st.h r12,-0x6b94[gp]
        (0x3AD20, "st.h", 4, (-0x6B94) & 0xFFFF, 10, True),    # st.h r10,-0x6b94[gp]
    ]
    for addr, mnem, reg1, disp, reg2, is_store in cases:
        got = decode_fmt7(img, addr)
        assert got is not None, f"{addr:#x} did not decode at all"
        g_reg2, g_mnem, g_disp, g_store, g_reg1 = got
        assert (g_mnem, g_reg1, g_disp, g_reg2, g_store) == (mnem, reg1, disp, reg2, is_store), \
            f"{addr:#x}: got {got}, expected {(reg2, mnem, disp, is_store, reg1)}"
    # And the one that matters most: the ld.bu whose displacement bit 0 lives in hw1 bit 5.
    got = decode_fmt7(img, 0x3AA94)
    assert got is not None and got[1] == "ld.bu" and got[2] == ((-0x683C) & 0xFFFF), got
    print("decoder self-check OK "
          "(ld.h/st.h pinned on gp-0x6b94; ld.bu hw1-bit-5 pinned on gp-0x683c @0x3AA94)\n")


def scan_ext(img, target_disp, base_reg=GP_REG):
    """Brute-force the 48-bit extended-displacement form: any 6-byte window whose two trailing
    halfwords reconstruct the target under either packing, with reg1 == base_reg."""
    hits = []
    for addr in range(0, len(img) - 6):
        hw1 = struct.unpack_from("<H", img, addr)[0]
        if (hw1 & 0x1F) != base_reg:
            continue
        hw2, hw3 = struct.unpack_from("<HH", img, addr + 2)
        for lo, hi in ((hw2, hw3), (hw3, hw2)):
            disp = (hi << 16) | lo
            disp &= 0x7FFFFF
            if disp & 0x400000:
                disp -= 0x800000
            if (disp & 0xFFFF) == (target_disp & 0xFFFF) and disp < 0:
                hits.append({"addr": addr, "bytes": img[addr:addr + 6].hex(), "disp": disp})
                break
    return hits


def report(img, name, offset, base_reg=GP_REG):
    target = (-offset) & 0xFFFF
    print(f"=== {name}  (disp {-offset:#x} -> u16 {target:#06x}) ===")
    hits = scan(img, target, base_reg)
    loads = [h for h in hits if not h["is_store"]]
    stores = [h for h in hits if h["is_store"]]
    print(f"  Format-VII 32-bit : {len(hits)} hits  ({len(loads)} load-class, {len(stores)} STORE-class)")
    for h in hits:
        par = "" if h["even"] else "   [ODD OFFSET -- almost certainly aliasing, confirm boundary]"
        print(f"    {h['addr']:#08x}  {h['bytes']}  {h['op']:<10s} reg2={REGNAME.get(h['reg2'], 'r%d' % h['reg2']):<6s}"
              f"{'  <== STORE' if h['is_store'] else ''}{par}")
    ext = scan_ext(img, -offset, base_reg)
    print(f"  48-bit extended   : {len(ext)} candidate windows")
    for h in ext[:12]:
        print(f"    {h['addr']:#08x}  {h['bytes']}  disp={h['disp']:#x}")
    if len(ext) > 12:
        print(f"    ... {len(ext) - 12} more")
    print()
    return hits, ext


if __name__ == "__main__":
    path = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
            "_v65_plain_image.bin")
    img = load_image(path)
    print(f"image {path}  len {len(img):#x}\n")
    args = sys.argv[1:] or ["0x683c", "0x671d", "0x671a", "0x6806", "0x67a4", "0x4f62"]
    for a in args:
        report(img, f"gp-{a}", int(a, 16))
