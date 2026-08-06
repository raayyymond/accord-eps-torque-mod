#!/usr/bin/env python3
"""verify_v75_image.py -- VALUE-ANCHORED verification of a built V75 image.

🛑🛑 STATUS: V75 is **BUILT, UNFLASHED, FLIGHT CONDITIONAL** -- verification is not clearance. The
route-5d abort check put V74's own 5x-f0 prominence at 2.884 [2.301, 3.575] against a 3.0 abort
line, and its CREEP-ONLY arm at 5.844 against a 0.632 baseline; creep is exactly where LEVER CY0
acts. Nothing this file prints is a flight decision.

🛑 THIS FILE VERIFIES THE **`CY0.566-EX1.200`** CUT. V75's two edits are independently toggleable and
**the cave is byte-identical across every lever set**, so no probe payload can distinguish the cuts.
The FILENAME is the only pre-drive discriminator -- which is why both output names carry the lever
token. To verify a different cut, pass its image path and expect this file's literals to FAIL: they
state the full set on purpose.

🛑 WHY THIS EXISTS AND WHY IT IS NOT `diff_build_vs_stock.py`.
That tool is SPAN-based: it asks "which byte ranges moved?" A span check passes on the WRONG BUILD --
two images that edit the same addresses to different values are indistinguishable to it, and the kit
has a recorded case where a re-cut under the same number produced an artefact no gate could check.
This file asserts the ACTUAL VALUES at every site, including every MUST-REMAIN site, so it fails on
any image that is not V75.

🛑 IT DOES NOT SIMPLY IMPORT THE BUILDER'S NUMBERS AND COMPARE THEM TO THEMSELVES. Every expected
address and value below is re-declared here as a LITERAL -- the 13 engaged modes, all 26 dose-crank
cells with their before/after values, the cave hex, the dose table -- and then CROSS-CHECKED against
`build_v75_tva.py`'s own tables AND re-derived from the image's pointer arrays. Three independent
statements must agree, so a typo in any one of them is caught.

★ WHAT V75 IS. V74 plus **additions only**: `FactorC Y[0] := 566` and `FactorE X[1] := 200` on the
ENGAGED column of all 16 rows -- the 13 modes {2,3,5,11,14,15,17,23,26,27,29,32,33} -- taking the
live mode 26 from **50 to 137 counts (2.74x)** at the measured in-burst rate 99; plus a redesigned
probe that replaces V74's four wasted state bits with a MAGNITUDE THERMOMETER on `gp-0x6BD0` and the
back-drive gate `gp-0x6AC2`.

⚠ MODES 2 AND 3 ARE HELD at V74's `C_Y[0] = 1356` rather than written to 566 -- writing 566 would
SUBTRACT 790 counts. Verified as a NO-OP here, not as an edit.
🛑 FactorE's whole Y ROW is FROZEN, and so is the ceiling table `0xC77A0`. Both are checked
byte-identical to V74 on every engaged mode: the Y row has zero verified headroom, and the ceiling
table is explicitly NOT this build's lever.

Usage:  python verify_v75_image.py [IMAGE]  (default: the CY0.566-EX1.200 cut)
        python verify_v75_image.py --rwd PATH     (decode a .rwd and verify the payload)
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v74_tva as V74                # noqa: E402
import build_v75_tva as V75                # noqa: E402
import v72_lane_model as LM                # noqa: E402
from encode_eps import parse_x31, build_decode_table                       # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path                 # noqa: E402
from verify_bootloader_crc import walk_all_blocks                          # noqa: E402

FAILS: list[str] = []

START, END = 0x13000, 0x100000
BASE_SHA256 = "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959"   # V74
CAVE_BASE, CAVE_EXTENT = 0xC4B34, 68
HOOK_ADDR, HOOK_RETURN = 0x55C0E, 0x55C12

# =====================================================================================================
# THE INDEPENDENT STATEMENT OF THE SPEC -- literals, not imports
# =====================================================================================================
EXPECT_ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
EXPECT_DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
EXPECT_LIVE_MODE, EXPECT_MANUAL_MODE = 26, 24
EXPECT_ROW, EXPECT_KEY = 11, "TVCA4"
EXPECT_LEVER_TOKEN = "CY0.566-EX1.200"
EXPECT_HELD = (2, 3)                       # ⚠ C_Y[0] left at V74's value: 566 would have SUBTRACTED

# ---- THE DOSE CRANK.  {mode: (FactorC rec, C_Y0 before, C_Y0 after,
#                              FactorE rec, X[1] before, X[1] after)} ------------------------------
EXPECT_C_Y0_TARGET, EXPECT_E_X1_TARGET = 566, 200
EXPECT_E_X0_CARRIED = 12                   # V74's, NOT re-written by V75
EXPECT_CRANK = {
    2:  (0xCF528, 1356, 1356, 0xCF550, 450, 200),     # ⚠ HELD -- 566 would subtract 790
    3:  (0xCF53C, 1356, 1356, 0xCF564, 450, 200),     # ⚠ HELD
    5:  (0xD07D0,  419,  566, 0xD080C, 400, 200),
    11: (0xD27D0,  431,  566, 0xD280C, 400, 200),
    14: (0xD37D0,  429,  566, 0xD380C, 400, 200),
    15: (0xD37E4,  426,  566, 0xD3820, 400, 200),
    17: (0xD47D0,  419,  566, 0xD480C, 400, 200),
    23: (0xD67D0,  431,  566, 0xD680C, 400, 200),
    26: (0xD77D0,  429,  566, 0xD780C, 400, 200),     # ★★ THE LIVE MODE
    27: (0xD77E4,  426,  566, 0xD7820, 400, 200),
    29: (0xD87D0,  565,  566, 0xD880C, 400, 200),
    32: (0xD97D0,  565,  566, 0xD980C, 400, 200),
    33: (0xD97E4,  565,  566, 0xD9820, 400, 200),
}
EXPECT_CEILING_FLOOR = 512
EXPECT_CEILING_REC = (2, [300, 800], [512, 1024])

# ---- MUST NOT CHANGE ------------------------------------------------------------------------------
EXPECT_SAR = {0x3AB76: "aa32", 0x3AC20: "aa42"}
EXPECT_GATE = (0x3AA96, 0xC5)
EXPECT_ARMS = {0xC643E: 1536, 0xC6444: 512, 0xC6446: 512}
EXPECT_GAIN_A = {0xC6A68: [512, 512, 512, 512], 0xC6A7C: [512, 512, 512, 512]}
EXPECT_GAIN_A_STOCK = (0xC6A90, 0xC6AA4)
EXPECT_GAIN_B_M10_KEEP = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4}
EXPECT_LEVER_C = (0xC63A0, 2048)
EXPECT_CARRIED = (0x454FE, 0xB5)
EXPECT_ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
EXPECT_CLAMP = (0xC407E, 850)              # V74's / V73's, already flown LIVE. NOT re-written.
EXPECT_CLAMP_HARD_CAP = 1000
# 🛑 the friction records (V74's x1.5) -- V75 does NOT touch them
EXPECT_FRICTION = {2: 0xCF6D8, 3: 0xCF6E8, 5: 0xD0A54, 11: 0xD2A54, 14: 0xD3A54, 15: 0xD3A64,
                   17: 0xD4A54, 23: 0xD6A54, 26: 0xD7A54, 27: 0xD7A64, 29: 0xD8A54, 32: 0xD9A54,
                   33: 0xD9A64}
EXPECT_FRIC_Y = [-14745, -8601, -2949]

# ---- the probe ------------------------------------------------------------------------------------
EXPECT_CAVE_HEX = ("003a24373094e031c205ae058031483a85326432a605443a6932a605423a6e32a605413ac43a"
                   "e4373f95e031a205483a8437edeac636070007314437ecea2436e8ea7f00")
EXPECT_CAVE_ASM = [
    "mov 0,r7", "ld.h -27600[r4],r6", "cmp r0,r6", "be +8", "bge +4", "subr r0,r6", "add 8,r7",
    "shr 0x5,r6", "cmp 4,r6", "blt +4", "add 4,r7", "cmp 9,r6", "blt +4", "add 2,r7",
    "cmp 14,r6", "blt +4", "add 1,r7", "shl 0x4,r7", "ld.hu -27330[r4],r6", "cmp r0,r6", "be +4",
    "add 8,r7", "ld.bu -5396[r4],r6", "andi 0x0007,r6,r6", "or r7,r6", "st.b r6,-5396[r4]",
    "movea 0xeae8,r4,r6", "jmp [lp]"]
EXPECT_DAMP_DISP, EXPECT_BACKDRIVE_DISP = 0x6BD0, 0x6AC2
EXPECT_STATE_DISP = 0x67FA                 # ⚠ V74's cell -- V75's cave must NOT read it
EXPECT_DAMP_CENSUS, EXPECT_BACKDRIVE_CENSUS = (5, 3), (8, 4)
EXPECT_SHADOWS = (0x4C39, 0x4CF2, 0x4CC6)  # gp-0x67fa's, gp-0x6bd0's, gp-0x6ac2's
EXPECT_PROBE_MASK = 0xF8
EXPECT_BITS = {"bit7 damper != 0": 0x80, "bit6 |damper| >= 128": 0x40,
               "bit5 |damper| >= 288": 0x20, "bit4 |damper| >= 448": 0x10,
               "bit3 back-drive != 0": 0x08}
EXPECT_MAG_THRESHOLDS = (128, 288, 448)
EXPECT_LEGAL_PAYLOADS = (0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8)
EXPECT_HOOK_RETURN_INSN = "083a"           # `mov 0x8,r7` ⇒ r7 is PROVABLY DEAD across the hook

# ---- the dose, at the measured burst rates --------------------------------------------------------
EXPECT_BURST_RATE = 99          # the IN-BURST p50 [94.2, 113.0]. 🛑 NOT the out-of-burst 9.4.
EXPECT_BURST_RATE_69HZ = 127
EXPECT_DOSE = {2: 189, 3: 189, 5: 179, 11: 512, 14: 179, 15: 137, 17: 137, 23: 137, 26: 137,
               27: 137, 29: 137, 32: 137, 33: 137}
EXPECT_DOSE_V74 = {2: 168, 3: 168, 5: 94, 11: 390, 14: 95, 15: 49, 17: 49, 23: 50, 26: 50, 27: 49,
                   29: 66, 32: 66, 33: 66}
EXPECT_DOSE_69HZ = {2: 201, 3: 201, 5: 211, 11: 512, 14: 212, 15: 181, 17: 180, 23: 181, 26: 181,
                    27: 181, 29: 180, 32: 180, 33: 180}
EXPECT_LIVE_RATIO = 2.74

# ---- CRC / diff accounting ------------------------------------------------------------------------
EXPECT_TRAILERS = [0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC,
                   0xD8FFC, 0xD9FFC]
# ⚠ CELLS, not bytes: modes 29/32/33 move 565 -> 566, which changes only the LOW byte.
EXPECT_CELLS_MOVED = {"FactorC": 11, "FactorE": 13}
EXPECT_DIFF_BY_LEVER = {"cave": 57, "FactorC Y[0]": 19, "FactorE X[1]": 26}
CRC_SKIPPED = (0xC5000, 0xC5FFC)


def check(cond, ok_msg, fail_msg):
    if cond:
        print(f"  ✅ {ok_msg}")
    else:
        FAILS.append(fail_msg)
        print(f"  🛑 {fail_msg}")
    return bool(cond)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    n = u16(b, base)
    return (n, list(struct.unpack_from(f"<{n}h", b, base + 2)),
            list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n)))


def rec_len(b, base):
    return 4 + 4 * u16(b, base)


def cross_check_against_builder():
    """🛑 THE TWO STATEMENTS OF THE SPEC MUST AGREE. Importing alone could never catch a typo."""
    print("=" * 100)
    print("  CROSS-CHECK -- this file's literals against build_v75_tva.py's own tables")
    ok = True
    ok &= check(tuple(EXPECT_ENGAGED) == V75.ENGAGED_EXPECTED,
                "the ENGAGED mode set agrees", f"ENGAGED differs: {EXPECT_ENGAGED} vs "
                f"{V75.ENGAGED_EXPECTED}")
    ok &= check(tuple(EXPECT_DISENGAGED) == V75.DISENGAGED_EXPECTED,
                "the DISENGAGED mode set agrees", "DISENGAGED differs")
    ok &= check(not (set(EXPECT_ENGAGED) & set(EXPECT_DISENGAGED)),
                "the two columns are DISJOINT (stated independently of the image)",
                "the two columns OVERLAP")
    ok &= check((EXPECT_C_Y0_TARGET, EXPECT_E_X1_TARGET) == (V75.TARGET_C_Y0, V75.TARGET_E_X1),
                f"the targets C_Y[0] := {EXPECT_C_Y0_TARGET} / X[1] := {EXPECT_E_X1_TARGET} agree",
                "the targets differ")
    ok &= check(V75.LEVERS == {"CY0": True, "EX1": True} and V75.lever_token() == EXPECT_LEVER_TOKEN,
                f"the builder's LEVERS are the FULL set and its token is {EXPECT_LEVER_TOKEN!r}",
                f"the builder's lever token is {V75.lever_token()!r}, not {EXPECT_LEVER_TOKEN!r} -- "
                "this file's literals describe the FULL cut only")
    ok &= check(EXPECT_LEVER_TOKEN in V75.bin_out() and EXPECT_LEVER_TOKEN in V75.out_rwd(),
                "both output filenames carry the lever token",
                "a filename does not carry the lever token")
    ok &= check(tuple(EXPECT_HELD) == tuple(V75.HELD_AT_BASE),
                f"the HELD set {list(EXPECT_HELD)} agrees", "the HELD set differs")
    ok &= check(EXPECT_E_X0_CARRIED == V75.E_X0_CARRIED, "the carried X[0] = 12 agrees",
                "the carried X[0] differs")
    ok &= check(EXPECT_CAVE_HEX == V75.build_cave()[0].hex(),
                "the cave hex agrees with the builder's emitted bytes", "the cave hex differs")
    ok &= check(len(EXPECT_CAVE_HEX) // 2 == CAVE_EXTENT == 68,
                f"the expected cave is exactly the proven {CAVE_EXTENT}-byte extent",
                f"the expected cave is {len(EXPECT_CAVE_HEX) // 2}B")
    ok &= check(tuple(EXPECT_BITS.values()) == (V75.BIT_DAMP_NZ, V75.BIT_MAG128, V75.BIT_MAG288,
                                                V75.BIT_MAG448, V75.BIT_BACKDRIVE)
                and EXPECT_PROBE_MASK == V75.PROBE_MASK,
                "the five probe bits and the mask agree", "the probe bits differ")
    ok &= check(EXPECT_MAG_THRESHOLDS == V75.MAG_THRESHOLDS,
                f"the thermometer thresholds {list(EXPECT_MAG_THRESHOLDS)} agree",
                "the thresholds differ")
    ok &= check(list(EXPECT_LEGAL_PAYLOADS) == V75.LEGAL_PAYLOADS,
                f"the {len(EXPECT_LEGAL_PAYLOADS)} reachable payloads agree "
                f"{[hex(p) for p in EXPECT_LEGAL_PAYLOADS]}", "the legal payload set differs")
    ok &= check((EXPECT_DAMP_DISP, EXPECT_BACKDRIVE_DISP) == (V75.DAMP_DISP, V75.BACKDRIVE_DISP),
                "the two probed cells agree", "the probed cells differ")
    ok &= check(tuple(sorted(EXPECT_SHADOWS)) == tuple(sorted(V75.SHADOW_DISPS)),
                "the three lockstep shadows agree", "the shadow set differs")
    ok &= check(EXPECT_BURST_RATE == V75.BURST_RATE, "the burst rate agrees", "the burst rate differs")
    ok &= check(EXPECT_CLAMP == (V74.CLAMP_ADDR, V74.CLAMP_VALUE), "the clamp agrees",
                "the clamp differs")
    ok &= check(EXPECT_FRIC_Y == V74.FRICTION_Y_NEW,
                "the carried V74 friction Y row agrees", "the friction Y row differs")
    ok &= check(EXPECT_TRAILERS == sorted(EXPECT_TRAILERS) and len(EXPECT_TRAILERS) == 10,
                "the expected trailer list is well-formed", "the trailer list is malformed")
    # ★ the thermometer must actually be a thermometer -- checked on the builder's own wire model
    bad = [v for v in range(0, 0x10000, 7)
           if (V75.wire_byte4(v, 0) & EXPECT_PROBE_MASK) not in EXPECT_LEGAL_PAYLOADS]
    ok &= check(not bad, "the builder's wire model only ever emits LEGAL payloads",
                f"the wire model emits illegal payloads at {bad[:4]}")
    return ok


def verify_columns(img):
    print("\n  THE MODE COLUMNS -- re-derived from the config table on the IMAGE UNDER TEST")
    eng, dis, rows = set(), set(), []
    for n in range(16):
        o = 0xCD000 + n * 0x24
        key = bytes(img[o:o + 5]).decode("ascii", "replace")
        m = list(img[0xCD012 + n * 0x24:0xCD012 + n * 0x24 + 4])
        rows.append((n, key, m))
        dis.update(m[:2])
        eng.update(m[2:])
    check(tuple(sorted(eng)) == tuple(EXPECT_ENGAGED),
          f"the ENGAGED column (e014/e015) derives to {sorted(eng)}",
          f"ENGAGED derives to {sorted(eng)}, expected {list(EXPECT_ENGAGED)}")
    check(tuple(sorted(dis)) == tuple(EXPECT_DISENGAGED),
          f"the DISENGAGED column (e012/e013) derives to {sorted(dis)}",
          f"DISENGAGED derives to {sorted(dis)}")
    check(not (eng & dis),
          "🛑 the two columns are DISJOINT ON THE IMAGE ⇒ writing the engaged column cannot reach "
          "manual or parking steering", f"the columns overlap on {sorted(eng & dis)}")
    r = rows[EXPECT_ROW]
    check(r[1] == EXPECT_KEY and r[2][0] == EXPECT_MANUAL_MODE and r[2][2] == EXPECT_LIVE_MODE,
          f"row {EXPECT_ROW} is {EXPECT_KEY!r} -> manual {EXPECT_MANUAL_MODE}, ENGAGED "
          f"{EXPECT_LIVE_MODE} (V73's on-car probe)", f"row {EXPECT_ROW} is {r[1]!r} {r[2]}")


def verify_crank(img, base):
    print(f"\n  THE DOSE CRANK -- FactorC Y[0] := {EXPECT_C_Y0_TARGET} · FactorE X[1] := "
          f"{EXPECT_E_X1_TARGET}, ADD-ONLY")
    for mode in EXPECT_ENGAGED:
        cb, c_before, c_after, eb, x1_before, x1_after = EXPECT_CRANK[mode]
        # 🛑 the address is RE-DERIVED from the pointer array, then matched to the literal.
        d_cb, d_eb = u32(img, 0xC9E9C + mode * 4), u32(img, 0xC9F84 + mode * 4)
        if not check(d_cb == cb and d_eb == eb,
                     f"m{mode:2d}: FactorC 0x{cb:05X} / FactorE 0x{eb:05X} re-derive from the arrays",
                     f"m{mode}: arrays give 0x{d_cb:05X}/0x{d_eb:05X}, expected 0x{cb:05X}/0x{eb:05X}"):
            continue
        n_c, cx, cy = rec(img, cb)
        n_e, ex, ey = rec(img, eb)
        _n, bcx, bcy = rec(base, cb)
        _n, bex, bey = rec(base, eb)
        ok = (n_c == 4 and n_e == 4
              and bcy[0] == c_before and cy[0] == c_after and cy[1:] == bcy[1:] and cx == bcx
              and bex[1] == x1_before and ex[1] == x1_after
              and ex[0] == bex[0] == EXPECT_E_X0_CARRIED and ex[2:] == bex[2:])
        check(ok, f"m{mode:2d}: C_Y {bcy} -> {cy}   E_X {bex} -> {ex}",
              f"m{mode}: C_Y {bcy}->{cy}, E_X {bex}->{ex} does not match the spec")
        # 🛑 ADD-ONLY, both cells, stated as a direction rather than as a value.
        check(cy[0] >= bcy[0] and ex[1] <= bex[1],
              f"m{mode:2d}: both edits are ADDITIONS (C_Y[0] up, X[1] left)",
              f"m{mode}: an edit SUBTRACTS -- C_Y[0] {bcy[0]}->{cy[0]}, X[1] {bex[1]}->{ex[1]}")
        # 🛑 FactorE's Y ROW IS FROZEN -- it has zero verified headroom.
        check(ey == bey,
              f"m{mode:2d}: FactorE's Y row is FROZEN at V74's {ey}",
              f"m{mode}: FactorE Y moved {bey} -> {ey} -- the Y axis has ZERO verified headroom")
        check(all(b > a for a, b in zip(ex, ex[1:])) and all(b >= a for a, b in zip(ey, ey[1:])),
              f"m{mode:2d}: FactorE X strictly increasing and Y monotone non-decreasing",
              f"m{mode}: FactorE X {ex} / Y {ey} broke monotonicity")
        # the HELD modes must be a NO-OP on FactorC
        if mode in EXPECT_HELD:
            check(c_after == c_before and c_after > EXPECT_C_Y0_TARGET,
                  f"m{mode:2d}: ⚠ HELD at {c_after} -- writing {EXPECT_C_Y0_TARGET} would have "
                  f"SUBTRACTED {c_after - EXPECT_C_Y0_TARGET} counts",
                  f"m{mode}: expected a HELD no-op, got {c_before} -> {c_after}")
        else:
            check(c_after == EXPECT_C_Y0_TARGET,
                  f"m{mode:2d}: C_Y[0] written to the full target {EXPECT_C_Y0_TARGET}",
                  f"m{mode}: C_Y[0] is {c_after}, expected {EXPECT_C_Y0_TARGET}")
        # FactorB / FactorD FLAT 1024 and the ceiling record, per mode
        for arr, name in ((0xC9CCC, "FactorB"), (0xC9DB4, "FactorD")):
            b_ = u32(img, arr + mode * 4)
            check(set(rec(img, b_)[2]) == {1024},
                  f"m{mode:2d}: {name} @0x{b_:05X} is FLAT 1024 ⇒ the chain reduces to (C*E)>>10",
                  f"m{mode}: {name} is not flat 1024")
        ce = u32(img, 0xC77A0 + mode * 4)
        check(rec(img, ce) == EXPECT_CEILING_REC and
              bytes(img[ce:ce + rec_len(img, ce)]) == bytes(base[ce:ce + rec_len(base, ce)]),
              f"m{mode:2d}: the ceiling @0x{ce:05X} is {EXPECT_CEILING_REC[2]} and byte-identical to "
              "V74 -- 0xC77A0 is explicitly NOT this build's lever",
              f"m{mode}: the ceiling record moved or is {rec(img, ce)}")
        # the friction record -- V74's x1.5, carried untouched
        fr = u32(img, 0xCBE74 + mode * 4)
        check(fr == EXPECT_FRICTION[mode] and rec(img, fr)[2] == EXPECT_FRIC_Y and
              bytes(img[fr:fr + rec_len(img, fr)]) == bytes(base[fr:fr + rec_len(base, fr)]),
              f"m{mode:2d}: the friction record 0x{fr:05X} carries V74's {EXPECT_FRIC_Y} untouched",
              f"m{mode}: friction 0x{fr:05X} moved -- V75 does not edit it")


def verify_no_clip_and_dose(img, base):
    """★ THE SURFACE RULE plus PEAK INVARIANCE -- the structural claim, re-derived."""
    print("\n  THE SURFACE -- no-clip, peak invariance, and the DOSE, recomputed from THESE bytes")
    speeds, rates = list(range(0, 14001, 32)), list(range(0, 4501, 20))

    def axes(b, mode):
        return ([LM.lerp_int(v, *rec(b, u32(b, 0xC9E9C + mode * 4))[1:]) for v in speeds],
                [LM.lerp_int(r, *rec(b, u32(b, 0xC9F84 + mode * 4))[1:]) for r in rates])

    def dose(b, mode, v, r):
        c = LM.lerp_int(v, *rec(b, u32(b, 0xC9E9C + mode * 4))[1:])
        e = LM.lerp_int(r, *rec(b, u32(b, 0xC9F84 + mode * 4))[1:])
        bb = LM.lerp_int(v, *rec(b, u32(b, 0xC9CCC + mode * 4))[1:])
        d = LM.lerp_int(r, *rec(b, u32(b, 0xC9DB4 + mode * 4))[1:])
        x = (1024 * bb) >> 10
        x = (x * c) >> 10
        x = (x * d) >> 10
        return (x * e) >> 10

    print(f"      {'mode':>4} {'dose@99':>8} {'V74':>6} {'x':>5} {'expected':>9} {'dose@127':>9} "
          f"{'raisedMax':>10} {'ptsRaised':>10} {'peak':>6} {'peak V74':>9}")
    for mode in EXPECT_ENGAGED:
        cs, es = axes(img, mode)
        cb_, eb_ = axes(base, mode)
        bad, raised, aff = [], 0, 0
        for si, (ci, cbv) in enumerate(zip(cs, cb_)):
            for ri, (ei, ebv) in enumerate(zip(es, eb_)):
                now, was = (ci * ei) >> 10, (cbv * ebv) >> 10
                if now > was:
                    raised += 1
                    aff = max(aff, now)
                    if now > EXPECT_CEILING_FLOOR:
                        bad.append((speeds[si], rates[ri], was, now))
        peak, peak_b = (max(cs) * max(es)) >> 10, (max(cb_) * max(eb_)) >> 10
        d, d_b = dose(img, mode, 0, EXPECT_BURST_RATE), dose(base, mode, 0, EXPECT_BURST_RATE)
        star = "  ★★ LIVE" if mode == EXPECT_LIVE_MODE else ""
        print(f"      {mode:4d} {d:8d} {d_b:6d} {d / max(d_b, 1):5.2f} {EXPECT_DOSE[mode]:9d} "
              f"{dose(img, mode, 0, EXPECT_BURST_RATE_69HZ):9d} {aff:10d} {raised:10d} {peak:6d} "
              f"{peak_b:9d}{star}")
        check(not bad,
              f"m{mode:2d}: every raised point stays at or below the floor {EXPECT_CEILING_FLOOR}",
              f"m{mode}: RAISES the surface above its floor at {len(bad)} point(s), e.g. {bad[:3]} "
              "⇒ a hard-clipping element inside a feedback loop")
        check(peak == peak_b, f"m{mode:2d}: the GLOBAL peak is unchanged at {peak}",
              f"m{mode}: the global peak moved {peak_b} -> {peak} -- C_Y0 and X[1] must not touch it")
        check(d == EXPECT_DOSE[mode] and d_b == EXPECT_DOSE_V74[mode],
              f"m{mode:2d}: dose at rate {EXPECT_BURST_RATE} = {EXPECT_DOSE_V74[mode]} -> {d}",
              f"m{mode}: dose is {d} (V74 {d_b}), the spec says {EXPECT_DOSE[mode]} "
              f"(V74 {EXPECT_DOSE_V74[mode]})")
        check(dose(img, mode, 0, EXPECT_BURST_RATE_69HZ) == EXPECT_DOSE_69HZ[mode],
              f"m{mode:2d}: dose at the 6-9 Hz rate {EXPECT_BURST_RATE_69HZ} = "
              f"{EXPECT_DOSE_69HZ[mode]}",
              f"m{mode}: dose at {EXPECT_BURST_RATE_69HZ} is "
              f"{dose(img, mode, 0, EXPECT_BURST_RATE_69HZ)}, expected {EXPECT_DOSE_69HZ[mode]}")
    live = dose(img, EXPECT_LIVE_MODE, 0, EXPECT_BURST_RATE)
    live_b = dose(base, EXPECT_LIVE_MODE, 0, EXPECT_BURST_RATE)
    check(abs(live / live_b - EXPECT_LIVE_RATIO) < 0.005,
          f"★★ THE LIVE MODE {EXPECT_LIVE_MODE}: {live_b} -> {live} counts = "
          f"{live / live_b:.2f}x at the measured burst rate {EXPECT_BURST_RATE}",
          f"the live ratio is {live / live_b:.3f}, the spec says {EXPECT_LIVE_RATIO}")
    # ⊕ the ZERO-RATE property that keeps the relay from chattering: X[0] = 12 is CARRIED, and
    # FactorE's Y[0] is 0 on the live mode, so the dose still vanishes with the rate.
    check(dose(img, EXPECT_LIVE_MODE, 0, 0) == 0 and dose(img, EXPECT_LIVE_MODE, 0, 9) == 0,
          f"★ the live mode still delivers ZERO at rate 0 and at the out-of-burst rate 9 ⇒ the "
          "magnitude vanishes with the rate; no discontinuity, no chatter mechanism",
          f"the live mode delivers {dose(img, EXPECT_LIVE_MODE, 0, 0)} at rate 0 -- V72's error")


def verify_must_not_change(img, base, stock):
    print("\n  🛑 THE KEEP-LIST")
    for addr, hx in EXPECT_SAR.items():
        check(bytes(img[addr:addr + 2]).hex() == hx == bytes(stock[addr:addr + 2]).hex(),
              f"0x{addr:05X} = {hx} (stock `sar`) -- grind #2's fix is an ABSENCE",
              f"0x{addr:05X} is {bytes(img[addr:addr + 2]).hex()}, expected the stock {hx}")
    check(img[EXPECT_GATE[0]] == EXPECT_GATE[1], f"the gate 0x{EXPECT_GATE[0]:05X} = 0xC5",
          f"the gate is 0x{img[EXPECT_GATE[0]]:02X}")
    for addr, val in EXPECT_ARMS.items():
        check(u16(img, addr) == val, f"0x{addr:05X} = {val}",
              f"0x{addr:05X} is {u16(img, addr)}, expected {val}")
    for b_, y in EXPECT_GAIN_A.items():
        got = list(struct.unpack_from("<4h", img, b_ + 0x0A))
        check(got == y, f"gain_A 0x{b_:05X} Y = {y} (V72's r26 cut, kept EXACTLY)",
              f"gain_A 0x{b_:05X} Y is {got}, expected {y}")
    for b_ in EXPECT_GAIN_A_STOCK:
        check(bytes(img[b_:b_ + 0x14]) == bytes(stock[b_:b_ + 0x14]),
              f"gain_A 0x{b_:05X} is byte-STOCK (the r26 cut is PARTIAL, by design)",
              f"gain_A 0x{b_:05X} is not stock")
    for b_, want in EXPECT_GAIN_B_M10_KEEP.items():
        got = list(struct.unpack_from("<4h", img, b_ + 0x0A))
        check(got == want and bytes(img[b_:b_ + 0x14]) == bytes(base[b_:b_ + 0x14]),
              f"gain_B mode-10 0x{b_:05X} Y = {got}, byte-identical to V74",
              f"gain_B mode-10 0x{b_:05X} Y is {got}, expected {want}")
    check(u16(img, EXPECT_LEVER_C[0]) == EXPECT_LEVER_C[1],
          f"V72's LEVER C 0x{EXPECT_LEVER_C[0]:05X} = {EXPECT_LEVER_C[1]}", "LEVER C moved")
    check(img[EXPECT_CARRIED[0]] == EXPECT_CARRIED[1],
          f"the carried 0x{EXPECT_CARRIED[0]:05X} = 0x{EXPECT_CARRIED[1]:02X}", "0x454FE moved")
    a, want = EXPECT_ROLE_TABLE
    got = list(img[a:a + len(want)])
    check(got == want and not any(r in (6, 7) for r in got),
          f"the role table 0x{a:05X} = {want} (no slot carries role 6 or 7)",
          f"the role table is {got}")
    addr, val = EXPECT_CLAMP
    check(u16(img, addr) == val == u16(base, addr) and val <= EXPECT_CLAMP_HARD_CAP < 1024,
          f"the clamp 0x{addr:05X} = {val}, UNCHANGED from V74 and below the aggregator's "
          "+/-0x400 ZERO-REJECT",
          f"0x{addr:05X} is {u16(img, addr)}, expected {val} on BOTH V74 and V75")
    bad = [(hex(arr), m) for arr in (0xCBE74, 0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0)
           for m in range(34) if u32(img, arr + m * 4) != u32(stock, arr + m * 4)]
    check(not bad, "all six pointer arrays are byte-STOCK across modes 0-33 ⇒ every edited table is "
          "reachable only through an unmoved pointer", f"a pointer moved: {bad[:6]}")
    check(bytes(img[0xCD000:0xCD000 + 16 * 0x24]) == bytes(stock[0xCD000:0xCD000 + 16 * 0x24]),
          "the config table 0xCD000 is byte-STOCK", "the config table moved")
    # ★★ THE SAFETY ARGUMENT: every DISENGAGED-column record byte-identical to V74
    bad = []
    for mode in EXPECT_DISENGAGED:
        for arr, name in ((0xC9CCC, "FactorB"), (0xC9E9C, "FactorC"), (0xC9DB4, "FactorD"),
                          (0xC9F84, "FactorE"), (0xC77A0, "ceiling"), (0xCBE74, "friction")):
            b_ = u32(img, arr + mode * 4)
            n = rec_len(img, b_)
            if bytes(img[b_:b_ + n]) != bytes(base[b_:b_ + n]):
                bad.append((mode, name, hex(b_)))
    check(not bad,
          f"★★ ALL {len(EXPECT_DISENGAGED)} DISENGAGED modes x 6 records are byte-identical to V74 "
          "⇒ manual and parking steering are UNTOUCHED",
          f"a DISENGAGED record MOVED: {bad[:6]}")
    # ★ the general form of the hybrid defect: a UNIFORM Y row must stay uniform
    recs = {u32(img, arr + m * 4)
            for arr in (0xCBE74, 0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0) for m in range(34)}
    recs |= set(EXPECT_GAIN_A) | set(EXPECT_GAIN_B_M10_KEEP) | set(EXPECT_GAIN_A_STOCK)
    hyb, uniform = [], 0
    for b_ in sorted(recs):
        n_b, _x, yb = rec(base, b_)
        n_o, _x2, yo = rec(img, b_)
        if n_b != n_o:
            hyb.append((hex(b_), "count", n_b, n_o))
        elif len(set(yb)) == 1 and len(yb) > 1:
            uniform += 1
            if len(set(yo)) != 1:
                hyb.append((hex(b_), "hybrid", yb, yo))
    check(not hyb, f"all {len(recs)} records keep their point count and all {uniform} with a UNIFORM "
          "Y row on V74 are still uniform ⇒ no hybrid was manufactured",
          f"PARTIAL WRITE detected: {hyb[:4]}")


def verify_cave(img):
    print("\n  THE PROBE")
    got = bytes(img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    check(got.hex() == EXPECT_CAVE_HEX and len(got) == CAVE_EXTENT == 68,
          f"the cave is the proven {CAVE_EXTENT}-byte extent and matches the expected hex exactly",
          f"the cave is {len(got)}B / {got.hex()}")
    asm = [m for _a, _r, m in V75.redisassemble_cave(got)]
    check(asm == EXPECT_CAVE_ASM,
          "the cave RE-DISASSEMBLES (raw Python decoder, not a Ghidra database) to exactly the "
          f"expected {len(EXPECT_CAVE_ASM)} instructions -- and there is NO padding",
          f"the re-disassembly is {asm}")
    check("nop" not in asm and not any(m.startswith("??") for m in asm),
          "every one of the 68 bytes decodes to a real instruction",
          "the cave contains a nop or an undecoded halfword")
    stores = [m for m in asm if m.startswith(("st.b", "st.h"))]
    check(len(stores) == 1 and stores[0] == "st.b r6,-5396[r4]",
          "GATE 1: EXACTLY ONE store, and it is the CAN-330 payload byte",
          f"the cave contains stores {stores}")
    check("ld.hu -27330[r4],r6" in asm and not any(m.startswith("ld.w") for m in asm),
          "🛑 the back-drive load is `ld.hu` and NOT `ld.w` -- opcode 0x3F with an even hw2 would be "
          "a MISALIGNED 32-bit read spanning gp-0x6ac2 AND gp-0x6ac0",
          "the back-drive load decoded as ld.w -- the hw2 LSB is clear")
    check(asm.count("subr r0,r6") == 1 and "sub r0,r6" not in asm,
          "the negate is `subr r0,r6` (op 0x0C) -- `sub` (0x0D) would compute r6 - 0 and vanish",
          "the negate is missing or is a `sub`")
    brs = [(i, m) for i, m in enumerate(asm)
           if m.startswith(("be ", "bne ", "blt ", "bge ", "b?"))]
    check([m for _i, m in brs] == ["be +8", "bge +4", "blt +4", "blt +4", "blt +4", "be +4"],
          "the six branches are exactly `be +8 · bge +4 · blt +4 x3 · be +4`, all FORWARD",
          f"the branches are {[m for _i, m in brs]}")
    # 🛑 every branch target must be an emitted instruction boundary, decoded from the FIELD
    bounds = [a for a, _r, _m in V75.redisassemble_cave(got)]
    off = [(a, m) for a, _r, m in V75.redisassemble_cave(got)
           if m.startswith(("be ", "bge ", "blt "))]
    check(all(a + int(m.split("+")[1]) in bounds for a, m in off),
          "every branch lands on an emitted instruction BOUNDARY (displacement decoded from the "
          "Format III field split, not from the constant we meant to encode)",
          f"a branch misses a boundary: {[(hex(a), m) for a, m in off]}")
    check(asm[brs[0][0] - 1] == "cmp r0,r6" and asm[brs[1][0] - 1] == "be +8",
          "🛑 FLAG LIVENESS: ONE `cmp r0,r6` feeds BOTH the `be` and the `bge`, with only the `be` "
          "between them -- a Bcond does not touch the PSW",
          "the be/bge pair does not read the same cmp's flags")
    for i, m in brs[2:5]:
        check(asm[i - 1].startswith("cmp ") and asm[i + 1].startswith("add "),
              f"the magnitude rung at {i} is cmp / blt / add, adjacent",
              f"the magnitude rung at {i} is malformed: {asm[i - 1:i + 2]}")
    # ★ the two `add 8,r7` mean DIFFERENT bits; only their position around the `shl` says which
    a8 = [i for i, m in enumerate(asm) if m == "add 8,r7"]
    shl = asm.index("shl 0x4,r7")
    check(len(a8) == 2 and a8[0] < shl < a8[1],
          "★ the two `add 8,r7` straddle the `shl 0x4,r7` -- the FIRST is bit7 (pre-shift weight 8 "
          "-> 0x80), the SECOND is bit3 (post-shift weight 8 -> 0x08)",
          f"the `add 8,r7` pair is at {a8} around the shl at {shl}")
    check("or r7,r6" in asm and "or r6,r7" not in asm,
          "the only `or` is the MERGE `or r7,r6` -- the swapped `or r6,r7` (0639) is a real "
          "instruction elsewhere in this image and is absent here",
          "the cave contains the swapped `or r6,r7`")
    check(bytes(img[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR),
          f"the hook 0x{HOOK_ADDR:05X} is `jarl 0x{CAVE_BASE:05X}`", "the hook is not our jarl")
    check(bytes(img[HOOK_RETURN:HOOK_RETURN + 2]).hex() == EXPECT_HOOK_RETURN_INSN,
          f"0x{HOOK_RETURN:05X} is `mov 0x8,r7` ⇒ r7 is PROVABLY DEAD across the hook",
          f"0x{HOOK_RETURN:05X} is {bytes(img[HOOK_RETURN:HOOK_RETURN + 2]).hex()}")
    # GATE 1 as a MEASUREMENT: both probed cells, by raw byte scan
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    for disp, (nr, nw) in ((EXPECT_DAMP_DISP, EXPECT_DAMP_CENSUS),
                           (EXPECT_BACKDRIVE_DISP, EXPECT_BACKDRIVE_CENSUS)):
        reads, writes, cave = V74.cell_census(img, disp, span)
        check(len(reads) == nr and len(writes) == nw and len(cave) == 1 and
              cave[0][1].startswith("ld."),
              f"gp-0x{disp:04X}: {len(reads)}r / {len(writes)}w firmware, and the cave adds EXACTLY "
              "ONE load and writes it NEVER",
              f"gp-0x{disp:04X}: {len(reads)}r/{len(writes)}w, cave {cave}")
    for disp in EXPECT_SHADOWS:
        _r, _w, shadow = V74.cell_census(img, disp, span)
        check(not shadow, f"the lockstep shadow gp-0x{disp:04X} is untouched by the cave",
              f"the cave touches the shadow gp-0x{disp:04X}: {shadow}")
    _r, _w, stale = V74.cell_census(img, EXPECT_STATE_DISP, span)
    check(not stale,
          f"⊕ the cave does NOT read V74's state cell gp-0x{EXPECT_STATE_DISP:04X} -- a surviving "
          "V74 cave would still carry its four wasted bits",
          f"the cave still reads gp-0x{EXPECT_STATE_DISP:04X} -- this is a V74 cave")


def verify_crc_and_diff(img, base, stock):
    print("\n  CRC AND THE FULL DIFF ACCOUNTING")
    check(walk_all_blocks(img) == 0, "the full CRC chain: 50/50 blocks PASS", "the CRC chain FAILED")
    diff = [i for i in range(START, END) if img[i] != base[i]]
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    c_cells = {v[0] + 0x0A + k for v in EXPECT_CRANK.values() for k in (0, 1)}
    e_cells = {v[3] + 0x04 + k for v in EXPECT_CRANK.values() for k in (0, 1)}

    touched = [CAVE_BASE] + sorted(c_cells | e_cells)
    blocks = sorted({tuple(V53.owning_block(img, a)) for a in touched})
    check([b[1] for b in blocks] == EXPECT_TRAILERS,
          f"exactly {len(EXPECT_TRAILERS)} blocks own an edit: {[hex(t) for t in EXPECT_TRAILERS]}",
          f"the owning blocks are {[hex(b[1]) for b in blocks]}")
    crc_only = {b[1] + k for b in blocks for k in range(4)}
    func = [d for d in diff if d not in crc_only]
    check(all(any(img[t + k] != base[t + k] for k in range(4)) for t in EXPECT_TRAILERS),
          "every expected trailer actually moved", "a trailer did not move")

    def attribute(d):
        return ("cave" if d in span else "FactorC Y[0]" if d in c_cells else
                "FactorE X[1]" if d in e_cells else None)

    stray = [hex(d) for d in func if attribute(d) is None]
    check(not stray, f"every one of the {len(func)} functional bytes is ATTRIBUTABLE to a named "
          "edit", f"UNATTRIBUTED functional bytes: {stray[:12]}")
    by = {}
    for d in func:
        by[attribute(d)] = by.get(attribute(d), 0) + 1
    check(by == EXPECT_DIFF_BY_LEVER and len(func) == sum(EXPECT_DIFF_BY_LEVER.values()),
          f"the functional diff vs V74 is exactly {sum(EXPECT_DIFF_BY_LEVER.values())} bytes: {by}",
          f"got {len(func)} bytes, {by}, expected {EXPECT_DIFF_BY_LEVER}")
    # ⚠ CELLS, not bytes -- 565 -> 566 moves only the low byte, so a byte count would mislead.
    moved_c = sum(1 for m, v in EXPECT_CRANK.items()
                  if img[v[0] + 0x0A:v[0] + 0x0C] != base[v[0] + 0x0A:v[0] + 0x0C])
    moved_e = sum(1 for m, v in EXPECT_CRANK.items()
                  if img[v[3] + 0x04:v[3] + 0x06] != base[v[3] + 0x04:v[3] + 0x06])
    check((moved_c, moved_e) == (EXPECT_CELLS_MOVED["FactorC"], EXPECT_CELLS_MOVED["FactorE"]),
          f"{moved_c} FactorC cells and {moved_e} FactorE cells moved -- the {len(EXPECT_HELD)} HELD "
          "modes are no-ops on FactorC",
          f"({moved_c}, {moved_e}) cells moved, expected {tuple(EXPECT_CELLS_MOVED.values())}")
    all_edits = set(span) | c_cells | e_cells
    check(not [a for a in all_edits if CRC_SKIPPED[0] <= a < CRC_SKIPPED[1]],
          f"NOTHING of the {len(all_edits)} edited bytes lands in "
          f"[0x{CRC_SKIPPED[0]:05X},0x{CRC_SKIPPED[1]:05X}) -- the CRC-skipped block, V40 ignition "
          "precedent", "an edit landed in the CRC-skipped block")
    inherited = {i for i in range(START, END) if base[i] != stock[i]}
    ds = [i for i in range(START, END) if img[i] != stock[i] and i not in crc_only]
    stray_s = [hex(d) for d in ds if attribute(d) is None and d not in inherited]
    check(not stray_s, f"vs STOCK: {len(ds)} functional bytes, all attributable to a V75 edit or to "
          "the carried V38->V74 lineage", f"UNATTRIBUTED vs stock: {stray_s[:12]}")


def verify(img, base, stock, label):
    print("=" * 100)
    print(f"  VERIFYING {label}")
    print(f"    SHA256 {hashlib.sha256(img).hexdigest()}")
    check(len(img) == 0x100000, "the image is 1 MiB", f"the image is {len(img)} bytes")
    check(hashlib.sha256(base).hexdigest() == BASE_SHA256,
          "the comparison base IS the recorded V74 image (by SHA256, not by shape)",
          "the base is NOT V74")
    verify_columns(img)
    verify_crank(img, base)
    verify_no_clip_and_dose(img, base)
    verify_must_not_change(img, base, stock)
    verify_cave(img)
    verify_crc_and_diff(img, base, stock)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=None)
    ap.add_argument("--rwd", default=None)
    args = ap.parse_args()

    base = Path(plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin")).read_bytes()
    stock = Path(stock_fw_path("code.bin")).read_bytes()

    if not cross_check_against_builder():
        print("\n🛑 THE TWO STATEMENTS OF THE SPEC DISAGREE. Nothing below can be trusted.")
        return 1

    if args.rwd:
        rwd = Path(args.rwd).read_bytes()
        FF.assert_x31_checksum(rwd, "the .rwd under test")
        info = parse_x31(rwd)
        decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        img = bytearray(base)
        img[START:END] = bytes(info["encs"][0]).translate(decode)
        verify(bytes(img), base, stock, f"{args.rwd} (decoded payload)")
    else:
        p = Path(args.image) if args.image \
            else Path(plain_image_path("_v75_CY0.566-EX1.200_magprobe_plain_image.bin"))
        verify(p.read_bytes(), base, stock, str(p))

    print("\n" + "=" * 100)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"     - {f}")
        return 1
    print(f"  ✅ V75 VERIFIED. The ENGAGED column {list(EXPECT_ENGAGED)}")
    print(f"     carries FactorC Y[0] := {EXPECT_C_Y0_TARGET} (11 modes; {list(EXPECT_HELD)} HELD at")
    print(f"     V74's higher value) and FactorE X[1] := {EXPECT_E_X1_TARGET} (all 13). The")
    print(f"     DISENGAGED column {list(EXPECT_DISENGAGED)}")
    print("     is byte-identical to V74, record by record ⇒ manual and parking steering untouched.")
    print(f"     The live mode {EXPECT_LIVE_MODE} delivers {EXPECT_DOSE[EXPECT_LIVE_MODE]} counts at "
          f"the burst rate {EXPECT_BURST_RATE} -- {EXPECT_LIVE_RATIO}x V74's "
          f"{EXPECT_DOSE_V74[EXPECT_LIVE_MODE]}.")
    print("     Every raised point stays at or below the ceiling floor, the global peak is unchanged")
    print("     on every mode, FactorE's Y row and the ceiling table 0xC77A0 are frozen, the cave and")
    print("     its re-disassembly match byte-for-byte, both probe-cell censuses and all three")
    print("     lockstep shadows are clean, and the CRC chain and full diff accounting PASS.")
    print("  🛑 Verification is not authorisation. Flash only on the operator's explicit")
    print("     instruction, naming the file and the bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
