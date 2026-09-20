# -*- coding: utf-8 -*-
"""VERIFY THE CRUX MYSELF, before relaying anything.

Three decision-bearing claims to check:
  1. WHAT makes the V282 controllers outrank r71 -- the relay, or LAF?  (decompose C_e)
  2. Does the ONE NEW TERM change clause (b) at all?  (score (b) with jerk OFF = gate #1's model)
  3. How fragile is clause (a)'s r73 PASS?  (it cleared the 3.000 Hz edge by 0.04 Hz)
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g2_lib as G  # noqa: E402

FG = np.arange(0.5, 12.0005, 0.002)


def main():
    C = G.read_controllers()
    P = G.load_plants("22+")

    print("=" * 120)
    print("CRUX 1 -- WHY the V282 controllers outrank r71.  |C_e| decomposed at 2.6 Hz (r71's crossing).")
    print("=" * 120)
    f = np.array([2.6])
    v = 26.5
    print(f"{'route':22s} {'label':22s} {'kp/LAF':>8s} {'fric*N':>8s} {'relay share':>11s} "
          f"{'|C_e| g#1':>10s} {'|C_e| g#2':>10s} {'ratio to r71':>13s}")
    base = None
    for rt in [G.R71, G.R73, G.R72] + G.CLEAN_T64 + G.CLEAN_V282 + G.CLEAN_V282_OLD:
        p = C[rt]
        A = P[rt]["A"]
        N = G.df_ramp(A)
        pid, rel = p["kp"] / p["laf"], p["fric"] * N
        c1 = abs(G.C_e(f, v, p, A, jerk=False)[0])
        c2 = abs(G.C_e(f, v, p, A, jerk=True)[0])
        if base is None:
            base = c2
        print(f"{rt:22s} {p['lbl']:22s} {pid:8.4f} {rel:8.4f} {rel/(pid+rel):10.1%} "
              f"{c1:10.4f} {c2:10.4f} {c2/base:12.2f}x")
    print("\n  r71's SteerFriction is 0.011; the V282 routes' is 0.010-0.030.  Their LAF is 2.11-6.0 vs r71's 14.0.")
    print("  If the relay were the whole story the V282 @0.010 routes would sit BELOW r71.  They do not.")

    print("\n" + "=" * 120)
    print("CRUX 2 -- does the ONE NEW TERM change clause (b)?   (b) scored with jerk OFF = gate #1's controller")
    print("=" * 120)
    cleans = [G.R72] + G.CLEAN_T64_ALL + G.CLEAN_V282 + G.CLEAN_V282_OLD
    for jerk in (False, True):
        ok = 0
        for prt in G.PREREG_PLANTS:
            pl = P[prt]
            r = {c: G.first_crossing(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], C[c], pl["A"], 0.065, 6e-4, jerk))[0]
                 for c in cleans + G.POSITIVES}
            wp, wc = min(r[t] for t in G.POSITIVES), max(r[c] for c in cleans)
            ok += wp > wc
            print(f"   jerk={'ON ' if jerk else 'OFF'}  plant {prt.split('--')[0][-2:]}: "
                  f"worst positive {wp:6.2f}   worst clean {wc:6.2f}  ({max(cleans, key=lambda c: r[c]).split('--')[0][-2:]})"
                  f"   {'ok' if wp > wc else 'FAIL'}")
        print(f"   jerk={'ON ' if jerk else 'OFF'}  => {ok}/3\n")
    print("  The new term does not touch (b)'s failure: it raises BOTH positives and every relay-live clean,")
    print("  and the V282 controllers are relay-live too.")

    print("=" * 120)
    print("CRUX 3 -- how fragile is clause (a)'s r73 PASS?  It cleared the 3.000 Hz edge by 0.04 Hz at b=6e-4/65 ms.")
    print("=" * 120)
    pl73, p73 = P[G.R73], dict(C[G.R73])
    print(f"{'variant':52s} {'f_cross':>9s} {'|L|':>7s} {'in [3.000,8.125]?':>19s}")
    variants = [
        ("as flown, notch f0 from ITS OWN commit (2.058 Hz)", dict(p73)),
        ("gate #1's constant: notch f0 = 2.212 Hz (K_LATE)", dict(p73, ktbl=G.K_LATE)),
        ("rate-loop RC = 0.01 (gate #1's wrong constant)", dict(p73, rate_rc=0.01)),
        ("both of gate #1's constants", dict(p73, ktbl=G.K_LATE, rate_rc=0.01)),
        ("notch Q = 1.0 but centred on the PLANT mode 2.212", dict(p73, ktbl=G.K_LATE)),
        ("no notch at all (NOT flown -- diagnostic only)", dict(p73, notch=None)),
    ]
    for name, p in variants:
        r, fx = G.first_crossing(FG, G.L_of(FG, pl73["v"], pl73["alpha"], pl73["c"], p, pl73["A"], 0.065, 6e-4))
        print(f"{name:52s} {fx:8.3f}  {r:7.2f} {('YES' if 3.0 <= fx <= 8.125 else 'no'):>19s}")
    print("\n  r73 OBSERVED: 4.0-6.5 Hz.  The model's best placement is ~3.0-3.3 Hz -- at or below the")
    print("  bottom edge of the +/-25% window, never inside the observed band itself.")

    print("\n" + "=" * 120)
    print("CRUX 4 -- clause (b) if the cross-firmware V282 anchors were dropped (NOT PERMITTED -- the anchor")
    print("           set is fixed; reported so the operator can see exactly where the failure lives)")
    print("=" * 120)
    for name, cl in (("V293-era cleans only (r72 + T64 x3)", [G.R72] + G.CLEAN_T64_ALL),
                     ("prereg's fixed set (with V282)", cleans)):
        ok = 0
        for prt in G.PREREG_PLANTS:
            pl = P[prt]
            r = {c: G.first_crossing(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], C[c], pl["A"], 0.065, 6e-4))[0]
                 for c in cl + G.POSITIVES}
            ok += min(r[t] for t in G.POSITIVES) > max(r[c] for c in cl)
        print(f"   {name:42s} -> both positives above all cleans on {ok}/3 plants")


if __name__ == "__main__":
    main()
