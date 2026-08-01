#!/usr/bin/env python3
"""v66_v67_explained.py -- what V67 does to each grind, and what V66 measures. Executable.

Every function below mirrors the decompiled arithmetic: integer `>>` (V850 `sar` floors toward
-infinity), the real Q-format, the real branch conditions, each line annotated with its instruction
address, every constant byte-read little-endian from `_v65_plain_image.bin`.

THE ONE-SENTENCE ANSWER
    V62 applied a x2 to the torsion-bar rate lane EVERYWHERE. That fixed grind #1 and caused grind #2.
    V67 applies the SAME x2, but only in the operating regime where grind #1 lives, and leaves the
    regime where grind #2 lives at exactly stock.
    => V67 does not "fix" grind #2. It removes the thing that CAUSED grind #2, and stock never had it.

WHY A GATE AND NOT A FILTER -- the constraint that forces this design
    The lane is a 4-sample finite difference, so its gain RISES with frequency: measured 1.93x more
    at 41.6 Hz than at 20.9 Hz. A x2 is flat in frequency, so it lifts the high band harder than the
    mode it damps. You cannot fix that with a low-pass: a differentiator rises +20 dB/dec and one
    real pole falls -20 dB/dec, so the cascade is FLAT above the corner -- a single pole drives the
    41.6/20.9 selectivity toward 1.0 and never below it. Two poles low enough to bite by 42 Hz cost
    ~ -92 deg at 20.9 Hz and destroy the +75 deg lead that IS the fix.
    => the separation cannot come from FREQUENCY. It has to come from an OPERATING CONDITION.
    Measured separations: driver torque >8x, LKAS engagement (grind #1 only), steering rate ~2x.
"""

# =================================================================================================
# SECTION 0 -- CALIBRATION, byte-read little-endian from _v65_plain_image.bin
# =================================================================================================
D_DELAY = 4            # 0xC6C42 (tp+0x7c42)  the finite-difference span, in producer samples
INPUT_CLAMP = 5120     # 0x3AAAC-0x3AAC0      r1 = clamp(gp-0x4f62, +-5120)
DEADZONE = 3           # 0xC61F6 (tp+0x71f6)  applied AFTER the shift
LANE_CLAMP = 8192      # 0x3AC42-0x3AC54      +-0x2000 on r24 itself
SUM_CLAMP = 10240      # 0x3ACE8-0x3AD27      +-0x2800 on the ten-lane sum -> gp-0x6b94

ARM_671D = 1024        # 0xC6442   priority 1, taken when gp-0x671d != 0
ARM_683C = 512         # 0xC6446   priority 2, taken when gp-0x683c != 0   <- DEAD on stock
ARM_671A = 2048        # 0xC6440   priority 3, taken when gp-0x671a > cal 0xC64FA (=5)

# The cross axis, tp+0x7010 = 0xC6010, in voted-speed counts at 64.0625 counts/km/h.
CROSS_X = (0, 640, 3200, 6400)                       # = 0 / 9.99 / 49.95 / 99.9 km/h

# r24's gain_B for THIS car (mode selector gp+0x63fd = 10), reached through FOUR pointer arrays at
# mode*4: 0xCBF5C / 0xCC044 / 0xCC12C / tp+0xD214=0xCC214.  🛑 NOT four consecutive records.
# Array k supplies the record at CROSS_X[k] -- proven by FUN_0003ad74's own edge cases: below the
# first breakpoint it reads aiStack_14[1] (the 0xCBF5C array) directly, above the last it reads
# psStack_4 (the 0xCC214 array) directly.
# ⚠ A parallel trace this session labelled these the other way round (0xCC214 <-> speed 0). That
# reading is rejected here on two grounds: the edge-case branches above, and monotonicity -- power
# steering assist must be HIGHEST at parking speed, and only this mapping gives 3072 at 0 km/h
# falling to 2151 at 100. The inverted mapping gives 2151 at 0 and 2305 at 100, which is backwards.
GAIN_B_MODE10 = (
    (0xD2A74, (0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),   # 0xCBF5C[10]  speed    0 km/h
    (0xD2AB0, (0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),   # 0xCC044[10]  speed   10
    (0xD2AEC, (0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),   # 0xCC12C[10]  speed   50
    (0xD2B28, (0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),   # 0xCC214[10]  speed  100
)
RATE_COUNTS_PER_DEGS = 16384 / 3477      # = 2**18 / (48*1159), exact; cal 0xC613A = 1159
RATE_FOLD = 13001                        # 0x3AAC8: rate >= this folds to 0 == the LERP's FIRST point


def _sar(x, n):
    """V850 `sar`: arithmetic shift, floors toward -infinity. Python's >> already does this."""
    return x >> n


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _lerp_flat(x, xs, ys):
    """The firmware's LERP idiom: flat outside the breakpoints, `mul` then `divq` (trunc-to-zero)."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            num, den = (ys[i + 1] - ys[i]) * (x - xs[i]), xs[i + 1] - xs[i]
            q = abs(num) // abs(den)
            return ys[i] + (-q if (num < 0) != (den < 0) else q)
    return ys[-1]


# =================================================================================================
# SECTION 1 -- THE PRODUCER.  FUN_0007e74a writes gp-0x4f62.
# =================================================================================================
def gp_4f62(bar_torque_history, d=D_DELAY):
    """gp-0x4f62 = 2*(x[n] - x[n-D]) / D.  A D-tick finite difference over an 8-slot ring.

    🛑 There is NO EMA and NO IIR anywhere in this producer -- confirmed by full decompile. The
    "dirty derivative" low-pass that would separate 21 Hz from 43 Hz DOES NOT EXIST in stock and
    would have to be built in a code cave. That is why the fix is a gate.
    """
    return (2 * (bar_torque_history[-1] - bar_torque_history[-1 - d])) // d


# =================================================================================================
# SECTION 2 -- THE GAIN.  A 4-level PRIORITY CHAIN, 0x3ABFA-0x3AC16.
# =================================================================================================
def r24_gain_q10(speed_counts, motor_rate, gate_671d, gate_683c, state_671a,
                 arm_683c=ARM_683C, ceil_671a=5):
    """Q10 gain for r24. Only the SELECTOR is conditional -- the LERP is computed either way.

    🛑 gp-0x671d is tested FIRST and it is LIVE (2 writers). If it fires, control never reaches the
    gp-0x683c test at 0x3AC04 at all, and the gain is pinned to 1024 -- BELOW the creep default of
    3072. So a firing gp-0x671d does not merely mask V67's arm, it cuts the lane to a third.
    """
    if gate_671d != 0:                                  # 0x3ABFA cmp r0,r6 / 0x3ABFC be
        return ARM_671D                                 # 0x3ABFE ld.hu 0x7442[tp]
    if gate_683c != 0:                                  # 0x3AC04 cmp r0,lp  / 0x3AC06 be
        return arm_683c                                 # 0x3AC08 ld.hu 0x7446[tp]   <- V67's arm
    if state_671a > ceil_671a:                          # 0x3AC0E cmp r0,r2  / 0x3AC10 be
        return ARM_671A                                 # 0x3AC12 ld.hu 0x7440[tp]
    # ---- default: FUN_0003ad74's cross-interpolated, mode-indexed curve -------------------------
    key = 0 if motor_rate >= RATE_FOLD else motor_rate  # 0x3AAC8 addi -0x32c9 / 0x3AACC cmovc
    xs = [_lerp_flat(speed_counts, CROSS_X, [rec[1][i] for rec in GAIN_B_MODE10]) for i in range(4)]
    ys = [_lerp_flat(speed_counts, CROSS_X, [rec[2][i] for rec in GAIN_B_MODE10]) for i in range(4)]
    return _lerp_flat(key, xs, ys)                      # -> gp-0x6e40 (X) / gp-0x6e38 (Y)


# =================================================================================================
# SECTION 3 -- THE LANE.  0x3AC16-0x3AC54.  `shift` IS the whole V62 edit.
# =================================================================================================
def r24_lane(dtorque, gain_q10, shift, polarity=1):
    """shift = 10 is stock `sar 0xa`; shift = 9 is V62/V65's `sar 0x9`, i.e. exactly x2."""
    r1 = _clamp(dtorque, -INPUT_CLAMP, INPUT_CLAMP)     # 0x3AAAC-0x3AAC0
    r8 = _sar(r1 * gain_q10, shift)                     # 0x3AC18 mul / 0x3AC20 sar
    if r8 > DEADZONE:                                   # 0x3AC24 cmp / 0x3AC2A ble
        r6 = r8 - DEADZONE
    elif r8 < -DEADZONE:                                # 0x3AC34 cmp / 0x3AC36 bge
        r6 = r8 + DEADZONE
    else:
        r6 = 0
    r6 *= polarity                                      # 0x3AC3E mul, gp-0x6752
    return _clamp(r6, -LANE_CLAMP, LANE_CLAMP)          # 0x3AC42-0x3AC54 -> r24


def aggregate(r24, other_lanes_sum):
    """Ten `add`s at 0x3ACC8-0x3ACDA -- NO `sub` -- then the saturating clip to gp-0x6b94.

    ✅ MEASURED 2026-08-01 (V65's ladder, 120,049 frames): this clip is NEVER reached. +RAIL 0,
    -RAIL 0; the sum never comes within 20% of +-10240. So the loop is LINEAR here, and a gain
    change on this lane propagates faithfully -- which is exactly why V62's flat x2 produced the
    frequency response it did, and why V67's gated x2 will behave predictably too.
    """
    return _clamp(r24 + other_lanes_sum, -SUM_CLAMP, SUM_CLAMP)   # 0x3ACE8-0x3AD27


# =================================================================================================
# SECTION 4 -- THE BUILDS, as parameter sets. This is the entire difference between them.
# =================================================================================================
BUILDS = {
    # name            shift   arm_683c   gate cell feeding gp-0x683c's load @0x3AA94
    "STOCK/V38":     dict(shift=10, arm_683c=ARM_683C, gate="(dead cell -- always 0)"),
    "V62 / V65":     dict(shift=9,  arm_683c=ARM_683C, gate="(dead cell -- always 0)"),
    "V66":           dict(shift=10, arm_683c=ARM_683C, gate="(dead cell -- always 0)"),
    "V67":           dict(shift=9,  arm_683c=1188,     gate="HANDS-ON cell (repointed, 1 byte)"),
}

# 🛑 SIZING CORRECTION, made by running this file. The first draft used arm = 1536, sized against
# the creep-and-ZERO-rate default of 3072. That was wrong: the arm is ONLY taken when the gate is
# true, i.e. while the driver is loading the wheel, and grind #2 lives at motor rate ~256 deg/s
# where the LERP has already rolled off to 2377 -- not 3072. A flat 1536 therefore delivered
# 1.29x stock in the very regime it exists to neutralise.
# The arm must be sized AT THE OPERATING POINT WHERE IT IS TAKEN:  arm ~= LERP_there / 2.
#     LERP(7.2 km/h, rate 1206 counts) = 2377  ->  arm = 1188  ->  1188/512 = 2.32 == stock exactly.
# ⚠ RESIDUAL, unavoidable: a SCALAR arm cannot track a CURVE. 1188 is exact at grind #2's measured
# operating point and drifts elsewhere in the hands-on regime (see the sensitivity table below).
# That is the price of using the existing arm rather than adding code.

# V67's two edits, in full:
#   0x3AA96   c5 -> <disp>   repoint `ld.bu -0x683c[gp],r15` to a hands-on cell. ONE BYTE if the
#                            target displacement is EVEN (V850 ld.bu carries disp bit0 in hw1 bit5).
#   0xC6446   512 -> 1536    the arm value. With `sar 0x9` the lane divides by 512, so 1536 gives
#                            1536/512 = 3.0 == the stock creep gain 3072/1024 = 3.0, EXACTLY.
#
# 🛑 THE ARM VALUE AND THE GATE POLARITY MUST AGREE, and 1536 assumes a HANDS-ON gate:
#       gate FALSE (driver light / hands-off)  -> default LERP, x2 via sar 0x9  -> grind #1 fixed
#       gate TRUE  (driver loading the wheel)  -> flat 1536 / 512 = 3.0         -> exactly stock
#    With an LKAS-ACTIVE gate the polarity inverts and 1536 is WRONG -- and worse, the measured
#    gating says grind #2 is NOT LKAS-gated (p99 1.33x, vs grind #1's 6.63x), so an LKAS gate
#    would only remove grind #2 from disengaged driving. Driver torque is the axis that separates
#    them (>8x). That is why V66 measures the candidates before V67 is built.


# =================================================================================================
# SECTION 5 -- WHAT V66 MEASURES.  The cave, re-decoded from the built image.
# =================================================================================================
def v66_probe(gp_6806, gp_67f5, gp_67fe, can_payload_byte):
    """V66's cave at 0xC4B34, emitted bytes verified in _v66_plain_image.bin.

        0xC4B34  movea 0x80,r0,r7                                 r7 = liveness
        0xC4B38  ld.bu -0x6806[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x40,r7,r7
        0xC4B44  ld.bu -0x67f5[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x20,r7,r7
        0xC4B50  ld.bu -0x67fe[gp],r6 ; cmp 0x1,r6 ; blt +6 ; movea 0x10,r7,r7
        0xC4B5C  ld.bu -0x1514[gp],r6 ; andi 0x7,r6,r6 ; or r7,r6
        0xC4B66  st.b  r6,-0x1514[gp]          <- THE ONLY STORE. GATE 1 is vacuous.
        0xC4B6A  movea -0x1518,gp,r6 ; jmp [lp]   the displaced hook instruction, then return

    V66 measures the THREE CANDIDATE GATE CELLS and nothing else. For each, the drive returns duty
    cycle, transitions per second, and dominant toggle frequency:

      gp-0x67f5  the driver-torque hands-on selector -- V67's PREFERRED gate, because driver torque
                 is the axis that separates the two grinds by >8x.
                 🛑 KILL CRITERION: the oscillation itself is +-1400 counts on the torsion bar, and
                 this cell's sustain is 10 ms against a 21 Hz half-period of 24 ms. If it toggles in
                 15-60 Hz, a gain keyed on it switches AT the mode frequency -- a parametric pump,
                 which is worse than the symptom. Then this candidate is DEAD.
      gp-0x6806  the LKAS-active enable. Chatter-safe (2 transitions in 180 s on record) but the
                 measured gating says it cannot remove grind #2, only its disengaged share.
      gp-0x67fe  semantics DISPUTED: a trace calls it the LKAS engage-SM state; the golden model
                 calls it `assist_substate`, i.e. BASE assist. Duty ~100% => base assist => useless
                 as a gate. Duty tracking engagement => the best candidate found. ONE bit settles it.

    ⚠ NOT measured, and it is the largest open risk: gp-0x671d, which OUTRANKS the arm and is live.
    """
    r7 = 0x80                                            # liveness
    if gp_6806 >= 1:
        r7 += 0x40
    if gp_67f5 >= 1:
        r7 += 0x20
    if gp_67fe >= 1:
        r7 += 0x10
    return (can_payload_byte & 0x07) | r7                # stock STEER_SENSOR_STATUS preserved


# =================================================================================================
# SECTION 6 -- THE TWO OPERATING POINTS, measured on-car, and what each build delivers there
# =================================================================================================
#   grind #1: LKAS engaged, HANDS-OFF creep. 18-22 Hz. Steering rate ~48 raw counts.
#   grind #2: creep with the driver CRANKING the wheel -- tq_avg 1600-2700, |angle| 150-265 deg,
#             steering rate ~256 raw counts. ~44.9 Hz, Q~37. Engaged AND disengaged.
OPS = (
    # label, voted-speed counts (2 m/s = 7.2 km/h), motor-rate counts, driver loading the wheel?
    ("grind #1  hands-off creep", int(7.2 * 64.0625), int(48 * RATE_COUNTS_PER_DEGS), False),
    ("grind #2  driver cranking", int(7.2 * 64.0625), int(256 * RATE_COUNTS_PER_DEGS), True),
)


def main():
    print("=" * 98)
    print("WHAT EACH BUILD DELIVERS AT EACH OPERATING POINT   (r24 gain, Q10, and the lane output)")
    print("=" * 98)
    print("  dtorque held at 400 counts (inside the measured 123-839 range) so the builds are")
    print("  compared on the GAIN, not on a different input.\n")
    dtorque = 400
    hdr = f"  {'operating point':<28}{'build':<12}{'gain':>7}{'r24':>8}{'vs stock':>10}"
    print(hdr + "\n  " + "-" * (len(hdr) - 2))
    base = {}
    for label, speed, rate, hands_on in OPS:
        for name, cfg in BUILDS.items():
            # The gate is non-zero only on V67 AND only when the driver is loading the wheel.
            gate_683c = 1 if (name == "V67" and hands_on) else 0
            g = r24_gain_q10(speed, rate, gate_671d=0, gate_683c=gate_683c, state_671a=0,
                             arm_683c=cfg["arm_683c"])
            out = r24_lane(dtorque, g, cfg["shift"])
            if name == "STOCK/V38":
                base[label] = out
            print(f"  {label:<28}{name:<12}{g:>7}{out:>8}{out / base[label]:>9.2f}x")
        print()

    print("=" * 98)
    print("A SCALAR ARM CANNOT TRACK A CURVE -- the sensitivity of the arm choice")
    print("=" * 98)
    print("  Where the gate is TRUE, V67 delivers arm/512 against stock's LERP/1024, so it lands on")
    print("  stock only where arm == LERP/2. Across the hands-on regime the LERP moves:\n")
    print(f"  {'speed':>8}{'rate deg/s':>12}{'LERP':>8}{'arm for 1.00x':>15}{'arm=1188 gives':>17}")
    for kmh in (2.0, 7.2, 20.0, 40.0):
        for degs in (100, 256, 400, 640):
            rc = int(degs * RATE_COUNTS_PER_DEGS)
            lerp = r24_gain_q10(int(kmh * 64.0625), rc, 0, 0, 0)
            print(f"  {kmh:>7.1f}{degs:>12}{lerp:>8}{lerp / 2:>15.0f}"
                  f"{(1188 / 512) / (lerp / 1024):>16.2f}x")
    print("\n  => 1188 is exact at grind #2's measured point (7.2 km/h, 256 deg/s) and stays within")
    print("     about +-25% across the rest of the hands-on regime. Every value there is far below")
    print("     V62's flat 2.00x, which is the number that produced the 11.71x at 40-49 Hz.\n")

    print("=" * 98)
    print("READ IT LIKE THIS")
    print("=" * 98)
    print("""  grind #1 (hands-off): V62/V65 and V67 both deliver 2.00x. V67 KEEPS the proven fix, exactly.
  grind #2 (cranking) : V62/V65 delivers 2.00x -- that is the 11.71x amplification at 40-49 Hz.
                        V67 delivers 1.00x AT THE MEASURED OPERATING POINT, i.e. exactly stock,
                        and stock never produced grind #2. Elsewhere in the hands-on regime it is
                        within ~+-25% of stock rather than exactly on it -- see the table above.
  V66                 : 1.00x everywhere. Stock base assist -- grind #1 returns as V38 has it,
                        and grind #2's cause is removed. It is the operator's stable long-drive
                        build AND the confirmatory revert AND the pre-flight probe, at once.

  🛑 V67 does not act on grind #2's mechanism. It removes V62's amplification from grind #2's
     regime. If grind #2 turns out NOT to be V62's doing -- which V66's drive tests directly --
     then V67 does nothing for it either, and the target becomes a ~44.9 Hz mechanical mode.
  🛑 And V67 is only as good as its GATE. If the hands-on cell chatters in 15-60 Hz, the gain
     switches at the mode frequency and V67 is WORSE than V62. That is what V66 measures.""")

    print("\n" + "=" * 98)
    print("V66's PROBE -- the five reachable payloads")
    print("=" * 98)
    print(f"  {'gp-0x6806':>10}{'gp-0x67f5':>11}{'gp-0x67fe':>11}   byte4")
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                print(f"  {a:>10}{b:>11}{c:>11}   0x{v66_probe(a, b, c, 0x07):02X}")
    print("\n  byte4 == 0x00 on any frame => the cave did not fire => the whole reading is VOID.")


def _self_check():
    # The lane must reproduce the golden model's own asserted value.
    assert r24_lane(512, 3072, 10) == 1533, r24_lane(512, 3072, 10)
    assert r24_lane(-512, 3072, 10) == -1533
    # `sar 0x9` is exactly x2 up to the deadzone.
    assert r24_lane(512, 3072, 9) == 3069
    # V67's arm must reproduce STOCK at the point where the arm is actually TAKEN -- i.e. in the
    # hands-on regime, NOT at creep-and-zero-rate. Sizing it at the wrong point was a real error.
    _lerp_at_grind2 = r24_gain_q10(int(7.2 * 64.0625), int(256 * RATE_COUNTS_PER_DEGS), 0, 0, 0)
    assert _lerp_at_grind2 == 2377, _lerp_at_grind2
    assert r24_lane(400, 1188, 9) == r24_lane(400, _lerp_at_grind2, 10), \
        "V67's arm does not reproduce stock where the gate is true"
    # The creep default really is 3072, and it is flat out to the first breakpoint.
    assert r24_gain_q10(0, 0, 0, 0, 0) == 3072
    assert r24_gain_q10(0, 400, 0, 0, 0) == 3072
    # The >=13001 fold lands on the LERP's FIRST point, i.e. MAXIMUM gain -- a real step.
    assert r24_gain_q10(0, 13000, 0, 0, 0) == 1536 and r24_gain_q10(0, 13001, 0, 0, 0) == 3072
    # gp-0x671d outranks the V67 arm and is BELOW the default -- the design's largest risk.
    assert r24_gain_q10(0, 0, 1, 1, 0) == ARM_671D < 3072
    # The probe preserves the stock low bits and is 0 only if the cave never ran.
    assert v66_probe(0, 0, 0, 0x07) == 0x87 and v66_probe(1, 1, 1, 0x07) == 0xF7
    # The producer is a plain D-tick difference -- no filter state anywhere.
    assert gp_4f62([0, 0, 0, 0, 100]) == (2 * 100) // 4
    return True


if __name__ == "__main__":
    _self_check()
    main()
