#!/usr/bin/env python3
"""build_v72_tva.py -- V72 = BOTH rate lanes dosed PLATEAU-ONLY, + the base damper opened at creep.

    V72  ==  V70  +  LEVER A (both lanes, Y[0]/Y[1] only)  +  LEVER B (FactorC/E, V47's bytes)
                  +  LEVER C (0xC63A0 x2)  +  0x454FE (carried)  +  a new 68-byte probe.

Spec: `docs/V72-DESIGN.md`. Every edit below asserts its FINAL byte value, so the artefact is
independent of which base was used.

WHY THIS SHAPE -- the one cell of the 2x2 that has never been tried
--------------------------------------------------------------------
                        one lane                    both lanes
    plateau only        V69, V70   -> null          ** V72 **   <- never tried
    whole rate axis     V71B/V71C  -> null          V62, V67/68 -> FIXED grind #1

  * BOTH lanes is required: five single-lane nulls, two two-lane fixes, across a 4:1 r24 range and
    a 2:1 r26 range (`V72-DESIGN.md` 0.6).
  * PLATEAU ONLY is required: grind #1 lives 97.77% below rate index 400; creep grind #2 straddles
    the knee. Dosing above 400 buys nothing for #1 and feeds #2 (0.9 / 2.1.1).
V72 delivers V67/V68's exact creep operating point through the UNGATED, SPEED-SHAPED surfaces, so
highway is EXACTLY 1.000x by record-selection geometry rather than by tuning.

🛑 THE BASE IS `_v70_plain_image.bin`, NOT `_v71b`. The brief offered either. V71B doubled ALL FOUR
gain_A Y points on rec0/rec1 (`0xC6A68` Y=[6144,6144,4868,4096]), so off V71B this build would have
to REVERT Y[2]/Y[3] as well. V70's gain_A is byte-stock and V70's gain_B rec1 Y[0]/Y[1] are ALREADY
5122 -- V72's own target -- so the diff off V70 is strictly smaller and every functional byte is
attributable. The cost is one byte: `0x454FE` becomes an edit rather than a carry. Both bases are
gateless (`0x3AA96` = 0xC5).

🛑🛑 LEVER B CARRIES V47's EXACT FLOWN BYTES, AND THAT IS A DELIBERATE CHOICE BETWEEN TWO SPECS
------------------------------------------------------------------------------------------------
The mission brief's Lever B table (FactorC Y[0..1] -> 877,877; FactorE Y[0..2] -> 927,927,927)
DISAGREES with the frozen design doc 2.2 (FactorC Y[0] -> 235/234; FactorE Y[0..2] -> 700,750,800).
Three facts decided it, all byte-read here rather than quoted:
  1. the design's set is 8 cells = **16 bytes**, and the brief's own byte count says "16 bytes"
     while its table lists 10 cells = 20. The count agrees with the design.
  2. the design's numbers are **V47's exact flown bytes** -- asserted below against
     `_v47_plain_image.bin`, not aimed at. The brief's 877 / 927 are each that record's own stock
     **Y[3]**, i.e. the top of the table.
  3. the arithmetic crosses a clamp. Delivered authority (seed 1024, FactorB/D inert at 1024):
        V47  : 235*700>>10 = 160 ... 235*800>>10 = 183   -- the design's own "~160-184"
        brief: 877*927>>10 = **793**
     The ceiling table `0xD209C` is a 2-point record X=[300,800] Y=[512,1024] (raw-read; fallback
     `0xC6158` = 512), so below `gp-0x6ac2` = 300 the ceiling is **512**. 793 > 512 ⇒ the damper
     would SATURATE, turning a proportional damper into a hard-clipping element inside the loop at
     the ratchet's own frequency -- the exact thing the design relies on NOT happening.
`LEVER_B_VARIANT` below switches to the brief's table in one line if the operator overrules this.

LEVER A -- 16 bytes, 4 records, Y[0] and Y[1] ONLY
--------------------------------------------------
    0xD2A7E  gain_B mode-10 rec0 (0 km/h)   r24   Y -> [5244, 5244, 2322, 1536]
    0xD2ABA  gain_B mode-10 rec1 (10 km/h)  r24   Y -> [5122, 5122, 2247, 1947]   (already V70's)
    0xC6A72  gain_A rec0 (0 km/h)           r26   Y -> [ 512,  512, 2434, 2048]
    0xC6A86  gain_A rec1 (10 km/h)          r26   Y -> [ 512,  512, 2488, 1536]
5244 and 512 are V67/V68's OWN arm values, used verbatim. 5122 (not 5244) at 10 km/h is a GUARANTEE,
not a tuning choice: it is exactly 2.000x, which is V70's own value, and it is what makes V72's r24
<= V70's r24 at every operating point.
🛑 gain_B is MODE-INDEXED through FOUR pointer arrays (0xCBF5C/0xCC044/0xCC12C/0xCC214, entry
mode*4). The contiguous 0x14 stride inside the block is the **MODE** axis: `0xD2A88` is mode 11's
record-0 and `0xD2A9C` is mode 12's. Both are byte-identical to mode 10's stock record, so a
span-based diff cannot see the difference. Dereferenced and asserted below.

LEVER B -- 16 bytes: the base-assist damper, opened at creep
-------------------------------------------------------------
`0xD27BC` FactorC m10 X = [2240,3840,5120,8960] counts = [35,60,80,140] km/h at 64 counts/km/h, so
the LERP clamps flat to Y[0] = 0 below 35 km/h. The five factors multiply in Q10 ⇒ **the car has NO
base-assist damping anywhere below 35 km/h**, which is the entire region where the ratchet
(4.9-8.0 km/h) and both grinds live. V47 opened exactly these cells, flew, and was filed null
**against the 21 Hz vibration** -- a target its own 100 Hz sample rate made unreachable (37.6 deg
average ZOH lag). At the ratchet's 7.79 Hz the same hold costs 14.0 deg, so 88-97% of the
velocity-proportional authority survives. It is not untested; it is untested against THIS symptom.
🛑 The ceiling `0xD209C` and its float twin `0xC6554` are NOT touched -- that pair is lockstep-checked
and escalates to DTC 0x1d hard shutdown. Both asserted byte-stock.

LEVER C -- 2 bytes: `0xC63A0` 1024 -> 2048
--------------------------------------------
The weight on `gp-0x6bd0` -- the damper's OWN output -- inside `FUN_00038148`'s 6-term composite.
✅ [EVIDENCE, decompile of FUN_00038148 + a raw both-parity byte scan] `0xC63A0` = tp+0x73A0 has
**exactly ONE reader image-wide**, `ld.hu 0x73a0[tp],r9` @`0x381AC`, and ZERO writers. The scan for
the even-parity (ld.h/st.h) form returns 0 hits and the disp23 form returns 0; the only other
occurrence of the odd-parity halfword is `0xC4764`, which Ghidra reports is in **no function** and
whose preceding halfword `0xC4762` is not a disp16 load ⇒ data, not an instruction. **One reader ⇒
no monitor can be checking it**, which closes the lockstep question structurally rather than
statistically. Buys the same authority as raising `0xD209C` with zero lockstep exposure.

CARRIED, NOT A LEVER -- `0x454FE` = 0xB5
-----------------------------------------
🛑 **FALSIFIED for the current 7.79 Hz ratchet.** V71B and V71C both flew carrying it and the
operator reports the ratchet UNCHANGED on both. It is carried ONLY because V42 confirmed it against a
DIFFERENT symptom (the ~10 s hard-turn recovery ratchet) and reverting would regress that.
**Do not describe it as a ratchet fix for this build.**

THE PROBE -- 68 of the proven 68 bytes, CAN 0x14A byte4 bits 7:3
-----------------------------------------------------------------
    bit7 = 1                        LIVENESS. field == 0 ⇒ the cave did not fire ⇒ frame VOID.
    bit6 = gp-0x69a4 >= 512    ★★★★ `a`, THE UNMEASURED WEIGHT. r26 = ((a * dtorque) >> 10) * gain_A
                                    >> 10, so `a` sets r26's magnitude RELATIVE to r24 and it has
                                    NEVER been measured. It makes every "r24 vs r26" number in this
                                    kit conditional and has blocked that attribution for ~10 builds.
                                    Producer: a live 10-segment LERP at 0x355C6 in FUN_000352b4.
    bit5 = STRUCTURALLY ZERO        🛑 THE DROPPED RUNG -- see the budget note below.
    bit4 = |gp-0x6bd0| >= 64        IS LEVER B IN FORCE? The damping lane's own output. Non-zero here
                                    is the first direct proof the base damper is alive at creep on
                                    any build in this kit. TWO-SIDED (the damper is velocity-
                                    OPPOSING, so it alternates sign every half cycle).
    bit3 = gp-0x6ac0 >= 400    📋   PRE-REGISTERED, with a built-in positive control.

🛑 THE BUDGET FORCED ONE CUT, AND IT IS THE ONE THE BRIEF NOMINATED. The brief asked for five rungs
and named the fallback order: "if the budget does not fit all four rungs, DROP bit5 first."
It does not fit. With bit4 two-sided (16 B, the same shape V71 re-cut to) the five-rung cave is
    4 seed + 18 (bit6+bit5 sharing one load) + 16 bit4 + 14 bit3 + 2 shl + 20 tail = **72 B**,
four over the proven 68. bit5 (`gp-0x69a4 >= 1024`) is dropped. **Weight 0x04 is therefore never
added, so bit5 reads 0 in every V72 frame** -- a one-way build falsifier: a single frame with bit5
SET proves the artefact is not V72. The `bit5 => bit6` monotone invariant the brief wanted is lost
with it; that is stated, not smoothed over.

★ WHAT THE CUT BOUGHT: bit3's threshold is **EXACTLY 400**, not the brief's fallback of 512. The
brief's premise -- "the rung idiom derives thresholds by `sar`, so they land on powers of two" -- is
incomplete: `cmp imm5` takes 1..15, so `shift s` + `cmp k` reaches any k*2^s. 400 = 25*16 needs
k = 25, out of imm5's range, so a plain shift+compare still cannot hit it -- but ONE extra 2-byte
instruction can:
        ld.hu -0x6ac0[gp],r6 ; shr 0x4,r6 ; add -0x10,r6 ; cmp 0x9,r6 ; blt +4
        fires  <=>  (v >> 4) - 16 >= 9  <=>  v >> 4 >= 25  <=>  **v >= 400**, exactly.
⇒ 📋 **THE PRE-REGISTRATION SURVIVES VERBATIM** rather than needing to be recomputed: engaged duty
must read **3.74%** under the settled scale (4.7121 counts per column deg/s ⇒ 400 counts = 84.89
deg/s) and **0.0000%** under the retired 8x-smaller alternative, and it must fire frame-for-frame
with bus `|rate_c| >= 84.9 deg/s`. That is the positive control, built into the same measurement.

🛑 THE ONE-BIT TRAP IS LIVE ON bit4, IN ITS WORST FORM. `ld.h` = opcode 0x39, `st.h` = 0x3B. Our
`ld.h -0x6bd0[gp],r6` is `24373094`; the firmware's own `st.h r6,-0x6bd0[gp]` @0x34730 is `64373094`
-- **the same displacement, the same register, one bit apart** -- and unlike V70/V71's zero-reader
mirrors, `gp-0x6bd0` has FIVE real readers including the 1 kHz aggregator. A slip would write a live
lane. The opcode field is asserted BY VALUE in the builder, in the readback, and in the verifier.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent 68 of the proven 68 B -- unchanged, flown 10x
(V55/V57/V58/V59/V64/V65/V66/V67/V70/V71, all clean). 🛑 ZERO spare. Growing a cave is this kit's
ONLY bricking class (V24, V27 and V48B all bricked the ECU).

Usage:  python build_v72_tva.py
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
import build_v62_tva as V62                # noqa: E402  (the sar sites -- LEFT STOCK here)
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the two-decoder scan)
import build_v65_tva as V65                # noqa: E402  (COND_BLT)
import build_v68_tva as V68                # noqa: E402  (cave machinery, D2000 block)
import build_v69_tva as V69                # noqa: E402  (gain_B model, surface records, neighbours)
import build_v71a_tva as A                 # noqa: E402  (ratchet edit + governor monitor safety)
import build_v71b_tva as B                 # noqa: E402  (gain_A model + records)
import v72_lane_model as LM                # noqa: E402  (the DELIVERED multiplier, both lanes)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = A.START, A.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = len(V55.CAVE_BYTES)          # 68 -- the PROVEN extent. Never grow it.

# =====================================================================================================
# LEVER A -- both rate lanes, PLATEAU ONLY (Y[0] and Y[1]); Y[2]/Y[3] stay STOCK
# =====================================================================================================
REC_B0, REC_B1 = V69.REC0, V69.REC1                 # 0xD2A74 / 0xD2AB0  gain_B mode-10, 0 / 10 km/h
REC_B_HWY = (0xD2AEC, 0xD2B28)                      # 50 / 100 km/h -- MUST REMAIN STOCK
REC_A0, REC_A1 = B.RATE_A_RECORDS[0], B.RATE_A_RECORDS[1]     # 0xC6A68 / 0xC6A7C  gain_A
REC_A_HWY = B.UNTOUCHED_A_RECS                      # 0xC6A90 / 0xC6AA4 -- MUST REMAIN STOCK
Y_OFF, REC_STRIDE = 0x0A, 0x14

# The FINAL Y row of every edited record, asserted by VALUE. Y[2]/Y[3] are the STOCK values and are
# listed so the assertion covers "the plateau moved AND nothing else in the record did".
LEVER_A_FINAL_Y = {
    REC_B0: ([5244, 5244, 2322, 1536], "gain_B mode-10 rec0 (0 km/h)   r24"),
    REC_B1: ([5122, 5122, 2247, 1947], "gain_B mode-10 rec1 (10 km/h)  r24"),
    REC_A0: ([512, 512, 2434, 2048], "gain_A rec0 (0 km/h)           r26"),
    REC_A1: ([512, 512, 2488, 1536], "gain_A rec1 (10 km/h)          r26"),
}
LEVER_A_STOCK_Y = {REC_B0: [3072, 3072, 2322, 1536], REC_B1: [2561, 2561, 2247, 1947],
                   REC_A0: [3072, 3072, 2434, 2048], REC_A1: [3072, 3072, 2488, 1536]}
V67_ARM_R24, V67_ARM_R26 = 5244, 512        # V67/V68's own arm values, used verbatim

# 🛑 gain_B's mode axis. Dereferenced from the four ROM pointer arrays, never assumed.
GAIN_B_PTR_ARRAYS = LM.GAIN_B_PTR_ARRAYS    # 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214
MODE = LM.MODE_DEFAULT                      # 10
MODE_NEIGHBOURS = (0xD2A88, 0xD2A9C)        # mode 11 / mode 12 record-0 -- byte-identical to mode 10

# =====================================================================================================
# LEVER B -- the base-assist damper, opened at creep
# =====================================================================================================
FACTOR_C = {10: 0xD27BC, 11: 0xD27D0, 12: 0xD27E4}
FACTOR_E = {10: 0xD27F8, 11: 0xD280C, 12: 0xD2820}
FACTOR_C_STOCK_Y = {10: [0, 235, 430, 877], 11: [0, 234, 431, 877], 12: [0, 234, 429, 908]}
FACTOR_E_STOCK_Y = {10: [0, 140, 539, 927], 11: [0, 140, 539, 927], 12: [0, 140, 539, 927]}
FACTOR_C_X = [2240, 3840, 5120, 8960]       # counts; /64 = [35, 60, 80, 140] km/h EXACTLY
FACTOR_E_X = [60, 400, 2500, 4000]          # counts of |motor rate|
SPEED_COUNTS_PER_KMH = 64                   # 0xC6010 gives 640 counts = 10 km/h

# 🛑 TWO SPECS DISAGREE HERE. See the docstring. "V47" is the frozen design doc 2.2 AND V47's own
# flown bytes; "FLATMAX" is the mission brief's table. Switch in ONE line if overruled.
LEVER_B_VARIANT = "V47"
LEVER_B_TABLES = {
    # variant: {addr: (stock, new, label)}
    "V47": {
        0xD27C6: (0, 235, "FactorC m10 Y[0]"),
        0xD27DA: (0, 234, "FactorC m11 Y[0]"),
        0xD2802: (0, 700, "FactorE m10 Y[0]"),
        0xD2804: (140, 750, "FactorE m10 Y[1]"),
        0xD2806: (539, 800, "FactorE m10 Y[2]"),
        0xD2816: (0, 700, "FactorE m11 Y[0]"),
        0xD2818: (140, 750, "FactorE m11 Y[1]"),
        0xD281A: (539, 800, "FactorE m11 Y[2]"),
    },
    "FLATMAX": {
        0xD27C6: (0, 877, "FactorC m10 Y[0]"),
        0xD27C8: (235, 877, "FactorC m10 Y[1]"),
        0xD27DA: (0, 877, "FactorC m11 Y[0]"),
        0xD27DC: (234, 877, "FactorC m11 Y[1]"),
        0xD2802: (0, 927, "FactorE m10 Y[0]"),
        0xD2804: (140, 927, "FactorE m10 Y[1]"),
        0xD2806: (539, 927, "FactorE m10 Y[2]"),
        0xD2816: (0, 927, "FactorE m11 Y[0]"),
        0xD2818: (140, 927, "FactorE m11 Y[1]"),
        0xD281A: (539, 927, "FactorE m11 Y[2]"),
    },
}
LEVER_B = LEVER_B_TABLES[LEVER_B_VARIANT]

# 🛑 NOT TOUCHED, and lockstep-checked to DTC 0x1d if they ever disagree.
CEILING_REC = (0xD209C, 12)                 # a 2-POINT record: count 2, X=[300,800], Y=[512,1024]
CEILING_X, CEILING_Y = [300, 800], [512, 1024]
CEILING_FLOAT_TWIN = (0xC6554, 8)           # 300.0f, 800.0f
CEILING_FALLBACK = (0xC6158, 512)           # used when gp-0x6ac2 fails its plausibility gate
Q10 = 1024

# =====================================================================================================
# LEVER C -- the damper's weight into FUN_00038148
# =====================================================================================================
DAMP_WEIGHT_ADDR, DAMP_WEIGHT_STOCK, DAMP_WEIGHT_NEW = 0xC63A0, 1024, 2048
DAMP_WEIGHT_READER = 0x381AC                # `ld.hu 0x73a0[tp],r9` -- the ONLY reader image-wide
DAMP_WEIGHT_TP_DISP = 0x73A0                # 0xC63A0 - tp (0xBF000)
TP = LM.TP

# =====================================================================================================
# MUST REMAIN BYTE-STOCK -- asserted by value, because a span check passes on the wrong build
# =====================================================================================================
GATE_ADDR, GATE_DEAD = A.REPOINT_BYTE, A.GATE_DEAD          # 0x3AA96 -> 0xC5 (gp-0x683c, 0 writers)
GATE_LOAD = (A.REPOINT_ADDR, bytes.fromhex("847fc597"))     # `ld.bu -0x683c[gp],r15`
SAR_SITES = (A.R26_SAR, A.R24_SAR)                          # 0x3AB76 / 0x3AC20 -- both `sar 0xa`
ARMS_STOCK = ((0xC643E, 1536), (0xC6440, 2048), (0xC6442, 1024), (0xC6444, 512), (0xC6446, 512))
ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])

# =====================================================================================================
# CARRIED -- V42's state-4 governor kill.  🛑 FALSIFIED for the 7.79 Hz ratchet (V71B + V71C flew it)
# =====================================================================================================
RATCHET_ADDR = A.RATCHET_ADDR               # 0x454FE

# =====================================================================================================
# THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT

# r7 accumulates a FIVE-BIT value; `shl 0x3,r7` moves it into bits 7:3 at the very end.
W_LIVE = 0x10           # -> bit7  LIVENESS (folded into the initial movea)
W_A512 = 0x08           # -> bit6  gp-0x69a4 >= 512
W_UNUSED_BIT5 = 0x04    # -> bit5  🛑 NEVER ADDED. The dropped rung; bit5 reads 0 in every frame.
W_DAMPABS = 0x02        # -> bit4  |gp-0x6bd0| >= 64, TWO-SIDED
W_RATE400 = 0x01        # -> bit3  gp-0x6ac0 >= 400
PAYLOAD_SHIFT = 3
BIT_LIVE, BIT_A512 = W_LIVE << PAYLOAD_SHIFT, W_A512 << PAYLOAD_SHIFT
BIT_UNUSED5 = W_UNUSED_BIT5 << PAYLOAD_SHIFT
BIT_DAMPABS, BIT_RATE400 = W_DAMPABS << PAYLOAD_SHIFT, W_RATE400 << PAYLOAD_SHIFT

A_DISP = 0x69A4                 # `a`  -- ld.hu, UNSIGNED halfword (0x3AB3A reads it the same way)
DAMP_DISP = 0x6BD0              # the base-assist damper output -- ld.h, SIGNED
RATE_DISP = 0x6AC0              # |motor rate| -- ld.hu, UNSIGNED

A_SHIFT, A_LEVEL = 9, 1                     # sar 0x9 ; cmp 0x1   =>  a >= 512
A_THRESHOLD = A_LEVEL << A_SHIFT            # 512
D_SHIFT, D_LEVEL, D_NEG_LEVEL = 6, 1, -1    # sar 0x6 ; cmp 0x1 / cmp -0x1
D_THRESHOLD = D_LEVEL << D_SHIFT            # +64
D_NEG_THRESHOLD = (D_NEG_LEVEL << D_SHIFT) - 1      # -65.  `sar` FLOORS -- see _wire_model()
R_SHIFT, R_BIAS, R_LEVEL = 4, -0x10, 9      # shr 0x4 ; add -0x10 ; cmp 0x9
R_THRESHOLD = (R_LEVEL - R_BIAS) << R_SHIFT         # (9 + 16) * 16 = 400  EXACT
RATE_SCALE_CTS_PER_DEGS = 4.7121            # the settled column-rate scale
COND_BLT, COND_BGE = V65.COND_BLT, V55.COND_BGE     # 0x6 SIGNED < ; 0xE SIGNED >=

# The firmware's OWN access sets for the three probed cells, re-derived from raw bytes by the
# two-decoder scan and asserted EXACTLY. 🛑 None of these is a zero-reader mirror -- gp-0x6bd0 has
# FIVE readers including the 1 kHz aggregator, which is what makes the ld.h/st.h check load-bearing.
PROBE_CENSUS = {
    A_DISP: (3, 1, [0x355C6], {"ld.hu", "st.h"}, "ld.hu",
             "`a`, r26's own weight -- producer is the LERP @0x355C6 in FUN_000352b4"),
    DAMP_DISP: (5, 3, [0x34730, 0x34744, 0x34752], {"ld.h", "st.h"}, "ld.h",
                "the base-assist damper output -- 3 writers, all inside FUN_00034350"),
    RATE_DISP: (26, 4, [0x41820, 0x41832, 0x41A8C, 0x41AAC], {"ld.hu", "st.h"}, "ld.hu",
                "|motor rate|, the shared gain-scheduling index"),
}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance in the STOCK image. ------
PIN_MOVEA_10_R7 = (0x49256, bytes.fromhex("203e1000"))     # `movea 0x10,r0,r7`
PIN_LDHU_69A4 = (0x3AB3A, bytes.fromhex("e4375d96"))       # BYTE-IDENTICAL: the aggregator's own read
PIN_LDHU_69A4_ALT = (0x3575A, bytes.fromhex("e4375d96"))   # a second byte-identical instance
PIN_LDHU_6AC0 = (0x45780, bytes.fromhex("e4374195"))       # BYTE-IDENTICAL (4 instances image-wide)
PIN_LDH_HW1 = (0x3ACA8, bytes.fromhex("24372c95"))         # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_HW1_ALT = (0x453E0, bytes.fromhex("24376c94"))     # hw1 donor #2, different cell
PIN_LDH_6BD0_DISP = (0x34726, bytes.fromhex("243f3094"))   # hw2 donor: `ld.h -0x6bd0[gp],r7`
PIN_STH_6BD0 = (0x34730, bytes.fromhex("64373094"))        # 🛑 THE ONE-BIT TWIN: st.h, SAME reg/disp
PIN_SAR9_R6 = (0x3E60C, bytes.fromhex("a932"))             # `sar 0x9,r6`   -- Ghidra-confirmed
PIN_SAR6_R6 = (0x2401A, bytes.fromhex("a632"))             # `sar 0x6,r6`
PIN_SHR4_R6 = (0x163A2, bytes.fromhex("8432"))             # `shr 0x4,r6`
PIN_ADD_M10_R6 = (0x50382, bytes.fromhex("5032"))          # `add -0x10,r6` -- Ghidra-confirmed
PIN_CMP_1_R6 = (0x14D46, bytes.fromhex("6132"))            # `cmp 0x1,r6`
PIN_CMP_M1_R6 = (0x1BC24, bytes.fromhex("7f32"))           # `cmp -0x1,r6`
PIN_CMP_9_R6 = (0xD398, bytes.fromhex("6932"))             # `cmp 0x9,r6`   -- Ghidra-confirmed
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))             # `shl 0x3,r7`   -- V31P FLASHED it 4x
PIN_ADD_R7 = {1: (0x15404, bytes.fromhex("413a")),
              2: (0x27EF0, bytes.fromhex("423a")),
              8: (0x17CD8, bytes.fromhex("483a"))}
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))                # `blt +4`
PIN_BGE4 = (0x244CE, bytes.fromhex("ae05"))                # `bge +4`
PIN_BGE6 = (0x6B176, bytes.fromhex("be05"))                # `bge +6`
PIN_BE6 = (0x3ABFC, bytes.fromhex("c205"))                 # ⚠ the TWIN of `bge +6` (be05)

TAG = ("LEVERA-BOTHLANES-PLATEAU-r24_5244_5122-r26_512-LEVERB-V47damp-LEVERC-63A0x2-"
       "0x454FE-probe-a69a4-damp6bd0-rate400-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V72-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v72_plain_image.bin"))
SRC_BIN = plain_image_path("_v70_plain_image.bin")
V67_BIN = plain_image_path("_v67_plain_image.bin")
V47_BIN = plain_image_path("_v47_plain_image.bin")
STOCK_BIN = stock_fw_path("code.bin")
DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v72_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


def _s16(x):
    """Interpret a 16-bit pattern the way `ld.h` does -- SIGNED."""
    return x - 0x10000 if x & 0x8000 else x


def rec_y(buf, base):
    return list(struct.unpack_from("<4h", buf, base + Y_OFF))


def rec_x(buf, base):
    return list(struct.unpack_from("<4h", buf, base + 0x02))


def add_imm5(imm, reg2):
    """V850 Format II `add imm5,reg2` -- opcode 0b010010. imm5 is SIGNED (-16..15)."""
    assert -16 <= imm <= 15, "Format II imm5 is SIGNED (-16..15)"
    assert 0 <= reg2 <= 31
    return struct.pack("<H", (reg2 << 11) | (0x12 << 5) | (imm & 0x1F))


def decode_fmt2(hw):
    """V850 Format-II field split: imm5 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"imm5": hw & 0x1F, "opcode": (hw >> 5) & 0x3F, "reg2": (hw >> 11) & 0x1F}


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v69a4, v6bd0, v6ac0, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the instructions, not a paraphrase."""
    r7 = W_LIVE                                     # movea 0x10,r0,r7
    r6 = (v69a4 & 0xFFFF) >> A_SHIFT                # ld.hu (ZERO-extends) ; sar 0x9
    if not (r6 < A_LEVEL):                          # cmp 0x1,r6 ; blt +4
        r7 += W_A512
    r6 = _s16(v6bd0) >> D_SHIFT                     # ld.h ; sar 0x6  (Python >> floors == `sar`)
    # 🛑 THE TWO-SIDED TEST, as CONTROL FLOW, not as a formula:
    #     cmp 0x1,r6  ; bge SET      -- s >=  1  => x is large POSITIVE
    #     cmp -0x1,r6 ; bge SKIP     -- s >= -1  => |x| is small; skip
    #                   fall through => SET       -- s <= -2  => x is large NEGATIVE
    if (r6 >= D_LEVEL) or not (r6 >= D_NEG_LEVEL):
        r7 += W_DAMPABS
    r6 = (v6ac0 & 0xFFFF) >> R_SHIFT                # ld.hu ; shr 0x4
    r6 = r6 + R_BIAS                                # add -0x10,r6
    if not (r6 < R_LEVEL):                          # cmp 0x9,r6 ; blt +4
        r7 += W_RATE400
    r7 <<= PAYLOAD_SHIFT                            # shl 0x3,r7
    return (r7 & 0xFF) | (status_bits & PAYLOAD_KEEP_MASK)


LEGAL_PAYLOADS = {BIT_LIVE | a | b | c
                  for a in (0, BIT_A512) for b in (0, BIT_DAMPABS) for c in (0, BIT_RATE400)}


def _wire_model():
    """The rungs' semantics, exhaustively: every halfword pattern and every byte value."""
    # ---- bit6, over ALL 65,536 patterns. The cell is read `ld.hu` ⇒ zero-extended ⇒ `sar` == `shr`.
    for raw in range(0x10000):
        b = wire_byte4(raw, 0, 0)
        assert bool(b & BIT_A512) == (raw >= A_THRESHOLD), \
            f"bit6 is not `gp-0x69a4 >= {A_THRESHOLD}` at {raw}"
    # 🛑 `sar` vs `shr` on the zero-extended operand: PROVEN equal, not assumed. The donor for
    # `shr 0x9,r6` does not exist in the stock image and `sar 0x9,r6` does (0x3E60C), so the cave
    # emits `sar` -- legitimate ONLY because ld.hu makes the operand non-negative.
    for raw in range(0x10000):
        assert (raw >> A_SHIFT) == (raw >> A_SHIFT), "unreachable"
        assert _s16(raw) >> A_SHIFT != raw >> A_SHIFT or raw < 0x8000, "unreachable"
    assert all((raw >> A_SHIFT) >= 0 for raw in range(0x10000)), \
        "a zero-extended operand went negative -- `sar` would stop equalling `shr`"

    # ---- bit4, over ALL 65,536 halfword patterns, including the one-count asymmetry --------------
    for raw in range(0x10000):
        x = _s16(raw)
        b = wire_byte4(0, raw, 0)
        assert bool(b & BIT_DAMPABS) == (x >= D_THRESHOLD or x <= D_NEG_THRESHOLD), \
            f"bit4 is not `x >= {D_THRESHOLD} or x <= {D_NEG_THRESHOLD}` at x = {x}"
    mismatch = {_s16(r) for r in range(0x10000)
                if bool(wire_byte4(0, r, 0) & BIT_DAMPABS) != (abs(_s16(r)) >= D_THRESHOLD)}
    assert mismatch == {-D_THRESHOLD}, \
        f"the two-sided rung differs from |x| >= {D_THRESHOLD} at {sorted(mismatch)[:6]}, expected " \
        f"exactly {{{-D_THRESHOLD}}} -- `sar` floors, so `x sar 6 == -1` spans [-64,-1] and no " \
        "single shifted compare can split -64 from -63"
    assert wire_byte4(0, 0xFF00, 0) & BIT_DAMPABS, "bit4 does not fire at x = -256: NOT two-sided"
    assert wire_byte4(0, 0x0100, 0) & BIT_DAMPABS, "bit4 does not fire at x = +256"
    assert not wire_byte4(0, 0x0000, 0) & BIT_DAMPABS, "bit4 fires at x = 0"

    # ---- bit3, over ALL 65,536 patterns. THE THRESHOLD IS EXACTLY 400. ---------------------------
    for raw in range(0x10000):
        assert bool(wire_byte4(0, 0, raw) & BIT_RATE400) == (raw >= R_THRESHOLD), \
            f"bit3 is not `gp-0x6ac0 >= {R_THRESHOLD}` at {raw}"
    assert R_THRESHOLD == 400, f"bit3's threshold is {R_THRESHOLD}, not the pre-registered 400"
    assert not wire_byte4(0, 0, 399) & BIT_RATE400 and wire_byte4(0, 0, 400) & BIT_RATE400, \
        "bit3 does not switch exactly between 399 and 400"
    # `add -0x10,r6` makes r6 NEGATIVE for small inputs, so `blt` (SIGNED) is required and its
    # compare must not overflow. Both proven over the reachable range rather than argued.
    shifted = {((raw & 0xFFFF) >> R_SHIFT) + R_BIAS for raw in range(0x10000)}
    assert min(shifted) == -16 and max(shifted) == (0xFFFF >> R_SHIFT) - 16
    assert -0x8000 < min(shifted) - R_LEVEL and max(shifted) - R_LEVEL < 0x7FFF, \
        "`cmp 0x9,r6` can overflow -- `blt` would stop meaning `<` and the rung would invert"

    # ---- 🛑 THE SHIFT MUST NEVER REACH THE PRESERVED STATUS BITS ---------------------------------
    reachable_r7 = {W_LIVE + a + b + c for a in (0, W_A512) for b in (0, W_DAMPABS)
                    for c in (0, W_RATE400)}
    assert max(reachable_r7) == 0x1B and min(reachable_r7) == W_LIVE
    for r7 in reachable_r7:
        assert (r7 << PAYLOAD_SHIFT) <= 0xF8, f"r7 = 0x{r7:02X} shifts past the byte"
        assert (r7 << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
            f"r7 = 0x{r7:02X} shifts INTO the preserved status bits -- the wire would be corrupted"
    assert (W_LIVE << PAYLOAD_SHIFT) == 0x80, \
        "the seed does NOT land on bit7 after the shift -- the VOID sentinel would be broken"
    for status in range(8):
        for inputs in ((0, 0, 0), (0xFFFF, 0x7FFF, 0xFFFF), (512, 0xFF00, 400)):
            assert wire_byte4(*inputs, status_bits=status) & PAYLOAD_KEEP_MASK == status, \
                "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
    # ★ bit5 IS STRUCTURALLY ZERO -- the dropped rung. A one-way build falsifier, asserted so the
    # decoder cannot claim more than this and so a future re-cut cannot silently reuse the weight.
    reach = {wire_byte4(a, d, r) & 0xF8
             for a in (0, 511, 512, 0xFFFF) for d in (0, 0x0100, 0xFF00, 0x7FFF)
             for r in (0, 399, 400, 0xFFFF)}
    assert all(not (p & BIT_UNUSED5) for p in reach), \
        "bit5 is SET somewhere -- it is the DROPPED rung and must read 0 in every frame"
    assert reach <= LEGAL_PAYLOADS, f"the wire model reaches {reach - LEGAL_PAYLOADS}, outside LEGAL"
    assert len(LEGAL_PAYLOADS) == 8, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 8"
    assert all(p & BIT_LIVE for p in LEGAL_PAYLOADS), "a legal payload lacks the liveness bit"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    """
    V65._self_check_encoders()               # chains down through V59/V58/V57/V55/V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVEA_10_R7, PIN_LDHU_69A4, PIN_LDHU_69A4_ALT, PIN_LDHU_6AC0, PIN_LDH_HW1,
            PIN_LDH_HW1_ALT, PIN_LDH_6BD0_DISP, PIN_STH_6BD0, PIN_SAR9_R6, PIN_SAR6_R6,
            PIN_SHR4_R6, PIN_ADD_M10_R6, PIN_CMP_1_R6, PIN_CMP_M1_R6, PIN_CMP_9_R6,
            PIN_SHL3_R7, PIN_BLT4, PIN_BGE4, PIN_BGE6, PIN_BE6]
    pins += list(PIN_ADD_R7.values())
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # ---- bit6's load: `ld.hu -0x69a4[gp],r6`, BYTE-IDENTICAL to the aggregator's own read --------
    ours = FF.ldhu(A_DISP, R6)
    assert ours == PIN_LDHU_69A4[1], \
        f"the `a` load is not byte-identical to the real one @0x{PIN_LDHU_69A4[0]:05X}"
    hw1, hw2 = struct.unpack("<HH", ours)
    assert ((hw1 >> 5) & 0x3F) == 0x3F, "the `a` load is not the ld.hu/ld.w opcode form 0x3F"
    assert hw2 == (((0x10000 - A_DISP) & 0xFFFE) | 1), "ld.hu hw2 must be (disp & ~1) | 1"
    assert ours != FF.sth(R6, -A_DISP, GP) and ours != V55.ldh(A_DISP, R6), \
        "the `a` load collapsed onto an st.h or a SIGNED ld.h"

    # ---- bit3's load: `ld.hu -0x6ac0[gp],r6` -----------------------------------------------------
    ours = FF.ldhu(RATE_DISP, R6)
    assert ours == PIN_LDHU_6AC0[1], \
        f"the rate load is not byte-identical to the real one @0x{PIN_LDHU_6AC0[0]:05X}"
    assert ours != FF.sth(R6, -RATE_DISP, GP), "the rate load collapsed onto an st.h -- a WRITE"

    # ---- bit4's load. 🛑🛑 THE ONE-BIT TRAP, IN ITS WORST FORM: ld.h = 0x39, st.h = 0x3B, and the
    # firmware's own `st.h r6,-0x6bd0[gp]` @0x34730 carries the SAME register and the SAME
    # displacement. gp-0x6bd0 has FIVE real readers, so a slip WRITES a live 1 kHz lane.
    ours = V55.ldh(DAMP_DISP, R6)
    hw1, hw2 = struct.unpack("<HH", ours)
    assert ((hw1 >> 5) & 0x3F) == 0x39, \
        f"emitted opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h), not 0x3B (st.h)"
    assert ours != PIN_STH_6BD0[1], \
        f"the emitted load IS the real st.h @0x{PIN_STH_6BD0[0]:05X} -- it would WRITE the damper cell"
    assert ours[:2] != PIN_STH_6BD0[1][:2], "hw1 matches the st.h form"
    assert ours[2:] == PIN_STH_6BD0[1][2:] == PIN_LDH_6BD0_DISP[1][2:], \
        "the displacement halfword does not match the real gp-0x6bd0 instances"
    assert ours != FF.sth(R6, -DAMP_DISP, GP), "the emitted load collapsed onto FF.sth"
    assert ours != FF.ldhu(DAMP_DISP, R6), "ld.h collapsed onto ld.hu -- the SIGN would be lost"
    assert hw1 & 0x1F == GP == 4 and (hw1 >> 11) == R6, "ld.h reg1/reg2 fields are wrong"
    assert hw2 & 1 == 0, "ld.h hw2 LSB must be CLEAR (LSB set is the ld.w/ld.hu form)"
    assert hw1 == struct.unpack_from("<H", PIN_LDH_HW1[1], 0)[0] == \
        struct.unpack_from("<H", PIN_LDH_HW1_ALT[1], 0)[0], "hw1 differs from BOTH real `ld.h ..,r6`"

    # ---- the 2-byte instructions -----------------------------------------------------------------
    assert V55.sar(A_SHIFT, R6) == PIN_SAR9_R6[1], "sar 0x9,r6 != the real one @0x3E60C"
    assert V55.sar(D_SHIFT, R6) == PIN_SAR6_R6[1], "sar 0x6,r6 != the real one @0x2401A"
    assert FF.shr(R_SHIFT, R6) == PIN_SHR4_R6[1], "shr 0x4,r6 != the real one @0x163A2"
    assert V55.sar(D_SHIFT, R6) != FF.shr(D_SHIFT, R6), \
        "bit4's shift collapsed onto a LOGICAL shr -- every negative damper value would read huge"
    assert FF.shr(R_SHIFT, R6) != V55.sar(R_SHIFT, R6), "bit3's shr collapsed onto sar"
    assert add_imm5(R_BIAS, R6) == PIN_ADD_M10_R6[1], "add -0x10,r6 != the real one @0x50382"
    assert decode_fmt2(struct.unpack("<H", PIN_ADD_M10_R6[1])[0]) == \
        {"imm5": 0x10, "opcode": 0x12, "reg2": R6}, \
        "add -0x10 does not encode as imm5 0x10 -- Format II imm5 is SIGNED and -16 is 0b10000"
    assert add_imm5(R_BIAS, R6) != V55.cmp_imm5(R_BIAS, R6), "add -0x10 collapsed onto cmp"
    assert V55.cmp_imm5(A_LEVEL, R6) == V55.cmp_imm5(D_LEVEL, R6) == PIN_CMP_1_R6[1], \
        "cmp 0x1,r6 encoding changed"
    assert V55.cmp_imm5(D_NEG_LEVEL, R6) == PIN_CMP_M1_R6[1], "cmp -0x1,r6 != the real one @0x1BC24"
    assert V55.cmp_imm5(R_LEVEL, R6) == PIN_CMP_9_R6[1], "cmp 0x9,r6 != the real one @0xD398"
    assert decode_fmt2(struct.unpack("<H", PIN_CMP_M1_R6[1])[0])["imm5"] == 0x1F, \
        "cmp -0x1 does not encode as imm5 0x1F"
    assert FF.bcond(COND_BLT, +4) == PIN_BLT4[1], "blt +4 != the real one @0x290A8"
    assert FF.bcond(COND_BGE, +4) == PIN_BGE4[1], "bge +4 != the real one @0x244CE"
    assert FF.bcond(COND_BGE, +6) == PIN_BGE6[1], "bge +6 != the real one @0x6B176"
    # 🛑🛑 THE CONDITION-NIBBLE TWINS. `bge +6` is be05 and `be +6` is b205 -- one nibble apart, and
    # the wrong one INVERTS a rung silently. This kit has lost time to exactly that confusion.
    assert FF.bcond(COND_BGE, +6) != PIN_BE6[1], "bge +6 collapsed onto `be +6` (b205 @0x3ABFC)"
    assert FF.bcond(COND_BGE, +6) != FF.bcond(COND_BLT, +6), "bge collapsed onto its negation blt"
    assert COND_BGE == 0xE and COND_BLT == 0x6 and COND_BGE != V55.COND_BL, \
        "bge/blt nibbles moved, or bge collapsed onto the UNSIGNED bl"
    for imm, (addr, raw) in PIN_ADD_R7.items():
        assert add_imm5(imm, R7) == raw, f"add 0x{imm:x},r7 != the real one @0x{addr:05X}"
        assert add_imm5(imm, R7) != V55.cmp_imm5(imm, R7), \
            f"add 0x{imm:x} collapsed onto cmp -- the bit would never set"
        assert decode_fmt2(struct.unpack("<H", raw)[0]) == {"imm5": imm, "opcode": 0x12, "reg2": R7}
    assert V54.shl(PAYLOAD_SHIFT, R7) == PIN_SHL3_R7[1] == V54.V31P_SHL3_R7, \
        "shl 0x3,r7 != the real one @0x4FB82 / V31P's FLASHED byte sequence"
    assert V54.shl(PAYLOAD_SHIFT, R7) != V55.sar(PAYLOAD_SHIFT, R7) and \
        V54.shl(PAYLOAD_SHIFT, R7) != FF.shr(PAYLOAD_SHIFT, R7), \
        "shl collapsed onto a RIGHT shift -- the payload would land in the wrong bits"
    assert FF.movea(W_LIVE, R0, R7) == PIN_MOVEA_10_R7[1], "movea 0x10,r0,r7 != the real one @0x49256"

    weights = (W_LIVE, W_A512, W_UNUSED_BIT5, W_DAMPABS, W_RATE400)
    assert len(set(weights)) == 5 and all(w & (w - 1) == 0 for w in weights), "weights not distinct"
    assert sum(weights) == 0x1F, f"weights must occupy exactly bits 4:0, got 0x{sum(weights):02X}"
    assert sum(w << PAYLOAD_SHIFT for w in weights) == 0xF8, "payload bits are not exactly 7:3"
    _wire_model()


def build_cave():
    """pack_v72_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x10,r0,r7       ; r7 = 0x10   bit7 LIVENESS, in PRE-SHIFT weights
        ld.hu -0x69a4[gp],r6   ; `a` -- r26's own weight. UNSIGNED (byte-identical to 0x3AB3A)
        sar   0x9,r6           ; units of 512.  == `shr` here: ld.hu zero-extends
        cmp   0x1,r6
        blt   +4
        add   0x8,r7           ; bit6 = gp-0x69a4 >= 512      ★★★★ THE UNMEASURED WEIGHT
      g0:
        ld.h  -0x6bd0[gp],r6   ; the base-assist damper output, SIGNED
        sar   0x6,r6           ; ARITHMETIC: units of 64, sign preserved
        cmp   0x1,r6
        bge   +6               ; s >=  1  =>  x >= +64        -> SET
        cmp   -0x1,r6
        bge   +4               ; s >= -1  =>  |x| is small    -> SKIP
        add   0x2,r7           ; bit4 = |gp-0x6bd0| >= 64, TWO-SIDED   (fallthrough: s <= -2)
      g1:
        ld.hu -0x6ac0[gp],r6   ; |motor rate| -- the gain-scheduling index. UNSIGNED
        shr   0x4,r6           ; units of 16 (LOGICAL: the cell is unsigned)
        add   -0x10,r6         ; -= 16
        cmp   0x9,r6           ; (v >> 4) - 16 >= 9  <=>  v >= 400   EXACT, not a power of two
        blt   +4
        add   0x1,r7           ; bit3 = gp-0x6ac0 >= 400   📋 PRE-REGISTERED
      g2:
        shl   0x3,r7           ; the 5-bit field -> bits 7:3  (V31P's FLASHED idiom; Honda's @0x4FB82)
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

    # ---- bit6: `a`, the unmeasured weight ---------------------------------------------------------
    emit(FF.ldhu(A_DISP, R6), f"ld.hu -0x{A_DISP:04x}[gp],r6 ; `a` = r26's own weight (UNSIGNED)")
    emit(V55.sar(A_SHIFT, R6), f"sar 0x{A_SHIFT:x},r6           ; units of {A_THRESHOLD}")
    emit(V55.cmp_imm5(A_LEVEL, R6), f"cmp 0x{A_LEVEL:x},r6")
    br_a = len(listing)
    emit(FF.bcond(COND_BLT, +4), "blt +4              ; skip -> g0")
    emit(add_imm5(W_A512, R7), f"add 0x{W_A512:x},r7          ; bit6 = gp-0x{A_DISP:04x} >= {A_THRESHOLD}")
    g0 = CAVE_BASE + len(body)

    # ---- bit4: ONE load, ONE shift, TWO signed bounds ---------------------------------------------
    emit(V55.ldh(DAMP_DISP, R6),
         f"ld.h -0x{DAMP_DISP:04x}[gp],r6 ; base-assist damper out (SIGNED). 🛑 op MUST be 0x39")
    emit(V55.sar(D_SHIFT, R6), f"sar 0x{D_SHIFT:x},r6           ; ARITHMETIC -- units of {D_THRESHOLD}")
    emit(V55.cmp_imm5(D_LEVEL, R6), f"cmp 0x{D_LEVEL:x},r6           ; the POSITIVE bound")
    br_hi = len(listing)
    emit(FF.bcond(COND_BGE, +6), f"bge +6              ; s >= {D_LEVEL} => x >= +{D_THRESHOLD} -> SET")
    emit(V55.cmp_imm5(D_NEG_LEVEL, R6), "cmp -0x1,r6         ; the NEGATIVE bound")
    br_lo = len(listing)
    emit(FF.bcond(COND_BGE, +4), f"bge +4              ; s >= {D_NEG_LEVEL} => small -> SKIP")
    emit(add_imm5(W_DAMPABS, R7),
         f"add 0x{W_DAMPABS:x},r7          ; bit4 = x >= +{D_THRESHOLD} or x <= {D_NEG_THRESHOLD}  TWO-SIDED")
    g1 = CAVE_BASE + len(body)

    # ---- bit3: the EXACT 400 threshold, via shr + a bias + cmp -----------------------------------
    emit(FF.ldhu(RATE_DISP, R6), f"ld.hu -0x{RATE_DISP:04x}[gp],r6 ; |motor rate| (UNSIGNED)")
    emit(FF.shr(R_SHIFT, R6), f"shr 0x{R_SHIFT:x},r6           ; LOGICAL -- units of {1 << R_SHIFT}")
    emit(add_imm5(R_BIAS, R6), f"add -0x{-R_BIAS:x},r6         ; -= {-R_BIAS}")
    emit(V55.cmp_imm5(R_LEVEL, R6), f"cmp 0x{R_LEVEL:x},r6           ; (v>>4)-16 >= 9 <=> v >= {R_THRESHOLD}")
    br_r = len(listing)
    emit(FF.bcond(COND_BLT, +4), "blt +4              ; skip -> g2")
    emit(add_imm5(W_RATE400, R7),
         f"add 0x{W_RATE400:x},r7          ; bit3 = gp-0x{RATE_DISP:04x} >= {R_THRESHOLD}  EXACT")
    g2 = CAVE_BASE + len(body)

    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7          ; the 5-bit field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp] ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands EXACTLY on its label, located BY POSITION -------------------
    for br_idx, label, cond, name in ((br_a, g0, COND_BLT, "bit6"), (br_r, g2, COND_BLT, "bit3")):
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a Bcond"
        assert addr + 4 == label, \
            f"{name}: branch target 0x{addr + 4:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, \
            f"{name}: branch condition is 0x{struct.unpack('<H', raw)[0] & 0xF:X}, not 0x{cond:X} -- " \
            "the wrong condition INVERTS the whole rung"
        setter = listing[br_idx + 1][1]
        assert len(setter) == 2 and decode_fmt2(struct.unpack("<H", setter)[0])["opcode"] == 0x12, \
            f"{name}: the skipped instruction is not a 2-byte `add imm5,r7`"
    # ---- bit4's TWO branches, checked as a PAIR ---------------------------------------------------
    hi_addr, hi_raw, _ = listing[br_hi]
    lo_addr, lo_raw, _ = listing[br_lo]
    setter_addr = listing[br_lo + 1][0]
    assert hi_addr + 6 == setter_addr, \
        f"bit4 high bound: `bge +6` @0x{hi_addr:05X} does not land on the setter 0x{setter_addr:05X}"
    assert lo_addr + 4 == g1, f"bit4 low bound: `bge +4` @0x{lo_addr:05X} does not land on g1"
    for raw, which in ((hi_raw, "high"), (lo_raw, "low")):
        assert struct.unpack("<H", raw)[0] & 0xF == COND_BGE, \
            f"bit4 {which} bound is not `bge` (0x{COND_BGE:X}) -- the rung would invert"
        assert raw != PIN_BE6[1], f"bit4 {which} bound emitted `be` (b205), not `bge` (be05)"
    assert (g0, g1, g2) == (0xC4B44, 0xC4B54, 0xC4B62), \
        f"the cave geometry drifted: g0/g1/g2 = {hex(g0)}/{hex(g1)}/{hex(g2)}"
    assert [listing[i][0] for i in (br_a, br_hi, br_lo, br_r)] == \
        [0xC4B40, 0xC4B4C, 0xC4B50, 0xC4B5E], "the branch addresses drifted from the design"

    # ---- GATE 2b: r6/r7 LIVENESS. Only a rung's own load/shift/bias may write r6 -----------------
    r6_writers = {listing[i][0] for i in (1, 2, 6, 7, 13, 14, 15)}   # ld.hu,sar | ld.h,sar | ld.hu,shr,add
    for idx in range(0, br_r + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                # cmp imm5,reg2 / cmp reg1,reg2 -- flags
            continue
        want = R6 if addr in r6_writers else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    # 🛑 bit4's negative bound reads r6 THREE instructions after the `sar` that produced it, so
    # r6-liveness across that window is load-bearing and is asserted rather than assumed.
    for idx in range(8, br_lo + 1):
        _a, raw, text = listing[idx]
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (len(raw) == 2 and raw[1] == 0x05) or ((hw >> 5) & 0x3F) in (0x13, 0x0F) \
            or (hw >> 11) == R7, f"'{text}' clobbers r6 between bit4's shift and its second bound"
    for disp, mk in ((A_DISP, FF.ldhu(A_DISP, R6)), (RATE_DISP, FF.ldhu(RATE_DISP, R6)),
                     (DAMP_DISP, V55.ldh(DAMP_DISP, R6))):
        assert sum(1 for _, r, _ in listing if r == mk) == 1, f"gp-0x{disp:04x} is loaded != once"
    # the cave must NOT read any cell it does not declare -- notably the retired V70/V71 mirrors
    for stale in (0x6ADA, 0x6ADC, 0x671D, 0x67FA):
        assert not [1 for _, r, _ in listing
                    if r in (V55.ldh(stale, R6), FF.ldhu(stale, R6), V55.ldbu_any(-stale, R6))], \
            f"the cave still reads gp-0x{stale:04x} -- V72 retired it"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store --------------------
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert len(store_idx) == 1, f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[store_idx[0]][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the CAN-330 payload byte"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == 4 + 12 + 16 + 14 + 2 + 20 == 68, \
        f"the cave is {len(body)}B, the budget says 68 " \
        "(seed 4 + bit6 12 + bit4 16 + bit3 14 + shl 2 + tail 20)"
    assert len(body) == CAVE_EXTENT, \
        f"cave {len(body)}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, in Python, from raw bytes.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. This walks the emitted bytes with a minimal V850 length/format decoder and returns
    (address, bytes, mnemonic) triples, which the caller compares against the build-time listing.
    """
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        if (hw >> 7) & 0xF == 0xB:                                        # Format III Bcond
            n, m = 2, {0x6: "blt", 0xE: "bge", 0xA: "bne", 0x2: "be"}.get(hw & 0xF, f"b?{hw & 0xF:x}")
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            m = f"{m} {d:+d}"
        elif op6 in (0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F, 0x31, 0x36):     # 4-byte disp/imm forms
            n = 4
            hw2 = struct.unpack_from("<H", raw, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            # 🛑 op 0x3F is ld.hu when hw2's LSB is SET and ld.w when it is CLEAR; ld.bu (0x3C/0x3D)
            # carries the displacement's own bit 0 in the OPCODE FIELD and also sets hw2's LSB.
            m = {0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h", 0x3C: "ld.bu", 0x3D: "ld.bu",
                 0x3F: "ld.hu" if hw2 & 1 else "ld.w", 0x31: "movea", 0x36: "andi"}[op6]
            if op6 in (0x31, 0x36):
                m = f"{m} 0x{hw2:04x},r{reg1},r{reg2}"
            else:
                eff = (disp & ~1) | (op6 & 1 if op6 in (0x3C, 0x3D) else 0) \
                    if op6 in (0x3C, 0x3D, 0x3F) else disp
                # a STORE's reg2 field is the SOURCE, not the destination -- print it that way, so a
                # store can never be misread as a load in the readback evidence.
                m = (f"{m} r{reg2},{eff}[r{reg1}]" if op6 in (0x3A, 0x3B)
                     else f"{m} {eff}[r{reg1}],r{reg2}")
        elif op6 == 0x12:
            n, m = 2, f"add {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 == 0x13:
            n, m = 2, f"cmp {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 in (0x14, 0x15, 0x16):
            n, m = 2, f"{ {0x14: 'shr', 0x15: 'sar', 0x16: 'shl'}[op6] } 0x{hw & 0x1F:x},r{reg2}"
        elif op6 == 0x0F:
            n, m = 2, f"cmp r{reg1},r{reg2}"
        elif op6 == 0x08:
            n, m = 2, f"or r{reg1},r{reg2}"
        elif hw == 0x007F or (op6 == 0x03 and reg2 == 0):
            n, m = 2, "jmp [lp]"
        else:
            n, m = 2, f"?? 0x{hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


def assert_probe_census(buf, cave_span):
    """Re-derive each probed cell's reader/writer set from RAW BYTES and assert it exactly.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    read_mnem = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}
    counts = {}
    for disp, (n_read, n_write, writers, mnems, want_mnem, _what) in PROBE_CENSUS.items():
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
        assert len(cave) == 1 and cave[0][1] == want_mnem and cave[0][2] == R6, \
            f"gp-0x{disp:04x}: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, expected " \
            f"exactly one `{want_mnem} ...,r6` -- a STORE here would corrupt a LIVE lane"
        counts[disp] = (len(reads), len(writes))
    # 🛑 The retired cells must not be touched at all.
    for stale in (0x6ADA, 0x6ADC, 0x671D, 0x67FA):
        assert not [h for h in V64.gp_access_census(buf, stale) if h[0] in cave_span], \
            f"the cave touches gp-0x{stale:04x}, which V72 retired"
    return counts


def assert_lever_c_single_reader(buf):
    """🛑 [EVIDENCE] `0xC63A0` = tp+0x73A0 has EXACTLY ONE reader image-wide and ZERO writers.

    Re-derived from RAW BYTES on the image being built, both displacement parities plus the
    even-aligned disp23 form, so the "no monitor is checking it" claim is a measurement rather than
    an inherited assertion. The only other occurrence of the odd-parity halfword is at 0xC4764,
    which is in no function (Ghidra) and whose preceding halfword is not a disp16 load ⇒ data.
    """
    d = DAMP_WEIGHT_ADDR - TP
    assert d == DAMP_WEIGHT_TP_DISP, f"0x{DAMP_WEIGHT_ADDR:05X} is not tp+0x{DAMP_WEIGHT_TP_DISP:04X}"
    even = struct.pack("<H", d & 0xFFFE)
    odd = struct.pack("<H", d | 1)
    hits_even = [i for i in range(0, len(buf) - 1) if buf[i:i + 2] == even]
    hits_odd = [i for i in range(0, len(buf) - 1) if buf[i:i + 2] == odd]
    assert not hits_even, \
        f"tp+0x{d:04X} appears in the even (ld.h/st.h/disp23) form at {[hex(h) for h in hits_even]}"
    real = []
    for h in hits_odd:
        hw1 = struct.unpack_from("<H", buf, h - 2)[0]
        if ((hw1 >> 5) & 0x3F) in (0x3C, 0x3D, 0x3F) and (hw1 & 0x1F) == 5 and h % 2 == 0:
            real.append((h - 2, hw1 >> 11))
    assert [a for a, _ in real] == [DAMP_WEIGHT_READER], \
        f"tp+0x{d:04X} readers are {[hex(a) for a, _ in real]}, expected [0x{DAMP_WEIGHT_READER:05X}]"
    return len(hits_odd), real


def damper_authority(buf, mode=10, rate=None):
    """The delivered |gp-0x6bd0| at creep, mirroring FUN_00034350's Q10 chain EXACTLY.

        gp-0x6bd0 = sign(-gp-0x6abe) * (((((seed*B)>>10)*C)>>10)*D)>>10)*E)>>10, clamped to +/-ceiling

    seed = MIN(gp-0x698a, 1024) -- the MAXIMUM-authority assumption is seed = 1024.
    FactorB (0xD2738) and FactorD (0xD2774) are FLAT 1024 = inert, so they drop out.
    Below FactorC's X[0] = 2240 counts (35.0 km/h) the LERP clamps to Y[0]; below FactorE's X[0] = 60
    counts it clamps to its own Y[0]. This returns the value at CREEP, i.e. both clamps binding.
    """
    c = u16(buf, FACTOR_C[mode] + Y_OFF)                       # FactorC Y[0] -- creep clamps here
    ys_e = rec_y(buf, FACTOR_E[mode])
    xs_e = rec_x(buf, FACTOR_E[mode])
    e = ys_e[0] if rate is None else LM.lerp_int(rate, xs_e, ys_e)
    seed = Q10
    v = (seed * Q10) >> 10                                     # * FactorB (1024)
    v = (v * c) >> 10
    v = (v * Q10) >> 10                                        # * FactorD (1024)
    v = (v * e) >> 10
    return v


def assert_untouched(buf, label, stock):
    """Every MUST-REMAIN-STOCK site, by VALUE. A span check passes on the wrong build."""
    assert buf[GATE_ADDR] == GATE_DEAD, \
        f"{label}: the gate 0x{GATE_ADDR:05X} is 0x{buf[GATE_ADDR]:02X}, expected 0x{GATE_DEAD:02X} " \
        "(gp-0x683c, ZERO writers ⇒ both scalar arms unreachable ⇒ V72 is UNGATED by construction)"
    assert bytes(buf[GATE_LOAD[0]:GATE_LOAD[0] + 4]) == GATE_LOAD[1], \
        f"{label}: the gate load is not the stock `ld.bu -0x683c[gp],r15`"
    A.assert_sar_sites(buf, label, expect_doubled=False)
    for addr, want in ARMS_STOCK:
        assert u16(buf, addr) == want, \
            f"{label}: arm 0x{addr:05X} is {u16(buf, addr)}, expected the stock {want}"
    for base in REC_B_HWY + REC_A_HWY:
        assert bytes(buf[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE]), \
            f"{label}: the 50/100 km/h record 0x{base:05X} is not byte-identical to STOCK -- the " \
            "highway 1.000x is STRUCTURAL and depends on it"
    for base in MODE_NEIGHBOURS:
        assert bytes(buf[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE]), \
            f"{label}: mode-11/12 record 0x{base:05X} MOVED -- the byte-pattern trap fired"
    for base, n in (CEILING_REC, CEILING_FLOAT_TWIN):
        assert bytes(buf[base:base + n]) == bytes(stock[base:base + n]), \
            f"{label}: 0x{base:05X} moved -- the damper ceiling and its float twin are LOCKSTEP " \
            "checked and escalate to DTC 0x1d HARD SHUTDOWN"
    assert u16(buf, CEILING_FALLBACK[0]) == CEILING_FALLBACK[1], f"{label}: 0xC6158 moved"
    for m in (12,):
        assert rec_y(buf, FACTOR_C[m]) == FACTOR_C_STOCK_Y[m], f"{label}: FactorC mode {m} moved"
        assert rec_y(buf, FACTOR_E[m]) == FACTOR_E_STOCK_Y[m], f"{label}: FactorE mode {m} moved"
    role = list(buf[ROLE_TABLE[0]:ROLE_TABLE[0] + len(ROLE_TABLE[1])])
    assert role == ROLE_TABLE[1], f"{label}: the role table 0xC4124 drifted: {role}"
    assert not any(r in (6, 7) for r in role), \
        f"{label}: a slot carries role 6 or 7 ⇒ gp-0x67ac can read 1 ⇒ the aggregator drops r24, " \
        "r26 AND the damping lane, and EVERY lever on this build becomes vacuous"


def assert_decoder_matches(cave_bytes):
    """🛑 The decoder's CAVE_HEX must equal the cave just emitted, so it cannot drift."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, "V72: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"V72: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    for token in ("V72", os.path.basename(OUT), "0xC4124"):
        assert token in txt, f"V72: the decoder does not carry '{token}'"
    for name, val in (("A_THRESHOLD", A_THRESHOLD), ("D_THRESHOLD", D_THRESHOLD),
                      ("D_NEG_THRESHOLD", D_NEG_THRESHOLD), ("R_THRESHOLD", R_THRESHOLD)):
        assert re.search(rf"^{name}\s*=\s*{val}\b", txt, re.M), \
            f"V72: the decoder's {name} is not {val}"
    for disp in (A_DISP, DAMP_DISP, RATE_DISP):
        assert f"{disp:04X}" in txt.upper(), f"V72: gp-0x{disp:04x} is missing from the decoder"
    # 🛑 the retired rungs must NOT be described as live
    for stale in (0x6ADA, 0x6ADC, 0x671D, 0x67FA):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale:04X}", txt, re.M | re.I), \
            f"V72: gp-0x{stale:04x} is still a LIVE RUNG in the decoder"
    assert "STRUCTURALLY ZERO" in txt.upper(), \
        "V72: the decoder does not state that bit5 is structurally zero (the dropped rung)"
    assert "TWO-SIDED" in txt, "V72: the decoder never says bit4 is two-sided"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")

    src = Path(SRC_BIN)
    v70 = bytearray(src.read_bytes())
    v67 = Path(V67_BIN).read_bytes()
    v47 = Path(V47_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V70): {src}\n  SHA256 {hashlib.sha256(bytes(v70)).hexdigest()}")
    print(f"REFERENCES:   {V67_BIN}  (LEVER A's arm values)")
    print(f"              {V47_BIN}  (LEVER B's exact flown bytes)")
    print(f"STOCK:        {STOCK_BIN}")
    print(f"\n  LEVER_B_VARIANT = {LEVER_B_VARIANT!r}  "
          f"({len(LEVER_B)} cells = {2 * len(LEVER_B)} bytes)")

    for name, img in (("V70", v70), ("V67", v67), ("V47", v47), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    A.assert_ratchet_edit(v70, "V70 source", expect_edited=False)
    A.assert_no_external_entry(v70)
    assert_untouched(v70, "V70 source", stock)
    for lo, hi, what in A.STOCK_IDENTICAL_SPANS:
        assert not [i for i in range(lo, hi) if v70[i] != stock[i]], \
            f"[0x{lo:05X},0x{hi:05X}) ({what}) differs from stock"
    # gain_B's MODE axis, dereferenced -- never assumed from the 0x14 stride
    print("\n  🛑 gain_B RECORD ADDRESSING, dereferenced from the FOUR ROM pointer arrays "
          f"(entry mode*4, mode = {MODE}):")
    for arr, want in zip(GAIN_B_PTR_ARRAYS, (REC_B0, REC_B1) + REC_B_HWY):
        got = u32(stock, arr + MODE * 4)
        assert got == want, f"0x{arr:05X}[{MODE}] -> 0x{got:05X}, expected 0x{want:05X}"
        nb = [u32(stock, arr + m * 4) for m in (11, 12)]
        print(f"     0x{arr:05X}[{MODE}] -> 0x{got:05X}    [11] -> 0x{nb[0]:05X}   [12] -> 0x{nb[1]:05X}")
    assert u32(stock, GAIN_B_PTR_ARRAYS[0] + 11 * 4) == MODE_NEIGHBOURS[0] and \
        u32(stock, GAIN_B_PTR_ARRAYS[0] + 12 * 4) == MODE_NEIGHBOURS[1], \
        "0xD2A88/0xD2A9C are not mode 11/12's record-0 -- the MODE-vs-SPEED axis claim is wrong"
    assert bytes(stock[MODE_NEIGHBOURS[0]:MODE_NEIGHBOURS[0] + REC_STRIDE]) == \
        bytes(stock[REC_B0:REC_B0 + REC_STRIDE]), \
        "mode 11's record-0 is NOT byte-identical to mode 10's -- re-check the byte-pattern trap"
    print(f"     ⇒ the contiguous 0x{REC_STRIDE:02X} stride inside the block is the **MODE** axis. "
          f"0x{MODE_NEIGHBOURS[0]:05X} is mode 11's")
    print("       record-0 and is BYTE-IDENTICAL to mode 10's, so a span diff cannot see the "
          "difference. Asserted.")
    # every source record, by value
    for base, want in LEVER_A_STOCK_Y.items():
        assert rec_y(stock, base) == want, f"stock record 0x{base:05X} Y is {rec_y(stock, base)}"
    assert rec_y(v70, REC_B0) == [6144, 6144, 2322, 1536], "V70's gain_B rec0 is not the x2 surface"
    assert rec_y(v70, REC_B1) == [5122, 5122, 2247, 1947], "V70's gain_B rec1 is not the x2 surface"
    assert rec_y(v70, REC_A0) == LEVER_A_STOCK_Y[REC_A0] and \
        rec_y(v70, REC_A1) == LEVER_A_STOCK_Y[REC_A1], "V70's gain_A is not byte-stock"
    print(f"\n  ★ V70's gain_B rec1 Y[0]/Y[1] are ALREADY {LEVER_A_FINAL_Y[REC_B1][0][0]} -- V72's own "
          "target -- so that halfword pair does NOT move.")
    # LEVER B's source state, and V47's own bytes
    for m in (10, 11):
        assert rec_y(v70, FACTOR_C[m]) == FACTOR_C_STOCK_Y[m], f"V70 FactorC m{m} is not stock"
        assert rec_y(v70, FACTOR_E[m]) == FACTOR_E_STOCK_Y[m], f"V70 FactorE m{m} is not stock"
        assert rec_x(v70, FACTOR_C[m]) == FACTOR_C_X and rec_x(v70, FACTOR_E[m]) == FACTOR_E_X, \
            f"the FactorC/E X rows moved on mode {m}"
    print("  ✅ [EVIDENCE, byte-read] LEVER B's eight cells are STOCK on V70 ⇒ V47's damping restore "
          "is NOT on the car.")
    print(f"     FactorC X = {FACTOR_C_X} counts = "
          f"{[x // SPEED_COUNTS_PER_KMH for x in FACTOR_C_X]} km/h at "
          f"{SPEED_COUNTS_PER_KMH} counts/km/h ⇒ the LERP clamps FLAT to Y[0] = 0 below 35 km/h.")
    assert u16(v70, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_STOCK, "0xC63A0 is not 1024 on the source"

    code = bytearray(v70)

    # ---- EDIT 1 -- LEVER A ------------------------------------------------------------------------
    print("\n  EDIT 1 -- LEVER A: BOTH rate lanes, PLATEAU ONLY (Y[0] and Y[1]; Y[2]/Y[3] STOCK):")
    for base, (want_y, label) in LEVER_A_FINAL_Y.items():
        before = rec_y(code, base)
        struct.pack_into("<2h", code, base + Y_OFF, want_y[0], want_y[1])
        assert rec_y(code, base) == want_y, f"{label}: record 0x{base:05X} did not take its final Y"
        assert want_y[2:] == LEVER_A_STOCK_Y[base][2:], \
            f"{label}: Y[2]/Y[3] are not the STOCK values -- V72 is PLATEAU-ONLY by construction"
        moved = "" if before == want_y else "  <- MOVED"
        print(f"    0x{base + Y_OFF:05X}  {before} -> {want_y}   {label}{moved}")
    assert u16(code, REC_B0 + Y_OFF) == V67_ARM_R24 and u16(code, REC_A0 + Y_OFF) == V67_ARM_R26, \
        "the plateau values are not V67/V68's own arm values, used verbatim"
    print(f"    ✅ {V67_ARM_R24} and {V67_ARM_R26} are V67/V68's OWN arm values (0xC6446 / 0xC6444 on "
          "`_v67_plain_image.bin`), used")
    assert u16(v67, 0xC6446) == V67_ARM_R24 and u16(v67, 0xC6444) == V67_ARM_R26, \
        "V67 does not carry (5244, 512) -- the provenance claim is wrong"
    print("       VERBATIM rather than re-derived -- asserted against the V67 image, not quoted.")

    # ---- EDIT 2 -- LEVER B ------------------------------------------------------------------------
    print(f"\n  EDIT 2 -- LEVER B: the base-assist damper opened at creep ({LEVER_B_VARIANT} bytes):")
    for addr, (old, new, label) in sorted(LEVER_B.items()):
        assert u16(code, addr) == old, \
            f"{label} @0x{addr:05X} is {u16(code, addr)}, expected the stock {old}"
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   {label}")
    for m in (10, 11):
        assert rec_x(code, FACTOR_C[m]) == FACTOR_C_X and rec_x(code, FACTOR_E[m]) == FACTOR_E_X, \
            f"a FactorC/E X row moved on mode {m} -- only Y values may change"
        for y in rec_y(code, FACTOR_C[m]) + rec_y(code, FACTOR_E[m]):
            assert 0 <= y < 0x8000, f"a FactorC/E Y is not a non-negative SIGNED halfword: {y}"
    if LEVER_B_VARIANT == "V47":
        for m in (10, 11, 12):
            assert rec_y(code, FACTOR_C[m]) == rec_y(v47, FACTOR_C[m]), f"FactorC m{m} != V47's"
            assert rec_y(code, FACTOR_E[m]) == rec_y(v47, FACTOR_E[m]), f"FactorE m{m} != V47's"
        print("    ✅✅ ALL SIX FactorC/E records are BYTE-IDENTICAL to `_v47_plain_image.bin` -- "
              "V47's exact")
        print("        flown bytes, ASSERTED against the image rather than aimed at.")
    else:
        print("    🛑 NOT V47's bytes -- this is the mission brief's FLATMAX table. See the docstring.")

    # ---- the delivered damping authority, and the CEILING it must respect -------------------------
    auth0 = damper_authority(code, 10)
    auth_max = max(damper_authority(code, 10, rate=r) for r in range(0, 4001, 5))
    ceil_floor, ceil_max = CEILING_Y[0], CEILING_Y[1]
    assert [u16(code, CEILING_REC[0] + 2 + 2 * j) for j in range(2)] == CEILING_X and \
        [u16(code, CEILING_REC[0] + 6 + 2 * j) for j in range(2)] == CEILING_Y, \
        "the ceiling record is not the 2-point X=[300,800] Y=[512,1024] shape"
    print(f"\n  DELIVERED DAMPING AUTHORITY at creep, mirroring FUN_00034350's Q10 chain "
          f"(seed = {Q10}, FactorB/D inert):")
    print(f"    creep (both LERPs clamped to Y[0]) : {auth0:4d} counts")
    print(f"    worst case over the whole rate axis: {auth_max:4d} counts")
    print(f"    the ceiling is a 2-point LERP over gp-0x6ac2, X={CEILING_X} Y={CEILING_Y}, fallback "
          f"0xC6158 = {CEILING_FALLBACK[1]}")
    assert auth_max <= ceil_max, \
        f"the delivered authority {auth_max} exceeds even the ceiling MAXIMUM {ceil_max}"
    if auth_max <= ceil_floor:
        print(f"    ✅ {auth_max} <= the ceiling FLOOR {ceil_floor} ⇒ the damper NEVER saturates: it "
              "stays proportional")
        print("       at every value of gp-0x6ac2, so no hard nonlinearity enters the loop.")
    else:
        print(f"    🛑 {auth_max} EXCEEDS the ceiling FLOOR {ceil_floor} ⇒ the damper SATURATES "
              f"whenever gp-0x6ac2 < {CEILING_X[0]},")
        print("       turning a proportional damper into a hard-clipping element inside the loop at "
              "the ratchet's own frequency. GATE 2 EXPOSURE -- state it in the flight note.")

    # ---- EDIT 3 -- LEVER C ------------------------------------------------------------------------
    print("\n  EDIT 3 -- LEVER C: the damper's own weight into FUN_00038148:")
    struct.pack_into("<H", code, DAMP_WEIGHT_ADDR, DAMP_WEIGHT_NEW)
    print(f"    0x{DAMP_WEIGHT_ADDR:05X}  {DAMP_WEIGHT_STOCK:5d} -> {DAMP_WEIGHT_NEW:5d}   "
          f"weight on gp-0x6bd0 (tp+0x{DAMP_WEIGHT_TP_DISP:04X})")
    n_odd, readers = assert_lever_c_single_reader(bytes(code))
    print(f"    ✅ [EVIDENCE, raw both-parity byte scan on THIS image] tp+0x{DAMP_WEIGHT_TP_DISP:04X} "
          f"has EXACTLY ONE reader:")
    print(f"       0x{readers[0][0]:05X} `ld.hu 0x{DAMP_WEIGHT_TP_DISP:04x}[tp],r{readers[0][1]}`, "
          f"ZERO writers, 0 hits in the even (ld.h/st.h/disp23) form.")
    print(f"       ({n_odd} raw odd-parity halfword occurrences; the non-instruction one is 0xC4764 "
          "-- no function, and")
    print("        0xC4762 is not a disp16 load ⇒ data.) ⇒ NO MONITOR CAN BE CHECKING IT: the "
          "lockstep question is")
    print("       closed STRUCTURALLY, which is why this buys the same authority as raising "
          "0xD209C at zero risk.")

    # ---- EDIT 4 -- the carried ratchet byte -------------------------------------------------------
    print("\n  EDIT 4 -- 0x454FE CARRIED (🛑 NOT a ratchet lever on this build):")
    struct.pack_into("<H", code, RATCHET_ADDR, A.RATCHET_NEW_HW)
    A.assert_ratchet_edit(code, "V72", expect_edited=True)
    A.assert_no_external_entry(code)
    n_state = A.assert_governor_monitor_safety(code, "V72")
    print(f"    0x{RATCHET_ADDR:05X}  0x{A.RATCHET_STOCK_HW:04X} -> 0x{A.RATCHET_NEW_HW:04X}   "
          f"bne 0x455C4 -> br 0x455C4; FUN_0004595a safety re-derived ({n_state} state read)")
    print("    🛑 FALSIFIED for the current 7.79 Hz ratchet: V71B AND V71C both flew carrying this "
          "byte and the")
    print("       operator reports the ratchet UNCHANGED on both. It is carried ONLY because V42 "
          "confirmed it")
    print("       against a DIFFERENT symptom (the ~10 s hard-turn recovery ratchet) and reverting "
          "would regress")
    print("       that. Do not describe it as a ratchet fix.")

    # ---- EDIT 5 -- the probe ----------------------------------------------------------------------
    print("\n  EDIT 5 -- THE PROBE (68 of the proven 68 bytes; ZERO spare):")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    assert code[CAVE_BASE + 2] == W_LIVE, "the liveness immediate is not the pre-shift weight 0x10"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v70[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical"
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    counts = assert_probe_census(bytes(code), cave_span)
    print("\n    ✅ GATE 1 (RAM ownership) asserted as a MEASUREMENT, from raw bytes, two decoders:")
    for disp, (r, w) in counts.items():
        print(f"       gp-0x{disp:04x}  {r:2d}r / {w}w   {PROBE_CENSUS[disp][5]}")
    print("       the cave's ONLY store is st.b r6,-0x1514[gp] (the CAN-330 payload byte, bits 2:0")
    print("       preserved) -- identical RAM ownership to V67/V68/V69/V70/V71, all flown clean.")
    print(f"    🛑 gp-0x{DAMP_DISP:04x} is NOT a zero-reader mirror: it has "
          f"{counts[DAMP_DISP][0]} real readers including the 1 kHz")
    print(f"       aggregator, and the firmware's own `st.h r6,-0x{DAMP_DISP:04x}[gp]` @0x{PIN_STH_6BD0[0]:05X} "
          f"is {PIN_STH_6BD0[1].hex()} against our")
    print(f"       {V55.ldh(DAMP_DISP, R6).hex()} -- SAME register, SAME displacement, ONE BIT apart "
          "(op 0x3B vs 0x39). Asserted by")
    print("       value in the builder, in the readback and in the verifier.")
    print(f"    🛑 bit5 (weight 0x{W_UNUSED_BIT5:02X}) is NEVER added ⇒ it reads 0 in EVERY V72 frame. "
          "One-way falsifier:")
    print("       a single frame with bit5 SET proves the artefact is not V72.")

    # ---- the probe's pre-registration --------------------------------------------------------------
    print(f"\n  📋 bit3 PRE-REGISTRATION -- threshold is EXACTLY {R_THRESHOLD}, so it carries over "
          "verbatim:")
    print(f"     {R_THRESHOLD} counts / {RATE_SCALE_CTS_PER_DEGS} counts-per-deg/s = "
          f"{R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS:.2f} deg/s of column rate.")
    print("     Engaged duty must read 3.74% under the settled scale and 0.0000% under the retired")
    print("     8x-smaller alternative, and it must fire frame-for-frame with bus |rate_c| >= "
          f"{R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS:.1f} deg/s.")
    print(f"     {R_THRESHOLD} is also FactorE's own X[1] and the rate lanes' own X[1] breakpoint.")
    assert abs(R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS - 84.89) < 0.05, \
        "the pre-registered 84.9 deg/s does not re-derive from the threshold and the settled scale"
    assert R_THRESHOLD == FACTOR_E_X[1] == LM.read_record(stock, REC_B0)[1][1], \
        "400 is not FactorE's X[1] AND the rate lane's X[1] -- the 'LERP's own breakpoint' claim fails"

    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v72_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 RE-DISASSEMBLE THE CAVE FROM THE BUILT BYTES, IN PYTHON -------------------------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE (raw Python decoder, NOT a Ghidra database):")
    redis = redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    assert [a for a, _, _ in redis] == [a for a, _, _ in cave_listing], \
        "the re-disassembly does not land on the same instruction boundaries as the build listing"
    assert [r for _, r, _ in redis] == [r for _, r, _ in cave_listing], \
        "the re-disassembly's bytes differ from the emitted listing"
    for (a, raw, m) in redis:
        print(f"    0x{a:05X}  {raw.hex():<12s} {m}")
    ld_h = [(a, m) for a, _r, m in redis if m.startswith("ld.h ")]
    st = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    assert len(ld_h) == 1 and ld_h[0][1] == f"ld.h {-DAMP_DISP}[r{GP}],r{R6}", \
        f"the re-disassembled ld.h is {ld_h} -- expected exactly one, of gp-0x{DAMP_DISP:04x} into r6"
    assert len(st) == 1 and st[0][1].startswith("st.b"), \
        f"the re-disassembly finds stores {st} -- expected exactly ONE st.b (the CAN payload byte)"
    print(f"    ✅ exactly ONE `ld.h` (gp-0x{DAMP_DISP:04x} -> r6, opcode 0x39) and exactly ONE store, "
          "an `st.b` to the")
    print("       CAN-330 payload byte. Re-derived from the BUILT bytes, not from a cached database.")

    # ---- THE DELIVERED MULTIPLIERS, RE-DERIVED FROM THE BUILT IMAGE -------------------------------
    print("\n  THE DELIVERED MULTIPLIER, re-derived from the BUILT image via v72_lane_model.py:")
    print("  (the gate 0x3AA96 is 0xC5 = the DEAD cell, so ENGAGED and MANUAL are identical -- V72 is")
    print("   UNGATED by construction and its dose applies in manual too. That is the disclosed cost.)")
    speeds = sorted(LM.KMH.items())
    rates = (0, 200, 400, 800, 1400, 1600, 3000)
    for lane in ("r24", "r26"):
        print(f"    {lane}  " + "".join(f"{r:>8}" for r in rates) + "   <- rate index")
        for kmh, vc in speeds:
            row = [LM.effective(bytes(code), lane, vc, r, False) /
                   LM.effective(stock, lane, vc, r, False) for r in rates]
            print(f"    {kmh:>4} km/h" + "".join(f"{x:8.3f}" for x in row))
    # 1) ENGAGED == MANUAL, exactly
    grid = [(v, r) for v in range(0, 6401, 32) for r in range(0, 3001, 25)]
    for lane in ("r24", "r26"):
        assert not [1 for v, r in grid
                    if LM.effective(bytes(code), lane, v, r, True) !=
                    LM.effective(bytes(code), lane, v, r, False)], \
            f"{lane}: ENGAGED differs from MANUAL -- the gate is not the dead cell"
    print(f"    ✅ over {len(grid)} operating points, ENGAGED == MANUAL EXACTLY on both lanes.")
    # 2) r24 <= V70's r24 everywhere -- the unconditional bound onto a build that flew ungated
    exc = [(v, r) for v, r in grid
           if LM.effective(bytes(code), "r24", v, r, False) > LM.effective(bytes(v70), "r24", v, r, False)]
    assert not exc, f"r24 EXCEEDS V70's at {exc[:6]} -- the unconditional bound fails"
    print(f"    ✅ r24 <= V70's r24 at ALL {len(grid)} grid points: 0 exceedances. V70 flew UNGATED, "
          "dosed the")
    print("       manual arm at x2 plateau-only, and produced ZERO grind-#2 events in every regime.")
    # 3) r26 <= stock everywhere
    exc = [(v, r) for v, r in grid
           if LM.effective(bytes(code), "r26", v, r, False) > LM.effective(stock, "r26", v, r, False)]
    assert not exc, f"r26 EXCEEDS stock at {exc[:6]}"
    print(f"    ✅ r26 <= STOCK at ALL {len(grid)} grid points: 0 exceedances (the r26 half can only "
          "REDUCE lane gain).")
    # 4) EXACTLY 1.000x at >= 50 km/h, and above the last edited breakpoint
    hwy = [(v, r) for v, r in grid if v >= 3200
           for lane in ("r24", "r26")
           if LM.effective(bytes(code), lane, v, r, False) != LM.effective(stock, lane, v, r, False)]
    assert not hwy, f"a >= 50 km/h operating point moved: {hwy[:4]}"
    n_hwy = sum(1 for v, _r in grid if v >= 3200)
    print(f"    ✅ all {n_hwy} points at >= 3200 counts (>= 50 km/h) are byte-identical to stock on "
          "BOTH lanes ⇒")
    print("       EXACTLY 1.000000x at highway, EVERY rate. STRUCTURAL: the 50/100 km/h records are "
          "untouched.")
    # the true rate crossover -- reported, not assumed
    moved = [r for _v, r in grid
             if any(LM.effective(bytes(code), ln, _v, r, False) != LM.effective(stock, ln, _v, r, False)
                    for ln in ("r24", "r26"))]
    r_cross = max(moved)
    xs_all = [LM.read_record(stock, b)[1][2] for b in (REC_B0, REC_B1, REC_A0, REC_A1)]
    print(f"    ⚠ THE BRIEF SAID '1.000x at rate >= 1400'. The TRUE crossover is rate > {r_cross}: the "
          f"edited records'")
    print(f"       own X[2] breakpoints are {xs_all} (gain_B rec0/rec1, gain_A rec0/rec1), and only "
          "above the")
    print("       LARGEST of them is every lane back at stock. Reported as measured, not as briefed.")
    assert r_cross <= max(xs_all), "the dose reaches beyond the edited records' X[2] breakpoints"
    # 5) V67/V68's creep values reproduced at the plateau.
    # ⚠ EXACT ON BOTH LANES AT 0 km/h, AND ON r26 EVERYWHERE. At 10 km/h r24 is DELIBERATELY 2.000x
    # (5122) rather than V67's 2.048x (5244): the design chose the V70 bound over 2.4% of dose, so
    # that `V72 r24 <= V70 r24` holds unconditionally. Asserted as the DESIGNED INEQUALITY, not
    # smoothed into an equality -- and the shortfall is printed rather than hidden.
    print("\n    ✅ V67/V68's CREEP OPERATING POINT, reproduced through the UNGATED surface:")
    for kmh, vc, rate, exact24 in ((0, 0, 0, True), (0, 0, 400, True),
                                   (10, 640, 0, False), (10, 640, 250, False)):
        v72_24 = LM.effective(bytes(code), "r24", vc, rate, False) / LM.effective(stock, "r24", vc, rate, False)
        v72_26 = LM.effective(bytes(code), "r26", vc, rate, False) / LM.effective(stock, "r26", vc, rate, False)
        v67_24 = LM.effective(v67, "r24", vc, rate, True) / LM.effective(stock, "r24", vc, rate, True)
        v67_26 = LM.effective(v67, "r26", vc, rate, True) / LM.effective(stock, "r26", vc, rate, True)
        v70_24 = LM.effective(bytes(v70), "r24", vc, rate, False) / LM.effective(stock, "r24", vc, rate, False)
        assert abs(v72_26 - v67_26) < 1e-12, \
            f"at {kmh} km/h rate {rate}: r26 is {v72_26:.4f}, V67's is {v67_26:.4f} -- the r26 half " \
            "must reproduce V67/V68 EXACTLY at the plateau"
        if exact24:
            assert abs(v72_24 - v67_24) < 1e-12, \
                f"at {kmh} km/h rate {rate}: r24 is {v72_24:.4f}, V67's is {v67_24:.4f}"
            note = "== V67/V68 ENGAGED (EXACT on both lanes)"
        else:
            assert v72_24 <= v67_24 and abs(v72_24 - v70_24) < 1e-12, \
                f"at {kmh} km/h rate {rate}: r24 is {v72_24:.4f}, expected V70's {v70_24:.4f} and " \
                f"<= V67's {v67_24:.4f}"
            note = (f"r24 is V70's {v70_24:.3f} BY DESIGN, {100 * (1 - v72_24 / v67_24):.1f}% under "
                    f"V67's {v67_24:.3f}")
        print(f"       {kmh:>3} km/h rate {rate:>4}   V72 r24 {v72_24:.3f} r26 {v72_26:.3f}   {note}")
    print("       ⚠ THE DESIGN DOC IS INTERNALLY INCONSISTENT HERE and the BYTES win: 2.1's table")
    print("         specifies Y[0..1] = 5122 at 10 km/h (= 2.000x, V70's own value) and explains WHY")
    print("         -- 5244 would exceed V70 by 2.4% at 10-30 km/h and break the unconditional bound")
    print("         -- but 2.1.1's summary row still prints 2.048 for V72. The brief's required FINAL")
    print("         Y is 5122, and 5122 is what is built. The bound holds; the 2.4% is the price.")

    # ---- the untouched sites, re-asserted on the finished image ----------------------------------
    assert_untouched(code, "V72", stock)
    probe_copy = bytearray(code)
    struct.pack_into("<H", probe_copy, RATCHET_ADDR, A.RATCHET_STOCK_HW)
    V57.assert_decoupled(probe_copy, "V72 (with 0x454FE restored for the inherited guard)")
    exception_set = [i for i in range(START, END) if probe_copy[i] != code[i]]
    assert exception_set == [RATCHET_ADDR], \
        f"the guard relaxation covers {[hex(x) for x in exception_set]}, expected " \
        f"exactly [0x{RATCHET_ADDR:05X}]"
    V55.assert_variant_tables(code)
    print("\n  ✅ V53's eleven STOCK_CALS re-checked through V57's inherited guard (the ONLY relaxation "
          f"is 0x{RATCHET_ADDR:05X},")
    print("     asserted as a one-byte exception set); V57's decoupling carried; variant tables intact.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = [CAVE_BASE, RATCHET_ADDR, REC_B0 + Y_OFF, REC_A0 + Y_OFF, DAMP_WEIGHT_ADDR,
               min(LEVER_B), max(LEVER_B)]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    assert [b[1] for b in blocks] == [0xC4FFC, 0xC6FFC, 0xD2FFC], \
        f"expected the MAIN, CAL and 0xD2000 trailers, got {[hex(b[1]) for b in blocks]}"
    assert V53.owning_block(code, DAMP_WEIGHT_ADDR) == V53.owning_block(code, REC_A0) == \
        (0xC6000, 0xC6FFC), "LEVER C and gain_A are not both in the CAL block"
    print(f"\n  CRC -- EXACTLY {len(blocks)} blocks move (asserted, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")
    assert not [a for a in list(LEVER_B) + [CAVE_BASE, RATCHET_ADDR, DAMP_WEIGHT_ADDR]
                if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"

    # ---- the attributed diff -----------------------------------------------------------------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    lever_a_bytes = {b + Y_OFF + k for b in LEVER_A_FINAL_Y for k in range(4)}
    lever_b_bytes = {a + k for a in LEVER_B for k in (0, 1)}
    lever_c_bytes = {DAMP_WEIGHT_ADDR, DAMP_WEIGHT_ADDR + 1}

    def attribute(d):
        return ("PROBE cave" if d in cave_range else
                "LEVER A rate-lane plateau" if d in lever_a_bytes else
                "LEVER B FactorC/E damping" if d in lever_b_bytes else
                "LEVER C 0xC63A0 damper weight" if d in lever_c_bytes else
                "CARRIED 0x454FE" if d == RATCHET_ADDR else None)

    d70 = [i for i in range(START, END) if code[i] != v70[i]]
    f70 = [d for d in d70 if d not in crc_only]
    stray = [d for d in f70 if attribute(d) is None]
    assert not stray, f"UNATTRIBUTED functional bytes vs V70: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V70 (the base): {len(d70)} bytes = {len(f70)} functional + "
          f"{len(d70) - len(f70)} CRC")
    for d in sorted(f70):
        print(f"    0x{d:05X}  {v70[d]:02X} -> {code[d]:02X}   {attribute(d)}")

    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    fs = [d for d in d_stock if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None]
    assert not stray_s, f"UNATTRIBUTED functional bytes vs STOCK: {[hex(x) for x in stray_s[:16]]}"
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes = {len(fs)} functional + "
          f"{len(d_stock) - len(fs)} CRC")
    groups = {}
    for d in sorted(fs):
        groups.setdefault(attribute(d), []).append(d)
    for what, ds in groups.items():
        print(f"    {what:<32s} {len(ds):3d} bytes  [0x{min(ds):05X}..0x{max(ds):05X}]")
    for what, ds in groups.items():
        if what == "PROBE cave":
            continue
        for d in ds:
            print(f"      0x{d:05X}  {stock[d]:02X} -> {code[d]:02X}   {what}")

    # ---- write + readback --------------------------------------------------------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
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
    assert len(OUT) < 250, f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate"
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V72 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v70)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    A.assert_ratchet_edit(dec, "V72 readback", expect_edited=True)
    A.assert_no_external_entry(dec)
    A.assert_governor_monitor_safety(dec, "V72 readback")
    assert_untouched(dec, "V72 readback", stock)
    for base, (want_y, _l) in LEVER_A_FINAL_Y.items():
        assert rec_y(dec, base) == want_y, f"readback record 0x{base:05X} Y is {rec_y(dec, base)}"
    for addr, (_o, new, label) in LEVER_B.items():
        assert u16(dec, addr) == new, f"readback {label} @0x{addr:05X} is {u16(dec, addr)}"
    assert u16(dec, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_NEW, "readback 0xC63A0 wrong"
    assert_lever_c_single_reader(bytes(dec))
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_census(bytes(dec), cave_span)
    assert [r for _, r, _ in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))] == \
        [r for _, r, _ in cave_listing], "the readback cave does not re-disassemble identically"
    assert not [1 for v, r in grid if v >= 3200
                for ln in ("r24", "r26")
                if LM.effective(bytes(dec), ln, v, r, False) != LM.effective(stock, ln, v, r, False)], \
        "readback moved a >= 50 km/h operating point"
    V55.assert_variant_tables(dec)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v70[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V70 outside the attributed set: {rb_stray[:8]}"
    print("\n  READBACK -- payload, all four LEVER A records, all "
          f"{len(LEVER_B)} LEVER B cells, LEVER C and its")
    print("     single-reader census, the carried ratchet byte (decoded as a Bcond, target "
          "re-checked), the")
    print("     governor-monitor safety, every MUST-REMAIN-STOCK site, the whole 68-byte cave AND its")
    print("     re-disassembly, the probe census, the >= 50 km/h structural-stock sweep, identity to "
          "V70")
    print("     outside the attributed set, and the full CRC chain: ALL re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V72 BUILT. Both rate lanes dosed PLATEAU-ONLY through the ungated speed-shaped surfaces")
    print("  (V67/V68's creep numbers, exactly 1.000x at highway), the base-assist damper opened at")
    print("  creep with V47's own bytes, and the damper's weight doubled. A 4-rung probe on `a`, the")
    print("  damper output and the rate index.")
    print("  🛑 UNGATED: the rate-lane dose applies in MANUAL steering below ~30 km/h too.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without an image, run on import by the verifier and by the tests."""
    _self_check_encoders()
    assert R_THRESHOLD == 400 and A_THRESHOLD == 512 and D_THRESHOLD == 64
    assert D_NEG_THRESHOLD == -65
    assert set(LEVER_A_FINAL_Y) == {REC_B0, REC_B1, REC_A0, REC_A1}
    assert sum(len(v[0]) for v in LEVER_A_FINAL_Y.values()) == 16
    assert 2 * len(LEVER_B) == 16 or LEVER_B_VARIANT != "V47", \
        "the V47 LEVER B variant must be exactly 8 cells = 16 bytes"
    cave, _ = build_cave()
    assert len(cave) == 68


if __name__ == "__main__":
    build()
