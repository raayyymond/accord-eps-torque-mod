# -*- coding: utf-8 -*-
"""s1_central.py -- adversary `stability`: re-derive the design's CENTRAL numbers (C1-C3 of ADV-stability-CRITERIA.md)
by two methods each, and the trim's 13-25 Hz damping sign under delay (attack surface b, first half).

Method 1: my z-domain lane (advlin.LaneLin) x the 3 ms rate former, exact.
Method 2: TIME DOMAIN -- a sampled sinusoidal wheel angle -> my integer rate former (round) -> my INTEGER lane
          (s0_lane_spotcheck.MyLane, == golden model) -> least-squares gain/phase of T against the analytic omega.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advlin as AL  # noqa: E402
from s0_lane_spotcheck import MyLane  # noqa: E402

LANES = dict(V294=AL.LaneLin(1011, 567, name="V294"), A1017=AL.LaneLin(1017, 567, name="A1017"),
             V282=AL.LaneLin(923, 1560, op="sum", kp=248, kd=128, name="V282"))


def td_T_per_omega(fa, f, W=100.0, secs=6.0, w=3):
    """time-domain opposing torque per deg/s at f: theta = (W/2 pi f) sin -> x = round(8 (th[n]-th[n-w])/(w ms)) -> the
    integer lane (x_lane = -x) -> T ; fit T = A cos + B sin over the last 3 s; return complex T/omega (opposing: -T/(+omega)
    in the lane's sign convention: T is in the tap sign, u = -T, so the opposing torque on a +left omega is +T... see note)."""
    n = int(secs * 1000)
    t = np.arange(n + w) * 1e-3
    th = (W / (2 * np.pi * f)) * np.sin(2 * np.pi * f * t)        # deg, + left
    om = W * np.cos(2 * np.pi * f * t)                             # deg/s
    lane = MyLane(1, fa, 567)
    T = np.zeros(n)
    for i in range(n):
        x = int(np.round(8.0 * (th[i + w] - th[i]) / (w * 1e-3)))
        Ti, _ = lane.tick(np.array([-x]), np.array([0]))
        T[i] = Ti[0]
    tt = t[w:w + n]
    m = tt > secs - 3.0
    X = np.vstack([np.cos(2 * np.pi * f * tt[m]), np.sin(2 * np.pi * f * tt[m]), np.ones(m.sum())]).T
    co, *_ = np.linalg.lstsq(X, T[m], rcond=None)
    # T = Re{ G * W e^{j w t} } with omega = W cos -> G = (A - jB) / W  (T in tap sign = + right).  The plant input is
    # u = -T (+ left), so the torque OPPOSING a + left omega is +T ... the opposing torque per deg/s is G itself.
    return (co[0] - 1j * co[1]) / W, lane


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    fC = np.array([1.0, 2.0, 2.5, 3.0, 5.0])
    pr("C1  trim opposing torque T/omega (T per deg/s), angle deg (0 = damping, +90 inertia), damping part |.|cos")
    for nm in ("V294", "A1017"):
        To = AL.trim_T_per_omega(LANES[nm], fC)
        pr("  %-6s z-domain  |T/w| %s  angle %s  damp %s" % (nm, np.round(np.abs(To), 3).tolist(),
                                                           np.round(np.degrees(np.angle(To)), 1).tolist(),
                                                           np.round(np.abs(To) * np.cos(np.angle(To)), 3).tolist()))
        td = []
        for f in fC:
            g, _ = td_T_per_omega(1011 if nm == "V294" else 1017, f)
            td.append(g)
        td = np.array(td)
        pr("  %-6s TIME-dom  |T/w| %s  angle %s  damp %s" % (nm, np.round(np.abs(td), 3).tolist(),
                                                           np.round(np.degrees(np.angle(td)), 1).tolist(),
                                                           np.round(np.abs(td) * np.cos(np.angle(td)), 3).tolist()))
        fg = np.linspace(0.3, 10, 4000)
        Tg = AL.trim_T_per_omega(LANES[nm], fg)
        dmp = np.abs(Tg) * np.cos(np.angle(Tg))
        pr("  %-6s damping-part peak %.3f T per deg/s at %.2f Hz" % (nm, dmp.max(), fg[np.argmax(dmp)]))
    pr("  design: V294 1.61/1.83/1.91/1.60 at 2/2.5/3/5 Hz, A1017 2.17/2.19/2.11/1.52; peak 3.15 -> 2.32 Hz")

    fH = np.array([9.0, 13.0, 17.0, 20.0, 25.0, 30.0])
    pr("\nC2  |T/x| (T per x count) and ratio A1017/V294; |P/x| at 20 Hz")
    for nm in ("V294", "A1017", "V282"):
        pr("  %-6s |T/x| %s   |P/x|(20) %.3f" % (nm, np.round(np.abs(LANES[nm].ctf(fH)), 4).tolist(),
                                                abs(LANES[nm].ptf(np.array([20.0]))[0])))
    pr("  ratio A1017/V294 %s" % np.round(np.abs(LANES["A1017"].ctf(fH)) / np.abs(LANES["V294"].ctf(fH)), 4).tolist())
    pr("  ratio V294/V282  %s" % np.round(np.abs(LANES["V294"].ctf(fH)) / np.abs(LANES["V282"].ctf(fH)), 4).tolist())

    pr("\nC3  arithmetic")
    for a in (1011, 1017):
        Ka = 8e-3 * 567 / (1024 - a) * (960 / 256) * (254 / 256) * (2 * 507 / (32 * 32)) * (5346 / 32768)
        bmax = 2 ** 31 * (1024 - a) / (12000 * a)
        s_max = 567 * 12000 / (1024 - a)
        pr("  a %d: K_alpha %.4f T per deg/s^2 ; pole %.3f Hz ; b_max %.1f ; b/b_max %.3f ; worst a*s %.4e margin %.3f ;"
           " fb clamp binds at alpha %.0f deg/s^2 (below the pole)" % (
               a, Ka, -np.log(a / 1024) / (2 * np.pi * 1e-3), bmax, 567 / bmax, a * s_max, 2 ** 31 / (a * s_max),
               1024 / (8e-3 * 567 / (1024 - a))))
    # int32 on the integer lane at the |x| = 12000 edge: march to steady state
    for a in (1011, 1017):
        L = MyLane(1, a, 567)
        for _ in range(8000):
            L.tick(np.array([12000]), np.array([0]))
        pr("  integer march at x = +12000 for 8 s: a %d  max|a*s| %.4e  margin %.3f" % (a, L.max_as[0], 2 ** 31 / L.max_as[0]))

    pr("\n(b1) the trim's damping part at 13-25 Hz vs extra sensing/actuation delay (T per deg/s; + = damping)")
    fB = np.array([13.0, 17.0, 20.0, 25.0])
    V282m = np.abs(AL.trim_T_per_omega(LANES["V282"], fB))
    pr("  V282 |T/w| at %s = %s (the on-car de-damper's size)" % (fB.tolist(), np.round(V282m, 3).tolist()))
    for age in (0.0, 2.0, 4.0, 6.0, 9.0, 12.0, 18.0):
        row = []
        for nm in ("V294", "A1017", "V282"):
            To = AL.trim_T_per_omega(LANES[nm], fB, age_ms=age)
            row.append(np.abs(To) * np.cos(np.angle(To)))
        dlt = row[1] - row[0]
        pr("  +%4.1f ms  V294 %s  A1017 %s  V282 %s  | A1017-V294 %s = %s %% of V282 |T/w|" % (
            age, np.round(row[0], 3).tolist(), np.round(row[1], 3).tolist(), np.round(row[2], 2).tolist(),
            np.round(dlt, 4).tolist(), np.round(100 * dlt / V282m, 2).tolist()))
    open(os.path.join(HERE, "s1_central_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
