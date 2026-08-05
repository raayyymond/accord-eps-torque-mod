#!/usr/bin/env python3
"""decode_v72_probe.py -- read V72's probe: `a`, the base damper, and the rate index.

WHAT V72 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
  LEVER A  both rate lanes dosed **PLATEAU ONLY** through the UNGATED, speed-shaped surfaces:
           gain_B mode-10 rec0/rec1 Y[0..1] -> 5244 / 5122 (r24) and gain_A rec0/rec1 Y[0..1] -> 512
           (r26). Y[2]/Y[3] and the 50/100 km/h records are BYTE-STOCK, so highway is EXACTLY
           1.000000x by record-selection geometry rather than by tuning.
  LEVER B  the base-assist damper opened at creep -- FactorC `0xD27C6`/`0xD27DA` and FactorE
           `0xD2802/04/06` + `0xD2816/18/1A`, **V47's exact flown bytes**. Stock has NO base-assist
           damping anywhere below 35 km/h, which is the whole region where the ratchet and both
           grinds live.
  LEVER C  `0xC63A0` 1024 -> 2048, the weight on `gp-0x6bd0` into FUN_00038148. ONE reader
           image-wide (`0x381AC`), so no monitor can be checking it.
  CARRIED  `0x454FE` = 0xB5. 🛑 **FALSIFIED for the 7.79 Hz ratchet** -- V71B and V71C both flew it
           and the operator reports no change. Carried only because V42 confirmed it against a
           DIFFERENT symptom. **Do not read this build as testing it.**
🛑 V72 IS UNGATED (`0x3AA96` = 0xC5, the dead cell), so the rate-lane dose applies in MANUAL steering
below ~30 km/h too. V67/V68's version was engaged-only. Score manual feel separately.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
-----------------------------------------
    bit7 = 1                     LIVENESS. field == 0 ⇒ the cave did not fire ⇒ the frame is VOID.
    bit6 = gp-0x69a4 >= 512      ★★★★ `a`, **THE UNMEASURED WEIGHT.** r26 = ((a * dtorque) >> 10) *
                                 gain_A >> 10, so `a` sets r26's magnitude RELATIVE to r24. It has
                                 NEVER been measured on this car, it makes every "r24 vs r26" number
                                 in this kit conditional, and it has blocked that attribution for
                                 about ten builds. Producer: a live 10-segment LERP at 0x355C6 in
                                 FUN_000352b4. 512 = 0.5 in the Q10 reading of `a`.
    bit5 = **STRUCTURALLY ZERO** 🛑 THE DROPPED RUNG. The design wanted `gp-0x69a4 >= 1024` here as a
                                 second thermometer step; with bit4 two-sided the five-rung cave came
                                 to 72 B against the proven 68, and the brief's own fallback order
                                 says drop bit5 first. Its weight (0x04) is NEVER added, so bit5
                                 reads 0 in every V72 frame. ⇒ **ONE-WAY BUILD FALSIFIER: a single
                                 frame with bit5 SET proves the artefact is not V72.** The
                                 `bit5 => bit6` monotone invariant the design wanted is LOST with it.
    bit4 = |gp-0x6bd0| >= 64     **IS LEVER B IN FORCE?** The damping lane's own output, post-clamp.
                                 On every build in this kit it is a HARD STRUCTURAL ZERO at creep
                                 (FactorC's LERP clamps to Y[0] = 0 below 35 km/h and the five
                                 factors multiply in Q10), so a non-zero reading below 35 km/h is the
                                 FIRST direct proof the base damper is alive at creep on any build
                                 here. **TWO-SIDED**: the damper is velocity-OPPOSING by construction
                                 (`0x3469e`: if gp-0x6abe > 0, negate), so it alternates sign every
                                 half cycle and a one-sided rung would halve its duty for nothing.
                                 ★ IT CARRIES ITS OWN POSITIVE CONTROL: above 35 km/h stock ALREADY
                                 produces non-zero damping, so the rung must fire at speed even if
                                 Lever B did nothing. A rung that is silent at highway is broken,
                                 not informative.
    bit3 = gp-0x6ac0 >= 400      📋 **PRE-REGISTERED, with a built-in positive control.** Engaged duty
                                 must read **3.74%** under the settled scale (4.7121 counts per
                                 column deg/s ⇒ 400 counts = **84.89 deg/s**) and **0.0000%** under
                                 the retired 8x-smaller alternative, and it must fire frame-for-frame
                                 with bus `|rate_c| >= 84.9 deg/s`. 400 is FactorE's own X[1] AND the
                                 rate lanes' own X[1] breakpoint.

★ THE THRESHOLD IS EXACTLY 400, NOT A POWER OF TWO, AND THAT IS WHAT THE DROPPED RUNG BOUGHT.
The rung idiom derives thresholds by a shift plus `cmp imm5`, which reaches any k*2^s for k in 1..15
-- 400 = 25*16 needs k = 25 and is out of range. One extra 2-byte instruction fixes it:
        ld.hu -0x6ac0[gp],r6 ; shr 0x4,r6 ; add -0x10,r6 ; cmp 0x9,r6 ; blt +4
        fires  <=>  (v >> 4) - 16 >= 9  <=>  v >> 4 >= 25  <=>  **v >= 400**, exactly.
⇒ the pre-registration above carries over VERBATIM instead of needing to be recomputed at 512.

⚠ bit4's EXACT TEST, because it is ONE COUNT asymmetric and that must not be glossed:

        bit4  =  (gp-0x6bd0 >= +64)  OR  (gp-0x6bd0 <= -65)

`sar` FLOORS, so `x sar 6 == -1` spans x in [-64,-1] and no single shifted compare can split
x = -64 from x = -63. The negative arm therefore trips at -65. That is |x| >= 64 for every value
EXCEPT x == -64 exactly. Proven exhaustively over all 65,536 halfword patterns in `_self_check()`
below, not asserted in prose.

🛑🛑 THE ONE-BIT TRAP IS LIVE ON bit4, IN ITS WORST FORM IN THIS KIT'S HISTORY.
`ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT -- and the firmware's own
`st.h r6,-0x6bd0[gp]` @`0x34730` is **`64373094`** against our **`24373094`**: the SAME register and
the SAME displacement halfword. Unlike V70's and V71's zero-reader mirrors, **`gp-0x6bd0` has FIVE
real readers including the 1 kHz aggregator**, so a slipped bit would not corrupt a cell nobody
reads -- it would WRITE a live lane. If you ever see hw1 `0x64..` at cave offset 0x10 where `0x24..`
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
CAVE_HEX = "203e1000e4375d96a9326132a605483a24373094a6326132be057f32ae05423ae4374195843250326932a605413ac33a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e1000  movea 0x10,r0,r7      bit7 LIVENESS, in PRE-SHIFT weights
#   0xC4B38  e4375d96  ld.hu -0x69a4[gp],r6  `a` -- BYTE-IDENTICAL to the aggregator's own read
#                                            @0x3AB3A. UNSIGNED (ld.hu), so `sar` == `shr` below.
#   0xC4B3C  a932      sar   0x9,r6          units of 512
#   0xC4B3E  6132      cmp   0x1,r6
#   0xC4B40  a605      blt   +4
#   0xC4B42  483a      add   0x8,r7          bit6 = gp-0x69a4 >= 512
#   0xC4B44  24373094  ld.h  -0x6bd0[gp],r6  🛑 op 0x39. The st.h twin @0x34730 is 64373094.
#   0xC4B48  a632      sar   0x6,r6          ARITHMETIC -- units of 64, sign preserved
#   0xC4B4A  6132      cmp   0x1,r6          the POSITIVE bound
#   0xC4B4C  be05      bge   +6              s >=  1 => x >= +64            -> SET
#   0xC4B4E  7f32      cmp   -0x1,r6         the NEGATIVE bound (imm5 is SIGNED; -1 encodes 0x1F)
#   0xC4B50  ae05      bge   +4              s >= -1 => |x| is small        -> SKIP
#   0xC4B52  423a      add   0x2,r7          bit4 = |gp-0x6bd0| >= 64, TWO-SIDED (fallthrough)
#   0xC4B54  e4374195  ld.hu -0x6ac0[gp],r6  |motor rate|, UNSIGNED (4 byte-identical real instances)
#   0xC4B58  8432      shr   0x4,r6          LOGICAL -- units of 16
#   0xC4B5A  5032      add   -0x10,r6        -= 16   (Ghidra-confirmed real instance @0x50382)
#   0xC4B5C  6932      cmp   0x9,r6          (v>>4)-16 >= 9  <=>  v >= 400  EXACT
#   0xC4B5E  a605      blt   +4
#   0xC4B60  413a      add   0x1,r7          bit3 = gp-0x6ac0 >= 400
#   0xC4B62  c33a      shl   0x3,r7          the 5-bit field -> bits 7:3. V31P FLASHED this 4x;
#                                            Honda's own idiom @0x4FB82 (shl 0x3,r7 / andi 0xf8).
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]  THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6   the displaced hook instruction
#   0xC4B76  7f00      jmp   [lp]            -> 0x55C12
# 🛑🛑 THE CONDITION-NIBBLE TWINS. `bge +6` is **be05** and `be +6` is **b205** -- ONE NIBBLE apart,
# and the wrong one INVERTS the rung silently. Likewise `bge +4` = ae05 vs `be +4` = a205, and
# `blt +4` = a605. If you are hand-decoding, check the LOW nibble of the first byte: 0xE = bge,
# 0x6 = blt, 0xA = bne, 0x2 = be. Both `bge`s are pinned BY VALUE against real instructions
# (0x6B176 and 0x244CE) and against the real `be +6` @0x3ABFC, in the builder and in the verifier.

BIT_LIVE = 0x80
BIT_A512 = 0x40               # bit6  gp-0x69a4 >= 512   ★★★★ `a`, THE UNMEASURED WEIGHT
BIT_UNUSED5 = 0x20            # bit5  🛑 STRUCTURALLY ZERO -- the dropped rung
BIT_DAMPABS = 0x10            # bit4  |gp-0x6bd0| >= 64, TWO-SIDED -- IS LEVER B IN FORCE?
BIT_RATE400 = 0x08            # bit3  gp-0x6ac0 >= 400   📋 PRE-REGISTERED
PROBE_MASK = 0xF8

A_THRESHOLD = 512             # bit6: ld.hu -> sar 0x9 -> cmp 0x1
D_THRESHOLD = 64              # bit4: ld.h  -> sar 0x6 -> cmp 0x1 / cmp -0x1
D_NEG_THRESHOLD = -65         # ⚠ `sar` FLOORS, so the NEGATIVE arm trips at -65, not -64.
R_THRESHOLD = 400             # bit3: ld.hu -> shr 0x4 -> add -0x10 -> cmp 0x9.  EXACT.

A_DISP, DAMP_DISP, RATE_DISP = 0x69A4, 0x6BD0, 0x6AC0
RATE_SCALE_CTS_PER_DEGS = 4.7121          # the settled column-rate scale
RATE_DEGS = R_THRESHOLD / RATE_SCALE_CTS_PER_DEGS         # 84.89 deg/s
PREREG_ENGAGED_DUTY = 3.74                # 📋 percent, pre-registered BEFORE the drive
PREREG_RETIRED_SCALE_DUTY = 0.0           # under the retired 8x-smaller alternative

FACTORC_ONSET_KMH = 35.0      # below this, STOCK base-assist damping is a HARD ZERO
CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit

# 🛑 ONE LINE, deliberately. build_v72_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V72-LEVERA-BOTHLANES-PLATEAU-r24_5244_5122-r26_512-LEVERB-V47damp-LEVERC-63A0x2-0x454FE-probe-a69a4-damp6bd0-rate400-can330byte4-0x13000-0x100000.rwd"  # noqa: E501

# ⚠ V72's three live rungs are INDEPENDENT, so all EIGHT of their payloads are reachable. bit5 is the
# only forbidden bit, and it is forbidden absolutely.
LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_A512) for b in (0, BIT_DAMPABS) for c in (0, BIT_RATE400)}
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
}

# The cave's REAL instruction boundaries, as (offset, length). Every byte-level check below is made
# on these rather than on "every even offset" -- a displacement halfword decoded as an opcode is how
# a store gets invented or missed. The builder emits exactly this geometry and asserts it.
BOUNDARIES = ((0, 4), (4, 4), (8, 2), (10, 2), (12, 2), (14, 2),          # seed + bit6
              (16, 4), (20, 2), (22, 2), (24, 2), (26, 2), (28, 2), (30, 2),   # bit4
              (32, 4), (36, 2), (38, 2), (40, 2), (42, 2), (44, 2),       # bit3
              (46, 2), (48, 4), (52, 4), (56, 2), (58, 4), (62, 4), (66, 2))   # shl + tail


def _s16(raw):
    return raw - 0x10000 if raw & 0x8000 else raw


def wire_byte4(v69a4, v6bd0, v6ac0, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order."""
    r7 = 0x10                                       # movea 0x10,r0,r7
    if not (((v69a4 & 0xFFFF) >> 9) < 1):           # ld.hu ; sar 0x9 ; cmp 0x1 ; blt +4
        r7 += 0x08
    s = _s16(v6bd0 & 0xFFFF) >> 6                   # ld.h ; sar 0x6  (Python >> floors == `sar`)
    if (s >= 1) or not (s >= -1):                   # cmp 0x1 ; bge SET ; cmp -0x1 ; bge SKIP ; SET
        r7 += 0x02
    q = ((v6ac0 & 0xFFFF) >> 4) - 16                # ld.hu ; shr 0x4 ; add -0x10
    if not (q < 9):                                 # cmp 0x9 ; blt +4
        r7 += 0x01
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 8, f"{len(LEGAL)} legal payloads, expected 8 (three independent rungs)"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert all(not (b & BIT_UNUSED5) for b in LEGAL), "a legal payload has bit5 SET -- it is dropped"
    assert BIT_LIVE | BIT_A512 | BIT_UNUSED5 | BIT_DAMPABS | BIT_RATE400 == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    # ---- bit6, EXHAUSTIVELY. The cell is read `ld.hu` ⇒ zero-extended ⇒ `sar` == `shr`. ----------
    for raw in range(0x10000):
        assert bool(wire_byte4(raw, 0, 0) & BIT_A512) == (raw >= A_THRESHOLD), \
            f"bit6 is not `gp-0x69a4 >= {A_THRESHOLD}` at {raw}"
    # ---- bit4, EXHAUSTIVELY, including the one-count asymmetry ----------------------------------
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
    # ---- bit3, EXHAUSTIVELY. THE THRESHOLD IS EXACTLY 400. --------------------------------------
    for raw in range(0x10000):
        assert bool(wire_byte4(0, 0, raw) & BIT_RATE400) == (raw >= R_THRESHOLD), \
            f"bit3 is not `gp-0x6ac0 >= {R_THRESHOLD}` at {raw}"
    assert not wire_byte4(0, 0, 399) & BIT_RATE400 and wire_byte4(0, 0, 400) & BIT_RATE400, \
        "bit3 does not switch exactly between 399 and 400"
    assert abs(RATE_DEGS - 84.89) < 0.05, "400 counts is not the pre-registered 84.9 deg/s"
    # ---- bit5 is NEVER set, for ANY input --------------------------------------------------------
    for a in (0, 511, 512, 0xFFFF):
        for d in (0, 0x0100, 0xFF00, 0x7FFF, 0x8000):
            for r in (0, 399, 400, 0xFFFF):
                assert not wire_byte4(a, d, r) & BIT_UNUSED5, \
                    "bit5 fired -- it is the DROPPED rung and must read 0 in every frame"
                assert wire_byte4(a, d, r) & PROBE_MASK in LEGAL, "an illegal payload is reachable"
    for status in range(8):
        assert wire_byte4(0xFFFF, 0x7FFF, 0xFFFF, status) == 0xD8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
    # ---- the cave hex, field by field ------------------------------------------------------------
    raw = bytes.fromhex(CAVE_HEX)
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, not the proven 68"
    assert CAVE_HEX.endswith("2436e8ea7f00"), \
        "CAVE_HEX does not end in the displaced movea + jmp [lp]"
    # 🛑 Offsets are (address - 0xC4B34), DERIVED from the listing above, not guessed -- an off-by-4
    # checks the wrong halfword and the guard silently passes on a cave that WRITES.
    assert raw[0:4] == bytes.fromhex("203e1000"), "offset 0 is not `movea 0x10,r0,r7`"
    for off, hw1, disp, kind, what in ((4, "e437", A_DISP, "odd", "ld.hu `a`"),
                                       (16, "2437", DAMP_DISP, "even", "ld.h damper"),
                                       (32, "e437", RATE_DISP, "odd", "ld.hu rate")):
        assert raw[off:off + 2] == bytes.fromhex(hw1), \
            f"CAVE_HEX offset {off} is not a `{what} ...,r6` -- a 0x44../0x64.. hw1 would be a STORE"
        want = (0x10000 - disp) & 0xFFFF
        want = (want & 0xFFFE) | 1 if kind == "odd" else (want & 0xFFFE)
        assert raw[off + 2:off + 4] == want.to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x}"
    # 🛑🛑 THE ld.h / st.h ONE-BIT TRAP, checked against the REAL st.h twin's bytes.
    assert raw[16:20] == bytes.fromhex("24373094"), "the damper load is not `ld.h -0x6bd0[gp],r6`"
    assert raw[16:20] != bytes.fromhex("64373094"), \
        "the damper load IS the real `st.h r6,-0x6bd0[gp]` @0x34730 -- the cave would WRITE a lane " \
        "with FIVE readers, one of them the 1 kHz aggregator. DO NOT FLASH."
    # ⚠ Assemble the HALFWORD first. Picking the opcode field out of individual bytes by hand is the
    # exact "build upward from raw bytes" mistake this kit keeps paying for -- it got this very line
    # wrong once before the assertion caught it.
    _hw1 = int.from_bytes(raw[16:18], "little")
    assert (_hw1 >> 5) & 0x3F == 0x39, \
        f"the damper load's opcode field is 0x{(_hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h). " \
        "0x3B is st.h and the cave would WRITE a live 1 kHz lane."
    assert (_hw1 >> 11) == 6 and (_hw1 & 0x1F) == 4, "the damper load is not `... [gp],r6`"
    for off, want, what in ((8, "a932", "sar 0x9,r6  (bit6)"),
                            (10, "6132", "cmp 0x1,r6  (bit6)"),
                            (12, "a605", "blt +4      (bit6)"),
                            (14, "483a", "add 0x8,r7  (bit6 setter)"),
                            (20, "a632", "sar 0x6,r6  (bit4)"),
                            (22, "6132", "cmp 0x1,r6  (bit4 POSITIVE bound)"),
                            (24, "be05", "bge +6      (bit4 POSITIVE bound)"),
                            (26, "7f32", "cmp -0x1,r6 (bit4 NEGATIVE bound)"),
                            (28, "ae05", "bge +4      (bit4 NEGATIVE bound)"),
                            (30, "423a", "add 0x2,r7  (bit4 setter)"),
                            (36, "8432", "shr 0x4,r6  (bit3)"),
                            (38, "5032", "add -0x10,r6 (bit3 bias)"),
                            (40, "6932", "cmp 0x9,r6  (bit3, => v >= 400)"),
                            (42, "a605", "blt +4      (bit3)"),
                            (44, "413a", "add 0x1,r7  (bit3 setter)"),
                            (46, "c33a", "shl 0x3,r7")):
        assert raw[off:off + 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what}) -- a wrong nibble INVERTS the rung"
    assert raw[24:26] != bytes.fromhex("b205"), "bit4's positive bound is `be` (b205), not `bge`"
    # 🛑 the weight 0x04 (bit5) must appear NOWHERE as an `add imm5,r7`
    assert bytes.fromhex("443a") not in raw, \
        "the cave contains `add 0x4,r7` -- bit5 is the DROPPED rung and must never be set"
    # 🛑 EXACTLY ONE STORE IN THE WHOLE CAVE, and it is the CAN-330 payload byte. Checked on the
    # REAL instruction boundaries -- scanning every even offset would decode displacement halfwords
    # as opcodes and is how a "store" gets missed or invented.
    assert sum(n for _o, n in BOUNDARIES) == 68 and [o for o, _n in BOUNDARIES][0] == 0, \
        "the boundary table does not tile the 68-byte cave"
    for prev, nxt in zip(BOUNDARIES, BOUNDARIES[1:]):
        assert prev[0] + prev[1] == nxt[0], f"the boundary table is not contiguous at {prev}"
    stores = [o for o, n in BOUNDARIES
              if n >= 4 and ((int.from_bytes(raw[o:o + 2], "little") >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert stores == [58], f"the cave's store set is {stores}, expected exactly [58]"
    assert raw[58:62] == bytes.fromhex("4437ecea"), \
        "offset 58 is not `st.b r6,-0x1514[gp]` -- the sole store moved"


_self_check()

RUNGS = ((BIT_A512, f"bit6 gp-0x{A_DISP:04X}", A_DISP,
          f"`a` >= {A_THRESHOLD} (0.5 in Q10) -- r26's own weight, NEVER measured before V72"),
         (BIT_DAMPABS, f"bit4 gp-0x{DAMP_DISP:04X}", DAMP_DISP,
          f"|base-assist damper| >= {D_THRESHOLD}, TWO-SIDED -- IS LEVER B IN FORCE?"),
         (BIT_RATE400, f"bit3 gp-0x{RATE_DISP:04X}", RATE_DISP,
          f"|motor rate| >= {R_THRESHOLD} counts = {RATE_DEGS:.1f} deg/s -- 📋 PRE-REGISTERED"))


def identify(b4):
    """Which build produced this payload stream? Reported at its REAL strength, not more."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    illegal = int(np.count_nonzero([(v & PROBE_MASK) not in LEGAL for v in b4]))
    bit5 = int(np.count_nonzero((b4 & BIT_UNUSED5) != 0))
    print(f"  VOID (probe field == 0, the cave did not fire) : {void} / {len(b4)}")
    print(f"  ILLEGAL (bit7 clear, or bit5 SET)              : {illegal} / {len(b4)}")
    print(f"  bit5 SET (🛑 must be 0 in EVERY V72 frame)      : {bit5} / {len(b4)}")
    if void or illegal:
        print("  🛑 HARD FAIL. A VOID frame means the cave did not run; a bit5-SET frame means the")
        print("     flashed image is NOT V72 (bit5's weight is never added). Nothing below may be")
        print("     interpreted. Check the .rwd filename against RWD_NAME.")
        return False
    for name in STRUCTURALLY_DISJOINT:
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    print("  ✅ bit5 is CLEAR in every frame -- consistent with V72. ⚠ This is a ONE-WAY test: it")
    print("     falsifies V72 when bit5 fires, but a clear bit5 does not PROVE V72 (V70's bit5 read 0")
    print("     too). The .rwd FILENAME remains the pre-drive discriminator:")
    print(f"       {RWD_NAME}")
    for bit, name, _cell, what in RUNGS:
        n = int(np.count_nonzero((b4 & bit) != 0))
        print(f"  {name} set: {n:7d} / {len(b4)}  ({100.0 * n / max(len(b4), 1):6.3f}%)   {what}")
    return True


def report_bit6(b4, engaged):
    """★★★★ `a` -- the quantity that makes every r24-vs-r26 number in this kit conditional."""
    print("\n  ★★★★ bit6 -- `a` = gp-0x69a4, THE UNMEASURED WEIGHT")
    n = int(np.count_nonzero((b4 & BIT_A512) != 0))
    duty = 100.0 * n / max(len(b4), 1)
    print(f"     duty over all frames      : {duty:6.3f}%  ({n} / {len(b4)})")
    if engaged is not None and engaged.any():
        for label, m in (("engaged", engaged), ("manual ", ~engaged)):
            if m.sum() >= MIN_SAMPLES:
                d = 100.0 * np.count_nonzero((b4[m] & BIT_A512) != 0) / m.sum()
                print(f"     duty {label}              : {d:6.3f}%  ({m.sum()} frames)")
    print(f"     ⇒ a duty near 0% bounds `a` BELOW {A_THRESHOLD} (0.5 in Q10) for the whole drive;")
    print(f"       a duty near 100% bounds it ABOVE. Either way r26's magnitude relative to r24 is")
    print("       BOUNDED for the first time, and the ~10-build r24-vs-r26 attribution unblocks.")
    print("     ⚠ It is a ONE-BIT comparator, not a measurement of `a`. Do not quote a value for `a`;")
    print(f"       quote the bound and the duty. (V72's r26 = ((a*dtorque)>>10)*gain_A>>10.)")


def report_bit4(b4, speed_ms):
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
        print("        not run. The creep reading below is UNINTERPRETABLE. Do not report it.")


def report_bit3(b4, engaged):
    """📋 The pre-registered rung. Compare against the number written BEFORE the drive."""
    print("\n  📋 bit3 -- gp-0x6ac0 >= 400 counts = "
          f"{RATE_DEGS:.2f} deg/s. PRE-REGISTERED at {PREREG_ENGAGED_DUTY}% engaged.")
    if engaged is None or engaged.sum() < MIN_SAMPLES:
        n = int(np.count_nonzero((b4 & BIT_RATE400) != 0))
        print(f"     all frames: {100.0 * n / max(len(b4), 1):6.4f}%  (no engagement channel)")
        return
    n = int(np.count_nonzero((b4[engaged] & BIT_RATE400) != 0))
    duty = 100.0 * n / engaged.sum()
    print(f"     engaged duty: {duty:6.4f}%  ({n} / {int(engaged.sum())})")
    print(f"     📋 predicted {PREREG_ENGAGED_DUTY}% under the SETTLED scale "
          f"({RATE_SCALE_CTS_PER_DEGS} counts per deg/s)")
    print(f"     📋 predicted {PREREG_RETIRED_SCALE_DUTY}% under the RETIRED 8x-smaller alternative")
    if duty == 0.0:
        print("     🛑 ZERO. That matches the RETIRED scale, not the settled one -- which would mean")
        print("        the axis scale in the golden model is wrong by 8x and every rate-indexed")
        print("        conclusion in this kit needs re-pricing. Treat as a finding, not a bug.")
    elif abs(duty - PREREG_ENGAGED_DUTY) <= 0.5 * PREREG_ENGAGED_DUTY:
        print("     ✅ within a factor of 1.5 of the pre-registration ⇒ the settled scale HOLDS and")
        print("        the cave is reading the cell it thinks it is.")
    else:
        print("     ⚠ neither prediction. Report the number; do not re-explain the scale after the")
        print("       fact -- that is exactly what pre-registration exists to prevent.")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for target in argv[1:]:
        print("=" * 100)
        print(f"  {target}")
        data = collect(target)
        b4 = np.asarray(data["byte4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            continue
        engaged = np.asarray(data["engaged"], dtype=bool) if "engaged" in data else None
        speed_ms = data.get("speed_ms")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: "
              f"{dict(Counter(hex(int(v)) for v in b4).most_common(10))}")
        if not identify(b4):
            continue
        report_bit6(b4, engaged)
        report_bit4(b4, speed_ms)
        report_bit3(b4, engaged)
        print("\n  🛑 REMINDER: `0x454FE` is CARRIED on V72 but is FALSIFIED for the 7.79 Hz ratchet")
        print("     (V71B and V71C both flew it unchanged). Do not score the ratchet against it.")
        print("  🛑 V72 is UNGATED -- the rate-lane dose applies in MANUAL below ~30 km/h. Score")
        print("     manual steering feel separately from engaged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
