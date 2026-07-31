#!/usr/bin/env python3
"""build_v64_tva.py -- V64 = V63's two calibration edits + a cave that INSTRUMENTS V63'S OWN MECHANISM.

WHAT V64 IS, AND WHY IT EXISTS
------------------------------
V63 raises only the "oscillation-detected" gain arms of the two torsion-bar rate lanes:

    0xC6440  2048 -> 4096   r24's state>=5 arm
    0xC643E  1536 -> 3072   r26's state>=5 arm

It rides the firmware's own reversal detector: `assist_state gp-0x671a` (FUN_000428d4, 1 kHz), and
`state >= CEIL` selects those arms. *** V63's fatal weakness is that a NULL would be uninterpretable. ***
We could not tell "the detector never tripped" from "the damping rise was too small". Meanwhile V59's
probe still measures `gp-0x6ba6`, the parametric-pump index V60 ALREADY FALSIFIED -- dead weight.

V64 keeps V63's two cal halfwords byte-for-byte and repoints the cave at the detector, so ONE drive
answers both "did V63 do anything?" and, if not, "which knob would make it fire?".

🛑 A LATCH, NOT A GATE -- THE FINDING THAT CAME OUT OF VERIFYING THIS PROBE
---------------------------------------------------------------------------
build_v63_tva.py's docstring says `gp-0x671a = min(revcount, CEIL)` and "sits at 0 during smooth
steering". *** THAT IS NOT WHAT THE OUTPUT STAGE DOES. *** Re-read from the disassembly, 0x429A0-0x42A12:

    0x429A0  ld.hu 0x72de[tp],r12      ; 640
    0x429A4  ld.hu -0x6a5e[gp],r15     ; the speed-like signal
    0x429A8  cmp   r15,r12 / bh 0x429CA  ; 640 > speed        -> RELOAD path
    0x429AC  cmp   r0,r14  / bne 0x429CA ; revcount != 0      -> RELOAD path
      decay:  gp-0x6a88 -= 1; when it hits 0, r8 = 0 and the output collapses to revcount
      reload: gp-0x6a88 = tp+0x7270 = 5000 ticks = 5 s
    0x429DA  ld.bu 0x74fa[tp],r6 / cmp r8,r6 / bh 0x429F0   ; CEIL > held  -> output = revcount
    0x429EA  ld.bu 0x74fa[tp],r8                            ; else          -> output = CEIL
    0x42A12  st.b  r7,-0x671a[gp]                           ; the SOLE writer

Read that carefully. Once the held value REACHES CEIL, the `bh` at 0x429E0 stops firing and the output
is re-pinned to CEIL every tick. The only way down is the decay path draining 5000 consecutive ticks,
which needs `gp-0x6a5e >= 640` AND `revcount == 0` throughout. So:

    * gp-0x671a is a ONE-WAY LATCH AT CEIL with a 5-second hold, not a per-tick oscillation flag.
    * At creep -- where the grinding lives -- `gp-0x6a5e < 640` keeps the RELOAD path running every
      tick, the timer never drains, and *** THE LATCH NEVER CLEARS WITHIN A LOW-SPEED SEGMENT. ***

Two consequences, both stated rather than smoothed:

 1. FOR V63 (the flashable part): the decoupling the operator asked for is WEAKER THAN V63 CLAIMS. It
    is not "extra damping only while an oscillation is happening"; it is "extra damping latched on for
    the rest of the low-speed driving, from the first 5-reversal burst onward". A car that never
    oscillates still never sees it -- that much survives -- but manual feel after a burst IS affected.
    This does not change a byte of V63's edit; it changes what we should expect the operator to feel,
    and it is the orchestrator's call, not this builder's.
 2. FOR V64 (the probe): bit6's OCCUPANCY is nearly worthless once it first sets -- it will read ~100%.
    The informative statistics are TIME-TO-FIRST-SET and WHETHER IT EVER CLEARS. The decoder leads with
    those. Occupancy is still reported, because occupancy == 0 is the decisive null.

🛑 AND THE NESTING IN THE PROBE SPEC IS ONLY HALF TRUE
------------------------------------------------------
The spec called bits 6 => 5 => 4 nested and asked the decoder to hard-stop on violations. Only the
first implication is structural:

    bit6 => bit5   STRUCTURAL. Same register, same tick, CEIL = 5 > 0. A violation is a DECODE ERROR.
    bit5 => bit4   *** NOT AN INVARIANT. *** The latch above holds gp-0x671a at CEIL long after the FSM
                   has timed out back to NEUTRAL (dwell > HYST = 50 ticks, while the hold is 5 s or
                   unbounded at creep). bit6=1,bit5=1,bit4=0 is the ordinary tail of every burst.

Hard-stopping on bit5=>bit4 would abort on perfectly good data. The decoder therefore hard-stops on
bit6=>bit5 only, and REPORTS bit5&~bit4 as a measurement -- it is the latch tail, and its size is a
free read on the hold timer.

THE PROBE -- CAN 0x14A byte4, 100 Hz, bits 7:3 (bits 2:0 stay stock status)
---------------------------------------------------------------------------
    bit7 = 1                    LIVENESS (field == 0 => the cave did not fire => VOID)
    bit6 = gp-0x671a >= 5       *** V63'S ARM IS SELECTED. The decisive bit. ***
    bit5 = gp-0x671a != 0       the reversal counter is counting at all
    bit4 = gp-0x67df != 0       the FSM has left NEUTRAL, i.e. |gp-0x6c2c| crossed +/-T
    bit3 = gp-0x671d != 0       r24's HIGHER-PRIORITY override is active (r24 takes 0xC6442, not 0xC6440)

WHAT EACH OUTCOME BUYS
----------------------
    bit6 ever set        -> V63's arm IS selected; a null V63 drive means the damping rise was too small
                            (next lever: raise 0xC6440/0xC643E further, or V62's unconditional double).
    bit6 never set, bit4 set   -> the input crosses T but never latches to CEIL  => lower CEIL 0xC64FA.
    bit6 never set, bit4 clear -> |gp-0x6c2c| never crosses T at all             => lower T   0xC620A.
    bit3 set             -> r24 is on 0xC6442 and V63's 0xC6440 raise does nothing for r24; raise
                            0xC6442 too. (r26's chain is clean -- gate_683c has zero st.b writers.)

CELL VERIFICATION -- Ghidra for the reading, raw LE byte scan for the census (both required)
--------------------------------------------------------------------------------------------
    gp-0x671a  BYTE, unsigned, [0,CEIL].  ld.bu @0x3AA70 (the arm test) + 6 more; SOLE st.b @0x42A12.
    gp-0x67df  BYTE, unsigned, {0,1,2}.   ld.bu @0x428E6 -- the FSM dispatch:
                 cmp 0x1,r16 / bc -> 0x428F6 NEUTRAL (zeroes dwell gp-0x6759 AND revcount gp-0x357c
                 every tick, leaves only on |gp-0x6c2c| > T);  be -> 0x42920 state 1;  cmp 0x2 / bne
                 -> 0x42996 reset;  else 0x4295C state 2.  SOLE st.b @0x4299C, r11 in {0,1,2}.
                 => 0 IS NEUTRAL, which is the whole meaning of bit4.
    gp-0x671d  BYTE, unsigned.  ld.bu @0x3AB98 into r6, then `setfne r6` @0x3ABA8, then
                 `cmp r0,r6 / be 0x3AC04` @0x3ABFA selects 0xC6442 -- so the firmware itself reduces
                 this cell to exactly the != 0 test bit3 emits.
    ⚠ The raw revcount is gp-0x357c, NOT gp-0x671a (st.b r0 @0x42906 zeroes gp-0x357c). V63's docstring
      attributes that zeroing to the wrong cell. gp-0x671a is the LATCHED OUTPUT.
    The census is re-run over the built image by assert_cell_census() on every build.

CAVE DISCIPLINE -- caves are this kit's ONLY bricking class (V24, V27, V48B)
----------------------------------------------------------------------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte extent as V55/V57/V58/V59, all four flew clean.
Read-only; r6/r7 only; the sole write is the existing CAN-330 payload byte gp-0x1514 with bits 2:0
preserved -- GATE 1 stays VACUOUS, no new RAM cell is claimed. 68 bytes exactly: the full proven
extent, ZERO remaining budget. Nothing may be added to this cave without removing something else.

ONE encoder is not already flown in its exact form: `cmp imm5,reg2` (Format II, op 0x13). It is pinned
three ways below -- to `cmp 0x5,r28` @0x3D0D0 inside DEFINED FUN_0003d04c (Ghidra lists 0x3D0D0 in its
analysed instruction set), to `cmp 0x1,r16` @0x428EA inside DEFINED FUN_000428d4, and to the exact
halfword we emit, `cmp 0x5,r6` = 6532 @0x2A50C, which sits in the identical idiom
(`ld.bu ...,gp,r6 / cmp 0x5,r6 / b<unsigned>`). V55 additionally FLASHED `cmp 0xa,r6` = 6a32, so op
0x13 with reg2 = r6 has already run on this ECU. Every other encoder is inherited and self-checked.

⚠ The cave hardcodes 5 while the firmware reads CEIL from cal 0xC64FA. They agree today; the builder
ASSERTS the equality, so a future revision that moves CEIL cannot silently decouple bit6 from the arm.

BASE = V59 + V63's cals, so V61's tap kill and V62's `sar` shifts are both ABSENT. Asserted both ways.

Decoder: rlog-tools/decode_v64_detector.py
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
import build_v63_tva as V63                # noqa: E402

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged from V55/V57/V58/V59
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- the three cells ------------------------------------------------------------------------------
STATE_DISP = 0x671A         # BYTE, [0,CEIL] -- the latched reversal counter the arm test reads
FSM_DISP = 0x67DF           # BYTE, {0,1,2}  -- 0 = NEUTRAL
OVERRIDE_DISP = 0x671D      # BYTE          -- r24's higher-priority gate

CEIL_CAL = 0xC64FA          # tp+0x74fa, BYTE. The cave hardcodes this value; equality is asserted.
CEIL_VALUE = 5
T_CAL, T_VALUE = 0xC620A, 12800          # tp+0x720a, halfword (ld.h)
HYST_CAL, HYST_VALUE = 0xC64DD, 50       # tp+0x74dd, BYTE
HOLD_CAL, HOLD_VALUE = 0xC6270, 5000     # tp+0x7270, halfword -- the 5 s latch hold

# The producer / consumer sites, all Ghidra-confirmed and byte-pinned in _self_check_encoders().
STATE_WRITER = 0x42A12      # st.b r7,-0x671a[gp]  -- SOLE writer image-wide
FSM_WRITER = 0x4299C        # st.b r11,-0x67df[gp] -- SOLE writer image-wide
ARM_TEST_LDBU = 0x3AA70     # ld.bu -0x671a,gp,r12 ; cmp r14,r12 ; bc -> r2 = (state >= CEIL)
FSM_DISPATCH_LDBU = 0x428E6  # ld.bu -0x67df,gp,r16 ; cmp 0x1,r16 ; bc -> NEUTRAL block
OVERRIDE_LDBU = 0x3AB98     # ld.bu -0x671d,gp,r6  -- byte-IDENTICAL to what this cave emits

# ---- encoder pins ---------------------------------------------------------------------------------
# Each is (address, expected bytes). Checked against the REAL IMAGE in build(), not just as literals.
PIN_LDBU_671A = (ARM_TEST_LDBU, bytes.fromhex("8467e798"))     # reg2 = r12; ours differs in reg2 only
PIN_LDBU_67DF = (FSM_DISPATCH_LDBU, bytes.fromhex("a4872198"))  # reg2 = r16; odd-disp op 0x3D form
PIN_LDBU_671D = (OVERRIDE_LDBU, bytes.fromhex("a437e398"))     # reg2 = r6 -- BYTE-IDENTICAL to ours
PIN_LDBU_R6_HW1 = (0x2A508, bytes.fromhex("8437c9c2"))         # ld.bu -0x3d38,gp,r6: our exact hw1
PIN_STB_671A = (STATE_WRITER, bytes.fromhex("443fe698"))       # the sole writer, for the census
PIN_STB_67DF = (FSM_WRITER, bytes.fromhex("445f2198"))         # the FSM's sole writer, r11 in {0,1,2}
# `cmp imm5,reg2` (Format II op 0x13) -- the one encoder not already flown in its exact form.
PIN_CMP5_R28 = (0x3D0D0, 5, 28, bytes.fromhex("65e2"))    # inside DEFINED FUN_0003d04c
PIN_CMP1_R16 = (0x428EA, 1, 16, bytes.fromhex("6182"))    # inside DEFINED FUN_000428d4
PIN_CMP5_R6 = (0x2A50C, 5, R6, bytes.fromhex("6532"))     # the EXACT halfword this cave emits

BIT_LIVE, BIT_ARMED, BIT_COUNTING, BIT_FSM, BIT_OVERRIDE = 0x80, 0x40, 0x20, 0x10, 0x08

COND_BL = V55.COND_BL       # 0x1, unsigned <  (bl == bc, pinned by FF to the real `bc +6` @0x2fc)
COND_BE = V57.COND_BE       # 0x2, Z == 1     (pinned to real `be` @0x296f0 and @0x2a2ae)

TAG = "LKAS-4x-mss0-decouple0xC646C-rateosc2x-detectorprobe-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V64-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v64_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


# =======================================================================================================
# Encoders -- every one is inherited and self-checked, or pinned to a real instance below.
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V59._self_check_encoders()          # inherits V58/V57/V55/V54/FF self-checks

    # ---- ld.bu, all three cells. BYTE loads: gp-0x671a/67df/671d are written by st.b, so ld.h would
    # read the neighbouring cell as the high byte. The kit's `hw2 = disp|1` trap runs the other way for
    # ld.bu (the trailing 1 is the selector and is ALWAYS set), so check the OPCODE parity instead.
    for disp, pin, nm in ((STATE_DISP, PIN_LDBU_671A, "gp-0x671a"),
                          (FSM_DISP, PIN_LDBU_67DF, "gp-0x67df"),
                          (OVERRIDE_DISP, PIN_LDBU_671D, "gp-0x671d")):
        ours = V55.ldbu_any(-disp, R6)
        real = pin[1]
        assert len(ours) == 4, f"{nm}: ld.bu must be 4 bytes"
        assert ours[2:] == real[2:], \
            f"{nm}: displacement halfword {ours[2:].hex()} != the real instance {real[2:].hex()}"
        # only the reg2 field (hw1 bits 15:11) may differ from the pinned instance
        hw_ours, hw_real = struct.unpack("<H", ours[:2])[0], struct.unpack("<H", real[:2])[0]
        assert (hw_ours & 0x07FF) == (hw_real & 0x07FF), \
            f"{nm}: opcode/reg1 field differs from the real instance -- not a register-field change"
        assert (hw_ours >> 11) == R6, f"{nm}: reg2 field is r{hw_ours >> 11}, expected r{R6}"
        d16 = (0x10000 - disp) & 0xFFFF
        # The MIRROR of V59's `ld.h` check (which asserts the hw2 LSB is CLEAR): for ld.bu/ld.hu/ld.w
        # the LSB of hw2 is the width selector and must be SET. Defensive against a future edit of
        # ldbu_any dropping the `| 1` -- that would silently turn these into ld.b/ld.h.
        assert struct.unpack_from("<H", ours, 2)[0] & 1 == 1, \
            f"{nm}: ld.bu hw2 LSB must be SET (`disp|1`) -- clear would be ld.b/ld.h, a WIDTH change"
        # ⚠ AND THE SHARPER CHECK, because the LSB above is forced unconditionally by the encoder and
        # so can never fail on its own: the REAL displacement bit 0 lives in the OPCODE (0x3C | d&1).
        # Get THAT wrong and the address is off by one -- gp-0x671a would read gp-0x671b.
        assert ((hw_ours >> 5) & 0x3F) == (0x3C | (d16 & 1)), \
            f"{nm}: ld.bu opcode parity is wrong for a 0x{d16:04X} displacement"
    # gp-0x671d's read is byte-IDENTICAL to the firmware's own -- the strongest pin available.
    assert V55.ldbu_any(-OVERRIDE_DISP, R6) == PIN_LDBU_671D[1], \
        "ld.bu -0x671d[gp],r6 must be byte-identical to the real instance @0x3AB98"
    # and our hw1 for an EVEN gp displacement into r6 is pinned by a second real instruction
    assert V55.ldbu_any(-STATE_DISP, R6)[:2] == PIN_LDBU_R6_HW1[1][:2], \
        "our even-displacement `ld.bu ...,gp,r6` hw1 differs from the real instance @0x2A508"

    # ---- cmp imm5,reg2 -- the ONE encoder not already flown in its exact form. Three pins.
    for addr, imm5, reg2, raw in (PIN_CMP5_R28, PIN_CMP1_R16, PIN_CMP5_R6):
        assert V55.cmp_imm5(imm5, reg2) == raw, \
            f"cmp_imm5({imm5},r{reg2}) fails the real instance @0x{addr:05X}"
    assert V55.cmp_imm5(CEIL_VALUE, R6) == PIN_CMP5_R6[3], "the emitted `cmp 0x5,r6` is not 6532"
    # the imm5 field must actually carry the value -- a helper that ignored it would pass a single pin
    assert V55.cmp_imm5(5, R6) != V55.cmp_imm5(1, R6), "cmp_imm5 ignores its immediate"
    assert V55.cmp_imm5(5, R6) != V55.cmp_imm5(5, R7), "cmp_imm5 ignores its register"
    assert 0 <= CEIL_VALUE <= 15, "Format II imm5 is SIGNED (-16..15); CEIL must fit unambiguously"

    # ---- st.b: the encoder that writes our payload byte, cross-pinned to the detector's own two
    # writers. It already reproduces V31P's flashed byte4 store (checked by V54); these add two more
    # real instances at different registers and displacements, which is what a register-field claim needs.
    assert FF.stb(7, -STATE_DISP, GP) == PIN_STB_671A[1], \
        f"FF.stb fails the real `st.b r7,-0x671a[gp]` @0x{STATE_WRITER:05X}"
    assert FF.stb(11, -FSM_DISP, GP) == PIN_STB_67DF[1], \
        f"FF.stb fails the real `st.b r11,-0x67df[gp]` @0x{FSM_WRITER:05X}"

    # ---- branch conditions. V64 introduces NONE: both are pinned to real instances.
    assert FF.bcond(COND_BL, +6).hex() == "b105", "bl/bc +6 drifted from its real instance"
    assert FF.bcond(COND_BE, +6).hex() == "b205", "be +6 drifted from V57"
    assert FF.bcond(COND_BE, +8).hex() == "c205", "be +8 fails the real instance @0x296f0"

    # ---- the four bit-set moveas: V54's flashed reg1=r7 bias form, different immediates.
    for bit in (BIT_ARMED, BIT_COUNTING, BIT_FSM, BIT_OVERRIDE):
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"movea 0x{bit:x},r7,r7 malformed"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"

    # ---- the five bits occupy exactly 7:3, leaving the stock status field alone.
    bits = (BIT_LIVE, BIT_ARMED, BIT_COUNTING, BIT_FSM, BIT_OVERRIDE)
    assert len(set(bits)) == 5 and all(b & (b - 1) == 0 for b in bits), "probe bits are not distinct"
    assert sum(bits) == 0xF8, f"probe bits must occupy exactly 7:3, got 0x{sum(bits):02X}"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    # bit6 => bit5 is the STRUCTURAL invariant the decoder hard-checks; it only holds if CEIL > 0.
    assert CEIL_VALUE > 0, "bit6 => bit5 requires CEIL > 0"


# =======================================================================================================
# The cave -- 68 bytes exactly, the full proven extent
# =======================================================================================================

def build_cave():
    """pack_reversal_detector -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.bu -0x671a[gp],r6   ; the LATCHED reversal counter (BYTE, 0..CEIL)
        cmp   0x5,r6           ; CEIL -- asserted equal to cal 0xC64FA
        bl    +6               ; unsigned < 5 -> V63's arm is NOT selected, leave bit6 clear
        movea 0x40,r7,r7       ; bit6 = state >= 5   *** V63'S ARM IS SELECTED ***
      arm_done:
        cmp   r0,r6            ; r6 still holds the counter (cmp and movea-into-r7 left it alone)
        be    +6               ; == 0 -> not counting
        movea 0x20,r7,r7       ; bit5 = state != 0
      count_done:
        ld.bu -0x67df[gp],r6   ; the FSM state (BYTE, 0 = NEUTRAL)
        cmp   r0,r6
        be    +6               ; == 0 -> still NEUTRAL, |gp-0x6c2c| never crossed T
        movea 0x10,r7,r7       ; bit4 = FSM has LEFT neutral
      fsm_done:
        ld.bu -0x671d[gp],r6   ; r24's higher-priority override (BYTE)
        cmp   r0,r6
        be    +6               ; == 0 -> override idle
        movea 0x8,r7,r7        ; bit3 = r24 is on 0xC6442, NOT on V63's 0xC6440
      override_done:
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

    emit(V55.ldbu_any(-STATE_DISP, R6), "ld.bu -0x671a[gp],r6 ; latched reversal counter")
    emit(V55.cmp_imm5(CEIL_VALUE, R6), f"cmp 0x{CEIL_VALUE:x},r6            ; CEIL (cal 0xC64FA)")
    emit(FF.bcond(COND_BL, +6), "bl +6               ; unsigned < CEIL -> arm NOT selected")
    emit(FF.movea(BIT_ARMED, R7, R7), "movea 0x40,r7,r7    ; bit6 = V63'S ARM IS SELECTED")
    arm_done = CAVE_BASE + len(body)

    emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; r6 still = the counter")
    emit(FF.bcond(COND_BE, +6), "be +6               ; == 0 -> not counting")
    emit(FF.movea(BIT_COUNTING, R7, R7), "movea 0x20,r7,r7    ; bit5 = counter != 0")
    count_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-FSM_DISP, R6), "ld.bu -0x67df[gp],r6 ; FSM state (0 = NEUTRAL)")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BE, +6), "be +6               ; == 0 -> still NEUTRAL")
    emit(FF.movea(BIT_FSM, R7, R7), "movea 0x10,r7,r7    ; bit4 = FSM LEFT neutral")
    fsm_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-OVERRIDE_DISP, R6), "ld.bu -0x671d[gp],r6 ; r24 override counter")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BE, +6), "be +6               ; == 0 -> override idle")
    emit(FF.movea(BIT_OVERRIDE, R7, R7), "movea 0x8,r7,r7     ; bit3 = r24 on 0xC6442")
    override_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # Every branch must land exactly on its label. Located BY POSITION, not by content: this cave
    # reuses `be +6` THREE times, so a content-based lookup would be ambiguous.
    for idx, label, name in [(3, arm_done, "bl->arm_done"),
                             (6, count_done, "be->count_done"),
                             (10, fsm_done, "be->fsm_done"),
                             (14, override_done, "be->override_done")]:
        addr, raw, _ = listing[idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"

    # r6 must still hold the counter at the bit5 test -- nothing between may write it.
    for _, raw, text in listing[4:5]:
        assert raw[:2] == bytes.fromhex("273e"), "the bit6 set must be a movea into r7, not into r6"

    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V64 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, do not grow it"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_byte4(state, fsm, override, status_bits=0x7):
    """Exactly what the cave writes, given the three cell values. Mirrors the branch conditions."""
    b = BIT_LIVE
    if state >= CEIL_VALUE:          # cmp 0x5,r6 / bl  -- UNSIGNED, and the cell is a ld.bu
        b |= BIT_ARMED
    if state != 0:                   # cmp r0,r6 / be
        b |= BIT_COUNTING
    if fsm != 0:
        b |= BIT_FSM
    if override != 0:
        b |= BIT_OVERRIDE
    return b | (status_bits & PAYLOAD_KEEP_MASK)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false".

    `structural_ok` is bit6 => bit5 ONLY. bit5 => bit4 is NOT an invariant -- the gp-0x671a latch
    outlives the FSM's return to NEUTRAL by up to 5 s (indefinitely at creep), so bit5 & ~bit4 is the
    ordinary tail of a burst and must be reported, not rejected.
    """
    if (byte4 >> 3) & 0x1F == 0:
        return None
    armed = bool(byte4 & BIT_ARMED)
    counting = bool(byte4 & BIT_COUNTING)
    return {
        "live": bool(byte4 & BIT_LIVE),
        "armed": armed,
        "counting": counting,
        "fsm_left_neutral": bool(byte4 & BIT_FSM),
        "r24_override": bool(byte4 & BIT_OVERRIDE),
        "structural_ok": (not armed) or counting,
        "latch_tail": counting and not bool(byte4 & BIT_FSM),
    }


def assert_probe_sites(code, label="V64"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V59 cave remnants survive past our payload"


def assert_detector_intact(code, label="V64"):
    """The probe is only interpretable if the detector it watches is byte-for-byte stock.

    ⚠ WIDTH MATTERS. CEIL and HYST are read by `ld.bu` (BYTE) at 0x429DA/0x42920; T is a genuine
    halfword (`ld.h 0x720a[tp]`). Reading 0xC64FA as u16 gives 517, not 5 -- the trap V63 hit.
    """
    assert code[CEIL_CAL] == CEIL_VALUE, \
        f"{label}: CEIL 0x{CEIL_CAL:05X} is {code[CEIL_CAL]}, not {CEIL_VALUE} -- the cave hardcodes " \
        f"{CEIL_VALUE}, so bit6 would no longer mean 'V63's arm is selected'"
    assert code[HYST_CAL] == HYST_VALUE, f"{label}: HYST 0x{HYST_CAL:05X} moved"
    assert u16(code, T_CAL) == T_VALUE, f"{label}: reversal threshold T 0x{T_CAL:05X} moved"
    assert u16(code, HOLD_CAL) == HOLD_VALUE, f"{label}: latch hold 0x{HOLD_CAL:05X} moved"
    # the producer's sole writers and the two consumers we are calibrated against
    for addr, raw in (PIN_STB_671A, PIN_STB_67DF, PIN_LDBU_671A, PIN_LDBU_67DF, PIN_LDBU_671D,
                      PIN_LDBU_R6_HW1):
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the pinned instruction at 0x{addr:05X} is not {raw.hex()}"
    for addr, imm5, reg2, raw in (PIN_CMP5_R28, PIN_CMP1_R16, PIN_CMP5_R6):
        assert bytes(code[addr:addr + 2]) == raw, \
            f"{label}: the `cmp 0x{imm5:x},r{reg2}` pin at 0x{addr:05X} is not {raw.hex()}"


# =======================================================================================================
# The census -- the REQUIRED second method, re-run over the built image on every build
# =======================================================================================================

_GP = 4
_FORMS = [("ld.b", 0x38, "disp"), ("ld.h", 0x39, "even"), ("ld.w", 0x39, "odd"),
          ("st.b", 0x3A, "disp"), ("st.h", 0x3B, "even"), ("st.w", 0x3B, "odd"),
          ("ld.bu", None, "odd"), ("ld.hu", 0x3F, "odd")]


def gp_access_census(buf, disp_neg):
    """Every 4-byte gp-relative access to -disp_neg, by raw LE byte scan at even offsets.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    Hits are reported at every even offset; an address-literal collision is possible in principle and
    would show up as an extra hit, so the counts are asserted EXACTLY rather than as lower bounds.
    """
    d16 = (0x10000 - disp_neg) & 0xFFFF
    out = []
    for mnem, op, kind in _FORMS:
        hw2 = d16 if kind == "disp" else (d16 & 0xFFFE) | (1 if kind == "odd" else 0)
        for o in ([0x3C | (d16 & 1)] if op is None else [op]):
            for reg2 in range(32):
                pat = struct.pack("<HH", (reg2 << 11) | (o << 5) | _GP, hw2)
                i = buf.find(pat)
                while i >= 0:
                    if i % 2 == 0:
                        out.append((i, mnem, reg2))
                    i = buf.find(pat, i + 1)
    return sorted(out)


# The firmware's OWN accesses, outside the cave span. (reads, writes, writer addresses)
CENSUS_EXPECTED = {
    STATE_DISP: (7, 1, [STATE_WRITER]),        # 7 ld.bu readers, 1 st.b writer @0x42A12
    FSM_DISP: (1, 1, [FSM_WRITER]),            # 1 reader (the dispatch), 1 writer @0x4299C
    OVERRIDE_DISP: (14, 2, [0x3BD2A, 0x41EC6]),
}
# The consumer each bit is calibrated against -- these must survive as readers.
CENSUS_CONSUMERS = {STATE_DISP: ARM_TEST_LDBU, FSM_DISP: FSM_DISPATCH_LDBU,
                    OVERRIDE_DISP: OVERRIDE_LDBU}

# Where THIS cave reads each cell, derived from the listing so it can never drift from the emitted code.
CAVE_CELL_READS = {}
for _disp in (STATE_DISP, FSM_DISP, OVERRIDE_DISP):
    _sites = [a for a, r, _ in CAVE_LISTING if r == V55.ldbu_any(-_disp, R6)]
    assert len(_sites) == 1, f"gp-0x{_disp:04x} must be read EXACTLY once in the cave"
    CAVE_CELL_READS[_disp] = _sites[0]


def assert_cell_census(buf, label="V64", in_cave=True):
    """Re-derive the reader/writer sets from raw bytes and assert them exactly.

    Firmware accesses (outside the cave span) and this cave's own reads are asserted SEPARATELY --
    pooling them would let a cave read mask the loss of a firmware one, which is precisely the
    substitution the census exists to catch. `in_cave=False` gates a pre-edit source image.
    """
    span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    for disp, (n_read, n_write, writers) in CENSUS_EXPECTED.items():
        hits = gp_access_census(buf, disp)
        assert all(m in ("ld.bu", "st.b") for _, m, _ in hits), \
            f"{label}: gp-0x{disp:04x} has a non-BYTE access -- the cell is not a byte after all"
        fw = [h for h in hits if h[0] not in span]
        reads = [h for h in fw if h[1] == "ld.bu"]
        writes = [h for h in fw if h[1] == "st.b"]
        assert len(reads) == n_read, \
            f"{label}: gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert len(writes) == n_write, \
            f"{label}: gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}"
        assert [a for a, _, _ in writes] == writers, \
            f"{label}: gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}, not " \
            f"{[hex(w) for w in writers]}"
        assert any(a == CENSUS_CONSUMERS[disp] for a, _, _ in reads), \
            f"{label}: the consumer at 0x{CENSUS_CONSUMERS[disp]:05X} no longer reads gp-0x{disp:04x}"
        # ⚠ GATE 1 restated as a measurement: the cave READS these cells and WRITES none of them.
        cave = [h for h in hits if h[0] in span]
        want = [(CAVE_CELL_READS[disp], "ld.bu", R6)] if in_cave else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"


def build():
    if not os.path.exists(V59_BIN):
        print(f"  {V59_BIN} missing -- running the V59 builder first\n")
        V59.build()
    v59 = bytearray(open(V59_BIN, "rb").read())
    print(f"  V59 source {V59_BIN}\n    SHA256 {hashlib.sha256(bytes(v59)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v59, "V59 source")
    assert walk(bytes(v59), label="V59 source") == 0
    assert walk_all_blocks(bytes(v59), label="V59 source") == 0
    V59.assert_probe_sites(v59, "V59 source")        # V59's OWN cave must be intact first
    V59.assert_index_chain(v59, "V59 source")
    V55.assert_variant_tables(v59)
    V57.assert_decoupled(v59, "V59 source")
    assert u16(v59, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V59 source lost the lockout edit"
    V63.assert_arms(v59, "V59 source", expect_raised=False)
    V63.assert_untouched(v59, "V59 source")
    assert_detector_intact(v59, "V59 source")
    assert_cell_census(bytes(v59), "V59 source", in_cave=False)
    print("    census OK: gp-0x671a 7r/1w, gp-0x67df 1r/1w, gp-0x671d 14r/2w -- all BYTE accesses,")
    print("               and V59's cave touches none of the three (the pre-edit baseline for GATE 1)")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    V63.assert_arms(baseline, "V38 baseline", expect_raised=False)
    V63.assert_untouched(baseline, "V38 baseline")
    assert_detector_intact(baseline, "V38 baseline")

    code = bytearray(v59)

    # ---- EDIT 1: V63's two calibration halfwords, byte-for-byte ----------------------------------
    print("\n  EDIT 1 -- V63's two cal halfwords (the state>=5 arms), carried verbatim:")
    for addr, stock, new, what in V63.EDITS:
        assert u16(code, addr) == stock, f"0x{addr:05X} is not stock {stock}"
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {stock:5d} -> {new:5d}   {what}")
    V63.assert_arms(code, "V64", expect_raised=True)
    V63.assert_untouched(code, "V64")     # also proves V61's taps and V62's sars are ABSENT

    # ---- EDIT 2: replace the cave payload --------------------------------------------------------
    print(f"\n  EDIT 2 -- replace V59's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} remaining):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v59[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V59's -- same cave base, same jarl"
    assert_probe_sites(code, "V64")
    assert_detector_intact(code, "V64")
    assert_cell_census(bytes(code), "V64")

    # ---- everything V57/V59 established must still hold ------------------------------------------
    V57.assert_decoupled(code, "V64")
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, "V64")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "0xC6AF0 must stay STOCK -- V56's mute is falsified"
    assert u16(code, 0xD2006) == 102, "V60's falsified blend must be absent"
    assert code[0xC64DE] == 27 and code[0xC64A3] == 1
    assert struct.unpack_from("<9H", code, 0xD27BC) == \
        struct.unpack_from("<9H", baseline, 0xD27BC), "FactorC 0xD27BC moved (V44 is falsified)"
    # V64 changes NO calibration except V63's two arms.
    moved = {a for a, _, _, _ in V63.EDITS}
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC61B2, "fwd clamp"), (0xC61B4, "fwd clamp"),
                    (0xC6442, "r24 override arm"), (0xC6446, "r24 dead arm"), (0xC6444, "r26 dead arm"),
                    (0xC61F6, "r24 deadzone"), (0xC61D6, "slew step -- V16 REJECTED"),
                    (0xC6424, "shaper deadband"), (0xC64C9, "2D-map mux"),
                    (0xC646C, "shared sensor scale"), (0xC6CD0, "private LKAS gain"),
                    (0xC63BA, "FUN_3b66a EMA alpha")):
        assert a not in moved and u16(code, a) == u16(v59, a), f"{name} 0x{a:05X} moved"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A,
              0xD200C, 0xD2000):
        assert u16(code, a) == u16(baseline, a), f"damper/rate cal 0x{a:05X} moved"
    assert struct.unpack_from("<11H", code, 0xD20C0) == \
        struct.unpack_from("<11H", baseline, 0xD20C0), "0xD20C0 ceiling moved"
    for a in (0xC4018, 0xC401C, 0xC4020, 0xC4048, 0xC404C, 0xC4050):
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v59, a), \
            f"FIR coefficient 0x{a:05X} moved"

    # ---- CRC. BOTH blocks move: EDIT 1 is calibration, EDIT 2 is code. ---------------------------
    assert V53.owning_block(code, CAVE_BASE) == MAIN_BLOCK
    assert V53.owning_block(code, V63.R24_OSC_ARM) == CAL_BLOCK
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        assert old_crc != new_crc, f"the CRC for block 0x{block[0]:X} did not move, but its bytes did"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    cal_crc = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    # ⚠ Do NOT hardcode WHICH cal bytes move: 2048->4096 is 0x0800->0x1000, so in LE only the HIGH byte
    # of each halfword differs. Assert CONTAINMENT in the two edited halfwords instead.
    cal_span = {a + k for a, _, _, _ in V63.EDITS for k in (0, 1)}
    permitted = cave_span | main_crc | cal_crc | cal_span
    stray = [i for i in d59 if i not in permitted]
    assert not stray, f"V64 touches bytes outside cave + cals + both CRCs: {[hex(x) for x in stray]}"
    assert main_crc <= set(d59) and cal_crc <= set(d59), "a CRC trailer did not move"
    n_cave = len([i for i in d59 if i in cave_span])
    n_cal = len([i for i in d59 if i in cal_span])
    print(f"\n  V64 vs V59: {len(d59)} bytes  ({n_cave} cave + {n_cal} calibration + 8 CRC)")

    v63_bin = str(plain_image_path("_v63_plain_image.bin"))
    if os.path.exists(v63_bin):
        v63 = bytearray(open(v63_bin, "rb").read())
        d63 = [i for i in range(0x13000, 0x100000) if code[i] != v63[i]]
        outside = [i for i in d63 if i not in (cave_span | main_crc)]
        assert not outside, \
            f"V64 differs from V63 outside the cave + MAIN CRC: {[hex(x) for x in outside[:16]]}"
        print(f"  V64 vs V63: {len(d63)} bytes  (cave payload + MAIN CRC ONLY)")
        print("    => machine proof V64 carries V63's calibration EXACTLY: the CAL block is identical,")
        print("       so V64 is V63 plus an instrument, not a different experiment.")
    else:
        print("  V64 vs V63: _v63_plain_image.bin absent -- run build_v63_tva.py for that comparison")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V64 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V64")
    assert walk(bytes(code), label="V64") == 0
    assert walk_all_blocks(bytes(code), label="V64") == 0
    assert_probe_sites(code, "V64")
    assert_detector_intact(code, "V64")
    V55.assert_variant_tables(code)
    V63.assert_arms(code, "V64", expect_raised=True)
    V63.assert_untouched(code, "V64")

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback ------------------------------
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
    FF.assert_x31_checksum(rwd, "V64 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V64 readback")
    assert walk(bytes(readback), label="V64 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V64 readback") == 0
    assert_probe_sites(readback, "V64 readback")
    assert_detector_intact(readback, "V64 readback")
    assert_cell_census(bytes(readback), "V64 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V64 readback")
    V59.assert_index_chain(readback, "V64 readback")
    V63.assert_arms(readback, "V64 readback", expect_raised=True)
    V63.assert_untouched(readback, "V64 readback")
    assert u16(readback, V57.PRIVATE_ADDR) == V57.GAIN_4X
    assert u16(readback, V57.GAIN_ADDR) == V57.GAIN_STOCK
    assert readback[0xC64A3] == 1 and readback[0xC64DE] == 27

    # re-decode the cave FROM THE BUILT IMAGE, instruction by instruction, against the listing
    print("\n  cave re-decoded from the BUILT image:")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)
    print(f"    {len(CAVE_BYTES)} bytes used of the {len(V55.CAVE_BYTES)}-byte proven extent; "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} remaining")

    # the wire model must be self-consistent for every reachable cell combination
    for state in range(0, CEIL_VALUE + 2):
        for fsm in (0, 1, 2):
            for override in (0, 1, 7):
                b4 = wire_byte4(state, fsm, override)
                d = decode_field(b4)
                assert d is not None and d["live"], f"state={state} decodes as VOID"
                assert d["armed"] == (state >= CEIL_VALUE)
                assert d["counting"] == (state != 0)
                assert d["fsm_left_neutral"] == (fsm != 0)
                assert d["r24_override"] == (override != 0)
                assert d["structural_ok"], "bit6 => bit5 must hold for every reachable state"
    # the latch tail -- a REAL reading, not a decode error
    tail = decode_field(wire_byte4(CEIL_VALUE, 0, 0))
    assert tail["structural_ok"] and tail["latch_tail"] and tail["armed"], \
        "state==CEIL with the FSM back in NEUTRAL is the latch tail and must decode cleanly"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  PROBE: 0x14A byte4  bit7=LIVENESS  bit6=(gp-0x671a>=5, V63'S ARM SELECTED)")
    print("                      bit5=(gp-0x671a!=0)  bit4=(gp-0x67df!=0, FSM left NEUTRAL)")
    print("                      bit3=(gp-0x671d!=0, r24 on 0xC6442)   bits2:0 = stock status.")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("         bit6 => bit5 is STRUCTURAL; a violation is a decode error. bit5 => bit4 IS NOT --")
    print("         the gp-0x671a latch outlives the FSM's return to neutral. That is the burst tail.")
    print("  GATE 1 RAM ownership: VACUOUS -- same cave base/hook/extent as V55/V57/V58/V59, all four")
    print("          flew fault-free. Read-only, no new RAM cell, r6/r7 only.")
    print("  GATE 2 closed-loop stability: the CAVE is vacuous (its only output is a TX payload byte no")
    print("          control path reads). V63's two cal arms carry V63's own GATE 2: they add damping")
    print("          in the 1 kHz lane, gated on the detector. *** Still CODE in the 1 kHz TX path.")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     Route: the V61/V63 route -- parking-lot creep, LKAS on/off at matched speed and angle,")
    print("     plus manual-forward and manual-REVERSE passes. Condition on carControl.latActive or")
    print("     0x18F byte4 bit3, NEVER carState.cruiseState.enabled.")
    print("     🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT. gp-0x671a is a ONE-WAY LATCH that never")
    print("     clears at creep, so TIME-TO-FIRST-SET is the measurement and it happens exactly once.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
