#!/usr/bin/env python3
"""verify/verify_v70_image.py -- EXACT-VALUE anchors for V70, independent of the builder.

🛑 WHY THIS FILE EXISTS, AND WHY THE DIFFER IS NOT ENOUGH.
`verify/diff_build_vs_stock.py` is **span-based, not value-based**: an address inside an existing `EDITS`
span is attributed by RANGE, so a WRONG VALUE there is silently accepted and the gate passes. That
matters more on V70 than on any previous build, because V70's control-path addresses are the SAME
addresses V69 edited -- only the values differ. A span differ literally cannot tell the two apart.
Run BOTH.

This re-reads the built image from disk and re-derives everything; it shares no state with
`builds/v50_v79/build_v70_tva.py` beyond the addresses.

★ V70 CARRIES ONE ANCHOR NO PREVIOUS VERIFIER COULD: **byte-identity to `_v69_plain_image.bin`
outside the cave and the four surface halfwords.** V70 is defined as "V69's topology at half the
dose plus a new cave", so that identity IS the specification of PART A, and checking it directly is
strictly stronger than checking the control addresses one at a time -- it also catches anything
nobody thought to list.

🛑 THIS FILE WAS RE-ANCHORED. V70's FIRST CUT restored V67/V68's control path (gate 0xFB, arm 5244,
surface stock) and this verifier anchored that. The operator overrode it -- *"V70 just reverts back
to V68, which has the high-speed grind #2 issue"* -- so the shipped V70 keeps **V69's** topology
(gate 0xC5 on the dead cell, arm stock 512, mode-10 gain_B rec0/rec1 at **x2**). Every control-path
anchor below therefore inverts relative to the first cut, **including the edit-order invariant**.
If you are reading this against an image built before the re-cut, it will fail -- correctly.

Usage:  python verify/verify_v70_image.py [path-to-_v70_plain_image.bin]
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

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from firmware_paths import plain_image_path                     # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCALE = 2          # 🛑 THE DOSE. V69 shipped 4; halved on the operator override. Every expected
                   # surface value below is DERIVED from stock x SCALE, never hand-written.
CAVE_BASE, CAVE_LEN = 0xC4B34, 68
CRC_WORDS = {0xC4FFC + k for k in range(4)} | {0xC6FFC + k for k in range(4)} | \
            {0xD2FFC + k for k in range(4)}

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
    p = Path(path) if path else Path(plain_image_path("_v70_plain_image.bin"))
    b = p.read_bytes()
    print(f"verify/verify_v70_image.py -- {p}\n  {len(b)} bytes\n")
    check(len(b) == 0x100000, "image is exactly 1 MiB", len(b), 0x100000)

    print("\nCONTROL PATH -- V69's TOPOLOGY, KEPT. 🛑 These are the SAME addresses V67/V68 edited;")
    print("  only the VALUES distinguish the topologies, which is exactly what a span differ cannot")
    print("  see. The gate MUST stay on the dead cell: the surface only reaches the ENGAGED lane")
    print("  when the gate is OFF, because the gate branch REPLACES the LERP rather than scaling it.")
    check(b[0x3AA96] == 0xC5, "0x3AA96 gate byte == 0xC5 (ld.bu -0x683c[gp],r15, the DEAD cell -- "
          "0 writers image-wide)", hex(b[0x3AA96]), "0xc5")
    check(bytes(b[0x3AA94:0x3AA98]) == bytes.fromhex("847fc597"),
          "0x3AA94 full word == 847fc597 (the stock gate load)",
          bytes(b[0x3AA94:0x3AA98]).hex(), "847fc597")
    check(u16(b, 0xC6446) == 512, "0xC6446 r24 LKAS arm == 512 (stock, and UNREACHABLE with the "
          "gate off)", u16(b, 0xC6446), 512)
    # 🛑🛑 THE EDIT-ORDER INVARIANT -- V69's FORM. The dangerous combination is a STOCK arm (512)
    # with the gate STILL repointed to the LIVE cell: the engaged lane is then pinned at 512 against
    # a stock LERP of 2101-3072, i.e. ~5x BELOW stock everywhere -- V61 territory, and V61 measured
    # WORSE on-car. ⚠ V70's FIRST CUT asserted the INVERSE because it shipped the V68 topology;
    # both directions are checked here so neither topology can pass in a broken combination.
    check(not (u16(b, 0xC6446) == 512 and b[0x3AA96] != 0xC5),
          "EDIT-ORDER INVARIANT (V69's form): arm == 512 ⟹ gate == 0xC5 (else the arm is LIVE at "
          "~5x BELOW the stock LERP everywhere)")
    check(not (b[0x3AA96] == 0xFB and u16(b, 0xC6446) != 5244),
          "EDIT-ORDER INVARIANT (the other topology): gate == 0xFB ⟹ arm == 5244")
    check((b[0x3AA96], u16(b, 0xC6446)) == (0xC5, 512),
          "the (gate, arm) pair is exactly V69's (0xC5, 512), not V67/V68's (0xFB, 5244)",
          (hex(b[0x3AA96]), u16(b, 0xC6446)), ("0xc5", 512))
    for a, want in ((0xC6440, 2048), (0xC6442, 1024), (0xC6444, 512)):
        check(u16(b, a) == want, f"0x{a:05X} sibling arm == {want} (stock)", u16(b, a), want)
    for a, want in ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA)):
        check(u16(b, a) == want, f"0x{a:05X} sar site == 0x{want:04X} (stock, NOT V62's 0x9)",
              hex(u16(b, a)), hex(want))

    print(f"\nSURFACE -- mode-10 rec0/rec1 at x{SCALE} (V69 shipped x4; the dose was HALVED).")
    print("  🛑 Every expected value is DERIVED from the stock halfword x SCALE, so a hand-edited")
    print("     literal cannot drift out of step with the dose.")
    for a, st, name in ((0xD2A7E, 3072, "rec0 (0 km/h)  Y[0]"),
                        (0xD2A80, 3072, "rec0 (0 km/h)  Y[1]"),
                        (0xD2ABA, 2561, "rec1 (10 km/h) Y[0]"),
                        (0xD2ABC, 2561, "rec1 (10 km/h) Y[1]")):
        want = st * SCALE
        check(u16(b, a) == want, f"0x{a:05X} {name} == {want} (= {st} x {SCALE}; V69 shipped "
              f"{st * 4})", u16(b, a), want)
        check(0 < want < 0x8000, f"0x{a:05X} {name} stays a POSITIVE SIGNED halfword "
              "(>= 0x8000 would invert the lane under an `ld.h` accessor)")
    r0y = [3072 * SCALE, 3072 * SCALE, 2322, 1536]
    r1y = [2561 * SCALE, 2561 * SCALE, 2247, 1947]
    check(rec(b, 0xD2A74)[1] == r0y, f"rec0 Y == {r0y}", rec(b, 0xD2A74)[1], r0y)
    check(rec(b, 0xD2AB0)[1] == r1y, f"rec1 Y == {r1y}", rec(b, 0xD2AB0)[1], r1y)
    check(rec(b, 0xD2A74)[0] == [0, 400, 1400, 3000], "rec0 X == [0,400,1400,3000]",
          rec(b, 0xD2A74)[0], [0, 400, 1400, 3000])
    check(rec(b, 0xD2AB0)[0] == [0, 400, 1500, 3000], "rec1 X == [0,400,1500,3000]",
          rec(b, 0xD2AB0)[0], [0, 400, 1500, 3000])
    # ★★ THE OPERATOR'S COMPLAINT, ANCHORED STRUCTURALLY. At and above 50 km/h the cross-axis
    # interpolation reads ONLY rec2 and rec3 (the axis is [0, 640, 3200, 6400] counts and 50 km/h is
    # 3204), so if BOTH are stock the delivered highway multiplier is EXACTLY 1.000000x at every
    # rate, on either candidate axis scale. It cannot drift with a re-tune -- that is why V70 edits
    # rec0/rec1 ONLY, and it is the configuration the operator reported clean on V69.
    check(rec(b, 0xD2AEC)[1] == [2305, 2304, 2149, 1948],
          "rec2 (50 km/h) Y STOCK ⇒ highway 1.000000x is STRUCTURAL, not tuned",
          rec(b, 0xD2AEC)[1], [2305, 2304, 2149, 1948])
    check(rec(b, 0xD2B28)[1] == [2151, 2151, 2049, 1947], "rec3 (100 km/h) Y STOCK",
          rec(b, 0xD2B28)[1], [2151, 2151, 2049, 1947])
    # ⚠ READ FROM THE IMAGE, not assumed: rec0's X row is [0,400,1400,3000] but rec1/rec2/rec3's is
    # [0,400,**1500**,3000]. An earlier revision of this anchor guessed 1400 for all four and FAILED
    # on its first run -- which is exactly what a value anchor is for, and why these are literals
    # read out of the ROM rather than a pattern.
    check(rec(b, 0xD2AEC)[0] == [0, 400, 1500, 3000] and rec(b, 0xD2B28)[0] == [0, 400, 1500, 3000],
          "rec2/rec3 X rows stock too ⇒ nothing about the >=50 km/h surface moved",
          (rec(b, 0xD2AEC)[0], rec(b, 0xD2B28)[0]), [0, 400, 1500, 3000])

    print("\nNEIGHBOUR TRAP -- mode 11/12 rec0 are BYTE-IDENTICAL to mode 10's stock rec0,")
    print("  so the target pattern occurs 3x within 40 bytes. Addressed absolutely, never by pattern.")
    # 🛑 Literals READ FROM the stock image, not assumed. Mode 12 is NOT a copy of mode 11 -- its
    # rec2/rec3 differ (2303/2151/1947 vs 2304/2150/1946). Assuming they matched is exactly the error
    # this anchor caught on its first run under V69, and it is why the anchors are values, not spans.
    for a, wy in ((0xD2A88, [3072, 3072, 2322, 1536]),    # m11 rec0 -- identical to m10's stock
                  (0xD2AC4, [2560, 2560, 2246, 1946]),    # m11 rec1
                  (0xD2B00, [2304, 2304, 2150, 1946]),    # m11 rec2
                  (0xD2B3C, [2150, 2150, 2048, 1946]),    # m11 rec3
                  (0xD2A9C, [3072, 3072, 2322, 1536]),    # m12 rec0 -- identical to m10's stock
                  (0xD2AD8, [2560, 2560, 2246, 1946]),    # m12 rec1
                  (0xD2B14, [2303, 2303, 2151, 1947]),    # m12 rec2 -- NOT m11's
                  (0xD2B50, [2150, 2150, 2049, 1947])):   # m12 rec3 -- NOT m11's
        check(rec(b, a)[1] == wy, f"0x{a:05X} mode-11/12 record UNTOUCHED", rec(b, a)[1], wy)

    print("\nPROBE -- three REPAIRED rungs plus the sign bit. 🛑 EVERY byte of the 68-byte cave is")
    print("  anchored below, because a cave is this kit's ONLY bricking class (V24, V27, V48B).")
    CAVE = bytes.fromhex(
        "203e8000"                                     # movea 0x80,r0,r7   bit7 LIVENESS
        "24372695" "a932" "6132" "b605" "273e4000"     # bit6 = gp-0x6ada >= +512
        "e031" "a605" "483a"                           # bit3 = gp-0x6ada >= 0   (SAME shifted r6)
        "84370798" "6a32" "ba05" "273e2000"            # bit5 = (gp-0x67fa == 10)
        "24372495" "e031" "b605" "273e1000"            # bit4 = gp-0x6adc >= 0
        "8437edea" "c6360700" "0731" "4437ecea"        # payload read / mask / or / THE ONLY STORE
        "2436e8ea" "7f00"                              # displaced movea, then jmp [lp]
    )
    check(len(CAVE) == CAVE_LEN, "the anchored cave is the PROVEN 68-byte extent", len(CAVE), CAVE_LEN)
    check(bytes(b[CAVE_BASE:CAVE_BASE + CAVE_LEN]) == CAVE,
          "0xC4B34 cave is byte-exact over all 68 bytes",
          bytes(b[CAVE_BASE:CAVE_BASE + CAVE_LEN]).hex(), CAVE.hex())
    check(b[0xC4B36] == 0x80, "0xC4B36 liveness immediate == 0x80 (bit3 CLEAR here -- on V70 bit3 is "
          "a RUNG, not a constant; V68 folds bit3 INTO this immediate as 0x88)", hex(b[0xC4B36]), "0x80")

    # 🛑🛑 THE ONE-BIT TRAP, CHECKED BY VALUE, ON ALL THREE LOADS.
    #   `ld.h`  0x39  vs  `st.h` 0x3B   -- and BOTH probed mirrors have their only real instances as
    #                                      the st.h form (0x3AD5A, 0x3AD4E) carrying the SAME hw2.
    #   `ld.bu` 0x3C  vs  `st.b` 0x3A   -- on gp-0x67fa, a LIVE state variable with 128 readers.
    for a, disp, op, name in ((0xC4B38, 0x6ADA, 0x39, "r24 lane mirror (0 readers image-wide)"),
                              (0xC4B58, 0x6ADC, 0x39, "r26 lane mirror (0 readers image-wide)"),
                              (0xC4B4C, 0x67FA, 0x3C, "the ECU STATE byte (128 readers -- LIVE)")):
        hw1, hw2 = struct.unpack("<HH", bytes(b[a:a + 4]))
        got = (hw1 >> 5) & 0x3F
        twin = {0x39: "0x3B (st.h)", 0x3C: "0x3A (st.b)"}[op]
        check(got == op, f"0x{a:05X} opcode field == 0x{op:02X} -- NOT {twin}: {name}",
              hex(got), hex(op))
        want_hw2 = ((0x10000 - disp) & 0xFFFF) | (1 if op == 0x3C else 0)
        check(hw2 == want_hw2, f"0x{a:05X} displacement halfword == 0x{want_hw2:04X} (gp-0x{disp:04x})",
              hex(hw2), hex(want_hw2))
        check((hw1 & 0x1F) == 4 and (hw1 >> 11) == 6, f"0x{a:05X} reg1 == gp(r4), reg2 == r6")
    # 🛑 the hw1-bit-5 PARITY trap on the ld.bu: -0x67fa = 0x9806 is EVEN ⇒ opcode 0x3C. Had it been
    # odd the opcode would be 0x3D, and a scan or encoder assuming one parity silently addresses the
    # NEIGHBOURING cell with every other field perfect.
    check(((0x10000 - 0x67FA) & 0xFFFF) % 2 == 0 and ((struct.unpack_from("<H", b, 0xC4B4C)[0] >> 5)
          & 0x3F) == 0x3C, "0xC4B4C ld.bu opcode parity matches the EVEN displacement 0x9806")

    check(bytes(b[0xC4B3C:0xC4B3E]) == bytes.fromhex("a932"),
          "0xC4B3C == sar 0x9,r6 (ARITHMETIC, not shr) ⇒ bit6's threshold is +512",
          bytes(b[0xC4B3C:0xC4B3E]).hex(), "a932")
    check(bytes(b[0xC4B3E:0xC4B40]) == bytes.fromhex("6132"), "0xC4B3E == cmp 0x1,r6",
          bytes(b[0xC4B3E:0xC4B40]).hex(), "6132")
    check(bytes(b[0xC4B50:0xC4B52]) == bytes.fromhex("6a32"),
          "0xC4B50 == cmp 0xa,r6 ⇒ bit5 tests STATE == 10", bytes(b[0xC4B50:0xC4B52]).hex(), "6a32")
    for a in (0xC4B46, 0xC4B5C):
        check(bytes(b[a:a + 2]) == bytes.fromhex("e031"),
              f"0x{a:05X} == cmp r0,r6 (the sign test; flown in V57's cave)",
              bytes(b[a:a + 2]).hex(), "e031")
    # the branch CONDITIONS. A wrong condition INVERTS a whole rung and still looks plausible on the
    # wire -- that is the V67 setfne/setfe lesson, and bit5's `bne` is the one that would bite.
    for a, raw, why in ((0xC4B40, "b605", "blt +6 (SIGNED; bl 0x1 is the UNSIGNED twin)"),
                        (0xC4B48, "a605", "blt +4 -- skips the 2-byte `add`, not a 4-byte movea"),
                        (0xC4B52, "ba05", "bne +6 -- 🛑 `be` (b205) would INVERT the state rung"),
                        (0xC4B5E, "b605", "blt +6")):
        check(bytes(b[a:a + 2]) == bytes.fromhex(raw), f"0x{a:05X} == {why}",
              bytes(b[a:a + 2]).hex(), raw)
    check(bytes(b[0xC4B4A:0xC4B4C]) == bytes.fromhex("483a"),
          "0xC4B4A == add 0x8,r7 -- the 2-byte bit-setter that makes bit3 affordable "
          "(byte-identical to the real instruction @0x17CD8)", bytes(b[0xC4B4A:0xC4B4C]).hex(), "483a")

    # ★ THE ORDER INVARIANT, re-derived HERE from the image's own bytes rather than trusted:
    # bit6 and bit3 read the SAME register after the SAME `sar`, at levels 1 and 0, so bit6 ⇒ bit3.
    same_reg = (struct.unpack_from("<H", b, 0xC4B3E)[0] >> 11) == \
               (struct.unpack_from("<H", b, 0xC4B46)[0] >> 11) == 6
    no_clobber = all((struct.unpack_from("<H", b, a)[0] >> 11) == 7
                     for a in (0xC4B42,))          # only the movea sits between, and it writes r7
    check(same_reg and no_clobber,
          "ORDER INVARIANT bit6 ⇒ bit3: both tests read r6 after the SAME `sar 0x9`, and the only "
          "instruction between them writes r7 ⇒ bit6=1 with bit3=0 is IMPOSSIBLE on the wire")

    # EXACTLY ONE STORE in the whole cave, and it is the CAN payload byte.
    stores = [CAVE_BASE + i for i in range(0, CAVE_LEN - 3, 2)
              if ((struct.unpack_from("<H", CAVE, i)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    check(stores == [0xC4B6E], "the cave contains EXACTLY ONE store, at 0xC4B6E (the payload byte)",
          [hex(s) for s in stores], ["0xc4b6e"])
    check(bytes(b[0xC4B76:0xC4B78]) == bytes.fromhex("7f00"), "cave ends jmp [lp]",
          bytes(b[0xC4B76:0xC4B78]).hex(), "7f00")
    check(bytes(b[0xC4B72:0xC4B76]) == bytes.fromhex("2436e8ea"),
          "0xC4B72 re-executes the displaced hook instruction `movea -0x1518,gp,r6`")
    # 🛑 A gate that cannot fail informatively is worse than no gate (the 2026-08-03 differ lesson).
    check(bytes(b[0x55C0E:0x55C12]) == bytes.fromhex("86ff26ef"),
          "0x55C0E == jarl 0xC4B34,lp (the cave entry, byte-identical to V55..V69)",
          bytes(b[0x55C0E:0x55C12]).hex(), "86ff26ef")

    print("\nSAFETY ANCHORS -- each one reverts a published conclusion if it ever drifts")
    role = list(b[0xC4124:0xC4124 + 11])
    check(role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
          "0xC4124 role table == [0,0,5,0,5,5,0,0,0,5,0] (no slot 6 or 7 ⇒ gp-0x67ac stays 0 ⇒ the "
          "FULL aggregator path runs, which is what makes bit6/bit4/bit3 mean anything)",
          role, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
    check(not any(r in (6, 7) for r in role), "no role slot is 6 or 7")
    check(bytes(b[0xC6564:0xC6564 + 40]) == bytes(40),
          "0xC6564 == 40 zero bytes ⇒ r26 structurally INERT is still the standing claim -- and "
          "bit4 is now the ON-CAR test of exactly that")
    check(u16(b, 0xC62EA) == 0, "0xC62EA low-speed lockout == 0 (carried since V53)",
          u16(b, 0xC62EA), 0)
    check(u16(b, 0xC6CD0) == 3564, "0xC6CD0 V57 private LKAS gain == 3564", u16(b, 0xC6CD0), 3564)
    check(u16(b, 0xC646C) == 891, "0xC646C shared sensor scale == 891 (stock; V57 moved the 3564 "
          "onto the private cell)", u16(b, 0xC646C), 891)
    check(u16(b, 0xC6010) == 0 and u16(b, 0xC6012) == 640 and u16(b, 0xC6014) == 3200
          and u16(b, 0xC6016) == 6400, "0xC6010 cross axis == [0,640,3200,6400] counts")

    print("\n★ THE DEFINING IDENTITY -- V70 IS V69 PLUS FOUR SURFACE HALFWORDS AND A CAVE")
    try:
        v69 = Path(plain_image_path("_v69_plain_image.bin")).read_bytes()
    except OSError as e:
        print(f"  ⚠ _v69_plain_image.bin unavailable ({e}) -- the identity anchor is NOT checked")
    else:
        cave = set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN))
        surf = {a + k for a in (0xD2A7E, 0xD2A80, 0xD2ABA, 0xD2ABC) for k in (0, 1)}
        stray = [i for i in range(0x13000, 0x100000)
                 if b[i] != v69[i] and i not in cave and i not in surf and i not in CRC_WORDS]
        check(not stray, "V70 is byte-identical to V69 over ALL of [0x13000,0x100000) except the "
              "68-byte cave, the 8 surface bytes and the CRC trailers ⇒ PART A verified as an "
              "IDENTITY, not address by address", [hex(x) for x in stray[:8]], [])
        check(b[0x3AA96] == v69[0x3AA96] and b[0xC6446:0xC6448] == v69[0xC6446:0xC6448],
              "the gate byte and the arm are UNTOUCHED relative to V69 (V70 moves the DOSE only)")
        crcs = sorted(i for i in CRC_WORDS if b[i] != v69[i])
        want = sorted([0xC4FFC + k for k in range(4)] + [0xD2FFC + k for k in range(4)])
        check(crcs == want, "exactly TWO CRC words differ from V69 -- the cave's block and the "
              "surface's block; the 0xC6000 block is untouched",
              [hex(x) for x in crcs], [hex(x) for x in want])

    print("\nCRC")
    check(walk(bytes(b), label="V70") == 0, "bootloader CRC walk PASS")
    check(walk_all_blocks(bytes(b), label="V70") == 0, "full 50-block CRC chain PASS")

    print("\n" + "=" * 90)
    if FAIL:
        print(f"🛑 {len(FAIL)} ANCHOR(S) FAILED:")
        for f in FAIL:
            print(f"   - {f}")
        sys.exit(1)
    print("✅ ALL V70 VALUE ANCHORS PASS.")
    print("   🛑 This checks VALUES. Run verify/diff_build_vs_stock.py v70 for SPAN coverage. Both, always.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
