#!/usr/bin/env python3
"""builds/v50_v79/build_v67_tva.py -- V67 = V66 PLUS the grind #1 fix, GATED ON LKAS.

WHAT V67 IS
-----------
V62 applied a x2 to the r24 torsion-bar rate lane EVERYWHERE. That FIXED grind #1 (18-22 Hz down
2.9x at the corner) and CAUSED grind #2 (40-49 Hz up 11.7x, p = 0.0003). V66 reverted the x2 to
stock. V67 puts the x2 back, but ONLY while LKAS is applying:

    0x3AA96  c5 -> fb     ONE BYTE. Repoints `ld.bu -0x683c[gp],r15` @0x3AA94 (a DEAD cell) to
                          `ld.bu -0x6806[gp],r15` (the LKAS-active flag), so `lp` -- which gates
                          cal 0xC6446 for r24 at 0x3AC04 -- becomes an LKAS-conditional selector.
    0xC6446  512 -> 5244  r24's now-live arm.  5244 = 2.00 x 2622, the LERP at grind #1's measured
                          operating point (creep 7.2 km/h, motor rate 128 deg/s).
    0x3AC20 / 0x3AB76 / 0x3AB70   ALL STOCK `sar 0xa`   -- V66's reverts are KEPT.

=> gate FALSE (LKAS off) is BYTE-FOR-BYTE STOCK BEHAVIOUR on the rate lane; gate TRUE (LKAS
applying) delivers V62's proven 2.00x at grind #1's operating point. Base steering is untouched in
every condition, which is the requirement the operator stated from the start.

🛑 WHAT IT DOES NOT DO, stated first so it cannot be discovered later: **grind #2 SURVIVES under
LKAS.** V67 does not act on grind #2's mechanism; it removes V62's amplification from every
condition where the gate is false. Measured on the provoked routes that is 15.7% of windows, but
ordinary driving is mostly LKAS-off, so in practice far more. Full argument in
`docs/specs/design/V66-V67-DESIGN.md`; the executable arithmetic is `analysis-2020accord/studies/sessions/v68/v66_v67_explained.py`.

★ THE REPOINT IS BYTE-IDENTICAL TO A REAL INSTRUCTION -- ALL FOUR BYTES, REGISTER FIELDS INCLUDED
--------------------------------------------------------------------------------------------------
    0x3AA94  84 7f c5 97   ld.bu -0x683c[gp],r15   CURRENT (dead cell)
    0x3AA94  84 7f fb 97   ld.bu -0x6806[gp],r15   V67
    0x42842  84 7f fb 97   ld.bu -0x6806[gp],r15   *** A REAL INSTRUCTION, byte-for-byte ours ***
    0x55C76  84 7f fb 97   ld.bu -0x6806[gp],r15   *** AND A SECOND ONE ***
    0x2A1B6  84 67 fb 97   ld.bu -0x6806[gp],r12   a third, differing only in reg2

The design note claimed provenance "differs only in reg2". It is stronger than that: the EXACT
halfword pair we write already executes at two addresses in this ROM. Both are asserted from the
image on every build, and the emitted bytes are decoded back through scan_gp_accesses' INDEPENDENT
decoder rather than compared against our own intent.

⚠ ONE BYTE, AND WHY hw1 MUST NOT MOVE. For V850 `ld.bu` the displacement's bit 0 lives in **hw1
bit 5** (the opcode field's own low bit, 0x3C vs 0x3D) and hw2's LSB is the ld.bu/ld.hu WIDTH
selector, always 1. `-0x6806` = 0x97FA is EVEN, so the opcode field, BOTH register fields and the
high displacement byte are all untouched and only 0x3AA96 moves. Had the target been odd this would
be a three-byte edit across both halfwords, and writing only hw2 would silently address the
NEIGHBOURING cell. The build asserts hw1 is unchanged and re-decodes the result.

★★ THE GATE IS VALIDATED ON-CAR. GATE 2 IS MEASURED, NOT ARGUED.
-----------------------------------------------------------------
V57 already flew a probe that put `(gp-0x6806 == 0)` on 0x14A byte4 bit6, in July, on routes 28/29 --
nobody had correlated it. `analysis-2020accord/verify/validate_gp6806_gate.py` (numbers reproduced by this
build from `_scratch/out/_gp6806_gate_validation.json`, and asserted, so the claim cannot rot):

    route   frames    span     agreement with carControl.latActive   duty      transitions
    29       7,924    79.2 s              99.899%                   21.73%    4  = 0.0505/s
    28      29,990   299.9 s              99.943%                   49.88%    9  = 0.0300/s
                                                    pooled: 37,914 frames, 379.1 s, 13 transitions

⇒ **`gp-0x6806 != 0` IS "LKAS is applying"**, confirmed at two very different duty cycles (21.7% and
49.9%), so it is not one route's pattern. And it does **not** drop out during steady engaged holding
-- the one hole static analysis could not close, because gp-0x6806 is a ramp-FSM phase flag whose
"settled" phases 5/6/7 could not be ruled out by reading the writers.

🛑 THE POLARITY, AND THE ONE BYTE IT RESTS ON. V57's bit6 is the INVERSE of what V67 needs, so the
validation only holds if that inversion is real. Read out of the FLOWN V57 image, not its docstring:

    0xC4B38  8437fb97  ld.bu -0x6806[gp],r6
    0xC4B3C  e031      cmp r0,r6
    0xC4B3E  ba05      bne +6        <- condition 0xA = NE. Taken when r6 != 0, SKIPPING the movea.
    0xC4B40  273e4000  movea 0x40,r7,r7    => bit6 is set ONLY when gp-0x6806 == 0

So V57's bit6 == 1 means the cell is ZERO, the validation script's `~bit6` is correct, and the
99.9% agreement belongs to `gp-0x6806 != 0`. V67's `setfne lp` @0x3AAA8 therefore gives lp = 1 while
LKAS applies, the arm is taken there, and the polarity is as designed. Had that branch been `be`
instead of `bne` the entire design would invert and 5244 would be the wrong number. Asserted from
the V57 artifact on every build by `assert_v57_probe_polarity()`.

⚠ ON THE PARAMETRIC-PUMP CRITERION, the transition COUNT is not the strong evidence -- 4 and 9 are
small numbers. The strong evidence is STRUCTURAL: a signal that agrees with `latActive` to 99.9%
over 37,914 frames toggles when the DRIVER engages and disengages, which is a human-scale event.
It cannot toggle at 21 or 45 Hz without destroying that agreement. Three orders of magnitude of
margin, and the margin is a consequence of the agreement rather than an independent count.

★ lp SURVIVES FROM THE setf TO BOTH CONSUMERS -- verified in Ghidra, not assumed
--------------------------------------------------------------------------------
The repoint only means anything if `lp` reaches 0x3AC04 intact. FUN_0003aa2c disassembled in full:

    0x3AA94  ld.bu -0x683c[gp],r15      <- V67 repoints THIS
    0x3AAA6  cmp   r0,r15
    0x3AAA8  setfne lp                  <- lp = (cell != 0)
    ...      no write to lp, and NO `jarl`, anywhere in between ...
    0x3AB56  cmp   r0,lp  / 0x3AB5E ld.hu 0x7444[tp],r8    <- r26's arm, cal 0xC6444
    0x3AC04  cmp   r0,lp  / 0x3AC08 ld.hu 0x7446[tp],r10   <- r24's arm, cal 0xC6446  *** V67 ***
    0x3ACDC  jarl  0x36682,lp           <- the FIRST jarl, and it is AFTER both consumers
    0x3AA2C  prepare {...,lp},0x0  /  0x3AD70 dispose {...,lp},[lp]   -- lp is saved and restored

🛑 AND THE CONSEQUENCE NOBODY HAD WRITTEN DOWN: **the repoint puts r26's arm on the SAME gate.**
`0xC6444` stays stock 512, so while LKAS applies r26's gain becomes a flat 512 instead of its
gain_A LERP (3072 at creep) -- a 6x REDUCTION on that lane, not an increase. It is harmless only
because **r26 is structurally inert**: its input is an average whose cal base 0xC6564 is 40 bytes
of exact zero (asserted on every build below). If that record is ever overturned, V67 costs r26
damping under LKAS and this is the paragraph to come back to. Direction matters: this residual
pushes loop gain DOWN, i.e. it cannot be a V62-style amplifier, but "less damping" is not "no
effect" -- V56 is on record for exactly that.

⚠ THE ARM VALUE, AND WHY IT IS 5244 AND NOT 1536 OR 6144
---------------------------------------------------------
With `sar 0xa` kept stock the lane divides by 1024, so the arm is a DIRECT replacement for the LERP:
arm / LERP is the multiplier. 2622 is the LERP at grind #1's operating point and is computed here by
calling `v66_v67_explained.r24_gain_q10`, never hard-coded -- and the four gain_B records that LERP
reads are themselves asserted byte-identical to V66's, so the number cannot drift silently.

⚠ RESIDUAL, unavoidable and stated rather than smoothed over: a SCALAR arm cannot track a CURVE.
5244 is exactly 2.00x at (7.2 km/h, 128 deg/s) and drifts across the rest of the LKAS-on regime --
about 1.7x at the slowest creep with a fast wheel, about 2.7x at road speed. `0xC6446` is one
halfword in one CRC block, so it is trivially re-tunable after a drive.

Arithmetic, so the saturation question is closed rather than argued:
    5120 (the input clamp) x 5244 = 26,849,280 = 1.25% of INT32_MAX -- no `mul` truncation.
    The lane's +-8192 clamp is reached at |dtorque| >= 1601 counts, against a MEASURED 123-839.
    ⚠ the design note's "1599" is the NO-DEADZONE figure (8192*1024/5244 = 1600); the 3-count
    deadzone cal 0xC61F6 is subtracted BEFORE the clamp, so the real threshold is 1601. Derived
    from EX.r24_lane on every build, not quoted.
    The ten-lane sum clip to +-10240 was measured NEVER reached (V65's ladder, 120,049 frames).
=> the loop is linear here and the gain change propagates faithfully.

THE PROBE -- 0x14A byte4 bits 7:3, and it is a DIFFERENT probe from V66's
-------------------------------------------------------------------------
V67's whole point is that a gate is now LOAD-BEARING, so the probe must make every failure mode
diagnosable. This is the V64 lesson applied: *probe the gate, not just the output.*

    bit7 = 1                      LIVENESS. field == 0 => the cave did not fire => the reading is VOID
    bit6 = gp-0x6806 != 0         *** THE GATE ITSELF. *** Low duty while engaged => wrong cell and
                                  V67 is inert. Toggling in 15-60 Hz => a parametric pump, ABORT.
    bit5 = gp-0x671d != 0         *** THE MASKING RISK. *** It OUTRANKS the arm at 0x3ABFA: if set,
                                  r24's gain is pinned to 0xC6442 = 1024, which is BELOW the stock
                                  creep LERP of 3072 -- so V67 would be WORSE than V66, not merely
                                  inert. V64 read this 0 across 14,980 frames of ONE 149.8 s creep
                                  route; that is not a clearance for a long mixed drive.
    bit4 = gp-0x671a >= 5         the THIRD arm (0xC6440 = 2048). Below the gate in priority, so it
                                  only bites when bit6 is clear -- but it replaces the LERP when it
                                  does, and it is a ONE-WAY LATCH with a 5 s hold.
    bit3 = 0                      UNUSED. Never set by this cave.
    bits 2:0                      stock STEER_SENSOR_STATUS, preserved

🛑 bit4 IS `>=`, NOT `>` -- A CORRECTION TO THE SPEC, MADE BY READING THE INSTRUCTIONS
--------------------------------------------------------------------------------------
The brief asked for `gp-0x671a > cal 0xC64FA`, and `v66_v67_explained.r24_gain_q10` mirrors it as
`state_671a > ceil_671a`. The firmware disagrees, at 0x3AA70-0x3AA88:

    0x3AA70  ld.bu -0x671a[gp],r12      the latched reversal counter
    0x3AA78  ld.bu 0x74fa[tp],r14       CEIL, cal 0xC64FA = 5 (a BYTE -- reading it u16 gives 517)
    0x3AA7C  cmp   r14,r12              r12 - r14
    0x3AA7E  bc    0x3AA88              UNSIGNED <  -> skip
    0x3AA80  mov   0x1,r2               r2 = 1  <=>  state >= CEIL
    0x3AA88  mov   0x0,r2
    ...
    0x3AC0E  cmp   r0,r2 / be 0x3AC16 / 0x3AC12 ld.hu 0x7440[tp],r10   the arm, IFF r2 != 0

So the arm fires at state >= 5, and the probe must say the same thing or bit4 does not mean "the
third arm is selected". This is exactly the test V64 flew as its bit6, with the same encoders.
⚠ The mirror in `studies/sessions/v68/v66_v67_explained.py` is therefore off by one at the boundary. It is NOT corrected
from here -- that file is the operator's reference and edits to it belong in the close-out -- but
`assert_explained_mirror()` below asserts the discrepancy is confined to state == 5 exactly, so it
cannot quietly become something else.

⚠ THE CAL IS READ, NOT ASSUMED. The cave hardcodes 5 because Format-II `cmp imm5` is the only
2-byte compare; `code[0xC64FA] == 5` is asserted on the source AND on the readback, so a revision
that moved CEIL would fail the build rather than silently decouple bit4 from the arm.

🛑 V66 AND V67 EMIT STRUCTURALLY IDENTICAL PAYLOADS. THIS IS A TRAP.
---------------------------------------------------------------------
Both use bits 7:4 with bit3 never set, so the eight legal payloads are the SAME EIGHT BYTES with
DIFFERENT MEANINGS. There is no structural discriminator, unlike V66-vs-V59/V64/V65. The only
discriminators are (a) the .rwd filename on the car and (b) a weak behavioural asymmetry: under V66
bit4 is gp-0x67fe (base-assist substate, expected near 100% duty) while under V67 bit4 is a rare
latch. The decoder says this in its first section and refuses to lean on (b).

ENCODER PROVENANCE -- every emitted instruction pinned byte-for-byte to a real instance
----------------------------------------------------------------------------------------
    ld.bu -0x6806[gp],r6   8437fb97   BYTE-IDENTICAL @0x2A8C0 (and the cave site on V66, flown)
    ld.bu -0x671d[gp],r6   a437e398   BYTE-IDENTICAL @0x3AB98 -- r24's own priority-chain read
    ld.bu -0x671a[gp],r6   8437e798   ⚠ no byte-identical instance image-wide: hw2 from the real
                                      `ld.bu -0x671a[gp],r12` @0x3AA70, hw1 from the real
                                      `ld.bu -0x3d38[gp],r6` @0x2A508. Both halves real, the
                                      COMBINATION ours -- and FLOWN, byte-for-byte, on V64.
    ld.bu -0x6806[gp],r15  847ffb97   the REPOINT. BYTE-IDENTICAL @0x42842 and @0x55C76.
    cmp   0x1,r6           6132       BYTE-IDENTICAL @0x14D46
    cmp   0x5,r6           6532       BYTE-IDENTICAL @0x2A50C
    blt   +6               b605       BYTE-IDENTICAL @0x1C006
    bl    +6               b105       flown on V64 (its arm rung); condition + displacement decoded
    movea 0x80,r0,r7       203e8000   flashed on V54/V55/V59/V64/V65/V66
    movea 0xBB,r7,r7       273eBB00   flashed on V54/V55/V59/V64/V65/V66 (immediate differs only)
    ld.bu -0x1514[gp],r6 / andi 0x7,r6,r6 / or r7,r6 / st.b r6,-0x1514[gp]   flashed since V31P

GATES
-----
GATE 1 (RAM ownership): **VACUOUS, and asserted as a MEASUREMENT.** The repoint is a read-only load
    DISPLACEMENT -- no RAM cell is claimed, no store is added, no register allocation changes (r15
    was already the destination and is already dead after 0x3AAA6). The cave's only store is the
    existing CAN-330 payload byte gp-0x1514 with bits 2:0 preserved; the emitted listing is scanned
    and must contain EXACTLY ONE store instruction.
GATE 2 (closed-loop stability):
    * The lane is a DERIVATIVE => DC-neutral. A gain step at engagement produces NO torque step;
      it changes the damping coefficient, not the operating point.
    * ★★ THE GATE ITSELF IS MEASURED, NOT ARGUED. See the section below.
    * Magnitude: 5120 x 5244 = 1.25% of INT32_MAX; lane saturation needs |dtorque| >= 1601 against a
      measured 123-839; the ten-lane sum clip was measured never reached.
    * State-mask residual (recorded, not ignored): arbitration runs under `andi 0x930` and the
      aggregator under `andi 0xc30`, so in state 10 gp-0x6806 is one or more ticks stale. Harmless
      for a <= 0.1 Hz signal.
    * Masking residual: gp-0x671d OUTRANKS the arm and pins the gain to 1024, BELOW stock. bit5
      measures it -- that is why it is on the car instead of in a document.
    * r26 residual: see the lp section above.
    *** Still CODE in the 1 kHz TX path, which is why base/hook/extent are reused, not moved.

CAVE DISCIPLINE -- caves are this kit's ONLY bricking class (V24, V27, V48B)
----------------------------------------------------------------------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte proven extent as V55/V57/V58/V59/V64/V65/V66 --
all SEVEN flew clean. Read-only; r6/r7 only. 60 of 68 bytes used, 8 spare; a fourth rung needs 12.

BASE = V66 (SHA 0d4a0a53...). Every V66 invariant is re-asserted on the output, with exactly two
documented exceptions -- 0x3AA94's bytes and 0xC6446's value -- and the exception set is itself
asserted to be exactly those two, against V62's and V63's own tables.

Decoder: rlog-tools/probe/decode_v67_gate.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import hashlib
import itertools
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v54_tva as V54                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v59_tva as V59                # noqa: E402
import build_v61_tva as V61                # noqa: E402
import build_v62_tva as V62                # noqa: E402
import build_v63_tva as V63                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (census helper + the >=CEIL rung's pins)
import build_v65_tva as V65                # noqa: E402
import build_v66_tva as V66                # noqa: E402  (direct base)
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT second decoder)
import v66_v67_explained as EX             # noqa: E402  (the arithmetic; the arm is DERIVED from it)

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged since V55
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# =======================================================================================================
# EDIT 1 -- the repoint. ONE BYTE.
# =======================================================================================================
REPOINT_ADDR = 0x3AA94                         # ld.bu -0x683c[gp],r15
REPOINT_BYTE = 0x3AA96                         # the ONLY byte that moves: hw2's low half
REPOINT_FROM = bytes.fromhex("847fc597")       # ld.bu -0x683c[gp],r15
REPOINT_TO = bytes.fromhex("847ffb97")         # ld.bu -0x6806[gp],r15
DEAD_DISP = 0x683C                             # the cell V67 stops reading -- 0 readers afterwards
GATE_DISP = 0x6806                             # the cell V67 starts reading -- the LKAS-active flag
# Real instructions BYTE-IDENTICAL to what the repoint writes, all four bytes, register fields included.
REPOINT_TWINS = (0x42842, 0x55C76)
REPOINT_REG2_TWIN = (0x2A1B6, bytes.fromhex("8467fb97"), 12)   # differs from ours in reg2 only

# The consumer chain the repoint feeds, asserted from the image so a moved instruction fails the build.
LP_CHAIN = ((0x3AAA6, bytes.fromhex("e079"), "cmp r0,r15"),
            (0x3AAA8, bytes.fromhex("eaff0000"), "setfne lp"),
            (0x3AB56, bytes.fromhex("e0f9"), "cmp r0,lp        (r26's arm test)"),
            (0x3AB5E, bytes.fromhex("e5474574"), "ld.hu 0x7444[tp],r8   -> cal 0xC6444 (r26 arm)"),
            (0x3AC04, bytes.fromhex("e0f9"), "cmp r0,lp        (r24's arm test)"),
            (0x3AC06, bytes.fromhex("c205"), "be 0x3AC0E"),
            (0x3AC08, bytes.fromhex("e5574774"), "ld.hu 0x7446[tp],r10  -> cal 0xC6446 (V67's arm)"))
# The FIRST jarl in FUN_0003aa2c. lp is scratch up to here, and this is AFTER both consumers.
FIRST_JARL_AFTER = 0x3ACDC

# =======================================================================================================
# EDIT 2 -- the arm. Value DERIVED from v66_v67_explained, never hard-coded blind.
# =======================================================================================================
ARM_ADDR = 0xC6446                             # tp+0x7446, halfword, ONE reader (0x3AC08)
ARM_STOCK = 512
R26_ARM_ADDR = 0xC6444                         # tp+0x7444, r26's arm on the SAME gate -- stays stock
R26_ARM_STOCK = 512
R26_AVG_CAL = 0xC6564                          # 40 bytes of exact zero == the r26-inert record
R26_AVG_LEN = 40

GRIND1_KMH, GRIND1_DEGS = 7.2, 128             # grind #1's measured operating point
ARM_MULTIPLIER = 2                             # V62's proven dose, and only where the gate is true


def _derive_arm():
    """arm = 2.00 x the LERP at grind #1's operating point. Computed, then sanity-bounded."""
    speed_counts = int(GRIND1_KMH * 64.0625)
    rate_counts = int(GRIND1_DEGS * EX.RATE_COUNTS_PER_DEGS)
    lerp = EX.r24_gain_q10(speed_counts, rate_counts, gate_671d=0, gate_683c=0, state_671a=0)
    arm = ARM_MULTIPLIER * lerp
    assert lerp == 2622, f"the LERP at grind #1's operating point is {lerp}, not 2622 -- STOP"
    assert arm == 5244, f"the derived arm is {arm}, not the 5244 the design note specifies"
    assert 0 < arm <= 0xFFFF, "the arm does not fit the halfword cal"
    return speed_counts, rate_counts, lerp, arm


GRIND1_SPEED_COUNTS, GRIND1_RATE_COUNTS, GRIND1_LERP, ARM_NEW = _derive_arm()

INPUT_CLAMP = EX.INPUT_CLAMP                   # 5120
LANE_CLAMP = EX.LANE_CLAMP                     # 8192

# =======================================================================================================
# EDIT 3 -- the cave. Four bits: liveness, THE GATE, THE MASKING RISK, the third arm.
# =======================================================================================================
BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_ARM3 = 0x40, 0x20, 0x10
BIT_UNUSED = 0x08              # bit3: never set by this cave.

MASK_DISP = 0x671D             # OUTRANKS the arm -- pins the gain to 0xC6442 = 1024, BELOW stock
ARM3_DISP = 0x671A             # the third arm's latched reversal counter
CEIL_CAL, CEIL_VALUE = V64.CEIL_CAL, V64.CEIL_VALUE       # 0xC64FA, BYTE = 5

COND_BLT = V65.COND_BLT        # 0x6, SIGNED <   -- pinned to the real `blt` @0x1C006
COND_BL = V55.COND_BL          # 0x1, UNSIGNED < -- flown on V64's arm rung

# (gp displacement, bit, label, cmp immediate, branch condition, what it decides).
# EMISSION ORDER == descending bit order. `cmp N,r6` + `b<cond> +6` skips the movea, so:
#   (1, COND_BLT) sets the bit when the cell is NON-ZERO   (ld.bu zero-extends => signed <1 IS ==0)
#   (5, COND_BL)  sets the bit when the cell is >= 5       (unsigned, matching the firmware's `bc`)
CELLS = (
    (GATE_DISP, BIT_GATE, "gate_6806", 1, COND_BLT,
     "*** THE GATE *** -- duty vs latActive, transitions/s, dominant toggle Hz"),
    (MASK_DISP, BIT_MASK, "mask_671d", 1, COND_BLT,
     "*** THE MASKING RISK *** -- outranks the arm; if set, gain is pinned to 1024, BELOW stock"),
    (ARM3_DISP, BIT_ARM3, "arm3_671a", CEIL_VALUE, COND_BL,
     "the THIRD arm (0xC6440 = 2048), selected at state >= CEIL; below the gate in priority"),
)

# ---- encoder pins, all read back FROM THE IMAGE in assert_signal_sites() -----------------------------
PIN_CMP_P1_R6 = V65.PIN_CMP_P1_R6            # (0x14D46, 6132, 1, r6)   BYTE-IDENTICAL to ours
PIN_BLT6 = V65.PIN_BLT6                      # (0x1C006, b605)          BYTE-IDENTICAL to ours
PIN_CMP5_R6 = V64.PIN_CMP5_R6                # (0x2A50C, 5, r6, 6532)   BYTE-IDENTICAL to ours

# Real `ld.bu` donors. (address, bytes, displacement, reg2).
PIN_LDBU_6806_R6 = V66.PIN_LDBU_6806_R6                              # (0x2A8C0, 8437fb97, 0x6806, 6)
PIN_LDBU_671D_R6 = (0x3AB98, bytes.fromhex("a437e398"), 0x671d, 6)   # BYTE-IDENTICAL to ours
PIN_LDBU_671A_R12 = (0x3AA70, bytes.fromhex("8467e798"), 0x671a, 12)  # hw2 donor (reg2 differs)
PIN_LDBU_R6_HW1 = (0x2A508, bytes.fromhex("8437c9c2"), 0x3d38, 6)    # hw1 donor: even-disp -> r6
PIN_LDBU_6806_R15 = (0x42842, REPOINT_TO, 0x6806, 15)                # the REPOINT, byte-identical
# ⚠ WEAKER PROVENANCE, declared rather than buried: gp-0x671a has no `ld.bu ...,r6` instance
# image-wide, so its load is a TWO-WAY field decomposition (hw1 from 0x2A508, hw2 from 0x3AA70).
# It is nevertheless FLOWN: V64's cave emitted these exact four bytes and V64 booted and ran clean.
WEAK_PIN_DISPS = (ARM3_DISP,)

TAG = "LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-gateprobe4-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V67-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v67_plain_image.bin"))
V66_BIN = str(plain_image_path("_v66_plain_image.bin"))
V65_BIN = str(plain_image_path("_v65_plain_image.bin"))
V62_BIN = str(plain_image_path("_v62_plain_image.bin"))
DECODER = os.path.join(os.path.dirname(HERE), "rlog-tools", "probe/decode_v67_gate.py")

V66_SOURCE_SHA256 = "0d4a0a5361e8ba91b1a24ad3298dd617ad541903070b02a58b9ae6df6709f246"


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

    🛑 This is the hw1-bit-5 guard, and it is why the check is not done by re-reading our own
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
# Encoders
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V66._self_check_encoders()          # inherits V65/V64-adjacent/V62/V59/V58/V57/V55/V54/FF
    V64._self_check_encoders()          # the >=CEIL rung's own pins (cmp 0x5,r6 / bl +6 / ld.bu 671a)

    assert GP == 4, f"GP is r{GP}; every real gp-relative instance in this image carries reg1 = r4"

    # ---- THE REPOINT. Built by the encoder, NOT copied from the docstring, then decoded back.
    built = V55.ldbu_any(-GATE_DISP, 15)
    assert built == REPOINT_TO, \
        f"the encoder builds {built.hex()} for `ld.bu -0x6806[gp],r15`, not {REPOINT_TO.hex()}"
    assert REPOINT_FROM == V55.ldbu_any(-DEAD_DISP, 15), \
        "REPOINT_FROM is not what the encoder builds for `ld.bu -0x683c[gp],r15`"
    # ONE BYTE, and it is hw2's low half. hw1 -- opcode parity AND both register fields -- must not move.
    diff = [i for i in range(4) if REPOINT_FROM[i] != REPOINT_TO[i]]
    assert diff == [2], f"the repoint moves bytes {diff}, not exactly byte 2 (0x3AA96)"
    assert REPOINT_FROM[:2] == REPOINT_TO[:2], "hw1 MOVED -- opcode/reg1/reg2 must all be untouched"
    assert REPOINT_ADDR + 2 == REPOINT_BYTE
    for raw, disp, nm in ((REPOINT_FROM, DEAD_DISP, "before"), (REPOINT_TO, GATE_DISP, "after")):
        mnem, got, reg1, reg2 = decode_ldbu(raw)
        assert (mnem, got, reg1, reg2) == ("ld.bu", disp, GP, 15), \
            f"repoint {nm}: {raw.hex()} decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
        d16 = (0x10000 - disp) & 0xFFFF
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == (0x3C | (d16 & 1)), f"repoint {nm}: opcode 0x{op:02X} vs displacement parity"
        assert struct.unpack_from("<H", raw, 2)[0] & 1 == 1, \
            f"repoint {nm}: ld.bu hw2 LSB must be SET -- a clear LSB is the ld.h/ld.hu form"
    assert ((0x10000 - GATE_DISP) & 0xFFFF) % 2 == 0, \
        "gp-0x6806's displacement is ODD -- then this is NOT a one-byte edit and hw1 must move too"
    # it must not collapse onto a store or a wider load
    assert REPOINT_TO != FF.stb(15, -GATE_DISP, GP), "the repoint collapsed onto an st.b"
    assert REPOINT_TO != FF.ldhu(GATE_DISP, 15) and REPOINT_TO != V55.ldh(GATE_DISP, 15), \
        "the repoint collapsed onto a HALFWORD load -- it would straddle the neighbouring cell"

    # ---- the three cell loads, each decoded back and its DISPLACEMENT asserted.
    for disp, _bit, name, _lvl, _cond, _why in CELLS:
        raw = V55.ldbu_any(-disp, R6)
        mnem, got, reg1, reg2 = decode_ldbu(raw)
        assert mnem == "ld.bu", f"{name}: emitted {mnem}, not ld.bu"
        assert got == disp, \
            f"{name}: the emitted load addresses gp-0x{got:04x}, NOT gp-0x{disp:04x} -- this is the " \
            "hw1-bit-5 trap and the neighbouring cell is a real, live cell"
        assert (reg1, reg2) == (GP, R6), f"{name}: reg1/reg2 are r{reg1}/r{reg2}"
        hw1 = struct.unpack_from("<H", raw, 0)[0]
        op = (hw1 >> 5) & 0x3F
        assert op == (0x3C | (((0x10000 - disp) & 0xFFFF) & 1)), \
            f"{name}: opcode field 0x{op:02X} does not match the displacement parity"
        assert struct.unpack_from("<H", raw, 2)[0] & 1 == 1, f"{name}: ld.bu hw2 LSB must be SET"
        assert raw != FF.stb(R6, -disp, GP), f"{name}: the emitted load collapsed onto an st.b"
        assert raw != FF.ldhu(disp, R6) and raw != V55.ldh(disp, R6), \
            f"{name}: ld.bu collapsed onto a HALFWORD load -- it would straddle the neighbour"
    loads = [V55.ldbu_any(-d, R6) for d, _, _, _, _, _ in CELLS]
    assert len(set(loads)) == len(CELLS), "two cell loads are byte-identical -- a displacement is wrong"

    # BYTE-IDENTICAL to a real instance, register field included.
    for pin in (PIN_LDBU_6806_R6, PIN_LDBU_671D_R6):
        assert V55.ldbu_any(-pin[2], R6) == pin[1], \
            f"ld.bu -0x{pin[2]:04x}[gp],r6 must be byte-identical to the instance @0x{pin[0]:05X}"
        assert pin[2] not in WEAK_PIN_DISPS, f"gp-0x{pin[2]:04x} is both byte-identical and 'weak'"
    # TWO-WAY decomposition for the one cell with no byte-identical instance image-wide.
    ours = V55.ldbu_any(-ARM3_DISP, R6)
    assert ARM3_DISP in WEAK_PIN_DISPS, "gp-0x671a is field-decomposed but not declared weak"
    assert ours[2:] == PIN_LDBU_671A_R12[1][2:], \
        f"gp-0x671a hw2 {ours[2:].hex()} != the real hw2 @0x{PIN_LDBU_671A_R12[0]:05X}"
    assert ours[:2] == PIN_LDBU_R6_HW1[1][:2], \
        f"gp-0x671a hw1 {ours[:2].hex()} != the real even-disp `ld.bu ...,gp,r6` hw1 @0x2A508"
    a = struct.unpack("<H", ours[:2])[0]
    b = struct.unpack("<H", PIN_LDBU_671A_R12[1][:2])[0]
    assert (a & 0x07FF) == (b & 0x07FF), \
        f"the hw2 donor @0x{PIN_LDBU_671A_R12[0]:05X} differs from ours in more than reg2"
    assert (b >> 11) == 12 and (a >> 11) == R6, "donor/emitted reg2 fields are not as read"
    # and it is FLOWN: V64's cave carries these exact four bytes.
    assert ours in V64.CAVE_BYTES, "gp-0x671a's load is not byte-present in V64's FLOWN cave"

    for addr, raw, disp, reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_671D_R6, PIN_LDBU_671A_R12,
                                  PIN_LDBU_R6_HW1, PIN_LDBU_6806_R15):
        assert struct.unpack("<H", raw[:2])[0] & 0x1F == GP, \
            f"the donor @0x{addr:05X} does not carry reg1 = r4 -- gp is not r4 after all"
        assert decode_ldbu(raw) == ("ld.bu", disp, GP, reg2), \
            f"the donor @0x{addr:05X} does not decode as `ld.bu -0x{disp:04x}[gp],r{reg2}`"
    assert decode_ldbu(REPOINT_REG2_TWIN[1]) == ("ld.bu", GATE_DISP, GP, REPOINT_REG2_TWIN[2])

    # ---- the two compares, both byte-identical to real instances.
    assert V55.cmp_imm5(1, R6) == PIN_CMP_P1_R6[1], \
        f"cmp 0x1,r6 must be byte-identical to the real instance @0x{PIN_CMP_P1_R6[0]:05X}"
    assert V55.cmp_imm5(CEIL_VALUE, R6) == PIN_CMP5_R6[3], \
        f"cmp 0x5,r6 must be byte-identical to the real instance @0x{PIN_CMP5_R6[0]:05X}"
    assert V55.cmp_imm5(5, R6) != V55.cmp_imm5(1, R6), "cmp_imm5 ignores its immediate"
    assert V55.cmp_imm5(5, R6) != V55.cmp_imm5(5, R7), "cmp_imm5 ignores its register"
    assert 0 <= CEIL_VALUE <= 15, "Format II imm5 is SIGNED (-16..15); CEIL must fit unambiguously"
    for lvl in {c[3] for c in CELLS}:
        f = decode_fmt2(struct.unpack("<H", V55.cmp_imm5(lvl, R6))[0])
        assert (f["opcode"], f["reg2"], f["imm5"]) == (0x13, R6, lvl), f"cmp {lvl},r6 decodes as {f}"

    # ---- the two branch conditions. V67 introduces NEITHER.
    assert COND_BLT == 0x6 and COND_BL == 0x1, "branch conditions drifted"
    assert COND_BLT != COND_BL, "blt collapsed onto the UNSIGNED bl"
    assert FF.bcond(COND_BLT, +6) == PIN_BLT6[1], \
        f"blt +6 fails the real `blt` @0x{PIN_BLT6[0]:05X}"
    assert FF.bcond(COND_BL, +6).hex() == "b105", "bl/bc +6 drifted from the form V64 flew"
    assert FF.bcond(COND_BL, +6) in V64.CAVE_BYTES, "`bl +6` is not byte-present in V64's FLOWN cave"
    for cond in (COND_BLT, COND_BL):
        raw = FF.bcond(cond, +6)
        assert len(raw) == 2 and raw[1] == 0x05, f"cond {cond}: not a +6 Bcond"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, "bcond does not carry the condition in 3:0"

    # ---- the bit-set moveas: V54's flashed reg1=r7 bias form, different immediates.
    for _d, bit, name, _l, _c, _w in CELLS:
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"{name}: movea 0x{bit:x},r7,r7 bad"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"

    # ---- the bit map.
    bits = (BIT_LIVE,) + tuple(b for _, b, _, _, _, _ in CELLS)
    assert len(set(bits)) == len(bits) and all(b & (b - 1) == 0 for b in bits), \
        "probe bits are not distinct single bits"
    assert sum(bits) | BIT_UNUSED == 0xF8, "probe bits + the unused bit must span exactly 7:3"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert sum(bits) & BIT_UNUSED == 0, "bit3 must NOT be assigned"
    assert [b for _, b, _, _, _, _ in CELLS] == \
        sorted((b for _, b, _, _, _, _ in CELLS), reverse=True), \
        "the cell bits are not in descending bit order -- wire order must match the brief's order"


# =======================================================================================================
# The cave -- 60 bytes of the 68-byte proven extent
# =======================================================================================================

def build_cave():
    """pack_gate_probe -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.bu -0x6806[gp],r6   ; *** THE GATE *** -- the cell 0x3AA94 now reads
        cmp   0x1,r6           ; ld.bu zero-extends => SIGNED < 1 is exactly == 0
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6806 != 0
      g_gate:
        ld.bu -0x671d[gp],r6   ; *** THE MASKING RISK *** -- outranks the arm at 0x3ABFA
        cmp   0x1,r6
        blt   +6
        movea 0x20,r7,r7       ; bit5 = gp-0x671d != 0  => gain pinned to 1024, BELOW stock
      g_mask:
        ld.bu -0x671a[gp],r6   ; the third arm's latched reversal counter (BYTE, 0..CEIL)
        cmp   0x5,r6           ; CEIL -- asserted equal to cal 0xC64FA
        bl    +6               ; UNSIGNED < CEIL -> the third arm is NOT selected
        movea 0x10,r7,r7       ; bit4 = gp-0x671a >= 5
      g_arm3:
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
    for disp, bit, name, lvl, cond, _why in CELLS:
        load_idx = len(listing)
        emit(V55.ldbu_any(-disp, R6), f"ld.bu -0x{disp:04x}[gp],r6 ; {name}")
        emit(V55.cmp_imm5(lvl, R6),
             f"cmp 0x{lvl:x},r6          ; " +
             ("zero-extended byte: <1 IS ==0" if lvl == 1 else "CEIL (cal 0xC64FA)"))
        emit(FF.bcond(cond, +6),
             ("blt +6" if cond == COND_BLT else "bl  +6") +
             f"              ; skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7   ; bit{bit.bit_length() - 1} = gp-0x{disp:04x} " +
             ("!= 0" if lvl == 1 else f">= {lvl}"))
        rungs.append((load_idx, len(listing) - 2, CAVE_BASE + len(body), name, disp, bit, lvl, cond))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands exactly on its label. Located BY POSITION, not by content --
    # the cave emits two identical `blt +6`, so a content lookup is ambiguous by construction.
    assert [b for _, b, _, _, _, _, _, _ in rungs] == [3, 7, 11], f"rung indices drifted: {rungs}"
    for load_idx, br_idx, label, name, disp, _bit, lvl, cond in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, f"{name}: wrong branch condition"
        assert br_idx == load_idx + 2, f"{name}: load/cmp/branch are not consecutive"
        assert listing[load_idx][1] == V55.ldbu_any(-disp, R6), f"{name}: wrong cell loaded"
        assert listing[load_idx + 1][1] == V55.cmp_imm5(lvl, R6), f"{name}: cmp is not `0x{lvl:x},r6`"

    # ---- GATE 2b: r6 LIVENESS. Between each rung's load and its compare, NOTHING may write r6.
    load_addrs = {listing[i][0] for i, _, _, _, _, _, _, _ in rungs}
    for idx in range(1, rungs[-1][1] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) == 0x13:                        # cmp imm5,reg2 -- flags only
            continue
        if addr in load_addrs:
            assert (hw >> 11) == R6, f"listing[{idx}] '{text}' is a load into r{hw >> 11}, not r6"
            continue
        assert (hw >> 11) == R7, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{R7}"
    for disp, _bit, name, _l, _c, _w in CELLS:
        assert sum(1 for _, r, _ in listing if r == V55.ldbu_any(-disp, R6)) == 1, \
            f"{name}: gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store, the payload byte.
    store_ops = {0x3A: "st.b", 0x3B: "st.h/st.w"}
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in store_ops]
    assert store_idx == [16], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[16][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
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
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V67 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, " \
        "do not grow it: caves are this kit's only bricking class"
    assert len(body) == 24 + 12 * len(CELLS), \
        f"the cave is {len(body)}B; the budget says {24 + 12 * len(CELLS)}B"
    assert 24 + 12 * (len(CELLS) + 1) > len(V55.CAVE_BYTES), \
        "a fourth rung WOULD have fit -- re-add the bit-3 signal"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_byte4(values, status_bits=0x7):
    """Exactly what the cave writes, given each cell's RAM byte. `values` is keyed by displacement."""
    b = BIT_LIVE
    for disp, bit, _name, lvl, cond, _why in CELLS:
        v = values[disp] & 0xFF                 # ld.bu ZERO-EXTENDS a byte -> r6 in [0,255]
        skip = (v < lvl)                        # signed AND unsigned agree on a zero-extended byte
        if not skip:
            b |= bit
    return b | (status_bits & PAYLOAD_KEEP_MASK)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false"."""
    if (byte4 >> 3) & 0x1F == 0:
        return None
    out = {"live": bool(byte4 & BIT_LIVE), "bit3_unused_set": bool(byte4 & BIT_UNUSED)}
    for disp, bit, name, _l, _c, _w in CELLS:
        out[name] = bool(byte4 & bit)
    out["structural_ok"] = out["live"] and not out["bit3_unused_set"]
    return out


def r24_gain_under_v67(speed_counts, motor_rate, gate, mask_671d, state_671a):
    """The FULL priority chain as V67 leaves it -- the model the probe bits map onto, one for one.

    bit5 (mask) beats bit6 (gate) beats bit4 (arm3) beats the LERP. Mirrors 0x3ABFA-0x3AC16.
    """
    if mask_671d != 0:
        return EX.ARM_671D, "0xC6442 = 1024  (gp-0x671d -- BELOW stock: V67 is WORSE than V66 here)"
    if gate != 0:
        return ARM_NEW, f"0xC6446 = {ARM_NEW}  (V67's LKAS arm)"
    if state_671a >= CEIL_VALUE:
        return EX.ARM_671A, "0xC6440 = 2048  (the third arm)"
    return EX.r24_gain_q10(speed_counts, motor_rate, 0, 0, 0), "the mode-10 LERP (stock)"


def assert_explained_mirror():
    """v66_v67_explained mirrors the third arm as `> CEIL`; the firmware is `>= CEIL`.

    🛑 Not silently patched. The discrepancy is asserted to be confined to state == CEIL exactly, so
    it cannot broaden into something else while this build still cites that file for the arm value.
    """
    disagree = [s for s in range(0, 16)
                if (EX.r24_gain_q10(0, 0, 0, 0, s) == EX.ARM_671A) != (s >= CEIL_VALUE)]
    assert disagree == [CEIL_VALUE], \
        f"the explained-model mirror disagrees with the firmware at states {disagree}, " \
        f"expected exactly [{CEIL_VALUE}] (its `>` vs the firmware's `bc` = unsigned `>=`)"
    # and the arm value's own derivation must be reproducible from that file
    assert EX.r24_gain_q10(GRIND1_SPEED_COUNTS, GRIND1_RATE_COUNTS, 0, 0, 0) == GRIND1_LERP


def _self_check_wire():
    """Every cell EXHAUSTIVELY over its 256 byte values, and the three jointly over a product grid."""
    assert_explained_mirror()
    zeros = {d: 0 for d, _, _, _, _, _ in CELLS}
    for other in (0, 0xFF):
        for disp, bit, name, lvl, _c, _w in CELLS:
            for v in range(256):
                vals = {d: (v if d == disp else other) for d, _, _, _, _, _ in CELLS}
                d_ = decode_field(wire_byte4(vals))
                assert d_ is not None and d_["live"], f"{name}={v} decodes as VOID"
                assert d_[name] == (v >= lvl), f"{name}: bit wrong at value {v} (level {lvl})"
                assert not d_["bit3_unused_set"], "bit3 must never be set by this cave"
    grid = (0, 1, 2, 4, 5, 6, 0x0F, 0x10, 0x7F, 0x80, 0xFF)
    for combo in itertools.product(grid, repeat=len(CELLS)):
        vals = {d: v for (d, _, _, _, _, _), v in zip(CELLS, combo)}
        d_ = decode_field(wire_byte4(vals))
        for (disp, _bit, name, lvl, _c, _w), v in zip(CELLS, combo):
            assert d_[name] == (v >= lvl), f"{name} wrong in combo {combo}"
    # 🛑 The compare is safe precisely because ld.bu ZERO-EXTENDS: r6 lands in [0,255], so the
    # SIGNED `blt` and the UNSIGNED `bl` agree on every reachable value. That is what lets the two
    # rung shapes share one wire model. Asserted, not assumed -- on the real encodings.
    assert COND_BLT != COND_BL, "the two branch conditions must differ"
    for lvl in sorted({c[3] for c in CELLS}):
        for v in range(256):
            signed_lt = v < lvl                     # blt, on a zero-extended byte
            unsigned_lt = (v & 0xFF) < (lvl & 0xFF)  # bl/bc
            assert signed_lt == unsigned_lt, \
                f"signed and unsigned `< {lvl}` disagree at {v} -- the rung shapes are NOT shareable"
    assert all((v < 1) == (v == 0) for v in range(256)), "signed `< 1` is not `== 0` over a byte"
    # exactly EIGHT payloads are reachable, all with bit7 set and bit3 clear
    legal = {wire_byte4({d: (lvl if on else 0) for (d, _, _, lvl, _, _), on in zip(CELLS, c)},
                        status_bits=0)
             for c in itertools.product((0, 1), repeat=len(CELLS))}
    assert len(legal) == 2 ** len(CELLS), f"the probe emits {len(legal)} payloads, expected 8"
    assert all(b & BIT_LIVE for b in legal), "a reachable payload has bit7 clear"
    assert all(not (b & BIT_UNUSED) for b in legal), "a reachable payload has bit3 SET"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"
    # 🛑 the ambiguity, as an executable fact: an all-clear V67 frame is 0x87, byte-identical to
    # V64's null, V65's NEUTRAL bucket AND V66's all-gates-zero reading.
    assert wire_byte4(zeros, status_bits=0x7) == 0x87, "an all-clear V67 frame is not 0x87"
    assert V66.wire_byte4({d: 0 for d, _, _, _ in V66.CELLS}, status_bits=0x7) == 0x87, \
        "V66's all-clear frame is not 0x87 -- the stated ambiguity would be wrong"

    # ---- the priority chain, as the probe bits map onto it
    sc, rc = GRIND1_SPEED_COUNTS, GRIND1_RATE_COUNTS
    assert r24_gain_under_v67(sc, rc, 0, 0, 0)[0] == GRIND1_LERP, "gate false must be the stock LERP"
    assert r24_gain_under_v67(sc, rc, 1, 0, 0)[0] == ARM_NEW, "gate true must take V67's arm"
    assert r24_gain_under_v67(sc, rc, 1, 1, 0)[0] == EX.ARM_671D < GRIND1_LERP, \
        "gp-0x671d must OUTRANK the arm and land BELOW the stock LERP"
    assert r24_gain_under_v67(sc, rc, 1, 0, CEIL_VALUE)[0] == ARM_NEW, \
        "the gate must outrank the third arm"
    assert r24_gain_under_v67(sc, rc, 0, 0, CEIL_VALUE)[0] == EX.ARM_671A
    assert r24_gain_under_v67(sc, rc, 0, 0, CEIL_VALUE - 1)[0] == GRIND1_LERP

    # ---- the delivered multiplier, through the REAL lane arithmetic (deadzone included)
    for dtorque in (123, 400, 839):
        stock = EX.r24_lane(dtorque, GRIND1_LERP, 10)
        v67 = EX.r24_lane(dtorque, ARM_NEW, 10)
        assert abs(v67 / stock - 2.0) < 0.02, \
            f"V67 delivers {v67 / stock:.3f}x at dtorque {dtorque}, not 2.00x"
        assert abs(v67) < LANE_CLAMP, "the lane saturates inside the MEASURED dtorque range"
    # ---- saturation threshold, DERIVED from the real lane rather than quoted
    # ⚠ CORRECTION. `docs/specs/design/V66-V67-DESIGN.md` and v66_v67_explained say "|dtorque| >= 1599". That is
    # the no-deadzone figure, 8192*1024/5244 = 1599.7 -> 1600. The lane subtracts the 3-count
    # deadzone (cal 0xC61F6) BEFORE the +-8192 clamp, so the real threshold is 1601. Immaterial to
    # the conclusion -- the measured dtorque range is 123-839, i.e. 1.9x below either number -- but
    # the build asserts what the arithmetic gives, not what the note says.
    SAT_MEASURED_MAX = 839
    sat = next(d for d in range(1, INPUT_CLAMP + 1) if abs(EX.r24_lane(d, ARM_NEW, 10)) >= LANE_CLAMP)
    naive = -(-LANE_CLAMP * 1024 // ARM_NEW)
    assert (sat, naive) == (1601, 1600), \
        f"lane saturation is at {sat} (naive {naive}); the design note's 1599 assumed no deadzone"
    assert sat > 1.9 * SAT_MEASURED_MAX, \
        f"saturation at {sat} is not comfortably clear of the measured maximum {SAT_MEASURED_MAX}"
    assert INPUT_CLAMP * ARM_NEW < 0x7FFFFFFF // 50, "the mul is not comfortably inside INT32"
    _self_check_wire.sat = sat


_self_check_wire()


# =======================================================================================================
# Image-level gates
# =======================================================================================================

# =======================================================================================================
# The ON-CAR validation of the gate -- V57's flown probe, and the one byte its polarity rests on
# =======================================================================================================
V57_BIN = str(plain_image_path("_v57_plain_image.bin"))
GATE_VALIDATION_JSON = os.path.join(HERE, "_scratch/out/_gp6806_gate_validation.json")
# V57's bit6 rung, at the SAME cave base V67 uses. `bne` (condition 0xA) means the movea is SKIPPED
# when the cell is non-zero => bit6 == 1 <=> gp-0x6806 == 0, i.e. the INVERSE of V67's gate.
V57_PROBE_RUNG = ((0xC4B38, bytes.fromhex("8437fb97"), "ld.bu -0x6806[gp],r6"),
                  (0xC4B3C, bytes.fromhex("e031"), "cmp r0,r6"),
                  (0xC4B3E, bytes.fromhex("ba05"), "bne +6   <- condition 0xA = NE"),
                  (0xC4B40, bytes.fromhex("273e4000"), "movea 0x40,r7,r7"))
COND_BNE = 0xA
# Reproduced by analysis-2020accord/verify/validate_gp6806_gate.py over V57's routes 28/29.
GATE_VALIDATION = {"_scratch/cache/r29": dict(frames=7924, agreement_pct=99.899, duty_pct=21.73,
                                      transitions=4, transitions_per_s=0.0505),
                   "_scratch/cache/r28": dict(frames=29990, agreement_pct=99.943, duty_pct=49.88,
                                      transitions=9, transitions_per_s=0.0300)}
GATE_AGREEMENT_MIN = 99.0        # below this, gp-0x6806 is not the engagement flag and V67 inverts
GATE_TPS_MAX = 1.0               # transitions/s; the kill band starts at 15 Hz = 30 transitions/s


def assert_v57_probe_polarity(label="V67"):
    """🛑 V57's bit6 is `gp-0x6806 == 0`; the validation inverts it. Prove the inversion is REAL.

    The whole 99.9% agreement -- and therefore V67's polarity, and therefore the arm VALUE -- turns
    on one branch byte in a DIFFERENT build's cave. If it were `be` (0x2) instead of `bne` (0xA) the
    design would invert. Read out of the flown V57 artifact, never from its docstring.
    Returns False (with a printed warning) if the V57 image is not present, rather than passing mute.
    """
    if not os.path.exists(V57_BIN):
        print(f"    ⚠ {V57_BIN} missing -- V57's probe POLARITY is NOT verified this run, so the")
        print("      on-car gate validation is quoted, not checked. Rebuild V57 to close this.")
        return False
    v57 = open(V57_BIN, "rb").read()
    for addr, raw, what in V57_PROBE_RUNG:
        got = bytes(v57[addr:addr + len(raw)])
        assert got == raw, \
            f"{label}: V57's probe rung at 0x{addr:05X} is {got.hex()}, not {raw.hex()} ({what}) -- " \
            "the on-car validation's polarity cannot be confirmed"
    hw = struct.unpack_from("<H", v57, 0xC4B3E)[0]
    assert (hw >> 7) & 0xF == 0xB, f"{label}: 0x{0xC4B3E:05X} is not a Bcond at all"
    assert hw & 0xF == COND_BNE, \
        f"{label}: V57's bit6 branch is condition 0x{hw & 0xF:X}, not NE (0x{COND_BNE:X}) -- if it " \
        "is BE then V57's bit6 means `gp-0x6806 != 0`, the validation's inversion is WRONG, and " \
        "V67's polarity AND its 5244 arm invert with it. STOP."
    assert hw & 0xF != V57.COND_BE, "V57's bit6 branch collapsed onto `be` -- the polarity inverts"
    # and V57 read the SAME cell, with the SAME four bytes V67's own cave emits
    assert V57_PROBE_RUNG[0][1] == V55.ldbu_any(-GATE_DISP, R6), \
        f"{label}: V57 did not read gp-0x{GATE_DISP:04x} with the bytes this cave emits"
    return True


def assert_gate_validation(label="V67"):
    """The on-car numbers, re-read from the artifact verify/validate_gp6806_gate.py writes."""
    if not os.path.exists(GATE_VALIDATION_JSON):
        print(f"    ⚠ {GATE_VALIDATION_JSON} missing -- run verify/validate_gp6806_gate.py; the docstring's")
        print("      on-car numbers are then QUOTED, not checked.")
        return False
    got = json.load(open(GATE_VALIDATION_JSON, encoding="utf-8"))
    for route, want in GATE_VALIDATION.items():
        assert route in got, f"{label}: {route} missing from the gate-validation artifact"
        for k, v in want.items():
            g = got[route][k]
            assert abs(g - v) <= (0.001 if isinstance(v, float) else 0), \
                f"{label}: {route}.{k} is {g}, not the {v} the docstring states"
        assert got[route]["agreement_pct"] >= GATE_AGREEMENT_MIN, \
            f"{label}: {route} agreement {got[route]['agreement_pct']}% is below " \
            f"{GATE_AGREEMENT_MIN}% -- gp-0x6806 is NOT the engagement flag and V67's design inverts"
        assert got[route]["transitions_per_s"] <= GATE_TPS_MAX, \
            f"{label}: {route} toggles at {got[route]['transitions_per_s']}/s -- the kill band " \
            f"starts at 15 Hz = 30 transitions/s; a gate above {GATE_TPS_MAX}/s needs re-examining"
    # the two routes must differ substantially in DUTY, or "not one route's pattern" is unearned
    duties = sorted(got[r]["duty_pct"] for r in GATE_VALIDATION)
    assert duties[-1] - duties[0] > 20.0, \
        f"{label}: the two validation routes have duties {duties} -- too similar to claim the " \
        "agreement is not one route's pattern"
    return got


def assert_probe_sites(code, label="V67"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V66 cave remnants survive past our payload"


def assert_repoint(code, label="V67", done=True):
    """The one-byte edit, and the whole `lp` chain it feeds, read FROM THE IMAGE."""
    want = REPOINT_TO if done else REPOINT_FROM
    got = bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4])
    assert got == want, \
        f"{label}: 0x{REPOINT_ADDR:05X} is {got.hex()}, expected {want.hex()}"
    # hw1 must equal the STOCK hw1 either way -- this is the "one byte" claim, machine-checked
    assert got[:2] == REPOINT_FROM[:2], f"{label}: hw1 at 0x{REPOINT_ADDR:05X} MOVED"
    mnem, disp, reg1, reg2 = decode_ldbu(got)
    assert (mnem, reg1, reg2) == ("ld.bu", GP, 15), f"{label}: 0x{REPOINT_ADDR:05X} is not ld.bu ->r15"
    assert disp == (GATE_DISP if done else DEAD_DISP), \
        f"{label}: 0x{REPOINT_ADDR:05X} addresses gp-0x{disp:04x}"
    if done:
        for a in REPOINT_TWINS:
            assert bytes(code[a:a + 4]) == REPOINT_TO, \
                f"{label}: the byte-identical twin @0x{a:05X} is not {REPOINT_TO.hex()}"
        assert bytes(code[REPOINT_REG2_TWIN[0]:REPOINT_REG2_TWIN[0] + 4]) == REPOINT_REG2_TWIN[1], \
            f"{label}: the reg2-only twin @0x{REPOINT_REG2_TWIN[0]:05X} moved"
    for addr, raw, what in LP_CHAIN:
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the lp chain at 0x{addr:05X} ({what}) is " \
            f"{bytes(code[addr:addr+len(raw)]).hex()}, expected {raw.hex()}"


def assert_signal_sites(code, label="V67"):
    """Every instruction donor the emitted encoders are pinned to, read FROM THE IMAGE."""
    for addr, raw, _disp, _reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_671D_R6, PIN_LDBU_671A_R12,
                                    PIN_LDBU_R6_HW1, PIN_LDBU_6806_R15):
        assert bytes(code[addr:addr + 4]) == raw, \
            f"{label}: the pinned ld.bu at 0x{addr:05X} is {bytes(code[addr:addr+4]).hex()}, not " \
            f"{raw.hex()}"
    for addr, raw in (PIN_BLT6,):
        assert bytes(code[addr:addr + len(raw)]) == raw, \
            f"{label}: the pinned branch at 0x{addr:05X} is not {raw.hex()}"
    assert bytes(code[PIN_CMP_P1_R6[0]:PIN_CMP_P1_R6[0] + 2]) == PIN_CMP_P1_R6[1], \
        f"{label}: the pinned `cmp 0x1,r6` at 0x{PIN_CMP_P1_R6[0]:05X} moved"
    assert bytes(code[PIN_CMP5_R6[0]:PIN_CMP5_R6[0] + 2]) == PIN_CMP5_R6[3], \
        f"{label}: the pinned `cmp 0x5,r6` at 0x{PIN_CMP5_R6[0]:05X} moved"
    # the third arm's own test, and CEIL's width. Reading 0xC64FA as u16 gives 517, not 5.
    assert code[CEIL_CAL] == CEIL_VALUE, \
        f"{label}: CEIL 0x{CEIL_CAL:05X} is {code[CEIL_CAL]}, not {CEIL_VALUE} -- the cave hardcodes " \
        f"{CEIL_VALUE}, so bit4 would no longer mean 'the third arm is selected'"
    assert bytes(code[0x3AA78:0x3AA7C]) == bytes.fromhex("8577fb74"), \
        f"{label}: `ld.bu 0x74fa[tp],r14` @0x3AA78 moved -- the arm test no longer reads CEIL"
    assert bytes(code[0x3AA7C:0x3AA80]) == bytes.fromhex("ee61d105"), \
        f"{label}: `cmp r14,r12 / bc 0x3AA88` @0x3AA7C moved -- the >= test itself"
    assert bytes(code[0x3AA80:0x3AA82]) == bytes.fromhex("0112") and \
        bytes(code[0x3AA88:0x3AA8A]) == bytes.fromhex("0012"), \
        f"{label}: the r2 = (state >= CEIL) assignment moved"
    # gp-0x671d's own priority test, ahead of the arm
    assert bytes(code[0x3ABFA:0x3ABFE]) == bytes.fromhex("e031c205"), \
        f"{label}: `cmp r0,r6 / be 0x3AC04` @0x3ABFA moved -- gp-0x671d's priority test"
    assert bytes(code[0x3ABFE:0x3AC02]) == bytes.fromhex("e5574374"), \
        f"{label}: `ld.hu 0x7442[tp],r10` @0x3ABFE moved -- gp-0x671d's arm"
    assert bytes(code[0x3AC0E:0x3AC12]) == bytes.fromhex("e011b205"), \
        f"{label}: `cmp r0,r2 / be 0x3AC16` @0x3AC0E moved -- the third arm's test"
    assert bytes(code[0x3AC12:0x3AC16]) == bytes.fromhex("e5574174"), \
        f"{label}: `ld.hu 0x7440[tp],r10` @0x3AC12 moved -- the third arm"
    V65.assert_signal_sites(code, label)


# ---- V62's and V63's tables, with the ONE documented exception ---------------------------------------
# 🛑 Both parents assert 0xC6446 == 512, which is precisely what V67 changes. Rather than skip the
# parent functions, their tables are re-run here with a single override, and the override set is
# itself asserted to be exactly {0xC6446}. A future edit to either parent table therefore cannot
# widen the exception silently.
ARM_EXCEPTION = {ARM_ADDR: ARM_NEW}


def assert_untouched_context_v67(code, label="V67"):
    """V62.assert_untouched_context, with 0xC6446 expected at V67's value instead of 512."""
    overridden = set()
    for addr, want, what in V62.TAP_STOCK:
        assert u16(code, addr) == want, f"{label}: tap 0x{addr:05X} ({what}) moved"
    for addr, want, what in V62.CLAMP_CTX:
        got = bytes(code[addr:addr + len(want)])
        assert got == want, f"{label}: shared-clamp context at 0x{addr:05X} ({what}) is {got.hex()}"
    for addr, want, what in V62.SUM_CTX:
        assert u16(code, addr) == want, f"{label}: aggregator sum at 0x{addr:05X} ({what}) moved"
    for addr, want, what in V61.RATE_GAIN_CALS:
        if addr in ARM_EXCEPTION:
            overridden.add(addr)
            want = ARM_EXCEPTION[addr]
        assert u16(code, addr) == want, \
            f"{label}: rate gain cal 0x{addr:05X} ({what}) is {u16(code, addr)}, expected {want}"
    for base, ys in zip(V62.RATE_A_RECORDS, V62.RATE_A_Y_STOCK):
        assert struct.unpack_from("<4h", code, base + 0xA) == ys, \
            f"{label}: r26 gain_A record 0x{base:05X} Y row moved -- V42's edit must NOT be present"
    for a, t in zip(V62.GAIN_B_LERP_MODE10, V62.GAIN_B_LERP_MODE22):
        assert bytes(code[a:a + 0x12]) == bytes(code[t:t + 0x12]), \
            f"{label}: gain_B default record mode-10 0x{a:05X} != mode-22 0x{t:05X}"
    assert overridden == set(ARM_EXCEPTION), \
        f"{label}: V61.RATE_GAIN_CALS no longer lists 0x{ARM_ADDR:05X} -- the exception is stale"


def assert_untouched_v67(code, label="V67"):
    """V63.assert_untouched, with the same single override."""
    overridden = set()
    for addr, want, width, what in V63.MUST_STAY_STOCK:
        if addr in ARM_EXCEPTION:
            overridden.add(addr)
            want = ARM_EXCEPTION[addr]
        got = u16(code, addr) if width == 2 else code[addr]
        assert got == want, f"{label}: 0x{addr:05X} ({what}) is {got}, expected {want}"
    for base, ys in zip(V63.RATE_A_RECORDS, V63.RATE_A_Y_STOCK):
        assert struct.unpack_from("<4h", code, base + 0xA) == ys, \
            f"{label}: r26 smooth-steering gain_A record 0x{base:05X} moved -- the MANUAL path"
    for a, t in zip(V63.GAIN_B_MODE10, V63.GAIN_B_MODE22):
        assert bytes(code[a:a + 0x12]) == bytes(code[t:t + 0x12]), \
            f"{label}: r24 smooth-steering LERP mode-10 0x{a:05X} != mode-22 0x{t:05X}"
    for addr, want in V63.SAR_SITES:
        assert u16(code, addr) == want, \
            f"{label}: 0x{addr:05X} is not stock `sar 0xa` -- V67 keeps V66's reverts"
    for addr, want in V63.TAP_SITES:
        assert u16(code, addr) == want, f"{label}: 0x{addr:05X} tap is not stock r1"
    assert overridden == set(ARM_EXCEPTION), \
        f"{label}: V63.MUST_STAY_STOCK no longer lists 0x{ARM_ADDR:05X} -- the exception is stale"
    # r26's arm on the SAME gate, and the record that makes it harmless
    assert u16(code, R26_ARM_ADDR) == R26_ARM_STOCK, \
        f"{label}: r26's arm 0x{R26_ARM_ADDR:05X} is {u16(code, R26_ARM_ADDR)}, not stock " \
        f"{R26_ARM_STOCK} -- it rides the SAME gate the repoint makes live"
    assert set(code[R26_AVG_CAL:R26_AVG_CAL + R26_AVG_LEN]) == {0}, \
        f"{label}: 0x{R26_AVG_CAL:05X}+{R26_AVG_LEN} is no longer all-zero -- the r26-INERT record " \
        "is the only thing making r26's shared gate harmless. STOP and re-derive."


# =======================================================================================================
# The census -- the REQUIRED second method, re-run over the built image on every build, TWICE
# =======================================================================================================
# (readers, writers, writer addresses, permitted access mnemonics)
GATE_WRITERS = list(V66.CENSUS_EXPECTED[0x6806][2])      # 16, inherited from V66's own census
MASK_WRITERS = list(V66.CENSUS_EXPECTED[MASK_DISP][2])   # [0x3BD2A, 0x41EC6]
ARM3_WRITERS = [V64.STATE_WRITER]                        # [0x42A12] -- SOLE writer image-wide
assert (V66.CENSUS_EXPECTED[0x6806][:2], V66.CENSUS_EXPECTED[MASK_DISP][:2]) == ((13, 16), (14, 2)), \
    "V66's own census counts moved -- V67's expectations are derived from them and are now stale"
assert len(GATE_WRITERS) == 16 and MASK_WRITERS == [0x3BD2A, 0x41EC6]

CENSUS_EXPECTED_SRC = {                     # on the V66 SOURCE, before the repoint
    GATE_DISP: (13, 16, GATE_WRITERS, {"ld.bu", "st.b"}),
    DEAD_DISP: (1, 0, [], {"ld.bu"}),
    MASK_DISP: (14, 2, MASK_WRITERS, {"ld.bu", "st.b"}),
    ARM3_DISP: (7, 1, ARM3_WRITERS, {"ld.bu", "st.b"}),
}
CENSUS_EXPECTED = {                         # on the V67 OUTPUT: the repoint moves ONE reader
    GATE_DISP: (14, 16, GATE_WRITERS, {"ld.bu", "st.b"}),
    DEAD_DISP: (0, 0, [], {"ld.bu"}),       # *** 0 readers: the cell is now UNREFERENCED image-wide
    MASK_DISP: (14, 2, MASK_WRITERS, {"ld.bu", "st.b"}),
    ARM3_DISP: (7, 1, ARM3_WRITERS, {"ld.bu", "st.b"}),
}
# The consumer each cell is calibrated against -- these must survive as readers.
CENSUS_CONSUMERS_SRC = {GATE_DISP: 0x2A1B6, DEAD_DISP: REPOINT_ADDR,
                        MASK_DISP: 0x3AB98, ARM3_DISP: 0x3AA70}
CENSUS_CONSUMERS = {GATE_DISP: REPOINT_ADDR,   # *** the repoint itself, asserted as a reader
                    MASK_DISP: 0x3AB98, ARM3_DISP: 0x3AA70}
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# Where THIS cave reads each cell, derived from the listing so it can never drift from the code.
CAVE_CELL_READS = {}
for _disp, _bit, _name, _l, _c, _w in CELLS:
    _sites = [a for a, r, _ in CAVE_LISTING if r == V55.ldbu_any(-_disp, R6)]
    assert len(_sites) == 1, f"gp-0x{_disp:04x} must be read EXACTLY once in the cave"
    CAVE_CELL_READS[_disp] = _sites[0]


def scan_self_check(buf, label="V67", repointed=True):
    """SCAN.self_check, re-pinned -- it hard-codes 0x3AA94 == gp-0x683c, which V67 CHANGES.

    🛑 Calling SCAN.self_check on a V67 image would fail on the very edit the build is making, so
    the four gp-0x6b94 cases are re-run verbatim and the hw1-bit-5 pin is MOVED to a case that is
    strictly stronger: gp-0x671d's displacement 0x98E3 is ODD, so it actually exercises the
    opcode-0x3D path, whereas BOTH gp-0x683c and gp-0x6806 are EVEN and never did. Its neighbour
    gp-0x671a (EVEN, three bytes away) is pinned alongside it, so a parity slip in either direction
    fails here rather than on the car.
    """
    cases = [(0x453E0, "ld.h", 4, (-0x6B94) & 0xFFFF, 6, False),
             (0x3ACEC, "ld.h", 4, (-0x6B94) & 0xFFFF, 13, False),
             (0x3ACFA, "st.h", 4, (-0x6B94) & 0xFFFF, 12, True),
             (0x3AD20, "st.h", 4, (-0x6B94) & 0xFFFF, 10, True),
             (0x3AB98, "ld.bu", 4, (-MASK_DISP) & 0xFFFF, 6, False),     # ODD disp -- the real test
             (0x3AA70, "ld.bu", 4, (-ARM3_DISP) & 0xFFFF, 12, False),    # EVEN neighbour
             (REPOINT_ADDR, "ld.bu", 4,
              (-(GATE_DISP if repointed else DEAD_DISP)) & 0xFFFF, 15, False)]
    for addr, mnem, reg1, disp, reg2, is_store in cases:
        got = SCAN.decode_fmt7(buf, addr)
        assert got is not None, f"{label}: 0x{addr:05X} did not decode at all"
        g_reg2, g_mnem, g_disp, g_store, g_reg1 = got
        assert (g_mnem, g_reg1, g_disp, g_reg2, g_store) == (mnem, reg1, disp, reg2, is_store), \
            f"{label}: 0x{addr:05X} decodes as {got}, expected " \
            f"{(reg2, mnem, disp, is_store, reg1)}"
    # the ODD and EVEN pins must really differ in the OPCODE field, or the check proves nothing
    odd_op = (struct.unpack_from("<H", buf, 0x3AB98)[0] >> 5) & 0x3F
    even_op = (struct.unpack_from("<H", buf, 0x3AA70)[0] >> 5) & 0x3F
    assert (odd_op, even_op) == (0x3D, 0x3C), \
        f"{label}: the ODD/EVEN ld.bu pins carry opcodes 0x{odd_op:02X}/0x{even_op:02X}, not 3D/3C"


def assert_cell_census(buf, label="V67", cave_reads=None, expected=None, consumers=None):
    """Re-derive the reader/writer sets from raw bytes and assert them exactly, by TWO decoders.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    expected = CENSUS_EXPECTED if expected is None else expected
    consumers = CENSUS_CONSUMERS if consumers is None else consumers
    cave_reads = CAVE_CELL_READS if cave_reads is None else cave_reads
    span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    for disp, (n_read, n_write, writers, mnems) in expected.items():
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
            f"{label}: gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}"
        assert [a for a, _, _ in writes] == writers, \
            f"{label}: gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}"
        if disp in consumers:
            assert any(a == consumers[disp] for a, _, _ in reads), \
                f"{label}: the consumer at 0x{consumers[disp]:05X} no longer reads gp-0x{disp:04x}"
        # ⚠ GATE 1 restated as a MEASUREMENT: the cave READS this cell and WRITES it nowhere.
        cave = [h for h in hits if h[0] in span]
        want = [(cave_reads[disp], "ld.bu", R6)] if disp in cave_reads else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"

        # ---- SECOND METHOD: per-opcode decode over EVERY byte offset + the 48-bit extended form.
        if disp == GATE_DISP:
            scan_self_check(buf, label, repointed=(expected is CENSUS_EXPECTED))
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
            assert not ext, f"{label}: gp-0x683c has {len(ext)} extended-displacement candidates"
            assert n_write == 0 and not writes, f"{label}: gp-0x683c has acquired a writer"
        assert not genuine, \
            f"{label}: gp-0x{disp:04x} has {len(genuine)} extended-form candidate(s) that are NOT " \
            f"32-bit aliases: {[hex(h['addr']) for h in genuine[:8]]}"


def assert_decoder_matches(cave_bytes, label="V67"):
    """🛑 The decoder's header must match the BUILT image, not a previous revision.

    V66's decoder header was stale for one revision and said bit4 = gp-0x683c when the image read
    gp-0x67fe. That is the exact trap this kit has been bitten by (`0x87` meaning opposite things on
    V62 vs V64), so the link is made MECHANICAL: probe/decode_v67_gate.py carries the built cave's hex and
    the build fails if they disagree.
    """
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, f"{label}: {DECODER} carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"{label}: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   " \
        f"{cave_bytes.hex()}"
    for disp, bit, name, lvl, _c, _w in CELLS:
        needle = f"gp-0x{disp:04x}"
        assert needle in txt, f"{label}: the decoder never mentions {needle} (bit{bit.bit_length()-1})"
    assert f"0x{ARM_NEW:X}" in txt or str(ARM_NEW) in txt, \
        f"{label}: the decoder does not carry the arm value {ARM_NEW}"
    return True


def build():
    if not os.path.exists(V66_BIN):
        print(f"  {V66_BIN} missing -- running the V66 builder first\n")
        V66.build()
    v66 = bytearray(open(V66_BIN, "rb").read())
    sha = hashlib.sha256(bytes(v66)).hexdigest()
    print(f"  V66 source {V66_BIN}\n    SHA256 {sha}")
    assert sha == V66_SOURCE_SHA256, \
        f"the V66 source SHA is {sha}, not the {V66_SOURCE_SHA256} this build is written against"

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v66, "V66 source")
    assert walk(bytes(v66), label="V66 source") == 0
    assert walk_all_blocks(bytes(v66), label="V66 source") == 0
    V66.assert_probe_sites(v66, "V66 source")        # V66's OWN cave must be intact first
    V66.assert_signal_sites(v66, "V66 source")
    V66.assert_cell_census(bytes(v66), "V66 source")
    V59.assert_index_chain(v66, "V66 source")
    V55.assert_variant_tables(v66)
    V57.assert_decoupled(v66, "V66 source")
    assert u16(v66, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V66 source lost the lockout edit"
    V62.assert_sar_sites(v66, "V66 source", expect_doubled=False)
    V62.assert_untouched_context(v66, "V66 source")
    V63.assert_arms(v66, "V66 source", expect_raised=False)
    V63.assert_untouched(v66, "V66 source")          # incl. 0xC6446 == 512, before the edit
    assert u16(v66, V62.BLEND_ADDR) == V62.BLEND_STOCK, "V60's falsified blend must be absent"
    V66.assert_gain_b_surface(v66, v66, "V66 source")
    assert_signal_sites(v66, "V66 source")
    assert_repoint(v66, "V66 source", done=False)
    # V66's OWN cave reads gp-0x6806 (its bit6) and nothing else V67 cares about -- that is the
    # pre-edit GATE 1 baseline, and it is taken from V66's listing, not written by hand.
    v66_cave_reads = {d: a for d, a in V66.CAVE_CELL_READS.items() if d in CENSUS_EXPECTED_SRC}
    assert v66_cave_reads == {GATE_DISP: 0xC4B38}, \
        f"V66's cave reads {v66_cave_reads} of V67's cells -- the source baseline is stale"
    assert_cell_census(bytes(v66), "V66 source", cave_reads=v66_cave_reads,
                       expected=CENSUS_EXPECTED_SRC, consumers=CENSUS_CONSUMERS_SRC)
    print("    census OK (TWO decoders): gp-0x6806 13r/16w, gp-0x683c 1r/0w, gp-0x671d 14r/2w,")
    print("               gp-0x671a 7r/1w -- every access a BYTE; V66's cave touches none of them")
    print(f"    0x{REPOINT_ADDR:05X} = {REPOINT_FROM.hex()}  ld.bu -0x683c[gp],r15   (the DEAD gate)")
    print(f"    0x{ARM_ADDR:05X} = {u16(v66, ARM_ADDR)}   0x{R26_ARM_ADDR:05X} = "
          f"{u16(v66, R26_ARM_ADDR)}   0x{CEIL_CAL:05X} = {v66[CEIL_CAL]} (BYTE)")

    # ---- ★★ THE GATE, VALIDATED ON-CAR -----------------------------------------------------------
    print("\n  ★★ GATE 2 IS MEASURED, NOT ARGUED -- gp-0x6806 validated on V57's flown probe:")
    pol = assert_v57_probe_polarity("V67")
    val = assert_gate_validation("V67")
    if pol:
        print("    POLARITY confirmed from the FLOWN V57 image, one byte at a time:")
        for addr, raw, what in V57_PROBE_RUNG:
            print(f"      0x{addr:05X}  {raw.hex():<10s} {what}")
        print("      => V57's bit6 is set only when gp-0x6806 == 0, so the validation's inversion is")
        print("         REAL and the 99.9% agreement belongs to `gp-0x6806 != 0`. If that branch had")
        print("         been `be`, V67's polarity AND its 5244 arm would both invert.       PASS")
    if val:
        print(f"    {'route':>10s} {'frames':>8s} {'agree w/ latActive':>20s} {'duty':>8s} "
              f"{'transitions':>13s}")
        for route, v in val.items():
            print(f"    {route.replace('_cache_r', 'route '):>10s} {v['frames']:>8d} "
                  f"{v['agreement_pct']:>19.3f}% {v['duty_pct']:>7.2f}% "
                  f"{v['transitions']:>4d} = {v['transitions_per_s']:.4f}/s")
        tot = sum(v["frames"] for v in val.values())
        trn = sum(v["transitions"] for v in val.values())
        print(f"    pooled {tot:,} frames, {trn} transitions. Two very different duties (21.7% vs")
        print("    49.9%) => not one route's pattern; and no dropout during steady engaged holding,")
        print("    which is the one hole static analysis could not close (ramp-FSM phases 5/6/7).")
        print("    ⚠ The transition COUNT is not the strong evidence -- 4 and 9 are small. The")
        print("      STRUCTURAL argument is: a signal agreeing with latActive to 99.9% over 37,914")
        print("      frames toggles when the DRIVER engages, and cannot also toggle at 21/45 Hz")
        print("      without destroying that agreement.                                     PASS")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    V62.assert_sar_sites(baseline, "V38 baseline", expect_doubled=False)
    V63.assert_untouched(baseline, "V38 baseline")
    assert_repoint(baseline, "V38 baseline", done=False)
    V66.assert_gain_b_surface(baseline, v66, "V38 baseline")
    print("    V38 baseline reads `sar 0xa` at both sites and the DEAD gate at 0x3AA94 -- V67's two")
    print("    edits are the only difference from stock behaviour on this lane")

    code = bytearray(v66)

    # ---- EDIT 1: the repoint. ONE BYTE. ----------------------------------------------------------
    print(f"\n  EDIT 1 -- repoint the DEAD gate load to the LKAS-active flag  (ONE BYTE):")
    print(f"    0x{REPOINT_BYTE:05X}  0x{code[REPOINT_BYTE]:02X} -> 0x{REPOINT_TO[2]:02X}")
    code[REPOINT_BYTE] = REPOINT_TO[2]
    print(f"    0x{REPOINT_ADDR:05X}  {REPOINT_FROM.hex()} -> {bytes(code[REPOINT_ADDR:REPOINT_ADDR+4]).hex()}"
          f"   ld.bu -0x683c[gp],r15 -> ld.bu -0x6806[gp],r15")
    print(f"    byte-identical real instances of the RESULT: "
          f"{', '.join(f'0x{a:05X}' for a in REPOINT_TWINS)}"
          f"  (+ 0x{REPOINT_REG2_TWIN[0]:05X}, reg2 only)")
    assert_repoint(code, "V67", done=True)

    # ---- EDIT 2: the arm -------------------------------------------------------------------------
    print(f"\n  EDIT 2 -- r24's now-live arm:")
    print(f"    0x{ARM_ADDR:05X}  {u16(code, ARM_ADDR)} -> {ARM_NEW}"
          f"   = {ARM_MULTIPLIER}.00 x LERP({GRIND1_KMH} km/h, {GRIND1_DEGS} deg/s) = "
          f"{ARM_MULTIPLIER} x {GRIND1_LERP}")
    assert u16(code, ARM_ADDR) == ARM_STOCK, "the arm is not stock before the edit"
    struct.pack_into("<H", code, ARM_ADDR, ARM_NEW)
    print(f"    0x{R26_ARM_ADDR:05X}  {u16(code, R26_ARM_ADDR)} (UNCHANGED) -- r26's arm on the SAME "
          "gate; r26 is inert (0xC6564 = 40 zero bytes)")

    # ---- EDIT 3: replace the cave payload ---------------------------------------------------------
    print(f"\n  EDIT 3 -- replace V66's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare; a fourth rung needs 12):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v66[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V66's -- same cave base, same jarl"
    assert_probe_sites(code, "V67")
    assert_signal_sites(code, "V67")
    assert_cell_census(bytes(code), "V67")

    # ---- the gates, each PRINTED with its result --------------------------------------------------
    print("\n  GATES on the built image (each re-derived, not inherited):")
    n_store = sum(1 for _, raw, _ in CAVE_LISTING if len(raw) >= 4
                  and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B))
    print(f"    GATE 1  cave stores = {n_store} (the CAN-330 payload byte only); the repoint adds no")
    print("            store and claims no RAM cell                                        PASS")
    print("    census (TWO decoders, on the OUTPUT):")
    for disp in (GATE_DISP, DEAD_DISP, MASK_DISP, ARM3_DISP):
        hits = V64.gp_access_census(bytes(code), disp)
        span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
        fw = [h for h in hits if h[0] not in span]
        r = len([h for h in fw if h[1] in _READ_MNEM])
        w = len(fw) - r
        cv = [hex(h[0]) for h in hits if h[0] in span]
        note = ""
        if disp == DEAD_DISP:
            note = "  *** UNREFERENCED image-wide -- the repoint removed its only reader"
        elif disp == GATE_DISP:
            note = f"  (+1 firmware reader: the repoint @0x{REPOINT_ADDR:05X})"
        print(f"      gp-0x{disp:04x}  {r:2d}r / {w:2d}w firmware, cave {cv or 'none'}{note}")
    print("    gain_B surface: all FOUR mode-10 records + all FOUR pointer slots  (V62's tripwire")
    print("            watched only 2 of 4 -- widened):")
    for arr, rec, (xs, ys) in zip(V66.GAIN_B_PTR_ARRAYS, V66.GAIN_B_RECORDS, V66.GAIN_B_EXPECT):
        slot = arr + 4 * V66.GAIN_B_MODE
        same = bytes(code[rec:rec + V66.GAIN_B_RECORD_LEN]) == \
            bytes(v66[rec:rec + V66.GAIN_B_RECORD_LEN])
        print(f"      0x{arr:05X}[10] @0x{slot:05X} -> 0x{struct.unpack_from('<I', code, slot)[0]:05X}"
              f"  X{xs} Y{ys}  {'identical to V66' if same else '*** MOVED ***'}")
    print(f"    sar sites STOCK: 0x{V62.R24_SAR:05X}=0x{u16(code, V62.R24_SAR):04X}  "
          f"0x{V62.R26_SAR:05X}=0x{u16(code, V62.R26_SAR):04X}  "
          f"0x{V62.R26_SAR_FIRST:05X}=0x{u16(code, V62.R26_SAR_FIRST):04X}   PASS "
          "(expect_doubled=False)")

    # ---- every inherited invariant, read FROM THE BUILT IMAGE -------------------------------------
    V62.assert_sar_sites(code, "V67", expect_doubled=False)
    assert_untouched_context_v67(code, "V67")
    V63.assert_arms(code, "V67", expect_raised=False)
    assert_untouched_v67(code, "V67")
    V57.assert_decoupled(code, "V67")
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, "V67")
    V66.assert_gain_b_surface(code, v66, "V67")
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
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v66, a), \
            f"FIR coefficient 0x{a:05X} moved"

    # ---- MACHINE PROOF: the CAL block differs from V66's in EXACTLY the arm halfword -------------
    cal_d = [i for i in range(CAL_BLOCK[0], CAL_BLOCK[1]) if code[i] != v66[i]]
    assert cal_d == [ARM_ADDR, ARM_ADDR + 1], \
        f"the CAL block differs from V66's at {[hex(x) for x in cal_d]}, expected only the arm"

    # ---- GATE 9: every edited address is owned by the CRC block we recompute ----------------------
    for a, what, blk in ((CAVE_BASE, "cave base", MAIN_BLOCK),
                         (CAVE_BASE + len(V55.CAVE_BYTES) - 1, "cave last byte", MAIN_BLOCK),
                         (HOOK_ADDR, "hook", MAIN_BLOCK),
                         (REPOINT_BYTE, "the repoint byte", MAIN_BLOCK),
                         (V62.R24_SAR, "r24 sar", MAIN_BLOCK), (V62.R26_SAR, "r26 sar", MAIN_BLOCK),
                         (ARM_ADDR, "the arm", CAL_BLOCK), (ARM_ADDR + 1, "the arm hi", CAL_BLOCK)):
        assert V53.owning_block(code, a) == blk, \
            f"{what} 0x{a:05X} is not in the expected CRC block {[hex(x) for x in blk]}"

    # ---- CRC. BOTH blocks move: V67 edits code AND calibration. ----------------------------------
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        assert old_crc != new_crc, \
            f"the CRC for [0x{block[0]:X},0x{block[1]:X}) did not move, but its bytes did"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    sar_span = {a + k for a in (V62.R24_SAR, V62.R26_SAR) for k in (0, 1)}
    arm_span = {ARM_ADDR, ARM_ADDR + 1}
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    cal_crc = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    allowed66 = cave_span | arm_span | main_crc | cal_crc | {REPOINT_BYTE}

    d66 = [i for i in range(0x13000, 0x100000) if code[i] != v66[i]]
    stray = [i for i in d66 if i not in allowed66]
    assert not stray, \
        f"V67 differs from V66 outside cave + repoint + arm + both CRCs: {[hex(x) for x in stray[:16]]}"
    assert main_crc <= set(d66) and cal_crc <= set(d66), "a CRC trailer did not move"
    assert REPOINT_BYTE in d66 and arm_span <= set(d66), "an edit did not take"
    n_cave = len([i for i in d66 if i in cave_span])
    print(f"\n  V67 vs V66: {len(d66)} bytes  ({n_cave} cave + 1 repoint + 2 arm + 4 MAIN CRC + "
          f"4 CAL CRC)")
    print("    EXACT byte list (excluding the cave span and the two CRC trailers):")
    for i in sorted(set(d66) - cave_span - main_crc - cal_crc):
        print(f"      0x{i:05X}  0x{v66[i]:02X} -> 0x{code[i]:02X}   "
              f"(halfword 0x{u16(v66, i & ~1):04X} -> 0x{u16(code, i & ~1):04X})")
    print(f"    cave span 0x{CAVE_BASE:05X}-0x{CAVE_BASE + len(V55.CAVE_BYTES) - 1:05X}: "
          f"{n_cave} of {len(V55.CAVE_BYTES)} bytes differ")
    print(f"    MAIN CRC 0x{MAIN_BLOCK[1]:05X} (4) + CAL CRC 0x{CAL_BLOCK[1]:05X} (4)")
    print("    => the 0xD2000 block is byte-identical to V66's; all four mode-10 gain_B records and")
    print("       all four pointer-array slots are unchanged.")

    if os.path.exists(V62_BIN):
        v62 = bytearray(open(V62_BIN, "rb").read())
        d62 = [i for i in range(0x13000, 0x100000) if code[i] != v62[i]]
        outside = [i for i in d62 if i not in (allowed66 | sar_span)]
        assert not outside, \
            f"V67 differs from V62 outside cave + sar + repoint + arm + CRCs: " \
            f"{[hex(x) for x in outside[:8]]}"
        n_sar = len([i for i in d62 if i in sar_span])
        print(f"  V67 vs V62: {len(d62)} bytes  (cave + {n_sar} sar immediate + 1 repoint + 2 arm "
              f"+ both CRCs)")
        print("    => V62 applied the x2 EVERYWHERE via the shifts; V67 applies it ONLY when the")
        print("       gate is true, via the arm. Same dose at grind #1's point, different support.")
    if os.path.exists(V65_BIN):
        v65 = bytearray(open(V65_BIN, "rb").read())
        d65 = [i for i in range(0x13000, 0x100000) if code[i] != v65[i]]
        outside = [i for i in d65 if i not in (allowed66 | sar_span)]
        assert not outside, f"V67 differs from V65 outside the expected set: {[hex(x) for x in outside[:8]]}"
        print(f"  V67 vs V65: {len(d65)} bytes")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V67 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")
    assert not any(a <= V62.R24_SAR <= b or a <= V62.R26_SAR <= b for a, b in runs), \
        "V67 differs from V38 at a sar site -- V66's revert must be carried"

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V67")
    assert walk(bytes(code), label="V67") == 0
    assert walk_all_blocks(bytes(code), label="V67") == 0
    assert_probe_sites(code, "V67")
    assert_signal_sites(code, "V67")
    assert_repoint(code, "V67", done=True)
    V55.assert_variant_tables(code)
    V62.assert_sar_sites(code, "V67", expect_doubled=False)

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
    FF.assert_x31_checksum(rwd, "V67 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V67 readback")
    assert walk(bytes(readback), label="V67 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V67 readback") == 0
    assert_probe_sites(readback, "V67 readback")
    assert_signal_sites(readback, "V67 readback")
    assert_repoint(readback, "V67 readback", done=True)
    assert_cell_census(bytes(readback), "V67 readback")
    V66.assert_gain_b_surface(readback, v66, "V67 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V67 readback")
    V59.assert_index_chain(readback, "V67 readback")
    V62.assert_sar_sites(readback, "V67 readback", expect_doubled=False)
    assert_untouched_context_v67(readback, "V67 readback")
    V63.assert_arms(readback, "V67 readback", expect_raised=False)
    assert_untouched_v67(readback, "V67 readback")
    assert u16(readback, V57.PRIVATE_ADDR) == V57.GAIN_4X
    assert u16(readback, V57.GAIN_ADDR) == V57.GAIN_STOCK
    assert readback[0xC64A3] == 1 and readback[0xC64DE] == 27
    assert u16(readback, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(readback, ARM_ADDR) == ARM_NEW, "the readback lost the arm edit"
    assert u16(readback, R26_ARM_ADDR) == R26_ARM_STOCK
    assert readback[CEIL_CAL] == CEIL_VALUE

    # re-decode the cave FROM THE READBACK, instruction by instruction, against the listing
    print("\n  cave re-decoded from the READBACK (not from what we meant to write):")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)

    print("\n  cell loads re-decoded from the READBACK by scan_gp_accesses (the hw1-bit-5 guard),")
    print("  with the PARITY of every encoded cell:")
    print(f"    {'site':>9s}  {'bytes':<10s} {'cell':<12s} {'disp':<8s} {'parity':<7s} {'op':<5s} "
          f"{'bit':<5s} {'test':<9s} provenance")
    for disp, bit, name, lvl, cond, why in CELLS:
        a = CAVE_CELL_READS[disp]
        raw = bytes(readback[a:a + 4])
        mnem, got, reg1, reg2 = decode_ldbu(raw)
        assert (mnem, got, reg1, reg2) == ("ld.bu", disp, GP, R6), \
            f"{name}: readback @0x{a:05X} decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
        d16 = (0x10000 - disp) & 0xFFFF
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        prov = "FIELD-DECOMPOSED (weak, but FLOWN on V64)" if disp in WEAK_PIN_DISPS \
            else "byte-identical instance"
        test = "!= 0" if lvl == 1 else f">= {lvl}"
        print(f"    0x{a:05X}  {raw.hex():<10s} gp-0x{disp:04x}    0x{d16:04X}   "
              f"{'ODD' if d16 & 1 else 'EVEN':<7s} 0x{op:02X}  bit{bit.bit_length() - 1}  "
              f"{test:<9s} {prov}")

    print("\n  the REPOINT, re-decoded from the READBACK:")
    raw = bytes(readback[REPOINT_ADDR:REPOINT_ADDR + 4])
    mnem, got, reg1, reg2 = decode_ldbu(raw)
    print(f"    0x{REPOINT_ADDR:05X}  {raw.hex()}  {mnem} -0x{got:04x}[r{reg1}],r{reg2}")
    print(f"      was {REPOINT_FROM.hex()} (gp-0x{DEAD_DISP:04x}); hw1 {raw[:2].hex()} UNCHANGED; "
          f"only 0x{REPOINT_BYTE:05X} moved")
    print(f"      byte-identical to the real instructions at "
          f"{', '.join(f'0x{a:05X}' for a in REPOINT_TWINS)}")
    for addr, r, what in LP_CHAIN:
        print(f"    0x{addr:05X}  {bytes(readback[addr:addr+len(r)]).hex():<10s} {what}")
    print(f"    0x{FIRST_JARL_AFTER:05X}  the first `jarl` in FUN_0003aa2c -- AFTER both consumers, "
          "so lp is live throughout")

    print(f"\n  the ARM, read back: 0x{ARM_ADDR:05X} = {u16(readback, ARM_ADDR)}"
          f"   ({ARM_NEW}/{GRIND1_LERP} = {ARM_NEW / GRIND1_LERP:.2f}x at grind #1's point)")
    print(f"    r24 gain by state, at {GRIND1_KMH} km/h / {GRIND1_DEGS} deg/s:")
    for mask, gate, st, tag in ((0, 0, 0, "LKAS off             (bit6=0)"),
                                (0, 1, 0, "LKAS applying        (bit6=1)"),
                                (1, 1, 0, "gp-0x671d SET        (bit5=1)"),
                                (0, 0, CEIL_VALUE, "third arm selected   (bit4=1)")):
        g, note = r24_gain_under_v67(GRIND1_SPEED_COUNTS, GRIND1_RATE_COUNTS, gate, mask, st)
        out = EX.r24_lane(400, g, 10)
        base = EX.r24_lane(400, GRIND1_LERP, 10)
        print(f"      {tag}  gain {g:>5}  r24 {out:>6}  {out / base:>5.2f}x stock   {note}")
    sat = next(d for d in range(1, INPUT_CLAMP + 1) if abs(EX.r24_lane(d, ARM_NEW, 10)) >= LANE_CLAMP)
    print(f"    saturation: 5120 x {ARM_NEW} = {INPUT_CLAMP * ARM_NEW:,} = "
          f"{100 * INPUT_CLAMP * ARM_NEW / 0x7FFFFFFF:.2f}% of INT32_MAX; the lane clamps at "
          f"|dtorque| >= {sat} vs a MEASURED 123-839")
    print(f"    ⚠ the design note says 1599; that is the no-deadzone figure "
          f"(8192*1024/{ARM_NEW} = 1600). The 3-count deadzone (cal 0xC61F6) is subtracted BEFORE")
    print(f"      the clamp, so the real threshold is {sat}. Immaterial -- {sat / 839:.1f}x clear of "
          "the measured maximum -- but recorded rather than repeated.")

    ok = assert_decoder_matches(CAVE_BYTES, "V67")
    print(f"\n  decoder link: rlog-tools/probe/decode_v67_gate.py CAVE_HEX "
          f"{'MATCHES the built image' if ok else 'NOT CHECKED'}")

    print("\n  PROBE: 0x14A byte4  bit7 = LIVENESS (constant 1)")
    for disp, bit, name, lvl, cond, why in CELLS:
        t = "!= 0" if lvl == 1 else f">= {lvl}"
        print(f"                      bit{bit.bit_length() - 1} = gp-0x{disp:04x} {t:6s} "
              f"{name:11s} {why}")
    print("                      bit3 = UNUSED, never set")
    print("                      bits 2:0 = stock STEER_SENSOR_STATUS, preserved")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("  🛑 V66 AND V67 EMIT THE SAME EIGHT BYTES WITH DIFFERENT MEANINGS. bit3 does NOT")
    print("     separate them. Confirm the .rwd filename on the car before reading any verdict.")
    print("  GATE 1 RAM ownership: VACUOUS, and MEASURED -- the repoint is a read-only load")
    print("          displacement (no RAM claimed, no register allocation change); the census shows")
    print("          the cave reads each cell exactly once and writes none; the emitted listing")
    print("          contains EXACTLY ONE store, the existing CAN-330 payload byte gp-0x1514.")
    print("  GATE 2 closed-loop stability:")
    print("          * the lane is a DERIVATIVE => DC-neutral: a gain step at engagement produces")
    print("            NO torque step, only a change of damping coefficient.")
    print("          * ★★ THE GATE IS VALIDATED ON-CAR, so this is MEASURED, not argued:")
    print("            gp-0x6806 != 0 agrees with carControl.latActive at 99.899% / 99.943% over")
    print("            V57's routes 29/28 (37,914 frames, 379.1 s, duties 21.7% and 49.9%), at")
    print("            13 transitions total = 0.030-0.051/s. Three orders of magnitude below the")
    print("            21/45 Hz modes; it cannot parametrically pump. V57's `bne` polarity byte is")
    print("            asserted from the flown artifact. bit6 re-measures it on this drive.")
    print(f"          * magnitude: 5120 x {ARM_NEW} = 1.25% of INT32_MAX; lane saturation needs")
    print(f"            |dtorque| >= {sat} against a measured 123-839; the ten-lane sum clip was")
    print("            measured NEVER reached (120,049 frames).")
    print("          * gp-0x671d OUTRANKS the arm and pins the gain to 1024, BELOW stock -> bit5.")
    print("          * r26's arm rides the SAME gate; 0xC6444 stays stock 512 and r26 is inert")
    print("            (0xC6564 = 40 zero bytes, asserted). Direction is DOWN, not up.")
    print("          *** Still CODE in the 1 kHz TX path, which is why base/hook/extent are reused.")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is")
    print("        unmeasurable. Long drive, mixed: highway engaged, city manual, parking-lot creep.")
    print("     Condition on carControl.latActive or 0x18F byte4 bit3, NEVER carState.cruiseState.")
    print("     Decode with rlog-tools/probe/decode_v67_gate.py.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
