"""
studies/models/eps_feedback_path_coverage.py
=======================================================================================================
The torsion-bar feedback surface has TWO paths, and V52C could only ever reach one of them.

🛑 CORRECTION, 2026-07-31 — an earlier draft of this file was titled "Why V52C HALVED the grinding."
V52C did NOT halve anything. "Halved the mode" is the FILTER'S OWN TRANSFER FUNCTION (|H(20.9 Hz)| =
0.4963 = -6.08 dB) quoted inside a caveat about why V52C's NULL was weak evidence, then restated two
handoffs later as a positive on-car result. V52C's on-car outcome, in the operator's words, was:
"V52C did not fix the vibration; it clearly changed manual driving feel." A NULL. No V52C rlog exists.
See memory/accord/instruments/accord-a-caveat-can-mutate-into-a-result.md.

Context. The grinding requires LKAS to be APPLYING torque (V58 route 2b: prominence 122.7x engaged vs
3.6x disengaged, 60 s moving-but-disengaged control). The leading explanation is a feedback loop through
the torsion bar: motor torque twists the column -> the sensor reads the twist as driver input -> assist
boosts it -> more motor torque. V52C is the ONLY build ever flashed on that feedback path, and it had the
largest single effect of ~55 builds.

Everything below is byte-verified against _v59_plain_image.bin by a raw little-endian scan (V850 is LE),
with each hit confirmed to carry base-register field == r4 (gp). Site addresses are instruction addresses.

    gp = 0xFEDF8000   ->  gp-0x4f60 = torsion-bar column torque (Sensor B), disp16 0xB0A0, 69 sites
                          gp-0x4f62 = its RATE (first difference),          disp16 0xB09E,  9 sites

🛑 Frequency/dB interpretation comes AFTER the integer code, never instead of it (standing operator
instruction, 2026-07-28).
=======================================================================================================
"""

# --- V52C's repoint set, read from builds/v50_v79/build_v52c_tva.py: BASE(7) + EXTRA(3) + BROAD(9) = 19 sites -------
V52C_REPOINTED = {
    0x2C480: "FUN_0002c478 type-8",
    0x354D2: "FUN_000352b4 magnitude",
    0x35AA4: "FUN_000352b4 magnitude",
    0x3A6CA: "FUN_0003a382 resonance",
    0x3A7CA: "FUN_0003a382 resonance",
    0x3B4A8: "FUN_0003b49a -> FUN_0003a382",
    0x3B672: "FUN_0003b66a damping+boost Factor-A",
    0x2F318: "FUN_0002eda8 branch A",
    0x2F330: "FUN_0002eda8 branch B",
    0x2F33E: "FUN_0002eda8 branch C",
    0x29A90: "FUN_00028ea6 arbitration LERP select",
    0x2B69E: "FUN_0002b62c EMA/corridor blend",
    0x2DF32: "FUN_0002db94 LERP boost/damping blend",
    0x33D2A: "FUN_00033d10 float PID",
    0x3F8E2: "FUN_0003f884 angle integrator",
    0x3FCC6: "FUN_0003fc16 angle integrator",
    0x36682: "FUN_00036682 own EMA fc=0.94 Hz",
    0x36846: "FUN_00036828 + DTC-0x23 rate check",
    0x3B908: "FUN_0003b8f6 degenerate biquad (~236 Hz)",
}

# --- the gp-0x4f62 RATE path: 9 sites, none of them in V52C's set ------------------------------------
RATE_SITES = {
    0x02C4E8: ("read", "FUN_0002c478 type-8 lane"),
    0x03AA9C: ("read", "AGGREGATOR FUN_0003aa2c -- the inline r24/r26 torque-rate lanes"),
    0x03B6A8: ("read", "FUN_0003b66a -> the FIR producing gp-0x6b9a / gp-0x6ba6 (boost amplitude index)"),
    0x07E7E0: ("read", "FUN_0007e74a producer"),
    0x07E7EC: ("store", "FUN_0007e74a producer"),
    0x07E854: ("read", "FUN_0007e74a producer"),
    0x07E860: ("store", "FUN_0007e74a producer"),
    0x07F436: ("read", "FUN_0007f3f8 producer"),
    0x07F442: ("store", "FUN_0007f3f8 producer"),
}
# The producer's INPUT: a gp-0x4f60 read at 0x07E78E, inside FUN_0007e74a, immediately preceding its
# gp-0x4f62 read/store pair. builds/v50_v79/build_v52c_tva.py leaves it RAW deliberately, classified as part of "the
# FUN_0007f3f8 A/B cross-check" health gate.
RATE_PRODUCER_INPUT = 0x07E78E

RATE_SAMPLE_DELAY = 4      # tp+0x7c42 (= 0xC6C42); golden model records 4 producer samples [VERIFIED]
# Confirmed live by byte decode: 0x07E7D8 is `ld.hu tp+0x7c42` -- hw1 0x87E5 (base-register field
# r5 == tp), hw2 0x7C43 == 0x7C42|1, the ld.hu displacement idiom. Two further reads at 0x07E7F6/0x07E7FA.

# --- ★★ THE RATE HAS ITS OWN SHADOW-LOCKSTEP TWIN, and it never leaves the producer -------------------
# Byte-scanned on _v59_plain_image.bin, base-register field == r4 (gp) on every hit:
#     gp-0x4f60  VALUE          disp16 0xB0A0   69 sites, image-wide
#     gp-0x4486  VALUE shadow   disp16 0xBB7A   15 sites, ALL within 0x7F2D4..0x7FD1E (producer region)
#     gp-0x4f62  RATE           disp16 0xB09E    9 sites  (3 consumers + 6 producer-local)
#     gp-0x4488  RATE shadow    disp16 0xBB78    8 sites, ALL within 0x7E7E4..0x7F44C (producer region)
# 0x4f60-0x4486 == 0x4f62-0x4488 == 0xADA: an identical offset, i.e. one matched shadow-pair
# architecture applied to both cells. Both producers maintain their pair in lockstep -- load rate+shadow
# (0x07E7E0/0x07E7E4), store both (0x07E7EC/0x07E7F0); same at 0x07F436/0x07F43A -> 0x07F442/0x07F446.
#
# ⇒ LOAD-BEARING SAFETY CONSEQUENCE: the RATE shadow has ZERO sites outside the producer functions, so
# the three downstream consumers are NOT shadow-checked. Repointing THOSE THREE to a filtered copy
# cannot desync a lockstep monitor -- the same argument V52C used for the value path, and cleaner here
# (8 producer-local shadow sites vs the value path's 15). It also says the safe shape of any rate-path
# intervention is: filter a COPY, repoint the 3 consumers, and leave BOTH producers and BOTH shadows
# untouched. Do NOT repoint the producer's input read at 0x07E78E -- that feeds the lockstep pair, and
# an asymmetric raw-vs-filtered split across a monitor is the V27 brick class.
# ⚠ Static disp16 clearance is NOT sufficient on its own (gp-0x1500 passed two static methods and still
# failed on-car). The 6-byte extended-displacement encoding and register-indirect/table-dispatched
# access must both be swept before this is treated as closed.
VALUE_SHADOW = 0x4486
RATE_SHADOW = 0x4488
SHADOW_OFFSET = 0xADA
RATE_CONSUMERS_NOT_SHADOW_CHECKED = (0x02C4E8, 0x03AA9C, 0x03B6A8)


def v52c_ema(x_new: int, y_prev: int, alpha: int = 74) -> int:
    """V52C's first-order EMA on the torsion bar, as integer arithmetic.

    ⚠ CORRECTED 2026-07-31: an earlier draft here omitted the `addi 512` and so implemented V50's
    arithmetic, not V52C's. V50's floor-rounding was ASYMMETRIC (step 0 for d in [0,+13] but -1 already
    at d = -1) -> a ~-7-count DC bias and a one-way ratchet. V52C's `addi 512` @0xC4B62 makes it
    round-half-up, which is the whole point of the C revision.

        y[n] = y[n-1] + ((alpha * (x[n] - y[n-1]) + 512) >> 10)    alpha = 74 (Q10) => 0.07227

    Cave instructions: ld.h gp-0x1300 @0xC4B48 / ld.h gp-0x4f60 @0xC4B4C / sub @0xC4B50 /
    shift-add *74 @0xC4B52..0xC4B60 (64+8+2; NOT mulhi, which would truncate the s17 d to 16 bits) /
    addi 512 @0xC4B62 / sar 10 @0xC4B66 / add @0xC4B68 / st.h gp-0x1300 @0xC4B6A.

    DEADBAND: the step is 0 iff -512 <= alpha*d < 512, i.e. |d| <= 511/alpha -- a SYMMETRIC dead zone of
    +/-(512/alpha) counts, NOT the 1024/alpha of the floor version. At alpha=74 that is +/-6 counts.
    """
    return y_prev + ((alpha * (x_new - y_prev) + 512) >> 10)


def ema_response(alpha: int, f_hz: float, fs_hz: float):
    """Magnitude and phase of y[n] = y[n-1] + (alpha/1024)*(x[n]-y[n-1]), i.e. a 1-pole low-pass."""
    import cmath
    import math
    a = alpha / 1024.0
    z = cmath.exp(-2j * math.pi * f_hz / fs_hz)
    h = a / (1.0 - (1.0 - a) * z)
    return abs(h), math.degrees(cmath.phase(h))


def differencer_response(delay_samples: int, f_hz: float, fs_hz: float):
    """Magnitude of the RATE producer's first difference y[n] = x[n] - x[n-delay].

    |H(f)| = |1 - exp(-j*2*pi*f*delay/fs)| = 2*|sin(pi*f*delay/fs)|
    This is a DERIVATIVE: +20 dB/decade. It is exactly the shape that turns a small high-frequency
    ripple on the torsion bar into a large contribution downstream.
    """
    import math
    return 2.0 * abs(math.sin(math.pi * f_hz * delay_samples / fs_hz))


def coverage_report(fs_hz: float = 1000.0, f_mode: float = 20.9, f_ref: float = 1.0) -> dict:
    """What V52C attenuated, what it did not, and by how much at the mode frequency."""
    import math

    mag_v, ph_v = ema_response(74, f_mode, fs_hz)                 # the VALUE path, as V52C shipped it
    d_mode = differencer_response(RATE_SAMPLE_DELAY, f_mode, fs_hz)
    d_ref = differencer_response(RATE_SAMPLE_DELAY, f_ref, fs_hz)

    return {
        "sample_rate_hz": fs_hz,
        "mode_hz": f_mode,
        "value_path_v52c": {
            "alpha_q10": 74,
            "fc_hz": round(-fs_hz * math.log(1 - 74 / 1024.0) / (2 * math.pi), 2),
            "gain_at_mode": round(mag_v, 4),
            "dB_at_mode": round(20 * math.log10(mag_v), 2),
            "phase_deg_at_mode": round(ph_v, 1),
        },
        "rate_path_untouched": {
            "delay_samples": RATE_SAMPLE_DELAY,
            "gain_at_mode": round(d_mode, 4),
            "gain_at_%gHz" % f_ref: round(d_ref, 4),
            "emphasis_mode_vs_ref": round(d_mode / d_ref, 1),
            "live_consumers_outside_producer": [
                hex(a) for a, (k, _) in RATE_SITES.items() if k == "read" and a < 0x07E000
            ],
        },
        "coverage": {
            "v52c_repointed_sites": len(V52C_REPOINTED),
            "rate_sites_repointed_by_v52c": len(set(RATE_SITES) & set(V52C_REPOINTED)),
            "rate_producer_input_repointed": RATE_PRODUCER_INPUT in V52C_REPOINTED,
        },
    }


def tracking_lag(alpha: int, amp: int, f_in_hz: float, fs_hz: float = 1000.0) -> int:
    """Peak |x - y| the assist would see, simulating the EXACT integer kernel.

    ★ This -- not the dead zone -- is the dominant manual-feel cost of a feedback-path low-pass, and it
    scales in direct proportion to the attenuation bought. Recorded driver torque: ~2166 counts hands-on
    and ~328 hands-off (route 13, creep).
    """
    import math
    y, worst = 0, 0
    n = int(6 * fs_hz / f_in_hz)
    for i in range(n):
        x = int(amp * math.sin(2 * math.pi * f_in_hz * i / fs_hz))
        y = v52c_ema(x, y, alpha)
        if i > n // 3:
            worst = max(worst, abs(x - y))
    return worst


def stronger_filter_sweep(fs_hz: float = 1000.0, f_mode: float = 20.9):
    """Attenuation vs added lag vs dead zone vs TRACKING LAG, for a range of alphas.

    🛑 THREE costs, not one, and the third is the binding one:
      1. PHASE. Already -56.5 deg at V52C's alpha=74 and asymptotic to -90; going much stronger buys a
         lot of attenuation for little extra phase. Cheaper than it looks.
      2. DEAD ZONE = +/-(512/alpha) counts. Close to feel-neutral across this range: a smaller alpha
         lets d grow proportionally larger before crossing a proportionally larger dead zone, so the
         held-tick fraction barely moves.
      3. ★ TRACKING LAG -- the peak |x-y| the assist actually sees. This is the real feel cost, it is
         intrinsic to any low-pass on the feedback path, and it grows in direct proportion to the
         attenuation. ⇒ THERE IS NO LOW-PASS SETTING BOTH MATERIALLY STRONGER THAN V52C AND
         FEEL-NEUTRAL. That is the argument for a notch (gain reduction without broadband lag) or for
         feedforward cancellation (a static gain: no lag, no dead zone, no pole) instead.
    """
    import math
    rows = []
    for alpha in (128, 96, 74, 48, 32, 24, 16, 8):
        mag, ph = ema_response(alpha, f_mode, fs_hz)
        rows.append({
            "alpha_q10": alpha,
            "fc_hz": round(-fs_hz * math.log(1 - alpha / 1024.0) / (2 * math.pi), 2),
            "dB_at_mode": round(20 * math.log10(mag), 2),
            "phase_deg": round(ph, 1),
            "deadband_counts": round(512.0 / alpha, 1),      # symmetric half-width, round-to-nearest
            "lag_2166_at_1Hz": tracking_lag(alpha, 2166, 1.0, fs_hz),
            "lag_328_at_1Hz": tracking_lag(alpha, 328, 1.0, fs_hz),
        })
    return rows


if __name__ == "__main__":
    import json
    print("=" * 100)
    print("FEEDBACK-PATH COVERAGE: what V52C filtered and what it missed")
    print("=" * 100)
    for fs in (1000.0, 500.0):
        print("\n--- assuming producer sample rate %.0f Hz ---" % fs)
        print(json.dumps(coverage_report(fs_hz=fs), indent=2))
    print("\n" + "=" * 100)
    print("STRONGER-FILTER SWEEP at 1 kHz -- note TRACKING LAG, not the dead zone, is the feel cost")
    print("=" * 100)
    print("  alpha    fc Hz   dB@20.9  phase   deadzone   lag@2166ct/1Hz   lag@328ct/1Hz")
    for row in stronger_filter_sweep():
        print("  %5d  %7.2f  %7.2f  %+6.1f   +/-%5.1f   %10d      %8d"
              % (row["alpha_q10"], row["fc_hz"], row["dB_at_mode"], row["phase_deg"],
                 row["deadband_counts"], row["lag_2166_at_1Hz"], row["lag_328_at_1Hz"]))
    print("\n  V52C ran alpha=74. Recorded driver torque: ~2166 counts hands-on, ~328 hands-off.")
    print("  The lag column is why there is no low-pass both stronger than V52C and feel-neutral.")
