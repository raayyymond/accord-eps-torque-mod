#!/usr/bin/env python3
"""rate_lane_frequency_response.py -- why doubling r24 fixed 21 Hz and could excite ~40-60 Hz.

Mirrors the decompiled arithmetic of the r24 torsion-bar torque-RATE lane exactly, then reads off
what the lane delivers AS DAMPING at each frequency of interest. Standing operator instruction:
integer `>>`, the real Q-format, the real branch conditions, each line annotated with its
instruction address, constants byte-read little-endian. dB/Hz interpretation comes AFTER the code.

THE CHAIN (all addresses byte-verified in _v65_plain_image.bin unless marked)

    producer  FUN_0007e74a                       gp-0x4f62 = 2*(x[n] - x[n-D]) / D
              cal tp+0x7c42 = 0xC6C42 = 4        D = 4 samples          [byte-read: 4]
    consumer  FUN_0003aa2c  r24 lane
              0x3AC16  mov r1,r8                 r1 = clamp(gp-0x4f62, +-5120)
                       mul gain_B,r8             gain_B = Q10 LERP, 2305 at the creep operating point
              0x3AC20  sar 0xa,r8   (STOCK)      >>10       -- V62/V65 patch this to `sar 0x9` = x2
                       deadzone +-3              cal 0xC61F6 = 3        [byte-read: 3]
              0x3AC42  clamp +-8192
    then      ten `add`s at 0x3ACC8-0x3ACDA (NO `sub`), clip +-10240 -> gp-0x6b94

Because every lane enters with `add`, r24 = +Kd * d(T_bar)/dt IN PHASE WITH ASSIST. For the
wheel-inertia-on-torsion-bar mode that is viscous damping and the coefficient is LINEAR in Kd --
which is what V61 (Kd -> 0, WORSE) and V62 (Kd -> 2x, FIXED) measured on-car.

WHAT THIS SCRIPT ADDS: the same lane at a HIGHER frequency. A finite-difference derivative is not a
band-limited operator; its gain RISES with frequency up to fs/(2D). The loop's phase, however, keeps
rotating. Past the point where total loop phase reaches -180 deg, the SAME +Kd term is negative
damping. That is the standard failure mode of a lead compensator and it is the leading hypothesis
for the operator's "grind #2".
"""
import math

FS = 1000.0          # task 1 = 1 kHz, ON-CAR MEASURED (STEER_STATUS=4 dwell; CAN 399 at 100.000 Hz)
D = 4                # cal 0xC6C42, byte-read
DEADZONE = 3         # cal 0xC61F6, byte-read
GAIN_Q10 = 2305      # gain_B at the creep operating point (record 0xD2AEC Y[0])
LANE_CLAMP = 8192    # 0x3AC42
INPUT_CLAMP = 5120   # r1 = clamp(gp-0x4f62, +-5120)

# ---------------------------------------------------------------------------------------------
# 1. THE LITERAL INTEGER LANE -- one tick, exactly as the firmware computes it
# ---------------------------------------------------------------------------------------------

def r24_lane(dtorque_raw: int, gain_q10: int = GAIN_Q10, shift: int = 10, polarity: int = 1) -> int:
    """One tick of FUN_0003aa2c's r24. `shift` is the `sar` immediate: 10 = stock, 9 = V62/V65."""
    d = max(-INPUT_CLAMP, min(INPUT_CLAMP, int(dtorque_raw)))      # r1 clamp
    scaled = (d * gain_q10) >> shift                                # 0x3AC20 (V850 sar: floors)
    if scaled > DEADZONE:
        shaped = scaled - DEADZONE
    elif scaled < -DEADZONE:
        shaped = scaled + DEADZONE
    else:
        shaped = 0
    return max(-LANE_CLAMP, min(LANE_CLAMP, polarity * shaped))     # 0x3AC42


def producer_gp4f62(hist, d: int = D) -> int:
    """FUN_0007e74a: 2*(current - delayed)/sample_delta. hist[-1] is current, hist[-1-d] is delayed."""
    return (2 * (hist[-1] - hist[-1 - d])) // d


# ---------------------------------------------------------------------------------------------
# 2. THE FREQUENCY RESPONSE OF THAT DIFFERENCE -- exact, not a continuous approximation
# ---------------------------------------------------------------------------------------------
# H_diff(f) = (2/D) * (1 - exp(-j*2*pi*f*D/FS))
#   |H| = (4/D) * sin(pi*f*D/FS)              zero at f = FS/D = 250 Hz, peak at FS/(2D) = 125 Hz
#   arg = +90deg - 180*f*D/FS                 a LEAD that decays linearly with frequency

def h_diff(f: float, d: int = D, fs: float = FS) -> complex:
    w = 2.0 * math.pi * f / fs
    return (2.0 / d) * (1.0 - complex(math.cos(w * d), -math.sin(w * d)))


def h_lowpass(f: float, fc: float) -> complex:
    """One real pole. fc = None/inf means no filter."""
    if fc is None or fc == float("inf"):
        return complex(1.0, 0.0)
    return 1.0 / complex(1.0, f / fc)


def damping_component(f: float, kd: float = 1.0, fc=None, d: int = D) -> float:
    """The part of the lane's force that is IN PHASE WITH VELOCITY -- i.e. what actually damps.

    Torsion-bar torque is proportional to relative DISPLACEMENT. Damping needs force at +90 deg
    from displacement. So the damping-effective magnitude is |H| * sin(arg H), and a term that has
    rotated to arg = 0 is a pure SPRING contribution (no damping), while arg < 0 is ANTI-damping.
    """
    h = kd * h_diff(f, d) * h_lowpass(f, fc)
    return abs(h) * math.sin(math.atan2(h.imag, h.real))


def spring_component(f: float, kd: float = 1.0, fc=None, d: int = D) -> float:
    h = kd * h_diff(f, d) * h_lowpass(f, fc)
    return abs(h) * math.cos(math.atan2(h.imag, h.real))


# ---------------------------------------------------------------------------------------------
# 3. THE FREQUENCIES IN PLAY
# ---------------------------------------------------------------------------------------------
# 20.9 Hz  GRIND #1 -- the LKAS-engaged hands-off creep mode. V62 FIXED it. [on-car]
# 41.6 Hz  GRIND #2 candidate -- the 38-46 Hz burst band on V62 route 37.
# 58.9 Hz  THE ALIAS OF 41.6 Hz at the 100.5 Hz bus rate. The bus CANNOT distinguish these two.
#          Reported here so no conclusion silently assumes the lower one.
BANDS = [("grind #1  (20.9 Hz)", 20.9), ("grind #2? (41.6 Hz)", 41.64), ("its alias (58.9 Hz)", 58.86)]


def table(title, rows, headers):
    w = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    print(title)
    print("  " + " | ".join(str(headers[i]).ljust(w[i]) for i in range(len(headers))))
    print("  " + "-+-".join("-" * w[i] for i in range(len(headers))))
    for r in rows:
        print("  " + " | ".join(str(r[i]).ljust(w[i]) for i in range(len(headers))))
    print()


def main():
    # --- self-check: the integer lane reproduces the golden model's asserted values ------------
    assert r24_lane(512) == 1149 or r24_lane(512) == 1150, r24_lane(512)
    # golden model _self_check asserts _inline_torque_rate_b == 1533 at dtorque 512 with gain 3072
    assert r24_lane(512, gain_q10=3072) == 1533, r24_lane(512, gain_q10=3072)
    assert r24_lane(-512, gain_q10=3072) == -1533
    # V62 doubles it exactly
    assert r24_lane(512, gain_q10=3072, shift=9) == 3069  # 2x minus the deadzone, not exactly 2x
    print("self-check OK: the integer lane matches the golden model at dtorque = +-512\n")

    print("=" * 96)
    print("1. WHAT THE FINITE DIFFERENCE ITSELF DOES  (D = %d samples at %.0f Hz)" % (D, FS))
    print("=" * 96)
    print("   zero at fs/D = %.0f Hz, peak at fs/2D = %.0f Hz\n" % (FS / D, FS / (2 * D)))
    rows = []
    for name, f in BANDS:
        h = h_diff(f)
        rows.append([name, f"{abs(h):.4f}", f"{math.degrees(math.atan2(h.imag, h.real)):+.1f}",
                     f"{damping_component(f):.4f}", f"{spring_component(f):+.4f}"])
    table("", rows, ["band", "|H_diff|", "phase deg", "damping part", "spring part"])
    d21, d41 = damping_component(20.9), damping_component(41.64)
    d58 = damping_component(58.86)
    print("  => the lane delivers %.2fx MORE damping-effective gain at 41.6 Hz than at 20.9 Hz," % (d41 / d21))
    print("     and %.2fx more at 58.9 Hz. Doubling Kd doubles ALL of them equally.\n" % (d58 / d21))
    print("  That is the whole problem in one line: V62's x2 is NOT frequency-selective inside")
    print("  this lane. It is only selective against the DRIVER (1 Hz), which is what the V62")
    print("  build note computed (+50 counts at 1 Hz vs +732 at the mode, 14.6:1). Nobody")
    print("  computed the ratio against a HIGHER mode, and that ratio runs the wrong way.\n")

    print("=" * 96)
    print("2. THE DIRTY-DERIVATIVE IDEA -- AND WHY IT DOES NOT WORK ON THIS LANE")
    print("=" * 96)
    print("""   FIRST, A CORRECTION TO SECTION 1's FRAMING. The `damping part` column above uses the
   LANE's own phase and silently assumes the plant adds none. That assumption is REFUTED by
   the on-car record: stock (Kd=1x) produced no grind #2 and Kd=2x did, so at grind #2's
   frequency the r24 term must be net DEstabilising -- which it cannot be with a +60 deg lead
   unless the PLANT contributes enough further lag to carry the loop past -180 deg. The plant
   phase at 40-60 Hz is NOT measured (see section 5: the bus cannot even resolve the frequency).

   => The only phase-agnostic statement available is about MAGNITUDE. Reduce |H| at grind #2's
   frequency, keep the lane's damping-effective term at 20.9 Hz. So the figure of merit is

        SELECTIVITY  =  |H(f2)| / |H(20.9 Hz)|     -- lower is better, and it must fall
                                                      BELOW stock's value to be a real gain
""")
    base21 = damping_component(20.9, kd=1.0, fc=None)   # stock, unfiltered, the normaliser below
    rows = []
    for label, kd, fc in [("stock / V62 / V65   no filter", 1.0, None),
                          ("+ 1 pole  fc = 40 Hz", 1.0, 40.0),
                          ("+ 1 pole  fc = 30 Hz", 1.0, 30.0),
                          ("+ 1 pole  fc = 25 Hz", 1.0, 25.0),
                          ("+ 1 pole  fc = 15 Hz", 1.0, 15.0),
                          ("+ 1 pole  fc = 10 Hz", 1.0, 10.0)]:
        h21 = abs(kd * h_diff(20.9) * h_lowpass(20.9, fc))
        ph21 = math.degrees(math.atan2((kd * h_diff(20.9) * h_lowpass(20.9, fc)).imag,
                                       (kd * h_diff(20.9) * h_lowpass(20.9, fc)).real))
        r = [label]
        for _, f in BANDS[1:]:
            r.append(f"{abs(kd * h_diff(f) * h_lowpass(f, fc)) / h21:6.3f}")
        r.append(f"{ph21:+6.1f}")
        rows.append(r)
    table("   SELECTIVITY |H(f2)|/|H(20.9)|, and the lane's phase left at 20.9 Hz",
          rows, ["configuration", "41.6/20.9", "58.9/20.9", "phase@20.9"])
    print("""  !!! THE DIRTY DERIVATIVE IS DEAD, AND THE REASON IS STRUCTURAL, NOT NUMERIC.
     A differentiator rises at +20 dB/dec; ONE real pole falls at -20 dB/dec. Cascaded, the
     response is FLAT above fc -- so a single pole can at best drive the selectivity toward 1.0
     and can never push it below. Getting it below 1 needs TWO poles, and two poles placed low
     enough to bite by 42 Hz cost ~2 x atan(20.9/fc) of phase at 20.9 Hz: at fc = 20 Hz that is
     -92 deg, which takes the lane's +75 deg lead to -17 deg. The lane would stop being a damper
     at 20.9 Hz entirely -- i.e. it would undo V62, which is the one thing that must not happen.
     Note also that every row above needs Kd raised to restore |H(20.9)|, and raising Kd scales
     f2 by the SAME factor: the selectivity column is what a gain change cannot move.

  => FILTERING THIS LANE CANNOT SEPARATE THE TWO MODES. The separation has to come from a
     variable that DIFFERS between the two symptoms, not from frequency. Two exist:
       (a) MOTOR RATE  -- grind #1 is hands-off creep (low rate); grind #2 requires the driver
           to crank the wheel (high rate). r24's gain is ALREADY a LERP on motor rate
           (X = [0, 400, 1500, 3000]); the breakpoints are CALIBRATION.
       (b) LKAS ENGAGEMENT -- grind #1 is engagement-gated on-car (V58: absent disengaged, 60 s
           moving-but-disengaged control). Grind #2 is reported present with LKAS OFF.
     (a) is cal-only. (b) is what the operator asked for and needs an LKAS-live signal readable
     inside FUN_0003aa2c. They compose.
""")

    print("=" * 96)
    print("3. THE OTHER LEVER THAT LOOKS ATTRACTIVE AND IS NOT: RAISING THE DELAY D")
    print("=" * 96)
    print("   cal 0xC6C42 = 4. Raising D moves the difference's zero DOWN (zero at fs/D), and")
    print("   D = 24 puts an exact zero on 41.67 Hz. That is seductive and it is WRONG:\n")
    rows = []
    for d in (4, 8, 12, 16, 20, 24):
        r = [f"D = {d:2d}  (zero at {FS/d:6.1f} Hz)"]
        for _, f in BANDS:
            h = d * 0 + h_diff(f, d)
            r.append(f"{damping_component(f, 1.0, None, d)/base21:6.3f} @ {math.degrees(math.atan2(h.imag, h.real)):+6.1f}d")
        rows.append(r)
    table("   damping-effective gain (norm. to stock@20.9) @ phase of the difference",
          rows, ["delay", "20.9 Hz", "41.6 Hz", "58.9 Hz"])
    print("  => at D = 24 the difference's phase at 20.9 Hz has fallen to ~0 deg. The term is then")
    print("     a pure SPRING, not a damper -- it stiffens the mode instead of dissipating it, and")
    print("     the 21 Hz damping V62 bought goes to ZERO. RAISING D IS NOT A CANDIDATE FIX.")
    print("     (It is also a shared producer: gp-0x4f62 has other consumers. Blast radius open.)\n")

    print("=" * 96)
    print("4. AMPLITUDE CHECK -- does V62 push r24 into its +-8192 clamp?")
    print("=" * 96)
    print("   Route-37 measured dtorque was 123-839 counts (worst transient 739).")
    rows = []
    for dt in (123, 400, 739, 839, 1820, 3639, 5120):
        rows.append([dt, r24_lane(dt, shift=10), r24_lane(dt, shift=9),
                     "CLAMPED" if abs(r24_lane(dt, shift=9)) >= LANE_CLAMP else ""])
    table("", rows, ["dtorque", "r24 stock", "r24 V62/V65", "note"])
    print("  => at the measured amplitudes V62 is a clean linear x2; the clamp does not bind.")
    print("     So grind #2 is NOT a saturation artefact of the doubling -- it is the LINEAR")
    print("     high-frequency gain rise quantified in section 1.\n")

    print("=" * 96)
    print("5. WHAT THE BUS CANNOT TELL US")
    print("=" * 96)
    print("   The torsion-bar channel is sampled on the 0x14A/0x18F 100 Hz grid => Nyquist 50 Hz.")
    print("   41.64 Hz and 58.86 Hz alias onto each other at fs = 100.5 Hz and are INDISTINGUISHABLE")
    print("   from any rlog. Every row above is therefore given for BOTH, and the fix ranking is")
    print("   the same for both -- a low-pass that kills 41.6 kills 58.9 harder. That is the")
    print("   argument for acting without resolving the ambiguity first.")
    print("   To RESOLVE it needs a firmware-side measurement immune to bus aliasing: count")
    print("   sign changes of the signal at 1 kHz inside the ECU and report the COUNT per 10 ms")
    print("   frame. 5 bits carries 0-31 crossings/10 ms = up to 1550 Hz unambiguously.")


if __name__ == "__main__":
    main()
