# -*- coding: utf-8 -*-
r"""ARM GEOMETRY -- what ACTUALLY moves the 7.3 Hz lower root, and the `s` sensitivity WITHOUT the
renormalisation that hid it.

Subagent `znback`, 2026-09-04, third pass.  Written because `team-lead` correctly caught that my
stated mechanism is SELF-CONTRADICTORY: "cancels less" and "the sum shrinks" are opposite
consequences of the same phase change.  This script resolves it from the numbers instead of
rewording it.  ANALYSIS ONLY.

Ls (servo arm, INCLUDING the plant) = Ls_base * R, where R = C(f0,Kp,Kd)/C(f0,248,128) is the
controller-only ratio; every other factor in the servo path is common and cancels in R.
Lr (r24 arm) is FIXED -- FUN_0003aa2c references neither Kp (0xE5378) nor Kd (0xE511C).

Run: python analysis-2020accord/studies/pidframe/zn_arm_geometry.py
"""
import cmath
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zn_backwards_no_overshoot as Z  # noqa: E402

C, GM, track, dg = Z.C, Z.GM, Z.track, Z.dg
F0 = Z.F0
LS0_M, LS0_P = 0.55, 96.0
LR_M, LR_P = 1.19, -27.0
L_TODAY = 0.976


def arms(kp, kd, ls_m=LS0_M, lr_m=LR_M):
    R = C(F0, kp, kd) / C(F0, 248, 128)
    Ls = ls_m * cmath.exp(1j * math.radians(LS0_P)) * R
    Lr = lr_m * cmath.exp(1j * math.radians(LR_P))
    return Ls, Lr


def decomp(Ls, Lr):
    """project Ls onto Lr: the ALONG component cancels (if negative), the QUADRATURE adds in RMS."""
    u = Lr / abs(Lr)
    proj = (Ls / u)
    return proj.real, proj.imag       # along (signed), quadrature


print("=" * 126)
print("1. THE GEOMETRY AT 7.3 Hz -- Lr fixed, Ls = Ls_base * R(Kp,Kd).  Kd HELD AT 128.")
print("=" * 126)
print("  %5s %16s %22s %11s %11s %12s %12s"
      % ("Kp", "Lr (fixed)", "Ls (with plant)", "angle Ls-Lr", "|Ls+Lr|", "ALONG Lr", "QUADRATURE"))
base = None
for kp in (248, 200, 176, 148, 100):
    Ls, Lr = arms(kp, 128)
    a, q = decomp(Ls, Lr)
    s = abs(Ls + Lr)
    if base is None:
        base = s
    print("  %5d   %5.3f /_%+6.1f    %6.3f /_%+7.1f %10.1f %11.4f %12.4f %12.4f"
          % (kp, abs(Lr), dg(Lr), abs(Ls), dg(Ls), dg(Ls) - dg(Lr), s, a, q))
print("")
print("  sanity: |Lr| = %.3f alone, |Ls+Lr| = %.4f at Kp 248  ==> the servo arm IS cancelling today."
      % (LR_M, base))
print("  and  |Ls+Lr|^2 = (|Lr| + ALONG)^2 + QUADRATURE^2  -- check at Kp 248: %.4f vs %.4f"
      % (base, math.hypot(LR_M + decomp(*arms(248, 128))[0], decomp(*arms(248, 128))[1])))

print("\n" + "=" * 126)
print("2. !! MY STATED MECHANISM WAS WRONG.  What the numbers actually say:")
print("=" * 126)
a0, q0 = decomp(*arms(248, 128))
a1, q1 = decomp(*arms(148, 128))
print("  Kp 248 -> 148 at fixed Kd 128:")
print("    angle between the arms : %.1f deg -> %.1f deg   ==> CLOSER to anti-phase, not further"
      % (dg(arms(248, 128)[0]) - LR_P, dg(arms(148, 128)[0]) - LR_P))
print("    ALONG-Lr component     : %+.4f -> %+.4f   ==> cancellation GROWS slightly (%.1f %%)"
      % (a0, a1, 100 * (a1 / a0 - 1)))
print("    QUADRATURE component   : %+.4f -> %+.4f   ==> falls %.1f %%  <-- THE DOMINANT TERM"
      % (q0, q1, 100 * (1 - q1 / q0)))
print("    |Ls+Lr|                : %.4f -> %.4f" % (abs(sum(arms(248, 128))), abs(sum(arms(148, 128)))))
print("")
print("  CORRECTED MECHANISM, in one sentence:")
print("    Lowering Kp rotates the servo arm TOWARD the D term's +88.7 deg, which moves it CLOSER to")
print("    anti-phase with the fixed r24 arm; the small shrink in |Ls| costs almost nothing in the")
print("    cancelling (along-Lr) direction because the rotation compensates it, while it removes")
print("    most of the QUADRATURE component -- and the quadrature is what was inflating the RMS sum.")
print("    ==> the sum shrinks because the servo arm becomes a PURER canceller, not a weaker one.")
print("  (My earlier 'sits further from anti-phase and cancels less' was wrong on BOTH clauses.)")

print("\n" + "=" * 126)
print("3. WHY THE ROOT MOVES DOWN WITH Kp -- the same decomposition, now sweeping Kd at each Kp")
print("=" * 126)
for kp in (248, 148):
    root = Z.lower_root(kp)
    print("  --- Kp %d (root at Kd %.1f) ---" % (kp, root))
    print("      %6s %9s %11s %11s %12s %11s" % ("Kd", "|Ls|", "angle Ls", "ALONG", "QUADRATURE", "|Ls+Lr|"))
    for kd in (192, 160, 128, 110, int(round(root)), 80, 60):
        Ls, Lr = arms(kp, kd)
        a, q = decomp(Ls, Lr)
        mark = "   <-- ROOT" if abs(kd - root) < 1.5 else ""
        print("      %6d %9.4f %+10.1f %11.4f %12.4f %11.4f%s" % (kd, abs(Ls), dg(Ls), a, q, abs(Ls + Lr), mark))
    print("")
print("  ==> cutting Kd rotates Ls BACK toward P (angle falls), which BOTH reduces the along-Lr")
print("      cancellation AND (below the corner) is no longer compensated -- the sum climbs to 1.")
print("      At a LOWER Kp the SAME Kd leaves C more D-dominated (|D|/|P| = 33.03*sin(pi f T)/(Kp/256)),")
print("      so the arm stays rotated further out; you must cut Kd FURTHER before the along-Lr")
print("      cancellation collapses.  THAT is why the root falls with Kp.  [EVIDENCE, byte-exact C]")

print("\n" + "=" * 126)
print("4. !! THE `s` SENSITIVITY, WITHOUT MY RENORMALISATION.  team-lead is right that preserving")
print("   |Ls|+|Lr| FORCED the servo arm up when r24 went down and hid the threat.")
print("=" * 126)
print("  (a) NAIVE -- scale Lr down, leave Ls at 0.55.  This BREAKS the measurement:")
print("      %8s %9s %9s %12s %16s" % ("Lr scale", "|Ls|", "|Lr|", "|Ls+Lr|", "implied |L_today|"))
for sc in (1.0, 1 / 3.0, 1 / 5.0):
    Ls, Lr = arms(248, 128, lr_m=LR_M * sc)
    print("      %8.3f %9.3f %9.3f %12.4f %16.3f"
          % (sc, abs(Ls), abs(Lr), abs(Ls + Lr), L_TODAY * abs(Ls + Lr) / base))
print("      ==> a 3x smaller r24 predicts |L_today| = 0.46 against a MEASURED 0.976.  The naive")
print("          scaling is REFUTED BY THE MEASUREMENT -- it is not an admissible sensitivity.")
print("")
print("  (b) MEASUREMENT-CONSISTENT -- the real constraint is |Ls + Lr| = %.4f (that IS the" % base)
print("      measured 0.976 up to the shared normalisation).  Hold the two PHASES, scale |Lr|,")
print("      and SOLVE for |Ls|:   a^2 + r^2 + 2*a*r*cos(123 deg) = |Ls+Lr|^2")
COSA = math.cos(math.radians(LS0_P - LR_P))
print("      %8s %9s %9s %13s %13s %13s %13s"
      % ("Lr scale", "|Lr|", "|Ls|", "root @Kp248", "root @Kp148", "|L| 148/128", "Kd128 margin"))
rows = []
for sc in (1.0, 0.8, 0.6, 1 / 3.0, 0.25, 1 / 5.0):
    r = LR_M * sc
    # a^2 + 2*a*r*cosA + (r^2 - base^2) = 0
    disc = (2 * r * COSA) ** 2 - 4 * (r * r - base * base)
    a = (-2 * r * COSA + math.sqrt(disc)) / 2
    L73f, rootf = None, None

    def mk(a_=a, r_=r):
        LS = a_ * cmath.exp(1j * math.radians(LS0_P))
        LR = r_ * cmath.exp(1j * math.radians(LR_P))
        b = abs(LS + LR)

        def f(kp, kd):
            R = C(F0, kp, kd) / C(F0, 248, 128)
            return L_TODAY * abs(LS * R + LR) / b
        return f
    f = mk()

    def root(kp, lo=0.5, hi=250.0):
        g = lambda kd: f(kp, kd) - 1.0        # noqa: E731
        if g(lo) * g(hi) >= 0:
            return float("nan")
        for _ in range(80):
            m = (lo + hi) / 2
            if g(lo) * g(m) < 0:
                hi = m
            else:
                lo = m
        return (lo + hi) / 2
    r248, r148 = root(248), root(148)
    rows.append((sc, r, a, r248, r148, f(148, 128)))
    print("      %8.3f %9.3f %9.3f %13.1f %13.1f %13.3f %12.2fx"
          % (sc, r, a, r248, r148, f(148, 128), 128 / r148 if r148 == r148 else float("nan")))
print("")
print("  ==> AT EVERY r24 SCALE THE MEASUREMENT FORCES |Ls| UP, AND THE ROOT STILL FALLS WITH Kp.")
print("      That is not an artefact of my renormalisation -- it survives the constraint-solved")
print("      version too, because it is driven by the CONTROLLER's rotation, which is byte-exact")
print("      and `s`-independent.  What DOES move is the root's absolute location.")
print("")
print("  (c) THE REGIME CHANGE, stated plainly.  At Lr scale 1/3 the solved |Ls| = %.2f > |Lr| = %.2f:"
      % (rows[3][2], rows[3][1]))
print("      the SERVO becomes the dominant arm.  That is exactly the branch grind39 is adjudicating")
print("      ('the servo is the 7 Hz pump after all').  In that regime a Kp CUT attacks the arm that")
print("      DOMINATES, so it gets MORE effective, not less -- see the |L| 148/128 column falling")
print("      from %.3f to %.3f.  My Kp conclusions STRENGTHEN if grind39's branch is right."
      % (rows[0][5], rows[5][5]))
print("      !! BUT THE Kd-RAISE CONCLUSION WEAKENS IN THAT REGIME -- check it:")
print("      %8s %9s %9s %13s %13s %13s" % ("Lr scale", "|Lr|", "|Ls|", "|L| 248/160", "|L| 248/192", "vs today"))
for sc, r, a, _, _, _ in rows:
    LS = a * cmath.exp(1j * math.radians(LS0_P))
    LR = r * cmath.exp(1j * math.radians(LR_P))
    b = abs(LS + LR)
    g = lambda kp, kd: L_TODAY * abs(LS * (C(F0, kp, kd) / C(F0, 248, 128)) + LR) / b   # noqa: E731
    print("      %8.3f %9.3f %9.3f %13.3f %13.3f %12.2fx" % (sc, r, a, g(248, 160), g(248, 192), g(248, 192) / L_TODAY))
