# -*- coding: utf-8 -*-
"""straight_understeer_sr.py -- THE TRUE STEERING RATIO, MEASURED FROM THE WIRE, and what the outer
loop does with the difference.  Companion to straight_understeer_v282.py sections A/C.

Section A of that script (a TLS of actualLateralAccel on the road value) was too noisy to decide,
because actualLateralAccel carries an angle-offset intercept and a roll term.  This script inverts
openpilot's own vehicle model instead, which removes both:

    calc_curvature(sa, u, roll) = curvature_factor(u) * sa / sR + roll_compensation(roll, u)
    =>   sR_true = curvature_factor(u) * sa / (curv_road - roll_compensation(roll, u))

with  curv_road = yaw_cal / v   -- the calibrated device yaw rate over speed, which contains NO
steering ratio at all.  Everything on the right is on the wire: sa from carState.steeringAngleDeg
minus liveParameters.angleOffsetDeg, roll from liveParameters.roll, the vehicle constants from
carParams.  stiffnessFactor is pinned to 1.0 by the operator's ForceAutoTuneOff, so cF/cR are the
carParams values and the slip factor is a constant.

F  sR_true per route, by speed and by |angle| stratum.  H3 (the SR-12.5 measurement bias) requires
   sR_true near 16, not near 12.5.
G  the SIGNED f/p/i/d decomposition on straights, expressed in the frame of the feedforward:
   med(i * sign(f)) < 0 means the integrator is CANCELLING the feedforward, which is what an
   inflated measurement forces it to do.
H  the steady-state prediction: at the controller's own equilibrium m = des, so the ROAD receives
   des * sR_param / sR_true.  Compare against the road/asked ratio measured on curve frames.

Run: python rlog-tools/studies/osc-highangle/straight_understeer_sr.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import straight_understeer_v282 as S  # noqa: E402

O, B, V = S.O, S.B, S.V
FS = S.FS
GRAV = 9.81
ROUTES = S.ROUTES
ARMS = S.ARMS
SR_PARAM = S.SR_PARAM
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


GRIDS, CPS = {}, {}


def gof(tag):
    if tag not in GRIDS:
        D = B.load(tag)
        GRIDS[tag] = B.grid(D)
        CPS[tag] = D["cp"]
    return GRIDS[tag], CPS[tag]


def main():
    pr("=" * 165)
    pr("F -- THE TRUE STEERING RATIO, MEASURED SR-FREE:  sR_true = curvature_factor(v)*sa / (yaw/v - roll_comp)")
    pr("     TLS slope of cfac*sa on (curv_road - roll_comp), through the origin; frames: engaged, not pressed,")
    pr("     calibrated, v > 15 m/s, |sa| > 1.5 deg, QUASI-STATIC (|steeringRateDeg| < 10 deg/s).")
    pr("     chi (steerRatioRear) = 0.0; stiffnessFactor pinned to 1.0 by ForceAutoTuneOff.")
    pr("=" * 165)
    pr("  %-5s %10s %10s %10s %10s %10s %8s %9s" % ("route", "SRparam", "sR_true", "sR |sa|<5", "sR 5-15", "sR >15", "n(s)", "bias"))
    SRT = {}
    for name, tags in ARMS:
        for tag in tags:
            g, cp = gof(tag)
            m_, l_, aF, cF, cR = cp["mass"], cp["wheelbase"], cp["centerToFront"], cp["tireStiffnessFront"], cp["tireStiffnessRear"]
            aR = l_ - aF
            chi = 0.0
            sf = m_ * (cF * aF - cR * aR) / (l_ ** 2 * cF * cR)
            v = g["v"]
            cfac = (1.0 - chi) / (1.0 - sf * v ** 2) / l_
            rollc = (GRAV * g["proll"]) / ((1.0 / sf) - v ** 2)
            sa = np.radians(g["ang"] - g["aoff"])
            # openpilot uses measured_curvature = -VM.calc_curvature(sa, v, roll), so the ROAD curvature
            # in calc_curvature's own sign convention is -yaw_cal/v.  denom = cfac*sa/sR, i.e. the
            # steering-angle share of the curvature with the roll compensation removed.
            curv_road = -g["yaw_cal"] / np.maximum(v, 1e-3)
            denom = curv_road - rollc
            j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
            base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (v > 15.0) & g["lp_calok"][j]
            quasi = np.abs(g["rate"]) < 10.0
            ok = base & quasi & (np.abs(np.degrees(sa)) > 1.5) & np.isfinite(denom)
            y = cfac * sa                      # = sR * denom
            cells = []
            for lo, hi in ((1.5, 5.0), (5.0, 15.0), (15.0, 999.0)):
                mm = ok & (np.abs(np.degrees(sa)) >= lo) & (np.abs(np.degrees(sa)) < hi)
                sl, n = S.tls_slope(denom[mm], y[mm])
                cells.append("%10s" % ("%.2f" % sl if n > 200 else "--"))
            srt, ntot = S.tls_slope(denom[ok], y[ok])
            SRT[tag] = srt
            pr("  %-5s %10.2f %10.2f %s %8.0f %8.2fx" % (tag, SR_PARAM[tag], srt, "".join(cells), ok.sum() / FS, srt / SR_PARAM[tag]))
    pr("  bias = sR_true / SR_param = the factor by which openpilot OVER-READS its own curvature measurement.")
    pr("  At the controller's equilibrium (m -> des) the ROAD receives des / bias, i.e. an under-turn of (1 - 1/bias).")

    pr()
    pr("=" * 165)
    pr("G -- THE SIGNED PID DECOMPOSITION ON STRAIGHTS, IN THE FRAME OF THE FEEDFORWARD")
    pr("     med(x * sign(f)): positive = the term ADDS to the feedforward, negative = it CANCELS it.")
    pr("     frames: the straight mask of straight_understeer_v282.py, restricted to |f| > 0.05 m/s2 so sign(f) is meaningful.")
    pr("=" * 165)
    pr("  %-5s %9s %9s %9s %9s %9s %9s %8s" % ("route", "f", "p*sgnf", "i*sgnf", "d*sgnf", "out*sgnf", "out/f", "sec"))
    for name, tags in ARMS:
        for tag in tags:
            g, _ = gof(tag)
            j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
            base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 15.0) & g["lp_calok"][j]
            st = base & (np.abs(g["descurv"]) < S.STRAIGHT) & (np.abs(g["f"]) > 0.05)
            s = np.sign(g["f"])
            pr("  %-5s %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %8.0f" % (
                tag, med(np.abs(g["f"][st])), med((g["p"] * s)[st]), med((g["i"] * s)[st]), med((g["d"] * s)[st]),
                med((g["output"] * s)[st]), med((g["output"] / np.where(np.abs(g["f"]) > 0.05, g["f"], np.nan))[st]), st.sum() / FS))

    pr()
    pr("=" * 165)
    pr("H -- WHAT THE MEASURED BIAS PREDICTS FOR THE ROAD, vs the road/asked ratio actually measured")
    pr("=" * 165)
    for name, tags in ARMS:
        for tag in tags:
            b = SRT[tag] / SR_PARAM[tag]
            pr("  %-5s sR_true %.2f / SR_param %.1f = bias %.3f  ->  predicted road/asked at equilibrium %.3f  (under-turn %.1f %%)"
               % (tag, SRT[tag], SR_PARAM[tag], b, 1.0 / b, 100.0 * (1.0 - 1.0 / b)))

    out = os.path.join(HERE, "_scratch", "straight_understeer_sr.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
