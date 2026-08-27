#!/usr/bin/env python3
"""probe/decode_v68_probe.py -- read V68's rate-axis probe out of an rlog.

V68 IS V67'S CONTROL PATH, BYTE-IDENTICAL, WITH A RE-AIMED PROBE. It changes nothing that touches
torque: the only bytes that differ from V67 anywhere in [0x13000,0x100000) are the cave span and the
MAIN CRC trailer, and the CAL CRC is UNCHANGED -- which is itself the proof.

    0x3AA96  = 0xFB     V67's repoint, carried:  ld.bu -0x6806[gp],r15 @0x3AA94
    0xC6446  = 5244     V67's LKAS arm, carried
    0x3AB70 / 0x3AB76 / 0x3AC20  all STOCK `sar 0xa`
    => every ride impression on V68 is a ride impression on V67.

V68 packs FIVE bits into CAN 330 (0x14A) byte4 at ~100 Hz:

    bit 7 = 1                    LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6806 != 0       *** THE GATE *** -- carried from V67 unchanged   (disp 0x97FA)
    bit 5 = gp-0x67df != 0       *** FSM LEFT NEUTRAL *** |gp-0x6c2c| crossed +-T (disp 0x9821 ODD)
    bit 4 = gp-0x671a >= 1       *** THE ABOVE-50-Hz DETECTOR *** lowest rung     (disp 0x98E6)
    bit 3 = 1                    THE V68 BUILD-CLASS MARKER (constant)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

🛑🛑 bit5 AND bit4 ARE TWO ORDERED STAGES OF ONE 1 kHz DETECTOR
-------------------------------------------------------------
    bit5  gp-0x67df != 0   the FSM has LEFT NEUTRAL: |gp-0x6c2c| crossed +-T = 12800.
                           *** NO REVERSAL REQUIRED. ***
    bit4  gp-0x671a >= 1   ...and then REVERSED at least once.

gp-0x67df fires on events too BRIEF or too ONE-SIDED to produce a reversal -- precisely the
marginal, intermittent case the operator describes, and the case bit4 alone cannot see. Both cells
hold >= 50 ms (the 0xC64DD = 50-tick dwell), so both are reliably catchable by a 100 Hz probe.
⇒ EXPECT bit4 => bit5 on the wire. **bit5 set with bit4 clear is the new information**: a
threshold crossing that never became a reversal.
⚠ That is an EXPECTATION, not an encoding guarantee -- the two cells are sampled at the same TX
tick but cleared by different rules, so bit4 && !bit5 can occur at a clear boundary. This tool
REPORTS its rate rather than asserting it away.

🛑 gp-0x67ac IS NOT PROBED. IT IS PROVABLY 0 ON THIS BUILD.
-----------------------------------------------------------
An earlier revision aimed bit5 at gp-0x67ac, whose `== 1` makes FUN_0003aa2c skip the r24/r26
aggregate add -- a lane dropout that would have invalidated the highway null. It cannot happen
here. The 11-slot OR-latch feeding it can only be set for a per-slot role of 6 or 7, and the static
role table at tp+0x5124 = 0xC4124 reads [0,0,5,0,5,5,0,0,0,5,0]. No slot is ever 6 or 7.
⇒ the rate lanes CANNOT silently drop out, so the highway null was NOT reading a disconnected
lane. That question is CLOSED without spending a rung -- probing a proven zero is exactly the error
V68's original bit4 made.
⚠ It rests on CALIBRATION BYTES, not structure. The builder re-reads 0xC4124 every build and
STOPS if a 6 or 7 ever appears. Open follow-up: gp-0x61a0's writer and gp-0x61e8's identity.

★★ bit4 IS THE ONLY ABOVE-50-Hz INSTRUMENT THIS KIT HAS
------------------------------------------------------------
gp-0x6c2c's cascade is a BAND-PASS PEAKING NEAR 61 Hz, not a low-pass. Gain relative to 21.09 Hz:

    1 Hz 0.05x  ·  45 Hz 1.54x  ·  61 Hz 1.61x (max)  ·  100 Hz 1.43x  ·  200 Hz 0.94x

so the amplitude needed to TRIP the detector FALLS above 50 Hz:

    21.3 Hz 1683  ·  45 Hz 1104  ·  60 Hz 1056  ·  100 Hz 1186  ·  150 Hz 1478  ·  200 Hz 1735 counts

Sanity-checked against the golden model's own sizing: amplitude 1683 -> 12804 (trips T = 12800),
1682 -> 12797 (does not). ⇒ Honda's own 1 kHz detector is MORE sensitive exactly where CAN
(Nyquist 50.00 Hz) and the comma IMU (50.51 Hz) are both blind.
⚠ V67's 0.000% does NOT speak to this: V67's rung tested `>= 5`, the CEIL (cal 0xC64FA = 5). This
one tests `>= 1`, the lowest rung of the same 0..5 counter. A null at 5 does not imply a null at 1.

🛑 HOW TO READ bit4 -- DUTY IS NOT OCCUPANCY
------------------------------------------------
gp-0x671a counts REVERSALS of gp-0x6c2c past +-T (cal 0xC620A = 12800), via raw counter gp-0x357c
and FSM state gp-0x67df.

  * SUB-CEIL (1..4): cleared by the 50-tick dwell (cal 0xC64DD = 50) => visible ~50 ms => about
    5 frames at 100 Hz. ⚠ BRIEF EVENTS ARE UNDER-COUNTED; an isolated reversal may be missed.
  * AT CEIL (5): the output is RE-PINNED every tick. Release needs 5000 ticks (cal 0xC6270 = 5.0 s)
    with gp-0x6a5e >= 640 AND no reversals. gp-0x6a5e is voted VEHICLE SPEED (voter FUN_00041eec,
    settled 2026-07-29) and 640 counts is ~10 km/h. => BELOW ~10 km/h THE LATCH NEVER RELEASES and
    duty SATURATES; at road speed it releases 5.0 s after the last reversal.

⇒ bit4 IS A HOLD-TIME STATISTIC, NOT AN EVENT RATE. Never quote its duty as a detector rate.
🛑 AND IT IS A DETECTOR, NOT A SPECTROMETER: it reports THAT a reversal past +-T happened. It
gives NEITHER amplitude NOR frequency. Any frequency attribution must come from conditioning on
something else (speed, maneuver, the gate) -- never from bit4 alone.
⚠ The 100 Hz sampling barrier is UNCHANGED. bit4's own time series is aliased like everything
else; what is new is that the QUANTITY it reports was computed at 1 kHz inside the ECU. bit4 carries
above-50-Hz INFORMATION, not an above-50-Hz WAVEFORM.

★★ V68 CARRIES A BUILD-CLASS MARKER -- AND HERE IS EXACTLY HOW STRONG IT IS
----------------------------------------------------------------------------
🛑 The problem this addresses, in the kit's own words: a constant `0x87` has meant FOUR different
things across builds (V64's detector null, V65's neutral ladder bucket, V66's all-gates-zero, V67's
gate-never-true), and V66/V67 are MUTUALLY INSEPARABLE by payload -- `route_build_registry.identify`
asserts that as a property of the pair. Reading one build's log with another build's decoder has
already cost this kit a session.

V68 folds bit3 into the liveness immediate (`movea 0x88,r0,r7` instead of `movea 0x80,r0,r7` --
same instruction, same four bytes, different immediate, zero extra cave bytes), so:

    EVERY legal V68 frame has BOTH bit7 AND bit3 set, and V68 NEVER emits 0x87.

🛑 THE MARKER IS NOT A PROOF, AND THE DIFFERENCE MATTERS. Two tiers, both machine-checked in
`_self_check()` below rather than asserted in prose:

  TIER 1 -- STRUCTURALLY DISJOINT. These builds arithmetically CANNOT emit any byte V68 emits:
      V53 (no probe bits: 0x07 only) · V54 (bit7 never set: 0x0F only) ·
      V66 and V67 (both assert bit3 is NEVER set by their caves).
    For these the exclusion is absolute.

  TIER 2 -- EXCLUDED ONLY BY THEIR RECORDED ROUTES. The overlaps are DERIVED in `_self_check()`
    from the builds' own invariants, not typed, and against V59/V62 the marker is WEAK:
      V59/V62 thermometer space ∩ V68 = {0x8F, 0x9F, 0xBF, 0xCF, 0xDF, 0xFF}  -- SIX of eight
      V65 ladder space          ∩ V68 = {0x9F}                                -- one of eight
    So V65 is nearly excluded on structure; **V59/V62 are not excluded on structure at all.** They
    are excluded because both of their recorded routes contain 0x87, which V68 cannot emit. A
    hypothetical V59 log in which the boost index never dropped below 512 would be INDISTINGUISHABLE
    from V68 by payload. Do not upgrade this claim.
    ⇒ this tool therefore ALSO runs the V59/V62 thermometer-nesting test and the V65 ladder test and
      reports which the log satisfies, plus one SEMANTIC (not structural) argument: every V68 byte
      with bit6 set requires, under V59/V62 semantics, their FAULT SENTINEL to be set -- and that
      read 0.000% on routes 2c and 37.

⚠ AND THE HARD LIMIT: the marker excludes PRIOR builds. It cannot exclude a FUTURE one, and it is
not a substitute for knowing what was flashed. The .rwd filename remains the primary evidence:
    39990-TVA,A160-V68-LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-fsm67df-detector671a-can330byte4-0x13000-0x100000.rwd

🛑 WHAT V68 CANNOT DO: IT DOES NOT BREAK THE ALIASING BARRIER
--------------------------------------------------------------
CAN samples at ~100.5 Hz (Nyquist ~50.2) and the comma IMU at 99.9-100.5 Hz. Both instruments are
blind above ~50 Hz, and grind #2's "44.9 Hz" is itself an alias -- 44.9 and ~55.6 Hz are the same
observation. V68 does not change that. A sticky/latching rung was designed and REJECTED on FOUR
independent grounds, all recorded in builds/v50_v79/build_v68_tva.py's docstring:

  0. 🛑🛑 THE HOOK RUNS AT 100 Hz, NOT 1 kHz -- THE PREMISE IS FALSE, and this one is fatal alone.
     Traced end to end: 0x55C0E is in FUN_00055a98 (the 0x14A builder); its ONLY pointer image-wide
     is 0xB72D4 = index 10 of PTR_FUN_000b72ac; message-10's pending bit is set only by
     FUN_0001eaa6(0xa) @0x5560C, whose sole caller is FUN_00022ca0 @0x234C4 = TCB idx-4 = task 5 =
     c%10==4 = 100 Hz. A latch at this hook CANNOT sample faster than the frame it is written into,
     so it degenerates to a plain sample at any budget and with any RAM cell.
     ⇒ NO PROBE ON THIS HOOK CAN EVER BREAK THE ALIASING BARRIER. Doing so needs a SECOND hook
       inside task 1 -- new code on the 1 kHz path, under the DTC-0x18 cadence watchdog's timing
       budget. That is a different and much larger decision.
     ⚠ V67's docstring calls this "the 1 kHz TX path". THAT IS WRONG.
  1. BUDGET -- 20 bytes are free after bit6 and bit5; the rung needs 22 before any latch machinery
     and 42 with it (2.1x). The cave must not grow: caves are this kit's only bricking class.
  2. SELECTIVITY -- gp-0x4f62 is read `ld.h` (SIGNED halfword, confirmed two ways at 6 sites) and a
     scalar threshold on |it| is an amplitude detector, not a band detector. Its low-frequency
     content already measures 123-839 counts, so any threshold above the driver fires exactly during
     large driver inputs -- which is also when grind #2 occurs. Confounded by construction.
  3. NO CLEAR EVENT -- CONFIRMED from the code, not inferred. gp-0x1514 has exactly EIGHT accesses
     image-wide and none writes bits 7:3: the WORD read-modify-write at 0x2194A/0x21964 ANDs with
     0xff0000ff and ORs a term whose low byte is zero, so our byte returns BIT-IDENTICAL; the three
     pairs at 0x55AAC/0x55AD4/0x55AF4 mask 0xFB/0xFD/0xFE and touch only bits 2:0. The
     block-copy / register-indirect class is clean too. A latch would pin ON forever.

Do not read any bit here as evidence about content above ~50 Hz.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all established the hard way:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes
     while lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is unmeasurable.
  4. Statistics are computed PER CONTIGUOUS RUN and pooled -- never over a concatenated subset,
     which manufactures a transition at every join (V58's retracted 25 Hz coherence).

Usage:  python probe/decode_v68_probe.py RLOG [RLOG ...]
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

# 🛑 WINDOWS REDIRECT FIX (same as probe/decode_v67_gate.py). cp1252 is chosen for a redirected stdout on
# this machine and the first `print(__doc__)` raises UnicodeEncodeError on the 🛑/★/⚠ glyphs, so
# `> out.txt` crashed before emitting a line. Set here as well as in the imported module, because
# either file can be the __main__ one.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parents[1]))
# ⚠ The NUMERIC MACHINERY is shared with V67's decoder on purpose -- collect/sustained/gate_stats
# are instrument code, not semantics, and two copies would drift. Everything V68-SPECIFIC (the bit
# map, the identification, the verdict) is defined here and nowhere else.
from decode_v67_gate import (collect, gate_stats, print_gate_row, sustained,   # noqa: E402
                             KILL_LO_HZ, KILL_HI_HZ, GATE_TRACKS_MIN,
                             V57_BASELINE, V57_AGREEMENT_MIN)

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v68_tva.assert_decoder_matches() fails the BUILD if
# this string is not byte-for-byte the cave in the built artifact. V66's decoder header was stale
# for one revision and claimed bit4 = gp-0x683c when the image read gp-0x67fe; this is the fix for
# that class of error. Do not edit by hand -- rebuild and copy.
CAVE_HEX = "203e88008437fb976132b605273e4000a43721986132b605273e20008437e7986132b605273e10008437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e8800  movea 0x88,r0,r7        bit7 LIVENESS + bit3 BUILD-CLASS MARKER
#   0xC4B38  8437fb97  ld.bu -0x6806[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e4000 movea 0x40
#   0xC4B44  a4372198  ld.bu -0x67df[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e2000 movea 0x20
#                                              *** ODD disp 0x9821 -> opcode 0x3D, hw1 a437 ***
#   0xC4B50  8437e798  ld.bu -0x671a[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e1000 movea 0x10
#   0xC4B5C  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B66  4437ecea  st.b  r6,-0x1514[gp]     THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B6E  2436e8ea  movea -0x1518,gp,r6     the displaced hook instruction
#   0xC4B72  7f00      jmp [lp]                -> 0x55C12
# ⚠ All three probed cells have EVEN displacements on this revision (0x6806 -> 0x97FB is odd-valued
# selector; 0x671a -> 0x98E6 is EVEN -> opcode 0x3C, hw1 8437; but gp-0x67df -> 0x9821 is
# ODD -> opcode 0x3D, hw1 a437. `ld.bu` hides displacement bit 0 in the OPCODE FIELD, so
# assuming one parity addresses the NEIGHBOURING cell with every other field perfect.
# load's opcode field is 0x3C. The previous revision probed gp-0x671d, whose 0x98E3 is ODD and reads
# 0x3D -- the hw1-bit-5 trap. If you see 0x3D on this build, the cave is not the one documented here.
# ⚠ 60 of the 68 proven cave bytes are used. 8 spare -- still not enough for a fourth rung (12 min).

BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_RATE = 0x40, 0x20, 0x10
BIT_CLASS = 0x08              # *** CONSTANT 1 on V68. The build-class marker. ***
PROBE_MASK = 0xF8
CONSTANT_BITS = BIT_LIVE | BIT_CLASS      # 0x88 -- both must be set on EVERY legal V68 frame

RATE_BREAKPOINT = 400         # xs[1] in every mode-10 gain_B record
RATE_FOLD = 13001             # 0x3AAC8: at or above this the LERP key folds to 0 -> the flat point
RATE_COUNTS_PER_DEGS = 16384 / 3477       # cal 0xC613A = 1159; 400 counts = 84.9 deg/s
BUS_SCALE = 1.697754          # bus counts per gp-0x6ac0 count -- UNUSED on this revision (no rung
                              # probes gp-0x6ac0); kept because studies/sessions/r47/r47_rate_axis.py imports it.

ARM_VALUE = 5244              # cal 0xC6446 under V67 and V68
ARM_MASK_VALUE = 1024         # cal 0xC6442, taken when bit5 is set -- BELOW the stock creep LERP
LERP_FLAT = 2704              # the mode-10 LERP at 7.2 km/h anywhere below the breakpoint
LERP_AT_603 = 2622            # ...and at 603 counts (= 128 deg/s), which is what 5244 was derived from
ARM_FOR_2X_IF_FLAT = 5408     # 2 x LERP_FLAT -- the arm V67 would need if bit4 reads ~0%

# ---- bit4: Honda's 1 kHz oscillation detector ---------------------------------------------------
DETECT_T = 12800              # cal 0xC620A -- the +-T that gp-0x6c2c must reverse past
DETECT_CEIL = 5               # cal 0xC64FA -- the counter's ceiling
DETECT_DWELL_TICKS = 50       # cal 0xC64DD -- SUB-CEIL clear dwell, 50 ms at 1 kHz => ~5 frames
DETECT_HOLD_TICKS = 5000      # cal 0xC6270 -- AT-CEIL release, 5.0 s at 1 kHz
DETECT_RELEASE_SPEED = 640    # cal 0xC62DE on gp-0x6a5e = voted VEHICLE SPEED => ~10 km/h
SPEED_COUNTS_PER_KMH = 64.0625
# 🛑 The band-pass that makes bit4 worth reading: gp-0x6c2c's cascade PEAKS near 61 Hz, so the trip
# AMPLITUDE falls above 50 Hz -- where CAN (Nyquist 50.00) and the comma IMU (50.51) are both blind.
DETECT_TRIP_AMPLITUDE = {21.3: 1683, 45: 1104, 60: 1056, 100: 1186, 150: 1478, 200: 1735}
DETECT_BANDPASS_GAIN = {1: 0.05, 45: 1.54, 61: 1.61, 100: 1.43, 200: 0.94}   # relative to 21.09 Hz

# (bit, short name, gp cell, test text, what it decides)
GATES = (
    (BIT_GATE, "bit6 gp-0x6806", 0x6806, "!= 0",
     "*** THE GATE *** -- V67/V68's arm is taken here and nowhere else"),
    (BIT_MASK, "bit5 gp-0x67df", 0x67df, "!= 0",
     "*** FSM LEFT NEUTRAL *** -- |gp-0x6c2c| crossed +-T. NO reversal required; the stage BELOW bit4"),
    (BIT_RATE, "bit4 gp-0x671a", 0x671a, ">= 1",
     "*** ABOVE-50-Hz DETECTOR *** -- Honda's 1 kHz osc counter, lowest rung. HOLD TIME, not rate"),
)

LEGAL = {CONSTANT_BITS | a | b | c
         for a in (0, BIT_GATE) for b in (0, BIT_MASK) for c in (0, BIT_RATE)}

# 🛑 ONE LINE, deliberately. The builder asserts this exact basename appears in this file; splitting
# it across a string concatenation makes the substring vanish and the check silently harder to pass.
RWD_NAME = "39990-TVA,A160-V68-LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-fsm67df-detector671a-can330byte4-0x13000-0x100000.rwd"  # noqa: E501
IMAGE_SHA = "PENDING"
RWD_SHA = "PENDING"

ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

# TIER 1 -- builds whose ENTIRE reachable payload space is disjoint from V68's. Absolute exclusion.
#   V53 emits only 0x07; V54 only 0x0F (bit7 clear); V66 and V67 both ASSERT that bit3 is never set
#   by their caves, so their whole 8-payload space has bit3 clear.
STRUCTURALLY_DISJOINT = {
    "V53": {0x07},
    "V54": {0x0F},
    "V66/V67 (bit3 never set -- asserted by both builds)":
        {0x87 | a | b | c for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)},
}
# TIER 2 -- builds excluded only because their RECORDED routes contain a byte V68 cannot emit.
#   ⚠ V59/V62 CAN reach 0x8F/0x9F/0xBF and V65 can reach 0x97. The exclusion is empirical.
RECORDED_ROUTES = {
    "V59 (route 2c)": {0xBF, 0x8F, 0x9F, 0x87},
    "V62 (route 37)": {0x87, 0x8F, 0x9F, 0xBF},
    "V64 (route 35)": {0x87},
    "V65 (routes 3a/3b)": {0x87, 0x97, 0xA7},
    "V66/V67 (route 47)": {0x87, 0xC7},
}


def thermometer_ok(vals):
    """V59/V62's one-sided thermometer: bit5 => bit4 => bit3. True if every value obeys it."""
    return all((not (v >> 5 & 1) or (v >> 4 & 1)) and (not (v >> 4 & 1) or (v >> 3 & 1))
               for v in vals)


def ladder_ok(vals):
    """V65's saturation ladder: bit6 => bit5, bit3 => bit4, never both sides at once."""
    return all((not (v >> 6 & 1) or (v >> 5 & 1)) and (not (v >> 3 & 1) or (v >> 4 & 1))
               and not (((v >> 5) & 3) and ((v >> 3) & 3)) for v in vals)


def _self_check():
    """The build-class claim, as an executable assertion rather than a paragraph.

    🛑 It asserts the claim AT ITS REAL STRENGTH, in two tiers. An earlier draft of this file
    claimed "no prior build can produce that", which is FALSE -- V59's thermometer reaches three of
    V68's eight bytes. The check below would have failed it, and did.
    """
    assert len(LEGAL) == 8, f"{len(LEGAL)} legal payloads, expected 8"
    assert all(b & CONSTANT_BITS == CONSTANT_BITS for b in LEGAL), \
        "a legal payload is missing bit7 or bit3"
    assert CONSTANT_BITS == 0x88 and 0x87 not in ON_WIRE, "V68 must never emit 0x87"
    # TIER 1: absolute disjointness.
    for name, space in STRUCTURALLY_DISJOINT.items():
        clash = ON_WIRE & space
        assert not clash, \
            f"V68 shares payload(s) {sorted(hex(b) for b in clash)} with {name}, which was claimed " \
            "to be STRUCTURALLY disjoint -- demote it to the empirical tier or fix the marker"
    # TIER 2: every recorded route must contain at least one byte V68 cannot emit, so that reading
    # that route with THIS tool trips the refusal rather than producing a confident wrong verdict.
    for name, seen in RECORDED_ROUTES.items():
        assert not (seen <= ON_WIRE), \
            f"{name}'s recorded payload set is a SUBSET of V68's -- this tool would silently " \
            "interpret that route as V68. The marker does not separate them."
    # ...and the honest converse, DERIVED from each build's own invariants rather than typed, so a
    # future edit cannot quietly upgrade the claim to "structurally unique" without failing here.
    space = [b for b in range(0x80, 0x100) if b & 0x07 == 0x07]
    v59_space = {b for b in space if thermometer_ok([b])}
    v65_space = {b for b in space if ladder_ok([b])}
    assert ON_WIRE & v59_space == {0x8F, 0x9F, 0xBF, 0xCF, 0xDF, 0xFF}, \
        f"the V59/V62 thermometer overlap is now {sorted(hex(b) for b in ON_WIRE & v59_space)} -- " \
        "the docstring's TIER 2 numbers are stale"
    assert len(ON_WIRE & v59_space) == 6, \
        "V59/V62 overlap V68 in 6 of 8 payloads. The marker does NOT separate them structurally."
    assert ON_WIRE & v65_space == {0x9F}, \
        f"the V65 ladder overlap is now {sorted(hex(b) for b in ON_WIRE & v65_space)}"
    # the ONLY thing separating V59/V62 from V68 is that their recorded routes contain 0x87
    assert 0x87 in RECORDED_ROUTES["V59 (route 2c)"] and 0x87 in RECORDED_ROUTES["V62 (route 37)"], \
        "V59/V62's recorded routes no longer contain 0x87 -- their exclusion rested on nothing else"
    return True


_self_check()


def print_bit4_caveat(indent="   "):
    """🛑 DUTY IS NOT OCCUPANCY. Print this beside every bit4 number, without exception."""
    rel = DETECT_RELEASE_SPEED / SPEED_COUNTS_PER_KMH
    print(f"{indent}🛑 bit4 IS A HOLD-TIME STATISTIC, NOT AN EVENT RATE.")
    print(f"{indent}  gp-0x671a counts REVERSALS of gp-0x6c2c past +/-{DETECT_T} (cal 0xC620A), via")
    print(f"{indent}  raw counter gp-0x357c and FSM state gp-0x67df. bit4 asks only 'is it >= 1'.")
    print(f"{indent}  SUB-CEIL (1..{DETECT_CEIL - 1}): cleared by a {DETECT_DWELL_TICKS}-tick dwell "
          f"(cal 0xC64DD) => visible ~{DETECT_DWELL_TICKS} ms")
    print(f"{indent}     => only ~{DETECT_DWELL_TICKS // 10} frames at 100 Hz. BRIEF EVENTS ARE "
          "UNDER-COUNTED; a single")
    print(f"{indent}     reversal may be missed entirely.")
    print(f"{indent}  AT CEIL ({DETECT_CEIL}, cal 0xC64FA): re-pinned every tick. Release needs "
          f"{DETECT_HOLD_TICKS} ticks")
    print(f"{indent}     (cal 0xC6270 = {DETECT_HOLD_TICKS / 1000:.1f} s) with gp-0x6a5e >= "
          f"{DETECT_RELEASE_SPEED} AND no reversals. gp-0x6a5e is")
    print(f"{indent}     voted VEHICLE SPEED (FUN_00041eec, settled 2026-07-29) => ~{rel:.0f} km/h.")
    print(f"{indent}     => BELOW ~{rel:.0f} km/h THE LATCH NEVER RELEASES and duty SATURATES; at")
    print(f"{indent}     road speed it releases {DETECT_HOLD_TICKS / 1000:.1f} s after the last "
          "reversal.")
    print(f"{indent}🛑 IT IS A DETECTOR, NOT A SPECTROMETER: neither amplitude nor frequency. Any")
    print(f"{indent}  frequency attribution must come from conditioning on something else.")
    print(f"{indent}★ Why it is worth reading: gp-0x6c2c's cascade is a BAND-PASS peaking near 61 Hz")
    print(f"{indent}  ({', '.join(f'{k} Hz {v}x' for k, v in DETECT_BANDPASS_GAIN.items())} rel. "
          "21.09 Hz), so the trip")
    print(f"{indent}  AMPLITUDE FALLS above 50 Hz: "
          + ", ".join(f"{k} Hz {v}" for k, v in DETECT_TRIP_AMPLITUDE.items()) + " counts.")
    print(f"{indent}  It is the ONLY above-50-Hz instrument here -- but it carries above-50-Hz")
    print(f"{indent}  INFORMATION, not an above-50-Hz WAVEFORM: the field is still sampled at 100 Hz.")


def print_bit5_caveat(indent="   "):
    """bit5 is the detector's FIRST stage: crossed +-T, no reversal required."""
    print(f"{indent}★ bit5 = gp-0x67df != 0 -- the detector FSM has LEFT NEUTRAL, i.e."
          f" |gp-0x6c2c| crossed")
    print(f"{indent}  +/-{DETECT_T} (cal 0xC620A). *** NO REVERSAL REQUIRED. *** bit4 requires one.")
    print(f"{indent}  ⇒ bit5 SET with bit4 CLEAR = a crossing that never became a reversal --")
    print(f"{indent}    the brief or one-sided event bit4 alone cannot see. That is what this rung buys.")
    print(f"{indent}  ⚠ Same band-pass as bit4, so it inherits the above-50-Hz sensitivity AND the")
    print(f"{indent}    same limits: no amplitude, no frequency, and it is a HOLD (>= 50 ms), not a count.")
    print(f"{indent}  ⚠ bit4 => bit5 is EXPECTED, not guaranteed: different clear rules, so a clear")
    print(f"{indent}    boundary can show bit4 && !bit5. Its rate is reported below, not asserted away.")


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    nyq = fs / 2.0
    field = (d["b4"] >> 3) & 0x1F
    dur = d["t"][-1] - d["t"][0]
    print(f"\n{'=' * 100}\n{tag}   {n} frames  {dur:.1f}s  fs={fs:.2f} Hz  (Nyquist {nyq:.1f} Hz)")

    # ---- 0. LIVENESS -- a HARD STOP ---------------------------------------------------------------
    void = field == 0
    print("\n-- 0. LIVENESS (HARD STOP) --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {int(void.sum())} / {n}  ({100 * void.mean():.4f}%)")
    print(f"   bit7 set                       : {int((d['b4'] & BIT_LIVE != 0).sum())} / {n}")
    print(f"   bit3 set (V68 CLASS MARKER)    : {int((d['b4'] & BIT_CLASS != 0).sum())} / {n}")
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"].tolist()).most_common(10)))
    if void.any():
        first = d["t"][void][0] - d["t"][0]
        print(f"\n   *** STOP. The cave failed to fire on {int(void.sum())} frame(s), first at "
              f"t+{first:.2f}s.")
        print("       Bits 7 AND 3 are hard-wired by a single `movea 0x88,r0,r7` that executes")
        print("       before any branch in the cave, so field == 0 cannot be a physical reading --")
        print("       the hook did not run, or the frame was not produced by V68 at all.")
        print(f"       => No statistic below is trustworthy. Confirm the flashed .rwd:\n"
              f"          {RWD_NAME}")
        return

    g6806 = (d["b4"] & BIT_GATE) != 0
    g671d = (d["b4"] & BIT_MASK) != 0
    g6ac0 = (d["b4"] & BIT_RATE) != 0
    marker = (d["b4"] & BIT_CLASS) != 0

    # ---- 1. WHICH BUILD IS THIS? -- run BEFORE any verdict ----------------------------------------
    print("\n-- 1. BUILD IDENTIFICATION -- ★★ V68 IS SEPARABLE, AND THIS IS THE CHECK --")
    illegal = np.array([(b & PROBE_MASK) not in LEGAL for b in d["b4"]])
    vals = sorted(set(d["b4"].tolist()))
    print(f"   bit7 AND bit3 both set (the V68 signature) : {int((marker & (d['b4'] & BIT_LIVE != 0)).sum()):6d}"
          f" / {n}  ({100 * marker.mean():.4f}%)")
    print(f"   payload not one of the 8 legal V68 bytes   : {int(illegal.sum()):6d} / {n} "
          f"({100 * illegal.mean():.4f}%)")
    print(f"   byte4 values seen: {[hex(v) for v in vals]}")

    # 🛑 THE REFUSAL. This is the V64 lesson, made mechanical.
    if illegal.any() or not marker.all():
        print("\n   *** STOP. THIS LOG WAS NOT PRODUCED BY V68 -- NO VERDICT IS COMPUTED. ***")
        print("       Every V68 frame carries bit7 AND bit3, and only eight payloads are reachable.")
        print("       The bytes above do not satisfy that. Matching against the builds on record:")
        seen = set(vals)
        for name, payloads in sorted(RECORDED_ROUTES.items()):
            if seen <= payloads:
                print(f"         -> consistent with {name} (recorded payload set)")
        for name, space in sorted(STRUCTURALLY_DISJOINT.items()):
            if seen <= space:
                print(f"         -> inside {name}'s reachable payload space")
        if thermometer_ok(seen):
            print("         -> the V59/V62 thermometer nesting HOLDS on every value")
        if ladder_ok(seen):
            print("         -> every V65 ladder invariant HOLDS on every value")
        print(f"       Expected file on the car: {RWD_NAME}")
        print(f"         image SHA256 {IMAGE_SHA}")
        print(f"         rwd   SHA256 {RWD_SHA}")
        return

    # 🛑 THE FROZEN-CONSTANT REFUSAL -- GATED ON THE PROBE HAVING BEEN EXERCISED.
    # A single repeated payload is uninterpretable EVEN when structurally legal; that is exactly how
    # V64's null was misread for a session. BUT an ungated version of this test fires on every
    # parked / never-engaged SEGMENT (it did so on r47 s24 and s25 in V67's decoder), where a single
    # value is the CORRECT reading because bit6 could not move. False alarms are how a real one gets
    # ignored, so the hard refusal requires the log to actually change engagement state.
    _eng = d["sca"] == 1
    exercised = bool(_eng.any() and (~_eng).any())
    if len(vals) == 1 and exercised:
        v = vals[0]
        print(f"\n   *** STOP. byte4 IS A FROZEN CONSTANT 0x{v:02X} across all {n} frames, AND this")
        print("       log CHANGES engagement state -- so bit6 had the opportunity to move and did")
        print("       not. Zero variance in a field carrying three INDEPENDENT live signals is not")
        print("       a measurement, it is a symptom. Under V64 exactly this pattern was read as a")
        print("       physical null for a whole session before the probe was found to be unarmed.")
        print("       At minimum one of the following is true, and this tool will not choose:")
        print("         - a rung's cell is not what the build believes it is;")
        print("         - the cave is not running the code this decoder describes;")
        print("         - the flashed image is not V68 despite the payload being legal for it.")
        print("       No duty, rate or spectrum below would mean anything. RE-DRIVE with the log")
        print("       started BEFORE the first engagement, and confirm the .rwd:")
        print(f"         {RWD_NAME}")
        return
    if len(vals) == 1:
        v = vals[0]
        print(f"\n   -- byte4 is single-valued (0x{v:02X}) over all {n} frames, but this log NEVER")
        print("      CHANGES engagement state, so bit6 had no opportunity to move. That is an")
        print("      UNEXERCISED probe, NOT a frozen one, and it is the expected reading for a")
        print("      parked or never-engaged segment. No ambiguity is claimed and the bit4 sections")
        print("      below are still valid -- bit4 does not depend on engagement. Pool with an")
        print("      engaged segment before reading section 4.")
    print("   => the payload is V68's and it VARIES. Exclusions, at their real strength:")
    print("      TIER 1 (structural, absolute): V53 emits only 0x07, V54 only 0x0F (bit7 clear),")
    print("        and V66/V67 both assert bit3 is NEVER set -- their whole payload space is")
    print("        disjoint from V68's.")
    seen = set(vals)
    therm, ladd = thermometer_ok(seen), ladder_ok(seen)
    print("      TIER 2 (empirical, and WEAK against V59/V62): six of V68's eight payloads")
    print("        {0x8F,0x9F,0xBF,0xCF,0xDF,0xFF} are also thermometer-legal for V59/V62. Only")
    print("        0x9F is ladder-legal for V65. V59/V62 are excluded on their recorded routes")
    print("        ONLY -- both contain 0x87, which V68 cannot emit.")
    print(f"        V59/V62 thermometer nesting on this log : {'HOLDS' if therm else 'VIOLATED'}"
          + ("   <- does NOT exclude them on structure" if therm else "  => V59/V62 EXCLUDED"))
    print(f"        V65 ladder invariants on this log       : {'HOLD' if ladd else 'VIOLATED'}"
          + ("   <- does NOT exclude V65 on structure" if ladd else "  => V65 EXCLUDED"))
    if seen & {0xCF, 0xDF, 0xEF, 0xFF}:
        print("        ★ SEMANTIC (not structural) argument: a bit6-set payload is present. Under")
        print("          V59/V62 bit6 is the FAULT SENTINEL, which read 0.000% over route 2c")
        print("          (50,963 frames) and route 37 (86,278). A route where it is set for a")
        print("          material fraction of frames is not a V59/V62 route.")
        if 0xEF in seen:
            print("        ★ 0xEF is present, and it is NOT thermometer-legal => V59/V62 EXCLUDED")
            print("          structurally as well.")
    if therm or ladd:
        print("        🛑 A structurally-compatible prior build remains on the table. The .rwd")
        print("           filename is then the ONLY hard evidence. Do not skip it.")
    print("   ⚠ None of this excludes a FUTURE build. Confirm the .rwd:")
    print(f"      {RWD_NAME}")

    # ---- 2. SUBSETS -------------------------------------------------------------------------------
    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    eng = d["sca"] == 1
    print("\n-- 2. ENGAGEMENT / SUBSETS (cruiseState is long+lat: NOT used) --")
    print(f"   carControl.latActive    : {int(d['lat'].sum()):6d} ({100 * d['lat'].mean():5.2f}%)"
          + ("" if d["has_lat"] else "   ⚠ ABSENT from the log -- this column is EMPTY, not zero"))
    print(f"   STEER_CONTROL_ACTIVE==1 : {int(eng.sum()):6d} ({100 * eng.mean():5.2f}%)")
    print(f"   agreement latActive vs SCA : {100 * (d['lat'] == eng).mean():.2f}%")
    print(f"   hands-off by SUSTAINED effort: {int(hands_off.sum())} "
          f"| by raw |tq|<=200: {int((np.abs(d['tq']) <= 200).sum())}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {int(creep.sum())}")
    if not d["has_gear"]:
        print("   ⚠ carState.gearShifter absent -- the reverse split is EMPTY, not zero.")

    verdict_ok = True
    if eng.sum() == 0 or (~eng).sum() == 0:
        print("\n   *** THE LOG HAS FRAMES IN ONLY ONE ENGAGEMENT STATE. bit6's transition structure")
        print("       cannot be measured and 'duty tracks engagement' is undefined. This is the")
        print("       'start the log before the first engagement' failure. RE-DRIVE.")
        verdict_ok = False

    # ---- 3. *** THE HEADLINE: bit4, the above-50-Hz detector *** ----------------------------------
    print(f"\n{'-' * 100}\n-- 3. *** THE HEADLINE: bit4 = gp-0x671a >= 1 *** --")
    print("   Honda's own 1 kHz oscillation detector, at its LOWEST rung. This is the only quantity")
    print("   in this log that was computed above the ~50 Hz barrier CAN and the IMU both hit.")
    duty4 = float(g6ac0.mean())
    print(f"\nbit4 duty, WHOLE LOG                    : {100 * duty4:6.2f}%   "
          f"({int(g6ac0.sum())} / {n} frames)")
    for sname, sel in (("ENGAGED", eng), ("MANUAL", ~eng),
                       ("ENGAGED + creep(v<=5)", eng & creep),
                       ("MANUAL + creep(v<=5)", ~eng & creep),
                       ("ENGAGED + hands-off", eng & hands_off),
                       ("ENGAGED + hands-ON", eng & ~hands_off)):
        if sel.sum() < 2:
            print(f"   bit4 duty, {sname:29s}: (fewer than 2 frames)")
            continue
        print(f"   bit4 duty, {sname:29s}: {100 * float(g6ac0[sel].mean()):6.2f}%   "
              f"({int(g6ac0[sel].sum())} / {int(sel.sum())})")
    print()
    print_bit4_caveat()

    print("\n⚠ READ THE CREEP ROWS SEPARATELY FROM THE ROAD-SPEED ROWS. Below ~10 km/h the")
    print("      CEIL latch never releases, so a creep duty is a LATCH-STATE duty and cannot be")
    print("      compared with a road-speed duty. They are different measurements.")
    print("   ⚠ V67's rung read 0.000% at `>= 5`; this reads `>= 1`. A non-zero reading here is")
    print("      NOT a contradiction of V67 -- it is the sub-CEIL activity V67 could not see.")

    if duty4 == 0.0:
        print("\n⇒ bit4 NEVER SET. The detector saw no reversal past +/-12800 anywhere in this")
        print("      log -- including above 50 Hz, where nothing else here can look. Combined with a")
        print("      symptom the driver reports, that ARGUES AGAINST an amplitude large enough to")
        print("      trip Honda's own detector, at any frequency in its 45-100 Hz sweet spot.")
        print("      ⚠ It does NOT rule out a smaller-amplitude resonance: 1056-1186 counts is a")
        print("         floor, not zero. And brief events are under-counted (~5 frames each).")
    elif duty4 < 0.005:
        print(f"\n⇒ bit4 set on a HANDFUL of frames ({int(g6ac0.sum())}). At ~5 frames per")
        print("      sub-CEIL trip this is on the order of a few isolated reversals. Locate them in")
        print("      time and cross-reference the maneuver log before reading anything into the rate.")
    else:
        print(f"\n⇒ bit4 duty is SUBSTANTIAL ({100 * duty4:.2f}%). Before interpreting:")
        print("      a) split creep from road speed -- the CEIL latch never releases below ~10 km/h;")
        print("      b) check whether the set frames are contiguous HOLDS or scattered TRIPS. A hold")
        print("         is ONE event, not N frames of events. Duty is not a rate.")
        print("      c) condition on bit6: a detector firing only when LKAS is engaged is a different")
        print("         finding from one that fires in manual steering too.")

    # ---- 4. bit6, THE GATE -- carried from V67 and still load-bearing ------------------------------
    print(f"\n{'-' * 100}\n-- 4. bit6 = THE GATE (carried from V67 unchanged) --")
    print("   V67/V68's arm is taken WHEN AND ONLY WHEN this bit is 1 and bit5 is 0. It is also the")
    print("   engagement covariate every bit4 number above is conditioned on, so it is checked here")
    print("   even though the build did not change it.")
    m6 = g6806
    if d["has_lat"] and d["lat"].any() and (~d["lat"]).any():
        de, dm = float(m6[d["lat"]].mean()), float(m6[~d["lat"]].mean())
        agree = 100 * (m6 == d["lat"]).mean()
        print(f"   duty vs carControl.latActive :  latActive {100 * de:6.2f}%   "
              f"manual {100 * dm:6.2f}%   gap {100 * (de - dm):+6.2f} pp")
        print(f"   agreement bit6 == latActive  : {agree:.3f}%")
        if de - dm < -GATE_TRACKS_MIN:
            print("   *** OBSERVED: duty is HIGHER WHEN MANUAL. THE POLARITY IS INVERTED relative to")
            print("       the design -- the arm would apply while the driver steers alone. STOP.")
            verdict_ok = False
        elif de - dm < GATE_TRACKS_MIN:
            print(f"   *** THE GATE DOES NOT TRACK LATERAL ENGAGEMENT (gap < "
                  f"{100 * GATE_TRACKS_MIN:.0f} pp). Treat the build as UNVALIDATED.")
            verdict_ok = False
        else:
            print("   => the gate TRACKS lateral engagement, as designed.")
        print("\n   ★★ AGAINST THE ON-CAR BASELINE for the same cell (V57 routes 29/28, V67 route 47):")
        for rt, fr, ag, du, tps in V57_BASELINE:
            print(f"      V57 route {rt:<3d} {fr:6d} frames   agreement {ag:.3f}%   duty {du:5.2f}%   "
                  f"{tps:.4f} transitions/s")
        print("      V67 route 47  150327 frames   agreement 99.983%   (25 single-frame edges)")
        s6 = gate_stats(m6, np.ones(n, bool), fs, "")
        print(f"      THIS DRIVE    {n:6d} frames   agreement {agree:.3f}%   duty "
              f"{100 * s6['duty']:5.2f}%   {s6['tps']:.4f} transitions/s")
        if agree < V57_AGREEMENT_MIN:
            print(f"      *** AGREEMENT IS BELOW {V57_AGREEMENT_MIN}%, AND V57 GOT 99.9% AND V67")
            print("          99.98% ON THE SAME CELL. Either gp-0x6806 is not behaving as it did, or")
            print("          the build on the car is not V68. STOP and confirm the .rwd.")
            verdict_ok = False
        else:
            print("      => reproduces the V57/V67 validation.")
    else:
        print("   ⚠ carControl.latActive is absent or single-valued; falling back to")
        print("     STEER_CONTROL_ACTIVE. Note the fallback in any writeup.")
        if eng.any() and (~eng).any():
            de, dm = float(m6[eng].mean()), float(m6[~eng].mean())
            print(f"   duty vs SCA : engaged {100 * de:6.2f}%   manual {100 * dm:6.2f}%   "
                  f"gap {100 * (de - dm):+6.2f} pp")
            if de - dm < GATE_TRACKS_MIN:
                verdict_ok = False

    # ---- 5. bit5, THE r24/r26 LANE DROPOUT --------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 5. bit5 = gp-0x67df != 0, THE DETECTOR'S FIRST STAGE --")
    print("   When this fires, FUN_0003aa2c SKIPS the aggregate add and BOTH rate lanes leave the")
    print("   loop -- whichever gain arm was selected. It is not a mask on the arm; it removes the")
    print("   lane. Routes 47 and 4a never exercised this cell (V67 probed gp-0x671d instead).")
    print()
    print_bit5_caveat()
    n5 = int(g671d.sum())
    print(f"\nbit5 set: {n5} / {n}  ({100 * g671d.mean():.4f}%)")
    if n5 == 0:
        print("   => the lanes were CONNECTED throughout this drive. The highway 40-49 Hz dose null")
        print("      is NOT a dropout artifact, and that alternative explanation is closed.")
        print("      ⚠ One drive is not a proof of unreachability -- only of not-reached.")
    else:
        print(f"   *** bit5 FIRED on {n5} frames. On those frames BOTH r24 and r26 were OUT of the")
        print(f"       {ARM_MASK_VALUE}, BELOW stock -- the build was WORSE than baseline there, not")
        print("       merely inert. Report this separately from the rest of the drive; excluding")
        print("       those frames from a grind statistic is legitimate ONLY if it is stated.")
        verdict_ok = False

    # ---- 6. ALL THREE BITS, per subset ------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 6. ALL BITS, per subset --")
    print(f"   {'gate / subset':24s} {'n':>7s} {'expos':>8s} {'runs':>5s}  {'duty':>12s}  "
          f"{'transitions':>13s}  {'rate':>10s}  {'dominant':>17s}")
    print("   exposure = selected samples / fs;  'r' = contiguous runs. Transitions are counted")
    print("   WITHIN runs only, and the spectrum comes from the LONGEST run -- never a concatenation.")
    headline = {}
    subsets = [("ALL", np.ones(n, bool)),
               ("ENGAGED", eng),
               ("MANUAL", ~eng),
               ("ENGAGED+creep", eng & creep),
               ("MANUAL+creep", ~eng & creep)]
    for bit, name, _cell, test, why in GATES:
        m = (d["b4"] & bit) != 0
        print(f"   -- {name} {test}   {why}")
        for sname, sel in subsets:
            if sel.sum() < 2:
                print(f"   {'  ' + sname:24s}   (fewer than 2 frames)")
                continue
            s = gate_stats(m, sel, fs, "  " + sname)
            print_gate_row(s)
            if sname == "ALL":
                headline[bit] = s

    # ---- 7. THE KILL CRITERION --------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 7. THE KILL CRITERION: a gain that switches near the mode frequency --")
    print(f"   ANY gate toggling inside {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz is a PARAMETRIC PUMP.")
    print("   For bit6 that is an ABORT -- it is the live gate on the flashed build. bit4 is NOT a")
    print("   gate on anything (it selects a LERP segment, and the LERP is continuous across the")
    print("   breakpoint), so a fast bit4 is information about the plant, not a stability risk.")
    for bit, name, _cell, test, _why in GATES:
        s = headline.get(bit)
        if s is None:
            continue
        toggles = s["rise"] + s["fall"]
        if toggles == 0:
            print(f"   {name}: NEVER TOGGLES over the whole log ({s['span']:.1f}s, duty "
                  f"{100 * s['duty']:.2f}%).")
            print("      🛑 NOT automatically a pass. A gate that never changes cannot be shown to be")
            print("         SLOW -- only to have not been EXERCISED.")
            continue
        pk = s["peak_hz"]
        inband = np.isfinite(pk) and KILL_LO_HZ <= pk <= KILL_HI_HZ
        print(f"   {name}: {toggles} transitions in {s['span']:.1f}s = {s['tps']:.3f}/s, dominant "
              f"{pk:.2f} Hz (prom {s['prom']:.1f}x)")
        if inband and bit == BIT_GATE:
            print("      *** ABORT CRITERION MET ON THE LIVE GATE. The gain is switching inside the")
            print("          kill band. Do not keep driving on this build's conclusions.")
            verdict_ok = False
        elif inband:
            print("      (in band, but this bit gates nothing -- information, not a stability risk)")
    print(f"   🛑 NYQUIST: fs = {fs:.2f} Hz, so anything above {nyq:.1f} Hz is ALIASED. A true "
          f"{2 * nyq - 42:.0f} Hz")
    print("      toggle reads as 42 Hz here. The band above ~50 Hz is NOT observable by this probe,")
    print("      by the CAN bus, or by the comma IMU. See the docstring.")

    # ---- 8. BY SPEED ------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 8. BY SPEED -- where the rate axis actually goes --")
    print(f"   {'band':>12s} {'n':>7s} {'b6 duty':>9s} {'b5 duty':>9s} {'b4 duty':>9s} {'b4 t/s':>8s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 25), (25, 99)):
        sel = (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() < 2:
            continue
        s6 = gate_stats(g6806, sel, fs, "")
        s5 = gate_stats(g671d, sel, fs, "")
        s4 = gate_stats(g6ac0, sel, fs, "")
        print(f"   {f'{lo}-{hi} m/s':>12s} {int(sel.sum()):7d} {100 * s6['duty']:8.2f}% "
              f"{100 * s5['duty']:8.2f}% {100 * s4['duty']:8.2f}% {s4['tps']:8.3f}")
    print("   ⚠ bit4 is a HOLD-TIME statistic. Below ~10 km/h the CEIL latch never releases, so")
    print("     vehicle speed is exactly what parking-lot steering should produce; the flat-segment")
    print("     claim is about the SYMPTOM windows, so read the creep rows against section 3.")

    # ---- THE VERDICT ------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- THE VERDICT --")
    for bit, name, _cell, test, _why in GATES:
        s = headline.get(bit)
        if s:
            print(f"   {name} {test:8s}: duty {100 * s['duty']:6.2f}%, "
                  f"{s['rise'] + s['fall']:5d} transitions in {s['span']:.1f}s = {s['tps']:.3f}/s")
    print()
    print_bit4_caveat()
    if verdict_ok:
        print("\n   *** THE PROBE IS VALID ON EVERY CRITERION THIS DRIVE CAN TEST. *** Read section 3")
        print("   for the answer V68 was built to get.")
    else:
        print("\n   *** A CRITERION FAILED. *** See above; section 3's answer is conditional on it.")
    print("\n   ⚠ OUTSTANDING, and NOT testable from this log:")
    print("      Anything above ~50 Hz. V68 does not break the aliasing barrier and was not built")
    print("        to -- see the docstring for the three reasons the sticky rung was rejected.")
    print("      gp-0x683c is UNREFERENCED by any displacement form (0 readers, 0 writers) and is the")
    print("        best free-RAM candidate this kit has. It is .data, boot value 0x00 from flash")
    print("        0x86874 via the copy loop at 0x14766. The pointer / ep / stack / boot-init legs")
    print("        of GATE 1 are CLOSED; the runtime-base-pointer and DMA legs are NOT -- and they")
    print("        are not statically closable for ANY cell. V68 does not use it.")
    print("        🛑 The clearance is V67-AND-LATER ONLY. On a stock base 0x3AA94 still reads this")
    print("           byte and writing it flips r24/r26's gain arm onto cals 0xC6446/0xC6444.")
    print("      The r26 lane rides the SAME gate as r24 (cal 0xC6444, stock 512), so under LKAS")
    print("        r26's gain becomes 512 instead of its gain_A LERP. Harmless only because r26 is")
    print("        structurally inert (0xC6564 = 40 bytes of exact zero). If the ride reports LESS")
    print("        damping under LKAS rather than less grinding, look here first.")
    print("      Grind #2 SURVIVES under LKAS by design, unchanged from V67. Judge it on the MANUAL")
    print("        rows, not the engaged ones.")
    print(f"\n   Expected file on the car: {RWD_NAME}")
    print(f"     image SHA256 {IMAGE_SHA}")
    print(f"     rwd   SHA256 {RWD_SHA}")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
