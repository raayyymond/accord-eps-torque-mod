#!/usr/bin/env python3
"""verify_v76_image.py -- VALUE-ANCHORED verification of a built V76 image.

🛑🛑 STATUS: V76 is **BUILT, UNFLASHED**, and it is a **SIBLING** of V75, not a successor. Both
branch from the same V74 base -- V75 cranks the DAMPER dose 2.74x, V76 restores the RATE LANE -- and
the operator chooses ONE to fly. **Verification is not clearance.** Nothing this file prints is a
flight decision.

🛑 WHY THIS EXISTS AND WHY IT IS NOT `diff_build_vs_stock.py`.
That tool is SPAN-based: it asks "which byte ranges moved?" A span check passes on the WRONG BUILD --
two images that edit the same addresses to different values are indistinguishable to it, and the kit
has a recorded case where a re-cut under the same number produced an artefact no gate could check.
This file asserts the ACTUAL VALUES at every site, including every MUST-REMAIN site, so it fails on
any image that is not V76.

🛑 IT DOES NOT SIMPLY IMPORT THE BUILDER'S NUMBERS AND COMPARE THEM TO THEMSELVES. Every expected
address and value below is re-declared here as a LITERAL and then CROSS-CHECKED against
`build_v76_tva.py`'s own tables AND re-derived from the image, so a typo in either one is caught.

★ WHAT V76 IS. V74's damper, byte for byte, plus V67/V68's rate-lane configuration -- the best
grind-#1 result in this kit's history, off the car since V68. TWO cells:
    `0x3AA96`  `0xC5 -> 0xFB`   ONE in-place branch-operand byte. Repoints `ld.bu -0x683c[gp],r15`
                                @0x3AA94 to `ld.bu -0x6806[gp],r15` -- from a DEAD cell to the
                                LKAS-applying flag.
    `0xC6446`  `512 -> 5244`    r24's gate-active arm.
    `0xC6444`  UNCHANGED at 512 -- it already holds V67/V68's value. ASSERTED, never written.
  Both are MODE-PROOF: reached by plain `ld.hu <disp>[tp]` scalars with no `mode*4` index, which is
  why RULE 7 voided V69/V70 but not V67/V68.

★★ THE STRUCTURAL PROOF OF THE REPOINT IS A CENSUS, AND IT IS TWO-SIDED:
    `gp-0x683c`   1 firmware reader on V74 -> **0** on V76   (the dead cell is abandoned)
    `gp-0x6806`  13 firmware readers on V74 -> **14**, the new one at EXACTLY `0x3AA94`
  A one-byte edit that failed to land, or landed on a neighbouring cell, cannot produce that pair.

🛑 AND THE NEGATIVE: **V75's levers must be ABSENT.** All 204 damper records (FactorB/C/D/E +
ceiling + friction, over all 34 modes) are asserted byte-identical to V74, so the two siblings are
provably single-variable against each other.

Usage:  python verify_v76_image.py [IMAGE]
        python verify_v76_image.py --rwd PATH     (decode a .rwd and verify the payload)
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
import build_v76_tva as V76                # noqa: E402
from encode_eps import parse_x31, build_decode_table                        # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path                  # noqa: E402
from verify_bootloader_crc import walk_all_blocks                           # noqa: E402

START, END = V76.START, V76.END
CAVE_BASE, CAVE_EXTENT = 0xC4B34, 68
FAILS: list[str] = []

# =====================================================================================================
# EVERY EXPECTATION, RE-DECLARED AS A LITERAL. Cross-checked against the builder below.
# =====================================================================================================
EXPECT_BASE_SHA = "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959"
EXPECT_IMAGE_SHA = "f27e1fd8540c52c753e9513f6ab9db4599f3d65400dd400cd393b91322cd2b5e"
EXPECT_RWD_SHA = "5ea4f75825964897d6e0e18b721e4b759fe74b5bd8aea115d9dadccf4790eca9"
EXPECT_IMAGE_NAME = "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"
EXPECT_RWD_NAME = ("39990-TVA,A160-V76-V74BASE-GATE-FB-ARM5244-gateprobe-6806-671d-671a-"
                   "0x13000-0x100000.rwd")

# ---- THE TWO LEVERS ---------------------------------------------------------------------------
EXPECT_GATE_INSN_ADDR = 0x3AA94
EXPECT_GATE_ADDR = 0x3AA96
EXPECT_GATE_BYTE_OLD, EXPECT_GATE_BYTE_NEW = 0xC5, 0xFB
EXPECT_GATE_INSN_OLD, EXPECT_GATE_INSN_NEW = "847fc597", "847ffb97"
EXPECT_GATE_DISP_OLD, EXPECT_GATE_DISP_NEW = 0x683C, 0x6806
EXPECT_ARM_B = (0xC6446, 512, 5244)          # (addr, V74, V76)
EXPECT_ARM_A = (0xC6444, 512)                # 🛑 ASSERTED, NEVER WRITTEN
# ---- THE KEEP-LIST, by value -------------------------------------------------------------------
EXPECT_LADDER_KEEP = {0xC643E: 1536, 0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512}
EXPECT_THRESHOLD = (0xC64FA, 5, 517)         # (addr, the BYTE, its u16 -- the V63 trap)
EXPECT_SAR = {0x3AB76: "aa32", 0x3AC20: "aa42"}
EXPECT_GAIN_A = {0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}
EXPECT_GAIN_A_STOCK = (0xC6A90, 0xC6AA4)     # ⚠ byte-STOCK: V72's r26 cut is PARTIAL by design
EXPECT_CARRIED = (0x454FE, 0xB5)
EXPECT_CLAMP = (0xC407E, 850)
EXPECT_LADDER_SPANS = {0x3AB56: 0x3AB6C, 0x3ABFA: 0x3AC16}
EXPECT_LADDER_BRANCHES = {0x3AB5C: ("c205", 0x2, 8), 0x3AC06: ("c205", 0x2, 8)}   # (hex, cond, disp)
# ---- THE DAMPER LANE -- V75's territory, frozen here -------------------------------------------
EXPECT_DAMPER_PTRS = (0xC9CCC, 0xC9E9C, 0xC9DB4, 0xC9F84, 0xC77A0, 0xCBE74)
EXPECT_DAMPER_RECORDS = 6 * 34               # 204: every factor, every mode
EXPECT_ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
EXPECT_DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
# ---- THE CAVE -----------------------------------------------------------------------------------
EXPECT_CAVE_HEX = ("003a24373094e031a205483a8437fb97e031a205443aa437e398e031a205423a8437e798"
                   "6532a605413ac43a8437edeac636070007314437ecea2436e8ea7f0000000000")
EXPECT_CAVE_CODE_LEN, EXPECT_PAD = 64, 4
EXPECT_CAVE_ASM = [
    "mov 0,r7", "ld.h -27600[r4],r6", "cmp r0,r6", "be +4", "add 8,r7",
    "ld.bu -26630[r4],r6", "cmp r0,r6", "be +4", "add 4,r7",
    "ld.bu -26397[r4],r6", "cmp r0,r6", "be +4", "add 2,r7",
    "ld.bu -26394[r4],r6", "cmp 5,r6", "blt +4", "add 1,r7", "shl 0x4,r7",
    "ld.bu -5396[r4],r6", "andi 0x0007,r6,r6", "or r7,r6", "st.b r6,-5396[r4]",
    "movea 0xeae8,r4,r6", "jmp [lp]"]
EXPECT_PROBED = {0x6BD0: "the damper output (SIGNED ld.h)", 0x6806: "THE GATE (ld.bu, EVEN disp)",
                 0x671D: "the mask (ld.bu, ODD disp -> op 0x3D)", 0x671A: "the third arm's index"}
EXPECT_NOT_PROBED = {0x67FA: "V74's state cell", 0x6AC2: "V75's back-drive cell"}
EXPECT_DEAD_DISP = 0x683C
EXPECT_CENSUS_V74 = {0x6BD0: (5, 3), 0x6806: (13, 16), 0x671D: (14, 2), 0x671A: (7, 1),
                     0x683C: (1, 0)}
EXPECT_CENSUS_V76 = {0x6BD0: (5, 3), 0x6806: (14, 16), 0x671D: (14, 2), 0x671A: (7, 1),
                     0x683C: (0, 0)}
EXPECT_SHADOWS = (0x4C39, 0x4CF2, 0x4CC6)
EXPECT_PROBE_MASK = 0xF0
EXPECT_BITS = {"bit7 damper != 0": 0x80, "bit6 THE GATE gp-0x6806 != 0": 0x40,
               "bit5 the mask gp-0x671d != 0": 0x20, "bit4 gp-0x671a >= 5": 0x10}
EXPECT_BIT_UNUSED = 0x08                     # 🛑 STRUCTURALLY ZERO -- the build-identity guard
EXPECT_LEGAL_PAYLOADS = tuple(v << 4 for v in range(16))
EXPECT_HOOK_ADDR, EXPECT_HOOK_RETURN_INSN = 0x55C0E, "083a"
# ---- CRC / diff accounting ------------------------------------------------------------------------
EXPECT_TRAILERS = [0xC4FFC, 0xC6FFC]
EXPECT_DIFF_BY_LEVER = {"gate": 1, "arm": 2, "cave": 53}
EXPECT_FUNCTIONAL_BYTES = 56
CRC_SKIPPED = (0xC5000, 0xC5FFC)
# ---- the delivered ratios --------------------------------------------------------------------------
EXPECT_GAIN_B_CREEP, EXPECT_GAIN_A_CREEP = 3072, 3072
EXPECT_R24_RATIO, EXPECT_R26_RATIO = 5244 / 3072, 512 / 3072
EXPECT_PARITY_A = 0.848


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


def cross_check_against_builder():
    """🛑 THE TWO STATEMENTS OF THE SPEC MUST AGREE. Importing alone could never catch a typo."""
    print("=" * 100)
    print("  CROSS-CHECK -- this file's literals against build_v76_tva.py's own tables")
    ok = True
    ok &= check(EXPECT_BASE_SHA == V76.SRC_SHA256, "the V74 base SHA256 agrees",
                f"base SHA differs: {EXPECT_BASE_SHA} vs {V76.SRC_SHA256}")
    ok &= check((EXPECT_GATE_INSN_ADDR, EXPECT_GATE_ADDR) == (V76.GATE_INSN_ADDR, V76.GATE_ADDR)
                and (EXPECT_GATE_BYTE_OLD, EXPECT_GATE_BYTE_NEW) ==
                (V76.GATE_BYTE_V74, V76.GATE_BYTE_V76),
                f"the gate lever agrees: 0x{EXPECT_GATE_ADDR:05X} "
                f"0x{EXPECT_GATE_BYTE_OLD:02X} -> 0x{EXPECT_GATE_BYTE_NEW:02X}",
                "the gate lever differs")
    ok &= check(EXPECT_GATE_INSN_OLD == V76.GATE_INSN_V74.hex()
                and EXPECT_GATE_INSN_NEW == V76.GATE_INSN_V76.hex(),
                "both gate instruction encodings agree", "a gate instruction encoding differs")
    ok &= check((EXPECT_GATE_DISP_OLD, EXPECT_GATE_DISP_NEW) ==
                (V76.GATE_DISP_V74, V76.GATE_DISP_V76),
                f"the two displacements agree: -0x{EXPECT_GATE_DISP_OLD:04X} (dead) -> "
                f"-0x{EXPECT_GATE_DISP_NEW:04X} (the gate)", "a displacement differs")
    ok &= check(EXPECT_ARM_B == (V76.ARM_B_ADDR, V76.ARM_B_V74, V76.ARM_B_V76),
                f"the arm lever agrees: 0x{EXPECT_ARM_B[0]:05X} {EXPECT_ARM_B[1]} -> "
                f"{EXPECT_ARM_B[2]}", "the arm lever differs")
    ok &= check(EXPECT_ARM_A == (V76.ARM_A_ADDR, V76.ARM_A_VALUE),
                f"0x{EXPECT_ARM_A[0]:05X} = {EXPECT_ARM_A[1]} is ASSERT-ONLY in both files",
                "the assert-only arm differs")
    ok &= check(EXPECT_LADDER_KEEP == V76.LADDER_KEEP, "the four keep-list arms agree",
                "the keep-list arms differ")
    ok &= check((EXPECT_THRESHOLD[0], EXPECT_THRESHOLD[1]) ==
                (V76.ARM_THRESHOLD_ADDR, V76.ARM_THRESHOLD),
                f"the BYTE cal 0x{EXPECT_THRESHOLD[0]:05X} = {EXPECT_THRESHOLD[1]} agrees "
                f"(⚠ its u16 is {EXPECT_THRESHOLD[2]} -- the V63 trap)",
                "the threshold cal differs")
    ok &= check({a: v.hex() for a, v in V76.SAR_SITES.items()} == EXPECT_SAR,
                "both `sar` sites agree and are at STOCK", "a `sar` site differs")
    ok &= check(EXPECT_GAIN_A == V76.V72_GAIN_A, "V72's gain_A r26 cut agrees", "gain_A differs")
    ok &= check(EXPECT_CARRIED == V76.V72_CARRIED and EXPECT_CLAMP == V76.CLAMP_KEEP,
                "the carried 0x454FE and the 850 clamp agree", "a carried value differs")
    ok &= check(EXPECT_LADDER_SPANS == V76.LADDER_SPANS, "both selector spans agree",
                "a selector span differs")
    ok &= check(EXPECT_DAMPER_PTRS == (V76.FACTOR_B_PTRS, V76.FACTOR_C_PTRS, V76.FACTOR_D_PTRS,
                                       V76.FACTOR_E_PTRS, V76.CEILING_PTRS, V76.FRICTION_PTR_ARRAY),
                "the six damper pointer arrays agree", "a pointer array differs")
    ok &= check(EXPECT_ENGAGED == V76.ENGAGED_EXPECTED and
                EXPECT_DISENGAGED == V76.DISENGAGED_EXPECTED,
                "both mode columns agree", "a mode column differs")
    ok &= check(not (set(EXPECT_ENGAGED) & set(EXPECT_DISENGAGED)),
                "the two columns are DISJOINT (stated independently of the image)",
                "the two columns OVERLAP")
    built = V76.build_cave()
    ok &= check(EXPECT_CAVE_HEX == built[0].hex(),
                "the cave hex agrees with the builder's emitted bytes", "the cave hex differs")
    ok &= check(len(EXPECT_CAVE_HEX) // 2 == CAVE_EXTENT == 68 and
                built[2] == EXPECT_CAVE_CODE_LEN and
                EXPECT_CAVE_CODE_LEN + EXPECT_PAD == CAVE_EXTENT,
                f"the cave is {EXPECT_CAVE_CODE_LEN}B of code + {EXPECT_PAD}B pad = the proven "
                f"{CAVE_EXTENT}B region", "the cave geometry differs")
    ok &= check(tuple(EXPECT_BITS.values()) == (V76.BIT_DAMP_NZ, V76.BIT_GATE, V76.BIT_MASK,
                                                V76.BIT_ARM3)
                and EXPECT_PROBE_MASK == V76.PROBE_MASK and EXPECT_BIT_UNUSED == V76.BIT_UNUSED,
                "the four probe bits, the mask and the UNUSED bit3 agree", "the probe bits differ")
    ok &= check(EXPECT_LEGAL_PAYLOADS == V76.LEGAL_PAYLOADS and len(EXPECT_LEGAL_PAYLOADS) == 16,
                f"all {len(EXPECT_LEGAL_PAYLOADS)} reachable payloads agree",
                "the legal payload set differs")
    ok &= check(tuple(EXPECT_PROBED) == (V76.DAMP_DISP, V76.GATE_DISP, V76.MASK_DISP, V76.ARM3_DISP),
                "the four probed cells agree", "the probed cells differ")
    ok &= check(tuple(EXPECT_NOT_PROBED) == (V76.STATE_DISP, V76.BACKDRIVE_DISP)
                and all(V76.CAVE_ACCESS_ON_OUTPUT[d] == 0 for d in EXPECT_NOT_PROBED),
                "the two cells V76 must NOT read agree and are asserted at 0 accesses",
                "the not-probed set differs")
    ok &= check(EXPECT_DEAD_DISP == V76.DEAD_DISP, "the dead cell agrees", "the dead cell differs")
    ok &= check({d: (r, w) for d, (r, w, _rm, _wm) in V76.CENSUS_BASE.items()} == EXPECT_CENSUS_V74
                and {d: (r, w) for d, (r, w, _rm, _wm) in V76.CENSUS_OUT.items()} == EXPECT_CENSUS_V76,
                "both censuses agree, INCLUDING the two-sided repoint (683c 1->0, 6806 13->14)",
                "a census differs")
    ok &= check(tuple(sorted(EXPECT_SHADOWS)) == tuple(sorted(V76.SHADOW_DISPS)),
                "the three lockstep shadows agree", "the shadow set differs")
    ok &= check(EXPECT_TRAILERS == sorted(EXPECT_TRAILERS) and len(EXPECT_TRAILERS) == 2,
                "the expected trailer list is well-formed", "the trailer list is malformed")
    ok &= check(abs(EXPECT_R24_RATIO - V76.R24_RATIO_EXPECT) < 1e-9
                and abs(EXPECT_R26_RATIO - V76.R26_RATIO_EXPECT) < 1e-9
                and EXPECT_PARITY_A == V76.PARITY_A,
                f"the two-lane ratios agree: r24 x{EXPECT_R24_RATIO:.5f}, r26 "
                f"/{1 / EXPECT_R26_RATIO:.2f}, parity at a = {EXPECT_PARITY_A}",
                "a delivered ratio differs")
    # ★ bit3 must be structurally zero on the builder's OWN wire model, over a wide sample
    bad = [(d, g, m, a) for d in (0, 1, 0xFFFF) for g in (0, 1, 255) for m in (0, 1, 255)
           for a in (0, 4, 5, 255) if V76.wire_byte4(d, g, m, a) & EXPECT_BIT_UNUSED]
    ok &= check(not bad, "the builder's wire model NEVER sets bit3 -- the identity guard is sound",
                f"the wire model sets bit3 at {bad[:4]}")
    bad2 = [(d, g, m, a) for d in (0, 1, 0xFFFF) for g in (0, 1) for m in (0, 1) for a in (0, 5)
            if (V76.wire_byte4(d, g, m, a) & EXPECT_PROBE_MASK) not in EXPECT_LEGAL_PAYLOADS]
    ok &= check(not bad2, "the builder's wire model only ever emits LEGAL payloads",
                f"the wire model emits illegal payloads at {bad2[:4]}")
    return ok


def verify_levers(img, base):
    print("\n" + "=" * 100)
    print("  THE TWO LEVERS -- by VALUE, and the gate instruction re-decoded BY FIELD")
    got = bytes(img[EXPECT_GATE_INSN_ADDR:EXPECT_GATE_INSN_ADDR + 4])
    check(got.hex() == EXPECT_GATE_INSN_NEW,
          f"0x{EXPECT_GATE_INSN_ADDR:05X} = {got.hex()} -- the repointed `ld.bu`",
          f"0x{EXPECT_GATE_INSN_ADDR:05X} is {got.hex()}, expected {EXPECT_GATE_INSN_NEW}")
    hw1, hw2 = struct.unpack("<HH", got)
    disp = (hw2 & 0xFFFE) | ((hw1 >> 5) & 1)
    signed = disp - 0x10000 if disp & 0x8000 else disp
    check(signed == -EXPECT_GATE_DISP_NEW,
          f"decoded by field: disp {signed:+#x} = -0x{EXPECT_GATE_DISP_NEW:04X} ⇒ THE GATE",
          f"the decoded displacement is {signed:+#x}, not -0x{EXPECT_GATE_DISP_NEW:04X}")
    check(((hw1 >> 5) & 0x3F) == 0x3C,
          "the opcode field is 0x3C (EVEN displacement) -- 0x3D would address the NEIGHBOURING cell",
          f"the opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, expected 0x3C")
    check((hw1 >> 11) == 15 and (hw1 & 0x1F) == 4, "the load is still `... [gp],r15`",
          f"the load targets r{hw1 >> 11} from r{hw1 & 0x1F}")
    moved = [i for i in range(EXPECT_GATE_INSN_ADDR, EXPECT_GATE_INSN_ADDR + 4)
             if img[i] != base[i]]
    check(moved == [EXPECT_GATE_ADDR],
          f"EXACTLY ONE byte moved in the instruction: 0x{EXPECT_GATE_ADDR:05X} "
          f"0x{EXPECT_GATE_BYTE_OLD:02X} -> 0x{EXPECT_GATE_BYTE_NEW:02X}",
          f"the repoint moved {[hex(x) for x in moved]}, expected one byte")
    a, old, new = EXPECT_ARM_B
    check(u16(img, a) == new and u16(base, a) == old,
          f"0x{a:05X} = {u16(img, a)} (V74 had {old}) -- r24's gate-active arm",
          f"0x{a:05X} is {u16(img, a)}, expected {new}")
    a2, v2 = EXPECT_ARM_A
    check(u16(img, a2) == v2 == u16(base, a2),
          f"0x{a2:05X} = {v2} on BOTH images -- V67/V68's value, asserted and never written",
          f"0x{a2:05X} is {u16(img, a2)}, expected {v2} UNCHANGED")
    r24 = EXPECT_ARM_B[2] / EXPECT_GAIN_B_CREEP
    r26 = EXPECT_ARM_A[1] / EXPECT_GAIN_A_CREEP
    print(f"  ⊕ DELIVERED, recomputed from the bytes just read: r24 x{r24:.5f} · r26 "
          f"/{1 / r26:.2f} EXACTLY · net = (5244 + 512a)/(3072 + 3072a), parity at a = "
          f"{EXPECT_PARITY_A}")
    print("     ⚠ This is a TWO-LANE lever. V76 reproduces V67/V68's CONFIGURATION; the corpus")
    print("       cannot separate which lane produced their result.")


def verify_keep_list(img, base, stock):
    print("\n" + "=" * 100)
    print("  THE KEEP-LIST -- every MUST-REMAIN site, by VALUE")
    for a, want in EXPECT_SAR.items():
        got = bytes(img[a:a + 2]).hex()
        check(got == want == bytes(stock[a:a + 2]).hex(),
              f"`sar` site 0x{a:05X} = {got} -- STOCK (V62's `a9` causes grind #2; the fix is an "
              "ABSENCE)", f"`sar` site 0x{a:05X} is {got}, expected the stock {want}")
    for a, want in sorted(EXPECT_LADDER_KEEP.items()):
        check(u16(img, a) == want, f"0x{a:05X} = {want}",
              f"0x{a:05X} is {u16(img, a)}, expected {want}")
    ta, tb, tu = EXPECT_THRESHOLD
    check(img[ta] == tb and u16(img, ta) == tu,
          f"0x{ta:05X}: BYTE = {tb} and u16 = {tu} -- both halves of the V63 trap asserted",
          f"0x{ta:05X} byte is {img[ta]} / u16 {u16(img, ta)}, expected {tb} / {tu}")
    for b_, want in EXPECT_GAIN_A.items():
        check(V74.rec4_y(img, b_) == want, f"gain_A 0x{b_:05X} Y = {want} (V72's r26 cut)",
              f"gain_A 0x{b_:05X} Y is {V74.rec4_y(img, b_)}, expected {want}")
    for b_ in EXPECT_GAIN_A_STOCK:
        check(bytes(img[b_:b_ + 0x14]) == bytes(stock[b_:b_ + 0x14]),
              f"gain_A 0x{b_:05X} is byte-STOCK (V72's cut is PARTIAL by design)",
              f"gain_A 0x{b_:05X} is not byte-stock")
    check(img[EXPECT_CARRIED[0]] == EXPECT_CARRIED[1],
          f"0x{EXPECT_CARRIED[0]:05X} = 0x{EXPECT_CARRIED[1]:02X} (carried inertly since V71)",
          f"0x{EXPECT_CARRIED[0]:05X} is 0x{img[EXPECT_CARRIED[0]]:02X}")
    check(u16(img, EXPECT_CLAMP[0]) == EXPECT_CLAMP[1],
          f"0x{EXPECT_CLAMP[0]:05X} = {EXPECT_CLAMP[1]} (V73's live clamp)",
          f"0x{EXPECT_CLAMP[0]:05X} is {u16(img, EXPECT_CLAMP[0])}")
    for lo, hi in EXPECT_LADDER_SPANS.items():
        check(bytes(img[lo:hi + 4]) == bytes(base[lo:hi + 4]),
              f"the selector span 0x{lo:05X}-0x{hi:05X} is byte-identical to V74 -- the lever is "
              "the GATE, not the ladders",
              f"the selector span 0x{lo:05X}-0x{hi:05X} MOVED")
    for a, (hx, cond, d_want) in EXPECT_LADDER_BRANCHES.items():
        got = bytes(img[a:a + 2])
        hw = struct.unpack("<H", got)[0]
        d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
        d -= 0x200 if d & 0x100 else 0
        check(got.hex() == hx and (hw & 0xF) == cond and d == d_want,
              f"the ladder branch @0x{a:05X} = {got.hex()} is `be +{d}` -- decoded from the Format "
              "III field split, not from the constant we expected",
              f"the ladder branch @0x{a:05X} is {got.hex()} (cond 0x{hw & 0xF:X}, disp {d:+d})")
    # ---- pointer arrays and the config table -------------------------------------------------------
    ok = all(u32(img, arr + m * 4) == u32(stock, arr + m * 4)
             for arr in EXPECT_DAMPER_PTRS for m in range(34))
    check(ok, "all six damper pointer arrays are byte-STOCK over all 34 modes",
          "a damper pointer array moved -- an edited table would be silently redirected")
    check(bytes(img[0xCD000:0xCD000 + 16 * 0x24]) == bytes(stock[0xCD000:0xCD000 + 16 * 0x24]),
          "the config table 0xCD000 is byte-STOCK", "the config table moved")
    # ---- 🛑 THE NEGATIVE: V75's levers must be ABSENT ------------------------------------------------
    n = 0
    bad = []
    for arr, name in zip(EXPECT_DAMPER_PTRS, ("FactorB", "FactorC", "FactorD", "FactorE",
                                              "ceiling", "friction")):
        for m in range(34):
            b_ = V74.factor_rec(img, arr, m)
            ln = V74.rec_len(img, b_)
            n += 1
            if bytes(img[b_:b_ + ln]) != bytes(base[b_:b_ + ln]):
                bad.append((name, m, hex(b_)))
    check(not bad and n == EXPECT_DAMPER_RECORDS,
          f"ALL {n} damper records (FactorB/C/D/E + ceiling + friction x 34 modes) are "
          "byte-identical to V74 ⇒ **V75's levers are provably ABSENT**",
          f"{len(bad)} damper record(s) moved: {bad[:5]} -- V76 must be single-variable vs V75")
    # ---- the inherited V74 guard, with V76's two edits relaxed on a copy ---------------------------
    try:
        V76.assert_must_not_change(bytearray(img), "verify_v76", stock, base)
        check(True, "V74's FULL inherited keep-list passes with the relaxation covering EXACTLY "
                    "0x3AA96, 0xC6446, 0xC6447", "")
    except AssertionError as e:
        check(False, "", f"the inherited V74 guard FAILED: {e}")


def verify_cave(img, base):
    print("\n" + "=" * 100)
    print("  THE CAVE -- bytes, re-disassembly, GATE 1, and the two-sided repoint proof")
    cave = bytes(img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    check(cave.hex() == EXPECT_CAVE_HEX, f"the {CAVE_EXTENT}-byte cave matches byte for byte",
          f"the cave is {cave.hex()}")
    check(cave[EXPECT_CAVE_CODE_LEN:] == b"\x00" * EXPECT_PAD,
          f"the final {EXPECT_PAD} bytes are zero pad (V74's own idiom: 46 B code + 22 B pad)",
          "the pad is not zero")
    redis = V76.redisassemble_cave(cave[:EXPECT_CAVE_CODE_LEN])
    asm = [m for _a, _r, m in redis]
    check(asm == EXPECT_CAVE_ASM,
          f"the re-disassembly (raw Python, NOT a Ghidra database) matches all {len(asm)} "
          "instructions",
          f"the re-disassembly differs:\n      got  {asm}\n      want {EXPECT_CAVE_ASM}")
    stores = [m for m in asm if m.startswith(("st.b", "st.h"))]
    check(len(stores) == 1 and stores[0] == "st.b r6,-5396[r4]",
          "GATE 1: EXACTLY ONE store, and it is the CAN-330 payload byte",
          f"the cave contains stores {stores}")
    check(sum(1 for m in asm if m.startswith(("jr", "jarl"))) == 0 and asm[-1] == "jmp [lp]",
          "the cave has a SINGLE exit", "the cave has more than one exit")
    check(sum(1 for m in asm if m.startswith("or ")) == 1 and "or r7,r6" in asm,
          "only the MERGE `or r7,r6` -- not the swapped twin `or r6,r7`",
          "the cave carries the swapped `or r6,r7`")
    # ---- the censuses, on BOTH images ---------------------------------------------------------------
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    for label, buf, want in (("V74 base", base, EXPECT_CENSUS_V74), ("V76", img, EXPECT_CENSUS_V76)):
        for disp, (wr, ww) in sorted(want.items()):
            r, w, c = V74.cell_census(buf, disp, span)
            check((len(r), len(w)) == (wr, ww),
                  f"{label}: gp-0x{disp:04X} has {wr} firmware reader(s) / {ww} writer(s)",
                  f"{label}: gp-0x{disp:04X} has {len(r)}r/{len(w)}w, expected {wr}r/{ww}w")
    for disp, why in EXPECT_PROBED.items():
        _r, _w, c = V74.cell_census(img, disp, span)
        check(len(c) == 1 and c[0][1].startswith("ld.") and c[0][2] == 6,
              f"the cave READS gp-0x{disp:04X} exactly once into r6, never writes it -- {why}",
              f"the cave's access to gp-0x{disp:04X} is {[(hex(a), m, r) for a, m, r in c]}")
    for disp, why in EXPECT_NOT_PROBED.items():
        _r, _w, c = V74.cell_census(img, disp, span)
        check(not c, f"the cave does NOT touch gp-0x{disp:04X} ({why}) -- so neither sibling's cave "
                     "can masquerade as this one",
              f"the cave touches gp-0x{disp:04X} ({why})")
    for disp in EXPECT_SHADOWS:
        _r, _w, c = V74.cell_census(img, disp, span)
        check(not c, f"the cave does not touch the lockstep shadow gp-0x{disp:04X}",
              f"the cave touches the lockstep shadow gp-0x{disp:04X}")
    # ---- ★★ THE TWO-SIDED PROOF ---------------------------------------------------------------------
    rb_dead, _w, _c = V74.cell_census(base, EXPECT_DEAD_DISP, span)
    ri_dead, _w2, _c2 = V74.cell_census(img, EXPECT_DEAD_DISP, span)
    rb_gate, _w3, _c3 = V74.cell_census(base, 0x6806, span)
    ri_gate, _w4, _c4 = V74.cell_census(img, 0x6806, span)
    check(len(rb_dead) == 1 and not ri_dead and
          [a for a, _m, _r in rb_dead] == [EXPECT_GATE_INSN_ADDR],
          f"★★ gp-0x{EXPECT_DEAD_DISP:04X} (the DEAD cell): 1 reader on V74, at exactly "
          f"0x{EXPECT_GATE_INSN_ADDR:05X} -> 0 on V76. ABANDONED.",
          f"the dead-cell census is {len(rb_dead)} -> {len(ri_dead)}, expected 1 -> 0")
    new = sorted(set(a for a, _m, _r in ri_gate) - set(a for a, _m, _r in rb_gate))
    check(len(ri_gate) == len(rb_gate) + 1 == 14 and new == [EXPECT_GATE_INSN_ADDR],
          f"★★ gp-0x6806 (THE GATE): {len(rb_gate)} readers -> {len(ri_gate)}, and the NEW one is at "
          f"exactly 0x{EXPECT_GATE_INSN_ADDR:05X}. A one-byte edit that missed cannot do that.",
          f"the gate census is {len(rb_gate)} -> {len(ri_gate)}, new readers {[hex(a) for a in new]}")
    # ---- the hook -----------------------------------------------------------------------------------
    check(bytes(img[EXPECT_HOOK_ADDR:EXPECT_HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE,
                                                                         EXPECT_HOOK_ADDR),
          f"the hook @0x{EXPECT_HOOK_ADDR:05X} is `jarl 0x{CAVE_BASE:05X}`", "the hook is wrong")
    check(bytes(img[EXPECT_HOOK_ADDR + 4:EXPECT_HOOK_ADDR + 6]).hex() == EXPECT_HOOK_RETURN_INSN,
          f"0x{EXPECT_HOOK_ADDR + 4:05X} is `mov 0x8,r7` ⇒ r7 is PROVABLY DEAD across the hook",
          "the return site is not `mov 0x8,r7` -- the r7-dead proof is void")
    print(f"  ⊕ bit3 = 0x{EXPECT_BIT_UNUSED:02X} is emitted by NO instruction in the listing above ⇒ "
          "STRUCTURALLY ZERO on every")
    print("     V76 frame. V74's on-car payload (0x28/0xA8) has bit3 SET on every frame, so ONE")
    print("     frame rejects a V74 log. That is the build-identity guard.")


def verify_crc_and_diff(img, base, stock):
    print("\n" + "=" * 100)
    print("  CRC AND THE FULL BYTE ATTRIBUTION")
    check(walk_all_blocks(img) == 0, "the full CRC chain verifies: 50/50 blocks PASS",
          "the CRC chain FAILED")
    touched = [CAVE_BASE, EXPECT_GATE_ADDR, EXPECT_ARM_B[0]]
    blocks = sorted({tuple(V53.owning_block(img, a)) for a in touched})
    check([b[1] for b in blocks] == EXPECT_TRAILERS,
          f"exactly {len(EXPECT_TRAILERS)} CRC blocks own the edits: "
          f"{[hex(t) for t in EXPECT_TRAILERS]}",
          f"the owning blocks are {[hex(b[1]) for b in blocks]}")
    crc_only = {b[1] + k for b in blocks for k in range(4)}
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)

    def attribute(d):
        return ("cave" if d in cave_span else "gate" if d == EXPECT_GATE_ADDR else
                "arm" if d in (EXPECT_ARM_B[0], EXPECT_ARM_B[0] + 1) else None)

    diff = [i for i in range(START, END) if img[i] != base[i]]
    func = [d for d in diff if d not in crc_only]
    stray = [d for d in func if attribute(d) is None]
    check(not stray, f"every one of the {len(func)} functional bytes vs V74 is attributable",
          f"UNATTRIBUTED bytes vs V74: {[hex(x) for x in stray[:12]]}")
    counts = {}
    for d in func:
        counts[attribute(d)] = counts.get(attribute(d), 0) + 1
    check(counts == EXPECT_DIFF_BY_LEVER and len(func) == EXPECT_FUNCTIONAL_BYTES,
          f"the diff splits exactly as specified: {EXPECT_DIFF_BY_LEVER} "
          f"({EXPECT_FUNCTIONAL_BYTES} functional + {len(diff) - len(func)} CRC)",
          f"the diff is {counts} / {len(func)} functional, expected {EXPECT_DIFF_BY_LEVER} / "
          f"{EXPECT_FUNCTIONAL_BYTES}")
    all_edit = set(cave_span) | {EXPECT_GATE_ADDR, EXPECT_ARM_B[0], EXPECT_ARM_B[0] + 1}
    check(not [a for a in all_edit if CRC_SKIPPED[0] <= a < CRC_SKIPPED[1]],
          f"NOTHING of the {len(all_edit)} edited bytes lands in "
          f"[0x{CRC_SKIPPED[0]:X},0x{CRC_SKIPPED[1]:X}) -- the CRC-skipped block, V40 precedent",
          "an edit landed in the CRC-skipped block")
    inherited = {i for i in range(START, END) if base[i] != stock[i]}
    ds = [i for i in range(START, END) if img[i] != stock[i]]
    fs = [d for d in ds if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None and d not in inherited]
    check(not stray_s, f"vs STOCK: {len(fs)} functional bytes, all attributable to V76's levers or "
                       "the carried V38->V74 lineage",
          f"UNATTRIBUTED bytes vs STOCK: {[hex(x) for x in stray_s[:12]]}")


def verify_v67_identity(img):
    """★★ The rate lane must be byte-identical to V67 -- that is V76's whole claim."""
    print("\n" + "=" * 100)
    print("  THE RATE LANE vs V67 -- the configuration V76 reproduces")
    try:
        v67 = Path(plain_image_path("_v67_plain_image.bin")).read_bytes()
    except OSError as e:
        check(False, "", f"cannot read the V67 reference image: {e}")
        return
    addrs = sorted({EXPECT_GATE_ADDR, EXPECT_ARM_B[0], EXPECT_ARM_B[0] + 1,
                    EXPECT_ARM_A[0], EXPECT_ARM_A[0] + 1, EXPECT_THRESHOLD[0],
                    *(a + k for a in EXPECT_LADDER_KEEP for k in (0, 1)),
                    *range(EXPECT_GATE_INSN_ADDR, EXPECT_GATE_INSN_ADDR + 4),
                    *range(0x3AB56, 0x3AB70), *range(0x3ABF8, 0x3AC18),
                    *(a + k for a in EXPECT_SAR for k in (0, 1))})
    bad = [a for a in addrs if img[a] != v67[a]]
    check(not bad, f"all {len(addrs)} rate-lane bytes (the gate instruction, both selector spans, "
                   "all five arms, the threshold cal and both `sar` sites) are byte-identical to V67",
          f"the rate lane differs from V67 at {[hex(x) for x in bad[:12]]}")
    # and the DAMPER lane must DIFFER from V67 -- V76 carries V74's, which V67 never had
    dfr = V74.factor_rec(img, 0xC9E9C, 26)
    check(bytes(img[dfr:dfr + V74.rec_len(img, dfr)]) != bytes(v67[dfr:dfr + V74.rec_len(v67, dfr)]),
          "the live mode's FactorC DIFFERS from V67 ⇒ V74's damper lever set is carried, as intended",
          "the live FactorC equals V67's -- V74's damper lever is MISSING")


def verify(img, base, stock, label):
    print("\n" + "=" * 100)
    print(f"  IMAGE: {label}")
    sha = hashlib.sha256(img).hexdigest()
    print(f"  SHA256 {sha}")
    check(len(img) == 0x100000, "the image is 1 MiB", f"the image is {len(img)} bytes")
    check(hashlib.sha256(base).hexdigest() == EXPECT_BASE_SHA,
          "the V74 base reference matches the recorded SHA256", "the V74 base reference is wrong")
    if sha != EXPECT_IMAGE_SHA:
        print(f"  ⚠ SHA256 is not the recorded {EXPECT_IMAGE_SHA} -- every check below still runs, "
              "and they are the ones that decide.")
    else:
        print("  ✅ SHA256 matches the recorded V76 image exactly.")
    verify_levers(img, base)
    verify_keep_list(img, base, stock)
    verify_cave(img, base)
    verify_v67_identity(img)
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
        raw = Path(args.rwd).read_bytes()
        FF.assert_x31_checksum(raw, "the .rwd under test")
        info = parse_x31(raw)
        decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        img = bytearray(base)
        img[START:END] = bytes(info["encs"][0]).translate(decode)
        print(f"\n  .rwd SHA256 {hashlib.sha256(raw).hexdigest()}")
        if hashlib.sha256(raw).hexdigest() != EXPECT_RWD_SHA:
            print(f"  ⚠ not the recorded {EXPECT_RWD_SHA}")
        if EXPECT_RWD_NAME not in str(args.rwd):
            print(f"  ⚠ the filename is not {EXPECT_RWD_NAME} -- the filename is the ONLY pre-drive "
                  "discriminator between cuts")
        verify(bytes(img), base, stock, f"{args.rwd} (decoded payload)")
    else:
        p = Path(args.image) if args.image else Path(plain_image_path(EXPECT_IMAGE_NAME))
        verify(p.read_bytes(), base, stock, str(p))

    print("\n" + "=" * 100)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"     · {f}")
        return 1
    print("  ✅ ALL CHECKS PASSED -- this image IS V76.")
    print("  🛑 THAT IS NOT CLEARANCE TO FLY. V76 is a SIBLING candidate to V75, both off the same")
    print("     V74 base; the operator chooses one. Verification says the artefact is what it")
    print("     claims to be, nothing more.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
