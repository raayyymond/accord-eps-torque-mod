#!/usr/bin/env python3
"""v70_rail_describing_function.py -- does V69's +-0x2000 rail explain grind #1 at CREEP?

Mirrors FUN_0003aa2c's r24 lane exactly (integer >>, real branch order, LE cals), then asks the
only question the rail can answer: at what oscillation amplitude does V69's EFFECTIVE (describing-
function) gain fall below V62's, and below stock's?

The lane, instruction by instruction (stock image, verified in Ghidra by the orchestrator):

    0x3AAC4  ld.hu -0x6ac0[gp],r11      motor rate
    0x3AAC8  addi -0x32c9,r11,r0        \\ zero it at >= 13001
    0x3AACC  cmovc 0x0,r11,r13          /
    0x3AAAC  addi -0x1400,r14,r0        \\ dtorque = clamp(gp-0x4f62, +-5120)
    0x3AAB8  addi  0x1400,r14,r0        /   -> r1
    0x3ABBA..0x3ABF8                    LERP(r13) over the RAM table at gp-0x6e40  -> r10
    0x3ABFA  cmp r0,r6 / be 0x3AC04     gp-0x671d != 0 ?
    0x3ABFE    ld.hu 0x7442[tp],r10       -> 1024   (masking arm; OUTRANKS the gate arm)
    0x3AC04  cmp r0,lp / be 0x3AC0E     the GATE  (gp-0x683c stock/V69 ; gp-0x6806 on V67/V68)
    0x3AC08    ld.hu 0x7446[tp],r10       -> the ARM, REPLACING the LERP entirely
    0x3AC0E  cmp r0,r2  / be 0x3AC16
    0x3AC12    ld.hu 0x7440[tp],r10
    0x3AC16  mov r1,r8
    0x3AC18  mul r10,r8,r0              r8 = dtorque * gain
    0x3AC20  sar 0xa,r8                 >> 10          <- V62 moved this to 0x9 (and 0x3AB76)
    0x3AC1C  ld.hu 0x71f6[tp],r12       deadzone cal 0xC61F6 = 3, applied BEFORE the clamp
    0x3AC3E  mul r14,r6,r0              * polarity gp-0x6752
    0x3AC42..0x3AC54                    clamp +-0x2000
    0x3AD5A  st.h r24,-0x6ada[gp]       the mirror V69's probe bit6 reads (0 readers / 1 writer)
"""
import math

DTORQUE_CLAMP = 0x1400   # 5120, cal-free, 0x3AAAC/0x3AAB8
OUT_CLAMP     = 0x2000   # 8192, 0x3AC42-0x3AC54
DEADZONE      = 3        # cal 0xC61F6, byte-read LE


def r24_lane(dtorque: int, gain_q10: int, sar: int = 10, polarity: int = 1) -> int:
    """Integer-exact, in the real order. `sar` is 10 stock / 9 on V62-V65."""
    d = max(-DTORQUE_CLAMP, min(DTORQUE_CLAMP, dtorque))       # 0x3AAAC / 0x3AAB8
    r8 = (d * gain_q10) >> sar                                  # 0x3AC18 / 0x3AC20
    if r8 > DEADZONE:                                           # 0x3AC24-0x3AC2E
        r6 = r8 - DEADZONE
    elif r8 < -DEADZONE:                                        # 0x3AC32-0x3AC3C
        r6 = r8 + DEADZONE
    else:
        r6 = 0
    r6 *= polarity                                              # 0x3AC3E
    return max(-OUT_CLAMP, min(OUT_CLAMP, r6))                  # 0x3AC42-0x3AC54


def rail_at(gain_q10: int, sar: int = 10) -> float:
    """Smallest |dtorque| whose lane output reaches the +-8192 rail."""
    return (OUT_CLAMP + DEADZONE) * (1 << sar) / gain_q10


def df_ratio(amp: float, a_sat: float) -> float:
    """Describing-function gain of a saturating element, relative to its own linear gain."""
    if amp <= a_sat:
        return 1.0
    m = a_sat / amp
    return (2.0 / math.pi) * (math.asin(m) + m * math.sqrt(1.0 - m * m))


# gain_q10 actually in force, by build, on the r24 lane -------------------------------------
# stock rec0 Y0/Y1 = 3072 (0xD2A7E/80); rec1 = 2561 (0xD2ABA/BC); rec2 Y0 = 2305 (0xD2AF6).
# All byte-verified LE against the shipped _v*_plain_image.bin snapshots.
BUILDS = {
    "stock            (0 km/h)":  dict(gain=3072,  sar=10),
    "V62/V65  sar 0x9 (0 km/h)":  dict(gain=3072,  sar=9),    # x2 via the shift, arm-agnostic
    "V67/V68 arm=5244 (engaged)": dict(gain=5244,  sar=10),   # arm REPLACES the LERP, any speed
    "V67/V68          (manual)":  dict(gain=3072,  sar=10),   # gate closed -> stock LERP
    "V69     rec0=12288 (creep)": dict(gain=12288, sar=10),   # x4, BOTH arms
    "V69              (>=50 km/h)": dict(gain=2305, sar=10),  # rec2/rec3 untouched == stock
}

print("=" * 78)
print("RAIL THRESHOLD -- smallest |dtorque| that saturates the +-8192 lane clamp")
print("=" * 78)
print(f"{'build':<30}{'gain_q10':>10}{'sar':>5}{'rails at |dtorque|':>22}")
for name, p in BUILDS.items():
    print(f"{name:<30}{p['gain']:>10}{p['sar']:>5}{rail_at(p['gain'], p['sar']):>22.1f}")

print()
print("  cross-check against the repo's own recorded figures:")
print(f"    V67 arm 5244 -> {rail_at(5244):.1f}   (record: 1601, incl. the 3-count deadzone) ")
print(f"    V69 x4 12288 -> {rail_at(12288):.1f}   (record: 683)")
print(f"    x2      6144 -> {rail_at(6144):.1f}   (record: 1366)")

# ------------------------------------------------------------------------------------------
# The question: V69 at creep is 4x LINEAR but rails at 683. Where does saturation take its
# effective gain below V62's and below stock's? Compare FUNDAMENTAL output amplitude.
STOCK_G, V62_G, V69_G = 3072, 3072, 12288
A_STOCK, A_V62, A_V69 = rail_at(STOCK_G, 10), rail_at(V62_G, 9), rail_at(V69_G, 10)

print()
print("=" * 78)
print("EFFECTIVE (describing-function) GAIN vs OSCILLATION AMPLITUDE, at creep")
print("relative to STOCK at the same amplitude -- 1.00 means 'no better than stock'")
print("=" * 78)
print(f"{'|dtorque| amp':>14}{'stock':>10}{'V62 x2':>10}{'V69 x4':>10}   note")
NOTE = {
    683:  "V69 starts to rail",
    839:  "<- repo-recorded MAX |dtorque| (a LOWER BOUND)",
    1366: "V62 x2 starts to rail",
    2732: "stock starts to rail",
    3477: "<- V69 finally falls to stock",
    5120: "the +-5120 input clamp; nothing exists above this",
}
for amp in [200, 400, 683, 839, 1200, 1366, 2000, 2732, 3477, 4200, 5120]:
    s = STOCK_G * df_ratio(amp, A_STOCK)
    v62 = (V62_G * 2) * df_ratio(amp, A_V62)
    v69 = V69_G * df_ratio(amp, A_V69)
    print(f"{amp:>14}{s / s:>10.2f}{v62 / s:>10.2f}{v69 / s:>10.2f}   {NOTE.get(amp, '')}")

# Does V69's curve EVER cross stock's? Scan the whole reachable domain rather than assuming.
worst = min(((V69_G * df_ratio(a, A_V69)) / (STOCK_G * df_ratio(a, A_STOCK)), a)
            for a in [1 + 0.5 * i for i in range(2 * DTORQUE_CLAMP)])
print()
print(f"  minimum of V69/stock over the ENTIRE reachable domain |dtorque| in [1, {DTORQUE_CLAMP}]:")
print(f"    {worst[0]:.3f}x  at |dtorque| = {worst[1]:.0f}")
print(f"  repo-recorded max |dtorque| = 839  ->  V69 still delivers "
      f"{V69_G * df_ratio(839, A_V69) / (STOCK_G * df_ratio(839, A_STOCK)):.2f}x stock damping there.")
print()
print("=" * 78)
print("VERDICT -- THE CREEP-SATURATION HYPOTHESIS IS ELIMINATED, AT EVERY AMPLITUDE")
print("=" * 78)
print("""
Stock and V69 share the SAME +-8192 rail. Saturation therefore compresses the two toward
each other but can never invert them: as amplitude grows both outputs tend to the same
(4/pi)*8192 fundamental, so V69/stock decays monotonically toward 1.0 FROM ABOVE and never
crosses it. The minimum over the entire reachable input domain is printed above -- it is
> 1. At the corpus's recorded max |dtorque| = 839, V69 still delivers ~3.6x stock damping.

=> "V69's 4x rails the lane, so the damping collapsed and grind #1 came back at creep" is
   ARITHMETICALLY IMPOSSIBLE as stated. The rail is real, and it does mean V69 delivers less
   than its nominal 4x during large transients -- but never less than stock, and never less
   than V62's flown 2x by more than the same compression applies to V62 itself.

!! WHAT THIS DOES *NOT* EXCLUDE, stated so it is not read as more than it is:
   (a) The describing function captures the FUNDAMENTAL gain only. A hard saturation inside a
       loop also generates harmonics and can support jump/limit-cycle behaviour that no linear
       gain change produces. This analysis bounds the gain, NOT the nonlinear dynamics.
   (b) Every |dtorque| figure in this kit is a LOWER BOUND -- CAN's 50 Hz Nyquist hides content
       the 1 kHz finite difference is still rising through. The amplitudes above are what the
       instrument can see.
   (c) It says nothing about the >=50 km/h regime, where V69 is byte-identical to stock and no
       saturation argument is needed at all.
""")
