#!/usr/bin/env python3
"""build_v72_tva.py -- V72 = V67/V68's creep rate lane, delivered UNGATED and speed-shaped.

    V72  ==  V70  +  LEVER A (both lanes, WHOLE rate axis, 0 and 10 km/h records)
                  +  LEVER B (FactorC/E damping at creep)  +  LEVER C (0xC63A0 x2)
                  +  0x454FE (carried, inert)  +  a new 68-byte probe.

Spec: `docs/V72-DESIGN.md` + the team-lead's routes-54/58 revisions (whole-axis Lever A; Lever B at
430/431 + 927; probe at 512/1024). Every edit asserts its FINAL byte value, so the artefact is
independent of which base was used.

★★ THE OBJECTIVE, IN ONE LINE: reproduce V67/V68's creep configuration EXACTLY -- the best-measured
build this car has ever had (median `e_18-22` engaged creep = 109 against stock's 879) -- and remove
its only failure, which is that a scalar gated arm cannot be highway-clean while dosing at creep.

WHY WHOLE-AXIS AND NOT PLATEAU-ONLY  [the spec changed mid-build; the reason is on the record]
------------------------------------------------------------------------------------------------
An earlier cut of this build dosed only Y[0]/Y[1] (the flat [0,400] plateau), on the grounds that
grind #1 is 97.8% below rate index 400 *instantaneously*. Two measurements killed that:
  1. what matters for a derivative term is the PEAK of each cycle -- per-window peak index p50 =
     **523**, and **56.7% of windows peak above 400**;
  2. the on-car ladder separates the two shapes directly. Every build that raised r24 across the
     WHOLE axis lands at 70-268 median; **both plateau-only builds land at 729-746 -- the two worst
     dosed builds in the corpus, at x2 and x4.**
⇒ Only the whole-axis form reproduces V67/V68. The plateau-only form diverges from it on BOTH lanes
above rate 400. **This build asserts the reproduction rather than aiming at it** (see the sweep).

LEVER A -- 32 bytes: all four Y, both records, both surfaces
--------------------------------------------------------------
    0xD2A7E  gain_B mode-10 rec0 (0 km/h)   r24   Y -> [5244, 5244, 5244, 5244]
    0xD2ABA  gain_B mode-10 rec1 (10 km/h)  r24   Y -> [5244, 5244, 5244, 5244]
    0xC6A72  gain_A rec0 (0 km/h)           r26   Y -> [ 512,  512,  512,  512]
    0xC6A86  gain_A rec1 (10 km/h)          r26   Y -> [ 512,  512,  512,  512]
5244 and 512 are V67/V68's OWN arm values (`0xC6446` / `0xC6444`), used verbatim. A FLAT record is
exactly what a scalar arm delivers, so at 0 and 10 km/h V72's multiplier equals V67/V68's ENGAGED
multiplier at EVERY rate index -- 1.707 / 1.707 / 2.258 / 3.414 on r24 and 0.167 / 0.167 / 0.202 /
0.250 on r26 at 0 km/h. Asserted against `_v67_plain_image.bin` evaluated in its engaged arm.
🛑 `0xD2AEC` / `0xD2B28` / `0xC6A90` / `0xC6AA4` STAY BYTE-STOCK ⇒ **exactly 1.000x on both lanes at
and above 50 km/h, structurally** -- the highway fix, by record-selection geometry, not by tuning.
🛑 gain_B is MODE-INDEXED through FOUR pointer arrays (`0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`, entry
mode*4). The contiguous 0x14 stride inside the block is the **MODE** axis: `0xD2A88` is mode 11's
record-0 and `0xD2A9C` is mode 12's, both byte-identical to mode 10's stock record, so a span diff
cannot see the difference. Dereferenced and asserted below.

LEVER B -- 20 bytes: the base-assist damper, opened at creep
--------------------------------------------------------------
    0xD27C6/C8  FactorC m10 Y[0],Y[1]  0, 235  -> 430, 430   ⇒ Y = [430, 430, 430, 877]
    0xD27DA/DC  FactorC m11 Y[0],Y[1]  0, 234  -> 431, 431   ⇒ Y = [431, 431, 431, 877]
    0xD2802/04/06  FactorE m10 Y[0..2] 0,140,539 -> 927,927,927  ⇒ Y = [927, 927, 927, 927]
    0xD2816/18/1A  FactorE m11 Y[0..2] 0,140,539 -> 927,927,927  ⇒ Y = [927, 927, 927, 927]
`0xD27BC` FactorC X = [2240,3840,5120,8960] counts = [35,60,80,140] km/h at 64 counts/km/h, so the
LERP clamps flat to Y[0] = 0 below 35 km/h. The five factors multiply in Q10 ⇒ **stock has NO
base-assist damping anywhere below 35 km/h**, the entire region where the ratchet (4.9-8.0 km/h) and
both grinds live. At the ratchet's 7.79 Hz the 100 Hz task-5 ZOH costs only 14.0 deg average, so
88-97% of the velocity-proportional authority survives -- unlike at 21 Hz, where the same hold made
V47's target structurally unreachable.
★ FactorC = its own Y[2] and FactorE = its own Y[3], which is the largest value that keeps each
record MONOTONE NON-DECREASING. Both properties are asserted, not chosen and hoped for.
🛑 The ceiling `0xD209C` and its float twin `0xC6554` are NOT touched -- lockstep-checked at 5/1024,
escalating to DTC 0x1d hard shutdown. Asserted byte-stock.

LEVER C -- 2 bytes: `0xC63A0` 1024 -> 2048
--------------------------------------------
The weight on `gp-0x6bd0` -- the damper's OWN output -- inside `FUN_00038148`'s 6-term composite.
✅ [EVIDENCE, decompile of FUN_00038148 + a raw both-parity byte scan] `0xC63A0` = tp+0x73A0 has
**exactly ONE reader image-wide**, `ld.hu 0x73a0[tp],r9` @`0x381AC`, and ZERO writers. The
even-parity (ld.h/st.h/disp23) form returns 0 hits; the only other odd-parity occurrence is
`0xC4764`, which Ghidra reports is in **no function** and whose preceding halfword is not a disp16
load ⇒ data. **One reader ⇒ no monitor can be checking it**, which is why this was chosen over
raising `0xD209C`.

CARRIED, NOT A LEVER -- `0x454FE` = 0xB5
-----------------------------------------
🛑 **CARRIED, CURRENTLY INERT, AND UNTESTED -- neither a fix nor falsified.**
[EVIDENCE] V71's bit5 rung measured `gp-0x67fa == 4` at **0 / 123,277** frames (route 54) and
**8 / 92,826** (route 58) -- and all eight are one 80 ms burst at 0.00 km/h **in park**. State 4
never occurred while driving ⇒ V42's substitution never ran on either flight ⇒ the V71B/V71C
"no change" result is a **null by construction, not a falsification.** An earlier note in this file
called it falsified; that was wrong and is retracted here.
⚠ [OPEN] The same measurement cuts the other way too: V42 was confirmed on-car against the ~10 s
hard-turn recovery ratchet, and if state 4 never occurs then that fix could not have acted either.
Carried because reverting it cannot help and might regress a confirmed result.

THE PROBE -- 68 of the proven 68 bytes, CAN 0x14A byte4 bits 7:3
-----------------------------------------------------------------
    bit7 = 1                     LIVENESS. field == 0 ⇒ the cave did not fire ⇒ frame VOID.
    bit6 = gp-0x69a4 >= 512 ★★★★ `a`, THE UNMEASURED WEIGHT. r26 = ((a * dtorque) >> 10) * gain_A
                                 >> 10, so `a` sets r26's magnitude RELATIVE to r24 and it has NEVER
                                 been measured. No prior -- this rung IS the measurement.
    bit5 = gp-0x69a4 >= 1024 ★★★ the second thermometer step. ★ `bit5 => bit6` is a MONOTONE
                                 INVARIANT, structurally guaranteed, so a wrong build is DETECTABLE
                                 rather than merely implausible.
    bit4 = |gp-0x6bd0| >= 64     IS LEVER B IN FORCE? TWO-SIDED -- the damper is velocity-OPPOSING
                                 (`0x3469e`: if gp-0x6abe > 0, negate) so it alternates sign every
                                 half cycle, and r24's own excursions measured 0.5013 positive on
                                 V71, i.e. all but perfectly symmetric. A one-sided rung would halve
                                 the count for nothing. V71 proved this idiom WORKS: 4,478 engaged
                                 frames, engaged-vs-manual 416x [172, 1748], p = 0/20,000.
    bit3 = gp-0x6ac0 >= 512   📋 PRE-REGISTERED at **2.750%** engaged duty (9,497 / 345,396 frames),
                                 and it must fire frame-for-frame with bus `|rate_c| >= 108.7 deg/s`
                                 (512 counts / 4.7121 counts-per-deg-s). A POSITIVE CONTROL: the rate
                                 axis is settled three independent ways, so a miss indicts the cave,
                                 not the scale. 🛑 512 is also the hard floor -- at 250 the retired
                                 8x-smaller scale starts firing (0.058%) and the rung stops
                                 discriminating.

★★ HOW FIVE RUNGS FIT IN 68 BYTES -- and the ONE new architectural fact it rests on
-------------------------------------------------------------------------------------
The obvious encoding does not fit: 4 seed + 18 (bit6+bit5 sharing one load) + 16 bit4 + 12 bit3 +
2 shl + 20 tail = **72 B**, four over the proven extent. The four bytes come from a fact this kit has
never used before, so it is stated explicitly and it is EVIDENCE, not assumption:

🛑 **V850 shift instructions SET THE Z FLAG, and a following Bcond reads it with no `cmp`.**
    [EVIDENCE, Ghidra-disassembled at 0x318DA, and Honda does it three times in a row:]
        0x318D6  andi 0x200,r14,r8
        0x318DA  sar  0x9,r8          <- sets Z
        0x318DC  bne  0x319CA         <- branches on it, NO intervening cmp
        0x318DE  andi 0x800,r14,r6 ; 0x318E2 sar 0xb,r6 ; 0x318E4 bne ...  (and again at 0x318EA)
Both `a` and the rate index are loaded `ld.hu` (zero-extended, so non-negative), which makes
`s = v sar 9` satisfy `s != 0  <=>  v >= 512`. So bit6 and bit3 each drop their `cmp 0x1`, saving
2 bytes apiece: `ld.hu ; sar 0x9 ; be +4 ; add w,r7`.
⚠ THE COST, DECLARED: **flag liveness across the `sar`->`be` pair is now load-bearing.** If anything
were ever inserted between them the rung would silently read the PREVIOUS comparison's flags -- a
plausible-looking wrong answer, which is the exact failure class this kit keeps paying for. The
builder asserts that each `sar` is IMMEDIATELY followed by its own `be`, by position, in the emitted
listing AND again in the re-disassembly of the BUILT bytes.
⚠ AND A NEAR-MISS WORTH RECORDING: the raw byte scan that first suggested this found 801
"shift-then-Bcond" pairs, and the first two sampled (0x283CE, 0x1B56E) were **NOT on instruction
boundaries** -- they were the second halfwords of a 4-byte `st.b` and a 4-byte `jr`. The claim is
carried on the Ghidra-confirmed site above, not on the scan count.

🛑 THE ONE-BIT TRAP IS LIVE ON bit4, IN ITS WORST FORM IN THIS KIT'S HISTORY. `ld.h` = opcode 0x39,
`st.h` = 0x3B. Our `ld.h -0x6bd0[gp],r6` is `24373094`; the firmware's own `st.h r6,-0x6bd0[gp]`
@`0x34730` is `64373094` -- **the same displacement, the same register, one bit apart** -- and unlike
V70/V71's zero-reader mirrors, `gp-0x6bd0` has FIVE real readers including the 1 kHz aggregator. A
slip would write a live lane. The opcode field is asserted BY VALUE in the builder, in the readback
and in the verifier.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent 68 of the proven 68 B -- unchanged, flown 10x
(V55/V57/V58/V59/V64/V65/V66/V67/V70/V71, all clean). 🛑 ZERO spare. Growing a cave is this kit's
ONLY bricking class (V24, V27 and V48B all bricked the ECU).

🛑 THE DISCLOSED RISKS -- stated, not bounded away. NO POINTWISE-BOUND CLAIM IS MADE.
--------------------------------------------------------------------------------------
Earlier cuts of this build asserted `V72 <= V62` and `V72 <= V70` pointwise. **Both are FALSE for
this spec** -- V72's r24 reaches 3.414x at rate 3000 where V62 is 2.000x -- and they must not appear.
What replaces them is a measured association and three honest risks:
  ★★ THE TWO-LANE RULE, 6 builds, no exceptions [EVIDENCE, gains read from the shipped images]:
     creep grind #2 requires r24 high-rate >~ 3.4x **AND** r26 high-rate >~ 1.5x; cutting EITHER
     kills it. stock/V69/V70 (1.000, 1.000) none · V71B (1.000, 2.000) none · V62/V65 (3.414, 2.000)
     worst in corpus · V71C (3.414, 1.500) 3 events · **V67/V68 (3.414, 0.250) none** · **V72
     (3.414, 0.250) -- V67/V68's exact row.** ⚠ [EVIDENCE] for the association; the "product of the
     two lanes" mechanism is [BELIEF].
  🛑 RISK 1: V67/V68's clean grind-#2 cell is the WEAKEST evidence in that table -- ~42 s of engaged
     creep, so its rate of 0 gives P(0) = 1.000 against any reference. The protective value of the
     r26 cut is associated, not established.
  🛑 RISK 2: V71C carries the SAME r24 arm (5244) and produced grind #2 at V62's own rate -- 7 bursts
     / 485 s engaged, 3 / 62.7 s at creep. The ONLY difference from V72 on that lane is r26.
  🛑 RISK 3: V72 IS UNGATED, and grind #2 follows the GATE, not the driver's hands: V62/V65 were
     ungated and burst in BOTH arms at equal rates (0.0444/s engaged vs 0.0430/s manual); V71C is
     gated and burst ONLY engaged. ⇒ **if V72 produces grind #2 it will produce it in MANUAL too.**
     That is the price of the highway fix; it is not jointly avoidable with calibration-only edits,
     and the operator has authorised manual-feel changes.
  ⊕ The direct high-rate test that was the red team's open hole: V71B is the corpus's ONLY high-rate
     dose on either lane, and over 21.8 s of engaged high-rate exposure its 40-49 Hz p90 is 58.5
     [55.1, 60.1] against stock's 77.4 in the same cell -- a high-rate dose on r26 moved NOTHING.
     ⚠ count test P(0) = 0.081 (marginal); the LEVEL test is not (58.5 vs V62/V65's 1441.9, 24x
     non-overlapping). ⚠ Route 54 had ZERO manual high-rate exposure, so the ungated half of that
     question is EMPTY, not null.
  ⚠ Highway grind #2 is NOT cleared on any build; V72 is structurally 1.000x at >=50 km/h, which is
     the intended fix, and it needs highway exposure to test.
⚠ 🛑 The "grind #2 IS grind #1's 2nd harmonic" result was RETRACTED in-session (a ratio is not a
  tracking test; a shuffle control reproduced it, and every tracking slope contains 0 and excludes
  2.0). It is NOT written into this build's rationale.

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
# LEVER A -- both rate lanes, the WHOLE rate axis, at the 0 and 10 km/h records
# =====================================================================================================
REC_B0, REC_B1 = V69.REC0, V69.REC1                 # 0xD2A74 / 0xD2AB0  gain_B mode-10, 0 / 10 km/h
REC_B_HWY = (0xD2AEC, 0xD2B28)                      # 50 / 100 km/h -- MUST REMAIN STOCK
REC_A0, REC_A1 = B.RATE_A_RECORDS[0], B.RATE_A_RECORDS[1]     # 0xC6A68 / 0xC6A7C  gain_A
REC_A_HWY = B.UNTOUCHED_A_RECS                      # 0xC6A90 / 0xC6AA4 -- MUST REMAIN STOCK
Y_OFF, REC_STRIDE = 0x0A, 0x14

V67_ARM_R24, V67_ARM_R26 = 5244, 512        # V67/V68's own arm values (0xC6446 / 0xC6444), verbatim
LEVER_A_FINAL_Y = {
    REC_B0: ([V67_ARM_R24] * 4, "gain_B mode-10 rec0 (0 km/h)   r24"),
    REC_B1: ([V67_ARM_R24] * 4, "gain_B mode-10 rec1 (10 km/h)  r24"),
    REC_A0: ([V67_ARM_R26] * 4, "gain_A rec0 (0 km/h)           r26"),
    REC_A1: ([V67_ARM_R26] * 4, "gain_A rec1 (10 km/h)          r26"),
}
LEVER_A_STOCK_Y = {REC_B0: [3072, 3072, 2322, 1536], REC_B1: [2561, 2561, 2247, 1947],
                   REC_A0: [3072, 3072, 2434, 2048], REC_A1: [3072, 3072, 2488, 1536]}
GAIN_B_PTR_ARRAYS = LM.GAIN_B_PTR_ARRAYS    # 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214
MODE = LM.MODE_DEFAULT                      # 10
MODE_NEIGHBOURS = (0xD2A88, 0xD2A9C)        # mode 11 / mode 12 record-0 -- byte-identical to mode 10

# =====================================================================================================
# LEVER B -- the base-assist damper, opened at creep. 10 cells = 20 bytes.
# =====================================================================================================
FACTOR_C = {10: 0xD27BC, 11: 0xD27D0, 12: 0xD27E4}
FACTOR_E = {10: 0xD27F8, 11: 0xD280C, 12: 0xD2820}
FACTOR_C_STOCK_Y = {10: [0, 235, 430, 877], 11: [0, 234, 431, 877], 12: [0, 234, 429, 908]}
FACTOR_E_STOCK_Y = {10: [0, 140, 539, 927], 11: [0, 140, 539, 927], 12: [0, 140, 539, 927]}
FACTOR_C_X = [2240, 3840, 5120, 8960]       # counts; /64 = [35, 60, 80, 140] km/h EXACTLY
FACTOR_E_X = [60, 400, 2500, 4000]          # counts of |motor rate|
SPEED_COUNTS_PER_KMH = 64
FACTORC_ONSET_COUNTS = FACTOR_C_X[0]        # 2240 = 35 km/h -- below this stock damping is ZERO

# ★ FactorC takes its OWN Y[2]; FactorE takes its OWN Y[3]. Largest values that keep each record
# MONOTONE NON-DECREASING -- both properties asserted below, not chosen and hoped for.
LEVER_B = {
    0xD27C6: (0, 430, "FactorC m10 Y[0]"), 0xD27C8: (235, 430, "FactorC m10 Y[1]"),
    0xD27DA: (0, 431, "FactorC m11 Y[0]"), 0xD27DC: (234, 431, "FactorC m11 Y[1]"),
    0xD2802: (0, 927, "FactorE m10 Y[0]"), 0xD2804: (140, 927, "FactorE m10 Y[1]"),
    0xD2806: (539, 927, "FactorE m10 Y[2]"),
    0xD2816: (0, 927, "FactorE m11 Y[0]"), 0xD2818: (140, 927, "FactorE m11 Y[1]"),
    0xD281A: (539, 927, "FactorE m11 Y[2]"),
}
EDITED_FACTOR_MODES = (10, 11)

# 🛑 NOT TOUCHED, and lockstep-checked to DTC 0x1d if they ever disagree.
CEILING_REC = (0xD209C, 12)                 # a 2-POINT record: count 2, X=[300,800], Y=[512,1024]
CEILING_X, CEILING_Y = [300, 800], [512, 1024]
CEILING_FLOAT_TWIN = (0xC6554, 8)           # 300.0f, 800.0f
CEILING_FALLBACK = (0xC6158, 512)           # used when gp-0x6ac2 fails its plausibility gate
CEILING_FLOOR = CEILING_Y[0]                # 512 -- the clamp that binds at low gp-0x6ac2
Q10 = 1024

# =====================================================================================================
# LEVER C -- the damper's weight into FUN_00038148
# =====================================================================================================
DAMP_WEIGHT_ADDR, DAMP_WEIGHT_STOCK, DAMP_WEIGHT_NEW = 0xC63A0, 1024, 2048
DAMP_WEIGHT_READER = 0x381AC                # `ld.hu 0x73a0[tp],r9` -- the ONLY reader image-wide
DAMP_WEIGHT_TP_DISP = 0x73A0
TP = LM.TP

# =====================================================================================================
# MUST REMAIN BYTE-STOCK -- asserted by value, because a span check passes on the wrong build
# =====================================================================================================
GATE_ADDR, GATE_DEAD = A.REPOINT_BYTE, A.GATE_DEAD          # 0x3AA96 -> 0xC5 (gp-0x683c, 0 writers)
GATE_LOAD = (A.REPOINT_ADDR, bytes.fromhex("847fc597"))     # `ld.bu -0x683c[gp],r15`
ARMS_STOCK = ((0xC643E, 1536), (0xC6440, 2048), (0xC6442, 1024), (0xC6444, 512), (0xC6446, 512))
ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
RATCHET_ADDR = A.RATCHET_ADDR               # 0x454FE -- carried, inert, UNTESTED

# =====================================================================================================
# THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT

W_LIVE = 0x10           # -> bit7  LIVENESS (folded into the initial movea)
W_A512 = 0x08           # -> bit6  gp-0x69a4 >= 512
W_A1024 = 0x04          # -> bit5  gp-0x69a4 >= 1024   ★ bit5 => bit6, a MONOTONE invariant
W_DAMPABS = 0x02        # -> bit4  |gp-0x6bd0| >= 64, TWO-SIDED
W_RATE512 = 0x01        # -> bit3  gp-0x6ac0 >= 512
PAYLOAD_SHIFT = 3
BIT_LIVE, BIT_A512 = W_LIVE << PAYLOAD_SHIFT, W_A512 << PAYLOAD_SHIFT
BIT_A1024 = W_A1024 << PAYLOAD_SHIFT
BIT_DAMPABS, BIT_RATE512 = W_DAMPABS << PAYLOAD_SHIFT, W_RATE512 << PAYLOAD_SHIFT

A_DISP = 0x69A4                 # `a`  -- ld.hu, UNSIGNED halfword (0x3AB3A reads it the same way)
DAMP_DISP = 0x6BD0              # the base-assist damper output -- ld.h, SIGNED
RATE_DISP = 0x6AC0              # |motor rate| -- ld.hu, UNSIGNED

A_SHIFT = 9                                 # sar 0x9 ; be +4  (branches on the SAR's OWN Z flag)
A_THRESHOLD = 1 << A_SHIFT                  # 512
A2_LEVEL = 2                                # cmp 0x2 ; blt +4
A2_THRESHOLD = A2_LEVEL << A_SHIFT          # 1024
D_SHIFT, D_LEVEL, D_NEG_LEVEL = 6, 1, -1    # sar 0x6 ; cmp 0x1 / cmp -0x1
D_THRESHOLD = D_LEVEL << D_SHIFT            # +64
D_NEG_THRESHOLD = (D_NEG_LEVEL << D_SHIFT) - 1      # -65.  `sar` FLOORS -- see _wire_model()
R_SHIFT = 9                                 # sar 0x9 ; be +4
R_THRESHOLD = 1 << R_SHIFT                  # 512
RATE_SCALE_CTS_PER_DEGS = 4.7121            # the settled column-rate scale, three ways
PREREG_BIT3_DUTY = 2.750                    # 📋 percent engaged, 9,497 / 345,396 frames
COND_BLT, COND_BGE, COND_BE = V65.COND_BLT, V55.COND_BGE, 0x2

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
PIN_LDHU_6AC0 = (0x45780, bytes.fromhex("e4374195"))       # BYTE-IDENTICAL (4 instances image-wide)
PIN_LDH_HW1 = (0x3ACA8, bytes.fromhex("24372c95"))         # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_HW1_ALT = (0x453E0, bytes.fromhex("24376c94"))     # hw1 donor #2, different cell
PIN_LDH_6BD0_DISP = (0x34726, bytes.fromhex("243f3094"))   # hw2 donor: `ld.h -0x6bd0[gp],r7`
PIN_STH_6BD0 = (0x34730, bytes.fromhex("64373094"))        # 🛑 THE ONE-BIT TWIN: st.h, SAME reg/disp
PIN_SAR9_R6 = (0x3E60C, bytes.fromhex("a932"))             # `sar 0x9,r6`   -- Ghidra-confirmed
PIN_SAR6_R6 = (0x2401A, bytes.fromhex("a632"))             # `sar 0x6,r6`
PIN_CMP_1_R6 = (0x14D46, bytes.fromhex("6132"))            # `cmp 0x1,r6`
PIN_CMP_2_R6 = (0x19304, bytes.fromhex("6232"))            # `cmp 0x2,r6`   -- Ghidra-confirmed
PIN_CMP_M1_R6 = (0x1BC24, bytes.fromhex("7f32"))           # `cmp -0x1,r6`
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))             # `shl 0x3,r7`   -- V31P FLASHED it 4x
PIN_ADD_R7 = {1: (0x15404, bytes.fromhex("413a")),
              2: (0x27EF0, bytes.fromhex("423a")),
              4: (0x2688E, bytes.fromhex("443a")),         # Ghidra-confirmed
              8: (0x17CD8, bytes.fromhex("483a"))}
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))                # `blt +4`
PIN_BGE4 = (0x244CE, bytes.fromhex("ae05"))                # `bge +4`
PIN_BGE6 = (0x6B176, bytes.fromhex("be05"))                # `bge +6`
PIN_BE4 = (0x5B38, bytes.fromhex("a205"))                  # `be +4`  -- Ghidra-confirmed
PIN_BE6 = (0x3ABFC, bytes.fromhex("c205"))                 # ⚠ the TWIN of `bge +6` (be05)
# 🛑 THE ARCHITECTURAL PIN: `sar imm5,rN` sets Z and the NEXT instruction branches on it, no `cmp`.
PIN_SAR_THEN_BCOND = (0x318DA, bytes.fromhex("a942fa75"))  # `sar 0x9,r8` ; `bne 0x319CA`

# ⚠ DELIBERATELY SHORT. V71A's note records the same trap: a fuller name overran Windows' 260-char
# path limit and the .rwd write failed AFTER the image had been written. The length is asserted
# BEFORE anything is written (see build()), not at the point of use.
TAG = ("A-WHOLEAXIS-r24_5244-r26_512-V67CREEP-hwy1x-B-FactorCE-430_927-"
       "C-63A0x2-454FE-probe-a512-a1024-damp-rate512")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V72-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v72_plain_image.bin"))
SRC_BIN = plain_image_path("_v70_plain_image.bin")
V67_BIN = plain_image_path("_v67_plain_image.bin")
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
    r6 = (v69a4 & 0xFFFF) >> A_SHIFT                # ld.hu (ZERO-extends) ; sar 0x9  -- SETS Z
    if r6 != 0:                                     # be +4   <- reads the SAR's OWN Z flag
        r7 += W_A512
    if not (r6 < A2_LEVEL):                         # cmp 0x2,r6 ; blt +4
        r7 += W_A1024
    r6 = _s16(v6bd0) >> D_SHIFT                     # ld.h ; sar 0x6  (Python >> floors == `sar`)
    # 🛑 THE TWO-SIDED TEST, as CONTROL FLOW, not as a formula:
    #     cmp 0x1,r6  ; bge SET      -- s >=  1  => x is large POSITIVE
    #     cmp -0x1,r6 ; bge SKIP     -- s >= -1  => |x| is small; skip
    #                   fall through => SET       -- s <= -2  => x is large NEGATIVE
    if (r6 >= D_LEVEL) or not (r6 >= D_NEG_LEVEL):
        r7 += W_DAMPABS
    r6 = (v6ac0 & 0xFFFF) >> R_SHIFT                # ld.hu ; sar 0x9  -- SETS Z
    if r6 != 0:                                     # be +4
        r7 += W_RATE512
    r7 <<= PAYLOAD_SHIFT                            # shl 0x3,r7
    return (r7 & 0xFF) | (status_bits & PAYLOAD_KEEP_MASK)


# ★ bit5 => bit6 is STRUCTURAL, so only 3 of the 4 (bit6,bit5) combinations are reachable.
LEGAL_PAYLOADS = {BIT_LIVE | a | b | c
                  for a in (0, BIT_A512, BIT_A512 | BIT_A1024)
                  for b in (0, BIT_DAMPABS) for c in (0, BIT_RATE512)}


def _wire_model():
    """The rungs' semantics, exhaustively: every halfword pattern."""
    # ---- bit6 and bit5, over ALL 65,536 patterns, plus the monotone invariant -------------------
    for raw in range(0x10000):
        b = wire_byte4(raw, 0, 0)
        assert bool(b & BIT_A512) == (raw >= A_THRESHOLD), \
            f"bit6 is not `gp-0x69a4 >= {A_THRESHOLD}` at {raw}"
        assert bool(b & BIT_A1024) == (raw >= A2_THRESHOLD), \
            f"bit5 is not `gp-0x69a4 >= {A2_THRESHOLD}` at {raw}"
        assert not (b & BIT_A1024) or (b & BIT_A512), \
            f"the bit5 => bit6 MONOTONE INVARIANT is violated at {raw}"
    assert not wire_byte4(511, 0, 0) & BIT_A512 and wire_byte4(512, 0, 0) & BIT_A512, \
        "bit6 does not switch exactly between 511 and 512"
    assert not wire_byte4(1023, 0, 0) & BIT_A1024 and wire_byte4(1024, 0, 0) & BIT_A1024, \
        "bit5 does not switch exactly between 1023 and 1024"
    # 🛑 `sar` vs `shr` on the zero-extended operand: the cave emits `sar` because `shr 0x9,r6` has
    # NO donor in the stock image and `sar 0x9,r6` does (0x3E60C). Legitimate ONLY because ld.hu
    # makes the operand non-negative -- proven here, not assumed.
    assert all((raw >> A_SHIFT) >= 0 for raw in range(0x10000)), \
        "a zero-extended operand went negative -- `sar` would stop equalling `shr`"

    # ---- bit4, over ALL 65,536 halfword patterns, including the one-count asymmetry --------------
    for raw in range(0x10000):
        x = _s16(raw)
        assert bool(wire_byte4(0, raw, 0) & BIT_DAMPABS) == \
            (x >= D_THRESHOLD or x <= D_NEG_THRESHOLD), \
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

    # ---- bit3, over ALL 65,536 patterns ----------------------------------------------------------
    for raw in range(0x10000):
        assert bool(wire_byte4(0, 0, raw) & BIT_RATE512) == (raw >= R_THRESHOLD), \
            f"bit3 is not `gp-0x6ac0 >= {R_THRESHOLD}` at {raw}"
    assert not wire_byte4(0, 0, 511) & BIT_RATE512 and wire_byte4(0, 0, 512) & BIT_RATE512, \
        "bit3 does not switch exactly between 511 and 512"
    assert R_THRESHOLD >= 400, \
        "bit3's threshold is below the 400 HARD FLOOR -- at 250 the retired 8x-smaller scale fires " \
        "(0.058%) and the rung stops discriminating between the two axis scales"

    # ---- 🛑 THE SHIFT MUST NEVER REACH THE PRESERVED STATUS BITS ---------------------------------
    reachable_r7 = {W_LIVE + a + b + c
                    for a in (0, W_A512, W_A512 + W_A1024)
                    for b in (0, W_DAMPABS) for c in (0, W_RATE512)}
    assert max(reachable_r7) == 0x1F and min(reachable_r7) == W_LIVE
    for r7 in reachable_r7:
        assert (r7 << PAYLOAD_SHIFT) <= 0xF8, f"r7 = 0x{r7:02X} shifts past the byte"
        assert (r7 << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
            f"r7 = 0x{r7:02X} shifts INTO the preserved status bits -- the wire would be corrupted"
    assert (W_LIVE << PAYLOAD_SHIFT) == 0x80, \
        "the seed does NOT land on bit7 after the shift -- the VOID sentinel would be broken"
    for status in range(8):
        for inputs in ((0, 0, 0), (0xFFFF, 0x7FFF, 0xFFFF), (512, 0xFF00, 512)):
            assert wire_byte4(*inputs, status_bits=status) & PAYLOAD_KEEP_MASK == status, \
                "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
    reach = {wire_byte4(a, d, r) & 0xF8
             for a in (0, 511, 512, 1023, 1024, 0xFFFF)
             for d in (0, 0x0100, 0xFF00, 0x7FFF) for r in (0, 511, 512, 0xFFFF)}
    assert reach <= LEGAL_PAYLOADS, f"the wire model reaches {reach - LEGAL_PAYLOADS}, outside LEGAL"
    assert len(LEGAL_PAYLOADS) == 12, \
        f"{len(LEGAL_PAYLOADS)} legal payloads, expected 12 (bit5 => bit6 forbids 4 of 16)"
    assert all(p & BIT_LIVE for p in LEGAL_PAYLOADS), "a legal payload lacks the liveness bit"
    assert not any((p & BIT_A1024) and not (p & BIT_A512) for p in LEGAL_PAYLOADS), \
        "a legal payload has bit5 set with bit6 clear -- the monotone invariant must forbid it"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    """
    V65._self_check_encoders()               # chains down through V59/V58/V57/V55/V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVEA_10_R7, PIN_LDHU_69A4, PIN_LDHU_6AC0, PIN_LDH_HW1, PIN_LDH_HW1_ALT,
            PIN_LDH_6BD0_DISP, PIN_STH_6BD0, PIN_SAR9_R6, PIN_SAR6_R6, PIN_CMP_1_R6,
            PIN_CMP_2_R6, PIN_CMP_M1_R6, PIN_SHL3_R7, PIN_BLT4, PIN_BGE4, PIN_BGE6,
            PIN_BE4, PIN_BE6, PIN_SAR_THEN_BCOND]
    pins += list(PIN_ADD_R7.values())
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # 🛑 THE ARCHITECTURAL CLAIM, PINNED: `sar imm5,rN` sets Z and the NEXT halfword is a Bcond that
    # reads it, with NO intervening `cmp`. Ghidra-confirmed at 0x318DA (and Honda repeats the idiom
    # at 0x318E2 and 0x318EA). Decoded here rather than trusted as a byte blob.
    _sar, _bc = struct.unpack("<HH", PIN_SAR_THEN_BCOND[1])
    assert ((_sar >> 5) & 0x3F) == 0x15, "the sar->Bcond donor's first halfword is not a `sar`"
    assert (_sar & 0x1F) == A_SHIFT, f"the donor's shift is {_sar & 0x1F}, not 0x{A_SHIFT:x}"
    assert ((_bc >> 7) & 0xF) == 0xB, "the donor's second halfword is not a Bcond"
    assert (_bc & 0xF) in (COND_BE, 0xA), "the donor's Bcond is not be/bne -- it does not test Z"

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
    # firmware's own `st.h r6,-0x6bd0[gp]` @0x34730 carries the SAME register and displacement.
    # gp-0x6bd0 has FIVE real readers, so a slip WRITES a live 1 kHz lane.
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
    assert V55.sar(D_SHIFT, R6) != FF.shr(D_SHIFT, R6), \
        "bit4's shift collapsed onto a LOGICAL shr -- every negative damper value would read huge"
    assert V55.cmp_imm5(D_LEVEL, R6) == PIN_CMP_1_R6[1], "cmp 0x1,r6 encoding changed"
    assert V55.cmp_imm5(A2_LEVEL, R6) == PIN_CMP_2_R6[1], "cmp 0x2,r6 != the real one @0x19304"
    assert V55.cmp_imm5(D_NEG_LEVEL, R6) == PIN_CMP_M1_R6[1], "cmp -0x1,r6 != the real one @0x1BC24"
    assert decode_fmt2(struct.unpack("<H", PIN_CMP_M1_R6[1])[0])["imm5"] == 0x1F, \
        "cmp -0x1 does not encode as imm5 0x1F"
    assert FF.bcond(COND_BLT, +4) == PIN_BLT4[1], "blt +4 != the real one @0x290A8"
    assert FF.bcond(COND_BGE, +4) == PIN_BGE4[1], "bge +4 != the real one @0x244CE"
    assert FF.bcond(COND_BGE, +6) == PIN_BGE6[1], "bge +6 != the real one @0x6B176"
    assert FF.bcond(COND_BE, +4) == PIN_BE4[1], "be +4 != the real one @0x5B38"
    # 🛑🛑 THE CONDITION-NIBBLE TWINS. `be +4` = a205, `bge +4` = ae05, `blt +4` = a605 -- ONE NIBBLE
    # apart, and the wrong one INVERTS a rung silently. This kit has lost time to exactly that.
    assert len({FF.bcond(COND_BE, +4), FF.bcond(COND_BGE, +4), FF.bcond(COND_BLT, +4)}) == 3, \
        "two of be/bge/blt collapsed onto each other at +4"
    assert FF.bcond(COND_BE, +4) != FF.bcond(0xA, +4), "be collapsed onto its negation bne"
    assert FF.bcond(COND_BGE, +6) != PIN_BE6[1], "bge +6 collapsed onto `be +6` (b205 @0x3ABFC)"
    assert COND_BGE == 0xE and COND_BLT == 0x6 and COND_BE == 0x2 and COND_BGE != V55.COND_BL, \
        "a condition nibble moved, or bge collapsed onto the UNSIGNED bl"
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

    weights = (W_LIVE, W_A512, W_A1024, W_DAMPABS, W_RATE512)
    assert len(set(weights)) == 5 and all(w & (w - 1) == 0 for w in weights), "weights not distinct"
    assert sum(weights) == 0x1F, f"weights must occupy exactly bits 4:0, got 0x{sum(weights):02X}"
    assert sum(w << PAYLOAD_SHIFT for w in weights) == 0xF8, "payload bits are not exactly 7:3"
    _wire_model()


def build_cave():
    """pack_v72_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x10,r0,r7       ; r7 = 0x10   bit7 LIVENESS, in PRE-SHIFT weights
        ld.hu -0x69a4[gp],r6   ; `a` -- r26's own weight. UNSIGNED (byte-identical to 0x3AB3A)
        sar   0x9,r6           ; units of 512.  🛑 SETS Z -- the next branch reads it, no `cmp`
        be    +4               ; Z set => a < 512 -> skip
        add   0x8,r7           ; bit6 = gp-0x69a4 >= 512     ★★★★ THE UNMEASURED WEIGHT
        cmp   0x2,r6
        blt   +4
        add   0x4,r7           ; bit5 = gp-0x69a4 >= 1024    ★ bit5 => bit6, MONOTONE
      g1:
        ld.h  -0x6bd0[gp],r6   ; the base-assist damper output, SIGNED. 🛑 op MUST be 0x39
        sar   0x6,r6           ; ARITHMETIC: units of 64, sign preserved
        cmp   0x1,r6
        bge   +6               ; s >=  1  =>  x >= +64        -> SET
        cmp   -0x1,r6
        bge   +4               ; s >= -1  =>  |x| is small    -> SKIP
        add   0x2,r7           ; bit4 = |gp-0x6bd0| >= 64, TWO-SIDED   (fallthrough: s <= -2)
      g2:
        ld.hu -0x6ac0[gp],r6   ; |motor rate| -- the gain-scheduling index. UNSIGNED
        sar   0x9,r6           ; 🛑 SETS Z
        be    +4
        add   0x1,r7           ; bit3 = gp-0x6ac0 >= 512   📋 PRE-REGISTERED at 2.750%
      g3:
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
    r6_writers = []

    def emit(raw, text, writes_r6=False):
        if writes_r6:
            r6_writers.append(CAVE_BASE + len(body))
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(W_LIVE, R0, R7), "movea 0x10,r0,r7    ; bit7 LIVENESS (pre-shift weight 0x10)")

    # ---- bit6 + bit5: ONE load of `a`, shared -----------------------------------------------------
    emit(FF.ldhu(A_DISP, R6), f"ld.hu -0x{A_DISP:04x}[gp],r6 ; `a` = r26's own weight (UNSIGNED)",
         writes_r6=True)
    sar_a = len(listing)
    emit(V55.sar(A_SHIFT, R6), f"sar 0x{A_SHIFT:x},r6           ; units of {A_THRESHOLD}  🛑 SETS Z",
         writes_r6=True)
    br_a = len(listing)
    emit(FF.bcond(COND_BE, +4), "be +4               ; Z set => a < 512 -> skip (reads the sar's Z)")
    emit(add_imm5(W_A512, R7), f"add 0x{W_A512:x},r7          ; bit6 = gp-0x{A_DISP:04x} >= {A_THRESHOLD}")
    emit(V55.cmp_imm5(A2_LEVEL, R6), f"cmp 0x{A2_LEVEL:x},r6")
    br_a2 = len(listing)
    emit(FF.bcond(COND_BLT, +4), "blt +4              ; skip -> g1")
    emit(add_imm5(W_A1024, R7),
         f"add 0x{W_A1024:x},r7          ; bit5 = gp-0x{A_DISP:04x} >= {A2_THRESHOLD}   ★ bit5 => bit6")
    g1 = CAVE_BASE + len(body)

    # ---- bit4: ONE load, ONE shift, TWO signed bounds ---------------------------------------------
    emit(V55.ldh(DAMP_DISP, R6),
         f"ld.h -0x{DAMP_DISP:04x}[gp],r6 ; base-assist damper out (SIGNED). 🛑 op MUST be 0x39",
         writes_r6=True)
    emit(V55.sar(D_SHIFT, R6), f"sar 0x{D_SHIFT:x},r6           ; ARITHMETIC -- units of {D_THRESHOLD}",
         writes_r6=True)
    emit(V55.cmp_imm5(D_LEVEL, R6), f"cmp 0x{D_LEVEL:x},r6           ; the POSITIVE bound")
    br_hi = len(listing)
    emit(FF.bcond(COND_BGE, +6), f"bge +6              ; s >= {D_LEVEL} => x >= +{D_THRESHOLD} -> SET")
    emit(V55.cmp_imm5(D_NEG_LEVEL, R6), "cmp -0x1,r6         ; the NEGATIVE bound")
    br_lo = len(listing)
    emit(FF.bcond(COND_BGE, +4), f"bge +4              ; s >= {D_NEG_LEVEL} => small -> SKIP")
    emit(add_imm5(W_DAMPABS, R7),
         f"add 0x{W_DAMPABS:x},r7          ; bit4 = x >= +{D_THRESHOLD} or x <= {D_NEG_THRESHOLD}  TWO-SIDED")
    g2 = CAVE_BASE + len(body)

    # ---- bit3: the rate index ---------------------------------------------------------------------
    emit(FF.ldhu(RATE_DISP, R6), f"ld.hu -0x{RATE_DISP:04x}[gp],r6 ; |motor rate| (UNSIGNED)",
         writes_r6=True)
    sar_r = len(listing)
    emit(V55.sar(R_SHIFT, R6), f"sar 0x{R_SHIFT:x},r6           ; units of {R_THRESHOLD}  🛑 SETS Z",
         writes_r6=True)
    br_r = len(listing)
    emit(FF.bcond(COND_BE, +4), "be +4               ; Z set => rate < 512 -> skip")
    emit(add_imm5(W_RATE512, R7),
         f"add 0x{W_RATE512:x},r7          ; bit3 = gp-0x{RATE_DISP:04x} >= {R_THRESHOLD}  📋 PRE-REGISTERED")
    g3 = CAVE_BASE + len(body)

    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7          ; the 5-bit field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4",
         writes_r6=True)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0",
         writes_r6=True)
    emit(V54.or_rr(R7, R6), "or r7,r6", writes_r6=True)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp] ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction", writes_r6=True)
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- 🛑🛑 FLAG LIVENESS: each `sar` must be IMMEDIATELY followed by its own `be`. -------------
    # NEW to this kit and load-bearing: anything inserted between them would make the branch read the
    # PREVIOUS comparison's flags -- a silent, plausible-looking wrong answer.
    for sar_idx, br_idx, name in ((sar_a, br_a, "bit6"), (sar_r, br_r, "bit3")):
        assert br_idx == sar_idx + 1, \
            f"{name}: {br_idx - sar_idx - 1} instruction(s) sit between the `sar` and its `be` -- " \
            "the branch would read STALE flags"
        s_addr, s_raw, _ = listing[sar_idx]
        b_addr, b_raw, _ = listing[br_idx]
        assert s_addr + 2 == b_addr and len(s_raw) == 2, f"{name}: the sar/be pair is not adjacent"
        assert ((struct.unpack("<H", s_raw)[0] >> 5) & 0x3F) == 0x15, f"{name}: not a `sar`"
        assert struct.unpack("<H", b_raw)[0] & 0xF == COND_BE, \
            f"{name}: the flag branch is not `be` -- `bne` would INVERT the rung"

    # ---- GATE 2a: every branch lands EXACTLY on its label, located BY POSITION -------------------
    # ⚠ The label is the address of the instruction AFTER the setter (listing[br+2]), NOT
    # `branch address + 4` -- that form is self-referential and would pass on any displacement.
    for br_idx, label, cond, name in ((br_a, listing[br_a + 2][0], COND_BE, "bit6"),
                                      (br_a2, g1, COND_BLT, "bit5"),
                                      (br_r, listing[br_r + 2][0], COND_BE, "bit3")):
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a Bcond"
        assert addr + 4 == label, f"{name}: target 0x{addr + 4:05X} != label 0x{label:05X}"
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
    assert lo_addr + 4 == g2, f"bit4 low bound: `bge +4` @0x{lo_addr:05X} does not land on g2"
    for raw, which in ((hi_raw, "high"), (lo_raw, "low")):
        assert struct.unpack("<H", raw)[0] & 0xF == COND_BGE, \
            f"bit4 {which} bound is not `bge` (0x{COND_BGE:X}) -- the rung would invert"
        assert raw != PIN_BE6[1], f"bit4 {which} bound emitted `be` (b205), not `bge` (be05)"
    assert (g1, g2, g3) == (0xC4B48, 0xC4B58, 0xC4B62), \
        f"the cave geometry drifted: g1/g2/g3 = {hex(g1)}/{hex(g2)}/{hex(g3)}"

    # ---- GATE 2b: r6/r7 LIVENESS. Only a rung's own load/shift may write r6 ----------------------
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
    # 🛑 bit5's `cmp` reads r6 two instructions after bit6's `sar`, and bit4's negative bound reads
    # it three after its own. Both windows are asserted, not assumed.
    for lo_i, hi_i, what in ((sar_a + 1, br_a2, "bit6's shift and bit5's test"),
                             (br_hi - 1, br_lo, "bit4's shift and its second bound")):
        for idx in range(lo_i, hi_i + 1):
            _a, raw, text = listing[idx]
            hw = struct.unpack_from("<H", raw, 0)[0]
            assert (len(raw) == 2 and raw[1] == 0x05) or ((hw >> 5) & 0x3F) in (0x13, 0x0F) \
                or (hw >> 11) == R7, f"'{text}' clobbers r6 between {what}"
    for disp, mk in ((A_DISP, FF.ldhu(A_DISP, R6)), (RATE_DISP, FF.ldhu(RATE_DISP, R6)),
                     (DAMP_DISP, V55.ldh(DAMP_DISP, R6))):
        assert sum(1 for _, r, _ in listing if r == mk) == 1, f"gp-0x{disp:04x} is loaded != once"
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
    assert len(body) == 4 + 16 + 16 + 10 + 2 + 20 == 68, \
        f"the cave is {len(body)}B, the budget says 68 " \
        "(seed 4 + bit6/bit5 16 + bit4 16 + bit3 10 + shl 2 + tail 20)"
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
            n = 2
            m = {0x6: "blt", 0xE: "bge", 0xA: "bne", 0x2: "be"}.get(hw & 0xF, f"b?{hw & 0xF:x}")
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
        f"🛑 tp+0x{d:04X} readers are {[hex(a) for a, _ in real]}, expected exactly " \
        f"[0x{DAMP_WEIGHT_READER:05X}]. MORE THAN ONE READER ⇒ DROP LEVER C AND REPORT."
    return len(hits_odd), real


def damper_authority(buf, mode=10, speed_counts=0, rate=0):
    """The delivered |gp-0x6bd0|, mirroring FUN_00034350's Q10 chain EXACTLY.

        gp-0x6bd0 = sign(-gp-0x6abe) * ((((seed*B)>>10)*C)>>10)*D)>>10)*E)>>10, clamped to +/-ceiling

    seed = MIN(gp-0x698a, 1024) -- the MAXIMUM-authority assumption is seed = 1024.
    FactorB (0xD2738) and FactorD (0xD2774) are FLAT 1024 = inert, so they drop out.
    FactorC is keyed on VOTED SPEED (0xC6010's 64 counts/km/h axis); FactorE on |motor rate|.
    """
    c = LM.lerp_int(speed_counts, rec_x(buf, FACTOR_C[mode]), rec_y(buf, FACTOR_C[mode]))
    e = LM.lerp_int(rate, rec_x(buf, FACTOR_E[mode]), rec_y(buf, FACTOR_E[mode]))
    v = (Q10 * Q10) >> 10                                      # seed * FactorB
    v = (v * c) >> 10
    v = (v * Q10) >> 10                                        # * FactorD
    return (v * e) >> 10


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
            "checked at 5/1024 and escalate to DTC 0x1d HARD SHUTDOWN"
    assert u16(buf, CEILING_FALLBACK[0]) == CEILING_FALLBACK[1], f"{label}: 0xC6158 moved"
    assert rec_y(buf, FACTOR_C[12]) == FACTOR_C_STOCK_Y[12], f"{label}: FactorC mode 12 moved"
    assert rec_y(buf, FACTOR_E[12]) == FACTOR_E_STOCK_Y[12], f"{label}: FactorE mode 12 moved"
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
    for name, val in (("A_THRESHOLD", A_THRESHOLD), ("A2_THRESHOLD", A2_THRESHOLD),
                      ("D_THRESHOLD", D_THRESHOLD), ("D_NEG_THRESHOLD", D_NEG_THRESHOLD),
                      ("R_THRESHOLD", R_THRESHOLD)):
        assert re.search(rf"^{name}\s*=\s*{val}\b", txt, re.M), \
            f"V72: the decoder's {name} is not {val}"
    # ⚠ Parse the VALUE, don't regex the literal: `f"{2.750}"` renders "2.75" and would never match
    # the decoder's "2.750". A formatting mismatch must not read as a spec mismatch.
    m = re.search(r"^PREREG_BIT3_DUTY\s*=\s*([0-9.]+)", txt, re.M)
    assert m and float(m.group(1)) == PREREG_BIT3_DUTY, \
        f"V72: the decoder's bit3 pre-registration is {m and m.group(1)}, not {PREREG_BIT3_DUTY}%"
    for disp in (A_DISP, DAMP_DISP, RATE_DISP):
        assert f"{disp:04X}" in txt.upper(), f"V72: gp-0x{disp:04x} is missing from the decoder"
    for stale in (0x6ADA, 0x6ADC, 0x671D, 0x67FA):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale:04X}", txt, re.M | re.I), \
            f"V72: gp-0x{stale:04x} is still a LIVE RUNG in the decoder"
    for claim in ("MONOTONE", "TWO-SIDED"):
        assert claim in txt.upper(), f"V72: the decoder never states '{claim}'"
    # 🛑 the decoder must NOT carry the retracted harmonic claim, and MUST carry the corrected
    # 0x454FE status. Both were wrong in an earlier cut of this build's own paperwork.
    assert "2nd harmonic" not in txt, \
        "V72: the decoder repeats the RETRACTED 'grind #2 is grind #1's 2nd harmonic' claim"
    assert "UNTESTED" in txt, "V72: the decoder does not describe 0x454FE as carried-and-UNTESTED"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")

    # 🛑 CHECKED BEFORE ANYTHING IS WRITTEN. V71A's note records the failure mode: an over-long tag
    # made the .rwd write fail AFTER the plain image had already been written, leaving a snapshot on
    # disk with no flashable artefact beside it. This assert used to sit next to the write; it does
    # not any more.
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it. Shorten TAG " \
        "BEFORE building; nothing has been written yet."

    src = Path(SRC_BIN)
    v70 = bytearray(src.read_bytes())
    v67 = Path(V67_BIN).read_bytes()
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V70): {src}\n  SHA256 {hashlib.sha256(bytes(v70)).hexdigest()}")
    print(f"REFERENCE:    {V67_BIN}  (the configuration V72 reproduces at creep)")
    print(f"STOCK:        {STOCK_BIN}")

    for name, img in (("V70", v70), ("V67", v67), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    A.assert_ratchet_edit(v70, "V70 source", expect_edited=False)
    A.assert_no_external_entry(v70)
    assert_untouched(v70, "V70 source", stock)
    for lo, hi, what in A.STOCK_IDENTICAL_SPANS:
        assert not [i for i in range(lo, hi) if v70[i] != stock[i]], \
            f"[0x{lo:05X},0x{hi:05X}) ({what}) differs from stock"
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
    for base, want in LEVER_A_STOCK_Y.items():
        assert rec_y(stock, base) == want, f"stock record 0x{base:05X} Y is {rec_y(stock, base)}"
    for m in EDITED_FACTOR_MODES:
        assert rec_y(v70, FACTOR_C[m]) == FACTOR_C_STOCK_Y[m], f"V70 FactorC m{m} is not stock"
        assert rec_y(v70, FACTOR_E[m]) == FACTOR_E_STOCK_Y[m], f"V70 FactorE m{m} is not stock"
        assert rec_x(v70, FACTOR_C[m]) == FACTOR_C_X and rec_x(v70, FACTOR_E[m]) == FACTOR_E_X, \
            f"the FactorC/E X rows moved on mode {m}"
    print("\n  ✅ [EVIDENCE, byte-read] LEVER B's cells are STOCK on V70 ⇒ the base-assist damper is "
          "OFF the car.")
    print(f"     FactorC X = {FACTOR_C_X} counts = "
          f"{[x // SPEED_COUNTS_PER_KMH for x in FACTOR_C_X]} km/h at "
          f"{SPEED_COUNTS_PER_KMH} counts/km/h ⇒ the LERP clamps FLAT to Y[0] = 0 below 35 km/h.")
    assert u16(v70, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_STOCK, "0xC63A0 is not 1024 on the source"
    assert u16(v67, 0xC6446) == V67_ARM_R24 and u16(v67, 0xC6444) == V67_ARM_R26, \
        "V67 does not carry the (5244, 512) arms -- LEVER A's provenance claim is wrong"

    code = bytearray(v70)

    # ---- EDIT 1 -- LEVER A ------------------------------------------------------------------------
    print("\n  EDIT 1 -- LEVER A: BOTH rate lanes, the WHOLE rate axis, at 0 and 10 km/h:")
    for base, (want_y, label) in LEVER_A_FINAL_Y.items():
        before = rec_y(code, base)
        struct.pack_into("<4h", code, base + Y_OFF, *want_y)
        assert rec_y(code, base) == want_y, f"{label}: record 0x{base:05X} did not take its final Y"
        assert len(set(want_y)) == 1, \
            f"{label}: the record is not FLAT -- a flat record is what reproduces a scalar arm"
        print(f"    0x{base + Y_OFF:05X}  {before} -> {want_y}   {label}")
    print(f"    ✅ {V67_ARM_R24} and {V67_ARM_R26} are V67/V68's OWN arm values (0xC6446 / 0xC6444 on")
    print("       `_v67_plain_image.bin`), used VERBATIM -- asserted against the V67 image, not quoted.")

    # ---- EDIT 2 -- LEVER B ------------------------------------------------------------------------
    print("\n  EDIT 2 -- LEVER B: the base-assist damper opened at creep (10 cells = 20 bytes):")
    for addr, (old, new, label) in sorted(LEVER_B.items()):
        assert u16(code, addr) == old, \
            f"{label} @0x{addr:05X} is {u16(code, addr)}, expected the stock {old}"
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   {label}")
    print("\n    RESULTING RECORDS, and the MONOTONICITY they must satisfy:")
    for tbl, name, stock_y, xs in ((FACTOR_C, "FactorC", FACTOR_C_STOCK_Y, FACTOR_C_X),
                                   (FACTOR_E, "FactorE", FACTOR_E_STOCK_Y, FACTOR_E_X)):
        for m in EDITED_FACTOR_MODES:
            ys = rec_y(code, tbl[m])
            assert rec_x(code, tbl[m]) == xs, f"{name} m{m}: the X row moved -- only Y may change"
            assert all(b >= a for a, b in zip(ys, ys[1:])), \
                f"🛑 {name} m{m} Y = {ys} is NOT monotone non-decreasing -- a dip in the middle of a " \
                "gain schedule is a defect, and it is what killed the 877/927 candidate"
            assert all(0 <= y < 0x8000 for y in ys), f"{name} m{m}: a Y is not a positive short"
            assert ys[-1] == stock_y[m][-1], f"{name} m{m}: Y[3] moved -- only Y[0..2] may change"
            print(f"      {name} m{m}  {stock_y[m]} -> {ys}   monotone ✅")

    # ---- the delivered damping authority, and the CEILING it must respect -------------------------
    print("\n  DELIVERED DAMPING AUTHORITY, mirroring FUN_00034350's Q10 chain "
          f"(seed = {Q10}, FactorB/D inert):")
    creep = damper_authority(code, 10, speed_counts=0, rate=0)
    creep11 = damper_authority(code, 11, speed_counts=0, rate=0)
    # 🛑 SCOPE THE CLAIM. The region V72 NEWLY OPENS is speed < FactorC's X[0] = 35 km/h, where stock
    # delivers a HARD ZERO. That is where the no-clip guarantee has to hold.
    opened = [damper_authority(code, m, v, r) for m in EDITED_FACTOR_MODES
              for v in range(0, FACTORC_ONSET_COUNTS + 1, 32) for r in range(0, 4001, 25)]
    grid_all = [(m, v, r) for m in EDITED_FACTOR_MODES
                for v in range(0, 9001, 64) for r in range(0, 4001, 50)]
    max_new = max(damper_authority(code, m, v, r) for m, v, r in grid_all)
    max_stock = max(damper_authority(stock, m, v, r) for m, v, r in grid_all)
    print(f"    creep, both LERPs at Y[0]  : m10 {creep:4d}   m11 {creep11:4d} counts "
          f"(stock: {damper_authority(stock, 10, 0, 0)})")
    print(f"    max over the OPENED region (< {FACTORC_ONSET_COUNTS // SPEED_COUNTS_PER_KMH} km/h, "
          f"every rate): {max(opened):4d} counts")
    print(f"    the ceiling is a 2-point LERP over gp-0x6ac2, X={CEILING_X} Y={CEILING_Y}, fallback "
          f"0xC6158 = {CEILING_FALLBACK[1]}")
    assert max(opened) < CEILING_FLOOR, \
        f"🛑 the opened region delivers {max(opened)}, at or above the ceiling FLOOR {CEILING_FLOOR} " \
        "⇒ the damper would SATURATE at low gp-0x6ac2, putting a hard-clipping element inside a " \
        "feedback loop at the frequency of a Q~40 resonance. That is the mechanism that CREATES " \
        "limit cycles; it is the hazard, not a safety feature."
    print(f"    ✅ {max(opened)} < the ceiling FLOOR {CEILING_FLOOR} ⇒ the damper NEVER saturates in "
          f"the region V72 opens ({100 * (1 - max(opened) / CEILING_FLOOR):.0f}% headroom), at every "
          "value of gp-0x6ac2.")
    assert max_new == max_stock, \
        f"V72's global max delivered authority {max_new} != stock's {max_stock} -- V72 must open the " \
        "low-speed region without raising the peak anywhere"
    print(f"    ✅ and V72 does NOT raise the GLOBAL peak: max over all speeds/rates is {max_new}, "
          f"IDENTICAL to STOCK's {max_stock}")
    print(f"    ⚠ SCOPE, STATED: a blanket 'max_delivered < {CEILING_FLOOR}' is FALSE at high speed "
          f"({max_new} at 140 km/h + high")
    print("      rate) -- but it is EQUALLY false on STOCK, where the ceiling LERP has itself risen "
          "to 1024, so it")
    print("      cannot be a V72 requirement. The correctly-scoped claim is the one asserted above.")
    print(f"    ✅ {creep} counts at creep is {creep / 160:.1f}x V47's 160 ⇒ the under-dose that was "
          "one of V47's four")
    print("       failure conditions is addressed, not repeated.")

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
    print(f"       ({n_odd} raw odd-parity occurrences; the non-instruction one is 0xC4764 -- no "
          "function, and 0xC4762 is")
    print("        not a disp16 load ⇒ data.) ⇒ NO MONITOR CAN BE CHECKING IT. That is why this lever "
          "was chosen over")
    print("       raising 0xD209C, whose float twin 0xC6554 IS lockstep-checked to DTC 0x1d.")

    # ---- EDIT 4 -- the carried ratchet byte -------------------------------------------------------
    print("\n  EDIT 4 -- 0x454FE CARRIED (🛑 currently INERT and UNTESTED -- not a fix, not falsified):")
    struct.pack_into("<H", code, RATCHET_ADDR, A.RATCHET_NEW_HW)
    A.assert_ratchet_edit(code, "V72", expect_edited=True)
    A.assert_no_external_entry(code)
    n_state = A.assert_governor_monitor_safety(code, "V72")
    print(f"    0x{RATCHET_ADDR:05X}  0x{A.RATCHET_STOCK_HW:04X} -> 0x{A.RATCHET_NEW_HW:04X}   "
          f"bne 0x455C4 -> br 0x455C4; FUN_0004595a safety re-derived ({n_state} state read)")
    print("    🛑 [EVIDENCE] V71's bit5 measured `gp-0x67fa == 4` at 0/123,277 frames (route 54) and")
    print("       8/92,826 (route 58) -- all eight one 80 ms burst at 0.00 km/h IN PARK. State 4 never")
    print("       occurred while driving ⇒ V42's substitution never ran ⇒ the V71B/V71C 'no change'")
    print("       result is a NULL BY CONSTRUCTION, not a falsification. An earlier cut of this file")
    print("       called it falsified; that was WRONG and is retracted.")
    print("    ⚠ [OPEN] The same measurement cuts both ways: V42 was confirmed on-car against the")
    print("      hard-turn recovery ratchet, and if state 4 never occurs that fix could not have")
    print("      acted either. Carried because reverting cannot help and might regress a confirmed")
    print("      result. Do NOT score the 7.79 Hz ratchet against it.")

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
    print(f"    🛑 gp-0x{DAMP_DISP:04x} is NOT a zero-reader mirror: {counts[DAMP_DISP][0]} real readers "
          "including the 1 kHz")
    print(f"       aggregator, and the firmware's own `st.h r6,-0x{DAMP_DISP:04x}[gp]` @0x{PIN_STH_6BD0[0]:05X} "
          f"is {PIN_STH_6BD0[1].hex()} against our")
    print(f"       {V55.ldh(DAMP_DISP, R6).hex()} -- SAME register, SAME displacement, ONE BIT apart "
          "(op 0x3B vs 0x39).")
    print("    ★ bit5 => bit6 is a STRUCTURAL MONOTONE INVARIANT ⇒ only 12 of the 16 payloads are "
          "legal, and a")
    print("      frame with bit5 SET while bit6 is CLEAR proves the artefact is NOT V72.")

    print(f"\n  📋 bit3 PRE-REGISTRATION: {R_THRESHOLD} counts / {RATE_SCALE_CTS_PER_DEGS} "
          f"counts-per-deg/s = {R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS:.2f} deg/s.")
    print(f"     Engaged duty must read {PREREG_BIT3_DUTY}% (9,497 / 345,396 frames), and it must fire")
    print(f"     frame-for-frame with bus |rate_c| >= {R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS:.1f} deg/s. "
          "A POSITIVE CONTROL: the rate axis is")
    print("     settled three independent ways, so a miss indicts the cave, not the scale.")
    assert abs(R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS - 108.7) < 0.1, \
        "the pre-registered 108.7 deg/s does not re-derive from the threshold and the settled scale"

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
    # 🛑 the sar->be adjacency, re-derived from the BUILT bytes rather than from the build listing
    n_pairs = 0
    for i, (a, _r, m) in enumerate(redis):
        if m.startswith(f"sar 0x{A_SHIFT:x}"):
            assert redis[i + 1][2].startswith("be "), \
                f"the `sar` @0x{a:05X} is not immediately followed by its `be` in the BUILT bytes " \
                f"(found '{redis[i + 1][2]}') -- the branch would read STALE flags"
            n_pairs += 1
    assert n_pairs == 2, f"expected 2 `sar 0x9`->`be` pairs in the built cave, found {n_pairs}"
    print(f"    ✅ exactly ONE `ld.h` (gp-0x{DAMP_DISP:04x} -> r6, opcode 0x39), exactly ONE store (an "
          "`st.b` to the CAN-330")
    print(f"       payload byte), and both `sar 0x{A_SHIFT:x}` instructions IMMEDIATELY followed by "
          "their own `be`. Re-derived")
    print("       from the BUILT bytes, not from a cached database.")

    # ---- THE DELIVERED MULTIPLIERS, RE-DERIVED FROM THE BUILT IMAGE -------------------------------
    print("\n  THE DELIVERED MULTIPLIER, re-derived from the BUILT image via v72_lane_model.py:")
    print("  (the gate 0x3AA96 is 0xC5 = the DEAD cell, so ENGAGED and MANUAL are identical -- V72 is")
    print("   UNGATED by construction and its dose applies in manual too. That is the disclosed cost.)")
    rates = (0, 400, 800, 1400, 2000, 3000)
    for lane in ("r24", "r26"):
        print(f"    {lane}  " + "".join(f"{r:>8}" for r in rates) + "   <- rate index")
        for kmh, vc in sorted(LM.KMH.items()):
            row = [LM.effective(bytes(code), lane, vc, r, False) /
                   LM.effective(stock, lane, vc, r, False) for r in rates]
            print(f"    {kmh:>4} km/h" + "".join(f"{x:8.3f}" for x in row))

    grid = [(v, r) for v in range(0, 6401, 32) for r in range(0, 3001, 25)]
    for lane in ("r24", "r26"):
        assert not [1 for v, r in grid
                    if LM.effective(bytes(code), lane, v, r, True) !=
                    LM.effective(bytes(code), lane, v, r, False)], \
            f"{lane}: ENGAGED differs from MANUAL -- the gate is not the dead cell"
    print(f"    ✅ over {len(grid)} operating points, ENGAGED == MANUAL EXACTLY on both lanes.")

    # ★★ THE ASSERTION THAT MATTERS: V67/V68's ENGAGED multipliers reproduced at 0 and 10 km/h,
    # at EVERY rate index. A flat record is exactly what a scalar arm delivers.
    print("\n    ★★ V67/V68's ENGAGED multipliers, reproduced EXACTLY at 0 and 10 km/h:")
    for kmh, vc in ((0, 0), (10, 640)):
        for lane in ("r24", "r26"):
            n = 0
            for r in range(0, 3001, 5):
                got = (LM.effective(bytes(code), lane, vc, r, False) /
                       LM.effective(stock, lane, vc, r, False))
                want = (LM.effective(v67, lane, vc, r, True) /
                        LM.effective(stock, lane, vc, r, True))
                assert abs(got - want) < 1e-12, \
                    f"{kmh} km/h {lane}: at rate {r} V72 is {got:.6f}x, V67 ENGAGED is {want:.6f}x " \
                    "-- the reproduction FAILS"
                n += 1
            show = [LM.effective(bytes(code), lane, vc, r, False) /
                    LM.effective(stock, lane, vc, r, False) for r in (0, 400, 1400, 3000)]
            print(f"       {kmh:>3} km/h {lane}: " + " / ".join(f"{x:.3f}" for x in show) +
                  f"   == V67/V68 engaged at ALL {n} rate indices")

    hwy = [(v, r, ln) for v, r in grid if v >= 3200 for ln in ("r24", "r26")
           if LM.effective(bytes(code), ln, v, r, False) != LM.effective(stock, ln, v, r, False)]
    assert not hwy, f"a >= 50 km/h operating point moved: {hwy[:4]}"
    n_hwy = sum(1 for v, _r in grid if v >= 3200)
    print(f"\n    ✅ all {n_hwy} points at >= 3200 counts (>= 50 km/h) are byte-identical to stock on "
          "BOTH lanes ⇒")
    print("       EXACTLY 1.000000x at highway, EVERY rate. STRUCTURAL: the 50/100 km/h records are "
          "untouched.")
    print("       ⇒ THAT IS V67/V68'S ONLY FAILURE, REMOVED, WITHOUT TOUCHING WHAT WORKED.")
    # 🛑 NO POINTWISE BOUND IS CLAIMED, and the reason is asserted so it cannot creep back in.
    hi24 = LM.effective(bytes(code), "r24", 0, 3000, False) / LM.effective(stock, "r24", 0, 3000, False)
    hi26 = LM.effective(bytes(code), "r26", 0, 3000, False) / LM.effective(stock, "r26", 0, 3000, False)
    assert hi24 > 2.0, "r24's high-rate multiplier is not above V62's 2.000x -- re-check the spec"
    print(f"\n    🛑 NO POINTWISE BOUND IS CLAIMED. At creep / rate 3000 V72's r24 is {hi24:.3f}x, "
          "ABOVE V62's 2.000x,")
    print(f"       so `V72 <= V62` is FALSE; and r26 is {hi26:.3f}x, so `V72 <= V70` is FALSE too. "
          "Earlier cuts of this")
    print("       build asserted both; they are REMOVED. What replaces them is the two-lane rule "
          f"(r24 high-rate {hi24:.3f}x")
    print(f"       AND r26 high-rate {hi26:.3f}x = V67/V68's exact row -- the only 3.4x-r24 row with "
          "no creep grind #2 in")
    print("       six builds) plus three DISCLOSED RISKS. See this file's docstring.")

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
    assert not [a for a in list(LEVER_B) + list(LEVER_A_FINAL_Y) +
                [CAVE_BASE, RATCHET_ADDR, DAMP_WEIGHT_ADDR] if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"

    # ---- the attributed diff -----------------------------------------------------------------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    lever_a_bytes = {b + Y_OFF + k for b in LEVER_A_FINAL_Y for k in range(8)}
    lever_b_bytes = {a + k for a in LEVER_B for k in (0, 1)}
    lever_c_bytes = {DAMP_WEIGHT_ADDR, DAMP_WEIGHT_ADDR + 1}

    def attribute(d):
        return ("PROBE cave" if d in cave_range else
                "LEVER A rate lane, whole axis" if d in lever_a_bytes else
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

    # 🛑 THE STOCK DIFF ALSO CARRIES THE WHOLE V38 -> V70 LINEAGE. Those bytes are not V72's and must
    # not be attributed to it -- but neither may they be waved away. The assertion that matters is
    # that every unattributed byte is one where the BASE already differed from stock.
    inherited = {i for i in range(START, END) if v70[i] != stock[i]}
    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    fs = [d for d in d_stock if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None and d not in inherited]
    assert not stray_s, f"UNATTRIBUTED functional bytes vs STOCK: {[hex(x) for x in stray_s[:16]]}"
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes = {len(fs)} functional + "
          f"{len(d_stock) - len(fs)} CRC")
    groups = {}
    for d in sorted(fs):
        groups.setdefault(attribute(d) or "INHERITED from the V38->V70 lineage", []).append(d)

    def runs(ds):
        out, s = [], ds[0]
        for a, b in zip(ds, ds[1:] + [None]):
            if b is None or b != a + 1:
                out.append((s, a))
                s = b
        return out

    for what in sorted(groups, key=lambda k: min(groups[k])):
        ds = groups[what]
        rr = runs(ds)
        print(f"    {what:<38s} {len(ds):3d} bytes in {len(rr):2d} range(s)")
        if what.startswith("INHERITED"):
            print(f"        {len(rr)} ranges spanning 0x{min(ds):05X}-0x{max(ds):05X} "
                  "(cave hook, V57 decoupling, mss0, the 0xE4xxx/0xE5xxx tables)")
            continue
        for lo, hi in rr:
            span = f"0x{lo:05X}" if lo == hi else f"0x{lo:05X}-0x{hi:05X}"
            print(f"        {span:<15s} {stock[lo:hi + 1].hex(' ')[:44]:<44s} -> "
                  f"{bytes(code[lo:hi + 1]).hex(' ')[:44]}")
    assert set(groups) - {"INHERITED from the V38->V70 lineage"} == \
        {"PROBE cave", "LEVER A rate lane, whole axis", "LEVER B FactorC/E damping",
         "LEVER C 0xC63A0 damper weight", "CARRIED 0x454FE"}, \
        f"the stock diff's attributed groups are {sorted(groups)}"

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
    for tbl in (FACTOR_C, FACTOR_E):
        for m in EDITED_FACTOR_MODES:
            ys = rec_y(dec, tbl[m])
            assert all(b >= a for a, b in zip(ys, ys[1:])), f"readback 0x{tbl[m]:05X} is not monotone"
    assert max(damper_authority(dec, m, v, r) for m in EDITED_FACTOR_MODES
               for v in range(0, FACTORC_ONSET_COUNTS + 1, 32)
               for r in range(0, 4001, 25)) < CEILING_FLOOR, "readback: the opened region clips"
    assert u16(dec, DAMP_WEIGHT_ADDR) == DAMP_WEIGHT_NEW, "readback 0xC63A0 wrong"
    assert_lever_c_single_reader(bytes(dec))
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_census(bytes(dec), cave_span)
    assert [r for _, r, _ in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))] == \
        [r for _, r, _ in cave_listing], "the readback cave does not re-disassemble identically"
    assert not [1 for v, r in grid if v >= 3200 for ln in ("r24", "r26")
                if LM.effective(bytes(dec), ln, v, r, False) != LM.effective(stock, ln, v, r, False)], \
        "readback moved a >= 50 km/h operating point"
    for kmh, vc in ((0, 0), (10, 640)):
        for lane in ("r24", "r26"):
            assert not [r for r in range(0, 3001, 25)
                        if abs(LM.effective(bytes(dec), lane, vc, r, False) /
                               LM.effective(stock, lane, vc, r, False) -
                               LM.effective(v67, lane, vc, r, True) /
                               LM.effective(stock, lane, vc, r, True)) > 1e-12], \
                f"readback lost the V67 reproduction at {kmh} km/h on {lane}"
    V55.assert_variant_tables(dec)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v70[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V70 outside the attributed set: {rb_stray[:8]}"
    print("\n  READBACK -- payload, all four LEVER A records, all "
          f"{len(LEVER_B)} LEVER B cells AND their monotonicity")
    print("     and no-clip properties, LEVER C and its single-reader census, the carried ratchet byte")
    print("     (decoded as a Bcond, target re-checked), the governor-monitor safety, every")
    print("     MUST-REMAIN-STOCK site, the whole 68-byte cave AND its re-disassembly, the probe")
    print("     census, the V67/V68 reproduction at 0 and 10 km/h, the >= 50 km/h structural-stock")
    print("     sweep, identity to V70 outside the attributed set, and the full CRC chain: ALL")
    print("     re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V72 BUILT. V67/V68's creep rate lane reproduced EXACTLY at 0 and 10 km/h on both lanes,")
    print("  through the ungated speed-shaped surfaces, with EXACTLY 1.000x at and above 50 km/h --")
    print("  V67/V68's only failure removed without touching what worked. The base-assist damper is")
    print("  opened at creep (389 counts, monotone, no clipping) and its weight doubled. A 5-rung")
    print("  probe on `a` (two thermometer steps), the damper output and the rate index.")
    print("  🛑 UNGATED: the rate-lane dose applies in MANUAL steering below ~30 km/h too, and if V72")
    print("     produces grind #2 it will produce it in the manual arm as well.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without an image."""
    _self_check_encoders()
    assert (A_THRESHOLD, A2_THRESHOLD, D_THRESHOLD, D_NEG_THRESHOLD, R_THRESHOLD) == \
        (512, 1024, 64, -65, 512)
    assert set(LEVER_A_FINAL_Y) == {REC_B0, REC_B1, REC_A0, REC_A1}
    assert sum(len(v[0]) for v in LEVER_A_FINAL_Y.values()) == 16      # 16 halfwords = 32 bytes
    assert len(LEVER_B) == 10                                          # 10 halfwords = 20 bytes
    cave, _ = build_cave()
    assert len(cave) == 68


if __name__ == "__main__":
    build()
