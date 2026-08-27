#!/usr/bin/env python3
"""verify/verify_v71c_image.py -- EXACT-VALUE anchors for V71C, independent of the builder.

🛑 THE THREE SIBLINGS ARE SPAN-IDENTICAL IN PLACES AND ONLY VALUES SEPARATE THEM:

                     0x3AA96   0xC6446   0xC6444   0x3AB76/0x3AC20   gain_A rec0/rec1   cave+0x1A
    V71A              0xC5       512       512        sar 0x9            STOCK            0x26
    V71B              0xC5       512       512        sar 0xa            x2               0x24
    **V71C**        **0xFB**   **5244**  **3072**     sar 0xa            STOCK            0x26
    (V67/V68)         0xFB      5244       512        sar 0xa            STOCK             --

All three carry `0x454FE = 0xB5` and a stock `gain_B` surface. `verify/diff_build_vs_stock.py` is span-based
and cannot tell any of them apart; this file asserts V71C's column by exact value and asserts the
other columns are ABSENT.

🛑 `0xC6444` IS LIVE ON THIS BUILD. On V71A/V71B the gate at 0x3AA96 is 0xC5 ⇒ `lp` derives from
gp-0x683c, which has ZERO writers, so the `ld.hu 0x7444[tp],r8` @0x3AB5E never executes and the cal
is null by construction. V71C repoints the gate, so it runs on every engaged tick. Do not carry the
"null lever" strike across builds -- it is a property of the GATE byte, not of the cal.

Usage:  python verify/verify_v71c_image.py [path-to-_v71c_plain_image.bin]
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
from firmware_paths import plain_image_path, stock_fw_path         # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
CAVE_BASE, CAVE_LEN = 0xC4B34, 68
RATCHET_ADDR = 0x454FE
CRC_WORDS = {a + k for a in (0xC4FFC, 0xC6FFC, 0xD2FFC) for k in range(4)}

# Byte-identical to V71A's cave: V71C doses r24 through a scalar ARM, so it watches the same mirror.
CAVE_HEX = ("203e1000a437e3986132a605483a843707986432aa05443a24372695a7326132be057f32"
            "ae05423ae031a605413ac33a8437edeac636070007314437ecea2436e8ea7f00")

GAIN_A = ((0xC6A68, (0, 400, 1600, 3000), (3072, 3072, 2434, 2048), "gain_A rec0    0 km/h"),
          (0xC6A7C, (0, 250, 1200, 3000), (3072, 3072, 2488, 1536), "gain_A rec1   10 km/h"),
          (0xC6A90, (0, 400, 1250, 3000), (2664, 2664, 2243, 1436), "gain_A rec2   50 km/h"),
          (0xC6AA4, (0, 400, 1250, 3000), (2560, 2560, 2145, 1331), "gain_A rec3  100 km/h"))
GAIN_B = ((0xD2A74, (3072, 3072, 2322, 1536), "gain_B rec0"),
          (0xD2AB0, (2561, 2561, 2247, 1947), "gain_B rec1"),
          (0xD2AEC, (2305, 2304, 2149, 1948), "gain_B rec2"),
          (0xD2B28, (2151, 2151, 2049, 1947), "gain_B rec3"))
R26_ARM_CEILING = 6553          # 2^31 / ((5120 * 65535) >> 10) -- V850 `mul` truncates SILENTLY

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
    p = Path(path) if path else Path(plain_image_path("_v71c_plain_image.bin"))
    b = p.read_bytes()
    stock = Path(stock_fw_path("code.bin")).read_bytes()
    v67 = Path(plain_image_path("_v67_plain_image.bin")).read_bytes()
    v70 = Path(plain_image_path("_v70_plain_image.bin")).read_bytes()
    print(f"verify/verify_v71c_image.py -- {p}\n  {len(b)} bytes\n")
    check(len(b) == 0x100000, "image is exactly 1 MiB", len(b), 0x100000)

    print("\nEDIT 1 -- THE RATCHET FIX (shared with V71A/V71B):")
    check(u16(b, RATCHET_ADDR) == 0x65B5, "0x454FE == 0x65B5 (`br`)",
          hex(u16(b, RATCHET_ADDR)), "0x65b5")
    check(decode_bcond(b, RATCHET_ADDR) == (0x5, 0x455C4),
          "0x454FE decodes as (BR, 0x455C4) -- displacement provably unchanged",
          decode_bcond(b, RATCHET_ADDR), (0x5, 0x455C4))
    d = [i for i in range(0x453E0, 0x455E0) if b[i] != stock[i]]
    check(d == [RATCHET_ADDR], "[0x453E0,0x455E0) differs from STOCK at EXACTLY 0x454FE",
          [hex(x) for x in d], ["0x454fe"])

    print("\n★ EDIT 2 -- V67/V68's CONTROL PATH, with the r26 CUT REMOVED. The V71C column:")
    check(b[0x3AA96] == 0xFB, "0x3AA96 gate byte == 0xFB ⇒ `ld.bu -0x6806[gp],r15` (LKAS applying) "
          "-- NOT V71A/V71B's dead 0xC5", hex(b[0x3AA96]), "0xfb")
    check(bytes(b[0x3AA94:0x3AA98]).hex() == "847ffb97",
          "0x3AA94 full word == 847ffb97 (only the displacement byte moved)",
          bytes(b[0x3AA94:0x3AA98]).hex(), "847ffb97")
    check(u16(b, 0xC6446) == 5244, "0xC6446 r24 arm == 5244 -- EXACTLY V67/V68's value",
          u16(b, 0xC6446), 5244)
    check(u16(b, 0xC6444) == 3072,
          "0xC6444 r26 arm == 3072 ★ THE NEW LEVER (V67/V68 have 512 = the ~6x CUT)",
          u16(b, 0xC6444), 3072)
    check(u16(b, 0xC6444) <= R26_ARM_CEILING,
          f"0xC6444 is inside the INT32 ceiling {R26_ARM_CEILING} -- V850 `mul` @0x3AB72 discards "
          "the high word SILENTLY", u16(b, 0xC6444), f"<= {R26_ARM_CEILING}")
    check(u16(b, 0xC6444) == 3072 and 327675 * 3072 < 2 ** 31,
          "INT32 headroom at 0x3AB72 is 46.87% -- EXACTLY stock/V71A, no headroom lost "
          "(V71B's 6144 would be 93.75%)")
    check(u16(b, 0xC643E) == 1536, "0xC643E (r26's state<CEIL arm) == 1536, untouched",
          u16(b, 0xC643E), 1536)
    # 🛑 BOTH DIRECTIONS OF THE EDIT-ORDER INVARIANT.
    check(not (b[0x3AA96] == 0xFB and u16(b, 0xC6446) == 512),
          "INVARIANT: a LIVE gate with a STOCK r24 arm is REFUSED (that pins the engaged lane ~5x "
          "BELOW stock -- V61 territory, measured WORSE on-car)")
    check(not (b[0x3AA96] == 0xFB and u16(b, 0xC6444) == 512),
          "INVARIANT: a LIVE gate with a STOCK r26 arm is REFUSED (that is V67/V68's ~6x CUT, which "
          "is exactly what this build removes)")
    check(not (b[0x3AA96] == 0xC5 and u16(b, 0xC6446) != 512),
          "INVARIANT: a DEAD gate with a non-stock arm is REFUSED")

    print("\nEDIT 3 -- both `sar` sites STOCK, both surfaces STOCK:")
    for a, want in ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA)):
        check(u16(b, a) == want, f"0x{a:05X} == 0x{want:04X} (`sar 0xa`) -- NOT V71A's 0x9",
              hex(u16(b, a)), hex(want))
    check(u16(b, 0x3AB76) != 0x32A9 and u16(b, 0x3AC20) != 0x42A9,
          "V71A's `sar 0x9` edit is ABSENT ⇒ this image is not V71A")
    for base, xs, ys, name in GAIN_A:
        got = list(struct.unpack_from("<4h", b, base + 0x0A))
        check(got == list(ys), f"0x{base:05X} {name} Y == {list(ys)} (STOCK -- NOT V71B's x2)",
              got, list(ys))
        check(bytes(b[base:base + 0x14]) == bytes(stock[base:base + 0x14]),
              f"0x{base:05X} {name} byte-identical to STOCK")
    for base, ys, name in GAIN_B:
        got = list(struct.unpack_from("<4h", b, base + 0x0A))
        check(got == list(ys), f"0x{base:05X} {name} Y == {list(ys)} (STOCK)", got, list(ys))
    for a in (0xD2A88, 0xD2A9C, 0xD2AC4, 0xD2AD8, 0xD2B00, 0xD2B14, 0xD2B3C, 0xD2B50):
        check(bytes(b[a:a + 20]) == bytes(stock[a:a + 20]),
              f"0x{a:05X} mode-11/12 neighbour record byte-identical to STOCK")

    print("\nEDIT 4 -- THE CAVE (byte-identical to V71A's; V71C doses r24 too):")
    cave = bytes(b[CAVE_BASE:CAVE_BASE + CAVE_LEN])
    check(cave.hex() == CAVE_HEX, "the whole 68-byte cave matches the expected literal",
          cave.hex(), CAVE_HEX)
    check(cave[0x1A] == 0x26,
          "cave+0x1A == 0x26 ⇒ bit4/bit3 watch gp-0x6ada (r24) -- NOT V71B's 0x24 (gp-0x6adc)",
          hex(cave[0x1A]), "0x26")
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
    check(cave[0x1C:0x1E].hex() == "a732", "cave+0x1C is `sar 0x7,r6` -- the two-sided |x| >= 128 rung",
          cave[0x1C:0x1E].hex(), "a732")
    stores = [off for off in range(0, CAVE_LEN, 2)
              if ((struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F) in (0x3A, 0x3B)
              and off in (0x00, 0x04, 0x0E, 0x18, 0x30, 0x34, 0x3A, 0x3E)]
    check(stores == [0x3A], "GATE 1: EXACTLY ONE store, the CAN-330 payload byte", stores, [0x3A])
    hw1, hw2 = struct.unpack_from("<HH", b, 0x55C0E)
    jd = ((hw1 & 0x3F) << 16) | hw2
    jd -= 0x400000 if jd & 0x200000 else 0
    check((hw1 >> 6) & 0x3FF == 0x3FE and 0x55C0E + jd == CAVE_BASE,
          f"the hook @0x55C0E is a `jarl` landing EXACTLY on 0x{CAVE_BASE:05X}",
          hex(0x55C0E + jd), hex(CAVE_BASE))

    print("\n★ THE SAFETY CLAIM -- byte-identity to V67, which flew twice flight-clean:")
    for lo, hi, what in ((0x3A300, 0x3AE00, "both rate lanes, the aggregator AND the gate"),
                         (0xD2000, 0xD2FFC, "the gain_B surface + V60's blend cells")):
        d = [i for i in range(lo, hi) if b[i] != v67[i]]
        check(not d, f"[0x{lo:05X},0x{hi:05X}) byte-identical to V67 -- {what}",
              [hex(x) for x in d[:6]], [])
    dcal = [i for i in range(0xC6000, 0xC6FFC) if b[i] != v67[i]]
    check(set(dcal) <= {0xC6444, 0xC6445},
          "the whole CAL block differs from V67 ONLY inside the r26 arm halfword 0xC6444 "
          "(512 = 0x0200 and 3072 = 0x0C00 share a zero low byte, so only 0xC6445 moves)",
          [hex(x) for x in dcal], ["<= 0xc6444/0xc6445"])
    d67 = [i for i in range(START, END) if b[i] != v67[i]]
    f67 = [i for i in d67 if i not in CRC_WORDS]
    allowed = set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN)) | {RATCHET_ADDR, 0xC6444, 0xC6445}
    check(set(f67) <= allowed,
          f"the WHOLE image differs from V67 ONLY inside the cave, at 0x454FE and at the r26 arm "
          f"({len(d67)} bytes total)", sorted(hex(x) for x in set(f67) - allowed)[:8], [])
    print("     ⇒ V71C IS V67's FLOWN CONTROL PATH + V42's FLOWN RATCHET BYTE + ONE CAL HALFWORD.")

    print("\nDIFF vs V70 (the carrier), fully attributed:")
    d70 = [i for i in range(START, END) if b[i] != v70[i]]
    buckets = {"cave": set(range(CAVE_BASE, CAVE_BASE + CAVE_LEN)),
               "gain_B surface": {a + k for a in (0xD2A7E, 0xD2A80, 0xD2ABA, 0xD2ABC) for k in (0, 1)},
               "arms": {0xC6444, 0xC6445, 0xC6446, 0xC6447},
               "code": {RATCHET_ADDR, 0x3AA96}, "CRC": CRC_WORDS}
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
    check(struct.unpack_from("<I", b, 0xD2FFC)[0] == struct.unpack_from("<I", v67, 0xD2FFC)[0],
          "the 0xD2000-block CRC EQUALS V67's = machine proof the surface is back at V67/stock")

    print("\n" + "=" * 100)
    if FAIL:
        print(f"🛑 {len(FAIL)} CHECK(S) FAILED:")
        for f in FAIL:
            print(f"   - {f}")
        return 1
    print("✅ ALL CHECKS PASSED -- the image on disk is V71C by exact value, not by span.")
    print("🛑 UNFLASHED. Flash only on the operator's explicit instruction, naming the file and bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
