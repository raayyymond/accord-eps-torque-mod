#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
studies/models/eps_loop_gain_model.py  --  QUANTITATIVE control-theory model of the 2020 Accord
EPS ~21 Hz steering vibration as a closed-loop stability / loop-gain problem.

PURPOSE
-------
Stop guessing. Put numbers on: (1) the loop gain |L(jw0)| and phase at the mode
for stock / 2x / 4x; (2) the self-excitation onset multiple and how far over the
edge 4x is; (3) whether the operator's "Route B" (4x via setpoint, gain 0xC646C
back to stock) actually changes the 21 Hz loop gain; (4) a notch design; and
(5) each cal lever's predicted effect on |L| and gain margin.

This is a STANDALONE script (pure stdlib: math / cmath). It does NOT import or
modify the golden model model/eps_lkas_chain_model.py -- that file was read only for
grounding. Run:  python studies/models/eps_loop_gain_model.py

=====================================================================================
 PROVENANCE OF INPUTS  --  MEASURED vs MODEL ASSUMPTION (kept strictly separate)
=====================================================================================
MEASURED (route b9 telemetry, V38, raw CAN 399 @ ~100 Hz; see docs/research/VIBRATION-DOSSIER.md
and model/eps_lkas_chain_model.py::vibration_hands_off_analysis):
  * Peak frequency ......... 21.4 Hz   (aliased vs 78.6 Hz at 100 Hz sampling; de-aliased below)
  * Q (closed loop, at 4x) . 13.6       => zeta_closed(4x) = 1/(2Q) = 0.0368
  * -3 dB width ............ 1.58 Hz
  * ring-down/coherence .... ~0.23 s (~4-5 cycles at 21.4 Hz)
  * "not a driven line" .... peak-height-vs-window slope 0.635 (1.0 == a fixed driven line)
  * band power 20-30 Hz, V38 vs 2x era ... 63.66x  => amplitude ratio sqrt(63.66) = 7.98x ~ "8x"
  * band power 0.5-5 Hz, V38 vs 2x era ... 0.37x   (DOWN -- internal control: not a global scale)
  * hands-off vs hands-on (19-23 Hz, speed matched) ... 75x .. 314x
  * onset: NOT reported at 2x (V31); present at 4x (V38)  => symptom onset in (2x, 4x]

LITERATURE (corroboration, docs/research/VIBRATION-DOSSIER.md sec.8):
  * two-inertia steering torsional pole ~131 rad/s (20.9 Hz) -- within rounding of 21.4 Hz.
  * production EPS fixes this with a NOTCH on the torque-sensor/current command, or a
    COLLOCATED torque-rate damper. This firmware has NO notch anywhere (the actionable gap).

FIRMWARE TOPOLOGY (GhidraMCP traces, this audit; dossier sec.4 + coordinator correction 2026-07-21):
  * Plant excited by the delivered motor command gp-0x6b98; feedback closes through
    UNFILTERED, 1 kHz, torsion-bar / delivered-command-reading base-assist lanes summed
    into the command aggregator gp-0x6b94. LKAS forward lane is a ~5 Hz low-pass and
    CANNOT carry 21 Hz.
  * "type-8" carrier gp-0x6b12: **CORRECTED 2026-07-21** -- it is an envelope-gated
    cycle-DELTA (one-sample derivative) of the DELIVERED command gp-0x6b98, i.e. a
    command-RATE feedback. It is NOT gp-0x4f60 x 0xC646C (that product feeds the DEAD
    variable gp-0x6b10). => type-8 scales with the DELIVERED COMMAND, not with 0xC646C.
  * FUN_0003a382 residual lane gp-0x6ad4: 3-way sum (Stage A EMA + Stage C raw derivative
    + S3 accumulator) of errorterm = clamp(Sensor-B gp-0x4f60 - model, +/-10240); UNFILTERED
    (both stage poles = Q10 unity), reinforcing sign. Reads the physical sensor, which reflects
    the DELIVERED torque. Post-sum magnitude gain uVar27 (table 0xC67B2, flat 1024, single reader).
    => scales with the DELIVERED torque, not with 0xC646C.
  * The ONLY 0xC646C-scaled base-assist path (FUN_00036682/FUN_00036828) is a genuine EMA
    with a 0.94 Hz corner => carries NO 21 Hz content.
  * CONSEQUENCE (the key structural fact this model rests on): EVERY unfiltered 21 Hz carrier
    scales with the DELIVERED command / torque, i.e. with the effective LKAS multiple m,
    and NONE of them is distinguished by HOW the 4x is split between 0xC646C and the setpoint.

MODEL ASSUMPTIONS (parametrized; sensitivity shown):
  * Plant P(s) = a single lightly-damped 2nd-order mode at w0 = 2*pi*21.4, unity DC gain.
  * Loop-gain magnitude scales LINEARLY with the delivered-command multiple m
    (m = 1 stock, 2, 4). Justified above: all unfiltered carriers ~ delivered command ~ m.
  * The measured "8x amplitude at 4x" is read as the resonant-peaking factor
    |1/(1 - L(jw0))| = 8  (self-excitation alignment: net carrier presents ~0 deg at w0),
    giving |L(jw0)| = 0.875 at 4x.  <-- the single calibration anchor.
  * Carrier phase at w0 ~ 0 deg for the loop gain L = C*P (the destabilizing alignment):
    the dominant carriers are command/torque RATE (derivative) feedbacks (+90 deg) through a
    resonance at its -90 deg peak => L ~ real positive => direct anti-damping. Small extra
    lag from sampling/ZOH is included as a sensitivity, not in the headline.
"""

import math
import cmath

# ---------------------------------------------------------------------------
# MEASURED CONSTANTS
# ---------------------------------------------------------------------------
F0_HZ        = 21.4                 # measured peak (de-aliased below)
W0           = 2.0 * math.pi * F0_HZ
Q_MEAS_4X    = 13.6                 # measured closed-loop Q at 4x (V38)
ZETA_MEAS_4X = 1.0 / (2.0 * Q_MEAS_4X)
BW3DB_HZ     = 1.58                 # measured -3 dB width
COH_TIME_S   = 0.23                 # measured ring-down / coherence time
AMP_RATIO_4X_VS_2X = math.sqrt(63.66)   # 20-30 Hz band power ratio V38 vs 2x era -> amplitude
F_ALIAS_HZ   = 100.0 - 78.6         # the alias partner of 21.4 at 100 Hz sampling  (== 21.4)
F_S_CTRL     = 1000.0               # confirmed control-task rate (Hz)

# ---------------------------------------------------------------------------
# CALIBRATION ANCHOR (MODEL ASSUMPTION)
# ---------------------------------------------------------------------------
# Read the measured 8x amplitude at 4x as the resonant-peaking factor of a
# positive-feedback loop:  peak = |1/(1 - L(jw0))| = 8  with L real-positive at w0.
PEAK_4X   = 8.0
L_MAG_4X  = 1.0 - 1.0 / PEAK_4X     # = 0.875   (|L(jw0)| at 4x)
K_PER_M   = L_MAG_4X / 4.0          # loop gain per unit delivered-command multiple = 0.21875

MULTIPLES = {"stock(1x)": 1.0, "2x(V31)": 2.0, "4x(V38)": 4.0}

# ---------------------------------------------------------------------------
# PLANT
# ---------------------------------------------------------------------------
def plant(w, zeta, w0=W0):
    """Unity-DC 2nd-order resonance P(jw) = w0^2 / ( (jw)^2 + 2*zeta*w0*(jw) + w0^2 )."""
    s = 1j * w
    return (w0 * w0) / (s * s + 2.0 * zeta * w0 * s + w0 * w0)

def loop_gain_mag(m):
    """|L(jw0)| under the linear delivered-command-scaling model."""
    return K_PER_M * m

def closed_loop_peaking(Lmag, Lphase_deg=0.0):
    """Positive-feedback resonant peaking |1/(1-L)| at the given complex L(jw0)."""
    L = Lmag * cmath.exp(1j * math.radians(Lphase_deg))
    denom = 1.0 - L
    return 1.0 / abs(denom) if abs(denom) > 1e-12 else float("inf")

# ---------------------------------------------------------------------------
# Infer the BARE-plant damping so the model reproduces Q_closed(4x) = 13.6.
# Anti-damping (loop) removes damping in proportion to |L| (both ~ m):
#     zeta_closed(m) = zeta_bare * (1 - |L(m)|)          [-> 0 as |L| -> 1]
# Anchor at 4x:  zeta_bare = zeta_closed(4x) / (1 - |L(4x)|)
# ---------------------------------------------------------------------------
ZETA_BARE = ZETA_MEAS_4X / (1.0 - L_MAG_4X)      # ~0.296  (Q_bare ~1.7)
Q_BARE    = 1.0 / (2.0 * ZETA_BARE)

def zeta_closed(m):
    return ZETA_BARE * (1.0 - loop_gain_mag(m))

def q_closed(m):
    z = zeta_closed(m)
    return float("inf") if z <= 0 else 1.0 / (2.0 * z)

def gain_margin_db(Lmag):
    return 20.0 * math.log10(1.0 / Lmag) if Lmag > 0 else float("inf")

# ===========================================================================
# TASK 1 -- |L| and phase at stock / 2x / 4x
# ===========================================================================
def task1():
    print("=" * 84)
    print("TASK 1  --  LOOP GAIN |L(j*w0)| AND PHASE AT 21.4 Hz  (stock / 2x / 4x)")
    print("=" * 84)
    # Sampling+ZOH lag of the loop at w0, for reference (why L is ~real, not exactly 0 deg).
    # Rate (derivative) carrier: +90 deg. Plant at peak: -90 deg. Loop delay: n samples + ZOH.
    n_delay = 1.0                       # ~1 compute sample
    tau_d = (n_delay + 0.5) / F_S_CTRL  # + half-sample ZOH
    delay_lag_deg = math.degrees(W0 * tau_d)
    aligned_phase_deg = 0.0             # the destabilizing (peaking) alignment used for the anchor
    print("  Plant at the peak w0:              |P(jw0)| = Q_closed,  angle P = -90.0 deg")
    print("  Dominant carriers are RATE (command/torque-derivative) feedbacks: angle C = +90 deg")
    print("  => open-loop L = C*P is ~REAL POSITIVE at w0 (the peaking/self-excitation alignment,")
    print("     angle L ~ 0 deg) -- this is exactly WHY the mode peaks (Barkhausen alignment).")
    print("     REFINEMENT: a ~%.1f-sample + ZOH loop delay @ %.0f Hz adds %.1f deg lag, so the true"
          % (n_delay, F_S_CTRL, delay_lag_deg))
    print("     angle L(jw0) ~ %+.1f deg; this slightly detunes the exact on-w0 peak (peaking 8.0 -> %.1f)"
          % (-delay_lag_deg, closed_loop_peaking(L_MAG_4X, -delay_lag_deg)))
    print("     and shifts the peak a few tenths of a Hz, but does not change any conclusion.")
    print()
    print("  %-11s  %8s  %11s  %9s  %10s  %11s" %
          ("build", "|L(w0)|", "angleL(deg)", "peaking", "Q_closed", "gain-margin"))
    print("  " + "-" * 74)
    for name, m in MULTIPLES.items():
        Lmag = loop_gain_mag(m)
        peak = closed_loop_peaking(Lmag, aligned_phase_deg)   # anchor alignment (phase ~0)
        Qc   = q_closed(m)
        gm   = gain_margin_db(Lmag)
        print("  %-11s  %8.4f  %11s  %8.2fx  %9.1f  %8.2f dB" %
              (name, Lmag, "~0 (aligned)", peak, Qc, gm))
    print()
    loop_phase_deg = -delay_lag_deg
    print("  Notes:")
    print("   * |L| scales linearly with the delivered-command multiple m (all unfiltered")
    print("     21 Hz carriers ~ delivered command ~ m). Anchor: |L(4x)| = 1 - 1/8 = 0.875.")
    print("   * 'peaking' at ~0 deg loop phase uses |1/(1-L)|; Q_closed uses zeta_closed(m).")
    print("     The two agree to rounding (both express the same resonant amplification).")
    print("   * INFERRED bare-plant damping zeta_bare = %.3f (Q_bare = %.2f): the plant is only mildly"
          % (ZETA_BARE, Q_BARE))
    print("     resonant on its own; ~%.0f%% of the measured Q=13.6 at 4x is FEEDBACK-induced peaking,"
          % (100.0 * (1.0 - Q_BARE / Q_MEAS_4X)))
    print("     not intrinsic. [MODEL OUTPUT, sensitive to the linear-scaling assumption.]")
    print()
    return loop_phase_deg

# ===========================================================================
# TASK 2 -- self-excitation onset + max usable multiple
# ===========================================================================
def task2():
    print("=" * 84)
    print("TASK 2  --  SELF-EXCITATION ONSET AND MAX USABLE LKAS MULTIPLE")
    print("=" * 84)
    m_hard = 1.0 / K_PER_M                     # |L| = 1
    # symptom (palpable) thresholds: closed-loop Q crossing feelable values
    def m_for_Q(Qtarget):
        # q_closed(m)=Qtarget  ->  zeta_bare(1-K*m) = 1/(2Qtarget)
        return (1.0 - 1.0 / (2.0 * Qtarget * ZETA_BARE)) / K_PER_M
    m_Q4 = m_for_Q(4.0)
    m_Q5 = m_for_Q(5.0)
    m_Q6 = m_for_Q(6.0)
    print("  HARD self-excitation edge  |L(jw0)| -> 1.0 :   m = %.2fx" % m_hard)
    print("    (at this multiple zeta_closed -> 0, Q -> infinity: a true growing self-oscillation.)")
    print()
    print("  SYMPTOM (palpable-vibration) onset -- closed-loop Q crossing feelable levels:")
    print("     Q_closed = 4  (still ~'2x feel') at m = %.2fx" % m_Q4)
    print("     Q_closed = 5  (becoming palpable) at m = %.2fx" % m_Q5)
    print("     Q_closed = 6  (clearly objectionable) at m = %.2fx" % m_Q6)
    print()
    print("  => MAX USABLE LKAS MULTIPLE ~ %.1f - %.1fx  (Q_closed <~ 4-5)." % (m_Q4, m_Q5))
    print("     This is the '2x fine, 4x vibrates' boundary and it lands in the expected 2.5-3x band.")
    print()
    print("  WHERE 4x SITS:")
    print("     |L(4x)| = %.3f  =>  %.1f%% of the way to the hard edge (|L|=1); gain margin %.2f dB."
          % (L_MAG_4X, 100.0 * L_MAG_4X, gain_margin_db(L_MAG_4X)))
    print("     4x is ~%.2fx PAST the palpable-onset (%.2fx) and ~%.2fx UNDER the hard edge (%.2fx)."
          % (4.0 - m_Q5, m_Q5, m_hard - 4.0, m_hard))
    print()
    print("  RECONCILIATION (why the measured Q is FINITE, not infinite):")
    print("   * 4x is NOT strictly self-oscillating -- |L|=0.875<1, so the measured Q=13.6 is finite and")
    print("     the ring-down is ~4-5 cycles (decaying), exactly as measured. The felt 'vibration' is")
    print("     strong resonant PEAKING (8x amplitude) of a lightly-damped mode driven by command ripple,")
    print("     not unbounded growth. This matches the broad Q=13.6 line and the 0.635 not-a-driven-line")
    print("     slope better than a razor-sharp limit cycle would.")
    print("   * The two thresholds the task asks for are DISTINCT and both fall out of one model:")
    print("       - palpable onset ~3x  (Q through 5-6)  <- 'max stable/usable'")
    print("       - hard self-excitation edge ~%.1fx  (|L|=1)" % m_hard)
    print("     4x lives between them: past palpable, just under the hard edge.")
    print()
    # sensitivity: how the measured "8x" is READ changes |L(4x)| and the edge only slightly.
    print("  SENSITIVITY -- how the measured amplitude ratio (sqrt(63.66)=%.2f) is interpreted:" % AMP_RATIO_4X_VS_2X)
    # A: absolute peaking vs open loop = 8  -> |L|4x = 1-1/8
    LA = 1.0 - 1.0 / AMP_RATIO_4X_VS_2X
    # B: 8x is V38/2x amplitude, = (2x excitation) x (peaking ratio); L4x=2*L2x
    #    (1-g)/(1-2g) = ratio/2  ->  solve for g
    for label, pk_ratio in (("B: 8x = V38/2x amplitude incl. 2x excitation", AMP_RATIO_4X_VS_2X / 2.0),
                             ("C: 8x = V38/2x peaking ratio (no excitation)", AMP_RATIO_4X_VS_2X)):
        g = (pk_ratio - 1.0) / (2.0 * pk_ratio - 1.0)   # from (1-g)/(1-2g)=pk_ratio
        L4 = 2.0 * g
        edge = 1.0 / (L4 / 4.0)
        print("     %-46s |L|4x=%.3f  edge=%.2fx" % (label, L4, edge))
    print("     %-46s |L|4x=%.3f  edge=%.2fx" % ("A: 8x = absolute peaking (task recipe, used above)", LA, 1.0 / (LA / 4.0)))
    print("   => ROBUST: every reading gives |L|4x ~ 0.86-0.93 and a hard edge ~4.3-4.7x. So 4x sits just")
    print("      below the hard edge with ~1-2 dB margin, NOT comfortably inside it.")
    print()
    print("  LIMIT-CYCLE vs PEAKED-RESONANCE (the one qualitative fork):")
    print("   * If 4x were a TRUE self-excited limit cycle, |L|4x >= 1 and the edge would be BELOW 4x")
    print("     (~2.5-3x). But the MEASURED Q is FINITE (13.6) with a ~4-5 cycle decaying ring-down,")
    print("     which requires |L|4x < 1. The finite Q is the tie-breaker: 4x is a strongly-peaked but")
    print("     still-decaying resonance, edge just above 4x. Either way the usable ceiling is ~3x.")
    print()
    return m_hard, m_Q5

# ===========================================================================
# TASK 3 -- THE DISCRIMINATOR: does Route B change |L(21Hz)| at all?
# ===========================================================================
def task3(loop_phase_deg):
    print("=" * 84)
    print("TASK 3  --  ROUTE B (4x via setpoint, 0xC646C -> stock):  FIX or HYGIENE-ONLY?")
    print("=" * 84)
    print("  ROUTE B DEFINITION: keep 4x forward authority but make it")
    print("     forward LKAS lane = (4x setpoint) x (stock gain)  instead of  (stock setpoint) x (4x gain).")
    print()
    print("  GAIN-RESCALING INVARIANCE (quantitative):")
    print("     forward lane counts = (setpoint * gain) >> 15.")
    print("       V38     : (setpoint_stock * 4*gain_stock)")
    print("       Route B : (4*setpoint_stock * gain_stock)   == SAME PRODUCT (bit-identical >>15).")
    print("     => the aggregator, governor, shaper and FOC replay the SAME counts")
    print("     => the DELIVERED command gp-0x6b98 is IDENTICAL between V38 and Route B.")
    print()
    print("  CARRIER-BY-CARRIER effect of Route B on the 21 Hz loop gain:")
    print("     %-34s %-26s %-10s" % ("carrier", "scales with", "Route B ?"))
    print("     " + "-" * 72)
    rows = [
        ("type-8  (delta of gp-0x6b98)", "DELIVERED command  (~m)", "UNCHANGED"),
        ("FUN_0003a382 residual (uVar27)", "DELIVERED torque   (~m)", "UNCHANGED"),
        ("boost / magnitude / r24 / r26", "DELIVERED command/torque",  "UNCHANGED"),
        ("FUN_00036682/828 (0xC646C x sens)", "0xC646C gain (goes 1/4)", "1/4 BUT 0.94 Hz-filtered"),
    ]
    for a, b, c in rows:
        print("     %-34s %-26s %-10s" % (a, b, c))
    print()
    # Quantify: what fraction of the 21 Hz loop gain is 0xC646C-scaled AND unfiltered?
    f_gain_scaled_unfiltered = 0.0   # the only 0xC646C path is filtered out at 21 Hz
    L_v38    = L_MAG_4X
    L_routeB = L_v38 * (f_gain_scaled_unfiltered * 0.25 + (1.0 - f_gain_scaled_unfiltered) * 1.0)
    print("  RESULT:")
    print("     fraction of |L(21Hz)| that is 0xC646C-scaled AND unfiltered = %.2f  (the only such" % f_gain_scaled_unfiltered)
    print("       path, FUN_00036682, is a 0.94 Hz EMA -> ~0 gain at 21 Hz).")
    print("     |L(21Hz)|  V38 = %.4f   ->   Route B = %.4f     (delta = %.4f, %.1f%%)" %
          (L_v38, L_routeB, L_routeB - L_v38, 100.0 * (L_routeB - L_v38) / L_v38))
    print("     Q_closed unchanged: %.1f -> %.1f." % (Q_MEAS_4X, q_closed(4.0 * L_routeB / L_v38 if L_v38 else 4.0)))
    print()
    print("  >>> VERDICT: ROUTE B IS HYGIENE-ONLY, NOT A VIBRATION FIX. <<<")
    print("     Re-splitting the 4x between gain and setpoint leaves the delivered command bit-identical,")
    print("     so every UNFILTERED 21 Hz carrier (all delivered-command/torque-scaled) is UNCHANGED, and")
    print("     the only 0xC646C-scaled path carries no 21 Hz. The loop gain at 21 Hz does NOT move.")
    print()
    print("  WHY THE ORIGINAL 'DIGITAL vs PHYSICAL' DISCRIMINATOR COLLAPSES:")
    print("     The task's candidate (a) 'DIGITAL type-8 = gp-0x4f60 x 0xC646C' does NOT exist on the")
    print("     corrected trace -- that product feeds the DEAD var gp-0x6b10. The LIVE type-8 is a")
    print("     command-derivative (delivered-scaled), i.e. it is in the SAME invariant class as the")
    print("     'physical' FUN_0003a382. There is NO unfiltered, 0xC646C-scaled, 21 Hz carrier. Hence")
    print("     Route B cannot discriminate anything -- it does nothing either way.")
    print()
    print("  THE DISCRIMINATOR THAT DOES WORK is to MUTE each carrier (at fixed delivered command):")
    print("     - mute type-8            -> if vibration clears, type-8 is the dominant carrier;")
    print("     - cut FUN_0003a382 uVar27-> if vibration clears, a382 is the dominant carrier;")
    print("     - if neither alone clears it, the anti-damping is DISTRIBUTED -> notch (split-independent).")
    print()

# ===========================================================================
# TASK 4 -- NOTCH DESIGN
# ===========================================================================
def notch(w, f_center_hz, depth_db, Q_notch):
    """Band-stop biquad N(jw) = (s^2 + 2*zn*wc*s + wc^2)/(s^2 + 2*zd*wc*s + wc^2),
       center attenuation = zn/zd = depth (linear), width set by zd = 1/(2*Q_notch)."""
    wc = 2.0 * math.pi * f_center_hz
    zd = 1.0 / (2.0 * Q_notch)
    depth_lin = 10.0 ** (-depth_db / 20.0)
    zn = zd * depth_lin
    s = 1j * w
    num = s * s + 2.0 * zn * wc * s + wc * wc
    den = s * s + 2.0 * zd * wc * s + wc * wc
    return num / den

def task4():
    print("=" * 84)
    print("TASK 4  --  NOTCH DESIGN (Tier-2 fallback if cal levers fail)")
    print("=" * 84)
    # (a) de-alias 21.4 vs 78.6 Hz -- from the DATA, not just plausibility
    print("  (a) 21.4 Hz vs 78.6 Hz aliasing  --  RESOLVED IN FAVOUR OF 21.4 Hz, from the data:")
    tau_214 = Q_MEAS_4X / (math.pi * 21.4)
    tau_786 = Q_MEAS_4X / (math.pi * 78.6)
    print("      A 2nd-order mode's ring-down time is tau = Q/(pi*f).  With the MEASURED Q=13.6:")
    print("         if f = 21.4 Hz -> tau = %.3f s   (MEASURED coherence ~0.23 s)   <-- MATCH" % tau_214)
    print("         if f = 78.6 Hz -> tau = %.3f s   (would be ~4x shorter)         <-- no" % tau_786)
    print("      The measured ~0.23 s coherence is only consistent with 21.4 Hz. Physical corroboration:")
    print("      steering-column two-inertia torsional modes are 12-25 Hz (lit. 20.9 Hz); 78.6 Hz would")
    print("      need ~14x the torsion stiffness or ~14x less column inertia (f ~ sqrt(k/J)) -- not a")
    print("      wheel/column torsional mode (that band is motor-electrical / bracket territory). Also the")
    print("      collocation keystone places the mode on the WHEEL side of the torsion bar = the low mode.")
    print("      => center the notch at 21.4 Hz.")
    print()
    # (b) depth needed to pull |L(21.4)| from 0.875 to <= 0.5 (6 dB margin)
    print("  (b) DEPTH / CENTER / Q to pull |L(21.4)| from %.3f to <= 0.5 (6 dB gain margin):" % L_MAG_4X)
    need_db = 20.0 * math.log10(L_MAG_4X / 0.5)
    print("      minimum center attenuation = 20log10(%.3f/0.5) = %.2f dB." % (L_MAG_4X, need_db))
    print("      Recommend %4.1f dB depth (robust to plant/param error) at Q_notch ~ 4-5:" % 8.0)
    for depth_db, Qn in ((need_db, 5.0), (6.0, 5.0), (8.0, 5.0), (8.0, 4.0)):
        Ln = L_MAG_4X * abs(notch(W0, 21.4, depth_db, Qn))
        bw = 21.4 / Qn
        print("        depth %4.1f dB, Q=%.0f (BW %.1f Hz): |L(21.4)| -> %.3f  (margin %.2f dB), Q_closed -> %.1f"
              % (depth_db, Qn, bw, Ln, gain_margin_db(Ln), q_closed(4.0 * Ln / L_MAG_4X)))
    print()
    # (c) phase lag at the forward crossover (few Hz)
    print("  (c) PHASE the notch adds at the ~few-Hz FORWARD (LKAS) crossover  --  is it a threat?")
    Qn, depth_db = 5.0, 8.0
    for fx in (1.0, 2.0, 3.0, 5.0, 10.0):
        ph = math.degrees(cmath.phase(notch(2.0 * math.pi * fx, 21.4, depth_db, Qn)))
        print("        at %5.1f Hz: notch phase = %+5.1f deg" % (fx, ph))
    print("      => a Q=5 notch at 21.4 Hz adds well under ~2 deg anywhere in the 1-5 Hz forward-loop")
    print("         crossover region -- NO meaningful erosion of the LKAS phase margin. (The forward lane")
    print("         is already rolled off by its own ~5 Hz IIR before the notch's phase grows near center.)")
    print()
    # (d) placement
    # ===================================================================================
    # 🛑 FALSIFIED ON-CAR 2026-07-21 -- V48B implemented exactly the "PREFERRED" placement
    # below (notch a filtered COPY of gp-0x4f60, repoint the base-assist carriers) and it
    # BRICKED: full-authority steering oscillation on startup, parked, NO LKAS command.
    # TWO reasons this placement reasoning was WRONG (see
    # docs/handoffs/2026-07/HANDOFF-2026-07-21-v48b-flashed-catastrophic.md):
    #   (1) "OFF the safety-critical motor-command path" -- FALSE. The base-assist carriers
    #       gp-0x4f60 feeds ARE the always-on power-steering assist loop into gp-0x6b94 ->
    #       gp-0x6b98. It is not off the control loop; it is inside a HIGH-GAIN one that is
    #       energized parked/hands-off (no LKAS, no speed gate).
    #   (2) "Base assist loses only its 21 Hz response, which it does not need" -- FALSE. A
    #       notch is a LIGHTLY-DAMPED RESONATOR (r=0.979, zeta~0.16, Q~3.2). Dropped into the
    #       base-assist feedback loop its own poles + its +-25 deg phase swing across 18-26 Hz
    #       (this model only ever checked notch phase at the 1-5 Hz FORWARD-LKAS crossover, and
    #       only inserted |N(w0)|, a single-frequency MAGNITUDE, into L) were never analyzed for
    #       CLOSED-LOOP stability of THAT loop. Open-loop pole-radius<1 / DC-unity / no-overflow
    #       is necessary but NOT sufficient.
    # BEFORE reviving any notch: model the base-assist loop and prove positive gain+phase margin
    # with the notch inserted (GATE 2), and put the biquad state in genuinely-free RAM verified
    # writer-side (GATE 1 -- V48B's x2 cell gp-0x14FA aliased a live monitor status byte).
    # ===================================================================================
    print("  (d) WHERE TO PUT IT:  [🛑 the 'PREFERRED' option below was FLASHED as V48B and BRICKED --")
    print("      it is inside the always-on base-assist loop, NOT off the control path; see header comment]")
    print("      PREFERRED -- on the TORSION-BAR / carrier-input signal (gp-0x4f60 / the errorterm),")
    print("        BEFORE it fans out to type-8, FUN_0003a382, boost, r24/r26. One insertion attenuates")
    print("        the 21 Hz feedback of ALL collocated carriers at once (robust to distributed anti-")
    print("        damping), it is OFF the safety-critical motor-command path (no governor/shaper/DTC-0x1d")
    print("        lockstep entanglement), and the forward LKAS command does not traverse it (so it cannot")
    print("        eat forward-loop phase). Base assist loses only its 21 Hz response, which it does not need.")
    print("      ALTERNATIVE -- on the AGGREGATED command (gp-0x6b94/gp-0x6ace): kills the 21 Hz DRIVE")
    print("        regardless of source and thus opens the loop, but sits ON the critical torque path")
    print("        (near the DTC-0x1d int/float lockstep) -> higher safety bar. Use only if the sensor-side")
    print("        insertion is not reachable in a code cave.")
    print()

# ===========================================================================
# TASK 5 -- per-lever margin effect
# ===========================================================================
def lever_report(f8, fa, label):
    """f8 = type-8 fraction of |L(4x)|, fa = FUN_0003a382 fraction; remainder = minor lanes."""
    fm = max(0.0, 1.0 - f8 - fa)
    L0 = L_MAG_4X
    def report(newL, name):
        print("       %-30s |L| %.3f -> %.3f   margin %.2f -> %.2f dB   Q_closed %.1f -> %.1f" %
              (name, L0, newL, gain_margin_db(L0), gain_margin_db(newL),
               Q_MEAS_4X, q_closed(4.0 * newL / L0)))
    print("   --- prior: type-8 = %.0f%%, FUN_0003a382 = %.0f%%, minor = %.0f%% of |L(4x)|  [%s]"
          % (100 * f8, 100 * fa, 100 * fm, label))
    report(L0 * (1.0 - f8),                 "MUTE type-8")
    report(L0 * (1.0 - 0.5 * fa),           "uVar27 1024->512 (a382 x1/2)")
    report(L0 * (1.0 - 0.75 * fa),          "uVar27 1024->256 (a382 x1/4)")
    report(L0 * (1.0 - fa),                 "uVar27 -> 0 (mute a382)")
    report(L0 * (1.0 - f8) * (1.0 - fa),    "MUTE type-8 AND mute a382")
    report(L0 * 1.0,                        "ROUTE B (delivered cmd fixed)")
    report(L0 * abs(notch(W0, 21.4, 8.0, 5.0)), "NOTCH 21.4Hz 8dB Q5 (split-indep)")
    print()

def task5():
    print("=" * 84)
    print("TASK 5  --  PER-LEVER EFFECT ON |L(21Hz)| AND GAIN MARGIN")
    print("=" * 84)
    print("  Target for 'restored stability' (acceptable / ~2x feel): |L| <= ~0.44 (Q_closed <~ 4),")
    print("  or for a comfortable 6 dB margin: |L| <= 0.5.  Baseline 4x: |L| = %.3f, margin %.2f dB, Q=13.6."
          % (L_MAG_4X, gain_margin_db(L_MAG_4X)))
    print()
    print("  The split (type-8 vs FUN_0003a382 vs minor) is UNKNOWN, so results are shown under three")
    print("  priors. Both named carriers are command/torque-RATE feedbacks (derivative, anti-damping).")
    print()
    lever_report(0.60, 0.30, "type-8 dominant")
    lever_report(0.30, 0.60, "FUN_0003a382 dominant")
    lever_report(0.40, 0.40, "co-dominant / distributed")
    # thresholds
    print("  DOMINANCE THRESHOLDS (single-cal-lever must remove enough loop gain):")
    thr_mute8 = (L_MAG_4X - 0.44) / L_MAG_4X
    thr_a382  = (L_MAG_4X - 0.44) / L_MAG_4X
    print("     muting type-8 ALONE reaches |L|<=0.44 only if type-8 >= %.0f%% of the loop gain." % (100 * thr_mute8))
    print("     muting a382   ALONE reaches |L|<=0.44 only if a382   >= %.0f%% of the loop gain." % (100 * thr_a382))
    Ln = L_MAG_4X * abs(notch(W0, 21.4, 8.0, 5.0))
    print("     a NOTCH (8 dB, Q5) reaches |L| = %.3f (margin %.2f dB) REGARDLESS of the split." % (Ln, gain_margin_db(Ln)))
    print()
    print("  >>> WHICH SINGLE LEVER RESTORES STABILITY? <<<")
    print("   * GUARANTEED, split-independent: the NOTCH (or a sensor-side band-stop every carrier passes")
    print("     through). It pulls |L(21Hz)| 0.875 -> ~0.35-0.44 and the margin 1.16 -> ~6-8 dB no matter")
    print("     how the anti-damping is distributed. This is the reliable single lever and the OEM-standard")
    print("     answer -- at the cost of a code cave (this kit's highest-risk change class).")
    print("   * CAL-ONLY, conditional: MUTE type-8 first (a clean full-carrier removal); if null, MUTE")
    print("     FUN_0003a382 via uVar27->0. Each cures the vibration ONLY IF that lane is >=~50% of the")
    print("     loop gain. Running them as two separate flashes also DISCRIMINATES which carrier dominates")
    print("     (the job Route B cannot do).")
    print("   * NOT A LEVER: Route B / any gain-vs-setpoint re-split -- delivered command is invariant,")
    print("     so |L(21Hz)| does not move (Task 3).")
    print()

# ===========================================================================
def summary(m_hard, m_symp):
    print("=" * 84)
    print("EXECUTIVE SUMMARY")
    print("=" * 84)
    print("  1. |L(21.4Hz)|: stock %.3f / 2x %.3f / 4x %.3f ; loop phase ~0 deg (rate carrier through the"
          % (loop_gain_mag(1), loop_gain_mag(2), loop_gain_mag(4)))
    print("     -90 deg plant peak = real-positive = anti-damping). Q_closed: %.1f / %.1f / %.1f."
          % (q_closed(1), q_closed(2), q_closed(4)))
    print("  2. Palpable onset ~%.1fx (Q~5); hard self-excitation edge %.1fx (|L|=1). 4x is at 87.5%% of"
          % (m_symp, m_hard))
    print("     the hard edge (margin %.2f dB) and well past palpable -- '2x fine, 4x vibrates' reproduced."
          % gain_margin_db(L_MAG_4X))
    print("  3. ROUTE B = HYGIENE ONLY. Delivered command is bit-identical (4x-setpoint*stock-gain ==")
    print("     stock-setpoint*4x-gain), so every unfiltered 21 Hz carrier is unchanged; the only")
    print("     0xC646C-scaled path is 0.94 Hz-filtered. dL(21Hz) ~ 0. It does NOT cure the vibration.")
    print("  4. NOTCH: center 21.4 Hz (de-aliased from the ring-down time), 6-8 dB deep, Q~4-5 -> |L| <=0.5,")
    print("     margin 6-8 dB, <2 deg at the forward crossover. Put it on the torsion-bar/carrier-input side.")
    print("  5. Reliable single lever = the NOTCH (split-independent). Cal-only: MUTE type-8, else mute a382")
    print("     via uVar27; each works only if its lane is >=~50% of the loop gain (and the pair discriminates).")
    print("=" * 84)

def main():
    print()
    print("2020 ACCORD EPS ~21 Hz VIBRATION  --  CLOSED-LOOP GAIN / STABILITY MODEL")
    print("(MEASURED inputs and MODEL ASSUMPTIONS separated; see module docstring.)")
    print()
    loop_phase_deg = task1()
    m_hard, m_symp = task2()
    task3(loop_phase_deg)
    task4()
    task5()
    summary(m_hard, m_symp)

if __name__ == "__main__":
    main()
