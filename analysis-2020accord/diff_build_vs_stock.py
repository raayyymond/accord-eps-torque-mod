"""
diff_build_vs_stock.py -- enumerate EVERY difference between a BUILD and the STOCK 39990-TVA-A160 image.

Usage:  python diff_build_vs_stock.py [v62|v63|...]      (default: v63)

Answers "what has this firmware actually had done to it, in total" -- not the per-build delta. Groups
the raw byte diff into named edits, and 🛑 FAILS LOUDLY on any changed byte it cannot attribute, so an
unaccounted edit cannot hide inside a summary.

🛑 Diff is restricted to [0x13000, 0x100000). build_*.full_image() writes 0xFF filler below 0x13000 and
a naive whole-file diff reports ~51,000 bogus bytes.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from firmware_paths import plain_image_path   # noqa: E402

STOCK = r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\stock_fw_dump\code.bin"
LO, HI = 0x13000, 0x100000

# CRC trailers -- bookkeeping, not behaviour. Every 4 KiB block plus the two big spans.
CRC_WORDS = [(0x13000, 0xC4FFC), (0xC5000, 0xC5FFC), (0xC6000, 0xC6FFC), (0xC7000, 0xCCFFC)]
CRC_WORDS += [(b, b + 0xFFC) for b in range(0xCD000, 0x100000, 0x1000)]

# (lo, hi_exclusive, build, one-line what-it-does)
# `build` = the build whose value V62 currently carries. Where an earlier build first moved the bytes and
# a later one changed them again, both are named. All attributions were derived EMPIRICALLY by walking
# every _v*_plain_image.bin in the archive, not from the lineage doc.
EDITS = [
    (0x13109, 0x1310A, "V22", "part-number string byte '-' -> ',' -- the modified-firmware marker"),
    (0x14120, 0x14121, "V22", "part-number string byte '-' -> ',' (second copy)"),
    (0xC61B2, 0xC61B6, "V22->V38", "LKAS forward-path clamps 512 -> 1024 -> 2048, tracking the gain"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce state-machine cals (gentle-EME fix)"),
    (0xC64B4, 0xC64B8, "V36", "STEER_STATUS debounce state-machine cals (second group)"),
    (0xC64B8, 0xC64B9, "V37", "DTC-0x49 fail-counter gate 112 -> 0xFF -- resolved the gentle EME"),
    (0xC64DE, 0xC64DF, "V18", "re-engage ramp 17 -> 27 (lengthens re-engage; road-validated)"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor, FLOAT set 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor, FLOAT set 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor, INT set 1024 -> 5120 (the lockstep twin)"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper (driver-pushback surface) flat Y 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank -- all 8 selector-reachable records"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0 (steer-to-zero; confirmed on-car)"),
    (0x55C0E, 0x55C12, "V53/V55", "cave HOOK -- the call that reaches the telemetry probe"),
    (0xC4B34, 0xC4B78, "V39->V59", "CODE CAVE: 0x14A byte4 telemetry probe (V59 boost-index thermometer)"),
    (0x2A1F0, 0x2A1F2, "V57", "forward LKAS reader re-pointed 0x746C -> 0x7CD0 (onto the private cell)"),
    (0xC6CD0, 0xC6CD2, "V57", "PRIVATE LKAS forward gain cell = 3564 (the decoupling's new cell)"),
    (0x3AB76, 0x3AB78, "V62", "r26 torsion-bar RATE lane: sar 0xa -> sar 0x9  (DOUBLE the lane)"),
    (0x3AC20, 0x3AC22, "V62", "r24 torsion-bar RATE lane: sar 0xa -> sar 0x9  (DOUBLE the lane)"),
    (0xC643E, 0xC6440, "V63", "r26 RATE lane, OSCILLATION-only gain arm (state>=5) 1536 -> 3072"),
    (0xC6440, 0xC6442, "V63", "r24 RATE lane, OSCILLATION-only gain arm (state>=5) 2048 -> 4096"),
]

# 🛑 Deliberately NOT in the list, and worth stating because it surprises people:
#   0xC646C (the shared sensor scale) is back at STOCK 891. V22/V38 raised it 891->1782->3564, and V57
#   REVERTED it, moving the 3564 onto the private cell 0xC6CD0 so only the forward LKAS path sees it.
#   0x454FE (V42's state-4 governor ratchet fix) is likewise absent -- V42's chain 1 is NOT in the
#   V53->V62 line. Both are asserted below so the claim cannot rot.
ASSERT_STOCK = [
    (0xC646C, "shared sensor scale -- reverted to stock by V57, gain lives at 0xC6CD0 now"),
    (0x454FE, "V42 state-4 governor bne->br -- NOT carried into this build line"),
]


def main():
    # ⚠ the EDITS loops below MUST NOT rebind this name -- they use `ebuild`.
    build = (sys.argv[1] if len(sys.argv) > 1 else "v63").lower().lstrip("v")
    v62 = open(str(plain_image_path(f"_v{build}_plain_image.bin")), "rb").read()
    stock = open(STOCK, "rb").read()
    assert len(v62) == len(stock) == 0x100000

    diff = [i for i in range(LO, HI) if v62[i] != stock[i]]
    crc_bytes = {i for lo, hi in CRC_WORDS for i in range(hi, hi + 4)}

    print(f"V{build.upper()} vs STOCK 39990-TVA-A160, range [0x{LO:X},0x{HI:X})")
    print(f"total differing bytes: {len(diff)}\n")

    attributed, rows = set(), []
    for lo, hi, ebuild, what in EDITS:
        hits = [i for i in diff if lo <= i < hi]
        attributed |= set(hits)
        if hits:
            rows.append((lo, hi, ebuild, what, len(hits)))

    rows.sort()
    print(f"{'address':>18}  {'build':<9} {'n':>3}  what")
    print("-" * 110)
    for lo, hi, ebuild, what, n in rows:
        span = f"0x{lo:05X}" if hi - lo <= 2 else f"0x{lo:05X}-0x{hi - 1:05X}"
        print(f"{span:>18}  {ebuild:<9} {n:>3}  {what}")

    crc_changed = sorted(set(diff) & crc_bytes - attributed)
    unattributed = sorted(set(diff) - attributed - crc_bytes)

    print("-" * 110)
    print(f"{'CRC trailers':>18}  {'--':<9} {len(crc_changed):>3}  "
          f"recomputed block checksums (bookkeeping, not behaviour)")
    print(f"\nfunctional bytes changed : {len(attributed)}")
    print(f"CRC bookkeeping bytes    : {len(crc_changed)}")
    print(f"UNATTRIBUTED             : {len(unattributed)}")
    if unattributed:
        print("\n🛑 UNATTRIBUTED BYTES -- every one must be explained before this summary can be trusted:")
        for i in unattributed[:60]:
            print(f"   0x{i:05X}  stock {stock[i]:02X} -> v62 {v62[i]:02X}")
        raise SystemExit("unattributed differences exist")

    print("\nasserted STILL STOCK (things people assume are changed and are not):")
    for a, why in ASSERT_STOCK:
        same = v62[a:a + 2] == stock[a:a + 2]
        print(f"   0x{a:05X}  {'STOCK' if same else '*** CHANGED ***':<15} {why}")
        assert same, f"0x{a:05X} is not stock -- this file's claim is wrong"

    # the two V62 edits, spelled out at halfword level
    own = sorted({lo for lo, _hi, b, _w in EDITS if b.lower() == f"v{build}"})
    print(f"\nV{build.upper()}'s own edits, halfword level:")
    for a in own:
        s = struct.unpack_from("<H", stock, a)[0]
        v = struct.unpack_from("<H", v62, a)[0]
        if a < 0xC0000:   # code halfword: show the Format-II field split
            print(f"   0x{a:05X}  {s:04X} -> {v:04X}   sar imm5 {s & 0x1F} -> {v & 0x1F}, "
                  f"opcode 0x{(s >> 5) & 0x3F:02X} and reg2 r{(s >> 11) & 0x1F} UNCHANGED")
        else:             # calibration halfword: show the decimal values
            print(f"   0x{a:05X}  {s:5d} -> {v:5d}   (calibration halfword, LE)")


if __name__ == "__main__":
    main()
