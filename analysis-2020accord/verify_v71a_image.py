#!/usr/bin/env python3
"""verify_v71a_image.py -- EXACT-VALUE anchors for V71A, independent of the builder.

🛑 WHY THIS FILE EXISTS, AND WHY THE DIFFER IS NOT ENOUGH.
`diff_build_vs_stock.py` is **span-based, not value-based**: an address inside an existing `EDITS`
span is attributed by RANGE, so a WRONG VALUE there is silently accepted and the gate passes. Three
of V71's edited addresses are addresses earlier builds also edited -- `0x3AB76`/`0x3AC20` (V62 vs
V61), `0xD2A7E`/`0xD2ABA` (V69 x4 vs V70 x2 vs V71 STOCK) and `0x454FE` (V42 vs everything after) --
so only exact values can tell the builds apart. Run BOTH.

This re-reads the built image from disk and re-derives everything; it shares no state with
`build_v71a_tva.py` beyond the addresses.

★ V71 CARRIES A STRONGER ANCHOR THAN ANY PREVIOUS VERIFIER: its RATE LANE is byte-identical to
`_v62_plain_image.bin` AND `_v65_plain_image.bin`, and the WHOLE IMAGE is byte-identical to V62
outside the 68-byte cave, `0x454FE` and the CRC words. That equivalence IS the specification, and
checking it directly is strictly stronger than checking the control addresses one at a time -- it
also catches anything nobody thought to list.

🛑 WHAT V71 IS, so a stale reader cannot mis-anchor:
  * `0x454FE` = 0xB5 (`br`)          -- V42's state-4 ratchet kill, RESTORED (stock/V53-V70: 0xBA).
  * `0x3AB76`/`0x3AC20` = `sar 0x9`  -- V62's rate-lane doubling, RESTORED (V66-V70: `sar 0xa`).
  * mode-10 `gain_B` rec0/rec1       -- back to STOCK 3072 / 2561 (V69: x4, V70: x2).
  * gate `0x3AA96` = 0xC5, arm `0xC6446` = 512 -- V69/V70's control path, UNCHANGED.

Usage:  python verify_v71a_image.py [path-to-_v71_plain_image.bin]
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

# The 68 cave bytes, as a LITERAL -- independent of the builder's encoders by construction.
CAVE_HEX = ("203e1000a437e3986132a605483a843707986432aa05443a24372695a7326132be057f32"
            "ae05423ae031a605413ac33a8437edeac636070007314437ecea2436e8ea7f00")

# (offset from CAVE_BASE, raw hex, mnemonic) -- every one of the 25 instructions, by value.
CAVE_LISTING = (
    (0x00, "203e1000", "movea 0x10,r0,r7      bit7 LIVENESS, pre-shift weight (0x10 << 3 = 0x80)"),
    (0x04, "a437e398", "ld.bu -0x671d[gp],r6  THE MASK  (ODD disp => opcode field 0x3D)"),
    (0x08, "6132", "cmp 0x1,r6"),
    (0x0A, "a605", "blt +4"),
    (0x0C, "483a", "add 0x8,r7            bit6 = gp-0x671d != 0"),
    (0x0E, "84370798", "ld.bu -0x67fa[gp],r6  the ECU STATE byte"),
    (0x12, "6432", "cmp 0x4,r6"),
    (0x14, "aa05", "bne +4"),
    (0x16, "443a", "add 0x4,r7            bit5 = (gp-0x67fa == 4)"),
    (0x18, "24372695", "ld.h -0x6ada[gp],r6   r24 lane out, post-clip"),
    (0x1C, "a732", "sar 0x7,r6            🛑 0x7, NOT 0x9 -- a932 is the FIRST CUT's failed rung"),
    (0x1E, "6132", "cmp 0x1,r6            the POSITIVE bound"),
    (0x20, "be05", "bge +6                🛑 be05 = bge; b205 = be, which would INVERT the rung"),
    (0x22, "7f32", "cmp -0x1,r6           the NEGATIVE bound (imm5 SIGNED; -1 encodes 0x1F)"),
    (0x24, "ae05", "bge +4"),
    (0x26, "423a", "add 0x2,r7            bit4 = |gp-0x6ada| >= 128, TWO-SIDED"),
    (0x28, "e031", "cmp r0,r6             the SAME shifted value"),
    (0x2A, "a605", "blt +4"),
    (0x2C, "413a", "add 0x1,r7            bit3 = gp-0x6ada >= 0   THE SIGN"),
    (0x2E, "c33a", "shl 0x3,r7            the 5-bit field -> bits 7:3"),
    (0x30, "8437edea", "ld.bu -0x1514[gp],r6  CAN-330 payload byte4"),
    (0x34, "c6360700", "andi 0x7,r6,r6        keep live status bits 2:0"),
    (0x38, "0731", "or r7,r6"),
    (0x3A, "4437ecea", "st.b r6,-0x1514[gp]   THE ONLY STORE"),
    (0x3E, "2436e8ea", "movea -0x1518,gp,r6   the displaced hook instruction"),
    (0x42, "7f00", "jmp [lp]"),
)
# 🛑 THE CONDITION NIBBLES, as an INDEPENDENT check on the listing above: bge = 0xE, be = 0x2,
# blt = 0x6, bne = 0xA. A wrong nibble inverts a rung silently and the payload still looks legal.
COND_NIBBLES = ((0x0A, 0x6, "blt +4  (bit6)"), (0x14, 0xA, "bne +4  (bit5)"),
                (0x20, 0xE, "bge +6  (bit4 POSITIVE bound)"), (0x24, 0xE, "bge +4  (bit4 NEGATIVE)"),
                (0x2A, 0x6, "blt +4  (bit3 SIGN)"))

RATE_LANE_SPANS = ((0x3A300, 0x3AE00, "both inline rate lanes + the aggregator"),
                   (0xC6000, 0xC7000, "every gain arm, deadzone, CEIL and gain_A record"),
                   (0xD2000, 0xD2FFC, "the mode-10 gain_B surface + V60's blend cells"))

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
    return (list(struct.unpack_from("<4h", b, a + 0x02)),
            list(struct.unpack_from("<4h", b, a + 0x0A)))


def decode_bcond(b, a):
    hw = u16(b, a)
    if (hw >> 7) & 0xF != 0xB:
        return None
    disp = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return hw & 0xF, a + disp


def main(path=None):
    p = Path(path) if path else Path(plain_image_path("_v71a_plain_image.bin"))
    b = p.read_bytes()
    stock = Path(stock_fw_path("code.bin")).read_bytes()
    v62 = Path(plain_image_path("_v62_plain_image.bin")).read_bytes()
    v65 = Path(plain_image_path("_v65_plain_image.bin")).read_bytes()
    v70 = Path(plain_image_path("_v70_plain_image.bin")).read_bytes()
    v42 = Path(plain_image_path("_v42_plain_image.bin")).read_bytes()
    print(f"verify_v71a_image.py -- {p}\n  {len(b)} bytes\n")
    check(len(b) == 0x100000, "image is exactly 1 MiB", len(b), 0x100000)

    # =================================================================================================
    print("\nEDIT 1 -- THE RATCHET FIX. 🛑 A SPAN DIFFER CANNOT SEE THIS: 0xBA and 0xB5 are the same")
    print("  address, and every build V53-V70 carries the STOCK 0xBA there.")
    check(b[RATCHET_ADDR] == 0xB5, "0x454FE low byte == 0xB5 (`br`)", hex(b[RATCHET_ADDR]), "0xb5")
    check(u16(b, RATCHET_ADDR) == 0x65B5, "0x454FE halfword == 0x65B5", hex(u16(b, RATCHET_ADDR)),
          "0x65b5")
    check(decode_bcond(b, RATCHET_ADDR) == (0x5, 0x455C4),
          "0x454FE decodes as (BR, target 0x455C4) -- the DISPLACEMENT is provably unchanged",
          decode_bcond(b, RATCHET_ADDR), (0x5, 0x455C4))
    check(b[RATCHET_ADDR + 1] == stock[RATCHET_ADDR + 1],
          "the HIGH byte of the branch is STOCK ⇒ only the condition nibble moved")
    check(b[RATCHET_ADDR:RATCHET_ADDR + 2] == v42[RATCHET_ADDR:RATCHET_ADDR + 2],
          "byte-identical to V42's FLOWN halfword")
    for a, want in ((0x454F4, "24373295"), (0x454F8, "84670798"), (0x454FC, "6462")):
        n = len(want) // 2
        check(bytes(b[a:a + n]).hex() == want,
              f"0x{a:05X} instruction context == {want} "
              f"({'ld.h -0x6ace' if a == 0x454F4 else 'ld.bu -0x67fa' if a == 0x454F8 else 'cmp 0x4'})",
              bytes(b[a:a + n]).hex(), want)
    d_region = [i for i in range(0x453E0, 0x455E0) if b[i] != stock[i]]
    check(d_region == [RATCHET_ADDR],
          "[0x453E0,0x455E0) differs from STOCK at EXACTLY 0x454FE and nowhere else",
          [hex(x) for x in d_region], ["0x454fe"])

    # =================================================================================================
    print("\nEDIT 2 -- V62's `sar`, BOTH LANES. 🛑 Also invisible to a span differ: V61 edited the")
    print("  neighbouring taps and V66-V70 carry the STOCK 0xAA at these very addresses.")
    for a, want, who in ((0x3AB76, 0x32A9, "r26 lane, (stage1 x gain_A) >> 9"),
                         (0x3AC20, 0x42A9, "r24 lane, (dtorque x gain_B) >> 9")):
        got = u16(b, a)
        check(got == want, f"0x{a:05X} == 0x{want:04X}  {who}", hex(got), hex(want))
        check(got & 0x1F == 9, f"0x{a:05X} imm5 == 9 (was 10)", got & 0x1F, 9)
        check((got >> 5) & 0x3F == 0x15, f"0x{a:05X} opcode == 0x15 (`sar`) -- UNCHANGED",
              hex((got >> 5) & 0x3F), "0x15")
        check((got >> 11) & 0x1F == (u16(stock, a) >> 11) & 0x1F,
              f"0x{a:05X} reg2 field UNCHANGED from stock ⇒ only the IMMEDIATE moved")
        check(got == u16(v62, a) == u16(v65, a), f"0x{a:05X} byte-identical to V62's AND V65's")
    check(u16(b, 0x3AB70) == 0x32AA,
          "0x3AB70 (r26's FIRST shift) is STILL `sar 0xa` -- editing it pushes a `mul` operand to "
          "94% of INT32_MAX and V850 `mul` truncates the high word SILENTLY",
          hex(u16(b, 0x3AB70)), "0x32aa")
    for a, want, who in ((0x3AB6C, 0x37E1, "r26 tap `mul r1,r6,r0`"),
                         (0x3AC16, 0x4001, "r24 tap `mov r1,r8`")):
        check(u16(b, a) == want, f"0x{a:05X} == 0x{want:04X}  {who} -- V61's kill is ABSENT",
              hex(u16(b, a)), hex(want))

    # =================================================================================================
    print("\nEDIT 3 -- THE SURFACE DOSE, DROPPED. Every mode-10 gain_B record must be STOCK.")
    for a, want, name in ((0xD2A7E, 3072, "rec0 (0 km/h)  Y[0]"), (0xD2A80, 3072, "rec0 (0 km/h)  Y[1]"),
                          (0xD2ABA, 2561, "rec1 (10 km/h) Y[0]"), (0xD2ABC, 2561, "rec1 (10 km/h) Y[1]")):
        check(u16(b, a) == want == u16(stock, a),
              f"0x{a:05X} {name} == {want} (STOCK; V70 shipped {want * 2}, V69 {want * 4})",
              u16(b, a), want)
    for base, ys, name in ((0xD2A74, [3072, 3072, 2322, 1536], "rec0  0 km/h"),
                           (0xD2AB0, [2561, 2561, 2247, 1947], "rec1 10 km/h"),
                           (0xD2AEC, [2305, 2304, 2149, 1948], "rec2 50 km/h"),
                           (0xD2B28, [2151, 2151, 2049, 1947], "rec3 100 km/h")):
        check(rec(b, base)[1] == ys, f"0x{base:05X} {name} Y == {ys}", rec(b, base)[1], ys)
        check(bytes(b[base:base + 0x14]) == bytes(stock[base:base + 0x14]),
              f"0x{base:05X} {name} is byte-identical to STOCK (count, X, Y and pad)")
    # 🛑 THE NEIGHBOUR TRAP: modes 11/12 interleave at stride 0x14 and their 0 km/h records are
    # BYTE-IDENTICAL to mode 10's, so the target pattern occurs THREE times within 40 bytes.
    for a in (0xD2A88, 0xD2A9C, 0xD2AC4, 0xD2AD8, 0xD2B00, 0xD2B14, 0xD2B3C, 0xD2B50):
        check(bytes(b[a:a + 20]) == bytes(stock[a:a + 20]),
              f"0x{a:05X} mode-11/12 neighbour record byte-identical to STOCK")

    # =================================================================================================
    print("\nEDIT 4 -- THE CAVE, instruction by instruction, BY VALUE.")
    cave = bytes(b[CAVE_BASE:CAVE_BASE + CAVE_LEN])
    check(cave.hex() == CAVE_HEX, "the whole 68-byte cave matches the expected literal",
          cave.hex(), CAVE_HEX)
    for off, want, text in CAVE_LISTING:
        n = len(want) // 2
        check(cave[off:off + n].hex() == want, f"0xC4B{0x34 + off:02X}  {want:<9s} {text}",
              cave[off:off + n].hex(), want)
    check(sum(len(w) // 2 for _o, w, *_ in CAVE_LISTING) == CAVE_LEN,
          f"the listing accounts for all {CAVE_LEN} cave bytes",
          sum(len(w) // 2 for _o, w, *_ in CAVE_LISTING), CAVE_LEN)
    # 🛑🛑 THE ONE-BIT TRAP, CHECKED INDEPENDENTLY OF THE LISTING ABOVE. ld.h = 0x39 / st.h = 0x3B and
    # ld.bu = 0x3C/0x3D / st.b = 0x3A are each ONE BIT apart, and gp-0x6ada's only real instance IS
    # the st.h form carrying the same displacement halfword. Decode the OPCODE FIELD by value.
    for off, want_op, what in ((0x04, 0x3D, "ld.bu -0x671d (ODD disp)"), (0x0E, 0x3C, "ld.bu -0x67fa"),
                               (0x18, 0x39, "ld.h -0x6ada"),
                               (0x30, 0x3C, "ld.bu -0x1514"), (0x3A, 0x3A, "st.b -0x1514")):
        op = (struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F
        check(op == want_op, f"cave+0x{off:02X} opcode field == 0x{want_op:02X}  ({what})",
              hex(op), hex(want_op))
    # 🛑 THE CONDITION NIBBLES, decoded independently of the listing literals above.
    for off, want, what in COND_NIBBLES:
        got = struct.unpack_from("<H", cave, off)[0] & 0xF
        check(got == want, f"cave+0x{off:02X} condition nibble == 0x{want:X}  ({what})",
              hex(got), hex(want))
    # 🛑 THE RE-CUT'S DEFINING BYTE. V71's FIRST CUT had `sar 0x9` here and its rung read ZERO on two
    # routes; this cut has `sar 0x7` and a second, NEGATIVE bound. A span differ cannot see it.
    check(cave[0x1C:0x1E].hex() == "a732",
          "cave+0x1C is `sar 0x7,r6` (a732) -- NOT the first cut's `sar 0x9,r6` (a932), whose rung "
          "read 0/18,010 on V70 and 0/47,990 on V69", cave[0x1C:0x1E].hex(), "a732")
    check(cave[0x22:0x24].hex() == "7f32",
          "cave+0x22 is `cmp -0x1,r6` -- the SECOND bound that makes the test TWO-SIDED",
          cave[0x22:0x24].hex(), "7f32")
    check(bytes.fromhex("6532") not in cave and bytes.fromhex("8437e798") not in cave,
          "the retired gp-0x671a rung (`ld.bu -0x671a`, `cmp 0x5,r6`) is ABSENT from the cave")
    stores = [off for off in range(0, CAVE_LEN, 2)
              if ((struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F) in (0x3A, 0x3B)
              and off in [o for o, _w, *_ in CAVE_LISTING]]
    check(stores == [0x3A], "GATE 1: the cave contains EXACTLY ONE store, and it is the CAN payload "
          "byte (bits 2:0 preserved by the `andi 0x7`)", stores, [0x3A])
    # The hook, DECODED rather than pattern-matched: a jarl whose disp22 must land on CAVE_BASE.
    hw1, hw2 = struct.unpack_from("<HH", b, 0x55C0E)
    jdisp = ((hw1 & 0x3F) << 16) | hw2
    if jdisp & 0x200000:
        jdisp -= 0x400000
    check((hw1 >> 6) & 0x3FF == 0x3FE, "0x55C0E is a `jarl disp22,lp` (opcode field 0x3FE)",
          hex((hw1 >> 6) & 0x3FF), "0x3fe")
    check(0x55C0E + jdisp == CAVE_BASE,
          f"the hook's jarl target is EXACTLY the cave base 0x{CAVE_BASE:05X}",
          hex(0x55C0E + jdisp), hex(CAVE_BASE))
    check(bytes(b[0x55C0E:0x55C12]) == bytes(v70[0x55C0E:0x55C12]),
          "the hook is byte-identical to V70's (unchanged since V53/V55)")

    # =================================================================================================
    print("\nCONTROL PATH -- UNCHANGED from V69/V70. The gate must stay on the DEAD cell.")
    check(b[0x3AA96] == 0xC5, "0x3AA96 gate byte == 0xC5 (`ld.bu -0x683c[gp],r15`, 0 writers "
          "image-wide ⇒ the 0xC6446 arm is UNREACHABLE)", hex(b[0x3AA96]), "0xc5")
    check(bytes(b[0x3AA94:0x3AA98]).hex() == "847fc597", "0x3AA94 full word == 847fc597",
          bytes(b[0x3AA94:0x3AA98]).hex(), "847fc597")
    for a, want, who in ((0xC6440, 2048, "r24 arm, gp-0x671a >= CEIL"),
                         (0xC6442, 1024, "r24 arm, gp-0x671d MASK"),
                         (0xC6444, 512, "r26 arm, gp-0x683c"),
                         (0xC6446, 512, "r24 arm, gp-0x683c -- DEAD")):
        check(u16(b, a) == want, f"0x{a:05X} == {want} (stock)  {who}", u16(b, a), want)
    check(b[0xC64FA] == 5, "cal 0xC64FA (CEIL) is a BYTE == 5 -- the cave hardcodes this value",
          b[0xC64FA], 5)
    check(not (u16(b, 0xC6446) == 512 and b[0x3AA96] != 0xC5),
          "EDIT-ORDER INVARIANT: arm == 512 ⟹ gate == 0xC5 (else the arm is LIVE at ~5x BELOW the "
          "stock LERP everywhere -- V61 territory, and V61 measured WORSE on-car)")
    check(not (b[0x3AA96] == 0xFB and u16(b, 0xC6446) != 5244),
          "EDIT-ORDER INVARIANT (the other topology): gate == 0xFB ⟹ arm == 5244")
    check(list(b[0xC4124:0xC4124 + 11]) == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
          "the 0xC4124 role table is unchanged (no slot carries role 6 or 7)",
          list(b[0xC4124:0xC4124 + 11]), [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])

    # =================================================================================================
    print("\n★★ THE CENTRAL SAFETY CLAIM -- GATE 2, asserted as byte identity, not argued.")
    for lo, hi, what in RATE_LANE_SPANS:
        d62 = [i for i in range(lo, hi) if b[i] != v62[i]]
        d65 = [i for i in range(lo, hi) if b[i] != v65[i]]
        check(not d62 and not d65,
              f"[0x{lo:05X},0x{hi:05X}) byte-identical to V62 AND V65 -- {what}",
              (len(d62), len(d65)), (0, 0))
    d62 = [i for i in range(START, END) if b[i] != v62[i]]
    f62 = [i for i in d62 if i not in CRC_WORDS]
    allowed = set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN)) | {RATCHET_ADDR}
    check(set(f62) <= allowed,
          f"the WHOLE image differs from V62 ONLY inside the cave and at 0x454FE "
          f"({len(d62)} bytes total, {len(f62)} functional)",
          sorted(hex(x) for x in set(f62) - allowed)[:8], [])
    print("     ⇒ V71 IS V62's FLOWN RATE LANE + V42's FLOWN RATCHET BYTE + a new probe. Both")
    print("       component configurations have already flown on this car, flight-clean.")

    # =================================================================================================
    print("\nDIFF vs V70 (the source), fully attributed:")
    d70 = [i for i in range(START, END) if b[i] != v70[i]]
    surf = {a + k for a in (0xD2A7E, 0xD2A80, 0xD2ABA, 0xD2ABC) for k in (0, 1)}
    codeb = {RATCHET_ADDR, 0x3AB76, 0x3AC20}
    buckets = {"cave": set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN)), "surface": surf,
               "code": codeb, "CRC": CRC_WORDS}
    seen = set()
    for name, s in buckets.items():
        n = len([i for i in d70 if i in s])
        seen |= {i for i in d70 if i in s}
        print(f"     {name:<9s} {n:>3d} bytes")
    check(seen == set(d70), f"every one of the {len(d70)} differing bytes is attributed",
          sorted(hex(x) for x in set(d70) - seen)[:8], [])

    # =================================================================================================
    print("\nCRC:")
    check(walk(b) == 0, "the bridged CRC walk passes")
    check(walk_all_blocks(b) == 0, "all 50 CRC blocks pass")
    check(struct.unpack_from("<I", b, 0xD2FFC)[0] == struct.unpack_from("<I", v62, 0xD2FFC)[0],
          "the 0xD2000-block CRC EQUALS V62's = machine proof the surface revert is exact")
    check(struct.unpack_from("<I", b, 0xC6FFC)[0] == struct.unpack_from("<I", v62, 0xC6FFC)[0],
          "the CAL-block CRC EQUALS V62's = machine proof no 0xC6xxx calibration moved")

    print("\n" + "=" * 100)
    if FAIL:
        print(f"🛑 {len(FAIL)} CHECK(S) FAILED:")
        for f in FAIL:
            print(f"   - {f}")
        return 1
    print("✅ ALL CHECKS PASSED -- the image on disk is V71A by exact value, not by span.")
    print("🛑 UNFLASHED. Flash only on the operator's explicit instruction, naming the file and bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
