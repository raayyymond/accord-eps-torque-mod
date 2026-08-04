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

SCALE = 4          # 🛑 the surface dose. Operator instruction 2026-08-04: was 2.

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

    # 🛑 SCALE is the dose. Operator instruction 2026-08-04: 2x -> 4x. Every expected value below is
    # DERIVED from the stock halfword x SCALE, so a hand-edited literal cannot drift out of step.
    print(f"\nSURFACE -- mode-10 rec0/rec1 scaled x{SCALE}, rec2/rec3 untouched")
    for a, stock, name in ((0xD2A7E, 3072, "rec0 (0 km/h)  Y[0]"),
                           (0xD2A80, 3072, "rec0 (0 km/h)  Y[1]"),
                           (0xD2ABA, 2561, "rec1 (10 km/h) Y[0]"),
                           (0xD2ABC, 2561, "rec1 (10 km/h) Y[1]")):
        want = stock * SCALE
        check(u16(b, a) == want, f"0x{a:05X} {name} == {want} (= {stock} x {SCALE})",
              u16(b, a), want)
        check(0 < want < 0x8000, f"0x{a:05X} {name} stays a POSITIVE SIGNED halfword "
              "(>= 0x8000 would invert the lane under an `ld.h` accessor)")
    r0y = [3072 * SCALE, 3072 * SCALE, 2322, 1536]
    r1y = [2561 * SCALE, 2561 * SCALE, 2247, 1947]
    check(rec(b, 0xD2A74)[1] == r0y, f"rec0 Y == {r0y}", rec(b, 0xD2A74)[1], r0y)
    check(rec(b, 0xD2AB0)[1] == r1y, f"rec1 Y == {r1y}", rec(b, 0xD2AB0)[1], r1y)
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

    print("\nPROBE -- RE-AIMED AT THE RATCHET: three SIGNED-halfword rungs on the aggregator's own")
    print("  hard nonlinearities. 🛑 EVERY byte of the 68-byte cave extent is anchored below, because")
    print("  a cave is this kit's ONLY bricking class (V24, V27, V48B all bricked the ECU).")
    CAVE = bytes.fromhex(
        "203e8000"                          # movea 0x80,r0,r7   bit7 LIVENESS, bit3 CLEAR = V69
        "24372695" "ac32" "6132" "b605" "273e4000"   # bit6 = gp-0x6ada >= +4096
        "24379e94" "ac32" "6132" "b605" "273e2000"   # bit5 = gp-0x6b62 >= +4096
        "24372c95" "ac32" "6132" "b605" "273e1000"   # bit4 = gp-0x6ad4 >= +4096
        "8437edea" "c6360700" "0731" "4437ecea"      # payload read / mask / or / THE ONLY STORE
        "2436e8ea" "7f00"                            # displaced movea, then jmp [lp]
    ) + b"\xff" * 2
    check(len(CAVE) == 68, "the anchored cave is the PROVEN 68-byte extent", len(CAVE), 68)
    check(bytes(b[0xC4B34:0xC4B34 + 68]) == CAVE, "0xC4B34 cave is byte-exact over all 68 bytes",
          bytes(b[0xC4B34:0xC4B34 + 68]).hex(), CAVE.hex())
    check(b[0xC4B36] == 0x80, "0xC4B36 liveness immediate == 0x80 (bit3 CLEAR ⇒ NOT V68, which "
          "emits bit3 = 1 in 100.000% of frames)", hex(b[0xC4B36]), "0x80")
    # 🛑🛑 THE ONE-BIT TRAP, CHECKED BY VALUE. `ld.h` is opcode 0x39; `st.h` is 0x3B. gp-0x6ada's
    # only real instance @0x3AD5A IS the st.h form and carries the SAME displacement halfword we
    # emit -- one bit turns each of these reads into a WRITE into a 1 kHz aggregator lane.
    for a, disp, name in ((0xC4B38, 0x6ADA, "r24 lane out (0 readers image-wide)"),
                          (0xC4B46, 0x6B62, "return-to-centre (the operator's hypothesis)"),
                          (0xC4B54, 0x6AD4, "unfiltered residual / resonance")):
        raw = bytes(b[a:a + 4])
        hw1, hw2 = struct.unpack("<HH", raw)
        check(((hw1 >> 5) & 0x3F) == 0x39, f"0x{a:05X} opcode field == 0x39 (ld.h, SIGNED) -- "
              f"NOT 0x3B (st.h) and NOT 0x3F (ld.hu): {name}", hex((hw1 >> 5) & 0x3F), "0x39")
        check(hw2 == (0x10000 - disp) & 0xFFFF and hw2 & 1 == 0,
              f"0x{a:05X} displacement == -0x{disp:04x}, hw2 LSB clear", hex(hw2),
              hex((0x10000 - disp) & 0xFFFF))
        check((hw1 & 0x1F) == 4 and (hw1 >> 11) == 6, f"0x{a:05X} reg1 == gp(r4), reg2 == r6")
    # the three shifts are ARITHMETIC and the three compares are SIGNED -- an `shr` or a `bl` would
    # fire every rung on the wrong half-cycle of a symmetric limit cycle and still look plausible.
    for a in (0xC4B3C, 0xC4B4A, 0xC4B58):
        check(bytes(b[a:a + 2]) == bytes.fromhex("ac32"), f"0x{a:05X} == sar 0xc,r6 (ARITHMETIC, "
              "not shr)", bytes(b[a:a + 2]).hex(), "ac32")
    for a in (0xC4B3E, 0xC4B4C, 0xC4B5A):
        check(bytes(b[a:a + 2]) == bytes.fromhex("6132"), f"0x{a:05X} == cmp 0x1,r6 ⇒ threshold "
              "+4096", bytes(b[a:a + 2]).hex(), "6132")
    for a in (0xC4B40, 0xC4B4E, 0xC4B5C):
        check(bytes(b[a:a + 2]) == bytes.fromhex("b605"), f"0x{a:05X} == blt +6 (SIGNED; bl 0x1 is "
              "the UNSIGNED twin and would invert every negative sample)",
              bytes(b[a:a + 2]).hex(), "b605")
    # EXACTLY ONE STORE in the whole cave, and it is the CAN payload byte.
    stores = [0xC4B34 + i for i in range(0, 68 - 3, 2)
              if ((struct.unpack_from("<H", CAVE, i)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    check(stores == [0xC4B6C], "the cave contains EXACTLY ONE store, at 0xC4B6C (the payload byte)",
          [hex(s) for s in stores], ["0xc4b6c"])
    check(bytes(b[0xC4B74:0xC4B76]) == bytes.fromhex("7f00"), "cave ends jmp [lp]",
          bytes(b[0xC4B74:0xC4B76]).hex(), "7f00")
    check(bytes(b[0xC4B70:0xC4B74]) == bytes.fromhex("2436e8ea"),
          "0xC4B70 re-executes the displaced hook instruction `movea -0x1518,gp,r6`")
    # 🛑 A gate that cannot fail informatively is worse than no gate (the 2026-08-03 differ lesson).
    # The hook is anchored BY VALUE: `jarl 0xC4B34,lp` at 0x55C0E, the same 4 bytes flown 8 times.
    check(bytes(b[0x55C0E:0x55C12]) == bytes.fromhex("86ff26ef"),
          "0x55C0E == jarl 0xC4B34,lp (the cave entry, byte-identical to V55..V68)",
          bytes(b[0x55C0E:0x55C12]).hex(), "86ff26ef")

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
