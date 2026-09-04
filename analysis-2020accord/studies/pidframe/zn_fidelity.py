# -*- coding: utf-8 -*-
r"""THE ACTUATOR / FIDELITY SPEC -- ranking candidates on the CLOSED-LOOP demand->delivered transfer.

Subagent `znback`, 2026-09-04 (second pass, after team-lead's actuator reframing).
ANALYSIS ONLY -- nothing built, nothing sent.

Companion to zn_backwards_no_overshoot.py (imported for the byte-exact controller, the Nyquist/GM
model, the ring composition and the DC chain).

  !! CONVENTION AUDIT FIRST.  The record carries TWO loop models in DIFFERENT sign conventions and
  they DISAGREE at 7.3 Hz.  This script prints the disagreement before using either, because a
  closed-loop |T(f)| curve built from the wrong one is exactly the class of confident-wrong-answer
  the kit warns about.  See SECTION 0.

Run: python analysis-2020accord/studies/pidframe/zn_fidelity.py
"""
import cmath
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zn_backwards_no_overshoot as Z  # noqa: E402

C, Hlag, Fb, GM, track, dg = Z.C, Z.Hlag, Z.Fb, Z.GM, Z.track, Z.dg
L73, ring, lower_root = Z.L73, Z.ring, Z.lower_root
F0 = Z.F0

# ---------------------------------------------------------------------------------------------- 0
print("=" * 122)
print("SECTION 0 -- !! CONVENTION AUDIT.  Two models, two conventions, and they DISAGREE at 7.3 Hz.")
print("=" * 122)
print("  (a) The NYQUIST/GM model (addendum sec-A3, anchored on the measured plant phase and the")
print("      item-4 |L| row).  Negative feedback: instability at angle L = -180 deg.")
print("      %8s %10s %12s %14s" % ("f (Hz)", "|L|", "angle L", "|T|=|L/(1+L)|"))
for f in (0.3, 1.0, 3.0, 7.3, 13.0, 20.0, 28.1):
    Lc = Z.magL(f, 248, 128) * cmath.exp(1j * math.radians(Z.phL(f, 248, 128)))
    print("      %8.1f %10.3f %+11.1f %14.3f" % (f, abs(Lc), dg(Lc), abs(Lc / (1 + Lc))))
print("")
print("  (b) The MEASURED RING (per-episode complex-ACF, 5 episodes).  Positive feedback around the")
print("      ripple: sustained oscillation at L = +1, margin |1-L| ~ 1/Q.")
print("      |L_ring(7.3)| = 0.976 [0.944-0.990],  Q ~ 41.7  =>  peak |L/(1-L)| ~ %.1f" % (0.976 / 0.024))
print("")
print("  !! THEY DO NOT DESCRIBE THE SAME LOOP.  Model (a) puts 7.3 Hz at |L| = %.3f angle %+.1f deg,"
      % (Z.magL(7.3, 248, 128), Z.phL(7.3, 248, 128)))
print("     i.e. |1+L| = %.3f and NO PEAK AT ALL (|T| = %.2f).  Model (b) measures a Q ~ 42 resonance"
      % (abs(1 + Z.magL(7.3, 248, 128) * cmath.exp(1j * math.radians(Z.phL(7.3, 248, 128)))),
         abs(Z.magL(7.3, 248, 128) * cmath.exp(1j * math.radians(Z.phL(7.3, 248, 128)))
             / (1 + Z.magL(7.3, 248, 128) * cmath.exp(1j * math.radians(Z.phL(7.3, 248, 128)))))))
print("     there.  Model (a) is a SMOOTH DELAY model fitted at 20 Hz -- it contains no plant")
print("     resonance and no r24 lane at all.  The ring lives in a PARALLEL arm (r24, FUN_0003aa2c)")
print("     that (a)'s single forward path does not contain.")
print("  ==> A SINGLE CLOSED-LOOP |T(f)| CURVE FOR THIS SYSTEM IS NOT COMPUTABLE FROM WHAT IS")
print("      MEASURED.  What IS computable is listed in SECTION 2, and what is not in SECTION 6.")

# ---------------------------------------------------------------------------------------------- 1
print("\n" + "=" * 122)
print("SECTION 1 -- THE COMMAND BAND, MEASURED (not assumed).  From the engaged 0x18F/0xE4 LKAS")
print("  command on r34/r35/r36/r37/r38 (100 Hz, Welch nperseg 2048), cumulative energy fraction:")
print("=" * 122)
print("""      route      0.5      1.0      1.5      2.0      3.0    band-95%
      r34      0.929    0.983    0.994    0.997    0.998     0.59 Hz
      r35      0.920    0.975    0.991    0.994    0.996     0.71 Hz
      r36      0.893    0.975    0.992    0.996    0.997     0.74 Hz
      r37      0.921    0.983    0.994    0.997    0.998     0.60 Hz
      r38      0.897    0.978    0.991    0.996    0.997     0.71 Hz
   (demand index gp-0x697a, which adds the taper and sign: 95 % below 1.40-2.78 Hz)""")
print("")
print("  !! THE COMMAND BAND IS 0-0.75 Hz, NOT 0-3 Hz.  97.5-98.3 % of engaged command energy sits")
print("     below 1 Hz.  ==> criterion 1 ('|T| flat and near 1.0 across the command band') is, on")
print("     this car, almost exactly the statement '|T(0)| = 1.0'.  Every dynamic feature of the")
print("     loop -- the 5.05 Hz output-lag pole, the 7.3 Hz ring, the 9.64 Hz D=P corner, the")
print("     16.5 Hz feedback EMA, the 20 Hz creep line -- is 7x to 27x ABOVE the command band.")

# ---------------------------------------------------------------------------------------------- 2
CANDS = [("today (V282)", 248, 128), ("Kp 200, Kd 128", 200, 128), ("Kp 176, Kd 128", 176, 128),
         ("Q1: Kp 148, Kd 128", 148, 128), ("Kp 128, Kd 128", 128, 128), ("Kp 100, Kd 128", 100, 128),
         ("ZN-PI 148/122", 148, 122), ("F: 248/160", 248, 160), ("Kp 248, Kd 192", 248, 192),
         ("Kp 176, Kd 160", 176, 160), ("Kp 248, Kd 216", 248, 216)]

print("\n" + "=" * 122)
print("SECTION 2 -- THE FIDELITY TABLE, restricted to what is actually anchored.")
print("=" * 122)
print("  |T(0)|      : the DC chain, from the four measured (|T|, rate) stall pairs.  [EVIDENCE]")
print("  scale error : 1/|T(0)| -- the factor the outer loop must make up.  Criterion 1 + 4(scale).")
print("  ph @0.75 Hz : inner-loop lag at the top of the MEASURED command band.  Criterion 3.")
print("  ring peak   : 1/|1 - L_ring(7.3)| -- criterion 2, and the ONLY peak with a measured handle.")
print("                !! a TRANSFER-FUNCTION number; the record explicitly warns it does NOT map to")
print("                felt amplitude (zn285 sec5.3 item 5).  Read the RATIO column, not the value.")
print("  GM          : blind-band gain margin (27-32 Hz), the constraint on pushing the ring down.")
print("")
print("  %-20s %5s %5s %8s %10s %11s %10s %9s %8s"
      % ("candidate", "Kp", "Kd", "|T(0)|", "scale err", "ph @0.75Hz", "ring peak", "vs today", "GM"))
base_peak = 1.0 / (1.0 - 0.976)
for nm, kp, kd in CANDS:
    t0, _ = track(kp)
    Lr = L73(kp, kd)
    peak = 1.0 / (1.0 - Lr) if Lr < 1 else float("inf")
    # inner-loop phase at 0.75 Hz: controller + lag + fb + the measured plant slope, closed
    Lc = Z.magL(0.75, kp, kd) * cmath.exp(1j * math.radians(Z.phL(0.75, kp, kd)))
    Tc = Lc / (1 + Lc)
    gm, _ = GM(kp, kd)
    print("  %-20s %5d %5d %8.3f %9.2fx %10.2f %10.1f %8.2fx %7.2fx"
          % (nm, kp, kd, t0, 1 / t0, dg(Tc), peak, peak / base_peak, gm))

phs = [dg((lambda L: L / (1 + L))(Z.magL(0.75, kp, kd)
       * cmath.exp(1j * math.radians(Z.phL(0.75, kp, kd))))) for _, kp, kd in CANDS]
print("\n  => CRITERION 3 IS MOOT: phase lag at 0.75 Hz spans only %.2f deg across EVERY candidate"
      % (max(phs) - min(phs)))
print("     (%.2f to %.2f), i.e. %.2f ms of difference against openpilot's own 200 ms SteerDelay."
      % (min(phs), max(phs), (max(phs) - min(phs)) / 360.0 / 0.75 * 1000))
print("  => CRITERION 1 (|T(0)|) and CRITERION 2 (ring peak) are ANTI-CORRELATED IN Kp -- but")
print("     criterion 2 is improvable in Kd at ZERO |T(0)| cost.  Compare, from the rows above:")
print("       Kp 148, Kd 128 : ring peak 10.0 (0.24x)  at |T(0)| 0.407   <-- pays 24 % of |T(0)|")
print("       Kp 248, Kd 160 : ring peak 11.0 (0.27x)  at |T(0)| 0.535   <-- pays NOTHING")
print("       Kp 248, Kd 192 : ring peak  6.5 (0.16x)  at |T(0)| 0.535   <-- BETTER ON BOTH")
print("     !! ON THE FIDELITY SPEC A Kd RAISE DOMINATES A Kp CUT.  Its cost is blind-band GM only.")

# ---------------------------------------------------------------------------------------------- 3
print("\n" + "=" * 122)
print("SECTION 3 -- IS max|T| <= 1.05 REACHABLE?  (criterion 2, taken literally)")
print("=" * 122)
print("  |T| = |L/(1-L)| at the ring, so |T| <= 1.05 needs |L_ring(7.3)| <= %.3f." % (1.05 / 2.05))
print("  Sweep the feasible box.  THREE constraints, enforced together:")
print("    (i)   GM >= the floor in column 1 (the blind-band Nyquist point)")
print("    (ii)  Kd >= 1.10 x the ring lower root AT THAT Kp (do not approach the re-arm point)")
print("    (iii) |T(0)| >= 0.311 -- below this the OUTER integrator saturates (SECTION 4).")
print("          !! Without (iii) the optimiser returns Kp = 0 every time, and Kp = 0 is DEAD.")
print("  %-12s %8s %8s %10s %11s %9s %12s %9s"
      % ("GM floor", "best Kp", "best Kd", "|L_ring|", "ring peak", "|T(0)|", "root margin", "vs today"))
T0_FLOOR = 0.311
best_rows = []
for gm_floor in (1.77, 1.60, 1.48, 1.35, 1.25, 1.15):
    best = None
    for kp in range(96, 249, 4):
        t0, _ = track(kp)
        if t0 < T0_FLOOR:
            continue
        root = lower_root(kp)
        if root is None:
            continue
        for kd in range(60, 261, 2):
            if kd < root * 1.10:
                continue
            gm, _ = GM(kp, kd)
            if gm < gm_floor:
                continue
            Lr = L73(kp, kd)
            if best is None or Lr < best[0]:
                best = (Lr, kp, kd, gm, root, t0)
    if best:
        Lr, kp, kd, gm, root, t0 = best
        peak = 1.0 / (1.0 - Lr)
        best_rows.append((gm_floor, kp, kd, Lr, peak, t0))
        print("  >= %-9.2fx %8d %8d %10.3f %11.1f %9.3f %11.2fx %8.2fx"
              % (gm_floor, kp, kd, Lr, peak, t0, kd / root, peak / base_peak))
print("")
bl = best_rows[-1]
print("  !! THE BEST RING ACHIEVABLE ANYWHERE IN THE FEASIBLE BOX IS |L| = %.3f (Kp %d, Kd %d),"
      % (bl[3], bl[1], bl[2]))
print("     i.e. a peak of ~%.1fx -- and that is at a GM floor of only 1.15x (1.2 dB, THIN)." % bl[4])
print("     max|T| <= 1.05 needs |L_ring| <= 0.512 and is NOT REACHABLE: it needs Kd past Ku = 227,")
print("     and the Kp = 0 end of the axis is dead independently.  ==> CRITERION 2 CANNOT BE MET.")
print("     The design question is not 'flat or not' but 'how much peaking, at what GM and |T(0)|'.")
print("")
print("  !! READ THAT TABLE CAREFULLY -- it optimises the RING ALONE, so it drives Kp down to")
print("     constraint (iii) and reports |T(0)| = 0.317 every time.  That is criterion 2 winning")
print("     outright over criterion 1.  A single optimum is the WRONG object here; the honest")
print("     object is the PARETO FRONTIER over (|T(0)|, ring peak).  Below, at a GM floor of 1.48x")
print("     (candidate F's own margin), the best ring available AT EACH |T(0)|:")
print("")
print("  %8s %10s %10s %11s %12s %11s" % ("Kp", "|T(0)|", "best Kd", "|L_ring|", "ring peak", "GM"))
for kp in (248, 224, 200, 176, 148, 128, 100):
    t0, _ = track(kp)
    root = lower_root(kp)
    best = None
    for kd in range(60, 261, 2):
        if kd < root * 1.10:
            continue
        gm, _ = GM(kp, kd)
        if gm < 1.48:
            continue
        Lr = L73(kp, kd)
        if best is None or Lr < best[0]:
            best = (Lr, kd, gm)
    if best:
        Lr, kd, gm = best
        print("  %8d %10.3f %10d %11.3f %12.1f %10.2fx" % (kp, t0, kd, Lr, 1 / (1 - Lr), gm))
print("")
print("  ** THE DECISION-BEARING PAIRWISE COMPARISON, straight off SECTION 2 and needing no optimiser:")
print("       Kp 148, Kd 128 : ring peak 10.0 , |T(0)| 0.407 , GM 1.93x , deadband +29 %")
print("       Kp 248, Kd 192 : ring peak  6.5 , |T(0)| 0.535 , GM 1.27x , deadband UNCHANGED")
print("     Kd 192 is BETTER ON BOTH FIDELITY CRITERIA and costs no deadband.  It pays in GM alone.")
print("     ==> on the actuator spec the Kp cut is DOMINATED, and the currency is blind-band margin,")
print("     not DC authority.  The ranking inverts relative to the loop-gain framing.")

# ---------------------------------------------------------------------------------------------- 4
print("\n" + "=" * 122)
print("SECTION 4 -- OUTER-INTEGRATOR HEADROOM.  The gate that replaces 'DC authority is cheap'.")
print("=" * 122)
BOUND = 2.110
print("  Prior-route basis [team-lead, to be replaced by r39 when `dec39` reports]:")
print("    max|i| = 1.225 against a bound of +-%.3f  =>  %.1f %% of bound, saturated 0.00 %% of frames."
      % (BOUND, 100 * 1.225 / BOUND))
print("")
print("  CONSERVATIVE (multiplicative) model: the outer integrator must supply 1/k_T more, where")
print("  k_T = |T(0)|_cand / |T(0)|_today.  |i'| = max|i| / k_T.")
print("  %-20s %5s %9s %8s %12s %13s" % ("candidate", "Kp", "|T(0)|", "k_T", "req. mult.", "% of bound"))
t0_base, _ = track(248)
for nm, kp, kd in CANDS:
    t0, _ = track(kp)
    kT = t0 / t0_base
    frac = 100 * (1.225 / kT) / BOUND
    flag = "   ** SATURATES **" if frac >= 100 else ("   thin" if frac >= 90 else "")
    print("  %-20s %5d %9.3f %8.3f %11.3fx %12.1f%s" % (nm, kp, t0, kT, 1 / kT, frac, flag))

print("\n  THE FLOOR, as a FUNCTION of max|i| (so it can be re-evaluated when r39 lands):")
print("    saturation when  max|i| / k_T = %.3f  =>  k_T_min = max|i| / %.3f" % (BOUND, BOUND))
print("  %-12s %10s %12s %12s %14s" % ("max|i|", "% of bound", "k_T min", "|T(0)| min", "=> Kp FLOOR"))
for m in (1.000, 1.225, 1.400, 1.600, 1.800, 2.000):
    kT_min = m / BOUND
    t0_min = t0_base * kT_min
    if t0_min >= 1.0:
        print("  %-12.3f %9.1f %12.3f %12s %14s" % (m, 100 * m / BOUND, kT_min, "n/a", "no cut possible"))
        continue
    L_min = t0_min / (1 - t0_min)
    kp_floor = 248 * L_min / 1.1512
    print("  %-12.3f %9.1f %12.3f %12.3f %13.0f" % (m, 100 * m / BOUND, kT_min, t0_min, kp_floor))
print("")
print("  (!) WHY THE MULTIPLICATIVE MODEL IS PROBABLY PESSIMISTIC, and I flag it rather than use it")
print("    silently: at steady state p -> 0 and the FEEDFORWARD is inner-loop-blind, so structurally")
print("    i' = u/k_T - f, i.e. ADDITIVE in (u/k_T - u), not multiplicative in |i|.  STATE.md's own")
print("    measured decomposition in steady curves is f = +0.800 with i = -0.392 OPPOSING it and a")
print("    net output of only +0.108.  With f dominant and i of the opposite sign, needing MORE")
print("    output makes i LESS negative -- |i| would FALL, not rise.  I report the multiplicative")
print("    bound because it is the one that could disqualify a candidate; the additive structure")
print("    says the true cost is smaller.  [BELIEF -- I do not have max|i| paired with u on a route.]")

# ---------------------------------------------------------------------------------------------- 5
print("\n" + "=" * 122)
print("SECTION 5 -- Kp = 0.  I AGREE IT STAYS DEAD, and the actuator spec adds a third reason.")
print("=" * 122)
print("  1. |T(0)| = 0 EXACTLY (type-0 plant, C(s) = Kd_r*s, L(0) = 0).  zn285 sec1.4, and the")
print("     orchestrator's own integer mirror.  [EVIDENCE]")
print("  2. The outer integrator cannot close a plant with zero DC gain: it winds up without bound")
print("     and never converges.  Its bound is +-%.3f, so it rails and the lane is lost." % BOUND)
print("  3. NEW, on the actuator spec: |T(0)| = 0 is MAXIMAL infidelity -- the actuator delivers")
print("     none of the demanded rate at DC.  It is not a low-authority actuator, it is not an")
print("     actuator.")
print("  ==> CONFIRMED DEAD.  Note this makes Kp = 0 unusable even as a Ku-hunt drive.")

# ---------------------------------------------------------------------------------------------- 6
print("\n" + "=" * 122)
print("SECTION 6 -- WHAT I COULD NOT COMPUTE, and what would make it computable")
print("=" * 122)
print("  NOT COMPUTABLE from measured data, and I decline to manufacture it:")
print("   * a full closed-loop |T(f)| curve  -- section 0: the two models disagree and the ring")
print("     lives in a lane the Nyquist model's forward path does not contain.")
print("   * f_-3dB (closed-loop bandwidth)   -- needs the plant MAGNITUDE above ~5 Hz.  The record")
print("     measures the plant PHASE (-28 deg @10 Hz, -73 deg @22 Hz) and its DC gain, never its")
print("     magnitude in between.  Any f_-3dB I printed would be an artefact of assuming flat.")
print("   * max|T| over 0-50 Hz             -- the 20 Hz creep line has NO measured |L| at all")
print("     (CREEP-20HZ item 7(a): L_in(line) = -1 by construction at a spectral line), so its")
print("     peak height is unquantified in both directions.")
print("  WHAT WOULD MAKE THEM COMPUTABLE: a plant MAGNITUDE identification -- a swept or")
print("  broadband excitation with the 427 T tap and the 0x18F rate read simultaneously.  That is a")
print("  drive design, not a build, and it is the single measurement that would turn this whole")
print("  framework from composed to identified.")
