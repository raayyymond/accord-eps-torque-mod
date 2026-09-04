# -*- coding: utf-8 -*-
r"""SUPPLEMENT to zn_backwards_no_overshoot.py -- the three robustness checks the headline needs.

1. THE LOWER ROOT MOVES WITH Kp.  Every published statement of the form "Kd 122 sits 3 % above the
   ring root of 118" compares a CANDIDATE Kd against the root computed at Kp 248.  ZN-PI also cuts
   Kp.  Recompute each candidate's margin against the root AT ITS OWN Kp.
2. PER-ROUTE ARMS.  The pooled arms (0.55/_+96, 1.19/_-27) hide a 1.6x route-to-route servo-share
   spread.  Re-run every candidate on r36's and r38's own measured arms.
3. THE |L_today| INTERVAL [0.944, 0.990] and a coarse `s`-sensitivity sweep on the r24 arm magnitude.

Run: python analysis-2020accord/studies/pidframe/zn_backwards_supp.py
"""
import cmath
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zn_backwards_no_overshoot as Z  # noqa: E402

C, Hlag, GM, track = Z.C, Z.Hlag, Z.GM, Z.track
F0 = Z.F0

ARMS = {
    "pooled": (0.55, 96.0, 1.19, -27.0),
    "r36 (largest servo share)": (0.69, 85.0, 1.16, -36.0),
    "r38 (smallest servo share)": (0.42, 95.0, 1.12, -22.0),
}


def make(arm, L_today=0.976):
    ls_m, ls_p, lr_m, lr_p = arm
    LS = ls_m * cmath.exp(1j * math.radians(ls_p))
    LR = lr_m * cmath.exp(1j * math.radians(lr_p))

    def raw(kp, kd):
        R = C(F0, kp, kd) / C(F0, 248, 128)
        return abs(LS * R + LR)

    base = raw(248, 128)
    L73 = lambda kp, kd: L_today * raw(kp, kd) / base          # noqa: E731

    def root(kp, lo=0.5, hi=250.0):   # hi < the UPPER root, else the V shape defeats the bisection
        f = lambda kd: L73(kp, kd) - 1.0                       # noqa: E731
        if f(lo) * f(hi) >= 0:
            return float("nan")
        for _ in range(80):
            m = (lo + hi) / 2
            if f(lo) * f(m) < 0:
                hi = m
            else:
                lo = m
        return (lo + hi) / 2

    return L73, root


CANDS = [("today (V282)", 248, 128), ("Q1: Kp 148, Kd 128", 148, 128), ("ZN-PI (new) 148/122", 148, 122),
         ("F: 248/160", 248, 160), ("Kp 148, Kd 160", 148, 160), ("Kp 200, Kd 128", 200, 128),
         ("Kp 176, Kd 128", 176, 128), ("ZN some-overshoot 183/90", 183, 90),
         ("ZN no-overshoot 110/54", 110, 54), ("ZN no-overshoot 82/45", 82, 45)]

print("=" * 122)
print("1. THE LOWER ROOT MOVES WITH Kp -- every candidate against the root AT ITS OWN Kp (pooled arms)")
print("=" * 122)
L73, root = make(ARMS["pooled"])
print("  %-26s %5s %5s %10s %13s %13s %13s"
      % ("candidate", "Kp", "Kd", "|L(7.3)|", "root @ Kp 248", "root @ its Kp", "Kd / own root"))
for nm, kp, kd in CANDS:
    r_own = root(kp)
    print("  %-26s %5d %5d %10.3f %13.1f %13.1f %12.2fx%s"
          % (nm, kp, kd, L73(kp, kd), root(248), r_own, kd / r_own,
             "   ** BELOW **" if kd < r_own else ""))

print("\n  the root as a continuous function of Kp (pooled arms):")
print("   %6s" % "Kp" + "".join("%8d" % k for k in (248, 220, 200, 176, 148, 128, 100, 64, 0)))
print("   %6s" % "root" + "".join("%8.1f" % root(k) for k in (248, 220, 200, 176, 148, 128, 100, 64, 0)))
print("   %6s" % "Kd128/" + "".join("%8.2f" % (128.0 / root(k)) for k in (248, 220, 200, 176, 148, 128, 100, 64, 0)))

print("\n" + "=" * 122)
print("2. PER-ROUTE ARMS -- the dominant uncertainty (1.6x servo-share spread)")
print("=" * 122)
for arm_nm, arm in ARMS.items():
    L73a, roota = make(arm)
    print("\n  --- arms: %s ---" % arm_nm)
    print("  %-26s %5s %5s %10s %13s %13s" % ("candidate", "Kp", "Kd", "|L(7.3)|", "root @ its Kp", "Kd / root"))
    for nm, kp, kd in CANDS[:5]:
        r_own = roota(kp)
        print("  %-26s %5d %5d %10.3f %13.1f %12.2fx%s"
              % (nm, kp, kd, L73a(kp, kd), r_own, kd / r_own, "   ** BELOW **" if kd < r_own else ""))

print("\n" + "=" * 122)
print("3. |L_today| INTERVAL [0.944, 0.990]  and  an `s`-SENSITIVITY SWEEP on the r24 arm magnitude")
print("   (`s` = r24 real/closed-form = 0.37 [0.24-0.52]; scaling the r24 arm by s/0.37 and")
print("    renormalising Ls + Lr = 1 is the coarse propagation nobody has done)")
print("=" * 122)
print("  %-14s %10s %12s %12s %12s %12s"
      % ("|L_today|", "arms", "root @248", "root @148", "|L| 248/128", "|L| 148/128"))
for Lt in (0.944, 0.976, 0.990):
    L73b, rootb = make(ARMS["pooled"], Lt)
    print("  %-14.3f %10s %12.1f %12.1f %12.3f %12.3f"
          % (Lt, "pooled", rootb(248), rootb(148), L73b(248, 128), L73b(148, 128)))

print("")
print("  `s` sweep -- r24 arm magnitude scaled, then BOTH arms renormalised so |Ls| + |Lr| is preserved:")
print("  %-10s %8s %8s %12s %12s %12s %12s"
      % ("s", "|Ls|", "|Lr|", "root @248", "root @148", "|L| 248/128", "|L| 148/128"))
for s in (0.24, 0.30, 0.37, 0.43, 0.52):
    scale = s / 0.37
    ls_m, lr_m = 0.55, 1.19 * scale
    tot = (0.55 + 1.19) / (ls_m + lr_m)
    arm = (ls_m * tot, 96.0, lr_m * tot, -27.0)
    L73c, rootc = make(arm)
    print("  %-10.2f %8.3f %8.3f %12.1f %12.1f %12.3f %12.3f"
          % (s, arm[0], arm[2], rootc(248), rootc(148), L73c(248, 128), L73c(148, 128)))

print("\n" + "=" * 122)
print("4. THE GM COST OF NOT CUTTING Kd -- what the Kd cut buys in the blind band, and what it costs")
print("=" * 122)
print("  %-26s %5s %5s %9s %11s %13s" % ("candidate", "Kp", "Kd", "GM", "GM dB", "root margin"))
for nm, kp, kd in CANDS[:5]:
    gm, fx = GM(kp, kd)
    print("  %-26s %5d %5d %8.2fx %10.1f %12.2fx" % (nm, kp, kd, gm, 20 * math.log10(gm), kd / root(kp)))
