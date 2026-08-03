#!/usr/bin/env python3
"""build_v68_tva.py -- V68 = V67's CONTROL PATH, BYTE-IDENTICAL, with a re-aimed probe.

WHAT V68 IS, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------
V68 is a **MEASUREMENT BUILD**. It changes NOTHING that touches torque. V67's two control-path
edits -- the one-byte repoint at `0x3AA96` and the arm `0xC6446 = 5244` -- are carried forward
byte-for-byte, and the build asserts that the ONLY differences from V67 anywhere in
`[0x13000,0x100000)` are the cave span and the two CRC trailers.

🛑 **NO CONTROL-PATH CHANGE IS JUSTIFIED BY THE CURRENT EVIDENCE.** V67 is the best build this kit
has measured: grind #1 fixed (18-22 Hz 0.55 [0.34, 0.65] vs the Kd=1 pool against a split-half null
of [0.88, 1.13]), creep grind #2 eliminated (0 burst blocks in 113 s vs 24 at Kd=2x), flight-clean,
and byte-stock on the rate lane whenever LKAS is off. The operator reports a highway resonance, but
a three-dose highway comparison shows NO rate-lane dose response at 40-49 Hz (0.98 [0.71, 1.63] and
0.77 [0.56, 1.44] against a null of [0.53, 1.86], zero burst windows at any dose over ~1400 s). A
lever aimed at that would be aimed at nothing.

THE ONE CHANGE: bit4 is repointed from a DEAD rung to the LERP's inner breakpoint
----------------------------------------------------------------------------------
On route `47` (V67, 150,327 frames, 26 segments) bit4 (`gp-0x671a >= 5`) read **0.000%** and bit5
read **0.000%**. bit5 is a real risk that must stay on the car -- if it ever fires, r24's gain is
pinned to `0xC6442 = 1024`, BELOW stock, and V67 becomes worse than V66. bit4 is a **wasted rung**:
V64 already closed the whole oscillation-detector approach, and its own route read the same 0.

V68 spends that rung on the one structural claim this session leaned on hardest and never measured:

    bit4 = (gp-0x6ac0 >= 400)     the r24 gain LERP's INNER (motor/resolver-rate) axis, against its
                                  FIRST breakpoint above zero.

★★ WHY THAT IS THE HIGHEST-VALUE BIT AVAILABLE -- IT ADJUDICATES A LIVE CONTRADICTION
--------------------------------------------------------------------------------------
Two of this kit's own load-bearing numbers disagree about which side of that breakpoint the car
operates on, and NOTHING in the record resolves it:

  * The **telemetry derivation**: bus counts = 1.697754 x `gp-0x6ac0` (byte-verified through cal
    `0xC613A` = 1159), from which 100% of all symptom windows were placed INSIDE the flat first
    segment `[0, 400]`. That was never measured directly -- it is bus telemetry pushed through a
    scale chain.
  * **V67's own arm value**: `5244 = 2 x 2622`, where 2622 is the LERP at "motor rate 128 deg/s".
    128 deg/s is **603 counts** -- which is on the SLOPED segment, i.e. the opposite side.

Both cannot be right, and the difference is not cosmetic. Read from the four mode-10 `gain_B`
records this build asserts byte-identical (`0xD2A74/0xD2AB0/0xD2AEC/0xD2B28`):

    X = (0, 400, 1400|1500, 3000)      Y = (3072, 3072, 2322, 1536)  etc.
    => the segment [0, 400] is EXACTLY FLAT in three of four records and flat to one count
       (2305 -> 2304) in the fourth.

    at 7.2 km/h:   rate <  400 counts  ->  LERP = 2704   (flat)
                   rate =  603 counts  ->  LERP = 2622   (sloped -- what 5244 was derived from)

⇒ if bit4 reads ~0%, V67's arm is delivering **5244/2704 = 1.94x**, not the 2.00x its docstring
claims, and the arm for exactly 2.00x is **5408**. That is a 3% correction -- immaterial to the fix,
but it is the difference between a number we measured and a number we assumed. More importantly it
decides, for every FUTURE calibration on this lane, whether the rate axis can discriminate at all:
**a lane whose operating point never leaves a flat segment cannot be tuned on wheel rate.**

⚠ ONE ASYMMETRY, STATED RATHER THAN DISCOVERED LATER. The LERP folds its key to 0 above
`RATE_FOLD = 13001` (`0x3AAC8 addi -0x32c9 / 0x3AACC cmovc`), so a folded value ALSO lands on the
flat first point. bit4 does not test the fold -- a second compare costs 6 more bytes than the cave
has. Therefore:

    bit4 == 0  =>  DEFINITELY inside the flat segment.                        (unambiguous)
    bit4 == 1  =>  on the sloped segment, OR folded past 13001 counts.        (two readings)

13001 counts is **2759 deg/s** of motor rate, roughly 20x the fastest this kit has ever recorded,
so the fold is implausible rather than impossible. The asymmetry runs in the safe direction: the
claim under test is "always flat", and bit4 == 0 confirms it outright.

★ bit3 BECOMES A BUILD-CLASS MARKER -- AND IT COSTS ZERO BYTES
---------------------------------------------------------------
🛑 The V64 lesson: a constant `0x87` has meant FOUR different things across builds (V64's detector
null, V65's neutral ladder bucket, V66's all-gates-zero, V67's gate-never-true), and V66/V67 are
**mutually inseparable by payload** -- `route_build_registry.identify()` asserts that as a property.
That ambiguity has already cost this kit a session.

V68 ends it for itself by folding bit3 into the liveness immediate: `movea 0x88,r0,r7` instead of
`movea 0x80,r0,r7`. **Same instruction, same four bytes, same encoder, different immediate.** So:

    EVERY legal V68 frame has BOTH bit7 AND bit3 set.

No prior build can produce that. V53 emits `0x07` and V54 `0x0F` (bit7 clear). V59/V62/V65 all emit
`0x87` (bit3 clear) on their own recorded routes. V66/V67 never set bit3 at all -- both builds
assert it. So "bit7 set and bit3 set on every distinct value" is a signature unique to V68, and
`identify()` is extended to say so. It also doubles as a second liveness bit: a frame with bit7 set
and bit3 clear is ILLEGAL under V68 and means the log is not V68's.

⚠ It is a marker, not proof of the flashed file. It EXCLUDES every prior build; it cannot exclude a
future one. The .rwd filename remains the primary evidence and the decoder still says so.

THE PAYLOAD -- 0x14A byte4 bits 7:3
------------------------------------
    bit7 = 1                    LIVENESS.  field == 0 => the cave did not fire => the reading is VOID
    bit6 = gp-0x6806 != 0       *** THE GATE *** -- carried from V67 unchanged. V67's own route
                                measured it at 99.983% agreement with carControl.latActive over
                                150,327 frames; bit6 keeps re-measuring it, and it is the
                                engagement covariate every other bit is conditioned on.
    bit5 = gp-0x671d != 0       *** THE MASKING RISK *** -- carried from V67 unchanged. It OUTRANKS
                                the arm at 0x3ABFA; if set, the gain is pinned to 1024, BELOW stock.
                                0.000% on route 47, but that is a clearance for one drive, not for
                                the lane.
    bit4 = gp-0x6ac0 >= 400     *** NEW *** the LERP inner axis vs its first breakpoint.
    bit3 = 1                    *** NEW *** the V68 BUILD-CLASS MARKER. Constant.
    bits 2:0                    stock STEER_SENSOR_STATUS, preserved.

🛑 WHAT THE STICKY / HIGH-FREQUENCY RUNG WOULD HAVE BEEN, AND WHY IT IS NOT HERE
---------------------------------------------------------------------------------
The brief asked for a latching rung sampling inside the 1 kHz task, to break the ~50 Hz aliasing
barrier (CAN 100.5 Hz, comma IMU 99.9-100.5 Hz; grind #2's "44.9 Hz" is itself an alias of ~55.6).
**It is not built, and the reason is not caution -- it is arithmetic, and three independent walls.**

  1. **BUDGET. It does not fit, and the cave must not grow.** V55's proven extent is 68 bytes and
     has flown eight times (V55/V57/V58/V59/V64/V65/V66/V67). Fixed overhead -- liveness, the
     payload read-modify-write, the displaced hook instruction, `jmp [lp]` -- is 24 bytes. Keeping
     bit6 and bit5 costs 12 bytes each. **That leaves 20 bytes.** A latch rung on `gp-0x4f62`
     needs, at minimum: `ld.h` (4) + abs via `cmp`/`bge`/`subr` (6) + a threshold compare (4+2+2)
     + the bit `movea` (4) = **22 bytes before any latch machinery at all**, and a genuine latch
     adds a RAM-cell load, a store, and a clear -- 38 bytes more. Growing the cave past 68 is
     precisely this kit's only bricking class (V24, V27, V48B).
  2. **IT IS NOT FREQUENCY-SELECTIVE, so it would not answer the question.** `gp-0x4f62` is read
     `ld.h` at 6 sites -- a SIGNED halfword, byte-verified -- and it is the raw 4-sample finite
     difference. A scalar threshold on |it| is an amplitude detector, not a band detector. Its
     low-frequency content (driver steering) already measures 123-839 counts, so any threshold that
     ignores the driver must sit above ~839 -- at which point the bit fires exactly during large
     driver inputs, which is *also* the condition under which grind #2 occurs. **The bit would be
     confounded with its own hypothesis by construction.** Making it band-selective needs a filter,
     and this kit has already established (see `docs/STATE.md`) that a filter able to bite by 42 Hz
     destroys the 20.9 Hz lead V62/V67 bought.
  3. **THE LATCH NEEDS A CLEAR EVENT THE CAVE CANNOT SEE.** A latch is only informative if it is
     reset once per transmitted frame. The cave cannot detect transmission, and its own payload
     write happens every invocation, so a self-cleared latch degenerates to a plain sample and a
     never-cleared latch pins ON after the first trip -- a dead probe that still looks alive.

⇒ **The sticky rung is not safe and not affordable, and it would not have measured what it was
meant to measure. GATE 1 was never reached, so no RAM cell is claimed and GATE 1 stays VACUOUS.**
V68 claims no RAM. Its only store is the existing CAN-330 payload byte `gp-0x1514`, asserted from
the emitted listing to be the ONE AND ONLY store in the cave -- exactly as on V55 through V67.

⚠ Recorded for whoever picks this up: `gp-0x683c` IS genuinely free after V67's repoint (0 readers,
0 writers, 0 extended-form candidates -- asserted below on every build). It is the best RAM
candidate this kit has. It is not used here because the *rung that would need it* fails on (1) and
(2) above, not because the cell failed. Do not read this build as clearing it either -- GATE 1's
register-indirect leg was never closed on it, and `gp-0x1500` passed both static methods and still
failed on-car.

THE NEW RUNG -- ENCODING, AND WHY IT IS 16 BYTES
-------------------------------------------------
`gp-0x6ac0` is a HALFWORD, read `ld.hu` at all 26 firmware read sites (byte-verified; zero `ld.h`,
zero `ld.b`), so it is UNSIGNED and no sign trap exists. 400 = 0x190 does not fit Format-II's
signed 5-bit `cmp` immediate, so the compare is done by subtracting the breakpoint with `movea`
(which sign-extends its imm16) and testing the sign:

    ld.hu -0x6ac0[gp],r6      e4374195     r6 = zero_extend(cell)          in [0, 65535]
    movea -0x190,r6,r6        263670fe     r6 = r6 - 400                   in [-400, 65135]
    cmp   r0,r6               e031         S = (r6 < 0), OV = 0 (no overflow is reachable)
    blt   +6                  b605         taken iff S^OV, i.e. iff cell < 400 -> skip
    movea 0x10,r7,r7          273e1000     bit4 = (cell >= 400)

The wire model checks that EXHAUSTIVELY over all 65,536 reachable cell values, not on a sample.

ENCODER PROVENANCE -- every emitted instruction pinned to a real instance
--------------------------------------------------------------------------
    ld.hu -0x6ac0[gp],r6   e4374195   *** BYTE-IDENTICAL at 0x45780, 0x4E6BA, 0x7CCCA, 0x7CE26 ***
    cmp   r0,r6            e031       BYTE-IDENTICAL at 398 sites, and FLOWN: it is V57's own
                                      cave rung at 0xC4B3C.
    blt   +6               b605       BYTE-IDENTICAL @0x1C006 (V65's pin) + 29 more
    movea 0x10,r7,r7       273e1000   FLOWN: V67's own bit4 movea at 0xC4B58
    movea -0x190,r6,r6     263670fe   ⚠ no byte-identical instance. hw1 `2636` -- opcode AND both
                                      register fields -- is byte-identical to 7 real instructions
                                      (0x1B114, 0x1B158, 0x4A712, 0x4A756, 0x5AE26, 0x60C56,
                                      0x85D8A); only the 16-bit IMMEDIATE is ours, which is data,
                                      not an encoding field. The reg1==reg2 "movea as add-immediate"
                                      shape is flown on seven builds (`movea 0xBB,r7,r7`), and the
                                      NEGATIVE-imm16 sign-extension it relies on is proven by the
                                      hook's own displaced instruction, `movea -0x1518,gp,r6`,
                                      which this very cave re-executes.
    movea 0x88,r0,r7       203e8800   hw1 `203e` byte-identical to `movea 0x80,r0,r7` at 0x1ED14 /
                                      0x51568 / 0x63726 (all real) and flown since V54; immediate
                                      differs only.
    ld.bu -0x6806[gp],r6   8437fb97   BYTE-IDENTICAL @0x2A8C0; flown V66/V67
    ld.bu -0x671d[gp],r6   a437e398   BYTE-IDENTICAL @0x3AB98 -- r24's own priority-chain read
    cmp   0x1,r6           6132       BYTE-IDENTICAL @0x14D46
    ld.bu -0x1514[gp],r6 / andi 0x7,r6,r6 / or r7,r6 / st.b r6,-0x1514[gp]   flashed since V31P

GATES
-----
GATE 1 (RAM ownership): **VACUOUS, and asserted as a MEASUREMENT.** No RAM cell is claimed. The
    cave's only store is the existing payload byte; the emitted listing is scanned and must contain
    EXACTLY ONE store. Every probed cell is asserted to be READ by the cave and WRITTEN nowhere.
    `gp-0x6ac0`'s own census (26 readers / 4 writers, all `ld.hu`/`st.h`, one extended-form hit that
    is a 32-bit alias of an already-counted store) is re-derived from raw bytes by TWO decoders.
GATE 2 (closed-loop stability): **NOT ENGAGED.** V68 changes no control path. The control-path
    assertions below are the proof of that, not a summary of it: the CAL block is asserted
    byte-identical to V67's, and the only permitted differences image-wide are the cave and the CRCs.
    V67's own GATE 2 argument carries over unchanged and is not restated here.
    *** Still CODE in the CAN-330 TX path, which is why base/hook/extent are reused, not moved.

⚠ ONE RESIDUAL ON THE NEW BIT, stated because it is real: the cave samples `gp-0x6ac0` at the TX
hook, while the LERP reads it inside `FUN_0003aa2c`. They are different points in the schedule, so
the probe's sample can be one tick stale relative to the gain evaluation. Immaterial for a
DISTRIBUTION question ("which side of 400 does the car live on"), and it is the same residual class
V67 recorded for the state mask. It would matter for a per-tick correlation; do not use it that way.

CAVE DISCIPLINE
---------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte proven extent as V55/V57/V58/V59/V64/V65/V66/V67
-- all EIGHT flew clean. Read-only; r6/r7 only. **64 of 68 bytes used, 4 spare.**

BASE = V67. Every V67 invariant is re-asserted on the output with ZERO exceptions on the control
path, and the exception set is machine-checked to be exactly {the cave span, the two CRC trailers}.

Decoder: rlog-tools/decode_v68_probe.py
"""
import hashlib
import itertools
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v54_tva as V54                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v59_tva as V59                # noqa: E402
import build_v62_tva as V62                # noqa: E402
import build_v63_tva as V63                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (census helper)
import build_v65_tva as V65                # noqa: E402  (COND_BLT and its pin)
import build_v66_tva as V66                # noqa: E402  (gain_B surface)
import build_v67_tva as V67                # noqa: E402  (direct base -- control path comes from here)
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT second decoder)
import v66_v67_explained as EX             # noqa: E402  (the arithmetic the new bit indexes)

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged since V55
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN

# =======================================================================================================
# V67's control path -- CARRIED, NOT RE-DERIVED. Every one of these is asserted on the output.
# =======================================================================================================
REPOINT_ADDR = V67.REPOINT_ADDR                # 0x3AA94
REPOINT_BYTE = V67.REPOINT_BYTE                # 0x3AA96 -- the one byte V67 moved
REPOINT_TO = V67.REPOINT_TO                    # ld.bu -0x6806[gp],r15
ARM_ADDR = V67.ARM_ADDR                        # 0xC6446
ARM_VALUE = V67.ARM_NEW                        # 5244
R26_ARM_ADDR = V67.R26_ARM_ADDR                # 0xC6444, stays stock 512
R26_AVG_CAL, R26_AVG_LEN = V67.R26_AVG_CAL, V67.R26_AVG_LEN
GATE_DISP = V67.GATE_DISP                      # 0x6806
DEAD_DISP = V67.DEAD_DISP                      # 0x683c -- UNREFERENCED after the repoint
MASK_DISP = V67.MASK_DISP                      # 0x671d
ARM3_DISP = V67.ARM3_DISP                      # 0x671a -- watched, but no longer probed

# The three `sar` sites the brief names explicitly, all STOCK (V66's revert, kept by V67 and V68).
SAR_SITES_STOCK = ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA))
# The four mode-10 gain_B records the new bit's breakpoint is read out of.
GAIN_B_RECORDS = V66.GAIN_B_RECORDS            # 0xD2A74 / 0xD2AB0 / 0xD2AEC / 0xD2B28
# The three sibling arms, all stock.
ARM_671D_ADDR, ARM_671D_STOCK = 0xC6442, EX.ARM_671D      # 1024
ARM_671A_ADDR, ARM_671A_STOCK = 0xC6440, EX.ARM_671A      # 2048
D2000_BLOCK = (0xD2000, 0xD2010)               # the slew-blend block V60 falsified; must not move

# =======================================================================================================
# THE ONE CHANGE -- the probe. bit4 is repointed; bit3 becomes the build-class marker.
# =======================================================================================================
BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_RATE = 0x40, 0x20, 0x10
BIT_CLASS = 0x08               # bit3: CONSTANT 1 on V68. The build-class marker.
LIVE_IMM = BIT_LIVE | BIT_CLASS                            # 0x88 -- one movea, zero extra bytes

RATE_DISP = 0x6AC0             # the r24 gain LERP's INNER axis. HALFWORD, ld.hu, unsigned.
RATE_BREAKPOINT = 400          # xs[1] in every mode-10 gain_B record -- asserted from the image
RATE_FOLD = EX.RATE_FOLD       # 13001; above this the LERP key folds to 0 -- the stated asymmetry

COND_BLT = V65.COND_BLT        # 0x6, SIGNED < -- pinned to the real `blt` @0x1C006

# Rung kinds. "byte_ge" = ld.bu + cmp imm5 + Bcond + movea       (12 bytes)
#             "hword_ge" = ld.hu + movea(-T) + cmp r0 + blt + movea (16 bytes)
KIND_BYTE, KIND_HWORD = "byte_ge", "hword_ge"
RUNG_LEN = {KIND_BYTE: 12, KIND_HWORD: 16}

# (gp displacement, bit, name, kind, threshold, what it decides)
CELLS = (
    (GATE_DISP, BIT_GATE, "gate_6806", KIND_BYTE, 1,
     "*** THE GATE *** -- carried from V67; duty vs latActive and the engagement covariate"),
    (MASK_DISP, BIT_MASK, "mask_671d", KIND_BYTE, 1,
     "*** THE MASKING RISK *** -- outranks the arm; if set the gain is pinned to 1024, BELOW stock"),
    (RATE_DISP, BIT_RATE, "rate_6ac0", KIND_HWORD, RATE_BREAKPOINT,
     "*** NEW *** the LERP inner axis vs its FIRST breakpoint -- flat segment or sloped"),
)

# ---- encoder pins, all read back FROM THE IMAGE in assert_signal_sites() -----------------------------
PIN_CMP_P1_R6 = V65.PIN_CMP_P1_R6                                    # (0x14D46, 6132, 1, r6)
PIN_BLT6 = V65.PIN_BLT6                                              # (0x1C006, b605)
PIN_LDBU_6806_R6 = V66.PIN_LDBU_6806_R6                              # (0x2A8C0, 8437fb97, 0x6806, 6)
PIN_LDBU_671D_R6 = V67.PIN_LDBU_671D_R6                              # (0x3AB98, a437e398, 0x671d, 6)
PIN_LDBU_6806_R15 = V67.PIN_LDBU_6806_R15                            # the repoint, byte-identical
# ★ the NEW rung's load -- FOUR byte-identical real instances, register field included.
PIN_LDHU_6AC0_R6 = (0x45780, bytes.fromhex("e4374195"), RATE_DISP, 6)
PIN_LDHU_6AC0_TWINS = (0x45780, 0x4E6BA, 0x7CCCA, 0x7CE26)
# `cmp r0,r6`. Byte-identical at 398 sites; the pin chosen is the FLOWN one -- V57's own cave rung.
PIN_CMP_R0_R6 = (0xC4B3C, bytes.fromhex("e031"))
PIN_CMP_R0_R6_ROM = 0x1507C                                          # a real, non-cave instance
# `movea 0x80,r0,r7` -- hw1 donor for the 0x88 liveness immediate.
PIN_MOVEA_R0_R7 = (0x1ED14, bytes.fromhex("203e8000"))
# ⚠ WEAKER PROVENANCE, declared rather than buried: `movea -0x190,r6,r6` has no byte-identical
# instance image-wide. hw1 (opcode + BOTH register fields) is byte-identical to these seven.
PIN_MOVEA_R6_R6_HW1 = (bytes.fromhex("2636"),
                       (0x1B114, 0x1B158, 0x4A712, 0x4A756, 0x5AE26, 0x60C56, 0x85D8A))
WEAK_PINS = ("movea -0x190,r6,r6",)

TAG = "LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-rateaxisprobe-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V68-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v68_plain_image.bin"))
V67_BIN = str(plain_image_path("_v67_plain_image.bin"))
DECODER = os.path.join(os.path.dirname(HERE), "rlog-tools", "decode_v68_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def decode_fmt2(halfword):
    """V850 Format-II split: imm5 = bits[4:0] (SIGNED), opcode = bits[10:5], reg2 = bits[15:11]."""
    imm = halfword & 0x1F
    return {"imm5": imm - 32 if imm & 0x10 else imm,
            "opcode": (halfword >> 5) & 0x3F,
            "reg2": (halfword >> 11) & 0x1F}


def decode_load(raw):
    """Decode an emitted 4-byte load through the INDEPENDENT scan_gp_accesses decoder.

    🛑 The hw1-bit-5 guard. `ld.bu` puts the displacement's bit 0 in the OPCODE FIELD (0x3C/0x3D),
    so a parity slip silently addresses the NEIGHBOURING cell with every other field still perfect.
    Returns (mnemonic, gp offset as a POSITIVE kit-convention number, reg1, reg2).
    """
    hw1, hw2 = struct.unpack("<HH", raw)
    d = SCAN.decode_op((hw1 >> 5) & 0x3F, hw1, hw2)
    assert d is not None, f"{raw.hex()} is not a Format-VII load/store at all"
    mnem, disp_u16, _is_store = d
    return mnem, (0x10000 - disp_u16) & 0xFFFF, hw1 & 0x1F, (hw1 >> 11) & 0x1F


def _emit_load(disp, kind):
    """The one place a cell's load is encoded, so the wire model and the cave cannot diverge."""
    return V55.ldbu_any(-disp, R6) if kind == KIND_BYTE else FF.ldhu(disp, R6)


# =======================================================================================================
# Encoders
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V67._self_check_encoders()          # inherits the whole chain back to FOURFRAME
    assert GP == 4, "GP is not r4; every real gp-relative instance in this image carries reg1 = r4"

    # ---- the two BYTE rungs, carried from V67 unchanged -------------------------------------------
    for disp, _bit, name, kind, lvl, _why in CELLS:
        if kind != KIND_BYTE:
            continue
        raw = V55.ldbu_any(-disp, R6)
        mnem, got, reg1, reg2 = decode_load(raw)
        assert (mnem, got, reg1, reg2) == ("ld.bu", disp, GP, R6), \
            f"{name}: emitted load decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2} -- the " \
            "hw1-bit-5 trap, and the neighbouring cell is a real live cell"
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == (0x3C | (((0x10000 - disp) & 0xFFFF) & 1)), \
            f"{name}: opcode field 0x{op:02X} does not match the displacement parity"
        assert struct.unpack_from("<H", raw, 2)[0] & 1 == 1, f"{name}: ld.bu hw2 LSB must be SET"
        assert raw != FF.stb(R6, -disp, GP), f"{name}: the load collapsed onto an st.b"
        assert raw != FF.ldhu(disp, R6), f"{name}: ld.bu collapsed onto ld.hu -- it would straddle"
        assert V55.cmp_imm5(lvl, R6) == PIN_CMP_P1_R6[1], f"{name}: `cmp 0x1,r6` is not the pin"

    # ---- ★ THE NEW RUNG. Every instruction built by the encoder, then decoded back. ---------------
    load = FF.ldhu(RATE_DISP, R6)
    assert load == PIN_LDHU_6AC0_R6[1], \
        f"the encoder builds {load.hex()} for `ld.hu -0x6ac0[gp],r6`, not the real instance " \
        f"{PIN_LDHU_6AC0_R6[1].hex()} @0x{PIN_LDHU_6AC0_R6[0]:05X}"
    mnem, got, reg1, reg2 = decode_load(load)
    assert (mnem, got, reg1, reg2) == ("ld.hu", RATE_DISP, GP, R6), \
        f"the new rung's load decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
    assert struct.unpack_from("<H", load, 2)[0] & 1 == 1, \
        "ld.hu hw2 LSB must be SET -- a clear LSB is the ld.h (SIGNED) form and would invert the test"
    assert load != V55.ldh(RATE_DISP, R6), \
        "the emitted ld.hu collapsed onto the SIGNED ld.h -- negative cells would then pass `>= 400`"
    assert load != V55.ldbu_any(-RATE_DISP, R6), "ld.hu collapsed onto ld.bu -- it would read 8 bits"
    assert load != FF.sth(R6, -RATE_DISP, GP), "the emitted load collapsed onto an st.h"

    sub = FF.movea((-RATE_BREAKPOINT) & 0xFFFF, R6, R6)
    assert sub == bytes.fromhex("263670fe"), f"`movea -0x190,r6,r6` encodes as {sub.hex()}"
    assert sub[:2] == PIN_MOVEA_R6_R6_HW1[0], \
        f"the movea hw1 {sub[:2].hex()} is not the real {PIN_MOVEA_R6_R6_HW1[0].hex()}"
    hw1 = struct.unpack("<H", sub[:2])[0]
    assert ((hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11) == (0x31, R6, R6), \
        "the movea's opcode/reg1/reg2 fields are not (0x31, r6, r6)"
    assert struct.unpack("<H", sub[2:])[0] == (0x10000 - RATE_BREAKPOINT), \
        "the movea's imm16 is not -400"
    # 🛑 sign-extension is the whole rung. Pinned to the hook's OWN displaced instruction, which is a
    # real `movea` with a NEGATIVE imm16 and which this cave re-executes verbatim.
    assert HOOK_STOCK == FF.movea((-0x1518) & 0xFFFF, GP, R6), \
        "the displaced hook instruction is not `movea -0x1518,gp,r6` -- the sign-extension pin is gone"
    assert struct.unpack("<H", HOOK_STOCK[2:])[0] & 0x8000, \
        "the hook's movea imm16 is not negative -- it no longer demonstrates sign-extension"

    cmp_rr = V54.cmp_rr(R0, R6)
    assert cmp_rr == PIN_CMP_R0_R6[1], f"`cmp r0,r6` encodes as {cmp_rr.hex()}, not e031"
    f = decode_fmt2(struct.unpack("<H", cmp_rr)[0])
    assert (f["opcode"], f["reg2"]) == (0x0F, R6) and struct.unpack("<H", cmp_rr)[0] & 0x1F == R0, \
        f"`cmp r0,r6` decodes as {f} -- not Format-I cmp reg1=r0 reg2=r6"
    assert V54.cmp_rr(R0, R6) != V54.cmp_rr(R0, R7), "cmp_rr ignores reg2"
    assert V54.cmp_rr(R0, R6) != V54.cmp_rr(R7, R6), "cmp_rr ignores reg1"
    assert cmp_rr != V55.cmp_imm5(0, R6), "the reg-reg cmp collapsed onto the imm5 form"

    assert FF.bcond(COND_BLT, +6) == PIN_BLT6[1], \
        f"`blt +6` fails the real `blt` @0x{PIN_BLT6[0]:05X}"
    assert COND_BLT == 0x6, "COND_BLT drifted"
    assert struct.unpack("<H", FF.bcond(COND_BLT, +6))[0] & 0xF == COND_BLT

    # ---- the bit-set moveas ----------------------------------------------------------------------
    for _d, bit, name, _k, _l, _w in CELLS:
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"{name}: movea 0x{bit:x},r7,r7 bad"
    live = FF.movea(LIVE_IMM, R0, R7)
    assert live.hex() == "203e8800", f"`movea 0x88,r0,r7` encodes as {live.hex()}"
    assert live[:2] == PIN_MOVEA_R0_R7[1][:2], \
        "the liveness movea's hw1 differs from the real `movea 0x80,r0,r7` -- more than the immediate"
    assert live != FF.movea(BIT_LIVE, R0, R7), "the class marker did not change the immediate"
    assert FF.movea(LIVE_IMM, R0, R7)[:2] != FF.movea(LIVE_IMM, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 is ADDED to itself, not loaded"

    # ---- the bit map -----------------------------------------------------------------------------
    bits = (BIT_LIVE, BIT_CLASS) + tuple(b for _, b, _, _, _, _ in CELLS)
    assert len(set(bits)) == len(bits) and all(b & (b - 1) == 0 for b in bits), \
        "probe bits are not distinct single bits"
    assert sum(bits) == 0xF8, "probe bits must span exactly 7:3 with NO bit unassigned on V68"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert LIVE_IMM == BIT_LIVE | BIT_CLASS, "the liveness immediate does not carry the class marker"
    assert [b for _, b, _, _, _, _ in CELLS] == \
        sorted((b for _, b, _, _, _, _ in CELLS), reverse=True), \
        "the cell bits are not in descending bit order"
    assert {c[0] for c in CELLS} == {GATE_DISP, MASK_DISP, RATE_DISP}, "the probed cell set moved"
    assert ARM3_DISP not in {c[0] for c in CELLS}, \
        "gp-0x671a is still probed -- V68's whole point is that bit4 was a wasted rung"


# =======================================================================================================
# The cave -- 64 bytes of the 68-byte proven extent
# =======================================================================================================

def build_cave():
    """pack_rate_axis_probe -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x88,r0,r7       ; r7 = 0x88   bit7 LIVENESS + bit3 BUILD-CLASS MARKER
        ld.bu -0x6806[gp],r6   ; *** THE GATE *** -- carried from V67
        cmp   0x1,r6           ; ld.bu zero-extends => SIGNED < 1 is exactly == 0
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6806 != 0
      g_gate:
        ld.bu -0x671d[gp],r6   ; *** THE MASKING RISK *** -- carried from V67
        cmp   0x1,r6
        blt   +6
        movea 0x20,r7,r7       ; bit5 = gp-0x671d != 0
      g_mask:
        ld.hu -0x6ac0[gp],r6   ; *** NEW *** the LERP inner axis. HALFWORD, UNSIGNED.
        movea -0x190,r6,r6     ; r6 = rate - 400   (movea sign-extends its imm16)
        cmp   r0,r6            ; S = (r6 < 0), OV = 0
        blt   +6               ; SIGNED < 0  -> rate < 400 -> the FLAT segment -> skip
        movea 0x10,r7,r7       ; bit4 = gp-0x6ac0 >= 400
      g_rate:
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(LIVE_IMM, R0, R7), "movea 0x88,r0,r7    ; bit7 LIVENESS + bit3 CLASS MARKER")

    rungs = []
    for disp, bit, name, kind, lvl, _why in CELLS:
        load_idx = len(listing)
        emit(_emit_load(disp, kind),
             f"ld.{'bu' if kind == KIND_BYTE else 'hu'} -0x{disp:04x}[gp],r6 ; {name}")
        if kind == KIND_BYTE:
            emit(V55.cmp_imm5(lvl, R6), "cmp 0x1,r6          ; zero-extended byte: <1 IS ==0")
        else:
            emit(FF.movea((-lvl) & 0xFFFF, R6, R6),
                 f"movea -0x{lvl:x},r6,r6  ; r6 = rate - {lvl}  (movea SIGN-EXTENDS imm16)")
            emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; S = (r6 < 0), OV = 0")
        br_idx = len(listing)
        emit(FF.bcond(COND_BLT, +6), f"blt +6              ; skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7   ; bit{bit.bit_length() - 1} = gp-0x{disp:04x} >= {lvl}")
        rungs.append((load_idx, br_idx, CAVE_BASE + len(body), name, disp, bit, kind, lvl))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands exactly on its label. Located BY POSITION, not by content --
    # the cave emits THREE identical `blt +6`, so a content lookup is ambiguous by construction.
    assert [r[1] for r in rungs] == [3, 7, 12], f"rung branch indices drifted: {[r[1] for r in rungs]}"
    for load_idx, br_idx, label, name, disp, _bit, kind, lvl in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == COND_BLT, f"{name}: wrong branch condition"
        assert listing[load_idx][1] == _emit_load(disp, kind), f"{name}: wrong cell loaded"
        n_mid = br_idx - load_idx - 1
        assert n_mid == (1 if kind == KIND_BYTE else 2), \
            f"{name}: {n_mid} instruction(s) between the load and the branch, expected " \
            f"{1 if kind == KIND_BYTE else 2} for a {kind} rung"
        if kind == KIND_BYTE:
            assert listing[load_idx + 1][1] == V55.cmp_imm5(lvl, R6), f"{name}: cmp is not `0x{lvl:x},r6`"
        else:
            assert listing[load_idx + 1][1] == FF.movea((-lvl) & 0xFFFF, R6, R6), \
                f"{name}: the threshold subtract is not `movea -0x{lvl:x},r6,r6`"
            assert listing[load_idx + 2][1] == V54.cmp_rr(R0, R6), f"{name}: the compare is not `cmp r0,r6`"

    # ---- GATE 2b: r6/r7 LIVENESS. Only the rung's own load and its threshold subtract may write r6;
    # everything else in the rung region writes r7. Nothing else may be touched at all.
    load_addrs = {listing[r[0]][0] for r in rungs}
    sub_addrs = {listing[r[0] + 1][0] for r in rungs if r[6] == KIND_HWORD}
    for idx in range(1, rungs[-1][1] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        op = (hw >> 5) & 0x3F
        if op in (0x13, 0x0F):                                # cmp imm5,reg2 / cmp reg1,reg2 -- flags only
            continue
        if addr in load_addrs or addr in sub_addrs:
            assert (hw >> 11) == R6, f"listing[{idx}] '{text}' writes r{hw >> 11}, not r6"
            continue
        assert (hw >> 11) == R7, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{R7}"
    for disp, _bit, name, kind, _l, _w in CELLS:
        assert sum(1 for _, r, _ in listing if r == _emit_load(disp, kind)) == 1, \
            f"{name}: gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store, the payload byte.
    store_ops = {0x3A: "st.b", 0x3B: "st.h/st.w"}
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in store_ops]
    assert store_idx == [17], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[17][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the payload byte"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    want = 24 + sum(RUNG_LEN[c[3]] for c in CELLS)
    assert len(body) == want == 64, f"the cave is {len(body)}B; the budget says {want}B"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V68 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, " \
        "do not grow it: caves are this kit's only bricking class"
    # 🛑 the sticky-rung finding, as an executable fact rather than a paragraph: a latching HF rung
    # needs >= 22 bytes before any latch machinery, and only this much is free.
    spare = len(V55.CAVE_BYTES) - len(body)
    assert spare == 4, f"{spare} spare bytes, expected 4"
    assert spare < 22, \
        "there are now >= 22 spare bytes -- re-examine the sticky/HF rung, the budget argument in " \
        "this build's docstring assumed it did not fit"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_byte4(values, status_bits=0x7):
    """Exactly what the cave writes, given each cell's RAM value. `values` is keyed by displacement."""
    b = LIVE_IMM                                # bit7 liveness + bit3 class marker
    for disp, bit, _name, kind, lvl, _why in CELLS:
        if kind == KIND_BYTE:
            v = values[disp] & 0xFF             # ld.bu ZERO-EXTENDS a byte -> r6 in [0,255]
            skip = v < lvl                      # signed and unsigned agree on a zero-extended byte
        else:
            v = values[disp] & 0xFFFF           # ld.hu ZERO-EXTENDS a halfword -> r6 in [0,65535]
            skip = (v - lvl) < 0                # movea then SIGNED blt, in 32 bits
        if not skip:
            b |= bit
    return b | (status_bits & PAYLOAD_KEEP_MASK)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false"."""
    if (byte4 >> 3) & 0x1F == 0:
        return None
    out = {"live": bool(byte4 & BIT_LIVE), "class_marker": bool(byte4 & BIT_CLASS)}
    for disp, bit, name, _k, _l, _w in CELLS:
        out[name] = bool(byte4 & bit)
    # ★ V68's structural signature: BOTH constants must be set on every legal frame.
    out["structural_ok"] = out["live"] and out["class_marker"]
    return out


def _self_check_wire():
    """The byte cells EXHAUSTIVELY over 256 values, the halfword cell over all 65,536."""
    zeros = {d: 0 for d, _, _, _, _, _ in CELLS}
    for other in (0, 0xFF):
        for disp, bit, name, kind, lvl, _w in CELLS:
            span = 256 if kind == KIND_BYTE else 65536
            for v in range(span):
                vals = {d: (v if d == disp else other) for d, _, _, _, _, _ in CELLS}
                d_ = decode_field(wire_byte4(vals))
                assert d_ is not None and d_["live"], f"{name}={v} decodes as VOID"
                assert d_["class_marker"], f"{name}={v}: the class marker is CLEAR"
                assert d_[name] == (v >= lvl), f"{name}: bit wrong at value {v} (threshold {lvl})"
    grid = (0, 1, 2, 5, 0xFF)
    hgrid = (0, 1, 399, 400, 401, 13000, RATE_FOLD, 0x7FFF, 0x8000, 0xFFFF)
    for combo in itertools.product(grid, grid, hgrid):
        vals = {c[0]: v for c, v in zip(CELLS, combo)}
        d_ = decode_field(wire_byte4(vals))
        for (disp, _bit, name, _k, lvl, _w), v in zip(CELLS, combo):
            assert d_[name] == (v >= lvl), f"{name} wrong in combo {combo}"

    # 🛑 THE SIGN TRAP, exhaustively: a halfword above 0x7FFF must still read as a LARGE number,
    # because the load is ld.hu (zero-extending) and the subtract happens in 32 bits. If the load
    # were ever `ld.h`, 0x8000..0xFFFF would go NEGATIVE and every one of them would flip.
    for v in (0x8000, 0xC000, 0xFFFF):
        assert wire_byte4({**zeros, RATE_DISP: v}) & BIT_RATE, \
            f"halfword 0x{v:04X} reads as BELOW the breakpoint -- the load is behaving as SIGNED"
    for v in range(0, RATE_BREAKPOINT):
        assert not (wire_byte4({**zeros, RATE_DISP: v}) & BIT_RATE)
    for v in range(RATE_BREAKPOINT, RATE_BREAKPOINT + 64):
        assert wire_byte4({**zeros, RATE_DISP: v}) & BIT_RATE
    # no signed overflow is reachable, so `blt` (S^OV) really is the sign of the difference
    assert -0x8000 < (0 - RATE_BREAKPOINT) and (0xFFFF - RATE_BREAKPOINT) < 0x7FFFFFFF, \
        "the movea subtract can overflow -- `blt` would then not be the sign of the difference"

    # exactly EIGHT payloads are reachable, all with bit7 AND bit3 set
    legal = {wire_byte4({c[0]: (c[4] if on else 0) for c, on in zip(CELLS, sel)}, status_bits=0)
             for sel in itertools.product((0, 1), repeat=len(CELLS))}
    assert len(legal) == 2 ** len(CELLS), f"the probe emits {len(legal)} payloads, expected 8"
    assert all(b & BIT_LIVE and b & BIT_CLASS for b in legal), \
        "a reachable payload is missing the liveness bit or the class marker"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"

    # ★★ THE BUILD-CLASS MARKER, as an executable claim: V68's payload set is DISJOINT from the
    # payload sets of every prior build with a probe. This is the thing V66/V67 could not do.
    v67_legal = {V67.wire_byte4({d: (lvl if on else 0)
                                 for (d, _, _, lvl, _, _), on in zip(V67.CELLS, sel)}, status_bits=0)
                 for sel in itertools.product((0, 1), repeat=len(V67.CELLS))}
    v66_legal = {V66.wire_byte4({d: (1 if on else 0) for (d, _, _, _), on in zip(V66.CELLS, sel)},
                                status_bits=0)
                 for sel in itertools.product((0, 1), repeat=len(V66.CELLS))}
    assert not (legal & v67_legal), \
        f"V68 and V67 share payloads {sorted(hex(b) for b in legal & v67_legal)} -- the marker fails"
    assert not (legal & v66_legal), "V68 and V66 share a payload -- the marker fails"
    assert v66_legal == v67_legal, \
        "V66 and V67 no longer emit identical payload sets -- the premise of the marker has moved"
    on_wire = {b | PAYLOAD_KEEP_MASK for b in legal}     # as transmitted, status bits all set
    assert 0x87 not in on_wire and 0x8F in on_wire, \
        "V68 must never emit 0x87 (the four-way-ambiguous byte) and must emit 0x8F"
    assert all(b & 0xF8 != 0 for b in legal), "a legal payload collides with the VOID sentinel"

    # ---- the breakpoint's MEANING, through the real LERP arithmetic -------------------------------
    sc = int(7.2 * 64.0625)
    flat = EX.r24_gain_q10(sc, 0, 0, 0, 0)
    assert EX.r24_gain_q10(sc, RATE_BREAKPOINT - 1, 0, 0, 0) == flat, \
        "the segment below the breakpoint is not flat -- bit4 does not mean what the docstring says"
    assert EX.r24_gain_q10(sc, RATE_BREAKPOINT + 200, 0, 0, 0) < flat, \
        "the segment above the breakpoint does not fall -- the breakpoint is not where we think"
    assert EX.r24_gain_q10(sc, RATE_FOLD, 0, 0, 0) == flat, \
        "the fold above RATE_FOLD does not land on the flat first point -- the stated asymmetry is wrong"
    _self_check_wire.flat_lerp = flat
    _self_check_wire.arm_for_2x_if_flat = 2 * flat


_self_check_wire()

FLAT_LERP = _self_check_wire.flat_lerp                       # 2704
ARM_FOR_2X_IF_FLAT = _self_check_wire.arm_for_2x_if_flat     # 5408


# =======================================================================================================
# Image-level gates
# =======================================================================================================

CENSUS_EXPECTED = {                         # on the V68 OUTPUT
    GATE_DISP: (14, 16, V67.GATE_WRITERS, {"ld.bu", "st.b"}, "ld.bu"),
    DEAD_DISP: (0, 0, [], {"ld.bu"}, None),     # UNREFERENCED image-wide since V67's repoint
    MASK_DISP: (14, 2, V67.MASK_WRITERS, {"ld.bu", "st.b"}, "ld.bu"),
    ARM3_DISP: (7, 1, V67.ARM3_WRITERS, {"ld.bu", "st.b"}, None),   # watched, no longer probed
    RATE_DISP: (26, 4, [0x41820, 0x41832, 0x41A8C, 0x41AAC], {"ld.hu", "st.h"}, "ld.hu"),
}
CENSUS_EXPECTED_SRC = dict(CENSUS_EXPECTED)     # on the V67 SOURCE the cave reads gp-0x671a, not 0x6ac0
CENSUS_EXPECTED_SRC[ARM3_DISP] = (7, 1, V67.ARM3_WRITERS, {"ld.bu", "st.b"}, "ld.bu")
CENSUS_EXPECTED_SRC[RATE_DISP] = (26, 4, [0x41820, 0x41832, 0x41A8C, 0x41AAC], {"ld.hu", "st.h"}, None)

CENSUS_CONSUMERS = {GATE_DISP: REPOINT_ADDR,        # the repoint itself, asserted as a reader
                    MASK_DISP: 0x3AB98,
                    ARM3_DISP: 0x3AA70,
                    RATE_DISP: 0x3AAC4}             # r24's own LERP index read in FUN_0003aa2c
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# Where THIS cave reads each cell, derived from the listing so it can never drift from the code.
CAVE_CELL_READS = {}
for _disp, _bit, _name, _kind, _l, _w in CELLS:
    _sites = [a for a, r, _ in CAVE_LISTING if r == _emit_load(_disp, _kind)]
    assert len(_sites) == 1, f"gp-0x{_disp:04x} must be read EXACTLY once in the cave"
    CAVE_CELL_READS[_disp] = (_sites[0], "ld.bu" if _kind == KIND_BYTE else "ld.hu")

V67_CAVE_CELL_READS = {d: (a, "ld.bu") for d, a in V67.CAVE_CELL_READS.items()}


def assert_cell_census(buf, label="V68", cave_reads=None, expected=None):
    """Re-derive the reader/writer sets from raw bytes and assert them exactly, by TWO decoders.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    expected = CENSUS_EXPECTED if expected is None else expected
    cave_reads = CAVE_CELL_READS if cave_reads is None else cave_reads
    span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    for disp, (n_read, n_write, writers, mnems, _cave_mnem) in expected.items():
        hits = V64.gp_access_census(buf, disp)
        assert all(m in mnems for _, m, _ in hits), \
            f"{label}: gp-0x{disp:04x} has an access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        fw = [h for h in hits if h[0] not in span]
        reads = [h for h in fw if h[1] in _READ_MNEM]
        writes = [h for h in fw if h[1] not in _READ_MNEM]
        assert len(reads) == n_read, \
            f"{label}: gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}: " \
            f"{[hex(a) for a, _, _ in reads]}"
        assert len(writes) == n_write, \
            f"{label}: gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}: " \
            f"{[hex(a) for a, _, _ in writes]}"
        assert [a for a, _, _ in writes] == writers, \
            f"{label}: gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}"
        if disp in CENSUS_CONSUMERS:
            assert any(a == CENSUS_CONSUMERS[disp] for a, _, _ in reads), \
                f"{label}: the consumer at 0x{CENSUS_CONSUMERS[disp]:05X} no longer reads " \
                f"gp-0x{disp:04x} -- the cell the probe reports on is not the one the gain uses"
        # ⚠ GATE 1 restated as a MEASUREMENT: the cave READS this cell and WRITES it nowhere.
        cave = [h for h in hits if h[0] in span]
        want = [(cave_reads[disp][0], cave_reads[disp][1], R6)] if disp in cave_reads else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"

        # ---- SECOND METHOD: per-opcode decode over EVERY byte offset + the 48-bit extended form.
        alt = SCAN.scan(buf, (-disp) & 0xFFFF)
        alt_even = [h for h in alt if h["even"]]
        assert len(alt_even) == len(hits), \
            f"{label}: the two decoders disagree on gp-0x{disp:04x}: {len(hits)} vs {len(alt_even)}"
        assert sorted(h["addr"] for h in alt_even) == sorted(a for a, _, _ in hits), \
            f"{label}: the two decoders disagree on WHICH addresses touch gp-0x{disp:04x}"
        assert not [h for h in alt if not h["even"]], \
            f"{label}: gp-0x{disp:04x} has an ODD-OFFSET hit -- confirm the instruction boundary"
        ext = SCAN.scan_ext(buf, -disp)
        genuine = []
        for h in ext:
            d7 = SCAN.decode_fmt7(buf, h["addr"])
            if d7 is None or d7[4] != GP:
                genuine.append(h)
        if disp == DEAD_DISP:
            # ⚠ The record, kept alive on every build: gp-0x683c is UNREFERENCED after V67's repoint.
            # That makes it the best free-RAM candidate this kit has -- and V68 still does not use it.
            assert not ext, f"{label}: gp-0x683c has {len(ext)} extended-displacement candidates"
            assert n_read == 0 and n_write == 0 and not reads and not writes, \
                f"{label}: gp-0x683c has acquired an access"
        assert not genuine, \
            f"{label}: gp-0x{disp:04x} has {len(genuine)} extended-form candidate(s) that are NOT " \
            f"32-bit aliases: {[hex(h['addr']) for h in genuine[:8]]}"


def assert_probe_sites(code, label="V68"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V67 cave remnants survive past our payload"


def assert_signal_sites(code, label="V68"):
    """Every instruction donor the emitted encoders are pinned to, read FROM THE IMAGE."""
    for addr, raw, disp, reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_671D_R6, PIN_LDBU_6806_R15,
                                  PIN_LDHU_6AC0_R6):
        assert bytes(code[addr:addr + 4]) == raw, \
            f"{label}: the pinned load at 0x{addr:05X} is {bytes(code[addr:addr+4]).hex()}, not {raw.hex()}"
        assert decode_load(raw)[1:] == (disp, GP, reg2), \
            f"{label}: the donor @0x{addr:05X} does not decode as gp-0x{disp:04x} -> r{reg2}"
    # ★ all FOUR byte-identical twins of the new rung's load
    for a in PIN_LDHU_6AC0_TWINS:
        assert bytes(code[a:a + 4]) == PIN_LDHU_6AC0_R6[1], \
            f"{label}: the `ld.hu -0x6ac0[gp],r6` twin @0x{a:05X} moved"
    assert bytes(code[PIN_BLT6[0]:PIN_BLT6[0] + 2]) == PIN_BLT6[1], \
        f"{label}: the pinned `blt +6` at 0x{PIN_BLT6[0]:05X} moved"
    assert bytes(code[PIN_CMP_P1_R6[0]:PIN_CMP_P1_R6[0] + 2]) == PIN_CMP_P1_R6[1], \
        f"{label}: the pinned `cmp 0x1,r6` at 0x{PIN_CMP_P1_R6[0]:05X} moved"
    assert bytes(code[PIN_CMP_R0_R6_ROM:PIN_CMP_R0_R6_ROM + 2]) == PIN_CMP_R0_R6[1], \
        f"{label}: the real `cmp r0,r6` at 0x{PIN_CMP_R0_R6_ROM:05X} moved"
    assert bytes(code[PIN_MOVEA_R0_R7[0]:PIN_MOVEA_R0_R7[0] + 4]) == PIN_MOVEA_R0_R7[1], \
        f"{label}: the real `movea 0x80,r0,r7` at 0x{PIN_MOVEA_R0_R7[0]:05X} moved"
    # ⚠ the WEAK pin: hw1 only, at seven real sites. Assert every one of them.
    hw1, sites = PIN_MOVEA_R6_R6_HW1
    for a in sites:
        assert bytes(code[a:a + 2]) == hw1, \
            f"{label}: the `movea imm,r6,r6` hw1 donor @0x{a:05X} is " \
            f"{bytes(code[a:a+2]).hex()}, not {hw1.hex()} -- the new rung's only provenance"
    # r24's own LERP index read and the fold, so the new bit provably indexes the SAME cell the gain does
    assert bytes(code[0x3AAC4:0x3AAC8]) == bytes.fromhex("e45f4195"), \
        f"{label}: `ld.hu -0x6ac0[gp],r11` @0x3AAC4 moved -- r24's own read of the LERP index"
    assert u16(code, 0x3AAC8) == 0x060B and u16(code, 0x3AACC) == 0x5FE0, \
        f"{label}: the RATE_FOLD test at 0x3AAC8/0x3AACC moved -- the stated bit4 asymmetry is stale"
    V67.assert_signal_sites(code, label)


def assert_control_path(code, v67, label="V68"):
    """🛑 V68's core claim: the control path is V67's, byte for byte. Asserted, never assumed."""
    # --- the two V67 edits, from the image
    V67.assert_repoint(code, label, done=True)
    assert code[REPOINT_BYTE] == REPOINT_TO[2] == 0xFB, \
        f"{label}: 0x{REPOINT_BYTE:05X} is 0x{code[REPOINT_BYTE]:02X}, not 0xFB -- V67's repoint"
    assert u16(code, ARM_ADDR) == ARM_VALUE, \
        f"{label}: the arm 0x{ARM_ADDR:05X} is {u16(code, ARM_ADDR)}, not V67's {ARM_VALUE}"
    # --- the three `sar` sites, ALL STOCK
    for addr, want in SAR_SITES_STOCK:
        assert u16(code, addr) == want, \
            f"{label}: 0x{addr:05X} is 0x{u16(code, addr):04X}, not the stock 0x{want:04X}"
    # --- the sibling arms
    for addr, want, what in ((ARM_671A_ADDR, ARM_671A_STOCK, "0xC6440 the third arm"),
                             (ARM_671D_ADDR, ARM_671D_STOCK, "0xC6442 the masking arm"),
                             (R26_ARM_ADDR, V67.R26_ARM_STOCK, "0xC6444 r26's arm")):
        assert u16(code, addr) == want, f"{label}: {what} is {u16(code, addr)}, not {want}"
    # --- the four mode-10 gain_B records the new bit's breakpoint is read out of
    for rec in GAIN_B_RECORDS:
        assert bytes(code[rec:rec + V66.GAIN_B_RECORD_LEN]) == \
            bytes(v67[rec:rec + V66.GAIN_B_RECORD_LEN]), \
            f"{label}: mode-10 gain_B record 0x{rec:05X} differs from V67's"
    # --- the blend block, the lockout, the decoupled private gain
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == bytes(v67[D2000_BLOCK[0]:D2000_BLOCK[1]]), \
        f"{label}: the 0xD2000 block differs from V67's"
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW == 0, \
        f"{label}: 0xC62EA is {u16(code, V53.LOCKOUT_ADDR)}, not 0"
    assert u16(code, V57.PRIVATE_ADDR) == V57.GAIN_4X == 3564, \
        f"{label}: 0xC6CD0 is {u16(code, V57.PRIVATE_ADDR)}, not 3564"
    # --- and every inherited table, re-run through V67's own assertions
    V62.assert_sar_sites(code, label, expect_doubled=False)
    V67.assert_untouched_context_v67(code, label)
    V63.assert_arms(code, label, expect_raised=False)
    V67.assert_untouched_v67(code, label)
    V57.assert_decoupled(code, label)
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, label)
    V66.assert_gain_b_surface(code, v67, label)
    assert set(code[R26_AVG_CAL:R26_AVG_CAL + R26_AVG_LEN]) == {0}, \
        f"{label}: 0xC6564 is no longer all-zero -- the r26-INERT record is what makes V67's shared " \
        "gate harmless, and V68 carries that gate unchanged. STOP and re-derive."


def assert_decoder_matches(cave_bytes, label="V68"):
    """🛑 The decoder's header must match the BUILT image, not a previous revision."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, f"{label}: {DECODER} carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"{label}: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   " \
        f"{cave_bytes.hex()}"
    for disp, bit, _name, _k, _l, _w in CELLS:
        assert f"gp-0x{disp:04x}" in txt, \
            f"{label}: the decoder never mentions gp-0x{disp:04x} (bit{bit.bit_length() - 1})"
    for token in (str(RATE_BREAKPOINT), str(RATE_FOLD), str(ARM_VALUE), os.path.basename(OUT)):
        assert token in txt, f"{label}: the decoder does not carry '{token}'"
    return True


def build():
    if not os.path.exists(V67_BIN):
        print(f"  {V67_BIN} missing -- running the V67 builder first\n")
        V67.build()
    v67 = bytearray(open(V67_BIN, "rb").read())
    sha = hashlib.sha256(bytes(v67)).hexdigest()
    print(f"  V67 source {V67_BIN}\n    SHA256 {sha}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v67, "V67 source")
    assert walk(bytes(v67), label="V67 source") == 0
    assert walk_all_blocks(bytes(v67), label="V67 source") == 0
    V67.assert_probe_sites(v67, "V67 source")        # V67's OWN cave must be intact first
    assert_signal_sites(v67, "V67 source")
    assert_control_path(v67, v67, "V67 source")
    assert_cell_census(bytes(v67), "V67 source",
                       cave_reads=V67_CAVE_CELL_READS, expected=CENSUS_EXPECTED_SRC)
    V67.scan_self_check(bytes(v67), "V67 source", repointed=True)
    print("    census OK (TWO decoders): gp-0x6806 14r/16w, gp-0x683c 0r/0w, gp-0x671d 14r/2w,")
    print("               gp-0x671a 7r/1w, gp-0x6ac0 26r/4w (ALL ld.hu/st.h -> UNSIGNED halfword)")
    print(f"    control path: 0x{REPOINT_BYTE:05X}=0x{v67[REPOINT_BYTE]:02X}  "
          f"0x{ARM_ADDR:05X}={u16(v67, ARM_ADDR)}  sar "
          + "  ".join(f"0x{a:05X}=0x{u16(v67, a):04X}" for a, _ in SAR_SITES_STOCK))

    # ---- ★★ the on-car gate validation V67 rests on, re-asserted because V68 carries the gate ----
    print("\n  ★★ V67's gate validation is CARRIED, and re-checked rather than quoted:")
    pol = V67.assert_v57_probe_polarity("V68")
    val = V67.assert_gate_validation("V68")
    if pol:
        print("    V57's `bne` polarity byte re-read from the FLOWN V57 image                 PASS")
    if val:
        for route, v in val.items():
            print(f"    {route.replace('_cache_r', 'route '):>10s} {v['frames']:>8d} frames  "
                  f"{v['agreement_pct']:>7.3f}% agreement  duty {v['duty_pct']:>5.2f}%  "
                  f"{v['transitions_per_s']:.4f} transitions/s")
    print("    ⇒ and route 47 re-measured it end-to-end: bit6 == carControl.latActive in")
    print("      150,302 / 150,327 frames (99.983%) over 26 segments, the 25 disagreements all")
    print("      single-frame transition edges. bit6 is carried unchanged to keep measuring it.")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v67)

    # ---- THE ONLY EDIT: replace the cave payload --------------------------------------------------
    print(f"\n  THE ONLY EDIT -- replace V67's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v67[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V67's -- same cave base, same jarl"
    assert_probe_sites(code, "V68")
    assert_signal_sites(code, "V68")
    assert_cell_census(bytes(code), "V68")
    V67.scan_self_check(bytes(code), "V68", repointed=True)

    # ---- 🛑 THE CORE CLAIM: the control path is V67's, byte for byte -----------------------------
    print("\n  🛑 CONTROL PATH -- asserted byte-identical to V67, not summarised:")
    assert_control_path(code, v67, "V68")
    print(f"    0x{REPOINT_BYTE:05X} = 0x{code[REPOINT_BYTE]:02X}   the V67 repoint "
          f"(ld.bu -0x6806[gp],r15 @0x{REPOINT_ADDR:05X})")
    print(f"    0x{ARM_ADDR:05X} = {u16(code, ARM_ADDR):<6d} r24's LKAS arm")
    print(f"    0x{ARM_671A_ADDR:05X} = {u16(code, ARM_671A_ADDR):<6d} 0x{ARM_671D_ADDR:05X} = "
          f"{u16(code, ARM_671D_ADDR):<6d} 0x{R26_ARM_ADDR:05X} = {u16(code, R26_ARM_ADDR):<6d} "
          "(all stock)")
    print("    sar  " + "   ".join(f"0x{a:05X} = 0x{u16(code, a):04X}" for a, _ in SAR_SITES_STOCK)
          + "   ALL STOCK")
    for rec, (xs, ys) in zip(GAIN_B_RECORDS, V66.GAIN_B_EXPECT):
        print(f"    gain_B 0x{rec:05X}  X{xs}  Y{ys}   identical to V67")
    print(f"    0xD2000 block, 0x{V53.LOCKOUT_ADDR:05X} = {u16(code, V53.LOCKOUT_ADDR)}, "
          f"0x{V57.PRIVATE_ADDR:05X} = {u16(code, V57.PRIVATE_ADDR)}   all carried")

    # ---- MACHINE PROOF: the CAL block is byte-identical to V67's ---------------------------------
    cal_d = [i for i in range(CAL_BLOCK[0], CAL_BLOCK[1]) if code[i] != v67[i]]
    assert cal_d == [], \
        f"the CAL block differs from V67's at {[hex(x) for x in cal_d]} -- V68 must not touch calibration"
    print(f"    ⇒ the ENTIRE CAL block [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X}) is byte-identical to "
          "V67's: 0 differing bytes")

    # ---- GATES ------------------------------------------------------------------------------------
    print("\n  GATES on the built image (each re-derived, not inherited):")
    n_store = sum(1 for _, raw, _ in CAVE_LISTING if len(raw) >= 4
                  and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B))
    print(f"    GATE 1  cave stores = {n_store} (the CAN-330 payload byte only); NO RAM cell is")
    print("            claimed and no store is added                                       PASS")
    print("    GATE 2  NOT ENGAGED -- V68 changes no control path (CAL block 0 bytes differ) PASS")
    print("    census (TWO decoders, on the OUTPUT):")
    for disp in (GATE_DISP, DEAD_DISP, MASK_DISP, ARM3_DISP, RATE_DISP):
        hits = V64.gp_access_census(bytes(code), disp)
        span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
        fw = [h for h in hits if h[0] not in span]
        r = len([h for h in fw if h[1] in _READ_MNEM])
        cv = [f"{hex(h[0])} {h[1]}" for h in hits if h[0] in span]
        note = {DEAD_DISP: "  *** UNREFERENCED image-wide -- the best free-RAM candidate, UNUSED",
                ARM3_DISP: "  (V67's bit4; V68 stops probing it -- it read 0.000% on route 47)",
                RATE_DISP: "  *** V68's NEW bit4 -- the LERP inner axis"}.get(disp, "")
        print(f"      gp-0x{disp:04x}  {r:2d}r / {len(fw) - r:2d}w firmware, cave "
              f"{cv or 'none'}{note}")

    # ---- CRC. ONLY the MAIN block moves: V68 edits code and no calibration. -----------------------
    for a, what, blk in ((CAVE_BASE, "cave base", MAIN_BLOCK),
                         (CAVE_BASE + len(V55.CAVE_BYTES) - 1, "cave last byte", MAIN_BLOCK)):
        assert V53.owning_block(code, a) == blk, \
            f"{what} 0x{a:05X} is not in the expected CRC block {[hex(x) for x in blk]}"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        moved = old_crc != new_crc
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({'RECOMPUTED' if moved else 'unchanged'})")
        if block == MAIN_BLOCK:
            assert moved, "the MAIN CRC did not move, but the cave did"
        else:
            assert not moved, "the CAL CRC MOVED -- V68 must not touch calibration"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    allowed = cave_span | main_crc

    d67 = [i for i in range(0x13000, 0x100000) if code[i] != v67[i]]
    stray = [i for i in d67 if i not in allowed]
    assert not stray, \
        f"V68 differs from V67 outside the cave + the MAIN CRC: {[hex(x) for x in stray[:16]]}"
    assert main_crc <= set(d67), "the MAIN CRC trailer did not move"
    n_cave = len([i for i in d67 if i in cave_span])
    print(f"\n  V68 vs V67: {len(d67)} bytes  ({n_cave} cave + 4 MAIN CRC).  ZERO bytes outside "
          "the cave span")
    print("    EXACT byte list within the cave span:")
    for i in sorted(i for i in d67 if i in cave_span):
        print(f"      0x{i:05X}  0x{v67[i]:02X} -> 0x{code[i]:02X}")
    print(f"    MAIN CRC 0x{MAIN_BLOCK[1]:05X}: 4 bytes")
    print(f"    ⇒ no calibration byte moved; the CAL CRC 0x{CAL_BLOCK[1]:05X} is unchanged, which is")
    print("      itself the proof that V68's control path is V67's.")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V68 vs V38 baseline: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V68")
    assert walk(bytes(code), label="V68") == 0
    assert walk_all_blocks(bytes(code), label="V68") == 0
    assert_probe_sites(code, "V68")
    assert_signal_sites(code, "V68")
    assert_control_path(code, v67, "V68")

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the READBACK ------------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V68 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V68 readback")
    assert walk(bytes(readback), label="V68 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V68 readback") == 0
    assert_probe_sites(readback, "V68 readback")
    assert_signal_sites(readback, "V68 readback")
    assert_cell_census(bytes(readback), "V68 readback")
    V67.scan_self_check(bytes(readback), "V68 readback", repointed=True)
    assert_control_path(readback, v67, "V68 readback")
    assert bytes(readback[0x13000:0x100000]) == bytes(code[0x13000:0x100000]), \
        "the readback differs from the built image inside the flashed span"

    # re-decode the cave FROM THE READBACK, instruction by instruction, against the listing
    print("\n  cave re-decoded from the READBACK (not from what we meant to write):")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)

    print("\n  cell loads re-decoded from the READBACK by scan_gp_accesses (the hw1-bit-5 guard):")
    print(f"    {'site':>9s}  {'bytes':<10s} {'cell':<12s} {'disp':<8s} {'parity':<7s} {'op':<6s} "
          f"{'bit':<5s} {'test':<12s} provenance")
    for disp, bit, name, kind, lvl, _why in CELLS:
        a, want_mnem = CAVE_CELL_READS[disp]
        raw = bytes(readback[a:a + 4])
        mnem, got, reg1, reg2 = decode_load(raw)
        assert (mnem, got, reg1, reg2) == (want_mnem, disp, GP, R6), \
            f"{name}: readback @0x{a:05X} decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
        d16 = (0x10000 - disp) & 0xFFFF
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        prov = "4 byte-identical instances" if kind == KIND_HWORD else "byte-identical instance"
        print(f"    0x{a:05X}  {raw.hex():<10s} gp-0x{disp:04x}    0x{d16:04X}   "
              f"{'ODD' if d16 & 1 else 'EVEN':<7s} 0x{op:02X}   bit{bit.bit_length() - 1}  "
              f">= {lvl:<9d} {prov}")
    print("    ⚠ the new rung's `movea -0x190,r6,r6` has NO byte-identical instance. Its hw1 "
          f"({PIN_MOVEA_R6_R6_HW1[0].hex()} = opcode + BOTH register fields) is byte-identical at")
    print("      " + ", ".join(f"0x{a:05X}" for a in PIN_MOVEA_R6_R6_HW1[1]) + ";")
    print("      only the 16-bit IMMEDIATE is ours, and the negative-imm16 sign-extension it relies")
    print("      on is demonstrated by the hook's own displaced `movea -0x1518,gp,r6`.")

    print("\n  the CONTROL PATH, read back:")
    raw = bytes(readback[REPOINT_ADDR:REPOINT_ADDR + 4])
    mnem, got, reg1, reg2 = decode_load(raw)
    print(f"    0x{REPOINT_ADDR:05X}  {raw.hex()}  {mnem} -0x{got:04x}[r{reg1}],r{reg2}   "
          "(V67's repoint, carried)")
    print(f"    0x{ARM_ADDR:05X}  {u16(readback, ARM_ADDR)}   r24's LKAS arm (V67's, carried)")
    for addr, want in SAR_SITES_STOCK:
        print(f"    0x{addr:05X}  0x{u16(readback, addr):04X}  STOCK sar")

    print(f"\n  ★ WHAT bit4 DECIDES, computed from the image's own gain_B records:")
    sc = int(7.2 * 64.0625)
    for rc in (0, 200, 399, RATE_BREAKPOINT, 603, 1000, RATE_FOLD):
        g = EX.r24_gain_q10(sc, rc, 0, 0, 0)
        seg = "FLAT (bit4=0)" if rc < RATE_BREAKPOINT else \
              ("FOLDED->flat (bit4=1)" if rc >= RATE_FOLD else "SLOPED (bit4=1)")
        print(f"    gp-0x6ac0 = {rc:>5d} counts = {rc / EX.RATE_COUNTS_PER_DEGS:>7.1f} deg/s   "
              f"LERP {g:>5d}   {seg}")
    print(f"    ⇒ if bit4 reads ~0%, the operating point is INSIDE the flat segment, the LERP is a")
    print(f"      constant {FLAT_LERP}, and V67's arm of {ARM_VALUE} is delivering "
          f"{ARM_VALUE / FLAT_LERP:.3f}x -- not the 2.000x")
    print(f"      its docstring claims. The arm for exactly 2.00x would then be "
          f"{ARM_FOR_2X_IF_FLAT}, a one-halfword cal edit.")
    print(f"    ⇒ if bit4 reads substantially > 0%, the rate axis IS live and this lane can be")
    print("      calibrated on wheel rate. Either answer closes the question.")

    ok = assert_decoder_matches(CAVE_BYTES, "V68")
    print(f"\n  decoder link: rlog-tools/decode_v68_probe.py CAVE_HEX "
          f"{'MATCHES the built image' if ok else 'NOT CHECKED'}")

    print("\n  PROBE: 0x14A byte4  bit7 = LIVENESS (constant 1)")
    for disp, bit, name, kind, lvl, why in CELLS:
        print(f"                      bit{bit.bit_length() - 1} = gp-0x{disp:04x} >= {lvl:<5d} "
              f"{name:11s} {why}")
    print("                      bit3 = 1  *** THE V68 BUILD-CLASS MARKER *** (constant)")
    print("                      bits 2:0 = stock STEER_SENSOR_STATUS, preserved")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("  ★★ V68 NEVER EMITS 0x87. Every legal frame carries bit7 AND bit3, which no prior build")
    print("     with a probe can produce -- V53/V54 clear bit7, V59/V62/V65 all emit 0x87, and")
    print("     V66/V67 never set bit3. The four-way 0x87 ambiguity does not apply to this build.")
    print("     ⚠ It EXCLUDES every prior build; it cannot exclude a future one. Confirm the .rwd.")
    print("  🛑 WHAT EACH BIT CAN AND CANNOT DISTINGUISH:")
    print("     bit6 CAN: engagement duty, transitions/s, and whether the gate ever toggles in the")
    print("               15-60 Hz kill band (aliased above ~50 Hz -- the tool says so).")
    print("          CANNOT: tell an inert gate from a mis-timed one within a single 10 ms frame.")
    print("     bit5 CAN: prove or refute that gp-0x671d ever pins the gain BELOW stock on a long,")
    print("               mixed drive. Route 47's 0.000% is one drive, not a clearance.")
    print("          CANNOT: say what would set it -- only that it did.")
    print("     bit4 CAN: settle which side of the LERP's first breakpoint the car operates on, and")
    print("               therefore whether V67's arm is 2.00x or 1.94x and whether this lane can")
    print("               ever be tuned on wheel rate.")
    print(f"          CANNOT: separate 'sloped' from 'folded past {RATE_FOLD}' "
          f"(= {RATE_FOLD / EX.RATE_COUNTS_PER_DEGS:.0f} deg/s, implausible")
    print("               but not ruled out), and it is a TX-time sample, so it is a DISTRIBUTION")
    print("               statistic, not a per-tick correlate of the gain.")
    print("     NOTHING HERE CAN: see above ~50 Hz. CAN is a 100.5 Hz grid and the cave writes into")
    print("               a 100 Hz frame. The aliasing barrier is NOT broken by V68 -- see the")
    print("               docstring for why the sticky rung was rejected on budget, selectivity")
    print("               and the missing clear event, all three.")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is")
    print("        unmeasurable. Long drive, mixed: highway engaged, city manual, parking-lot creep.")
    print("     Condition on carControl.latActive or 0x18F byte4 bit3, NEVER carState.cruiseState.")
    print("     Decode with rlog-tools/decode_v68_probe.py.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
