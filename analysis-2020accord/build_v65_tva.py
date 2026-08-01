#!/usr/bin/env python3
"""build_v65_tva.py -- V65 = V62, byte-identical in every control path, + a 4-LEVEL SATURATION LADDER.

WHAT V65 IS
-----------
V65 carries V62's two `sar` immediates unchanged and swaps ONLY the cave payload:

    0x3AC20  a942   sar 0x9,r8    r24 lane: (dtorque * gain_B) >> 9      (V62, carried verbatim)
    0x3AB76  a932   sar 0x9,r6    r26 lane: (stage1  * gain_A) >> 9      (V62, carried verbatim)
    0x3AB70  aa32   sar 0xa,r6    DELIBERATELY LEFT -- editing it puts a mul operand at 94% of INT32_MAX

NO calibration byte moves. The CAL block is asserted byte-identical to V62's and its CRC word is
asserted UNCHANGED -- machine proof, printed on every build. The only bytes that differ from V62 are
the cave span and the MAIN block CRC trailer.

THE QUESTION -- is the aggregator RAILING during the ratchet, and is it CLIPPED or merely LARGE?
----------------------------------------------------------------------------------------------------
FUN_0003aa2c sums ten lanes and hard-clips the total to +/-10240 into `gp-0x6b94`. Byte-confirmed
from the image and Ghidra-confirmed as one contiguous instruction stream, 0x3ACE8-0x3AD27:

    0x3ACE8  addi  -0x2800,r10,r0     ; flags = sum - 10240
    0x3ACEC  ld.h  -0x6b94[gp],r13    ; the lockstep read-back
    0x3ACF0  ble   0x3AD04            ; <= +10240 -> no positive clamp
    0x3ACF6  movea 0x2800,r0,r12      ; r12 = +10240
    0x3ACFA  st.h  r12,-0x6b94[gp]    ; *** POSITIVE RAIL ***   (+ shadow st.h to gp-0x4ce0)
    0x3AD04  addi  0x2800,r10,r0      ; flags = sum + 10240
    0x3AD08  bge   0x3AD1C            ; >= -10240 -> no negative clamp
    0x3AD0E  movea -0x2800,r0,r12     ; r12 = -10240
    0x3AD12  st.h  r12,-0x6b94[gp]    ; *** NEGATIVE RAIL ***   (+ shadow st.h to gp-0x4ce0)
    0x3AD20  st.h  r10,-0x6b94[gp]    ; the unsaturated path    (+ shadow st.h to gp-0x4ce0)

If the ~7 Hz ratchet is a rail-to-rail limit cycle in that sum, the aggregator is bouncing between
+10240 and -10240 and the lever is LOOP GAIN UPSTREAM, not any damper downstream. If it never goes
near either rail, the nonlinearity lives past the aggregator, in the motor/FOC path. Nothing in this
kit has ever measured that, and every damper lever so far has been aimed downstream of it.

THE PROBE -- CAN 0x14A byte4, 100 Hz, bits 7:3 (bits 2:0 stay stock STEER_SENSOR_STATUS)
-----------------------------------------------------------------------------------------
A SYMMETRIC FOUR-LEVEL LADDER on one signal, from ONE load and ONE shift:

    bit7 = 1                        LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x6b94 >= +8192       *** POSITIVE RAIL ***  (80% of the +10240 clip)
    bit5 = gp-0x6b94 >= +4096       positive, large        (40%)
    bit4 = gp-0x6b94 <= -4097       negative, large        (40%)
    bit3 = gp-0x6b94 <= -8193       *** NEGATIVE RAIL ***  (80%)

WHY `sar 0xc` GIVES ALL FOUR FROM ONE REGISTER, AND WHY THE SYMMETRY MATTERS
----------------------------------------------------------------------------
`sar 0xc` is an arithmetic >>12. On the clamped range [-10240,+10240] it produces exactly [-3,+2]:

    r6 >= +2  <=>  v >= +8192      r6 <= -2  <=>  v <= -4097
    r6 >= +1  <=>  v >= +4096      r6 <= -3  <=>  v <= -8193

Four levels, four 2-byte compares, one 2-byte shift. Each level pair is symmetric to within ONE count
(+8192/-8193 and +4096/-4097). That symmetry is load-bearing: an asymmetric pair would manufacture a
"more negative rail than positive" reading out of the encoding alone, and the kit would have no way to
separate that artefact from a real DC bias in the sum. The exhaustive wire-model self-check below walks
all 20,481 values in [-10240,+10240] and asserts every boundary and every bucket width exactly.

WHAT THE INNER PAIR BUYS OVER A BARE RAIL TEST
-----------------------------------------------
bit5/bit4 separate "the sum is BIG" from "the sum is CLIPPED". A large-but-unclipped oscillation and a
clipped one look identical to a rail-only probe, and they call for opposite next moves: the first is a
linear gain problem, the second means every downstream lever is describing-function-irrelevant because
the loop is running against a hard nonlinearity. That distinction is the whole reason the waveform's
symmetry mattered in the first place.

THREE STRUCTURAL INVARIANTS -- the decoder can DETECT a wrong build, not merely find it plausible
--------------------------------------------------------------------------------------------------
    bit6 => bit5                            >= +8192 implies >= +4096
    bit3 => bit4                            <= -8193 implies <= -4097
    NOT ((bit6|bit5) AND (bit4|bit3))       one value cannot be both positive and negative

The third is the discriminator against V59 and V64, both of which routinely set bits from "both sides"
in the same frame. This is V59's own proven thermometer pattern, turned into a two-sided ladder. Only
FIVE payload values are reachable at all, which the builder asserts and the decoder checks against.

WHAT WAS DROPPED FROM THE FIRST V65 DRAFT, AND WHY -- keep this, it is a real finding
--------------------------------------------------------------------------------------
The first draft spent bit6/bit3 on `gp-0x67ac`, the nine-lane suppression latch. It was dropped because
that cell is STRUCTURALLY PINNED AT 0 on this ROM, so both bits were predicted-constant and the drive
would have spent 2 of 5 bits on a foregone conclusion -- the V64 mistake one build later. Verified
first-hand, and recorded here because the finding outlives the draft:

  * gp-0x67ac has TWO ld.bu readers -- `...,r8` @0x3AA34 (the one functional consumer) and `...,r15`
    @0x2772A (the lockstep self-comparison) -- and ONE writer, `st.b r8` @0x2773A.
  * That writer is lockstep-shadowed (pair gp-0x4c37, mismatch calls FUN_0006b9fa). Its value comes
    from gp-0x3d98, staged by `st.w r22` @0x27314 (census: exactly one writer, one reader).
  * FUN_00026c80's accumulation loop computes gp-0x3d98 as a STICKY OR over the 11 sources of
        (source_type gp-0x61a0[i] IN {2,3,4})  AND  (gp-0x617c[i] != 0)
  * cal 0xC4124 reads (0,0,5,0,5,5,0,0,0,5,0) -- no element is in {2,3,4}, so the fold can never
    produce 1. [INHERITED] the gp-0x61a0 <- 0xC4124 link: gp-0x61a0 has ZERO fixed-displacement
    accesses image-wide, so it is reached only through computed pointers and a displacement scan is
    structurally blind to its writer. Matches the guards in build_v39/v40/v41 and build_vfourframe.
  ⚠ gp-0x67ab is a REAL adjacent cell -- the other fold result, stored at 0x2773E. Encoding -0x67ac
    with the odd-displacement opcode would silently have read it instead. See the ld.bu note below.

⚠ A CONSTANT 0x87 IS AMBIGUOUS WITH V64 AND THE DECODER STOPS ON IT
-------------------------------------------------------------------
V64 read a constant 0x87 for all 14,980 frames. Under V65, 0x87 is the NEUTRAL bucket -- "cave fired,
sum never past +/-4096" -- a LEGITIMATE reading, and byte-identical to V64's null. The decoder cannot
tell them apart from the payload alone and says so instead of guessing. Confirm which .rwd is on the
car before reading any verdict. That trap has already cost this kit one session.

PRE-COMMITTED INTERPRETATION -- written before the drive, so it cannot be fitted afterwards
--------------------------------------------------------------------------------------------
    bit6 <-> bit3 ALTERNATING at ~7 Hz  (i.e. ~14 alternations/s)
        => the aggregator is RAIL-TO-RAIL and CLIPPED. The lever is LOOP GAIN UPSTREAM, not damping
           downstream. Next: r24's gain_B breakpoints at 0xD2AEC (the MODE-10 record; 0xD6AEC is mode
           22's byte-identical but SEPARATE record, not a redundancy mirror -- see build_v62_tva.py).
           It also re-reads the null run from V39 onward as "aimed past the clip".
    bit5 <-> bit4 alternating but bit6/bit3 quiet
        => a LARGE oscillation that is NOT clipping. Linear-regime problem; the damper lanes are still
           in play and a gain change will behave predictably. Do NOT jump to the gain_B breakpoints.
    all four quiet
        => the nonlinearity is DOWNSTREAM of the aggregator, in the motor/FOC path. Every lane lever
           inside FUN_0003aa2c is aimed at the wrong side of the clip. Next target: gp-0x6b98 (the
           merged motor command, V55's probe) and the FOC current loop -- NOT another lane gain.
    a rail bit set with its partner half-bit clear, or bits from both sides in one frame
        => DECODE ERROR, not a reading. The build on the car is not V65.

CAVE DISCIPLINE -- caves are this kit's ONLY bricking class (V24, V27, V48B)
----------------------------------------------------------------------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte proven extent as V55/V57/V58/V59/V64 -- all five
flew clean. Read-only; r6/r7 only; the sole write is the existing CAN-330 payload byte gp-0x1514 with
bits 2:0 preserved, so GATE 1 stays VACUOUS and no new RAM cell is claimed. 62 of 68 bytes used.

ENCODER PROVENANCE -- every encoder pinned to a Ghidra-BOUNDARY-CONFIRMED real instruction
--------------------------------------------------------------------------------------------
BYTE-IDENTICAL to what this cave emits, register field included:

    ld.h -0x6b94[gp],r6   24376c94  @0x453E0  `ld.h -0x6b94, gp, r6`   the firmware's own read
    sar  0xc,r6           ac32      @0x2C0BA  `sar 0xc, r6`
    cmp  0x2,r6           6232      @0x19304  `cmp 0x2, r6`  -- and it is a BRANCH TARGET (reached
                                     from 0x192DA / 0x192E0 / 0x192EC), the strongest boundary
                                     evidence available short of executing it
    cmp  0x1,r6           6132      @0x14D46  (second instance @0x192E2)
    blt  +6               b605      @0x1C006  `blt 0x0001c00c`   same +6 displacement
    bgt  +6               bf05      @0x279FC  `bgt 0x00027a02`   same +6 displacement
    ld.h -0x6b94[gp],r13  246f6c94  @0x3ACEC  second donor, same cell, reg2 differs only

`cmp -0x2,r6` (7e32) and `cmp -0x3,r6` (7d32) have NO byte occurrence anywhere in the image, so each is
pinned by a THREE-WAY field decomposition, every part Ghidra-boundary-confirmed:

    op 0x13 + reg2 r6 + NEGATIVE imm5 : `cmp -0x1,r6`  7f32  @0x1BC24
    op 0x13 + reg2 r6 + positive imm5 : `cmp 0x2,r6`   6232  @0x19304
    Format II imm5 field 0x1E == -2   : `mov -0x2,r8`  1e42  @0x50A12  (and @0x18B1C)
    Format II imm5 field 0x1D == -3   : `mov -0x3,r8`  1d42  @0x18B32
The two `mov` pins sit in the identical compiler idiom (`bne / mov -N,r8 / and r8,r28 / br` against an
`ori` on the other arm -- a clear-bit/set-bit pair), which is why both immediates exist at all.

🛑 A BYTE SCAN IS NOT CONFIRMATION. Chasing these pins produced FIVE Format-V aliasing false positives:
   `cmp -0x2,rN` at 0x1A278 (inside `mov 0x1a27e,lp`), 0x2806A (inside a `jarl`), 0x4C12A (inside a
   `dispose`), 0x55FC6 (inside a `jarl`); and `bgt` at 0x1BA28 (inside a `dispose`). Every candidate
   used below was decoded from a function entry or a self-synchronising window and checked to sit on a
   real instruction boundary. `mov -0x3,r6` 1d32 @0x15B6E exists in the bytes but its boundary was NOT
   confirmed, so it is deliberately NOT cited as a pin.

⚠ ONE ENCODING READING CORRECTED, recorded because the opposite was proposed and would mis-encode:
  V850 carries an ld.bu/ld.hu displacement's bit 0 in the OPCODE, i.e. in **hw1 bit 5**; hw2's LSB is
  the WIDTH selector and is always 1. On an `ld.h` (opcode 0x39) hw1 bit 5 is merely the opcode's low
  bit and carries NO displacement meaning -- reading it as one there is the mirror-image error.

BASE = V62. V61's tap kill and V63's raised arms are both asserted ABSENT.

Decoder: rlog-tools/decode_v65_saturation.py
"""
import hashlib
import os
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
import build_v64_tva as V64                # noqa: E402  (census helper only -- V63's cals are NOT here)

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged from V55/V57/V58/V59/V64
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- the ONE cell ---------------------------------------------------------------------------------
SUM_DISP = 0x6B94           # SIGNED halfword, the aggregator output, hard-clipped to +/-10240
SUM_CLAMP = 10240           # 0x2800 -- Ghidra-confirmed at 0x3ACF6 / 0x3AD0E
SUM_SHIFT = 12              # sar 0xc: [-10240,+10240] -> [-3,+2]

# The four ladder levels, as COMPARED VALUES after the shift. Thresholds are derived, never hardcoded.
L_POS_RAIL = 2              # r6 >= +2  <=>  v >= +8192
L_POS_HALF = 1              # r6 >= +1  <=>  v >= +4096
L_NEG_HALF = -2             # r6 <= -2  <=>  v <= -4097
L_NEG_RAIL = -3             # r6 <= -3  <=>  v <= -8193


def ge_threshold(level):
    """The smallest aggregator value for which `(v >> SUM_SHIFT) >= level`."""
    return level << SUM_SHIFT


def le_threshold(level):
    """The largest aggregator value for which `(v >> SUM_SHIFT) <= level`."""
    return ((level + 1) << SUM_SHIFT) - 1


# ---- producer / consumer sites, all byte-pinned in assert_signal_sites() --------------------------
SUM_REAL_LDH = 0x453E0          # ld.h -0x6b94,gp,r6 -- BYTE-IDENTICAL to what this cave emits
SUM_LDH_R13 = 0x3ACEC           # ld.h -0x6b94,gp,r13 -- the lockstep read-back, second donor
SUM_WRITERS = (0x3ACFA, 0x3AD12, 0x3AD20)

# The clamp itself, Ghidra-confirmed as one contiguous stream. If any of it moves, "+/-10240" stops
# being the rail and every threshold above is void.
CLAMP_CTX = (
    (0x3ACE8, bytes.fromhex("0a0600d8"), "addi -0x2800,r10,r0  ; flags = sum - 10240"),
    (0x3ACEC, bytes.fromhex("246f6c94"), "ld.h -0x6b94[gp],r13 ; the lockstep read-back"),
    (0x3ACF0, bytes.fromhex("a70d"), "ble 0x3AD04          ; <= +10240 -> no positive clamp"),
    (0x3ACF6, bytes.fromhex("20660028"), "movea 0x2800,r0,r12  ; r12 = +10240"),
    (0x3ACFA, bytes.fromhex("64676c94"), "st.h r12,-0x6b94[gp] ; POSITIVE RAIL"),
    (0x3ACFE, bytes.fromhex("646720b3"), "st.h r12,-0x4ce0[gp] ; its lockstep shadow"),
    (0x3AD04, bytes.fromhex("0a060028"), "addi 0x2800,r10,r0   ; flags = sum + 10240"),
    (0x3AD08, bytes.fromhex("ae0d"), "bge 0x3AD1C          ; >= -10240 -> no negative clamp"),
    (0x3AD0E, bytes.fromhex("206600d8"), "movea -0x2800,r0,r12 ; r12 = -10240"),
    (0x3AD12, bytes.fromhex("64676c94"), "st.h r12,-0x6b94[gp] ; NEGATIVE RAIL"),
    (0x3AD16, bytes.fromhex("646720b3"), "st.h r12,-0x4ce0[gp] ; its lockstep shadow"),
    (0x3AD20, bytes.fromhex("64576c94"), "st.h r10,-0x6b94[gp] ; unsaturated path"),
    (0x3AD26, bytes.fromhex("646720b3"), "st.h r12,-0x4ce0[gp] ; its lockstep shadow"),
)

# ---- encoder pins. Every one Ghidra-BOUNDARY-confirmed this session (see docstring). --------------
PIN_LDH_6B94_R6 = (SUM_REAL_LDH, bytes.fromhex("24376c94"))       # BYTE-IDENTICAL to ours
PIN_LDH_6B94_R13 = (SUM_LDH_R13, bytes.fromhex("246f6c94"))       # same cell, reg2 = r13
PIN_SAR_C_R6 = (0x2C0BA, bytes.fromhex("ac32"), 12, R6)           # BYTE-IDENTICAL to ours
PIN_SAR_A_R6 = (0x3AB70, bytes.fromhex("aa32"), 10, R6)           # the site V62 must NOT move
PIN_CMP_P2_R6 = (0x19304, bytes.fromhex("6232"), 2, R6)           # BYTE-IDENTICAL, and a branch target
PIN_CMP_P1_R6 = (0x14D46, bytes.fromhex("6132"), 1, R6)           # BYTE-IDENTICAL
PIN_CMP_M1_R6 = (0x1BC24, bytes.fromhex("7f32"), -1, R6)          # negative imm5 with reg2 = r6
PIN_MOVI5_M2_R8 = (0x50A12, bytes.fromhex("1e42"), -2, 8)         # imm5 field 0x1E == -2
PIN_MOVI5_M3_R8 = (0x18B32, bytes.fromhex("1d42"), -3, 8)         # imm5 field 0x1D == -3
PIN_BLT6 = (0x1C006, bytes.fromhex("b605"))
PIN_BGT6 = (0x279FC, bytes.fromhex("bf05"))

BIT_LIVE = 0x80
BIT_POS_RAIL, BIT_POS_HALF, BIT_NEG_HALF, BIT_NEG_RAIL = 0x40, 0x20, 0x10, 0x08

COND_BLT = 0x6              # SIGNED <   -- pinned to the real `blt` @0x1C006
COND_BGT = 0xF              # SIGNED >   -- pinned to the real `bgt` @0x279FC

# (compared level, bit, branch condition, label name) -- the ladder, in emission order.
LADDER = ((L_POS_RAIL, BIT_POS_RAIL, COND_BLT, "p_hi"),
          (L_POS_HALF, BIT_POS_HALF, COND_BLT, "p_lo"),
          (L_NEG_HALF, BIT_NEG_HALF, COND_BGT, "n_lo"),
          (L_NEG_RAIL, BIT_NEG_RAIL, COND_BGT, "n_hi"))

TAG = "LKAS-4x-mss0-decouple0xC646C-ratelane2x-satladder4-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V65-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v65_plain_image.bin"))
V62_BIN = str(plain_image_path("_v62_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def decode_fmt2(halfword):
    """V850 Format-II split: imm5 = bits[4:0] (SIGNED), opcode = bits[10:5], reg2 = bits[15:11]."""
    imm = halfword & 0x1F
    return {"imm5": imm - 32 if imm & 0x10 else imm,
            "imm_field": imm,
            "opcode": (halfword >> 5) & 0x3F,
            "reg2": (halfword >> 11) & 0x1F}


# =======================================================================================================
# Encoders -- every one inherited and self-checked, or pinned to a real instance above.
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V59._self_check_encoders()          # inherits V58/V57/V55/V54/FF self-checks

    # ---- ld.h -0x6b94[gp],r6 -- BYTE-IDENTICAL to the firmware's own read @0x453E0. The strongest
    # pin available, and the one that matters most: the cell is SIGNED and an ld.hu would turn every
    # negative sample into a huge positive one, deleting the whole negative half of the ladder.
    ours = V55.ldh(SUM_DISP, R6)
    assert ours == PIN_LDH_6B94_R6[1], \
        f"ld.h -0x6b94[gp],r6 must be byte-identical to the real instance @0x{SUM_REAL_LDH:05X}"
    assert struct.unpack_from("<H", ours, 2)[0] & 1 == 0, \
        "ld.h hw2 LSB must be CLEAR -- LSB set is the ld.w/ld.hu form"
    assert struct.unpack_from("<H", ours, 2)[0] == (0x10000 - SUM_DISP) & 0xFFFF, \
        "ld.h displacement halfword is not the two's complement of the gp offset"
    # 🛑 OPCODE FIELD BY VALUE. A one-bit slip from 0x39 to 0x3B turns this READ into an st.h -- a
    # WRITE straight into the aggregator output, in the 1 kHz control path. Checked explicitly, and
    # against both forms it could plausibly collapse onto.
    hw_ours = struct.unpack("<H", ours[:2])[0]
    assert ((hw_ours >> 5) & 0x3F) == 0x39, \
        f"the emitted ld.h opcode field is 0x{(hw_ours >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h)"
    assert ((hw_ours >> 5) & 0x3F) != 0x3B, "opcode 0x3B is st.h -- that would WRITE the aggregator"
    assert ((hw_ours >> 5) & 0x3F) != 0x3F, "opcode 0x3F is ld.hu -- an UNSIGNED read"
    assert ours != FF.stb(R6, -SUM_DISP, GP) and ours[:2] != FF.sth(R6, -SUM_DISP, GP)[:2], \
        "the emitted ld.h shares an opcode field with a STORE"
    assert ours != FF.ldhu(SUM_DISP, R6), \
        "ld.h collapsed onto ld.hu -- the sign of the aggregator output would be lost"
    # a SECOND real donor for the same cell at a different reg2: only the reg2 field may differ
    hw_r13 = struct.unpack("<H", PIN_LDH_6B94_R13[1][:2])[0]
    assert ours[2:] == PIN_LDH_6B94_R13[1][2:], "the r13 donor @0x3ACEC carries a different hw2"
    assert (hw_ours & 0x07FF) == (hw_r13 & 0x07FF), \
        "the r13 donor @0x3ACEC differs from ours in more than the reg2 field"
    assert (hw_r13 >> 11) == 13 and (hw_ours >> 11) == R6, "donor/emitted reg2 fields are not as read"

    # ---- gp IS r4 on this firmware. Every gp-relative instruction we emit must carry reg1 = 4.
    assert GP == 4, f"GP is r{GP}; every real gp-relative instance in this image carries reg1 = r4"
    for raw, what in ((V55.ldh(SUM_DISP, R6), "ld.h gp-0x6b94"),
                      (V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu gp-0x1514"),
                      (FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b gp-0x1514")):
        assert struct.unpack("<H", raw[:2])[0] & 0x1F == 4, f"{what}: reg1 field is not r4 (gp)"
    for addr, raw in (PIN_LDH_6B94_R6, PIN_LDH_6B94_R13):
        assert struct.unpack("<H", raw[:2])[0] & 0x1F == 4, \
            f"the donor @0x{addr:05X} does not carry reg1 = r4 -- gp is not r4 after all"

    # ---- sar 0xc,r6 -- BYTE-IDENTICAL to the real instance @0x2C0BA, reg2 included.
    ours = V55.sar(SUM_SHIFT, R6)
    assert ours == PIN_SAR_C_R6[1], \
        f"sar 0xc,r6 must be byte-identical to the real instance @0x{PIN_SAR_C_R6[0]:05X}"
    for addr, raw, imm, reg2 in (PIN_SAR_C_R6, PIN_SAR_A_R6):
        assert V55.sar(imm, reg2) == raw, f"sar({imm},r{reg2}) fails the real instance @0x{addr:05X}"
    f = decode_fmt2(struct.unpack("<H", ours)[0])
    assert f["opcode"] == 0x15 and f["reg2"] == R6 and f["imm_field"] == SUM_SHIFT, \
        f"sar 0xc,r6 decodes as {f}"
    # 🛑 ARITHMETIC, not logical. shr would map every negative sum to a huge positive one and the two
    # negative levels could never be reached at all.
    assert ours != FF.shr(SUM_SHIFT, R6), "sar collapsed onto shr (logical) -- the sign would be lost"
    assert V55.sar(SUM_SHIFT, R6) != V55.sar(SUM_SHIFT - 1, R6), "sar ignores its immediate"

    # ---- cmp imm5,reg2. The two POSITIVE levels are byte-identical to real instances; the two
    # NEGATIVE ones have no byte occurrence image-wide and are pinned by field decomposition.
    for addr, raw, imm, reg2 in (PIN_CMP_P2_R6, PIN_CMP_P1_R6, PIN_CMP_M1_R6):
        assert V55.cmp_imm5(imm, reg2) == raw, \
            f"cmp_imm5({imm},r{reg2}) fails the real instance @0x{addr:05X}"
    for addr, raw, imm, reg2 in (PIN_MOVI5_M2_R8, PIN_MOVI5_M3_R8):
        assert FF.movi5(imm, reg2) == raw, \
            f"movi5({imm},r{reg2}) fails the real `mov {imm},r{reg2}` @0x{addr:05X}"
    neg_field_pins = {decode_fmt2(struct.unpack("<H", p[1])[0])["imm_field"]: p
                      for p in (PIN_MOVI5_M2_R8, PIN_MOVI5_M3_R8)}
    reg2_field = decode_fmt2(struct.unpack("<H", PIN_CMP_M1_R6[1])[0])["reg2"]
    for level, _bit, _cond, name in LADDER:
        raw = V55.cmp_imm5(level, R6)
        f = decode_fmt2(struct.unpack("<H", raw)[0])
        assert f["opcode"] == 0x13, f"{name}: `cmp {level},r6` opcode field is not 0x13"
        assert f["reg2"] == R6 == reg2_field, f"{name}: reg2 field is r{f['reg2']}"
        assert f["imm5"] == level, f"{name}: imm5 decodes as {f['imm5']}, expected {level}"
        assert -16 <= level <= 15, f"{name}: Format II imm5 is SIGNED (-16..15)"
        if level < 0:
            # the immediate BIT PATTERN must be one a confirmed real instruction carries
            pin = neg_field_pins.get(f["imm_field"])
            assert pin is not None and pin[2] == level, \
                f"{name}: imm field 0x{f['imm_field']:02X} is not pinned to a confirmed `mov {level},rN`"
    # the four ladder immediates must be distinct and strictly descending
    levels = [lv for lv, _, _, _ in LADDER]
    assert levels == [L_POS_RAIL, L_POS_HALF, L_NEG_HALF, L_NEG_RAIL], "ladder order changed"
    assert levels == sorted(levels, reverse=True) and len(set(levels)) == 4, \
        "the ladder levels are not strictly descending and distinct"
    assert struct.unpack("<H", V55.cmp_imm5(-3, R6))[0] + 1 == \
        struct.unpack("<H", V55.cmp_imm5(-2, R6))[0] == \
        struct.unpack("<H", V55.cmp_imm5(-1, R6))[0] - 1, "cmp_imm5 immediate is not the low 5 bits"
    assert V55.cmp_imm5(L_NEG_RAIL, R6) != V55.cmp_imm5(L_NEG_RAIL, R7), "cmp_imm5 ignores its register"

    # ---- branch conditions. Both are SIGNED, and both are byte-pinned.
    # 🛑 bl (0x1) / bh (0xB) are the UNSIGNED pair and would silently invert every negative test,
    # because a negative aggregator value is a LARGE unsigned one.
    assert COND_BLT == 0x6, f"blt must be condition 6, got {COND_BLT}"
    assert COND_BGT == 0xF, f"bgt must be condition 15, got {COND_BGT}"
    assert COND_BLT != V55.COND_BL and COND_BGT != 0xB, "blt/bgt collapsed onto the UNSIGNED bl/bh"
    assert FF.bcond(COND_BLT, +6) == PIN_BLT6[1], \
        f"blt +6 fails the real `blt 0x1c00c` @0x{PIN_BLT6[0]:05X}"
    assert FF.bcond(COND_BGT, +6) == PIN_BGT6[1], \
        f"bgt +6 fails the real `bgt 0x27a02` @0x{PIN_BGT6[0]:05X}"
    assert COND_BLT != COND_BGT, "the two branch conditions collided"
    for cond in (COND_BLT, COND_BGT):
        assert struct.unpack("<H", FF.bcond(cond, +6))[0] & 0xF == cond, \
            f"bcond does not carry condition {cond} in bits 3:0"
    # each rung must use the condition matching the SIDE it tests: a `>=` rung skips on blt, a `<=`
    # rung skips on bgt. A swap here inverts one rung without changing any byte count.
    for level, _bit, cond, name in LADDER:
        assert cond == (COND_BLT if level > 0 else COND_BGT), \
            f"{name}: level {level} is paired with the wrong branch condition"

    # ---- the four bit-set moveas: V54's flashed reg1=r7 bias form, different immediates.
    for _lv, bit, _c, _n in LADDER:
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"movea 0x{bit:x},r7,r7 malformed"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"

    # ---- the five bits occupy exactly 7:3, and the ladder bits must DESCEND with the level so the
    # wire order matches the physical order (+rail, +half, -half, -rail from bit6 down to bit3).
    bits = (BIT_LIVE,) + tuple(b for _, b, _, _ in LADDER)
    assert len(set(bits)) == 5 and all(b & (b - 1) == 0 for b in bits), "probe bits are not distinct"
    assert sum(bits) == 0xF8, f"probe bits must occupy exactly 7:3, got 0x{sum(bits):02X}"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert [b for _, b, _, _ in LADDER] == sorted((b for _, b, _, _ in LADDER), reverse=True), \
        "the ladder bits are not in descending bit order -- wire order must match physical order"

    # ---- the thresholds must be SYMMETRIC to within one count at BOTH levels, or an encoding
    # artefact would masquerade as a DC bias in the aggregator.
    assert ge_threshold(L_POS_RAIL) == -le_threshold(L_NEG_RAIL) - 1, "rail levels are asymmetric"
    assert ge_threshold(L_POS_HALF) == -le_threshold(L_NEG_HALF) - 1, "half levels are asymmetric"
    assert ge_threshold(L_POS_RAIL) == SUM_CLAMP * 4 // 5, "the rail level is not 80% of the clamp"
    assert ge_threshold(L_POS_HALF) == SUM_CLAMP * 2 // 5, "the half level is not 40% of the clamp"
    # ---- every level must be REACHABLE inside the clamp, or its bit could never set
    assert ge_threshold(L_POS_RAIL) <= SUM_CLAMP and le_threshold(L_NEG_RAIL) >= -SUM_CLAMP, \
        "a ladder level lies outside the clamped range and could never be observed"
    assert (SUM_CLAMP >> SUM_SHIFT) == L_POS_RAIL and (-SUM_CLAMP >> SUM_SHIFT) == L_NEG_RAIL, \
        "sar 0xc does not map the clamp endpoints onto the outer ladder levels"


# =======================================================================================================
# The cave -- 62 bytes of the 68-byte proven extent
# =======================================================================================================

def build_cave():
    """pack_saturation_ladder -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.h  -0x6b94[gp],r6   ; aggregator output, SIGNED halfword, clipped +-10240
        sar   0xc,r6           ; >>12 maps [-10240,+10240] -> [-3,+2]
        cmp   0x2,r6
        blt   +6               ; SIGNED < +2 -> not at the + rail
        movea 0x40,r7,r7       ; bit6 = sum >= +8192   *** POSITIVE RAIL ***
      p_hi:
        cmp   0x1,r6
        blt   +6               ; SIGNED < +1
        movea 0x20,r7,r7       ; bit5 = sum >= +4096
      p_lo:
        cmp   -0x2,r6
        bgt   +6               ; SIGNED > -2
        movea 0x10,r7,r7       ; bit4 = sum <= -4097
      n_lo:
        cmp   -0x3,r6
        bgt   +6               ; SIGNED > -3 -> not at the - rail
        movea 0x8,r7,r7        ; bit3 = sum <= -8193   *** NEGATIVE RAIL ***
      n_hi:
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(BIT_LIVE, R0, R7), "movea 0x80,r0,r7    ; bit7 LIVENESS")
    emit(V55.ldh(SUM_DISP, R6), "ld.h -0x6b94[gp],r6 ; aggregator output (SIGNED)")
    emit(V55.sar(SUM_SHIFT, R6), f"sar 0x{SUM_SHIFT:x},r6            ; arithmetic >>{SUM_SHIFT}")

    rungs = []
    for level, bit, cond, name in LADDER:
        rel, thr = (">=", ge_threshold(level)) if level > 0 else ("<=", le_threshold(level))
        imm = f"0x{level:x}" if level > 0 else f"-0x{-level:x}"
        emit(V55.cmp_imm5(level, R6), f"cmp {imm},r6{'':<{7 - len(imm)}}; level {level:+d}")
        emit(FF.bcond(cond, +6),
             f"{'blt' if cond == COND_BLT else 'bgt'} +6              ; SIGNED skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7{'':<{4 - len(f'{bit:x}')}}; bit{bit.bit_length() - 1} = "
             f"sum {rel} {thr:+d}")
        rungs.append((len(listing) - 2, CAVE_BASE + len(body), name, cond))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2: every branch lands exactly on its label. Located BY POSITION, not by content --
    # the ladder emits `blt +6` twice and `bgt +6` twice, so a content lookup is ambiguous by
    # construction. The rung indices come out of the emission loop, so they cannot drift from it.
    assert [i for i, _, _, _ in rungs] == [4, 7, 10, 13], f"rung indices drifted: {rungs}"
    for idx, label, name, cond in rungs:
        addr, raw, _ = listing[idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, \
            f"{name}: emitted condition is {struct.unpack('<H', raw)[0] & 0xF}, expected {cond}"

    # ---- GATE 3: r6 LIVENESS. r6 is loaded once (listing[1]) and shifted once (listing[2]); all
    # FOUR rungs then read it. Nothing from listing[3] through the last `cmp` may write r6.
    last_cmp = rungs[-1][0] - 1
    assert last_cmp == 12, f"the last cmp is listing[{last_cmp}], expected 12"
    for idx in range(3, last_cmp + 1):
        _, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                        # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) == 0x13:                      # cmp imm5,reg2 -- flags only
            continue
        assert (hw >> 11) == R7, \
            f"r6 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{R7}"
    # one load, one shift, four reads -- a second load or shift would silently re-base the ladder
    assert sum(1 for _, r, _ in listing if r == V55.ldh(SUM_DISP, R6)) == 1, "gp-0x6b94 loaded twice"
    assert sum(1 for _, r, _ in listing if r == V55.sar(SUM_SHIFT, R6)) == 1, "r6 shifted twice"

    # ---- GATE 6: the ONLY store in the cave is the st.b to the CAN payload byte.
    store_ops = {0x3A: "st.b", 0x3B: "st.h/st.w"}
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in store_ops]
    assert store_idx == [18], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        # Format IV short stores (sst.b/sst.h/sst.w) live in bits 10:7 == 0b0111
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- GATE 5 / geometry ---------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V65 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, " \
        "do not grow it: caves are this kit's only bricking class"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_byte4(aggregator_sum, status_bits=0x7):
    """Exactly what the cave writes, given the aggregator value. Mirrors the branch conditions.

    Integer `>>` in Python is arithmetic on negatives, which is what V850 `sar` does.
    """
    b = BIT_LIVE
    lvl = aggregator_sum >> SUM_SHIFT             # sar 0xc,r6
    for level, bit, cond, _name in LADDER:
        if (lvl >= level) if cond == COND_BLT else (lvl <= level):
            b |= bit
    return b | (status_bits & PAYLOAD_KEEP_MASK)


# The five buckets the ladder resolves, outermost first. (name, (lo, hi)) with INCLUSIVE bounds.
BUCKETS = (
    ("+RAIL", (ge_threshold(L_POS_RAIL), SUM_CLAMP)),
    ("+HALF", (ge_threshold(L_POS_HALF), ge_threshold(L_POS_RAIL) - 1)),
    ("NEUTRAL", (le_threshold(L_NEG_HALF) + 1, ge_threshold(L_POS_HALF) - 1)),
    ("-HALF", (le_threshold(L_NEG_RAIL) + 1, le_threshold(L_NEG_HALF))),
    ("-RAIL", (-SUM_CLAMP, le_threshold(L_NEG_RAIL))),
)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false".

    Three structural invariants, all guaranteed by the cave's own arithmetic on ONE register:
        bit6 => bit5                        >= +8192 implies >= +4096
        bit3 => bit4                        <= -8193 implies <= -4097
        NOT ((bit6|bit5) AND (bit4|bit3))   one value cannot be both positive and negative
    """
    if (byte4 >> 3) & 0x1F == 0:
        return None
    p_rail = bool(byte4 & BIT_POS_RAIL)
    p_half = bool(byte4 & BIT_POS_HALF)
    n_half = bool(byte4 & BIT_NEG_HALF)
    n_rail = bool(byte4 & BIT_NEG_RAIL)
    if p_rail:
        bucket = "+RAIL"
    elif p_half:
        bucket = "+HALF"
    elif n_rail:
        bucket = "-RAIL"
    elif n_half:
        bucket = "-HALF"
    else:
        bucket = "NEUTRAL"
    return {
        "live": bool(byte4 & BIT_LIVE),
        "pos_rail": p_rail, "pos_half": p_half, "neg_half": n_half, "neg_rail": n_rail,
        "bucket": bucket,
        "sum_range": dict(BUCKETS)[bucket],
        "structural_ok": ((not p_rail or p_half) and (not n_rail or n_half)
                          and not ((p_rail or p_half) and (n_half or n_rail))),
    }


def _self_check_wire():
    """Walk EVERY value in the clamped range and assert each boundary and invariant exactly."""
    seen = {name: [] for name, _ in BUCKETS}
    for v in range(-SUM_CLAMP, SUM_CLAMP + 1):
        d = decode_field(wire_byte4(v))
        assert d is not None and d["live"], f"sum={v} decodes as VOID"
        assert d["pos_rail"] == (v >= 8192), f"bit6 wrong at sum={v}"
        assert d["pos_half"] == (v >= 4096), f"bit5 wrong at sum={v}"
        assert d["neg_half"] == (v <= -4097), f"bit4 wrong at sum={v}"
        assert d["neg_rail"] == (v <= -8193), f"bit3 wrong at sum={v}"
        assert d["structural_ok"], f"a structural invariant is broken at sum={v}"
        lo, hi = d["sum_range"]
        assert lo <= v <= hi, f"sum={v} decodes to bucket {d['bucket']} = [{lo},{hi}]"
        seen[d["bucket"]].append(v)
    # every bucket must be non-empty, and the five must exactly partition the clamped range
    total = 0
    for name, (lo, hi) in BUCKETS:
        assert seen[name], f"bucket {name} is unreachable inside the clamp"
        assert (min(seen[name]), max(seen[name])) == (lo, hi), \
            f"bucket {name} spans {min(seen[name])}..{max(seen[name])}, declared [{lo},{hi}]"
        total += len(seen[name])
    assert total == 2 * SUM_CLAMP + 1, "the buckets do not partition the clamped range"
    # ---- SYMMETRY, measured on the decoded buckets rather than re-derived from the constants.
    # 🛑 The RAIL buckets differ by EXACTLY ONE count (2049 vs 2048) and that is CORRECT, not a bug.
    # `sar` is floor division, so the thresholds are +8192 / -8193: |-8193| = 8192 + 1. The value
    # -8192 therefore lands in -HALF while +8192 lands in +RAIL. The HALF buckets are exactly equal
    # (4096 each) because both of their bounds shift by the same one count.
    # Size of the artefact: 1 in 2048 = 0.049% of the rail bucket. Any real rail skew the drive can
    # resolve is orders of magnitude larger, but the number is asserted rather than assumed so a
    # future edit that made the ladder genuinely lopsided could not hide behind "it was always so".
    assert len(seen["+RAIL"]) - len(seen["-RAIL"]) == 1, \
        f"rail buckets are {len(seen['+RAIL'])}/{len(seen['-RAIL'])}; the sar floor-division " \
        "artefact is exactly ONE count and anything else means the thresholds moved"
    assert len(seen["+HALF"]) == len(seen["-HALF"]), "the two half buckets must be exactly equal"
    assert len(seen["+RAIL"]) + len(seen["+HALF"]) - (len(seen["-RAIL"]) + len(seen["-HALF"])) == 1, \
        "the positive and negative halves of the ladder are lopsided by more than the one-count artefact"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"
    # exactly FIVE payloads are reachable -- the decoder uses this to detect a foreign build
    legal = {wire_byte4(v) for v in range(-SUM_CLAMP, SUM_CLAMP + 1)}
    assert len(legal) == 5, f"the ladder emits {len(legal)} distinct payloads, expected 5"
    assert all(decode_field(b)["structural_ok"] for b in legal), "a reachable payload is not legal"
    # ⚠ the V64 ambiguity, stated as an executable fact rather than a comment
    assert wire_byte4(0, status_bits=0x7) == 0x87, \
        "a NEUTRAL V65 frame is 0x87 -- byte-identical to V64's null; the decoder must warn about it"


_self_check_wire()


# =======================================================================================================
# Image-level gates
# =======================================================================================================

def assert_probe_sites(code, label="V65"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V59 cave remnants survive past our payload"


def assert_signal_sites(code, label="V65"):
    """The probe is only interpretable if the signal's producers and the clamp are byte-for-byte stock."""
    for addr, raw in (PIN_LDH_6B94_R6, PIN_LDH_6B94_R13, PIN_BLT6, PIN_BGT6):
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the pinned instruction at 0x{addr:05X} is not {raw.hex()}"
    for addr, raw, _imm, _reg in (PIN_SAR_C_R6, PIN_SAR_A_R6, PIN_CMP_P2_R6, PIN_CMP_P1_R6,
                                  PIN_CMP_M1_R6, PIN_MOVI5_M2_R8, PIN_MOVI5_M3_R8):
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the pinned Format-II instance at 0x{addr:05X} is not {raw.hex()}"
    # the +/-10240 clamp -- the whole ladder rests on this being the rail
    for addr, raw, what in CLAMP_CTX:
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: aggregator clamp at 0x{addr:05X} ({what}) is " \
            f"{bytes(code[addr:addr + len(raw)]).hex()}, expected {raw.hex()}"
    assert s16(code, 0x3ACF8) == SUM_CLAMP and s16(code, 0x3AD10) == -SUM_CLAMP, \
        f"{label}: the clamp magnitude is no longer +/-{SUM_CLAMP}"


# =======================================================================================================
# The census -- the REQUIRED second method, re-run over the built image on every build
# =======================================================================================================

# (readers, writers, writer addresses, permitted access mnemonics)
CENSUS_EXPECTED = {SUM_DISP: (5, 3, list(SUM_WRITERS), {"ld.h", "st.h"})}
CENSUS_CONSUMERS = {SUM_DISP: SUM_REAL_LDH}
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# Where THIS cave reads the cell, derived from the listing so it can never drift from the emitted code.
_sites = [a for a, r, _ in CAVE_LISTING if r == V55.ldh(SUM_DISP, R6)]
assert len(_sites) == 1, "gp-0x6b94 must be read EXACTLY once in the cave"
CAVE_CELL_READS = {SUM_DISP: _sites[0]}


def assert_cell_census(buf, label="V65", in_cave=True):
    """Re-derive the reader/writer set from raw bytes and assert it exactly.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    Firmware accesses (outside the cave span) and this cave's own read are asserted SEPARATELY;
    pooling them would let the cave read mask the loss of a firmware one.
    """
    span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    for disp, (n_read, n_write, writers, mnems) in CENSUS_EXPECTED.items():
        hits = V64.gp_access_census(buf, disp)
        assert all(m in mnems for _, m, _ in hits), \
            f"{label}: gp-0x{disp:04x} has an access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        fw = [h for h in hits if h[0] not in span]
        reads = [h for h in fw if h[1] in _READ_MNEM]
        writes = [h for h in fw if h[1] not in _READ_MNEM]
        assert len(reads) == n_read, \
            f"{label}: gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert len(writes) == n_write, \
            f"{label}: gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}"
        assert [a for a, _, _ in writes] == writers, \
            f"{label}: gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}, not " \
            f"{[hex(w) for w in writers]}"
        assert any(a == CENSUS_CONSUMERS[disp] for a, _, _ in reads), \
            f"{label}: the consumer at 0x{CENSUS_CONSUMERS[disp]:05X} no longer reads gp-0x{disp:04x}"
        # ⚠ GATE 1 restated as a measurement: the cave READS this cell and WRITES it nowhere.
        cave = [h for h in hits if h[0] in span]
        want = [(CAVE_CELL_READS[disp], "ld.h", R6)] if in_cave else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"


def build():
    if not os.path.exists(V62_BIN):
        print(f"  {V62_BIN} missing -- running the V62 builder first\n")
        V62.build()
    v62 = bytearray(open(V62_BIN, "rb").read())
    print(f"  V62 source {V62_BIN}\n    SHA256 {hashlib.sha256(bytes(v62)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v62, "V62 source")
    assert walk(bytes(v62), label="V62 source") == 0
    assert walk_all_blocks(bytes(v62), label="V62 source") == 0
    V59.assert_probe_sites(v62, "V62 source")        # V59's OWN cave must be intact first
    V59.assert_index_chain(v62, "V62 source")
    V55.assert_variant_tables(v62)
    V57.assert_decoupled(v62, "V62 source")
    assert u16(v62, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V62 source lost the lockout edit"
    V62.assert_sar_sites(v62, "V62 source", expect_doubled=True)
    V62.assert_untouched_context(v62, "V62 source")
    V63.assert_arms(v62, "V62 source", expect_raised=False)
    assert_signal_sites(v62, "V62 source")
    assert_cell_census(bytes(v62), "V62 source", in_cave=False)
    print("    census OK: gp-0x6b94 5 readers / 3 writers, every access a SIGNED halfword,")
    print("               and V59's cave touches the cell nowhere (the pre-edit baseline for GATE 1)")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    V62.assert_sar_sites(baseline, "V38 baseline", expect_doubled=False)
    V62.assert_untouched_context(baseline, "V38 baseline")
    V63.assert_arms(baseline, "V38 baseline", expect_raised=False)
    assert_signal_sites(baseline, "V38 baseline")

    code = bytearray(v62)

    # ---- THE ONLY EDIT: replace the cave payload -------------------------------------------------
    print(f"\n  THE ONLY EDIT -- replace V59's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v62[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V62's -- same cave base, same jarl"
    assert_probe_sites(code, "V65")
    assert_signal_sites(code, "V65")
    assert_cell_census(bytes(code), "V65")

    # ---- V62's control path must be untouched, read FROM THE BUILT IMAGE --------------------------
    V62.assert_sar_sites(code, "V65", expect_doubled=True)
    V62.assert_untouched_context(code, "V65")
    V63.assert_arms(code, "V65", expect_raised=False)     # V63's raised arms must be ABSENT
    for addr, want, width, what in V63.MUST_STAY_STOCK:
        got = u16(code, addr) if width == 2 else code[addr]
        assert got == want, f"V65: 0x{addr:05X} ({what}) is {got}, expected {want}"
    V57.assert_decoupled(code, "V65")
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, "V65")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert u16(code, V62.BLEND_ADDR) == V62.BLEND_STOCK, "V60's falsified blend must be absent"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "0xC6AF0 must stay STOCK -- V56's mute is falsified"
    assert code[0xC64DE] == 27 and code[0xC64A3] == 1
    assert struct.unpack_from("<9H", code, 0xD27BC) == \
        struct.unpack_from("<9H", baseline, 0xD27BC), "FactorC 0xD27BC moved (V44 is falsified)"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A,
              0xD200C, 0xD2000):
        assert u16(code, a) == u16(baseline, a), f"damper/rate cal 0x{a:05X} moved"
    assert struct.unpack_from("<11H", code, 0xD20C0) == \
        struct.unpack_from("<11H", baseline, 0xD20C0), "0xD20C0 ceiling moved"
    for a in (0xC4018, 0xC401C, 0xC4020, 0xC4048, 0xC404C, 0xC4050):
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v62, a), \
            f"FIR coefficient 0x{a:05X} moved"

    # ---- MACHINE PROOF: the whole calibration block is byte-identical to V62's -------------------
    assert bytes(code[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]) == bytes(v62[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]), \
        "the CAL block differs from V62 -- V65 must move NO calibration byte"

    # ---- GATE 9: the cave span is owned by the MAIN block ---------------------------------------
    assert V53.owning_block(code, CAVE_BASE) == MAIN_BLOCK, "cave base is not in the MAIN CRC block"
    assert V53.owning_block(code, CAVE_BASE + len(V55.CAVE_BYTES) - 1) == MAIN_BLOCK, \
        "the cave's last byte is not in the MAIN CRC block"
    assert V53.owning_block(code, HOOK_ADDR) == MAIN_BLOCK, "the hook is not in the MAIN CRC block"

    # ---- CRC. ONLY the MAIN block moves: V65's single edit is code. ------------------------------
    print()
    cal_crc_before = struct.unpack_from("<I", code, CAL_BLOCK[1])[0]
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        if block == CAL_BLOCK:
            assert old_crc == new_crc, "CAL CRC moved -- V65 must change NO calibration"
        else:
            assert old_crc != new_crc, "the MAIN CRC did not move, but the cave bytes did"
    assert struct.unpack_from("<I", code, CAL_BLOCK[1])[0] == cal_crc_before == \
        struct.unpack_from("<I", v62, CAL_BLOCK[1])[0], \
        "the CAL CRC word is not byte-identical to V62's"
    print(f"    => CAL CRC 0x{cal_crc_before:08X} IDENTICAL to V62's = machine proof no cal byte moved")

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    cal_crc = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))

    d62 = [i for i in range(0x13000, 0x100000) if code[i] != v62[i]]
    stray = [i for i in d62 if i not in (cave_span | main_crc)]
    assert not stray, f"V65 differs from V62 outside the cave + MAIN CRC: {[hex(x) for x in stray[:16]]}"
    assert main_crc <= set(d62), "the MAIN CRC trailer did not move"
    assert not (cal_crc & set(d62)), "the CAL CRC trailer moved -- impossible if no cal byte moved"
    n_cave = len([i for i in d62 if i in cave_span])
    print(f"\n  V65 vs V62: {len(d62)} bytes  ({n_cave} cave + {len(d62) - n_cave} MAIN CRC)")
    print("    => the CAL block AND the 0xD2000 block are byte-identical: V65 is V62 plus an")
    print("       instrument, not a different experiment.")

    sar_span = {a + k for a in (V62.R24_SAR, V62.R26_SAR) for k in (0, 1)}
    if os.path.exists(V59_BIN):
        v59 = bytearray(open(V59_BIN, "rb").read())
        d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
        outside = [i for i in d59 if i not in (cave_span | main_crc | sar_span)]
        assert not outside, \
            f"V65 differs from V59 outside cave + sar + MAIN CRC: {[hex(x) for x in outside[:16]]}"
        n_sar = len([i for i in d59 if i in sar_span])
        n_cave59 = len([i for i in d59 if i in cave_span])
        print(f"  V65 vs V59: {len(d59)} bytes  ({n_cave59} cave + {n_sar} sar immediate + "
              f"{len(d59) - n_cave59 - n_sar} MAIN CRC)")
    else:
        print("  V65 vs V59: _v59_plain_image.bin absent -- run build_v59_tva.py for that comparison")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V65 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V65")
    assert walk(bytes(code), label="V65") == 0
    assert walk_all_blocks(bytes(code), label="V65") == 0
    assert_probe_sites(code, "V65")
    assert_signal_sites(code, "V65")
    V55.assert_variant_tables(code)
    V62.assert_sar_sites(code, "V65", expect_doubled=True)
    V62.assert_untouched_context(code, "V65")

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
    FF.assert_x31_checksum(rwd, "V65 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V65 readback")
    assert walk(bytes(readback), label="V65 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V65 readback") == 0
    assert_probe_sites(readback, "V65 readback")
    assert_signal_sites(readback, "V65 readback")
    assert_cell_census(bytes(readback), "V65 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V65 readback")
    V59.assert_index_chain(readback, "V65 readback")
    V62.assert_sar_sites(readback, "V65 readback", expect_doubled=True)
    V62.assert_untouched_context(readback, "V65 readback")
    V63.assert_arms(readback, "V65 readback", expect_raised=False)
    assert u16(readback, V57.PRIVATE_ADDR) == V57.GAIN_4X
    assert u16(readback, V57.GAIN_ADDR) == V57.GAIN_STOCK
    assert readback[0xC64A3] == 1 and readback[0xC64DE] == 27
    assert bytes(readback[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]) == \
        bytes(v62[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]), "readback CAL block differs from V62's"

    # re-decode the cave FROM THE BUILT IMAGE, instruction by instruction, against the listing
    print("\n  cave re-decoded from the BUILT image (readback, not from what we meant to write):")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)
    print(f"    {len(CAVE_BYTES)} bytes used of the {len(V55.CAVE_BYTES)}-byte proven extent; "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare")
    print(f"    sar sites read back: 0x{V62.R24_SAR:05X}={u16(readback, V62.R24_SAR):04X}  "
          f"0x{V62.R26_SAR:05X}={u16(readback, V62.R26_SAR):04X}  "
          f"0x{V62.R26_SAR_FIRST:05X}={u16(readback, V62.R26_SAR_FIRST):04X} (untouched, by design)")

    print("\n  PROBE: 0x14A byte4  bit7=LIVENESS, then a SYMMETRIC FOUR-LEVEL LADDER on gp-0x6b94:")
    for name, (lo, hi) in BUCKETS:
        print(f"           {name:>8s}  sum in [{lo:+6d},{hi:+6d}]   byte4 = 0x{wire_byte4(lo):02X}")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("         INVARIANTS: bit6=>bit5, bit3=>bit4, and NOT((bit6|bit5) AND (bit4|bit3)).")
    print("         Exactly FIVE payloads are reachable; anything else means the build is not V65.")
    print("  🛑 A CONSTANT 0x87 IS AMBIGUOUS WITH V64's NULL (it is V65's NEUTRAL bucket).")
    print("     Confirm which .rwd is on the car before reading any verdict.")
    print("  GATE 1 RAM ownership: VACUOUS -- same cave base/hook/extent as V55/V57/V58/V59/V64, all")
    print("          five flew fault-free. Read-only, no new RAM cell, r6/r7 only, ONE store.")
    print("  GATE 2 closed-loop stability: the CAVE is vacuous (its only output is a TX payload byte no")
    print("          control path reads). The control-path risk is V62's, unchanged and already argued")
    print("          in build_v62_tva.py. *** Still CODE in the 1 kHz TX path.")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     Route: the V61/V62 route -- parking-lot creep, LKAS on/off at matched speed and angle,")
    print("     plus manual-forward and manual-REVERSE passes. Condition on carControl.latActive or")
    print("     0x18F byte4 bit3, NEVER carState.cruiseState.enabled.")
    print("     Decode with rlog-tools/decode_v65_saturation.py.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
