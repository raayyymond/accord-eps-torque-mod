#!/usr/bin/env python3
"""Reconstruct the "RAM-resident" LERP of FUN_00038148 from FLASH.

Owner: close-the-sign agent. Study-only.

Claim under test: STATE.md says the LERP table at gp-0x64b8 / gp-0x641c
"cannot be read from the image" because it lives in RAM. It CAN:

  FUN_000382d8 (0x382d8, sole writer of both source arrays; caller FUN_00022ca0)
     mode = byte at gp+0x63fd
     brk   = *(int*)(0xCC9FC + mode*4)            7 speed breakpoints (shorts)
     recs  = *(int*)(base + mode*4) for base in
             0xC7B40 0xC7C28 0xC7D10 0xC7DF8 0xC7EE0 0xC7FC8 0xC80B0
             -> 7 records, one per speed breakpoint
     record layout: +0x00 count, +0x02..+0x12 nine X shorts,
                    +0x14..+0x24 nine Y shorts
     writes gp-0x6350[0..8]  (X source)  0x38880 / 0x388aa
            gp-0x630c[0..8]  (Y source)  0x3884c / 0x38886 / 0x388b0
     then EIGHT unconditional rungs Y[i] = max(Y[i], Y[i-1])   0x388c4 onward

  FUN_000389ec (0x389ec) rescales those into gp-0x64b8[] / gp-0x641c[]
     X[0] = 0, Y[0] = 0                            0x38d1c / 0x38d22
     X[i] = (Xsrc[i-1] << 10) / K1                 0x38c64 shl / 0x38c6a divq
     Y[i] = (Ysrc[i-1] * K2) >> 10                 0x38c7e mul / 0x38c84 sar
     Y[i] = max(Y[i], Y[i-1])                      0x38de2 cmp / 0x38e48 cmp
     Y[i] = min(Y[i], cal 0xC6200)                 0x38e9c cmp / 0x38ea2 st.h

  FUN_00038148 (0x38148) consumes gp-0x64b8[0..9] / gp-0x641c[0..9].
"""
import os
import struct
import sys

TP = 0xBF000
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      r"C:/Users/dudei/Desktop/Projects/accord-firmwares")
A = os.path.join(ROOT, "analysis-2020accord")
STOCK = os.path.join(A, "stock_fw_dump", "code.bin")

BRK_PTRS = 0xCC9FC
REC_PTRS = [0xC7B40, 0xC7C28, 0xC7D10, 0xC7DF8, 0xC7EE0, 0xC7FC8, 0xC80B0]

MODES = [24, 26]          # the live modes on this car (TVCA4)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def dump_mode(buf, mode):
    print("=" * 78)
    print("MODE %d  (index into every pointer table is mode*4 = 0x%X)" % (mode, mode * 4))
    print("=" * 78)

    brk_p = u32(buf, BRK_PTRS + mode * 4)
    print("  breakpoint array ptr @0x%05X -> 0x%05X" % (BRK_PTRS + mode * 4, brk_p))
    if not (0 <= brk_p < len(buf) - 16):
        print("  !! pointer out of image range; aborting this mode")
        return
    brks = [s16(buf, brk_p + 2 * i) for i in range(7)]
    print("  speed breakpoints (raw counts, scale 0.015625 = /64 -> km/h):")
    print("    %s" % brks)
    print("    km/h: %s" % ["%.2f" % (v / 64.0) for v in brks])
    print()

    recs = []
    for k, base in enumerate(REC_PTRS):
        p = u32(buf, base + mode * 4)
        recs.append(p)
        print("  rec[%d] ptr @0x%05X -> 0x%05X" % (k, base + mode * 4, p))
    print()

    for k, p in enumerate(recs):
        if not (0 <= p < len(buf) - 0x30):
            print("  rec[%d] @0x%05X OUT OF RANGE" % (k, p))
            continue
        cnt = s16(buf, p)
        xs = [s16(buf, p + 2 + 2 * i) for i in range(9)]
        ys = [s16(buf, p + 0x14 + 2 * i) for i in range(9)]
        xmono = all(xs[i] <= xs[i + 1] for i in range(8))
        ymono = all(ys[i] <= ys[i + 1] for i in range(8))
        print("  rec[%d] @0x%05X count=%d" % (k, p, cnt))
        print("     X: %s   monotone_nondecreasing=%s" % (xs, xmono))
        print("     Y: %s   monotone_nondecreasing=%s" % (ys, ymono))
        if not xmono:
            print("     !!! X NOT MONOTONE — the LERP denominator can go negative")
        if not ymono:
            print("     (Y non-monotone in flash, but FUN_000382d8 0x388c4+ forces it)")
    print()


def main():
    with open(STOCK, "rb") as f:
        buf = f.read()

    # Anchor the tp arithmetic against values already established in the kit.
    anchors = [(0xC6468, 2639, "0xC6468 via ld.hu 0x7468[tp]"),
               (0xC40BC, 600, "0xC40BC Coulomb relay gate"),
               (0xC6200, None, "0xC6200 via ld.hu 0x7200[tp] (the +-clamp)")]
    print("--- anchors ---")
    for addr, expect, why in anchors:
        v = u16(buf, addr)
        ok = "" if expect is None else ("  OK" if v == expect else "  *** MISMATCH ***")
        print("  0x%05X = %-6d  %s%s" % (addr, v, why, ok))
    print("  tp+0x8b40 = 0x%05X (expect 0xC7B40)" % (TP + 0x8B40))
    print("  tp+0x90b0 = 0x%05X (expect 0xC80B0)" % (TP + 0x90B0))
    print()

    # Cals that scale the built table.
    for addr, name in [(0xC613A, "0xC613A  (uVar9, scales gp-0x4f60 path in 3b8f6 too)"),
                       (0xC613C, "0xC613C  X[9] floor"),
                       (0xC613E, "0xC613E  low-speed Y floor gate"),
                       (0xC6140, "0xC6140  second Y floor gate"),
                       (0xC617A, "0xC617A  Y floor A"),
                       (0xC617C, "0xC617C  Y floor B"),
                       (0xC6178, "0xC6178  slew cap"),
                       (0xC63AE, "0xC63AE  LERP input scale (x/1024)"),
                       (0xC6200, "0xC6200  Y ceiling / output clamp")]:
        print("  %-52s = %d" % (name, u16(buf, addr)))
    print()

    for m in MODES:
        dump_mode(buf, m)

    # Do the two live modes ship identical curves? (kit: mode24 == mode26 on stock)
    print("--- mode 24 vs mode 26 record-pointer comparison ---")
    for k, base in enumerate([BRK_PTRS] + REC_PTRS):
        p24 = u32(buf, base + 24 * 4)
        p26 = u32(buf, base + 26 * 4)
        same = "SAME PTR" if p24 == p26 else "differ"
        note = ""
        if p24 != p26 and 0 <= p24 < len(buf) - 0x30 and 0 <= p26 < len(buf) - 0x30:
            note = "  bytes %s" % ("IDENTICAL" if buf[p24:p24 + 0x26] == buf[p26:p26 + 0x26]
                                   else "DIFFER")
        print("  base 0x%05X: m24->0x%05X m26->0x%05X  %s%s" % (base, p24, p26, same, note))


if __name__ == "__main__":
    main()
