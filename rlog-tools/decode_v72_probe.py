#!/usr/bin/env python3
"""decode_v72_probe.py -- read V72's probe: `a`, the base damper, and the rate index.

WHAT V72 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
  LEVER A  both rate lanes dosed across the **WHOLE rate axis** at the 0 and 10 km/h records, through
           the UNGATED speed-shaped surfaces: gain_B mode-10 rec0/rec1 Y[0..3] -> **5244** (r24) and
           gain_A rec0/rec1 Y[0..3] -> **512** (r26). Those are V67/V68's own arm values, and a FLAT
           record is exactly what a scalar arm delivers -- so at 0 and 10 km/h V72's multiplier
           equals **V67/V68's ENGAGED multiplier at every rate index**. The 50/100 km/h records are
           BYTE-STOCK, so highway is EXACTLY 1.000000x by record-selection geometry. That removes
           V67/V68's only failure without touching what worked.
  LEVER B  the base-assist damper opened at creep -- FactorC `0xD27C6/C8` -> 430 and `0xD27DA/DC` ->
           431, FactorE `0xD2802/04/06` and `0xD2816/18/1A` -> 927. Stock has NO base-assist damping
           anywhere below 35 km/h (FactorC's LERP clamps to Y[0] = 0 and the five factors multiply in
           Q10), which is the whole region where the ratchet and both grinds live. Delivered
           authority at creep is **389 counts**, monotone, and below the 512 ceiling floor.
  LEVER C  `0xC63A0` 1024 -> 2048, the weight on `gp-0x6bd0` into FUN_00038148. ONE reader
           image-wide (`0x381AC`), so no monitor can be checking it.
  CARRIED  `0x454FE` = 0xB5. 🛑 **CARRIED, CURRENTLY INERT, UNTESTED -- not a fix and NOT falsified.**
           V71's bit5 measured `gp-0x67fa == 4` at 0/123,277 (route 54) and 8/92,826 (route 58), all
           eight an 80 ms burst **in park** ⇒ state 4 never occurred while driving ⇒ V42's
           substitution never ran ⇒ the V71B/V71C "no change" is a **null by construction.**
           **Do not score the 7.79 Hz ratchet against it.**
🛑 V72 IS UNGATED (`0x3AA96` = 0xC5, the dead cell), so the rate-lane dose applies in MANUAL steering
below ~30 km/h too. V67/V68's version was engaged-only. **And grind #2 follows the GATE, not the
driver's hands** (V62/V65 ungated: 0.0444/s engaged vs 0.0430/s manual; V71C gated: engaged only)
⇒ **if V72 produces grind #2 it will produce it in the manual arm as well.** Score manual separately.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
-----------------------------------------
    bit7 = 1                     LIVENESS. field == 0 ⇒ the cave did not fire ⇒ the frame is VOID.
    bit6 = gp-0x69a4 >= 512      ★★★★ `a`, **THE UNMEASURED WEIGHT.** r26 = ((a * dtorque) >> 10) *
                                 gain_A >> 10, so `a` sets r26's magnitude RELATIVE to r24. It has
                                 NEVER been measured on this car, it makes every "r24 vs r26" number
                                 in this kit conditional, and it has blocked that attribution for
                                 about ten builds. Producer: a live 10-segment LERP at 0x355C6 in
                                 FUN_000352b4. 512 = 0.5 and 1024 = 1.0 in the Q10 reading of `a`.
                                 📋 NO PRIOR -- these two rungs ARE the measurement.
    bit5 = gp-0x69a4 >= 1024     ★★★ the second thermometer step. ★★ **`bit5 => bit6` is a MONOTONE
                                 INVARIANT**, structurally guaranteed by the emitted code (both come
                                 from ONE `sar 0x9`), so only **12 of the 16** payloads are legal.
                                 A frame with bit5 SET and bit6 CLEAR proves the artefact is NOT V72.
    bit4 = |gp-0x6bd0| >= 64     **IS LEVER B IN FORCE?** The damping lane's own output, post-clamp.
                                 On every build in this kit it is a HARD STRUCTURAL ZERO at creep, so
                                 a non-zero reading below 35 km/h is the FIRST direct proof the base
                                 damper is alive at creep on any build here. **TWO-SIDED**: the
                                 damper is velocity-OPPOSING (`0x3469e`: if gp-0x6abe > 0, negate) so
                                 it alternates sign every half cycle. V71 proved this idiom works --
                                 4,478 engaged frames, engaged-vs-manual 416x [172, 1748],
                                 p = 0/20,000 -- and r24's excursions measured 0.5013 positive, all
                                 but perfectly symmetric, so a one-sided rung would halve the count
                                 for nothing.
                                 ★ IT CARRIES ITS OWN POSITIVE CONTROL: above 35 km/h stock ALREADY
                                 produces non-zero damping, so the rung must fire at speed even if
                                 Lever B did nothing. A rung silent at highway is broken, not null.
    bit3 = gp-0x6ac0 >= 512   📋 **PRE-REGISTERED at 2.750% engaged duty** (9,497 / 345,396 frames),
                                 and it must fire frame-for-frame with bus `|rate_c| >= 108.7 deg/s`
                                 (512 counts / 4.7121 counts-per-deg-s). A POSITIVE CONTROL: the rate
                                 axis is settled three independent ways (the CAN divisibility/
                                 quantile test, the regression on differentiated angle, and
                                 disassembly of both packers -- `0x14A` packs `(-gp-0x6a56)>>3`,
                                 `0x18F` packs it unshifted), so a miss indicts the cave, not the
                                 scale. 🛑 **512 clears the hard floor of 400**: at 250 the retired
                                 8x-smaller scale starts firing (0.058%) and the rung stops
                                 discriminating between the two candidate scales.

★★ HOW FIVE RUNGS FIT IN 68 BYTES, and the ONE architectural fact it rests on
------------------------------------------------------------------------------
🛑 **V850 shift instructions SET THE Z FLAG, and a following Bcond reads it with no `cmp`.**
[EVIDENCE, Ghidra-disassembled at 0x318DA, and Honda does it three times in a row:]
    0x318D6 andi 0x200,r14,r8 · 0x318DA sar 0x9,r8 · 0x318DC bne 0x319CA   (again at 0x318E2/0x318EA)
Both `a` and the rate index are loaded `ld.hu` (zero-extended ⇒ non-negative), so `s = v sar 9`
satisfies `s != 0 <=> v >= 512` and bit6/bit3 each drop a `cmp`, saving 2 bytes apiece.
⚠ **Flag liveness across each `sar`->`be` pair is therefore load-bearing.** The builder asserts the
adjacency by position in the emitted listing AND again in a re-disassembly of the BUILT bytes; this
file re-checks it from CAVE_HEX. Anything inserted between them would make the branch read the
PREVIOUS comparison's flags -- a plausible-looking wrong answer.

⚠ bit4's EXACT TEST, because it is ONE COUNT asymmetric and that must not be glossed:

        bit4  =  (gp-0x6bd0 >= +64)  OR  (gp-0x6bd0 <= -65)

`sar` FLOORS, so `x sar 6 == -1` spans x in [-64,-1] and no single shifted compare can split
x = -64 from x = -63. The negative arm therefore trips at -65. That is |x| >= 64 for every value
EXCEPT x == -64 exactly. Proven exhaustively over all 65,536 halfword patterns in `_self_check()`.

🛑🛑 THE ONE-BIT TRAP IS LIVE ON bit4, IN ITS WORST FORM IN THIS KIT'S HISTORY.
`ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT -- and the firmware's own
`st.h r6,-0x6bd0[gp]` @`0x34730` is **`64373094`** against our **`24373094`**: the SAME register and
the SAME displacement halfword. Unlike V70's and V71's zero-reader mirrors, **`gp-0x6bd0` has FIVE
real readers including the 1 kHz aggregator**, so a slipped bit would not corrupt a cell nobody
reads -- it would WRITE a live lane. If you ever see hw1 `0x64..` at cave offset 20 where `0x24..`
is written below, the cave WRITES. **Do not flash it.**

CAVE DISCIPLINE -- 68 of the 68 proven bytes, ZERO spare. The extent must NOT be grown to fit more:
caves are this kit's only bricking class (V24, V27 and V48B all bricked the ECU).
⚠ The role table at 0xC4124 is asserted unchanged by the builder ([0,0,5,0,5,5,0,0,0,5,0]); a slot
carrying role 6 or 7 makes gp-0x67ac live and the aggregator drops r24, r26 AND the damping lane --
which would make every lever on this build vacuous at once.

Usage:  python decode_v72_probe.py <rlog-or-route-dir> [...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> out.txt` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
# ⚠ The NUMERIC MACHINERY is shared on purpose -- collect/sustained/runs_of are instrument code, not
# semantics, and two copies would drift. The 128-sample floor and the episode bootstrap were FIXED
# on 2026-08-04; do not re-derive them here and do not regress them.
from decode_v67_gate import collect, runs_of, sustained                     # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES                                  # noqa: E402
from decode_v70_probe import episode_ratio, episodes_of                     # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v72_tva.assert_decoder_matches() FAILS THE BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "203e1000e4375d96a932a205483a6232a605443a24373094a6326132be057f32ae05423ae4374195a932a205413ac33a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e1000  movea 0x10,r0,r7      bit7 LIVENESS, in PRE-SHIFT weights
#   0xC4B38  e4375d96  ld.hu -0x69a4[gp],r6  `a` -- BYTE-IDENTICAL to the aggregator's own read
#                                            @0x3AB3A. UNSIGNED (ld.hu), so `sar` == `shr` below.
#   0xC4B3C  a932      sar   0x9,r6          units of 512.  🛑 SETS Z
#   0xC4B3E  a205      be    +4              reads the sar's OWN Z flag -- no `cmp`
#   0xC4B40  483a      add   0x8,r7          bit6 = gp-0x69a4 >= 512
#   0xC4B42  6232      cmp   0x2,r6
#   0xC4B44  a605      blt   +4
#   0xC4B46  443a      add   0x4,r7          bit5 = gp-0x69a4 >= 1024   ★ bit5 => bit6
#   0xC4B48  24373094  ld.h  -0x6bd0[gp],r6  🛑 op 0x39. The st.h twin @0x34730 is 64373094.
#   0xC4B4C  a632      sar   0x6,r6          ARITHMETIC -- units of 64, sign preserved
#   0xC4B4E  6132      cmp   0x1,r6          the POSITIVE bound
#   0xC4B50  be05      bge   +6              s >=  1 => x >= +64            -> SET
#   0xC4B52  7f32      cmp   -0x1,r6         the NEGATIVE bound (imm5 is SIGNED; -1 encodes 0x1F)
#   0xC4B54  ae05      bge   +4              s >= -1 => |x| is small        -> SKIP
#   0xC4B56  423a      add   0x2,r7          bit4 = |gp-0x6bd0| >= 64, TWO-SIDED (fallthrough)
#   0xC4B58  e4374195  ld.hu -0x6ac0[gp],r6  |motor rate|, UNSIGNED (4 byte-identical real instances)
#   0xC4B5C  a932      sar   0x9,r6          🛑 SETS Z
#   0xC4B5E  a205      be    +4
#   0xC4B60  413a      add   0x1,r7          bit3 = gp-0x6ac0 >= 512
#   0xC4B62  c33a      shl   0x3,r7          the 5-bit field -> bits 7:3. V31P FLASHED this 4x;
#                                            Honda's own idiom @0x4FB82 (shl 0x3,r7 / andi 0xf8).
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]  THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6   the displaced hook instruction
#   0xC4B76  7f00      jmp   [lp]            -> 0x55C12
# 🛑🛑 THE CONDITION-NIBBLE TWINS. `be +4` = **a205**, `bge +4` = **ae05**, `blt +4` = **a605** and
# `bne +4` = **aa05** -- ONE NIBBLE apart, and the wrong one INVERTS a rung silently. If you are
# hand-decoding, check the LOW nibble of the first byte: 0x2 = be, 0xE = bge, 0x6 = blt, 0xA = bne.
# Every one is pinned BY VALUE against a real instruction in the builder and again below.

BIT_LIVE = 0x80
BIT_A512 = 0x40               # bit6  gp-0x69a4 >= 512    ★★★★ `a`, THE UNMEASURED WEIGHT
BIT_A1024 = 0x20              # bit5  gp-0x69a4 >= 1024   ★ bit5 => bit6, MONOTONE
BIT_DAMPABS = 0x10            # bit4  |gp-0x6bd0| >= 64, TWO-SIDED -- IS LEVER B IN FORCE?
BIT_RATE512 = 0x08            # bit3  gp-0x6ac0 >= 512    📋 PRE-REGISTERED
PROBE_MASK = 0xF8

A_THRESHOLD = 512             # bit6: ld.hu -> sar 0x9 -> be   (branches on the sar's own Z flag)
A2_THRESHOLD = 1024           # bit5: cmp 0x2 -> blt
D_THRESHOLD = 64              # bit4: ld.h  -> sar 0x6 -> cmp 0x1 / cmp -0x1
D_NEG_THRESHOLD = -65         # ⚠ `sar` FLOORS, so the NEGATIVE arm trips at -65, not -64.
R_THRESHOLD = 512             # bit3: ld.hu -> sar 0x9 -> be

A_DISP, DAMP_DISP, RATE_DISP = 0x69A4, 0x6BD0, 0x6AC0
RATE_SCALE_CTS_PER_DEGS = 4.7121          # the settled column-rate scale, three independent ways
RATE_DEGS = R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS         # 108.66 deg/s
PREREG_BIT3_DUTY = 2.750                  # 📋 percent engaged, 9,497 / 345,396 frames
RATE_HARD_FLOOR = 400                     # below this the retired 8x-smaller scale starts firing

FACTORC_ONSET_KMH = 35.0      # below this, STOCK base-assist damping is a HARD ZERO
CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit

# 🛑 ONE LINE, deliberately. build_v72_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V72-A-WHOLEAXIS-r24_5244-r26_512-V67CREEP-hwy1x-B-FactorCE-430_927-C-63A0x2-454FE-probe-a512-a1024-damp-rate512-0x13000-0x100000.rwd"  # noqa: E501

# ★ bit5 => bit6 is STRUCTURAL, so 4 of the 16 payloads are FORBIDDEN.
LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_A512, BIT_A512 | BIT_A1024)
         for b in (0, BIT_DAMPABS) for c in (0, BIT_RATE512)}
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
}

# The cave's REAL instruction boundaries, as (offset, length). Every byte-level check below is made
# on these rather than on "every even offset" -- a displacement halfword decoded as an opcode is how
# a store gets invented or missed.
BOUNDARIES = ((0, 4), (4, 4), (8, 2), (10, 2), (12, 2), (14, 2), (16, 2), (18, 2),      # seed+6+5
              (20, 4), (24, 2), (26, 2), (28, 2), (30, 2), (32, 2), (34, 2),            # bit4
              (36, 4), (40, 2), (42, 2), (44, 2),                                       # bit3
              (46, 2), (48, 4), (52, 4), (56, 2), (58, 4), (62, 4), (66, 2))            # shl + tail


def _s16(raw):
    return raw - 0x10000 if raw & 0x8000 else raw


def wire_byte4(v69a4, v6bd0, v6ac0, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order."""
    r7 = 0x10                                       # movea 0x10,r0,r7
    s = (v69a4 & 0xFFFF) >> 9                       # ld.hu ; sar 0x9   (SETS Z)
    if s != 0:                                      # be +4  <- reads the sar's own Z flag
        r7 += 0x08
    if not (s < 2):                                 # cmp 0x2,r6 ; blt +4
        r7 += 0x04
    d = _s16(v6bd0 & 0xFFFF) >> 6                   # ld.h ; sar 0x6  (Python >> floors == `sar`)
    if (d >= 1) or not (d >= -1):                   # cmp 0x1 ; bge SET ; cmp -0x1 ; bge SKIP ; SET
        r7 += 0x02
    q = (v6ac0 & 0xFFFF) >> 9                       # ld.hu ; sar 0x9  (SETS Z)
    if q != 0:                                      # be +4
        r7 += 0x01
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 12, f"{len(LEGAL)} legal payloads, expected 12 (bit5 => bit6 forbids 4)"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert not any((b & BIT_A1024) and not (b & BIT_A512) for b in LEGAL), \
        "a legal payload has bit5 set with bit6 clear -- the monotone invariant must forbid it"
    assert BIT_LIVE | BIT_A512 | BIT_A1024 | BIT_DAMPABS | BIT_RATE512 == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    # ---- bit6 and bit5, EXHAUSTIVELY, plus the monotone invariant --------------------------------
    for raw in range(0x10000):
        b = wire_byte4(raw, 0, 0)
        assert bool(b & BIT_A512) == (raw >= A_THRESHOLD), \
            f"bit6 is not `gp-0x69a4 >= {A_THRESHOLD}` at {raw}"
        assert bool(b & BIT_A1024) == (raw >= A2_THRESHOLD), \
            f"bit5 is not `gp-0x69a4 >= {A2_THRESHOLD}` at {raw}"
        assert not (b & BIT_A1024) or (b & BIT_A512), f"bit5 => bit6 is violated at {raw}"
    # ---- bit4, EXHAUSTIVELY, including the one-count asymmetry -----------------------------------
    for raw in range(0x10000):
        x = _s16(raw)
        assert bool(wire_byte4(0, raw, 0) & BIT_DAMPABS) == \
            (x >= D_THRESHOLD or x <= D_NEG_THRESHOLD), \
            f"bit4 is not `x >= {D_THRESHOLD} or x <= {D_NEG_THRESHOLD}` at x = {x}"
    mismatch = {_s16(r) for r in range(0x10000)
                if bool(wire_byte4(0, r, 0) & BIT_DAMPABS) != (abs(_s16(r)) >= D_THRESHOLD)}
    assert mismatch == {-D_THRESHOLD}, \
        f"bit4 differs from |x| >= {D_THRESHOLD} at {sorted(mismatch)[:6]}, expected exactly " \
        f"{{{-D_THRESHOLD}}} -- `sar` floors and that is the ONLY value it can miss"
    assert wire_byte4(0, 0xFF00, 0) & BIT_DAMPABS, "bit4 does not fire at x = -256: NOT two-sided"
    # ---- bit3, EXHAUSTIVELY ----------------------------------------------------------------------
    for raw in range(0x10000):
        assert bool(wire_byte4(0, 0, raw) & BIT_RATE512) == (raw >= R_THRESHOLD), \
            f"bit3 is not `gp-0x6ac0 >= {R_THRESHOLD}` at {raw}"
    assert R_THRESHOLD >= RATE_HARD_FLOOR, \
        f"bit3's threshold is below the {RATE_HARD_FLOOR} HARD FLOOR -- the rung would stop " \
        "discriminating between the settled and the retired axis scale"
    assert abs(RATE_DEGS - 108.7) < 0.1, "512 counts is not the pre-registered 108.7 deg/s"
    for status in range(8):
        assert wire_byte4(0xFFFF, 0x7FFF, 0xFFFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
        assert wire_byte4(0, 0, 0, status) == 0x80 | status, "an all-zero input is not bare liveness"
    # ---- the cave hex, field by field ------------------------------------------------------------
    raw = bytes.fromhex(CAVE_HEX)
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, not the proven 68"
    assert CAVE_HEX.endswith("2436e8ea7f00"), \
        "CAVE_HEX does not end in the displaced movea + jmp [lp]"
    assert sum(n for _o, n in BOUNDARIES) == 68, "the boundary table does not tile the cave"
    for prev, nxt in zip(BOUNDARIES, BOUNDARIES[1:]):
        assert prev[0] + prev[1] == nxt[0], f"the boundary table is not contiguous at {prev}"
    assert raw[0:4] == bytes.fromhex("203e1000"), "offset 0 is not `movea 0x10,r0,r7`"
    # 🛑 Offsets are (address - 0xC4B34), DERIVED from the listing above, not guessed -- an off-by-4
    # checks the wrong halfword and the guard silently passes on a cave that WRITES.
    for off, hw1, disp, kind, what in ((4, "e437", A_DISP, "odd", "ld.hu `a`"),
                                       (20, "2437", DAMP_DISP, "even", "ld.h damper"),
                                       (36, "e437", RATE_DISP, "odd", "ld.hu rate")):
        assert raw[off:off + 2] == bytes.fromhex(hw1), \
            f"CAVE_HEX offset {off} is not a `{what} ...,r6` -- a 0x44../0x64.. hw1 would be a STORE"
        want = (0x10000 - disp) & 0xFFFF
        want = (want & 0xFFFE) | 1 if kind == "odd" else (want & 0xFFFE)
        assert raw[off + 2:off + 4] == want.to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x}"
    # 🛑🛑 THE ld.h / st.h ONE-BIT TRAP, checked against the REAL st.h twin's bytes. Assemble the
    # HALFWORD first -- picking the opcode field out of individual bytes by hand is the exact
    # "build upward from raw bytes" mistake this kit keeps paying for.
    assert raw[20:24] == bytes.fromhex("24373094"), "the damper load is not `ld.h -0x6bd0[gp],r6`"
    assert raw[20:24] != bytes.fromhex("64373094"), \
        "the damper load IS the real `st.h r6,-0x6bd0[gp]` @0x34730 -- the cave would WRITE a lane " \
        "with FIVE readers, one of them the 1 kHz aggregator. DO NOT FLASH."
    _hw1 = int.from_bytes(raw[20:22], "little")
    assert (_hw1 >> 5) & 0x3F == 0x39, \
        f"the damper load's opcode field is 0x{(_hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h); " \
        "0x3B is st.h"
    assert (_hw1 >> 11) == 6 and (_hw1 & 0x1F) == 4, "the damper load is not `... [gp],r6`"
    for off, want, what in ((8, "a932", "sar 0x9,r6  (bit6/bit5, SETS Z)"),
                            (10, "a205", "be +4       (bit6, reads the sar's Z)"),
                            (12, "483a", "add 0x8,r7  (bit6 setter)"),
                            (14, "6232", "cmp 0x2,r6  (bit5)"),
                            (16, "a605", "blt +4      (bit5)"),
                            (18, "443a", "add 0x4,r7  (bit5 setter)"),
                            (24, "a632", "sar 0x6,r6  (bit4)"),
                            (26, "6132", "cmp 0x1,r6  (bit4 POSITIVE bound)"),
                            (28, "be05", "bge +6      (bit4 POSITIVE bound)"),
                            (30, "7f32", "cmp -0x1,r6 (bit4 NEGATIVE bound)"),
                            (32, "ae05", "bge +4      (bit4 NEGATIVE bound)"),
                            (34, "423a", "add 0x2,r7  (bit4 setter)"),
                            (40, "a932", "sar 0x9,r6  (bit3, SETS Z)"),
                            (42, "a205", "be +4       (bit3)"),
                            (44, "413a", "add 0x1,r7  (bit3 setter)"),
                            (46, "c33a", "shl 0x3,r7")):
        assert raw[off:off + 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- a wrong nibble INVERTS the rung"
    assert raw[28:30] != bytes.fromhex("b205"), "bit4's positive bound is `be` (b205), not `bge`"
    # 🛑 FLAG LIVENESS: each `sar 0x9` must be IMMEDIATELY followed by its `be`, or the branch reads
    # the PREVIOUS comparison's flags. Re-derived from CAVE_HEX, not inherited from the builder.
    for sar_off in (8, 40):
        assert raw[sar_off:sar_off + 2] == bytes.fromhex("a932"), f"offset {sar_off} is not a sar"
        assert raw[sar_off + 2:sar_off + 4] == bytes.fromhex("a205"), \
            f"the `sar` at offset {sar_off} is not immediately followed by its `be` -- the branch " \
            "would read STALE flags and the rung would be meaningless"
    # 🛑 EXACTLY ONE STORE, on the REAL instruction boundaries.
    stores = [o for o, n in BOUNDARIES
              if n >= 4 and ((int.from_bytes(raw[o:o + 2], "little") >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert stores == [58], f"the cave's store set is {stores}, expected exactly [58]"
    assert raw[58:62] == bytes.fromhex("4437ecea"), \
        "offset 58 is not `st.b r6,-0x1514[gp]` -- the sole store moved"


_self_check()

RUNGS = ((BIT_A512, f"bit6 gp-0x{A_DISP:04X}", A_DISP,
          f"`a` >= {A_THRESHOLD} (0.5 in Q10) -- r26's own weight, NEVER measured before V72"),
         (BIT_A1024, f"bit5 gp-0x{A_DISP:04X}", A_DISP,
          f"`a` >= {A2_THRESHOLD} (1.0 in Q10) -- the second thermometer step"),
         (BIT_DAMPABS, f"bit4 gp-0x{DAMP_DISP:04X}", DAMP_DISP,
          f"|base-assist damper| >= {D_THRESHOLD}, TWO-SIDED -- IS LEVER B IN FORCE?"),
         (BIT_RATE512, f"bit3 gp-0x{RATE_DISP:04X}", RATE_DISP,
          f"|motor rate| >= {R_THRESHOLD} counts = {RATE_DEGS:.1f} deg/s -- 📋 PRE-REGISTERED"))


def identify(b4):
    """Which build produced this payload stream? Reported at its REAL strength, not more."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    illegal = int(np.count_nonzero([(v & PROBE_MASK) not in LEGAL for v in b4]))
    inv = int(np.count_nonzero(((b4 & BIT_A1024) != 0) & ((b4 & BIT_A512) == 0)))
    print(f"  VOID (probe field == 0, the cave did not fire)   : {void} / {len(b4)}")
    print(f"  ILLEGAL (bit7 clear, or bit5 set with bit6 clear): {illegal} / {len(b4)}")
    print(f"  bit5 => bit6 VIOLATIONS (🛑 must be 0)            : {inv} / {len(b4)}")
    if void or illegal:
        print("  🛑 HARD FAIL. A VOID frame means the cave did not run; a bit5-with-clear-bit6 frame")
        print("     means the flashed image is NOT V72 -- both `a` rungs derive from ONE `sar 0x9`,")
        print("     so the implication is structural. Nothing below may be interpreted. Check the")
        print(f"     .rwd filename against:\n       {RWD_NAME}")
        return False
    for name in STRUCTURALLY_DISJOINT:
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    print("  ✅ the bit5 => bit6 MONOTONE INVARIANT holds in every frame -- consistent with V72.")
    print("     ⚠ ONE-WAY: a violation falsifies V72, but holding does not PROVE it. The .rwd")
    print("     FILENAME remains the pre-drive discriminator.")
    for bit, name, _cell, what in RUNGS:
        n = int(np.count_nonzero((b4 & bit) != 0))
        print(f"  {name} set: {n:7d} / {len(b4)}  ({100.0 * n / max(len(b4), 1):6.3f}%)   {what}")
    return True


def report_a(b4, engaged):
    """★★★★ `a` -- the quantity that makes every r24-vs-r26 number in this kit conditional."""
    print("\n  ★★★★ bit6 + bit5 -- `a` = gp-0x69a4, THE UNMEASURED WEIGHT (a 2-step thermometer)")
    for bit, label in ((BIT_A512, "bit6 `a` >= 512  (0.5 Q10)"),
                       (BIT_A1024, "bit5 `a` >= 1024 (1.0 Q10)")):
        n = int(np.count_nonzero((b4 & bit) != 0))
        print(f"     {label}: {100.0 * n / max(len(b4), 1):7.3f}%  ({n} / {len(b4)})")
        if engaged is not None and engaged.any():
            for lab, m in (("engaged", engaged), ("manual ", ~engaged)):
                if m.sum() >= MIN_SAMPLES:
                    d = 100.0 * np.count_nonzero((b4[m] & bit) != 0) / m.sum()
                    print(f"       {lab}: {d:7.3f}%  ({int(m.sum())} frames)")
    lo = int(np.count_nonzero((b4 & BIT_A512) != 0))
    hi = int(np.count_nonzero((b4 & BIT_A1024) != 0))
    n = max(len(b4), 1)
    print(f"     ⇒ BRACKET: `a` < 512 in {100.0 * (n - lo) / n:.1f}% of frames, in [512, 1024) in "
          f"{100.0 * (lo - hi) / n:.1f}%, and >= 1024 in {100.0 * hi / n:.1f}%.")
    print("       That is the first bound on `a` this kit has ever had, and it unblocks the ~10-build")
    print("       r24-vs-r26 attribution: r26 = ((a * dtorque) >> 10) * gain_A >> 10.")
    print("     ⚠ Two ONE-BIT comparators, not a measurement of `a`. Quote the BRACKET and the")
    print("       duties; do not quote a value for `a`.")


def report_damper(b4, speed_ms):
    """IS LEVER B IN FORCE -- with its own positive control above 35 km/h."""
    print("\n  bit4 -- |gp-0x6bd0| >= 64: IS THE BASE-ASSIST DAMPER ALIVE?")
    if speed_ms is None:
        print("     ⚠ no speed channel -- the creep/highway split is the whole test. Cannot report.")
        return
    kmh = np.asarray(speed_ms) * 3.6
    lo, hi = kmh < FACTORC_ONSET_KMH, kmh >= FACTORC_ONSET_KMH
    for label, m, expect in ((f"below {FACTORC_ONSET_KMH:.0f} km/h (THE TEST)     ", lo,
                              "STOCK is a HARD ZERO here -- any firing is LEVER B"),
                             (f"at/above {FACTORC_ONSET_KMH:.0f} km/h (CONTROL) ", hi,
                              "stock already damps here -- a SILENT rung is BROKEN")):
        if m.sum() < MIN_SAMPLES:
            print(f"     {label}: only {int(m.sum())} frames (< {MIN_SAMPLES}) -- not reportable")
            continue
        n = int(np.count_nonzero((b4[m] & BIT_DAMPABS) != 0))
        print(f"     {label}: {100.0 * n / m.sum():6.3f}%  ({n} / {int(m.sum())})   {expect}")
    if hi.sum() >= MIN_SAMPLES and not np.count_nonzero((b4[hi] & BIT_DAMPABS) != 0):
        print("     🛑 THE POSITIVE CONTROL FAILED. Stock firmware produces non-zero damping above")
        print("        35 km/h, so a rung that never fires there is measuring the wrong cell or did")
        print("        not run. The creep reading above is UNINTERPRETABLE. Do not report it.")


def report_rate(b4, engaged):
    """📋 The pre-registered rung. Compare against the number written BEFORE the drive."""
    print(f"\n  📋 bit3 -- gp-0x6ac0 >= {R_THRESHOLD} counts = {RATE_DEGS:.2f} deg/s. "
          f"PRE-REGISTERED at {PREREG_BIT3_DUTY}% engaged.")
    if engaged is None or engaged.sum() < MIN_SAMPLES:
        n = int(np.count_nonzero((b4 & BIT_RATE512) != 0))
        print(f"     all frames: {100.0 * n / max(len(b4), 1):6.4f}%  (no engagement channel)")
        return
    n = int(np.count_nonzero((b4[engaged] & BIT_RATE512) != 0))
    duty = 100.0 * n / engaged.sum()
    print(f"     engaged duty: {duty:6.4f}%  ({n} / {int(engaged.sum())})")
    print(f"     📋 predicted {PREREG_BIT3_DUTY}% from 345,396 engaged frames of prior route data")
    if duty == 0.0:
        print("     🛑 ZERO. The rate axis is settled three independent ways, so this indicts the")
        print("        CAVE, not the scale: the rung did not run, or it is reading the wrong cell.")
        print("        Treat every other rung on this drive as suspect until it is explained.")
    elif abs(duty - PREREG_BIT3_DUTY) <= 0.5 * PREREG_BIT3_DUTY:
        print("     ✅ within a factor of 1.5 of the pre-registration ⇒ the cave is reading the cell")
        print("        it thinks it is, and the other four rungs inherit that credibility.")
    else:
        print("     ⚠ outside the pre-registration. Report the number; do not re-explain it after the")
        print("       fact -- that is exactly what pre-registration exists to prevent.")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for target in argv[1:]:
        print("=" * 100)
        print(f"  {target}")
        # 🛑 GLUE, fixed 2026-08-04 while extracting route 59: `collect()` takes a LIST of paths and
        # returns `b4` / `lat` / `v`. Passing the bare string made it iterate the path's CHARACTERS
        # (FileNotFoundError: 'a'), and `byte4`/`engaged`/`speed_ms` are not keys it ever returns.
        # Semantics below are untouched.
        data = collect([target])
        b4 = np.asarray(data["b4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            continue
        engaged = np.asarray(data["lat"], dtype=bool) if data.get("has_lat") else None
        speed_ms = data.get("v")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: {dict(Counter(hex(int(v)) for v in b4).most_common(12))}")
        if not identify(b4):
            continue
        report_a(b4, engaged)
        report_damper(b4, speed_ms)
        report_rate(b4, engaged)
        print("\n  🛑 REMINDER: `0x454FE` is CARRIED on V72 but is currently INERT and UNTESTED --")
        print("     V71 measured `gp-0x67fa == 4` at 0/123,277 and 8/92,826 frames (all eight in")
        print("     park), so V42's substitution never ran. It is NOT a fix and NOT falsified.")
        print("     Do not score the 7.79 Hz ratchet against it.")
        print("  🛑 V72 is UNGATED -- the rate-lane dose applies in MANUAL below ~30 km/h, and grind")
        print("     #2 follows the GATE rather than the driver's hands, so if it appears it will")
        print("     appear in BOTH arms. Score manual steering feel separately from engaged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
