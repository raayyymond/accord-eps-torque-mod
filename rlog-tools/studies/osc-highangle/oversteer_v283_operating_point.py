# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v283_operating_point.py -- THE OPERATING POINT as a two-parameter problem:
(inner command->rate DC gain g, SteerRatio SR) such that the road-level curvature ratio in tight curves lands
near 1.00 AND the idx 40-80 stalls do not return.  Subagent oversteer283, 2026-09-03.

The structure of the problem, from the code and from the measurements:
  * SteerRatio enters StarPilot's torque controller ONLY through the measurement
    (latcontrol_torque.py L232-233: measured_curvature = -VM.calc_curvature(angle...) ; measurement = *v^2).
    Define rho = m / pose = (the controller's lat accel) / (the road's).  rho is proportional to 1/SR.
    With the outer integrator converged the loop forces m -> des, so the ROAD gets des / rho.
    => the EQUILIBRIUM ratio R_eq = 1/rho is a function of SR ALONE.  g cannot change it.
  * the inner DC gain g sets how fast the cascade gets there, and what the SR-free feedforward delivers
    on the way (f = torque_from_lateral_accel(des), LAF-based).  It also sets the stall statistic.
  => the two knobs are NOT two gains in series.  SR picks the DESTINATION, g picks the APPROACH.
     They only look coupled when SR is wrong, because then g decides how much of a wrong answer you reach.

Sections
  A  rho and the true angle->lat-accel constant k_true, per route and per speed bin; the SR that makes rho = 1
  B  the FEEDFORWARD's own over-delivery: the measured plant gain (lat accel per unit output torque) vs the
     latAccelFactor the tune assumes -- the term that produces overshoot on entry independently of both knobs
  C  the target metric: bias-corrected road curvature ratio R in TIGHT curves, per arm, and vs dwell
  D  the GRID R(g, SR): what each candidate inner gain gives at each SteerRatio, which cells the operator's
     toggle bounds can reach, and which cells are "no SR value works"
  E  what the grid cannot tell us, and the ONE drive that places it

Run: python oversteer_v283_operating_point.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v283 as O  # noqa: E402

V, CO, B = O.V, O.CO, O.B
FS, CPD = O.FS, O.CPD
SR_OF = {"r34": 16.1, "r35": 12.5, "r36": 12.5, "r37": 12.5, "r38": 12.5}
CP_SR = 16.33
ARMS = (("r34", ("r34",)), ("r35", ("r35",)), ("V283", ("r36", "r37", "r38")))
VBINS = ((6, 9), (9, 12), (12, 16), (16, 22), (22, 40))
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def main():
    G = {t: B.grid(B.load(t)) for t in O.ROUTES}
    R = {t: V.Route(t) for t in O.ROUTES}

    # ------------------------------------------------------------------ A. rho and k_true
    pr("=" * 175)
    pr("A -- THE MEASUREMENT BIAS rho = m/pose, THE CAR'S OWN CONSTANT k_true, AND THE SteerRatio THAT MAKES rho = 1")
    pr("  k_model = |m| / (|angle_rad| v^2)   [the controller's vehicle model; proportional to 1/SR -- a pure model quantity]")
    pr("  k_true  = |pose| / (|angle_rad| v^2) [the CAR: livePose lat accel minus the roll term; a property of the vehicle, NOT of the tune]")
    pr("  rho = k_model / k_true.  With the outer integrator converged the loop forces m -> des, so the road gets des/rho.")
    pr("  SR* = SR_now * rho  is the SteerRatio at which the controller's instrument tells the truth (rho = 1, R_eq = 1.00).")
    pr("  frames: engaged, torque controller active, hands off, |des| > 0.5, |angle| > 3 deg, |m| > 0.3, |pose| > 0.3")
    pr("=" * 175)
    A = {}
    pr("  %-5s %5s | %-42s | %-42s | %-30s" % ("route", "SR", "k_model by speed bin", "k_true by speed bin", "rho by speed bin"))
    for tag in O.ROUTES:
        g = G[tag]
        ok = ((g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (np.abs(g["desiredLateralAccel"]) > 0.5)
              & (np.abs(g["ang"]) > 3) & (np.abs(g["actualLateralAccel"]) > 0.3) & (np.abs(g["lat_torqued"]) > 0.3)
              & (np.sign(g["actualLateralAccel"]) == np.sign(g["lat_torqued"])))
        km, kt, rho = [], [], []
        for lo, hi in VBINS:
            m = ok & (g["v"] >= lo) & (g["v"] < hi)
            if m.sum() < 200:
                km.append(np.nan); kt.append(np.nan); rho.append(np.nan); continue
            a = np.abs(np.radians(g["ang"][m])) * g["v"][m] ** 2
            km.append(med(np.abs(g["actualLateralAccel"][m]) / a))
            kt.append(med(np.abs(g["lat_torqued"][m]) / a))
            rho.append(med(np.abs(g["actualLateralAccel"][m]) / np.abs(g["lat_torqued"][m])))
        A[tag] = dict(k_model=km, k_true=kt, rho=rho, SR=SR_OF[tag])
        f = lambda v, p="%.4f": " ".join((p % x) if np.isfinite(x) else "  --  " for x in v)  # noqa: E731
        pr("  %-5s %5.2f | %s | %s | %s" % (tag, SR_OF[tag], f(km), f(kt), f(rho, "%.2f ")))
    pr("  speed bins: " + " ".join("%d-%d" % b for b in VBINS))
    pr()
    pr("  k_true is the CAR and must not depend on the tune.  Pooled over 9-16 m/s: " +
       " ".join("%s %.4f" % (t, np.nanmean(A[t]["k_true"][1:3])) for t in O.ROUTES))
    pr("  k_model must scale exactly as 1/SR.  Pooled 9-16 m/s: " +
       " ".join("%s %.4f" % (t, np.nanmean(A[t]["k_model"][1:3])) for t in O.ROUTES) +
       "   (r34/r35 ratio %.3f, expected 12.5/16.1 = %.3f)" %
       (np.nanmean(A["r34"]["k_model"][1:3]) / np.nanmean(A["r35"]["k_model"][1:3]), 12.5 / 16.1))
    pr()
    pr("  %-5s %5s | %8s | %8s | %8s   -> SR* for rho = 1" % ("route", "SR", "rho 9-16", "R_eq=1/rho", "SR*"))
    for tag in O.ROUTES:
        rho = float(np.nanmean(A[tag]["rho"][1:3]))
        A[tag]["rho_pool"] = rho
        A[tag]["SR_star"] = SR_OF[tag] * rho
        pr("  %-5s %5.2f | %8.3f | %8.3f | %8.2f" % (tag, SR_OF[tag], rho, 1 / rho, A[tag]["SR_star"]))
    sr_star = float(np.nanmean([A[t]["SR_star"] for t in O.ROUTES]))
    sr_star_12 = float(np.nanmean([A[t]["SR_star"] for t in ("r35", "r36", "r37", "r38")]))
    pr("  SR* pooled over all five routes %.2f ; over the four SR-12.5 routes %.2f ; r34 alone %.2f  [carParams SR %.2f]"
       % (sr_star, sr_star_12, A["r34"]["SR_star"], CP_SR))

    # ------------------------------------------------------------------ B. the feedforward
    pr()
    pr("=" * 175)
    pr("B -- THE FEEDFORWARD'S OWN OVER-DELIVERY (independent of BOTH knobs)")
    pr("  f = torque_from_lateral_accel(des)/LAF with LAF = SteerLatAccel = 2.110.  If the CAR's true lat accel per unit")
    pr("  output torque is larger than 2.110, the feedforward alone commands MORE than the request, and the feedback")
    pr("  (which sees the SR-biased m) has to pull it back.  That is an overshoot source neither g nor SR removes.")
    pr("=" * 175)
    Bp = {}
    for tag in O.ROUTES:
        g = G[tag]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (np.abs(g["desiredLateralAccel"]) > 0.5)
        cells = []
        vals = []
        for lo, hi in VBINS:
            m = ok & (g["v"] >= lo) & (g["v"] < hi) & (np.abs(g["output"]) > 0.05)
            if m.sum() < 200:
                cells.append("  --  "); continue
            d = np.sign(g["desiredLateralAccel"][m])
            k = med(g["lat_torqued"][m] * d / (g["output"][m] * d))
            cells.append("%6.2f" % k); vals.append(k)
        Bp[tag] = dict(gain=float(np.nanmedian(vals)) if vals else np.nan, cells=cells)
        pr("  %-5s plant gain (road lat accel per unit output torque) by speed bin: %s | pooled %.2f  => the feedforward over-delivers x%.2f at LAF 2.110 ; LAF needed for an exact FF: %.2f (toggle ceiling 2.53)"
           % (tag, " ".join(cells), Bp[tag]["gain"], Bp[tag]["gain"] / 2.110, Bp[tag]["gain"]))

    # ------------------------------------------------------------------ C. the target metric
    pr()
    pr("=" * 175)
    pr("C -- THE TARGET METRIC: bias-corrected ROAD CURVATURE RATIO R in TIGHT curves (|des| > 0.5), by arm and by dwell")
    pr("  R = (pose - straight_road_bias) / des in the curve's own direction.  R = 1.00 is 'the road did what was asked'.")
    pr("=" * 175)
    C = {}
    for name, tags in ARMS:
        acc, accd = [], {t: [] for t in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0)}
        gsum, n = [], 0
        for tag in tags:
            g = G[tag]
            des = g["desiredLateralAccel"]
            pose = g["lat_torqued"]
            ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
            st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
            bp = med(pose[st] - des[st])
            runs = CO.merge_runs(ok & (np.abs(des) > CO.DES_THR), int(1.5 * FS), int(0.3 * FS))
            for a, b in runs:
                d = np.sign(np.median(des[a:b])) or 1.0
                s = slice(a + 150, b)
                big = np.abs(des[s]) > 0.5
                if big.sum() > 20:
                    acc.append(med((pose[s][big] - bp * d) * d / np.abs(des[s][big])))
                for tt in accd:
                    k = a + int(tt * FS)
                    if k < b and abs(des[k]) > 0.5:
                        accd[tt].append(float((pose[k] - bp * d) * d / abs(des[k])))
        C[name] = dict(R=med(acc), n=len(acc), dwell={str(t): med(v) for t, v in accd.items()},
                       ndwell={str(t): len(v) for t, v in accd.items()})
        pr("  %-5s R in tight curves (n %3d curves): %.3f | R vs dwell: %s"
           % (name, C[name]["n"], C[name]["R"], "  ".join("%.1fs %.2f(n%2d)" % (t, med(v), len(v)) for t, v in sorted(accd.items()))))
    pr()
    pr("  The inner DC gain (idx >= 20, section A of oversteer_v283_gain.py): r34 0.67 | r35 0.36 | V283 0.76")
    pr("  R_eq = 1/rho from section A:                                        r34 %.2f | r35 %.2f | V283 %.2f"
       % (1 / A["r34"]["rho_pool"], 1 / A["r35"]["rho_pool"], 1 / float(np.nanmean([A[t]["rho_pool"] for t in ("r36", "r37", "r38")]))))
    pr("  => every arm sits ABOVE its own equilibrium: the curves are too short for the outer integrator (t63 1.2-2.8 s)")
    pr("     to pull the feedforward's over-delivery down to des/rho.  R is a TRANSIENT, not a settled value.")

    json.dump(dict(bias=A, plant=Bp, target=C), open(os.path.join(HERE, "oversteer_v283_operating_point.json"), "w"),
              indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    with open(os.path.join(HERE, "_scratch", "oversteer_v283_operating_point.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
