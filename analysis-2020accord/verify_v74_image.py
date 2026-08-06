#!/usr/bin/env python3
"""verify_v74_image.py -- VALUE-ANCHORED verification of a built V74 image.

🛑 WHY THIS EXISTS AND WHY IT IS NOT `diff_build_vs_stock.py`.
That tool is SPAN-based: it asks "which byte ranges moved?" A span check passes on the WRONG BUILD --
two images that edit the same addresses to different values are indistinguishable to it, and the kit
has a recorded case where a re-cut under the same number produced an artefact no gate could check.
This file asserts the ACTUAL VALUES at every site, including every MUST-REMAIN site, so it fails on
any image that is not V74.

🛑 IT DOES NOT SIMPLY IMPORT THE BUILDER'S NUMBERS AND COMPARE THEM TO THEMSELVES. Every expected
address and value below is re-declared here as a LITERAL -- the 13 engaged modes, all 39 LEVER E'
cells with their before/after values, all 13 friction records, the cave hex, the dose table -- and
then CROSS-CHECKED against `build_v74_tva.py`'s own tables AND re-derived from the image's pointer
arrays. Three independent statements must agree, so a typo in any one of them is caught.

★ WHAT V74 IS. V73's on-car probe read the damper's mode selector and the answer was **not 10**: the
car is config row 11 `TVCA4`, running mode **24 disengaged / 26 ENGAGED**. V74 moves every lever onto
the **ENGAGED COLUMN (e014/e015) OF ALL 16 ROWS** -- the 13 modes {2,3,5,11,14,15,17,23,26,27,29,32,
33}. The disengaged column is **disjoint** and is verified byte-identical to V73, record by record,
so manual and parking steering are untouched. That disjointness is checked HERE from the table, not
taken on trust.

🛑 THIS FILE VERIFIES THE `x0_12_addonly` CUT. Two earlier V74 cuts are retired, both renamed
`SUPERSEDED-DO-NOT-FLASH-…` with the REASON in the name, and neither was ever flashed:
    `…x0_6_staleX0…`      -- built against a stale `X[0] = 6`
    `…x0_12_hybridD2A7E…` -- correct `X[0]`, but it carried the WITHDRAWN 0xD2A7E/0xD2ABA revert,
                             leaving `[3072, 5244, 5244, 5244]` -- a row attributable to NO build
🛑 **ALL THREE SHARE A BYTE-IDENTICAL CAVE**, so no probe payload can tell them apart, and the
hybrid cut differs from this one by only EIGHT bytes. **The FILENAME is the only pre-drive
discriminator** -- which is exactly why the retired ones are renamed rather than left alongside.

★ `verify_no_partial_record_write()` below is the GENERAL form of the hybrid defect: a Y row that was
UNIFORM on the base must still be uniform on the output. It would have caught 0xD2A7E automatically.

Usage:  python verify_v74_image.py [IMAGE]  (default: _v74_engagedcols_x0_12_addonly_plain_image.bin)
        python verify_v74_image.py --rwd PATH     (decode a .rwd and verify the payload)
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
import v72_lane_model as LM                # noqa: E402
from encode_eps import parse_x31, build_decode_table                       # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path                 # noqa: E402
from verify_bootloader_crc import walk_all_blocks                          # noqa: E402

FAILS: list[str] = []

START, END = 0x13000, 0x100000
BASE_SHA256 = "918a37151876a1a321103fbd7252684d944773109ff454a08a41fe2c191ee63a"   # V73
CAVE_BASE, CAVE_EXTENT = 0xC4B34, 68
HOOK_ADDR, HOOK_RETURN = 0x55C0E, 0x55C12

# =====================================================================================================
# THE INDEPENDENT STATEMENT OF THE SPEC -- literals, not imports
# =====================================================================================================
EXPECT_ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
EXPECT_DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
EXPECT_LIVE_MODE, EXPECT_MANUAL_MODE = 26, 24
EXPECT_ROW, EXPECT_KEY = 11, "TVCA4"

# ---- LEVER E'.  {mode: (FactorC rec, C_Y0 before, C_Y0 after,
#                        FactorE rec, E_X0 before, E_Y1 before, E_Y1 after)} ------------------------
# 🛑 E_X0 after is 12 on EVERY engaged mode. ⚠ modes 2 and 3 carry a stock X[0] of 70, not 60.
EXPECT_E_X0_AFTER = 12          # ⚠ 12, NOT 6 -- revised; top of the recommended 6-12 band
EXPECT_LEVER_E = {
    2:  (0xCF528,  950, 1356, 0xCF550, 70, 115, 177),
    3:  (0xCF53C,  950, 1356, 0xCF564, 70, 115, 177),
    5:  (0xD07D0,  242,  419, 0xD080C, 60, 142, 536),
    11: (0xD27D0,  431,  431, 0xD280C, 60, 927, 927),
    14: (0xD37D0,  234,  429, 0xD380C, 60, 140, 539),
    15: (0xD37E4,    0,  426, 0xD3820, 60, 140, 539),
    17: (0xD47D0,    0,  419, 0xD480C, 60, 142, 536),
    23: (0xD67D0,    0,  431, 0xD680C, 60, 140, 539),
    26: (0xD77D0,    0,  429, 0xD780C, 60, 140, 539),     # ★★ THE LIVE MODE
    27: (0xD77E4,    0,  426, 0xD7820, 60, 140, 539),
    29: (0xD87D0,    0,  565, 0xD880C, 60, 142, 536),     # ⚠ CAPPED from Y[2] = 571
    32: (0xD97D0,    0,  565, 0xD980C, 60, 142, 536),     # ⚠ CAPPED from Y[2] = 594
    33: (0xD97E4,    0,  565, 0xD9820, 60, 142, 536),     # ⚠ CAPPED from Y[2] = 590
}
EXPECT_CAPPED = {29: 571, 32: 594, 33: 590}
EXPECT_CEILING_FLOOR = 512

# ---- LEVER D'.  {mode: friction record} -----------------------------------------------------------
EXPECT_FRICTION = {2: 0xCF6D8, 3: 0xCF6E8, 5: 0xD0A54, 11: 0xD2A54, 14: 0xD3A54, 15: 0xD3A64,
                   17: 0xD4A54, 23: 0xD6A54, 26: 0xD7A54, 27: 0xD7A64, 29: 0xD8A54, 32: 0xD9A54,
                   33: 0xD9A64}
EXPECT_FRIC_X = [0, 1280, 5760]
EXPECT_FRIC_Y_BEFORE = [-9830, -5734, -1966]
EXPECT_FRIC_Y_AFTER = [-14745, -8601, -2949]
EXPECT_CLAMP = (0xC407E, 850)              # NOT re-written by V74 -- V73's, already flown LIVE
EXPECT_CLAMP_HARD_CAP = 1000               # 🛑 never 1024: the aggregator's +/-0x400 ZERO-REJECT

# ---- 🛑 THE WITHDRAWN REVERT -- these are KEEP-LIST entries, not edits ---------------------------
# V74 is ADD-ONLY on V73. 0xD2A7E/0xD2ABA are Y[0] of the gain_B mode-10 records, set by V72 (LEVER
# A) to 5244 along with all three other Y cells. Reverting them was withdrawn: they are inert only
# *because* the car is row 11, which is an INFERENCE -- if it were wrong, mode 10 is the car's
# DISENGAGED mode and a revert would SUBTRACT something currently on the car.
EXPECT_GAIN_B_M10_KEEP = {0xD2A74: [5244, 5244, 5244, 5244], 0xD2AB0: [5244, 5244, 5244, 5244]}
EXPECT_GAIN_B_M10_STOCK_Y0 = {0xD2A7E: 3072, 0xD2ABA: 2561}   # what a revert WOULD have written

# ---- MUST NOT CHANGE ------------------------------------------------------------------------------
EXPECT_SAR = {0x3AB76: "aa32", 0x3AC20: "aa42"}
EXPECT_GATE = (0x3AA96, 0xC5)
EXPECT_ARMS = {0xC643E: 1536, 0xC6444: 512, 0xC6446: 512}
EXPECT_GAIN_A = {0xC6A68: [512, 512, 512, 512], 0xC6A7C: [512, 512, 512, 512]}
EXPECT_GAIN_A_STOCK = (0xC6A90, 0xC6AA4)
EXPECT_LEVER_C = (0xC63A0, 2048)
EXPECT_CARRIED = (0x454FE, 0xB5)
EXPECT_ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])

# ---- the probe ------------------------------------------------------------------------------------
EXPECT_CAVE_HEX = ("003a24373094e031b205203e100084370798c6360f000639c33a8437edeac63607000731"
                   "4437ecea2436e8ea7f00" + "00" * 22)
EXPECT_CAVE_ASM = [
    "mov 0,r7", "ld.h -27600[r4],r6", "cmp r0,r6", "be +6", "movea 0x0010,r0,r7",
    "ld.bu -26618[r4],r6", "andi 0x000f,r6,r6", "or r6,r7", "shl 0x3,r7",
    "ld.bu -5396[r4],r6", "andi 0x0007,r6,r6", "or r7,r6", "st.b r6,-5396[r4]",
    "movea 0xeae8,r4,r6", "jmp [lp]"] + ["nop"] * 11
EXPECT_STATE_DISP, EXPECT_DAMP_DISP = 0x67FA, 0x6BD0
EXPECT_STATE_VALUE_SET = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11]
EXPECT_STATE_CENSUS, EXPECT_DAMP_CENSUS = (128, 33), (5, 3)
EXPECT_PROBE_MASK, EXPECT_BIT_DAMP_NZ, EXPECT_STATE_FIELD = 0xF8, 0x80, 0x78
EXPECT_HOOK_RETURN_INSN = "083a"           # `mov 0x8,r7` ⇒ r7 is PROVABLY DEAD across the hook

# ---- the dose, at the measured burst rate ---------------------------------------------------------
EXPECT_BURST_RATE = 99          # the IN-BURST p50 [94.2, 113.0]. 🛑 NOT the out-of-burst 9.4.
EXPECT_BURST_RATE_69HZ = 127    # the 6-9 Hz arm's p50
EXPECT_DOSE = {2: 168, 3: 168, 5: 94, 11: 390, 14: 95, 15: 49, 17: 49, 23: 50, 26: 50, 27: 49,
               29: 66, 32: 66, 33: 66}
EXPECT_DOSE_69HZ = {2: 173, 3: 173, 5: 105, 11: 390, 14: 108, 15: 66, 17: 64, 23: 66, 26: 66,
                    27: 66, 29: 87, 32: 87, 33: 87}
EXPECT_DOSE_69HZ_LIVE = 66      # mode 26 at rate 127
# ⊕ modes 2/3 are unmoved by the X[0] revision (168 at both 6 and 12): their Y[0] is 115, not 0, so
# the segment they interpolate on is shallow and the left edge barely matters. Not an error.
EXPECT_LIVE_DOSE_INTERVAL = (30, 60)

# ---- CRC / diff accounting ------------------------------------------------------------------------
EXPECT_TRAILERS = [0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC,
                   0xD8FFC, 0xD9FFC]
EXPECT_DIFF_BY_LEVER = {"cave": 42, "FactorC": 24, "FactorE X[0]": 13, "FactorE Y[1]": 22,
                        "friction": 78}
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
    print("  CROSS-CHECK -- this file's literals against build_v74_tva.py's own tables")
    ok = True
    ok &= check(tuple(EXPECT_ENGAGED) == V74.ENGAGED_EXPECTED,
                "the ENGAGED mode set agrees", f"ENGAGED differs: {EXPECT_ENGAGED} vs "
                f"{V74.ENGAGED_EXPECTED}")
    ok &= check(tuple(EXPECT_DISENGAGED) == V74.DISENGAGED_EXPECTED,
                "the DISENGAGED mode set agrees", "DISENGAGED differs")
    ok &= check(not (set(EXPECT_ENGAGED) & set(EXPECT_DISENGAGED)),
                "the two columns are DISJOINT (stated independently of the image)",
                "the two columns OVERLAP")
    ok &= check(EXPECT_E_X0_AFTER == V74.E_X0_NEW, f"FactorE X[0] -> {EXPECT_E_X0_AFTER} agrees",
                f"E_X0 differs: {EXPECT_E_X0_AFTER} vs {V74.E_X0_NEW}")
    ok &= check(EXPECT_FRIC_Y_AFTER == V74.FRICTION_Y_NEW and
                EXPECT_FRIC_Y_BEFORE == V74.FRICTION_Y_STOCK,
                "the friction Y rows agree", "the friction Y rows differ")
    ok &= check(EXPECT_CLAMP == (V74.CLAMP_ADDR, V74.CLAMP_VALUE), "the clamp agrees",
                "the clamp differs")
    ok &= check(V74.GAIN_B_M10_KEEP == EXPECT_GAIN_B_M10_KEEP and
                V74.GAIN_B_M10_STOCK_Y0 == EXPECT_GAIN_B_M10_STOCK_Y0 and
                not hasattr(V74, "REVERT_CELLS"),
                "the gain_B mode-10 KEEP entries agree and the builder carries NO revert",
                "the builder still carries a gain_B mode-10 revert")
    ok &= check(EXPECT_CAVE_HEX == V74.build_cave()[0].hex(),
                "the cave hex agrees with the builder's emitted bytes", "the cave hex differs")
    ok &= check((EXPECT_PROBE_MASK, EXPECT_BIT_DAMP_NZ, EXPECT_STATE_FIELD) ==
                (V74.PROBE_MASK, V74.BIT_DAMP_NZ, V74.STATE_FIELD),
                "the payload masks agree", "the payload masks differ")
    ok &= check(sorted(EXPECT_STATE_VALUE_SET) == sorted(V74.STATE_VALUE_SET),
                "the gp-0x67FA value set agrees", "the gp-0x67FA value set differs")
    ok &= check((EXPECT_STATE_DISP, EXPECT_DAMP_DISP) == (V74.STATE_DISP, V74.DAMP_DISP),
                "the two probed cells agree", "the probed cells differ")
    ok &= check(EXPECT_BURST_RATE == V74.BURST_RATE and
                EXPECT_LIVE_DOSE_INTERVAL == V74.DOSE_REQUIREMENT,
                "the burst rate and the dose interval agree", "the sizing constants differ")
    ok &= check(EXPECT_TRAILERS == sorted(EXPECT_TRAILERS) and len(EXPECT_TRAILERS) == 10,
                "the expected trailer list is well-formed", "the trailer list is malformed")
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
          f"{EXPECT_LIVE_MODE} (V73's on-car probe)",
          f"row {EXPECT_ROW} is {r[1]!r} {r[2]}")


def verify_lever_e(img, base):
    print("\n  LEVER E' -- FactorC Y[0] := Y[2] · FactorE X[0] := 6 · FactorE Y[1] := Y[2]")
    for mode in EXPECT_ENGAGED:
        cb, c_before, c_after, eb, e_x0, e_y1_b, e_y1_a = EXPECT_LEVER_E[mode]
        # 🛑 the address is RE-DERIVED from the pointer array, then matched to the literal.
        d_cb, d_eb = u32(img, 0xC9E9C + mode * 4), u32(img, 0xC9F84 + mode * 4)
        if not check(d_cb == cb and d_eb == eb,
                     f"m{mode:2d}: FactorC 0x{cb:05X} / FactorE 0x{eb:05X} re-derive from the arrays",
                     f"m{mode}: arrays give 0x{d_cb:05X}/0x{d_eb:05X}, expected 0x{cb:05X}/0x{eb:05X}"):
            continue
        n_c, cx, cy = rec(img, cb)
        n_e, ex, ey = rec(img, eb)
        _n, _bx, by_ = rec(base, cb)
        _n, bex, bey = rec(base, eb)
        ok = (n_c == 4 and n_e == 4
              and by_[0] == c_before and cy[0] == c_after and cy[1:] == by_[1:]
              and bex[0] == e_x0 and ex[0] == EXPECT_E_X0_AFTER and ex[1:] == bex[1:]
              and bey[1] == e_y1_b and ey[1] == e_y1_a and ey[0] == bey[0] and ey[2:] == bey[2:])
        check(ok, f"m{mode:2d}: C_Y {by_} -> {cy}   E_X {bex} -> {ex}   E_Y {bey} -> {ey}",
              f"m{mode}: C_Y {by_}->{cy}, E_X {bex}->{ex}, E_Y {bey}->{ey} does not match the spec")
        # 🛑 FactorE monotone non-decreasing -- that is what protects rate-proportionality.
        check(all(b >= a for a, b in zip(ey, ey[1:])),
              f"m{mode:2d}: FactorE is monotone non-decreasing {ey}",
              f"m{mode}: FactorE {ey} is NOT monotone")
        # ⚠ FactorC's SPEED-axis dip is EXPECTED -- reported, not failed.
        if cy[0] > cy[1]:
            print(f"     ⊕ m{mode:2d}: FactorC dips on the SPEED axis ({cy[0]} > {cy[1]}) -- EXPECTED "
                  "and allowed; it is what confines the change to creep")
        # ★ V72's error, asserted against: FactorE must not be a CONSTANT unless it already was.
        if len(set(ey)) == 1:
            check(len(set(bey)) == 1,
                  f"m{mode:2d}: FactorE was ALREADY flat on the base (V72's LEVER B) -- not V74's",
                  f"m{mode}: V74 FLATTENED FactorE to {ey} -- the bang-bang relay shape")
        # the caps
        if mode in EXPECT_CAPPED:
            ey3 = ey[3]
            check(c_after == (EXPECT_CEILING_FLOOR * 1024) // ey3 and c_after < EXPECT_CAPPED[mode],
                  f"m{mode:2d}: CAPPED from Y[2]={EXPECT_CAPPED[mode]} to "
                  f"floor(512*1024/{ey3}) = {c_after} (no-clip)",
                  f"m{mode}: the cap is {c_after}, expected {(EXPECT_CEILING_FLOOR * 1024) // ey3}")
        else:
            check(c_after == cy[2],
                  f"m{mode:2d}: uncapped -- Y[0] is that record's own Y[2] = {cy[2]}",
                  f"m{mode}: Y[0] {c_after} != Y[2] {cy[2]} and the mode is not in the cap list")
        # FactorB / FactorD FLAT 1024 and the ceiling floor, per mode
        for arr, name in ((0xC9CCC, "FactorB"), (0xC9DB4, "FactorD")):
            b_ = u32(img, arr + mode * 4)
            check(set(rec(img, b_)[2]) == {1024},
                  f"m{mode:2d}: {name} @0x{b_:05X} is FLAT 1024 ⇒ the chain reduces to (C*E)>>10",
                  f"m{mode}: {name} is not flat 1024")
        ce = u32(img, 0xC77A0 + mode * 4)
        n, cx2, cyy = rec(img, ce)
        check((n, cx2, cyy) == (2, [300, 800], [512, 1024]),
              f"m{mode:2d}: ceiling @0x{ce:05X} = {cyy} ⇒ floor {EXPECT_CEILING_FLOOR}, verified "
              "PER MODE", f"m{mode}: ceiling is ({n}, {cx2}, {cyy})")


def verify_no_clip_and_dose(img, base):
    """★ THE SURFACE RULE: wherever V74 raises the surface it stays at or below the floor."""
    print("\n  THE SURFACE -- no-clip, peak invariance, and the DOSE, recomputed from THESE bytes")
    grid = [(v, r) for v in range(0, 14001, 32) for r in range(0, 4501, 20)]

    def surface(b, mode, v, r):
        c = LM.lerp_int(v, *rec(b, u32(b, 0xC9E9C + mode * 4))[1:])
        e = LM.lerp_int(r, *rec(b, u32(b, 0xC9F84 + mode * 4))[1:])
        bb = LM.lerp_int(v, *rec(b, u32(b, 0xC9CCC + mode * 4))[1:])
        d = LM.lerp_int(r, *rec(b, u32(b, 0xC9DB4 + mode * 4))[1:])
        x = (1024 * bb) >> 10
        x = (x * c) >> 10
        x = (x * d) >> 10
        return (x * e) >> 10

    print(f"      {'mode':>4} {'dose@rate99':>11} {'expected':>9} {'raisedMax':>10} "
          f"{'pointsRaised':>13} {'peak':>6} {'peak base':>10}")
    for mode in EXPECT_ENGAGED:
        bad, raised, aff, peak, peak_b = [], 0, 0, 0, 0
        for v, r in grid:
            now, was = surface(img, mode, v, r), surface(base, mode, v, r)
            peak, peak_b = max(peak, now), max(peak_b, was)
            if now > was:
                raised += 1
                aff = max(aff, now)
                if now > EXPECT_CEILING_FLOOR:
                    bad.append((v, r, was, now))
        dose = surface(img, mode, 0, EXPECT_BURST_RATE)
        check(surface(img, mode, 0, EXPECT_BURST_RATE_69HZ) == EXPECT_DOSE_69HZ[mode],
              f"m{mode:2d}: dose at the 6-9 Hz rate {EXPECT_BURST_RATE_69HZ} = "
              f"{EXPECT_DOSE_69HZ[mode]}",
              f"m{mode}: dose at {EXPECT_BURST_RATE_69HZ} is "
              f"{surface(img, mode, 0, EXPECT_BURST_RATE_69HZ)}, expected {EXPECT_DOSE_69HZ[mode]}")
        star = "  ★★ LIVE" if mode == EXPECT_LIVE_MODE else ""
        print(f"      {mode:4d} {dose:11d} {EXPECT_DOSE[mode]:9d} {aff:10d} {raised:13d} "
              f"{peak:6d} {peak_b:10d}{star}")
        check(not bad,
              f"m{mode:2d}: every raised point stays at or below the floor {EXPECT_CEILING_FLOOR}",
              f"m{mode}: RAISES the surface above its floor at {len(bad)} point(s), e.g. {bad[:3]} "
              "⇒ a hard-clipping element inside a feedback loop")
        check(peak == peak_b, f"m{mode:2d}: the GLOBAL peak is unchanged at {peak}",
              f"m{mode}: the global peak moved {peak_b} -> {peak}")
        check(dose == EXPECT_DOSE[mode], f"m{mode:2d}: dose at rate {EXPECT_BURST_RATE} = {dose}",
              f"m{mode}: dose is {dose}, the spec says {EXPECT_DOSE[mode]}")
    lo, hi = EXPECT_LIVE_DOSE_INTERVAL
    live = surface(img, EXPECT_LIVE_MODE, 0, EXPECT_BURST_RATE)
    check(lo <= live <= hi and surface(base, EXPECT_LIVE_MODE, 0, EXPECT_BURST_RATE) == 0,
          f"★★ THE LIVE MODE {EXPECT_LIVE_MODE}: 0 (V73) -> {live} counts, inside the sizing "
          f"interval {list(EXPECT_LIVE_DOSE_INTERVAL)}",
          f"the live mode delivers {live}, outside {EXPECT_LIVE_DOSE_INTERVAL}")


def verify_friction_and_clamp(img, base):
    print("\n  LEVER D' -- the friction lane x1.5, and the clamp (asserted, NOT re-written)")
    for mode in EXPECT_ENGAGED:
        want = EXPECT_FRICTION[mode]
        got = u32(img, 0xCBE74 + mode * 4)
        if not check(got == want, f"m{mode:2d}: friction record 0x{want:05X} re-derives",
                     f"m{mode}: friction derives to 0x{got:05X}, expected 0x{want:05X}"):
            continue
        n, xs, ys = rec(img, got)
        _n, _bx, bys = rec(base, got)
        check((n, xs, ys) == (3, EXPECT_FRIC_X, EXPECT_FRIC_Y_AFTER) and
              bys == EXPECT_FRIC_Y_BEFORE,
              f"m{mode:2d}: Y {bys} -> {ys} @0x{got + 8:05X} (x1.5, exact)",
              f"m{mode}: friction is ({n}, {xs}, {ys}), base {bys}")
    addr, val = EXPECT_CLAMP
    check(u16(img, addr) == val and u16(base, addr) == val,
          f"the clamp 0x{addr:05X} = {val} and is UNCHANGED from V73 (already flown LIVE)",
          f"0x{addr:05X} is {u16(img, addr)}, expected {val} on BOTH V73 and V74")
    check(val <= EXPECT_CLAMP_HARD_CAP < 1024,
          f"🛑 the clamp {val} is at or below the hard cap {EXPECT_CLAMP_HARD_CAP} and below the "
          "aggregator's +/-0x400 ZERO-REJECT window",
          f"the clamp {val} breaches the hard cap")


def verify_no_partial_record_write(img, base):
    """★ THE GENERAL FORM OF THE HYBRID DEFECT: a UNIFORM Y row must stay uniform.

    An earlier V74 cut reverted Y[0] of the two gain_B mode-10 records to stock while V72 had set
    ALL FOUR cells to 5244, producing `[3072, 5244, 5244, 5244]` -- neither stock nor V72, and
    attributable to no build. This is the rule rather than a spot check on two addresses: any
    partial write to a multi-cell row that carried ONE decided value manufactures a hybrid.
    """
    print("\n  ★ NO PARTIAL WRITE TO ANY MULTI-CELL RECORD (the general form of the hybrid defect)")
    recs = {u32(img, arr + m * 4)
            for arr in (0xCBE74, 0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0)
            for m in range(34)}
    recs |= set(EXPECT_GAIN_A) | set(EXPECT_GAIN_B_M10_KEEP) | set(EXPECT_GAIN_A_STOCK)
    bad, uniform = [], 0
    for b_ in sorted(recs):
        n_b, _x, yb = rec(base, b_)
        n_o, _x2, yo = rec(img, b_)
        if n_b != n_o:
            bad.append((hex(b_), "count", n_b, n_o))
            continue
        if len(set(yb)) == 1 and len(yb) > 1:
            uniform += 1
            if len(set(yo)) != 1:
                bad.append((hex(b_), "hybrid", yb, yo))
    check(not bad,
          f"all {len(recs)} records keep their point count, and all {uniform} with a UNIFORM Y row "
          "on V73 are still uniform ⇒ no hybrid was manufactured",
          f"PARTIAL WRITE detected: {bad[:4]}")
    for b_, want in EXPECT_GAIN_B_M10_KEEP.items():
        got = list(struct.unpack_from("<4h", img, b_ + 0x0A))
        check(len(set(got)) == 1 and got == want,
              f"gain_B mode-10 0x{b_:05X} Y = {got} -- UNIFORM, the instance that motivated the rule",
              f"gain_B mode-10 0x{b_:05X} Y is {got}, expected the uniform {want}")


def verify_hygiene(img, base, stock):
    """🛑 The WITHDRAWN revert: these cells must be byte-identical to V73, not reverted."""
    print("\n  🛑 gain_B mode-10 -- the WITHDRAWN revert. V74 is ADD-ONLY on V73.")
    for b_, want in EXPECT_GAIN_B_M10_KEEP.items():
        got = list(struct.unpack_from("<4h", img, b_ + 0x0A))
        stk = list(struct.unpack_from("<4h", stock, b_ + 0x0A))
        check(got == want and bytes(img[b_:b_ + 0x14]) == bytes(base[b_:b_ + 0x14]),
              f"0x{b_:05X} Y = {got}, byte-identical to V73 (stock would be {stk})",
              f"0x{b_:05X} Y is {got}, expected V73's {want} byte-for-byte")
    for addr, would in EXPECT_GAIN_B_M10_STOCK_Y0.items():
        check(u16(img, addr) == 5244 and u16(stock, addr) == would,
              f"0x{addr:05X} still holds V72's 5244 (a revert would have written {would})",
              f"0x{addr:05X} is {u16(img, addr)} -- it looks REVERTED; V74 must not subtract")
    print("     ⊕ Withdrawn for two reasons: V72 (not V73) set ALL FOUR Y cells to 5244, so a")
    print("       4-byte revert leaves a row that is neither stock nor V72 -- and decisively, these")
    print("       cells are inert only *because* the car is row 11, which is an INFERENCE. If it")
    print("       were wrong, mode 10 is the car's DISENGAGED mode and a revert would SUBTRACT.")


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
    check(u16(img, EXPECT_LEVER_C[0]) == EXPECT_LEVER_C[1],
          f"V72's LEVER C 0x{EXPECT_LEVER_C[0]:05X} = {EXPECT_LEVER_C[1]}", "LEVER C moved")
    check(img[EXPECT_CARRIED[0]] == EXPECT_CARRIED[1],
          f"the carried 0x{EXPECT_CARRIED[0]:05X} = 0x{EXPECT_CARRIED[1]:02X}", "0x454FE moved")
    a, want = EXPECT_ROLE_TABLE
    got = list(img[a:a + len(want)])
    check(got == want and not any(r in (6, 7) for r in got),
          f"the role table 0x{a:05X} = {want} (no slot carries role 6 or 7)",
          f"the role table is {got}")
    # the six pointer arrays over all 34 modes, and the config table
    bad = [(hex(arr), m) for arr in (0xCBE74, 0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0)
           for m in range(34) if u32(img, arr + m * 4) != u32(stock, arr + m * 4)]
    check(not bad, "all six pointer arrays are byte-STOCK across modes 0-33 ⇒ every edited table is "
          "reachable only through an unmoved pointer", f"a pointer moved: {bad[:6]}")
    check(bytes(img[0xCD000:0xCD000 + 16 * 0x24]) == bytes(stock[0xCD000:0xCD000 + 16 * 0x24]),
          "the config table 0xCD000 is byte-STOCK", "the config table moved")
    # ★★ THE SAFETY ARGUMENT: every DISENGAGED-column record byte-identical to V73
    bad = []
    for mode in EXPECT_DISENGAGED:
        for arr, name in ((0xC9CCC, "FactorB"), (0xC9E9C, "FactorC"), (0xC9DB4, "FactorD"),
                          (0xC9F84, "FactorE"), (0xC77A0, "ceiling"), (0xCBE74, "friction")):
            b_ = u32(img, arr + mode * 4)
            n = rec_len(img, b_)
            if bytes(img[b_:b_ + n]) != bytes(base[b_:b_ + n]):
                bad.append((mode, name, hex(b_)))
    check(not bad,
          f"★★ ALL {len(EXPECT_DISENGAGED)} DISENGAGED modes x 6 records are byte-identical to V73 "
          "⇒ manual and parking steering are UNTOUCHED",
          f"a DISENGAGED record MOVED: {bad[:6]}")


def verify_cave(img):
    print("\n  THE PROBE")
    got = bytes(img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    check(got.hex() == EXPECT_CAVE_HEX and len(got) == CAVE_EXTENT == 68,
          f"the cave is the proven {CAVE_EXTENT}-byte extent and matches the expected hex exactly",
          f"the cave is {len(got)}B / {got.hex()}")
    asm = [m for _a, _r, m in V74.redisassemble_cave(got)]
    check(asm == EXPECT_CAVE_ASM,
          "the cave RE-DISASSEMBLES (raw Python decoder, not a Ghidra database) to exactly the "
          "expected 15 instructions + 11 nop", f"the re-disassembly is {asm}")
    stores = [m for m in asm if m.startswith(("st.b", "st.h"))]
    check(len(stores) == 1 and stores[0] == "st.b r6,-5396[r4]",
          "GATE 1: EXACTLY ONE store, and it is the CAN-330 payload byte",
          f"the cave contains stores {stores}")
    brs = [(i, m) for i, m in enumerate(asm) if m.startswith(("be ", "bne ", "blt ", "bge ", "b?"))]
    check(len(brs) == 1 and brs[0][1] == "be +6",
          "exactly ONE branch, `be +6`, FORWARD and landing before `jmp [lp]` ⇒ the 22 zero bytes "
          "stay unreachable", f"the branches are {brs}")
    check(asm[brs[0][0] - 1] == "cmp r0,r6",
          "🛑 FLAG LIVENESS: the `be` immediately follows its own `cmp` -- nothing between them",
          "the branch does not immediately follow its cmp -- it would read STALE flags")
    check(asm.index("or r6,r7") < asm.index("shl 0x3,r7") < asm.index("or r7,r6"),
          "the `or` pair is in the right ORDER: ACCUMULATE `or r6,r7`, then MERGE `or r7,r6`",
          "the `or` order is wrong -- the payload would read `state 0` on every frame")
    check(bytes(img[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR),
          f"the hook 0x{HOOK_ADDR:05X} is `jarl 0x{CAVE_BASE:05X}`", "the hook is not our jarl")
    check(bytes(img[HOOK_RETURN:HOOK_RETURN + 2]).hex() == EXPECT_HOOK_RETURN_INSN,
          f"0x{HOOK_RETURN:05X} is `mov 0x8,r7` ⇒ r7 is PROVABLY DEAD across the hook",
          f"0x{HOOK_RETURN:05X} is {bytes(img[HOOK_RETURN:HOOK_RETURN + 2]).hex()}")
    # GATE 1 as a MEASUREMENT: both probed cells, by raw byte scan
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    for disp, (nr, nw) in ((EXPECT_STATE_DISP, EXPECT_STATE_CENSUS),
                           (EXPECT_DAMP_DISP, EXPECT_DAMP_CENSUS)):
        reads, writes, cave = V74.cell_census(img, disp, span)
        check(len(reads) == nr and len(writes) == nw and len(cave) == 1 and
              cave[0][1].startswith("ld."),
              f"gp-0x{disp:04X}: {len(reads)}r / {len(writes)}w firmware, and the cave adds EXACTLY "
              "ONE load and writes it NEVER",
              f"gp-0x{disp:04X}: {len(reads)}r/{len(writes)}w, cave {cave}")
    _r, _w, shadow = V74.cell_census(img, 0x4C39, span)
    check(not shadow, "the lockstep shadow gp-0x4C39 is untouched by the cave",
          f"the cave touches the shadow: {shadow}")
    vals, nonlit = V74.assert_state_value_set(img)
    check(vals == EXPECT_STATE_VALUE_SET and 0 not in vals and all(v < 16 for v in vals),
          f"★★ STRUCTURAL LIVENESS: gp-0x67FA's 33 writers give {vals} -- 0 is IMPOSSIBLE and every "
          "value is < 16 ⇒ `bits 6:3 == 0` for a whole drive means THE CAVE DID NOT FIRE",
          f"the state value set is {vals}")


def verify_crc_and_diff(img, base, stock):
    print("\n  CRC AND THE FULL DIFF ACCOUNTING")
    check(walk_all_blocks(img, verbose=False) == 0 if _accepts_verbose() else
          walk_all_blocks(img) == 0, "the full CRC chain: 50/50 blocks PASS",
          "the CRC chain FAILED")
    diff = [i for i in range(START, END) if img[i] != base[i]]
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    c_cells = {a + k for _m, (cb, _b, _a2, _eb, _x, _y1, _y2) in EXPECT_LEVER_E.items()
               for a in (cb + 0x0A,) for k in (0, 1)}
    ex_cells = {a + k for _m, (_cb, _b, _a2, eb, _x, _y1, _y2) in EXPECT_LEVER_E.items()
                for a in (eb + 0x02,) for k in (0, 1)}
    ey_cells = {a + k for _m, (_cb, _b, _a2, eb, _x, _y1, _y2) in EXPECT_LEVER_E.items()
                for a in (eb + 0x0C,) for k in (0, 1)}
    fr_cells = {r + 8 + k for r in EXPECT_FRICTION.values() for k in range(6)}
    hy_cells = set()          # the revert was WITHDRAWN -- no hygiene bytes in this cut

    # 🛑 The moved CRC blocks are derived from the LEVER ADDRESSES, not from the diff -- a trailer
    # address is not itself inside any block, so `owning_block` cannot resolve one. Deriving them
    # this way is also STRICTER: it fixes the expected trailer set before looking at the diff, so a
    # block that moved for some other reason shows up as an unattributed byte below.
    touched = [CAVE_BASE] + sorted(c_cells | ex_cells | ey_cells | fr_cells | hy_cells)
    blocks = sorted({tuple(V53.owning_block(img, a)) for a in touched})
    check([b[1] for b in blocks] == EXPECT_TRAILERS,
          f"exactly {len(EXPECT_TRAILERS)} blocks own an edit: {[hex(t) for t in EXPECT_TRAILERS]}",
          f"the owning blocks are {[hex(b[1]) for b in blocks]}")
    crc_only = {b[1] + k for b in blocks for k in range(4)}
    func = [d for d in diff if d not in crc_only]
    check(all(img[t] != base[t] or img[t + 1] != base[t + 1] or img[t + 2] != base[t + 2]
              or img[t + 3] != base[t + 3] for t in EXPECT_TRAILERS),
          "every expected trailer actually moved", "a trailer did not move")

    def attribute(d):
        return ("cave" if d in span else "FactorC" if d in c_cells else
                "FactorE X[0]" if d in ex_cells else "FactorE Y[1]" if d in ey_cells else
                "friction" if d in fr_cells else None)

    stray = [hex(d) for d in func if attribute(d) is None]
    check(not stray, f"every one of the {len(func)} functional bytes is ATTRIBUTABLE to a named "
          "lever", f"UNATTRIBUTED functional bytes: {stray[:12]}")
    by = {}
    for d in func:
        by[attribute(d)] = by.get(attribute(d), 0) + 1
    check(by == EXPECT_DIFF_BY_LEVER and len(func) == sum(EXPECT_DIFF_BY_LEVER.values()),
          f"the functional diff vs V73 is exactly {sum(EXPECT_DIFF_BY_LEVER.values())} bytes: {by}",
          f"got {len(func)} bytes, {by}, expected {EXPECT_DIFF_BY_LEVER}")
    all_edits = set(span) | c_cells | ex_cells | ey_cells | fr_cells | hy_cells
    check(not [a for a in all_edits if CRC_SKIPPED[0] <= a < CRC_SKIPPED[1]],
          f"NOTHING of the {len(all_edits)} edited bytes lands in "
          f"[0x{CRC_SKIPPED[0]:05X},0x{CRC_SKIPPED[1]:05X}) -- the CRC-skipped block, V40 ignition "
          "precedent", "an edit landed in the CRC-skipped block")
    inherited = {i for i in range(START, END) if base[i] != stock[i]}
    ds = [i for i in range(START, END) if img[i] != stock[i] and i not in crc_only]
    stray_s = [hex(d) for d in ds if attribute(d) is None and d not in inherited]
    check(not stray_s, f"vs STOCK: {len(ds)} functional bytes, all attributable to a V74 lever or "
          "to the carried V38->V73 lineage", f"UNATTRIBUTED vs stock: {stray_s[:12]}")


def _accepts_verbose():
    import inspect
    return "verbose" in inspect.signature(walk_all_blocks).parameters


def verify(img, base, stock, label):
    print("=" * 100)
    print(f"  VERIFYING {label}")
    print(f"    SHA256 {hashlib.sha256(img).hexdigest()}")
    check(len(img) == 0x100000, "the image is 1 MiB", f"the image is {len(img)} bytes")
    check(hashlib.sha256(base).hexdigest() == BASE_SHA256,
          "the comparison base IS the recorded V73 image (by SHA256, not by shape)",
          "the base is NOT V73")
    verify_columns(img)
    verify_lever_e(img, base)
    verify_no_clip_and_dose(img, base)
    verify_friction_and_clamp(img, base)
    verify_hygiene(img, base, stock)
    verify_no_partial_record_write(img, base)
    verify_must_not_change(img, base, stock)
    verify_cave(img)
    verify_crc_and_diff(img, base, stock)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=None)
    ap.add_argument("--rwd", default=None)
    args = ap.parse_args()

    base = Path(plain_image_path("_v73_plain_image.bin")).read_bytes()
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
            else Path(plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin"))
        verify(p.read_bytes(), base, stock, str(p))

    print("\n" + "=" * 100)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"     - {f}")
        return 1
    print(f"  ✅ V74 VERIFIED. The ENGAGED column {list(EXPECT_ENGAGED)}")
    print(f"     carries all 39 LEVER E' cells and all 13 friction records; the DISENGAGED column")
    print(f"     {list(EXPECT_DISENGAGED)}")
    print("     is byte-identical to V73, record by record ⇒ manual and parking steering untouched.")
    print(f"     The live mode {EXPECT_LIVE_MODE} delivers {EXPECT_DOSE[EXPECT_LIVE_MODE]} counts at "
          f"the measured burst rate {EXPECT_BURST_RATE} (V73: 0).")
    print("     The cave, its re-disassembly, both probe-cell censuses, the structural-liveness")
    print("     value set, the whole keep-list, the CRC chain and the full diff accounting: all PASS.")
    print("  🛑 Verification is not authorisation. Flash only on the operator's explicit")
    print("     instruction, naming the file and the bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
