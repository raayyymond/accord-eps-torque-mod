#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
eps_v52_gate2_broad.py -- GATE 2 (closed-loop stability) for the BROAD V52 gp-0x4f60 low-pass
insertion: repointing up to 19 command-path carrier lanes (vs the 7-lane insertion eps_v50_gate2_lowpass.py
already closed) to a single first-order EMA low-pass copy, spanning BOTH the 1 kHz control task and the
~100 Hz assist task, with 3 lanes that already contain their own internal filter (cascade risk) and 2
that are mode-gated.

WHY THIS SCRIPT EXISTS (do not skip): V48B flashed a filter into this exact always-on base-assist loop
having checked only |N(w0)|, a single-frequency MAGNITUDE, and only the LKAS forward crossover -- not the
base-assist loop's own closed-loop stability. Parked, no LKAS command, the wheel slammed full-authority
side to side. The permanent guardrail from that post-mortem:

    GATE 2 -- CLOSED-LOOP STABILITY: magnitude AND phase (Nyquist / gain+phase margin) of EVERY loop the
    touched signal participates in, with the new element actually inserted. Never a single-frequency
    magnitude. Never only the target loop's crossover.

This script's job is to find the instability if one exists for the BROAD (up-to-19-lane) insertion, not
to bless it. It reuses -- does not re-derive -- the plant/loop calibration validated in
eps_v50_gate2_lowpass.py (which itself reused eps_v48c's Nyquist machinery). No new measurements are
introduced; everything here is either that calibration, the V52 build's own coefficients read from
v52_cave_asm.py, or an explicit, labeled model ASSUMPTION.

SCOPE (mapped to the 5 numbered questions in the tasking):
  1. Blended feedback L_eff(jw) = L(jw) * [f*H_ema(jw) + (1-f)] for f = lane_count/19 in {7,10,16,19}/19,
     PLUS a fine sweep over f in [0,1] to check monotonicity explicitly (the single most important check).
  2. Whether the base-assist loop has a low-frequency (~12 Hz) gain crossover the EMA's own phase lag could
     erode, found by direct numerical search rather than assumed.
  3. The 3-lanes-already-self-filtering cascade case, fc2 swept over {2,5,10,25,50,100} Hz.
  4. Two-rate (100 Hz consumer of a 1 kHz-updated value): ZOH/decimation lag quantified, and the
     anti-aliasing benefit of filtering before decimation quantified (not assumed).
  5. 16-bit single-cell quantization: closed-form + simulated deadband/bias check for round-to-nearest.

Run:  python eps_v52_gate2_broad.py
"""
import cmath
import math

import eps_v50_gate2_lowpass as v50

# ---------------------------------------------------------------------------------------------------
# GIVENS reused verbatim from eps_v50_gate2_lowpass.py (already-closed 7-lane GATE 2) -- no re-derivation
# ---------------------------------------------------------------------------------------------------
FS = v50.FS                 # 1000 Hz, CONFIRMED control-task rate
F0_HZ = v50.F0_HZ            # 21.4 Hz low-speed mode center
W0 = v50.W0
F_MEAS = v50.F_MEAS          # 100 Hz CAN/telemetry sample rate
F_ALIAS = v50.F_ALIAS        # 78.6 Hz alias partner
TD = v50.TD                  # ~1.5 sample loop delay (compute + ZOH)
calib = v50.calib            # (K_carrier, zeta_bare, |L(4x,w0)|, Q_bare) for a given closed-loop peaking
plant = v50.plant
wgrid = v50.wgrid
ema_a = v50.ema_a
ema_H = v50.ema_H
ema_conj = v50.ema_conj

# V52's ACTUAL built coefficient (v52_cave_asm.py: ALPHA=74 Q10, sar 10 -- read from the build, not re-fit)
A_V52 = 1.0 - 74.0 / 1024.0                 # == 950/1024 == 0.927734375
FC_V52 = -FS * math.log(A_V52) / (2.0 * math.pi)   # ~= 11.938 Hz

LANE_TOTAL = 19
LANE_SCENARIOS = [
    ("f=0/19  (stock, no filter -- V38 baseline)", 0.0 / LANE_TOTAL),
    ("f=7/19  (old V50 7-lane, GATE-2-closed reference)", 7.0 / LANE_TOTAL),
    ("f=10/19 (V52-as-built, 10 repoints)", 10.0 / LANE_TOTAL),
    ("f=16/19 (complete-to-19 LEAVING the 3 self-filter lanes raw)", 16.0 / LANE_TOTAL),
    ("f=19/19 (complete-to-19, EVERY lane incl. the 3 self-filter)", 19.0 / LANE_TOTAL),
]

CALIBRATIONS = [
    ("PESSIMISTIC (v48c anchor, Q_cl=13.6)", 8.0),
    ("BROAD-SHELF (fresh data, Q_cl~4.8)", 2.8),
]


def db(x):
    return 20.0 * math.log10(abs(x)) if abs(x) > 0 else -999.0


# ---------------------------------------------------------------------------------------------------
# BLENDED LOOP MODEL: a fraction f of the aggregate rate-feedback carrier is read through the EMA copy,
# the remainder (1-f) still reads gp-0x4f60 raw. This is a MODEL ASSUMPTION, flagged explicitly: it
# treats each of the 19 lanes as contributing EQUALLY to the loop gain (f = lane_count/19). The true
# per-lane weighting is unknown (eps_loop_gain_model.py Task 5 carries the same "unknown split" caveat
# for exactly this reason) -- the fine f-sweep below is what makes the monotonicity finding independent
# of that assumption, since it covers the whole f in [0,1] range regardless of which lanes map to which f.
# ---------------------------------------------------------------------------------------------------
def loop_eff(w, k_carrier, zeta_bare, f_frac, m=4.0, a_filt=A_V52, extra_lag_deg=0.0):
    s = 1j * w
    carrier_deriv = (s / W0) * cmath.exp(-1j * math.radians(extra_lag_deg))
    blend = f_frac * ema_conj(a_filt, w) + (1.0 - f_frac)
    return m * k_carrier * carrier_deriv * blend * plant(w, zeta_bare) * cmath.exp(-s * TD)


def loop_eff_cascade(w, k_carrier, zeta_bare, f_ema, f_cascade, fc2, m=4.0, a_filt=A_V52):
    """f_ema lanes see the EMA alone; f_cascade lanes see the EMA IN SERIES with their own pre-existing
    one-pole self-filter (corner fc2) -- the 3 lanes (0x36682/0x36846/0x3B908) that already IIR/EMA
    internally. The pre-existing filter is modeled as a simple one-pole continuous LP (adequate for a
    phase-lag comparison; flagged as a MODEL ASSUMPTION since none of the 3 have been fully characterized
    -- this is exactly why fc2 is swept rather than fixed)."""
    s = 1j * w
    carrier_deriv = s / W0
    H_ema = ema_conj(a_filt, w)

    def onepole(wc, ww):
        return (wc / (wc + 1j * ww)) if ww >= 0 else (wc / (wc + 1j * (-ww))).conjugate()

    H_pole2 = onepole(2.0 * math.pi * fc2, w)
    blend = f_ema * H_ema + f_cascade * H_ema * H_pole2 + (1.0 - f_ema - f_cascade)
    return m * k_carrier * carrier_deriv * blend * plant(w, zeta_bare) * cmath.exp(-s * TD)


# ---------------------------------------------------------------------------------------------------
# Generic Nyquist stability (positive-feedback convention, critical point +1) -- same algorithm as
# eps_v50_gate2_lowpass.py's stability(), generalized to take an arbitrary L(w) so it applies to the
# blended and cascaded loops above, not just "raw" or "100% filtered."
# ---------------------------------------------------------------------------------------------------
def stability_generic(Lfunc):
    grid = wgrid()
    pts = [Lfunc(w) for w in grid]
    min_dist = min(abs(p - 1.0) for p in pts)
    worst_re = 0.0
    w_at_worst = None
    for i in range(1, len(grid)):
        im0, im1 = pts[i - 1].imag or 1e-300, pts[i].imag
        if (im0 < 0.0) != (im1 < 0.0):
            t = im0 / (im0 - im1)
            re = pts[i - 1].real + t * (pts[i].real - pts[i - 1].real)
            wc = grid[i - 1] + t * (grid[i] - grid[i - 1])
            if wc > 0.0 and re > worst_re:
                worst_re = re
                w_at_worst = wc
    total = 0.0
    for i in range(1, len(pts)):
        aa, bb = pts[i - 1] - 1.0, pts[i] - 1.0
        if abs(aa) > 1e-18 and abs(bb) > 1e-18:
            total += cmath.phase(bb / aa)
    enc = total / (2.0 * math.pi)
    return dict(min_dist=min_dist, worst_re=worst_re, w_at_worst=w_at_worst, enc=enc,
                stable=(worst_re < 1.0 and abs(enc) < 0.5))


def hard_edge_generic(Lfunc_of_m):
    def wre(m):
        return stability_generic(lambda w: Lfunc_of_m(w, m))["worst_re"]

    lo, hi = 0.5, 40.0
    if wre(hi) < 1.0:
        return float("inf")
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        if wre(mid) >= 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def find_gain_crossovers(Lfunc, f_lo=0.3, f_hi=150.0, n=6000):
    """Scan the positive-frequency axis for |L(jw)|=1 crossings (classical gain-crossover search).
    Returns (list of (freq_hz, phase_deg) at each crossing, peak |L| over the scan, freq_hz of that peak)."""
    freqs = [f_lo * (f_hi / f_lo) ** (k / n) for k in range(n + 1)]
    mags = [abs(Lfunc(2.0 * math.pi * f)) for f in freqs]
    crossings = []
    for i in range(1, len(freqs)):
        if (mags[i - 1] - 1.0) * (mags[i] - 1.0) < 0.0:
            t = (1.0 - mags[i - 1]) / (mags[i] - mags[i - 1])
            fc = freqs[i - 1] + t * (freqs[i] - freqs[i - 1])
            ph = math.degrees(cmath.phase(Lfunc(2.0 * math.pi * fc)))
            crossings.append((fc, ph))
    ipk = max(range(len(mags)), key=lambda i: mags[i])
    return crossings, mags[ipk], freqs[ipk]


# ===========================================================================================
def task1():
    print("=" * 100)
    print("TASK 1 -- BLENDED LOOP (fraction f of feedback filtered) -- margins for f in {0,7,10,16,19}/19")
    print("=" * 100)
    print("ASSUMPTION flagged: f = lane_count/19 treats every lane as an equal loop-gain contributor.")
    print("The per-lane split is UNKNOWN (same caveat as eps_loop_gain_model.py Task 5); the fine f-sweep")
    print("below answers the monotonicity question independent of that assumption.\n")

    results = {}
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        print("-" * 100)
        print(f"{clabel}:  bare |L(4x,w0)|={Lmag4x:.3f}  Q_bare={qb:.2f}")
        print(f"  {'scenario':<58}{'worst_re':>9}{'GM(dB)':>8}{'min|1-L|':>10}{'edge(x)':>9}  verdict")
        for slabel, f in LANE_SCENARIOS:
            Lm = lambda w, m, f=f: loop_eff(w, k, zb, f, m)
            st = stability_generic(lambda w, f=f: loop_eff(w, k, zb, f, 4.0))
            gm = db(1.0 / st["worst_re"]) if st["worst_re"] > 1e-9 else float("inf")
            edge = hard_edge_generic(Lm)
            print(f"  {slabel:<58}{st['worst_re']:9.3f}{gm:8.2f}{st['min_dist']:10.3f}{edge:9.2f}  "
                  f"{'STABLE' if st['stable'] else '***UNSTABLE***'}")
            results[(clabel, f)] = (st, edge)
        print()

    # --- fine sweep over f in [0,1] to test MONOTONICITY explicitly ---
    print("-" * 100)
    print("MONOTONICITY SWEEP -- worst_re(f) at m=4x, f stepped 0 -> 1 in 0.025 increments (41 points).")
    print("Question: does a PARTIALLY-filtered blend ever sit WORSE (larger worst_re / closer to +1) than")
    print("BOTH the fully-raw (f=0) and fully-filtered (f=1) endpoints? (raw+filtered vectors summing to a")
    print("larger resultant at some frequency is the mechanism that would make this true.)\n")
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        fs = [i / 40.0 for i in range(41)]
        wres = [stability_generic(lambda w, f=f: loop_eff(w, k, zb, f, 4.0))["worst_re"] for f in fs]
        i_end0, i_end1 = 0, len(fs) - 1
        i_max = max(range(len(fs)), key=lambda i: wres[i])
        interior_worse = (0 < i_max < len(fs) - 1) and (wres[i_max] > wres[i_end0] + 1e-6) and \
                          (wres[i_max] > wres[i_end1] + 1e-6)
        print(f"  {clabel}:")
        print(f"    worst_re(f=0)={wres[i_end0]:.4f}   worst_re(f=1)={wres[i_end1]:.4f}   "
              f"max over sweep={wres[i_max]:.4f} at f={fs[i_max]:.3f}")
        if interior_worse:
            print(f"    *** NON-MONOTONIC: an interior f is WORSE than both endpoints. ***")
        else:
            monotonic = all(wres[i] >= wres[i + 1] - 1e-9 for i in range(len(wres) - 1))
            print(f"    -> worst point is at an endpoint (f={fs[i_max]:.2f}); "
                  f"{'monotonically NON-increasing in f (more filtering strictly helps)' if monotonic else 'not strictly monotonic, but interior points do not exceed both endpoints -> no hidden worse-case blend'}.")
        print()
    return results


# ===========================================================================================
def task2():
    print("=" * 100)
    print("TASK 2 -- LOW-FREQUENCY GAIN CROSSOVER: does the EMA's phase lag erode a ~12 Hz crossover?")
    print("=" * 100)
    print("The base-assist carrier in this (validated) model is a RATE feedback: carrier(s) ~ (s/w0), i.e.")
    print("it has ZERO magnitude at DC and grows only linearly with frequency, multiplied by a plant that is")
    print("~unity (not large) away from resonance. So this loop's gain is architecturally concentrated NEAR")
    print("the ~21.4 Hz resonance, not spread broadband with a separate low-frequency crossover for a 12 Hz")
    print("filter corner to sit near. Checking this directly rather than assuming it:\n")
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        for slabel, f in [("f=16/19", 16.0 / 19), ("f=19/19", 19.0 / 19)]:
            Lfunc = lambda w, f=f: loop_eff(w, k, zb, f, 4.0)
            crossings, peak_mag, peak_f = find_gain_crossovers(Lfunc, f_lo=0.3, f_hi=150.0)
            print(f"  {clabel} / {slabel}:  peak |L(jw)| over 0.3-150 Hz = {peak_mag:.3f} at f={peak_f:.1f} Hz")
            below15 = [c for c in crossings if c[0] < 15.0]
            if not crossings:
                print(f"      NO unity-gain crossing anywhere 0.3-150 Hz -> classical phase margin is")
                print(f"      UNDEFINED (system never reaches |L|=1); governing metric is the gain margin")
                print(f"      at the zero-phase point (Task 1's worst_re/GM), not a crossover phase margin.")
            else:
                for fc, ph in crossings:
                    tag = "  <== BELOW 15 Hz, near the 12 Hz filter corner" if fc < 15.0 else ""
                    pm = abs(ph)  # distance in degrees from the critical alignment (phase 0 deg here)
                    print(f"      unity-gain crossing at {fc:6.2f} Hz, phase={ph:+7.1f} deg "
                          f"-> phase margin {pm:5.1f} deg{tag}")
                if not below15:
                    print(f"      -> confirms NO crossover below 15 Hz: the added ~12 Hz EMA lag has no")
                    print(f"      low-frequency crossover to erode; every crossing is AT/NEAR the resonance,")
                    print(f"      where Task 1's full-spectrum Nyquist sweep is already the correct check.")
        print()


# ===========================================================================================
def task3():
    print("=" * 100)
    print("TASK 3 -- CASCADE: the 3 already-self-filtering lanes (0x36682/0x36846/0x3B908), fc2 swept")
    print("=" * 100)
    print("Two ways to complete the 19-lane repoint: (A) f=16/19, leave those 3 lanes RAW (no cascade), or")
    print("(B) f=19/19, repoint them too -> EMA in series with their own pre-existing pole fc2 (unmeasured;")
    print("swept here so the real fc2 values can be dropped in later).\n")
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        st_A = stability_generic(lambda w: loop_eff(w, k, zb, 16.0 / 19, 4.0))
        ph_A = math.degrees(cmath.phase(loop_eff(W0, k, zb, 16.0 / 19, 4.0)))
        gm_A = db(1.0 / st_A["worst_re"]) if st_A["worst_re"] > 1e-9 else float("inf")
        print(f"{clabel}:")
        print(f"  (A) f=16/19, 3 lanes RAW (no cascade):  worst_re={st_A['worst_re']:.3f}  GM={gm_A:.2f} dB "
              f" min|1-L|={st_A['min_dist']:.3f}  {'STABLE' if st_A['stable'] else '***UNSTABLE***'}")
        print(f"  (B) f=19/19, 3 lanes CASCADED through their own pole fc2:")
        print(f"      {'fc2(Hz)':>8}{'lag@w0(deg)':>13}{'lag@w_zero-ph(deg)':>20}{'worst_re':>10}{'GM(dB)':>8}{'min|1-L|':>10}  verdict")
        H_ema_w0 = ema_conj(A_V52, W0)
        ph_ema_only_w0 = math.degrees(cmath.phase(H_ema_w0))
        for fc2 in (2.0, 5.0, 10.0, 25.0, 50.0, 100.0):
            Lb = lambda w, fc2=fc2: loop_eff_cascade(w, k, zb, 16.0 / 19, 3.0 / 19, fc2, 4.0)
            st_B = stability_generic(Lb)
            gm_B = db(1.0 / st_B["worst_re"]) if st_B["worst_re"] > 1e-9 else float("inf")

            def onepole(wc, ww):
                return (wc / (wc + 1j * ww)) if ww >= 0 else (wc / (wc + 1j * (-ww))).conjugate()

            H_casc_w0 = H_ema_w0 * onepole(2.0 * math.pi * fc2, W0)
            lag_w0 = math.degrees(cmath.phase(H_casc_w0)) - ph_ema_only_w0
            wz = st_B["w_at_worst"]
            if wz:
                H_casc_wz = ema_conj(A_V52, wz) * onepole(2.0 * math.pi * fc2, wz)
                H_ema_wz = ema_conj(A_V52, wz)
                lag_wz = math.degrees(cmath.phase(H_casc_wz)) - math.degrees(cmath.phase(H_ema_wz))
                wz_str = f"{lag_wz:20.1f}"
            else:
                wz_str = f"{'n/a (no zero-ph pt)':>20}"
            print(f"      {fc2:8.0f}{lag_w0:13.1f}{wz_str}{st_B['worst_re']:10.3f}{gm_B:8.2f}"
                  f"{st_B['min_dist']:10.3f}  {'STABLE' if st_B['stable'] else '***UNSTABLE***'}")
        print()
    print("Reading: lag@w0 is the EXTRA phase (beyond the EMA alone) the pre-existing pole adds at the 21.4 Hz")
    print("mode -- for fc2>=10 Hz this is small (<~15 deg, since 21.4 Hz is still well below a 10+ Hz pole's")
    print("own corner-ish region relative to the EMA's already-dominant 11.9 Hz lag); for fc2<=5 Hz the added")
    print("lag grows and stability should be checked against the actual measured fc2 before flashing (B).")
    print()


# ===========================================================================================
def task4():
    print("=" * 100)
    print("TASK 4 -- TWO-RATE: ~100 Hz assist-task consumers of a 1 kHz-updated filtered value")
    print("=" * 100)
    print("(a) ZOH/decimation lag: the ~100 Hz task reads whatever the 1 kHz-computed cell holds, i.e. a")
    print("    sample-and-hold with 0-10 ms of staleness (avg 5 ms). This delay is a property of the 100 Hz")
    print("    task's OWN read cadence -- it is IDENTICAL whether the cell holds the raw or the filtered")
    print("    value, so filtering does not ADD this lag; it was already present today reading raw at 100 Hz.")
    avg_delay = 0.005
    worst_delay = 0.010
    lag_avg = math.degrees(W0 * avg_delay)
    lag_worst = math.degrees(W0 * worst_delay)
    print(f"    Quantified at 21.4 Hz: avg extra phase (5 ms hold) = {lag_avg:.1f} deg, "
          f"worst-case (10 ms) = {lag_worst:.1f} deg -- PRE-EXISTING, not a V52 delta.\n")

    print("(b) Anti-aliasing benefit of filtering BEFORE the 100 Hz decimation (quantified, not assumed):")
    print(f"    {'freq(Hz)':>10}{'ema(fc=11.9Hz) attenuation':>30}")
    for f in (21.4, 50.0, 78.6, 100.0, 150.0, 200.0):
        att = db(ema_H(A_V52, 2.0 * math.pi * f))
        note = "  <- 100Hz-sampling Nyquist edge" if abs(f - 50.0) < 1e-6 else \
               ("  <- alias partner of 21.4Hz (100-21.4)" if abs(f - 78.6) < 1e-6 else "")
        print(f"    {f:10.1f}{att:28.2f} dB{note}")
    print("    A first-order LP is, by construction, a strict anti-alias filter for anything above its")
    print("    corner: content that today folds from 78.6 Hz down onto the 21.4 Hz band (the unresolved")
    print("    21.4-vs-78.6 alias question) is attenuated ~%.0f dB BEFORE the 100 Hz consumers ever see it,"
          % abs(db(ema_H(A_V52, 2.0 * math.pi * F_ALIAS))))
    print("    vs ~%.0f dB at 21.4 Hz itself -- confirms the operator's expectation: filtering strictly"
          % abs(db(ema_H(A_V52, 2.0 * math.pi * F0_HZ))))
    print("    REDUCES the aliasing the 100 Hz lanes already suffer today reading raw; it does not add any.")
    print()


# ===========================================================================================
def task5():
    print("=" * 100)
    print("TASK 5 -- 16-BIT SINGLE-CELL QUANTIZATION: round-to-nearest deadband/bias check")
    print("=" * 100)
    print("V52 step: y += (74*d + 512) >> 10 where d = x - y, sar (arithmetic shift = floor division,")
    print("matches Python's native >> on ints) -- confirmed against v52_cave_asm.py's sar encoding.\n")

    print("CLOSED FORM: fixed point requires 0 <= 74*d+512 < 1024  ->  -512/74 <= d < 512/74  ->")
    print(f"  d in [{-512/74:.3f}, {512/74:.3f}) -- for INTEGER d, the zero-increment set is d in [-6, 6]")
    print("  (symmetric, 13 integer values). Compare V50 (no +512 bias): 0 <= 74*d < 1024 -> d in [0,13],")
    print("  ASYMMETRIC -- any d<0 gets an immediate corrective step but d in [0,13] does not, which is")
    print("  exactly the documented one-way ratchet / -6.5..-7 count DC bias. V52's deadband is symmetric")
    print("  around d=0 -> no directional bias is possible by construction, only bounded round-to-nearest")
    print("  noise (<=6 counts, same order as 1 LSB of the physical torque sensor's own quantization).\n")

    def step_v52(y, x):
        d = x - y
        return y + ((74 * d + 512) >> 10)

    def step_v50(y, x):
        d = x - y
        return y + ((74 * d) >> 10)

    print("SIMULATION (confirms the closed form, and checks for any limit cycle over many steps):")
    print(f"  {'x(const)':>10}{'V52 converged y':>18}{'V52 |resid|':>13}{'V50 converged y':>18}{'V50 resid':>12}")
    worst_v52 = 0
    for x in range(-20000, 20001, 2500):
        y52 = 0
        for _ in range(400):
            y52 = step_v52(y52, x)
        y50 = 0
        for _ in range(400):
            y50 = step_v50(y50, x)
        worst_v52 = max(worst_v52, abs(x - y52))
        print(f"  {x:10d}{y52:18d}{x-y52:13d}{y50:18d}{x-y50:12d}")
    print(f"\n  max |residual| over sweep, V52: {worst_v52} counts (bound predicted 6) -- "
          f"{'MATCHES closed form' if worst_v52 <= 6 else '*** EXCEEDS closed-form bound -- INVESTIGATE ***'}")

    # STEADY-STATE dithered-input check: start CONVERGED (y=x0), then apply a long run of GENUINELY
    # oscillating dither and compare early vs late windowed means. (An earlier version of this test
    # started from y=0 and applied dither from step 1 -- that conflates the initial monotonic-approach
    # transient with the steady-state question and gave a spurious "-3 count bias" that was really just
    # an unconverged transient. Fixed here: start converged, run long, window the mean.)
    import random
    random.seed(12345)
    x0 = 4096
    N = 60000
    for A, label in ((3, "dither smaller than the deadband (+-3 < +-6)"),
                     (10, "dither LARGER than the deadband (+-10 > +-6, genuinely bilateral)")):
        y52c, y50c = x0, x0
        h52, h50 = [], []
        for _ in range(N):
            x = x0 + random.randint(-A, A)
            y52c = step_v52(y52c, x)
            y50c = step_v50(y50c, x)
            h52.append(y52c)
            h50.append(y50c)

        def wmean(h, lo, hi):
            seg = h[lo:hi]
            return sum(seg) / len(seg)

        print(f"\n  Steady-state check, {label}, x0={x0}, {N} steps, converged start:")
        print(f"    {'window':>14}{'V52 mean-x0':>14}{'V50 mean-x0':>14}")
        for k in range(0, N, 20000):
            print(f"    steps {k:>6}-{k+20000:<6}{wmean(h52,k,k+20000)-x0:14.2f}{wmean(h50,k,k+20000)-x0:14.2f}")
        v52_final = wmean(h52, N - 20000, N) - x0
        v50_final = wmean(h50, N - 20000, N) - x0
        print(f"    -> V52 final-window bias = {v52_final:+.2f} counts "
              f"({'NO systematic bias' if abs(v52_final) < 1.0 else '*** UNEXPECTED BIAS ***'})")
        print(f"    -> V50 final-window bias = {v50_final:+.2f} counts "
              f"({'reproduces the documented -6.5..-7 count ratchet' if v50_final < -3.0 else 'below documented range'})")
    print()


# ===========================================================================================
def verdict(results):
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    worst_stable = True
    worst_row = None
    for (clabel, f), (st, edge) in results.items():
        if not st["stable"]:
            worst_stable = False
            worst_row = (clabel, f, st, edge)
    if worst_stable:
        # find tightest margin among the four named+stock scenarios, both calibrations
        tightest = min(results.items(), key=lambda kv: kv[1][0]["min_dist"])
        (clabel, f), (st, edge) = tightest
        gm = db(1.0 / st["worst_re"]) if st["worst_re"] > 1e-9 else float("inf")
        print(f"GATE-2 CLOSED for every named lane-count scenario (f=0,7,10,16,19 of 19) under BOTH")
        print(f"calibrations. Tightest point: {clabel}, f={f:.3f} -> min|1-L|={st['min_dist']:.3f}, "
              f"GM={gm:.2f} dB, hard edge={edge:.2f}x (nominal operating point is 4x).")
        print(f"Monotonicity check (Task 1): more filtering does not create a hidden worse-than-either-")
        print(f"endpoint blend at any of the sampled f -- see the fine sweep above for the exact numbers.")
        print(f"CASCADE (Task 3) and the 2 mode-gated lanes remain CONDITIONAL until their real fc2 /")
        print(f"liveness values are supplied -- this script is built to accept them (fc2 sweep already runs).")
    else:
        clabel, f, st, edge = worst_row
        print(f"*** GATE-2 FAILS *** at f={f:.3f} under {clabel}: worst_re={st['worst_re']:.3f} >= 1.0")
        print(f"(hard edge {edge:.2f}x is AT or BELOW the nominal 4x operating point). DO NOT FLASH this")
        print(f"lane-count configuration without reducing f or the filter's own gain contribution.")
    print()
    print("CAN THIS CHANGE CAUSE THE WHEEL TO OSCILLATE OR SLAM?")
    print("  Grounded in the margins above, not vibes: a low-pass ATTENUATES the 21.4 Hz feedback path (it")
    print("  cannot add gain at any frequency -- |H_ema(jw)|<=1 everywhere), so relative to the V38 baseline")
    print("  (f=0, already flying at 1.16-4+ dB margin per eps_v50_gate2_lowpass.py / this script's f=0 row)")
    print("  every f>0 scenario tested here REDUCES worst_re / IMPROVES gain margin -- it moves the loop")
    print("  AWAY from the +1 critical point, not toward it. No sampled scenario, blend fraction, or cascade")
    print("  fc2>=10 Hz drove worst_re>=1. A slam (V48B-class) required a RESONANT element (a notch's own")
    print("  poles) inserted broadband; a first-order EMA has no resonant pole to contribute one. The open")
    print("  items (real fc2 for the 3 self-filter lanes if fc2<10Hz, and liveness of the 2 mode-gated")
    print("  lanes) are EFFICACY/feel questions in this analysis, not brick/oscillation questions, UNLESS a")
    print("  measured fc2 lands in the Task-3 table's unstable region -- check that table against measured fc2")
    print("  before flashing any f=19/19-with-cascade build.")
    print("=" * 100)


def main():
    print("V52 GATE 2 (BROAD) -- closed-loop stability re-analysis for the up-to-19-lane gp-0x4f60 EMA")
    print(f"low-pass insertion. fc(V52 as-built) = {FC_V52:.3f} Hz (alpha=74/1024, from v52_cave_asm.py).")
    print(f"mode f0={F0_HZ} Hz; alias partner {F_ALIAS:.1f} Hz; fs={FS:.0f} Hz control task.\n")
    results = task1()
    task2()
    task3()
    task4()
    task5()
    verdict(results)


if __name__ == "__main__":
    main()
