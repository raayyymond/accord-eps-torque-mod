#!/usr/bin/env python3
"""decode_v69_ratchet.py -- read V69's probe, which is aimed at the RATCHET, not the grinds.

WHAT CHANGED, AND WHY
---------------------
V64/V66/V67/V68 all spent their middle bits on Honda's 1 kHz OSCILLATION DETECTOR -- the gp-0x67df
FSM and the gp-0x671a reversal counter. That instrument is now exhausted in the only way that
matters: **the FSM cell has never been observed non-zero in this kit** (0/53,991 frames on V68,
0/186,321 on V67, straight through the captured 28 Hz burst), and with no positive control that null
is uninterpretable -- it cannot separate "no oscillation" from "detector disabled / input dead /
FUN_000428d4 not reached".

V69 re-aims all three rungs at the RATCHET, on the operator's instruction (2026-08-04). Two reasons
this is the right trade:

  1. ★ THE RATCHET IS THE ONE SYMPTOM THIS CHANNEL CAN RESOLVE. It runs at ~7.4-7.6 Hz, so a
     100.000 Hz probe gets ~13.5 samples per cycle and each bit's OWN TIME SERIES carries the line.
     At grind #1 (21 Hz) and grind #2 (43 Hz) it never could -- those sit at 0.42x and 0.86x of
     Nyquist and every prior probe could only report duty.
  2. The ratchet's own signature says where to look. From the record: waveform SYMMETRIC on every
     build (skew -0.16..+0.06 against a -3.27 sawtooth calibration) => an AMPLITUDE-SATURATED
     RESONANCE, pointing at damping / loop gain; Q ~= 36; creep; ENGAGED; hands-off; NOT the V42
     state-4 governor (`ST == 4` fires 0/37,922). "Symmetric + amplitude-saturated" is the
     describing-function signature of a HARD NONLINEARITY inside the loop.

V65 already killed the obvious one: its 4-level ladder on the aggregator SUM `gp-0x6b94` found
+RAIL 0 / -RAIL 0 over 120,049 frames, with only 54 frames past +/-4096. So the ratchet is not
amplitude-saturated AT THE SUM. What that null never covered is **each lane's OWN nonlinearity
upstream of the sum** -- eight ZERO-type range gates (out-of-window contributes 0, NOT clipped, so a
crossing is a STEP) and two saturating lane clips. None has ever been measured. That is this probe.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7 = 1                    LIVENESS. field == 0 => the cave did not fire => the frame is VOID.
    bit6 = gp-0x6ada >= +4096   *** r24's LANE OUTPUT, after its own +/-0x2000 saturating clip. ***
                                The lane V69 scales, the damping/torque-rate lane the record points
                                at, mirrored to RAM by Honda's own code at 0x3AD5A every 1 kHz tick.
                                🛑 0 READERS / 1 WRITER image-wide -- nothing in the firmware
                                consumes it, so reading it cannot perturb anything even in
                                principle. +4096 is HALF ITS RAIL, so this bit's duty is a direct
                                rail-proximity meter -- and that is how V69's 4x dose gets priced.
    bit5 = gp-0x6b62 >= +4096   *** THE OPERATOR'S OWN RATCHET HYPOTHESIS, never probed in 69
                                builds. *** The return-to-centre lane: FUN_00036388, a slow
                                +/-1/tick accumulator WITH HYSTERESIS, feeding a +/-0x2000 ZERO
                                gate. +4096 is half that gate.
    bit4 = gp-0x6ad4 >= +4096   the UNFILTERED residual / resonance lane (FUN_0003a382: two
                                passthroughs and a RAW derivative on the physical torque sensor,
                                reaching the aggregator directly), into a +/-0x2800 ZERO gate. Its
                                gain is LERP-indexed by gp-0x671a -- Honda's oscillation counter --
                                so this lane closes a loop from the detector back into assist. It is
                                live HANDS-OFF, which the boost lane (driver-torque indexed) is not.
    bit3 = 0                    V69 BUILD-CLASS MARKER.
    bits 2:0                    stock STEER_SENSOR_STATUS, preserved.

🛑 HOW TO READ A NULL ON THIS PROBE -- three residuals, all real.
  (a) ONE-SIDED. Every rung tests the POSITIVE side only; two-sided costs 8 more bytes per rung and
      does not fit in the proven 68-byte cave. For a SYMMETRIC limit cycle the positive half-cycles
      alone still put the 7.4 Hz line in the bit's spectrum -- that is the measurement. But a rung
      reading 0 bounds only that lane's POSITIVE excursions. Never quote a null as two-sided.
  (b) SAMPLED AT 100 Hz AT THE TX HOOK while the aggregator runs at 1 kHz, so a sample can be one
      tick stale relative to the lane evaluation. Immaterial for duty and for a 7.4 Hz line. Do NOT
      use these bits for a per-tick correlation.
  (c) POSITIVE CONTROL. bit6 is expected to fire on any real drive (V69 runs r24 at 4x, and the lane
      rails at |dtorque| ~683 against a repo-recorded max of 839). If bit6 ALSO reads 0.000%, the
      most likely reading is that the cave is not the one you think -- check bit7 and the .rwd name
      BEFORE interpreting bit5/bit4. That ordering is the V64 lesson, applied.
  ⚠ bit5 and bit4 have NO established positive control. If they read 0, that is a bound on those
      lanes' positive excursions and NOT a demonstration that the instrument works.

🛑 ONE FIRMWARE PRECONDITION MAKES ALL THREE BITS MEANINGFUL, and it is an IMAGE fact, not a wire
fact -- so it is asserted at BUILD time (`verify_v69_image.py`) and only recorded here.
FUN_0003aa2c has a REDUCED aggregator mode: when `gp-0x67ac == 1` it sums the LKAS lane and
gp-0x6b62 ONLY, skipping six sibling lanes AND both inline r24/r26 lanes. In that mode bit6 and bit4
would be reporting lanes that are not in the sum at all. It is unreachable on this ROM: the selector
traces to the per-source TYPE array (cal **0xC4124** = [0,0,5,0,5,5,0,0,0,5,0]), which never matches
the qualifying literals {2,3,4}, so gp-0x67ac is always 0 and the FULL path always runs. Every V69
build asserts that table byte-for-byte and refuses to emit if a slot ever reads 6 or 7.

Usage:  python decode_v69_ratchet.py <route-dir-or-segment-paths...>
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
# ⚠ The NUMERIC MACHINERY is shared with V67's decoder on purpose -- collect/gate_stats/sustained
# are instrument code, not semantics, and two copies would drift. Everything V69-SPECIFIC (the bit
# map, the identification, the ratchet statistic, the verdict) is defined here and nowhere else.
from decode_v67_gate import (collect, dominant_hz, gate_stats, runs_of,        # noqa: E402
                             sustained, transitions)

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v69_tva.assert_decoder_matches() fails the BUILD if
# this string is not byte-for-byte the cave in the built artifact. V66's decoder header was stale for
# one revision and claimed bit4 = gp-0x683c when the image read gp-0x67fe; this is the fix for that
# class of error. Do not edit by hand -- rebuild and copy.
CAVE_HEX = "203e800024372695ac326132b605273e400024379e94ac326132b605273e200024372c95ac326132b605273e10008437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e8000  movea 0x80,r0,r7        bit7 LIVENESS, bit3 CLEAR = the V69 build class
#   0xC4B38  24372695  ld.h -0x6ada[gp],r6   | ac32 sar 0xc,r6 | 6132 cmp 0x1,r6 | b605 | movea 0x40
#   0xC4B46  24379e94  ld.h -0x6b62[gp],r6   | ac32 sar 0xc,r6 | 6132 cmp 0x1,r6 | b605 | movea 0x20
#   0xC4B54  24372c95  ld.h -0x6ad4[gp],r6   | ac32 sar 0xc,r6 | 6132 cmp 0x1,r6 | b605 | movea 0x10
#   0xC4B62  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B6C  4437ecea  st.b  r6,-0x1514[gp]     THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B70  2436e8ea  movea -0x1518,gp,r6     the displaced hook instruction
#   0xC4B74  7f00      jmp [lp]                -> 0x55C12
# 🛑 `ld.h` is opcode 0x39 and `st.h` is 0x3B -- ONE BIT apart. gp-0x6ada's only real instance
# (@0x3AD5A) *is* the st.h form and carries the same displacement halfword. If you ever see hw1
# 0x64.. instead of 0x24.. here, the cave WRITES the aggregator's lanes. Do not flash it.
# ⚠ 66 of the 68 proven cave bytes are used; 2 spare. A fourth rung needs 14. The extent is NOT
# grown -- caves are this kit's only bricking class (V24, V27, V48B all bricked the ECU).

BIT_LIVE = 0x80
BIT_R24, BIT_RTC, BIT_RES = 0x40, 0x20, 0x10
BIT_CLASS = 0x08              # *** CONSTANT 0 on V69. The build-class marker. ***
PROBE_MASK = 0xF8
THRESHOLD = 4096              # every rung: ld.h -> sar 0xc -> cmp 0x1  =>  cell >= 1 << 12

# (bit, short name, gp cell, that lane's own hard nonlinearity, what a 1 means)
RUNGS = (
    (BIT_R24, "bit6 gp-0x6ada", 0x6ADA, 0x2000,
     "r24 lane OUT, top half of its +/-8192 saturating clip -- 0 readers image-wide"),
    (BIT_RTC, "bit5 gp-0x6b62", 0x6B62, 0x2000,
     "return-to-centre lane at half its +/-8192 ZERO gate -- THE OPERATOR'S HYPOTHESIS"),
    (BIT_RES, "bit4 gp-0x6ad4", 0x6AD4, 0x2800,
     "unfiltered residual/resonance lane at 40% of its +/-10240 ZERO gate"),
)

# The ratchet, from docs/STATE.md. These are the numbers the verdict is scored against.
RATCHET_LO_HZ, RATCHET_HI_HZ = 6.0, 9.0
RATCHET_F0 = 7.56             # route 2c: 7.56 +/- 0.36 Hz, within-run sd 0.07-0.10 Hz, Q ~= 36
CREEP_MAX_MS = 4.0            # the ratchet is a creep symptom (1-4 m/s in the recorded episodes)
HANDS_OFF_TQ = 300            # |sustained torsion-bar| below which the recorded episodes sit

LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_R24) for b in (0, BIT_RTC) for c in (0, BIT_RES)}
ON_WIRE = {b | 0x07 for b in LEGAL}       # as transmitted, with all three status bits set

# 🛑 ONE LINE, deliberately. The builder asserts this exact basename appears in this file; splitting
# it across a string concatenation makes the substring vanish and the check silently harder to pass.
RWD_NAME = "39990-TVA,A160-V69-LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-gainB-rec0rec1-x4-ratchetprobe-can330byte4-0x13000-0x100000.rwd"  # noqa: E501

# TIER 1 -- builds whose ENTIRE reachable payload space is disjoint from V69's. Absolute exclusion.
#   V53 emits only 0x07; V54 only 0x0F (bit7 clear); V68 ASSERTS bit3 is set on every frame it emits
#   and measured it at 100.000% over 53,991 frames -- and V68 is the image on the car before V69.
STRUCTURALLY_DISJOINT = {
    "V53": {0x07},
    "V54": {0x0F},
    "V68 (bit3 CONSTANT 1 -- asserted by the build, measured 53,991/53,991)":
        {0x8F | a | b | c for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)},
}
# 🛑 TIER 2 -- AND THIS IS A REAL LIMIT, NOT A FORMALITY. V66 and V67 also emit bit3 = 0, and their
# bits 5:4 were measured 0 over 186,321 frames, so their reachable payloads {0x87, 0xC7} are a
# SUBSET of V69's. V69-vs-V66/V67 is therefore NOT structural: it rests on bit5 or bit4 ever firing,
# plus the flashed .rwd filename. Two builds back, so the practical risk is a mis-flash of an old
# file -- accepted and stated, not hidden.
SUBSET_RISK = {"V66/V67 (bits 5:4 measured 0 over 186,321 frames)": {0x87, 0xC7}}


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 8, f"{len(LEGAL)} legal payloads, expected 8"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert all(b & BIT_CLASS == 0 for b in LEGAL), "a legal payload has bit3 SET -- that is V68"
    assert sum(b for b, _, _, _, _ in RUNGS) | BIT_LIVE | BIT_CLASS == PROBE_MASK, \
        "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    for name, space in STRUCTURALLY_DISJOINT.items():
        assert not (space & ON_WIRE), f"{name} is not actually disjoint from V69's payload space"
    for name, space in SUBSET_RISK.items():
        assert space <= ON_WIRE, f"{name} is not a subset -- re-derive the identification"
    # the cave hex must be an even number of bytes and end in the `jmp [lp]` epilogue
    assert len(CAVE_HEX) % 2 == 0 and CAVE_HEX.endswith("2436e8ea7f00"), "CAVE_HEX is malformed"
    assert len(bytes.fromhex(CAVE_HEX)) == 66, "CAVE_HEX is not the 66-byte V69 cave"
    # 🛑 the three loads must all be ld.h (hw1 0x2437), never st.h (0x6437) -- see the header
    raw = bytes.fromhex(CAVE_HEX)
    for off in (4, 18, 32):
        assert raw[off:off + 2] == bytes.fromhex("2437"), \
            f"CAVE_HEX offset {off} is not an `ld.h ...,r6` -- 0x6437 would be an st.h, a WRITE"


_self_check()


def identify(b4):
    """Which build produced this payload stream? Reported at its real strength, in two tiers."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    illegal = int(np.count_nonzero([(v & PROBE_MASK) not in LEGAL for v in b4]))
    print(f"  VOID (probe field == 0, the cave did not fire) : {void} / {len(b4)}")
    print(f"  ILLEGAL (outside V69's 8 legal payloads)        : {illegal} / {len(b4)}")
    if void or illegal:
        print("  🛑 STOP. A VOID or ILLEGAL frame means the flashed image is not this build, or the")
        print("     cave did not run. Do not interpret any bit below until this is 0.")
        return False
    bit3 = np.count_nonzero((b4 & BIT_CLASS) != 0)
    print(f"  bit3 (V69 build class, must be 0)               : {bit3} / {len(b4)} set")
    if bit3:
        print("  🛑 bit3 is SET -- this is V68, not V69.")
        return False
    for name, space in STRUCTURALLY_DISJOINT.items():
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    for name, space in SUBSET_RISK.items():
        overlap = vals & space
        print(f"  ⚠ NOT excluded structurally: {name} -- its payloads {sorted(hex(v) for v in space)}"
              f" are a SUBSET of V69's")
        if vals - space:
            print(f"     ...but this route emits {sorted(hex(v) for v in vals - space)}, which that "
                  "build cannot ⇒ excluded EMPIRICALLY on this route.")
        else:
            print("     🛑 and this route emits NOTHING outside that subset ⇒ V69 is NOT confirmed "
                  "from the probe. Confirm the flashed .rwd filename before proceeding:")
            print(f"     {RWD_NAME}")
    return True


MIN_SAMPLES = 128
# 🛑 128, NOT 256, AND THE REASON IS A REAL BUG THIS FILE SHIPPED. The split-half null below halves
# each episode before scoring it. Route 4f's ratchet episodes are 268-462 samples, so with a
# 256-sample minimum EVERY HALF FAILED, the null came back n = 0 / floor = NaN, and the verdict
# table printed "0 / 9" -- which reads as a clean negative but is a TAUTOLOGY: nothing can exceed
# NaN. A gate that cannot fail informatively is the V64 lesson, and it was sitting in the scorer.
# 128 samples = 1.28 s = 0.78 Hz resolution, so 6-9 Hz still spans ~4 bins. Corrected 2026-08-04
# from `analysis-2020accord/r4f_v69_readout.py`, which also adds the matched negative control that
# `matched_null()` below now implements.


def ratchet_line(mask, fs):
    """The ratchet statistic: is there a 6-9 Hz line in THIS BIT's own 100 Hz time series?

    A bit is a square wave, so its spectrum carries the fundamental of whatever gates it. At 7.4 Hz
    on a 100.000 Hz grid that is ~13.5 samples/cycle -- resolvable, unlike 21 or 43 Hz.
    Returns (peak Hz, prominence) over the band, or (nan, nan) if the bit never toggles.
    """
    mask = np.asarray(mask, bool)
    if mask.sum() in (0, len(mask)) or len(mask) < MIN_SAMPLES:
        return float("nan"), float("nan")
    x = mask.astype(float)
    x = x - x.mean()
    w = np.hanning(len(x))
    P = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    band = (f >= RATCHET_LO_HZ) & (f <= RATCHET_HI_HZ)
    # background = the 2-20 Hz median EXCLUDING the band, so a real line cannot inflate its own floor
    bg = (f >= 2.0) & (f <= 20.0) & ~band
    if not band.any() or not bg.any():
        return float("nan"), float("nan")
    i = np.argmax(P[band])
    floor = np.median(P[bg])
    return float(f[band][i]), float(P[band][i] / floor) if floor > 0 else float("nan")


def analog_line(x, fs):
    """The SAME 6-9 Hz statistic on a CONTINUOUS channel (bar torque / angle rate).

    ★ WHY THIS EXISTS. Every probe bit on route 4f was CONSTANT, so `ratchet_line` returned NaN for
    all of them -- and a null on a bit is only interpretable if the SYMPTOM was present. The analog
    channels answer that: route 4f's ratchet cell carries 7.56 Hz at 2,823 counts p-p in four
    episodes, which is what turned "0.0000%" from uninterpretable into a real one-sided bound.
    """
    x = np.asarray(x, float)
    if len(x) < MIN_SAMPLES or not np.isfinite(x).all() or x.std() == 0:
        return float("nan"), float("nan")
    x = x - x.mean()
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    band = (f >= RATCHET_LO_HZ) & (f <= RATCHET_HI_HZ)
    bg = (f >= 2.0) & (f <= 20.0) & ~band
    floor = np.median(P[bg])
    i = np.argmax(P[band])
    return float(f[band][i]), float(P[band][i] / floor) if floor > 0 else float("nan")


def matched_null(chans, outside, fs, lengths, draws=400, seed=69):
    """★ THE NEGATIVE CONTROL the split-half null is not: same-length windows from OUTSIDE the cell.

    A split-half null is contaminated by its own signal -- halving an episode that contains the
    line leaves the line in both halves, so it floors HIGH and understates a detection. This draws
    matched-length windows from engaged-but-not-in-the-cell time, where a generic-roughness 6-9 Hz
    line would also live. Use max(split_half_95, matched_95) as the floor: conservative for a
    DETECTION claim, which is the direction that matters.
    """
    rr = [ab for ab in runs_of(outside) if ab[1] - ab[0] >= MIN_SAMPLES]
    if not rr or not lengths:
        return []
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        a, b = rr[rng.integers(len(rr))]
        L = min(int(lengths[rng.integers(len(lengths))]), b - a)
        if L < MIN_SAMPLES:
            continue
        s0 = a + int(rng.integers(0, b - a - L + 1))
        for ch in chans:
            _, p = analog_line(ch[s0:s0 + L], fs)
            if np.isfinite(p):
                out.append(p)
    return out


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

    tq, rate, sca = d["tq"], d["rate"], d["sca"]
    v = d.get("v", np.full(len(b4), np.nan))
    lat = d.get("lat", np.zeros(len(b4), bool))
    sus = np.abs(sustained(tq, fs))

    cells = (
        ("WHOLE ROUTE", np.ones(len(b4), bool)),
        ("engaged", np.asarray(lat, bool)),
        ("engaged + creep", np.asarray(lat, bool) & (v <= CREEP_MAX_MS)),
        ("engaged + creep + hands-off  ⇐ THE RATCHET'S OWN CELL",
         np.asarray(lat, bool) & (v <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)),
        ("manual (disengaged)", ~np.asarray(lat, bool)),
    )

    print("\n" + "=" * 102)
    print("PER-BIT DUTY AND TOGGLE RATE")
    for bit, name, disp, win, what in RUNGS:
        mask = (b4 & bit) != 0
        print(f"\n  {name}  >= +{THRESHOLD}   (that lane's own hard nonlinearity: ±0x{win:04X})")
        print(f"    {what}")
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

    print("\n" + "=" * 102)
    print("THE RATCHET TEST -- a 6-9 Hz line in a bit's own series, against a SPLIT-HALF NULL")
    print("🛑 The null is computed FIRST, from the same data, by splitting each run in half and")
    print("   scoring half against half. A prominence is only a detection if it clears that floor.")
    print("   (Bootstrap over EPISODES, not windows -- window bootstraps shrink CIs by ~sqrt(n) and")
    print("    manufacture significance. Standing instruction, 2026-08-02.)")
    sel = np.asarray(lat, bool) & (v <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ)
    rr = [ab for ab in runs_of(sel) if ab[1] - ab[0] >= 256]
    print(f"\n  ratchet-cell episodes of >= 2.56 s: {len(rr)}   "
          f"total {sum(b - a for a, b in rr) / fs:.1f} s")
    if not rr:
        print("  🛑 NO EPISODES. This route cannot speak to the ratchet in either direction.")
        print("     The recorded episodes are hands-off + ENGAGED + CREEP with |angle| 9-133 deg.")
        print("     Route 2b failed exactly this test and the operator said so before the data did.")
    else:
        # ★ STEP 0 -- WAS THE SYMPTOM EVEN PRESENT? If the analog channels carry no 6-9 Hz line in
        # the cell, this route cannot speak to the ratchet and NOTHING below is interpretable.
        chans = (tq, rate)
        lengths = [b - a for a, b in rr]
        mnull = matched_null(chans, np.asarray(lat, bool) & ~sel, fs, lengths)
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
              f"⚠ contaminated by its own signal, floors HIGH")
        print(f"  NULL 2 matched OUTSIDE the cell (n={len(mnull):4d}): 95th {f_match:8.2f}   "
              f"⇐ the clean negative control")
        print(f"  ⇒ FLOOR = max(NULL1, NULL2) = {floor:.2f}  (conservative for a DETECTION claim)")
        an_hits, an_pks = 0, []
        for a, b in rr:
            p_tq, _ = analog_line(tq[a:b], fs)
            v = max(analog_line(ch[a:b], fs)[1] for ch in chans)
            if np.isfinite(v) and v > floor:
                an_hits += 1
                an_pks.append(p_tq)
        med_an = float(np.median(an_pks)) if an_pks else float("nan")
        print(f"\n  ★ SYMPTOM PRESENT? analog bar-torque / angle-rate 6-9 Hz line above the floor "
              f"in {an_hits} / {len(rr)} episodes, median {med_an:.2f} Hz "
              f"(recorded ratchet {RATCHET_F0} Hz)")
        if not an_hits:
            print("    🛑 NO ANALOG LINE ⇒ the ratchet did not occur in this route's cell. Every")
            print("       per-bit null below is then a bound on nothing. Do not interpret it.")
        else:
            n_fr = sum(b - a for a, b in rr)
            print(f"    ⇒ the symptom IS present over {n_fr} frames / {n_fr / fs:.2f} s "
                  f"(~{med_an * n_fr / fs:.0f} cycles). The per-bit nulls below are REAL "
                  f"one-sided bounds.")
        print(f"\n  {'bit':<18s} {'episodes with a 6-9 Hz line above the null':>44s}  "
              f"{'median pk Hz':>13s}")
        for bit, name, _d, _w, _t in RUNGS:
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
        print("     on a CONSTANT bit is a statement about the bit, not a failed test. Read it with")
        print("     the duty table and the SYMPTOM PRESENT line above, never alone.")
        print("  🛑🛑 bit4 gp-0x6ad4 IS STRUCTURALLY VACUOUS AT THIS THRESHOLD -- FUN_0003a382's")
        print("     output is clamped to +/-CEILING = min of three LERPs, and cal 0xC67C8's max is")
        print("     1024, so |gp-0x6ad4| <= 1024 EVERYWHERE and <= 341 at creep. It can never reach")
        print("     +4096. See analysis-2020accord/v70_rung_reachability.py. bit5 is NOT vacuous")
        print("     (gp-0x6b62 reaches +/-8192).")

    print("\n" + "=" * 102)
    print("THE 4x DOSE, PRICED ON-CAR -- bit6 is a rail-proximity meter on the lane V69 scales")
    m6 = (b4 & BIT_R24) != 0
    for label, s in cells:
        n = int(np.count_nonzero(s))
        if n >= 64:
            print(f"  {label:<52s} r24 lane >= +4096 in {np.count_nonzero(m6[s]) / n:7.4f} of "
                  f"{n / fs:6.1f} s")
    print("  🛑 r24 clamps at +/-8192 and V69's peak gain 12288 rails it at |dtorque| ~683, against")
    print("     a repo-recorded max |dtorque| of 839 (margin 0.81x) and 511 on the two V68 routes")
    print("     (1.33x). A HIGH bit6 duty at creep is the 4x dose running into its own rail --")
    print("     the one metric on which V69 is worse than V68, disclosed rather than buried.")
    print("  ⚠ Every |dtorque| figure in this kit is a LOWER BOUND: CAN's 50 Hz Nyquist hides")
    print("     content whose contribution to the real gp-0x4f62 is still RISING through that band.")

    print("\n" + "=" * 102)
    print("FLIGHT SAFETY")
    st = Counter(int(x) & 0x07 for x in b4)
    print(f"  STEER_SENSOR_STATUS (payload bits 2:0) histogram: {dict(st)}")
    print("  🛑 ST == 4 and ST == 3 must be counted from the RAW 0x18F stream as well as the grid --")
    print("     V68 confirmed flight-clean two ways and that is the standard. See the handoff.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
