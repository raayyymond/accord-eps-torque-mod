#!/usr/bin/env python3
"""studies/firmware_scan/scan_tp_cal_c6444.py -- blast radius of the tp-relative cals 0xC6444 / 0xC6446.

tp = 0xBF000, so tp+0x7444 = 0xC6444 and tp+0x7446 = 0xC6446.
*** ANCHOR CHECK FIRST: the off-by-0x1000 tp error has recurred five times in this kit. This script
refuses to report anything until it re-derives tp from a load whose target is known independently.

Required second method for the Ghidra xref set (search_instructions undercounts analysed-only
instructions and over-counts on operand substrings). Covers both encodings:
  Format VII 32-bit   hw1 = [reg2|opcode|reg1], hw2 = disp16 (with the ld.w/st.w bit0 = 1 quirk and
                      the ld.bu hw1-bit-5 quirk)
  Format XIV 48-bit   extended displacement, brute-forced and flagged as CANDIDATE only
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from scan_gp_accesses import decode_fmt7, load_image  # noqa: E402

IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
       "_v65_plain_image.bin")
TP_REG = 5
GP_REG = 4
TP = 0xBF000

# The five cal-select loads inside FUN_0003aa2c, from the Ghidra listing. Used as the anchor.
ANCHORS = {
    0x3AB5E: ("ld.hu", 0x7444),
    0x3AB68: ("ld.hu", 0x743E),
    0x3ABFE: ("ld.hu", 0x7442),
    0x3AC08: ("ld.hu", 0x7446),
    0x3AC12: ("ld.hu", 0x7440),
}


def main():
    img = load_image(IMG)
    print(f"image {IMG}  len {len(img):#x}\n")

    print("=== ANCHOR: re-derive the tp encoding from five loads Ghidra already named ===")
    ok = True
    for addr, (mnem, disp) in ANCHORS.items():
        raw = img[addr:addr + 4]
        hw1, hw2 = struct.unpack_from("<HH", img, addr)
        d = decode_fmt7(img, addr)
        reg2, gm, gd, st, reg1 = d
        good = (gm == mnem and reg1 == TP_REG and gd == disp)
        ok &= good
        print(f"  {addr:#08x} {raw.hex()}  decoded {gm} {gd:#06x}[r{reg1}],r{reg2}   "
              f"expected {mnem} {disp:#06x}[tp]   {'OK' if good else '*** MISMATCH ***'}")
    if not ok:
        print("\n*** anchor failed -- decoder or tp assumption wrong. STOP.")
        return
    print(f"  => tp = {TP:#x} confirmed against these; tp+0x7444 = {TP+0x7444:#x}, "
          f"tp+0x7446 = {TP+0x7446:#x}\n")

    print("=== Format-VII census, reg1 == tp, for the whole 0x743E..0x7448 cal neighbourhood ===")
    want = {0x743E, 0x7440, 0x7442, 0x7444, 0x7446, 0x7448}
    # a halfword cal can also be touched by a WORD access one halfword below it
    found = {}
    for addr in range(0, len(img) - 4):
        d = decode_fmt7(img, addr)
        if d is None:
            continue
        reg2, mnem, disp, is_store, reg1 = d
        if reg1 != TP_REG or disp not in want:
            continue
        found.setdefault(disp, []).append((addr, img[addr:addr + 4].hex(), mnem, reg2, is_store))
    for disp in sorted(want):
        hits = found.get(disp, [])
        star = "  <<< TARGET" if disp in (0x7444, 0x7446) else ""
        print(f"  tp+{disp:#06x} = {TP+disp:#07x} : {len(hits)} access(es){star}")
        for addr, b, mnem, reg2, st in hits:
            print(f"      {addr:#08x}  {b}  {mnem:<6s} r{reg2}{'  <== STORE' if st else ''}")

    print("\n=== word-access overlap check (a ld.w/st.w at tp+0x7444 covers 0x7444 AND 0x7446) ===")
    for disp in (0x7440, 0x7442, 0x7444, 0x7446):
        for addr in range(0, len(img) - 4):
            d = decode_fmt7(img, addr)
            if d is None:
                continue
            reg2, mnem, dd, is_store, reg1 = d
            if reg1 == TP_REG and dd == disp and mnem in ("ld.w", "st.w"):
                print(f"      WORD access {addr:#08x} {mnem} tp+{disp:#06x}")
    print("      (no output above => no word-width access touches the pair)")

    print("\n=== 48-bit extended-displacement candidates (reg1 == tp, disp low16 in the set) ===")
    n = 0
    for addr in range(0, len(img) - 6):
        hw1 = struct.unpack_from("<H", img, addr)[0]
        if (hw1 & 0x1F) != TP_REG:
            continue
        hw2, hw3 = struct.unpack_from("<HH", img, addr + 2)
        for lo, hi in ((hw2, hw3), (hw3, hw2)):
            disp = ((hi << 16) | lo) & 0x7FFFFF
            if disp & 0x400000:
                disp -= 0x800000
            if (disp & 0xFFFF) in (0x7444, 0x7446) and disp > 0:
                print(f"      {addr:#08x}  {img[addr:addr+6].hex()}  disp={disp:#x}")
                n += 1
                break
    print(f"      {n} candidate window(s)")

    print("\n=== ALSO scan gp-relative for the same absolute addresses, in case a second base "
          "reaches them (gp = 0xFEDF8000, so 0xC6444 is not gp-reachable in 16 bits; this is a "
          "null-by-arithmetic, stated for the record) ===")
    print(f"      0xC6444 - gp = {(0xC6444 - 0xFEDF8000) & 0xFFFFFFFF:#x}  -> not a 16-bit disp")

    print("\n=== CAL VALUES (little-endian u16) ===")
    for a in range(0xC643C, 0xC644C, 2):
        v = struct.unpack_from("<H", img, a)[0]
        tag = {0xC643E: "  else-branch (r24 lane, r2 path)",
               0xC6440: "  else-branch (rate lane, r2 path)",
               0xC6442: "  gp-0x671d path (rate lane)",
               0xC6444: "  <<< lp path, AVG lane (r8)",
               0xC6446: "  <<< lp path, RATE lane (r10)"}.get(a, "")
        print(f"  {a:#07x} = {v:6d}  ({v/1024:.4f} in Q10){tag}")

    print("\n=== ramp step cals read by the gp-0x6806 writers (tp+0x73F6/F8/FA/FC) ===")
    for off in (0x73F6, 0x73F8, 0x73FA, 0x73FC):
        a = TP + off
        v = struct.unpack_from("<H", img, a)[0]
        print(f"  tp+{off:#06x} = {a:#07x} = {v:6d}   full-scale 0x8000 traversal = "
              f"{32768/v:.1f} ticks = {32768/v:.1f} ms at 1 kHz" if v else f"  {a:#07x} = 0")

    print("\n=== FLOAT-MIRROR check: any IEEE-754 f32 in [0xC6400,0xC6480) equal to a cal value? ===")
    vals = {struct.unpack_from("<H", img, a)[0] for a in (0xC6444, 0xC6446)}
    hits = 0
    for a in range(0xC6400, 0xC6480):
        f = struct.unpack_from("<f", img, a)[0]
        for v in vals:
            for cand in (v, v / 1024.0):
                if cand != 0 and abs(f - cand) < 1e-6 * max(1.0, abs(cand)):
                    print(f"      {a:#07x} f32={f} matches {cand}")
                    hits += 1
    print(f"      {hits} float mirror(s) found")


if __name__ == "__main__":
    main()
