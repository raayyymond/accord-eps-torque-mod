#!/usr/bin/env python3
r"""=================================================================================================
V100 -- THE SATURATION INSTRUMENT.  Does Path 2 have any marginal authority at all?
=================================================================================================

BASE: **V99** (`_v99_V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1_plain_image.bin`) -- the
build ON THE CAR, flown as route 0x82, fault-free, identity b5 duty 1.000000.

    TWO EDITS.  **ZERO CALIBRATION BYTES.**
    1. the CAVE payload  154 B -> **132 B**  (a SHRINK; 22 B returned to virgin 0xFF)
    2. CAN 427 source    `0x55DF2` hw2  gp-0x6b70 -> **gp-0x6b94**   (2 bytes, packer UNCHANGED)

-------------------------------------------------------------------------------------------------
WHAT THIS BUILD IS, AND WHAT IT IS NOT
-------------------------------------------------------------------------------------------------
**V100 IS AN INSTRUMENT.  IT IS NOT A FIX AND MUST NOT BE DESCRIBED AS ONE.**  It changes no
calibration cell, no gain, no pole, no clamp, no table.  Every control signal in the ECU is
bit-identical to the V99 that is on the car today.  The ONLY things that change are (a) what the
cave computes into five spare CAN bits and (b) which cell CAN 427 carries.

It answers two questions in one 60 s drive:

  Q1  **Is Path 2's marginal authority structurally ZERO?**  `FUN_0003a382` clamps the PID
      reference `gp-0x6ad6` to +-`cal(0xC6200)` = +-8192 BEFORE the error is formed, and clamps the
      error itself to +-10240.  Either saturation makes `d(gp-0x6ad4)/d(gp-0x6b70)` EXACTLY zero
      through P, I **and** D simultaneously.  Nobody has ever measured whether either fires.
  Q2  **What is `phi`, Path 2's share of the delivered command at 6-9 Hz?**  `phi` priced V97's
      cost and is quoted as `[0.085, 0.556]` -- a 6.5x range, which is not a constraint.  It needs
      exactly ONE number that has never been on the wire: the aggregator output `gp-0x6b94`.

-------------------------------------------------------------------------------------------------
THE STRUCTURE, read from the instruction stream [EVIDENCE -- `disassemble_bytes` on `code.bin`]
-------------------------------------------------------------------------------------------------
    0x3a798  ld.h  -0x6ad6,gp,r7   ; r7 = the PID REFERENCE, as written (writer-clamped +-25600)
    0x3a7a2  ld.h  0x7200,tp,r6    ; r6 = cal 0xC6200 = 8192      <- THE CLAMP CONSTANT
    0x3a7b8  mov   r11,r7          ; r7 := +8192                  <- HIGH RAIL
    0x3a7c8  subr  r0,r7           ; r7 := -8192                  <- LOW RAIL
    0x3a7ca  ld.h  -0x4f60,gp,r8   ; r8 = the MEASURED DRIVER TORQUE
    0x3a7ce  sub   r7,r8           ; r8 = torque - clamp(ref, +-8192)         <- THE PID ERROR
    0x3a7d0  addi  -0x2800,r8,r0   ; err clamped to +-10240 (an IMMEDIATE, not a cal)  <- 2nd sat
    0x3a7e8  mul   lp,r8,r0        ; -> P;  I and D derive from the SAME err

=> `|gp-0x6ad6| >= 8192`  OR  `|err| >= 10240`  =>  Path 2's marginal authority is EXACTLY ZERO.

**THE SEPARATION IDENTITY -- why RUNG D' needs no clamp arithmetic.**  Define

    C1  = ( |gp-0x6ad6| >= cal(0xC6200) )                        # the reference clamp
    C2  = ( |gp-0x4f60 - clamp(gp-0x6ad6,+-8192)| >= 10240 )      # the TRUE error-clamp predicate
    C2' = ( |gp-0x4f60 -       gp-0x6ad6       | >= 10240 )       # RUNG D' -- no clamp computed

When `C1 = 0`, `clamp(REF,+-8192) === REF`, so **`C2' === C2` identically**.  When `C1 = 1`,
authority is already zero from the reference clamp and `C2` is moot.  Hence

    zero marginal authority  <=>  C1 OR C2' ,  with NO approximation,
    and C2' === C2 on exactly the frames where the attribution matters.

Verified by exhaustion over the full reachable `(REF, T)` grid in `assert_separation_identity()`
below -- **0 mismatches** -- so this is asserted, not argued.

**THEREFORE, AND WRITE THIS INTO THE SCORER:**
    d(b5)            = the reference clamp's duty              -- EXACT, unconditional
    d(b6 | b5 = 0)   = the error clamp's TRUE duty             -- EXACT   <- THE ONE TO QUOTE
    d(b5 or b6)      = the composite "authority is zero" duty  -- EXACT
    **d(b6) UNCONDITIONED IS NOT THE ERROR CLAMP'S DUTY** -- on `b5 = 1` frames `b6` is
    uninterpreted.  **NEVER QUOTE IT.**

BOUNDARY FOOTNOTE, from the assembly not the decompile: `0x3a7d0 addi -0x2800,r8,r0` + `bgt` rails
high iff `err > 10240`; `0x3a7da addi 0x2800,r8,r0` + `cmovle` rails low iff `err <= -10240`.
RUNG D' fires on `>= 10240` both ways, so it over-counts by the **single value `err = +10240`**.
Negligible for a duty.  **Recorded here so nobody rediscovers it as a bug.**

-------------------------------------------------------------------------------------------------
THE PAYLOAD -- five bits on `0x14A` byte 4, plus the 427 magnitude channel
-------------------------------------------------------------------------------------------------
| bit | measurand                                        | form                    | bytes |
|-----|--------------------------------------------------|-------------------------|-------|
| b7  | `gp-0x6b94 < 0`  -- MANDATORY sign for 427        | single-operand, PASS 1  |  10   |
| b6  | `|gp-0x4f60 - gp-0x6ad6| >= 10240`   RUNG D'      | comparator, PASS 2 seed |  30   |
| b5  | `|gp-0x6ad6| >= cal(0xC6200)`        RUNG A      | comparator, PASS 1 seed |  24   |
| b4  | `gp-0x6ad6 < 0`  -- sign / THE POSITIVE CONTROL   | single-operand, PASS 2  |  10   |
| b3  | **IDENTITY -- unconditional constant 1**          | `add 0x8,r7`, no guard  |   2   |
| byte7[7:6] | IDENTITY = 2, carried from V98/V99         | constant block          |  18   |

    PASS1    50 B   RUNG A (24) + b7 sign (10) + shl/merge (16)     andi 0x5f -> owns {b7,b5}
    PASS2    58 B   RUNG D' (30) + b4 sign (10) + b3 id (2)
                    + shl (2) + merge (14)                          andi 0xa7 -> owns {b6,b4,b3}
    BYTE7    18 B   unchanged from V98/V99
    RET       6 B
    TOTAL   132 B   vs V99's 154 B  =  **-22 B**  =  **10.9 % of the 1212 B extent**

**THE SIGN BIT IS NOT OPTIONAL.**  `TRACE-2026-08-13-c63ae-lever` Part 2 section 3a measured the
cost of omitting it on this exact lane: the rectified reconstruction understates the 6-9 Hz RMS by
**4.86x** (112.73 vs 548.28 ct), because the sign toggles **5.06 times per second**.  A magnitude
channel without its sign is not a magnitude channel.

**CAN 427 CANNOT SATURATE, STRUCTURALLY.**  The packer is unchanged --
`clamp(abs(X) * 5 >> 6, 0, 0x3FF)` (`FUN_00049a5a` = abs, `0x55E06 mul 0x5`, `0x55E10 sar 0x6`,
`0x55E0A movea 0x3ff`).  `gp-0x6b94` is clamped to **+-10240** by its own writer at
`0x3acf6`/`0x3ad0e` (`movea +-0x2800,r0,r12`), so the maximum reachable code is
`(10240*5)>>6 = 800` of 1023.  **LSB 12.8 ct.**  GATE 3 is satisfied by the lane's OWN output
clamp, read from the decompile -- not by a downstream gate (the V96 error).

-------------------------------------------------------------------------------------------------
THE PRE-REGISTERED ENDPOINTS -- written BEFORE the cut.  The sentence a null will license.
-------------------------------------------------------------------------------------------------
**E1 -- `d(b5)`, the REFERENCE-CLAMP duty, engaged**, CI from the bit's own measured tau.

  A HIGH reading (materially > 0, say >= 0.30) LICENSES, VERBATIM:
    *"On d(b5) of engaged frames the PID's reference was pinned at +-8192 by cal 0xC6200, so on
    those frames d(gp-0x6ad4)/d(gp-0x6b70) was EXACTLY ZERO and every gain upstream of it --
    0xC40D2 (V89), 0xC63AC (V97), 0xC63AE, the six lane weights, 0xC6468 -- had no effect on the
    delivered command at all.  V89's flat dose-response and V97's felt-null are then explained by
    ONE mechanism requiring nothing unmeasured.  The next lever must move 0xC6200 or term 0
    (gp-0x6b4a), not anything inside the observer."*

  A ZERO reading (0.0000, with b4 and b7 healthy) LICENSES, VERBATIM:
    *"gp-0x6ad6 never reached the PID's +-8192 clamp in any engaged frame.  Path 2's marginal
    authority was NOT zeroed by this saturation, d(gp-0x6b94)/d(gp-0x6b70) = 0.2565 stands in the
    flown regime, and the f'-compression account in STATE.md remains the only surviving
    explanation for V89 and V97.  THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND MUST NOT BE
    RE-PROPOSED."*

**E2 -- `d(b6 | b5 = 0)`, the ERROR CLAMP's TRUE duty**, exact by the separation identity.

  **THE COMPOSITE NULL SENTENCE IS UNCONDITIONAL AND IS PRE-REGISTERED HERE:**
    *"Neither saturation was active -- Path-2's marginal authority was never zeroed by clipping."*
  That sentence is licensed iff `d(b5) = 0.0000` AND `d(b6 | b5=0) = 0.0000` with the positive
  controls healthy.  It closes the whole saturation family, not one clamp.

**E3 -- `phi` = Path 2's share of the delivered command at 6-9 Hz.**

    phi(6-9 Hz) = 0.2565 * RMS_6-9(gp-0x6b70) / RMS_6-9(gp-0x6b94)
                = 140.6 ct / R          R = engaged 6-9 Hz RMS of the SIGNED gp-0x6b94, this drive

  **THERE IS NO NULL.**  R is measured from a signed, unsaturated, known-LSB channel; the
  measurement returns a number on every drive that flies at all.  There is no gate that can fail
  to arm.  **PRE-REGISTERED DECISION BOUNDARY:**

    | R (ct RMS) | phi   | delivered ratio for 0xC63AE's lane 1.242 | verdict on 0xC63AE       |
    |------------|-------|------------------------------------------|--------------------------|
    |     141    | 1.000 | 1.241                                    | ABOVE the floor          |
    |     300    | 0.469 | 1.113                                    | ABOVE                    |
    | **387**    | 0.373 | **1.088**  = V85's not-felt figure        | **THE CROSSOVER**        |
    |     500    | 0.281 | 1.068                                    | BELOW -- NO-GO stands    |
    |    1200    | 0.117 | 1.028                                    | BELOW -- NO-GO stands    |

    **`R < 387 ct` OVERTURNS the `0xC63AE` NO-GO.  `R > 387 ct` CONFIRMS it.**

  **STATED PLAINLY: the numerator is CROSS-ROUTE.**  140.6 ct = 0.2565 x 548.28, and 548.28 is
  route 81's engaged 6-9 Hz RMS of the SIGNED gp-0x6b70 -- which V100 no longer carries, because
  427 now carries gp-0x6b94 instead.  Both drives are parking-lot creep, so they are comparable,
  but this is a two-drive ratio and must be reported as one.

**POS-1 (IDENTITY)** byte7[7:6] == 2 **AND** b3 == 1, single-frame.  See the honest-strength note.
**POS-2 (427 non-degenerate)** >= 20 distinct codes, p99 >= 8, saturation duty 0.0000 (structural).
**POS-3 (b4)** `gp-0x6ad6 < 0` duty strictly inside (0.05, 0.95), and it must TRACK openpilot's
        commanded sign -- `gp-0x6ad6` is dominated by `-gp-0x6b4a`, the LKAS demand path.
**POS-4 (b7)** `gp-0x6b94 < 0` duty strictly inside (0.05, 0.95), with of order 5 sign transitions
        per second (route 81 measured 5.06/s on the sibling lane).

**THE DEAD-INSTRUMENT TRAP, STATED EXPLICITLY:  IF b5, b4 AND b7 ALL READ 0.0000, THE INSTRUMENT
IS DEAD, NOT THE CAR.**  b4 exists precisely to catch it: if `gp-0x6ad6 === 0` then RUNG A reads
0.0000 and b4 reads 0.0000, while RUNG D' degenerates into a pure driver-torque statistic that
would still look "live".  Without b4 that failure mode is invisible.  **A composite null may only
be reported when b4 and b7 are both strictly inside (0.05, 0.95).**

**IDENTITY RULE, PRE-REGISTERED:  byte7[7:6] == 2 AND b3 == 1, on the frame.  IF IT FAILS, NOTHING
IN THE READOUT MAY BE REPORTED.**

  **AND ITS HONEST STRENGTH.**  V98 and V99 both emit byte7[7:6] == 2, so byte 7 alone does not
  discriminate.  What discriminates is b3: on V98/V99 b3 = `(gp-0x6752 >= 0)`, and `gp-0x6752` was
  measured CONSTANT AND NEGATIVE -- **duty 0.0000, 0 transitions, ~30,000 frames, two routes** --
  so neither build has ever emitted `byte7==2 AND b3==1` on a single frame.
  **That is a MEASURED duty, not a structural impossibility.**  It is the same caveat that dogged
  V96-vs-V92 and it is not hidden.  What upgrades it from V99's duty-identity is that it is a
  SINGLE-FRAME rule again, and it also flips a ~50-build parity convention: V98/V99's byte4[7:3]
  field was EVEN on 100 % of frames; **V100's is ODD on every frame.**

-------------------------------------------------------------------------------------------------
DRIVE PROTOCOL -- and it is a CHANGE from V98/V99
-------------------------------------------------------------------------------------------------
  1. **ONE CONTINUOUS ENGAGED EPISODE OF ~60 s, LKAS ENGAGED, HANDS ON, USING OVERRIDE TO PROVOKE
     THE SYMPTOM -- KEPT UNBROKEN.**  Resampling blocks come from CONTIGUOUS engaged seconds, not
     total.  Route 82's 59.8 s split 15.9 / 31.3 / 2.5 / 10.1 gave only 12-14 blocks, where route
     81's 65.9 s in three long runs gave 21.  **Three builds in a row -- V89, V97, V99 -- died to
     this.**  Do not disengage to reposition if the episode can be kept alive.
  2. **MANDATORY: a within-drive LKAS-OFF arm of the same creep at matched speed.**  Without it
     there is no control arm at all.  Route 81 proved it is obtainable back-to-back, consecutive
     frames, same lot.
  3. **STOP THE MOMENT THE SYMPTOM IS FELT.**
  Nothing in this build alters steering feel.  Zero calibration bytes; the car should feel EXACTLY
  like V99.  If it does not, that is a finding in itself and the drive should stop.

-------------------------------------------------------------------------------------------------
GATE 1 -- RAM OWNERSHIP
-------------------------------------------------------------------------------------------------
**THE STORE SET IS UNCHANGED: 3 stores across 2 cells, `{gp-0x1514, gp-0x1511}`** -- byte-identical
in structure to the set that has now flown FIVE routes (7e / 7f / 80 / 81 / 82).  Asserted three
ways from the BUILT IMAGE's own bytes, never from this source file:
  (a) the cave re-disassembles to a 49-instruction rung table, offset for offset;
  (b) the DIFFERENTIAL whole-image gp-relative store scan, V100 vs STOCK, returns exactly those
      three `st.b` and nothing else -- which also rules out an accidental write edit anywhere in
      [0x13000, 0x100000);
  (c) registers WRITTEN subset {r6, r7}; registers REFERENCED subset {r0, gp, tp, r6, r7, lp}.

**THE ONE NEW REGISTER REFERENCE IS `tp` (r5), READ-ONLY -- AND IT IS CERTIFIED, NOT ASSUMED.**
RUNG A reads the clamp constant at runtime with `ld.hu 0x7200,tp,r6` rather than hard-coding 8192,
so the rung tracks the cal it is testing.  That makes `tp`'s value load-bearing.  Two methods:
  * **Ghidra:** `search_instructions(mnemonic="mov", operand_pattern=", tp")` returns exactly ONE
    hit inside a defined function image-wide -- `0x0000008c mov r0,tp`, the reset handler's
    register clear.  `movhi ... tp` returns no hit in code.
  * **Python raw scan** (the required second method) over every form whose `reg2` field is a
    destination finds the app's own initialiser, which Ghidra had NOT analysed (it lies outside any
    defined function -- a textbook `search_instructions` undercount, adjudicated by
    `disassemble_bytes(dry_run)`):

        0x140C0  ori   0x8000, r0, r1      ; r1 = 0x00008000
        0x140C4  movhi -0x121, r0, gp      ; gp = 0xFEDF0000
        0x140C8  movea 0x0,    gp, gp
        0x140CC  add   r1, gp              ; gp = 0xFEDF8000   <- the kit's gp
        0x140CE  movhi 0xb,    r0, tp      ; tp = 0x000B0000
        0x140D2  movea 0x7000, tp, tp      ; tp = 0x000B7000
        0x140D6  add   r1, tp              ; tp = 0x000BF000   <- the kit's tp

  => **`gp` and `tp` are set by the SAME three-instruction idiom, four instructions apart, from the
  SAME `r1`.**  `tp` is therefore exactly as constant and exactly as live as `gp` -- and `gp` has
  flown five routes inside this cave.  Every remaining raw candidate was adjudicated OUT
  individually: `0x38FE0`, `0x19934`, `0x543E6`, `0x68FEE`, `0x566CE` are all the hw2 half of a
  `jarl` disp22 or an `andi` imm16 (Format-V aliasing, the kit's own recorded trap), and the rest
  lie in calibration/data pages.  **This is a VERIFIED zero, not a tool zero.**
  It is nevertheless a claim this cave has not flown before, and it is flagged as such.

**NEVER-TOUCH, honoured and asserted.**  `gp-0x6b94` is **shadow-lockstep protected at `gp-0x4ce0`**
-- NEW TO THE KIT RECORD, found this session:
    0x3acfa st.h r12,-0x6b94  / 0x3acfe st.h r12,-0x4ce0
    0x3ad12 st.h r12,-0x6b94  / 0x3ad16 st.h r12,-0x4ce0
    0x3ad20 st.h r10,-0x6b94  / 0x3ad26 st.h r12,-0x4ce0
    0x3ad1c cmp r15,r13 / bne 0x3ad2c -> 0x3ad30 jarl 0x6b9fa   (the hard-shutdown monitor)
Same class as `gp-0x6bfa`/`gp-0x4cfa` and `gp-0x6b4a`/`gp-0x4cd2`.  **V100 only READS `gp-0x6b94`,
twice -- once in the cave and once in the 427 builder.  Reading is free; WRITING either cell would
trip a hard-shutdown monitor.**  The 427 repoint changes a LOAD displacement only.

-------------------------------------------------------------------------------------------------
GATE 2 -- CLOSED-LOOP STABILITY:  **NOT APPLICABLE, BY CONSTRUCTION -- AND ASSERTED, NOT ASSUMED**
-------------------------------------------------------------------------------------------------
V100 alters **zero calibration bytes** and makes **zero code edits outside the cave** except a CAN
transmit source displacement.  No gain, pole, clamp, table, threshold or branch anywhere in the
control path moves.  This is asserted FROM THE BUILT IMAGE in [10] and [14]: every FROZEN cell is
byte-equal to V99, and the full byte diff outside the cave and 427 is EMPTY.
The honest residual: the cave runs inside an interrupts-off window that has already flown five
routes at 154 B; V100's payload is 132 B, i.e. STRICTLY SHORTER than what is on the car.

GATE 3 -- SIZING: satisfied by construction.  A comparator has no LSB and no ceiling, so there is
no field to size; and 427's +-10240 is the aggregator's OWN output clamp read at `0x3acf6`.

-------------------------------------------------------------------------------------------------
CLASS, AGAINST THE WHOLE ARC SINCE V38 -- what is genuinely new, and what is a re-run
-------------------------------------------------------------------------------------------------
V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate lane -
V74-V83a the base-assist damper - V84-V86B damper reverts + phase - V87 subtractive rebase -
V88 Lever B - V89 the plant model's K1 - V90 control - V91/V92 0xCBE74 x1.5 - V93/V94 0xCBE74 CUT
(ABORTED) - V96 instrument - V97 the first loop pole - V98 the first RELATIONAL instrument -
V99 the first build aimed by an in-frame measurement from its predecessor.

**V100 IS THE FIRST BUILD IN THE ARC THAT ASKS WHETHER THE LEVERS THEMSELVES CAN REACH.**  Every
build from V89 on has assumed Path 2 has authority and argued about the dose or the direction.
V100 measures the assumption.  It is a ZERO-CALIBRATION build -- the first since V98 -- and the
first ever to instrument a **SATURATION** rather than a signal.

**AND WHAT IS NOT NEW, SAID PLAINLY:**
  * The cave, the hook, the store set, the branch condition `bge`, the r6/r7 discipline and the
    RMW merge idiom are all V96/V98/V99's, flown five routes.  V100's branch set is `{bge}` -- a
    STRICT SUBSET of the flown `{bge, bnh}`, because deleting b3's guard removed the only `bnh`.
  * The 427 repoint is the same 2-byte edit at the same site used by V92 / V95 / V96.  Only the
    displacement is new.
  * **NOTHING HAS MOVED MICRO-RATCHETING OR RATCHETING IN SIXTY BUILDS.**  V100 makes no symptom
    claim of any kind and no symptom claim may be made from it.

CROSS-BUILD CELL MATRIX -- printed by this script FROM THE IMAGES, not from the build scripts.
=================================================================================================
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, ANALYSIS_ROOT, RWD_DIR              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V100_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000     # tp+0x7200 = 0xC6200, NOT 0xC7200.  Anchored in [2].

BASE_NAME = "_v99_V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# THE SOURCE CELLS.  Named so a swap is a one-line change.
# =================================================================================================
SRC_REF = 0x6AD6         # gp-0x6ad6  the PID REFERENCE.  b5 / b6 / b4.
SRC_TORQ = 0x4F60        # gp-0x4f60  the MEASURED DRIVER TORQUE.  b6.
SRC_AGG = 0x6B94         # gp-0x6b94  the AGGREGATOR OUTPUT.  b7, and CAN 427's new source.
DST_B4 = 0x1514          # gp-0x1514  CAN 0x14A byte 4   (~50 flown builds)
DST_B7 = 0x1511          # gp-0x1511  CAN 0x14A byte 7   (V92/V96/V97/V98/V99)

CLAMP_CELL, CLAMP_TP_OFF = 0xC6200, 0x7200   # the reference clamp, READ AT RUNTIME by RUNG A
CLAMP_EXPECT = 8192
ERR_CLAMP = 10240                            # 0x2800 -- an IMMEDIATE in the firmware, not a cal
IDENTITY_CODE = 2                            # byte7[7:6]

MASK_B4_PASS1 = 0x005F   # pass 1 writes bits 7 and 5    -> preserves 6,4,3 and Honda 2:0
MASK_B4_PASS2 = 0x00A7   # pass 2 writes bits 6,4,3      -> preserves 7,5 (pass 1) and Honda 2:0
MASK_B7 = 0x003F         # byte7 writes bits 7:6         -> preserves Honda 5:0

# =================================================================================================
# THE CAVE
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V99_CAVE_LEN = 154                            # what is on the car
CAVE_LEN = 132                                # V100 -- a SHRINK

PAYLOAD = bytes.fromhex(
    # =============================================================================================
    # PASS 1 -- RUNG A (b5, the reference clamp) + the 427 SIGN bit (b7).   andi 0x5f
    # =============================================================================================
    "24372a95"      # +0x00  ld.h  -0x6ad6[gp],r6    the PID REFERENCE  (sign-extends)
    "6032" "ae05"   # +0x04  cmp 0x0,r6 / bge +4 -> +0x0A
    "8031"          # +0x08  subr  r0,r6             r6 = |REF|         (NOT satsubr 3080)
    "0638"          # +0x0A  mov   r6,r7             r7 = |REF|  -- frees r6 for the threshold
    "e5370172"      # +0x0C  ld.hu 0x7200[tp],r6     r6 = cal 0xC6200 -- READ AT RUNTIME
    "e639"          # +0x10  cmp   r6,r7             flags = r7 - r6 = |REF| - cal
    "023a"          # +0x12  mov   0x2,r7            ASSUME SET (pre-shift bit1 -> byte4 b5)
    "ae05"          # +0x14  bge   +4 -> +0x18       taken iff |REF| >= cal  => KEEP
    "003a"          # +0x16  mov   0x0,r7            else CLEAR
    "24376c94"      # +0x18  ld.h  -0x6b94[gp],r6    the AGGREGATOR OUTPUT
    "6032" "ae05"   # +0x1C  cmp 0x0,r6 / bge +4 -> +0x22
    "483a"          # +0x20  add   0x8,r7            b7 = (gp-0x6b94 < 0)  pre-shift bit3
    "c43a"          # +0x22  shl   0x4,r7            -> byte4 bits 7 and 5
    "8437edea"      # +0x24  ld.bu -0x1514[gp],r6
    "c636" "5f00"   # +0x28  andi  0x5f,r6,r6        clear ONLY bits 7 and 5
    "0731"          # +0x2C  or    r7,r6
    "4437ecea"      # +0x2E  st.b  r6,-0x1514[gp]    CAN 0x14A byte 4, pass 1
    # =============================================================================================
    # PASS 2 -- RUNG D' (b6, the error clamp) + the REFERENCE SIGN (b4) + IDENTITY (b3). andi 0xa7
    # =============================================================================================
    "2437a0b0"      # +0x32  ld.h  -0x4f60[gp],r6    the MEASURED DRIVER TORQUE
    "243f2a95"      # +0x36  ld.h  -0x6ad6[gp],r7    the REFERENCE -- the PID's OWN 4 bytes
    "a731"          # +0x3A  sub   r7,r6             r6 = r6 - r7 = TORQUE - REF   (err_pre)
    "6032" "ae05"   # +0x3C  cmp 0x0,r6 / bge +4 -> +0x42
    "8031"          # +0x40  subr  r0,r6             r6 = |err_pre|
    "0638"          # +0x42  mov   r6,r7             r7 = |err_pre|
    "20360028"      # +0x44  movea 0x2800,r0,r6      r6 = 10240 -- the firmware's own IMMEDIATE
    "e639"          # +0x48  cmp   r6,r7             flags = |err_pre| - 10240
    "043a"          # +0x4A  mov   0x4,r7            ASSUME SET (pre-shift bit2 -> byte4 b6)
    "ae05"          # +0x4C  bge   +4 -> +0x50       taken iff |err_pre| >= 10240 => KEEP
    "003a"          # +0x4E  mov   0x0,r7            else CLEAR
    "24372a95"      # +0x50  ld.h  -0x6ad6[gp],r6    the REFERENCE, re-read (atomic: DI is on)
    "6032" "ae05"   # +0x54  cmp 0x0,r6 / bge +4 -> +0x5A
    "413a"          # +0x58  add   0x1,r7            b4 = (gp-0x6ad6 < 0)  pre-shift bit0
    "c43a"          # +0x5A  shl   0x4,r7            -> byte4 bits 6 and 4
    "483a"          # +0x5C  add   0x8,r7            b3 = IDENTITY, UNCONDITIONAL CONSTANT 1
    "8437edea"      # +0x5E  ld.bu -0x1514[gp],r6
    "c636" "a700"   # +0x62  andi  0xa7,r6,r6        clear bits 6, 4, 3; keep 7,5 and Honda 2:0
    "0731"          # +0x66  or    r7,r6
    "4437ecea"      # +0x68  st.b  r6,-0x1514[gp]    CAN 0x14A byte 4, pass 2
    # =============================================================================================
    # byte 7 -- THE BUILD IDENTITY.  Byte-identical to V98/V99.
    # =============================================================================================
    "023a"          # +0x6C  mov   0x2,r7            byte7[7:6] == 2
    "c63a"          # +0x6E  shl   0x6,r7            -> 0x80
    "a437efea"      # +0x70  ld.bu -0x1511[gp],r6
    "c636" "3f00"   # +0x74  andi  0x3f,r6,r6        keep Honda's bits 5:0
    "0731"          # +0x78  or    r7,r6
    "4437efea"      # +0x7A  st.b  r6,-0x1511[gp]    CAN 0x14A byte 7
    # =============================================================================================
    # return
    # =============================================================================================
    "2436e8ea"      # +0x7E  movea -0x1518,gp,r6     restore the hooked instruction
    "7f00")         # +0x82  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp
DI_CALL_ADDR, DI_TARGET = 0x55C0A, 0x1FA42                   # interrupts OFF
EI_CALL_ADDR, EI_TARGET = 0x55C2E, 0x1FA72                   # interrupts ON
CKSUM_CALL_ADDR = 0x55C18                                    # FUN_00057b24(gp-0x1518, 8, 0x14a)

# ---- THE 427 REPOINT -- the ONLY edit outside the cave ------------------------------------------
R427_LOAD_ADDR = 0x55DF0                     # ld.h ..[gp],r6 inside the 0x1AB/427 builder
R427_ADDR = 0x55DF2                          # its hw2 -- the displacement
R427_FROM, R427_TO = 0x6B70, SRC_AGG         # gp-0x6b70 -> gp-0x6b94
R427_SAR_ADDR, R427_SAR = 0x55E10, bytes.fromhex("a632")     # sar 0x6,r6 -- CARRIED
R427_MUL_ADDR = 0x55E06                      # mul 0x5,r6,r0
R427_CLAMP_ADDR = 0x55E0A                    # movea 0x3ff,r0,r8
R427_ABS_CALL = 0x55DF4                      # jarl FUN_00049a5a (abs)
AGG_CLAMP = 10240                            # gp-0x6b94's OWN writer clamp, 0x3acf6 / 0x3ad0e

# ---- the tp initialiser, certified in Ghidra this session ---------------------------------------
TP_INIT = ((0x140C0, "800e0080", "ori   0x8000,r0,r1"),
           (0x140C4, "4026dffe", "movhi -0x121,r0,gp"),
           (0x140C8, "24260000", "movea 0x0,gp,gp"),
           (0x140CC, "c121", "add   r1,gp        => gp = 0xFEDF8000"),
           (0x140CE, "402e0b00", "movhi 0xb,r0,tp"),
           (0x140D2, "252e0070", "movea 0x7000,tp,tp"),
           (0x140D6, "c129", "add   r1,tp        => tp = 0x000BF000"))

# ---- gp-0x6b94's shadow-lockstep twin, NEW TO THE RECORD ----------------------------------------
AGG_SHADOW = 0x4CE0
AGG_STORE_SITES = ((0x3ACFA, "64676c94", "st.h r12,-0x6b94[gp]"),
                   (0x3ACFE, "646720b3", "st.h r12,-0x4ce0[gp]  SHADOW"),
                   (0x3AD12, "64676c94", "st.h r12,-0x6b94[gp]"),
                   (0x3AD16, "646720b3", "st.h r12,-0x4ce0[gp]  SHADOW"),
                   (0x3AD20, "64576c94", "st.h r10,-0x6b94[gp]"),
                   (0x3AD26, "646720b3", "st.h r12,-0x4ce0[gp]  SHADOW"))

VARIANT_TOKEN = "V99BASE-CAVE.SAT.6AD6.C6200.4F60-SIGN.6B94-ID.B3CONST1-427.6B94"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v100_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V100-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check."""
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    """DEREFERENCE. An address is not a mode. Never hard-code a record address."""
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


# =================================================================================================
# EVERY BYTE OF THE PAYLOAD, AND THE ADDRESS IT IS COPIED FROM.  Coverage asserted 132/132.
#   `V99CAVE + k` sources are bytes PRESENT IN THE BASE IMAGE'S OWN CAVE and FLOWN on routes
#   7e / 7f / 80 / 81 / 82.  Everything else is a Honda instruction in this same image, certified
#   by Ghidra as a real instruction inside a defined function (or, for the two hw2 halves, at a
#   real operand position inside one).
#   A RAW BYTE HIT IS NOT A TWIN -- ~1 in 6 of a raw scan's candidates is not at an instruction
#   boundary at all (V98 found 0x20CB8 / 0x1E41E / 0x1B9DA that way).  Each address below was
#   checked with `disassemble_bytes(dry_run=true)` and `get_function_by_address` THIS SESSION.
# =================================================================================================
TWIN_LD_H_REF_R7 = 0x3A798    # `ld.h -0x6ad6[gp],r7`  243f2a95  FUN_0003a382 -- the PID's OWN read
TWIN_HW2_REF = 0x3A79A        # hw2 `2a95`             the displacement half of the above
TWIN_LD_HU_CLAMP = 0x382BC    # `ld.hu 0x7200[tp],r6`  e5370172  FUN_00038148
TWIN_LD_H_AGG_R6 = 0x453E0    # `ld.h -0x6b94[gp],r6`  24376c94  FUN_0004503c
TWIN_LD_H_TORQ_R6 = 0x4E452   # `ld.h -0x4f60[gp],r6`  2437a0b0  (+5 more: 2d9a2/2dae6/55624/...)
TWIN_SUB_R7_R6 = 0x4333E      # `sub r7,r6`            a731      FUN_00042af8
TWIN_HW1_MOVEA_R6 = 0x27798   # hw1 `2036` of `movea -0x6400,r0,r6`   FUN_000276xx
TWIN_HW2_2800 = 0x3A7D6       # hw2 `0028` of `movea 0x2800,r0,r14`   FUN_0003a382
TWIN_MOV_R6_R7 = 0x14EEE      # `mov r6,r7`   0638
TWIN_CMP_R6_R7 = 0x1BD96      # `cmp r6,r7`   e639   flags = r7 - r6
TWIN_MOV_4_R7 = 0x1A79C       # `mov 0x4,r7`  043a
TWIN_MOV_2_R7 = 0x1708C       # `mov 0x2,r7`  023a
TWIN_ADD_1_R7 = 0x15404       # `add 0x1,r7`  413a   SETS THE PSW -- see the PSW-window check

# (payload offset, length, source address, note).  `None` source == V99 cave offset in `src2`.
TWINS = [
    # ---- PASS 1 ---------------------------------------------------------------------------------
    (0x00, 2, None, 0x00, "ld.h hw1 `2437` (gp,r6)       V99 cave +0x00 (FLOWN 5 routes)"),
    (0x02, 2, TWIN_HW2_REF, None, "hw2 -0x6ad6 `2a95`            HONDA @0x3A79A -- hw2 of the PID's"
                                  " own `ld.h -0x6ad6[gp],r7`, bit 0 CLEAR => ld.h not ld.w"),
    (0x04, 2, None, 0x04, "cmp   0x0,r6                  V99 cave +0x04"),
    (0x06, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x08, 2, None, 0x08, "subr  r0,r6  `8031`           V99 cave +0x08   NOT satsubr 3080"),
    (0x0A, 2, TWIN_MOV_R6_R7, 0x0A, "mov   r6,r7  `0638`           V99 cave +0x0A / HONDA @0x14EEE"),
    (0x0C, 4, TWIN_LD_HU_CLAMP, None, "ld.hu 0x7200[tp],r6           HONDA @0x382BC, WHOLE 4 B --"
                                      " FUN_00038148's own read of the SAME cal"),
    (0x10, 2, TWIN_CMP_R6_R7, 0x18, "cmp   r6,r7  `e639`           V99 cave +0x18 / HONDA @0x1BD96"),
    (0x12, 2, TWIN_MOV_2_R7, 0x1A, "mov   0x2,r7 `023a`           V99 cave +0x1A / HONDA @0x1708C"),
    (0x14, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x16, 2, None, 0x4E, "mov   0x0,r7 `003a`           V99 cave +0x4E"),
    (0x18, 4, TWIN_LD_H_AGG_R6, None, "ld.h  -0x6b94[gp],r6          HONDA @0x453E0, WHOLE 4 B --"
                                      " the only ld.h of this cell into r6 in the image"),
    (0x1C, 2, None, 0x04, "cmp   0x0,r6                  V99 cave +0x04"),
    (0x1E, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x20, 2, None, 0x58, "add   0x8,r7 `483a`           V99 cave +0x58"),
    (0x22, 2, None, 0x20, "shl   0x4,r7 `c43a`           V99 cave +0x20"),
    (0x24, 4, None, 0x22, "ld.bu -0x1514[gp],r6          V99 cave +0x22, WHOLE"),
    (0x28, 2, None, 0x26, "andi hw1 `c636` (imm,r6,r6)   V99 cave +0x26"),
    # +0x2A the imm16 0x005F -- DERIVED, pure data, see DERIVED_IMM
    (0x2C, 2, None, 0x2A, "or    r7,r6  `0731`           V99 cave +0x2A"),
    (0x2E, 4, None, 0x2C, "st.b  r6,-0x1514[gp]          V99 cave +0x2C, WHOLE"),
    # ---- PASS 2 ---------------------------------------------------------------------------------
    (0x32, 4, TWIN_LD_H_TORQ_R6, None, "ld.h  -0x4f60[gp],r6          HONDA @0x4E452, WHOLE 4 B"
                                       " (6 occurrences image-wide)"),
    (0x36, 4, TWIN_LD_H_REF_R7, None, "ld.h  -0x6ad6[gp],r7          HONDA @0x3A798, WHOLE 4 B --"
                                      " byte-for-byte the PID's OWN read of the reference"),
    (0x3A, 2, TWIN_SUB_R7_R6, None, "sub   r7,r6  `a731`           HONDA @0x4333E (FUN_00042af8)"
                                    " -- reg2 = reg2 - reg1, the firmware's own orientation"),
    (0x3C, 2, None, 0x04, "cmp   0x0,r6                  V99 cave +0x04"),
    (0x3E, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x40, 2, None, 0x08, "subr  r0,r6                   V99 cave +0x08"),
    (0x42, 2, TWIN_MOV_R6_R7, 0x0A, "mov   r6,r7                   V99 cave +0x0A / HONDA"),
    (0x44, 2, TWIN_HW1_MOVEA_R6, None, "movea hw1 `2036` (imm,r0,r6)  HONDA @0x27798"),
    (0x46, 2, TWIN_HW2_2800, None, "movea hw2 `0028` = +10240     HONDA @0x3A7D6 -- the hw2 of"
                                   " `movea 0x2800,r0,r14` in the VERY clamp being measured"),
    (0x48, 2, TWIN_CMP_R6_R7, 0x18, "cmp   r6,r7                   V99 cave +0x18 / HONDA"),
    (0x4A, 2, TWIN_MOV_4_R7, 0x4A, "mov   0x4,r7 `043a`           V99 cave +0x4A / HONDA @0x1A79C"),
    (0x4C, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x4E, 2, None, 0x4E, "mov   0x0,r7                  V99 cave +0x4E"),
    (0x50, 2, None, 0x00, "ld.h hw1 `2437`               V99 cave +0x00"),
    (0x52, 2, TWIN_HW2_REF, None, "hw2 -0x6ad6 `2a95`            HONDA @0x3A79A"),
    (0x54, 2, None, 0x04, "cmp   0x0,r6                  V99 cave +0x04"),
    (0x56, 2, None, 0x06, "bge   +4                      V99 cave +0x06"),
    (0x58, 2, TWIN_ADD_1_R7, 0x64, "add   0x1,r7 `413a`           V99 cave +0x64 / HONDA @0x15404"),
    (0x5A, 2, None, 0x20, "shl   0x4,r7                  V99 cave +0x20"),
    (0x5C, 2, None, 0x58, "add   0x8,r7 `483a`           V99 cave +0x58  <== THE IDENTITY, and it"
                          " is a REMOVAL: V99's guard is deleted, the accumulate byte is unchanged"),
    (0x5E, 4, None, 0x22, "ld.bu -0x1514[gp],r6          V99 cave +0x22, WHOLE"),
    (0x62, 2, None, 0x26, "andi hw1 `c636`               V99 cave +0x26"),
    # +0x64 the imm16 0x00A7 -- DERIVED, pure data, see DERIVED_IMM
    (0x66, 2, None, 0x2A, "or    r7,r6                   V99 cave +0x2A"),
    (0x68, 4, None, 0x2C, "st.b  r6,-0x1514[gp]          V99 cave +0x2C, WHOLE"),
    # ---- byte 7 ---------------------------------------------------------------------------------
    (0x6C, 2, TWIN_MOV_2_R7, 0x82, "mov   0x2,r7                  V99 cave +0x82  THE IDENTITY"),
    (0x6E, 2, None, 0x84, "shl   0x6,r7 `c63a`           V99 cave +0x84"),
    (0x70, 4, None, 0x86, "ld.bu -0x1511[gp],r6          V99 cave +0x86, WHOLE"),
    (0x74, 4, None, 0x8A, "andi  0x3f,r6,r6              V99 cave +0x8A, WHOLE (imm too)"),
    (0x78, 2, None, 0x8E, "or    r7,r6                   V99 cave +0x8E"),
    (0x7A, 4, None, 0x90, "st.b  r6,-0x1511[gp]          V99 cave +0x90, WHOLE"),
    # ---- return ---------------------------------------------------------------------------------
    (0x7E, 6, None, 0x94, "movea -0x1518,gp,r6 / jmp[lp] V99 cave +0x94, the return"),
]

# The ONLY payload bytes with no twin: two pure-data imm16 halfwords.  No encoding ambiguity exists
# in an imm16 -- it is struct.pack and nothing else.  Each is DERIVED from the constant the rung map
# requires, asserted here AND again from the built image.
DERIVED_IMM = [
    (0x2A, lambda: struct.pack("<H", MASK_B4_PASS1),
     f"andi imm16 = 0x{MASK_B4_PASS1:04X} => pass 1 clears ONLY byte4 bits 7 and 5 and preserves "
     f"bits 6,4,3 (pass 2's) and Honda's 2:0"),
    (0x64, lambda: struct.pack("<H", MASK_B4_PASS2),
     f"andi imm16 = 0x{MASK_B4_PASS2:04X} => pass 2 clears ONLY byte4 bits 6,4,3 and preserves "
     f"bits 7 and 5 (pass 1's) and Honda's 2:0"),
]

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  V100 writes ZERO calibration bytes, so EVERY one of these is
# asserted EQUAL TO THE V99 IMAGE -- and the declared values are V99's, read from V99's own bytes.
# =================================================================================================
FROZEN = {
    0xC40BC: (2, 300, "V99's Coulomb ramp knee -- ON THE CAR. V100 does NOT move it"),
    0xC63AC: (2, 102, "the ACTUAL accumulator IIR pole -- HONDA's own value after V99's revert"),
    0xC40D2: (2, 204, "V89's K1, modelled Coulomb gain -- CARRIED"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip. V73 "
                      "raised it and V74/V75 HARD-FAULTED"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024 BIT-EXACTLY"),
    0xC40D4: (2, 573, "command-branch EMA x2 -- V86 took it to 286 and was FALSIFIED"),
    0xC40D6: (2, 246, "accel/inertia EMA x2, fc 9.86 Hz -- VIRGIN. NOT touched"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP (-0.6 deg). Kill any proposal to move it"),
    0xC4048: (4, None, "FIR tap b0 = 1.0 (the 3-tap FIR is an IDENTITY)"),
    0xC404C: (4, None, "FIR tap b1 = 0.0"),
    0xC4050: (4, None, "FIR tap b2 = 0.0"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0 -- lane measured ~0 on 87,940 frames; frozen since V83a"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN. A cliff edge, not a lever"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e -- lane PROVABLY == 0"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane"),
    0xC63AE: (2, 1024, "the Stage-2 LERP index scale -- THE CELL THIS BUILD PRICES. NOT MOVED"),
    0xC6200: (2, 8192, "THE REFERENCE CLAMP -- RUNG A reads it at runtime and does NOT move it"),
    0xC6468: (2, 2639, "shared model gain -- scales BOTH arms, cannot change their ratio"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC6446: (2, 5244, "Lever B ARM -- the ONLY measured fix on the car. Reverted 3x at rebases"),
    0x3AA96: (1, 0xFB, "Lever B GATE -- both halves or neither"),
    0xC6CD0: (2, 3564, "the 4x forward LKAS gain -- NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC640A: (2, 0xE000, "FALLBACK-2 = -8192 (STOCK) -- V94 cut it to -6144"),
    0xC640C: (2, 0xF333, "FALLBACK-1 = -3277 (STOCK) -- V94 cut it to -2458"),
    0xC63D2: (2, 6, "FUN_00036682 pole, fc 0.93 Hz"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN. Pure phase; do NOT lower"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN but INERT"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN. Blunt"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- dead because 0xC4118 is all-1. Do not arm"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried because free"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE (UNGATED; V65's subwoofer)"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xE547C: (2, None, "AUTHORITY CURVE -- virgin on all 101 images. NOT touched"),
    0xE5404: (2, None, "AUTHORITY CURVE -- virgin. NOT touched"),
    0xE52FC: (2, None, "AUTHORITY CURVE -- virgin. NOT touched"),
    0xE5284: (2, None, "AUTHORITY CURVE -- virgin. NOT touched"),
    0xC520C: (2, None, "governor rate ceiling -- V40 BRICKED on a neighbour. NOT touched"),
}

# the friction DOSE family -- V92's x1.5 on the ENGAGED columns, CARRIED unchanged.
FRICTION_PTR_ARRAY, FRICTION_N_MODES = 0xCBE74, 34
REC_X_OFF, REC_Y_OFF, REC_LEN = 0x02, 0x08, 0x10
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_X = (0, 1280, 5760)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)
DOSE_FAMILY_Y = {24: 0xD6A6C, 26: 0xD7A5C, 27: 0xD7A6C}


def assert_frozen(buf, label, ref=None):
    """`want is None` means 'must equal the reference image', for cells whose value is not declared."""
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        exp = want if want is not None else rdw(ref, a, w)
        if got != exp:
            bad.append((a, got, exp, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


# =================================================================================================
# A V850E2 decoder covering exactly the formats this cave uses.  It exists so the script
# RE-DISASSEMBLES THE PAYLOAD FROM THE BUILT IMAGE and checks it against the RUNG TABLE, rather
# than checking the bytes against the string it was handed.
# =================================================================================================
COND = {0x3: "bnh", 0xE: "bge"}
RN = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def rn(i):
    return RN.get(i, f"r{i}")


def _s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def decode(img, addr):
    """Return (text, length, kind, operand, writes, refs) for one instruction at `addr`."""
    hw1 = struct.unpack_from("<H", img, addr)[0]
    reg2, op, reg1 = (hw1 >> 11) & 0x1F, (hw1 >> 5) & 0x3F, hw1 & 0x1F
    imm5 = hw1 & 0x1F
    if op == 0x00 and reg2 != 0:
        return f"mov   {rn(reg1)},{rn(reg2)}", 2, "mov_r", None, {reg2}, {reg1, reg2}
    if op == 0x10:
        return f"mov   0x{imm5:x},{rn(reg2)}", 2, "mov", imm5, {reg2}, {reg2}
    if op == 0x12:
        return f"add   0x{imm5:x},{rn(reg2)}", 2, "add", imm5, {reg2}, {reg2}
    if op == 0x13:
        return f"cmp   0x{imm5:x},{rn(reg2)}", 2, "cmp", imm5, set(), {reg2}
    if op == 0x0F:
        return f"cmp   {rn(reg1)},{rn(reg2)}", 2, "cmp_r", None, set(), {reg1, reg2}
    if op == 0x14:
        return f"shr   0x{imm5:x},{rn(reg2)}", 2, "shr", imm5, {reg2}, {reg2}
    if op == 0x15:
        return f"sar   0x{imm5:x},{rn(reg2)}", 2, "sar", imm5, {reg2}, {reg2}
    if op == 0x16:
        return f"shl   0x{imm5:x},{rn(reg2)}", 2, "shl", imm5, {reg2}, {reg2}
    if op == 0x0C:
        return f"subr  {rn(reg1)},{rn(reg2)}", 2, "subr", None, {reg2}, {reg1, reg2}
    if op == 0x0D:                                # 🛑 sub reg1,reg2 : reg2 = reg2 - reg1
        return f"sub   {rn(reg1)},{rn(reg2)}", 2, "sub", None, {reg2}, {reg1, reg2}
    if op == 0x08:
        return f"or    {rn(reg1)},{rn(reg2)}", 2, "or", None, {reg2}, {reg1, reg2}
    if op == 0x03 and reg2 == 0:
        return f"jmp   [{rn(reg1)}]", 2, "jmp", None, set(), {reg1}
    if (hw1 >> 7) & 0xF == 0xB:                                  # Format III  bcond disp9
        disp = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 0x7) << 1)
        disp -= 0x200 if disp & 0x100 else 0
        c = hw1 & 0xF
        return f"{COND.get(c, f'b?{c:x}'):5s} +{disp}", 2, "branch", disp, set(), set()
    hw2 = struct.unpack_from("<H", img, addr + 2)[0]
    if op == 0x30:                                # addi imm16,reg1,reg2 -- reg2 == r0 = flags only
        return (f"addi  {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "addi",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x36:
        return (f"andi  0x{hw2:x},{rn(reg1)},{rn(reg2)}", 4, "andi", (reg1, hw2),
                {reg2}, {reg1, reg2})
    if op == 0x31:
        return (f"movea {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "movea",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x39:                                # ld.h (hw2 bit0 == 0) / ld.w (bit0 == 1)
        name, d = ("ld.w", hw2 & ~1) if hw2 & 1 else ("ld.h", hw2)
        return (f"{name}  {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, name,
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x38:                                # ld.b, full disp16
        return (f"ld.b  {_s16(hw2):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.b",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op in (0x3C, 0x3D):                        # ld.bu -- disp bit0 lives in the op field LSB
        d = (hw2 & ~1) | (op & 1)
        return (f"ld.bu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.bu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op in (0x3E, 0x3F):                        # ld.hu -- hw2 bit0 is a marker, disp is even
        d = hw2 & ~1
        return (f"ld.hu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.hu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x3A:                                # st.b, full disp16
        return (f"st.b  {rn(reg2)},{_s16(hw2):#x}[{rn(reg1)}]", 4, "st.b",
                (reg1, _s16(hw2)), set(), {reg1, reg2})
    if op == 0x3B:                                # st.h (bit0 == 0) / st.w (bit0 == 1)
        name, d = ("st.w", hw2 & ~1) if hw2 & 1 else ("st.h", hw2)
        return (f"{name}  {rn(reg2)},{_s16(d):#x}[{rn(reg1)}]", 4, name,
                (reg1, _s16(d)), set(), {reg1, reg2})
    return f"op{op:02x} ??", 4, f"op{op:02x}", None, {reg2}, {reg1, reg2}


PSW_SETTERS = {"cmp", "cmp_r", "add", "addi", "sar", "shl", "shr", "subr", "sub", "or", "andi"}
PSW_TRANSPARENT = {"mov", "mov_r", "movea", "ld.h", "ld.w", "ld.b", "ld.bu", "ld.hu",
                   "st.b", "st.h", "st.w", "jmp"}


def assert_psw_windows(listing):
    """For EVERY branch, walk back to the nearest flag-setter and prove the gap is transparent.

    `mov`'s flag-transparency is [BELIEF], not [EVIDENCE]: it rests on the SLEIGH model plus Honda's
    own compiled code scheduling `mov` into exactly this gap (0x1bd32, 0x1539a, 0x1a7b6), not on a
    quotation from the V850E2 manual.  It is UNCHANGED from V98/V99, which have flown it.
    """
    rows, bad, windows = list(listing), [], []
    for i, (off, _, _, text, kind, _, _, _) in enumerate(rows):
        if kind != "branch":
            continue
        j, gap = i - 1, []
        while j >= 0 and rows[j][4] not in PSW_SETTERS:
            gap.append(rows[j])
            if rows[j][4] not in PSW_TRANSPARENT:
                bad.append(f"+0x{off:02X}: unclassified `{rows[j][3].strip()}` in the window")
            j -= 1
        if j < 0:
            bad.append(f"+0x{off:02X} {text.strip()}: NO flag-setter precedes it")
            continue
        windows.append((rows[j][0], rows[j][3].strip(), off, text.strip(),
                        [g[3].strip() for g in reversed(gap)]))
    return windows, bad


def scan_gp_stores(img, lo=START, hi=END):
    """EVERY gp-relative STORE encoding image-wide, as a raw LE byte scan.

    The DIFFERENTIAL GATE-1 proof: run it on the BUILT image and on STOCK and diff.  Keyed on the
    STORE OPCODE, reporting whatever displacement it finds -- so it is NOT blind to a 32-bit access
    at a different displacement covering the same byte (the method gap V96 itself found).
    """
    out = set()
    for a in range(lo, hi - 3, 2):
        hw1 = struct.unpack_from("<H", img, a)[0]
        op, reg1 = (hw1 >> 5) & 0x3F, hw1 & 0x1F
        if op not in (0x3A, 0x3B) or reg1 != 4:
            continue
        hw2 = struct.unpack_from("<H", img, a + 2)[0]
        if op == 0x3A:
            name, d = "st.b", hw2
        else:
            name, d = ("st.w", hw2 & ~1) if hw2 & 1 else ("st.h", hw2)
        out.add((a, name, _s16(d)))
    return out


def scan_tp_accesses(img, lo=START, hi=END):
    """EVERY tp-relative 4-byte reg-disp16 access, both load and store, ALL parity traps covered."""
    forms = {0x38: "ld.b", 0x39: "ld.h/w", 0x3A: "st.b", 0x3B: "st.h/w", 0x3C: "ld.bu",
             0x3D: "ld.bu", 0x3E: "ld.hu", 0x3F: "ld.hu", 0x30: "addi", 0x31: "movea",
             0x36: "andi", 0x37: "ori"}
    out = []
    for a in range(lo, hi - 3, 2):
        hw1 = struct.unpack_from("<H", img, a)[0]
        op, reg1 = (hw1 >> 5) & 0x3F, hw1 & 0x1F
        if reg1 != 5 or op not in forms:
            continue
        hw2 = struct.unpack_from("<H", img, a + 2)[0]
        if op in (0x3C, 0x3D):
            d = (hw2 & ~1) | (op & 1)
        elif op in (0x39, 0x3B, 0x3E, 0x3F):
            d = hw2 & ~1
        else:
            d = hw2
        out.append((a, forms[op], TP + d, op in (0x3A, 0x3B)))
    return out


def scan_tp_writes(img, lo=0, hi=0x100000):
    """EVERY raw candidate that WRITES tp (reg2 == 5), over the whole image.

    The second method behind the tp-liveness claim.  It is deliberately OVER-inclusive: a 16-bit
    halfword inside a `jarl` disp22 or an `andi` imm16 aliases these encodings, which is exactly the
    Format-V trap this kit has recorded.  The adjudication is in the docstring and was done with
    Ghidra's `disassemble_bytes(dry_run)` -- NOT by this scan.
    """
    w2 = {0x00, 0x01, 0x02, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E,
          0x10, 0x11, 0x12, 0x14, 0x15, 0x16, 0x17}
    w4 = {0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3C, 0x3D, 0x3E, 0x3F}
    out = []
    for a in range(lo, hi - 3, 2):
        hw1 = struct.unpack_from("<H", img, a)[0]
        if ((hw1 >> 11) & 0x1F) != 5:
            continue
        op = (hw1 >> 5) & 0x3F
        if op in w2 or op in w4:
            out.append((a, op))
    return out


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand, writes, refs = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand,
                    writes, refs))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT.  The BUILT image is checked against THIS, not against any hex string.
EXPECTED = [
    # ---- PASS 1: b5 = RUNG A (the reference clamp)  +  b7 = sign(gp-0x6b94) --------------------
    (0x00, "ld.h  -0x6ad6[gp],r6", "the PID REFERENCE (sign-extends)"),
    (0x04, "cmp   0x0,r6", ""), (0x06, "bge   +4", "-> +0x0A"),
    (0x08, "subr  r0,r6", "r6 = |REF|"),
    (0x0A, "mov   r6,r7", "r7 = |REF| -- frees r6"),
    (0x0C, "ld.hu 0x7200[tp],r6", "r6 = cal 0xC6200 -- READ AT RUNTIME, not hard-coded"),
    (0x10, "cmp   r6,r7", "flags = |REF| - cal"),
    (0x12, "mov   0x2,r7", "ASSUME SET -> byte4 b5"),
    (0x14, "bge   +4", "-> +0x18, taken iff |REF| >= cal => KEEP"),
    (0x16, "mov   0x0,r7", "else CLEAR"),
    (0x18, "ld.h  -0x6b94[gp],r6", "the AGGREGATOR OUTPUT -- 427's new source"),
    (0x1C, "cmp   0x0,r6", ""), (0x1E, "bge   +4", "-> +0x22"),
    (0x20, "add   0x8,r7", "b7 = (gp-0x6b94 < 0) -- MANDATORY sign for 427"),
    (0x22, "shl   0x4,r7", "-> byte4 bits 7 and 5"),
    (0x24, "ld.bu -0x1514[gp],r6", ""),
    (0x28, "andi  0x5f,r6,r6", "clear ONLY bits 7 and 5"),
    (0x2C, "or    r7,r6", ""),
    (0x2E, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 1"),
    # ---- PASS 2: b6 = RUNG D' (the error clamp) + b4 = sign(REF) + b3 = IDENTITY ---------------
    (0x32, "ld.h  -0x4f60[gp],r6", "the MEASURED DRIVER TORQUE"),
    (0x36, "ld.h  -0x6ad6[gp],r7", "the REFERENCE -- the PID's OWN 4 bytes @0x3A798"),
    (0x3A, "sub   r7,r6", "r6 = TORQUE - REF   (reg2 = reg2 - reg1)"),
    (0x3C, "cmp   0x0,r6", ""), (0x3E, "bge   +4", "-> +0x42"),
    (0x40, "subr  r0,r6", "r6 = |err_pre|"),
    (0x42, "mov   r6,r7", "r7 = |err_pre|"),
    (0x44, "movea 0x2800,r0,r6", "r6 = 10240 -- the firmware's own IMMEDIATE at 0x3a7d0"),
    (0x48, "cmp   r6,r7", "flags = |err_pre| - 10240"),
    (0x4A, "mov   0x4,r7", "ASSUME SET -> byte4 b6"),
    (0x4C, "bge   +4", "-> +0x50, taken iff |err_pre| >= 10240 => KEEP"),
    (0x4E, "mov   0x0,r7", "else CLEAR"),
    (0x50, "ld.h  -0x6ad6[gp],r6", "the REFERENCE, re-read (atomic -- interrupts are off)"),
    (0x54, "cmp   0x0,r6", ""), (0x56, "bge   +4", "-> +0x5A"),
    (0x58, "add   0x1,r7", "b4 = (gp-0x6ad6 < 0) -- THE POSITIVE CONTROL"),
    (0x5A, "shl   0x4,r7", "-> byte4 bits 6 and 4"),
    (0x5C, "add   0x8,r7", "b3 = IDENTITY, UNCONDITIONAL CONSTANT 1 (V99's guard DELETED)"),
    (0x5E, "ld.bu -0x1514[gp],r6", ""),
    (0x62, "andi  0xa7,r6,r6", "clear bits 6,4,3; keep 7,5 (pass 1) and Honda's 2:0"),
    (0x66, "or    r7,r6", ""),
    (0x68, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 2"),
    # ---- byte 7: CARRIED FROM V98/V99 -----------------------------------------------------------
    (0x6C, "mov   0x2,r7", "byte7[7:6] == 2, carried. NOT discriminating on its own"),
    (0x6E, "shl   0x6,r7", "-> bits 7:6 = 0b10 = 2"),
    (0x70, "ld.bu -0x1511[gp],r6", ""),
    (0x74, "andi  0x3f,r6,r6", "keep Honda's bits 5:0"),
    (0x78, "or    r7,r6", ""),
    (0x7A, "st.b  r6,-0x1511[gp]", "CAN 0x14A byte 7"),
    # ---- return ---------------------------------------------------------------------------------
    (0x7E, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x82, "jmp   [lp]", ""),
]

M32 = 0xFFFFFFFF


def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def _abs_rung(v):
    """`cmp 0x0,rN / bge +4 / subr r0,rN` -- the cave's abs, in 32-bit register arithmetic."""
    return s32(0 - v) if not v >= 0 else v


def wire_byte4(ref, agg, torq, clamp=CLAMP_EXPECT, honda_bits=0x7):
    """Mirrors the V100 cave's integer arithmetic EXACTLY, one line per instruction offset."""
    out = honda_bits & 0x7
    # ---- PASS 1 -- RUNG A (b5) and the 427 sign (b7) --------------------------------------------
    r6 = _abs_rung(s32(ref))                         # +0x00..+0x08
    r7 = r6                                          # +0x0A
    r6 = clamp & 0xFFFF                              # +0x0C  ld.hu ZERO-extends
    r7 = 2 if r7 >= r6 else 0                        # +0x10..+0x16   b5
    if not s32(agg) >= 0:
        r7 += 8                                      # +0x18..+0x20   b7
    assert 0 <= r7 <= 0xA and (r7 & 0x5) == 0, "the pass-1 accumulator escaped bits 3,1"
    r7 = (r7 << 4) & M32                             # +0x22
    out = ((out & MASK_B4_PASS1) | (r7 & 0xFF)) & 0xFF
    # ---- PASS 2 -- RUNG D' (b6), the reference sign (b4), the identity (b3) ---------------------
    r6 = s32(s32(torq) - s32(ref))                   # +0x32..+0x3A
    r6 = _abs_rung(r6)                               # +0x3C..+0x40
    r7 = r6                                          # +0x42
    r6 = ERR_CLAMP                                   # +0x44
    r7 = 4 if r7 >= r6 else 0                        # +0x48..+0x4E   b6
    if not s32(ref) >= 0:
        r7 += 1                                      # +0x50..+0x58   b4
    assert 0 <= r7 <= 0x5 and (r7 & 0xA) == 0, "the pass-2 accumulator escaped bits 2,0"
    r7 = (r7 << 4) & M32                             # +0x5A
    r7 += 8                                          # +0x5C   b3 -- UNCONDITIONAL
    return ((out & MASK_B4_PASS2) | (r7 & 0xFF)) & 0xFF


def wire_byte7(honda_bits=0x3F):
    return ((honda_bits & MASK_B7) | ((IDENTITY_CODE << 6) & M32)) & 0xFF


def decode_wire(b4, b7):
    """The SCORER's reconstruction, written here so it is pre-registered WITH the build."""
    return dict(identity_byte7=(b7 >> 6) & 0x3, identity_b3=bool(b4 & 0x08),
                valid=(((b7 >> 6) & 0x3) == IDENTITY_CODE) and bool(b4 & 0x08),
                sign_6b94=-1 if (b4 & 0x80) else +1,      # b7 -- pair with CAN 427's magnitude
                err_clamped=bool(b4 & 0x40),              # b6 -- RUNG D'
                ref_clamped=bool(b4 & 0x20),              # b5 -- RUNG A
                sign_6ad6=-1 if (b4 & 0x10) else +1)      # b4 -- the positive control


def firmware_pid_zero_authority(ref, torq, clamp=CLAMP_EXPECT):
    """The GROUND TRUTH, mirrored from 0x3a798..0x3a7e2, for the separation-identity proof."""
    ref_c = max(-clamp, min(clamp, ref))              # 0x3a7b0..0x3a7c8
    err = torq - ref_c                                # 0x3a7ce
    c1 = abs(ref) >= clamp                            # RUNG A
    c2 = abs(err) >= ERR_CLAMP                        # the TRUE error-clamp predicate
    return c1, c2


def assert_separation_identity():
    """C2' === C2 whenever C1 == 0, BY EXHAUSTION over the full reachable (REF, TORQUE) grid."""
    refs = list(range(-25600, 25601, 61)) + [-25600, -8193, -8192, -8191, 0, 8191, 8192, 8193, 25600]
    torqs = list(range(-25600, 25601, 71)) + [-10240, -1, 0, 1, 10239, 10240, 10241, 25600]
    n, mism, both = 0, 0, 0
    for ref in refs:
        for t in torqs:
            c1, c2 = firmware_pid_zero_authority(ref, t)
            c2p = abs(t - ref) >= ERR_CLAMP
            b4 = wire_byte4(ref, 0, t)
            assert bool(b4 & 0x20) == c1, f"b5 != C1 at ({ref},{t})"
            assert bool(b4 & 0x40) == c2p, f"b6 != C2' at ({ref},{t})"
            if not c1:
                mism += (c2p != c2)
                both += 1
            n += 1
    assert mism == 0, f"{mism} mismatches -- the separation identity is FALSE"
    print(f"    [OK] SEPARATION IDENTITY proven by exhaustion: {n:,} (REF,TORQUE) pairs, "
          f"{both:,} of them with C1 == 0, and C2' == C2 on EVERY ONE. **0 mismatches.**")
    print(f"         => d(b6 | b5=0) IS the error clamp's TRUE duty, exactly. "
          f"d(b6) unconditioned is NOT -- never quote it.")
    over = [t for t in range(-30000, 30001)
            if (abs(t) >= ERR_CLAMP) != (t > ERR_CLAMP or t <= -ERR_CLAMP)]
    assert over == [ERR_CLAMP], f"the boundary over-count is {over[:4]}, expected [{ERR_CLAMP}]"
    print(f"    [OK] BOUNDARY: RUNG D' over-counts the firmware's `bgt`/`cmovle` rails by the "
          f"SINGLE value err = +{ERR_CLAMP}. Recorded, not a bug.")


def assert_rung_semantics():
    """Every rung proven by exhaustion / a corner grid, before a single byte is written."""
    assert_separation_identity()

    refs, aggs, torqs = [], [], []
    for k in (0, 1, 2, 8191, 8192, 8193, 10239, 10240, 10241, 25599, 25600, 32767):
        refs += [k, -k]
        aggs += [k, -k]
        torqs += [k, -k]
    aggs += [-10240, 10240, -32768]
    refs, aggs, torqs = sorted(set(refs)), sorted(set(aggs)), sorted(set(torqs))
    n, seen = 0, {5: set(), 6: set(), 7: set(), 4: set(), 3: set()}
    for ref in refs:
        for agg in aggs:
            for t in torqs:
                for hb in (0x7, 0x0, 0x5):
                    w4, w7 = wire_byte4(ref, agg, t, CLAMP_EXPECT, hb), wire_byte7()
                    assert bool(w4 & 0x80) == (agg < 0), "b7 is not sign(gp-0x6b94)"
                    assert bool(w4 & 0x40) == (abs(t - ref) >= ERR_CLAMP), "b6 is not RUNG D'"
                    assert bool(w4 & 0x20) == (abs(ref) >= CLAMP_EXPECT), "b5 is not RUNG A"
                    assert bool(w4 & 0x10) == (ref < 0), "b4 is not sign(gp-0x6ad6)"
                    assert (w4 & 0x08) == 0x08, "b3 IS NOT A CONSTANT 1 -- IDENTITY BROKEN"
                    assert (w4 & 0x07) == (hb & 0x07), "Honda's byte4 bits 2:0 were not preserved"
                    assert w7 & 0x3F == 0x3F, "Honda's byte7 bits 5:0 were not preserved"
                    d = decode_wire(w4, w7)
                    assert d["valid"] and d["ref_clamped"] == (abs(ref) >= CLAMP_EXPECT), \
                        "the scorer's reconstruction does not round-trip"
                    for bit, mask in ((5, 0x20), (6, 0x40), (7, 0x80), (4, 0x10), (3, 0x08)):
                        seen[bit].add(bool(w4 & mask))
                    n += 1
    print(f"    [OK] {n:,} corner cases, ZERO deviations, all five rungs + Honda's bits 2:0")
    assert seen[3] == {True}, f"b3 reachable set is {seen[3]}, must be {{True}}"
    print(f"    [OK] THE IDENTITY: b3 == 1 on EVERY input. V98/V99's b3 = (gp-0x6752 >= 0) was "
          f"measured duty 0.0000 over ~30,000 frames on two routes => a frame carrying "
          f"byte7[7:6]==2 AND b3==1 is a reading NEITHER has ever produced. "
          f"MEASURED, not structural -- said plainly.")
    for bit in (5, 6, 7, 4):
        assert seen[bit] == {True, False}, f"b{bit} is not a live measurand: {seen[bit]}"
    print(f"    [OK] b7, b6, b5 and b4 are ALL live measurands (both values reachable)")
    for v in (0, 1, 8192, 25600):
        assert wire_byte4(v, 0, 0) & 0x20 == (0x20 if v >= CLAMP_EXPECT else 0), \
            f"the |REF| == cal TIE at {v} is wrong -- the rung must be `>=`, not `>`"
    assert wire_byte4(CLAMP_EXPECT, 0, 0) & 0x20 == 0x20, "the TIE |REF| == 8192 must read 1"
    assert wire_byte4(0, 0, ERR_CLAMP) & 0x40 == 0x40, "the TIE |err| == 10240 must read 1"
    print(f"    [OK] both TIES read 1: |REF| == {CLAMP_EXPECT} and |err| == {ERR_CLAMP} "
          f"(the rungs are `>=`, not `>`)")
    assert {wire_byte7(h) >> 6 for h in range(64)} == {IDENTITY_CODE}
    print(f"    [OK] byte7[7:6] == {IDENTITY_CODE} on every Honda bit pattern -- CARRIED from V99")
    par = {wire_byte4(r, a, t) & 0x08 for r in (-1, 0, 1) for a in (-1, 0, 1) for t in (-1, 0, 1)}
    assert par == {0x08}, "b3 is not constantly 1"
    print(f"    [OK] PARITY FLIP: b3 == 1 always => byte4[7:3] is ODD on EVERY V100 frame. "
          f"V98/V99 measured byte4[7:3] EVEN on 100 % of frames (alphabet {{2,8,10,12,16,24,26,28}} "
          f"on route 81) => the single-frame discriminator is the LOW bit of that field")
    lo = wire_byte4(0, 0, 0) & 0xF8
    hi = wire_byte4(-25600, -1, 25600) & 0xF8
    print(f"    [OK] byte4[7:3] spans 0x{lo:02X}..0x{hi:02X}; the RUNTIME clamp read means RUNG A "
          f"tracks 0xC6200 automatically if a future build ever moves it")


def assert_427_sizing():
    """GATE 3, from the lane's OWN output clamp -- not a downstream gate (the V96 error)."""
    code_max = min((AGG_CLAMP * 5) >> 6, 0x3FF)
    check(code_max == 800 and code_max < 0x3FF,
          f"CAN 427 CANNOT SATURATE: gp-0x{SRC_AGG:04X}'s OWN writer clamp is +-{AGG_CLAMP} "
          f"(0x3acf6/0x3ad0e `movea +-0x2800,r0,r12`), and clamp(|x|*5>>6, 0, 0x3FF) tops out at "
          f"{code_max} of 1023 -- {0x3FF - code_max} codes of headroom, STRUCTURALLY")
    lsb = 64.0 / 5.0
    check(abs(lsb - 12.8) < 1e-9,
          f"LSB = 64/5 = {lsb} counts; quantisation noise = LSB/sqrt(12) = {lsb / 12 ** 0.5:.2f} ct "
          f"against an expected 6-9 Hz RMS in the hundreds")
    r_cross, phi_num = 387.0, 140.6
    lane = 1.242
    delivered = 1.0 + (lane - 1.0) * (phi_num / r_cross)
    check(abs(delivered - 1.088) < 0.002,
          f"THE PRE-REGISTERED CROSSOVER: R = {r_cross:.0f} ct gives phi = {phi_num / r_cross:.3f} "
          f"and a delivered ratio of {delivered:.3f} == V85's not-felt 1.088. "
          f"R < {r_cross:.0f} OVERTURNS the 0xC63AE NO-GO; R > {r_cross:.0f} CONFIRMS it")
    for r, want in ((141.0, 1.241), (300.0, 1.113), (500.0, 1.068), (1200.0, 1.028)):
        got = 1.0 + (lane - 1.0) * (phi_num / r)
        check(abs(got - want) < 0.002, f"    R = {r:6.0f} ct -> phi {phi_num / r:.3f} -> "
                                       f"delivered {got:.3f} ({'ABOVE' if r < r_cross else 'BELOW'})")


# =================================================================================================
# THE CUMULATIVE NON-STOCK LEDGER.  Every byte V100 differs from HONDA by, attributed to the build
# that introduced it.  Derived by walking the V99 image against stock, not from the lineage doc.
# (lo, hi_exclusive, build, what it is / what it does to the car)
# =================================================================================================
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number string '-' -> ',' -- the MODIFIED-FIRMWARE marker"),
    (0x14120, 0x14121, "pre-V38", "part-number string '-' -> ',' (second copy)"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader re-pointed tp+0x746C -> tp+0x7CD0, so the 4x "
                              "gain lives on a PRIVATE cell and the shared 0xC646C stays Honda"),
    (0x3AA96, 0x3AA97, "V67/V88", "LEVER B GATE: ld.bu gp-0x683c -> gp-0x6806 => the r24 gain arm "
                                  "is LKAS-GATED. Half of the kit's only measured fix"),
    (0x454FE, 0x454FF, "V42", "state-4 governor `bne` -> `br`. MEASURED INERT; carried, free"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp inside the 100 Hz 0x14A builder"),
    (0x55DF2, 0x55DF4, "V96/V100", "CAN 427 SOURCE displacement. **V100 MOVES IT**: "
                                   "gp-0x6b70 -> gp-0x6b94"),
    (0x55E10, 0x55E11, "V96", "CAN 427 scaler `sar 0x3` -> `sar 0x6` => code = |x|*5>>6"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp normaliser 600 -> 300: the friction knee moves "
                              "10.61 -> 5.31 deg/s, i.e. INTO the micro regime. ON THE CAR"),
    (0xC40D2, 0xC40D3, "V89", "K1, the modelled Coulomb gain 102 -> 204. Measured FLAT"),
    (0xC4B34, 0xC4BD0, "CAVE", "THE CODE CAVE -- V100's 132 B saturation instrument"),
    (0xC61B2, 0xC61B6, "pre-V38", "LKAS forward-path clamps 512 -> 2048, tracking the 4x gain"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce state-machine cals (the gentle-EME fix)"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0 (steer-to-zero; confirmed on-car)"),
    (0xC6446, 0xC6448, "V67/V88", "LEVER B ARM 512 -> 5244. The other half of the measured fix"),
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + the DTC-0x49 fail-counter gate -> 0xFF"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27 (lengthens re-engage; road-validated)"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor, FLOAT set 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor, FLOAT set 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor, INT set 1024 -> 5120 (the lockstep twin)"),
    (0xC6CD0, 0xC6CD2, "V57", "the PRIVATE forward-LKAS gain cell = 3564 (the 4x). NEVER lower"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 on ENGAGED mode 26. MEASURED INERT (ratio 0.99)"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 on ENGAGED mode 27. MEASURED INERT"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper (driver-pushback surface) 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "the same taper surface, second bank"),
]


def build():
    print("=" * 102)
    print("  V100 -- THE SATURATION INSTRUMENT.  ZERO calibration bytes.")
    print("  cave 154 -> 132 B (a SHRINK)  +  CAN 427 repointed gp-0x6b70 -> gp-0x6b94 (2 bytes).")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V99, the build ON THE CAR (route 0x82, fault-free)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    check(base_sha == BASE_SHA, f"base is V99, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference dump loaded, sha256 {STOCK_SHA[:24]}...")

    # ==============================================================================================
    print("\n  [2] ADDRESS ARITHMETIC -- computed, never eyeballed (off-by-0x1000 has recurred 5x)")
    check(TP + CLAMP_TP_OFF == CLAMP_CELL,
          f"tp(0x{TP:X}) + 0x{CLAMP_TP_OFF:X} == 0x{CLAMP_CELL:X}  "
          f"(NOT 0x{TP + 0x1000 + CLAMP_TP_OFF:X})")
    check(u16(base, CLAMP_CELL) == CLAMP_EXPECT and u16(stock, CLAMP_CELL) == CLAMP_EXPECT,
          f"ANCHOR: 0x{CLAMP_CELL:X} reads {CLAMP_EXPECT} on BOTH V99 and STOCK -- if the tp offset "
          f"were wrong this would not land on a known value. 0xC5200 reads "
          f"{u16(base, 0xC5200)} (the off-by-0x1000 neighbour), which is NOT {CLAMP_EXPECT}")
    check(u16(base, 0xC40BC) == 300 and u16(base, 0xC63AC) == 102 and u16(base, 0xC40D2) == 204,
          "anchors 0xC40BC = 300 (V99), 0xC63AC = 102 (Honda, V99's revert), 0xC40D2 = 204 (V89)")

    print("\n  [2b] THE tp INITIALISER -- the ONE thing this cave has never depended on before")
    for a, hx, what in TP_INIT:
        got = rd(base, a, len(hx) // 2).hex()
        check(got == hx and rd(base, a, len(hx) // 2) == rd(stock, a, len(hx) // 2),
              f"0x{a:05X} {hx:<8s} {what}   (byte-identical in STOCK and V99)")
    tp_val = ((0x000B << 16) + 0x7000 + 0x8000) & 0xFFFFFFFF
    gp_val = ((0xFEDF << 16) + 0x0000 + 0x8000) & 0xFFFFFFFF
    check(tp_val == TP and gp_val == GP,
          f"=> tp = 0x{tp_val:08X} and gp = 0x{gp_val:08X}, DERIVED from those bytes. gp and tp are "
          f"set by the SAME idiom, 4 instructions apart, from the SAME r1 = 0x8000 => tp is exactly "
          f"as constant and as live as gp, and gp has flown 5 routes inside this cave")
    tpw = scan_tp_writes(base)
    inits = [a for a, _ in tpw if a in (0x140CE, 0x140D2, 0x140D6)]
    check(sorted(inits) == [0x140CE, 0x140D2, 0x140D6],
          f"raw LE scan of EVERY reg2 == tp write form image-wide: {len(tpw)} candidates, and the "
          f"app's real initialiser is among them at {[hex(x) for x in sorted(inits)]}. Ghidra's "
          f"`search_instructions` MISSES 0x140CE entirely (it lies outside any defined function) -- "
          f"the documented undercount, caught by the second method. Every other candidate inside a "
          f"defined function was adjudicated OUT with disassemble_bytes(dry_run): 0x38FE0 / "
          f"0x19934 / 0x543E6 / 0x68FEE / 0x566CE are all the hw2 half of a `jarl` disp22 or an "
          f"`andi` imm16 (Format-V aliasing). VERIFIED zero, not a tool zero")

    # ==============================================================================================
    print("\n  [3] THE FIRMWARE THIS BUILD MEASURES -- read from the BASE IMAGE's own bytes")
    for a, hx, what in ((0x3A798, "243f2a95", "ld.h  -0x6ad6[gp],r7   the REFERENCE"),
                        (0x3A7A2, "25370072", "ld.h  0x7200[tp],r6    THE CLAMP CONSTANT"),
                        (0x3A7B2, "e55f0172", "ld.hu 0x7200[tp],r11   the HIGH rail"),
                        (0x3A7C4, "e53f0172", "ld.hu 0x7200[tp],r7    the LOW rail (then subr)"),
                        (0x3A7CA, "2447a0b0", "ld.h  -0x4f60[gp],r8   the DRIVER TORQUE"),
                        (0x3A7CE, "a741", "sub   r7,r8            err = torque - clamp(ref)"),
                        (0x3A7D0, "080600d8", "addi  -0x2800,r8,r0    the SECOND saturation")):
        got = rd(base, a, len(hx) // 2).hex()
        check(got == hx, f"0x{a:05X} = {got}  {what}")
    check(rd(base, 0x3A798, 4) == rd(stock, 0x3A798, 4)
          and rd(base, 0x3A7D0, 4) == rd(stock, 0x3A7D0, 4),
          "and FUN_0003a382's clamp structure is byte-identical to STOCK on the base -- V100 "
          "measures Honda's own arithmetic, unmodified")
    for a, hx, what in AGG_STORE_SITES:
        check(rd(base, a, 4).hex() == hx,
              f"0x{a:05X} = {hx}  {what}")
    check(True, f"=> gp-0x{SRC_AGG:04X} is SHADOW-LOCKSTEP protected at gp-0x{AGG_SHADOW:04X} "
                f"(mismatch trap `cmp r15,r13`/`bne 0x3ad2c` -> `jarl 0x6b9fa`, the hard-shutdown "
                f"monitor). NEW TO THE KIT RECORD. V100 only READS the cell -- twice. Reading is "
                f"free; writing either cell would trip the monitor")

    # ==============================================================================================
    print("\n  [4] RUNG SEMANTICS + THE SEPARATION IDENTITY -- proven BEFORE any byte is written")
    assert_rung_semantics()

    print("\n  [4b] GATE 3 -- CAN 427 sizing, from the LANE'S OWN output clamp")
    assert_427_sizing()

    # ==============================================================================================
    print("\n  [5] THE CAVE REGION AND ITS HOOK -- unchanged from the build that is flying")
    V99_CAVE = rd(base, CAVE_BASE, V99_CAVE_LEN)
    check(len(V99_CAVE) == V99_CAVE_LEN
          and all(b == 0xFF for b in base[CAVE_BASE + V99_CAVE_LEN:CAVE_FREE_END]),
          f"V99's flown cave 0x{CAVE_BASE:05X}..0x{CAVE_BASE + V99_CAVE_LEN - 1:05X} "
          f"({V99_CAVE_LEN} B) is present and the tail to 0x{CAVE_FREE_END:05X} is virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp UNCHANGED")
    hk1, hk2 = u16(base, HOOK_ADDR), u16(base, HOOK_ADDR + 2)
    check(HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2) == CAVE_BASE,
          f"the hook's disp22 DECODES to 0x{HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2):05X} == the "
          f"cave base -- derived from the bytes, not assumed")

    def jarl_target(a):
        """Format-V disp22 is SIGNED; the DI/EI calls branch BACKWARD."""
        h1, h2 = u16(base, a), u16(base, a + 2)
        d = ((h1 & 0x3F) << 16) | h2
        return a + (d - 0x400000 if d & 0x200000 else d)

    check(jarl_target(DI_CALL_ADDR) == DI_TARGET and jarl_target(EI_CALL_ADDR) == EI_TARGET
          and DI_CALL_ADDR < HOOK_ADDR < EI_CALL_ADDR,
          f"INTERRUPTS ARE OFF ACROSS THE CAVE: 0x{DI_CALL_ADDR:05X} -> 0x{DI_TARGET:05X} (DI) and "
          f"0x{EI_CALL_ADDR:05X} -> 0x{EI_TARGET:05X} (EI), hook between them => the three reads of "
          f"gp-0x6ad6 are MUTUALLY CONSISTENT and b5/b6/b4 describe ONE value")
    check(CKSUM_CALL_ADDR > HOOK_ADDR,
          f"the checksum call at 0x{CKSUM_CALL_ADDR:05X} runs AFTER the hook => both bytes the cave "
          f"writes are covered by 0x14A's own checksum")
    hw1_id, id_imm = u16(base, 0x55C14), u16(base, 0x55C16)
    check(((hw1_id >> 5) & 0x3F) == 0x31 and (hw1_id & 0x1F) == 0 and id_imm == 0x14A,
          f"THE HOOK IS THE 100 Hz CAN-TX BUILDER, NOT THE 1 kHz CONTROL TASK: 0x55C14 decodes "
          f"`movea 0x{id_imm:X},r0,r{(hw1_id >> 11) & 0x1F}`")

    # ==============================================================================================
    print("\n  [6] THE 427 BUILDER -- every instruction of the packer, from the BASE's own bytes")
    check(s16(base, R427_ADDR) == -R427_FROM,
          f"0x{R427_ADDR:05X} currently selects gp-0x{R427_FROM:04X} (V96's source) -- the "
          f"displacement we are about to move")
    hw1_427 = u16(base, R427_LOAD_ADDR)
    check(((hw1_427 >> 5) & 0x3F) == 0x39 and (hw1_427 & 0x1F) == 4
          and ((hw1_427 >> 11) & 0x1F) == 6,
          f"0x{R427_LOAD_ADDR:05X} hw1 = 0x{hw1_427:04X} decodes `ld.h <disp>[gp],r6` -- reg1 = gp, "
          f"reg2 = r6. ONLY the hw2 displacement moves; the opcode and both registers are untouched")
    check((-R427_TO & 0xFFFF) % 2 == 0,
          f"and the NEW displacement -0x{R427_TO:04X} = 0x{-R427_TO & 0xFFFF:04X} has bit 0 CLEAR "
          f"=> it stays an `ld.h` (SIGNED halfword). A set bit 0 would silently make it an `ld.w`")
    for a, hx, what in ((R427_ABS_CALL, None, "jarl FUN_00049a5a -- abs(), decompiled this session"),
                        (R427_MUL_ADDR, "e5374002", "mul   0x5,r6,r0"),
                        (R427_CLAMP_ADDR, "2046ff03", "movea 0x3ff,r0,r8   the UPPER clamp"),
                        (R427_SAR_ADDR, "a632", "sar   0x6,r6        V96's scaler, CARRIED")):
        if hx is None:
            continue
        check(rd(base, a, len(hx) // 2).hex() == hx, f"0x{a:05X} = {hx}  {what}")
    check(rd(base, R427_SAR_ADDR, 2) == R427_SAR,
          f"=> CAN 427 = clamp(abs(X) * 5 >> 6, 0, 0x3FF), packer BYTE-IDENTICAL to V96/V98/V99. "
          f"V100 changes the SOURCE ONLY")

    # ==============================================================================================
    print("\n  [7] THE PAYLOAD -- every byte, and the address it is copied from")
    check(len(PAYLOAD) == CAVE_LEN,
          f"payload is {len(PAYLOAD)} B == {CAVE_LEN} B, vs V99's {V99_CAVE_LEN} B "
          f"({CAVE_LEN - V99_CAVE_LEN:+d} B). Extent used: {CAVE_LEN} of "
          f"{CAVE_FREE_END - CAVE_BASE} B = {100.0 * CAVE_LEN / (CAVE_FREE_END - CAVE_BASE):.1f} %")
    covered, bad_twin = set(), []
    for off, n, honda, cave_off, note in TWINS:
        want = PAYLOAD[off:off + n]
        srcs = []
        if honda is not None:
            srcs.append(("HONDA 0x%05X" % honda, rd(base, honda, n), rd(stock, honda, n)))
        if cave_off is not None:
            srcs.append(("V99CAVE +0x%02X" % cave_off,
                         rd(base, CAVE_BASE + cave_off, n), None))
        ok = False
        for label, got, got_stock in srcs:
            if got == want and (got_stock is None or got_stock == want):
                ok = True
                print(f"    +0x{off:02X} {n}B {want.hex():12s} <- {label:16s} {note}")
                break
        if not ok:
            bad_twin.append(f"+0x{off:02X} {want.hex()} has NO matching source in {srcs}")
        covered |= set(range(off, off + n))
    check(not bad_twin, f"every TWIN byte group is byte-identical to its cited source "
                        f"({bad_twin[:2]})")
    for off, fn, why in DERIVED_IMM:
        want = fn()
        check(PAYLOAD[off:off + 2] == want,
              f"    +0x{off:02X} 2B {want.hex()} DERIVED   {why}")
        covered |= {off, off + 1}
    check(sorted(covered) == list(range(CAVE_LEN)),
          f"PAYLOAD COVERAGE {len(covered)}/{CAVE_LEN}: EVERY byte is either a certified twin or a "
          f"derived imm16. Zero bytes are hand-invented")
    check((MASK_B4_PASS1 & MASK_B4_PASS2) == 0x07 and (MASK_B4_PASS1 | MASK_B4_PASS2) == 0xFF
          and (~MASK_B4_PASS1 & 0xFF) == 0xA0 and (~MASK_B4_PASS2 & 0xFF) == 0x58,
          f"the RMW masks PARTITION byte 4: pass 1 owns exactly {{b7,b5}} = 0xA0, pass 2 exactly "
          f"{{b6,b4,b3}} = 0x58, disjoint, and Honda's 2:0 survive both")

    # ==============================================================================================
    code = bytearray(base)
    attributed, by_addr = set(), {}

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
            by_addr[addr + k] = label
        print(f"    0x{addr:05X}  {len(post):4d} B   {label}")

    print("\n  [8] THE EDIT -- TWO, AND EVERY BYTE IS NAMED")
    apply(CAVE_BASE, V99_CAVE, PAYLOAD + b"\xff" * (V99_CAVE_LEN - CAVE_LEN),
          f"EDIT 1  THE INSTRUMENT  cave 0x{CAVE_BASE:05X} {V99_CAVE_LEN} -> {CAVE_LEN} B "
          f"(+{V99_CAVE_LEN - CAVE_LEN} B returned to virgin 0xFF)")
    apply(R427_ADDR, struct.pack("<h", -R427_FROM), struct.pack("<h", -R427_TO),
          f"EDIT 2  THE CHANNEL     0x{R427_ADDR:05X} hw2  gp-0x{R427_FROM:04X} -> "
          f"gp-0x{R427_TO:04X}  (CAN 427 source; packer UNCHANGED)")
    check(len(attributed) == V99_CAVE_LEN + 2,
          f"TOTAL ATTRIBUTED = {len(attributed)} bytes = {V99_CAVE_LEN} (the whole cave region) "
          f"+ 2 (the 427 displacement) and NOTHING ELSE")
    check(rd(code, CAVE_BASE, CAVE_LEN) == PAYLOAD,
          "the cave in the built image is byte-identical to the payload built above")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"cave tail 0x{CAVE_BASE + CAVE_LEN:05X}-0x{CAVE_FREE_END:05X} is virgin 0xFF -- "
          f"{CAVE_FREE_END - CAVE_BASE - CAVE_LEN} B free, "
          f"{100.0 * CAVE_LEN / (CAVE_FREE_END - CAVE_BASE):.1f} % of the extent used")
    check(s16(code, R427_ADDR) == -R427_TO and rd(code, R427_SAR_ADDR, 2) == R427_SAR
          and rd(code, R427_LOAD_ADDR, 2) == rd(base, R427_LOAD_ADDR, 2),
          f"built 427: source gp-0x{R427_TO:04X}, `sar 0x6,r6` carried, hw1 (opcode + both "
          f"registers) byte-identical to V99")

    # ==============================================================================================
    print("\n  [9] EVERY CALIBRATION CELL IS BYTE-EQUAL TO V99 -- V100 MOVES NONE")
    assert_frozen(code, "built image", ref=base)
    assert_frozen(base, "V99 base", ref=base)
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, rec_addr(code, m), REC_LEN) != rd(base, rec_addr(base, m), REC_LEN)]
    check(not moved, f"all {FRICTION_N_MODES} friction records BYTE-IDENTICAL to V99 -- zero moved")
    for m, want_addr in sorted(DOSE_FAMILY_Y.items()):
        got = rec_addr(code, m) + REC_Y_OFF
        check(got == want_addr and rd(code, got, 6) == rd(base, got, 6),
              f"the DOSE FAMILY: mode {m}'s Y array DEREFERENCES to 0x{got:05X} == the named "
              f"0x{want_addr:05X} and its 6 bytes are byte-equal to V99")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == FRICTION_Y_STOCK, f"mode {m} (MANUAL)  Y = STOCK, unchanged")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == FRICTION_Y_V92, f"mode {m} (ENGAGED) Y = V92's x1.5, CARRIED")
    cal_lo, cal_hi = 0xC0000, 0xD0000
    cal_diff = [a for a in range(cal_lo, cal_hi) if code[a] != base[a] and a != 0xC6FFC]
    cal_diff = [a for a in cal_diff if not (CAVE_BASE <= a < CAVE_FREE_END)]
    check(not cal_diff,
          f"GATE 2, ASSERTED FROM THE IMAGE: ZERO differing bytes in the whole calibration span "
          f"[0x{cal_lo:05X},0x{cal_hi:05X}) outside the cave. **V100 IS A ZERO-CALIBRATION BUILD** "
          f"=> no gain, pole, clamp, table or threshold moves, so there is no closed-loop change "
          f"to argue about ({[hex(x) for x in cal_diff[:6]]})")

    # ==============================================================================================
    print("\n  [10] RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, CAVE_LEN)
    check(len(listing) == len(EXPECTED) == 49,
          f"{len(listing)} instructions decoded, rung table has {len(EXPECTED)}, expected 49 "
          f"(V98/V99 were 59)")
    boundaries = {off for off, *_ in listing}
    writes, refs, conds = set(), set(), set()
    bad_text, bad_tgt, nbranch = [], [], 0
    for (off, addr, hx, text, kind, operand, w, r), (eoff, etext, note) in zip(listing, EXPECTED):
        if off != eoff or text.split() != etext.split():
            bad_text.append(f"+0x{off:02X} got `{text}` want `{etext}` @+0x{eoff:02X}")
        if kind == "branch":
            nbranch += 1
            conds.add(text.split()[0])
            if off + operand not in boundaries:
                bad_tgt.append(f"+0x{off:02X} -> +0x{off + operand:02X}")
        writes |= w
        refs |= r
        print(f"    +0x{off:02X}  0x{addr:05X}  {hx:12s}  {text:22s}  {note}")
    check(not bad_text,
          f"all {len(listing)} instructions match the RUNG TABLE offset-for-offset ({bad_text[:3]})")
    check(nbranch == 6 and not bad_tgt,
          f"{nbranch} branches, EVERY target lands on an instruction BOUNDARY ({bad_tgt[:3]})")
    check(conds == {"bge"},
          f"BRANCH SET = {sorted(conds)} -- a STRICT SUBSET of V98/V99's flown {{bge, bnh}}. "
          f"Deleting the b3 guard removed the only `bnh` in the cave")
    bad_mn = [t.split()[0] for _, _, _, t, _, _, _, _ in listing
              if t.split()[0].startswith("op") or "?" in t
              or t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare", "dispose")]
    check(not bad_mn,
          f"the cave is a STRAIGHT-LINE LEAF: no call, no loop, no divide, no float, no unknown "
          f"opcode ({bad_mn[:4]})")
    check(writes <= {6, 7},
          f"registers WRITTEN = {sorted(writes)} subset of {{r6, r7}} -- TIGHTER than V96/V98/V99, "
          f"which also wrote r0. NO NEW LIVENESS CLAIM ON A SCRATCH REGISTER")
    check(refs <= {0, 4, 5, 6, 7, 31} and 5 in refs,
          f"registers REFERENCED = {sorted(refs)} subset of {{r0, gp, tp, r6, r7, lp}}. "
          f"tp (r5) is the ONE addition vs the flown set, READ-ONLY, and it is certified in [2b]. "
          f"r8 and r10 stay LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and are never touched")
    stores = [(off, operand) for off, _, _, _, k, operand, _, _ in listing if k.startswith("st.")]
    check([(o, d) for o, (rb, d) in stores] == [(0x2E, -DST_B4), (0x68, -DST_B4), (0x7A, -DST_B7)]
          and all(rb == 4 for _, (rb, _) in stores),
          f"GATE 1: the STORE SET is exactly {{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} -- three "
          f"store instructions, TWO cells, THE SET THAT HAS FLOWN FIVE ROUTES")
    loads = sorted({row[5][1] & 0xFFFF for row in listing if row[4].startswith("ld.")})
    want_loads = sorted({(-x) & 0xFFFF for x in (SRC_REF, SRC_TORQ, SRC_AGG, DST_B4, DST_B7)}
                        | {CLAMP_TP_OFF})
    check(loads == want_loads,
          f"and it LOADS exactly five gp cells + one tp cal: gp-0x{SRC_REF:04X}, gp-0x{SRC_TORQ:04X}"
          f", gp-0x{SRC_AGG:04X}, gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}, tp+0x{CLAMP_TP_OFF:04X}. "
          f"ALL PURE LOADS, no side effects. gp-0x6bfa / gp-0x374c / gp-0x6752 / gp-0x6b70 are no "
          f"longer read at all")
    windows, psw_bad = assert_psw_windows(listing)
    for foff, ftext, boff, btext, gap in windows:
        print(f"      +0x{foff:02X} {ftext:<20s} -> +0x{boff:02X} {btext:<10s} gap: "
              f"{gap if gap else '(adjacent)'}")
    check(not psw_bad,
          f"PSW WINDOW: all {len(windows)} cmp -> branch windows contain ONLY PSW-TRANSPARENT "
          f"instructions ({psw_bad[:3]})")
    gapped = [w for w in windows if w[4]]
    check(all(all(g.split()[0] == "mov" for g in w[4]) for w in gapped) and len(gapped) == 2,
          f"exactly {len(gapped)} windows are non-adjacent and BOTH contain only a `mov imm5` -- "
          f"the SAME exposure V98/V99 have flown. `mov`'s flag transparency remains BELIEF "
          f"(SLEIGH + Honda's own scheduling at 0x1bd32/0x1539a/0x1a7b6)")
    kinds = {row[4] for row in listing if row[4].startswith("ld.")}
    check(kinds == {"ld.h", "ld.hu", "ld.bu"},
          f"load CLASSES = {sorted(kinds)} -- `ld.h` SIGN-extends the three measurands and `ld.hu` "
          f"ZERO-extends the unsigned cal. The decode of the BUILT image separates them")

    # ==============================================================================================
    print("\n  [11] VALUE-ANCHORED READBACK (a span diff is NOT a value check)")
    for off, want, why in ((0x0E, CLAMP_TP_OFF | 1, "RUNG A's cal displacement (ld.hu marker bit)"),
                           (0x1A, (-SRC_AGG) & 0xFFFF, "b7's source = gp-0x6b94"),
                           (0x34, (-SRC_TORQ) & 0xFFFF, "RUNG D's torque source = gp-0x4f60"),
                           (0x38, (-SRC_REF) & 0xFFFF, "RUNG D's reference source = gp-0x6ad6"),
                           (0x46, ERR_CLAMP, "RUNG D's threshold = 10240"),
                           (0x2A, MASK_B4_PASS1, "pass-1 andi mask"),
                           (0x64, MASK_B4_PASS2, "pass-2 andi mask")):
        got = u16(code, CAVE_BASE + off)
        check(got == want, f"cave +0x{off:02X} = 0x{got:04X} == 0x{want:04X}   {why}")
    check(code[CAVE_BASE + 0x5C] == 0x48 and code[CAVE_BASE + 0x5D] == 0x3A,
          "cave +0x5C = `add 0x8,r7` UNGUARDED => b3 == 1 STRUCTURALLY, on every frame")
    check(code[CAVE_BASE + 0x6C] == IDENTITY_CODE and code[CAVE_BASE + 0x6D] == 0x3A,
          f"cave +0x6C = `mov 0x{IDENTITY_CODE:x},r7` => byte7[7:6] == {IDENTITY_CODE}, CARRIED")
    check(code[CAVE_BASE + 0x12] == 0x02 and code[CAVE_BASE + 0x4A] == 0x04,
          "cave +0x12 = `mov 0x2,r7` (b5 SET) and +0x4A = `mov 0x4,r7` (b6 SET) -- the two "
          "comparator seeds, at their pre-shift bit weights")

    print("\n  [11b] THE DIFFERENTIAL STORE-SET SCAN: every gp-relative WRITE, V100 vs STOCK")
    v100_st, stock_st = scan_gp_stores(code), scan_gp_stores(stock)
    added, removed = sorted(v100_st - stock_st), sorted(stock_st - v100_st)
    for a, nm, d in added:
        print(f"       + 0x{a:05X}  {nm}  gp{d:+#07x}   {rd(code, a, 4).hex()}")
    for a, nm, d in removed:
        print(f"       - 0x{a:05X}  {nm}  gp{d:+#07x}")
    check(not removed, f"no gp-relative store present in STOCK was removed or moved ({removed[:3]})")
    check([(a, nm, d) for a, nm, d in added]
          == [(CAVE_BASE + 0x2E, "st.b", -DST_B4), (CAVE_BASE + 0x68, "st.b", -DST_B4),
              (CAVE_BASE + 0x7A, "st.b", -DST_B7)],
          f"GATE 1, DIFFERENTIALLY: diffing ALL gp-relative writes image-wide, V100 vs STOCK, "
          f"returns EXACTLY {len(added)} -- three `st.b` across TWO cells, and NOTHING was added or "
          f"removed anywhere else in [0x{START:X},0x{END:X}). Read from the BUILT IMAGE's bytes")
    check({(nm, d) for _, nm, d in v100_st} == {(nm, d) for _, nm, d in scan_gp_stores(base)},
          "=> the SET OF CELLS WRITTEN is identical to V99's -- V100 adds no RAM ownership claim. "
          "(The two store ADDRESSES moved inside the cave because the payload shrank.)")
    shadow_writes = [(a, nm, d) for a, nm, d in v100_st
                     if d in (-SRC_AGG, -AGG_SHADOW, -0x6BFA, -0x4CFA, -0x6B4A, -0x4CD2)]
    check(sorted(shadow_writes) == sorted((a, nm, d) for a, nm, d in stock_st
                                          if d in (-SRC_AGG, -AGG_SHADOW, -0x6BFA, -0x4CFA,
                                                   -0x6B4A, -0x4CD2)),
          f"NEVER-TOUCH: every writer of the three SHADOW-LOCKSTEP pairs (gp-0x{SRC_AGG:04X}/"
          f"gp-0x{AGG_SHADOW:04X}, gp-0x6bfa/gp-0x4cfa, gp-0x6b4a/gp-0x4cd2) is byte-for-byte "
          f"Honda's. V100 adds none and removes none -- it only READS gp-0x{SRC_AGG:04X}")

    # ==============================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [12] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
          f"self-describing 50-block map")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len([a for a in touched if blk[0] <= a < blk[1]])} of "
              f"{len(touched)} touched byte(s)")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xC4FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc4ffc}} -- BOTH edits lie "
          f"in the MAIN block [0x013000,0x0C4FFC), so exactly ONE trailer moves. Because V100 "
          f"writes no calibration byte, 0xC6FFC does NOT move (V99 moved two)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(0x055FFC not in crc_only,
          "0x055FFC is LIVE CODE (`6477b8f0`), NOT a CRC trailer -- writing there would silently "
          "overwrite 4 bytes of executable code and the recompute would HIDE it")
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [13])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC])
          and not [a for a in attributed if 0xC5000 <= a < 0xC5FFC],
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")

    # ==============================================================================================
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1

    def attribute(d):
        return by_addr.get(d, "CRC trailer" if d in crc_only else None)

    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  [13] FULL BYTE DIFF: BUILT V100 vs the FLOWN V99 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V99 (stray = {[hex(x) for x in stray[:16]]})")
    non_crc = sorted(d for a, b in runs for d in range(a, b + 1) if d not in crc_only)
    in_cave = [d for d in non_crc if CAVE_BASE <= d < CAVE_BASE + V99_CAVE_LEN]
    in_427 = [d for d in non_crc if d in (R427_ADDR, R427_ADDR + 1)]
    check(sorted(in_cave + in_427) == non_crc and in_427 == [R427_ADDR],
          f"AND OUTSIDE THE CRC TRAILER, EVERY DIFFERING BYTE IS EITHER IN THE CAVE "
          f"({len(in_cave)} of {V99_CAVE_LEN}) OR THE 427 DISPLACEMENT ({len(in_427)}). "
          f"{total} differing bytes in total including the 4-byte CRC trailer")
    check(len(in_427) == 1 and code[R427_ADDR + 1] == base[R427_ADDR + 1] == 0x94,
          f"THE 427 REPOINT IS A **ONE-BYTE** EDIT: -0x{R427_FROM:04X} = 0x{-R427_FROM & 0xFFFF:04X}"
          f" and -0x{R427_TO:04X} = 0x{-R427_TO & 0xFFFF:04X} share the HIGH byte 0x94, so only "
          f"0x{R427_ADDR:05X} moves (0x{base[R427_ADDR]:02X} -> 0x{code[R427_ADDR]:02X}). Two bytes "
          f"are WRITTEN, one DIFFERS -- the same shape as V97's and V99's one-byte cal edits")
    check(len(non_crc) == len(in_cave) + 1,
          f"RECONCILED TWO WAYS: {len(non_crc)} non-CRC differing bytes = {len(in_cave)} cave + 1 "
          f"(427); and the WRITTEN set is {len(attributed)} = {V99_CAVE_LEN} + 2, of which "
          f"{V99_CAVE_LEN + 2 - len(non_crc)} were written back to their existing value "
          f"({V99_CAVE_LEN - len(in_cave)} inside the cave, 1 in the 427 displacement)")
    for lo, hi, why in ((0xC0000, CAVE_BASE, "the WHOLE calibration span below the cave"),
                        (CAVE_FREE_END, 0xD0000, "the calibration span above the cave"),
                        (0xE5000, 0xE6000, "THE AUTHORITY CURVE -- virgin, and it stays virgin"),
                        (0xCB000, 0xE0000, "every friction/gain record page (the dose family)"),
                        (0xD6000, 0xD8000, "the mode records"),
                        (0x3A000, 0x3B000, "FUN_0003a382 -- the PID this build MEASURES"),
                        (0x38000, 0x39000, "FUN_00038148 -- Path 2's Stage-1/Stage-2"),
                        (0x3B000, 0x3C000, "FUN_0003b8f6 -- the plant model"),
                        (0x55A00, R427_ADDR, "the 0x14A builder and the hook -- unchanged"),
                        (R427_ADDR + 2, 0x56000, "the rest of the 427 builder incl. `sar 0x6`")):
        check(not [d for a, b in runs for d in range(a, b + 1)
                   if lo <= d < hi and d not in crc_only],
              f"ZERO differing bytes in [0x{lo:05X},0x{hi:05X}) -- {why}. Proven by DIFF, not a list")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V99 BIT-FOR-BIT")

    # ==============================================================================================
    print("\n  [13b] FULL BYTE DIFF vs HONDA STOCK -- the CUMULATIVE non-stock delta")
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + k for b in (0xC4FFC, 0xC5FFC, 0xC6FFC, 0xCCFFC) for k in range(4)}
    scrc |= {b + 0xFFC + k for b in range(0xCD000, 0x100000, 0x1000) for k in range(4)}
    sattr, srows = set(), []
    for lo, hi, bld, what in VS_STOCK:
        hits = [i for i in sruns if lo <= i < hi]
        sattr |= set(hits)
        if hits:
            srows.append((lo, hi, bld, what, len(hits)))
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"       {'address':>18}  {'build':<10} {'n':>4}  what it is / what it does to the car")
    print("       " + "-" * 95)
    for lo, hi, bld, what, n in sorted(srows):
        span = f"0x{lo:05X}" if hi - lo <= 2 else f"0x{lo:05X}-0x{hi - 1:05X}"
        print(f"       {span:>18}  {bld:<10} {n:>4}  {what}")
    ncrc = len(set(sruns) & scrc)
    print(f"       {'CRC trailers':>18}  {'--':<10} {ncrc:>4}  recomputed block checksums")
    check(not sun, f"ZERO UNATTRIBUTED bytes vs STOCK ({[hex(x) for x in sun[:16]]})")
    print(f"       TOTAL vs Honda: {len(sruns)} bytes = {len(sattr)} functional + {ncrc} CRC")

    # ==============================================================================================
    print("\n  [14] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V100 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V100_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            print("\n  [15] FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V100 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk", ref=base)
            check(rd(sd, CAVE_BASE, CAVE_LEN) == PAYLOAD
                  and all(b == 0xFF for b in sd[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
                  f"shipped .rwd: the {CAVE_LEN}-byte payload is byte-identical and the tail is "
                  f"virgin 0xFF")
            check(s16(sd, R427_ADDR) == -R427_TO and rd(sd, R427_SAR_ADDR, 2) == R427_SAR,
                  f"shipped .rwd: CAN 427 selects gp-0x{R427_TO:04X} and the packer is unchanged -- "
                  f"the CHANNEL is live in the artefact that will actually be flashed")
            check(sd[CAVE_BASE + 0x5C] == 0x48 and sd[CAVE_BASE + 0x6C] == IDENTITY_CODE,
                  "shipped .rwd: the IDENTITY (b3 == 1 unguarded, byte7[7:6] == 2) is present")
            check(u16(sd, CLAMP_CELL) == CLAMP_EXPECT and u16(sd, 0xC63AE) == 1024
                  and u16(sd, 0xC40BC) == 300 and u16(sd, 0xC63AC) == 102
                  and u16(sd, 0xC40D2) == 204 and u16(sd, 0xC4080) == 0
                  and u16(sd, 0xC407E) == 511,
                  "shipped .rwd: 0xC6200 = 8192, 0xC63AE = 1024, 0xC40BC = 300 (V99), "
                  "0xC63AC = 102, K1 = 204 (V89), K0 = 0, interlock = 511 -- ALL UNMOVED")
            check(u16(sd, 0xC6446) == 5244 and sd[0x3AA96] == 0xFB and sd[0x454FE] == 0xB5
                  and u16(sd, 0xC6CD0) == 3564,
                  "shipped .rwd: Lever B BOTH halves, 0x454FE = 0xB5, and the 4x gain = 3564")
            sd_listing = disassemble_cave(sd, CAVE_BASE, CAVE_LEN)
            check([(row[0], row[3].split()) for row in sd_listing]
                  == [(e[0], e[1].split()) for e in EXPECTED],
                  f"shipped .rwd: the cave RE-DISASSEMBLES to the same {len(EXPECTED)}-instruction "
                  f"rung table, offset for offset")
            sd_stores = [op for _, _, _, _, k, op, _, _ in sd_listing if k.startswith("st.")]
            check(sorted({d for _, d in sd_stores}) == sorted([-DST_B4, -DST_B7]),
                  f"shipped .rwd: the STORE SET re-disassembles to "
                  f"{{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} -- GATE 1 verified from the ARTEFACT")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

            print("\n  [16] ARTEFACT UNIQUENESS -- every V100-matching file in both directories")
            stray_rwd = sorted(p for p in Path(RWD_DIR).iterdir()
                               if p.is_file() and "v100" in p.name.lower())
            stray_img = sorted(p for p in Path(ANALYSIS_ROOT).iterdir()
                               if p.is_file() and "v100" in p.name.lower())
            for p in stray_rwd + stray_img:
                mark = "  <-- THIS BUILD" if str(p) in (OUT, BIN_OUT) else "  STRAY"
                print(f"       {p.name}{mark}")
            check([str(p) for p in stray_rwd] == [OUT],
                  f"exactly ONE V100 .rwd in {RWD_DIR} (found {len(stray_rwd)})")
            check([str(p) for p in stray_img] == [BIN_OUT],
                  f"exactly ONE V100 image in {ANALYSIS_ROOT} (found {len(stray_img)})")
            check(hashlib.sha256(plain_image_path(BASE_NAME).read_bytes()).hexdigest() == BASE_SHA,
                  "the V99 base image is STILL byte-identical after the V100 cut -- untouched")

    print("\n" + "=" * 102)
    print(f"  V100 [{VARIANT_TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  TWO EDITS, **ZERO CALIBRATION BYTES**: the cave 154 -> {CAVE_LEN} B (a SHRINK) and "
          f"2 bytes at 0x{R427_ADDR:05X}\n     repointing CAN 427 from gp-0x{R427_FROM:04X} to "
          f"gp-0x{R427_TO:04X}. GATE 2 is N/A BY CONSTRUCTION and is asserted from the image.")
    print(f"  CAVE: {CAVE_LEN} B / 49 instructions, "
          f"{100.0 * CAVE_LEN / (CAVE_FREE_END - CAVE_BASE):.1f} % of the extent. Store set "
          f"UNCHANGED (3 stores, 2 cells).\n     Branch set {{bge}} -- a STRICT SUBSET of the flown "
          f"{{bge, bnh}}. Registers written {{r6, r7}}.")
    print(f"  THE ONE NEW CLAIM: the cave now READS tp (r5). Certified in [2b] -- gp and tp are set "
          f"by the\n     SAME idiom at 0x140C4/0x140CE, 4 instructions apart, from the same r1.")
    print(f"  IDENTITY RULE: byte7[7:6] == 2 AND b3 == 1, SINGLE-FRAME. byte4[7:3] is ODD on every "
          f"V100 frame\n     and was EVEN on 100 % of V98/V99 frames. IF IT FAILS, NOTHING MAY BE "
          f"REPORTED.")
    print(f"  READ-OUT: d(b5) = reference clamp - d(b6 | b5=0) = error clamp (EXACT) - "
          f"NEVER quote d(b6) alone.\n     phi = 140.6 / R;  R < 387 ct overturns the 0xC63AE "
          f"NO-GO, R > 387 ct confirms it.")
    print(f"  THIS IS AN INSTRUMENT, NOT A FIX. No symptom claim may be made from it.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
