# -*- coding: utf-8 -*-
"""c7 -- VERIFY THE CRUX: why does the k_d slot buy closure so cheaply, and where does Tier A stop?

The brief's prior was "margin is NOT binding (PM 95-141 deg), SHAKE is, so a lead adds gain exactly
where the cost is."  The first half is right about the CROSSOVER.  This script tests whether it is
right about the METRIC BAND, where |L| < 1 and what matters is |1 + L|, not the phase margin.
"""
import itertools
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                    # noqa: E402
from f5_frontier import FLOWN                          # noqa: E402
from c3_ceiling import Ceiling, C_gen, fmt, HDR        # noqa: E402

np.seterr(divide="ignore", invalid="ignore")
KD_LP = 2.0

if __name__ == "__main__":
    E = Ceiling()
    f = E.f
    FQ = [0.20, 0.29, 0.39, 0.59, 0.98, 1.46, 1.95, 2.54, 3.03]
    j = [int(np.argmin(np.abs(f - q))) for q in FQ]

    print("1. THE MECHANISM.  |K| = |C_new/C_old|, arg K, |rho| = |(1+L0)/(1+L1)| and |S| per frequency.")
    print("   A metric improvement needs |rho| < 1 IN THE 0.15-0.60 BAND; a shake cost is |U| growth")
    print("   at 1.8-3.5 Hz, which is |K * rho| there.")
    for lbl, kp, q, kd in (("ARM-KP2  KP3.0 Q0.60 kd0", 3.0, 0.60, 0.0),
                           ("+ k_d 0.40              ", 3.0, 0.60, 0.40)):
        C1 = C_gen(f, E.v, kp, 14.0, 0.3, 0.0, q, kd=kd, kd_lp_hz=KD_LP)
        K = C1 / E.C0
        L1 = E.L0 * K
        rho = (1.0 + E.L0) / (1.0 + L1)
        print(f"\n   {lbl}")
        print("      f Hz   " + " ".join(f"{q_:>7.2f}" for q_ in FQ))
        print("      |K|    " + " ".join(f"{np.mean(np.abs(K[:, i])):7.3f}" for i in j))
        print("      argK   " + " ".join(f"{np.degrees(np.angle(np.mean(K[:, i]))):7.1f}" for i in j))
        print("      |L1|   " + " ".join(f"{np.mean(np.abs(L1[:, i])):7.3f}" for i in j))
        print("      |rho|  " + " ".join(f"{np.mean(np.abs(rho[:, i])):7.3f}" for i in j))
        print("      |K*rho|" + " ".join(f"{np.mean(np.abs((K*rho)[:, i])):7.3f}" for i in j))
    print()
    print("   READ: the k_d term's |K| is ~1.0 below 0.3 Hz and ~2x at 2-3 Hz -- the brief's prior is")
    print("   correct about WHERE THE GAIN GOES.  Whether that costs anything is |K*rho| there.")

    print()
    print("=" * 132)
    print("2. DOES TIER A SATURATE?  k_d extended past the earlier grid edge (0.8), SteerKP free.")
    print(HDR + "   config")
    rows = []
    for kp, q, kd in itertools.product([3.0, 4.0, 5.0, 6.0, 8.0], [0.2, 0.3, 0.4, 0.6, 0.8, 1.0],
                                       [0.0, 0.4, 0.8, 1.2, 1.6, 2.4, 3.2]):
        r = E.score(kp=kp, laf=14.0, q=q, kd=kd, kd_lp_hz=KD_LP)
        r.update(kp=kp, q=q, kd=kd)
        rows.append(r)
    tierA = lambda r: np.isnan(r["wc"]) or r["wc"] <= 0.50
    for ceil in (32.4, 37.5, 45.0, 60.0, 90.0, 140.0, 176.0):
        ok = [r for r in rows if r["shake_common"] <= ceil and tierA(r)]
        if ok:
            b = min(ok, key=lambda r: r["metric"])
            print(fmt(f"TIER A shake <= {ceil:5.1f}", b, f"KP {b['kp']:.1f} Q {b['q']:.2f} kd {b['kd']:.2f}"))
    print("   (no shake ceiling at all, Tier A only):")
    ok = [r for r in rows if tierA(r)]
    b = min(ok, key=lambda r: r["metric"])
    print("   " + fmt("TIER A unconstrained", b, f"KP {b['kp']:.1f} Q {b['q']:.2f} kd {b['kd']:.2f}"))
    print("   (no shake ceiling, no tier):")
    b = min(rows, key=lambda r: r["metric"])
    print("   " + fmt("unconstrained", b, f"KP {b['kp']:.1f} Q {b['q']:.2f} kd {b['kd']:.2f}"))

    print()
    print("=" * 132)
    print("3. THE k_d TERM'S UNMODELLED COST.  It is the ONLY candidate that creates a NEW")
    print("   differentiating path (d/dt of the measured steering angle).  The re-synthesis scales the")
    print("   MEASURED UFB spectrum, so it cannot see sensor noise entering through a path that does")
    print("   not exist today.  Size of the blind spot, from the logged steering angle:")
    D = np.load(FRONT / "out" / "f1_0000006c--68c6e94b17.npz")
    ff, SR = D["f"], D["SR"]
    hi = (ff >= 5.0) & (ff <= 45.0)
    lo = (ff >= 0.15) & (ff <= 2.4)
    print(f"   logged steering-RATE spectrum: power above 5 Hz / power in 0.15-2.4 Hz = "
          f"{float(np.sum(np.abs(SR[:, hi])**2) / np.sum(np.abs(SR[:, lo])**2)):.3f}")
    print("   the D path sees measurement_rate, LOW-PASSED at MAX_LAT_JERK_UP-0.5 = 2.0 Hz and CLIPPED")
    print("   to +/-2.5 m/s^3, so the 5-45 Hz content above is attenuated by |LP(2 Hz)|:")
    from c3_ceiling import lp1
    for q_ in (5.0, 10.0, 20.0, 40.0):
        print(f"      |LP(2Hz)| at {q_:4.0f} Hz = {abs(lp1(np.array([q_]), 2.0)[0]):.4f}")
    del D
