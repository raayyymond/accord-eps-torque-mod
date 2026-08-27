"""
studies/models/rate_lane_damping_model.py -- size the torsion-bar RATE lane as a DAMPER, post-V61.

WHY THIS FILE EXISTS
--------------------
V61 zeroed the torsion-bar torque-RATE lane at both taps (r24 and r26) inside FUN_0003aa2c, the 1 kHz
aggregator. On-car 2026-07-31 the ~21 Hz grinding got **significantly WORSE** with LKAS on, and grinding
appeared in MANUAL driving where there was none before -- unmistakably in reverse.

That is a SIGNED result, and it inverts the record. model/eps_lkas_chain_model.py framed r26 as an
"excitation-to-amplifier" (faster slew -> bigger derivative -> bigger r26 -> more motor torque ->
repeat), which predicts that killing it HELPS. It did the opposite. The lane is a DAMPER.

THE SIGN, verified independently (not relayed from a subagent)
-------------------------------------------------------------
  * polarity gp-0x6752 is the literal 1, written at boot in FUN_000490ac (0x490b6-0x490c0), and it is
    the SAME byte scaling boost, r24 and r26.
  * all nine aggregator lanes combine with `add` @0x3acc8-0x3acd8. Not one `sub`.
  => r24, r26 = +Kd * d(bar torque)/dt, added IN PHASE WITH ASSIST.

WHY "in phase with assist" IS DAMPING AND NOT POSITIVE FEEDBACK
---------------------------------------------------------------
Hands-off, the mode is the steering-wheel inertia on the torsion bar. With
    theta_w = wheel angle (J_w, free),  theta_c = column angle (J_c),  bar stiffness k,
    T_b = k*(theta_w - theta_c) = the sensed torque,  phi = theta_w - theta_c,
    motor torque applied to the COLUMN only:  T_m = K*T_b + Kd*dT_b/dt
        J_w*theta_w'' = -T_b
        J_c*theta_c'' = +T_b + T_m - T_road
    phi'' = -k*phi/J_w - (k*phi + K*k*phi + Kd*k*phi' - T_road)/J_c
    ------------------------------------------------------------------
    phi'' + (Kd*k/J_c)*phi' + k*(1/J_w + (1+K)/J_c)*phi = T_road/J_c
    ------------------------------------------------------------------
The phi' coefficient is Kd*k/J_c > 0: POSITIVE DAMPING, linear in Kd. At Kd = 0 the mode has no damping
term at all -- which is V61, and which is what the car did.

🛑 THE LAG MATTERS FOR **BOTH** TERMS -- and carrying it through the Kd term is what explains the
   MEASURED FREQUENCY SHIFT. The first draft of this file only lagged the K term. That was incomplete,
   and an analyst correctly objected that a PURE viscous damper cannot move a resonance frequency
   (omega_d = omega_n*sqrt(1-zeta^2); at Q=15.7 removing damping moves it +0.05%, UPWARD -- while the
   measurement is -12.8%, DOWNWARD). The objection is right and the resolution is below.

Motor torque arrives late by tau, so BOTH terms are evaluated at phi(t-tau), phi'(t-tau). For a sinusoid:
    phi (t-tau) = phi *cos(w*tau) - (phi'/w)*sin(w*tau)
    phi'(t-tau) = phi'*cos(w*tau) + (w*phi) *sin(w*tau)
Substituting T_m = K*k*phi(t-tau) + Kd*k*phi'(t-tau) into the phi equation and collecting:

    DAMPING   coefficient:  (k/J_c) * [  Kd*cos(w*tau)  -  K*sin(w*tau)/w  ]
    STIFFNESS coefficient:  k*(1/J_w + 1/J_c) + (k/J_c) * [ K*cos(w*tau) + Kd*w*sin(w*tau) ]
                                                                            ^^^^^^^^^^^^^^^^
                                                            Kd ALSO ADDS STIFFNESS when lagged.

=> Removing Kd removes that stiffness term, so **omega_n FALLS**. Direction matches the measurement.

★ AND IT MAKES A SHARP, TESTED PREDICTION. For small w*tau, sin(w*tau) ~ w*tau, so
    d(omega_n^2) = Kd*k*w^2*tau/J_c   =>   d(omega_n^2)/omega_n^2 ~ Kd*k*tau/J_c
which is **FREQUENCY-INDEPENDENT**: every mode in the loop must shift by the SAME FRACTION.
MEASURED, V61 vs V59: grinding 21.18 -> 18.32 Hz (x0.865); ratchet 7.73 -> 6.56 Hz (x0.849), or x0.923
speed-restricted. **Two independent modes, same fractional shift.** A purely viscous term cannot produce
that; a LAGGED derivative predicts it exactly. This is the strongest structural evidence in the session.

⚠ Bound on tau, from the AMPLITUDE result rather than assumed: V61 made the mode 2.75-8.3x LOUDER, so Kd
   was supplying REAL damping, so cos(w*tau) must be solidly positive. That rules out w*tau near 90 deg
   (tau ~ 13.7 ms at 18.25 Hz), where the lagged derivative would be pure stiffness and no damping at all.

    zeta_net  ~  (Kd*cos(w*tau) - K*sin(w*tau)/w) * k / (2*J_c*omega)

Stock behaviour pins the operating point: the mode SUSTAINS with no ring-down at all (66 candidate
decays, longest 0.63 cycles) => zeta_net ~ 0 => Kd ~ K*tau. Then:
    V61  (Kd = 0)   => zeta_net ~ -K*tau            < 0   -> diverges. OBSERVED: worse, and in manual too.
    V62  (Kd = 2*Kd) => zeta_net ~ +Kd*k/(2*J_c*w)  > 0   -> decays.   PREDICTION.
Doubling the lane is the smallest edit that moves zeta_net from ~0 to ~ +zeta_lead.

[VERIFIED] the sign, the add order, the polarity byte, every constant below (byte-read LE from
           _v61_plain_image.bin).
[INFERRED] the plant model above -- it is a 2-DOF lumped idealisation, not a measured plant. It predicts
           direction and linearity in Kd, NOT the absolute zeta. Do not quote a dB figure from it.
"""

# ---- constants, all byte-read little-endian from _v61_plain_image.bin -----------------------------
RATE_DELAY_D = 4              # 0xC6C42  -- FUN_0007e74a's sample delay
TASK1_HZ = 1000.0             # FUN_0003aa2c runs on task 1, every tick (FUN_00014be4 rate divider)
SHARED_INPUT_CLAMP = 5120     # @0x3AAAC-0x3AAC0, r1 = clamp(gp-0x4f62, +/-5120)
LANE_OUTPUT_CLAMP = 8192      # +/-0x2000 on r24 and on r26 -- the LARGEST per-lane clamp in the group
                              # (damper gp-0x6bd0 is only +/-0x800, friction gp-0x6b26 +/-0x400)
R24_DEADZONE = 3              # 0xC61F6
R24_GAIN_ARMS = {             # Q10; which arm is live is branch-selected, see the tracer's report
    0xC6440: 2048,            # default arm, assist_state gp-0x671a >= 5
    0xC6442: 1024,            # arm taken when gp-0x671d != 0
    0xC6446: 512,             # arm taken when gp-0x683c != 0
}
R26_OVERRIDES = {0xC6444: 512, 0xC643E: 1536}          # Q10
R26_GAIN_A_Y = {              # Q10, LERP over motor rate gp-0x6ac0, rebuilt each cycle by FUN_0003ad74
    0xC6A68: (3072, 3072, 2434, 2048),
    0xC6A7C: (3072, 3072, 2488, 1536),
    0xC6A90: (2664, 2664, 2243, 1436),
    0xC6AA4: (2560, 2560, 2145, 1331),
}
AGGREGATOR_SUM_CLAMP = 10240  # the sum's own bound, for authority fractions


def _sar(x: int, n: int) -> int:
    """V850 `sar`: arithmetic shift right = floor division, INCLUDING for negatives."""
    return x >> n


def column_torque_rate(bar_counts, f_hz, delay=RATE_DELAY_D, fs=TASK1_HZ):
    """
    FUN_0007e74a: gp-0x4f62 = 2*(x[n] - x[n-delay]) / delta_samples, delay cal tp+0x7c42 = 4.
    It writes a LOCKSTEP PAIR gp-0x4f62 / gp-0x4488 -- so the PRODUCER (and cal 0xC6C42) must not be
    edited without mirroring; V62 does not touch it.
    Peak of the first difference for a sinusoid of amplitude `bar_counts` at f_hz.
    """
    import math
    dt = delay / fs
    diff_peak = 2.0 * bar_counts * math.sin(math.pi * f_hz * dt)   # exact, not the small-angle form
    return _sar(int(2 * diff_peak), 2) if delay == 4 else int(2 * diff_peak / delay)


def r24(rate: int, gain_q10: int, polarity: int = 1) -> int:
    """FUN_0003aa2c r24 lane, mirroring the integer arithmetic exactly."""
    dtorque = max(-SHARED_INPUT_CLAMP, min(SHARED_INPUT_CLAMP, rate))   # 0x3AAAC-0x3AAC0
    scaled = _sar(dtorque * gain_q10, 10)                               # 0x3AC20  sar 0xa,r8
    if scaled > R24_DEADZONE:                                           # 0x3AC24 / 0x3AC2A
        shaped = scaled - R24_DEADZONE
    elif scaled < -R24_DEADZONE:                                        # 0x3AC32 / 0x3AC34 / 0x3AC36
        shaped = scaled + R24_DEADZONE
    else:
        shaped = 0
    out = polarity * shaped                                             # 0x3AC3E  mul r14,r6,r0
    return max(-LANE_OUTPUT_CLAMP, min(LANE_OUTPUT_CLAMP, out))


def r26(rate: int, avg_slope_q10: int, gain_q10: int, polarity: int = 1) -> int:
    """FUN_0003aa2c r26 lane. No deadzone -- near zero rate it is the ONLY live derivative lane."""
    dtorque = max(-SHARED_INPUT_CLAMP, min(SHARED_INPUT_CLAMP, rate))
    stage1 = _sar(dtorque * avg_slope_q10, 10)                          # 0x3AB6C / 0x3AB70
    pre = _sar(stage1 * gain_q10, 10)                                   # 0x3AB72
    out = polarity * pre                                                # 0x3AB7E
    return max(-LANE_OUTPUT_CLAMP, min(LANE_OUTPUT_CLAMP, out))


def clip_multiple(rate: int, gain_q10: int) -> float:
    """At what MULTIPLE of the stock gain does the lane first hit its own +/-8192 clamp?"""
    per_unit = abs(_sar(max(-SHARED_INPUT_CLAMP, min(SHARED_INPUT_CLAMP, rate)) * gain_q10, 10))
    return float("inf") if per_unit == 0 else LANE_OUTPUT_CLAMP / per_unit


# MEASURED bar amplitudes (half of peak-to-peak), routes 31 / 2c, mode-TRACKING band.
# ⚠ These SUPERSEDE the +/-1400 figure this file first used. The V61 drive measured the mode far larger,
# and the strict 18-26 Hz band understated it by 20-29% because the mode had MOVED BELOW that band.
MEASURED_AMPLITUDES = (
    (473,  "V59 engaged creep hands-off, MEDIAN (pp 945)"),
    (1610, "V61 engaged creep hands-off, MEDIAN (pp 3216) -- 3.4x V59"),
    (2726, "V61 engaged creep hands-off, p90  (pp 5451)"),
    (3218, "V61 engaged creep hands-off, p99  (pp 6437)   <-- the BINDING case"),
)
WORST_ARM_GAIN = 3072   # the natural LERP at its stock max: the tightest headroom of the four gain arms


def report(f_hz=18.25):
    print(f"torsion-bar rate lane authority at {f_hz} Hz, delay D={RATE_DELAY_D} @ {TASK1_HZ:.0f} Hz")
    print("MEASURED amplitudes, mode-tracking band. Two gain arms: the state>=5 override (2048) and the")
    print("natural LERP at stock max (3072), which is the WORST case.\n")
    print(f"{'bar amp':>8} {'0x4f62':>8} {'%in':>6} | {'r24@2048':>9} {'%lane':>7} {'clip':>7} "
          f"| {'r24@3072':>9} {'%lane':>7} {'clip':>7}  what")
    for amp, what in MEASURED_AMPLITUDES:
        rate = column_torque_rate(amp, f_hz)
        b2, b3 = r24(rate, 2048), r24(rate, WORST_ARM_GAIN)
        print(f"{amp:>8} {rate:>8} {100*abs(rate)/SHARED_INPUT_CLAMP:>5.1f}% |"
              f" {b2:>9} {100*abs(b2)/LANE_OUTPUT_CLAMP:>6.1f}% {clip_multiple(rate, 2048):>6.1f}x |"
              f" {b3:>9} {100*abs(b3)/LANE_OUTPUT_CLAMP:>6.1f}% "
              f"{clip_multiple(rate, WORST_ARM_GAIN):>6.1f}x  {what}")
    worst = column_torque_rate(MEASURED_AMPLITUDES[-1][0], f_hz)
    m = clip_multiple(worst, WORST_ARM_GAIN)
    print(f"\n=> BINDING CASE: p99 amplitude on the worst gain arm clips at {m:.1f}x stock gain.")
    print(f"   V62 doubles => {200/m:.0f}% of the way to that clamp; {m/2:.1f}x margin remains.")
    print("   ⚠ TIGHTER than the >=3.6x this file first claimed off a +/-1400 assumption. Still linear,")
    print("   but the honest margin at the loudest measured moment on the worst arm is ~2x, not ~4x.")
    print("   V62's purpose is to REDUCE the amplitude, which walks the operating point back UP this")
    print("   table -- the p99 row is V61's pathological case, not V62's expected one.")


if __name__ == "__main__":
    report()
