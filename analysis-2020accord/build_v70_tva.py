#!/usr/bin/env python3
"""build_v70_tva.py -- V70 = V69's TOPOLOGY at HALF the dose, + a REPAIRED probe.

    V70  ==  V69  everywhere except FOUR surface halfwords and the 68-byte cave.

That identity is not a design goal aimed at -- it is ASSERTED, byte-for-byte, against
`_v69_plain_image.bin`, over the whole image. It is the strongest available statement of PART A and
it costs nothing.

🛑 THIS FILE WAS RE-CUT. Its first revision restored V67/V68's control path. That was WRONG and the
operator said so: *"V70 just reverts back to V68, which has the high-speed grind #2 issue. This
needs to change. V70 needs to try to fix all grind issues."* The record of why the first cut was
wrong is kept below, because the reasoning error is more valuable than the result.

WHY THE FIRST CUT WAS WRONG -- AN INSTRUMENT LIMIT MISTAKEN FOR EVIDENCE OF ABSENCE
------------------------------------------------------------------------------------
The V68-restore was chosen because V67/V68 measured best on the two symptoms this kit can SEE, and
the operator's high-speed report was discounted on the grounds that there is no line anywhere in
30-49.5 Hz. That inference is invalid, and the numbers were already on file:

  * CAN's Nyquist is 50.00 Hz and the comma IMU's is 50.51 Hz. **BOTH vibration instruments are
    blind above ~50 Hz.** "No line below 50" is not evidence of absence; it is the edge of the
    instrument.
  * The ACOUSTIC inversion -- a completely independent channel, needing no transfer model -- places
    the excess at an effective centroid of **63.5 Hz [54, 80]**, which sits essentially ON
    `gp-0x6c2c`'s 61 Hz band-pass peak. The whole interval is ABOVE the Nyquist ceiling.
  ⇒ **the operator is the only instrument that can see that band**, and his report is not an
    impression but a DOSE-RESPONSE: the high-speed grind is present on V67/V68 and he reported it
    GONE on V69. Those two builds differ at highway by exactly the lever below.

★ AND THE ARM IS THE WORST-SHAPED LEVER IN THE KIT FOR THAT SYMPTOM. A scalar arm REPLACES a
surface Honda deliberately rolls off with speed (3072 -> 2151), so `arm / LERP` RISES with speed and
PEAKS at highway. The rate lane is a differentiator (gain proportional to frequency), so that peak
lands hardest in precisely the band he feels. Delivered r24 multiplier vs the stock surface,
RE-DERIVED FROM THE IMAGE by this file's own sweep (not quoted):

    operating point                      x2 surface   V69 x4   V67/V68 arm
    grind #1        (7.2 km/h, rk 603)       1.836     3.508      2.000
    grind #1  on the ALTERNATE axis scale    2.000     4.000      1.939
    grind #2 creep  (7.2 km/h, rk 1206)      1.282     1.847      2.206
    engaged HIGHWAY (93 km/h)                1.000     1.000      2.436

WHY x2 FIXES ALL THREE RATHER THAN TRADING THEM
-------------------------------------------------
  HIGH-SPEED GRIND -- the operator's complaint. At and above 50 km/h the surface is STRUCTURALLY
      stock: the cross-axis interpolation there reads ONLY rec2/rec3, which this edit does not
      touch. Asserted by sweep below (0 differing points), not by argument. That is the exact
      configuration he reported clean on V69.
  GRIND #1. 1.836x at its measured operating point (2.000x on the alternate axis scale -- the scale
      is [OPEN] and the edit is deliberately near-invariant to it). The dose-response is NON-
      MONOTONE with a minimum near 2x (0x -> 2501, 1x -> 879, **2x -> 168**, 4x -> 746), which is
      why V69's 4x overshot and grind #1 came back. V62 flew a flat 2.00x to *"the original grinding
      at 2-5 mph is gone."*
  GRIND #2 AT CREEP. 1.282x -- far below the flat 2.00x that V62/V65 flew and that CAUSED grind #2
      (11.71x), because this edit raises only the FLAT [0,400] rate segment while grind #2 lives at
      rateKey >= 1126 (19 of 24 recorded bursts). **Strictly better here than V62.** And V69 already
      flew 4x manual creep with ZERO bursts and the lowest max of any pool (50.5).

✅ **MAX DELIVERED MULTIPLIER ANYWHERE IS EXACTLY 2.000000 AND THE MINIMUM IS EXACTLY 1.000000** --
so every operating point lies inside the flown bracket [stock 1.00x, V62/V65 2.00x], both of which
flew flight-clean, and NO operating point is ever below stock. That safety property is the reason
this dose and not 3x, and it is asserted by a 24,321-point sweep rather than reasoned about.
✅ SATURATION IS NO LONGER A LIVE CONCERN. Peak gain 6144 rails the r24 lane at |dtorque| ~1365,
against the repo-recorded max 839 (margin 1.63x) and V69's own flight max of 633.9 (margin 2.15x).
At V69's 4x the peak was 12288 and the rail was 683 -- BELOW the recorded max. Halving the dose
removes the one metric on which V69 was worse than V68.
⚠ THE COST, STATED: manual steering below ~50 km/h gets 2.000x of the rate damping -- exactly the
dose V62/V65 flew. Manual highway stays byte-identical to stock.

🛑🛑 THE EDIT-ORDER INVARIANT IS V69's FORM, NOT THE FIRST CUT's
------------------------------------------------------------------
`arm == 512 ⇒ gate == 0xc5`. The dangerous combination is a STOCK arm (512) with the gate still
repointed to the LIVE cell: that leaves the engaged lane pinned at 512 against a stock LERP of
2101-3072, i.e. ~5x BELOW stock everywhere, which is V61 territory and V61 measured WORSE on-car.
🛑 The first cut of this file asserted the INVERSE (`gate == 0xfb ⇒ arm == 5244`) because it shipped
the V68 topology. Both directions are asserted below so that neither topology can be emitted wrong,
and the pair `(gate, arm)` is pinned to exactly one of the two known-good combinations.

🛑 THE NEIGHBOUR TRAP. Modes 10/11/12 interleave at stride 0x14 and **mode 11's and mode 12's
0 km/h records are BYTE-IDENTICAL to mode 10's**. The target byte pattern occurs THREE times within
40 bytes. Every cell here is addressed absolutely and all eight neighbours are asserted unchanged;
`diff_build_vs_stock.py` is span-based and would NOT catch a stray hit.

PART B -- THE PROBE. UNCHANGED FROM THE FIRST CUT; every byte identical.
------------------------------------------------------------------------
  bit7 = 1                   LIVENESS.
  bit6 = gp-0x6ada >= +512   THE POSITIVE CONTROL. r24's lane output, post its +/-0x2000 clip.
  bit5 = (gp-0x67fa == 10)   THE STATE GATE. FUN_00036388 (return-to-centre) and FUN_000428d4
                             (Honda's oscillation detector) are called under `andi 0x830` = {4,5,11};
                             FUN_0003aa2c / FUN_0003a382 under `andi 0xc30` = {4,5,10,11}. State 10
                             is the difference, and the mask wraps the `jarl` in the CALLER, so a
                             masked-out state means the function is never invoked.
  bit4 = gp-0x6adc >= 0      r26's post-clamp mirror SIGN -- 0 readers / 1 writer image-wide.
  bit3 = gp-0x6ada >= 0      r24's SIGN. Build identity + the order invariant + the ratchet.

★ bit4 IS A SIGN, NOT THE MATCHED +512 THRESHOLD -- a deviation from the original brief, raised
before building and approved. The cave budget is 68 B and four signals cost 2 B more than that with
a `sar` on bit4, so one `sar` had to go; and the sign is the better measurement anyway, because the
standing record (cal base 0xC6564 = 40 bytes of exact zero) PREDICTS r26 inert, so a `>= +512` rung
reading 0.000% was the expected outcome and could not separate "inert" from "live but under 512" --
the uninterpretable-zero class that wasted V64's and V69's probes. Read bit4 as an AGREEMENT
statistic against bit3: r24 and r26 take the same `dtorque` and the SAME single polarity read
(`ld.b -0x6752[gp],r14` @0x3AB78), and `gp-0x69a4` is an unsigned magnitude at both ends, so the two
lanes always carry the SAME SIGN. bit4 pinned ⇒ r26 inert; bit4 tracking bit3 ⇒ r26 live.
🛑 THE COST: V70 measures r26's LIVENESS, not `a`.

★ bit6's THRESHOLD SURVIVES THE RE-CUT. T = +512 was sized on the first cut's arm-5244 path; under
this dose it sits BETWEEN the stock case (route duty 0.500%, prominence 15.6) and the 4x case
(4.878%, 30.6), so it remains a live positive control with no saturation risk at either end.

🛑🛑 THE ONE-BIT TRAP IS LIVE ON THREE RUNGS
`ld.h` = 0x39, `st.h` = 0x3B -- ONE BIT -- and BOTH `gp-0x6ada` and `gp-0x6adc` have their only real
instances as the `st.h` form carrying the SAME displacement halfword (0x3AD5A, 0x3AD4E). `ld.bu` =
0x3C vs `st.b` = 0x3A is likewise one bit, on `gp-0x67fa`, a LIVE state variable with 128 readers.
All three opcodes are asserted BY VALUE here and independently in `verify_v70_image.py`.
★ A genuine de-risking versus V69: V69's third rung read `gp-0x6ad4`, which the aggregator CONSUMES
at 0x3ACA8, so a one-bit slip there would have corrupted a live lane. V70's two `ld.h` rungs are
both on ZERO-READER mirror cells, so even a slipped opcode could only produce a wrong READING.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent **68 of the proven 68 B** -- unchanged, flown 8x
(V55/V57/V58/V59/V64/V65/V66/V67, all clean). Read-only; r6/r7 only; exactly ONE store, the CAN-330
payload byte. Growing a cave is this kit's ONLY bricking class (V24, V27, V48B all bricked the ECU).
🛑 ZERO spare: every one of the 68 bytes is used.

Usage:  python build_v70_tva.py
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

# 🛑 WINDOWS REDIRECT FIX. cp1252 is chosen for a redirected stdout on this machine, so the first
# `print(__doc__)` raises UnicodeEncodeError on the 🛑/★/⚠ glyphs and `> build.log` crashes before
# emitting a line -- i.e. the build "fails" for a reason that has nothing to do with the firmware.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v54_tva as V54                # noqa: E402  (andi / or_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldh / sar / cmp_imm5 / ldbu_any encoders)
import build_v57_tva as V57                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the two-decoder scan)
import build_v65_tva as V65                # noqa: E402
import build_v67_tva as V67                # noqa: E402
import build_v68_tva as V68                # noqa: E402  (cave machinery + the STOCK-surface reference)
import build_v69_tva as V69                # noqa: E402  (the SOURCE image's builder: gain model)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                               # noqa: E402

START, END = V68.START, V68.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = len(V55.CAVE_BYTES)          # 68 -- the PROVEN extent, flown 8x. Never grow it.
D2000_BLOCK = V68.D2000_BLOCK

# ---- PART A: V69's TOPOLOGY IS KEPT. Only the DOSE moves. --------------------------------------
REPOINT_ADDR = V67.REPOINT_ADDR            # 0x3AA94  ld.bu -0x????[gp],r15
REPOINT_BYTE = V67.REPOINT_BYTE            # 0x3AA96  UNCHANGED on V70: stays V69's 0xC5
GATE_DEAD, GATE_LIVE = 0xC5, 0xFB          # gp-0x683c (DEAD, 0 writers) vs gp-0x6806 (LKAS-active)
ARM_ADDR = V67.ARM_ADDR                    # 0xC6446  UNCHANGED on V70: stays stock 512
ARM_STOCK, ARM_GATED = 512, 5244
# 🛑 The gate must stay on the DEAD cell: the surface only reaches the ENGAGED lane when the gate is
# OFF, because the gate branch at 0x3AC04 REPLACES the LERP rather than scaling it.

SCALE = 2                                  # 🛑 THE DOSE. Was 4 on V69; halved on operator override.
REC0, REC1 = V69.REC0, V69.REC1            # 0xD2A74 / 0xD2AB0 -- mode-10 gain_B 0 and 10 km/h
STOCK_Y = {REC0 + 0x0A: 3072, REC0 + 0x0C: 3072, REC1 + 0x0A: 2561, REC1 + 0x0C: 2561}
SURFACE = tuple((a, stock * 4, stock * SCALE, nm) for (a, nm), stock in zip(
    ((REC0 + 0x0A, "rec0 (0 km/h)  Y[0]"), (REC0 + 0x0C, "rec0 (0 km/h)  Y[1]"),
     (REC1 + 0x0A, "rec1 (10 km/h) Y[0]"), (REC1 + 0x0C, "rec1 (10 km/h) Y[1]")),
    (3072, 3072, 2561, 2561)))
NEIGHBOURS = V69.NEIGHBOURS                # mode 11/12 -- BYTE-IDENTICAL to mode 10's stock rec0
UNTOUCHED_RECS = V69.UNTOUCHED_RECS        # 0xD2AEC / 0xD2B28 -- mode-10 50 and 100 km/h
HIGHWAY_COUNTS = 3200                      # the cross-axis breakpoint above which only rec2/rec3 read

# =====================================================================================================
# PART B -- THE PROBE.  0x14A byte4 bits 7:3.  68 of the proven 68 bytes; ZERO spare. UNCHANGED.
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP        # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK          # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT

BIT_LIVE = 0x80
BIT_R24_HALF = 0x40        # bit6  gp-0x6ada >= +512      THE POSITIVE CONTROL
BIT_STATE10 = 0x20         # bit5  gp-0x67fa == 10        THE STATE GATE
BIT_R26_SIGN = 0x10        # bit4  gp-0x6adc >= 0         r26's mirror -- 0 readers image-wide
BIT_R24_SIGN = 0x08        # bit3  gp-0x6ada >= 0         SIGN: identity + order invariant + ratchet
LIVE_IMM = BIT_LIVE        # 0x80 -- bit3 is a RUNG on V70, never a constant

SHIFT, LEVEL = 9, 1
THRESHOLD = LEVEL << SHIFT                 # = +512
STATE_VALUE = 10
COND_BLT = 0x6                             # SIGNED <.  🛑 bl (0x1) is the UNSIGNED twin and inverts
COND_BNE = 0xA                             # != .       🛑 be (0x2) is its twin and inverts the rung

PROBE_CENSUS = {
    0x6ADA: (0, 1, [0x3AD5A], {"st.h"}, None),          # pure mirror of r24: NOTHING reads it
    0x6ADC: (0, 1, [0x3AD4E], {"st.h"}, None),          # pure mirror of r26: NOTHING reads it
}
STATE_DISP = 0x67FA
STATE_MIN_READERS = 100                    # measured 128 loads; assert a floor, not equality

PIN_LDH_6AD4 = (0x3ACA8, bytes.fromhex("24372c95"))   # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_6B94 = (0x453E0, bytes.fromhex("24376c94"))   # hw1 donor #2 (V65's), different cell
PIN_STH_6ADA = (0x3AD5A, bytes.fromhex("64c72695"))   # 🛑 opcode 0x3B -- ONE BIT from our 0x39
PIN_STH_6ADC = (0x3AD4E, bytes.fromhex("64d72495"))   # 🛑 likewise, for the second ld.h rung
PIN_LDBU_67FA = (0x18C7C, bytes.fromhex("84370798"))  # BYTE-IDENTICAL to what we emit (13 instances)
PIN_SAR9_R6 = (0x3E60C, bytes.fromhex("a932"))        # `sar 0x9,r6`, followed by st.h -- our idiom
PIN_CMP_A_R6 = (0x3553A, bytes.fromhex("6a32"))       # `cmp 0xa,r6`
PIN_CMP_R0_R6 = (0x1507C, bytes.fromhex("e031"))      # `cmp r0,r6` -- and FLOWN in V57's cave
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))           # `blt +4`, preceded by `cmp r0,r7`: our shape
PIN_BNE6 = (0x14CB2, bytes.fromhex("ba05"))           # `bne +6`, skipping a 4-byte instruction
PIN_ADD8_R7 = (0x17CD8, bytes.fromhex("483a"))        # `add 0x8,r7`
# ⚠ PROVENANCE NOTE, declared not buried: a raw byte scan finds `483a` twice, but the second hit
# (0x37FB4) lies INSIDE a `jarl 0x6b9fa,lp` immediate and is not an instruction. So `add 0x8,r7` has
# exactly ONE real instance. It is nevertheless a strong pin: 0x17CD4/0x17CD6 are `add 0x8,ep` and
# `add 0x8,r10` -- the SAME opcode and immediate differing only in reg2, three consecutive
# instructions, and ours is literally the middle one.
PIN_ADD8_SIBLINGS = ((0x17CD4, bytes.fromhex("48f2"), 30), (0x17CD6, bytes.fromhex("4852"), 10))

TAG = ("LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-"
       "gainB-rec0rec1-x2-signprobe-6ada-67fa10-6adc-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V70-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v70_plain_image.bin"))
SRC_BIN = plain_image_path("_v69_plain_image.bin")
STOCK_SURF_BIN = plain_image_path("_v68_plain_image.bin")   # its rec0/rec1 ARE the stock surface
DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v70_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def _s16(x):
    """Interpret a 16-bit pattern the way `ld.h` does -- SIGNED."""
    return x - 0x10000 if x & 0x8000 else x


def add_imm5(imm, reg2):
    """V850 Format II `add imm5,reg2` -- opcode 0b010010. The ONLY 2-byte way to set a bit <= 15."""
    assert 0 <= imm <= 15, "Format II imm5 is SIGNED (-16..15); a bit above 15 does not fit"
    assert 0 <= reg2 <= 31
    return struct.pack("<H", (reg2 << 11) | (0x12 << 5) | (imm & 0x1F))


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v6ada, v67fa, v6adc, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the decompiled arithmetic, not a paraphrase."""
    r7 = LIVE_IMM                                   # movea 0x80,r0,r7
    r6 = _s16(v6ada) >> SHIFT                       # ld.h ; sar 0x9  (Python >> floors == `sar`)
    if not (r6 < LEVEL):                            # cmp 0x1,r6 ; blt +6
        r7 += BIT_R24_HALF                          # movea 0x40,r7,r7
    if not (r6 < 0):                                # cmp r0,r6 ; blt +4
        r7 += BIT_R24_SIGN                          # add 0x8,r7
    r6 = v67fa & 0xFF                               # ld.bu (ZERO-extends a byte)
    if not (r6 != STATE_VALUE):                     # cmp 0xa,r6 ; bne +6
        r7 += BIT_STATE10                           # movea 0x20,r7,r7
    r6 = _s16(v6adc)                                # ld.h  (NO shift on this rung)
    if not (r6 < 0):                                # cmp r0,r6 ; blt +6
        r7 += BIT_R26_SIGN                          # movea 0x10,r7,r7
    return r7 | (status_bits & PAYLOAD_KEEP_MASK)


LEGAL_PAYLOADS = {BIT_LIVE | a | b | c | d
                  for a in (0, BIT_R24_HALF) for b in (0, BIT_STATE10)
                  for c in (0, BIT_R26_SIGN) for d in (0, BIT_R24_SIGN)
                  if not (a and not d)}


def _wire_model():
    """The rungs' semantics, over ALL 65,536 halfword patterns and all 256 state bytes."""
    for raw in range(0x10000):
        x = _s16(raw)
        b = wire_byte4(raw, 0, 0)
        assert bool(b & BIT_R24_HALF) == (x >= THRESHOLD), f"bit6 is not `>= {THRESHOLD}` at x = {x}"
        assert bool(b & BIT_R24_SIGN) == (x >= 0), f"bit3 is not `>= 0` at x = {x}"
        # ★ THE ORDER INVARIANT -- this is what makes V70 identifiable, so it is PROVEN, not argued.
        assert not (b & BIT_R24_HALF) or (b & BIT_R24_SIGN), \
            f"bit6 without bit3 at x = {x} -- the order invariant is broken"
        assert bool(wire_byte4(0, 0, raw) & BIT_R26_SIGN) == (x >= 0), f"bit4 is not `>= 0` at x = {x}"
    for s in range(0x100):
        assert bool(wire_byte4(0, s, 0) & BIT_STATE10) == (s == STATE_VALUE), \
            f"bit5 is not `== {STATE_VALUE}` at state {s}"
    # 🛑 `blt` is (S xor OV), not a mathematical `<`, so the model above is only exact if the compares
    # CANNOT overflow. Asserted rather than reasoned about: after `sar 0x9` a signed halfword lands in
    # [-64, 63], and `cmp r0` subtracts zero where OV is 0 by construction.
    shifted = {_s16(raw) >> SHIFT for raw in range(0x10000)}
    assert min(shifted) == -(1 << (15 - SHIFT)) and max(shifted) == (1 << (15 - SHIFT)) - 1, \
        f"the shifted range is {min(shifted)}..{max(shifted)} -- re-derive the overflow argument"
    assert -0x8000 < min(shifted) - LEVEL and max(shifted) - LEVEL < 0x7FFF, \
        "the compare can overflow -- `blt` would stop meaning `<` and the rungs would invert"
    # 🛑 the UNSIGNED failure modes, spelled out rather than trusted.
    assert ((-1 & 0xFFFF) >> SHIFT) >= LEVEL, "the unsigned reading of -1 does NOT fire -- re-derive"
    assert not ((-1 >> SHIFT) >= LEVEL), "the signed reading of -1 fires -- the model is wrong"
    assert wire_byte4(0xFFFF, 0, 0) & BIT_R24_SIGN == 0, "bit3 fires on -1: the sign test is unsigned"
    assert wire_byte4(0x0000, 0, 0) & BIT_R24_SIGN, "bit3 does not fire on 0 -- `>= 0` must include 0"
    reach = {wire_byte4(a, s, c) & 0xF8
             for a in (0x0000, 0x7FFF, 0x0100, 0x8000, 0xFE00)
             for s in (0, STATE_VALUE) for c in (0x0000, 0x8000)}
    assert reach <= LEGAL_PAYLOADS, f"the wire model reaches {reach - LEGAL_PAYLOADS}, outside LEGAL"
    assert len(LEGAL_PAYLOADS) == 12, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 12 of 16"
    assert not any((p & BIT_R24_HALF) and not (p & BIT_R24_SIGN) for p in LEGAL_PAYLOADS), \
        "LEGAL_PAYLOADS contains a bit6-without-bit3 payload -- the invariant is not encoded"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction, or to a self-checked ancestor.

    🛑 Caves are this kit's ONLY bricking class (V24, V27, V48B all bricked the ECU).
    """
    V65._self_check_encoders()               # chains down through V59/V58/V57/V55/V54/FF
    src = Path(STOCK_SURF_BIN).read_bytes()

    for addr, raw in (PIN_LDH_6AD4, PIN_LDH_6B94, PIN_STH_6ADA, PIN_STH_6ADC, PIN_LDBU_67FA,
                      PIN_SAR9_R6, PIN_CMP_A_R6, PIN_CMP_R0_R6, PIN_BLT4, PIN_BNE6, PIN_ADD8_R7):
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the reference image -- re-pin"
    for addr, raw, reg2 in PIN_ADD8_SIBLINGS:
        assert bytes(src[addr:addr + 2]) == raw, f"the `add 0x8` sibling @0x{addr:05X} moved"
        assert add_imm5(8, reg2) == raw, \
            f"our add_imm5 encoder does not reproduce the real `add 0x8,r{reg2}` @0x{addr:05X}"

    # ---- the two `ld.h` rungs. THE ONE-BIT TRAP: ld.h = 0x39, st.h = 0x3B --------------------
    for disp, sth_pin, name in ((0x6ADA, PIN_STH_6ADA, "r24 mirror"),
                                (0x6ADC, PIN_STH_6ADC, "r26 mirror")):
        ours = V55.ldh(disp, R6)
        hw1, hw2 = struct.unpack("<HH", ours)
        assert ((hw1 >> 5) & 0x3F) == 0x39, \
            f"{name}: emitted opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h)"
        assert ours != FF.sth(R6, -disp, GP) and ours[:2] != FF.sth(R6, -disp, GP)[:2], \
            f"{name}: the emitted load shares an opcode field with `st.h` -- that would WRITE the lane"
        assert ours != FF.ldhu(disp, R6), f"{name}: ld.h collapsed onto ld.hu -- the SIGN would be lost"
        assert hw1 & 0x1F == GP == 4, f"{name}: reg1 field is not r4 (gp)"
        assert (hw1 >> 11) == R6, f"{name}: reg2 field is not r6"
        assert hw2 & 1 == 0, f"{name}: ld.h hw2 LSB must be CLEAR (LSB set is the ld.w/ld.hu form)"
        assert hw2 == (0x10000 - disp) & 0xFFFF, f"{name}: displacement is not -0x{disp:04x}"
        assert hw1 == struct.unpack_from("<H", PIN_LDH_6AD4[1], 0)[0] == \
            struct.unpack_from("<H", PIN_LDH_6B94[1], 0)[0], \
            f"{name}: hw1 differs from BOTH real `ld.h ...,r6` donors"
        assert hw2 == struct.unpack_from("<H", sth_pin[1], 2)[0], \
            f"{name}: displacement halfword does not match the real st.h @0x{sth_pin[0]:05X}"
    assert V55.ldh(0x6ADA, R6) != V55.ldh(0x6ADC, R6), "the two mirror loads are byte-identical"

    # ---- the state rung's `ld.bu`. ANOTHER ONE-BIT TRAP: ld.bu = 0x3C, st.b = 0x3A -----------
    ours = V55.ldbu_any(-STATE_DISP, R6)
    assert ours == PIN_LDBU_67FA[1], \
        f"ld.bu -0x67fa[gp],r6 is not byte-identical to the real instance @0x{PIN_LDBU_67FA[0]:05X}"
    hw1, hw2 = struct.unpack("<HH", ours)
    assert ((hw1 >> 5) & 0x3F) == 0x3C, \
        f"state rung: opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x3C (ld.bu, EVEN disp)"
    assert ours != FF.stb(R6, -STATE_DISP, GP), "the state load collapsed onto an st.b -- a WRITE"
    assert ours != V55.ldh(STATE_DISP, R6) and ours != FF.ldhu(STATE_DISP, R6), \
        "the state load collapsed onto a HALFWORD load -- it would straddle the neighbouring cell"
    # 🛑 THE hw1-BIT-5 PARITY TRAP. `ld.bu` carries the displacement's bit 0 in the OPCODE FIELD
    # (0x3C even / 0x3D odd), NOT in hw2, so a parity slip silently addresses the NEIGHBOURING cell
    # with every other field perfect. -0x67fa = 0x9806 is EVEN => opcode 0x3C, hw2 = 0x9807.
    assert ((0x10000 - STATE_DISP) & 0xFFFF) % 2 == 0, "gp-0x67fa's displacement is ODD -- re-derive"
    assert hw2 == (((0x10000 - STATE_DISP) & 0xFFFF) | 1) == 0x9807, \
        f"state rung: hw2 is 0x{hw2:04X}, expected 0x9807 (disp | 1)"

    # ---- the 2-byte instructions, each byte-identical to a real instance ---------------------
    assert V55.sar(SHIFT, R6) == PIN_SAR9_R6[1], f"sar 0x9,r6 != the real one @0x{PIN_SAR9_R6[0]:05X}"
    assert V55.sar(SHIFT, R6) != FF.shr(SHIFT, R6), "sar collapsed onto shr -- the sign would be lost"
    assert V55.cmp_imm5(LEVEL, R6) == bytes.fromhex("6132"), "cmp 0x1,r6 (@0x14D46) encoding changed"
    assert V55.cmp_imm5(STATE_VALUE, R6) == PIN_CMP_A_R6[1], \
        f"cmp 0xa,r6 != the real one @0x{PIN_CMP_A_R6[0]:05X}"
    assert 0 <= STATE_VALUE <= 15, "Format II imm5 is SIGNED (-16..15); the state must fit"
    assert FF.bcond(COND_BLT, +6) == bytes.fromhex("b605"), "blt +6 (@0x1C006) encoding changed"
    assert FF.bcond(COND_BLT, +4) == PIN_BLT4[1], f"blt +4 != the real one @0x{PIN_BLT4[0]:05X}"
    assert FF.bcond(COND_BNE, +6) == PIN_BNE6[1], f"bne +6 != the real one @0x{PIN_BNE6[0]:05X}"
    assert FF.bcond(COND_BNE, +6) in V57.CAVE_BYTES, "`bne +6` is not byte-present in V57's FLOWN cave"
    assert COND_BLT != V55.COND_BL, "blt collapsed onto the UNSIGNED bl"
    assert COND_BNE != 0x2, "bne collapsed onto be -- the state rung would invert"
    assert add_imm5(8, R7) == PIN_ADD8_R7[1], f"add 0x8,r7 != the real one @0x{PIN_ADD8_R7[0]:05X}"
    assert add_imm5(8, R7) != add_imm5(8, R6), "add_imm5 ignores its register"
    assert add_imm5(8, R7) != V55.cmp_imm5(8, R7), "add collapsed onto cmp -- the bit would never set"
    assert FF.movea(LIVE_IMM, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert PIN_CMP_R0_R6[1] in V57.CAVE_BYTES, "`cmp r0,r6` is not byte-present in V57's FLOWN cave"

    bits = (BIT_LIVE, BIT_R24_HALF, BIT_STATE10, BIT_R26_SIGN, BIT_R24_SIGN)
    assert len(set(bits)) == 5 and all(b & (b - 1) == 0 for b in bits), "probe bits are not distinct"
    assert sum(bits) == 0xF8, f"probe bits must occupy exactly 7:3, got 0x{sum(bits):02X}"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert LIVE_IMM & BIT_R24_SIGN == 0, "bit3 must not be in the liveness immediate -- it is a rung"
    assert V68.LIVE_IMM & BIT_R24_SIGN != 0, "V68 no longer emits bit3 = 1 -- re-derive the identity"
    _wire_model()


def build_cave():
    """pack_sign_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80   bit7 LIVENESS  (bit3 is a RUNG, not a constant)
        ld.h  -0x6ada[gp],r6   ; r24's lane output, post +/-0x2000 clip   (0 readers image-wide)
        sar   0x9,r6           ; ARITHMETIC: units of 512, sign preserved
        cmp   0x1,r6
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6ada >= +512      THE POSITIVE CONTROL
      g0:
        cmp   r0,r6            ; the SAME shifted value -- (x >> 9) >= 0  <=>  x >= 0
        blt   +4
        add   0x8,r7           ; bit3 = gp-0x6ada >= 0         SIGN. bit6 => bit3, always.
      g1:
        ld.bu -0x67fa[gp],r6   ; the ECU STATE byte
        cmp   0xa,r6
        bne   +6
        movea 0x20,r7,r7       ; bit5 = (gp-0x67fa == 10)      THE STATE GATE
      g2:
        ld.h  -0x6adc[gp],r6   ; r26's lane mirror  (0 readers image-wide)
        cmp   r0,r6
        blt   +6
        movea 0x10,r7,r7       ; bit4 = gp-0x6adc >= 0
      g3:
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

    emit(FF.movea(LIVE_IMM, R0, R7), "movea 0x80,r0,r7    ; bit7 LIVENESS (bit3 is a RUNG on V70)")

    # ---- bit6 + bit3: ONE load, ONE shift, TWO tests --------------------------------------
    emit(V55.ldh(0x6ADA, R6), "ld.h -0x6ada[gp],r6 ; r24 lane out, post-clip (SIGNED, 0 readers)")
    emit(V55.sar(SHIFT, R6), f"sar 0x{SHIFT:x},r6           ; ARITHMETIC -- units of {THRESHOLD}")
    emit(V55.cmp_imm5(LEVEL, R6), f"cmp 0x{LEVEL:x},r6           ; signed compare")
    br_hi = len(listing)
    emit(FF.bcond(COND_BLT, +6), "blt +6              ; skip -> g0")
    emit(FF.movea(BIT_R24_HALF, R7, R7), f"movea 0x40,r7,r7    ; bit6 = gp-0x6ada >= +{THRESHOLD}")
    g0 = CAVE_BASE + len(body)
    emit(PIN_CMP_R0_R6[1], "cmp r0,r6           ; SAME shifted value: (x>>9) >= 0  <=>  x >= 0")
    br_sign = len(listing)
    emit(FF.bcond(COND_BLT, +4), "blt +4              ; skip -> g1")
    emit(add_imm5(8, R7), "add 0x8,r7          ; bit3 = gp-0x6ada >= 0   (bit6 => bit3, always)")
    g1 = CAVE_BASE + len(body)

    # ---- bit5: the STATE GATE, an EQUALITY not a threshold --------------------------------
    emit(V55.ldbu_any(-STATE_DISP, R6), "ld.bu -0x67fa[gp],r6 ; the ECU state byte")
    emit(V55.cmp_imm5(STATE_VALUE, R6), f"cmp 0x{STATE_VALUE:x},r6           ; the aggregator-only state")
    br_state = len(listing)
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; skip -> g2   (be would INVERT this rung)")
    emit(FF.movea(BIT_STATE10, R7, R7), f"movea 0x20,r7,r7    ; bit5 = (gp-0x67fa == {STATE_VALUE})")
    g2 = CAVE_BASE + len(body)

    # ---- bit4: r26's mirror, SIGN (no shift -- that is the 2 bytes bit3 costs) -------------
    emit(V55.ldh(0x6ADC, R6), "ld.h -0x6adc[gp],r6 ; r26 lane mirror (SIGNED, 0 readers)")
    emit(PIN_CMP_R0_R6[1], "cmp r0,r6")
    br_r26 = len(listing)
    emit(FF.bcond(COND_BLT, +6), "blt +6              ; skip -> g3")
    emit(FF.movea(BIT_R26_SIGN, R7, R7), "movea 0x10,r7,r7    ; bit4 = gp-0x6adc >= 0")
    g3 = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands EXACTLY on its label, located BY POSITION ---------------
    for br_idx, label, cond, size, name in ((br_hi, g0, COND_BLT, 6, "bit6"),
                                            (br_sign, g1, COND_BLT, 4, "bit3"),
                                            (br_state, g2, COND_BNE, 6, "bit5"),
                                            (br_r26, g3, COND_BLT, 6, "bit4")):
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a Bcond"
        assert addr + size == label, \
            f"{name}: branch target 0x{addr + size:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, \
            f"{name}: branch condition is 0x{struct.unpack('<H', raw)[0] & 0xF:X}, not 0x{cond:X} -- " \
            "the wrong condition INVERTS the whole rung (the V67 setfne/setfe lesson)"
        setter = listing[br_idx + 1][1]
        assert len(setter) == size - 2, f"{name}: the skipped setter is {len(setter)}B, not {size - 2}B"
    assert [listing[i][0] for i in (br_hi, br_sign, br_state, br_r26)] == \
        [0xC4B40, 0xC4B48, 0xC4B52, 0xC4B5E], "the branch addresses drifted from the design"

    # ---- GATE 2b: r6/r7 LIVENESS. Only a rung's own load/shift may write r6 ------------------
    # 🛑 bit3 reads r6 THREE instructions after the shift that produced it, across a `cmp`, a `blt`
    # and a `movea` -- so r6-liveness across that window is load-bearing and is asserted, not assumed.
    r6_writers = {listing[1][0], listing[2][0], listing[9][0], listing[13][0]}
    for idx in range(1, br_r26 + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                # cmp imm5,reg2 / cmp reg1,reg2 -- flags
            continue
        want = R6 if addr in r6_writers else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    for _a, raw, text in [listing[i] for i in range(3, 6)]:   # between the sar and bit3's test
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (len(raw) == 2 and raw[1] == 0x05) or ((hw >> 5) & 0x3F) in (0x13, 0x0F) \
            or (hw >> 11) == R7, f"'{text}' clobbers r6 between the shift and bit3's test"
    for disp in (0x6ADA, 0x6ADC):
        assert sum(1 for _, r, _ in listing if r == V55.ldh(disp, R6)) == 1, \
            f"gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store ---------------
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert store_idx == [20], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[20][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "the sole store is not the payload"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == 4 + 14 + 6 + 12 + 12 + 20 == 68, f"the cave is {len(body)}B, the budget says 68"
    assert len(body) <= CAVE_EXTENT, \
        f"cave {len(body)}B overruns the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def assert_probe_census(buf, cave_span):
    """Re-derive each probed cell's reader/writer set from RAW BYTES and assert it exactly.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    read_mnem = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}
    for disp, (n_read, n_write, writers, mnems, consumer) in PROBE_CENSUS.items():
        hits = V64.gp_access_census(buf, disp)
        assert all(m in mnems | {"ld.h"} for _, m, _ in hits), \
            f"gp-0x{disp:04x} has an access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        fw = [h for h in hits if h[0] not in cave_span]
        reads = [h for h in fw if h[1] in read_mnem]
        writes = [h for h in fw if h[1] not in read_mnem]
        assert len(reads) == n_read, \
            f"gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert [a for a, _, _ in writes] == writers, \
            f"gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}, expected " \
            f"{[hex(w) for w in writers]}"
        if consumer is not None:
            assert any(a == consumer for a, _, _ in reads), f"0x{consumer:05X} no longer reads it"
        cave = [h for h in hits if h[0] in cave_span]
        assert len(cave) == 1 and cave[0][1] == "ld.h" and cave[0][2] == R6, \
            f"gp-0x{disp:04x}: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, expected " \
            "exactly one `ld.h ...,r6`"
    # 🛑 BOTH probed halfword cells have ZERO firmware readers -- the strongest GATE-1 statement
    # available anywhere in this chain, AND it means a one-bit ld.h->st.h slip could only corrupt a
    # cell nobody reads.
    for disp in (0x6ADA, 0x6ADC):
        assert PROBE_CENSUS[disp][0] == 0, f"gp-0x{disp:04x} acquired a reader -- no longer free"

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


def assert_decoder_matches(cave_bytes, label="V70"):
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
        f"{label}: the decoder's THRESHOLD is not {THRESHOLD} -- it applies V69's semantics"
    assert re.search(rf"^STATE_VALUE\s*=\s*{STATE_VALUE}\b", txt, re.M), \
        f"{label}: the decoder's STATE_VALUE is not {STATE_VALUE}"
    # 🛑 THE STALENESS CHECK MUST TARGET THE BIT MAP, NOT THE PROSE. V70's decoder legitimately
    # EXPLAINS why gp-0x6b62 and gp-0x6ad4 were retired, so a whole-file substring search would
    # forbid exactly the documentation that stops the next session re-proposing them.
    m = re.search(r"^RUNGS\s*=\s*\((.*?)^\)", txt, re.M | re.S)
    assert m, f"{label}: the decoder has no RUNGS literal -- its bit map cannot be checked"
    up = m.group(1).upper()                  # ⚠ so is the needle: `0x` upper-cases to `0X`
    for disp in (0x6ADA, STATE_DISP, 0x6ADC):
        assert f"{disp:04X}" in up, f"{label}: gp-0x{disp:04x} is not a rung in the decoder's bit map"
    for stale in (0x6B62, 0x6AD4, 0x67DF, 0x671A):
        assert f"{stale:04X}" not in up, \
            f"{label}: gp-0x{stale:04x} is still a LIVE RUNG in the decoder's bit map -- V70 retired it"
    # 🛑 AND THE CONTROL PATH IT DESCRIBES MUST BE THIS BUILD'S. The first cut of V70 shipped the V68
    # topology; a decoder still asserting that as V70's own would be a confident WRONG provenance
    # claim on a flown artifact -- the V66 stale-header class exactly.
    # ⚠ THE GUARD TESTS THE CLAIM, NOT THE STRING. An earlier revision of this check simply banned
    # the substring "arm-5244" and thereby forbade the very paragraph that DOCUMENTS the
    # supersession -- the same over-broad-guard mistake the RUNGS check above already had to fix.
    # Mentioning the superseded path is REQUIRED for the record; asserting it as V70's is the fault.
    for false_claim in ("V68CONTROLPATH", "byte-identical to V68's", "V68's control path, restored"):
        assert false_claim not in txt, \
            f"{label}: the decoder asserts the SUPERSEDED V68 control path as V70's ('{false_claim}')"
    if "arm-5244" in txt:
        assert "SUPERSEDED" in txt, \
            f"{label}: the decoder mentions the arm-5244 path without marking it SUPERSEDED"
    # and it must name THIS artifact's topology, which the .rwd basename above already encodes
    # ("gateREVERTED" + "x2"); assert those tokens explicitly so a rename cannot silently pass.
    for token in ("gateREVERTED", "x2-signprobe"):
        assert token in txt, f"{label}: the decoder does not name the shipped topology ('{token}')"
    return True


def build():
    print(__doc__)
    src = Path(SRC_BIN)
    v69 = bytearray(src.read_bytes())
    stock = Path(STOCK_SURF_BIN).read_bytes()          # the STOCK surface reference
    print("=" * 102)
    print(f"SOURCE (V69): {src}\n  SHA256 {hashlib.sha256(bytes(v69)).hexdigest()}")
    print(f"STOCK-SURFACE REFERENCE (V68): {STOCK_SURF_BIN}")

    # ---- gate the SOURCE before touching it ---------------------------------------------------
    assert len(v69) == len(stock) == 0x100000, "an image is not 1 MiB"
    assert v69[REPOINT_BYTE] == GATE_DEAD, \
        f"source gate byte is 0x{v69[REPOINT_BYTE]:02X}, expected V69's 0x{GATE_DEAD:02X}"
    assert u16(v69, ARM_ADDR) == ARM_STOCK, f"source arm is {u16(v69, ARM_ADDR)}, expected {ARM_STOCK}"
    for addr, old, _new, name in SURFACE:
        assert u16(v69, addr) == old, f"{name} @0x{addr:05X} is {u16(v69, addr)}, expected V69's {old}"
        assert u16(stock, addr) == STOCK_Y[addr], f"{name} is not stock on the reference image"
    role = list(v69[0xC4124:0xC4124 + 11])
    assert role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0], f"role table drifted: {role}"
    assert not any(r in (6, 7) for r in role), \
        "a slot carries role 6 or 7 -- gp-0x67ac becomes LIVE and the rate lanes can drop out"
    assert bytes(v69[0xC6564:0xC6564 + 40]) == bytes(40), \
        "0xC6564 is no longer 40 zero bytes -- r26 may no longer be inert (bit4's whole premise)"
    print(f"  source gates: gate 0xC5, arm 512, surface x4, role {role}, 0xC6564 = 40 zero bytes  ✅")

    code = bytearray(v69)

    # ---- PART A: V69's TOPOLOGY IS KEPT; ONLY THE DOSE MOVES ----------------------------------
    print("\n  PART A -- V69's TOPOLOGY KEPT, DOSE HALVED (operator override: V70 must fix ALL grinds):")
    print(f"    0x{REPOINT_BYTE:05X}  0x{GATE_DEAD:02X} UNCHANGED   the gate stays on the DEAD "
          "gp-0x683c -- the surface only reaches the ENGAGED lane with the gate OFF")
    print(f"    0x{ARM_ADDR:05X}  {ARM_STOCK} UNCHANGED     r24's arm stays stock and unreachable")
    for addr, old, new, name in SURFACE:
        before = struct.pack("<H", old)
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   bytes {before.hex(' ')} -> "
              f"{struct.pack('<H', new).hex(' ')}   {name}")
        assert new == SCALE * STOCK_Y[addr], f"{name} is not an exact {SCALE}x of STOCK"
        assert old == 4 * STOCK_Y[addr], f"{name}'s source value is not V69's 4x"
        # 🛑 SIGN HEADROOM: the Y row must stay a POSITIVE SIGNED halfword, or an `ld.h` accessor
        # would read it NEGATIVE and invert the lane.
        assert 0 < new < 0x8000, f"{name} = {new} is not a positive signed halfword"

    # ---- 🛑🛑 THE EDIT-ORDER INVARIANT -- V69's FORM, ASSERTED BOTH DIRECTIONS ----------------
    gate_now, arm_now = code[REPOINT_BYTE], u16(code, ARM_ADDR)
    assert not (arm_now == ARM_STOCK and gate_now != GATE_DEAD), \
        "arm == 512 while the gate is STILL repointed to the LIVE cell -- that arm is LIVE and ~5x " \
        "BELOW the stock LERP everywhere, i.e. worse than stock (V61 territory). Refusing to emit."
    assert not (gate_now == GATE_LIVE and arm_now != ARM_GATED), \
        "gate == 0xFB (LIVE) with an arm that is not 5244 -- the other topology's failure mode. " \
        "Refusing to emit."
    assert (gate_now, arm_now) == (GATE_DEAD, ARM_STOCK), \
        "the control path is neither V69's (0xC5/512) nor V67/V68's (0xFB/5244)"
    print(f"    ✅ EDIT-ORDER INVARIANT (V69's form) asserted BOTH WAYS: arm == {ARM_STOCK} ⟹ gate "
          f"== 0x{GATE_DEAD:02X}, and gate == 0x{GATE_LIVE:02X} ⟹ arm == {ARM_GATED}")
    assert bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4]) == bytes.fromhex("847fc597"), \
        "the gate load is not the stock `ld.bu -0x683c[gp],r15`"

    # ---- PART B: the probe (UNCHANGED from the first cut) ------------------------------------
    print("\n  PART B -- THE PROBE, UNCHANGED (every byte identical to the approved first cut).")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    print(f"    cave {len(cave_bytes)}B of the proven {CAVE_EXTENT}B -- extent UNCHANGED (flown 8x), "
          "ZERO spare")
    assert code[CAVE_BASE + 2] == LIVE_IMM, "the liveness immediate is not 0x80"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v69[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical"

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    nr, nw = assert_probe_census(bytes(code), cave_span)
    print("\n    ✅ GATE 1 (RAM ownership) asserted as a MEASUREMENT, from raw bytes, two decoders:")
    for disp, (r, w, wr, _m, _c) in PROBE_CENSUS.items():
        print(f"       gp-0x{disp:04x}  {r}r / {w}w  writers {[hex(a) for a in wr]}"
              "   ⇐ ZERO readers: a pure mirror, nothing can be perturbed")
    print(f"       gp-0x{STATE_DISP:04x}  {nr}r / {nw}w  a LIVE state byte -- READ ONLY by the cave")
    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v70_probe.py CAVE_HEX matches the built cave byte-for-byte,")
        print("       and it no longer describes the SUPERSEDED V68 control path.")

    # ---- STRUCTURAL GATES --------------------------------------------------------------------
    print("\n  GATES:")
    for a in NEIGHBOURS:
        assert bytes(code[a:a + 20]) == bytes(stock[a:a + 20]), \
            f"neighbour record 0x{a:05X} MOVED -- the byte-pattern trap fired"
    print(f"    ✅ all {len(NEIGHBOURS)} mode-11/12 neighbour records byte-identical to STOCK "
          "(mode 11/12 rec0 are byte-IDENTICAL to mode 10's -- the pattern occurs 3x in 40 bytes)")
    for a in UNTOUCHED_RECS:
        assert bytes(code[a:a + 20]) == bytes(stock[a:a + 20]), f"mode-10 rec 0x{a:05X} moved"
    print("    ✅ mode-10 50 km/h and 100 km/h records byte-identical to STOCK ⇒ the highway "
          "1.000x is STRUCTURAL, not tuned")
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == bytes(v69[D2000_BLOCK[0]:D2000_BLOCK[1]]), \
        "V60's falsified slew-blend cells MOVED"
    assert u16(code, V57.PRIVATE_ADDR) == u16(v69, V57.PRIVATE_ADDR), "V57's private cell moved"
    for a, want in V68.SAR_SITES_STOCK:
        assert u16(code, a) == want, f"sar site 0x{a:05X} is not stock"
    print("    ✅ all three `sar` sites stock; V57's private gain cell carried; V60's cells unchanged")
    assert bytes(code[0xC6564:0xC6564 + 40]) == bytes(40), "0xC6564 moved -- bit4's premise is gone"
    print("    ✅ 0xC6564 = 40 zero bytes carried ⇒ r26 structurally inert is still the standing")
    print("       claim, and bit4 is the on-car test of it")

    # ---- THE DOSE, PROVEN BY SWEEP -----------------------------------------------------------
    print("\n  THE DELIVERED MULTIPLIER (V70 vs the STOCK surface), low rate axis:")
    print("      km/h  " + "".join(f"{k:>8}" for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)))
    row = [V69.gain_q10(code, int(k * 64.0625), 100) / V69.gain_q10(stock, int(k * 64.0625), 100)
           for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)]
    print("      mult  " + "".join(f"{x:8.3f}" for x in row))
    grid = [(v, r) for v in range(0, 6401, 32) for r in range(0, 3001, 25)]
    mults = [V69.gain_q10(code, v, r) / V69.gain_q10(stock, v, r) for v, r in grid]
    mx, mn = max(mults), min(mults)
    print(f"    ✅ over {len(grid)} operating points: MAX {mx:.6f}x, MIN {mn:.6f}x")
    assert abs(mx - SCALE) < 1e-9, f"the surface peaks at {mx}x, not exactly {SCALE}.000000x"
    assert abs(mn - 1.0) < 1e-9, f"the surface dips to {mn}x -- NO point may fall below stock"
    print(f"    ✅ every operating point lies inside the FLOWN BRACKET [stock 1.00x, V62/V65 "
          f"{SCALE}.00x] -- both flew flight-clean. Interpolation, not extrapolation.")
    bad = [(v, r) for v, r in grid if v >= HIGHWAY_COUNTS
           and V69.gain_q10(code, v, r) != V69.gain_q10(stock, v, r)]
    assert not bad, f"a >=50 km/h operating point moved: {bad[:4]}"
    n_hw = sum(1 for v, r in grid if v >= HIGHWAY_COUNTS)
    print(f"    ✅ all {n_hw} points at speed >= {HIGHWAY_COUNTS} counts (>= 50 km/h) are BYTE-"
          "IDENTICAL to stock ⇒ EXACTLY 1.000000x at highway, every rate, on every axis scale.")
    print("       ⇐ THE OPERATOR'S COMPLAINT. This is the configuration he reported clean on V69.")
    # ⚠ A SMALL CORRECTION TO THE SPEC'S WORDING, stated rather than quietly relaxed. "EXACTLY
    # 2.000000x for every speed <= 10 km/h" is true at the two EDITED RECORDS' OWN BREAKPOINTS
    # (0 and 640 counts) but NOT strictly between them: the cross-axis LERP's `divq` TRUNCATES
    # toward zero, so an interpolated stock value and its 2x counterpart can each land up to one
    # count low and the ratio is not exactly preserved. The worst case over the whole band is
    # 0.000390 (0.0195%), at 637 counts. Physically immaterial -- one count of a Q10 gain -- but
    # the assertion must claim what is TRUE, or it is the kind of gate that cannot fail honestly.
    for counts in (0, 640):
        got = V69.gain_q10(code, counts, 0) / V69.gain_q10(stock, counts, 0)
        assert abs(got - SCALE) < 1e-12, \
            f"{counts} counts at rateKey 0 delivers {got}x, not exactly {SCALE}.000000x"
    band = [abs(V69.gain_q10(code, v, r) / V69.gain_q10(stock, v, r) - SCALE)
            for v in range(0, 641, 4) for r in range(0, 401, 8)]
    assert max(band) < 1e-3, f"the <=10 km/h band deviates from {SCALE}x by {max(band)}, not truncation"
    print(f"    ✅ EXACTLY {SCALE}.000000x at rateKey 0 at both edited breakpoints (0 and 640 counts);")
    print(f"       between them the integer LERP truncates, worst deviation {max(band):.6f} "
          f"({max(band) / SCALE * 100:.4f}%) -- `divq` rounding, not a shaping error")
    # 🛑 SATURATION -- the metric that got WORSE with V69's dose, and halving it fixes.
    peak = max(V69.gain_q10(code, v, r) for v in range(0, 6401, 64) for r in range(0, 3001, 25))
    sat = 8192 * 1024 // peak
    print(f"    ✅ SATURATION: peak gain {peak} ⇒ the r24 lane rails at |dtorque| ~{sat}, vs the "
          f"repo-recorded max 839 (margin {sat / 839:.2f}x) and V69's own flight max 633.9 "
          f"({sat / 633.9:.2f}x). At V69's 4x the rail was 683 -- BELOW the recorded max.")
    assert sat > 839, "the r24 lane can rail below the repo-recorded max |dtorque| -- dose too high"
    assert 5120 * peak < 2 ** 31, "dtorque_clamp * peak gain overflows int32"

    # ---- CRC ---------------------------------------------------------------------------------
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in (CAVE_BASE, SURFACE[0][0], SURFACE[-1][0])})
    print(f"\n  CRC -- {len(blocks)} blocks move relative to the V69 source:")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")

    # ---- ✅ THE DEFINING IDENTITY: V70 == V69 + 4 surface halfwords + the cave ---------------
    cave_range = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    surf_bytes = {a + k for a, _, _, _ in SURFACE for k in (0, 1)}
    d69 = [i for i in range(0x13000, 0x100000) if code[i] != v69[i]]
    f69 = [d for d in d69 if d not in crc_only]
    stray = [d for d in f69 if d not in cave_range | surf_bytes]
    assert not stray, f"UNATTRIBUTED functional bytes vs V69: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V69: {len(d69)} bytes = {len(f69)} functional "
          f"({len(surf_bytes)} surface + {len(f69) - len(surf_bytes)} cave) + "
          f"{len(d69) - len(f69)} CRC")
    for d in sorted(f69):
        where = "PART B cave" if d in cave_range else "PART A surface (x4 -> x2)"
        print(f"    0x{d:05X}  {v69[d]:02X} -> {code[d]:02X}   {where}")
    print("    ✅ V70 IS V69 PLUS FOUR SURFACE HALFWORDS AND A NEW CAVE, AND NOTHING ELSE.")

    d68 = [i for i in range(0x13000, 0x100000) if code[i] != stock[i]]
    print(f"\n  EXACT DIFF vs V68 (the build on the car): {len(d68)} bytes -- the gate byte, the arm, "
          "the surface, the cave and 3 CRC words")

    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    # ---- ENCODE, then RE-RUN every gate on the DECODED READBACK -----------------------------
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
    FF.assert_x31_checksum(rwd, "V70 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v69)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    print("\n  READBACK -- decoded from the .rwd and re-gated:")
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    assert dec[REPOINT_BYTE] == GATE_DEAD, "readback gate byte wrong"
    assert u16(dec, ARM_ADDR) == ARM_STOCK, "readback arm wrong"
    assert not (u16(dec, ARM_ADDR) == ARM_STOCK and dec[REPOINT_BYTE] != GATE_DEAD), \
        "readback violates the edit-order invariant"
    for addr, _old, new, name in SURFACE:
        assert u16(dec, addr) == new, f"readback {name} wrong"
    assert dec[CAVE_BASE + 2] == LIVE_IMM, "readback liveness immediate wrong"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_census(bytes(dec), cave_span)
    for a in NEIGHBOURS:
        assert bytes(dec[a:a + 20]) == bytes(stock[a:a + 20]), "readback neighbour moved"
    rb_stray = [i for i in range(0x13000, 0x100000)
                if dec[i] != v69[i] and i not in cave_range and i not in surf_bytes
                and i not in crc_only]
    assert not rb_stray, f"readback differs from V69 outside the attributed set: {rb_stray[:8]}"
    assert not [(v, r) for v, r in grid if v >= HIGHWAY_COUNTS
                and V69.gain_q10(dec, v, r) != V69.gain_q10(stock, v, r)], \
        "readback moved a >=50 km/h operating point"
    nbad2 = walk_all_blocks(bytes(dec))
    assert nbad2 == 0, f"readback CRC chain FAILED: {nbad2} mismatching block(s)"
    print("    ✅ payload, gate byte, arm, the edit-order invariant, all four surface halfwords,")
    print("       the WHOLE 68-byte cave, the probe census (GATE 1 re-measured), every neighbour,")
    print("       the >=50 km/h structural-stock sweep, identity to V69 outside the attributed set,")
    print("       and the full CRC chain -- all re-verified ON THE DECODED READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print(f"  V70 BUILT (RE-CUT). V69's topology at HALF the dose + the approved probe.")
    print(f"  DOSE {SCALE}.000000x at creep -> EXACTLY 1.000000x at and above 50 km/h. Max anywhere "
          f"{mx:.6f}x, min {mn:.6f}x ⇒ inside the flown bracket everywhere.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
