# -*- coding: utf-8 -*-
"""straight_understeer_road.py -- THE ROAD-SIDE CONSEQUENCE of the SteerRatio measurement bias.

straight_understeer_sr.py section F measured the TRUE steering ratio from the wire (16.4-16.8 on four
routes, control r34 at SR 16.1 returning bias 1.05).  This script asks the road whether the predicted
consequence is actually there:

  at the torque controller's own equilibrium the loop drives m -> des, and m = bias * road, so the ROAD
  receives des / bias.  With bias = 1.33 that is a 25 % under-turn that openpilot cannot see, because
  its own `error` is zero while it happens.

I   road / asked, SR-free on BOTH sides:  lat_torqued = v*yaw_cal - g sin(roll_dev)  vs
    controlsState.desiredLateralAccel, delay-matched by a lag sweep, reported as OLS(road|des) and
    OLS(des|road)^-1 (the two attenuation bounds) and TLS, per |des| stratum.
J   the same on STRAIGHT frames only, after a 0.2 Hz low-pass on both channels (on straights the
    per-sample signal is below the yaw noise floor; the lane-offset correction lives at 0.05-0.3 Hz).
K   the counterfactual: what SteerRatio 16.1 would have delivered, and what is left over for the EPS.

Run: python rlog-tools/studies/osc-highangle/straight_understeer_road.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import straight_understeer_v282 as S  # noqa: E402
import straight_understeer_sr as SR  # noqa: E402

B, FS = S.B, S.FS
ARMS, SR_PARAM = S.ARMS, S.SR_PARAM
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def ols(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 100:
        return np.nan, 0
    return float((x @ y) / (x @ x)), len(x)


def lp(x, fc=0.2):
    b, a = signal.butter(2, fc / (FS / 2.0), "low")
    return signal.filtfilt(b, a, np.nan_to_num(x))


def main():
    LAGS = np.arange(0.0, 1.30, 0.05)
    pr("=" * 168)
    pr("I -- ROAD / ASKED, SR-FREE ON BOTH SIDES: lat_torqued (v*yaw_cal - g sin roll) vs desiredLateralAccel")
    pr("     Lag chosen per route by max correlation. OLS(road|des) attenuates toward 0 with noise in des;")
    pr("     1/OLS(des|road) inflates. The TRUE slope lies between them; TLS is the equal-noise point estimate.")
    pr("     frames: engaged, not pressed, calibrated, v > 15 m/s.")
    pr("=" * 168)
    pr("  %-5s %5s %5s | %-34s | %-34s | %-34s" % ("route", "lag", "r", "|des| 0.2-0.5", "|des| 0.5-1.0", "|des| > 1.0"))
    RES = {}
    for name, tags in ARMS:
        for tag in tags:
            g, _ = SR.gof(tag)
            t, des, road = g["t"], g["desiredLateralAccel"], g["lat_torqued"]
            j = np.clip(np.searchsorted(g["lp_t"], t) - 1, 0, len(g["lp_t"]) - 1)
            base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 15.0) & g["lp_calok"][j]
            best = (0.3, -9.0)
            for L in LAGS:
                d = np.interp(t - L, t, des)
                m = base & np.isfinite(d) & np.isfinite(road) & (np.abs(d) > 0.2)
                if m.sum() < 300:
                    continue
                c = float(np.corrcoef(d[m], road[m])[0, 1])
                if c > best[1]:
                    best = (L, c)
            L = best[0]
            d = np.interp(t - L, t, des)
            cells = []
            for lo, hi in ((0.2, 0.5), (0.5, 1.0), (1.0, 99.0)):
                m = base & np.isfinite(d) & np.isfinite(road) & (np.abs(d) >= lo) & (np.abs(d) < hi)
                a1, n = ols(d[m], road[m])
                a2, _ = ols(road[m], d[m])
                a3, _ = S.tls_slope(d[m], road[m])
                cells.append("%s" % ("%.2f-%.2f TLS %.2f (%4.0fs)" % (a1, 1.0 / a2 if a2 else np.nan, a3, n / FS) if n > 100 else "-- ".ljust(30)))
                if lo == 0.5:
                    RES[tag] = (a1, 1.0 / a2 if a2 else np.nan, a3)
            pr("  %-5s %5.2f %5.2f | %-34s | %-34s | %-34s" % (tag, L, best[1], cells[0], cells[1], cells[2]))

    pr()
    pr("=" * 168)
    pr("J -- THE SAME ON STRAIGHT FRAMES ONLY, both channels LOW-PASSED at 0.2 Hz")
    pr("     On straights the per-sample yaw signal is at the noise floor; the lane-offset correction lives at 0.05-0.3 Hz.")
    pr("     frames: |desiredCurvature| < %.4f /m, then |des_lp| > 0.10 m/s2 to stay off the floor." % S.STRAIGHT)
    pr("=" * 168)
    pr("  %-5s %5s %5s %10s %10s %10s %8s" % ("route", "lag", "r", "OLS(r|d)", "1/OLS(d|r)", "TLS", "sec"))
    for name, tags in ARMS:
        for tag in tags:
            g, _ = SR.gof(tag)
            t = g["t"]
            j = np.clip(np.searchsorted(g["lp_t"], t) - 1, 0, len(g["lp_t"]) - 1)
            base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 15.0) & g["lp_calok"][j]
            st = base & (np.abs(g["descurv"]) < S.STRAIGHT)
            dl, rl = lp(g["desiredLateralAccel"]), lp(g["lat_torqued"])
            best = (0.3, -9.0)
            for L in LAGS:
                d = np.interp(t - L, t, dl)
                m = st & (np.abs(d) > 0.10)
                if m.sum() < 300:
                    continue
                c = float(np.corrcoef(d[m], rl[m])[0, 1])
                if c > best[1]:
                    best = (L, c)
            L = best[0]
            d = np.interp(t - L, t, dl)
            m = st & (np.abs(d) > 0.10)
            a1, n = ols(d[m], rl[m])
            a2, _ = ols(rl[m], d[m])
            a3, _ = S.tls_slope(d[m], rl[m])
            pr("  %-5s %5.2f %5.2f %10.2f %10.2f %10.2f %8.0f" % (tag, L, best[1], a1, 1.0 / a2 if a2 else np.nan, a3, n / FS))

    pr()
    pr("=" * 168)
    pr("K -- THE COUNTERFACTUAL: SteerRatio 16.1 instead of 12.5")
    pr("=" * 168)
    pr("  Measured true ratio near centre (straight_understeer_sr.py F): 16.4-16.8 on r34/r35/r36/r38 (r37 14.9, 35 s only).")
    pr("  Taking 16.6 as the truth:")
    for srp, label in ((12.5, "his current SteerRatio"), (16.1, "SteerRatio 16.1"), (16.33, "SteerRatio 16.33 = CP default")):
        b = 16.6 / srp
        pr("    SR %-6.2f (%-22s) bias %.3f -> road gets %.3f of asked = %+5.1f %% turn vs a truthful ratio"
           % (srp, label, b, 1.0 / b, 100.0 * (1.0 / b - 1.0)))
    pr("  ⇒ moving 12.5 -> 16.1 restores %.1f %% of commanded lateral accel at the loop's own equilibrium." % (100.0 * (16.1 / 12.5 - 1.0)))

    pr()
    pr("=" * 168)
    pr("L -- INSIDE THE PERSISTENT ONE-SIGNED ERROR RUNS ON STRAIGHTS: is the EPS even being ASKED?")
    pr("     runs >= 1.0 s of |controlsState error| > 0.10 m/s2, one sign, inside the straight mask.")
    pr("     If |0xE4 cmd| is ~0 here, the EPS low-demand droop CANNOT be the binding constraint on straights.")
    pr("=" * 168)
    pr("  %-5s %8s %10s %10s %10s %10s %10s" % ("route", "runs", "tot(s)", "|err| in", "|out| in", "|opTq| in", "|E4 cmd| in"))
    for name, tags in ARMS:
        for tag in tags:
            g, _ = SR.gof(tag)
            t = g["t"]
            j = np.clip(np.searchsorted(g["lp_t"], t) - 1, 0, len(g["lp_t"]) - 1)
            base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 15.0) & g["lp_calok"][j]
            st = base & (np.abs(g["descurv"]) < S.STRAIGHT)
            sel = np.zeros(len(t), bool)
            nrun, tot = 0, 0.0
            for sgn in (+1, -1):
                m = st & (sgn * g["error"] > 0.10)
                for a, b in S.runs_of(m, int(1.0 * FS)):
                    sel[a:b] = True
                    nrun += 1
                    tot += (b - a) / FS
            pr("  %-5s %8d %10.1f %10.3f %10.3f %10.3f %10.1f" % (
                tag, nrun, tot, S.med(np.abs(g["error"][sel])), S.med(np.abs(g["output"][sel])),
                S.med(np.abs(g["tq"][sel])), S.med(np.abs(g["cmd"][sel]))))
    pr("  |opTq| is carOutput.actuatorsOutput.torque, normalised to +-1.0; |E4 cmd| is STEER_TORQUE counts (full scale ~3840).")

    out = os.path.join(HERE, "_scratch", "straight_understeer_road.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
