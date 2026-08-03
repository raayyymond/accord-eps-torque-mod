#!/usr/bin/env python3
"""Frequency response of `gp-0x6c2c`, the ONLY input to Honda's 1 kHz oscillation detector.

★★★★ THE RESULT: the cascade is a BAND-PASS PEAKING AT ~61 Hz, not a low-pass. It is MORE sensitive
in 45-100 Hz than at the 21 Hz mode it was assumed to be built around, and the 45-100 Hz band needs
LESS amplitude to trip than 21 Hz already required.

⇒ This is what makes `gp-0x671a` (the detector's reversal counter, readable by the EXISTING 100 Hz
probe hook) the kit's ONLY above-50-Hz-capable instrument. CAN is Nyquist 50.00 and the comma IMU
50.51; this signal is sampled inside the 1 kHz task and integrated into a counter that holds >=50 ms,
so reading it at 100 Hz does NOT alias.

🛑 Standing operator instruction, 2026-07-28: explain firmware with simple Python that MIRRORS THE
DECOMPILED ARITHMETIC EXACTLY -- integer `>>`, the real Q-format, the real branch conditions, each
line annotated with its instruction address, constants byte-read little-endian. dB/Hz interpretation
comes AFTER the code, never instead of it. This file is written to that rule.

PROVENANCE
  producer   FUN_00041464, stores to gp-0x6c2c @0x4184E  (task 1 = 1 kHz, by construction:
             TCB table 0xbb858, mod-100 divider 0x14be4, syscall8(0) unconditional)
  consumer   FUN_000428d4 -- thresholds |gp-0x6c2c| against T = cal 0xC620A = 12800, counts
             REVERSALS into gp-0x357c, holds the result in gp-0x671a (CEIL = 0xC64FA = 5,
             dwell = 0xC64DD = 50 ticks, hold = 0xC6270 = 5000 ticks released only when
             gp-0x6a5e >= 0xC62DE = 640 = 10.0 km/h at 64 counts/km-h)
  golden     eps_lkas_chain_model.detector_input_6c2c() -- confirmed correct as written

VALIDATION (this is why the model is trusted): the golden model records that a 21.3 Hz sinusoid needs
|gp-0x4f50| ~= 1683 counts to reach T. This simulation reproduces that pair to the integer --
1683 -> 12804 (trips), 1682 -> 12797 (does not). Orchestrator-verified independently, 2026-08-03.

🛑 UNITS: gp-0x4f50's deg/s conversion is [OPEN]. Do NOT borrow gp-0x6ac0's 4.7121 counts/deg-s --
it is a different internal signal with its own calibration, and composing the two is exactly what
produced this kit's RETRACTED "bus = 8 x deg/s". Amplitudes below are gp-0x4f50 RAW COUNTS.
"""
import math

FS = 1000.0          # task-1 rate, Hz -- confirmed structurally, not by dwell inference
T = 12800            # cal 0xC620A, byte-read LE
K1, K2 = 37, 22      # cals 0xC643C (>>7) and 0xC40DC (>>6)
RATE_CLAMP = 13000   # gp-0x4f50 plausibility gate, FUN_00068f52


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def detector_input_6c2c(rate_raw, ema_old, state_fast):
    """One tick of FUN_00041464. Returns (gp_0x6c2c, ema_new, state_fast_new).

    The band-pass falls out of ONE line: `step` is the EMA's own increment, i.e. a first difference
    in series with a low-pass -- H_step(z) = H_ema1(z) * (1 - z^-1). A differentiator (+6 dB/oct,
    zero at DC) ahead of two low-pass corners near 50-70 Hz gives a band-pass, not a low-pass.
    """
    if abs(rate_raw) > RATE_CLAMP:               # 0x415be-0x415ce plausibility gate
        return 0x7FFF, 0, 0                      # 0x41AC2 fault sentinel; both EMAs reset
    target = rate_raw * 1024                     # 0x415d0  Q10
    step = ((target - ema_old) * K1) >> 7        # 0x415e8  EMA #1 increment -- THE DIFFERENCE
    ema_new = ema_old + step
    acc = _clamp(step * 0x20, -0xFA0000, 0xFA0000)               # 0x41604-0x4161a  x32, clamp
    state_fast = state_fast + (((acc - state_fast) * K2) >> 6)   # 0x41622  EMA #2
    return state_fast >> 9, ema_new, state_fast                  # 0x4184a/0x4184e


def peak_response(amp, f_hz, n=20000):
    """Steady-state peak |gp-0x6c2c| for a sinusoid of `amp` raw counts at `f_hz`."""
    ema = sf = 0
    peak = 0
    for i in range(n):
        r = int(round(amp * math.sin(2 * math.pi * f_hz * i / FS)))
        out, ema, sf = detector_input_6c2c(r, ema, sf)
        if i > n // 2:                            # discard the transient
            peak = max(peak, abs(out))
    return peak


def trip_amplitude(f_hz, lo=1, hi=RATE_CLAMP):
    """Smallest raw amplitude whose steady-state peak reaches T. Binary search."""
    while lo < hi:
        mid = (lo + hi) // 2
        if peak_response(mid, f_hz) >= T:
            hi = mid
        else:
            lo = mid + 1
    return lo


if __name__ == "__main__":
    print("VALIDATION against the golden model's recorded 21.3 Hz sizing (T = %d)" % T)
    for a in (1683, 1682):
        p = peak_response(a, 21.3)
        print("   amp %4d -> peak %5d   %s" % (a, p, "TRIPS" if p >= T else "does not trip"))

    print("\nLINEAR-REGION GAIN (probe amp 1000), normalised to 21.09 Hz")
    base = peak_response(1000, 21.09)
    for f in (1, 21.09, 45, 60, 61, 80, 100, 150, 200, 250, 400):
        g = peak_response(1000, f)
        print("   %6.2f Hz  peak %6d  gain %6.3f  rel %5.2fx" % (f, g, g / 1000, g / base))

    print("\nAMPLITUDE REQUIRED TO TRIP T = %d (gp-0x4f50 raw counts; clamp is +-%d)"
          % (T, RATE_CLAMP))
    for f in (21.3, 45, 60, 80, 100, 150, 200):
        print("   %6.1f Hz -> %5d counts" % (f, trip_amplitude(f)))

    print("""
READING IT
  Peak at ~61 Hz, 1.61x the 21.09 Hz gain, still >90% of it out to ~180 Hz, and ~30x rejection of
  1 Hz driver-band content for free. 45-100 Hz trips on LESS amplitude (1056-1186) than 21 Hz
  already required (1683), and none of it is near gp-0x4f50's own +-13000 clamp => nothing in
  21-200 Hz is structurally untrippable.
  [!] V67 read this detector and measured 0.000% over 186,321 frames -- but at gp-0x671a >= 5.
  "Never reached 5" is NOT "never incremented"; the counter passes through 1,2,3,4 (verified in
  Ghidra at 0x429DA-0x429F2: the pin to CEIL fires only when already-saturated AND the fresh count
  lags; every other path is `mov r14,r8`, the raw count verbatim). V68 reads >= 1, plus gp-0x67df
  (FSM left neutral) one rung lower still.
  [!] These are DETECTORS, NOT SPECTROMETERS -- they give neither amplitude nor frequency, only
  "a threshold crossing / a reversal happened". Above-50-Hz INFORMATION, not an above-50-Hz waveform.
""")
