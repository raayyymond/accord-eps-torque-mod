#!/usr/bin/env python3
"""decode_v70_probe.py -- read V70's probe: three REPAIRED rungs and a sign bit.

WHAT CHANGED FROM V69, AND WHY EVERY RUNG MOVED
------------------------------------------------
V69's probe returned three uninterpretable zeros, and the post-mortem found a different cause for
each. None of them was "the lane was quiet":

  bit4 was STRUCTURALLY VACUOUS. `gp-0x6ad4` is clamped to +/-CEILING, where CEILING is the MIN of
      three LERPs whose smallest max is 1024 (cal 0xC67C8) and which reads 164-341 at the ratchet's
      own 4.9-8.0 km/h. V69 tested it at >= 4096 -- unreachable on ANY build, on ANY drive. The
      design had read the lane's ERR INPUT clamp (+/-0x2800) as if it were its OUTPUT range.
  bit5 was INSENSITIVE. `gp-0x6b62`'s reachable maximum is 5786, so 4096 sat at 71% of full range.
  bit6 had NO EXPOSURE at that threshold -- ~1 predicted one-sided hit across the whole of route 4f.

V70 keeps only the cell that was worth keeping, drops the threshold to where the lane actually
lives, and spends the freed bytes on two things V69 could not do: a STATE gate, and a SIGN bit.

🛑 WHICH CONTROL PATH THIS PROBE IS RIDING ON -- the probe was built against a FIRST CUT of V70 that
restored V67/V68's arm-5244 path. That cut was SUPERSEDED on operator override (*"V70 just reverts
back to V68, which has the high-speed grind #2 issue"*). **The shipped V70 is V69's TOPOLOGY at HALF
the dose**: gate on the DEAD `gp-0x683c`, arm stock 512 and unreachable, mode-10 gain_B rec0/rec1 at
2x -- delivering 2.000000x at creep tapering to EXACTLY 1.000000x at and above 50 km/h, with max
2.000000x and min 1.000000x anywhere. The probe is byte-for-byte unchanged across that re-cut; only
its sizing note (bit6) and the r26 framing (READOUT 1) needed re-stating, and both are re-stated
below rather than left to rot.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7 = 1                   LIVENESS. field == 0 => the cave did not fire => the frame is VOID.
    bit6 = gp-0x6ada >= +512   *** THE POSITIVE CONTROL. *** r24's lane output, after its own
                               +/-0x2000 saturating clip, mirrored to RAM by Honda's own code at
                               0x3AD5A every 1 kHz tick. 0 READERS / 1 WRITER image-wide.
                               🛑 T = +512 was sized on V70's FIRST CUT, which shipped V67/V68's
                               arm-5244 control path. That cut was SUPERSEDED (see below). The
                               threshold survives the re-cut: under the shipped 2x surface it sits
                               BETWEEN the stock case (route duty 0.500%, prominence 15.6) and the
                               4x case (4.878%, 30.6), so it stays a live positive control with no
                               saturation risk at either end.
    bit5 = gp-0x67fa == 10     *** THE STATE GATE. *** See READOUT 2 -- it is non-vacuous in BOTH
                               directions, which is the whole reason it is worth a rung.
    bit4 = gp-0x6adc >= 0      r26's post-clamp lane mirror -- also 0 READERS / 1 WRITER
                               (`st.h` @0x3AD4E). A SIGN test, not a threshold. Read it as an
                               AGREEMENT statistic against bit3, never as a standalone duty.
    bit3 = gp-0x6ada >= 0      r24's SIGN, from the same shifted register, for 6 more bytes.
    bits 2:0                   stock STEER_SENSOR_STATUS, preserved.

★★★ bit3 IS THE KEYSTONE -- IDENTITY, INVARIANT, RATCHET, AND bit4's CONTROL
------------------------------------------------------------------------------
 1. BUILD IDENTITY. A constant bit3 cannot separate V70 from both neighbours: V68 emits bit3 = 1
    (measured 100.000% of 53,991 frames), V66/V67/V69 emit bit3 = 0 (structurally -- all three
    ASSERT it in their builders). Either constant makes V70 a subset of one of them. A bit3 that is
    GUARANTEED NON-CONSTANT on any drive with steering excludes both directions at once.
 2. THE ORDER INVARIANT bit6 => bit3 (x >= +512 implies x >= 0), proven in the builder over all
    65,536 halfword patterns. Only 12 of the 16 payloads are reachable and **bit6 = 1 with
    bit3 = 0 is IMPOSSIBLE**. 🛑 This decoder treats an order violation as a HARD FAILURE, not a
    warning: it means the flashed image is not this build, and nothing below it can be trusted.
 3. ★ IT IS AMPLITUDE-INDEPENDENT. A one-sided THRESHOLD only sees the ratchet when the lane
    exceeds 512. The SIGN sees a symmetric limit cycle at ~50% duty REGARDLESS of amplitude. At
    ~7.4-7.6 Hz on the 100.000 Hz grid that is ~13.5 samples/cycle, so bit3's own time series
    carries the fundamental whether the ratchet is large or small. bit6 measures its SIZE; bit3
    measures its PRESENCE.
 4. ★★ IT IS bit4's MATCHED POSITIVE CONTROL -- see immediately below.

★★ READOUT 1: IS r26 LIVE?  THE STATISTIC IS bit3/bit4 AGREEMENT, NOT TWO SEPARATE DUTIES
--------------------------------------------------------------------------------------------
From the golden model (`eps_lkas_chain_model.py` ~line 1193): r24 and r26 take **the same
`dtorque`** and **the same single polarity read** -- one `ld.b -0x6752[gp],r14` @`0x3AB78`, reused
by both lanes -- and `gp-0x69a4` is an unsigned magnitude at both ends. ⇒ **r24 and r26 ALWAYS
CARRY THE SAME SIGN, by construction.** So the two sign rungs are a matched pair and the
discriminator is their AGREEMENT against a chance baseline, not their marginal duties:

    bit4 ≡ 1 while bit3 toggles      => gp-0x6adc is pinned at 0 => **r26 IS INERT**, a ~ 0, the r26
                                        concern evaporates, and V67/V68 were NOT secretly below
                                        stock. (Agreement then equals chance BY CONSTRUCTION -- the
                                        statistic degrades to "no information", which is correct.)
    bit4 TRACKS bit3 (agreement >>   => **r26 IS LIVE** and `a` is material. ⚠ RETROSPECTIVE, not a
    chance, excess CI clears 0)         property of V70: it would mean V67/V68's GATE was cutting
                                        total damping ~6x while engaged, because that gate pins
                                        r26's arm to 0xC6444 = 512 against a gain_A LERP of 3072 at
                                        creep. **V70's gate is OFF**, so r26 takes its own LERP here
                                        and nothing is being cut on this build -- the reading prices
                                        V67/V68 and any future GATED build, not this one.
    bit4 ANTI-correlates with bit3   => the same-sign claim is WRONG and the golden model needs
                                        correcting. Report it as such; do not explain it away.

🛑 THE COST, STATED HONESTLY: **V70 measures r26's LIVENESS, not `a`.** The brief originally specced
bit4 at the same +512 threshold as bit6 so the duty RATIO would estimate `a = gp-0x69a4/1024`
directly. That did not fit -- the cave budget is 68 B and four signals cost 2 B more than that with
a `sar` on bit4 -- and it was the weaker measurement anyway: the standing record (cal base 0xC6564
= 40 bytes of exact zero) PREDICTS r26 inert, so a `>= +512` rung reading 0.000% was the expected
outcome and could not separate "inert" from "live but under 512". Magnitude only ever mattered in
the branch where r26 turns out live, and this settles that branch first.

★★ READOUT 2: IS THE ECU IN STATE 10?  NON-VACUOUS IN BOTH DIRECTIONS
------------------------------------------------------------------------
🛑 THE GATE IS IN THE CALLER, NOT INSIDE THE FOUR FUNCTIONS. Each has exactly one call site, all in
the dispatcher `FUN_0002214a`, and the mask wraps the `jarl` -- so a masked-out state means the
function is **never invoked**, with no stack frame. That is a cleaner claim than "gated internally".
Verified at instruction level (EVIDENCE, GhidraMCP dry-run disassembly + raw LE byte scan, this
session):

    0x2214E  ld.bu -0x67fa,gp,r13      the state byte, at the very top of the dispatcher
    0x2216C  mov   0x1,r11
    0x22172  andi  0xf,r13,r15         state & 0xf
    0x2217C  shl   r15,r11,r25         r25 = 1 << (state & 0xf)   <- plain, NO off-by-one
    0x221D6  andi  0x830,r25,r28       r28 != 0  <=>  state in {4, 5, 11}
    0x2269A  andi  0xc30,r25,r22       r22 != 0  <=>  state in {4, 5, 10, 11}
    0x22518  andi  0x930,r25,r27       r27 != 0  <=>  state in {4, 5, 8, 11}   (arbitration trio)

    guarded by r28 (0x830):  0x22882 jarl FUN_00036388   return-to-centre
                             0x22926 jarl FUN_000428d4   Honda's 1 kHz oscillation detector
    guarded by r22 (0xc30):  0x226A0 jarl FUN_0003a382   unfiltered residual lane
                             0x2291E jarl FUN_0003aa2c   the assist aggregator

**State 10 is the difference**, and it is a real state: the 33 `st.b` writers of `gp-0x67fa` carry
the literal histogram {1:1, 3:1, 4:5, 5:1, 6:10, 7:4, 8:1, 9:2, 10:2, 11:4}, with 10 written at
`0x199CE` and at `0x19A74` (a normal-mode path) -- both `mov 0xa,rN` immediately followed by
`st.b rN,-0x67fa[gp]`, confirmed in Ghidra.
✅ PROVENANCE, and it is EVIDENCE rather than inference-by-adjacency: the dispatcher was decompiled
against stock `code.bin`, but `[0x2214A, 0x22940)` is **byte-identical between `code.bin` and
`_v68_plain_image.bin`** (raw Python compare), as are the four callees' entries and the `0x3AB78`
polarity load. The reading therefore transfers to the flown image exactly.
⚠ `andi 0xf` means a state >= 16 would ALIAS onto a low state. The maximum literal ever written is
11, so this cannot bite today -- but a future revision that adds states must re-check it.

★ WHY A ZERO HERE IS A RESULT, NOT A FAILURE. The car demonstrably steers, so the aggregator ran, so
`gp-0x67fa` was in {4, 5, 10, 11} by its own `0xc30` gate. Therefore:

    bit5 ~ 0                 => state in {4, 5, 11} => `FUN_00036388` and `FUN_000428d4` **DID
                                execute** => the `gp-0x67df` detector nulls on V64/V67/V68
                                (0/14,980 + 0/186,321 + 0/53,991) are **GENUINE**, and five builds
                                of null are vindicated rather than wasted.
    bit5 materially non-zero => those two were **skipped** => five builds of detector nulls were
                                nulls **on the gate**, bounding nothing about oscillation, and that
                                instrument is retired rather than merely quiet.

Both are decision-bearing. Reported below as a DUTY with an episode-clustered CI, never as hit/miss.

🛑 PRE-REGISTERED PREDICTION (recorded BEFORE any V70 drive, so a surprise is a real surprise and
not a post-hoc story): **bit5 will read LOW.** The third mask `0x930` = {4, 5, 8, 11} gates the
arbitration trio -- `gp-0x6806`'s producer -- and state 10 is absent from it too, so in state 10
that flag goes stale. But V67's probe measured `gp-0x6806 == carControl.latActive` in
**150,302 / 150,327 = 99.983%** of frames, with all 25 disagreements single-frame transition edges.
A stale flag cannot track engage/disengage transitions that closely, so the ECU is predominantly
NOT in state 10 while engaged.

⚠ OPEN, AND IT BEARS ON HOW ANY FUTURE DETECTOR NULL IS READ: `FUN_000428d4` has a **second,
independent entry gate** -- `FUN_00046ea6(5)` on bit 5 of `gp-0x18d0`/`gp-0x18d4`, a fault/DTC-style
bitmask, falling to a `0x8000` sentinel if set. The existing record established only that the
FUNCTION has one caller; it never established that this BIT is clear in operation. So `bit5 ~ 0`
licenses "the call was made", NOT "the detector body ran to completion". The other three functions
have no secondary gate. This rung cannot see `gp-0x18d0`, and no V70 reading closes it.

IDENTIFICATION -- what this probe can and cannot exclude
--------------------------------------------------------
  EXCLUDED ABSOLUTELY, from the value set alone:
    V53 {0x07} and V54 {0x0F}  -- bit7 CLEAR; V70 sets bit7 on every frame it emits.
    V66, V67 {0x87, 0xC7}      -- 0xC7 is bit6=1 with bit3=0, which V70 CANNOT emit. Their bit6 is
                                  the LKAS gate at 21.7-49.9% duty, so 0xC7 appears in bulk.
    V69                        -- bit3 structurally CONSTANT 0 => any bit3=1 frame excludes it.
    V68                        -- bit3 CONSTANT 1 (folded into its `movea 0x88` and measured
                                  53,991/53,991) => any bit3=0 frame excludes it.
    V65                        -- its ladder ASSERTS NOT((bit6|bit5) AND (bit4|bit3)); V70 emits
                                  bit6 AND bit3 together on every excursion >= +512.
  ⇒ EVERY BUILD FROM V65 ONWARD, including V68 (on the car) and V69 (the only other candidate).
  NEAR-CERTAIN, by co-occurrence: V59/V60/V61/V62/V63 run a nested thermometer with bit4 => bit3;
    V70 emits bit4=1 with bit3=0 (certain if r26 is inert, near-certain otherwise).
  ⚠ RESIDUAL, STATED PLAINLY: V55, V57, V58 and V64 are four-bit probes with INDEPENDENT bits, so
    their reachable space is all 16 payloads and NO value-set argument can exclude them. They are 6+
    builds back and none is a plausible mis-flash; identification against those rests on the .rwd
    filename. This is a strictly SMALLER residual than V69's, whose ambiguity was V66/V67 -- two
    builds back and the immediate predecessors.

🛑 HOW TO READ A NULL ON THIS PROBE
  (a) bit6 IS STILL ONE-SIDED. bit3 is its two-sided partner for gp-0x6ada; bit4's sign is one bit
      of a two-sided story on gp-0x6adc. Never quote a bit6 null as two-sided.
  (b) SAMPLED AT 100 Hz at the TX hook while the aggregator runs at 1 kHz, so a sample can be one
      tick stale relative to the lane evaluation. Immaterial for duty and for a 7.4 Hz line. Do NOT
      use these bits for a per-tick correlation.
  (c) ORDER OF INTERPRETATION, and it is the V64 lesson: check bit7 and the .rwd name, then confirm
      bit3 TOGGLES, then read bit6. A bit3 that never toggles means the probe is not V70's.

🛑 ONE FIRMWARE PRECONDITION MAKES bit6/bit4/bit3 MEANINGFUL, and it is an IMAGE fact, not a wire
fact -- so it is asserted at BUILD time (`verify_v70_image.py`) and only recorded here. FUN_0003aa2c
has a REDUCED aggregator mode: when `gp-0x67ac == 1` it sums the LKAS lane and gp-0x6b62 ONLY,
skipping both inline r24/r26 lanes. In that mode bit6, bit4 and bit3 would report lanes that are not
in the sum at all. It is unreachable on this ROM: the selector traces to the per-source TYPE array
(cal 0xC4124 = [0,0,5,0,5,5,0,0,0,5,0]), which never matches the qualifying literals {2,3,4}, so
gp-0x67ac is always 0 and the FULL path always runs.

Usage:  python decode_v70_probe.py <route-dir-or-segment-paths...>
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX. cp1252 is chosen for a redirected stdout on this machine and the first
# `print(__doc__)` raises UnicodeEncodeError on the 🛑/★/⚠ glyphs, so `> out.txt` crashed before
# emitting a line. Set here as well as in the imported module -- either file can be __main__.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
# ⚠ The NUMERIC MACHINERY is shared on purpose -- collect/sustained/runs_of are instrument code, not
# semantics, and two copies would drift. `analog_line`, `matched_null` and the 128-sample floor are
# inherited from decode_v69_ratchet, where they were FIXED on 2026-08-04; do not re-derive them here
# and do not regress them.
from decode_v67_gate import collect, runs_of, sustained, transitions        # noqa: E402
from decode_v69_ratchet import (MIN_SAMPLES, RATCHET_F0, analog_line,       # noqa: E402
                                matched_null, ratchet_line)

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v70_tva.assert_decoder_matches() fails the BUILD if this
# string is not byte-for-byte the cave in the built artifact. V66's decoder header was stale for one
# revision and claimed bit4 = gp-0x683c when the image read gp-0x67fe; this is the fix for that class
# of error. Do not edit by hand -- rebuild and copy.
CAVE_HEX = "203e800024372695a9326132b605273e4000e031a605483a843707986a32ba05273e200024372495e031b605273e10008437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e8000  movea 0x80,r0,r7        bit7 LIVENESS.  bit3 is a RUNG on V70, not a constant.
#   0xC4B38  24372695  ld.h  -0x6ada[gp],r6    r24 lane out, post +/-0x2000 clip  (0 readers)
#   0xC4B3C  a932      sar   0x9,r6            ARITHMETIC -- units of 512, sign preserved
#   0xC4B3E  6132      cmp   0x1,r6
#   0xC4B40  b605      blt   +6
#   0xC4B42  273e4000  movea 0x40,r7,r7        bit6 = gp-0x6ada >= +512
#   0xC4B46  e031      cmp   r0,r6             the SAME shifted value: (x>>9) >= 0  <=>  x >= 0
#   0xC4B48  a605      blt   +4
#   0xC4B4A  483a      add   0x8,r7            bit3 = gp-0x6ada >= 0     (bit6 => bit3, ALWAYS)
#   0xC4B4C  84370798  ld.bu -0x67fa[gp],r6    the ECU STATE byte
#   0xC4B50  6a32      cmp   0xa,r6
#   0xC4B52  ba05      bne   +6                🛑 `be` (b205) is its twin and would INVERT this rung
#   0xC4B54  273e2000  movea 0x20,r7,r7        bit5 = (gp-0x67fa == 10)
#   0xC4B58  24372495  ld.h  -0x6adc[gp],r6    r26 lane mirror  (0 readers)
#   0xC4B5C  e031      cmp   r0,r6
#   0xC4B5E  b605      blt   +6
#   0xC4B60  273e1000  movea 0x10,r7,r7        bit4 = gp-0x6adc >= 0
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]     THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6     the displaced hook instruction
#   0xC4B76  7f00      jmp   [lp]              -> 0x55C12
# 🛑 `ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT apart -- and BOTH probed mirrors have their
# only real instances as the st.h form (0x3AD5A, 0x3AD4E) carrying the SAME displacement halfword.
# `ld.bu` 0x3C vs `st.b` 0x3A is likewise one bit, on a LIVE state variable with 128 readers. If you
# ever see hw1 0x64.. where 0x24.. is written above, the cave WRITES. Do not flash it.
# ★ One real de-risking versus V69: V69's third rung read gp-0x6ad4, which the aggregator CONSUMES at
# 0x3ACA8, so a slipped opcode there would have corrupted a live lane. V70's two `ld.h` rungs are
# both on ZERO-READER mirrors -- a slip could only produce a wrong READING.
# ⚠ 68 of the 68 proven cave bytes are used. ZERO spare. A fifth signal does not fit, and the extent
# must NOT be grown to make one fit -- caves are this kit's only bricking class (V24, V27, V48B).

BIT_LIVE = 0x80
BIT_R24_HALF = 0x40           # bit6  gp-0x6ada >= +512   THE POSITIVE CONTROL
BIT_STATE10 = 0x20            # bit5  gp-0x67fa == 10     THE STATE GATE
BIT_R26_SIGN = 0x10           # bit4  gp-0x6adc >= 0      r26 mirror SIGN
BIT_R24_SIGN = 0x08           # bit3  gp-0x6ada >= 0      r24 mirror SIGN -- the keystone
PROBE_MASK = 0xF8
THRESHOLD = 512               # bit6: ld.h -> sar 0x9 -> cmp 0x1  =>  cell >= 1 << 9
STATE_VALUE = 10

# The dispatcher's three masks. state in mask  <=>  (1 << (state & 0xf)) & mask.
MASK_DETECTOR = 0x830         # {4,5,11}     FUN_00036388 @0x22882, FUN_000428d4 @0x22926
MASK_AGGREGATOR = 0xC30       # {4,5,10,11}  FUN_0003a382 @0x226A0, FUN_0003aa2c @0x2291E
MASK_ARBITRATION = 0x930      # {4,5,8,11}   the arbitration trio -- gp-0x6806's producer

# (bit, short name, gp cell, what a 1 means)
RUNGS = (
    (BIT_R24_HALF, "bit6 gp-0x6ada", 0x6ADA,
     f"r24 lane out >= +{THRESHOLD} (post +/-8192 clip) -- 0 readers image-wide. POSITIVE CONTROL"),
    (BIT_STATE10, "bit5 gp-0x67fa", 0x67FA,
     f"the ECU is in STATE {STATE_VALUE} -- aggregator runs, detector and return-to-centre do NOT"),
    (BIT_R26_SIGN, "bit4 gp-0x6adc", 0x6ADC,
     "r26 lane mirror >= 0 -- read as AGREEMENT with bit3, never as a standalone duty"),
    (BIT_R24_SIGN, "bit3 gp-0x6ada", 0x6ADA,
     "r24 lane mirror >= 0 -- the SIGN. Amplitude-independent, so it carries the ratchet line"),
)

CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit

# ★ THE ORDER INVARIANT, as the definition of the legal set: bit6 => bit3. 12 of 16, not 16.
LEGAL = {BIT_LIVE | a | b | c | d
         for a in (0, BIT_R24_HALF) for b in (0, BIT_STATE10)
         for c in (0, BIT_R26_SIGN) for d in (0, BIT_R24_SIGN)
         if not (a and not d)}
IMPOSSIBLE = {BIT_LIVE | BIT_R24_HALF | b | c
              for b in (0, BIT_STATE10) for c in (0, BIT_R26_SIGN)}      # bit6 set, bit3 clear
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

# 🛑 ONE LINE, deliberately. The builder asserts this exact basename appears in this file; splitting
# it across a string concatenation makes the substring vanish and the check silently harder to pass.
RWD_NAME = "39990-TVA,A160-V70-LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-gainB-rec0rec1-x2-signprobe-6ada-67fa10-6adc-can330byte4-0x13000-0x100000.rwd"  # noqa: E501

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
    "V66/V67 (0xC7 is bit6=1 with bit3=0 -- IMPOSSIBLE on V70)": {0x87, 0xC7},
}


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 12, f"{len(LEGAL)} legal payloads, expected 12 of 16"
    assert len(IMPOSSIBLE) == 4, "the invariant must forbid exactly 4 payloads"
    assert not (LEGAL & IMPOSSIBLE), "LEGAL and IMPOSSIBLE overlap -- the invariant is not encoded"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert BIT_LIVE | BIT_R24_HALF | BIT_STATE10 | BIT_R26_SIGN | BIT_R24_SIGN == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    assert all(b & BIT_R24_SIGN for b in {0x8F, 0xCF}), "V68's payloads must have bit3 SET"
    assert not any(b & BIT_R24_SIGN for b in {0x87, 0xC7}), "V66/V67/V69 payloads must have bit3 CLEAR"
    assert 0xC7 in {p | 0x07 for p in IMPOSSIBLE}, "0xC7 must be IMPOSSIBLE on V70 -- that is V66/V67"
    # the three dispatcher masks, decoded back to state sets so a typo cannot survive review
    assert {s for s in range(16) if (1 << s) & MASK_DETECTOR} == {4, 5, 11}, "0x830 is not {4,5,11}"
    assert {s for s in range(16) if (1 << s) & MASK_AGGREGATOR} == {4, 5, 10, 11}, \
        "0xc30 is not {4,5,10,11}"
    assert {s for s in range(16) if (1 << s) & MASK_ARBITRATION} == {4, 5, 8, 11}, \
        "0x930 is not {4,5,8,11}"
    assert (1 << STATE_VALUE) & MASK_AGGREGATOR and not (1 << STATE_VALUE) & MASK_DETECTOR, \
        f"state {STATE_VALUE} must be IN the aggregator mask and OUT of the detector mask -- that " \
        "difference is the entire point of the bit5 rung"
    raw = bytes.fromhex(CAVE_HEX)
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, not the 68-byte V70 cave"
    assert CAVE_HEX.endswith("2436e8ea7f00"), "CAVE_HEX does not end in the displaced movea + jmp [lp]"
    # offsets are (address - 0xC4B34): ld.h 6ada @0xC4B38 -> 4, ld.bu 67fa @0xC4B4C -> 24,
    # ld.h 6adc @0xC4B58 -> 36. 🛑 Derived from the listing, not guessed -- an off-by-4 here checks
    # the wrong halfword and the guard silently passes on a cave that WRITES.
    for off, disp in ((4, 0x6ADA), (36, 0x6ADC)):
        assert raw[off:off + 2] == bytes.fromhex("2437"), \
            f"CAVE_HEX offset {off} is not an `ld.h ...,r6` -- 0x6437 would be an st.h, a WRITE"
        assert raw[off + 2:off + 4] == ((0x10000 - disp) & 0xFFFF).to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x}"
    assert raw[24:26] == bytes.fromhex("8437"), \
        "CAVE_HEX offset 24 is not an `ld.bu ...,r6` (even-disp form) -- 0x4437 would be an st.b"
    assert raw[26:28] == bytes.fromhex("0798"), "CAVE_HEX offset 24 does not read gp-0x67fa"


_self_check()


def wire_byte4(v6ada, v67fa, v6adc, status_bits=0x7):
    """EXACTLY what the cave computes, mirroring the emitted instructions one for one."""
    def s16(x):
        return x - 0x10000 if x & 0x8000 else x
    r7 = BIT_LIVE
    r6 = s16(v6ada) >> 9                       # sar 0x9 -- Python >> floors, exactly like `sar`
    if not (r6 < 1):
        r7 += BIT_R24_HALF
    if not (r6 < 0):
        r7 += BIT_R24_SIGN
    if (v67fa & 0xFF) == STATE_VALUE:
        r7 += BIT_STATE10
    if not (s16(v6adc) < 0):
        r7 += BIT_R26_SIGN
    return r7 | (status_bits & 0x07)


# =====================================================================================================
# Episode-clustered inference. 🛑 Bootstrap over EPISODES, never windows -- window bootstraps shrink
# CIs by ~sqrt(frames per episode) and manufacture significance. Standing instruction, 2026-08-02.
# =====================================================================================================

def episodes_of(sel, min_len=MIN_SAMPLES):
    return [ab for ab in runs_of(np.asarray(sel, bool)) if ab[1] - ab[0] >= min_len]


def episode_ratio(eps, num, den, draws=2000, seed=70):
    """Pooled num/den with a CI from resampling EPISODES with replacement."""
    if not eps:
        return float("nan"), (float("nan"), float("nan"))
    n = np.array([float(np.asarray(num)[a:b].sum()) for a, b in eps])
    d = np.array([float(np.asarray(den)[a:b].sum()) for a, b in eps])
    point = n.sum() / d.sum() if d.sum() else float("nan")
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        i = rng.integers(0, len(eps), len(eps))
        if d[i].sum():
            out.append(n[i].sum() / d[i].sum())
    if not out:
        return point, (float("nan"), float("nan"))
    return point, (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def agreement_stats(m3, m4, eps, draws=2000, seed=70):
    """★ THE bit3/bit4 STATISTIC. Agreement, its CHANCE baseline, and the EXCESS, jointly resampled.

    r24 and r26 carry the same sign by construction, so if r26 is LIVE the two bits must agree far
    more often than chance. The chance baseline is computed from the SAME resampled episodes'
    marginals -- p3*p4 + (1-p3)*(1-p4) -- so a bit that is pinned constant gives excess == 0 exactly
    rather than a spurious "high agreement". That degradation is deliberate: a constant bit4 means
    "no sign information about r26", which is precisely what r26-inert looks like.
    """
    keys = ("agree", "chance", "excess")
    if not eps:
        return {k: (float("nan"), (float("nan"), float("nan"))) for k in keys}
    a3 = np.array([float(m3[a:b].sum()) for a, b in eps])
    a4 = np.array([float(m4[a:b].sum()) for a, b in eps])
    ag = np.array([float((m3[a:b] == m4[a:b]).sum()) for a, b in eps])
    nn = np.array([float(b - a) for a, b in eps])

    def _one(idx):
        n = nn[idx].sum()
        p3, p4 = a3[idx].sum() / n, a4[idx].sum() / n
        agree = ag[idx].sum() / n
        chance = p3 * p4 + (1 - p3) * (1 - p4)
        return agree, chance, agree - chance

    base = _one(np.arange(len(eps)))
    rng = np.random.default_rng(seed)
    cols = list(zip(*[_one(rng.integers(0, len(eps), len(eps))) for _ in range(draws)]))
    return {k: (base[j], (float(np.percentile(cols[j], 2.5)), float(np.percentile(cols[j], 97.5))))
            for j, k in enumerate(keys)}


def identify(b4):
    """Which build produced this payload stream? Reported at its real strength."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    illegal = int(np.count_nonzero([(v & PROBE_MASK) not in LEGAL for v in b4]))
    ord_viol = int(np.count_nonzero(((b4 & BIT_R24_HALF) != 0) & ((b4 & BIT_R24_SIGN) == 0)))
    print(f"  VOID (probe field == 0, the cave did not fire) : {void} / {len(b4)}")
    print(f"  ILLEGAL (outside V70's 12 legal payloads)      : {illegal} / {len(b4)}")
    print(f"  ORDER VIOLATION (bit6 = 1 with bit3 = 0)       : {ord_viol} / {len(b4)}")
    if void or illegal or ord_viol:
        print("  🛑 HARD FAIL. A VOID, ILLEGAL or ORDER-VIOLATING frame means the flashed image is")
        print("     not this build, or the cave did not run. bit6 ⇒ bit3 is ARITHMETIC, not a")
        print("     convention: x >= +512 implies x >= 0, proven over all 65,536 patterns at build")
        print("     time. A single violating frame is disqualifying -- this is NOT a warning, and")
        print("     nothing below may be interpreted until all three counters read 0.")
        return False

    n3 = int(np.count_nonzero((b4 & BIT_R24_SIGN) != 0))
    print(f"  bit3 (r24 SIGN -- must be NON-CONSTANT)        : {n3} set / {len(b4) - n3} clear")
    if n3 == 0:
        print("  🛑 bit3 is CONSTANT 0 ⇒ this is V66, V67 or V69, NOT V70.")
        return False
    if n3 == len(b4):
        print("  🛑 bit3 is CONSTANT 1 ⇒ this is V68, NOT V70. (V68 measured 53,991/53,991.)")
        return False
    print("  ✅ bit3 TOGGLES ⇒ V68 (constant 1) and V66/V67/V69 (constant 0) are BOTH excluded")
    print("     ABSOLUTELY -- the discrimination V69's probe could not make in either direction.")
    for name in STRUCTURALLY_DISJOINT:
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    print("  ✅ EXCLUDED ABSOLUTELY: V65 (its ladder forbids bit6 AND bit3 together; V70 emits it)")
    n_b4_b3 = int(np.count_nonzero(((b4 & BIT_R26_SIGN) != 0) & ((b4 & BIT_R24_SIGN) == 0)))
    if n_b4_b3:
        print("  ✅ EXCLUDED: V59/V60/V61/V62/V63 -- their thermometer requires bit4 ⇒ bit3, and this")
        print(f"     route emits bit4=1 with bit3=0 in {n_b4_b3} frames")
    else:
        print("  ⚠ NOT excluded: V59-V63's thermometer (bit4 ⇒ bit3) -- no bit4=1/bit3=0 frame here")
    print("  ⚠ NOT excluded by the value set: V55, V57, V58, V64 -- four-bit probes with INDEPENDENT")
    print("     bits, so their reachable space is all 16 payloads. Six-plus builds back and not")
    print("     plausible mis-flashes; confirm from the .rwd filename if it matters:")
    print(f"     {RWD_NAME}")
    return True


def main(paths):
    print(__doc__)
    d = collect(paths)
    b4, t = d["b4"], d["t"]
    if len(b4) == 0:
        print("🛑 no 0x14A frames on src 1 -- nothing to decode.")
        return 1
    fs = (len(t) - 1) / (t[-1] - t[0])
    print("=" * 102)
    print(f"FRAMES {len(b4)}   span {t[-1] - t[0]:.1f} s   mean rate {fs:.3f} Hz")
    # 🛑 use the MEAN rate + an index lattice, never 1/median(dt): frames are timestamped per log
    # packet, so on some routes 12% of dt exceed 15 ms and p10 is exactly 0 (STATE.md, 2026-08-03).
    print("IDENTIFICATION -- from the PROBE, never from the filename")
    if not identify(b4):
        return 1

    tq, rate = d["tq"], d["rate"]
    v = d.get("v", np.full(len(b4), np.nan))
    lat = np.asarray(d.get("lat", np.zeros(len(b4), bool)), bool)
    sus = np.abs(sustained(tq, fs))
    ratchet_cell = lat & (v <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)

    m5 = (b4 & BIT_STATE10) != 0
    m4 = (b4 & BIT_R26_SIGN) != 0
    m3 = (b4 & BIT_R24_SIGN) != 0
    ones = np.ones(len(b4), float)

    cells = (
        ("WHOLE ROUTE", np.ones(len(b4), bool)),
        ("engaged", lat),
        ("engaged + creep", lat & (v <= CREEP_MAX_MS)),
        ("engaged + creep + hands-off  ⇐ THE RATCHET'S OWN CELL", ratchet_cell),
        ("manual (disengaged)", ~lat),
    )

    print("\n" + "=" * 102)
    print("PER-BIT DUTY AND TOGGLE RATE")
    for bit, name, disp, what in RUNGS:
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
    print("★★ READOUT 1 -- IS r26 LIVE?  THE STATISTIC IS bit3/bit4 AGREEMENT, NOT TWO DUTIES.")
    print("   r24 and r26 take the SAME dtorque and the SAME single polarity read (ld.b -0x6752[gp],")
    print("   r14 @0x3AB78, reused by both lanes), and gp-0x69a4 is an unsigned magnitude at both")
    print("   ends ⇒ THE TWO LANES ALWAYS CARRY THE SAME SIGN, by construction. So bit4 must track")
    print("   bit3 if r26 is live, and can only be pinned if r26 is dead.")
    eps_eng = episodes_of(lat)
    print(f"\n   engaged episodes >= {MIN_SAMPLES} samples: {len(eps_eng)}   "
          f"total {sum(b - a for a, b in eps_eng) / fs:.1f} s")
    if not eps_eng:
        print("   🛑 no engaged episodes long enough -- READOUT 1 cannot be computed on this route.")
    else:
        st = agreement_stats(m3, m4, eps_eng)
        ag, agc = st["agree"]
        ch, chc = st["chance"]
        ex, exc = st["excess"]
        print(f"   agreement  bit3 == bit4 : {ag:7.4f}  [{agc[0]:.4f}, {agc[1]:.4f}]")
        print(f"   chance baseline         : {ch:7.4f}  [{chc[0]:.4f}, {chc[1]:.4f}]   "
              "(from the same resampled episodes' marginals)")
        print(f"   EXCESS over chance      : {ex:+7.4f}  [{exc[0]:+.4f}, {exc[1]:+.4f}]   "
              "⇐ THE DECISION STATISTIC")
        d4, d4c = episode_ratio(eps_eng, m4.astype(float), ones)
        d3, _ = episode_ratio(eps_eng, m3.astype(float), ones)
        print(f"   marginals: bit4 duty {d4:.4f} [{d4c[0]:.4f}, {d4c[1]:.4f}]   bit3 duty {d3:.4f}")
        if d4 > 0.999 or d4 < 0.001:
            print("\n   ⇒ bit4 is PINNED ⇒ **r26 IS INERT** (gp-0x6adc never changes sign). This")
            print("      CONFIRMS the 0xC6564 = 40-zero-bytes record ON-CAR for the first time:")
            print("      a ≈ 0, r24 carries the whole lane, and V67/V68's gate -- which pins r26's")
            print("      arm to 512 against a gain_A LERP of 3072 at creep -- was NOT cutting real")
            print("      damping. The r26 residual carried since V67 can be closed.")
            print("      ⚠ Excess ≈ 0 here is CORRECT and expected, NOT a failed test: a constant")
            print("        bit carries no sign information, which is exactly the inert signature.")
        elif exc[0] > 0:
            print("\n   🛑 bit4 TRACKS bit3 (excess CI clears 0) ⇒ **r26 IS LIVE**, contradicting the")
            print("      standing inert record. `a` is material, and V67/V68's gate HAS been cutting")
            print("      total damping ~6x while engaged. Re-price V67/V68 before the next build.")
        elif exc[1] < 0:
            print("\n   🛑🛑 bit4 ANTI-CORRELATES with bit3 (excess CI entirely below 0). The two lanes")
            print("      are claimed to share one polarity read, so this REFUTES the same-sign")
            print("      structure in the golden model (~line 1193). Correct the model; do not")
            print("      explain this away.")
        else:
            print("\n   ⇒ INCONCLUSIVE: the excess CI straddles 0 and bit4 is not pinned. Report it")
            print("      as inconclusive and say how many more engaged episodes would settle it.")
        print("\n   🛑 THE COST, STATED: V70 measures r26's LIVENESS, not `a`. The matched +512")
        print("      threshold that would have estimated a = gp-0x69a4/1024 did not fit the 68-byte")
        print("      cave, and its PREDICTED reading was 0.000% -- which cannot separate 'inert'")
        print("      from 'live but small'. Magnitude only matters in the live branch, which this")
        print("      settles first.")

    # =================================================================================================
    print("\n" + "=" * 102)
    print("★★ READOUT 2 -- IS THE ECU IN STATE 10?  NON-VACUOUS IN BOTH DIRECTIONS.")
    print(f"   Detector + return-to-centre run under andi 0x{MASK_DETECTOR:03X} = "
          f"{sorted(s for s in range(16) if (1 << s) & MASK_DETECTOR)};  aggregator + residual under "
          f"andi 0x{MASK_AGGREGATOR:03X} = {sorted(s for s in range(16) if (1 << s) & MASK_AGGREGATOR)}.")
    print("   The mask wraps the `jarl` in the caller (FUN_0002214a), so a masked-out state means the")
    print("   function is NEVER INVOKED -- no stack frame, not an early return.")
    print("   🛑 PRE-REGISTERED PREDICTION: bit5 reads LOW. gp-0x6806 tracked latActive in 99.983% of")
    print(f"      150,327 frames, and its producer runs under 0x{MASK_ARBITRATION:03X}, which ALSO")
    print("      excludes state 10 ⇒ a stale flag could not track transitions that closely.")
    for label, sel in cells:
        eps = episodes_of(sel)
        n = int(np.count_nonzero(sel))
        if n < 64 or not eps:
            continue
        p, ci = episode_ratio(eps, m5.astype(float), ones)
        print(f"   {label:<52s} state==10 duty {p:7.4f} [{ci[0]:.4f}, {ci[1]:.4f}]  "
              f"({len(eps)} eps, {n / fs:6.1f} s)")
    d5, d5ci = episode_ratio(eps_eng, m5.astype(float), ones) if eps_eng \
        else (float("nan"), (float("nan"), float("nan")))
    if eps_eng and d5ci[1] < 0.01:
        print("\n   ⇒ STATE 10 IS ESSENTIALLY ABSENT while engaged (CI upper < 1%). The car steered,")
        print("      so the aggregator ran, so the state was in {4,5,10,11} by its own 0xc30 gate;")
        print("      excluding 10 leaves {4,5,11} ⇒ **FUN_00036388 AND FUN_000428d4 DID EXECUTE.**")
        print("      ⇒ ★★ the gp-0x67df detector nulls on V64/V67/V68 (0/14,980 + 0/186,321 +")
        print("         0/53,991) are GENUINE -- five builds of null are VINDICATED, not wasted,")
        print("         and the state-gate explanation for them is REFUTED. Matches the prediction.")
        print("      ⚠ BUT NOT AT FULL STRENGTH: this licenses 'the CALL was made', not 'the")
        print("        detector BODY ran'. FUN_000428d4 has a SECOND, independent entry gate --")
        print("        FUN_00046ea6(5) on bit 5 of gp-0x18d0/gp-0x18d4, a fault/DTC-style bitmask")
        print("        with a 0x8000 sentinel. That bit is OPEN and no V70 reading closes it.")
    elif eps_eng and d5 > 0.05:
        print("\n   🛑 STATE 10 OCCURS MATERIALLY while engaged ⇒ FUN_00036388 and FUN_000428d4 were")
        print("      SKIPPED for that fraction of the drive ⇒ the detector nulls were nulls ON THE")
        print("      GATE, bounding NOTHING about oscillation. That instrument is retired, not")
        print("      merely quiet. 🛑 This CONTRADICTS the pre-registered prediction, which makes it")
        print("      a real surprise worth chasing -- and it also puts gp-0x6806's 99.983% agreement")
        print("      with latActive in question, since its producer excludes state 10 as well.")
    elif eps_eng:
        print("\n   ⇒ state 10 occurs INTERMITTENTLY. Cross the detector nulls against this bit's own")
        print("      time base before quoting either; do not pool.")

    # =================================================================================================
    print("\n" + "=" * 102)
    print("THE RATCHET TEST -- a 6-9 Hz line in a bit's own series, against a NULL computed FIRST")
    print("🛑 Bootstrap over EPISODES, not windows -- window bootstraps shrink CIs by ~sqrt(n) and")
    print("   manufacture significance. Standing instruction, 2026-08-02.")
    rr = [ab for ab in runs_of(ratchet_cell) if ab[1] - ab[0] >= 256]
    print(f"\n  ratchet-cell episodes of >= 2.56 s: {len(rr)}   "
          f"total {sum(b - a for a, b in rr) / fs:.1f} s")
    if not rr:
        print("  🛑 NO EPISODES. This route cannot speak to the ratchet in either direction.")
        print("     The recorded episodes are hands-off + ENGAGED + CREEP with |angle| 9-133 deg.")
        print("     Route 2b failed exactly this test and the operator said so before the data did.")
    else:
        chans = (tq, rate)
        lengths = [b - a for a, b in rr]
        mnull = matched_null(chans, lat & ~ratchet_cell, fs, lengths)
        snull = []
        for a, b in rr:
            m = (a + b) // 2
            for aa, bb in ((a, m), (m, b)):
                for ch in chans:
                    _, p = analog_line(ch[aa:bb], fs)
                    if np.isfinite(p):
                        snull.append(p)
        f_split = float(np.percentile(snull, 95)) if snull else float("nan")
        f_match = float(np.percentile(mnull, 95)) if mnull else float("nan")
        floor = float(np.nanmax([f_split, f_match]))
        print(f"  NULL 1 split-half   (n={len(snull):4d}): 95th {f_split:8.2f}   "
              "⚠ contaminated by its own signal, floors HIGH")
        print(f"  NULL 2 matched OUTSIDE the cell (n={len(mnull):4d}): 95th {f_match:8.2f}   "
              "⇐ the clean negative control")
        print(f"  ⇒ FLOOR = max(NULL1, NULL2) = {floor:.2f}  (conservative for a DETECTION claim)")

        an_hits, an_pks = 0, []
        for a, b in rr:
            p_tq, _ = analog_line(tq[a:b], fs)
            best = max(analog_line(ch[a:b], fs)[1] for ch in chans)
            if np.isfinite(best) and best > floor:
                an_hits += 1
                an_pks.append(p_tq)
        med_an = float(np.median(an_pks)) if an_pks else float("nan")
        print(f"\n  ★ SYMPTOM PRESENT? analog bar-torque / angle-rate 6-9 Hz line above the floor in "
              f"{an_hits} / {len(rr)} episodes, median {med_an:.2f} Hz (recorded {RATCHET_F0} Hz)")
        if not an_hits:
            print("    🛑 NO ANALOG LINE ⇒ the ratchet did not occur in this route's cell. Every")
            print("       per-bit null below is then a bound on nothing. Do not interpret it.")
        else:
            n_fr = sum(b - a for a, b in rr)
            print(f"    ⇒ the symptom IS present over {n_fr} frames / {n_fr / fs:.2f} s. The per-bit")
            print("       results below are REAL.")
        print(f"\n  {'bit':<18s} {'episodes with a 6-9 Hz line above the null':>44s}  "
              f"{'median pk Hz':>13s}")
        for bit, name, _disp, _what in RUNGS:
            hits, pks = 0, []
            for a, b in rr:
                pk, p = ratchet_line(((b4 & bit) != 0)[a:b], fs)
                if np.isfinite(p) and p > floor:
                    hits += 1
                    pks.append(pk)
            med = float(np.median(pks)) if pks else float("nan")
            flag = "  ⇐ DETECTION" if hits and abs(med - RATCHET_F0) < 1.0 else ""
            print(f"  {name:<18s} {hits:>3d} / {len(rr):<40d}  {med:13.2f}{flag}")
        print("  🛑 A bit that never toggles scores NaN, which cannot exceed any floor -- so '0 / N'")
        print("     on a CONSTANT bit is a statement about the bit, not a failed test.")
        print("  ★ bit3 IS THE SENSITIVE ONE. It is amplitude-independent, so it carries the line")
        print("     even when the lane never reaches +512 and bit6 stays flat. If bit3 detects and")
        print("     bit6 does not, the ratchet is REAL and SMALL -- which no prior probe could say.")

    print("\n" + "=" * 102)
    print("FLIGHT SAFETY")
    st = Counter(int(x) & 0x07 for x in b4)
    print(f"  STEER_SENSOR_STATUS (payload bits 2:0) histogram: {dict(st)}")
    print("  🛑 ST == 4 and ST == 3 must be counted from the RAW 0x18F stream as well as the grid --")
    print("     V68 confirmed flight-clean two ways and that is the standard. See the handoff.")
    print("  ⚠ V70's control path is V69's TOPOLOGY at HALF the dose -- gate on the dead cell, arm")
    print("     stock, mode-10 gain_B rec0/rec1 at 2x. V69 flew that topology at 4x flight-clean and")
    print("     every V70 operating point is INSIDE the flown bracket [stock 1.00x, V62/V65 2.00x],")
    print("     so a flight-safety surprise here would point at the CAVE, not the calibration.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
