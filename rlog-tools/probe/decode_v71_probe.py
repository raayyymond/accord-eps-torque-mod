#!/usr/bin/env python3
"""probe/decode_v71_probe.py -- read V71's probe: WHICH GAIN ARM IS ACTUALLY IN FORCE.

WHY THIS PROBE READS SELECTORS AND NOT A LANE OUTPUT
-----------------------------------------------------
V64, V68, V69 and V70 each returned an uninterpretable zero, and each one had read an OUTPUT. V70's
own positive control -- `gp-0x6ada >= +512`, r24's post-clip lane mirror -- read **0 / 18,010**
against a replay predicting **311** from the route's own data (52 even under STOCK firmware). A lane
output that reads zero cannot tell you WHY. V71 puts bit6 on the chain's TOP selector and
repairs the positive control so a null is finally interpretable:

    0x3ABFA  gp-0x671d != 0  ->  cal 0xC6442 = 1024   *** OUTRANKS EVERYTHING ***      bit6
    0x3AC04  lp != 0         ->  cal 0xC6446 =  512   DEAD on V71 (gp-0x683c: 0 writers)
    0x3AC0E  gp-0x671a >= 5  ->  cal 0xC6440 = 2048   (rung CUT -- V67: 0.000%/186,321)
    0x3AC16  else                the mode-10 gain_B LERP -- STOCK on V71
    0x3AC20  sar 0xa -> 0x9      *** V71 DOUBLES THE LANE HERE, under EVERY arm ***

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7 = 1                   LIVENESS. field == 0 => the cave did not fire => the frame is VOID.
    bit6 = gp-0x671d != 0      THE MASK. If it fires, r24's gain is pinned to 1024 -- BELOW the
                               stock LERP -- and the LERP arm never runs. 📋 PRE-REGISTERED
                               PREDICTION: reads 0. V64 measured this cell at 0/route (bit3) and V67
                               at 0/186,321 frames (bit5). A NON-ZERO here would be new information
                               and would explain V70's null outright.
    bit5 = gp-0x67fa == 4      THE RATCHET STATE. V71 DISABLES the state-4 governor substitution
                               (0x454FE bne->br), so this rung measures how often it WOULD have
                               fired -- the fix and its own test on a single drive. `gp-0x67fa`'s
                               runtime value has never been read for state 4 in this kit; V70 tested
                               `== 10` and read 0, which left the state in {4,5,11}.
    bit4 = |gp-0x6ada| >= 128  *** THE REPAIRED POSITIVE CONTROL -- TWO-SIDED AND LOW. *** r24's
                               lane output after its own +/-0x2000 saturating clip, mirrored to RAM
                               by Honda's own code at 0x3AD5A every 1 kHz tick. 0 READERS / 1 WRITER
                               image-wide.
    bit3 = gp-0x6ada >= 0      *** THE SIGN. *** Read it WITH bit4: together they give the lane's
                               side AND its magnitude, which is what settles the polarity leg.

🛑🛑 WHY bit4 IS TWO-SIDED, AND WHY `gp-0x671a` WAS CUT TO PAY FOR IT
`gp-0x6ada >= +512` has now returned ZERO twice: 0/18,010 frames on V70's route and **0/47,990 on
V69's route `4f`** -- at DOUBLE V70's dose, where the rung needed only **49 counts** of |dtorque|
against a repo-recorded max of **839**. That is not an arm-selection story. It points at either
  (a) the `dtorque` RECONSTRUCTION -- a 4-sample difference at 1 kHz rebuilt from a 100 Hz bus copy
      of a different, filtered torque cell; or
  (b) POLARITY -- a one-sided `>= +512` test is structurally blind to a lane living on the negative
      side.
A one-sided rung cannot separate them, and re-flying it would be the fifth uninterpretable zero in a
row. So bit4 is now TWO-SIDED and eight times lower, and the freed budget buys bit3 = the SIGN, which
reads (b) out directly. `gp-0x671a >= 5` was the designated cut: V67 measured it at **0.000% over
186,321 frames on two routes** and V64 measured both `>= 5` and `!= 0` at zero.

⚠ THE EXACT TEST, because it is ONE COUNT asymmetric and that must not be glossed:

        bit4  =  (gp-0x6ada >= +128)  OR  (gp-0x6ada <= -129)

`sar` FLOORS, so `x sar 7 == -1` spans x in [-128,-1] and no single shifted compare can split
x = -128 from x = -127. The negative arm therefore trips at -129. That is |x| >= 128 for every value
EXCEPT x == -128 exactly -- one count out of a +/-8192 lane. Proven exhaustively over all 65,536
halfword patterns in `_self_check()` below, not asserted in prose.

📋 THE PRE-REGISTERED THRESHOLDS. The rung fires at |dtorque| >= 128 x 2^7 / gain, i.e. **5 to 32
counts on EVERY branch of the priority chain**, against a recorded max of 839 and V69's own flight
max of 633.9 (re-derived from the image by builds/v50_v79/build_v71a_tva.py's own sweep, not quoted):
    mask arm 0xC6442 = 1024 -> 16.0 · third arm 0xC6440 = 2048 -> 8.0 · dead arm 0xC6446 -> 32.0
    LERP creep (3072) -> 5.3 · grind #1 (2622) -> 6.2 · grind #2 creep (2377) -> 6.9 · hwy -> 7.5
The rung this replaces needed 85-241 counts on the LERP branch and read ZERO on both routes.
⇒ a null at these thresholds refutes BOTH (a)-as-arms and (b), and moves the next probe onto
  dtorque's PRODUCER or onto gp-0x6ada's writer @0x3AD5A. Either outcome is actionable, which is the
  property V64/V68/V69/V70 lacked.

🛑 IDENTIFICATION IS WEAKER ON V71 THAN ON V70, AND THAT IS STATED RATHER THAN PAPERED OVER.
V70 carried an arithmetic invariant (its bit6 => its bit3, because x >= +512 implies x >= 0) that
excluded six builds absolutely from the VALUE SET alone. V71's four rungs are INDEPENDENT -- all four
(bit4, bit3) combinations are reachable, asserted at build time -- so all 16 payloads are legal and
none is forbidden. What remains:
  * HARD: bit7 must be set in every frame. A VOID frame means the cave did not run.
  * A bit4=1/bit3=0 frame is V71-shaped and V70 cannot emit its analogue (bit6=1/bit3=0).
  * The .rwd FILENAME is the pre-drive discriminator, and V71's is unique on disk.
🛑 THE "FAST-TOGGLING bit3 MEANS V70" FALSIFIER THAT V71's FIRST CUT CARRIED IS **RETIRED**. On this
cut bit3 IS a sign bit, exactly like V70's, so that test would now return a confidently WRONG answer.
Do not reintroduce it.

🛑🛑 THIS DECODER SERVES **TWO** BUILDS, AND THEY ARE NOT SEPARABLE ON THE WIRE.
**V71A** and **V71B** carry a **BYTE-IDENTICAL 68-byte cave**, so every payload this file decodes is
consistent with both. The **.rwd FILENAME is the only pre-drive discriminator**:
    V71A  39990-TVA,A160-V71A-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V62sar-BOTHLANES-surfREVERTED-probe2-671d-67fa4-6adaABS128-sign-can330byte4-0x13000-0x100000.rwd
    V71B  39990-TVA,A160-V71B-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-gainA-rec0rec1-x2-SPEEDSHAPED-sarSTOCK-probe2-671d-67fa4-6adaABS128-sign-can330byte4-0x13000-0x100000.rwd
They differ ONLY in how r26 is dosed and whether r24 is dosed at all:
  * **V71A** -- both `sar` sites at 0x9. r24 AND r26 doubled, FLAT 2.000000x at every speed.
  * **V71B** -- both `sar` sites STOCK; `gain_A` rec0/rec1 Y[0..3] doubled instead. **r26 alone**,
    2.000000x at <= 10 km/h tapering to EXACTLY 1.000000x at >= 50 km/h. **r24 is fully STOCK.**
🛑🛑 CORRECTED 2026-08-04 -- THE PREVIOUS TEXT HERE WAS WRONG IN BOTH DIRECTIONS AND MISLED A BRIEF.
It said bit4 "reads `gp-0x6ada`" on every sibling and that V71B's one-byte mirror fix "was NOT
applied". **Both are false.** The fix WAS applied: `CAVE_HEX_B[0x1A] == 0x24` (asserted in
`_self_check()` below), and `builds/v50_v79/build_v71b_tva.py` sets `MIRROR = A.R26_MIRROR_DISP`. **Each build
watches the lane IT doses** -- V71A/V71C read `gp-0x6ada` (**r24**), V71B reads `gp-0x6adc` (**r26**).
⇒ **A bit4 or bit3 duty from V71B and one from V71A/V71C MEASURE DIFFERENT CELLS ON DIFFERENT SCALES**
(r26 carries an extra `avg(gp-0x69a4)` factor) **and must never be ratioed.** Read the cell off
`BUILDS[<build>]["cell"]`; never assume it, and confirm the .rwd filename (`6adaABS128` vs
`6adcABS128` is in the basename).
✅ **MEASURED 2026-08-04 -- THE RUNG WORKS, and the five-build null is BROKEN.** Routes 54 (V71B) and
58 (V71C), 100.0000% bit7 liveness on both, 0 VOID / 0 illegal. V71C's WITHIN-ROUTE positive control
-- engaged (arm 5244) vs manual (byte-for-byte stock), same cell, same drive -- reads **416x
[171.7, 1748.0]** episode-unit, **p = 0/20,000** label permutations, and **99.5x [11.0, 169.0]** with
both arms restricted to 5-20 km/h so neither is standing still. bit4 fired **4,478 / 50,546** engaged
frames on route 58 and **148 / 66,385** on route 54. ⇒ the fault behind V64/V68/V69/V70 was **never**
`gp-0x6ada`'s writer @0x3AD5A nor the cave's own read. r24's large excursions are near-symmetric
(2,245 positive / 2,233 negative), so the two-sided repair was the right call -- though symmetry alone
does not explain a zero, and the one-sided rung's THRESHOLD remains a live part of that story.

WHAT V71 IS -- so a reader of this file cannot mistake the artefact
-------------------------------------------------------------------
V71 restores BOTH of the kit's confirmed fixes and drops the falsified surface dose:
  * 0x454FE  bne -> br      V42's state-4 governor ratchet kill (CONFIRMED root cause, on-car).
  * 0x3AB76 + 0x3AC20       V62sar: `sar 0xa` -> `sar 0x9` on BOTH rate lanes -- a FLAT 2.000000x.
  * surfaceREVERTED         mode-10 gain_B rec0/rec1 back to STOCK 3072 / 2561.
Its rate lane is asserted BYTE-IDENTICAL to V62's and V65's, both of which flew flight-clean.
🛑 THE COST: V70's dose tapered to EXACTLY 1.000000x at and above 50 km/h; V71's does NOT, because a
shift immediate is speed-independent. The flat 2.00x is the configuration on record as having caused
grind #2 (11.71x). SCORE GRIND #2 AT SPEED SEPARATELY on this drive.

Usage:  python probe/decode_v71_probe.py <rlog-or-route-dir> [...]
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> out.txt` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parents[1]))
# ⚠ The NUMERIC MACHINERY is shared on purpose -- collect/sustained/runs_of are instrument code, not
# semantics, and two copies would drift. The 128-sample floor and the episode bootstrap were FIXED
# on 2026-08-04; do not re-derive them here and do not regress them.
from decode_v67_gate import collect, runs_of, sustained, transitions        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES, ratchet_line                    # noqa: E402
from decode_v70_probe import episode_ratio, episodes_of                     # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v71a_tva/build_v71b_tva assert_decoder_matches() fails the BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX_A = "203e1000a437e3986132a605483a843707986432aa05443a24372695a7326132be057f32ae05423ae031a605413ac33a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
CAVE_HEX_B = "203e1000a437e3986132a605483a843707986432aa05443a24372495a7326132be057f32ae05423ae031a605413ac33a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
# 🛑 ONE BYTE separates them, at offset 0x1A: V71A's bit4/bit3 read `ld.h -0x6ada[gp],r6`
# (**r24**'s post-clip mirror, st.h @0x3AD5A); V71B's read `ld.h -0x6adc[gp],r6` (**r26**'s,
# st.h @0x3AD4E). Each build watches the lane IT doses -- V71A doses both lanes via the `sar`
# sites, V71B doses r26 alone via gain_A. Both cells are 0 readers / 1 writer image-wide.
# ⇒ **A CROSS-BUILD COMPARISON OF bit4 OR bit3 BETWEEN A AND B IS NOT LIKE-FOR-LIKE.** They
# measure different lanes on different scales (r26 carries an extra `avg(gp-0x69a4)` factor).
#
#   0xC4B34  203e1000  movea 0x10,r0,r7      bit7 LIVENESS, in PRE-SHIFT weights
#   0xC4B38  a437e398  ld.bu -0x671d[gp],r6  THE MASK  (⚠ ODD displacement 0x98E3 => opcode 0x3D)
#   0xC4B3C  6132      cmp   0x1,r6          zero-extended byte: `< 1` IS `== 0`
#   0xC4B3E  a605      blt   +4
#   0xC4B40  483a      add   0x8,r7          bit6 = gp-0x671d != 0
#   0xC4B42  84370798  ld.bu -0x67fa[gp],r6  the ECU STATE byte
#   0xC4B46  6432      cmp   0x4,r6
#   0xC4B48  aa05      bne   +4              🛑 `be` (a205) is its twin and would INVERT this rung
#   0xC4B4A  443a      add   0x4,r7          bit5 = (gp-0x67fa == 4)
#   0xC4B4C  24372695  ld.h  -0x6ada[gp],r6  r24 lane out, post +/-0x2000 clip  (0 readers)
#   0xC4B50  a732      sar   0x7,r6          ARITHMETIC -- units of 128, sign preserved
#   0xC4B52  6132      cmp   0x1,r6          the POSITIVE bound
#   0xC4B54  be05      bge   +6              s >=  1 => x >= +128           -> SET
#   0xC4B56  7f32      cmp   -0x1,r6         the NEGATIVE bound (imm5 is SIGNED; -1 encodes 0x1F)
#   0xC4B58  ae05      bge   +4              s >= -1 => |x| is small        -> SKIP
#   0xC4B5A  423a      add   0x2,r7          bit4 = |gp-0x6ada| >= 128, TWO-SIDED (fallthrough)
#   0xC4B5C  e031      cmp   r0,r6           the SAME shifted value: (x sar 7) >= 0 <=> x >= 0
#   0xC4B5E  a605      blt   +4
#   0xC4B60  413a      add   0x1,r7          bit3 = gp-0x6ada >= 0   THE SIGN
#   0xC4B62  c33a      shl   0x3,r7          the 5-bit field -> bits 7:3.  V31P FLASHED this 4x;
#                                            Honda's own idiom @0x4FB82 (shl 0x3,r7 / andi 0xf8).
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]  THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6   the displaced hook instruction
#   0xC4B76  7f00      jmp   [lp]            -> 0x55C12
# 🛑🛑 THE CONDITION-NIBBLE TWINS. `bge +6` is **be05** and `be +6` is **b205** -- ONE NIBBLE apart,
# and the wrong one INVERTS the rung silently. Likewise `bge +4` = ae05 vs `be +4` = a205, and
# `blt +4` = a605. If you are hand-decoding, check the LOW nibble of the first byte: 0xE = bge,
# 0x6 = blt, 0xA = bne, 0x2 = be. Both `bge`s above are pinned BY VALUE against real instructions
# (0x6B176 and 0x244CE) and against the real `be +6` @0x3ABFC, in the builder and in the verifier.
# 🛑 `ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT apart -- and gp-0x6ada's only real instance
# IS the st.h form carrying the same displacement halfword. `ld.bu` 0x3C/0x3D vs `st.b` 0x3A is
# likewise one bit, on THREE rungs, one of them a LIVE state variable with 128 readers. If you ever
# see hw1 0x64.. or 0x44.. where 0x24.. / 0x84.. is written above, the cave WRITES. Do not flash it.
# ⚠ 68 of the 68 proven cave bytes are used. ZERO spare. The extent must NOT be grown to fit more --
# caves are this kit's only bricking class (V24, V27, V48B all bricked the ECU).
# ⚠ The role table at 0xC4124 is asserted unchanged by the builder ([0,0,5,0,5,5,0,0,0,5,0]); a slot
# carrying role 6 or 7 makes gp-0x67ac live and the rate lanes can drop out entirely.

BIT_LIVE = 0x80
BIT_MASK671D = 0x40           # bit6  gp-0x671d != 0        THE MASK -- outranks every arm
BIT_STATE4 = 0x20             # bit5  gp-0x67fa == 4        THE RATCHET STATE this build disables
BIT_R24_ABS = 0x10            # bit4  |gp-0x6ada| >= 128    THE REPAIRED POSITIVE CONTROL
BIT_R24_SIGN = 0x08           # bit3  gp-0x6ada >= 0        THE SIGN
PROBE_MASK = 0xF8
THRESHOLD = 128               # bit4: ld.h -> sar 0x7 -> cmp 0x1 / cmp -0x1  =>  |cell| >= 1 << 7
NEG_THRESHOLD = -129          # ⚠ `sar` FLOORS, so the NEGATIVE arm trips at -129, not -128. The test
                              # is |x| >= 128 for every value EXCEPT x == -128 exactly. One count out
                              # of a +/-8192 lane; proven exhaustively at build time, not hand-waved.
STATE_VALUE = 4

# The dispatcher's three masks. state in mask  <=>  (1 << (state & 0xf)) & mask.
MASK_DETECTOR = 0x830         # {4,5,11}     FUN_00036388 @0x22882, FUN_000428d4 @0x22926
MASK_AGGREGATOR = 0xC30       # {4,5,10,11}  FUN_0003a382 @0x226A0, FUN_0003aa2c @0x2291E
MASK_ARBITRATION = 0x930      # {4,5,8,11}   the arbitration trio

# (bit, short name, gp cell, what a 1 means)
# 🛑 THE BUILD MUST BE NAMED. V71A and V71B differ in ONE cave byte and are NOT separable from the
# wire, so this decoder REFUSES to guess: `--v71a` or `--v71b` is required. Guessing would be exactly
# the confident-wrong-answer failure this probe arc exists to end.
BUILDS = {
    "v71a": dict(cave=CAVE_HEX_A, lane="r24", cell=0x6ADA,
                 dose="both `sar` sites 0x9 -- r24 AND r26 doubled, FLAT 2.000000x at every speed",
                 rwd="39990-TVA,A160-V71A-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V62sar-BOTHLANES-surfREVERTED-probe2-671d-67fa4-6adaABS128-sign-can330byte4-0x13000-0x100000.rwd"),  # noqa: E501
    "v71b": dict(cave=CAVE_HEX_B, lane="r26", cell=0x6ADC,
                 dose="`sar` sites STOCK; gain_A rec0/rec1 Y[0..3] x2 -- r26 ALONE, 2.000000x at "
                      "<= 10 km/h tapering to EXACTLY 1.000000x at >= 50 km/h. r24 fully STOCK",
                 rwd="39990-TVA,A160-V71B-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-gainA-rec0rec1-x2-SPEEDSHAPED-sarSTOCK-probe2-671d-67fa4-6adcABS128-sign-can330byte4-0x13000-0x100000.rwd"),  # noqa: E501
    # 🛑 V71C shares V71A's cave BYTE FOR BYTE -- it doses r24 ~2x at creep through a scalar ARM
    # rather than a `sar` immediate, so it watches the same mirror. A and C are therefore the ONE
    # like-for-like bit4 comparison in this set; B is not comparable to either.
    "v71c": dict(cave=CAVE_HEX_A, lane="r24", cell=0x6ADA,
                 dose="V67/V68's LKAS gate + arm 5244 (r24) + arm 3072 (r26, the ~6x CUT REMOVED); "
                      "`sar` sites STOCK, gain_B STOCK. MANUAL is byte-for-byte stock",
                 rwd="39990-TVA,A160-V71C-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V67gate-arm5244-r26arm3072UNCUT-sarSTOCK-probe2-671d-67fa4-6adaABS128-sign-can330byte4-0x13000-0x100000.rwd"),  # noqa: E501
}


def rungs_for(build):
    """The bit map, with bit4/bit3's CELL resolved for the named build."""
    b = BUILDS[build]
    return ((BIT_MASK671D, "bit6 gp-0x671D", 0x671D,
             "THE MASK is SET -> r24's gain is pinned to cal 0xC6442 = 1024, BELOW the stock LERP"),
            (BIT_STATE4, "bit5 gp-0x67FA", 0x67FA,
             f"the ECU is in STATE {STATE_VALUE} -- where the governor substitution WOULD have "
             "ratcheted"),
            (BIT_R24_ABS, f"bit4 gp-0x{b['cell']:04X}", b["cell"],
             f"|{b['lane']} lane out| >= {THRESHOLD} (post +/-8192 clip), TWO-SIDED -- 0 readers"),
            (BIT_R24_SIGN, f"bit3 gp-0x{b['cell']:04X}", b["cell"],
             f"{b['lane']} lane out >= 0 -- THE SIGN. Read WITH bit4: side AND magnitude"))


RUNGS = rungs_for("v71a")        # the default bit MAP; main() re-resolves it from the CLI selector

CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit

# ⚠ V71's four rungs are INDEPENDENT: all 16 payloads are reachable and none is forbidden.
LEGAL = {BIT_LIVE | a | b | c | d
         for a in (0, BIT_MASK671D) for b in (0, BIT_STATE4)
         for c in (0, BIT_R24_ABS) for d in (0, BIT_R24_SIGN)}
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

# 🛑 ONE LINE, deliberately. The builder asserts this exact basename appears in this file; splitting
# it across a string concatenation makes the substring vanish and the check silently harder to pass.
RWD_NAME = "39990-TVA,A160-V71A-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V62sar-BOTHLANES-surfREVERTED-probe2-671d-67fa4-6adaABS128-sign-can330byte4-0x13000-0x100000.rwd"  # noqa: E501

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
}


def wire_byte4(v671d, v67fa, v6ada, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order."""
    r7 = 0x10                                       # movea 0x10,r0,r7
    if not ((v671d & 0xFF) < 1):                    # cmp 0x1,r6  ; blt +4
        r7 += 0x08
    if not ((v67fa & 0xFF) != STATE_VALUE):         # cmp 0x4,r6  ; bne +4
        r7 += 0x04
    x = (v6ada - 0x10000) if v6ada & 0x8000 else v6ada
    s = x >> 7                                      # ld.h ; sar 0x7   (Python >> floors == `sar`)
    if (s >= 1) or not (s >= -1):                   # cmp 0x1 ; bge SET ; cmp -0x1 ; bge SKIP ; SET
        r7 += 0x02
    if not (s < 0):                                 # cmp r0,r6 ; blt +4
        r7 += 0x01
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 16, f"{len(LEGAL)} legal payloads, expected all 16 (independent rungs)"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert BIT_LIVE | BIT_MASK671D | BIT_STATE4 | BIT_R24_ABS | BIT_R24_SIGN == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    # the wire model, against the bit map above
    assert wire_byte4(0, 0, 0) & PROBE_MASK == BIT_LIVE | BIT_R24_SIGN, \
        "an all-zero input is not `liveness + sign` (0 is >= 0, so bit3 fires)"
    assert wire_byte4(1, 0, 0) & BIT_MASK671D, "bit6 does not fire on gp-0x671d == 1"
    assert not wire_byte4(0, 0, 0) & BIT_MASK671D, "bit6 fires on gp-0x671d == 0"
    assert wire_byte4(0, STATE_VALUE, 0) & BIT_STATE4, f"bit5 does not fire on state {STATE_VALUE}"
    assert not wire_byte4(0, 10, 0) & BIT_STATE4, "bit5 fires on state 10 -- that is V70's rung"
    # ---- bit4, EXHAUSTIVELY over all 65,536 halfword patterns, including the one-count asymmetry --
    def _s16(r):
        return r - 0x10000 if r & 0x8000 else r
    for r in range(0x10000):
        x = _s16(r)
        assert bool(wire_byte4(0, 0, r) & BIT_R24_ABS) == (x >= THRESHOLD or x <= NEG_THRESHOLD), \
            f"bit4 is not `x >= {THRESHOLD} or x <= {NEG_THRESHOLD}` at x = {x}"
        assert bool(wire_byte4(0, 0, r) & BIT_R24_SIGN) == (x >= 0), f"bit3 is not `>= 0` at x = {x}"
    mismatch = {_s16(r) for r in range(0x10000)
                if bool(wire_byte4(0, 0, r) & BIT_R24_ABS) != (abs(_s16(r)) >= THRESHOLD)}
    assert mismatch == {-THRESHOLD}, \
        f"bit4 differs from |x| >= {THRESHOLD} at {sorted(mismatch)[:6]}, expected exactly " \
        f"{{{-THRESHOLD}}} -- `sar` floors and that is the ONLY value it can miss"
    assert wire_byte4(0, 0, 0xFF00) & BIT_R24_ABS, "bit4 does not fire at x = -256: NOT two-sided"
    assert not wire_byte4(0, 0, 0xFFFF) & BIT_R24_SIGN, "bit3 fires on -1: the sign test is unsigned"
    for status in range(8):
        assert wire_byte4(0xFF, STATE_VALUE, 0x7FFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
    # the three dispatcher masks, decoded back to state sets so a typo cannot survive review
    assert {s for s in range(16) if (1 << s) & MASK_DETECTOR} == {4, 5, 11}, "0x830 is not {4,5,11}"
    assert {s for s in range(16) if (1 << s) & MASK_AGGREGATOR} == {4, 5, 10, 11}, \
        "0xc30 is not {4,5,10,11}"
    assert {s for s in range(16) if (1 << s) & MASK_ARBITRATION} == {4, 5, 8, 11}, \
        "0x930 is not {4,5,8,11}"
    assert all((1 << STATE_VALUE) & m for m in (MASK_DETECTOR, MASK_AGGREGATOR, MASK_ARBITRATION)), \
        f"state {STATE_VALUE} must be in ALL THREE masks -- bit5 = 1 means the whole chain is running"
    assert len(CAVE_HEX_A) == len(CAVE_HEX_B) == 136, "a CAVE_HEX is not 68 bytes"
    ndiff = sum(1 for x, y in zip(CAVE_HEX_A, CAVE_HEX_B) if x != y)
    assert ndiff and bytes.fromhex(CAVE_HEX_A)[0x1A] == 0x26         and bytes.fromhex(CAVE_HEX_B)[0x1A] == 0x24,         "the two caves must differ at offset 0x1A ONLY: 0x26 (gp-0x6ada) vs 0x24 (gp-0x6adc)"
    assert sum(1 for x, y in zip(bytes.fromhex(CAVE_HEX_A), bytes.fromhex(CAVE_HEX_B)) if x != y) == 1,         "the two caves differ in more than the one mirror byte"
    for raw, mdisp in ((bytes.fromhex(CAVE_HEX_A), 0x6ADA), (bytes.fromhex(CAVE_HEX_B), 0x6ADC)):
        assert raw[0x18:0x1A] == bytes.fromhex("2437"), "the mirror load is not an `ld.h ...,r6`"
        assert raw[0x1A:0x1C] == ((0x10000 - mdisp) & 0xFFFF).to_bytes(2, "little"),             f"the mirror load does not carry -0x{mdisp:04x}"
    raw = bytes.fromhex(CAVE_HEX_A)
    assert CAVE_HEX_A.endswith("2436e8ea7f00") and CAVE_HEX_B.endswith("2436e8ea7f00"),         "a CAVE_HEX does not end in the displaced movea + jmp [lp]"
    # 🛑 Offsets are (address - 0xC4B34), DERIVED from the listing above, not guessed -- an off-by-4
    # checks the wrong halfword and the guard silently passes on a cave that WRITES.
    for off, hw1, disp, what in ((4, "a437", 0x671D, "ld.bu odd-disp"),
                                 (14, "8437", 0x67FA, "ld.bu even-disp"),
                                 ):
        assert raw[off:off + 2] == bytes.fromhex(hw1), \
            f"CAVE_HEX offset {off} is not a `{what} ...,r6` -- a 0x44../0x64.. hw1 would be a STORE"
        want = (0x10000 - disp) & 0xFFFF
        want = want if hw1 == "2437" else (want | 1)     # ld.bu/ld.hu carry hw2 = disp | 1
        assert raw[off + 2:off + 4] == want.to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x}"
    assert raw[28:30] == bytes.fromhex("a732"), "CAVE_HEX offset 28 is not `sar 0x7,r6` -- if it " \
        "reads a932 this is V71's FIRST CUT, whose rung read ZERO on two routes. Do not fly it."
    # 🛑 THE CONDITION NIBBLES, BY VALUE. bge = 0xE, be = 0x2, blt = 0x6, bne = 0xA.
    for off, want, what in ((10, "a605", "blt +4 (bit6)"), (20, "aa05", "bne +4 (bit5)"),
                            (32, "be05", "bge +6 (bit4 POSITIVE bound)"),
                            (36, "ae05", "bge +4 (bit4 NEGATIVE bound)"),
                            (30, "6132", "cmp 0x1,r6"), (34, "7f32", "cmp -0x1,r6"),
                            (40, "e031", "cmp r0,r6"), (42, "a605", "blt +4 (bit3 SIGN)")):
        assert raw[off:off + 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- a wrong nibble INVERTS the rung"
    assert raw[32:34] != bytes.fromhex("b205"), "bit4's positive bound is `be` (b205), not `bge`"
    assert raw[46:48] == bytes.fromhex("c33a"), "CAVE_HEX offset 46 is not `shl 0x3,r7`"


_self_check()


def identify(b4):
    """Which build produced this payload stream? Reported at its REAL strength, which is lower
    than V70's -- V71's rungs are independent, so no payload is forbidden."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    illegal = int(np.count_nonzero([(v & PROBE_MASK) not in LEGAL for v in b4]))
    print(f"  VOID (probe field == 0, the cave did not fire) : {void} / {len(b4)}")
    print(f"  ILLEGAL (bit7 clear)                           : {illegal} / {len(b4)}")
    if void or illegal:
        print("  🛑 HARD FAIL. A VOID or bit7-clear frame means the flashed image is not this build,")
        print("     or the cave did not run. Nothing below may be interpreted.")
        return False
    for name in STRUCTURALLY_DISJOINT:
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    n6 = int(np.count_nonzero((b4 & BIT_MASK671D) != 0))
    n4 = int(np.count_nonzero((b4 & BIT_R24_ABS) != 0))
    n3 = int(np.count_nonzero((b4 & BIT_R24_SIGN) != 0))
    print(f"  bit6 set (📋 pre-registered prediction: 0)     : {n6} / {len(b4)}")
    print(f"  bit4 set (|r24 lane| >= {THRESHOLD}, TWO-SIDED)     : {n4} / {len(b4)}")
    print(f"  bit3 set (r24 lane >= 0, the SIGN)             : {n3} / {len(b4)}")
    if n6:
        print("  ★★ bit6 IS SET. `gp-0x671d != 0` has never been observed non-zero in this kit")
        print("     (V64: 0; V67: 0/186,321 over two routes). If it holds here, the LERP arm never")
        print("     ran, V70's surface dose was MASKED, and V70's null is explained outright.")
    # ---- bit4 WITH bit3 clear is the payload class that settles the POLARITY leg ----------------
    if any((v & BIT_R24_ABS) and not (v & BIT_R24_SIGN) for v in vals):
        print("  ★★ bit4 = 1 with bit3 = 0 IS PRESENT ⇒ the lane reaches |x| >= 128 on the NEGATIVE")
        print("     side. A one-sided `>= +512` rung was structurally blind to exactly this, which")
        print("     is why V69's and V70's nulls could not be interpreted.")
        print("  ✅ EXCLUDED ABSOLUTELY: V70 -- its bit6 (`x >= +512`) implies its bit3 (`x >= 0`),")
        print("     so V70 can NEVER emit a bit6=1/bit3=0 payload; V71's bit4 sits one bit lower and")
        print("     is two-sided, so this payload is V71-shaped, not V70-shaped.")
    # 🛑 NO STRONGER IDENTIFICATION IS AVAILABLE AND NONE IS CLAIMED. V71's four rungs are
    # independent, so all 16 payloads are reachable and no payload is forbidden. In particular the
    # "a fast-toggling bit3 means V70" falsifier that V71's FIRST CUT carried is RETIRED and MUST NOT
    # be reintroduced: on this cut bit3 IS a sign bit, exactly like V70's, so that test would now
    # return a confidently WRONG answer.
    print("  ⚠ NOT excluded by the value set: V55, V57, V58, V64 and V70 -- probes with INDEPENDENT")
    print("     bits, whose reachable space is all 16 payloads. The .rwd FILENAME is the pre-drive")
    for k, v in BUILDS.items():
        print(f"     {k.upper()}: {v['rwd']}")
    return True


def main(paths, build):
    global RUNGS
    RUNGS = rungs_for(build)
    info = BUILDS[build]
    print(__doc__)
    print("=" * 102)
    print(f"BUILD SELECTED: {build.upper()}   bit4/bit3 watch gp-0x{info['cell']:04X} = "
          f"{info['lane']}'s post-clip mirror")
    print(f"  dose: {info['dose']}")
    print(f"  rwd : {info['rwd']}")
    print("  🛑 CONFIRM THAT FILENAME IS WHAT FLEW. V71A and V71B differ in ONE cave byte and are")
    print("     NOT separable from the wire; every number below is read through the selected map.")
    d = collect(paths)
    b4, t = d["b4"], d["t"]
    if len(b4) == 0:
        print("🛑 no 0x14A frames on src 1 -- nothing to decode.")
        return 1
    fs = (len(t) - 1) / (t[-1] - t[0])
    print("=" * 102)
    print(f"FRAMES {len(b4)}   span {t[-1] - t[0]:.1f} s   mean rate {fs:.3f} Hz")
    # 🛑 use the MEAN rate + an index lattice, never 1/median(dt): frames are timestamped per log
    # packet, so on some routes 12% of dt exceed 15 ms and p10 is exactly 0.
    print("IDENTIFICATION -- from the PROBE first, then the filename")
    if not identify(b4):
        return 1

    tq, rate = d["tq"], d["rate"]
    v = d.get("v", np.full(len(b4), np.nan))
    lat = np.asarray(d.get("lat", np.zeros(len(b4), bool)), bool)
    sus = np.abs(sustained(tq, fs))
    ratchet_cell = lat & (v <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)

    m6 = (b4 & BIT_MASK671D) != 0
    m5 = (b4 & BIT_STATE4) != 0
    m4 = (b4 & BIT_R24_ABS) != 0
    m3 = (b4 & BIT_R24_SIGN) != 0

    cells = (
        ("WHOLE ROUTE", np.ones(len(b4), bool)),
        ("engaged", lat),
        ("engaged + creep", lat & (v <= CREEP_MAX_MS)),
        ("engaged + creep + hands-off  ⇐ THE RATCHET'S OWN CELL", ratchet_cell),
        ("manual (disengaged)", ~lat),
    )

    print("\n" + "=" * 102)
    print("PER-BIT DUTY AND TOGGLE RATE")
    for bit, name, _disp, what in RUNGS:
        mask = (b4 & bit) != 0
        print(f"\n  {name}   {what}")
        print(f"    {'cell':<52s} {'secs':>7s} {'duty':>8s} {'tog/s':>8s} {'pkHz':>7s} {'prom':>7s}")
        for label, sel in cells:
            n = int(np.count_nonzero(sel))
            if n < 64:
                print(f"    {label:<52s} {n / fs:7.1f}    (too few frames)")
                continue
            duty = float(np.count_nonzero(mask[sel])) / n
            rr = runs_of(sel)
            tog = sum(sum(transitions(mask[a:b])) for a, b in rr) / (n / fs)
            pk, prom = (float("nan"), float("nan"))
            if rr:
                a, b = max(rr, key=lambda ab: ab[1] - ab[0])
                pk, prom = ratchet_line(mask[a:b], fs)
            print(f"    {label:<52s} {n / fs:7.1f} {duty:8.4f} {tog:8.2f} {pk:7.2f} {prom:7.2f}")

    # =================================================================================================
    print("\n" + "=" * 102)
    print("★★ READOUT 1 -- WHICH GAIN ARM WAS IN FORCE?  Read bit6 FIRST -- it is the only rung left")
    print("   on the priority chain, and it OUTRANKS everything. The `lp` arm is structurally dead on")
    print("   V71 (gate 0x3AA96 = 0xC5 ⇒ gp-0x683c, ZERO writers image-wide). The third arm's rung")
    print("   (`gp-0x671a >= 5`) was CUT to pay for the two-sided bit4; V67 measured it at 0.000%")
    print("   over 186,321 frames on two routes, so `bit6 == 0` is taken to mean the LERP arm ran.")
    eps = episodes_of(lat)
    print(f"\n   engaged episodes >= {MIN_SAMPLES} samples: {len(eps)}   "
          f"total {sum(b - a for a, b in eps) / fs:.1f} s")
    ones = np.ones(len(b4), float)
    for label, mask in (("bit6  gp-0x671d != 0  -> arm 1024", m6),
                        (f"bit4  |gp-0x6ada| >= {THRESHOLD}  TWO-SIDED", m4),
                        ("bit3  gp-0x6ada >= 0   (the SIGN)", m3),
                        ("bit4 AND bit3 clear -> lane NEGATIVE and large", m4 & ~m3)):
        pt, (lo, hi) = episode_ratio(eps, mask.astype(float), ones)
        print(f"   {label:<46s} engaged duty {pt:.5f}  [{lo:.5f}, {hi:.5f}]")
    lerp = ~m6
    n4_on_lerp = int(np.count_nonzero(m4 & lerp & lat))
    n_lerp = int(np.count_nonzero(lerp & lat))
    print(f"\n   bit4 set WHILE bit6 is clear (the LERP arm), engaged: {n4_on_lerp} / {n_lerp}")
    if n_lerp and n4_on_lerp == 0:
        print("   🛑🛑 THE LANE IS NOT REACHING +/-128 AT ALL, AND POLARITY CANNOT EXPLAIN IT.")
        print("        This rung is TWO-SIDED and needs only 5-32 counts of |dtorque| on every branch")
        print("        of the priority chain, against a repo-recorded max of 839 and V69's own flight")
        print("        max of 633.9. A null here refutes BOTH remaining explanations for the")
        print("        V69/V70 zeros that were arm-selection or polarity. What is left is the dtorque")
        print("        RECONSTRUCTION itself, or gp-0x6ada's writer @0x3AD5A not being reached.")
        print("        Probe THOSE next -- do not spend another build on the arms.")
    elif n4_on_lerp:
        print("   ✅ THE POSITIVE CONTROL FIRES. The lane is live, the dose is being delivered, and")
        print("      the V69/V70 zeros were a THRESHOLD/POLARITY artefact of the one-sided rung, not")
        print("      a statement about the control path. Read bit3 alongside it for the side.")
    n_neg = int(np.count_nonzero(m4 & ~m3 & lat))
    if n_neg:
        print(f"   ★ {n_neg} engaged frames have bit4 = 1 with bit3 = 0 ⇒ the lane goes LARGE and")
        print("     NEGATIVE. A one-sided `>= +512` rung was blind to every one of them.")

    # =================================================================================================
    print("\n" + "=" * 102)
    print("★★ READOUT 2 -- HOW OFTEN WOULD THE STATE-4 RATCHET HAVE FIRED?")
    print("   V71 DISABLES the substitution (0x454FE bne->br), so bit5 is the counterfactual: every")
    print("   frame with bit5 = 1 is a frame on which stock/V53-V70 firmware forbade the command")
    print("   MAGNITUDE from rising, cumulatively and self-sustainingly.")
    print("   🛑 gp-0x67fa == 4 is NOT the bus STEER_STATUS. Do not cross-read them.")
    for label, sel in cells:
        n = int(np.count_nonzero(sel))
        if n < 64:
            continue
        duty = float(np.count_nonzero(m5[sel])) / n
        print(f"   {label:<52s} duty {duty:.5f}   ({np.count_nonzero(m5[sel])} / {n} frames)")
    if not np.count_nonzero(m5):
        print("   ⚠ bit5 reads 0 everywhere. That is INFORMATIVE, not a null: it means state 4 was")
        print("     never entered on this route, so the ratchet fix could not have acted here and")
        print("     any change in feel must come from EDIT 2 (the sar) instead. Re-fly the route")
        print("     that produced the recorded ratchet episodes before concluding anything.")

    print("\n" + "=" * 102)
    print("PAYLOAD HISTOGRAM (as transmitted, status bits included)")
    for val, n in Counter(int(x) for x in b4).most_common():
        flag = "" if val in ON_WIRE or (val & PROBE_MASK) in LEGAL else "   🛑 NOT A LEGAL V71 PAYLOAD"
        bits = " ".join(nm.split()[0] for bit, nm, _d, _w in RUNGS if val & bit)
        print(f"   0x{val:02X}  {n:8d}  {n / len(b4):7.4f}   {bits or '(bare liveness)'}{flag}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sel = [a[2:].lower() for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 1 or len(sel) != 1 or sel[0] not in BUILDS:
        print(__doc__)
        raise SystemExit(
            "usage: probe/decode_v71_probe.py --v71a|--v71b|--v71c <rlog-or-route-dir> [...]\n"
            "🛑 The build MUST be named. NONE of the three siblings is separable from the CAN\n"
            "   payload: V71A and V71C carry a BYTE-IDENTICAL cave (both watch gp-0x6ada / r24),\n"
            "   and V71B differs by ONE cave byte (gp-0x6adc / r26) that never reaches the wire.\n"
            "   This decoder refuses to guess. Read the build off the .rwd filename that was\n"
            "   flashed — it is the ONLY pre-drive discriminator.")
    raise SystemExit(main(args, sel[0]))
