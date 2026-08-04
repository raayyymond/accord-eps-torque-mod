#!/usr/bin/env python3
"""build_v71_tva.py -- V71 = V70 MINUS the falsified surface dose, PLUS both confirmed fixes back.

    V71  ==  V62/V65's RATE LANE, byte for byte,  +  V42's `0x454FE` ratchet byte,  +  a new cave.

That identity is not aimed at -- it is ASSERTED against `_v62_plain_image.bin` AND
`_v65_plain_image.bin`, over the whole image, and it is the build's central safety claim: the lane
configuration V71 ships has already flown TWICE, flight-clean.

WHY THIS BUILD EXISTS -- the one-paragraph rationale
-----------------------------------------------------
The car is missing **both** of its confirmed fixes. `0x454FE` (V42's state-4 governor ratchet kill,
"CONFIRMED ROOT CAUSE, carry forward") is byte-stock in every build **V53 -> V70** -- lost at the
V38/FOURFRAME rebase. `0x3AB76` + `0x3AC20` (V62's `sar 0xa` -> `0x9`, the kit's only measured
grind-#1 fix: 8x at creep, 42x at |rate| 16-32 deg/s) is carried by **V62 and V65 only** -- removed
as V66's confirmatory control and never restored. Every build since has re-created V62's effect in a
DIFFERENT encoding that doses **r24 only**, and grind #1 came back. **r26 is now proven live on-car**
(V70's probe: 1,644/18,010 frames with `gp-0x6adc` strictly negative; a pinned-zero cell cannot clear
a `>= 0` test), and V62's `sar` route is the **only** encoding that is dose-exact independent of
r26's share. V71 restores both confirmed fixes and drops the falsified surface dose.

🛑🛑 THE STATED COST, PUT FIRST BECAUSE IT IS THE ONE THING THIS BUILD TRADES AWAY
----------------------------------------------------------------------------------
V71's rate-lane dose is a **FLAT 2.000000x at every speed and every rate**, because a `sar` immediate
is speed-independent. That is exactly V62/V65's configuration -- and the record says that flat 2.00x
is what **CAUSED grind #2 (11.71x)**. V69/V70 chose a SPEED-SHAPED surface dose precisely to avoid
it: V70 delivers 2.000000x at creep tapering to **EXACTLY 1.000000x at and above 50 km/h**, which is
the configuration the operator reported clean at highway. **V71 gives up that taper.** The trade is
deliberate and was specified: the surface encoding doses r24 only, and r26 is now proven live, so the
surface route cannot deliver a known dose to the lane as a whole. Score grind #2 at speed
SEPARATELY on this drive, and treat a highway regression as expected-and-informative rather than as a
surprise. The lever to walk it back is the pair of `sar` immediates -- one byte each, fully
reversible by reflashing V70.

THE FOUR EDITS, off `_v70_plain_image.bin`
-------------------------------------------
  1. CODE, 1 byte.  `0x454FE`  0xBA -> 0xB5   `bne 0x455C4` -> `br 0x455C4`. V850 Bcond cond nibble
     0xA -> 0x5; the displacement field is untouched so the TARGET is provably unchanged. Kills the
     state-4 governor substitution -- the kit's one CONFIRMED root cause (V42, on-car).
     ⭐ ASSERTED, not re-derived: V70's `[0x453E0,0x455E0)` is byte-identical to STOCK (0 differing
     bytes) and V42 differs from stock there by EXACTLY this one byte.
  2. CODE, 2 bytes. `0x3AB76` 0xAA -> 0xA9 and `0x3AC20` 0xAA -> 0xA9 -- both `sar 0xa,rN` ->
     `sar 0x9,rN`. `0x3AB76` is **r26's** second Q10 shift, `0x3AC20` is **r24's**. BOTH are edited,
     which is what makes the 2.000000x exact independent of r26's share `a`.
     🛑 `0x3AB70` (r26's FIRST shift) is deliberately LEFT at `sar 0xa` -- editing it instead pushes a
     `mul` operand to 94% of INT32_MAX and V850 `mul` discards the high word into r0 silently.
  3. CAL, 8 bytes.  `0xD2A7E`/`0xD2A80` -> 3072 and `0xD2ABA`/`0xD2ABC` -> 2561 -- mode-10 `gain_B`
     rec0/rec1 back to STOCK. The surface dose is FALSIFIED: the V69 4x / V70 2x dose-response is
     non-monotone and the 4x brought grind #1 back, and the encoding doses r24 only.
  4. CAVE, 68 bytes at `0xC4B34` -- the probe. See PART B.

PART B -- THE PROBE: WHICH GAIN IS ACTUALLY IN FORCE
-----------------------------------------------------
🛑 V70's positive control `gp-0x6ada >= +512` read **0 / 18,010** against a replay predicting **311**
from the route's own data (**52 even under stock**). This is the FOURTH probe in a row to return an
uninterpretable zero by reading a lane OUTPUT. V71 reads the SELECTORS.

The priority chain, orchestrator-verified in Ghidra on the stock image (addresses annotated):

    0x3AB98  ld.bu -0x671d[gp],r6        the MASK cell
    0x3ABA8  setfne r6                   r6 = (gp-0x671d != 0)
    0x3ABFA  cmp   r0,r6 / be 0x3AC04
    0x3ABFE  ld.hu 0x7442[tp],r10        -> cal 0xC6442 = 1024    *** OUTRANKS EVERYTHING ***
    0x3AC04  cmp   r0,lp / be 0x3AC0E
    0x3AC08  ld.hu 0x7446[tp],r10        -> cal 0xC6446 = 512     DEAD on V71 (gate 0x3AA96 = 0xC5,
                                                                  gp-0x683c has ZERO writers)
    0x3AC0E  cmp   r0,r2 / be 0x3AC16
    0x3AC12  ld.hu 0x7440[tp],r10        -> cal 0xC6440 = 2048    r2 = (gp-0x671a >= cal 0xC64FA),
                                                                  set at 0x3AA7C-0x3AA7E, UNSIGNED
    0x3AC16  mov   r1,r8                 else: r10 is the mode-10 LERP from 0x3ABF8
    0x3AC18  mul   r10,r8,r0
    0x3AC20  sar   0xa,r8   -> 0x9       *** V71's EDIT 2 ***

  bit7 = 1                     LIVENESS.  field == 0 => the cave did not fire => the frame is VOID.
  bit6 = gp-0x671d != 0        *** THE MASK. *** Non-vacuous both ways; if it fires, r24's gain is
                               pinned to 1024, BELOW the stock LERP, and the LERP arm never runs.
  bit5 = gp-0x67fa == 4        *** THE RATCHET STATE. *** This build DISABLES the state-4
                               substitution, so the rung measures how often it WOULD have fired --
                               the fix and its own test on one drive. `gp-0x67fa`'s runtime value has
                               never been read for state 4 in this kit (V70 tested `== 10`, read 0,
                               leaving the state in {4,5,11}).
  bit4 = gp-0x6ada >= +512     the positive control, r24's post-clip lane mirror (0 readers / 1
                               writer image-wide).
  bit3 = gp-0x671a >= 5        the third arm, hardcoded against cal 0xC64FA (a BYTE = 5, asserted).

★ ALL FIVE RUNGS FIT IN 68 BYTES -- the budget did NOT bind, and no rung was dropped. The trick is
that r7 accumulates a FIVE-BIT value with weights {0x10, 0x8, 0x4, 0x2, 0x1} and a single
`shl 0x3,r7` moves it into bits 7:3 at the end. Every setter is then a TWO-byte `add imm5,r7`
instead of a four-byte `movea`, which buys 6 bytes and costs 2. 🛑 This introduces NO new instruction
form: `shl 0x3,r7` = `c33a` is V31P's own byte sequence, FLASHED FOUR TIMES and confirmed on the wire,
and re-flown in V54's and V55's caves; `add imm5,r7` flew on V70 (`add 0x8,r7`). It is also Honda's
own idiom at 0x4FB82 -- `shl 0x3,r7` immediately followed by `andi 0xf8,r7,r7`, i.e. literally
"build a 5-bit field, shift it into bits 7:3".

⚠ HOW STRONG bit4 REALLY IS -- stated precisely, because the loose version is wrong.
On the three ARM branches bit4 IS strictly stronger than V70's: a `sar` edit doubles r24 whichever
arm wins, whereas V70's surface edit applied ONLY on the LERP branch. On the LERP branch it is
stronger AWAY from 0 km/h and exactly EQUAL at the breakpoints V70's surface edit doubled. The rung
fires at |dtorque| >= 512 x 2^sar / gain; from the images (the sweep below re-derives it):

    operating point                     V70 thr   V71 thr
    creep 0 km/h, rateKey 0                85.3      85.3   <- IDENTICAL (V70's dose was exactly 2x)
    grind #1 op pt 7.2 km/h, rk 603       108.9     100.0
    grind #2 creep 7.2 km/h, rk 1206      172.0     110.3
    engaged highway 93 km/h, rk 300       241.3     120.6

⇒ bit4 is nowhere LESS sensitive than V70's rung, and up to 2x more sensitive off the breakpoints.
Therefore:
    bit6 = 0 AND bit3 = 0 AND bit4 = 0   =>  the LERP arm WAS selected and the lane output really is
                                             below +512, at a threshold no higher than the one that
                                             already read 0/18,010. The arm-selection explanation for
                                             V70's null is REFUTED and the problem is upstream
                                             (dtorque itself, or the mirror's writer @0x3AD5A not
                                             being reached).
    bit6 = 1 or bit3 = 1                 =>  an arm was selected; V70's surface edit was masked; the
                                             null is explained and the lever moves to that arm's cal.
Either outcome is actionable. That is the property V64/V68/V69/V70 lacked.

GATES
-----
GATE 1 (RAM ownership): the code edits claim no RAM at all. The cave is READ-ONLY apart from ONE
    store, `st.b r6,-0x1514[gp]` -- the existing CAN-330 payload byte, with bits 2:0 (live
    STEER_SENSOR_STATUS) preserved by `andi 0x7`. Identical ownership to V67/V68/V69/V70, all flown.
    Asserted as a property of the EMITTED CODE (exactly one store, and it is the payload byte), and
    the probed cells' reader/writer sets are re-derived from raw bytes by a two-decoder scan.
GATE 2 (closed-loop stability): the rate lane is asserted BYTE-IDENTICAL to V62 and to V65, both of
    which flew flight-clean. No filter, no pole, no delay, no phase change anywhere -- the two edited
    halfwords move a shift IMMEDIATE only (opcode and reg2 fields asserted unchanged). The gain
    change is a pure magnitude change on a DERIVATIVE lane, i.e. DC-neutral. The equivalence
    assertion IS the evidence; there is no argument to check.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent **68 of the proven 68 B** -- unchanged, flown 9x
(V55/V57/V58/V59/V64/V65/V66/V67/V70, all clean). 🛑 ZERO spare. Growing a cave is this kit's ONLY
bricking class (V24, V27 and V48B all bricked the ECU).

Usage:  python build_v71_tva.py
"""
import hashlib
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl encoders)
import build_v55_tva as V55                # noqa: E402  (ldh / sar / cmp_imm5 / ldbu_any encoders)
import build_v57_tva as V57                # noqa: E402
import build_v62_tva as V62                # noqa: E402  (the sar edit -- the lever being restored)
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the two-decoder scan)
import build_v65_tva as V65                # noqa: E402  (COND_BLT)
import build_v67_tva as V67                # noqa: E402  (671d / 671a pins, gate + arm addresses)
import build_v68_tva as V68                # noqa: E402  (cave machinery, D2000 block, sar sites)
import build_v69_tva as V69                # noqa: E402  (gain model, surface records, neighbours)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = V68.START, V68.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = len(V55.CAVE_BYTES)          # 68 -- the PROVEN extent. Never grow it.
D2000_BLOCK = V68.D2000_BLOCK

# =====================================================================================================
# PART A -- THE THREE RESTORATIONS
# =====================================================================================================

# ---- EDIT 1: V42's state-4 governor ratchet kill -----------------------------------------------
RATCHET_ADDR = V42_EDIT_ADDR = 0x454FE
RATCHET_STOCK_HW, RATCHET_NEW_HW = 0x65BA, 0x65B5          # bne +198 -> br +198, target 0x455C4
COND_BNE_BR = (0xA, 0x5)
SUBST_BLOCK = (0x45500, 0x455C4)           # the block the edit makes unreachable
RATCHET_CTX = ((0x454F4, bytes.fromhex("24373295")),       # ld.h  -0x6ace[gp],r6
               (0x454F8, bytes.fromhex("84670798")),       # ld.bu -0x67fa[gp],r12
               (0x454FC, bytes.fromhex("6462")))           # cmp   0x4,r12
# ⭐ The whole enclosing region is byte-identical to stock on V70, and V42 differs from stock there by
# EXACTLY this one byte. Both facts are ASSERTED below rather than re-derived.
RATCHET_REGION = (0x453E0, 0x455E0)

# ---- EDIT 2: V62's two `sar` immediates --------------------------------------------------------
R26_SAR, R24_SAR = V62.R26_SAR, V62.R24_SAR                # 0x3AB76 / 0x3AC20
SAR_STOCK_HW, SAR_NEW_HW = V62.SAR_STOCK_HW, V62.SAR_NEW_HW
R26_SAR_FIRST, R26_SAR_FIRST_HW = V62.R26_SAR_FIRST, V62.R26_SAR_FIRST_HW   # 0x3AB70 -- LEFT STOCK

# ---- EDIT 3: the falsified surface dose, reverted to stock -------------------------------------
REC0, REC1 = V69.REC0, V69.REC1            # 0xD2A74 / 0xD2AB0 -- mode-10 gain_B 0 and 10 km/h
STOCK_Y = {REC0 + 0x0A: 3072, REC0 + 0x0C: 3072, REC1 + 0x0A: 2561, REC1 + 0x0C: 2561}
V70_SCALE = 2                              # the dose being REMOVED
SURFACE = tuple((a, STOCK_Y[a] * V70_SCALE, STOCK_Y[a], nm) for a, nm in (
    (REC0 + 0x0A, "rec0 (0 km/h)  Y[0]"), (REC0 + 0x0C, "rec0 (0 km/h)  Y[1]"),
    (REC1 + 0x0A, "rec1 (10 km/h) Y[0]"), (REC1 + 0x0C, "rec1 (10 km/h) Y[1]")))
REC_Y_STOCK = {REC0: [3072, 3072, 2322, 1536], REC1: [2561, 2561, 2247, 1947],
               0xD2AEC: [2305, 2304, 2149, 1948], 0xD2B28: [2151, 2151, 2049, 1947]}
NEIGHBOURS = V69.NEIGHBOURS                # mode 11/12 -- BYTE-IDENTICAL to mode 10's stock rec0
UNTOUCHED_RECS = V69.UNTOUCHED_RECS        # 0xD2AEC / 0xD2B28

# ---- the control path, UNCHANGED from V70 (and therefore from V69) -----------------------------
REPOINT_ADDR, REPOINT_BYTE = V67.REPOINT_ADDR, V67.REPOINT_BYTE     # 0x3AA94 / 0x3AA96
GATE_DEAD, GATE_LIVE = 0xC5, 0xFB          # gp-0x683c (DEAD, 0 writers) vs gp-0x6806 (LKAS-active)
ARM_ADDR, ARM_STOCK, ARM_GATED = V67.ARM_ADDR, 512, 5244            # 0xC6446

# 🛑 THE RATE LANE, DEFINED AS A SET OF SPANS. V71's central safety claim is that all of it is
# byte-identical to V62 AND V65. Enumerated so the claim is machine-checked, not asserted in prose.
RATE_LANE_SPANS = (
    (0x3A300, 0x3AE00, "FUN_0003a382 + FUN_0003aa2c -- both inline rate lanes and the aggregator"),
    (0xC6000, 0xC7000, "the calibration block: every gain arm, deadzone, CEIL and gain_A record"),
    (0xD2000, 0xD2FFC, "the 0xD2000 block: mode-10 gain_B surface + V60's falsified blend cells"),
)

# =====================================================================================================
# PART B -- THE PROBE.  0x14A byte4 bits 7:3.  68 of the proven 68 bytes; ZERO spare.
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP        # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK          # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT

# 🛑 r7 accumulates a FIVE-BIT value; `shl 0x3,r7` moves it into bits 7:3 at the very end. The
# WEIGHTS below are pre-shift; the PAYLOAD bits are weight << 3.
W_LIVE = 0x10              # -> bit7  LIVENESS (a constant, folded into the initial movea)
W_MASK671D = 0x08          # -> bit6  gp-0x671d != 0     THE MASK -- outranks every arm
W_STATE4 = 0x04            # -> bit5  gp-0x67fa == 4     THE RATCHET STATE this build disables
W_R24HALF = 0x02           # -> bit4  gp-0x6ada >= +512  the positive control
W_ARM3671A = 0x01          # -> bit3  gp-0x671a >= 5     the third arm
PAYLOAD_SHIFT = 3
BIT_LIVE, BIT_MASK671D = W_LIVE << PAYLOAD_SHIFT, W_MASK671D << PAYLOAD_SHIFT
BIT_STATE4, BIT_R24HALF = W_STATE4 << PAYLOAD_SHIFT, W_R24HALF << PAYLOAD_SHIFT
BIT_ARM3671A = W_ARM3671A << PAYLOAD_SHIFT

MASK_DISP = V67.MASK_DISP                  # 0x671D -- odd displacement => ld.bu opcode field 0x3D
STATE_DISP = 0x67FA                        # the ECU state byte
R24_MIRROR_DISP = 0x6ADA                   # r24's post-clip lane mirror: 0 readers / 1 writer
ARM3_DISP = V67.ARM3_DISP                  # 0x671A
CEIL_CAL, CEIL_VALUE = V67.CEIL_CAL, V67.CEIL_VALUE        # 0xC64FA, a BYTE = 5
STATE_VALUE = 4                            # the ratchet state
SHIFT, LEVEL = 9, 1
THRESHOLD = LEVEL << SHIFT                 # = +512
STATE_MIN_READERS = 100                    # measured 128 loads; assert a floor, not equality

COND_BLT = V65.COND_BLT                    # 0x6  SIGNED <     🛑 bl (0x1) is the UNSIGNED twin
COND_BL = V55.COND_BL                      # 0x1  UNSIGNED <   -- matches the firmware's own `bc`
COND_BNE = 0xA                             # 0xA  !=           🛑 be (0x2) is its twin and inverts

PROBE_CENSUS = {
    # disp: (firmware readers, firmware writers, writer addresses, allowed mnemonics)
    R24_MIRROR_DISP: (0, 1, [0x3AD5A], {"st.h"}),      # pure mirror of r24: NOTHING reads it
    MASK_DISP: (14, 2, [0x3BD2A, 0x41EC6], {"ld.bu", "st.b"}),
    ARM3_DISP: (7, 1, [0x42A12], {"ld.bu", "st.b"}),
}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance, or a flown ancestor. ---
PIN_LDH_6AD4 = (0x3ACA8, bytes.fromhex("24372c95"))   # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_6B94 = (0x453E0, bytes.fromhex("24376c94"))   # hw1 donor #2 (V65's), different cell
PIN_STH_6ADA = (0x3AD5A, bytes.fromhex("64c72695"))   # 🛑 opcode 0x3B -- ONE BIT from our 0x39
PIN_LDBU_671D = (0x3AB98, bytes.fromhex("a437e398"))  # BYTE-IDENTICAL to what we emit (4 instances)
PIN_LDBU_67FA = (0x18C7C, bytes.fromhex("84370798"))  # BYTE-IDENTICAL to what we emit
PIN_LDBU_671A_R12 = (0x3AA70, bytes.fromhex("8467e798"))   # hw2 donor for the WEAK-pinned 671a load
PIN_LDBU_EVEN_R6 = (0x2A508, None)                    # hw1 donor: a real even-disp `ld.bu ...,gp,r6`
PIN_SAR9_R6 = (0x3E60C, bytes.fromhex("a932"))        # `sar 0x9,r6`
PIN_CMP_1_R6 = (0x14D46, bytes.fromhex("6132"))       # `cmp 0x1,r6`
PIN_CMP_4_R6 = (0x16F90, bytes.fromhex("6432"))       # `cmp 0x4,r6`   -- Ghidra-confirmed
PIN_CMP_5_R6 = (0x16FA4, bytes.fromhex("6532"))       # `cmp 0x5,r6`   -- Ghidra-confirmed
PIN_MOVEA_10_R7 = (0x49256, bytes.fromhex("203e1000"))     # `movea 0x10,r0,r7` -- Ghidra-confirmed
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))        # `shl 0x3,r7` -- and V31P FLASHED this 4x
# ★ 0x4FB82 is Honda's OWN version of this cave's idiom: `shl 0x3,r7` immediately followed by
# `andi 0xf8,r7,r7` -- build a 5-bit field, shift it into bits 7:3, mask. Confirmed in Ghidra.
PIN_ADD_R7 = {1: (0x15404, bytes.fromhex("413a")),    # all four Ghidra-confirmed as real instructions
              2: (0x27EF0, bytes.fromhex("423a")),
              4: (0x2688E, bytes.fromhex("443a")),
              8: (0x17CD8, bytes.fromhex("483a"))}    # flown in V70's cave
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))           # `blt +4`, skipping a 2-byte instruction
PIN_BL4 = (0x14F3A, bytes.fromhex("a105"))            # `bl/bc +4`, skipping a 2-byte `mov r0,r14`
PIN_BNE4 = (0x1A8A6, bytes.fromhex("aa05"))           # `bne +4`, skipping a 2-byte `mov 0x1,r26`
PIN_BNE6 = (0x14CB2, bytes.fromhex("ba05"))           # `bne +6` -- the cond-field cross-check

TAG = ("LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-ratchet-V62sar-BOTHLANES-"
       "surfaceREVERTED-gaininforce-probe-671d-67fa4-6ada-671a-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V71-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v71_plain_image.bin"))
SRC_BIN = plain_image_path("_v70_plain_image.bin")
V62_BIN = plain_image_path("_v62_plain_image.bin")
V65_BIN = plain_image_path("_v65_plain_image.bin")
V42_BIN = plain_image_path("_v42_plain_image.bin")
STOCK_BIN = stock_fw_path("code.bin")
DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v71_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def _s16(x):
    """Interpret a 16-bit pattern the way `ld.h` does -- SIGNED."""
    return x - 0x10000 if x & 0x8000 else x


def add_imm5(imm, reg2):
    """V850 Format II `add imm5,reg2` -- opcode 0b010010. Pinned to four real instances below."""
    assert 0 <= imm <= 15, "Format II imm5 is SIGNED (-16..15)"
    assert 0 <= reg2 <= 31
    return struct.pack("<H", (reg2 << 11) | (0x12 << 5) | (imm & 0x1F))


def decode_bcond(buf, address):
    """Decode a V850 Bcond halfword -> (cond, absolute_target). None if not a Bcond."""
    hw = struct.unpack_from("<H", buf, address)[0]
    if (hw >> 7) & 0xF != 0xB:
        return None
    disp = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return hw & 0xF, address + disp


def decode_fmt2(hw):
    """V850 Format-II field split: imm5 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"imm5": hw & 0x1F, "opcode": (hw >> 5) & 0x3F, "reg2": (hw >> 11) & 0x1F}


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v671d, v67fa, v6ada, v671a, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the decompiled arithmetic, not a paraphrase."""
    r7 = W_LIVE                                     # movea 0x10,r0,r7
    r6 = v671d & 0xFF                               # ld.bu (ZERO-extends a byte)
    if not (r6 < 1):                                # cmp 0x1,r6 ; blt +4
        r7 += W_MASK671D
    r6 = v67fa & 0xFF                               # ld.bu
    if not (r6 != STATE_VALUE):                     # cmp 0x4,r6 ; bne +4
        r7 += W_STATE4
    r6 = _s16(v6ada) >> SHIFT                       # ld.h ; sar 0x9  (Python >> floors == `sar`)
    if not (r6 < LEVEL):                            # cmp 0x1,r6 ; blt +4
        r7 += W_R24HALF
    r6 = v671a & 0xFF                               # ld.bu
    if not (r6 < CEIL_VALUE):                       # cmp 0x5,r6 ; bl +4   (UNSIGNED, as 0x3AA7E)
        r7 += W_ARM3671A
    r7 <<= PAYLOAD_SHIFT                            # shl 0x3,r7
    return (r7 & 0xFF) | (status_bits & PAYLOAD_KEEP_MASK)


LEGAL_PAYLOADS = {BIT_LIVE | a | b | c | d
                  for a in (0, BIT_MASK671D) for b in (0, BIT_STATE4)
                  for c in (0, BIT_R24HALF) for d in (0, BIT_ARM3671A)}


def _wire_model():
    """The rungs' semantics, exhaustively: every halfword pattern and every byte value."""
    # ---- bit4: the only SIGNED rung. Over ALL 65,536 halfword patterns. --------------------------
    for raw in range(0x10000):
        x = _s16(raw)
        assert bool(wire_byte4(0, 0, raw, 0) & BIT_R24HALF) == (x >= THRESHOLD), \
            f"bit4 is not `>= {THRESHOLD}` at x = {x}"
    # ---- the three BYTE rungs. Over ALL 256 values each. -----------------------------------------
    for v in range(0x100):
        assert bool(wire_byte4(v, 0, 0, 0) & BIT_MASK671D) == (v != 0), f"bit6 is not `!= 0` at {v}"
        assert bool(wire_byte4(0, v, 0, 0) & BIT_STATE4) == (v == STATE_VALUE), \
            f"bit5 is not `== {STATE_VALUE}` at {v}"
        assert bool(wire_byte4(0, 0, 0, v) & BIT_ARM3671A) == (v >= CEIL_VALUE), \
            f"bit3 is not `>= {CEIL_VALUE}` at {v}"
    # ---- 🛑 THE SHIFT MUST NEVER REACH THE PRESERVED STATUS BITS. If `shl` were mis-encoded or the
    # weights overflowed, `or r7,r6` would OVERWRITE live STEER_SENSOR_STATUS bits 2:0 on the wire.
    # That is the one failure mode of the 5-bit-accumulator scheme, so it is proven, not argued.
    reachable_r7 = {W_LIVE + a + b + c + d for a in (0, W_MASK671D) for b in (0, W_STATE4)
                    for c in (0, W_R24HALF) for d in (0, W_ARM3671A)}
    assert max(reachable_r7) == 0x1F and min(reachable_r7) == W_LIVE
    for r7 in reachable_r7:
        assert (r7 << PAYLOAD_SHIFT) <= 0xF8, f"r7 = 0x{r7:02X} shifts past the byte"
        assert (r7 << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
            f"r7 = 0x{r7:02X} shifts INTO the preserved status bits -- the wire would be corrupted"
    for status in range(8):
        for inputs in ((0, 0, 0, 0), (0xFF, STATE_VALUE, 0x7FFF, 0xFF), (1, 4, 0x0200, 5)):
            assert wire_byte4(*inputs, status_bits=status) & PAYLOAD_KEEP_MASK == status, \
                "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
    # 🛑 `blt` is (S xor OV), not a mathematical `<`, so the model is exact only if the compares
    # cannot overflow. Asserted rather than reasoned about.
    shifted = {_s16(raw) >> SHIFT for raw in range(0x10000)}
    assert min(shifted) == -(1 << (15 - SHIFT)) and max(shifted) == (1 << (15 - SHIFT)) - 1, \
        f"the shifted range is {min(shifted)}..{max(shifted)} -- re-derive the overflow argument"
    assert -0x8000 < min(shifted) - LEVEL and max(shifted) - LEVEL < 0x7FFF, \
        "the compare can overflow -- `blt` would stop meaning `<` and the rung would invert"
    # 🛑 the UNSIGNED failure modes, spelled out rather than trusted.
    assert ((-1 & 0xFFFF) >> SHIFT) >= LEVEL, "the unsigned reading of -1 does NOT fire -- re-derive"
    assert not ((-1 >> SHIFT) >= LEVEL), "the signed reading of -1 fires -- the model is wrong"
    reach = {wire_byte4(a, s, c, t) & 0xF8
             for a in (0, 1, 0xFF) for s in (0, STATE_VALUE, 10)
             for c in (0x0000, 0x7FFF, 0x0100, 0x8000, 0xFE00) for t in (0, 4, CEIL_VALUE, 0xFF)}
    assert reach <= LEGAL_PAYLOADS, f"the wire model reaches {reach - LEGAL_PAYLOADS}, outside LEGAL"
    assert len(LEGAL_PAYLOADS) == 16, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 16"
    assert all(p & BIT_LIVE for p in LEGAL_PAYLOADS), "a legal payload lacks the liveness bit"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction, or to a self-checked ancestor.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    """
    V65._self_check_encoders()               # chains down through V59/V58/V57/V55/V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_LDH_6AD4, PIN_LDH_6B94, PIN_STH_6ADA, PIN_LDBU_671D, PIN_LDBU_67FA,
            PIN_LDBU_671A_R12, PIN_SAR9_R6, PIN_CMP_1_R6, PIN_CMP_4_R6, PIN_CMP_5_R6,
            PIN_MOVEA_10_R7, PIN_SHL3_R7, PIN_BLT4, PIN_BL4, PIN_BNE4, PIN_BNE6]
    pins += list(PIN_ADD_R7.values())
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # ---- the ld.h rung. THE ONE-BIT TRAP: ld.h = 0x39, st.h = 0x3B ---------------------------
    ours = V55.ldh(R24_MIRROR_DISP, R6)
    hw1, hw2 = struct.unpack("<HH", ours)
    assert ((hw1 >> 5) & 0x3F) == 0x39, \
        f"emitted opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h), not 0x3B (st.h)"
    assert ours != FF.sth(R6, -R24_MIRROR_DISP, GP) and \
        ours[:2] != FF.sth(R6, -R24_MIRROR_DISP, GP)[:2], \
        "the emitted load shares an opcode field with `st.h` -- that would WRITE a 1 kHz lane"
    assert ours != FF.ldhu(R24_MIRROR_DISP, R6), "ld.h collapsed onto ld.hu -- the SIGN would be lost"
    assert hw1 & 0x1F == GP == 4 and (hw1 >> 11) == R6, "ld.h reg1/reg2 fields are wrong"
    assert hw2 & 1 == 0, "ld.h hw2 LSB must be CLEAR (LSB set is the ld.w/ld.hu form)"
    assert hw2 == (0x10000 - R24_MIRROR_DISP) & 0xFFFF, "ld.h displacement is not -0x6ada"
    assert hw1 == struct.unpack_from("<H", PIN_LDH_6AD4[1], 0)[0] == \
        struct.unpack_from("<H", PIN_LDH_6B94[1], 0)[0], "hw1 differs from BOTH real `ld.h ...,r6`"
    assert hw2 == struct.unpack_from("<H", PIN_STH_6ADA[1], 2)[0], \
        f"displacement halfword does not match the real st.h @0x{PIN_STH_6ADA[0]:05X}"

    # ---- the three `ld.bu` rungs. ANOTHER ONE-BIT TRAP: ld.bu = 0x3C/0x3D, st.b = 0x3A --------
    # 🛑 THE hw1-BIT-5 PARITY TRAP. `ld.bu` carries the displacement's bit 0 in the OPCODE FIELD
    # (0x3C even / 0x3D odd), NOT in hw2, so a parity slip silently addresses the NEIGHBOURING cell
    # with every other field perfect. -0x671d = 0x98E3 is ODD => opcode 0x3D. -0x67fa = 0x9806 and
    # -0x671a = 0x98E6 are EVEN => opcode 0x3C.
    for disp, want_op, pin, name in ((MASK_DISP, 0x3D, PIN_LDBU_671D, "mask gp-0x671d"),
                                     (STATE_DISP, 0x3C, PIN_LDBU_67FA, "state gp-0x67fa"),
                                     (ARM3_DISP, 0x3C, None, "arm3 gp-0x671a")):
        ours = V55.ldbu_any(-disp, R6)
        hw1, hw2 = struct.unpack("<HH", ours)
        d16 = (0x10000 - disp) & 0xFFFF
        assert (d16 & 1) == (want_op & 1), \
            f"{name}: displacement 0x{d16:04X} parity disagrees with the expected opcode 0x{want_op:02X}"
        assert ((hw1 >> 5) & 0x3F) == want_op, \
            f"{name}: opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x{want_op:02X}"
        assert hw2 == (d16 | 1), f"{name}: hw2 is 0x{hw2:04X}, expected 0x{d16 | 1:04X} (disp | 1)"
        assert ours != FF.stb(R6, -disp, GP), f"{name}: the load collapsed onto an st.b -- a WRITE"
        assert ours != V55.ldh(disp, R6) and ours != FF.ldhu(disp, R6), \
            f"{name}: the load collapsed onto a HALFWORD load -- it would straddle the neighbour"
        assert (hw1 >> 11) == R6 and (hw1 & 0x1F) == GP, f"{name}: reg1/reg2 fields are wrong"
        if pin is not None:
            assert ours == pin[1], \
                f"{name}: not byte-identical to the real instance @0x{pin[0]:05X}"
    # ⚠ WEAK PIN, declared not buried: `ld.bu -0x671a[gp],r6` has NO byte-identical instance
    # image-wide. It is field-decomposed -- hw2 from the real `ld.bu -0x671a[gp],r12` @0x3AA70, hw1
    # from the real even-displacement `ld.bu ...,gp,r6` @0x2A508 -- exactly as V64/V67 did, and V64
    # and V67 both FLEW that halfword.
    ours = V55.ldbu_any(-ARM3_DISP, R6)
    assert ARM3_DISP in V67.WEAK_PIN_DISPS, "gp-0x671a is field-decomposed but not declared weak"
    assert ours[2:] == PIN_LDBU_671A_R12[1][2:], \
        f"gp-0x671a hw2 {ours[2:].hex()} != the real hw2 @0x{PIN_LDBU_671A_R12[0]:05X}"
    assert ours[:2] == src[PIN_LDBU_EVEN_R6[0]:PIN_LDBU_EVEN_R6[0] + 2], \
        f"gp-0x671a hw1 != the real even-disp `ld.bu ...,gp,r6` hw1 @0x{PIN_LDBU_EVEN_R6[0]:05X}"
    assert ours in V64.CAVE_BYTES and ours in V67.CAVE_BYTES, \
        "gp-0x671a's load is not byte-present in V64's AND V67's FLOWN caves"

    # ---- the 2-byte instructions -------------------------------------------------------------
    assert V55.sar(SHIFT, R6) == PIN_SAR9_R6[1], "sar 0x9,r6 != the real one"
    assert V55.sar(SHIFT, R6) != FF.shr(SHIFT, R6), "sar collapsed onto shr -- the sign would be lost"
    assert V55.cmp_imm5(LEVEL, R6) == PIN_CMP_1_R6[1], "cmp 0x1,r6 encoding changed"
    assert V55.cmp_imm5(STATE_VALUE, R6) == PIN_CMP_4_R6[1], "cmp 0x4,r6 != the real one @0x16F90"
    assert V55.cmp_imm5(CEIL_VALUE, R6) == PIN_CMP_5_R6[1], "cmp 0x5,r6 != the real one @0x16FA4"
    assert 0 <= STATE_VALUE <= 15 and 0 <= CEIL_VALUE <= 15, "Format II imm5 is SIGNED (-16..15)"
    assert FF.bcond(COND_BLT, +4) == PIN_BLT4[1], "blt +4 != the real one @0x290A8"
    assert FF.bcond(COND_BL, +4) == PIN_BL4[1], "bl +4 != the real one @0x14F3A"
    assert FF.bcond(COND_BNE, +4) == PIN_BNE4[1], "bne +4 != the real one @0x1A8A6"
    assert FF.bcond(COND_BNE, +6) == PIN_BNE6[1], "bne +6 != the real one @0x14CB2 (cond cross-check)"
    assert COND_BLT != COND_BL, "blt collapsed onto the UNSIGNED bl"
    assert COND_BNE != 0x2, "bne collapsed onto be -- the state rung would INVERT"
    for imm, (addr, raw) in PIN_ADD_R7.items():
        assert add_imm5(imm, R7) == raw, f"add 0x{imm:x},r7 != the real one @0x{addr:05X}"
        assert add_imm5(imm, R7) != V55.cmp_imm5(imm, R7), \
            f"add 0x{imm:x} collapsed onto cmp -- the bit would never set"
        assert decode_fmt2(struct.unpack("<H", raw)[0]) == {"imm5": imm, "opcode": 0x12, "reg2": R7}
    assert add_imm5(8, R7) != add_imm5(8, R6), "add_imm5 ignores its register"
    assert V54.shl(PAYLOAD_SHIFT, R7) == PIN_SHL3_R7[1], "shl 0x3,r7 != the real one @0x4FB82"
    assert V54.shl(PAYLOAD_SHIFT, R7) == V54.V31P_SHL3_R7, \
        "shl 0x3,r7 differs from V31P's FLASHED byte sequence"
    assert V54.shl(PAYLOAD_SHIFT, R7) != V55.sar(PAYLOAD_SHIFT, R7) and \
        V54.shl(PAYLOAD_SHIFT, R7) != FF.shr(PAYLOAD_SHIFT, R7), \
        "shl collapsed onto a RIGHT shift -- the payload would land in the wrong bits"
    assert V54.shl(PAYLOAD_SHIFT, R7) in V55.CAVE_BYTES, \
        "`shl 0x3,r7` is not byte-present in V55's FLOWN cave"
    assert FF.movea(W_LIVE, R0, R7) == PIN_MOVEA_10_R7[1], "movea 0x10,r0,r7 != the real one @0x49256"

    weights = (W_LIVE, W_MASK671D, W_STATE4, W_R24HALF, W_ARM3671A)
    assert len(set(weights)) == 5 and all(w & (w - 1) == 0 for w in weights), "weights are not distinct"
    assert sum(weights) == 0x1F, f"weights must occupy exactly bits 4:0, got 0x{sum(weights):02X}"
    assert sum(w << PAYLOAD_SHIFT for w in weights) == 0xF8, "payload bits are not exactly 7:3"
    assert (sum(weights) << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
        "the shifted payload collides with the preserved status bits"
    _wire_model()


def build_cave():
    """pack_gain_in_force -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x10,r0,r7       ; r7 = 0x10   bit7 LIVENESS, in PRE-SHIFT weights
        ld.bu -0x671d[gp],r6   ; THE MASK -- outranks every arm at 0x3ABFA
        cmp   0x1,r6           ; zero-extended byte: `< 1` IS `== 0`
        blt   +4
        add   0x8,r7           ; bit6 = gp-0x671d != 0
      g0:
        ld.bu -0x67fa[gp],r6   ; the ECU STATE byte
        cmp   0x4,r6
        bne   +4
        add   0x4,r7           ; bit5 = (gp-0x67fa == 4)   THE RATCHET STATE this build disables
      g1:
        ld.h  -0x6ada[gp],r6   ; r24's lane output, post +/-0x2000 clip (0 readers image-wide)
        sar   0x9,r6           ; ARITHMETIC: units of 512, sign preserved
        cmp   0x1,r6
        blt   +4
        add   0x2,r7           ; bit4 = gp-0x6ada >= +512  THE POSITIVE CONTROL
      g2:
        ld.bu -0x671a[gp],r6   ; the third arm's latched reversal counter
        cmp   0x5,r6           ; CEIL -- asserted equal to cal 0xC64FA (a BYTE)
        bl    +4               ; UNSIGNED, matching the firmware's own `bc` @0x3AA7E
        add   0x1,r7           ; bit3 = gp-0x671a >= 5
      g3:
        shl   0x3,r7           ; the 5-bit field -> bits 7:3   (V31P's FLASHED idiom; Honda's @0x4FB82)
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    _self_check_encoders()
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(W_LIVE, R0, R7), "movea 0x10,r0,r7    ; bit7 LIVENESS (pre-shift weight 0x10)")

    rungs = []
    for disp, weight, cond, imm, name, note in (
            (MASK_DISP, W_MASK671D, COND_BLT, 1, "bit6",
             "gp-0x671d != 0   THE MASK: pins the gain to 0xC6442 = 1024"),
            (STATE_DISP, W_STATE4, COND_BNE, STATE_VALUE, "bit5",
             f"(gp-0x67fa == {STATE_VALUE})  THE RATCHET STATE"),
            (None, W_R24HALF, COND_BLT, LEVEL, "bit4",
             f"gp-0x6ada >= +{THRESHOLD}   THE POSITIVE CONTROL"),
            (ARM3_DISP, W_ARM3671A, COND_BL, CEIL_VALUE, "bit3",
             "gp-0x671a >= 5   the THIRD arm (0xC6440 = 2048)")):
        if disp is None:                       # bit4 is the one SIGNED, halfword rung
            emit(V55.ldh(R24_MIRROR_DISP, R6),
                 "ld.h -0x6ada[gp],r6 ; r24 lane out, post-clip (SIGNED, 0 readers)")
            emit(V55.sar(SHIFT, R6), f"sar 0x{SHIFT:x},r6           ; ARITHMETIC -- units of {THRESHOLD}")
        else:
            emit(V55.ldbu_any(-disp, R6), f"ld.bu -0x{disp:04x}[gp],r6 ; zero-extended BYTE")
        emit(V55.cmp_imm5(imm, R6), f"cmp 0x{imm:x},r6")
        br_idx = len(listing)
        emit(FF.bcond(cond, +4), f"b{'lt' if cond == COND_BLT else ('l' if cond == COND_BL else 'ne')}"
                                 f" +4              ; skip -> g{len(rungs)}")
        emit(add_imm5(weight, R7), f"add 0x{weight:x},r7          ; {name} = {note}")
        rungs.append((br_idx, CAVE_BASE + len(body), cond, name))

    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7          ; the 5-bit field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp] ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands EXACTLY on its label, located BY POSITION ---------------
    for br_idx, label, cond, name in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a Bcond"
        assert addr + 4 == label, f"{name}: branch target 0x{addr + 4:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, \
            f"{name}: branch condition is 0x{struct.unpack('<H', raw)[0] & 0xF:X}, not 0x{cond:X} -- " \
            "the wrong condition INVERTS the whole rung (the V67 setfne/setfe lesson)"
        setter = listing[br_idx + 1][1]
        assert len(setter) == 2 and decode_fmt2(struct.unpack("<H", setter)[0])["opcode"] == 0x12, \
            f"{name}: the skipped instruction is not a 2-byte `add imm5,r7`"
    assert [listing[i][0] for i, _, _, _ in rungs] == [0xC4B3E, 0xC4B48, 0xC4B54, 0xC4B5E], \
        "the branch addresses drifted from the design"

    # ---- GATE 2b: r6/r7 LIVENESS. Only a rung's own load/shift may write r6 ------------------
    r6_writers = {listing[i][0] for i in (1, 5, 9, 10, 14)}
    for idx in range(0, rungs[-1][0] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                # cmp imm5,reg2 / cmp reg1,reg2 -- flags
            continue
        want = R6 if addr in r6_writers else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    # 🛑 bit4 reads the SHIFTED r6 one instruction after the `sar`; nothing may clobber it between.
    for _a, raw, text in [listing[i] for i in (11,)]:
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert ((hw >> 5) & 0x3F) == 0x13, f"'{text}' is not the `cmp` that consumes the shift"
    for disp in (R24_MIRROR_DISP,):
        assert sum(1 for _, r, _ in listing if r == V55.ldh(disp, R6)) == 1, \
            f"gp-0x{disp:04x} is loaded more than once"
    for disp in (MASK_DISP, STATE_DISP, ARM3_DISP):
        assert sum(1 for _, r, _ in listing if r == V55.ldbu_any(-disp, R6)) == 1, \
            f"gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store ---------------
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert store_idx == [22], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[22][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "the sole store is not the payload"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == 4 + 10 + 10 + 12 + 10 + 2 + 20 == 68, \
        f"the cave is {len(body)}B, the budget says 68"
    assert len(body) <= CAVE_EXTENT, \
        f"cave {len(body)}B overruns the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def assert_probe_census(buf, cave_span):
    """Re-derive each probed cell's reader/writer set from RAW BYTES and assert it exactly.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    read_mnem = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}
    for disp, (n_read, n_write, writers, mnems) in PROBE_CENSUS.items():
        hits = V64.gp_access_census(buf, disp)
        fw = [h for h in hits if h[0] not in cave_span]
        assert all(m in mnems for _, m, _ in fw), \
            f"gp-0x{disp:04x} has a firmware access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        reads = [h for h in fw if h[1] in read_mnem]
        writes = [h for h in fw if h[1] not in read_mnem]
        assert len(reads) == n_read, \
            f"gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert [a for a, _, _ in writes] == writers, \
            f"gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}, expected " \
            f"{[hex(w) for w in writers]}"
        cave = [h for h in hits if h[0] in cave_span]
        want_mnem = "ld.h" if disp == R24_MIRROR_DISP else "ld.bu"
        assert len(cave) == 1 and cave[0][1] == want_mnem and cave[0][2] == R6, \
            f"gp-0x{disp:04x}: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, expected " \
            f"exactly one `{want_mnem} ...,r6`"
    # 🛑 The probed HALFWORD cell has ZERO firmware readers -- the strongest GATE-1 statement
    # available, AND it means a one-bit ld.h->st.h slip could only corrupt a cell nobody reads.
    assert PROBE_CENSUS[R24_MIRROR_DISP][0] == 0, "gp-0x6ada acquired a reader -- no longer free"

    # ---- the state cell gets a SHAPE check, not an equality: it is live, with ~128 readers -----
    hits = V64.gp_access_census(buf, STATE_DISP)
    fw = [h for h in hits if h[0] not in cave_span]
    reads = [h for h in fw if h[1] in read_mnem]
    writes = [h for h in fw if h[1] not in read_mnem]
    # 🛑 WIDTH, not mnemonic: 126 `ld.bu` + 2 `ld.b` + 33 `st.b` = 161, ALL byte-width. `ld.b`
    # SIGN-extends where ours zero-extends; immaterial because every legal state is < 0x80.
    assert all(m in {"ld.bu", "ld.b", "st.b"} for _, m, _ in fw), \
        f"gp-0x{STATE_DISP:04x} is not accessed purely as a BYTE -- our `ld.bu` has the wrong width"
    assert STATE_VALUE < 0x80, "the compared state is >= 0x80: ld.b and ld.bu would disagree"
    assert len(reads) >= STATE_MIN_READERS, \
        f"gp-0x{STATE_DISP:04x} has only {len(reads)} readers, expected >= {STATE_MIN_READERS}"
    assert writes, f"gp-0x{STATE_DISP:04x} has NO writer -- it is not a live state variable"
    cave = [h for h in hits if h[0] in cave_span]
    assert len(cave) == 1 and cave[0][1] == "ld.bu" and cave[0][2] == R6, \
        f"gp-0x{STATE_DISP:04x}: the cave must READ it exactly once and WRITE it never, got {cave}"
    return len(reads), len(writes)


def assert_ratchet_edit(buf, label, expect_edited):
    """The one code byte, decoded BOTH ways: as a Bcond, and as raw context."""
    for addr, raw in RATCHET_CTX:
        assert bytes(buf[addr:addr + len(raw)]) == raw, \
            f"{label}: instruction context @0x{addr:05X} is {bytes(buf[addr:addr + len(raw)]).hex()}, " \
            f"expected {raw.hex()} -- the baseline is not what we think it is"
    want_hw = RATCHET_NEW_HW if expect_edited else RATCHET_STOCK_HW
    want_cond = COND_BNE_BR[1] if expect_edited else COND_BNE_BR[0]
    got = u16(buf, RATCHET_ADDR)
    assert got == want_hw, f"{label}: 0x{RATCHET_ADDR:05X} is 0x{got:04X}, expected 0x{want_hw:04X}"
    decoded = decode_bcond(buf, RATCHET_ADDR)
    assert decoded == (want_cond, SUBST_BLOCK[1]), \
        f"{label}: 0x{RATCHET_ADDR:05X} decodes as {decoded}, expected " \
        f"(0x{want_cond:X}, 0x{SUBST_BLOCK[1]:05X})"
    assert buf[RATCHET_ADDR + 1] == (RATCHET_STOCK_HW >> 8), \
        f"{label}: the HIGH byte of the branch moved -- the DISPLACEMENT is no longer provably intact"


def assert_governor_monitor_safety(buf, label):
    """🛑 FUN_0004595a IS A REAL EXTERNAL MONITOR ON gp-0x6ace, WITH NO DEBOUNCE.

    It computes |gp-0x6b94| - |gp-0x6ace| and the product gp-0x6ace * gp-0x6b94, and faults --
    FUN_000462e6 -> FUN_00016de6(0x1d,...), hard-fault-eligible, motor off -- if the overshoot
    exceeds ~0.01 (about 10 raw counts) or the signs oppose. V42's build note recorded the safety
    argument as [INFERRED] with "zero margin for error". This function CONFIRMS it against the built
    image, by a raw two-decoder byte scan (the required second method), and the CONTROL-FLOW half was
    confirmed by reading the decompilation of FUN_0004503c directly:

      * the slew at 0x45434-0x4545A limits movement AWAY FROM ZERO only -- the rising branch is
        guarded by `0 < target` and the falling branch by `target < 0`; movement TOWARD zero falls
        through to `result = target` with no limit at all. So |gp-0x6ace| <= |target| ALWAYS, and its
        sign matches the target's (with a zero-crossing reset to 0 at 0x45434).
      * the target is derived SOLELY from gp-0x6b94 (0x453E0), which is what the monitor compares
        against. The relation the monitor checks is therefore invariant to the target's magnitude.
      * the substitution fires only when |gp-0x138a| < |gp-0x6ace| and substitutes the SMALLER
        magnitude, so removing it can only make |gp-0x6ace| LARGER -- never differently signed.
    ⇒ after the edit, state 4 delivers exactly what states 3/5/6/8/9/10/11 already deliver on EVERY
      cycle of every drive, including on stock firmware, and that is the value the monitor validates
      continuously. VERDICT: CONFIRMED. ⭐ V42 also FLEW this exact byte fault-free.

    ⚠ THE ONE GENUINELY NEW THING, stated rather than buried: no build has flown 0x454FE TOGETHER
      with the doubled rate lanes. The bounding argument is that gp-0x6ace is derived from gp-0x6b94
      by a Q15 scale plus a one-sided slew, so a larger target gives MORE absolute margin against the
      monitor's fixed ~10-count tolerance, not less -- but that is [BELIEF], not a measurement.
    """
    read_mnem = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}
    primary, subst = range(0x4503C, 0x454F8), range(*SUBST_BLOCK)
    func, monitor = range(0x4503C, 0x45700), range(0x4595A, 0x45A60)

    hits = V64.gp_access_census(buf, STATE_DISP)
    in_prim = [a for a, _m, _r in hits if a in primary]
    in_func = [a for a, _m, _r in hits if a in func]
    assert not in_prim, f"{label}: the PRIMARY block reads gp-0x67fa at {[hex(a) for a in in_prim]} " \
                        "-- the primary value would NOT be state-independent"
    assert in_func == [0x454F8], \
        f"{label}: gp-0x67fa is accessed in FUN_0004503c at {[hex(a) for a in in_func]}, expected " \
        "exactly [0x454f8] -- the state-4 check itself"
    assert not [a for a, _m, _r in V64.gp_access_census(buf, STATE_DISP) if a in monitor], \
        f"{label}: FUN_0004595a reads gp-0x67fa -- the monitor DOES model the state-4 hold, and the " \
        "whole safety argument collapses"

    # gp-0x6ace and its lockstep shadow gp-0x4cca must be written in PAIRS inside each block, so
    # skipping the substitution cannot desynchronise them (the V24/V25/V26/V27 fault mode).
    for blk, name in ((primary, "primary"), (subst, "substitution")):
        w6ace = [a for a, m, _r in V64.gp_access_census(buf, 0x6ACE) if a in blk and m not in read_mnem]
        w4cca = [a for a, m, _r in V64.gp_access_census(buf, 0x4CCA) if a in blk and m not in read_mnem]
        assert len(w6ace) == len(w4cca) == 2, \
            f"{label}: the {name} block writes gp-0x6ace {len(w6ace)}x and gp-0x4cca {len(w4cca)}x " \
            "-- the lockstep pair is no longer written on every path inside one block"
    # the gp-0x138a writeback must be OUTSIDE the block the edit makes unreachable.
    w138a = [a for a, m, _r in V64.gp_access_census(buf, 0x138A) if a in func and m not in read_mnem]
    assert 0x455CC in w138a and 0x455CC not in subst, \
        f"{label}: the gp-0x138a writeback is not the unconditional one at 0x455CC"
    assert not [a for a in w138a if a in subst], \
        f"{label}: the substitution block writes gp-0x138a at {[hex(a) for a in w138a if a in subst]}"
    return len(in_func)


def assert_no_external_entry(buf):
    """The substitution block must be reachable ONLY by falling through the edited branch."""
    low, high = SUBST_BLOCK
    for address in range(0x4503C, 0x45700, 2):
        if low <= address < high:
            continue
        decoded = decode_bcond(buf, address)
        if decoded and low <= decoded[1] < high:
            raise AssertionError(f"external Bcond @0x{address:05X} enters the substitution block")
        hw = u16(buf, address)
        if (hw & 0xFFC0) == 0x0780:                      # jr/jarl disp22
            disp = ((hw & 0x3F) << 16) | u16(buf, address + 2)
            if disp & 0x200000:
                disp -= 0x400000
            if low <= address + disp < high:
                raise AssertionError(f"external jr @0x{address:05X} enters the substitution block")


def assert_sar_sites(buf, label, expect_doubled):
    """Both shifts are `sar imm5,regN` with ONLY the immediate moved 10 -> 9. Nothing else may differ."""
    for addr in (R26_SAR, R24_SAR):
        want = SAR_NEW_HW[addr] if expect_doubled else SAR_STOCK_HW[addr]
        got = u16(buf, addr)
        assert got == want, f"{label}: 0x{addr:05X} is 0x{got:04X}, expected 0x{want:04X}"
        f_got, f_stock = decode_fmt2(got), decode_fmt2(SAR_STOCK_HW[addr])
        assert f_got["opcode"] == V62.SAR_OPCODE == 0x15, f"{label}: 0x{addr:05X} is not a `sar`"
        assert f_got["opcode"] == f_stock["opcode"] and f_got["reg2"] == f_stock["reg2"], \
            f"{label}: 0x{addr:05X} changed more than the immediate -- opcode/reg2 moved"
        assert f_got["imm5"] == (9 if expect_doubled else 10), \
            f"{label}: 0x{addr:05X} imm5 is {f_got['imm5']}"
    assert u16(buf, R26_SAR_FIRST) == R26_SAR_FIRST_HW, \
        f"{label}: 0x{R26_SAR_FIRST:05X} moved -- editing the FIRST r26 shift pushes a mul operand " \
        "to 94% of INT32_MAX and V850 `mul` truncates the high word silently"


def assert_decoder_matches(cave_bytes, label="V71"):
    """🛑 The decoder's header must match the BUILT image, not a previous revision."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, f"{label}: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"{label}: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    for token in ("0xC4124", os.path.basename(OUT)):
        assert token in txt, f"{label}: the decoder does not carry '{token}'"
    assert re.search(rf"^THRESHOLD\s*=\s*{THRESHOLD}\b", txt, re.M), \
        f"{label}: the decoder's THRESHOLD is not {THRESHOLD}"
    assert re.search(rf"^STATE_VALUE\s*=\s*{STATE_VALUE}\b", txt, re.M), \
        f"{label}: the decoder's STATE_VALUE is not {STATE_VALUE} -- it applies V70's semantics"
    m = re.search(r"^RUNGS\s*=\s*\((.*?)^\)", txt, re.M | re.S)
    assert m, f"{label}: the decoder has no RUNGS literal -- its bit map cannot be checked"
    up = m.group(1).upper()                  # ⚠ so is the needle: `0x` upper-cases to `0X`
    for disp in (MASK_DISP, STATE_DISP, R24_MIRROR_DISP, ARM3_DISP):
        assert f"{disp:04X}" in up, f"{label}: gp-0x{disp:04x} is not a rung in the decoder's bit map"
    for stale in (0x6ADC, 0x6B62, 0x6AD4, 0x67DF, 0x6806):
        assert f"{stale:04X}" not in up, \
            f"{label}: gp-0x{stale:04x} is still a LIVE RUNG in the decoder's bit map -- V71 retired it"
    # 🛑 AND THE CONTROL PATH IT DESCRIBES MUST BE THIS BUILD'S. ⚠ The guard tests the CLAIM, not the
    # string: mentioning a superseded path is REQUIRED for the record; asserting it as V71's is the
    # fault. (An earlier revision of this check on V70 banned a substring and thereby forbade the very
    # paragraph that documented the supersession.)
    for false_claim in ("V70CONTROLPATH", "byte-identical to V70's", "V70's surface dose, kept"):
        assert false_claim not in txt, \
            f"{label}: the decoder asserts the SUPERSEDED V70 surface dose as V71's ('{false_claim}')"
    for token in ("surfaceREVERTED", "0x454FE", "V62sar"):
        assert token in txt, f"{label}: the decoder does not name the shipped topology ('{token}')"
    return True


def r24_rail(gain_q10, sar_imm):
    """|dtorque| at which r24's lane output reaches its +/-0x2000 clip.  (d*g) >> sar == 8192."""
    return 0x2000 * (1 << sar_imm) // gain_q10


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    if os.path.exists(BIN_OUT):
        existing = Path(BIN_OUT).read_bytes()
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be compared, not blindly overwritten.")
    else:
        existing = None

    src = Path(SRC_BIN)
    v70 = bytearray(src.read_bytes())
    v62 = Path(V62_BIN).read_bytes()
    v65 = Path(V65_BIN).read_bytes()
    v42 = Path(V42_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V70): {src}\n  SHA256 {hashlib.sha256(bytes(v70)).hexdigest()}")
    print(f"RATE-LANE REFERENCES: {V62_BIN}\n                      {V65_BIN}")
    print(f"STOCK: {STOCK_BIN}")

    # ---- gate the SOURCE and every reference before touching anything --------------------------
    for name, img in (("V70", v70), ("V62", v62), ("V65", v65), ("V42", v42), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert v70[REPOINT_BYTE] == GATE_DEAD, \
        f"source gate byte is 0x{v70[REPOINT_BYTE]:02X}, expected V69/V70's 0x{GATE_DEAD:02X}"
    assert u16(v70, ARM_ADDR) == ARM_STOCK, f"source arm is {u16(v70, ARM_ADDR)}, expected {ARM_STOCK}"
    for addr, old, new, name in SURFACE:
        assert u16(v70, addr) == old, f"{name} @0x{addr:05X} is {u16(v70, addr)}, expected V70's {old}"
        assert u16(stock, addr) == new, f"{name} is not {new} on the STOCK image"
    assert_sar_sites(v70, "V70 source", expect_doubled=False)
    assert_sar_sites(stock, "stock", expect_doubled=False)
    assert_sar_sites(v62, "V62 reference", expect_doubled=True)
    assert_sar_sites(v65, "V65 reference", expect_doubled=True)
    assert_ratchet_edit(v70, "V70 source", expect_edited=False)
    assert_ratchet_edit(stock, "stock", expect_edited=False)
    assert_ratchet_edit(v42, "V42 reference", expect_edited=True)
    assert_no_external_entry(v70)
    role = list(v70[0xC4124:0xC4124 + 11])
    assert role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0], f"role table drifted: {role}"
    assert not any(r in (6, 7) for r in role), \
        "a slot carries role 6 or 7 -- gp-0x67ac becomes LIVE and the rate lanes can drop out"
    assert stock[CEIL_CAL] == CEIL_VALUE == 5, \
        f"cal 0xC64FA is {stock[CEIL_CAL]} on stock, not {CEIL_VALUE} -- bit3's hardcoded CEIL desyncs"
    assert v70[CEIL_CAL] == CEIL_VALUE, "cal 0xC64FA moved on V70 -- bit3's hardcoded CEIL desyncs"

    # ⭐ THE TWO FACTS THE ORCHESTRATOR VERIFIED. Asserted, not re-derived.
    lo, hi = RATCHET_REGION
    d_region = [i for i in range(lo, hi) if v70[i] != stock[i]]
    assert d_region == [], \
        f"V70's [0x{lo:05X},0x{hi:05X}) is NOT byte-identical to stock: {[hex(x) for x in d_region]}"
    d_v42 = [i for i in range(lo, hi) if v42[i] != stock[i]]
    assert d_v42 == [RATCHET_ADDR], \
        f"V42 differs from stock in [0x{lo:05X},0x{hi:05X}) at {[hex(x) for x in d_v42]}, expected " \
        f"exactly [0x{RATCHET_ADDR:05X}]"
    print(f"  source gates: gate 0xC5, arm 512, surface x{V70_SCALE}, sar sites STOCK, "
          f"0x{RATCHET_ADDR:05X} stock, role {role}, cal 0xC64FA = {CEIL_VALUE}  ✅")
    print(f"  ⭐ V70's [0x{lo:05X},0x{hi:05X}) is byte-identical to STOCK (0 differing bytes), and V42")
    print(f"     differs from stock there by EXACTLY 0x{RATCHET_ADDR:05X}. Both ASSERTED, not argued.")

    code = bytearray(v70)

    # ---- EDIT 1 -- the ratchet fix -------------------------------------------------------------
    print("\n  EDIT 1 -- THE RATCHET FIX (V42's CONFIRMED root cause), one condition-code nibble:")
    before = decode_bcond(code, RATCHET_ADDR)
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    after = decode_bcond(code, RATCHET_ADDR)
    print(f"    0x{RATCHET_ADDR:05X}  0x{RATCHET_STOCK_HW:04X} -> 0x{RATCHET_NEW_HW:04X}   "
          f"byte 0x{v70[RATCHET_ADDR]:02X} -> 0x{code[RATCHET_ADDR]:02X}")
    print(f"    bne 0x{before[1]:05X}  ->  br 0x{after[1]:05X}   cond 0x{before[0]:X} -> 0x{after[0]:X}"
          f"   ⇒ [0x{SUBST_BLOCK[0]:05X},0x{SUBST_BLOCK[1]:05X}) becomes UNREACHABLE")
    assert before[1] == after[1] == SUBST_BLOCK[1], "branch TARGET moved -- the displacement was disturbed"
    assert_ratchet_edit(code, "V71", expect_edited=True)
    assert bytes(code[RATCHET_ADDR:RATCHET_ADDR + 2]) == bytes(v42[RATCHET_ADDR:RATCHET_ADDR + 2]), \
        "the emitted halfword is not byte-identical to V42's FLOWN one"
    assert_no_external_entry(code)
    print("    ✅ branch target unchanged; the substitution block has NO external entry (Bcond + jr "
          "scan over 0x4503C-0x45700); the halfword is byte-identical to V42's FLOWN one.")
    n_state = assert_governor_monitor_safety(code, "V71")
    print("    ✅ FUN_0004595a SAFETY: CONFIRMED, not merely inherited. Re-derived on THIS image by a")
    print(f"       raw two-decoder byte scan: gp-0x67fa is read {n_state}x in FUN_0004503c -- ONLY at")
    print("       0x454F8, the state check itself -- and ZERO times in the primary block, so the")
    print("       primary value is STATE-INDEPENDENT; gp-0x6ace and its lockstep shadow gp-0x4cca are")
    print("       written in PAIRS inside each block, so skipping the substitution cannot desync")
    print("       them; the gp-0x138a writeback @0x455CC is OUTSIDE the skipped block; and")
    print("       FUN_0004595a's own body never reads gp-0x67fa. See the function's docstring for")
    print("       the control-flow half (the slew limits AWAY from zero only ⇒ |6ace| <= |target|).")
    print("    ⚠ NEW COMBINATION: no build has flown 0x454FE together with the doubled rate lanes.")
    print("      The bounding argument (a larger target gives MORE absolute margin against the")
    print("      monitor's fixed ~10-count tolerance) is [BELIEF], not a measurement.")

    # ---- EDIT 2 -- V62's two `sar` immediates ---------------------------------------------------
    print("\n  EDIT 2 -- THE GRIND FIX (V62's `sar`), BOTH lanes:")
    for addr, what in ((R26_SAR, "r26 lane: (stage1  * gain_A) >> 10 -> >> 9"),
                       (R24_SAR, "r24 lane: (dtorque * gain_B) >> 10 -> >> 9")):
        struct.pack_into("<H", code, addr, SAR_NEW_HW[addr])
        print(f"    0x{addr:05X}  0x{SAR_STOCK_HW[addr]:04X} -> 0x{SAR_NEW_HW[addr]:04X}   "
              f"sar 0xa -> sar 0x9   {what}")
    print(f"    0x{R26_SAR_FIRST:05X} deliberately LEFT at `sar 0xa` (overflow margin).")
    assert_sar_sites(code, "V71", expect_doubled=True)
    for addr in (R26_SAR, R24_SAR, R26_SAR_FIRST):
        assert u16(code, addr) == u16(v62, addr) == u16(v65, addr), \
            f"0x{addr:05X} does not equal V62's AND V65's halfword"
    print("    ✅ both `sar` halfwords are byte-identical to V62's and V65's, opcode and reg2 fields")
    print("       asserted UNCHANGED ⇒ the edit moves the shift IMMEDIATE and nothing else.")

    # ---- EDIT 3 -- drop the falsified surface dose ----------------------------------------------
    print("\n  EDIT 3 -- DROP THE FALSIFIED SURFACE DOSE (mode-10 gain_B rec0/rec1 -> STOCK):")
    for addr, old, new, name in SURFACE:
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   bytes {struct.pack('<H', old).hex(' ')} -> "
              f"{struct.pack('<H', new).hex(' ')}   {name}")
        assert new == STOCK_Y[addr] and u16(stock, addr) == new, f"{name} is not the STOCK value"
    for base, ys in REC_Y_STOCK.items():
        assert list(struct.unpack_from("<4h", code, base + 0x0A)) == ys, \
            f"mode-10 gain_B record 0x{base:05X} Y row is {list(struct.unpack_from('<4h', code, base + 0x0A))}, expected {ys}"
        assert bytes(code[base:base + 0x14]) == bytes(stock[base:base + 0x14]), \
            f"mode-10 gain_B record 0x{base:05X} is not byte-identical to STOCK"
    print("    ✅ all FOUR mode-10 gain_B records byte-identical to STOCK "
          f"(rec0 Y={REC_Y_STOCK[REC0]}, rec1 Y={REC_Y_STOCK[REC1]}, rec2/rec3 untouched).")

    # ---- EDIT 4 -- the probe --------------------------------------------------------------------
    print("\n  EDIT 4 -- THE PROBE (68 of the proven 68 bytes; ZERO spare):")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    print(f"    cave {len(cave_bytes)}B / {CAVE_EXTENT}B proven extent -- UNCHANGED (flown 9x), ZERO spare")
    assert code[CAVE_BASE + 2] == W_LIVE, "the liveness immediate is not the pre-shift weight 0x10"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v70[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical"

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    nr, nw = assert_probe_census(bytes(code), cave_span)
    print("\n    ✅ GATE 1 (RAM ownership) asserted as a MEASUREMENT, from raw bytes, two decoders:")
    for disp, (r, w, wr, _m) in PROBE_CENSUS.items():
        extra = "  ⇐ ZERO readers: a pure mirror" if r == 0 else ""
        print(f"       gp-0x{disp:04x}  {r}r / {w}w  writers {[hex(a) for a in wr]}{extra}")
    print(f"       gp-0x{STATE_DISP:04x}  {nr}r / {nw}w  a LIVE state byte -- READ ONLY by the cave")
    print("       the cave's ONLY store is st.b r6,-0x1514[gp] (the CAN-330 payload byte, bits 2:0")
    print("       preserved) -- identical RAM ownership to V67/V68/V69/V70, all flown clean.")
    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v71_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 THE CENTRAL SAFETY CLAIM: the rate lane IS V62's and V65's, byte for byte -----------
    print("\n  GATE 2 (closed-loop stability) -- ASSERTED, NOT ARGUED:")
    for lo_s, hi_s, what in RATE_LANE_SPANS:
        d62 = [i for i in range(lo_s, hi_s) if code[i] != v62[i]]
        d65 = [i for i in range(lo_s, hi_s) if code[i] != v65[i]]
        assert not d62, f"rate-lane span [0x{lo_s:05X},0x{hi_s:05X}) differs from V62 at " \
                        f"{[hex(x) for x in d62[:8]]}"
        assert not d65, f"rate-lane span [0x{lo_s:05X},0x{hi_s:05X}) differs from V65 at " \
                        f"{[hex(x) for x in d65[:8]]}"
        print(f"    ✅ [0x{lo_s:05X},0x{hi_s:05X}) byte-identical to V62 AND V65 -- {what}")
    print("    ⇒ no filter, no pole, no delay, no phase change anywhere. The lane configuration V71")
    print("      ships has ALREADY FLOWN TWICE, flight-clean. That equivalence IS the GATE-2 evidence.")

    # ---- structural gates ------------------------------------------------------------------------
    print("\n  STRUCTURAL GATES:")
    assert (code[REPOINT_BYTE], u16(code, ARM_ADDR)) == (GATE_DEAD, ARM_STOCK), \
        "the control path is neither V69/V70's (0xC5/512) nor V67/V68's (0xFB/5244)"
    assert not (u16(code, ARM_ADDR) == ARM_STOCK and code[REPOINT_BYTE] != GATE_DEAD), \
        "arm == 512 while the gate is STILL repointed to the LIVE cell -- ~5x BELOW stock everywhere"
    assert not (code[REPOINT_BYTE] == GATE_LIVE and u16(code, ARM_ADDR) != ARM_GATED), \
        "gate == 0xFB (LIVE) with an arm that is not 5244 -- the other topology's failure mode"
    assert bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4]) == bytes.fromhex("847fc597"), \
        "the gate load is not the stock `ld.bu -0x683c[gp],r15`"
    print(f"    ✅ EDIT-ORDER INVARIANT asserted BOTH WAYS; (gate, arm) = "
          f"(0x{GATE_DEAD:02X}, {ARM_STOCK}) ⇒ 0xC6446 is UNREACHABLE (gp-0x683c has 0 writers)")
    for a in NEIGHBOURS:
        assert bytes(code[a:a + 20]) == bytes(stock[a:a + 20]), \
            f"neighbour record 0x{a:05X} MOVED -- the byte-pattern trap fired"
    print(f"    ✅ all {len(NEIGHBOURS)} mode-11/12 neighbour records byte-identical to STOCK "
          "(mode 11/12 rec0 are byte-IDENTICAL to mode 10's -- the pattern occurs 3x in 40 bytes)")
    for a in UNTOUCHED_RECS:
        assert bytes(code[a:a + 20]) == bytes(stock[a:a + 20]), f"mode-10 rec 0x{a:05X} moved"
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == bytes(stock[D2000_BLOCK[0]:D2000_BLOCK[1]]), \
        "V60's falsified slew-blend cells are not at STOCK"
    assert u16(code, V57.PRIVATE_ADDR) == u16(v70, V57.PRIVATE_ADDR), "V57's private cell moved"
    # 🛑 V57's inherited guard asserts 0x454FE is the STOCK `bne` -- which is precisely what V71
    # changes. Rather than skip the guard (which would also stop checking V53's eleven STOCK_CALS),
    # run it in FULL on a copy with the one intended byte restored, and then ASSERT that the copy
    # differs from the built image at EXACTLY that byte. The exception set is itself gated, so a
    # future stray edit cannot hide inside the relaxation -- the V67/0xC6446 precedent.
    probe_copy = bytearray(code)
    struct.pack_into("<H", probe_copy, RATCHET_ADDR, RATCHET_STOCK_HW)
    V57.assert_decoupled(probe_copy, "V71 (with 0x454FE restored for the inherited guard)")
    exception_set = [i for i in range(START, END) if probe_copy[i] != code[i]]
    assert exception_set == [RATCHET_ADDR], \
        f"the guard relaxation covers {[hex(x) for x in exception_set]}, expected exactly " \
        f"[0x{RATCHET_ADDR:05X}]"
    assert V53.RATCHET_ADDR == RATCHET_ADDR and V53.RATCHET_STOCK_HW == RATCHET_STOCK_HW, \
        "this file's ratchet constants disagree with V53's"
    print(f"    ✅ V53's eleven STOCK_CALS re-checked through V57's inherited guard; the ONLY "
          f"relaxation is 0x{RATCHET_ADDR:05X} itself, asserted as a one-byte exception set")
    V55.assert_variant_tables(code)
    print("    ✅ V60's blend cells STOCK; V57's decoupling carried; variant tables intact")

    # ---- the dose, proven by sweep ---------------------------------------------------------------
    print("\n  THE DOSE -- a FLAT 2.000000x, from the shift, at EVERY speed and rate:")
    grid = [(v, r) for v in range(0, 6401, 32) for r in range(0, 3001, 25)]
    same = [(v, r) for v, r in grid if V69.gain_q10(code, v, r) != V69.gain_q10(stock, v, r)]
    assert not same, f"a gain_B operating point moved: {same[:4]} -- the surface must be STOCK"
    print(f"    ✅ over {len(grid)} operating points the mode-10 gain_B surface is EXACTLY STOCK "
          "⇒ the entire dose comes from the two `sar` immediates, which are speed-INDEPENDENT.")
    print(f"    ✅ delivered lane multiplier = 2.000000x everywhere, under EVERY branch of the gain")
    print("       priority chain and EVERY mode -- that is precisely why V62 chose the shift.")
    print("    🛑 COST, RESTATED: V70 tapered to EXACTLY 1.000000x at and above 50 km/h. V71 does NOT.")
    print("       Score grind #2 at speed separately; the walk-back lever is these two bytes.")

    # ---- saturation, per branch of the priority chain --------------------------------------------
    print("\n  SATURATION -- |dtorque| at which r24's lane output reaches its +/-0x2000 clip,")
    print("  for EVERY branch of the 0x3ABFA-0x3AC18 priority chain (repo-recorded max |dtorque| 839):")
    peak_lerp = max(V69.gain_q10(code, v, r) for v, r in grid)
    min_lerp = min(V69.gain_q10(code, v, r) for v, r in grid)
    branches = [("gp-0x671d != 0  -> cal 0xC6442", u16(code, 0xC6442), "bit6"),
                ("lp != 0         -> cal 0xC6446", u16(code, 0xC6446), "DEAD (0 writers)"),
                ("gp-0x671a >= 5  -> cal 0xC6440", u16(code, 0xC6440), "bit3"),
                ("else the mode-10 LERP (max)", peak_lerp, "bit6=0 and bit3=0"),
                ("else the mode-10 LERP (min)", min_lerp, "bit6=0 and bit3=0")]
    print(f"    {'branch':<38} {'gain':>6}  {'rail |dtorque|':>14}  {'margin':>7}  probe")
    worst = None
    for what, gain, bit in branches:
        rail = r24_rail(gain, 9)
        worst = rail if worst is None else min(worst, rail)
        flag = "  🛑 BELOW 839" if rail < 839 else ""
        print(f"    {what:<38} {gain:>6}  {rail:>14}  {rail / 839:>6.2f}x  {bit}{flag}")
    assert worst > 839, "a branch of the priority chain rails BELOW the repo-recorded max |dtorque| 839"
    assert 5120 * peak_lerp < 2 ** 31, "dtorque_clamp * peak gain overflows int32"
    print(f"    ✅ every branch rails ABOVE 839 (worst {worst}, margin {worst / 839:.2f}x). "
          f"5120 x {peak_lerp} = {5120 * peak_lerp / 2**31 * 100:.2f}% of INT32_MAX.")

    # ---- bit4's PREDICTED SENSITIVITY, re-derived from the images rather than quoted -------------
    print("\n  bit4's THRESHOLD in |dtorque| (= 512 x 2^sar / gain), V71 vs V70, on the LERP branch:")
    v70img = Path(SRC_BIN).read_bytes()
    print(f"    {'operating point':<36} {'V70 thr':>8} {'V71 thr':>8}   V71 is")
    for nm, kmh, rk in (("creep 0 km/h, rateKey 0", 0.0, 0),
                        ("grind #1 op pt 7.2 km/h, rk 603", 7.2, 603),
                        ("grind #2 creep 7.2 km/h, rk 1206", 7.2, 1206),
                        ("engaged highway 93 km/h, rk 300", 93.0, 300)):
        counts = int(kmh * 64.0625)
        t70 = 512 * 1024 / V69.gain_q10(v70img, counts, rk)
        t71 = 512 * 512 / V69.gain_q10(code, counts, rk)
        assert t71 <= t70 + 1e-9, f"bit4 is LESS sensitive than V70's rung at {nm}"
        verdict = "IDENTICAL" if abs(t71 - t70) < 1e-9 else f"{t70 / t71:.2f}x MORE sensitive"
        print(f"    {nm:<36} {t70:>8.1f} {t71:>8.1f}   {verdict}")
    print("    ⇒ bit4 is NOWHERE less sensitive than V70's rung, and up to 2x more off the")
    print("      breakpoints. A null here is therefore STRONGER evidence than V70's null was.")
    print("    ⚠ RESIDUAL, carried from V62 unchanged and NOT re-argued here: avg(gp-0x69a4) --")
    print("      r26's slope factor -- still has an UNMEASURED magnitude, so r26's own rail is not")
    print("      bounded the way r24's is. V62 and V65 both flew this exact configuration.")

    # ---- CRC -------------------------------------------------------------------------------------
    touched = [CAVE_BASE, RATCHET_ADDR, R26_SAR, R24_SAR, SURFACE[0][0], SURFACE[-1][0]]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  CRC -- {len(blocks)} block(s) move relative to the V70 source:")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        tag = "unchanged" if old == new else "RECOMPUTED"
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}  ({tag})")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")
    assert struct.unpack_from("<I", code, 0xD2FFC)[0] == struct.unpack_from("<I", v62, 0xD2FFC)[0], \
        "the 0xD2000 block CRC does not match V62's -- the surface revert is incomplete"
    print("    ✅ the 0xD2000-block CRC now EQUALS V62's = machine proof the surface revert is exact")

    # ---- ✅ THE DEFINING IDENTITY, and the full attributed diff ---------------------------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    surf_bytes = {a + k for a, _, _, _ in SURFACE for k in (0, 1)}
    code_bytes = {RATCHET_ADDR, R26_SAR, R24_SAR}

    d70 = [i for i in range(START, END) if code[i] != v70[i]]
    f70 = [d for d in d70 if d not in crc_only]
    stray = [d for d in f70 if d not in cave_range | surf_bytes | code_bytes]
    assert not stray, f"UNATTRIBUTED functional bytes vs V70: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V70: {len(d70)} bytes = {len(f70)} functional + {len(d70) - len(f70)} CRC")
    for d in sorted(f70):
        where = ("EDIT 4 cave" if d in cave_range else
                 "EDIT 3 surface (x2 -> STOCK)" if d in surf_bytes else
                 "EDIT 1 ratchet 0x454FE" if d == RATCHET_ADDR else "EDIT 2 sar 0xa -> 0x9")
        print(f"    0x{d:05X}  {v70[d]:02X} -> {code[d]:02X}   {where}")

    d62 = [i for i in range(START, END) if code[i] != v62[i]]
    f62 = [d for d in d62 if d not in crc_only]
    stray62 = [d for d in f62 if d not in cave_range | {RATCHET_ADDR}]
    assert not stray62, f"V71 differs from V62 outside the cave and 0x454FE: {[hex(x) for x in stray62]}"
    print(f"\n  ✅✅ EXACT DIFF vs V62: {len(d62)} bytes = the 68-byte cave + 0x{RATCHET_ADDR:05X} + "
          f"{len(d62) - len(f62)} CRC bytes, AND NOTHING ELSE.")
    print("      ⇒ V71 IS V62's FLOWN RATE LANE PLUS V42's FLOWN RATCHET BYTE PLUS A NEW PROBE.")

    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes in [0x{START:X},0x{END:X}) -- run "
          "`python diff_build_vs_stock.py v71` for the full attribution table.")

    # ---- write, encode, and RE-RUN every gate on the DECODED READBACK ---------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT _v71_plain_image.bin already exists "
            f"(on disk {hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). A same-number re-cut destroyed a "
            "predecessor's snapshot once already and produced an artefact NO gate could check. "
            "Rename or delete the existing file deliberately, then re-run.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)
    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(encode)])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V71 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v70)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    print("\n  READBACK -- decoded from the .rwd and re-gated:")
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    assert_ratchet_edit(dec, "V71 readback", expect_edited=True)
    assert_no_external_entry(dec)
    assert_governor_monitor_safety(dec, "V71 readback")
    assert_sar_sites(dec, "V71 readback", expect_doubled=True)
    for addr, _old, new, name in SURFACE:
        assert u16(dec, addr) == new, f"readback {name} wrong"
    for base, ys in REC_Y_STOCK.items():
        assert bytes(dec[base:base + 0x14]) == bytes(stock[base:base + 0x14]), \
            f"readback gain_B record 0x{base:05X} is not STOCK"
    assert dec[CAVE_BASE + 2] == W_LIVE, "readback liveness immediate wrong"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_census(bytes(dec), cave_span)
    assert (dec[REPOINT_BYTE], u16(dec, ARM_ADDR)) == (GATE_DEAD, ARM_STOCK), "readback control path"
    for a in NEIGHBOURS:
        assert bytes(dec[a:a + 20]) == bytes(stock[a:a + 20]), "readback neighbour moved"
    for lo_s, hi_s, _what in RATE_LANE_SPANS:
        assert bytes(dec[lo_s:hi_s]) == bytes(v62[lo_s:hi_s]) == bytes(v65[lo_s:hi_s]), \
            f"readback rate-lane span [0x{lo_s:05X},0x{hi_s:05X}) is not V62/V65-identical"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v70[i] and i not in cave_range | surf_bytes | code_bytes | crc_only]
    assert not rb_stray, f"readback differs from V70 outside the attributed set: {rb_stray[:8]}"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    print("    ✅ payload, the ratchet byte (decoded as a Bcond, target re-checked), both `sar`")
    print("       halfwords, all four surface halfwords, all four gain_B records == STOCK, the WHOLE")
    print("       68-byte cave, the probe census (GATE 1 re-measured), the control path, every")
    print("       neighbour, the V62/V65 rate-lane identity, the no-external-entry scan, identity to")
    print("       V70 outside the attributed set, and the full CRC chain -- all ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V71 BUILT. Both confirmed fixes restored; the falsified surface dose dropped;")
    print("  a 5-rung probe that reads WHICH GAIN IS IN FORCE rather than a lane output.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
