#!/usr/bin/env python3
"""decode_v68_probe.py -- read V68's rate-axis probe out of an rlog.

V68 IS V67'S CONTROL PATH, BYTE-IDENTICAL, WITH A RE-AIMED PROBE. It changes nothing that touches
torque: the only bytes that differ from V67 anywhere in [0x13000,0x100000) are the cave span and the
MAIN CRC trailer, and the CAL CRC is UNCHANGED -- which is itself the proof.

    0x3AA96  = 0xFB     V67's repoint, carried:  ld.bu -0x6806[gp],r15 @0x3AA94
    0xC6446  = 5244     V67's LKAS arm, carried
    0x3AB70 / 0x3AB76 / 0x3AC20  all STOCK `sar 0xa`
    => every ride impression on V68 is a ride impression on V67.

V68 packs FIVE bits into CAN 330 (0x14A) byte4 at ~100 Hz:

    bit 7 = 1                    LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6806 != 0       *** THE GATE *** -- carried from V67 unchanged   (EVEN disp 0x97FA)
    bit 5 = gp-0x671d != 0       *** THE MASKING RISK *** -- carried unchanged    (ODD  disp 0x98E3)
    bit 4 = gp-0x6ac0 >= 400     *** NEW *** the r24 gain LERP's INNER axis vs its FIRST breakpoint
    bit 3 = 1                    *** NEW *** THE V68 BUILD-CLASS MARKER (constant)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

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
    39990-TVA,A160-V68-LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-rateaxisprobe-can330byte4-0x13000-0x100000.rwd

THE HEADLINE -- bit4, and the contradiction it adjudicates
------------------------------------------------------------
Two of this kit's own load-bearing numbers disagree about which side of the LERP's first breakpoint
the car operates on, and nothing in the record resolves it:

  * The TELEMETRY derivation put 100% of symptom windows INSIDE the flat first segment [0, 400] --
    bus counts = 1.697754 x gp-0x6ac0, through cal 0xC613A = 1159. Never measured directly.
  * V67's ARM VALUE, 5244 = 2 x 2622, takes 2622 as the LERP at "motor rate 128 deg/s" -- which is
    603 counts, i.e. on the SLOPED segment. The opposite side.

Read from the four mode-10 gain_B records (0xD2A74/0xD2AB0/0xD2AEC/0xD2B28), X = (0, 400, 1400|1500,
3000) and the segment [0,400] is EXACTLY flat in three of four records, flat to one count in the
fourth. At 7.2 km/h the LERP is 2704 below the breakpoint and 2622 at 603 counts. So:

    bit4 duty ~= 0%   =>  the operating point never leaves the FLAT segment. V67's arm is
                          delivering 5244/2704 = 1.94x, not the 2.00x its docstring claims; the arm
                          for exactly 2.00x is 5408 (a one-halfword cal edit). AND -- the bigger
                          consequence -- THIS LANE CANNOT BE TUNED ON WHEEL RATE, because its rate
                          axis is a constant in the regime the car actually uses.
    bit4 duty >> 0%   =>  the rate axis IS live, the LERP really does roll off in use, and rate is
                          available as a discriminator for any future calibration on this lane.

Either answer closes the question. That is why the bit is worth a rung.

🛑🛑 bit4 IS PRE-REGISTERED TO READ 0.000%, AND THAT IS THE POINT
------------------------------------------------------------------
Route 47's own cache, pushed through the very scale chain the probe exists to test
(gp-0x6ac0 = |0x18F rate counts| x 32768/(48*1159) = x 0.5890135), 150,327 samples / 25.1 min,
creep AND highway, both gate arms:

    p50 0.6 · p90 10.6 · p99 105.4 · p99.9 221.3 · p99.99 264.4 · MAX 277.4 counts
    samples at or above the 400 breakpoint: 0 of 150,327
    => the axis must be 1.442x larger than the derivation says for bit4 to fire ONCE.

⇒ A FLAT ZERO IS THE EXPECTED RESULT AND IS A CONFIRMATION, NOT A DEAD RUNG. This is written down
before the drive precisely so it cannot be reinterpreted afterwards -- V67's bit4 read 0.000% and
was (correctly) called wasted, and a reader who has that in mind will misread this one.

★ The test is ONE-SIDED and aimed at the only direction that changes a decision: the flat-segment
claim survives a scale chain that OVER-estimates the axis and dies only to one that UNDER-estimates.
bit4 detects exactly that, from the firmware's own cell, with the chain removed from the question.
A 1.442x error is not exotic -- the chain runs through cal 0xC613A = 1159, an EMA, and a x8 grid
factor between the 0x18F and 0x14A copies, and this kit has already had one "128 deg/s vs 359 raw
counts" contradiction on this very axis.

⚠ ONE ASYMMETRY IN bit4, and it is NOT symmetric -- read this before quoting a duty.
The LERP folds its key to 0 above RATE_FOLD = 13001 counts (0x3AAC8 `addi -0x32c9` / 0x3AACC
`cmovc`), so a folded value ALSO lands on the flat first point. bit4 does not test the fold -- a
second compare costs 6 more bytes than the 68-byte proven cave has. Therefore:

    bit4 == 0  =>  DEFINITELY inside the flat segment.                          UNAMBIGUOUS
    bit4 == 1  =>  on the sloped segment, OR folded past 13001.                 TWO READINGS

13001 counts is 2759 deg/s of motor rate, roughly 20x the fastest this kit has recorded, so the fold
is implausible rather than impossible. The asymmetry runs in the SAFE direction for the claim under
test ("always flat"), and this tool prints the caveat next to every bit4 number rather than once.

🛑 WHAT V68 CANNOT DO: IT DOES NOT BREAK THE ALIASING BARRIER
--------------------------------------------------------------
CAN samples at ~100.5 Hz (Nyquist ~50.2) and the comma IMU at 99.9-100.5 Hz. Both instruments are
blind above ~50 Hz, and grind #2's "44.9 Hz" is itself an alias -- 44.9 and ~55.6 Hz are the same
observation. V68 does not change that. A sticky/latching rung sampling the 1 kHz task was designed
and REJECTED on three independent grounds, all recorded in build_v68_tva.py's docstring:
  1. BUDGET -- 20 bytes are free after bit6 and bit5; the rung needs 22 before any latch machinery
     and 60 with it. The cave must not grow: caves are this kit's only bricking class.
  2. SELECTIVITY -- gp-0x4f62 is read `ld.h` (SIGNED halfword, byte-verified at 6 sites) and a
     scalar threshold on |it| is an amplitude detector, not a band detector. Its low-frequency
     content already measures 123-839 counts, so any threshold above the driver fires exactly during
     large driver inputs -- which is also when grind #2 occurs. Confounded by construction.
  3. NO CLEAR EVENT -- a latch is informative only if reset once per transmitted frame, and the cave
     cannot detect transmission. Self-cleared it degenerates to a plain sample; never cleared it
     pins ON after the first trip, a dead probe that still looks alive.
Do not read any bit here as evidence about content above ~50 Hz.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all established the hard way:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes
     while lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is unmeasurable.
  4. Statistics are computed PER CONTIGUOUS RUN and pooled -- never over a concatenated subset,
     which manufactures a transition at every join (V58's retracted 25 Hz coherence).

Usage:  python decode_v68_probe.py RLOG [RLOG ...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
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
CAVE_HEX = "203e88008437fb976132b605273e4000a437e3986132b605273e2000e4374195263670fee031b605273e10008437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e8800  movea 0x88,r0,r7        bit7 LIVENESS + bit3 BUILD-CLASS MARKER
#   0xC4B38  8437fb97  ld.bu -0x6806[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e4000 movea 0x40
#   0xC4B44  a437e398  ld.bu -0x671d[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e2000 movea 0x20
#   0xC4B50  e4374195  ld.hu -0x6ac0[gp],r6    *** the NEW rung: an UNSIGNED HALFWORD ***
#   0xC4B54  263670fe  movea -0x190,r6,r6      r6 = rate - 400  (movea SIGN-EXTENDS its imm16)
#   0xC4B58  e031      cmp r0,r6             | b605 blt +6 | 273e1000 movea 0x10
#   0xC4B60  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6A  4437ecea  st.b  r6,-0x1514[gp]     THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B6E  2436e8ea  movea -0x1518,gp,r6     the displaced hook instruction
#   0xC4B72  7f00      jmp [lp]                -> 0x55C12
# ⚠ gp-0x671d's displacement 0x98E3 is ODD, so its opcode field reads 0x3D, not 0x3C. That is
# correct and is exactly the hw1-bit-5 trap that has produced false mismatches before.
# ⚠ 64 of the 68 proven cave bytes are used. 4 spare -- not enough for a fourth rung (12 minimum).

BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_RATE = 0x40, 0x20, 0x10
BIT_CLASS = 0x08              # *** CONSTANT 1 on V68. The build-class marker. ***
PROBE_MASK = 0xF8
CONSTANT_BITS = BIT_LIVE | BIT_CLASS      # 0x88 -- both must be set on EVERY legal V68 frame

RATE_BREAKPOINT = 400         # xs[1] in every mode-10 gain_B record
RATE_FOLD = 13001             # 0x3AAC8: at or above this the LERP key folds to 0 -> the flat point
RATE_COUNTS_PER_DEGS = 16384 / 3477       # cal 0xC613A = 1159; 400 counts = 84.9 deg/s
BUS_SCALE = 1.697754          # bus counts per gp-0x6ac0 count, via 0xC613A

ARM_VALUE = 5244              # cal 0xC6446 under V67 and V68
ARM_MASK_VALUE = 1024         # cal 0xC6442, taken when bit5 is set -- BELOW the stock creep LERP
LERP_FLAT = 2704              # the mode-10 LERP at 7.2 km/h anywhere below the breakpoint
LERP_AT_603 = 2622            # ...and at 603 counts (= 128 deg/s), which is what 5244 was derived from
ARM_FOR_2X_IF_FLAT = 5408     # 2 x LERP_FLAT -- the arm V67 would need if bit4 reads ~0%

# (bit, short name, gp cell, test text, what it decides)
GATES = (
    (BIT_GATE, "bit6 gp-0x6806", 0x6806, "!= 0",
     "*** THE GATE *** -- V67/V68's arm is taken here and nowhere else"),
    (BIT_MASK, "bit5 gp-0x671d", 0x671d, "!= 0",
     "*** THE MASKING RISK *** -- outranks the arm; gain pinned to 1024, BELOW stock"),
    (BIT_RATE, "bit4 gp-0x6ac0", 0x6ac0, f">= {RATE_BREAKPOINT}",
     "*** THE HEADLINE *** -- the LERP inner axis: flat segment or sloped"),
)

LEGAL = {CONSTANT_BITS | a | b | c
         for a in (0, BIT_GATE) for b in (0, BIT_MASK) for c in (0, BIT_RATE)}

RWD_NAME = ("39990-TVA,A160-V68-LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-"
            "rateaxisprobe-can330byte4-0x13000-0x100000.rwd")
IMAGE_SHA = "704ece2ee91f8ad605bb41d72d5013c3a7ddc2c6cde1176610e7291c67861635"
RWD_SHA = "387cc0be8ea8f4c5037dd4eb15f4d0f278a597881848fb9defe944ff24025c4a"

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
    print(f"{indent}⚠ bit4 == 0 is UNAMBIGUOUS (flat segment). bit4 == 1 means sloped OR folded")
    print(f"{indent}  past {RATE_FOLD} counts = {RATE_FOLD / RATE_COUNTS_PER_DEGS:.0f} deg/s -- "
          "implausible, not impossible. Do not")
    print(f"{indent}  quote a bit4 duty without this sentence.")


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

    # 🛑 THE FROZEN-CONSTANT REFUSAL. A single repeated payload is uninterpretable EVEN when it is
    # structurally legal -- that is exactly how V64's null was misread for a session.
    if len(vals) == 1:
        v = vals[0]
        print(f"\n   *** STOP. byte4 IS A FROZEN CONSTANT 0x{v:02X} across all {n} frames. ***")
        print("       Zero variance in a field carrying three INDEPENDENT live signals is not a")
        print("       measurement -- it is a symptom. Under V64 exactly this pattern was read as a")
        print("       physical null for a whole session before the probe was found to be unarmed.")
        print("       At minimum one of the following is true, and this tool will not choose:")
        print("         - the drive never changed lateral engagement state (bit6 could not move);")
        print("         - a rung's cell is not what the build believes it is;")
        print("         - the flashed image is not V68 despite the payload being legal for it.")
        print("       No duty, rate or spectrum below would mean anything. RE-DRIVE with the log")
        print("       started BEFORE the first engagement, and confirm the .rwd:")
        print(f"         {RWD_NAME}")
        return
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

    # ---- 3. *** THE HEADLINE: bit4, the LERP inner axis *** ---------------------------------------
    print(f"\n{'-' * 100}\n-- 3. *** THE HEADLINE: bit4 = gp-0x6ac0 >= {RATE_BREAKPOINT} *** --")
    print("   This is what V68 was built to measure. It decides whether the r24 gain LERP's rate")
    print("   axis is LIVE in the regime the car actually uses, or a constant.")
    duty4 = float(g6ac0.mean())
    print(f"\n   bit4 duty, WHOLE LOG                    : {100 * duty4:6.2f}%   "
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

    print("\n   THE ARITHMETIC THIS DECIDES (mode-10 gain_B, at 7.2 km/h):")
    print(f"     gp-0x6ac0 <  {RATE_BREAKPOINT:5d} counts (< {RATE_BREAKPOINT / RATE_COUNTS_PER_DEGS:5.1f} deg/s"
          f", < {RATE_BREAKPOINT * BUS_SCALE:.0f} bus counts)  ->  LERP = {LERP_FLAT}  FLAT")
    print(f"     gp-0x6ac0 =    603 counts (= 128.0 deg/s)                        ->  LERP = "
          f"{LERP_AT_603}  SLOPED   <- what V67's 5244 assumed")
    print("\n   🛑 THE PRE-REGISTERED PREDICTION (route 47, 150,327 samples, via the same scale")
    print("      chain this probe tests): p99 105 · p99.9 221 · MAX 277 counts · ZERO samples at or")
    print("      above 400. bit4 IS PREDICTED TO READ 0.000% -- the axis must be 1.442x larger than")
    print("      the derivation for it to fire once. A FLAT ZERO IS A CONFIRMATION, NOT A DEAD RUNG.")

    if duty4 < 0.01:
        print(f"\n   ⇒ *** THE FLAT-SEGMENT CLAIM IS CONFIRMED (bit4 duty {100 * duty4:.2f}%). ***")
        print("      This MATCHES the pre-registered prediction. The one-sided test passed: the")
        print("      scale chain does not under-estimate the axis by 1.442x or more.")
        print(f"      The LERP is a CONSTANT {LERP_FLAT} in the regime this car drives, so:")
        print(f"        a) V67/V68's arm {ARM_VALUE} is delivering {ARM_VALUE / LERP_FLAT:.3f}x, "
              f"NOT the 2.000x on record.")
        print(f"           The arm for exactly 2.00x is {ARM_FOR_2X_IF_FLAT} -- ONE halfword at "
              "0xC6446, cal-only,")
        print("           inside a CRC block this kit recomputes routinely. A 3% correction: real,")
        print("           but not a reason on its own to reflash a build that works.")
        print("        b) *** NO FUTURE CALIBRATION ON THIS LANE CAN DISCRIMINATE ON WHEEL RATE. ***")
        print("           Any proposal that shapes r24's gain by motor rate is shaping a constant.")
        print("           This is the durable finding; (a) is the footnote.")
    elif duty4 > 0.10:
        print(f"\n   ⇒ *** THE FLAT-SEGMENT CLAIM IS REFUTED (bit4 duty {100 * duty4:.2f}%). ***")
        print("      This CONTRADICTS the pre-registered prediction of 0.000%, which means the")
        print("      |0x18F| x 0.5890135 scale chain UNDER-ESTIMATES gp-0x6ac0 by at least 1.442x.")
        print("      🛑 That chain is load-bearing elsewhere -- r47_rate_axis.py's whole regime map")
        print("         and V67's arm derivation both use it. Re-derive them before anything else.")
        print("      The rate axis IS exercised. The LERP genuinely rolls off in use, wheel rate is")
        print("      available as a discriminator for future calibration on this lane, and V67's")
        print(f"      arm of {ARM_VALUE} is a scalar standing in for a CURVE -- the residual its own")
        print("      build note flagged. Re-derive the arm against the MEASURED distribution of")
        print("      gp-0x6ac0 above, not against a single assumed operating point.")
        print("      🛑 Before concluding: check the fold caveat above, and check whether the bit4")
        print("         frames are concentrated in one manoeuvre (see the by-speed table).")
    else:
        print(f"\n   ⇒ INTERMEDIATE (bit4 duty {100 * duty4:.2f}%). The axis is exercised, but rarely.")
        print("      Report the duty CONDITIONED on regime -- the engaged/creep rows above are the")
        print("      ones that matter for grind #1, and a whole-log duty pools regimes that differ.")

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

    # ---- 5. bit5, THE MASKING RISK ----------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 5. bit5 = gp-0x671d, THE MASKING RISK --")
    print("   gp-0x671d strictly OUTRANKS the arm at 0x3ABFA. Whenever it is set, r24's gain is")
    print(f"   pinned to cal 0xC6442 = {ARM_MASK_VALUE} -- BELOW the stock creep LERP. It does not")
    print("   merely mask the build, it cuts the lane. Route 47 read it 0.000% over 150,327 frames;")
    print("   route 35 (V64) read it 0 over 14,980. Each is one drive, not a clearance.")
    n5 = int(g671d.sum())
    print(f"   bit5 set: {n5} / {n}  ({100 * g671d.mean():.4f}%)")
    if n5 == 0:
        print("   => never fired on this drive either. The arm was unmasked throughout.")
        print("      🛑 This is an accumulating null, not a proof. It cannot be shown to be")
        print("         UNREACHABLE from logs -- only to have not been reached.")
    else:
        print(f"   *** bit5 FIRED on {n5} frames. On those frames the gain was pinned to")
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
    print("   ⚠ gp-0x6ac0 is a MOTOR/RESOLVER rate, not vehicle speed. A high bit4 duty at low")
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
    print("      gp-0x683c is UNREFERENCED image-wide (0 readers, 0 writers) and is the best free-RAM")
    print("        candidate this kit has. V68 does NOT use it and does NOT clear it: GATE 1's")
    print("        register-indirect leg was never closed on it, and gp-0x1500 passed both static")
    print("        methods and still failed on-car.")
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
