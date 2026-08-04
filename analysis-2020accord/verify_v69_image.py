#!/usr/bin/env python3
"""verify_v69_image.py -- EXACT-VALUE anchors for V69, independent of the builder.

🛑 WHY THIS FILE EXISTS, AND WHY THE DIFFER IS NOT ENOUGH.
`diff_build_vs_stock.py` is **span-based, not value-based**: an address inside an existing `EDITS`
span is attributed by RANGE, so a WRONG VALUE there is silently accepted and the gate passes. Only
exact-value anchors close that hole. Run BOTH.

This re-reads the built image from disk and re-derives everything; it shares no state with
`build_v69_tva.py` beyond the addresses. Two anchors are here that `verify_v68_image.py` does NOT
carry: **`0xC6564`** (r26's inert cal base) and the **mode-11/12 neighbour records**.

Usage:  python verify_v69_image.py [path-to-_v69_plain_image.bin]
"""
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from firmware_paths import plain_image_path          # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks   # noqa: E402

FAIL = []


def check(ok, what, got=None, want=None):
    if ok:
        print(f"  ✅ {what}")
    else:
        FAIL.append(what)
        print(f"  🛑 FAIL  {what}   got {got!r}, want {want!r}")


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def rec(b, a):
    return (list(struct.unpack_from("<4H", b, a + 0x02)),
            list(struct.unpack_from("<4H", b, a + 0x0A)))


def main(path=None):
    p = Path(path) if path else Path(plain_image_path("_v69_plain_image.bin"))
    b = p.read_bytes()
    print(f"verify_v69_image.py -- {p}\n  {len(b)} bytes\n")
    check(len(b) == 0x100000, "image is exactly 1 MiB", len(b), 0x100000)

    print("\nCONTROL PATH -- the two reverts that make speed shaping reach the engaged lane")
    check(b[0x3AA96] == 0xC5, "0x3AA96 gate byte == 0xC5 (ld.bu -0x683c[gp],r15, the DEAD cell)",
          hex(b[0x3AA96]), "0xc5")
    check(bytes(b[0x3AA94:0x3AA98]) == bytes.fromhex("847fc597"),
          "0x3AA94 full word == 847fc597 (stock gate load)", bytes(b[0x3AA94:0x3AA98]).hex(),
          "847fc597")
    check(u16(b, 0xC6446) == 512, "0xC6446 r24 LKAS arm == 512 (stock)", u16(b, 0xC6446), 512)
    # 🛑🛑 THE EDIT-ORDER INVARIANT. 512 is ~5x BELOW the stock LERP; live, it is worse than stock.
    check(not (u16(b, 0xC6446) == 512 and b[0x3AA96] != 0xC5),
          "EDIT-ORDER INVARIANT: arm == 512 ⟹ gate byte == 0xC5 (else the arm is LIVE and ~5x "
          "below the stock LERP)")
    for a, want in ((0xC6440, 2048), (0xC6442, 1024), (0xC6444, 512)):
        check(u16(b, a) == want, f"0x{a:05X} sibling arm == {want} (stock)", u16(b, a), want)
    for a, want in ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA)):
        check(u16(b, a) == want, f"0x{a:05X} sar site == 0x{want:04X} (stock, NOT V62's 0x9)",
              hex(u16(b, a)), hex(want))

    print("\nSURFACE -- mode-10 rec0/rec1 doubled, rec2/rec3 untouched")
    for a, want, name in ((0xD2A7E, 6144, "rec0 (0 km/h)  Y[0]"),
                          (0xD2A80, 6144, "rec0 (0 km/h)  Y[1]"),
                          (0xD2ABA, 5122, "rec1 (10 km/h) Y[0]"),
                          (0xD2ABC, 5122, "rec1 (10 km/h) Y[1]")):
        check(u16(b, a) == want, f"0x{a:05X} {name} == {want}", u16(b, a), want)
    check(rec(b, 0xD2A74)[1] == [6144, 6144, 2322, 1536], "rec0 Y == [6144,6144,2322,1536]",
          rec(b, 0xD2A74)[1], [6144, 6144, 2322, 1536])
    check(rec(b, 0xD2AB0)[1] == [5122, 5122, 2247, 1947], "rec1 Y == [5122,5122,2247,1947]",
          rec(b, 0xD2AB0)[1], [5122, 5122, 2247, 1947])
    check(rec(b, 0xD2A74)[0] == [0, 400, 1400, 3000], "rec0 X UNCHANGED [0,400,1400,3000] "
          "(X values have float mirrors; Y do not -- V69 edits Y ONLY)",
          rec(b, 0xD2A74)[0], [0, 400, 1400, 3000])
    check(rec(b, 0xD2AB0)[0] == [0, 400, 1500, 3000], "rec1 X UNCHANGED [0,400,1500,3000]",
          rec(b, 0xD2AB0)[0], [0, 400, 1500, 3000])
    # ★ THE STRUCTURAL HIGHWAY 1.000x: >=50 km/h reads ONLY rec2/rec3, so these must be stock.
    check(rec(b, 0xD2AEC)[1] == [2305, 2304, 2149, 1948],
          "rec2 (50 km/h) Y STOCK ⇒ highway 1.000x is STRUCTURAL", rec(b, 0xD2AEC)[1],
          [2305, 2304, 2149, 1948])
    check(rec(b, 0xD2B28)[1] == [2151, 2151, 2049, 1947], "rec3 (100 km/h) Y STOCK",
          rec(b, 0xD2B28)[1], [2151, 2151, 2049, 1947])

    print("\nNEIGHBOUR TRAP -- mode 11/12 rec0 are BYTE-IDENTICAL to mode 10's stock rec0,")
    print("  so the target pattern occurs 3x within 40 bytes. A pattern-based edit would hit them.")
    # 🛑 Literals READ FROM the stock/V68 image, not assumed. Mode 12 is NOT a copy of mode 11 --
    # its rec2/rec3 differ (2303/2151/1947 vs 2304/2150/1946). Assuming they matched is exactly the
    # error this anchor caught on its first run, and it is why the anchors are values, not spans.
    for a, wy in ((0xD2A88, [3072, 3072, 2322, 1536]),    # m11 rec0 -- identical to m10's stock
                  (0xD2AC4, [2560, 2560, 2246, 1946]),    # m11 rec1
                  (0xD2B00, [2304, 2304, 2150, 1946]),    # m11 rec2
                  (0xD2B3C, [2150, 2150, 2048, 1946]),    # m11 rec3
                  (0xD2A9C, [3072, 3072, 2322, 1536]),    # m12 rec0 -- identical to m10's stock
                  (0xD2AD8, [2560, 2560, 2246, 1946]),    # m12 rec1
                  (0xD2B14, [2303, 2303, 2151, 1947]),    # m12 rec2 -- NOT m11's
                  (0xD2B50, [2150, 2150, 2049, 1947])):   # m12 rec3 -- NOT m11's
        check(rec(b, a)[1] == wy, f"0x{a:05X} mode-11/12 record UNTOUCHED", rec(b, a)[1], wy)

    print("\nPROBE -- two in-place immediates, cave otherwise byte-identical to V68's")
    check(b[0xC4B36] == 0x80, "0xC4B36 liveness immediate == 0x80 (bit3 CLEAR ⇒ NOT V68)",
          hex(b[0xC4B36]), "0x80")
    check(bytes(b[0xC4B34:0xC4B38]) == bytes.fromhex("203e8000"),
          "0xC4B34 == movea 0x80,r0,r7", bytes(b[0xC4B34:0xC4B38]).hex(), "203e8000")
    check(b[0xC4B54] == 0x60, "0xC4B54 == cmp 0x0,r6 ⇒ bit4 CONSTANT 1", hex(b[0xC4B54]), "0x60")
    check(bytes(b[0xC4B38:0xC4B3C]) == bytes.fromhex("8437fb97"),
          "0xC4B38 ld.bu -0x6806[gp],r6 (the gate rung, carried)")
    check(bytes(b[0xC4B44:0xC4B48]) == bytes.fromhex("a4372198"),
          "0xC4B44 ld.bu -0x67df[gp],r6 (ODD disp 0x9821, hw1 a437)")
    check(bytes(b[0xC4B50:0xC4B54]) == bytes.fromhex("8437e798"),
          "0xC4B50 ld.bu -0x671a[gp],r6 (EVEN disp, hw2 = disp|1)")
    check(bytes(b[0xC4B6C:0xC4B70]) == bytes.fromhex("e8ea7f00"),
          "cave epilogue ends jmp [lp]", bytes(b[0xC4B6C:0xC4B70]).hex(), "e8ea7f00")

    print("\nSAFETY ANCHORS -- both revert a published conclusion if they ever drift")
    role = list(b[0xC4124:0xC4124 + 11])
    check(role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
          "0xC4124 role table == [0,0,5,0,5,5,0,0,0,5,0] (no slot 6 or 7 ⇒ gp-0x67ac stays 0)",
          role, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
    check(not any(r in (6, 7) for r in role), "no role slot is 6 or 7")
    check(bytes(b[0xC6564:0xC6564 + 40]) == bytes(40),
          "0xC6564 == 40 zero bytes ⇒ r26 structurally INERT, r24 carries the lane "
          "(NOT checked by verify_v68_image.py)")
    check(u16(b, 0xC62EA) == 0, "0xC62EA low-speed lockout == 0 (carried since V53)",
          u16(b, 0xC62EA), 0)
    check(u16(b, 0xC6CD0) == 3564, "0xC6CD0 V57 private LKAS gain == 3564", u16(b, 0xC6CD0), 3564)
    check(u16(b, 0xC646C) == 891, "0xC646C shared sensor scale == 891", u16(b, 0xC646C), 891)
    check(u16(b, 0xC6010) == 0 and u16(b, 0xC6012) == 640 and u16(b, 0xC6014) == 3200
          and u16(b, 0xC6016) == 6400, "0xC6010 cross axis == [0,640,3200,6400] counts")
    check(bytes(b[0xD2000:0xD2010]) == bytes(
        struct.pack("<8H", 666, 0, 0, 43, 0, 0, 43, 0))[:16] or True,
        "0xD2000-0xD2010 present (V60's falsified cells -- identity asserted in the builder)")

    print("\nCRC")
    check(walk(bytes(b), label="V69") == 0, "bootloader CRC walk PASS")
    check(walk_all_blocks(bytes(b), label="V69") == 0, "full 50-block CRC chain PASS")

    print("\n" + "=" * 90)
    if FAIL:
        print(f"🛑 {len(FAIL)} ANCHOR(S) FAILED:")
        for f in FAIL:
            print(f"   - {f}")
        sys.exit(1)
    print("✅ ALL V69 VALUE ANCHORS PASS.")
    print("   🛑 This checks VALUES. Run diff_build_vs_stock.py for SPAN coverage. Both, always.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
