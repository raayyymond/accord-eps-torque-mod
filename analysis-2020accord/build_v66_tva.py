#!/usr/bin/env python3
"""build_v66_tva.py -- V66 = V65 with the rate lane back at STOCK, plus a GATE PROBE cave.

WHAT V66 IS
-----------
The operator's spec: *V38 4x LKAS enable, steer-to-zero, live telemetry on the most valuable bits,
no V62-style edits -- leave grind #1 as V38 has it.* A stable build for a significantly longer drive.

    0x3AC20  42A9 -> 42AA   sar 0x9,r8 -> sar 0xa,r8    r24 lane: revert V62's doubling
    0x3AB76  32A9 -> 32AA   sar 0x9,r6 -> sar 0xa,r6    r26 lane: revert V62's doubling
    0x3AB70  32AA (UNTOUCHED)                           a DIFFERENT site V62 deliberately never moved

=> the torsion-bar rate lane returns to EXACTLY STOCK. Everything else is carried byte-identical from
V65: V57's 0xC646C decoupling with the private forward cal 0xC6CD0 = 3564, the 0xC62EA = 0
steer-to-zero, the 0xC64DE = 27 re-engage ramp, V38's 4x LKAS enable. NO calibration byte moves --
the CAL block is asserted byte-identical to V65's and its CRC word asserted UNCHANGED, machine proof,
printed on every build.

★ WHY THE REVERT IS THE RIGHT MOVE, AND WHY V66 IS ALSO A CONFIRMATORY INTERVENTION
------------------------------------------------------------------------------------
Corner-conditioned tail maxima, Kd = 1x vs Kd = 2x, 219 blocks:

    band        ratio 2x / 1x
    1- 4 Hz      1.01     <- the DRIVER band, flat: the control that says this is not a global gain
    10-16 Hz     0.80
    18-22 Hz     0.35     <- grind #1, CUT 2.9x   (this is V62's measured fix)
    24-28 Hz     2.66
    30-40 Hz     2.98
    40-49 Hz    11.71     <- grind #2, RAISED 11.7x   (p = 0.0003)

A MONOTONE response with a crossover at 22-24 Hz and a flat driver band. V62's x2 bought grind #1 at
the direct cost of grind #2, and the exchange rate is 2.9x down against 11.7x up. Reverting both `sar`
immediates is therefore the correct choice for a long, stable drive AND a confirmatory intervention:
the same lever pushed back the other way must move both bands back, in the same monotone pattern. A
null on V66 would mean the band table is not causal, which no other build can test as cheaply.

V66 is also the clean Kd = 1x CONTROL for the three-dose comparison V61(0x) / V66(1x) / V62(2x), on
one instrument, with everything else held fixed.

THE PROBE -- CAN 0x14A byte4, 100 Hz, bits 7:3 (bits 2:0 stay stock STEER_SENSOR_STATUS)
-----------------------------------------------------------------------------------------
V66 is the pre-flight for V67, which repoints ONE BYTE at 0x3AA96 so that `0xC6446` becomes an
LKAS-only gain override for r24 (`docs/V66-V67-DESIGN.md`). Every bit below measures one load-bearing
unknown in that design. All three payload cells are plain `!= 0` tests on gp-relative BYTE cells --
no thresholds, no arithmetic, no new condition codes, no new opcodes.

    bit7 = 1                    LIVENESS. field == 0 => the cave did not fire => the reading is VOID
    bit6 = gp-0x6806 != 0       gate candidate A -- has prior on-car data (2 transitions / 180 s)
    bit5 = gp-0x67f5 != 0       gate candidate B -- its toggle rate is the KILL CRITERION: a gain
                                keyed on a signal that toggles at 15-60 Hz is a parametric pump,
                                the exact failure mode V58/V59/V60 chased for three builds
    bit4 = gp-0x67fe != 0       gate candidate C -- semantics DISPUTED, one bit of duty settles it
    bit3 = 0                    UNUSED -- see the budget section. Never set by this cave.

⚠ THE PARITY AND WIDTH OF EVERY CELL ENCODED, as the brief requires
-------------------------------------------------------------------
    cell         disp u16   parity   width   ld.bu opcode   emitted bytes   provenance
    gp-0x6806      0x97FA   EVEN     BYTE    0x3C           8437fb97        BYTE-IDENTICAL @0x2A8C0
    gp-0x67f5      0x980B   *ODD*    BYTE    0x3D           a4370b98        field-decomposed (WEAK)
    gp-0x67fe      0x9802   EVEN     BYTE    0x3C           84370398        BYTE-IDENTICAL @0x34CE4
    gp-0x683c      0x97C4   EVEN     BYTE    0x3C           (not emitted)   V67's repoint site

Width is not assumed: the census below asserts that EVERY access to each cell image-wide is `ld.bu`
or `st.b`, so a halfword read would fail the build rather than silently straddle the neighbour.

🛑 gp-0x67f5's ODD PARITY, AND WHAT IT COSTS V67 (the probe is unaffected)
--------------------------------------------------------------------------
For `ld.bu` the displacement's bit 0 lives in **hw1 bit 5** -- the opcode field's own low bit, 0x3C
vs 0x3D -- and hw2's LSB is the width selector, always 1. So repointing the EVEN-displacement
`ld.bu -0x683c[gp],r15` @0x3AA94 (`84 7f c5 97`) to gp-0x67f5 is NOT a clean hw2 edit: it needs
hw1 0x3C -> 0x3D as well, i.e. `0x3AA94: 84 -> A4` AND `0x3AA96..97: c5 97 -> 0b 98` -- THREE bytes
across BOTH halfwords, versus ONE byte for an even-displacement target. gp-0x6806 (0x97FA) and
gp-0x67fe (0x9802) are both EVEN and stay one-byte repoints.
   ⚠ Mirror-image trap, recorded because getting it backwards is the same bug twice: for `st.b`
   STORES hw2 IS the exact displacement and hw1 bit 5 is a fixed opcode bit with no displacement
   meaning. The two forms disagree, which is why every emitted load below is decoded back through
   scan_gp_accesses' independent decoder and its displacement asserted.

🛑 gp-0x67f5 IS NOT A CLEAN 0 / NON-ZERO FLAG -- IT IS THREE-VALUED {0, 1, 0xFF}
--------------------------------------------------------------------------------
Read directly from FUN_00041eec (body 0x41EEC-0x42375, which contains ALL THREE of its writers, so
that function is the sole writer of the cell). Ghidra listing verified byte-identical to the V65
image over the whole body before it was trusted:

    0x42222  cmp r0,r12              ; r12 = gp-0x67f4, the validity flag
    0x42224  bne 0x42230
    0x42226  movea 0xff,r0,r13
    0x4222A  st.b r13,-0x67f5[gp]    ; *** writes 0xFF *** -- the INVALID/NOT-EVALUATED sentinel
    ...
    0x42256  mov 0x1,r7
    0x42258  st.b r7,-0x67f5[gp]     ; *** writes 1 ***  -- latched, after a debounce
    ...
    0x42288  st.b r0,-0x67f5[gp]     ; *** writes 0 ***  -- cleared, after a debounce

A plain `!= 0` test therefore CONFLATES the latched state (1) with the invalid sentinel (0xFF). That
is a real loss of meaning and it is reported rather than papered over. The build keeps the `!= 0`
test as specified -- deviating on semantics without being asked is worse than reporting -- and the
decoder carries a disambiguation rule: 0xFF is entered only while gp-0x67f4 == 0, a persistent
condition, so a bit5 that is HIGH continuously from the first frame is the sentinel, whereas a bit5
that debounces up and down is the latch. Stated as a hypothesis, not a fact.

⚠ AND THE "driver-torque hands-on gate" READING IS NOT SUPPORTED BY THE CODE
-----------------------------------------------------------------------------
FUN_00041eec reads NO torque cell. It reads the voted vehicle speed `gp-0x6a5e` into r7, then loops
four slots (`cmp 0x4,r10` @0x4210C) computing |slot| and |speed - |slot|| out of the halfword cells
gp-0x6a38 / -0x6a3c / -0x6a40 / -0x6a44, with gp-0x6a46 handled separately, and reduces them to a
max deviation r28 clamped to 0x7D00. The latch is then

    r28 >= cal tp+0x731e (0xC631E = 640) for cal tp+0x74e7 (0xC64E7 = 10, a BYTE) consecutive ticks

640 counts is 9.99 km/h on this ROM's established speed axis (`0xC6010 = [0,640,3200,6400]` =
0 / 9.99 / 49.95 / 99.9 km/h). So gp-0x67f5 reads as a DEBOUNCED WHEEL-SPEED-vs-VEHICLE-SPEED
PLAUSIBILITY LATCH -- a fault flag -- not a hands-on gate. If that is right it is near-constant 0 in
normal driving, its toggle rate is trivially ~0, and one bit is being spent on a foregone conclusion:
the V64 mistake. It is built as specified because the operator ranked it highest and the measurement
is cheap, but the ranking should be revisited BEFORE the drive, not after. Swapping it is a one-line
change to CELLS.

⚠ gp-0x67fe: FIVE WRITERS, NOT FOUR, AND IT IS LOCKSTEP-SHADOWED
-----------------------------------------------------------------
The subagent report of "sole writer FUN_0003bd7c, 4 st.b at 0x3BDB8/0x3BE4E/0x3BE5A/0x3BE7A" is
INCOMPLETE. Both decoders find a FIFTH store, `st.b r0,-0x67fe[gp]` @0x3E770, inside FUN_0003e760 --
a lockstep reset routine that clears the cell together with its shadow gp-0x4c3a and calls
FUN_0006b9fa on a mismatch. So gp-0x67fe is LOCKSTEP-SHADOWED (pair gp-0x4c3a), which does not
affect a read-only probe but is load-bearing for any future edit of the cell. 55 readers.
Its `{1,2}` test that the report cites is real: `ld.bu -0x67fe[gp],r10` @0x41FF2 / `cmp 0x2,r10`
@0x41FFA, inside the very FUN_00041eec above -- so the two candidate cells are coupled, and the
duty of bit4 is what decides between "LKAS engage state" and "base-assist substate". Measured, not
argued, exactly as instructed.

🛑 BIT 3 IS DROPPED, AND HERE IS THE ARITHMETIC RATHER THAN AN APOLOGY
----------------------------------------------------------------------
The final spec put `gp-0x683c` -- THE CONTROL -- on bit 3 and said to drop from the bottom. It does
not fit, and the budget is not negotiable by cleverness:

    FIXED OVERHEAD                                                     bytes
      movea 0x80,r0,r7        liveness -- imm16, no 2-byte form exists     4
      ld.bu -0x1514[gp],r6    read the CAN-330 payload byte                4
      andi  0x7,r6,r6         preserve the live STEER_SENSOR_STATUS        4
      or    r7,r6                                                          2
      st.b  r6,-0x1514[gp]                                                 4
      movea -0x1518,gp,r6     the DISPLACED instruction -- mandatory       4
      jmp   [lp]              mandatory                                    2
                                                                    ------ 24
    PER RUNG (four SEPARATE cells => four SEPARATE loads; V65 shared ONE load across four compares)
      ld.bu -0xNNNN[gp],r6                                                 4
      cmp   0x1,r6            V850 has no load-and-set-flags                2
      blt   +6                                                             2
      movea 0xBB,r7,r7        imm16 -- the only 2-byte alternative is
                              Format-II `add imm5`, an UNPINNED opcode      4
                                                                    ------ 12

    24 + 4*12 = 72 > 68.  Reordering to read the payload FIRST and mask straight into r7
    (`andi 0x7,r6,r7`) drops the `or` and folds the liveness movea, giving 22 + 48 = 70 -- STILL over,
    and it buys that at the cost of a reg2 field combination no flashed instruction carries.
    Three rungs in the maximally-pinned ordering = 24 + 36 = 60. That is what is built.

Every alternative was priced and every one is >= 12 bytes/rung: `cmp r0,r6` is the same 2 bytes as
`cmp 0x1,r6`; `setf`+`shl`+`or` is 14; shift-accumulating into r7 is 14; `shl 3,r6 / or r6,r7` is 8
but is WRONG unless the cell is provably 0/1 -- and `st.b` keeps only the low 8 bits, so any cell
value >= 2 would bleed into a NEIGHBOURING probe bit. gp-0x67f5 is DEMONSTRABLY not 0/1 (it takes
0xFF, which would shift straight over the whole field), so that shortcut is unsafe, not merely
unproven.

⚠ WHAT DROPPING BIT 3 ACTUALLY COSTS, stated plainly: V66 no longer measures gp-0x683c ON-CAR, so
the DEAD-CELL claim V67 rests on is now supported by STATIC evidence only -- 1 reader, 0 writers,
0 extended-form candidates, reproduced by two independent decoders on every build and asserted in
assert_cell_census(). What that cannot rule out is a non-zero value left by RAM init, or a write
through a computed pointer that no displacement scan can see (the gp-0x61a0 precedent). If V67 is
flashed and behaves as if 0xC6446 were already live, this is the first thing to re-examine.

⚠ `cmp 0x1,r6` + `blt` IS the `!= 0` test, and it introduces NOTHING NEW
------------------------------------------------------------------------
`ld.bu` ZERO-EXTENDS a byte, so r6 is in [0,255] and SIGNED `< 1` is exactly `== 0`. That lets the
whole cave run on `cmp 0x1,r6` (6132, BYTE-IDENTICAL @0x14D46) and `blt +6` (b605, BYTE-IDENTICAL
@0x1C006) -- the two encoders V65 already pinned and flew. No `be`/`bz` condition code is introduced,
and the polarity is the natural one (bit set = cell non-zero) rather than V59's inverted thermometer.

ENCODER PROVENANCE -- every emitted instruction pinned byte-for-byte to a real instance
----------------------------------------------------------------------------------------
🛑 V850 `ld.bu` carries the displacement's BIT 0 in **hw1 bit 5** (the opcode field's own low bit,
   0x3C vs 0x3D), NOT in hw2 -- hw2's LSB is the ld.bu/ld.hu width selector and is always 1.
   `ld.h`/`ld.w` and `ld.hu` instead use `hw2 = disp | 1`. Encoding -0x683c with the ODD-displacement
   opcode would silently read gp-0x683B, which is a REAL adjacent cell with four st.b writers.
   Every emitted load is therefore decoded back through scan_gp_accesses.decode_op(), which is an
   INDEPENDENT decoder, and its displacement asserted.

    ld.bu -0x6806[gp],r6   8437fb97   BYTE-IDENTICAL to the real instance @0x2A8C0
    ld.bu -0x67fe[gp],r6   84370398   BYTE-IDENTICAL to the real instance @0x34CE4 (also @0x36026,
                                      0x3BE3C, 0x3E46A, 0x40888 -- five instances)
    ld.bu -0x67f5[gp],r6   a4370b98   ⚠ WEAKER: no `ld.bu -0x67f5[gp],r6` exists image-wide, so this
                                      is a THREE-WAY field decomposition. hw1 a437 == the real
                                      `ld.bu -0x671d[gp],r6` @0x3AB98 (op 0x3D = the ODD-displacement
                                      form, reg1=gp, reg2=r6); hw2 0x980b == the real
                                      `ld.bu -0x67f5[gp],r7` @0x21DC0, which differs from ours in the
                                      reg2 field ONLY. Both halves are real; the COMBINATION is ours.
    cmp   0x1,r6           6132       BYTE-IDENTICAL @0x14D46            (V65's pin)
    blt   +6               b605       BYTE-IDENTICAL @0x1C006            (V65's pin)
    movea 0x80,r0,r7       203e8000   flashed on V54/V55/V59/V64/V65
    movea 0xBB,r7,r7       273eBB00   flashed on V54/V55/V59/V64/V65 (immediate differs only)
    ld.bu -0x1514[gp],r6   8437edea   flashed since V31P
    andi  0x7,r6,r6        c6360700   flashed since V31P
    or    r7,r6            0731       flashed since V31P
    st.b  r6,-0x1514[gp]   4437ecea   flashed since V31P

THE CELL CENSUS -- the required second method, by TWO independent decoders
---------------------------------------------------------------------------
Re-derived from raw bytes on every build, by V64.gp_access_census (pattern construction, even offsets)
AND by scan_gp_accesses.scan (per-opcode decode, EVERY byte offset) plus its 48-bit extended-
displacement brute force. Both must agree, exactly:

    gp-0x6806   13 ld.bu readers, 16 st.b writers    the arbitration output (LKAS active)
    gp-0x67f5    8 ld.bu readers,  3 st.b writers    ALL THREE in FUN_00041eec, values {0xFF, 1, 0}
    gp-0x67fe   55 ld.bu readers,  5 st.b writers    FIVE, not four -- 0x3E770 is in FUN_0003e760
    gp-0x683c    1 ld.bu reader,   0 writers, 0 extended-form hits   <-- THE DEAD-CELL CLAIM
    gp-0x671d   14 ld.bu readers,  2 st.b writers    (asserted, though V66 cannot probe it)

Every access to every one of these is a BYTE access; a non-byte hit would mean the cell is not what
this probe assumes and the build stops.

CAVE DISCIPLINE -- caves are this kit's ONLY bricking class (V24, V27, V48B)
----------------------------------------------------------------------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte proven extent as V55/V57/V58/V59/V64/V65 -- all
SEVEN flew clean. Read-only; r6/r7 only; the sole write is the existing CAN-330 payload byte
gp-0x1514 with bits 2:0 preserved, so GATE 1 stays VACUOUS and no new RAM cell is claimed.
60 of 68 bytes used, 8 spare -- and a fourth rung needs 12, which is the whole of the bit-3 story.

GATE 1 (RAM ownership): VACUOUS. Asserted as a MEASUREMENT, not a claim: the census shows the cave
    reads each cell exactly once and writes none of them, and the emitted listing contains EXACTLY
    ONE store instruction, the CAN-330 payload byte.
GATE 2 (closed-loop stability): VACUOUS for the probe -- its only output is a TX payload byte no
    control path reads. The two `sar` reverts need no stability argument at all: they restore the
    STOCK instruction stream, which is the configuration every pre-V62 build flew.
    *** Still CODE in the 1 kHz TX path, which is why base/hook/extent are reused, not moved.

⚠ A CONSTANT 0x87 IS AMBIGUOUS WITH V64's NULL AND V65's NEUTRAL BUCKET
-----------------------------------------------------------------------
Under V66, 0x87 is a LEGITIMATE reading -- "cave fired, all three gates zero". It is byte-identical
to V64's null (detector never armed, 14,980 frames) and to V65's NEUTRAL bucket. The decoder refuses
to interpret it and names the .rwd that must be confirmed. That trap has already cost this kit one
session.

PRE-COMMITTED INTERPRETATION -- written before the drive so it cannot be fitted afterwards
-------------------------------------------------------------------------------------------
    ANY of bits 6/5/4 toggles inside 15-60 Hz
        => that cell is DISQUALIFIED as a gate. A gain switching near the mode frequency is a
           parametric pump. If it is bit6, V67 as currently drawn is CANCELLED.
    bit6 toggles at <= ~1 Hz AND its duty tracks engagement
        => gate candidate A is usable. Proceed with V67 (0x3AA96 c5 -> fb, 0xC6446 512 -> 6144).
    bit4 duty ~= 100%
        => gp-0x67fe is the BASE-ASSIST substate the golden model calls it, non-zero whenever the
           car is running, and WORTHLESS as an LKAS gate. Retire candidate C.
    bit4 duty TRACKS ENGAGEMENT
        => gp-0x67fe is the LKAS engage state after all, it is EVEN-displacement (a one-byte
           repoint), and it becomes the best candidate available. This is the whole reason it is
           on the car instead of in a document.
    bit5 HIGH continuously from the first frame
        => that is most likely the 0xFF INVALID sentinel, not a latched gate. See the semantics
           section; the `!= 0` test cannot separate 1 from 0xFF.
    bit5 near-constant 0
        => consistent with the wheel-speed plausibility reading above, i.e. a fault latch. Retire
           candidate B rather than reading "quiet gate = good gate".
    field == 0 on any frame
        => the cave did not fire on that frame. Any non-zero count is a hard stop, not a filter.
    ⚠ NOT TESTED BY THIS BUILD: gp-0x683c (the control, cut for budget) and gp-0x671d (the masking
      risk, dropped by the final spec). Neither absence may be read as a pass.

    ⚠ 100 Hz sampling => NYQUIST 50 Hz. The 15-60 Hz kill band is NOT fully observable: a true 58 Hz
      toggle aliases to 42 Hz. The decoder says so instead of reporting a number that looks resolved.
      This is the same alias `docs/V66-V67-DESIGN.md` states up front for the 41.64/58.86 Hz pair.

BASE = V65. V61's tap kill, V62's doubling and V63's raised arms are ALL asserted ABSENT on the
output; V63.assert_untouched -- which V65 itself could not run, because V65 carries V62's shifts --
is run here in full.

Decoder: rlog-tools/decode_v66_gateprobe.py
"""
import hashlib
import itertools
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
import build_v64_tva as V64                # noqa: E402  (census helper)
import build_v65_tva as V65                # noqa: E402
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT second decoder)

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged from V55/V57/V58/V59/V64/V65
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- the probe bits -------------------------------------------------------------------------------
BIT_LIVE = 0x80
BIT_6806, BIT_67F5, BIT_67FE = 0x40, 0x20, 0x10
BIT_UNUSED = 0x08              # bit3: never set by this cave. A set bit3 means the build is not V66.

# (gp displacement, bit, label, what it decides).  EMISSION ORDER == descending bit order.
CELLS = (
    (0x6806, BIT_6806, "gate_6806",
     "LKAS gate candidate A -- has prior on-car data (2 transitions / 180 s)"),
    (0x67f5, BIT_67F5, "gate_67f5",
     "gate candidate B -- THREE-VALUED {0,1,0xFF}; see the semantics section"),
    (0x67fe, BIT_67FE, "gate_67fe",
     "gate candidate C -- semantics DISPUTED; one bit of duty settles it"),
)

# NOT probed, but their structure is asserted on every build because V67's design depends on both:
#   gp-0x683c -- the dead gate V67 repoints. Its DEAD-CELL claim is verified STATICALLY here (1 reader,
#                0 writers, 0 extended-form hits, by two decoders) but NOT on-car; see the budget note.
#   gp-0x671d -- the masking risk. V64 measured it 0 across 14,980 frames; dropped per the final spec.
CONTROL_DISP = 0x683c
MASK_DISP = 0x671d

COND_BLT = V65.COND_BLT        # 0x6, SIGNED <  -- pinned to the real `blt` @0x1C006
CMP_LEVEL = 1                  # `cmp 0x1,r6`; ld.bu zero-extends, so signed < 1 IS == 0

# ---- encoder pins, all inherited from V65 and re-asserted here on the built image -----------------
PIN_CMP_P1_R6 = V65.PIN_CMP_P1_R6            # (0x14D46, 6132, 1, r6)  BYTE-IDENTICAL to ours
PIN_BLT6 = V65.PIN_BLT6                      # (0x1C006, b605)         BYTE-IDENTICAL to ours

# Real `ld.bu` donors. (address, bytes, displacement, reg2).
PIN_LDBU_6806_R6 = (0x2A8C0, bytes.fromhex("8437fb97"), 0x6806, 6)    # BYTE-IDENTICAL to ours
PIN_LDBU_67FE_R6 = (0x34CE4, bytes.fromhex("84370398"), 0x67fe, 6)    # BYTE-IDENTICAL to ours
PIN_LDBU_67F5_R7 = (0x21DC0, bytes.fromhex("a43f0b98"), 0x67f5, 7)    # hw2 donor, ODD-disp opcode
PIN_LDBU_671D_R6 = (0x3AB98, bytes.fromhex("a437e398"), 0x671d, 6)    # hw1 donor for the ODD form
PIN_LDBU_683C_R15 = (0x3AA94, bytes.fromhex("847fc597"), 0x683c, 15)  # V67's repoint site, must stay

# ⚠ WEAKER PROVENANCE, stated as the brief requires. gp-0x67f5 has NO `ld.bu ...,r6` instance
# image-wide, so our load is pinned by a THREE-WAY field decomposition instead of byte-identity:
# hw1 from the real ODD-displacement `ld.bu -0x671d[gp],r6` @0x3AB98, hw2 from the real
# `ld.bu -0x67f5[gp],r7` @0x21DC0. Both halves are real; the COMBINATION is ours. The other two
# cells are byte-identical to real instances and carry no such caveat.
WEAK_PIN_DISPS = (0x67f5,)

TAG = "LKAS-4x-mss0-decouple0xC646C-ratelane-STOCK-gateprobe3-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V66-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v66_plain_image.bin"))
V65_BIN = str(plain_image_path("_v65_plain_image.bin"))
V62_BIN = str(plain_image_path("_v62_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def decode_fmt2(halfword):
    """V850 Format-II split: imm5 = bits[4:0] (SIGNED), opcode = bits[10:5], reg2 = bits[15:11]."""
    imm = halfword & 0x1F
    return {"imm5": imm - 32 if imm & 0x10 else imm,
            "imm_field": imm,
            "opcode": (halfword >> 5) & 0x3F,
            "reg2": (halfword >> 11) & 0x1F}


def decode_ldbu(raw):
    """Decode an emitted 4-byte load through the INDEPENDENT scan_gp_accesses decoder.

    🛑 This is the hw1-bit-5 guard, and it is the reason it is not done by re-reading our own
    encoder's inputs: `ld.bu` puts the displacement's bit 0 in the OPCODE FIELD (0x3C / 0x3D), so a
    parity slip silently addresses the NEIGHBOURING cell and every other field still looks perfect.
    Returns (mnemonic, gp offset as a POSITIVE kit-convention number, reg1, reg2).
    """
    hw1, hw2 = struct.unpack("<HH", raw)
    d = SCAN.decode_op((hw1 >> 5) & 0x3F, hw1, hw2)
    assert d is not None, f"{raw.hex()} is not a Format-VII load/store at all"
    mnem, disp_u16, _is_store = d
    return mnem, (0x10000 - disp_u16) & 0xFFFF, hw1 & 0x1F, (hw1 >> 11) & 0x1F


# =======================================================================================================
# Encoders -- every one inherited and self-checked, or pinned to a real instance above.
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V65._self_check_encoders()          # inherits V62/V59/V58/V57/V55/V54/FF self-checks

    # ---- gp IS r4 on this firmware. Every gp-relative instruction we emit must carry reg1 = 4.
    assert GP == 4, f"GP is r{GP}; every real gp-relative instance in this image carries reg1 = r4"

    # ---- the three cell loads. Each is decoded back through SCAN's independent decoder and its
    # DISPLACEMENT asserted -- the only check that actually catches an hw1-bit-5 parity slip.
    for disp, _bit, name, _why in CELLS:
        raw = V55.ldbu_any(-disp, R6)
        mnem, got_disp, reg1, reg2 = decode_ldbu(raw)
        assert mnem == "ld.bu", f"{name}: emitted {mnem}, not ld.bu"
        assert got_disp == disp, \
            f"{name}: the emitted load addresses gp-0x{got_disp:04x}, NOT gp-0x{disp:04x} -- this is " \
            "the hw1-bit-5 trap and the neighbouring cell is a real, live cell"
        assert (reg1, reg2) == (GP, R6), f"{name}: reg1/reg2 are r{reg1}/r{reg2}"
        # the opcode field must be 0x3C or 0x3D and must match the displacement's parity
        hw1 = struct.unpack_from("<H", raw, 0)[0]
        op = (hw1 >> 5) & 0x3F
        assert op == (0x3C | (((0x10000 - disp) & 0xFFFF) & 1)), \
            f"{name}: opcode field 0x{op:02X} does not match the displacement parity"
        assert struct.unpack_from("<H", raw, 2)[0] & 1 == 1, \
            f"{name}: ld.bu hw2 LSB must be SET -- a clear LSB is the ld.h/st.h form"
        # 🛑 it must NOT collapse onto a STORE or onto a wider load
        assert raw != FF.stb(R6, -disp, GP), f"{name}: the emitted load collapsed onto an st.b"
        assert raw != FF.ldhu(disp, R6) and raw != V55.ldh(disp, R6), \
            f"{name}: ld.bu collapsed onto a HALFWORD load -- it would straddle the neighbouring cell"

    # BYTE-IDENTICAL to a real instance, register field included -- the strongest provenance there is.
    for pin in (PIN_LDBU_6806_R6, PIN_LDBU_67FE_R6):
        assert V55.ldbu_any(-pin[2], R6) == pin[1], \
            f"ld.bu -0x{pin[2]:04x}[gp],r6 must be byte-identical to the instance @0x{pin[0]:05X}"
        assert pin[2] not in WEAK_PIN_DISPS, f"gp-0x{pin[2]:04x} is both byte-identical and 'weak'"
    # THREE-WAY decomposition for the one cell that has no byte-identical instance image-wide:
    #   hw1 (opcode + reg1 + reg2) from one real instance, hw2 (displacement) from another.
    for disp, hw1_pin, hw2_pin in ((0x67f5, PIN_LDBU_671D_R6, PIN_LDBU_67F5_R7),):
        assert disp in WEAK_PIN_DISPS, f"gp-0x{disp:04x} is field-decomposed but not declared weak"
        ours = V55.ldbu_any(-disp, R6)
        assert ours[:2] == hw1_pin[1][:2], \
            f"ld.bu -0x{disp:04x}[gp],r6 hw1 {ours[:2].hex()} is not the real hw1 " \
            f"{hw1_pin[1][:2].hex()} @0x{hw1_pin[0]:05X}"
        assert ours[2:] == hw2_pin[1][2:], \
            f"ld.bu -0x{disp:04x}[gp],r6 hw2 {ours[2:].hex()} is not the real hw2 " \
            f"{hw2_pin[1][2:].hex()} @0x{hw2_pin[0]:05X}"
        # the hw2 donor must differ from ours in the reg2 field ONLY
        a = struct.unpack("<H", ours[:2])[0]
        b = struct.unpack("<H", hw2_pin[1][:2])[0]
        assert (a & 0x07FF) == (b & 0x07FF), \
            f"the donor @0x{hw2_pin[0]:05X} differs from ours in more than the reg2 field"
        assert (b >> 11) == hw2_pin[3] and (a >> 11) == R6, "donor/emitted reg2 fields are not as read"
    for addr, raw, disp, reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_67FE_R6, PIN_LDBU_67F5_R7,
                                  PIN_LDBU_671D_R6, PIN_LDBU_683C_R15):
        assert struct.unpack("<H", raw[:2])[0] & 0x1F == GP, \
            f"the donor @0x{addr:05X} does not carry reg1 = r4 -- gp is not r4 after all"
        assert decode_ldbu(raw) == ("ld.bu", disp, GP, reg2), \
            f"the donor @0x{addr:05X} does not decode as `ld.bu -0x{disp:04x}[gp],r{reg2}`"
    # the three emitted loads must be DISTINCT -- a copy/paste would give three reads of one cell
    loads = [V55.ldbu_any(-d, R6) for d, _, _, _ in CELLS]
    assert len(set(loads)) == len(CELLS), "two cell loads are byte-identical -- a displacement is wrong"

    # ---- cmp 0x1,r6 -- BYTE-IDENTICAL to the real instance @0x14D46, reg2 included.
    ours = V55.cmp_imm5(CMP_LEVEL, R6)
    assert ours == PIN_CMP_P1_R6[1], \
        f"cmp 0x1,r6 must be byte-identical to the real instance @0x{PIN_CMP_P1_R6[0]:05X}"
    f = decode_fmt2(struct.unpack("<H", ours)[0])
    assert (f["opcode"], f["reg2"], f["imm5"]) == (0x13, R6, CMP_LEVEL), f"cmp 0x1,r6 decodes as {f}"

    # ---- blt +6 -- SIGNED, byte-pinned. 🛑 bl (0x1) is the UNSIGNED partner; on a ZERO-EXTENDED byte
    # the two happen to agree, but the assertion is kept because the encoder is shared with V65 where
    # they do NOT agree, and a silent collapse there would be invisible from here.
    assert COND_BLT == 0x6, f"blt must be condition 6, got {COND_BLT}"
    assert COND_BLT != V55.COND_BL, "blt collapsed onto the UNSIGNED bl"
    assert FF.bcond(COND_BLT, +6) == PIN_BLT6[1], \
        f"blt +6 fails the real `blt 0x1c00c` @0x{PIN_BLT6[0]:05X}"
    assert struct.unpack("<H", FF.bcond(COND_BLT, +6))[0] & 0xF == COND_BLT, \
        "bcond does not carry the condition in bits 3:0"

    # ---- the bit-set moveas: V54's flashed reg1=r7 bias form, different immediates.
    for _d, bit, name, _w in CELLS:
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"{name}: movea 0x{bit:x},r7,r7 bad"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"

    # ---- the bit map: liveness + three cell bits, all inside 7:4, bit3 deliberately unused.
    bits = (BIT_LIVE,) + tuple(b for _, b, _, _ in CELLS)
    assert len(set(bits)) == len(bits) and all(b & (b - 1) == 0 for b in bits), \
        "probe bits are not distinct single bits"
    assert sum(bits) | BIT_UNUSED == 0xF8, "probe bits + the unused bit must span exactly 7:3"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert sum(bits) & BIT_UNUSED == 0, "bit3 must NOT be assigned -- it is V66's build discriminator"
    assert [b for _, b, _, _ in CELLS] == sorted((b for _, b, _, _ in CELLS), reverse=True), \
        "the cell bits are not in descending bit order -- wire order must match the brief's order"


# =======================================================================================================
# The cave -- 60 bytes of the 68-byte proven extent
# =======================================================================================================

def build_cave():
    """pack_gate_probe -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.bu -0x6806[gp],r6   ; LKAS-active gate candidate
        cmp   0x1,r6           ; ld.bu zero-extends => SIGNED < 1 is exactly == 0
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6806 != 0
      g6806:
        ld.bu -0x67f5[gp],r6   ; driver-torque hands-on gate candidate
        cmp   0x1,r6
        blt   +6
        movea 0x20,r7,r7       ; bit5 = gp-0x67f5 != 0
      g67f5:
        ld.bu -0x683c[gp],r6   ; THE CONTROL -- zero writers image-wide
        cmp   0x1,r6
        blt   +6
        movea 0x10,r7,r7       ; bit4 = gp-0x683c != 0   *** MUST NEVER SET ***
      g683c:
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

    rungs = []
    for disp, bit, name, _why in CELLS:
        load_idx = len(listing)
        emit(V55.ldbu_any(-disp, R6), f"ld.bu -0x{disp:04x}[gp],r6 ; {name}")
        emit(V55.cmp_imm5(CMP_LEVEL, R6), "cmp 0x1,r6          ; zero-extended byte: <1 IS ==0")
        emit(FF.bcond(COND_BLT, +6), f"blt +6              ; cell == 0 -> skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7   ; bit{bit.bit_length() - 1} = gp-0x{disp:04x} != 0")
        rungs.append((load_idx, len(listing) - 2, CAVE_BASE + len(body), name, disp, bit))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands exactly on its label. Located BY POSITION, not by content --
    # the cave emits `blt +6` three times, so a content lookup is ambiguous by construction. The
    # indices come out of the emission loop, so they cannot drift from it.
    assert [b for _, b, _, _, _, _ in rungs] == [3, 7, 11], f"rung indices drifted: {rungs}"
    for load_idx, br_idx, label, name, disp, _bit in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == COND_BLT, f"{name}: wrong branch condition"
        # the load, the compare and the branch must be CONSECUTIVE and in that order
        assert br_idx == load_idx + 2, f"{name}: load/cmp/branch are not consecutive"
        assert listing[load_idx][1] == V55.ldbu_any(-disp, R6), f"{name}: wrong cell loaded"
        assert listing[load_idx + 1][1] == V55.cmp_imm5(CMP_LEVEL, R6), f"{name}: cmp is not `0x1,r6`"

    # ---- GATE 2b: r6 LIVENESS. Between each rung's load and its compare, NOTHING may write r6 --
    # asserted structurally by the consecutiveness check above, and re-asserted here by scanning the
    # whole rung span for any write to r6 outside the loads themselves.
    load_addrs = {listing[i][0] for i, _, _, _, _, _ in rungs}
    for idx in range(1, rungs[-1][1] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) == 0x13:                        # cmp imm5,reg2 -- flags only
            continue
        if addr in load_addrs:                                # the rung's own load, into r6
            assert (hw >> 11) == R6, f"listing[{idx}] '{text}' is a load into r{hw >> 11}, not r6"
            continue
        assert (hw >> 11) == R7, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{R7}"
    # exactly one load and one compare per cell -- a duplicate would silently re-base a rung
    for disp, _bit, name, _why in CELLS:
        assert sum(1 for _, r, _ in listing if r == V55.ldbu_any(-disp, R6)) == 1, \
            f"{name}: gp-0x{disp:04x} is loaded more than once"
    assert sum(1 for _, r, _ in listing if r == V55.cmp_imm5(CMP_LEVEL, R6)) == len(CELLS), \
        "the number of compares does not match the number of cells"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store, and it is the
    # CAN-330 payload byte. Any other store would claim a RAM cell the cave does not own.
    store_ops = {0x3A: "st.b", 0x3B: "st.h/st.w"}
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in store_ops]
    assert store_idx == [16], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[16][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "the sole store is not the payload byte"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        # Format IV short stores (sst.b/sst.h/sst.w) live in bits 10:7 == 0b0111
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V66 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, " \
        "do not grow it: caves are this kit's only bricking class"
    # the budget arithmetic in the docstring, as an executable fact
    assert len(body) == 24 + 12 * len(CELLS), \
        f"the cave is {len(body)}B; the docstring's budget says {24 + 12 * len(CELLS)}B"
    assert 24 + 12 * (len(CELLS) + 1) > len(V55.CAVE_BYTES), \
        "a fourth rung WOULD have fit -- the bit-3 drop is no longer justified, re-add it"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_byte4(values, status_bits=0x7):
    """Exactly what the cave writes, given each cell's RAM byte. `values` is keyed by displacement."""
    b = BIT_LIVE
    for disp, bit, _name, _why in CELLS:
        v = values[disp] & 0xFF                 # ld.bu ZERO-EXTENDS a byte -> r6 in [0,255]
        if not (v < CMP_LEVEL):                 # cmp 0x1,r6 ; blt +6 skips the movea
            b |= bit
    return b | (status_bits & PAYLOAD_KEEP_MASK)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false"."""
    if (byte4 >> 3) & 0x1F == 0:
        return None
    out = {"live": bool(byte4 & BIT_LIVE),
           "bit3_unused_set": bool(byte4 & BIT_UNUSED)}
    for disp, bit, name, _why in CELLS:
        out[name] = bool(byte4 & bit)
    out["structural_ok"] = out["live"] and not out["bit3_unused_set"]
    return out


def _self_check_wire():
    """Every cell EXHAUSTIVELY over its 256 byte values, and the three jointly over a product grid."""
    zeros = {d: 0 for d, _, _, _ in CELLS}
    # 1. each cell exhaustive, with the others pinned at both extremes -- proves independence
    for other in (0, 0xFF):
        for disp, bit, name, _why in CELLS:
            for v in range(256):
                vals = {d: (v if d == disp else other) for d, _, _, _ in CELLS}
                d_ = decode_field(wire_byte4(vals))
                assert d_ is not None and d_["live"], f"{name}={v} decodes as VOID"
                assert d_[name] == (v != 0), f"{name}: bit wrong at value {v}"
                assert not d_["bit3_unused_set"], "bit3 must never be set by this cave"
    # 2. jointly, over a product grid that includes every boundary value
    grid = (0, 1, 2, 0x0F, 0x10, 0x7F, 0x80, 0xFF)
    for combo in itertools.product(grid, repeat=len(CELLS)):
        vals = {d: v for (d, _, _, _), v in zip(CELLS, combo)}
        d_ = decode_field(wire_byte4(vals))
        for (disp, _bit, name, _why), v in zip(CELLS, combo):
            assert d_[name] == (v != 0), f"{name} wrong in combo {combo}"
    # 3. the SIGNED compare is safe precisely because ld.bu zero-extends
    for v in range(256):
        assert (v < CMP_LEVEL) == (v == 0), "signed `< 1` is not `== 0` over a zero-extended byte"
    # 4. exactly EIGHT payloads are reachable, all with bit7 set and bit3 clear
    legal = {wire_byte4({d: v for (d, _, _, _), v in zip(CELLS, c)}, status_bits=0)
             for c in itertools.product((0, 1), repeat=len(CELLS))}
    assert len(legal) == 2 ** len(CELLS), f"the probe emits {len(legal)} payloads, expected 8"
    assert all(b & BIT_LIVE for b in legal), "a reachable payload has bit7 clear"
    assert all(not (b & BIT_UNUSED) for b in legal), "a reachable payload has bit3 SET"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"
    # 5. ⚠ the V64/V65 ambiguity, stated as an executable fact rather than a comment
    assert wire_byte4(zeros, status_bits=0x7) == 0x87, \
        "an all-gates-zero V66 frame is 0x87 -- byte-identical to V64's null and V65's NEUTRAL bucket"


_self_check_wire()


# =======================================================================================================
# Image-level gates
# =======================================================================================================

def assert_probe_sites(code, label="V66"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V65 cave remnants survive past our payload"


def assert_signal_sites(code, label="V66"):
    """The instruction donors every emitted encoder is pinned to, read FROM THE IMAGE."""
    for addr, raw, _disp, _reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_67FE_R6, PIN_LDBU_67F5_R7,
                                    PIN_LDBU_671D_R6, PIN_LDBU_683C_R15):
        assert bytes(code[addr:addr + 4]) == raw, \
            f"{label}: the pinned ld.bu at 0x{addr:05X} is {bytes(code[addr:addr+4]).hex()}, not " \
            f"{raw.hex()}"
    for addr, raw in (PIN_BLT6,):
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the pinned branch at 0x{addr:05X} is not {raw.hex()}"
    assert bytes(code[PIN_CMP_P1_R6[0]:PIN_CMP_P1_R6[0] + 2]) == PIN_CMP_P1_R6[1], \
        f"{label}: the pinned `cmp 0x1,r6` at 0x{PIN_CMP_P1_R6[0]:05X} moved"
    # V65's own signal context: the aggregator clamp and its ld.h/sar/cmp donors. V66 does not read
    # gp-0x6b94, but the block is asserted anyway -- it is free, and it is the region both `sar`
    # edits live in, so a stray byte there would be caught here rather than by the diff alone.
    V65.assert_signal_sites(code, label)


# ---- r24's mode-10 gain_B surface --------------------------------------------------------------------
# ⚠ WIDENED from V62's tripwire, which watched only 0xD2AEC and 0xD2B28 and was therefore BLIND to an
# edit landing on 0xD2A74 or 0xD2AB0. FUN_0003ad74 resolves gain_B through FOUR SEPARATE pointer
# arrays, each indexed by mode*4 with mode = gp+0x63fd = 10; the four records are NOT consecutive.
GAIN_B_PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
GAIN_B_MODE = 10
GAIN_B_RECORDS = (0xD2A74, 0xD2AB0, 0xD2AEC, 0xD2B28)
GAIN_B_RECORD_LEN = 0x12          # count(2) + 4 X halfwords + 4 Y halfwords
GAIN_B_EXPECT = (((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),
                 ((0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),
                 ((0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),
                 ((0, 400, 1500, 3000), (2151, 2151, 2049, 1947)))


def assert_gain_b_surface(code, ref, label="V66"):
    """All FOUR mode-10 gain_B records byte-identical to `ref`, and the four pointers still resolve.

    The pointer check is the half that matters: a record can also be "moved" by repointing the array
    slot that reaches it, which a bytes-only comparison of the records would never see.
    """
    for arr, rec in zip(GAIN_B_PTR_ARRAYS, GAIN_B_RECORDS):
        slot = arr + 4 * GAIN_B_MODE
        got = struct.unpack_from("<I", code, slot)[0]
        assert got == rec, \
            f"{label}: pointer array 0x{arr:05X}[{GAIN_B_MODE}] @0x{slot:05X} resolves to 0x{got:05X}, " \
            f"expected 0x{rec:05X}"
    for rec, (xs, ys) in zip(GAIN_B_RECORDS, GAIN_B_EXPECT):
        assert bytes(code[rec:rec + GAIN_B_RECORD_LEN]) == bytes(ref[rec:rec + GAIN_B_RECORD_LEN]), \
            f"{label}: gain_B mode-10 record 0x{rec:05X} differs from the reference image"
        n = u16(code, rec)
        assert n == len(xs), f"{label}: record 0x{rec:05X} point count is {n}, expected {len(xs)}"
        assert struct.unpack_from(f"<{n}H", code, rec + 2) == xs, f"{label}: 0x{rec:05X} X row moved"
        assert struct.unpack_from(f"<{n}H", code, rec + 2 + 2 * n) == ys, \
            f"{label}: 0x{rec:05X} Y row moved"


# =======================================================================================================
# The census -- the REQUIRED second method, re-run over the built image on every build, TWICE
# =======================================================================================================

# (readers, writers, writer addresses, permitted access mnemonics)
CENSUS_EXPECTED = {
    0x6806: (13, 16, [0x293A6, 0x293E4, 0x2948C, 0x2958C, 0x29696, 0x296D2, 0x2970E, 0x29724,
                      0x2A582, 0x2A5B6, 0x2A658, 0x2A73C, 0x2A80A, 0x2A842, 0x2A862, 0x2A87E],
             {"ld.bu", "st.b"}),
    # 🛑 all three writers are inside FUN_00041eec (body 0x41EEC-0x42375) and they store THREE
    # DISTINCT VALUES -- 0xFF, 1 and 0. See the semantics section of the docstring.
    0x67f5: (8, 3, [0x4222A, 0x42258, 0x42288], {"ld.bu", "st.b"}),
    # ⚠ FIVE writers, not four. 0x3E770 is in FUN_0003e760 (a lockstep reset routine), NOT in
    # FUN_0003bd7c. The "sole writer FUN_0003bd7c" claim is corrected here.
    0x67fe: (55, 5, [0x3BDB8, 0x3BE4E, 0x3BE5A, 0x3BE7A, 0x3E770], {"ld.bu", "st.b"}),
    CONTROL_DISP: (1, 0, [], {"ld.bu"}),
    MASK_DISP: (14, 2, [0x3BD2A, 0x41EC6], {"ld.bu", "st.b"}),
}
# The consumer each cell is calibrated against -- these must survive as readers.
CENSUS_CONSUMERS = {0x6806: 0x2A1B6,        # FUN_00028ea6's own read-back
                    0x67f5: 0x21DC0,
                    0x67fe: 0x41FF2,        # `cmp 0x2,r10` in FUN_00041eec -- the {1,2} test
                    CONTROL_DISP: 0x3AA94,  # the dead gate V67 proposes to repoint
                    MASK_DISP: 0x3AB98}     # r24's priority chain, ahead of the LKAS arm
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# Where THIS cave reads each cell, derived from the listing so it can never drift from the emitted code.
CAVE_CELL_READS = {}
for _disp, _bit, _name, _why in CELLS:
    _sites = [a for a, r, _ in CAVE_LISTING if r == V55.ldbu_any(-_disp, R6)]
    assert len(_sites) == 1, f"gp-0x{_disp:04x} must be read EXACTLY once in the cave"
    CAVE_CELL_READS[_disp] = _sites[0]


def assert_cell_census(buf, label="V66", in_cave=True):
    """Re-derive the reader/writer sets from raw bytes and assert them exactly, by TWO decoders.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    Firmware accesses (outside the cave span) and this cave's own reads are asserted SEPARATELY;
    pooling them would let a cave read mask the loss of a firmware one.
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
        # ⚠ GATE 1 restated as a MEASUREMENT: the cave READS this cell and WRITES it nowhere.
        cave = [h for h in hits if h[0] in span]
        want = [(CAVE_CELL_READS[disp], "ld.bu", R6)] if (in_cave and disp in CAVE_CELL_READS) else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"

        # ---- SECOND METHOD: scan_gp_accesses decodes per-opcode over EVERY byte offset, including
        # odd ones, and covers the 48-bit extended-displacement form the pattern scan is blind to.
        if disp == 0x6806:
            SCAN.self_check(buf)
        alt = SCAN.scan(buf, (-disp) & 0xFFFF)
        alt_even = [h for h in alt if h["even"]]
        assert len(alt_even) == len(hits), \
            f"{label}: the two decoders disagree on gp-0x{disp:04x}: {len(hits)} vs {len(alt_even)}"
        assert sorted(h["addr"] for h in alt_even) == sorted(a for a, _, _ in hits), \
            f"{label}: the two decoders disagree on WHICH addresses touch gp-0x{disp:04x}"
        assert not [h for h in alt if not h["even"]], \
            f"{label}: gp-0x{disp:04x} has an ODD-OFFSET hit -- confirm the instruction boundary"
        # 48-bit extended-displacement form. scan_ext BRUTE-FORCES 6-byte windows, so it re-reports
        # every 32-bit hit (the instruction plus its two trailing bytes) and also any 32-bit
        # gp-access to a NEIGHBOURING cell whose low displacement halfword happens to collide --
        # e.g. `ld.bu -0x67f6[gp],r9` @0x4276C sits in gp-0x67f5's candidate list for exactly that
        # reason. A candidate is an ALIAS iff its own first four bytes already decode as a
        # Format-VII gp-relative access; anything else would be a genuine extended-form instruction.
        ext = SCAN.scan_ext(buf, -disp)
        genuine = []
        for h in ext:
            d7 = SCAN.decode_fmt7(buf, h["addr"])
            if d7 is None or d7[4] != GP:
                genuine.append(h)
        if disp == CONTROL_DISP:
            # 🛑 THE LOAD-BEARING NULL. V67 rests entirely on this cell having no writer at all.
            # V66 can no longer measure it ON-CAR (the bit was cut for budget), so this STATIC
            # verification is now the only evidence, and it is asserted on every build.
            assert not ext, f"{label}: gp-0x683c has {len(ext)} extended-displacement candidates"
            assert n_write == 0 and not writes, f"{label}: gp-0x683c has acquired a writer"
        assert not genuine, \
            f"{label}: gp-0x{disp:04x} has {len(genuine)} extended-form candidate(s) that are NOT " \
            f"32-bit aliases: {[hex(h['addr']) for h in genuine[:8]]}"


def build():
    if not os.path.exists(V65_BIN):
        print(f"  {V65_BIN} missing -- running the V65 builder first\n")
        V65.build()
    v65 = bytearray(open(V65_BIN, "rb").read())
    print(f"  V65 source {V65_BIN}\n    SHA256 {hashlib.sha256(bytes(v65)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v65, "V65 source")
    assert walk(bytes(v65), label="V65 source") == 0
    assert walk_all_blocks(bytes(v65), label="V65 source") == 0
    V65.assert_probe_sites(v65, "V65 source")        # V65's OWN cave must be intact first
    V65.assert_signal_sites(v65, "V65 source")
    V65.assert_cell_census(bytes(v65), "V65 source")
    V59.assert_index_chain(v65, "V65 source")
    V55.assert_variant_tables(v65)
    V57.assert_decoupled(v65, "V65 source")
    assert u16(v65, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V65 source lost the lockout edit"
    V62.assert_sar_sites(v65, "V65 source", expect_doubled=True)
    V62.assert_untouched_context(v65, "V65 source")
    V63.assert_arms(v65, "V65 source", expect_raised=False)
    assert u16(v65, V62.BLEND_ADDR) == V62.BLEND_STOCK, "V60's falsified blend must be absent"
    assert_signal_sites(v65, "V65 source")
    assert_gain_b_surface(v65, v65, "V65 source")
    assert_cell_census(bytes(v65), "V65 source", in_cave=False)
    print("    census OK (TWO decoders): gp-0x6806 13r/16w, gp-0x67f5 8r/3w, gp-0x67fe 55r/5w,")
    print("               gp-0x683c 1r/0w, gp-0x671d 14r/2w -- every access a BYTE, and V65's cave")
    print("               touches none of them (the pre-edit baseline for GATE 1)")
    print("    ⚠ gp-0x67fe has FIVE writers, not four: 0x3E770 is in FUN_0003e760 (a lockstep reset")
    print("      routine, shadow gp-0x4c3a), NOT in FUN_0003bd7c.")
    print(f"    ⚠ gp-0x{CONTROL_DISP:04x} DEAD-CELL CLAIM verified STATICALLY only "
          "(1 reader, 0 writers, 0 extended)")
    print("      -- V66 does not measure it on-car; the bit was cut for budget.")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    V62.assert_sar_sites(baseline, "V38 baseline", expect_doubled=False)
    V62.assert_untouched_context(baseline, "V38 baseline")
    V63.assert_arms(baseline, "V38 baseline", expect_raised=False)
    assert_signal_sites(baseline, "V38 baseline")
    assert_gain_b_surface(baseline, v65, "V38 baseline")
    print("    V38 baseline already reads `sar 0xa` at BOTH sites -- V66's revert targets exactly it")

    code = bytearray(v65)

    # ---- EDIT 1+2: revert V62's two `sar` immediates to STOCK ------------------------------------
    print("\n  EDIT 1+2 -- revert the torsion-bar RATE lane to EXACTLY STOCK:")
    for addr, what in V62.EDITS:
        struct.pack_into("<H", code, addr, V62.SAR_STOCK_HW[addr])
        print(f"    0x{addr:05X}  0x{V62.SAR_NEW_HW[addr]:04X} -> 0x{V62.SAR_STOCK_HW[addr]:04X}   "
              f"sar 0x9 -> sar 0xa   {what}")
    print(f"    0x{V62.R26_SAR_FIRST:05X} REMAINS 0x{V62.R26_SAR_FIRST_HW:04X} (sar 0xa) -- a DIFFERENT "
          "site V62 deliberately never touched.")
    V62.assert_sar_sites(code, "V66", expect_doubled=False)
    for addr, _what in V62.EDITS:
        assert u16(code, addr) == u16(baseline, addr), \
            f"0x{addr:05X} does not match the V38 baseline after the revert"

    # ---- EDIT 3: replace the cave payload ---------------------------------------------------------
    print(f"\n  EDIT 3 -- replace V65's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare; a fourth rung needs 12):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v65[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V65's -- same cave base, same jarl"
    assert_probe_sites(code, "V66")
    assert_signal_sites(code, "V66")
    assert_cell_census(bytes(code), "V66")

    # ---- every inherited invariant, read FROM THE BUILT IMAGE -------------------------------------
    V62.assert_untouched_context(code, "V66")
    V63.assert_arms(code, "V66", expect_raised=False)     # V63's raised arms must be ABSENT
    # 🛑 V63.assert_untouched is run in FULL here, which V65 could NOT do: it asserts both `sar`
    # sites are stock AND both of V61's taps are r1. On V66 all four hold, so the strongest single
    # statement about the rate lane in this kit applies to this build directly.
    V63.assert_untouched(code, "V66")
    for addr, want, width, what in V63.MUST_STAY_STOCK:
        got = u16(code, addr) if width == 2 else code[addr]
        assert got == want, f"V66: 0x{addr:05X} ({what}) is {got}, expected {want}"
    V57.assert_decoupled(code, "V66")
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, "V66")
    assert_gain_b_surface(code, v65, "V66")
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
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v65, a), \
            f"FIR coefficient 0x{a:05X} moved"
    # V67's two future edit sites must be STOCK on V66 -- V66 is the pre-flight, not the fix.
    assert bytes(code[0x3AA94:0x3AA98]) == PIN_LDBU_683C_R15[1], \
        "0x3AA94 already carries V67's repoint -- V66 must measure the DEAD gate, not a live one"
    assert u16(code, 0xC6446) == 512 and u16(code, 0xC6444) == 512, \
        "the 0x683c gain arms are not stock 512 -- V66 must not pre-empt V67"

    # ---- MACHINE PROOF: the whole calibration block is byte-identical to V65's -------------------
    assert bytes(code[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]) == bytes(v65[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]), \
        "the CAL block differs from V65 -- V66 must move NO calibration byte"

    # ---- GATE 9: the cave span and both edited shifts are owned by the MAIN block ------------------
    for a, what in ((CAVE_BASE, "cave base"),
                    (CAVE_BASE + len(V55.CAVE_BYTES) - 1, "cave last byte"),
                    (HOOK_ADDR, "hook"), (V62.R24_SAR, "r24 sar"), (V62.R26_SAR, "r26 sar")):
        assert V53.owning_block(code, a) == MAIN_BLOCK, f"{what} 0x{a:05X} is not in the MAIN CRC block"

    # ---- CRC. ONLY the MAIN block moves: all three V66 edits are code. ----------------------------
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
            assert old_crc == new_crc, "CAL CRC moved -- V66 must change NO calibration"
        else:
            assert old_crc != new_crc, "the MAIN CRC did not move, but code bytes did"
    assert struct.unpack_from("<I", code, CAL_BLOCK[1])[0] == cal_crc_before == \
        struct.unpack_from("<I", v65, CAL_BLOCK[1])[0], \
        "the CAL CRC word is not byte-identical to V65's"
    print(f"    => CAL CRC 0x{cal_crc_before:08X} IDENTICAL to V65's = machine proof no cal byte moved")

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    sar_span = {a + k for a in (V62.R24_SAR, V62.R26_SAR) for k in (0, 1)}
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    cal_crc = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))

    d65 = [i for i in range(0x13000, 0x100000) if code[i] != v65[i]]
    stray = [i for i in d65 if i not in (cave_span | sar_span | main_crc)]
    assert not stray, \
        f"V66 differs from V65 outside cave + sar + MAIN CRC: {[hex(x) for x in stray[:16]]}"
    assert main_crc <= set(d65), "the MAIN CRC trailer did not move"
    assert not (cal_crc & set(d65)), "the CAL CRC trailer moved -- impossible if no cal byte moved"
    n_sar = len([i for i in d65 if i in sar_span])
    n_cave = len([i for i in d65 if i in cave_span])
    # 0x42A9->0x42AA and 0x32A9->0x32AA each move ONLY the low byte (the imm5 field).
    assert sorted(i for i in d65 if i in sar_span) == sorted((V62.R24_SAR, V62.R26_SAR)), \
        "the sar reverts moved a byte other than the two imm5 fields"
    print(f"\n  V66 vs V65: {len(d65)} bytes  ({n_cave} cave + {n_sar} sar immediate + "
          f"{len(d65) - n_cave - n_sar} MAIN CRC)")
    print("    EXACT byte list (excluding the cave span and the MAIN CRC trailer):")
    for i in sorted(i for i in d65 if i in sar_span):
        print(f"      0x{i:05X}  0x{v65[i]:02X} -> 0x{code[i]:02X}   "
              f"(halfword 0x{u16(v65, i & ~1):04X} -> 0x{u16(code, i & ~1):04X})")
    print(f"    cave span 0x{CAVE_BASE:05X}-0x{CAVE_BASE + len(V55.CAVE_BYTES) - 1:05X}: "
          f"{n_cave} of {len(V55.CAVE_BYTES)} bytes differ")
    print(f"    MAIN CRC 0x{MAIN_BLOCK[1]:05X}: {len(d65) - n_cave - n_sar} bytes")
    print("    => the CAL block AND the 0xD2000 block are byte-identical to V65's.")

    if os.path.exists(V62_BIN):
        v62 = bytearray(open(V62_BIN, "rb").read())
        d62 = [i for i in range(0x13000, 0x100000) if code[i] != v62[i]]
        outside = [i for i in d62 if i not in (cave_span | sar_span | main_crc)]
        assert not outside, f"V66 differs from V62 outside cave + sar + CRC: {[hex(x) for x in outside[:8]]}"
        print(f"  V66 vs V62: {len(d62)} bytes  (cave + the two sar reverts + MAIN CRC)")
    if os.path.exists(V59_BIN):
        v59 = bytearray(open(V59_BIN, "rb").read())
        d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
        outside = [i for i in d59 if i not in (cave_span | main_crc)]
        assert not outside, \
            f"V66 differs from V59 outside cave + MAIN CRC: {[hex(x) for x in outside[:16]]}"
        print(f"  V66 vs V59: {len(d59)} bytes  (cave + MAIN CRC ONLY -- the rate lane is identical,")
        print("              which makes V59/V66/V62 a clean Kd = 1x / 1x / 2x ladder on one instrument)")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V66 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")
    assert not any(a <= V62.R24_SAR <= b or a <= V62.R26_SAR <= b for a, b in runs), \
        "V66 still differs from V38 at a sar site -- the revert did not take"

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V66")
    assert walk(bytes(code), label="V66") == 0
    assert walk_all_blocks(bytes(code), label="V66") == 0
    assert_probe_sites(code, "V66")
    assert_signal_sites(code, "V66")
    V55.assert_variant_tables(code)
    V62.assert_sar_sites(code, "V66", expect_doubled=False)
    V62.assert_untouched_context(code, "V66")
    V63.assert_untouched(code, "V66")

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
    FF.assert_x31_checksum(rwd, "V66 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V66 readback")
    assert walk(bytes(readback), label="V66 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V66 readback") == 0
    assert_probe_sites(readback, "V66 readback")
    assert_signal_sites(readback, "V66 readback")
    assert_cell_census(bytes(readback), "V66 readback")
    assert_gain_b_surface(readback, v65, "V66 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V66 readback")
    V59.assert_index_chain(readback, "V66 readback")
    V62.assert_sar_sites(readback, "V66 readback", expect_doubled=False)
    V62.assert_untouched_context(readback, "V66 readback")
    V63.assert_arms(readback, "V66 readback", expect_raised=False)
    V63.assert_untouched(readback, "V66 readback")
    assert u16(readback, V57.PRIVATE_ADDR) == V57.GAIN_4X
    assert u16(readback, V57.GAIN_ADDR) == V57.GAIN_STOCK
    assert readback[0xC64A3] == 1 and readback[0xC64DE] == 27
    assert u16(readback, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert bytes(readback[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]) == \
        bytes(v65[CAL_BLOCK[0]:CAL_BLOCK[1] + 4]), "readback CAL block differs from V65's"

    # re-decode the cave FROM THE READBACK, instruction by instruction, against the listing
    print("\n  cave re-decoded from the READBACK (not from what we meant to write):")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)
    # 🛑 and re-decode each cell load's DISPLACEMENT out of the readback bytes, independently
    print("\n  cell loads re-decoded from the READBACK by scan_gp_accesses (the hw1-bit-5 guard),")
    print("  with the PARITY of every encoded cell:")
    print(f"    {'site':>9s}  {'bytes':<10s} {'cell':<12s} {'disp':<8s} {'parity':<7s} {'op':<5s} "
          f"{'bit':<5s} provenance")
    for disp, bit, name, why in CELLS:
        a = CAVE_CELL_READS[disp]
        raw = bytes(readback[a:a + 4])
        mnem, got, reg1, reg2 = decode_ldbu(raw)
        assert (mnem, got, reg1, reg2) == ("ld.bu", disp, GP, R6), \
            f"{name}: readback @0x{a:05X} decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
        d16 = (0x10000 - disp) & 0xFFFF
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        prov = "FIELD-DECOMPOSED (weak)" if disp in WEAK_PIN_DISPS else "byte-identical instance"
        print(f"    0x{a:05X}  {raw.hex():<10s} gp-0x{disp:04x}    0x{d16:04X}   "
              f"{'ODD' if d16 & 1 else 'EVEN':<7s} 0x{op:02X}  bit{bit.bit_length() - 1}  {prov}")
    assert set(WEAK_PIN_DISPS) <= {d for d, _, _, _ in CELLS} , \
        "a cell declared weakly pinned is not actually emitted"
    print(f"    {len(CAVE_BYTES)} bytes used of the {len(V55.CAVE_BYTES)}-byte proven extent; "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare (a fourth rung needs 12 -- see the docstring)")
    print(f"    sar sites read back: 0x{V62.R24_SAR:05X}={u16(readback, V62.R24_SAR):04X}  "
          f"0x{V62.R26_SAR:05X}={u16(readback, V62.R26_SAR):04X}  "
          f"0x{V62.R26_SAR_FIRST:05X}={u16(readback, V62.R26_SAR_FIRST):04X} (untouched, by design)")
    print(f"    V38 baseline for comparison: 0x{u16(baseline, V62.R24_SAR):04X} / "
          f"0x{u16(baseline, V62.R26_SAR):04X} / 0x{u16(baseline, V62.R26_SAR_FIRST):04X}  => IDENTICAL")

    print("\n  PROBE: 0x14A byte4  bit7 = LIVENESS (constant 1)")
    for disp, bit, name, why in CELLS:
        print(f"                      bit{bit.bit_length() - 1} = gp-0x{disp:04x} != 0   {name:12s} {why}")
    print("                      bit3 = UNUSED, never set -- a set bit3 means the build is NOT V66")
    print("                      bits 2:0 = stock STEER_SENSOR_STATUS, preserved")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("         Exactly EIGHT payloads are reachable; anything else means the build is not V66.")
    print("  🛑 A CONSTANT 0x87 IS AMBIGUOUS WITH V64's NULL AND V65's NEUTRAL BUCKET.")
    print("     Confirm which .rwd is on the car before reading any verdict.")
    print("  GATE 1 RAM ownership: VACUOUS, and MEASURED -- the census shows the cave reads each cell")
    print("          exactly once and writes none; the listing contains EXACTLY ONE store, the")
    print("          existing CAN-330 payload byte gp-0x1514 with bits 2:0 preserved.")
    print("  GATE 2 closed-loop stability: VACUOUS for the probe (its only output is a TX payload byte")
    print("          no control path reads), and VACUOUS for the two sar reverts -- they restore the")
    print("          STOCK instruction stream, byte-identical to V38's, which every pre-V62 build flew.")
    print("          *** Still CODE in the 1 kHz TX path, which is why base/hook/extent are reused.")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is")
    print("        unmeasurable. Long drive, mixed: highway engaged, city manual, parking-lot creep.")
    print("     Condition on carControl.latActive or 0x18F byte4 bit3, NEVER carState.cruiseState.")
    print("     Decode with rlog-tools/decode_v66_gateprobe.py.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
