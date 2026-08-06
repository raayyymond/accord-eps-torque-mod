#!/usr/bin/env python3
"""build_v74_tva.py -- V74 = V73 CARRIED, with every lever moved onto the ENGAGED COLUMN OF EVERY ROW.

★★★★ THE ONE-LINE REASON THIS BUILD EXISTS. V73's probe read the damper's mode selector
`*(byte)(gp+0x63fd)` on-car and the answer was **not 10**. The car is config row **11 = `TVCA4`**,
running mode **24 disengaged / 26 engaged**. Every mode-indexed lever this kit has ever flown --
V44's, V72's LEVER B, V73's EDIT 1 and EDIT 2 -- addressed modes 0-5/10/11/12/14 and was therefore
**INERT BY CONSTRUCTION**. V74 writes the **engaged column (`e014`/`e015`) of all 16 rows**, so it
delivers whatever row is live while leaving the disengaged column -- manual and parking steering --
byte-stock.

★ THE MODE SETS ARE DISJOINT, AND THAT IS THE WHOLE SAFETY ARGUMENT.
    engaged    (e014, e015) = {2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33}   <- V74 writes these
    disengaged (e012, e013) = {0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31}   <- byte-stock
Both are DERIVED from the table at 0xCD000 (stride 0x24, mode fields +0x12..+0x15) on the image being
built, asserted against an independently stated literal, and asserted DISJOINT. Nothing is hand-listed:
every target address is dereferenced from its pointer array at build time.

LEVER E' -- OPEN BOTH DEAD ZONES. THE CORE OF V74.                    13 modes x 3 cells = 78 bytes
--------------------------------------------------------------------------------------------------
`dose = (FactorC x FactorE) >> 10`, with FactorB and FactorD FLAT 1024 on every engaged mode
(asserted, by COUNT -- FactorD is a FIVE-point record and a fixed 4-point reader mis-reads its Y).
**FactorC is speed-indexed and dead below its own X[0] (35 km/h on mode 26); FactorE is rate-indexed
and dead below 60 counts. The symptom sits under BOTH.**

★★ WHY THE DAMPER HAS ALWAYS PRODUCED ESSENTIALLY NOTHING, in one measurement: at stock `X[0] = 60`,
**FactorE is exactly 0 in 32.3% of IN-BURST frames, and 98.72% of engaged-highway frames sit below
that breakpoint.** ⇒ **this retires V72's `bit4` null with no exotic explanation** -- the rung was
reading a lane whose rate gate was closed almost all the time, on records the car never selected
anyway. The lever is shaped to open that gate rather than to raise a gain.

    1. FactorC (0xC9E9C[mode*4]):  Y[0] := that record's OWN Y[2]
    2. FactorE (0xC9F84[mode*4]):  X[0] := 12   and   Y[1] := that record's OWN Y[2]

🛑 THE RATE FORK, RESOLVED -- and it is the whole basis for the sizing. An earlier pricing used
`gp-0x6ac0 ~ 9.4`, concluded nothing could reach the requirement, and was **reading the OUT-OF-BURST
median**. Measured directly from telemetry, engaged creep:
        18-22 Hz burst   p10 14.1 · **p50 98.9 [94.2, 113.0]** · p90 263.7 · p99 353.1
        6-9 Hz burst     p10 28.2 · **p50 127.1** (⚠ 3 episodes, unpowered) · p90 251.4 · p99 367.4
        out of both      p10  0.0 · **p50   9.4**  <- the number that was mis-taken as in-burst
✅ The conversion is corroborated independently: route 5a's engaged-highway max **334.3** against the
   recorded route-59 peak **329.8** -- 1.4% apart on a DIFFERENT route. Not a fit.

    DELIVERED DOSE, mode 26:  at rate  99 -> E = 120, **dose 50** ✅ (requirement ~43, range 30-60)
                              at rate 127 -> E = 159, **dose 66**
                              stock at 99 -> 0 · FactorC alone -> 6 · FactorC at max alone -> 14
    🛑 Every number in that block is RECOMPUTED from the bytes actually written and printed by the
    builder; these are the expectation, not the source.

⚠ WHY 12 AND NOT 6. `Y[0] = 0` is preserved, so there is **no discontinuity at zero rate** and no
  chatter mechanism -- the magnitude vanishes with the rate and the bare `sign()` relay multiplies a
  vanishing quantity. But `X[0] = 6` starts the ramp 10x closer to zero and makes it 3.3x steeper,
  and `X0 < 30 with Y1 > 300` is the zone flagged as not-to-fly-without-telemetry. **12 sits at the
  top of the recommended 6-12 band and halves that concern for a 6% dose cost** (53 -> 50).
⊕ A third reason to err low: `rate_c` is the COLUMN and `gp-0x6ac0` is the MOTOR. The rigid-body
  scale is exact at DC and progressively wrong through a torsional resonance, and 18-22 Hz is one --
  so if the motor end swings more, **the TRUE dose is HIGHER than computed**. Erring low is the safe
  side of that error.

★ THIS IS THE OPPOSITE OF V72'S ERROR, NOT A LARGER VERSION. V72 raised FactorE's *floor* (Y[0] 0 ->
  927), producing a CONSTANT -- a near-bang-bang relay. Here **`Y[0] = 0` is preserved on every
  virgin record**, so the magnitude still vanishes with rate and the bare `sign()` relay multiplies a
  vanishing quantity: no discontinuity, no chatter mechanism.
🛑 MONOTONICITY IS ASSERTED ON THE RATE AXIS ONLY. FactorE must stay non-decreasing ([0, Y2, Y2, Y3]),
  because that is what protects rate-proportionality. **FactorC's speed-axis dip (Y[0] > Y[1]) is
  EXPECTED AND ALLOWED** -- it is precisely what confines the change to creep.
✅ NO-CLIP, RE-STATED STRONGER THAN V73's. Per mode, against that mode's OWN ceiling record
  `0xC77A0[mode*4]` (floor 512, VERIFIED per mode, not inherited from one): the worst case
  `(C_Y0 * E_Y3) >> 10` must be <= the floor, AND -- swept over a 99k-point (speed, rate) grid --
  **every point where the new surface exceeds the floor must be a point where the surface did not
  move.** That single rule covers the whole surface instead of a hand-drawn region, and it passes
  mode 11 (whose 793 is V72's pre-existing flat FactorE, which V74 raises at ZERO grid points).
⚠ THREE MODES NEEDED THE CAP -- 29, 32, 33 (TWAA chassis, inert here): their Y[2] is 571/594/590 and
  `(Y2 * 927) >> 10` = 516/537/534 > 512, so C_Y0 is capped to `floor(512 * 1024 / E_Y3)` = 565.
  Reported, not silently applied.

LEVER D' -- THE FRICTION LANE x1.5, on the same 13 modes.             13 x 6 = 78 bytes
--------------------------------------------------------------------------------------
`0xCBE74[mode*4] + 8`, the 3-point Y row: -9830/-5734/-1966 -> -14745/-8601/-2949 (x1.5, EXACT in
integers). All 13 engaged records are asserted to be `n=3, X=[0,1280,5760], Y=[-9830,-5734,-1966]`
BEFORE a byte is written -- V73 edited mode **10**'s copy (0xD2A44), which is in the DISENGAGED set,
so every engaged record is still stock.

LEVER D'b -- THE CLAMP. NOT MODE-INDEXED, AND ALREADY IN PLACE.       0 bytes
------------------------------------------------------------------------------
`0xC407E` (tp+0x507e) = 850. **V73 already set it and it FLEW LIVE** (~80% of burst frames), so V74
asserts it and does NOT re-write it. 🛑 HARD CAP 1000, NEVER 1024: the aggregator applies a
**zero-reject** window at +/-0x400 -- a lane landing on the cliff contributes 0, not a clamped value.

🛑 `0xD2A7E` / `0xD2ABA` ARE **NOT** TOUCHED -- the revert was WITHDRAWN. 0 bytes
---------------------------------------------------------------------------------
An earlier draft of this build reverted those two cells to stock for diff hygiene. **The instruction
was withdrawn and V74 leaves them byte-identical to V73**, which this file asserts alongside the rest
of the keep-list. Two reasons, the second decisive:
  1. It was arithmetically incoherent. The cells are Y[0] of the **gain_B mode-10** records
     0xD2A74 / 0xD2AB0, and they were set by **V72** (LEVER A), not V73 -- V72 set ALL FOUR Y cells
     of each record to 5244. Reverting the two named cells leaves `[3072, 5244, 5244, 5244]`, which
     is neither stock nor V72.
  2. 🛑 **V74 MUST BE V73 PLUS ADDITIONS ONLY.** Those cells are inert *because* the car is row 11 --
     a well-forced inference, but an inference. If it were ever wrong the car is row 2 (modes 10/11),
     mode 10 is its DISENGAGED mode, and reverting would **SUBTRACT something currently on the car**.
     Cosmetic diff cleanliness is not worth a subtractive change resting on an inference.

EDIT 4 -- THE PROBE. 46 of the proven 68 bytes, zero-padded, extent UNCHANGED.
-------------------------------------------------------------------------------
    bit7      = (*(short *)(gp - 0x6bd0) != 0)   ★★★★ **THE POSITIVE CONTROL THE LAST FIVE PROBES
                LACKED.** `gp-0x6bd0` is the damper's OWN output and goes non-zero exactly when
                LEVER E' delivers. V72 asked `|x| >= 64` and got 0/87,940; this asks `!= 0`.
    bits 6:3  = (*(byte *)(gp - 0x67fa)) & 0xF   ★★ THE ASSIST-CHAIN STATE.
    bits 2:0  = stock STEER_SENSOR_STATUS         preserved, untouched.
★★ LIVENESS IS STRUCTURAL, AND THAT IS NEW. `gp-0x67fa`'s complete value set is
   **{1, 3, 4, 5, 6, 7, 8, 9, 10, 11}** -- re-verified HERE, in this build, from the 33 `st.b`
   writers' own literals -- so **0 is impossible and 4 bits are lossless**. `bits 6:3 == 0` for a
   whole drive therefore means THE CAVE DID NOT FIRE. No prior probe could say that from the payload
   alone; V73 needed a dedicated bit7 for it and V64/V68 could not distinguish "gate never armed"
   from "hypothesis false".
   ⊕ Three of the 33 writers store a register rather than an inline literal; all three were read in
   Ghidra and are the shadow-lockstep re-store idiom (`gp-0x4c39` is the shadow). 0x19862 stores 3,
   0x19D24 stores 6, 0x1A0BA re-stores the value it just loaded from the cell itself.

🛑 THREE DURABLE FINDINGS THIS BUILD PRODUCED -- record them, they outlive V74
-------------------------------------------------------------------------------
  1. **V73'S GUARD WINDOW IS FOUR BYTES TOO WIDE, AND IT FALSE-POSITIVES ACROSS ADJACENT MODES.**
     V73's untouched-region guards use a flat `0x18` span "as a superset". That is right only for
     FactorD (5-point, `4 + 4*5 = 0x18`); a **4-point record is `0x14`**, so the window spills 4
     bytes into the NEXT MODE'S RECORD -- and the next mode is one this build may legitimately have
     edited. It fired here as "the DISENGAGED mode-4 FactorE @0xD07F8 MOVED", when what had actually
     moved was mode 5's `X[0]` at 0xD080E. **The fix is `rec_len(buf, base) = 4 + 4 * count`**
     (`rec_len()` below), verified against the arrays' own strides: ceiling (n=2) 0x0C, FactorB/C/E
     (n=4) 0x14, FactorD (n=5) 0x18. **Anything reusing V73's idiom across adjacent modes is wrong.**
  2. **`gp-0x67fa` IS LOCKSTEP-SHADOWED AT `gp-0x4c39`.** Every writer reads both, compares them, and
     stores only on agreement -- otherwise it calls `FUN_0006b9fa(gp-0x4c39)`. Our probe only READS,
     so the blast radius is zero, but a stray write to either half escalates. The cave is asserted to
     touch neither. ⊕ This is also how the value set was pinned: 30 of the 33 writers store an inline
     literal, and the 3 that store a register were read in Ghidra -- 0x19862 -> 3, 0x19D24 -> 6,
     0x1A0BA re-stores the cell's own value during the shadow compare. **0 is unreachable.**
  3. **MODES 2 AND 3 HAVE A DIFFERENT FactorE RECORD ENTIRELY**: `X = [70, 450, 1000, 4000]`,
     `Y = [115, 115, 177, 253]` -- a stock `X[0]` of **70**, not 60, and a non-zero `Y[0]`. ⇒ they are
     the only engaged modes whose dose is UNCHANGED by the `X[0]` revision (168 at both 6 and 12):
     the first segment is shallow, so its left edge barely moves the interpolation. Not an error.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent 68 of the proven 68 B -- unchanged, flown 11x (V55/V57/V58/V59/
V64/V65/V66/V67/V70/V71/V72/V73, all clean). 46 B of code; the remaining 22 are 0x00 (`nop`) and sit
AFTER `jmp [lp]`. 🛑 Growing a cave is this kit's ONLY bricking class (V24, V27 and V48B all bricked
the ECU); the extent is asserted at 68 on the emitted bytes AND on the .rwd readback.
★ ONE forward `be +6` -- the geometry V72 flew five times. Its target is asserted to be an emitted
  instruction BOUNDARY inside the code region and strictly before `jmp [lp]`, so the zero padding
  stays unreachable. r7 IS PROVABLY DEAD ACROSS THE HOOK: 0x55C12 is `mov 0x8,r7` (083a).

🛑 MUST NOT CHANGE -- asserted byte-identical to V73 on the input, the output AND the .rwd readback
-----------------------------------------------------------------------------------------------------
  0x3AB76 = aa32 · 0x3AC20 = aa42  -- stock `sar`. **Reintroducing V62's `a9` causes grind #2**, and
    the operator's reframing ("grind #2 only ever came through proposed fixes for grind #1") makes
    THE FIX AN ABSENCE. V74 keeps it by leaving both lanes alone.
  0x3AA96 = c5 (the gate) · 0xC6446 = 512 · 0xC6444 = 512 · 0xC643E = 1536
  gain_A rec0 0xC6A68 and rec1 0xC6A7C both Y = [512, 512, 512, 512] -- **V72's r26 cut, the leading
    candidate for the macro-ratchet fix. Keep EXACTLY; do not deepen.** rec2 0xC6A90 / rec3 0xC6AA4
    stock (⚠ the cut is PARTIAL, by design).
  The whole r24/r26 rate lane, both scalar arms, the ceiling and its lockstep float twin, the role
  table 0xC4124, V72's LEVER C and the carried 0x454FE.

Usage:  python build_v74_tva.py
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
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl / cmp_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldbu_any, ldh -- the odd-disp / signed forms)
import build_v57_tva as V57                # noqa: E402  (the decoupling guard)
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the raw byte scan)
import build_v68_tva as V68                # noqa: E402  (cave machinery)
import build_v71a_tva as A                 # noqa: E402  (ratchet byte + governor monitor safety)
import build_v72_tva as V72                # noqa: E402  (the inherited MUST-REMAIN-STOCK guard)
import build_v73_tva as V73                # noqa: E402  (THE BASE -- its levers and its guards)
import v72_lane_model as LM                # noqa: E402  (lerp_int)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = V72.START, V72.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT              # 68 -- the PROVEN extent. Never grow it.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
TP = LM.TP                                 # 0xBF000
Q10 = 1024

# =====================================================================================================
# THE BASE -- V73, carried
# =====================================================================================================
SRC_BIN = plain_image_path("_v73_plain_image.bin")
SRC_SHA256 = "918a37151876a1a321103fbd7252684d944773109ff454a08a41fe2c191ee63a"
STOCK_BIN = stock_fw_path("code.bin")
# 🛑 A SAME-NUMBER RE-CUT ONCE OVERWROTE A PREDECESSOR'S PLAIN IMAGE and produced an artefact NO gate
# could check. The recorded FIX is `_v<NN><tag>_plain_image.bin`; this build applies it, and the tag
# carries the ONE parameter that distinguishes this cut from the retired X0=6 one.
# ⊕ TWO EARLIER V74 CUTS ARE RETIRED, both renamed `SUPERSEDED-DO-NOT-FLASH-…`, neither flashed:
#     …x0_6_staleX0…      -- built against a stale `X[0] = 6`
#     …x0_12_hybridD2A7E… -- correct X[0], but it carried the WITHDRAWN 0xD2A7E/0xD2ABA revert,
#                            leaving `[3072, 5244, 5244, 5244]` -- a row attributable to NO build
#   🛑 All three cuts share a BYTE-IDENTICAL cave, so the payload cannot tell them apart and the
#   x0_12 cut even shares this one's MAIN CRC trailer. **The FILENAME is the only discriminator.**
BIN_OUT = str(plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin"))

# 🛑 V73's / V72's own levers, re-declared HERE as literals (not imported) so a drift in either fails.
V72_GAIN_A = {0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}     # r26 -- V72's cut. KEEP EXACTLY.
V72_LEVER_C = (0xC63A0, 2048)
V72_CARRIED = (0x454FE, 0xB5)              # the low byte -- `bne 0x455C4` -> `br 0x455C4`
V72_GATE = (0x3AA96, 0xC5)                 # gp-0x683c, ZERO writers ⇒ V72..V74 are UNGATED
SAR_SITES = {0x3AB76: bytes.fromhex("aa32"), 0x3AC20: bytes.fromhex("aa42")}
ARMS_STOCK = {0xC643E: 1536, 0xC6444: 512, 0xC6446: 512}
GAIN_A_STOCK_RECS = (0xC6A90, 0xC6AA4)     # rec2 / rec3 -- the cut is PARTIAL, by design
REC_STRIDE = 0x14

# =====================================================================================================
# THE MODE COLUMNS -- derived from the config table, never hand-listed
# =====================================================================================================
VARIANT_KEY_TABLE, VARIANT_IDX_TABLE, VARIANT_STRIDE = 0xCD000, 0xCD012, 0x24
VARIANT_ROWS = 16
COL_DISENGAGED, COL_ENGAGED = (0, 1), (2, 3)        # e012/e013 vs e014/e015
# ⊕ THE INDEPENDENT SECOND STATEMENT. Derivation and literal must agree, or a derivation bug passes.
ENGAGED_EXPECTED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_EXPECTED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
THIS_CAR_ROW, THIS_CAR_KEY = 11, "TVCA4"
THIS_CAR_MODES = [24, 25, 26, 27]          # manual 24, engaged 26 -- V73's probe, on-car
LIVE_MODE = 26

# =====================================================================================================
# LEVER E' -- open BOTH dead zones
# =====================================================================================================
FACTOR_B_PTRS, FACTOR_C_PTRS = 0xC9CCC, 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = 0xC9DB4, 0xC9F84
CEILING_PTRS = 0xC77A0
REC4_X_OFF, REC4_Y_OFF, REC4_STRIDE = 0x02, 0x0A, 0x14
CEILING_X, CEILING_Y = [300, 800], [512, 1024]
CEILING_FLOOR = CEILING_Y[0]               # 512 -- 🛑 VERIFIED PER MODE, never assumed from one
E_X0_NEW = 12                              # the rate dead zone's new left edge. ⚠ 12, NOT 6 -- top of
E_X0_MIN_SAFE = 12                         #   the recommended 6-12 band; see the hazard note above
E_X0_STOCK_SET = {60, 70}                  # ⚠ modes 2/3 carry 70, not 60. Asserted against STOCK.
BURST_RATE = 99                            # measured |gp-0x6ac0| p50 in-burst, [94.2, 113.0]
BURST_RATE_69HZ = 127                      # the 6-9 Hz arm's p50 (⚠ 3 episodes, unpowered)
OUT_OF_BURST_RATE = 9                      # 🛑 the OUT-of-burst p50 -- NOT the sizing input
DOSE_REQUIREMENT = (30, 60)                # the sizing work's interval; ~43 nominal
# ★ why the lever is shaped this way: at stock X[0] = 60 FactorE is EXACTLY 0 in 32.3% of in-burst
# frames, and 98.72% of engaged-highway frames sit below the breakpoint.
FACTORE_ZERO_INBURST_PCT, FACTORE_BELOW_X0_HWY_PCT = 32.3, 98.72

# ⊕ The expected geometry for THE LIVE MODE, stated independently and asserted after dereferencing.
LIVE_EXPECT = {"friction": 0xD7A54, "friction_y": 0xD7A5C,
               "factor_c": 0xD77D0, "factor_c_y0": 0xD77DA,
               "factor_e": 0xD780C, "factor_e_x0": 0xD780E, "factor_e_y1": 0xD7818,
               "factor_e_y1_old": 140, "factor_e_y1_new": 539,
               "factor_c_y0_old": 0, "factor_c_y0_new": 429,
               "dose": 50, "dose_69hz": 66}

# =====================================================================================================
# LEVER D' -- the friction lane
# =====================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_NPT, FRICTION_Y_OFF = 3, 0x08
FRICTION_X = [0, 1280, 5760]               # counts of voted vehicle speed = [0, 20, 90] km/h
FRICTION_Y_STOCK = [-9830, -5734, -1966]
FRICTION_SCALE_NUM, FRICTION_SCALE_DEN = 3, 2                       # x1.5, EXACT in integers
FRICTION_Y_NEW = [-14745, -8601, -2949]
SPEED_COUNTS_PER_KMH = 64
FRICTION_FN = 0x36C12

CLAMP_ADDR, CLAMP_VALUE = 0xC407E, 850     # ✅ ALREADY IN PLACE from V73, and it FLEW LIVE
CLAMP_TP_DISP = 0x507E
CLAMP_READERS = [0x36C34, 0x36CD0, 0x36CDC]
CLAMP_NEIGHBOUR = (0xC407C, 461)           # ⚠ NOT TOUCHED, owner unidentified
CLAMP_HARD_CAP = 1000                      # 🛑 never 1024 -- the aggregator's +/-0x400 ZERO-REJECT
AGGREGATOR_ZERO_REJECT = 1024

# =====================================================================================================
# 🛑 THE WITHDRAWN REVERT -- these cells are now part of the KEEP-LIST, not an edit
# =====================================================================================================
# The gain_B mode-10 records, at V72's LEVER A values. V74 is ADD-ONLY on V73: leaving them alone
# cannot subtract anything from the car even if the row-11 inference is ever overturned.
GAIN_B_M10_KEEP = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4}
GAIN_B_M10_STOCK_Y0 = {0xD2A7E: 3072, 0xD2ABA: 2561}     # what a revert WOULD have written. Not used.

# =====================================================================================================
# EDIT 4 -- THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
HOOK_RETURN = HOOK_ADDR + 4                     # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")        # `mov 0x8,r7` -- proves r7 is DEAD across the hook

STATE_DISP = 0x67FA             # gp-0x67fa -- the assist-chain state. NEGATIVE displacement, BYTE.
DAMP_DISP = 0x6BD0              # gp-0x6bd0 -- the base-assist damper output. ld.h, SIGNED.
STATE_MASK = 0xF
W_DAMP_NZ = 0x10                # -> bit7, in PRE-SHIFT weights (0x10 is OUTSIDE `add imm5`'s range,
PAYLOAD_SHIFT = 3               #    which is exactly why it is a `movea`, as in V72/V73)
BIT_DAMP_NZ = W_DAMP_NZ << PAYLOAD_SHIFT        # 0x80
STATE_FIELD = STATE_MASK << PAYLOAD_SHIFT       # 0x78 -- bits 6:3
PROBE_MASK = BIT_DAMP_NZ | STATE_FIELD          # 0xF8
BE_SKIP = 6                                     # `be +6` skips the 4-byte `movea 0x10,r0,r7`

# The two probed cells' firmware censuses, on the V73 base. (reads, writes, writer count, mnemonics)
STATE_CENSUS = (128, 33, {"ld.bu", "ld.b"}, {"st.b"})
DAMP_CENSUS = (5, 3, {"ld.h"}, {"st.h"})
DAMP_WRITERS = [0x34730, 0x34744, 0x34752]      # all inside FUN_00034350
STATE_SHADOW_DISP = 0x4C39                      # gp-0x4c39 -- the lockstep shadow. NOT touched.
# ★ Re-verified in THIS build from the 33 writers' own literals; three store a register and were read
# in Ghidra (0x19862 -> 3, 0x19D24 -> 6, 0x1A0BA -> a self-restore during the shadow compare).
STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}
STATE_NONLITERAL_WRITERS = {0x19862: 3, 0x19D24: 6, 0x1A0BA: None}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance in the STOCK image, and
# ---- every one below was rendered by Ghidra's own disassembler at that address before being used.
PIN_MOVI5_0_R7 = (0x34114, bytes.fromhex("003a"))          # `mov 0x0,r7`   -- Ghidra-confirmed
PIN_LDH_HW1 = (0x3ACA8, bytes.fromhex("24372c95"))         # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_6BD0_DISP = (0x34726, bytes.fromhex("243f3094"))   # hw2 donor: `ld.h -0x6bd0[gp],r7`
PIN_STH_6BD0 = (0x34730, bytes.fromhex("64373094"))        # 🛑 THE ONE-BIT TWIN: st.h, SAME reg/disp
PIN_CMP_R0_R6 = (0x3401E, bytes.fromhex("e031"))           # `cmp r0,r6`    -- Ghidra-confirmed
PIN_BE6 = (0x34CFA, bytes.fromhex("b205"))                 # `be 0x34D00` = +6 -- Ghidra-confirmed
PIN_MOVEA_10_R7 = (0x49256, bytes.fromhex("203e1000"))     # `movea 0x10,r0,r7`
PIN_LDBU_STATE_R6 = (0x18C7C, bytes.fromhex("84370798"))   # ★ `ld.bu -0x67fa,gp,r6` -- IDENTICAL
PIN_STB_STATE = (0x19862, bytes.fromhex("44370698"))       # 🛑 the ONE-BIT twin: st.b, SAME disp
PIN_ANDI_F_R6 = (0x45EBC, bytes.fromhex("c6360f00"))       # `andi 0xf,r6,r6`
PIN_OR_R6_R7 = (0x1C1C4, bytes.fromhex("0639"))            # `or r6,r7`   -> r7 |= r6
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))             # `shl 0x3,r7` -- V31P FLASHED it 4x
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))      # `ld.bu -0x1514,gp,r6`
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))       # `andi 0x7,r6,r6`
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))            # `or r7,r6`   -> r6 |= r7
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))       # `st.b r6,-0x1514,gp` -- THE ONLY STORE
PIN_MOVEA_HOOK = (0x55C0E, bytes.fromhex("2436e8ea"))      # the displaced `movea -0x1518,gp,r6`
PIN_JMP_LP = (0x1E4, bytes.fromhex("7f00"))                # `jmp lp`

COND_BE = FF.COND_BE                                        # 0x2
COND_BNE = FF.COND_BNE                                      # 0xA -- the INVERTING twin, asserted away

# ⚠ DELIBERATELY SHORT and asserted BEFORE anything is written -- V71A's note records an over-long
# tag that overran Windows' 260-char path limit and failed the .rwd write AFTER the image was on disk.
TAG = ("V73BASE-ENGCOLS13-x12-addonly-FactorCY0eqY2-FactorEX0to12-Y1eqY2-"
       "frictionx1p5-C407E850-probe-67fa-6bd0nz")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V74-{TAG}-0x{START:X}-0x{END:X}.rwd")
DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v74_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


def rec_any(buf, base):
    """(count, X, Y) for a record of ANY point count, driven by the count word at +0.

    🛑 Y lives at `base + 2 + 2 * count`. FactorD is a FIVE-point record and a fixed 4-point reader
    returns [X[4], Y[0], Y[1], Y[2]] for it -- which reads as "not flat". The count is READ.
    """
    n = u16(buf, base)
    assert 1 <= n <= 16, f"the record @0x{base:05X} declares count {n}"
    xs = list(struct.unpack_from(f"<{n}h", buf, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", buf, base + 2 + 2 * n))
    return n, xs, ys


def rec_len(buf, base):
    """The record's OWN byte length: count word + X + Y + terminator = 4 + 4n.

    🛑 THIS EXISTS BECAUSE A FIXED SPAN GAVE A FALSE POSITIVE DURING THIS BUILD. V73's guards used a
    flat 0x18 "superset" window, which is right for FactorD (5-point) but **spills 4 bytes past a
    4-point record into its NEIGHBOUR** -- and the neighbour is the next mode's record, which V74 may
    legitimately have edited. Verified against the arrays' own strides: ceiling (n=2) 0x0C,
    FactorB/C/E (n=4) 0x14, FactorD (n=5) 0x18.
    """
    n = u16(buf, base)
    assert 1 <= n <= 16, f"the record @0x{base:05X} declares count {n}"
    return 4 + 4 * n


def rec4_y(buf, base):
    return list(struct.unpack_from("<4h", buf, base + REC4_Y_OFF))


def rec3_x(buf, base):
    return list(struct.unpack_from("<3h", buf, base + 0x02))


def rec3_y(buf, base):
    return list(struct.unpack_from("<3h", buf, base + FRICTION_Y_OFF))


def factor_rec(buf, ptr_array, mode):
    """The record a factor's pointer array selects for `mode`. DEREFERENCED, never quoted."""
    return u32(buf, ptr_array + mode * 4)


def decode_fmt2(hw):
    """V850 Format-II field split: imm5 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"imm5": hw & 0x1F, "opcode": (hw >> 5) & 0x3F, "reg2": (hw >> 11) & 0x1F}


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v6bd0, state, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the instructions, not a paraphrase."""
    r7 = 0                                          # mov 0x0,r7
    r6 = v6bd0 - 0x10000 if v6bd0 & 0x8000 else v6bd0       # ld.h  (SIGN-extends a halfword)
    if r6 != 0:                                     # cmp r0,r6 ; be +6  (skips the movea)
        r7 = W_DAMP_NZ                              # movea 0x10,r0,r7
    r6 = state & 0xFF                               # ld.bu -0x67fa[gp],r6  (ZERO-extends a BYTE)
    r6 &= STATE_MASK                                # andi 0xf,r6,r6
    r7 |= r6                                        # or   r6,r7          -> r7 |= r6
    r7 <<= PAYLOAD_SHIFT                            # shl  0x3,r7
    return (r7 & 0xFF) | (status_bits & PAYLOAD_KEEP_MASK)


LEGAL_PAYLOADS = {(d << 7) | (s << PAYLOAD_SHIFT) for d in (0, 1) for s in range(STATE_MASK + 1)}


def _wire_model():
    """The rung's semantics, exhaustively over both fields' full ranges."""
    for raw in range(256):
        for v in (0, 1, 0x7FFF, 0x8000, 0xFFFF, 0x0040, 0xFFC0):
            b = wire_byte4(v, raw)
            signed = v - 0x10000 if v & 0x8000 else v
            assert bool(b & BIT_DAMP_NZ) == (signed != 0), \
                f"bit7 is not `gp-0x{DAMP_DISP:04x} != 0` at v=0x{v:04X}"
            assert (b & STATE_FIELD) >> PAYLOAD_SHIFT == (raw & STATE_MASK), \
                f"bits 6:3 are not `(gp-0x{STATE_DISP:04x}) & 0xF` at {raw}"
            assert (b & PROBE_MASK) in LEGAL_PAYLOADS, f"payload 0x{b:02X} is outside LEGAL"
    # 🛑 bit7 must be TWO-SIDED: a `ld.hu` (unsigned) would still work here, but a `sar`-based rung
    # would not, and the SIGN must not be lost -- -1 is as non-zero as +1.
    assert wire_byte4(0xFFFF, 0) & BIT_DAMP_NZ and wire_byte4(0x0001, 0) & BIT_DAMP_NZ, \
        "bit7 is not two-sided -- a negative damper output must set it"
    assert not (wire_byte4(0x0000, 0) & BIT_DAMP_NZ), "bit7 sets on a ZERO damper output"
    # 🛑 the field must never reach the preserved status bits, and the seed must land on bit7.
    for m in range(STATE_MASK + 1):
        r7 = W_DAMP_NZ | m
        assert (r7 << PAYLOAD_SHIFT) <= 0xF8, f"r7 = 0x{r7:02X} shifts past the byte"
        assert (r7 << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
            f"r7 = 0x{r7:02X} shifts INTO the preserved status bits -- the wire would be corrupted"
    assert (W_DAMP_NZ << PAYLOAD_SHIFT) == BIT_DAMP_NZ == 0x80, "the seed does NOT land on bit7"
    assert BIT_DAMP_NZ | STATE_FIELD == PROBE_MASK == 0xF8 and PROBE_MASK & PAYLOAD_KEEP_MASK == 0, \
        "the probe bits do not cover exactly 7:3"
    for status in range(8):
        for raw in (0, 10, 26, 0xFF):
            assert wire_byte4(0x0100, raw, status_bits=status) & PAYLOAD_KEEP_MASK == status, \
                "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
    assert len(LEGAL_PAYLOADS) == 32, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 32"
    # ★★ STRUCTURAL LIVENESS. `gp-0x67fa` never holds 0, so bits 6:3 == 0 can only mean the cave
    # never ran. This is what V64's and V68's five-build nulls could not establish.
    assert 0 not in STATE_VALUE_SET, "0 IS reachable on gp-0x67fa -- structural liveness is VOID"
    assert all(v < 16 for v in STATE_VALUE_SET), "a state value >= 16 would ALIAS in a 4-bit field"
    for v in STATE_VALUE_SET:
        assert (wire_byte4(0, v) & STATE_FIELD) >> PAYLOAD_SHIFT == v, \
            f"state {v} does not round-trip through the 4-bit field"
    # 🛑 the field ALIASES for state >= 16; named explicitly and checked on the image separately.
    assert wire_byte4(0, 16) == wire_byte4(0, 0) and wire_byte4(0, 26) == wire_byte4(0, 10), \
        "the 4-bit field does not alias mod 16 -- the aliasing statement in the docs is wrong"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    Each pin below was ALSO rendered by Ghidra's own disassembler at that address (dry run) before
    being written into this file -- the pin is the byte check, Ghidra is the semantic check.
    """
    V55._self_check_encoders()               # chains down through V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVI5_0_R7, PIN_LDH_HW1, PIN_LDH_6BD0_DISP, PIN_STH_6BD0, PIN_CMP_R0_R6, PIN_BE6,
            PIN_MOVEA_10_R7, PIN_LDBU_STATE_R6, PIN_STB_STATE, PIN_ANDI_F_R6, PIN_OR_R6_R7,
            PIN_SHL3_R7, PIN_LDBU_BYTE4, PIN_ANDI_7_R6, PIN_OR_R7_R6, PIN_STB_BYTE4,
            PIN_MOVEA_HOOK, PIN_JMP_LP]
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # ---- the state load. ★ BYTE-IDENTICAL to the real `ld.bu -0x67fa,gp,r6` @0x18C7C -------------
    ours = V55.ldbu_any(-STATE_DISP, R6)
    assert ours == PIN_LDBU_STATE_R6[1], \
        f"the state load is not byte-identical to the real one @0x{PIN_LDBU_STATE_R6[0]:05X}"
    hw1, hw2 = struct.unpack("<HH", ours)
    # 🛑 THE ODD-DISPLACEMENT TRAP: ld.bu carries disp bit 0 in the OPCODE FIELD (0x3C | (disp & 1))
    # and ALSO sets hw2's LSB. -0x67FA is 0x9806 -- EVEN -- so the opcode field MUST be 0x3C here.
    assert ((hw1 >> 5) & 0x3F) == 0x3C, \
        f"the state load's opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x3C for an EVEN disp"
    assert hw2 == (((0x10000 - STATE_DISP) & 0xFFFE) | 1) == 0x9807, "ld.bu hw2 must be (disp&~1)|1"
    assert (hw1 >> 11) == R6 and (hw1 & 0x1F) == GP == 4, "the state load is not `... [gp],r6`"
    # 🛑 THE ONE-BIT TRAP: st.b is op 0x3A. The firmware's own store to this very cell is 44370698.
    assert ours != PIN_STB_STATE[1] and ours[:2] != PIN_STB_STATE[1][:2], \
        f"the state load IS/matches the real `st.b r6,-0x67fa,gp` @0x{PIN_STB_STATE[0]:05X} -- the " \
        "cave would WRITE the assist chain's state selector, which is LOCKSTEP-CHECKED against " \
        f"gp-0x{STATE_SHADOW_DISP:04x} and escalates to a hard fault"
    assert ours != FF.stb(R6, -STATE_DISP, GP), "the state load collapsed onto an st.b -- a WRITE"
    assert ours != V55.ldbu_any(STATE_DISP, R6), \
        "the POSITIVE and NEGATIVE displacement forms collapsed -- gp-0x67fa is not gp+0x67fa"

    # ---- the damper load. SIGNED `ld.h`; its one-bit twin `st.h` is a real instruction. ----------
    ldh = V55.ldh(DAMP_DISP, R6)
    assert ldh[:2] == PIN_LDH_HW1[1][:2], "the ld.h hw1 is not the real `ld.h ...,gp,r6` form"
    assert ldh[2:] == PIN_LDH_6BD0_DISP[1][2:] == PIN_STH_6BD0[1][2:], \
        "the ld.h displacement halfword is not the real -0x6bd0"
    assert ((struct.unpack("<H", ldh[:2])[0] >> 5) & 0x3F) == 0x39, \
        "the damper load's opcode field is not 0x39 -- 0x3B would be an st.h, a WRITE"
    assert ldh != PIN_STH_6BD0[1] and ldh[:2] != PIN_STH_6BD0[1][:2], \
        f"the damper load matches the real `st.h r6,-0x6bd0,gp` @0x{PIN_STH_6BD0[0]:05X} -- the cave " \
        "would OVERWRITE the damper's own output"
    assert ldh != V54.ldhu(DAMP_DISP, R6) if hasattr(V54, "ldhu") else True, \
        "the SIGNED ld.h collapsed onto an UNSIGNED ld.hu -- a negative damper output would read huge"

    # ---- the rest -----------------------------------------------------------------------------------
    assert FF.movi5(0, R7) == PIN_MOVI5_0_R7[1], "mov 0x0,r7 != the real one @0x34114"
    assert FF.movi5(0, R7) != HOOK_RETURN_INSN, "mov 0x0,r7 collapsed onto the hook's `mov 0x8,r7`"
    assert V54.cmp_rr(R0, R6) == PIN_CMP_R0_R6[1], "cmp r0,r6 != the real one @0x3401E"
    assert V54.cmp_rr(R6, R0) != V54.cmp_rr(R0, R6), "cmp's two register fields collapsed"
    assert FF.bcond(COND_BE, BE_SKIP) == PIN_BE6[1], "be +6 != the real one @0x34CFA"
    assert FF.bcond(COND_BNE, BE_SKIP) != FF.bcond(COND_BE, BE_SKIP), \
        "🛑 `be +6` (b205) and `bne +6` (ba05) collapsed -- the wrong one INVERTS the whole rung"
    assert FF.bcond(COND_BE, 4) != FF.bcond(COND_BE, BE_SKIP), \
        "be +4 and be +6 collapsed -- +4 would land INSIDE the 4-byte movea"
    assert FF.movea(W_DAMP_NZ, R0, R7) == PIN_MOVEA_10_R7[1], "movea 0x10,r0,r7 != the real @0x49256"
    assert V54.andi(STATE_MASK, R6, R6) == PIN_ANDI_F_R6[1], "andi 0xf,r6,r6 != the real @0x45EBC"
    assert V54.andi(PAYLOAD_KEEP_MASK, R6, R6) == PIN_ANDI_7_R6[1], "andi 0x7,r6,r6 encoding changed"
    assert V54.andi(STATE_MASK, R6, R6) != V54.andi(PAYLOAD_KEEP_MASK, R6, R6), \
        "the 0xF and 0x7 masks collapsed -- the state's top bit would be lost"
    # 🛑🛑 `or r6,r7` (0639) vs `or r7,r6` (0731) -- SAME opcode, the two register fields SWAPPED, and
    # the wrong one accumulates into the scratch register instead of the payload. Both are real
    # instructions in this image, so a byte pin alone cannot catch the swap: the FIELDS are decoded.
    ours = V54.or_rr(R6, R7)
    assert ours == PIN_OR_R6_R7[1], "or r6,r7 != the real one @0x1C1C4"
    assert ours != V54.or_rr(R7, R6) == PIN_OR_R7_R6[1], \
        "or r6,r7 collapsed onto `or r7,r6` -- the state would be OR'd into the SCRATCH register and " \
        "the payload would carry the damper bit alone, reading as `state 0` on every frame"
    hw = struct.unpack("<H", ours)[0]
    assert ((hw >> 5) & 0x3F) == 0x08 and (hw >> 11) == R7 and (hw & 0x1F) == R6, \
        f"`or r6,r7` fields are wrong: op 0x{(hw >> 5) & 0x3F:02X} reg2 r{hw >> 11} reg1 r{hw & 0x1F}"
    assert V54.shl(PAYLOAD_SHIFT, R7) == PIN_SHL3_R7[1] == V54.V31P_SHL3_R7, \
        "shl 0x3,r7 != the real one @0x4FB82 / V31P's FLASHED byte sequence"
    assert V54.shl(PAYLOAD_SHIFT, R7) != V55.sar(PAYLOAD_SHIFT, R7) and \
        V54.shl(PAYLOAD_SHIFT, R7) != FF.shr(PAYLOAD_SHIFT, R7), \
        "shl collapsed onto a RIGHT shift -- the payload would land in the wrong bits"
    assert V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == PIN_LDBU_BYTE4[1], "the byte4 read changed"
    assert FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP) == PIN_STB_BYTE4[1], "the byte4 store changed"
    assert HOOK_STOCK == PIN_MOVEA_HOOK[1], "the displaced hook instruction changed"
    assert FF.JMP_LP == PIN_JMP_LP[1], "jmp [lp] changed"
    _wire_model()


def build_cave():
    """pack_v74_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        mov   0x0,r7           ; r7 = 0
        ld.h  -0x6bd0[gp],r6   ; ★★★★ THE DAMPER'S OWN OUTPUT. SIGNED (op 0x39, NOT 0x3B = st.h)
        cmp   r0,r6            ; 🛑 Z set  <=>  the damper output is exactly 0
        be    +6               ; skip the 4-byte setter -- reads the cmp's OWN flags, nothing between
        movea 0x10,r0,r7       ; bit7 = (gp-0x6bd0 != 0)   THE POSITIVE CONTROL
        ld.bu -0x67fa[gp],r6   ; ★★ THE STATE (byte cell; NEGATIVE disp; op 0x3C, EVEN disp)
        andi  0xf,r6,r6        ; 4 bits -- lossless; value set {1,3..11}, so 0 is impossible
        or    r6,r7            ; r7 |= state   🛑 NOT `or r7,r6` -- the fields are decoded, not
                               ;                merely byte-pinned, because both forms are real
        shl   0x3,r7           ; the 5-bit field -> bits 7:3 (V31P's FLASHED idiom; Honda's @0x4FB82)
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4   (r6 is free again: the field is in r7)
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        <22 bytes of 0x00 = `nop`, AFTER `jmp [lp]` ⇒ unreachable; the extent stays 68>
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

    emit(FF.movi5(0, R7), "mov 0x0,r7          ; r7 = 0")
    emit(V55.ldh(DAMP_DISP, R6),
         f"ld.h -0x{DAMP_DISP:04x}[gp],r6 ; ★★★★ THE DAMPER OUTPUT (SIGNED, op MUST be 0x39)",
         writes_r6=True)
    cmp_idx = len(listing)
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; 🛑 SETS Z iff the damper output is exactly 0")
    br_idx = len(listing)
    emit(FF.bcond(COND_BE, BE_SKIP), "be +6               ; Z => damper == 0 -> skip the setter")
    emit(FF.movea(W_DAMP_NZ, R0, R7),
         f"movea 0x{W_DAMP_NZ:x},r0,r7    ; bit7 = (gp-0x{DAMP_DISP:04x} != 0)  POSITIVE CONTROL")
    label = CAVE_BASE + len(body)
    emit(V55.ldbu_any(-STATE_DISP, R6),
         f"ld.bu -0x{STATE_DISP:04x}[gp],r6 ; ★★ THE STATE (byte, NEGATIVE disp, op 0x3C)",
         writes_r6=True)
    emit(V54.andi(STATE_MASK, R6, R6), "andi 0xf,r6,r6      ; 4 bits", writes_r6=True)
    or_pos = len(listing)
    emit(V54.or_rr(R6, R7), "or r6,r7            ; r7 |= state   🛑 NOT `or r7,r6`")
    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7          ; the 5-bit field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4",
         writes_r6=True)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0",
         writes_r6=True)
    emit(V54.or_rr(R7, R6), "or r7,r6", writes_r6=True)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp] ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction", writes_r6=True)
    ret_addr = CAVE_BASE + len(body)
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    code_len = len(body)
    pad = CAVE_EXTENT - code_len
    assert pad >= 0, f"the cave code is {code_len}B, over the PROVEN {CAVE_EXTENT}B extent"
    assert pad % 2 == 0, "the padding is not halfword-aligned"
    if pad:
        emit(bytes(pad), f"<{pad} x 0x00 = nop, AFTER `jmp [lp]` ⇒ UNREACHABLE; extent stays 68>")

    # ---- 🛑🛑 FLAG LIVENESS: the `cmp` must be IMMEDIATELY followed by its `be`. ------------------
    assert br_idx == cmp_idx + 1, \
        f"{br_idx - cmp_idx - 1} instruction(s) sit between the `cmp` and its `be` -- the branch " \
        "would read STALE flags, a silent and plausible-looking wrong answer"
    c_addr, c_raw, _ = listing[cmp_idx]
    b_addr, b_raw, _ = listing[br_idx]
    assert c_addr + 2 == b_addr and len(c_raw) == 2, "the cmp/be pair is not adjacent"
    assert ((struct.unpack("<H", c_raw)[0] >> 5) & 0x3F) == 0x0F, "listing[cmp_idx] is not a `cmp`"
    assert struct.unpack("<H", b_raw)[0] & 0xF == COND_BE, \
        "the flag branch is not `be` -- `bne` would INVERT the rung: bit7 would read the damper as " \
        "LIVE exactly when it is dead"

    # ---- GATE 2a: THE ONLY branch lands EXACTLY on an emitted instruction boundary ----------------
    # ⚠ The label is the address of the instruction AFTER the setter (listing[br+2]), NOT
    # `branch address + 6` -- that form is self-referential and would pass on any displacement.
    assert b_addr + BE_SKIP == label == listing[br_idx + 2][0], \
        f"`be +{BE_SKIP}` @0x{b_addr:05X} targets 0x{b_addr + BE_SKIP:05X}, not the state load " \
        f"0x{listing[br_idx + 2][0]:05X} -- +4 would land INSIDE the 4-byte movea"
    assert len(listing[br_idx + 1][1]) == 4 and listing[br_idx + 1][1] == PIN_MOVEA_10_R7[1], \
        "the skipped instruction is not the 4-byte `movea 0x10,r0,r7`"
    branches = [(i, a, r) for i, (a, r, _t) in enumerate(listing)
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    assert [i for i, _a, _r in branches] == [br_idx], \
        f"the cave has {len(branches)} Bcond(s), expected exactly one"
    # 🛑 THE PADDING'S UNREACHABILITY. The single branch is FORWARD and lands strictly before the
    # return, so control cannot reach past `jmp [lp]` and the 22 zero bytes are dead.
    assert b_addr < label < ret_addr, \
        f"the branch target 0x{label:05X} is not strictly between the branch and `jmp [lp]`"
    for _a, raw, text in listing:
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert raw == FF.JMP_LP or ((hw >> 5) & 0x3F) not in (0x1E, 0x1B), \
            f"'{text}' is a jr/jarl -- the cave must have a SINGLE exit"

    # ---- GATE 2b: r6/r7 liveness. Only the loads/masks may write r6; only r7 accumulates. --------
    for idx, (addr, raw, text) in enumerate(listing):
        if len(raw) > 4 or raw == FF.JMP_LP:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        if (hw >> 7) & 0xF == 0xB:                                # a Bcond writes no GPR
            continue
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                    # cmp -- flags only
            continue
        if raw == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP):            # a store's reg2 is the SOURCE
            continue
        want = R6 if addr in r6_writers else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    # ---- GATE 1 as a property of the EMITTED CODE: EXACTLY ONE store ------------------------------
    store_idx = [i for i, (_a, raw, _t) in enumerate(listing)
                 if len(raw) == 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert len(store_idx) == 1, f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[store_idx[0]][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the CAN-330 payload byte"
    for idx, (_a, raw, text) in enumerate(listing):
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"
    # ---- geometry ---------------------------------------------------------------------------------
    assert or_pos == 7, f"`or r6,r7` is at index {or_pos}, expected 7 (after the 0xF mask)"
    assert listing[or_pos - 1][1] == V54.andi(STATE_MASK, R6, R6), \
        "the accumulate is not immediately preceded by the 0xF mask -- an unmasked state >= 16 " \
        "would carry into bit7 and, after the shift, past the byte"
    assert listing[or_pos + 1][1] == V54.shl(PAYLOAD_SHIFT, R7), \
        "the accumulate is not immediately followed by `shl 0x3,r7`"
    ret_idx = [i for i, (_a, r, _t) in enumerate(listing) if r == FF.JMP_LP]
    assert ret_idx == [14], f"`jmp [lp]` is at {ret_idx}, expected exactly index 14"
    assert listing[13][1] == HOOK_STOCK, "displaced movea must precede the return"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert bytes(body[code_len:]) == bytes(pad), "the padding is not all zero"
    assert code_len == 2 + 4 + 2 + 2 + 4 + 4 + 4 + 2 + 2 + 4 + 4 + 2 + 4 + 4 + 2 == 46, \
        f"the cave code is {code_len}B, the budget says 46"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == CAVE_EXTENT == 68, \
        f"cave {len(body)}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, in Python, from raw bytes.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. Extended from V73's decoder with `mov imm5` (0x10) and `cmp reg1,reg2` (0x0F).
    """
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        if hw == 0x0000:
            n, m = 2, "nop"
        elif (hw >> 7) & 0xF == 0xB:                                      # Format III Bcond
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
        elif hw == 0x007F or (op6 == 0x03 and reg2 == 0):
            n, m = 2, "jmp [lp]"
        elif op6 == 0x10:
            n, m = 2, f"mov {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
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
        else:
            n, m = 2, f"?? 0x{hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


# =====================================================================================================
# Censuses -- raw byte scans, because `search_instructions` silently undercounts
# =====================================================================================================

def cell_census(buf, disp, cave_span):
    """(firmware reads, firmware writes, cave hits) for gp-disp, by raw LE byte scan."""
    hits = V64.gp_access_census(buf, disp)
    fw = [h for h in hits if h[0] not in cave_span]
    cave = [h for h in hits if h[0] in cave_span]
    return ([h for h in fw if h[1].startswith("ld.")],
            [h for h in fw if not h[1].startswith("ld.")], cave)


def assert_probe_censuses(buf, cave_span, expect_cave):
    """GATE 1 (RAM ownership) for BOTH probed cells, as a measurement from raw bytes.

    🛑 The cave must READ each cell and write NEITHER. `gp-0x67fa` is lockstep-checked against
    `gp-0x4c39` and a stray write escalates; `gp-0x6bd0` is the damper's own output.
    """
    out = {}
    for disp, (n_read, n_write, rmn, wmn), want_reg in (
            (STATE_DISP, STATE_CENSUS, R6), (DAMP_DISP, DAMP_CENSUS, R6)):
        reads, writes, cave = cell_census(buf, disp, cave_span)
        assert all(m in rmn for _a, m, _r in reads), f"gp-0x{disp:04x}: unexpected read WIDTH/SIGN"
        assert all(m in wmn for _a, m, _r in writes), f"gp-0x{disp:04x}: unexpected write WIDTH"
        assert len(reads) == n_read, \
            f"gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert len(writes) == n_write, \
            f"gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}"
        if expect_cave:
            assert len(cave) == 1 and cave[0][1].startswith("ld.") and cave[0][2] == want_reg, \
                f"gp-0x{disp:04x}: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, " \
                f"expected exactly one load into r{want_reg} -- a store here would CORRUPT the cell"
        else:
            assert not cave, f"the source image's cave already touches gp-0x{disp:04x}"
        out[disp] = (len(reads), len(writes))
    _r, dwrites, _c = cell_census(buf, DAMP_DISP, cave_span)
    assert [a for a, _m, _r in dwrites] == DAMP_WRITERS, \
        f"gp-0x{DAMP_DISP:04x} writers moved: {[hex(a) for a, _m, _r in dwrites]}"
    # 🛑 the SHADOW must be untouched by the cave -- a write there is the other half of the lockstep.
    _sr, _sw, scave = cell_census(buf, STATE_SHADOW_DISP, cave_span)
    assert not scave, f"the cave touches the lockstep shadow gp-0x{STATE_SHADOW_DISP:04x}"
    return out


def assert_state_value_set(buf):
    """★★ Re-derive `gp-0x67fa`'s value set from its 33 writers' own literals, on THIS image.

    The probe's structural-liveness claim rests entirely on `0 is unreachable`, so it is MEASURED
    here rather than quoted. Three writers store a register instead of an inline literal; all three
    were read in Ghidra and are named with their values (0x1A0BA re-stores the cell's own value
    during the shadow compare, so it introduces nothing).
    """
    hits = V64.gp_access_census(buf, STATE_DISP)
    writes = [h for h in hits if h[1] == "st.b"]
    assert len(writes) == STATE_CENSUS[1] == 33, f"{len(writes)} writers, expected 33"
    vals, nonliteral = set(), []
    for addr, _m, src in writes:
        found = None
        for k in range(1, 13):
            p = addr - 2 * k
            hw = u16(buf, p)
            if ((hw >> 5) & 0x3F) == 0x10 and (hw >> 11) == src:          # mov imm5,rN
                imm = hw & 0x1F
                found = imm - 32 if imm & 0x10 else imm
                break
            if ((hw >> 5) & 0x3F) == 0x31 and (hw >> 11) == src and (hw & 0x1F) == 0:  # movea imm,r0
                found = u16(buf, p + 2)
                break
        if found is None:
            nonliteral.append(addr)
        else:
            vals.add(found)
    assert set(nonliteral) == set(STATE_NONLITERAL_WRITERS), \
        f"the non-literal writer set moved: {[hex(a) for a in nonliteral]}, expected " \
        f"{[hex(a) for a in STATE_NONLITERAL_WRITERS]}"
    known = {v for v in STATE_NONLITERAL_WRITERS.values() if v is not None}
    assert vals | known == STATE_VALUE_SET, \
        f"gp-0x{STATE_DISP:04x}'s literal value set is {sorted(vals | known)}, expected " \
        f"{sorted(STATE_VALUE_SET)} -- the 4-bit lossless / 0-impossible claim rests on it"
    assert 0 not in vals and all(v < 16 for v in vals), \
        "a writer stores 0 or >= 16 -- structural liveness / losslessness is VOID"
    return sorted(vals | known), nonliteral


def assert_clamp_census(buf):
    """tp+0x507e (0xC407E): the friction lane's own clamp. THREE readers, ZERO writers, all `ld.h`."""
    d = CLAMP_ADDR - TP
    assert d == CLAMP_TP_DISP, f"0x{CLAMP_ADDR:05X} is not tp+0x{CLAMP_TP_DISP:04X}"
    out = []
    for mnem, op, kind in V64._FORMS:
        hw2 = d if kind == "disp" else (d & 0xFFFE) | (1 if kind == "odd" else 0)
        for o in ([0x3C | (d & 1)] if op is None else [op]):
            for reg2 in range(32):
                pat = struct.pack("<HH", (reg2 << 11) | (o << 5) | 5, hw2)     # reg1 = 5 = tp
                i = buf.find(pat)
                while i >= 0:
                    if i % 2 == 0:
                        out.append((i, mnem, reg2))
                    i = buf.find(pat, i + 1)
    out.sort()
    reads = [h for h in out if h[1].startswith("ld.")]
    writes = [h for h in out if not h[1].startswith("ld.")]
    assert [a for a, _m, _r in reads] == CLAMP_READERS, \
        f"tp+0x{d:04X} readers are {[hex(a) for a, _m, _r in reads]}, expected " \
        f"{[hex(r) for r in CLAMP_READERS]} -- all three inside FUN_00036c12"
    assert all(m == "ld.h" for _a, m, _r in reads), \
        "a tp+0x507e read is not `ld.h` -- the clamp is SIGNED and a `ld.hu` would break the sign"
    assert not writes, f"🛑 tp+0x{d:04X} HAS WRITERS at {[hex(a) for a, _m, _r in writes]}"
    return reads


# =====================================================================================================
# THE MODE COLUMNS
# =====================================================================================================

def derive_mode_columns(buf):
    """The engaged / disengaged mode sets, DERIVED from the config table on the image being built."""
    rows, engaged, disengaged = [], set(), set()
    for n in range(VARIANT_ROWS):
        o = VARIANT_KEY_TABLE + n * VARIANT_STRIDE
        key = bytes(buf[o:o + 5]).decode("ascii", "replace")
        m = list(buf[VARIANT_IDX_TABLE + n * VARIANT_STRIDE:VARIANT_IDX_TABLE + n * VARIANT_STRIDE + 4])
        rows.append((n, key, m))
        engaged.update(m[c] for c in COL_ENGAGED)
        disengaged.update(m[c] for c in COL_DISENGAGED)
    assert tuple(sorted(engaged)) == ENGAGED_EXPECTED, \
        f"the derived ENGAGED set is {sorted(engaged)}, the spec says {list(ENGAGED_EXPECTED)}"
    assert tuple(sorted(disengaged)) == DISENGAGED_EXPECTED, \
        f"the derived DISENGAGED set is {sorted(disengaged)}, the spec says {list(DISENGAGED_EXPECTED)}"
    assert not (engaged & disengaged), \
        f"🛑 THE COLUMNS ARE NOT DISJOINT ({sorted(engaged & disengaged)}) -- writing the engaged " \
        "column would reach manual/parking steering and the whole safety argument collapses"
    assert rows[THIS_CAR_ROW][1] == THIS_CAR_KEY and rows[THIS_CAR_ROW][2] == THIS_CAR_MODES, \
        f"row {THIS_CAR_ROW} is {rows[THIS_CAR_ROW][1]!r} {rows[THIS_CAR_ROW][2]}, expected " \
        f"{THIS_CAR_KEY!r} {THIS_CAR_MODES} -- V73's on-car probe reading rests on it"
    assert LIVE_MODE in engaged and THIS_CAR_MODES[0] in disengaged, \
        "the live mode is not in the engaged column"
    return rows, tuple(sorted(engaged)), tuple(sorted(disengaged))


# =====================================================================================================
# The delivered damper authority -- FUN_00034350's Q10 chain, mirrored EXACTLY
# =====================================================================================================

def ceiling_floor(buf, mode):
    """That mode's OWN ceiling floor, re-read per mode. 🛑 NOT assumed constant across modes."""
    base = factor_rec(buf, CEILING_PTRS, mode)
    n, xs, ys = rec_any(buf, base)
    assert (n, xs, ys) == (2, CEILING_X, CEILING_Y), \
        f"mode {mode}'s ceiling @0x{base:05X} is ({n}, {xs}, {ys}), expected (2, {CEILING_X}, " \
        f"{CEILING_Y}) -- the no-clip floor rests on it and it is VERIFIED per mode"
    return ys[0]


def damper_authority(buf, mode, speed_counts=0, rate=0, seed=Q10):
    """|gp-0x6bd0| for ANY mode, mirroring FUN_00034350's Q10 chain EXACTLY.

        gp-0x6bd0 = ((((seed*B)>>10)*C)>>10)*D)>>10)*E)>>10, then clamped to +/- the ceiling

    Every record is DEREFERENCED at `mode`, so this cannot be pointed at the wrong table by a stale
    literal. FactorB and FactorD are FLAT 1024 on every engaged mode (asserted by the caller).
    """
    # 🛑 rec_any, not a fixed-offset reader: FactorD is a FIVE-point record.
    c = LM.lerp_int(speed_counts, *rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))[1:])
    e = LM.lerp_int(rate, *rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))[1:])
    b = LM.lerp_int(speed_counts, *rec_any(buf, factor_rec(buf, FACTOR_B_PTRS, mode))[1:])
    d = LM.lerp_int(rate, *rec_any(buf, factor_rec(buf, FACTOR_D_PTRS, mode))[1:])
    v = (seed * b) >> 10
    v = (v * c) >> 10
    v = (v * d) >> 10
    return (v * e) >> 10


def friction_authority(buf, rec, speed_counts, drive):
    """|gp-0x6b26| for the friction lane, mirroring FUN_00036c12's arithmetic EXACTLY.

        sVar7 = LERP(gp-0x6a5e voted speed, record)          <- Y is NEGATIVE throughout
        iVar4 = ((short)(drive) * sVar7 >> 6) * 0x111        <- 273
        iVar5 = iVar4 >> 0x12                                <- 18
        clamp SYMMETRICALLY to +/- *(short *)(tp+0x507e)
    """
    y = LM.lerp_int(speed_counts, rec3_x(buf, rec), rec3_y(buf, rec))
    v = ((drive * y) >> 6) * 0x111
    v >>= 0x12
    lim = s16(buf, CLAMP_ADDR)
    return max(-lim, min(lim, v))


def derive_lever_e(buf, modes):
    """THE CORE EDIT, derived: FactorC `Y[0] := Y[2]`, FactorE `X[0] := 6` and `Y[1] := Y[2]`.

    Returns {cell_address: (old, new, label, mode, factor)}. Raises if ANY record fails to parse as a
    4-point form -- 🛑 the layout is never guessed -- or if two modes alias onto one record.
    """
    edits, seen = {}, {}
    for mode in modes:
        cb = factor_rec(buf, FACTOR_C_PTRS, mode)
        eb = factor_rec(buf, FACTOR_E_PTRS, mode)
        for base, name in ((cb, "FactorC"), (eb, "FactorE")):
            assert base not in seen, \
                f"mode {mode}'s {name} @0x{base:05X} is ALSO mode {seen[base]}'s -- two modes alias " \
                "onto one record and the second edit would read a mutated 'old' value"
            seen[base] = mode
            n, xs, ys = rec_any(buf, base)
            assert n == 4, \
                f"🛑 {name} mode {mode} @0x{base:05X} declares count {n}, not 4. STOP: do not guess."
            assert len(set(xs)) == 4 and all(x > 0 for x in xs) and \
                all(b > a for a, b in zip(xs, xs[1:])), f"{name} mode {mode} X = {xs} is not strictly increasing"
            assert all(0 <= y < 0x8000 for y in ys), f"{name} mode {mode}: a Y is not a positive short"
        # ---- FactorC: Y[0] := Y[2], capped so the newly-reachable corner cannot saturate ----------
        _n, _cx, cy = rec_any(buf, cb)
        _n, ex, ey = rec_any(buf, eb)
        floor = ceiling_floor(buf, mode)
        worst = (cy[2] * ey[3]) >> 10
        cap = (floor * Q10) // ey[3]
        c_new = min(cy[2], cap) if worst > floor else cy[2]
        assert ((c_new * ey[3]) >> 10) <= floor, \
            f"mode {mode}: even the capped C_Y0 {c_new} saturates ({(c_new * ey[3]) >> 10} > {floor})"
        edits[cb + REC4_Y_OFF] = (cy[0], c_new, f"FactorC mode {mode:2d} Y[0]", mode, "FactorC")
        # ---- FactorE: X[0] := 6 (open the rate dead zone) and Y[1] := Y[2] ------------------------
        assert ex[0] in E_X0_STOCK_SET, \
            f"🛑 FactorE mode {mode} X[0] is {ex[0]}, not one of the stock dead-zone edges " \
            f"{sorted(E_X0_STOCK_SET)} -- STOP and report rather than guess the axis"
        assert E_X0_NEW < ex[1], f"mode {mode}: the new X[0] {E_X0_NEW} is not below X[1] {ex[1]}"
        # ⚠ THE HAZARD BAND, asserted rather than remembered. `X0 < 30 with Y1 > 300` is the zone
        # flagged as not-to-fly-without-telemetry: the ramp starts close to zero AND is steep. 12 is
        # the top of the recommended 6-12 band; anything lower must be a deliberate re-decision.
        assert E_X0_NEW >= E_X0_MIN_SAFE, \
            f"🛑 X[0] = {E_X0_NEW} is below the agreed floor {E_X0_MIN_SAFE}. Y[0] = 0 is preserved " \
            "so there is no discontinuity at zero rate, but a smaller X[0] makes the ramp steeper " \
            "in exactly the band that was flagged. STOP and re-decide deliberately."
        edits[eb + REC4_X_OFF] = (ex[0], E_X0_NEW, f"FactorE mode {mode:2d} X[0]", mode, "FactorE")
        edits[eb + REC4_Y_OFF + 2] = (ey[1], ey[2], f"FactorE mode {mode:2d} Y[1]", mode, "FactorE")
    assert len(edits) == 3 * len(modes) == 39, f"{len(edits)} cells, expected 39"
    return edits


def derive_friction_edits(buf, modes):
    """LEVER D': the 3-point friction Y row x1.5 on every engaged mode. Addresses DEREFERENCED."""
    want = [(y * FRICTION_SCALE_NUM) // FRICTION_SCALE_DEN for y in FRICTION_Y_STOCK]
    assert want == FRICTION_Y_NEW, f"x1.5 gives {want}, not the declared {FRICTION_Y_NEW}"
    assert all(y * FRICTION_SCALE_NUM % FRICTION_SCALE_DEN == 0 for y in FRICTION_Y_STOCK), \
        "x1.5 is not exact on one of the Y values -- the multiplier would be silently rounded"
    assert all(-0x8000 <= y < 0x8000 for y in want), "a scaled Y does not fit in int16"
    assert all(a < b <= 0 for a, b in zip(want, want[1:])), \
        "the scaled Y row is not monotone increasing toward zero -- the stock shape must be preserved"
    out, seen = {}, {}
    for mode in modes:
        base = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        assert base not in seen, f"mode {mode}'s friction record is ALSO mode {seen[base]}'s"
        seen[base] = mode
        n, xs, ys = rec_any(buf, base)
        assert (n, xs, ys) == (FRICTION_NPT, FRICTION_X, FRICTION_Y_STOCK), \
            f"🛑 friction mode {mode} @0x{base:05X} is ({n}, {xs}, {ys}), expected " \
            f"({FRICTION_NPT}, {FRICTION_X}, {FRICTION_Y_STOCK}) -- STOP, do not guess the layout"
        out[base] = (base + FRICTION_Y_OFF, mode)
    assert len(out) == len(modes) == 13, f"{len(out)} friction records, expected 13"
    return out, want


# =====================================================================================================
# The MUST-REMAIN sites
# =====================================================================================================

def assert_no_partial_record_write(buf, base_img, label):
    """★ THE GENERAL FORM OF THE HYBRID-RECORD DEFECT: a UNIFORM Y row must stay uniform.

    🛑 WHY THIS EXISTS. An earlier V74 cut reverted `0xD2A7E`/`0xD2ABA` -- Y[0] of the two gain_B
    mode-10 records -- to stock. But V72 had set ALL FOUR Y cells of each record to 5244, so a
    two-cell revert produced `[3072, 5244, 5244, 5244]`: **neither stock nor V72, and attributable
    to no build.** This kit's expensive failures have all been artefacts that LOOKED interpretable.

    The rule is the general one, not a spot check on those two addresses: **if a record's Y row was
    UNIFORM on the base image, it must still be uniform on the output.** Any partial write to a
    multi-cell row breaks that, whichever record it lands in. It is deliberately one-directional --
    V74 legitimately makes already-non-uniform rows (FactorC, FactorE) more so, and that is allowed;
    what is forbidden is *manufacturing* a hybrid out of a row that carried a single decided value.
    """
    checked, uniform = 0, 0
    recs = {u32(buf, arr + m * 4)
            for arr in (FRICTION_PTR_ARRAY, FACTOR_B_PTRS, FACTOR_C_PTRS, FACTOR_D_PTRS,
                        FACTOR_E_PTRS, CEILING_PTRS)
            for m in range(34)}
    recs |= set(V72_GAIN_A) | set(GAIN_B_M10_KEEP) | set(GAIN_A_STOCK_RECS)
    for base in sorted(recs):
        n_b, _xb, yb = rec_any(base_img, base)
        n_o, _xo, yo = rec_any(buf, base)
        checked += 1
        assert n_b == n_o, f"{label}: the record @0x{base:05X} changed its point COUNT {n_b} -> {n_o}"
        if len(set(yb)) == 1 and len(yb) > 1:
            uniform += 1
            assert len(set(yo)) == 1, \
                f"🛑 {label}: record 0x{base:05X} had a UNIFORM Y row {yb} on the base and is now " \
                f"{yo} -- a PARTIAL WRITE to a multi-cell record. That is the exact shape of the " \
                "0xD2A7E hybrid: a row attributable to no build. Write the whole row or none of it."
    # the two that motivated the rule, named explicitly so a reader sees the instance and the rule
    for base, want in GAIN_B_M10_KEEP.items():
        got = rec4_y(buf, base)
        assert len(set(got)) == 1 and got == want, \
            f"🛑 {label}: gain_B mode-10 0x{base:05X} Y is {got}, expected the UNIFORM {want}"
    return checked, uniform


def assert_must_not_change(buf, label, stock, base_img):
    """🛑 The frozen keep-list, by VALUE. A span check passes on the wrong build."""
    for addr, raw in SAR_SITES.items():
        assert bytes(buf[addr:addr + 2]) == raw == bytes(stock[addr:addr + 2]), \
            f"{label}: the `sar` site 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
            f"the STOCK {raw.hex()} -- 🛑 reintroducing V62's `a9` CAUSES GRIND #2, and the " \
            "operator's reframing makes THE FIX AN ABSENCE"
    assert buf[V72_GATE[0]] == V72_GATE[1], \
        f"{label}: the gate 0x{V72_GATE[0]:05X} is 0x{buf[V72_GATE[0]]:02X}, expected 0x{V72_GATE[1]:02X}"
    for addr, want in ARMS_STOCK.items():
        assert u16(buf, addr) == want, \
            f"{label}: 0x{addr:05X} is {u16(buf, addr)}, expected {want}"
    for base, want in V72_GAIN_A.items():
        assert rec4_y(buf, base) == want, \
            f"{label}: gain_A 0x{base:05X} Y is {rec4_y(buf, base)}, expected V72's {want} -- that " \
            "r26 cut is the leading candidate for the macro-ratchet fix. Keep EXACTLY; do not deepen."
    for base in GAIN_A_STOCK_RECS:
        assert bytes(buf[base:base + REC_STRIDE]) == bytes(stock[base:base + REC_STRIDE]), \
            f"{label}: gain_A 0x{base:05X} is not byte-STOCK -- the r26 cut is PARTIAL by design"
    assert u16(buf, V72_LEVER_C[0]) == V72_LEVER_C[1], f"{label}: V72's LEVER C 0x{V72_LEVER_C[0]:05X}"
    assert buf[V72_CARRIED[0]] == V72_CARRIED[1], \
        f"{label}: the carried 0x{V72_CARRIED[0]:05X} is 0x{buf[V72_CARRIED[0]]:02X}"
    assert u16(buf, CLAMP_ADDR) == CLAMP_VALUE, \
        f"{label}: 0x{CLAMP_ADDR:05X} is {u16(buf, CLAMP_ADDR)}, expected V73's live {CLAMP_VALUE}"
    assert CLAMP_VALUE <= CLAMP_HARD_CAP < AGGREGATOR_ZERO_REJECT, \
        "🛑 the clamp is at or above the hard cap -- the aggregator's +/-0x400 window is a " \
        "ZERO-REJECT, so a lane landing on the cliff contributes NOTHING"
    assert u16(buf, CLAMP_NEIGHBOUR[0]) == CLAMP_NEIGHBOUR[1], \
        f"{label}: 0x{CLAMP_NEIGHBOUR[0]:05X} moved -- adjacent to the clamp, owner UNIDENTIFIED"
    # 🛑 the pointer arrays THEMSELVES must be byte-identical to STOCK -- every edited table is only
    # reachable through them, and a moved pointer would silently redirect the whole lever.
    for arr in (FRICTION_PTR_ARRAY, FACTOR_B_PTRS, FACTOR_C_PTRS, FACTOR_D_PTRS, FACTOR_E_PTRS,
                CEILING_PTRS):
        for mode in range(34):
            got, want = u32(buf, arr + mode * 4), u32(stock, arr + mode * 4)
            assert got == want, \
                f"{label}: 0x{arr:05X}[{mode}] -> 0x{got:05X} but STOCK says 0x{want:05X}"
    # the config table itself, and the whole DISENGAGED column's records
    assert bytes(buf[VARIANT_KEY_TABLE:VARIANT_KEY_TABLE + VARIANT_ROWS * VARIANT_STRIDE]) == \
        bytes(stock[VARIANT_KEY_TABLE:VARIANT_KEY_TABLE + VARIANT_ROWS * VARIANT_STRIDE]), \
        f"{label}: the config table 0xCD000 moved"
    V55.assert_variant_tables(buf)
    A.assert_ratchet_edit(buf, label, expect_edited=True)
    A.assert_no_external_entry(buf)
    A.assert_governor_monitor_safety(buf, label)
    V72.assert_lever_c_single_reader(bytes(buf))
    # ---- the inherited V72 guard, with its ONE documented relaxation ------------------------------
    # V72.assert_untouched asserts FactorC/E **mode 12** byte-stock; V73 edited those two Y[0] cells
    # and V74 carries them. Restore them on a COPY, run the FULL guard, and assert the exception set
    # is exactly those two cells -- the same idiom V73 used, so the guard is never weakened.
    probe = bytearray(buf)
    m12 = [factor_rec(buf, p, 12) + REC4_Y_OFF for p in (FACTOR_C_PTRS, FACTOR_E_PTRS)]
    for cell in m12:
        struct.pack_into("<H", probe, cell, 0)
    V72.assert_untouched(probe, label, stock)
    exc = [i for i in range(START, END) if probe[i] != buf[i]]
    allowed = {c + k for c in m12 for k in (0, 1)}
    assert set(exc) <= allowed, \
        f"{label}: the V72-guard relaxation reaches {[hex(x) for x in exc if x not in allowed][:8]}"
    # ---- V57's decoupling / V53's eleven STOCK_CALS, with V71A's one-byte relaxation --------------
    probe2 = bytearray(buf)
    struct.pack_into("<H", probe2, A.RATCHET_ADDR, A.RATCHET_STOCK_HW)
    V57.assert_decoupled(probe2, f"{label} (with 0x454FE restored for the inherited guard)")
    exc2 = [i for i in range(START, END) if probe2[i] != buf[i]]
    assert exc2 == [A.RATCHET_ADDR], \
        f"{label}: the V57 guard relaxation covers {[hex(x) for x in exc2]}, expected " \
        f"exactly [0x{A.RATCHET_ADDR:05X}]"
    # ---- ★ no PARTIAL write to any multi-cell record (the 0xD2A7E hybrid's general form) --------
    if base_img is not None:
        nrec, nuni = assert_no_partial_record_write(buf, base_img, label)
        assert nuni >= 6, f"{label}: only {nuni} uniform-Y records found across {nrec} -- the guard "             "is not seeing the records it is supposed to protect"
    # ---- the DISENGAGED column: every one of its records byte-identical to the V73 base -----------
    if base_img is not None:
        for mode in DISENGAGED_EXPECTED:
            for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_C_PTRS, "FactorC"),
                               (FACTOR_D_PTRS, "FactorD"), (FACTOR_E_PTRS, "FactorE"),
                               (CEILING_PTRS, "ceiling"), (FRICTION_PTR_ARRAY, "friction")):
                base = factor_rec(buf, ptrs, mode)
                # 🛑 the record's OWN length -- a flat 0x18 window spills into the NEXT mode's record
                n = rec_len(buf, base)
                assert bytes(buf[base:base + n]) == bytes(base_img[base:base + n]), \
                    f"🛑 {label}: the DISENGAGED mode-{mode} {name} @0x{base:05X} MOVED -- manual " \
                    "and parking steering must stay byte-stock; that is V74's whole safety argument"


def assert_v74_shape(buf, label, base_img, modes, lever_e, friction):
    """The post-edit shape: only the intended cells moved, and the surface rules hold."""
    for mode in modes:
        cb, eb = factor_rec(buf, FACTOR_C_PTRS, mode), factor_rec(buf, FACTOR_E_PTRS, mode)
        n_c, cx, cy = rec_any(buf, cb)
        n_e, ex, ey = rec_any(buf, eb)
        cy0, cx0 = rec_any(base_img, cb)[2], rec_any(base_img, cb)[1]
        ey0, ex0 = rec_any(base_img, eb)[2], rec_any(base_img, eb)[1]
        # 🛑 FactorE MUST stay monotone non-decreasing -- that is what protects rate-proportionality.
        assert all(b >= a for a, b in zip(ey, ey[1:])), \
            f"🛑 {label}: FactorE m{mode} Y = {ey} is NOT monotone non-decreasing"
        # ⚠ FactorC's SPEED-axis dip (Y[0] > Y[1]) is EXPECTED and allowed -- it confines the change
        # to creep. Only the rate axis carries the proportionality requirement.
        assert cy[1:] == cy0[1:] and cx == cx0, f"{label}: FactorC m{mode}: only Y[0] may move"
        assert ey[0] == ey0[0] and ey[2:] == ey0[2:], f"{label}: FactorE m{mode}: only Y[1] may move"
        assert ex[0] == E_X0_NEW and ex[1:] == ex0[1:], f"{label}: FactorE m{mode}: only X[0] may move"
        assert all(b > a for a, b in zip(ex, ex[1:])), f"{label}: FactorE m{mode} X = {ex} not increasing"
        assert (n_c, n_e) == (4, 4), f"{label}: a record's count moved"
        # ★ V72's ERROR, ASSERTED AGAINST: FactorE must not become a CONSTANT (bang-bang relay).
        if len(set(ey)) == 1:
            assert len(set(ey0)) == 1, \
                f"🛑 {label}: V74 FLATTENED FactorE m{mode} to {ey} -- that is the near-bang-bang " \
                "relay V72 produced on mode 10 and this build must NOT repeat"
        assert ey[0] == 0 or ey0[0] != 0, \
            f"{label}: FactorE m{mode} Y[0] moved off its stock value"
        # FactorB / FactorD FLAT 1024, read BY COUNT, and the ceiling byte-identical.
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
            base = factor_rec(buf, ptrs, mode)
            n, _xs, ys = rec_any(buf, base)
            assert set(ys) == {Q10}, f"{label}: {name} m{mode} ({n}-point) is not FLAT {Q10}: {ys}"
            ln = rec_len(buf, base)
            assert bytes(buf[base:base + ln]) == bytes(base_img[base:base + ln]), \
                f"{label}: {name} m{mode} @0x{base:05X} moved"
        base = factor_rec(buf, CEILING_PTRS, mode)
        ln = rec_len(buf, base)
        assert bytes(buf[base:base + ln]) == bytes(base_img[base:base + ln]), \
            f"{label}: the mode-{mode} ceiling @0x{base:05X} moved"
        # the friction record
        fb = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        n, xs, ys = rec_any(buf, fb)
        assert (n, xs, ys) == (FRICTION_NPT, FRICTION_X, FRICTION_Y_NEW), \
            f"{label}: the mode-{mode} friction record @0x{fb:05X} is ({n}, {xs}, {ys})"
    for addr, (_old, new, lbl, _m, _f) in lever_e.items():
        assert u16(buf, addr) == new, f"{label}: {lbl} @0x{addr:05X} is {u16(buf, addr)}, want {new}"
    for fb, (yoff, _mode) in friction.items():
        assert rec3_y(buf, fb) == FRICTION_Y_NEW, f"{label}: friction @0x{fb:05X} did not take Y"
    for base, want in GAIN_B_M10_KEEP.items():
        got = rec4_y(buf, base)
        assert got == want and \
            bytes(buf[base:base + REC_STRIDE]) == bytes(base_img[base:base + REC_STRIDE]), \
            f"{label}: gain_B mode-10 0x{base:05X} Y is {got}, expected V73's {want} byte-for-byte " \
            "-- the revert was WITHDRAWN and V74 must not SUBTRACT anything from the car"


def assert_no_clip(buf, base_img, modes, grid, label):
    """★ THE SURFACE RULE, stronger than a hand-drawn region.

    For every swept (speed, rate) point and every engaged mode: either the new damper authority is at
    or below that mode's OWN ceiling floor, or the point did not move. ⇒ V74 never raises the surface
    into saturation anywhere, so it cannot put a hard-clipping element inside a feedback loop at the
    frequency of a high-Q resonance. It also passes mode 11, whose 793 is V72's pre-existing flat
    FactorE and which V74 raises at ZERO points.
    """
    report = {}
    for mode in modes:
        fl = ceiling_floor(buf, mode)
        bad, raised, aff = [], 0, 0
        peak, peak_b = 0, 0
        for v, r in grid:
            now = damper_authority(buf, mode, v, r)
            was = damper_authority(base_img, mode, v, r)
            peak, peak_b = max(peak, now), max(peak_b, was)
            if now > was:
                raised += 1
                aff = max(aff, now)
                if now > fl:
                    bad.append((v, r, was, now))
        assert not bad, \
            f"🛑 {label}: mode {mode} RAISES the surface above its own ceiling floor {fl} at " \
            f"{len(bad)} point(s), e.g. {bad[:3]} ⇒ the damper would SATURATE there. That puts a " \
            "hard-clipping element inside a feedback loop and CREATES limit cycles."
        assert peak == peak_b, \
            f"{label}: mode {mode}'s GLOBAL peak moved {peak_b} -> {peak}"
        report[mode] = (fl, raised, aff, peak)
    return report


def assert_decoder_matches(cave_bytes):
    """🛑 The decoder's CAVE_HEX must equal the cave just emitted, so it cannot drift."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, "V74: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"V74: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    for token in ("V74", os.path.basename(OUT), "0x67FA", "0x6BD0", "0xC4124"):
        assert token in txt, f"V74: the decoder does not carry '{token}'"
    for name, val in (("BIT_DAMP_NZ", BIT_DAMP_NZ), ("STATE_FIELD", STATE_FIELD),
                      ("STATE_SHIFT", PAYLOAD_SHIFT), ("PROBE_MASK", PROBE_MASK)):
        mm = re.search(rf"^{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", txt, re.M)
        assert mm and int(mm.group(1), 0) == val, \
            f"V74: the decoder's {name} is {mm and mm.group(1)}, not {val}"
    for claim in ("STRUCTURAL", "POSITIVE CONTROL", "ENGAGED"):
        assert claim in txt.upper(), f"V74: the decoder never states '{claim}'"
    assert "2nd harmonic" not in txt, \
        "V74: the decoder repeats the RETRACTED 'grind #2 is grind #1's 2nd harmonic' claim"
    for stale in ("0x69A4", "0x6AC0", "0x63FD"):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale}", txt, re.M | re.I), \
            f"V74: {stale} is still a LIVE RUNG in the decoder"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it. Shorten TAG " \
        "BEFORE building; nothing has been written yet."

    v73 = bytearray(Path(SRC_BIN).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V73): {SRC_BIN}\n  SHA256 {hashlib.sha256(bytes(v73)).hexdigest()}")
    print(f"STOCK:        {STOCK_BIN}")
    for name, img in (("V73", v73), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert hashlib.sha256(bytes(v73)).hexdigest() == SRC_SHA256, \
        f"🛑 THE BASE IS NOT V73. SHA256 is {hashlib.sha256(bytes(v73)).hexdigest()}, expected " \
        f"{SRC_SHA256}. V74 is defined as V73 + these levers; any other base voids every claim."
    print("  ✅ the base SHA256 matches the recorded V73 image exactly.")

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_must_not_change(v73, "V73 source", stock, None)
    assert walk_all_blocks(bytes(v73)) == 0, "the V73 source's own CRC chain does not verify"
    assert_probe_censuses(bytes(v73), cave_span, expect_cave=False)
    print("  ✅ every MUST-NOT-CHANGE site, the six pointer arrays over all 34 modes, the config")
    print("     table, V72's LEVER C, the carried 0x454FE, the UNGATED gate byte, V57's decoupling,")
    print("     V53's eleven STOCK_CALS and the full CRC chain: all verified ON THE INPUT.")

    # ---- THE MODE COLUMNS --------------------------------------------------------------------------
    rows, ENGAGED, DISENGAGED = derive_mode_columns(bytes(v73))
    print(f"\n  🛑 THE CONFIG TABLE 0x{VARIANT_KEY_TABLE:05X} ({VARIANT_ROWS} keys, stride "
          f"0x{VARIANT_STRIDE:02X}, modes at +0x12..+0x15 = e012..e015):")
    for n, key, m in rows:
        mark = f"   <- ★★ THIS CAR (V73's on-car probe): manual {m[0]}, ENGAGED {m[2]}" \
            if n == THIS_CAR_ROW else ""
        print(f"     row {n:2d}  {key:6s}  disengaged {m[0]:2d},{m[1]:2d}   engaged {m[2]:2d},{m[3]:2d}"
              f"{mark}")
    print(f"\n     ENGAGED    (e014,e015) = {list(ENGAGED)}   <- V74 writes these 13")
    print(f"     DISENGAGED (e012,e013) = {list(DISENGAGED)}   <- byte-stock")
    print("     ✅ DERIVED from the table on this image, cross-checked against an independent")
    print("        literal, and asserted DISJOINT ⇒ manual and parking steering are untouched.")

    code = bytearray(v73)

    # ---- LEVER E' -- open BOTH dead zones -----------------------------------------------------------
    print(f"\n  LEVER E' -- OPEN BOTH DEAD ZONES on the {len(ENGAGED)} engaged modes. "
          f"FactorC Y[0] := Y[2] · FactorE X[0] := {E_X0_NEW} · FactorE Y[1] := Y[2].")
    print("    🛑 Every address is DEREFERENCED from the pointer arrays on the image being built.")
    lever_e = derive_lever_e(code, ENGAGED)
    print(f"\n    {'mode':>4} {'FactorC rec':>12} {'Y before':<24} {'FactorE rec':>12} "
          f"{'X before':<22} {'Y before':<22} {'floor':>6}")
    for mode in ENGAGED:
        cb, eb = factor_rec(code, FACTOR_C_PTRS, mode), factor_rec(code, FACTOR_E_PTRS, mode)
        print(f"    {mode:4d}      0x{cb:05X} {str(rec_any(code, cb)[2]):<24}      0x{eb:05X} "
              f"{str(rec_any(code, eb)[1]):<22} {str(rec_any(code, eb)[2]):<22} "
              f"{ceiling_floor(code, mode):6d}")
    # ⊕ the LIVE mode's geometry, against the independently stated expectation
    assert factor_rec(code, FACTOR_C_PTRS, LIVE_MODE) == LIVE_EXPECT["factor_c"], "live FactorC moved"
    assert factor_rec(code, FACTOR_E_PTRS, LIVE_MODE) == LIVE_EXPECT["factor_e"], "live FactorE moved"
    assert factor_rec(code, FRICTION_PTR_ARRAY, LIVE_MODE) == LIVE_EXPECT["friction"], "live fric moved"
    for key, addr in (("factor_c_y0", LIVE_EXPECT["factor_c"] + REC4_Y_OFF),
                      ("factor_e_x0", LIVE_EXPECT["factor_e"] + REC4_X_OFF),
                      ("factor_e_y1", LIVE_EXPECT["factor_e"] + REC4_Y_OFF + 2),
                      ("friction_y", LIVE_EXPECT["friction"] + FRICTION_Y_OFF)):
        assert addr == LIVE_EXPECT[key], \
            f"the LIVE mode's {key} derives to 0x{addr:05X}, the spec says 0x{LIVE_EXPECT[key]:05X}"
    print(f"    ✅ THE LIVE MODE {LIVE_MODE} derives to exactly the specified addresses: FactorC "
          f"0x{LIVE_EXPECT['factor_c']:05X} (Y[0] @0x{LIVE_EXPECT['factor_c_y0']:05X}),")
    print(f"       FactorE 0x{LIVE_EXPECT['factor_e']:05X} (X[0] @0x{LIVE_EXPECT['factor_e_x0']:05X}, "
          f"Y[1] @0x{LIVE_EXPECT['factor_e_y1']:05X}), friction 0x{LIVE_EXPECT['friction']:05X} "
          f"(Y @0x{LIVE_EXPECT['friction_y']:05X}).")

    capped = []
    print(f"\n    THE {len(lever_e)} EDITED CELLS:")
    for addr, (old, new, lbl, mode, _f) in sorted(lever_e.items()):
        assert u16(code, addr) == old, f"{lbl} @0x{addr:05X} is {u16(code, addr)}, expected {old}"
        struct.pack_into("<H", code, addr, new)
        cy2 = rec_any(v73, factor_rec(v73, FACTOR_C_PTRS, mode))[2][2]
        note = ""
        if lbl.startswith("FactorC") and new != cy2:
            capped.append((mode, cy2, new))
            note = f"   ⚠ CAPPED from Y[2] = {cy2} (no-clip)"
        print(f"      0x{addr:05X}  {old:5d} -> {new:5d}   {lbl}{note}")
    assert u16(code, LIVE_EXPECT["factor_c_y0"]) == LIVE_EXPECT["factor_c_y0_new"], "live C_Y0"
    assert u16(code, LIVE_EXPECT["factor_e_y1"]) == LIVE_EXPECT["factor_e_y1_new"], "live E_Y1"
    if capped:
        print(f"\n    ⚠ {len(capped)} MODE(S) NEEDED THE NO-CLIP CAP -- reported, not silently applied:")
        for mode, y2, new in capped:
            ey3 = rec_any(v73, factor_rec(v73, FACTOR_E_PTRS, mode))[2][3]
            print(f"      mode {mode:2d}: Y[2] = {y2} would give ({y2} * {ey3}) >> 10 = "
                  f"{(y2 * ey3) >> 10} > {CEILING_FLOOR}; capped to floor(512 * 1024 / {ey3}) = {new}")
        print(f"      (all three are TWAA-chassis modes, INERT on this car -- the live mode "
              f"{LIVE_MODE} needed no cap.)")

    # ---- LEVER D' -- the friction lane --------------------------------------------------------------
    print(f"\n  LEVER D' -- THE FRICTION LANE x1.5 (gp-0x6b26, FUN_000{FRICTION_FN:05x}) on the same "
          f"{len(ENGAGED)} modes. {len(ENGAGED) * 6} bytes:")
    friction, fric_y = derive_friction_edits(code, ENGAGED)
    print(f"    every engaged record is n={FRICTION_NPT}, X = {FRICTION_X} counts = "
          f"{[x // SPEED_COUNTS_PER_KMH for x in FRICTION_X]} km/h, Y = {FRICTION_Y_STOCK} "
          f"-> {fric_y}")
    for fb in sorted(friction):
        yoff, mode = friction[fb]
        struct.pack_into("<3h", code, yoff, *fric_y)
        print(f"      mode {mode:2d}  record 0x{fb:05X}  Y @0x{yoff:05X}  "
              f"{FRICTION_Y_STOCK} -> {rec3_y(code, fb)}")
    print(f"\n    THE DELIVERED FRICTION AUTHORITY on the LIVE mode {LIVE_MODE} "
          "(`(drive * Y >> 6) * 273 >> 18`, clamped to +/-850):")
    print("      drive |gp-0x6c2c|      0 km/h            20 km/h           90 km/h    (V73 -> V74)")
    live_fr = factor_rec(code, FRICTION_PTR_ARRAY, LIVE_MODE)
    for drive in (2000, 5000, 10000, 20000):
        row = []
        for vc in FRICTION_X:
            was = friction_authority(v73, live_fr, vc, drive)
            now = friction_authority(code, live_fr, vc, drive)
            row.append(f"{was:6d} -> {now:6d}")
        print(f"      {drive:12d}   " + "   ".join(row))
    creaders = assert_clamp_census(bytes(code))
    print(f"    ✅ [EVIDENCE, raw both-parity tp-relative byte scan on THIS image] the clamp "
          f"tp+0x{CLAMP_TP_DISP:04X} = {u16(code, CLAMP_ADDR)} (V73's, ALREADY LIVE ON-CAR -- not "
          "re-written here)")
    print(f"       has {len(creaders)} readers, ALL `ld.h`, ALL inside FUN_000{FRICTION_FN:05x}: "
          f"{[hex(a) for a, _m, _r in creaders]}, and ZERO writers.")

    # ---- 🛑 THE WITHDRAWN REVERT -- asserted UNTOUCHED, not written --------------------------------
    print("\n  🛑 0xD2A7E / 0xD2ABA ARE NOT TOUCHED -- the revert was WITHDRAWN. V74 is ADD-ONLY.")
    for base, want in sorted(GAIN_B_M10_KEEP.items()):
        got = rec4_y(code, base)
        assert got == want == rec4_y(v73, base), \
            f"gain_B mode-10 0x{base:05X} Y is {got}, expected V73's {want} -- V74 must not " \
            "SUBTRACT anything that is currently on the car"
        assert bytes(code[base:base + REC_STRIDE]) == bytes(v73[base:base + REC_STRIDE]), \
            f"gain_B mode-10 0x{base:05X} is not byte-identical to V73"
        print(f"      0x{base:05X}  Y = {got}   byte-identical to V73   (stock is "
              f"{rec4_y(stock, base)})")
    for addr, would in sorted(GAIN_B_M10_STOCK_Y0.items()):
        assert u16(code, addr) == 5244, f"0x{addr:05X} is {u16(code, addr)}, expected V72's 5244"
        assert u16(stock, addr) == would, f"STOCK 0x{addr:05X} is {u16(stock, addr)}, not {would}"
    print("      ⊕ A revert would have written 3072 / 2561 into Y[0] only -- but V72 (not V73) set")
    print("        ALL FOUR Y cells to 5244, so that leaves a row that is neither stock nor V72.")
    print("      🛑 AND THE DECISIVE REASON: these cells are inert *because* the car is row 11, which")
    print("         is an INFERENCE. If it were wrong the car is row 2, mode 10 is its DISENGAGED")
    print("         mode, and reverting would SUBTRACT something currently on the car.")

    # ---- THE SURFACE ------------------------------------------------------------------------------
    print(f"\n  ✅ DELIVERED DAMPING AUTHORITY (FactorB/D FLAT {Q10} ⇒ the chain reduces to "
          f"(C * E) >> 10, seed {Q10}):")
    grid = [(v, r) for v in range(0, 14001, 32) for r in range(0, 4501, 20)]
    surf = assert_no_clip(code, v73, ENGAGED, grid, "V74")
    print(f"    🛑 RECOMPUTED FROM THE BYTES JUST WRITTEN, not from the design note. Rate {BURST_RATE}"
          f" is the IN-BURST p50 [94.2, 113.0];")
    print(f"       {OUT_OF_BURST_RATE} is the OUT-of-burst p50 and is NOT the sizing input; "
          f"{BURST_RATE_69HZ} is the 6-9 Hz arm's p50.")
    print(f"      {'mode':>4} {'E@r99':>6} {'dose@99':>8} {'V73@99':>7} {'dose@127':>9} "
          f"{'dose@9':>7} {'floor':>6} {'raisedMax':>10} {'ptsRaised':>10} {'peak':>6}")
    doses = {}
    for mode in ENGAGED:
        fl, raised, aff, peak = surf[mode]
        d_now = damper_authority(code, mode, 0, BURST_RATE)
        d_was = damper_authority(v73, mode, 0, BURST_RATE)
        e_at_99 = LM.lerp_int(BURST_RATE, *rec_any(code, factor_rec(code, FACTOR_E_PTRS, mode))[1:])
        d_69 = damper_authority(code, mode, 0, BURST_RATE_69HZ)
        d_oob = damper_authority(code, mode, 0, OUT_OF_BURST_RATE)
        doses[mode] = d_now
        star = "  ★★ LIVE" if mode == LIVE_MODE else ""
        print(f"      {mode:4d} {e_at_99:6d} {d_now:8d} {d_was:7d} {d_69:9d} {d_oob:7d} {fl:6d} "
              f"{aff:10d} {raised:10d} {peak:6d}{star}")
    assert doses[LIVE_MODE] == LIVE_EXPECT["dose"], \
        f"the LIVE mode's dose at rate {BURST_RATE} is {doses[LIVE_MODE]}, the spec says " \
        f"{LIVE_EXPECT['dose']}"
    assert damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ) == LIVE_EXPECT["dose_69hz"], \
        f"the LIVE mode's dose at the 6-9 Hz rate {BURST_RATE_69HZ} is " \
        f"{damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ)}, the spec says " \
        f"{LIVE_EXPECT['dose_69hz']}"
    lo, hi = DOSE_REQUIREMENT
    assert lo <= doses[LIVE_MODE] <= hi, \
        f"the LIVE mode's dose {doses[LIVE_MODE]} is outside the sizing interval {DOSE_REQUIREMENT}"
    print(f"      ✅ every engaged mode: wherever V74 RAISES the surface it stays at or below that")
    print("         mode's own ceiling FLOOR, and the GLOBAL peak is byte-identical to the base.")
    print(f"      ★★ THE LIVE MODE {LIVE_MODE} delivers {doses[LIVE_MODE]} counts at the measured "
          f"burst rate {BURST_RATE} (V73: {damper_authority(v73, LIVE_MODE, 0, BURST_RATE)}), "
          f"against a requirement of ~43 {list(DOSE_REQUIREMENT)}.")
    e_stock = LM.lerp_int(BURST_RATE, *rec_any(v73, LIVE_EXPECT["factor_e"])[1:])
    c_peak = rec_any(v73, LIVE_EXPECT["factor_c"])[2][3]
    print(f"      ⊕ the dose ladder for mode {LIVE_MODE} at rate {BURST_RATE}: stock 0 · FactorC "
          f"alone {(LIVE_EXPECT['factor_c_y0_new'] * e_stock) >> 10} · FactorC at max alone "
          f"{(c_peak * e_stock) >> 10} · BOTH dead zones opened {doses[LIVE_MODE]}")
    print(f"      ★ WHY THE LEVER OPENS A GATE RATHER THAN RAISING A GAIN: at the stock X[0] "
          f"FactorE is EXACTLY 0 in {FACTORE_ZERO_INBURST_PCT}% of in-burst frames and "
          f"{FACTORE_BELOW_X0_HWY_PCT}% of")
    print("        engaged-highway frames sit below the breakpoint ⇒ V72's `bit4` null needs no "
          "exotic explanation.")
    print(f"      ⚠ mode 11's surface is raised at {surf[11][1]} points -- its FactorE is V72's FLAT "
          "[927]*4, so V74's edits there are value no-ops.")

    # ---- EDIT 4 -- the probe -----------------------------------------------------------------------
    print("\n  EDIT 4 -- THE PROBE (46 code bytes + 22 pad = the proven 68-byte extent):")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex()[:24]:<24s} {text}")
    # 🛑 The HOOK SITE already carries the `jarl` on every cave build -- HOOK_STOCK is the DISPLACED
    # original that the cave re-executes, NOT what sits at 0x55C0E. Both are asserted, separately.
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v73[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical to the base"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"the hook is not `jarl 0x{CAVE_BASE:05X}` -- the cave would never be entered"
    disp_off = cave_listing[13][0] - CAVE_BASE
    assert bytes(code[CAVE_BASE + disp_off:CAVE_BASE + disp_off + 4]) == HOOK_STOCK, \
        f"the displaced original is not at cave offset 0x{disp_off:02X}"
    assert bytes(code[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        f"0x{HOOK_RETURN:05X} is not `mov 0x8,r7` -- the proof that r7 is DEAD across the hook is void"
    print(f"    ★ r7 IS PROVABLY DEAD ACROSS THE HOOK: 0x{HOOK_RETURN:05X} (where the cave returns) "
          f"is `mov 0x8,r7` = {HOOK_RETURN_INSN.hex()},")
    print("      which overwrites it immediately. r6 is restored by re-executing the displaced movea.")
    cens = assert_probe_censuses(bytes(code), cave_span, expect_cave=True)
    print("\n    ✅ GATE 1 (RAM ownership), asserted as a MEASUREMENT from raw bytes:")
    for disp, (r, w) in cens.items():
        print(f"       gp-0x{disp:04x}  {r}r / {w}w -- the cave adds EXACTLY ONE load and writes it "
              "NEVER.")
    print(f"       🛑 The one-bit traps: the firmware's own `st.b r6,-0x{STATE_DISP:04x},gp` "
          f"@0x{PIN_STB_STATE[0]:05X} is {PIN_STB_STATE[1].hex()} against our "
          f"{V55.ldbu_any(-STATE_DISP, R6).hex()};")
    print(f"       `st.h r6,-0x{DAMP_DISP:04x},gp` @0x{PIN_STH_6BD0[0]:05X} is "
          f"{PIN_STH_6BD0[1].hex()} against our {V55.ldh(DAMP_DISP, R6).hex()}.")
    print(f"       The lockstep shadow gp-0x{STATE_SHADOW_DISP:04x} is untouched by the cave.")
    vals, nonlit = assert_state_value_set(bytes(code))
    print(f"\n    ★★ STRUCTURAL LIVENESS, RE-MEASURED ON THIS IMAGE: gp-0x{STATE_DISP:04x}'s 33 "
          f"writers give the value set {vals}.")
    print(f"       0 is IMPOSSIBLE and every value is < 16 ⇒ 4 bits are LOSSLESS and `bits 6:3 == 0`")
    print(f"       for a whole drive means THE CAVE DID NOT FIRE. {len(nonlit)} writers store a "
          f"register rather than an")
    print(f"       inline literal ({[hex(a) for a in nonlit]}) -- all three read in Ghidra: "
          "0x19862 -> 3, 0x19D24 -> 6,")
    print("       0x1A0BA re-stores the cell's own value during the shadow compare.")

    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v74_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 RE-DISASSEMBLE THE CAVE FROM THE BUILT BYTES, IN PYTHON -------------------------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE (raw Python decoder, NOT a Ghidra database):")
    redis = redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    ncode = len(cave_listing) - 1
    for (a, raw, m) in redis[:ncode]:
        print(f"    0x{a:05X}  {raw.hex():<12s} {m}")
    print(f"    0x{redis[ncode][0]:05X}..0x{redis[-1][0]:05X}  {len(redis) - ncode} x `nop` (0x0000) "
          "-- the zero padding, AFTER `jmp [lp]` ⇒ unreachable")
    assert [r for _a, r, _m in redis[:ncode]] == [r for _a, r, _t in cave_listing[:ncode]], \
        "the re-disassembly's bytes differ from the emitted listing"
    assert [a for a, _r, _m in redis[:ncode]] == [a for a, _r, _t in cave_listing[:ncode]], \
        "the re-disassembly does not land on the same instruction boundaries as the build listing"
    assert all(m == "nop" for _a, _r, m in redis[ncode:]), "the padding does not decode as nop"
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    assert len(stores) == 1 and stores[0][1] == f"st.b r{R6},{-PAYLOAD_BYTE4_DISP}[r{GP}]", \
        f"the re-disassembly finds stores {stores} -- expected exactly ONE st.b to the CAN payload"
    loads = [m for _a, _r, m in redis if m.startswith(("ld.bu ", "ld.h "))]
    assert loads == [f"ld.h {-DAMP_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-STATE_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-PAYLOAD_BYTE4_DISP}[r{GP}],r{R6}"], \
        f"the re-disassembled load sequence is {loads}"
    ors = [m for _a, _r, m in redis if m.startswith("or ")]
    assert ors == [f"or r{R6},r{R7}", f"or r{R7},r{R6}"], \
        f"the re-disassembled `or` sequence is {ors} -- the ACCUMULATE must be `or r6,r7` and the " \
        "MERGE `or r7,r6`"
    brs = [(a, m) for a, _r, m in redis if m.startswith(("be ", "bne ", "blt ", "bge ", "b?"))]
    assert len(brs) == 1 and brs[0][1] == f"be +{BE_SKIP}", \
        f"the re-disassembly finds branches {brs} -- expected exactly one `be +{BE_SKIP}`"
    assert brs[0][0] + BE_SKIP in [a for a, _r, _m in redis], \
        "the branch target is not an instruction boundary in the re-disassembly"
    print(f"    ✅ ONE `ld.h` (the damper, SIGNED) + TWO `ld.bu` (the state, the CAN byte), exactly "
          "ONE store, the `or`")
    print(f"       pair in the right ORDER, and the single `be +{BE_SKIP}` landing on an instruction "
          "BOUNDARY. Re-derived from the BUILT bytes.")

    # ---- the untouched sites, re-asserted on the finished image ------------------------------------
    assert_must_not_change(code, "V74", stock, v73)
    assert_v74_shape(code, "V74", v73, ENGAGED, lever_e, friction)
    print("\n  ✅ THE FULL KEEP-LIST RE-ASSERTED ON THE FINISHED IMAGE: both `sar` sites at stock,")
    print("     the gate, all three arms, V72's gain_A r26 cut EXACTLY (rec2/rec3 still stock),")
    print("     LEVER C, the carried 0x454FE, the clamp at 850, the six pointer arrays, the config")
    print("     table, V57's decoupling, V53's STOCK_CALS, and EVERY DISENGAGED-COLUMN RECORD")
    print("     byte-identical to V73 ⇒ manual and parking steering are untouched.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = [CAVE_BASE] + list(lever_e) + [y for y, _m in friction.values()]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC,
                       0xD8FFC, 0xD9FFC]
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
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
    # 🛑 [0xC5000, 0xC5FFC) is CRC-SKIPPED by the bootloader and carries the V40 ignition-brick
    # precedent. Checked over the FULL byte extent of every edit, not just its base address.
    all_edit_bytes = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)) | \
        {a + k for a in lever_e for k in (0, 1)} | \
        {y + k for y, _m in friction.values() for k in range(6)}
    assert not [a for a in all_edit_bytes if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"
    print(f"    ✅ NOTHING of the {len(all_edit_bytes)} edited bytes lands in [0xC5000,0xC5FFC) -- "
          "the CRC-skipped block, V40 ignition precedent.")

    # ---- the attributed diff -----------------------------------------------------------------------
    lever_e_c = {a + k for a, v in lever_e.items() if v[4] == "FactorC" for k in (0, 1)}
    lever_e_ex = {a + k for a, v in lever_e.items() if v[4] == "FactorE" and v[2].endswith("X[0]")
                  for k in (0, 1)}
    lever_e_ey = {a + k for a, v in lever_e.items() if v[4] == "FactorE" and v[2].endswith("Y[1]")
                  for k in (0, 1)}
    fric_bytes = {y + k for y, _m in friction.values() for k in range(6)}

    def attribute(d):
        return ("PROBE cave (6bd0!=0 / state 67fa)" if d in cave_span else
                "LEVER E' FactorC Y[0] := Y[2]" if d in lever_e_c else
                f"LEVER E' FactorE X[0] := {E_X0_NEW}" if d in lever_e_ex else
                "LEVER E' FactorE Y[1] := Y[2]" if d in lever_e_ey else
                "LEVER D' friction LERP x1.5" if d in fric_bytes else None)

    d73 = [i for i in range(START, END) if code[i] != v73[i]]
    f73 = [d for d in d73 if d not in crc_only]
    stray = [d for d in f73 if attribute(d) is None]
    assert not stray, f"UNATTRIBUTED functional bytes vs V73: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V73 (the base): {len(d73)} bytes = {len(f73)} functional + "
          f"{len(d73) - len(f73)} CRC")
    runs, prev = [], None
    for d in sorted(f73):
        if prev is not None and d == prev[1] + 1 and attribute(d) == attribute(prev[0]):
            prev = (prev[0], d)
            runs[-1] = prev
        else:
            prev = (d, d)
            runs.append(prev)
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} ({b - a + 1:2d} B)  {bytes(v73[a:b + 1]).hex():<24s} -> "
              f"{bytes(code[a:b + 1]).hex():<24s} {attribute(a)}")
    counts = {}
    for d in f73:
        counts[attribute(d)] = counts.get(attribute(d), 0) + 1
    print(f"    by lever: {counts}")

    inherited = {i for i in range(START, END) if v73[i] != stock[i]}
    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    fs = [d for d in d_stock if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None and d not in inherited]
    assert not stray_s, f"UNATTRIBUTED functional bytes vs STOCK: {[hex(x) for x in stray_s[:16]]}"
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes = {len(fs)} functional + "
          f"{len(d_stock) - len(fs)} CRC (the V38->V73 lineage is carried)")

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
    FF.assert_x31_checksum(rwd, "V74 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v73)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, not from the in-memory build.
    assert_must_not_change(dec, "V74 readback", stock, v73)
    assert_v74_shape(dec, "V74 readback", v73, ENGAGED, lever_e, friction)
    rows_rb, eng_rb, dis_rb = derive_mode_columns(bytes(dec))
    assert (eng_rb, dis_rb) == (ENGAGED, DISENGAGED), "the readback's mode columns differ"
    assert derive_lever_e(v73, ENGAGED) == lever_e, "the LEVER E' derivation is not reproducible"
    for addr, (_o, new, lbl, _m, _f) in lever_e.items():
        assert u16(dec, addr) == new, f"readback {lbl} @0x{addr:05X} is {u16(dec, addr)}"
    for fb, (yoff, mode) in friction.items():
        assert rec3_y(dec, fb) == FRICTION_Y_NEW, f"readback friction m{mode} @0x{fb:05X}"
    assert_clamp_census(bytes(dec))
    surf_rb = assert_no_clip(dec, v73, ENGAGED, grid, "V74 readback")
    doses_rb = {m: damper_authority(dec, m, 0, BURST_RATE) for m in ENGAGED}
    assert doses_rb == doses, f"the readback dose table differs: {doses_rb} vs {doses}"
    assert surf_rb == surf, "the readback surface report differs"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_censuses(bytes(dec), cave_span, expect_cave=True)
    assert assert_state_value_set(bytes(dec))[0] == vals, "the readback state value set differs"
    assert [r for _a, r, _m in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))] == \
        [r for _a, r, _m in redis], "the readback cave does not re-disassemble identically"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v73[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V73 outside the attributed set: {rb_stray[:8]}"
    print("\n  READBACK -- the payload, the config table and BOTH mode columns re-derived, all 39")
    print("     LEVER E' cells, all 13 friction records, the clamp and its reader census, the")
    print("     no-clip surface rule and the DOSE TABLE re-computed FROM THE READ-BACK BYTES, the")
    print("     whole 68-byte cave AND its re-disassembly, both probe-cell censuses, the state")
    print("     value set, the full keep-list, identity to V73 outside the attributed set, and the")
    print("     full CRC chain: ALL re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V74 BUILT. Every lever on the ENGAGED COLUMN OF EVERY ROW, for the first time.")
    print(f"  ★★ THE LIVE MODE IS {LIVE_MODE} (row {THIS_CAR_ROW} `{THIS_CAR_KEY}`, manual "
          f"{THIS_CAR_MODES[0]}) -- V73's on-car probe, not an inference.")
    print(f"  ★★ It delivers {doses[LIVE_MODE]} counts at the measured burst rate {BURST_RATE}, "
          f"against 0 on V73.")
    print("  🛑 The DISENGAGED column is byte-stock ⇒ manual and parking steering are untouched.")
    print("  🛑 Read the probe FIRST: `bits 6:3 == 0` for a whole drive means the cave never fired")
    print("     and nothing else in the log is interpretable. bit7 is the POSITIVE CONTROL.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without an image."""
    _self_check_encoders()
    assert (BIT_DAMP_NZ, STATE_FIELD, PROBE_MASK) == (0x80, 0x78, 0xF8)
    assert not (set(ENGAGED_EXPECTED) & set(DISENGAGED_EXPECTED)), "the mode columns overlap"
    assert len(ENGAGED_EXPECTED) == len(DISENGAGED_EXPECTED) == 13
    assert LIVE_MODE in ENGAGED_EXPECTED and 10 in DISENGAGED_EXPECTED
    assert FRICTION_Y_NEW == [(y * 3) // 2 for y in FRICTION_Y_STOCK]
    cave, listing = build_cave()
    assert len(cave) == 68 and len(listing) == 16, f"{len(cave)}B / {len(listing)} entries"
    assert cave.hex().startswith("003a24373094e031b205203e100084370798")


if __name__ == "__main__":
    build()
