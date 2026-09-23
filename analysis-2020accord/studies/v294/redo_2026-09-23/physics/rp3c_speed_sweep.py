"""Fine speed sweep of the wheel mode with/without the shipped trim: zeta, f_n, decay rate sigma, step overshoot.
Worlds: light b in {5e-4, 6e-4, 9e-4}; k = map, and map x HOLD_LEVEL (1.15 @12.5 -> 1.45 @17.5, the fork's rev-6.4 measured
correction); d = 1..3 ticks; also a direct step-response overshoot from the discrete closed loop."""
import math
import numpy as np
from scipy import signal
from rp3_wheel_mode import loop, closed_poles, mode, k_of, b_ident, J0, TS

LEVEL_BP, LEVEL_V = [12.5, 17.5], [1.15, 1.45]


def step_overshoot(Ln, Ld, J, b, k, n=6000):
    # response of theta to a step in u_ext: theta = G/(1+L) u ; use the closed loop via polynomials:
    from rp3_wheel_mode import plant_tf
    gn, gd = plant_tf(J, b, k)
    # T_cl = G / (1 + L) = gn/gd / (1 + Ln/Ld) = gn*Ld / (gd*(Ld + Ln))
    num = np.convolve(gn, Ld)
    nn = max(len(Ln), len(Ld)); A = np.zeros(nn); A[:len(Ld)] += Ld; A[:len(Ln)] += Ln
    den = np.convolve(gd, A)
    # remove common factor gd? (L contains gd in its denominator) -- simulate directly, it is stable
    y = signal.lfilter(num, den, np.ones(n))
    yss = 1.0 / k
    return (y.max() - yss) / yss, y


print(" v    k        b      | open: zeta  f_n  sigma  OS%  | trim: zeta  f_n  sigma  OS%  | zeta x   sigma x")
rows = []
for world in ("map", "levelled"):
    for b in (5e-4, 6e-4, 9e-4):
        for v in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12.5, 15, 19, 22, 26, 30):
            k = k_of(v) * (float(np.interp(v, LEVEL_BP, LEVEL_V)) if world == "levelled" and v >= 12.5 else 1.0)
            Ln0, Ld0 = loop(J0, b, k, gain=0.0); m0 = mode(closed_poles(Ln0, Ld0), 0.1, 8)
            Ln, Ld = loop(J0, b, k); m1 = mode(closed_poles(Ln, Ld), 0.1, 8)
            if m0 is None or m1 is None:
                print(f"{world[:3]} {v:5.1f} {k:.5f} {b:.0e} | open {m0} trim {m1} (overdamped)"); continue
            os0, _ = step_overshoot(Ln0, Ld0, J0, b, k)
            os1, _ = step_overshoot(Ln, Ld, J0, b, k)
            rows.append((world, b, v, m0, m1, os0, os1))
            if b == 6e-4 or v in (3, 5, 8):
                print(f"{world[:3]} {v:5.1f} {k:.5f} {b:.0e} | {m0[0]:.3f} {m0[1]:.2f} {m0[3]:5.2f} {os0*100:5.1f} | "
                      f"{m1[0]:.3f} {m1[1]:.2f} {m1[3]:5.2f} {os1*100:5.1f} | {m1[0]/m0[0]:.2f}    {m1[3]/m0[3]:.2f}")
# speed where zeta x crosses 1 (light 6e-4, map)
r = [(x[2], x[4][0] / x[3][0]) for x in rows if x[0] == "map" and x[1] == 6e-4]
for (v1, a1), (v2, a2) in zip(r, r[1:]):
    if (a1 - 1) * (a2 - 1) <= 0 and a1 != a2:
        print(f"\nzeta x crosses 1.00 between {v1} and {v2} m/s (map, b 6e-4): interpolated {v1 + (1-a1)*(v2-v1)/(a2-a1):.1f} m/s")
print("min zeta x over all rows:", min((x[4][0] / x[3][0], x[0], x[1], x[2]) for x in rows))
print("max step-overshoot increase (percentage points):", max(((x[6] - x[5]) * 100, x[0], x[1], x[2]) for x in rows))
