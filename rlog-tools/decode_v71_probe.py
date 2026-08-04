#!/usr/bin/env python3
"""decode_v71_probe.py -- read V71's probe: WHICH GAIN ARM IS ACTUALLY IN FORCE.

WHY THIS PROBE READS SELECTORS AND NOT A LANE OUTPUT
-----------------------------------------------------
V64, V68, V69 and V70 each returned an uninterpretable zero, and each one had read an OUTPUT. V70's
own positive control -- `gp-0x6ada >= +512`, r24's post-clip lane mirror -- read **0 / 18,010**
against a replay predicting **311** from the route's own data (52 even under STOCK firmware). A lane
output that reads zero cannot tell you WHY. V71 spends four of its five rungs on the inputs to the
gain PRIORITY CHAIN, so every outcome is actionable:

    0x3ABFA  gp-0x671d != 0  ->  cal 0xC6442 = 1024   *** OUTRANKS EVERYTHING ***      bit6
    0x3AC04  lp != 0         ->  cal 0xC6446 =  512   DEAD on V71 (gp-0x683c: 0 writers)
    0x3AC0E  gp-0x671a >= 5  ->  cal 0xC6440 = 2048   (5 = cal 0xC64FA, a BYTE)         bit3
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
    bit4 = gp-0x6ada >= +512   THE POSITIVE CONTROL. r24's lane output after its own +/-0x2000
                               saturating clip, mirrored to RAM by Honda's own code at 0x3AD5A every
                               1 kHz tick. 0 READERS / 1 WRITER image-wide.
    bit3 = gp-0x671a >= 5      the THIRD arm. 📋 PRE-REGISTERED PREDICTION: reads 0 (V67: 0.000%
                               over 186,321 frames on two routes; V64: 0 for both `>= 5` and `!= 0`).

⚠ HOW STRONG bit4 REALLY IS -- stated precisely, because the loose version is wrong.
On the three ARM branches bit4 IS strictly stronger than V70's equivalent rung, because a `sar` edit
doubles r24 whichever arm wins while V70's surface edit applied ONLY on the LERP branch. On the LERP
branch it is stronger AWAY from 0 km/h and exactly EQUAL at the breakpoints V70's surface dose
doubled. The rung fires at |dtorque| >= 512 x 2^sar / gain; re-derived from the two images by
build_v71_tva.py's own sweep, not quoted:

    operating point                     V70 thr   V71 thr
    creep 0 km/h, rateKey 0                85.3      85.3   <- IDENTICAL (V70's dose was exactly 2x)
    grind #1 op pt 7.2 km/h, rk 603       108.9     100.0
    grind #2 creep 7.2 km/h, rk 1206      172.0     110.3
    engaged highway 93 km/h, rk 300       241.3     120.6

⇒ bit4 is NOWHERE less sensitive than V70's rung. Therefore:
    bit6 = 0 AND bit3 = 0 AND bit4 = 0  =>  the LERP arm WAS selected and the lane output really is
                                            below +512, at a threshold NO HIGHER than the one that
                                            already read 0/18,010. The arm-selection explanation for
                                            V70's null is REFUTED, and the problem is upstream --
                                            dtorque itself, or the mirror's writer not being reached.
    bit6 = 1 or bit3 = 1                =>  an arm was selected, V70's surface edit was masked, the
                                            null is explained, and the lever moves to that arm's cal.
Either outcome is actionable. That is the property V64/V68/V69/V70 lacked.

🛑 IDENTIFICATION IS WEAKER ON V71 THAN ON V70, AND THAT IS STATED RATHER THAN PAPERED OVER.
V70 carried an arithmetic invariant (bit6 => bit3, because x >= +512 implies x >= 0) that excluded
six builds absolutely from the VALUE SET alone. V71's four rungs are INDEPENDENT, so its reachable
space is all 16 payloads and no payload is forbidden. What remains:
  * HARD: bit7 must be set in every frame. A VOID frame means the cave did not run.
  * STRONG NEGATIVE: on V71, bit3 is a LATCHED REVERSAL COUNTER test predicted to read 0, and it
    cannot toggle quickly -- `gp-0x671a` integrates 1 kHz information and holds >= 50 ms. On V70,
    bit3 was r24's SIGN, which toggles with the limit cycle. **A fast-toggling bit3 means the
    flashed image is V70, not V71.** That test is checked below and is reported at its real strength.
  * The .rwd FILENAME is the pre-drive discriminator, and V71's is unique on disk.

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

Usage:  python decode_v71_probe.py <rlog-or-route-dir> [...]
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
from decode_v67_gate import collect, runs_of, sustained, transitions        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES, ratchet_line                    # noqa: E402
from decode_v70_probe import episode_ratio, episodes_of                     # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v71_tva.assert_decoder_matches() fails the BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "203e1000a437e3986132a605483a843707986432aa05443a24372695a9326132a605423a8437e7986532a105413ac33a8437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
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
#   0xC4B50  a932      sar   0x9,r6          ARITHMETIC -- units of 512, sign preserved
#   0xC4B52  6132      cmp   0x1,r6
#   0xC4B54  a605      blt   +4
#   0xC4B56  423a      add   0x2,r7          bit4 = gp-0x6ada >= +512
#   0xC4B58  8437e798  ld.bu -0x671a[gp],r6  the third arm's latched reversal counter
#   0xC4B5C  6532      cmp   0x5,r6          CEIL, asserted == cal 0xC64FA (a BYTE = 5)
#   0xC4B5E  a105      bl    +4              UNSIGNED, matching the firmware's own `bc` @0x3AA7E
#   0xC4B60  413a      add   0x1,r7          bit3 = gp-0x671a >= 5
#   0xC4B62  c33a      shl   0x3,r7          the 5-bit field -> bits 7:3.  V31P FLASHED this 4x;
#                                            Honda's own idiom @0x4FB82 (shl 0x3,r7 / andi 0xf8).
#   0xC4B64  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6E  4437ecea  st.b  r6,-0x1514[gp]  THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B72  2436e8ea  movea -0x1518,gp,r6   the displaced hook instruction
#   0xC4B76  7f00      jmp   [lp]            -> 0x55C12
# 🛑 `ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT apart -- and gp-0x6ada's only real instance
# IS the st.h form carrying the same displacement halfword. `ld.bu` 0x3C/0x3D vs `st.b` 0x3A is
# likewise one bit, on THREE rungs, one of them a LIVE state variable with 128 readers. If you ever
# see hw1 0x64.. or 0x44.. where 0x24.. / 0x84.. is written above, the cave WRITES. Do not flash it.
# ⚠ 68 of the 68 proven cave bytes are used. ZERO spare. The extent must NOT be grown to fit more --
# caves are this kit's only bricking class (V24, V27, V48B all bricked the ECU).
# ⚠ The role table at 0xC4124 is asserted unchanged by the builder ([0,0,5,0,5,5,0,0,0,5,0]); a slot
# carrying role 6 or 7 makes gp-0x67ac live and the rate lanes can drop out entirely.

BIT_LIVE = 0x80
BIT_MASK671D = 0x40           # bit6  gp-0x671d != 0     THE MASK -- outranks every arm
BIT_STATE4 = 0x20             # bit5  gp-0x67fa == 4     THE RATCHET STATE this build disables
BIT_R24_HALF = 0x10           # bit4  gp-0x6ada >= +512  THE POSITIVE CONTROL
BIT_ARM3 = 0x08               # bit3  gp-0x671a >= 5     the THIRD arm
PROBE_MASK = 0xF8
THRESHOLD = 512               # bit4: ld.h -> sar 0x9 -> cmp 0x1  =>  cell >= 1 << 9
STATE_VALUE = 4
CEIL_VALUE = 5                # cal 0xC64FA, a BYTE -- hardcoded in the cave, asserted at build time

# The dispatcher's three masks. state in mask  <=>  (1 << (state & 0xf)) & mask.
MASK_DETECTOR = 0x830         # {4,5,11}     FUN_00036388 @0x22882, FUN_000428d4 @0x22926
MASK_AGGREGATOR = 0xC30       # {4,5,10,11}  FUN_0003a382 @0x226A0, FUN_0003aa2c @0x2291E
MASK_ARBITRATION = 0x930      # {4,5,8,11}   the arbitration trio

# (bit, short name, gp cell, what a 1 means)
RUNGS = (
    (BIT_MASK671D, "bit6 gp-0x671D", 0x671D,
     "THE MASK is SET -> r24's gain is pinned to cal 0xC6442 = 1024, BELOW the stock LERP"),
    (BIT_STATE4, "bit5 gp-0x67FA", 0x67FA,
     f"the ECU is in STATE {STATE_VALUE} -- where the governor substitution WOULD have ratcheted"),
    (BIT_R24_HALF, "bit4 gp-0x6ADA", 0x6ADA,
     f"r24 lane out >= +{THRESHOLD} (post +/-8192 clip) -- 0 readers image-wide. POSITIVE CONTROL"),
    (BIT_ARM3, "bit3 gp-0x671A", 0x671A,
     f"the reversal counter reached CEIL {CEIL_VALUE} -> the THIRD arm, cal 0xC6440 = 2048"),
)

CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit
FAST_TOGGLE_PER_S = 2.0       # bit3 above this is a SIGN bit, i.e. V70 -- see identify()

# ⚠ V71's four rungs are INDEPENDENT: all 16 payloads are reachable and none is forbidden.
LEGAL = {BIT_LIVE | a | b | c | d
         for a in (0, BIT_MASK671D) for b in (0, BIT_STATE4)
         for c in (0, BIT_R24_HALF) for d in (0, BIT_ARM3)}
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

# 🛑 ONE LINE, deliberately. The builder asserts this exact basename appears in this file; splitting
# it across a string concatenation makes the substring vanish and the check silently harder to pass.
RWD_NAME = "39990-TVA,A160-V71-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-ratchet-V62sar-BOTHLANES-surfaceREVERTED-gaininforce-probe-671d-67fa4-6ada-671a-can330byte4-0x13000-0x100000.rwd"  # noqa: E501

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
}


def wire_byte4(v671d, v67fa, v6ada, v671a, status_bits=0x7):
    """EXACTLY what the cave computes -- the same five instructions, in the same order."""
    r7 = 0x10                                       # movea 0x10,r0,r7
    if not ((v671d & 0xFF) < 1):
        r7 += 0x08
    if not ((v67fa & 0xFF) != STATE_VALUE):
        r7 += 0x04
    x = (v6ada - 0x10000) if v6ada & 0x8000 else v6ada
    if not ((x >> 9) < 1):
        r7 += 0x02
    if not ((v671a & 0xFF) < CEIL_VALUE):
        r7 += 0x01
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 16, f"{len(LEGAL)} legal payloads, expected all 16 (independent rungs)"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert BIT_LIVE | BIT_MASK671D | BIT_STATE4 | BIT_R24_HALF | BIT_ARM3 == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    # the wire model, against the bit map above
    assert wire_byte4(0, 0, 0, 0) & PROBE_MASK == BIT_LIVE, "an all-zero input is not bare liveness"
    assert wire_byte4(1, 0, 0, 0) & BIT_MASK671D, "bit6 does not fire on gp-0x671d == 1"
    assert not wire_byte4(0, 0, 0, 0) & BIT_MASK671D, "bit6 fires on gp-0x671d == 0"
    assert wire_byte4(0, STATE_VALUE, 0, 0) & BIT_STATE4, f"bit5 does not fire on state {STATE_VALUE}"
    assert not wire_byte4(0, 10, 0, 0) & BIT_STATE4, "bit5 fires on state 10 -- that is V70's rung"
    assert wire_byte4(0, 0, THRESHOLD, 0) & BIT_R24_HALF, "bit4 does not fire at exactly +512"
    assert not wire_byte4(0, 0, THRESHOLD - 1, 0) & BIT_R24_HALF, "bit4 fires below +512"
    assert not wire_byte4(0, 0, 0xFFFF, 0) & BIT_R24_HALF, "bit4 fires on -1: the test is UNSIGNED"
    assert wire_byte4(0, 0, 0, CEIL_VALUE) & BIT_ARM3, "bit3 does not fire at CEIL"
    assert not wire_byte4(0, 0, 0, CEIL_VALUE - 1) & BIT_ARM3, "bit3 fires below CEIL"
    for status in range(8):
        assert wire_byte4(0xFF, STATE_VALUE, 0x7FFF, 0xFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
    # the three dispatcher masks, decoded back to state sets so a typo cannot survive review
    assert {s for s in range(16) if (1 << s) & MASK_DETECTOR} == {4, 5, 11}, "0x830 is not {4,5,11}"
    assert {s for s in range(16) if (1 << s) & MASK_AGGREGATOR} == {4, 5, 10, 11}, \
        "0xc30 is not {4,5,10,11}"
    assert {s for s in range(16) if (1 << s) & MASK_ARBITRATION} == {4, 5, 8, 11}, \
        "0x930 is not {4,5,8,11}"
    assert all((1 << STATE_VALUE) & m for m in (MASK_DETECTOR, MASK_AGGREGATOR, MASK_ARBITRATION)), \
        f"state {STATE_VALUE} must be in ALL THREE masks -- bit5 = 1 means the whole chain is running"
    raw = bytes.fromhex(CAVE_HEX)
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, not the 68-byte V71 cave"
    assert CAVE_HEX.endswith("2436e8ea7f00"), "CAVE_HEX does not end in the displaced movea + jmp [lp]"
    # 🛑 Offsets are (address - 0xC4B34), DERIVED from the listing above, not guessed -- an off-by-4
    # checks the wrong halfword and the guard silently passes on a cave that WRITES.
    for off, hw1, disp, what in ((4, "a437", 0x671D, "ld.bu odd-disp"),
                                 (14, "8437", 0x67FA, "ld.bu even-disp"),
                                 (24, "2437", 0x6ADA, "ld.h"),
                                 (36, "8437", 0x671A, "ld.bu even-disp")):
        assert raw[off:off + 2] == bytes.fromhex(hw1), \
            f"CAVE_HEX offset {off} is not a `{what} ...,r6` -- a 0x44../0x64.. hw1 would be a STORE"
        want = (0x10000 - disp) & 0xFFFF
        want = want if hw1 == "2437" else (want | 1)     # ld.bu/ld.hu carry hw2 = disp | 1
        assert raw[off + 2:off + 4] == want.to_bytes(2, "little"), \
            f"CAVE_HEX offset {off} does not carry the displacement -0x{disp:04x}"
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
    n3 = int(np.count_nonzero((b4 & BIT_ARM3) != 0))
    print(f"  bit6 set (📋 pre-registered prediction: 0)     : {n6} / {len(b4)}")
    print(f"  bit3 set (📋 pre-registered prediction: 0)     : {n3} / {len(b4)}")
    if n6:
        print("  ★★ bit6 IS SET. `gp-0x671d != 0` has never been observed non-zero in this kit")
        print("     (V64: 0; V67: 0/186,321 over two routes). If it holds here, the LERP arm never")
        print("     ran, V70's surface dose was MASKED, and V70's null is explained outright.")
    if any((v & BIT_MASK671D) and not (v & BIT_ARM3) for v in vals):
        print("  ✅ EXCLUDED ABSOLUTELY: V70 -- it emits bit6 only with bit3 (x >= +512 implies")
        print("     x >= 0), and this route carries a bit6=1 / bit3=0 frame, which V70 cannot emit.")
    return True


def bit3_is_not_a_sign_bit(m3, fs):
    """★ THE STRONGEST AVAILABLE V70-vs-V71 DISCRIMINATOR, and it is a NEGATIVE test.

    On V71 bit3 is `gp-0x671a >= CEIL` -- a latched reversal counter that integrates 1 kHz
    information and holds >= 50 ms, so it CANNOT toggle quickly. On V70 bit3 was r24's SIGN, which
    toggles with the limit cycle (V70 measured it non-constant). A fast-toggling bit3 therefore means
    the flashed image is V70, not V71.
    🛑 This is a FALSIFIER, not a proof: a quiet bit3 is consistent with V71 AND with several older
    builds. The .rwd filename remains the pre-drive discriminator.
    """
    tog = float(np.count_nonzero(np.diff(m3.astype(np.int8)) != 0)) / (len(m3) / fs)
    print(f"\n  bit3 toggle rate: {tog:.3f} /s   (threshold {FAST_TOGGLE_PER_S:.1f} /s)")
    if tog > FAST_TOGGLE_PER_S:
        print("  🛑 bit3 TOGGLES FAST. On V71 bit3 is a latched counter test that holds >= 50 ms; a")
        print("     rate like this is a SIGN bit, i.e. V70's probe. STOP -- confirm which .rwd is on")
        print(f"     the car before interpreting anything. V71 is: {RWD_NAME}")
        return False
    print("  ✅ consistent with V71's latched-counter rung (falsifier not triggered)")
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
    m4 = (b4 & BIT_R24_HALF) != 0
    m3 = (b4 & BIT_ARM3) != 0
    bit3_is_not_a_sign_bit(m3, fs)

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
    print("★★ READOUT 1 -- WHICH GAIN ARM WAS IN FORCE?  Read bit6 and bit3 FIRST; bit4 is the")
    print("   consequence, not the question. The chain is a strict priority: bit6 outranks the dead")
    print("   `lp` arm, which outranks bit3, which outranks the mode-10 LERP.")
    eps = episodes_of(lat)
    print(f"\n   engaged episodes >= {MIN_SAMPLES} samples: {len(eps)}   "
          f"total {sum(b - a for a, b in eps) / fs:.1f} s")
    ones = np.ones(len(b4), float)
    for label, mask in (("bit6  gp-0x671d != 0  -> arm 1024", m6),
                        ("bit3  gp-0x671a >= 5  -> arm 2048", m3),
                        ("bit4  gp-0x6ada >= +512 (positive control)", m4)):
        pt, (lo, hi) = episode_ratio(eps, mask.astype(float), ones)
        print(f"   {label:<44s} engaged duty {pt:.5f}  [{lo:.5f}, {hi:.5f}]")
    lerp = (~m6) & (~m3)
    pt, (lo, hi) = episode_ratio(eps, lerp.astype(float), ones)
    print(f"   {'=> the mode-10 LERP arm was selected':<44s} engaged duty {pt:.5f}  [{lo:.5f}, {hi:.5f}]")
    n4_on_lerp = int(np.count_nonzero(m4 & lerp & lat))
    n_lerp = int(np.count_nonzero(lerp & lat))
    print(f"\n   bit4 set WHILE on the LERP arm, engaged: {n4_on_lerp} / {n_lerp}")
    if n_lerp and n4_on_lerp == 0:
        print("   🛑🛑 THE ARM-SELECTION EXPLANATION FOR V70'S NULL IS REFUTED. On the LERP branch")
        print("        V71's rung fires at a |dtorque| threshold NO HIGHER than V70's (identical at")
        print("        the 0 km/h breakpoints, up to 2x lower elsewhere). If bit4 is still 0 with no")
        print("        arm selected, the lane output really is below +512 and the problem is")
        print("        UPSTREAM -- dtorque itself, or gp-0x6ada's writer @0x3AD5A not being reached.")
        print("        Probe THOSE next, not the arms.")
    elif n4_on_lerp:
        print("   ✅ the positive control FIRES on the LERP branch ⇒ the lane is live and the dose is")
        print("      being delivered. V70's null was an instrument problem, not a control-path one.")

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
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit("give me one or more rlog paths / route directories")
    raise SystemExit(main(sys.argv[1:]))
