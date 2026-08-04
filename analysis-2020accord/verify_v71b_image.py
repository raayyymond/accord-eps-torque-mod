#!/usr/bin/env python3
"""verify_v71b_image.py -- EXACT-VALUE anchors for V71B, independent of the builder.

🛑 WHY A SEPARATE VERIFIER. V71A and V71B carry a **BYTE-IDENTICAL 68-byte cave** and differ only in
how r26 is dosed. `diff_build_vs_stock.py` is span-based and cannot tell them apart at all; even
`verify_v71a_image.py` would PASS on several of V71B's bytes. The distinguishing facts are:

    V71A   0x3AB76 = 0x32A9 and 0x3AC20 = 0x42A9   (`sar 0x9`)   · gain_A entirely STOCK
    V71B   0x3AB76 = 0x32AA and 0x3AC20 = 0x42AA   (`sar 0xa`)   · gain_A rec0/rec1 Y[0..3] DOUBLED

Both carry `0x454FE = 0xB5` and a stock `gain_B` surface. This file asserts V71B's side of that
table by exact value, and asserts V71A's side is ABSENT.

Usage:  python verify_v71b_image.py [path-to-_v71b_plain_image.bin]
"""
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from firmware_paths import plain_image_path, stock_fw_path         # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
CAVE_BASE, CAVE_LEN = 0xC4B34, 68
RATCHET_ADDR = 0x454FE
CRC_WORDS = {a + k for a in (0xC4FFC, 0xC6FFC, 0xD2FFC) for k in range(4)}

# The 68 cave bytes -- IDENTICAL to V71A's, by design. A literal, independent of any encoder.
CAVE_HEX = ("203e1000a437e3986132a605483a843707986432aa05443a24372695a7326132be057f32"
            "ae05423ae031a605413ac33a8437edeac636070007314437ecea2436e8ea7f00")

RATE_A = ((0xC6A68, (0, 400, 1600, 3000), (3072, 3072, 2434, 2048), True, "rec0    0 km/h"),
          (0xC6A7C, (0, 250, 1200, 3000), (3072, 3072, 2488, 1536), True, "rec1   10 km/h"),
          (0xC6A90, (0, 400, 1250, 3000), (2664, 2664, 2243, 1436), False, "rec2   50 km/h"),
          (0xC6AA4, (0, 400, 1250, 3000), (2560, 2560, 2145, 1331), False, "rec3  100 km/h"))
GAIN_B = ((0xD2A74, (3072, 3072, 2322, 1536), "gain_B rec0"),
          (0xD2AB0, (2561, 2561, 2247, 1947), "gain_B rec1"),
          (0xD2AEC, (2305, 2304, 2149, 1948), "gain_B rec2"),
          (0xD2B28, (2151, 2151, 2049, 1947), "gain_B rec3"))
SCALE = 2

FAIL = []


def check(ok, what, got=None, want=None):
    if ok:
        print(f"  ✅ {what}")
    else:
        FAIL.append(what)
        print(f"  🛑 FAIL  {what}   got {got!r}, want {want!r}")


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def decode_bcond(b, a):
    hw = u16(b, a)
    if (hw >> 7) & 0xF != 0xB:
        return None
    disp = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return hw & 0xF, a + disp


def main(path=None):
    p = Path(path) if path else Path(plain_image_path("_v71b_plain_image.bin"))
    b = p.read_bytes()
    stock = Path(stock_fw_path("code.bin")).read_bytes()
    v70 = Path(plain_image_path("_v70_plain_image.bin")).read_bytes()
    a_path = Path(plain_image_path("_v71a_plain_image.bin"))
    print(f"verify_v71b_image.py -- {p}\n  {len(b)} bytes\n")
    check(len(b) == 0x100000, "image is exactly 1 MiB", len(b), 0x100000)

    print("\nEDIT 1 -- THE RATCHET FIX (shared with V71A):")
    check(u16(b, RATCHET_ADDR) == 0x65B5, "0x454FE == 0x65B5 (`br`)", hex(u16(b, RATCHET_ADDR)), "0x65b5")
    check(decode_bcond(b, RATCHET_ADDR) == (0x5, 0x455C4),
          "0x454FE decodes as (BR, target 0x455C4) -- displacement provably unchanged",
          decode_bcond(b, RATCHET_ADDR), (0x5, 0x455C4))
    check(b[RATCHET_ADDR + 1] == stock[RATCHET_ADDR + 1], "the branch HIGH byte is STOCK")
    d = [i for i in range(0x453E0, 0x455E0) if b[i] != stock[i]]
    check(d == [RATCHET_ADDR], "[0x453E0,0x455E0) differs from STOCK at EXACTLY 0x454FE",
          [hex(x) for x in d], ["0x454fe"])

    print("\n🛑 THE V71A/V71B DISCRIMINATOR -- both `sar` sites must be STOCK on V71B:")
    for a, want in ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA)):
        check(u16(b, a) == want, f"0x{a:05X} == 0x{want:04X} (`sar 0xa`) -- NOT V71A's 0x9",
              hex(u16(b, a)), hex(want))
    check(u16(b, 0x3AB76) != 0x32A9 and u16(b, 0x3AC20) != 0x42A9,
          "V71A's `sar 0x9` edit is ABSENT ⇒ this image is not V71A")
    for a, want, what in ((0x3AB6C, 0x37E1, "r26 tap `mul r1,r6,r0`"),
                          (0x3AC16, 0x4001, "r24 tap `mov r1,r8`")):
        check(u16(b, a) == want, f"0x{a:05X} == 0x{want:04X}  {what} -- V61's kill ABSENT",
              hex(u16(b, a)), hex(want))
    for a, want in ((0x3AAB2, "200e0014"), (0x3AABC, "200e00ec")):
        check(bytes(b[a:a + 4]).hex() == want,
              f"0x{a:05X} dtorque clamp +/-0x1400 == {want} (the saturation model's anchor)",
              bytes(b[a:a + 4]).hex(), want)

    print("\nEDIT 2 -- gain_A: rec0/rec1 Y[0..3] DOUBLED, rec2/rec3 STOCK:")
    for base, xs, ys, edited, name in RATE_A:
        want_y = [y * SCALE for y in ys] if edited else list(ys)
        got_x = list(struct.unpack_from("<4h", b, base + 0x02))
        got_y = list(struct.unpack_from("<4h", b, base + 0x0A))
        check(got_x == list(xs), f"0x{base:05X} {name} X == {list(xs)} (never moves)", got_x, list(xs))
        check(got_y == want_y, f"0x{base:05X} {name} Y == {want_y}", got_y, want_y)
        check(u16(b, base) == 4 and u16(b, base + 0x12) == 0,
              f"0x{base:05X} {name} count == 4 and terminator == 0")
        for y in got_y:
            check(0 < y < 0x8000, f"0x{base:05X} {name} Y point {y} is a POSITIVE SIGNED halfword "
                  "(FUN_0003ad74 reads these through `short *`)")
        if not edited:
            check(bytes(b[base:base + 0x14]) == bytes(stock[base:base + 0x14]),
                  f"0x{base:05X} {name} is byte-identical to STOCK ⇒ highway 1.000000x is STRUCTURAL")
    check(list(struct.unpack_from("<4h", b, 0xC6010)) == [0, 640, 3200, 6400],
          "the SHARED speed cross-axis 0xC6010 == [0,640,3200,6400] counts (= 0/10/50/100 km/h)",
          list(struct.unpack_from("<4h", b, 0xC6010)), [0, 640, 3200, 6400])
    for a, want, what in ((0xC6444, 512, "r26 arm, gate gp-0x683c (DEAD)"),
                          (0xC643E, 1536, "r26 arm, state < CEIL")):
        check(u16(b, a) == want, f"0x{a:05X} == {want}  {what} -- untouched", u16(b, a), want)

    print("\nEDIT 3 -- V70's gain_B surface REVERTED; r24 is FULLY STOCK:")
    for base, ys, name in GAIN_B:
        got = list(struct.unpack_from("<4h", b, base + 0x0A))
        check(got == list(ys), f"0x{base:05X} {name} Y == {list(ys)} (STOCK)", got, list(ys))
        check(bytes(b[base:base + 0x14]) == bytes(stock[base:base + 0x14]),
              f"0x{base:05X} {name} byte-identical to STOCK")
    for a in (0xD2A88, 0xD2A9C, 0xD2AC4, 0xD2AD8, 0xD2B00, 0xD2B14, 0xD2B3C, 0xD2B50):
        check(bytes(b[a:a + 20]) == bytes(stock[a:a + 20]),
              f"0x{a:05X} mode-11/12 neighbour record byte-identical to STOCK")

    print("\nEDIT 4 -- THE CAVE (byte-identical to V71A's, by design):")
    cave = bytes(b[CAVE_BASE:CAVE_BASE + CAVE_LEN])
    check(cave.hex() == CAVE_HEX, "the whole 68-byte cave matches the expected literal",
          cave.hex(), CAVE_HEX)
    for off, want_op, what in ((0x04, 0x3D, "ld.bu -0x671d (ODD disp)"), (0x0E, 0x3C, "ld.bu -0x67fa"),
                               (0x18, 0x39, "ld.h -0x6ada"), (0x30, 0x3C, "ld.bu -0x1514"),
                               (0x3A, 0x3A, "st.b -0x1514")):
        op = (struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F
        check(op == want_op, f"cave+0x{off:02X} opcode field == 0x{want_op:02X}  ({what})",
              hex(op), hex(want_op))
    for off, want, what in ((0x0A, 0x6, "blt +4 (bit6)"), (0x14, 0xA, "bne +4 (bit5)"),
                            (0x20, 0xE, "bge +6 (bit4 POSITIVE)"), (0x24, 0xE, "bge +4 (bit4 NEG)"),
                            (0x2A, 0x6, "blt +4 (bit3 SIGN)")):
        got = struct.unpack_from("<H", cave, off)[0] & 0xF
        check(got == want, f"cave+0x{off:02X} condition nibble == 0x{want:X}  ({what})",
              hex(got), hex(want))
    stores = [off for off in (0x00, 0x04, 0x08, 0x0A, 0x0C, 0x0E, 0x12, 0x14, 0x16, 0x18, 0x1C,
                              0x1E, 0x20, 0x22, 0x24, 0x26, 0x28, 0x2A, 0x2C, 0x2E, 0x30, 0x34,
                              0x38, 0x3A, 0x3E, 0x42)
              if ((struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    check(stores == [0x3A], "GATE 1: EXACTLY ONE store, the CAN-330 payload byte", stores, [0x3A])
    hw1, hw2 = struct.unpack_from("<HH", b, 0x55C0E)
    jd = ((hw1 & 0x3F) << 16) | hw2
    jd -= 0x400000 if jd & 0x200000 else 0
    check((hw1 >> 6) & 0x3FF == 0x3FE and 0x55C0E + jd == CAVE_BASE,
          f"the hook @0x55C0E is a `jarl` landing EXACTLY on 0x{CAVE_BASE:05X}",
          hex(0x55C0E + jd), hex(CAVE_BASE))
    if a_path.exists():
        a_img = a_path.read_bytes()
        check(cave == bytes(a_img[CAVE_BASE:CAVE_BASE + CAVE_LEN]),
              "the cave is BYTE-IDENTICAL to V71A's ⇒ 🛑 the wire CANNOT separate the two builds; "
              "the .rwd FILENAME is the only pre-drive discriminator")

    print("\nCONTROL PATH -- unchanged from V69/V70:")
    check(b[0x3AA96] == 0xC5, "0x3AA96 gate byte == 0xC5 (the DEAD gp-0x683c)", hex(b[0x3AA96]), "0xc5")
    check(u16(b, 0xC6446) == 512, "0xC6446 == 512 (stock, unreachable)", u16(b, 0xC6446), 512)
    check(list(b[0xC4124:0xC4124 + 11]) == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
          "the 0xC4124 role table is unchanged")

    print("\nDIFF vs V70, fully attributed:")
    d70 = [i for i in range(START, END) if b[i] != v70[i]]
    buckets = {"cave": set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN)),
               "gain_A": {0xC6A68 + 0x0A + k for k in range(8)} | {0xC6A7C + 0x0A + k for k in range(8)},
               "gain_B surface": {a + k for a in (0xD2A7E, 0xD2A80, 0xD2ABA, 0xD2ABC) for k in (0, 1)},
               "code": {RATCHET_ADDR}, "CRC": CRC_WORDS}
    seen = set()
    for name, s in buckets.items():
        n = len([i for i in d70 if i in s])
        seen |= {i for i in d70 if i in s}
        print(f"     {name:<15s} {n:>3d} bytes")
    check(seen == set(d70), f"every one of the {len(d70)} differing bytes is attributed",
          sorted(hex(x) for x in set(d70) - seen)[:8], [])

    print("\nCRC:")
    check(walk(b) == 0, "the bridged CRC walk passes")
    check(walk_all_blocks(b) == 0, "all 50 CRC blocks pass")

    print("\n" + "=" * 100)
    if FAIL:
        print(f"🛑 {len(FAIL)} CHECK(S) FAILED:")
        for f in FAIL:
            print(f"   - {f}")
        return 1
    print("✅ ALL CHECKS PASSED -- the image on disk is V71B by exact value, not by span.")
    print("🛑 UNFLASHED. Flash only on the operator's explicit instruction, naming the file and bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
