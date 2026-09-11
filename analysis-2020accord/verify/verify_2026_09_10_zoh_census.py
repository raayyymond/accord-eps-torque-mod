"""
Verifier for TRACE-2026-09-10-command-intersample-zoh.md.

Re-runs, from raw bytes, the two load-bearing censuses in that trace:
  1. gp-0x69ae (the ZOH'd LKAS command cell) writer/reader census, cross-checked
     against two positive controls (gp-0x69ae itself found via an independent
     scanner build, and gp-0x6a34, a known-live cell).
  2. The 72-byte RAM run gp-0x6D74..gp-0x6D2D, scanned across 7 gp-relative
     access forms (ld.h/ld.w std+w-variant, ld.hu, ld.b, st.b, bit-ops,
     absolute 4-byte pointer), with the same two positive controls.
  3. The free-flash run in the ACTUAL V282 image (the current revert target),
     not V288/V289's post-cave images.

Run with the bin_decompile conda env's python:
    C:/Users/dudei/anaconda3/envs/bin_decompile/python verify_2026_09_10_zoh_census.py

Requires ACCORD_FIRMWARE_ROOT to point at the accord-firmwares checkout (see CLAUDE.md).
"""
import os
import struct

FW_ROOT = os.environ.get(
    "ACCORD_FIRMWARE_ROOT",
    "C:/Users/dudei/Desktop/Projects/accord-firmwares",
)
STOCK = os.path.join(FW_ROOT, "analysis-2020accord", "stock_fw_dump", "code.bin")
V282 = os.path.join(
    FW_ROOT,
    "analysis-2020accord",
    "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
)

GP = 0xFEDF8000


def scan_disp(data, disp, base_reg_field=4):
    """Scan `data` for every gp-relative access to gp-disp, across 7 encodings.
    Returns a list of (file_offset, hw1_hex, mnemonic, variant)."""
    hits = []
    hw2_std = (-disp) & 0xFFFF
    hw2_w = hw2_std | 1  # ld.w/st.w LSB-forced form
    for hw2_val, tag in [(hw2_std, "std"), (hw2_w, "w-variant")]:
        hw2b = struct.pack("<H", hw2_val)
        o = 0
        while True:
            i = data.find(hw2b, o)
            if i == -1:
                break
            o = i + 1
            if i < 2:
                continue
            hw1 = struct.unpack("<H", data[i - 2 : i])[0]
            opc = (hw1 >> 5) & 0x3F
            reg1 = hw1 & 0x1F
            if reg1 != base_reg_field:
                continue
            if opc == 0x39:
                hits.append((i - 2, hex(hw1), "ld.h/ld.w", tag))
            elif opc == 0x3B:
                hits.append((i - 2, hex(hw1), "st.h/st.w", tag))
            elif opc == 0x3F:
                hits.append((i - 2, hex(hw1), "ld.hu", tag))

    # ld.b (0x38) / st.b (0x3A): disp = hw2 exactly, both parities, no LSB games
    hw2b = struct.pack("<H", hw2_std)
    o = 0
    while True:
        i = data.find(hw2b, o)
        if i == -1:
            break
        o = i + 1
        if i < 2:
            continue
        hw1 = struct.unpack("<H", data[i - 2 : i])[0]
        opc = (hw1 >> 5) & 0x3F
        reg1 = hw1 & 0x1F
        if reg1 != base_reg_field:
            continue
        if opc == 0x38:
            hits.append((i - 2, hex(hw1), "ld.b", "byte"))
        elif opc == 0x3A:
            hits.append((i - 2, hex(hw1), "st.b", "byte"))

    # bit-ops: set1/clr1/tst1/not1, opcode6==0x3E, reg1==gp
    o = 0
    while True:
        i = data.find(hw2b, o)
        if i == -1:
            break
        o = i + 1
        if i < 2:
            continue
        hw1 = struct.unpack("<H", data[i - 2 : i])[0]
        opc = (hw1 >> 5) & 0x3F
        reg1 = hw1 & 0x1F
        if opc == 0x3E and reg1 == base_reg_field:
            hits.append((i - 2, hex(hw1), "bit-op", "byte"))

    # absolute 4-byte little-endian pointer to gp-disp, any alignment
    addr = (GP - disp) & 0xFFFFFFFF
    b = struct.pack("<I", addr)
    o = 0
    while True:
        i = data.find(b, o)
        if i == -1:
            break
        hits.append((i, hex(addr), "abs-ptr", "any-align"))
        o = i + 1

    return hits


def main():
    data = open(STOCK, "rb").read()

    print("=== positive controls ===")
    ctrl_69ae = scan_disp(data, 0x69AE)
    ctrl_6a34 = scan_disp(data, 0x6A34)
    print(f"gp-0x69ae: {len(ctrl_69ae)} hits (expect 7 -- 4 writers + 3 readers)")
    for h in ctrl_69ae:
        print("   ", h)
    print(f"gp-0x6a34: {len(ctrl_6a34)} hits (expect 3 -- documented live cell)")
    for h in ctrl_6a34:
        print("   ", h)
    assert len(ctrl_69ae) == 7, "positive control gp-0x69ae FAILED -- do not trust the census below"
    assert len(ctrl_6a34) == 3, "positive control gp-0x6a34 FAILED -- do not trust the census below"

    print()
    print("=== RAM census: gp-0x6d2d .. gp-0x6d74 (72 bytes) ===")
    found = {}
    for disp in range(0x6D2D, 0x6D75):
        h = scan_disp(data, disp)
        if h:
            found[disp] = h
    print(f"displacements with any hit: {len(found)} of {0x6D75 - 0x6D2D}")
    for d in sorted(found):
        print("   ", hex(d), found[d])
    if not found:
        print("VERDICT: clean -- re-confirms TRACE-2026-09-08's certification of this run.")

    print()
    print("=== free-flash census: the ACTUAL V282 image (current revert target) ===")
    v282 = open(V282, "rb").read()
    lo, hi = 0xC4B00, 0xC5200
    region = v282[lo:hi]
    runs = []
    i = 0
    n = len(region)
    while i < n:
        if region[i] == 0xFF:
            j = i
            while j < n and region[j] == 0xFF:
                j += 1
            runs.append((lo + i, lo + j - 1, j - i))
            i = j
        else:
            i += 1
    runs.sort(key=lambda r: -r[2])
    for r in runs[:5]:
        print(f"   {hex(r[0])} - {hex(r[1])}  len {r[2]}")
    largest = runs[0]
    print(f"largest contiguous 0xFF run: {hex(largest[0])}-{hex(largest[1])}, {largest[2]} bytes")


if __name__ == "__main__":
    main()
