#!/usr/bin/env python3
"""verify_v73_image.py -- VALUE-ANCHORED verification of a built V73 image.

🛑 WHY THIS EXISTS AND WHY IT IS NOT `diff_build_vs_stock.py`.
That tool is SPAN-based: it asks "which byte ranges moved?" A span check passes on the WRONG BUILD --
two images that edit the same addresses to different values are indistinguishable to it, and the kit
has a recorded case where a re-cut under the same number produced an artefact no gate could check.
This file asserts the ACTUAL VALUES at every site, including every MUST-REMAIN site, so it fails on
any image that is not V73.

🛑 IT DOES NOT SIMPLY IMPORT THE BUILDER'S NUMBERS AND COMPARE THEM TO THEMSELVES. Every expected
value below is re-declared here as a LITERAL and then CROSS-CHECKED against `build_v73_tva.py`'s own
tables. A divergence between the two independent statements is a failure -- so a typo in either file
is caught, which importing alone could never do.

★ V73 IS ADD-ONLY ON TOP OF V72, so this file verifies TWO things that a single-build verifier does
not: that V73's own edits took their intended values, AND that every V72 lever is still at its V72
value. The base image is identified by SHA256, not by shape.

Usage:  python verify_v73_image.py [IMAGE]        (default: _v73_plain_image.bin)
        python verify_v73_image.py --rwd PATH     (decode a .rwd and verify the payload)
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

import build_v73_tva as V73                                                  # noqa: E402
import build_vfourframe_tva as FF                                            # noqa: E402
import build_v64_tva as V64                                                  # noqa: E402
from encode_eps import parse_x31, build_decode_table                         # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path                   # noqa: E402
from verify_bootloader_crc import walk_all_blocks                            # noqa: E402

# =====================================================================================================
# THE EXPECTATION, RE-DECLARED AS LITERALS -- not imported
# =====================================================================================================
BASE_SHA256 = "466b5f2983167ed1599969eaf1165b570c34ff900012853c6fdb050deebaca58"   # _v72_plain_image

# ---- EDIT 1: the friction lane ----------------------------------------------------------------------
EXPECT_FRICTION = (0xD2A44, 3, [0, 1280, 5760], [-14745, -8601, -2949])   # base, count, X, Y
FRICTION_BASE_Y = [-9830, -5734, -1966]                                   # V72/stock, x1.5 -> above
EXPECT_FRICTION_PTR = (0xCBE74, 10)                                       # ptr[mode * 4] -> 0xD2A44
EXPECT_CLAMP = (0xC407E, 850)                                             # tp+0x507e, was 511
EXPECT_CLAMP_READERS = [0x36C34, 0x36CD0, 0x36CDC]                        # 3 x ld.h, 0 writers
EXPECT_CLAMP_NEIGHBOUR = (0xC407C, 461)                                   # ⚠ MUST NOT MOVE
# 🛑 the friction record is MODE-INDEXED; every OTHER mode's record must be byte-stock.
EXPECT_FRICTION_TWINS = {0: (0xCE6D8, FRICTION_BASE_Y), 1: (0xCE6E8, FRICTION_BASE_Y),
                         2: (0xCF6D8, FRICTION_BASE_Y), 3: (0xCF6E8, FRICTION_BASE_Y),
                         4: (0xD0A44, FRICTION_BASE_Y), 11: (0xD2A54, FRICTION_BASE_Y),
                         12: (0xD2A64, FRICTION_BASE_Y)}

# ---- EDIT 2: the ratchet, every candidate mode ------------------------------------------------------
# 🛑 ADDRESSES ARE LITERAL HERE ON PURPOSE. The builder DERIVES them from the pointer arrays; this
# file states the answer independently, so a derivation bug shows up as a disagreement rather than
# as two copies of the same mistake.
EXPECT_RATCHET_MODES = (0, 1, 2, 3, 4, 5, 12, 14)
EXPECT_EXCLUDED_MODES = (10, 11)              # V72's LEVER B -- must stay at V72's values
EXPECT_UNCOVERED_MODES = (13, 15)             # ⚠ TVAA7's e013/e015 -- reachable, NOT covered
# mode -> (FactorC record, FactorE record, new C Y[0], new E Y[0], creep dose)
EXPECT_RATCHET = {
    0:  (0xCE528, 0xCE550, 950, 115, 106),    1:  (0xCE53C, 0xCE564, 950, 115, 106),
    2:  (0xCF528, 0xCF550, 950, 115, 106),    3:  (0xCF53C, 0xCF564, 950, 115, 106),
    4:  (0xD07BC, 0xD07F8, 242, 142, 33),     5:  (0xD07D0, 0xD080C, 242, 142, 33),
    12: (0xD27E4, 0xD2820, 234, 140, 31),     14: (0xD37D0, 0xD380C, 234, 140, 31),
}
# ⚠ modes 12/14 deliver 31, NOT 32: (234 * 140) >> 10 = 32760 >> 10 = 31. Recomputed, not quoted.
EXPECT_UNCOVERED_RECORDS = {13: (0xD37BC, 0xD37F8), 15: (0xD37E4, 0xD3820)}
FACTOR_C_PTRS, FACTOR_E_PTRS, CEILING_PTRS = 0xC9E9C, 0xC9F84, 0xC77A0
CEILING_FLOOR = 512                           # 🛑 asserted PER MODE, never inherited from one mode
EXPECT_CEILING_ROW = (2, [300, 800], [512, 1024])
# ★ the max over the region raising Y[0] NEWLY AFFECTS ({v <= C.X[1]} U {r <= E.X[1]}), per family.
# ⚠ a blanket "max < 512 everywhere" is FALSE on modes 4/5/12/14 (global peaks 792/821) and EQUALLY
# false on the base, so it is not a V73 requirement. This is the correctly-scoped claim.
EXPECT_AFFECTED_MAX = {0: 234, 1: 234, 2: 234, 3: 234, 4: 219, 5: 219, 12: 211, 14: 211}

# ---- EDIT 3: the probe ------------------------------------------------------------------------------
EXPECT_CAVE = (0xC4B34, "203e1000a437fd63c6360f000639c33a8437edeac636070007314437ecea2436e8ea"
                        "7f000000000000000000000000000000000000000000000000000000000000000000")
EXPECT_CAVE_CODE_LEN = 36
EXPECT_CAVE_HOOK = (0x55C0E, "86ff26ef")      # `jarl 0xC4B34` -- the hook, unchanged from the base
EXPECT_HOOK_RETURN = (0x55C12, "083a")        # `mov 0x8,r7` ⇒ r7 is DEAD across the hook
EXPECT_MODE_DISP = 0x63FD                     # 🛑 POSITIVE gp displacement
EXPECT_MODE_CENSUS = (22, [0x426AE, 0x4279E, 0x427C4, 0x427FC, 0x42822])   # readers, writers
EXPECT_RETIRED = {0x69A4: (3, [0x355C6]), 0x6BD0: (5, [0x34730, 0x34744, 0x34752]),
                  0x6AC0: (26, [0x41820, 0x41832, 0x41A8C, 0x41AAC])}

# ---- V72's levers, which V73 CARRIES BYTE-IDENTICALLY -----------------------------------------------
EXPECT_V72_LEVER_A = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4,
                      0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}
EXPECT_V72_LEVER_B = {0xD27BC: [430, 430, 430, 877], 0xD27D0: [431, 431, 431, 877],
                      0xD27F8: [927] * 4, 0xD280C: [927] * 4}
EXPECT_V72_LEVER_C = (0xC63A0, 2048)
EXPECT_V72_CARRIED = (0x454FE, 0x65B5)        # `br 0x455C4` -- the cond nibble only
EXPECT_V72_GATE = (0x3AA96, 0xC5)             # gp-0x683c, ZERO writers ⇒ V73 is UNGATED

# ---- MUST REMAIN BYTE-STOCK -------------------------------------------------------------------------
EXPECT_STOCK_HALFWORDS = {0xC643E: 1536, 0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512, 0xC6446: 512,
                          0xC6158: 512}
EXPECT_SAR_SITES = {0x3AB76: 0x32AA, 0x3AC20: 0x42AA}
# 🛑 0xD27E4 / 0xD2820 (FactorC/E MODE 12) used to live in this table and have MOVED to the edited
# set -- V73's mode 12 is exactly them. They are asserted in EXPECT_RATCHET instead, and the
# inherited V72 guard is relaxed for those two cells only, with the exception set asserted.
EXPECT_STOCK_RECORDS = {0xD2AEC: [2305, 2304, 2149, 1948], 0xD2B28: [2151, 2151, 2049, 1947],
                        0xC6A90: [2664, 2664, 2243, 1436], 0xC6AA4: [2560, 2560, 2145, 1331],
                        0xD2A88: [3072, 3072, 2322, 1536], 0xD2A9C: [3072, 3072, 2322, 1536]}
EXPECT_ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
EXPECT_VARIANT_ROWS = {0: ("00000", [0, 1, 2, 3]), 2: ("TVAA1", [10, 10, 11, 11]),
                       8: ("TVAA7", [12, 13, 14, 15])}
CRC_BLOCKS_MOVED = [0xC4FFC, 0xCEFFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC]
CRC_SKIPPED_BLOCK = (0xC5000, 0xC5FFC)        # the V40 ignition-brick precedent

FAILS: list[str] = []


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def rec4_y(b, base):
    return list(struct.unpack_from("<4h", b, base + 0x0A))


def rec_any(b, base):
    n = u16(b, base)
    return (n, list(struct.unpack_from(f"<{n}h", b, base + 2)),
            list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n)))


def check(ok, msg, detail=""):
    if ok:
        print(f"    ✅ {msg}")
    else:
        FAILS.append(f"{msg}  {detail}")
        print(f"    🛑 FAIL: {msg}  {detail}")
    return ok


def cross_check_against_builder():
    """🛑 The two independent statements of the spec must agree. A typo in EITHER file fails here."""
    print("\n  CROSS-CHECK -- this file's literals vs build_v73_tva.py's tables:")
    ok = True
    ok &= check((V73.FRICTION_REC, V73.FRICTION_NPT, V73.FRICTION_X, V73.FRICTION_Y_NEW) ==
                EXPECT_FRICTION, "EDIT 1: the friction record, count, X and final Y agree",
                f"builder={(hex(V73.FRICTION_REC), V73.FRICTION_NPT, V73.FRICTION_X, V73.FRICTION_Y_NEW)}")
    ok &= check(V73.FRICTION_Y_STOCK == FRICTION_BASE_Y and
                [(y * 3) // 2 for y in FRICTION_BASE_Y] == EXPECT_FRICTION[3],
                "EDIT 1: the final Y row IS the base row x1.5, re-derived here independently")
    ok &= check((V73.CLAMP_ADDR, V73.CLAMP_NEW) == EXPECT_CLAMP, "EDIT 1: the clamp agrees")
    ok &= check(V73.CLAMP_READERS == EXPECT_CLAMP_READERS, "EDIT 1: the clamp's reader set agrees")
    ok &= check(V73.CLAMP_NEIGHBOUR == EXPECT_CLAMP_NEIGHBOUR,
                "EDIT 1: the untouched neighbour 0xC407C agrees")
    ok &= check(tuple(V73.RATCHET_MODES) == EXPECT_RATCHET_MODES and
                tuple(V73.EXCLUDED_MODES) == EXPECT_EXCLUDED_MODES and
                tuple(V73.UNCOVERED_MODES) == EXPECT_UNCOVERED_MODES,
                f"EDIT 2: the mode sets agree -- covered {EXPECT_RATCHET_MODES}, excluded "
                f"{EXPECT_EXCLUDED_MODES}, uncovered {EXPECT_UNCOVERED_MODES}",
                f"builder={V73.RATCHET_MODES}/{V73.EXCLUDED_MODES}/{V73.UNCOVERED_MODES}")
    # 🛑 THE DERIVATION, CHECKED AGAINST LITERALS. The builder derives every address from the pointer
    # arrays; this file hard-codes the answer. They must agree cell for cell.
    base_img = Path(plain_image_path("_v72_plain_image.bin")).read_bytes()
    derived = V73.derive_ratchet_edits(base_img)
    want = {}
    for m, (cb, eb, cy, ey, _d) in EXPECT_RATCHET.items():
        want[cb + 0x0A] = cy
        want[eb + 0x0A] = ey
    ok &= check({a: n for a, (_o, n, _l, _m, _f, _b) in derived.items()} == want,
                f"EDIT 2: the builder's DERIVED {len(derived)} cells equal this file's literals, "
                "address for address and value for value",
                f"derived={ {hex(a): n for a, (_o, n, _l, _m, _f, _b) in derived.items()} }")
    ok &= check(len(derived) == 2 * len(EXPECT_RATCHET_MODES) == 16, "EDIT 2: exactly 16 cells")
    ok &= check({m: d for m, (_c, _e, _cy, _ey, d) in EXPECT_RATCHET.items()} ==
                {m: v[2] for m, v in V73.RATCHET_CROSSCHECK.items()},
                "EDIT 2: the per-mode creep doses agree (106 / 106 / 33 / 31 by family)")
    ok &= check(all((cy * ey) >> 10 == d for _c, _e, cy, ey, d in EXPECT_RATCHET.values()),
                "EDIT 2: every dose re-derives as (C_Y0 * E_Y0) >> 10 here, independently")
    ok &= check(not (set(EXPECT_RATCHET_MODES) & set(EXPECT_EXCLUDED_MODES)) and
                not (set(EXPECT_RATCHET_MODES) & set(EXPECT_UNCOVERED_MODES)) and
                V73.FRICTION_MODE in EXPECT_EXCLUDED_MODES,
                "EDIT 1's mode and EDIT 2's mode set are DISJOINT ⇒ at most one lever can act")
    ok &= check(bytes.fromhex(EXPECT_CAVE[1]) == V73.build_cave()[0],
                "EDIT 3: the cave hex equals the one the builder emits, byte for byte")
    ok &= check((V73.MODE_DISP, V73.MODE_MASK, V73.BIT_LIVE, V73.MODE_FIELD) ==
                (EXPECT_MODE_DISP, 0xF, 0x80, 0x78), "EDIT 3: the probe's fields agree")
    ok &= check(V73.SRC_SHA256 == BASE_SHA256, "the base image SHA256 agrees")
    ok &= check(V73.V72_LEVER_A == EXPECT_V72_LEVER_A and V73.V72_LEVER_B == EXPECT_V72_LEVER_B and
                V73.V72_LEVER_C == EXPECT_V72_LEVER_C,
                "V72's LEVER A / B / C are stated identically in both files")
    # ★ the arithmetic that licenses the no-clip claim, re-derived here rather than imported.
    ok &= check(all(d < CEILING_FLOOR for d in EXPECT_AFFECTED_MAX.values()) and
                max(EXPECT_AFFECTED_MAX.values()) == 234,
                f"EDIT 2: the newly-affected-region maxima {sorted(set(EXPECT_AFFECTED_MAX.values()))}"
                f" are all below the ceiling FLOOR {CEILING_FLOOR}")
    ok &= check((234 * 140) >> 10 == 31,
                "EDIT 2: modes 12/14 deliver 31, not 32 -- (234 * 140) >> 10 = 32760 >> 10 = 31")
    return ok


def verify(img: bytes, base: bytes, label: str):
    print(f"\n{'=' * 100}\n  VERIFYING {label}\n  SHA256 {hashlib.sha256(img).hexdigest()}")
    check(len(img) == 0x100000, "the image is exactly 1 MiB", f"len={len(img)}")
    check(hashlib.sha256(base).hexdigest() == BASE_SHA256,
          "the BASE this is compared against is the recorded V72 image",
          hashlib.sha256(base).hexdigest())

    print("\n  EDIT 1 -- GRIND #1, the friction lane (gp-0x6b26, FUN_00036c12):")
    fbase, fn, fx, fy = EXPECT_FRICTION
    arr, mode = EXPECT_FRICTION_PTR
    got_ptr = struct.unpack_from("<I", img, arr + mode * 4)[0]
    check(got_ptr == fbase,
          f"0x{arr:05X}[{mode}] -> 0x{fbase:05X} 🛑 the record is MODE-INDEXED and V73 edits mode "
          f"{mode} ONLY", f"got 0x{got_ptr:05X}")
    n, xs, ys = rec_any(img, fbase)
    check((n, xs) == (fn, fx), f"0x{fbase:05X} is a {fn}-point record with X = {fx}", f"got ({n},{xs})")
    check(ys == fy, f"0x{fbase:05X} Y row == {fy}  (the base's {FRICTION_BASE_Y} x1.5)", f"got {ys}")
    check(all(a < b <= 0 for a, b in zip(ys, ys[1:])),
          "the Y row is still all-negative and monotone toward zero -- the stock SHAPE is preserved",
          f"got {ys}")
    caddr, cval = EXPECT_CLAMP
    check(u16(img, caddr) == cval,
          f"0x{caddr:05X} (tp+0x507e, the lane's own symmetric self-clamp) == {cval}",
          f"got {u16(img, caddr)}")
    check(u16(img, EXPECT_CLAMP_NEIGHBOUR[0]) == EXPECT_CLAMP_NEIGHBOUR[1] ==
          u16(base, EXPECT_CLAMP_NEIGHBOUR[0]),
          f"0x{EXPECT_CLAMP_NEIGHBOUR[0]:05X} == {EXPECT_CLAMP_NEIGHBOUR[1]} and is UNTOUCHED "
          "(adjacent, unread by this lane, owner unidentified)",
          f"got {u16(img, EXPECT_CLAMP_NEIGHBOUR[0])}")
    try:
        readers = V73.assert_clamp_census(img)
        check([a for a, _m, _r in readers] == EXPECT_CLAMP_READERS,
              f"tp+0x507e has exactly {len(EXPECT_CLAMP_READERS)} readers "
              f"({[hex(r) for r in EXPECT_CLAMP_READERS]}), all `ld.h`, ZERO writers ⇒ no lockstep "
              "monitor can be checking it")
    except AssertionError as exc:
        check(False, "the clamp's reader/writer census", str(exc))
    for m, (addr, want) in sorted(EXPECT_FRICTION_TWINS.items()):
        got = rec_any(img, addr)[2]
        check(got == want and img[addr:addr + 0x10] == base[addr:addr + 0x10],
              f"the mode-{m} friction record 0x{addr:05X} is BYTE-STOCK ({want}) -- V73's LERP half "
              f"is INERT in mode {m}", f"got {got}")

    print(f"\n  EDIT 2 -- THE RATCHET, modes {EXPECT_RATCHET_MODES} (`Y[0] := that record's own "
          "Y[1]`):")
    grid_vr = [(v, r) for v in range(0, 14001, 64) for r in range(0, 4501, 25)]
    for mode, (cb, eb, cy0, ey0, dose) in sorted(EXPECT_RATCHET.items()):
        for ptrs, want, nm in ((FACTOR_C_PTRS, cb, "FactorC"), (FACTOR_E_PTRS, eb, "FactorE")):
            got = struct.unpack_from("<I", img, ptrs + mode * 4)[0]
            check(got == want, f"mode {mode:2d}: 0x{ptrs:05X}[{mode}] -> 0x{want:05X}  ({nm})",
                  f"got 0x{got:05X}")
        for rbase, y0, nm in ((cb, cy0, "FactorC"), (eb, ey0, "FactorE")):
            n, xs, ys = rec_any(img, rbase)
            was = rec_any(base, rbase)[2]
            check((n, xs) == (4, rec_any(base, rbase)[1]),
                  f"mode {mode:2d} {nm} 0x{rbase:05X} is a 4-point record with an unchanged X row",
                  f"got ({n}, {xs})")
            check(ys[0] == y0 == was[1] and ys[1:] == was[1:],
                  f"mode {mode:2d} {nm} 0x{rbase:05X}: Y[0] == {y0} == its OWN Y[1], and Y[1..3] are "
                  f"unchanged ⇒ {ys}", f"got {ys}, base {was}")
            check(all(b >= a for a, b in zip(ys, ys[1:])),
                  f"mode {mode:2d} {nm} Y is MONOTONE non-decreasing", f"got {ys}")
            # 🛑 THE V72 LESSON, ASSERTED: a FLAT damper row is a near-bang-bang relay and a
            # limit-cycle hazard. V72 did that to mode 10's FactorE; V73 must not repeat it.
            check(len(set(ys)) > 1,
                  f"mode {mode:2d} {nm} Y is NOT flat ⇒ the damper stays RATE/SPEED-PROPORTIONAL "
                  "(V72 flattened mode 10's FactorE to [927,927,927,927]; this build does not)",
                  f"got {ys}")
        # FactorB/D flat 1024, and this mode's OWN ceiling floor -- re-read per mode, not assumed.
        for ptrs, nm in ((V73.FACTOR_B_PTRS, "FactorB"), (V73.FACTOR_D_PTRS, "FactorD")):
            fb = struct.unpack_from("<I", img, ptrs + mode * 4)[0]
            n, _xs, ys = rec_any(img, fb)
            check(set(ys) == {1024},
                  f"mode {mode:2d} {nm} 0x{fb:05X} ({n}-point) is FLAT 1024 ⇒ inert in the Q10 chain",
                  f"got {sorted(set(ys))}")
        cl = struct.unpack_from("<I", img, CEILING_PTRS + mode * 4)[0]
        got_ceil = rec_any(img, cl)
        check(got_ceil == EXPECT_CEILING_ROW,
              f"mode {mode:2d} ceiling 0x{cl:05X} == {EXPECT_CEILING_ROW} ⇒ its OWN FLOOR "
              f"{CEILING_FLOOR}, verified per mode", f"got {got_ceil}")
        # the delivered dose, and the correctly-scoped no-clip claim
        creep = V73.damper_authority(img, mode, 0, 0)
        cx = rec_any(img, cb)[1]
        ex = rec_any(img, eb)[1]
        aff = max(V73.damper_authority(img, mode, v, r) for v, r in grid_vr
                  if v <= cx[1] or r <= ex[1])
        peak = max(V73.damper_authority(img, mode, v, r) for v, r in grid_vr)
        peak_b = max(V73.damper_authority(base, mode, v, r) for v, r in grid_vr)
        check(creep == dose == (cy0 * ey0) >> 10 < got_ceil[2][0],
              f"mode {mode:2d}: creep dose == {dose} counts == (({cy0} * {ey0}) >> 10), below its "
              f"own floor {got_ceil[2][0]}", f"got {creep}")
        check(aff == EXPECT_AFFECTED_MAX[mode] < got_ceil[2][0],
              f"mode {mode:2d}: the max over the NEWLY AFFECTED region "
              f"({{v <= {cx[1]}}} U {{r <= {ex[1]}}}) is {EXPECT_AFFECTED_MAX[mode]}, under its own "
              f"floor {got_ceil[2][0]} ⇒ no saturation where V73 changed anything", f"got {aff}")
        check(peak == peak_b,
              f"mode {mode:2d}: the GLOBAL peak is {peak}, IDENTICAL to the base -- only Y[0] moved "
              "and the peak lives at Y[3]", f"got {peak} vs base {peak_b}")
    print("    ⚠ SCOPE, STATED: a blanket 'max < 512 everywhere' is FALSE on modes 4/5/12/14 (global")
    print("      peaks 792/821) and EQUALLY false on the base, where the ceiling LERP has itself")
    print("      risen to 1024 -- so it is not a V73 requirement. The scoped claim above is.")
    print("    🛑 DOSE SPREAD: modes 0-3 deliver 106 counts, 4/5 deliver 33, 12/14 deliver 31. A null")
    print("       on a 4/5/12/14 reading is an UNDER-DOSE, not a falsification of the lever.")
    for m, (c, e) in sorted(EXPECT_UNCOVERED_RECORDS.items()):
        for addr in (c, e):
            check(img[addr:addr + 0x14] == base[addr:addr + 0x14],
                  f"⚠ the mode-{m} record 0x{addr:05X} is UNTOUCHED -- 13 and 15 are TVAA7's "
                  "e013/e015 arms and V73 does NOT cover them")
    for m in EXPECT_EXCLUDED_MODES:
        for ptrs in (FACTOR_C_PTRS, FACTOR_E_PTRS):
            addr = struct.unpack_from("<I", img, ptrs + m * 4)[0]
            check(rec_any(img, addr)[2] == EXPECT_V72_LEVER_B[addr],
                  f"🛑 mode {m}'s record 0x{addr:05X} is EXACTLY at V72's LEVER B value "
                  f"{EXPECT_V72_LEVER_B[addr]} -- 10/11 are EXCLUDED from V73's loop by design",
                  f"got {rec_any(img, addr)[2]}")

    print("\n  EDIT 3 -- THE PROBE: the cave, its re-disassembly, and RAM ownership:")
    cbase, want_hex = EXPECT_CAVE
    got = bytes(img[cbase:cbase + 68])
    check(got.hex() == want_hex, "the 68-byte cave matches, byte for byte", f"got {got.hex()}")
    check(img[EXPECT_CAVE_HOOK[0]:EXPECT_CAVE_HOOK[0] + 4].hex() == EXPECT_CAVE_HOOK[1] ==
          base[EXPECT_CAVE_HOOK[0]:EXPECT_CAVE_HOOK[0] + 4].hex(),
          f"the hook @0x{EXPECT_CAVE_HOOK[0]:05X} is `jarl 0x{cbase:05X}` and is byte-identical to "
          "the base")
    check(img[EXPECT_HOOK_RETURN[0]:EXPECT_HOOK_RETURN[0] + 2].hex() == EXPECT_HOOK_RETURN[1],
          f"0x{EXPECT_HOOK_RETURN[0]:05X} (the return point) is `mov 0x8,r7` ⇒ **r7 is PROVABLY DEAD "
          "across the hook**")
    check(got[EXPECT_CAVE_CODE_LEN:] == bytes(68 - EXPECT_CAVE_CODE_LEN),
          f"the {68 - EXPECT_CAVE_CODE_LEN} bytes after `jmp [lp]` are all 0x00 (`nop`) ⇒ "
          "unreachable, and the extent is still the proven 68")
    # 🛑🛑 THE MODE LOAD'S ONE-BIT TRAP, checked against the REAL st.b twin's bytes. Assemble the
    # HALFWORD first -- picking the opcode field out of individual bytes by hand is the exact
    # "build upward from raw bytes" mistake this kit keeps paying for.
    check(got[4:8] == bytes.fromhex("a437fd63"),
          "cave offset 4 is `ld.bu 0x63fd[gp],r6` -- byte-identical to the real one @0x346B4",
          f"got {got[4:8].hex()}")
    check(got[4:8] != bytes.fromhex("4447fd63"),
          "the mode load is NOT the real `st.b r8,0x63fd,gp` @0x426AE -- a slip there would REWRITE "
          "the byte every damper factor table, the friction lane and r24's gain_B all index on")
    hw1 = u16(img, cbase + 4)
    check((hw1 >> 5) & 0x3F == 0x3D,
          "the mode load's opcode field is 0x3D (ld.bu with an ODD displacement); 0x3C is the EVEN "
          "form and 0x3A is st.b", f"got 0x{(hw1 >> 5) & 0x3F:02X}")
    check(u16(img, cbase + 6) == EXPECT_MODE_DISP,
          f"the mode load carries the POSITIVE displacement +0x{EXPECT_MODE_DISP:04X}",
          f"got 0x{u16(img, cbase + 6):04X}")
    # 🛑🛑 `or r6,r7` vs `or r7,r6`: SAME opcode, register fields SWAPPED, BOTH real in this image.
    _or = u16(img, cbase + 12)
    check(((_or >> 5) & 0x3F, _or >> 11, _or & 0x1F) == (0x08, 7, 6),
          "cave offset 12 is `or r6,r7` (mode INTO the payload), decoded by FIELD -- `or r7,r6` "
          "would OR the mode into the SCRATCH register and every frame would read mode 0",
          f"got op 0x{(_or >> 5) & 0x3F:02X}, dest r{_or >> 11}, src r{_or & 0x1F}")
    redis = V73.redisassemble_cave(got, cbase)
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    check(len(stores) == 1 and stores[0][1] == "st.b r6,-5396[r4]",
          "the cave contains EXACTLY ONE store, and it is the st.b to the CAN-330 payload byte",
          f"got {stores}")
    ldbu = [m for _a, _r, m in redis if m.startswith("ld.bu ")]
    check(ldbu == [f"ld.bu {EXPECT_MODE_DISP}[r4],r6", "ld.bu -5396[r4],r6"],
          "the cave READS exactly two cells: gp+0x63FD (the mode) and gp-0x1514 (the CAN byte)",
          f"got {ldbu}")
    check(all(m == "nop" for _a, _r, m in redis[11:]), "the padding re-disassembles as nop")
    cave_span = range(cbase, cbase + 68)
    try:
        nr, nw = V73.assert_mode_census(img, cave_span, expect_cave=True)
        check((nr, nw) == (EXPECT_MODE_CENSUS[0], len(EXPECT_MODE_CENSUS[1])),
              f"gp+0x{EXPECT_MODE_DISP:04X} firmware census is {EXPECT_MODE_CENSUS[0]}r / "
              f"{len(EXPECT_MODE_CENSUS[1])}w at {[hex(w) for w in EXPECT_MODE_CENSUS[1]]} (all "
              "inside FUN_00042746), and the cave READS it once and WRITES it never",
              f"got {nr}r / {nw}w")
    except AssertionError as exc:
        check(False, "the gp+0x63FD census", str(exc))
    for disp, (nread, writers) in sorted(EXPECT_RETIRED.items()):
        hits = V64.gp_access_census(img, disp)
        rd = [h for h in hits if h[0] not in cave_span and h[1].startswith("ld.")]
        wr = [h for h in hits if h[0] not in cave_span and not h[1].startswith("ld.")]
        check(not [h for h in hits if h[0] in cave_span] and len(rd) == nread and
              [a for a, _m, _r in wr] == writers,
              f"gp-0x{disp:04x} is RETIRED (V72 probed it): the cave does not touch it and its "
              f"firmware census is unchanged at {nread}r / {len(writers)}w",
              f"got cave={[hex(h[0]) for h in hits if h[0] in cave_span]}, {len(rd)}r / {len(wr)}w")

    print("\n  🛑 V72's LEVERS, CARRIED BYTE-IDENTICALLY -- asserted BY VALUE:")
    for lname, table in (("LEVER A", EXPECT_V72_LEVER_A), ("LEVER B", EXPECT_V72_LEVER_B)):
        for b_, want in sorted(table.items()):
            got_y = rec4_y(img, b_)
            check(got_y == want == rec4_y(base, b_), f"V72 {lname} 0x{b_:05X} Y == {want}",
                  f"got {got_y}")
    check(u16(img, EXPECT_V72_LEVER_C[0]) == EXPECT_V72_LEVER_C[1],
          f"V72 LEVER C 0x{EXPECT_V72_LEVER_C[0]:05X} == {EXPECT_V72_LEVER_C[1]}",
          f"got {u16(img, EXPECT_V72_LEVER_C[0])}")
    check(u16(img, EXPECT_V72_CARRIED[0]) == EXPECT_V72_CARRIED[1],
          f"the carried 0x{EXPECT_V72_CARRIED[0]:05X} == 0x{EXPECT_V72_CARRIED[1]:04X} "
          "(`br 0x455C4`; 🛑 INERT and UNTESTED, not a fix and not falsified)",
          f"got 0x{u16(img, EXPECT_V72_CARRIED[0]):04X}")
    check(img[EXPECT_V72_CARRIED[0] + 1] == 0x65,
          "the branch's HIGH byte is untouched ⇒ the DISPLACEMENT is provably unchanged")
    check(img[EXPECT_V72_GATE[0]] == EXPECT_V72_GATE[1],
          f"the gate 0x{EXPECT_V72_GATE[0]:05X} == 0x{EXPECT_V72_GATE[1]:02X} (gp-0x683c, ZERO "
          "writers) ⇒ V73 is UNGATED, exactly like V72 -- the dose applies in MANUAL too",
          f"got 0x{img[EXPECT_V72_GATE[0]]:02X}")

    print("\n  🛑 MUST REMAIN BYTE-STOCK -- asserted BY VALUE, not by span:")
    for addr, want in sorted(EXPECT_STOCK_HALFWORDS.items()):
        check(u16(img, addr) == want, f"0x{addr:05X} == {want}", f"got {u16(img, addr)}")
    for addr, want in sorted(EXPECT_SAR_SITES.items()):
        check(u16(img, addr) == want,
              f"0x{addr:05X} == 0x{want:04X} -- `sar 0xa`, V62's lever is NOT carried",
              f"got 0x{u16(img, addr):04X}")
    for b_, want in sorted(EXPECT_STOCK_RECORDS.items()):
        got_y = rec4_y(img, b_)
        check(got_y == want, f"0x{b_:05X} Y row == {want} (stock)", f"got {got_y}")
    rbase, rwant = EXPECT_ROLE_TABLE
    rgot = list(img[rbase:rbase + len(rwant)])
    check(rgot == rwant and not any(r in (6, 7) for r in rgot),
          f"0x{rbase:05X} role table == {rwant} and no slot carries role 6 or 7 ⇒ gp-0x67ac cannot "
          "read 1 ⇒ NO lever on this build is vacuous", f"got {rgot}")
    for n_, (key, modes) in sorted(EXPECT_VARIANT_ROWS.items()):
        o = 0xCD000 + n_ * 0x24
        gk = bytes(img[o:o + 5]).decode("ascii", "replace")
        gm = list(img[o + 0x12:o + 0x16])
        check((gk, gm) == (key, modes),
              f"the HW-ID table row {n_} is {key!r} -> modes {modes} -- V73's mode choices rest on it",
              f"got {gk!r} -> {gm}")
    try:
        _rows, aliasing = V73.assert_mode_field_lossless(img)
        check(True, f"every mode a TVA-family or blank row can select is < 16 ⇒ the probe's 4-bit "
                    f"field is LOSSLESS for this car ({len(aliasing)} TVC/TWA rows WOULD alias)")
    except AssertionError as exc:
        check(False, "the 4-bit mode field is lossless for this car", str(exc))

    print("\n  CRC:")
    check(walk_all_blocks(img) == 0, "the full bootloader CRC chain: 50/50 blocks PASS")
    moved = sorted(t for t in range(V73.START, 0x100000 - 3)
                   if (t & 0xFFF) == 0xFFC and img[t:t + 4] != base[t:t + 4])
    check(moved == sorted(CRC_BLOCKS_MOVED),
          f"EXACTLY {len(CRC_BLOCKS_MOVED)} trailers moved (MAIN + 0xCE000/0xCF000/0xD0000/0xD2000/"
          f"0xD3000): {[hex(t) for t in CRC_BLOCKS_MOVED]}", f"got {[hex(t) for t in moved]}")
    ratchet_bytes = {rec + 0x0A + k for cb, eb, _cy, _ey, _d in EXPECT_RATCHET.values()
                     for rec in (cb, eb) for k in (0, 1)}
    owned = set(range(EXPECT_CAVE[0], EXPECT_CAVE[0] + 68)) | \
        {EXPECT_CLAMP[0], EXPECT_CLAMP[0] + 1} | \
        {EXPECT_FRICTION[0] + 0x08 + k for k in range(6)} | ratchet_bytes
    check(not [a for a in owned if CRC_SKIPPED_BLOCK[0] <= a < CRC_SKIPPED_BLOCK[1]],
          f"NO edited byte lands in [0x{CRC_SKIPPED_BLOCK[0]:05X},0x{CRC_SKIPPED_BLOCK[1]:05X}) -- "
          "the CRC-SKIPPED block with the V40 ignition-brick precedent")

    print("\n  DIFF ACCOUNTING vs the V72 base:")
    d = [i for i in range(V73.START, V73.END) if img[i] != base[i]]
    crc_only = {t + k for t in CRC_BLOCKS_MOVED for k in range(4)}
    f = [i for i in d if i not in crc_only]
    stray = [i for i in f if i not in owned]
    check(not stray, f"all {len(f)} functional bytes vs the base are attributable to V73's own "
                     f"edits ({len(d) - len(f)} CRC bytes)", f"stray {[hex(x) for x in stray[:8]]}")
    # ⚠ these are bytes that DIFFER, not bytes EDITED, and the two counts are NOT equal: 32 ratchet
    # bytes are written but 12 high halves were already 0x00 (every value under 256 -- 115, 142, 140,
    # 242), and 7 of the 68 cave bytes coincide with V72's. Counting WRITTEN bytes here would be an
    # off-by-19 stated as fact, which is exactly the class of error this file exists to catch.
    by = {"cave": len([i for i in f if EXPECT_CAVE[0] <= i < EXPECT_CAVE[0] + 68]),
          "clamp": len([i for i in f if i in (EXPECT_CLAMP[0], EXPECT_CLAMP[0] + 1)]),
          "friction": len([i for i in f if EXPECT_FRICTION[0] + 8 <= i < EXPECT_FRICTION[0] + 14]),
          "ratchet": len([i for i in f if i in ratchet_bytes])}
    check(len(f) == sum(by.values()) and by == {"cave": 61, "clamp": 2, "friction": 6, "ratchet": 20},
          f"the functional diff is exactly {sum(by.values())} DIFFERING bytes: {by}",
          f"got {len(f)}, {by}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=None)
    ap.add_argument("--rwd", default=None)
    args = ap.parse_args()

    base = Path(plain_image_path("_v72_plain_image.bin")).read_bytes()
    _stock = Path(stock_fw_path("code.bin")).read_bytes()

    if not cross_check_against_builder():
        print("\n🛑 THE TWO STATEMENTS OF THE SPEC DISAGREE. Nothing below can be trusted.")
        return 1

    if args.rwd:
        rwd = Path(args.rwd).read_bytes()
        FF.assert_x31_checksum(rwd, "the .rwd under test")
        info = parse_x31(rwd)
        decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        img = bytearray(base)
        img[V73.START:V73.END] = bytes(info["encs"][0]).translate(decode)
        verify(bytes(img), base, f"{args.rwd} (decoded payload)")
    else:
        p = Path(args.image) if args.image else Path(plain_image_path("_v73_plain_image.bin"))
        verify(p.read_bytes(), base, str(p))

    print("\n" + "=" * 100)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"     - {f}")
        return 1
    print(f"  ✅ V73 VERIFIED. Both halves of the friction lever, all 16 ratchet cells across modes")
    print(f"     {EXPECT_RATCHET_MODES} with their monotone / proportional / per-mode-no-clip")
    print(f"     properties, modes {EXPECT_EXCLUDED_MODES} at V72's values and "
          f"{EXPECT_UNCOVERED_MODES} untouched, the cave")
    print("     and its re-disassembly, the gp+0x63FD census, every V72 lever at its V72 value,")
    print("     every MUST-REMAIN-STOCK site, the CRC chain and the full diff accounting.")
    print("  🛑 Verification is not authorisation. Flash only on the operator's explicit")
    print("     instruction, naming the file and the bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
