# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v283_pool.py -- companion to oversteer_v283.py.

(1) POOLS the three V283 routes (r36+r37+r38) into one arm so the oversteer statistic has a sample
    comparable to r35's 31 curves, and reports it beside r35 (V281 rev 3, Ki 0, same tune) and r34.
(2) Subtracts each ROUTE'S OWN straight-road bias (|des| < 0.2, v > 10) from the pose overshoot -- the
    road-crown + instrument offset that curve_oversteer_r34.py already prints and warns about.  Without
    this the routes are not comparable: the bias is -0.29 (r34), -0.31 (r35), -0.40 (r36/r37/r38).
(3) DWELL: the bias-corrected overshoot as a function of TIME SINCE CURVE ENTRY, pooled per arm.  A gain
    change shifts the whole curve; an INTEGRATOR makes the excess GROW with dwell.  This is the
    discriminator between "Ki did it" and "the map / Kp / SR did it" (those are unchanged from r35).
(4) The same trajectory for the EPS chain's own reconstructed I term, so the two can be laid side by side.

Run: python oversteer_v283_pool.py   (after oversteer_v283.py; reads its caches through the same imports)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v283 as O  # noqa: E402

V, CO, B = O.V, O.CO, O.B
FS = O.FS
ARMS = (("r34", ("r34",)), ("r35", ("r35",)), ("V283", ("r36", "r37", "r38")))
TS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def per_route(tag):
    g = B.grid(B.load(tag))
    r = V.Route(tag)
    R = O.sim(r, kp=O.KP_OF[tag], ki=O.KI_OF[tag])
    des = g["desiredLateralAccel"]
    pose = g["lat_torqued"]
    vyaw = g["v"] * g["yaw_cal"]
    m_ = g["actualLateralAccel"]
    ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
    st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
    bias_pose = med(pose[st] - des[st])
    bias_vyaw = med(vyaw[st] - des[st])
    curve = ok & (np.abs(des) > CO.DES_THR)
    runs = CO.merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
    rows = []
    I100 = R["I"][r.i100]
    for a, b in runs:
        d = np.sign(np.median(des[a:b])) or 1.0
        s = slice(a + 150, b) if b - a >= 250 else None
        row = dict(tag=tag, t0=a / FS, dur=(b - a) / FS, dirn=int(d), des=med(np.abs(des[a:b])), v=med(g["v"][a:b]))
        if s is not None:
            row["os_pose"] = med((pose[s] - des[s]) * d) - bias_pose * d * d
            row["os_pose_c"] = med((pose[s] - des[s]) * d - bias_pose * d)
            row["os_vyaw_c"] = med((vyaw[s] - des[s]) * d - bias_vyaw * d)
            row["os_m"] = med((m_[s] - des[s]) * d)
            row["i_out"] = med(g["i"][s] * d)
            row["f_out"] = med(g["f"][s] * d)
        else:
            for k in ("os_pose", "os_pose_c", "os_vyaw_c", "os_m", "i_out", "f_out"):
                row[k] = np.nan
        # dwell trajectory, bias-corrected, in the curve's own direction
        row["traj"] = {}
        for tt in TS:
            k = a + int(tt * FS)
            if k < b and k < len(des):
                row["traj"][tt] = ((pose[k] - des[k]) * d - bias_pose * d,
                                   (vyaw[k] - des[k]) * d - bias_vyaw * d,
                                   float(I100[min(k, len(I100) - 1)] * d) if k < len(I100) else np.nan,
                                   float(g["i"][k] * d))
        rows.append(row)
    return rows, bias_pose, bias_vyaw


def main():
    per = {}
    for tag in O.ROUTES:
        per[tag] = per_route(tag)
        pr("  %s: %d curves, straight-road bias pose %+.3f vyaw %+.3f" % (tag, len(per[tag][0]), per[tag][1], per[tag][2]))
    pr()
    pr("=" * 150)
    pr("POOLED OVERSTEER, curve_oversteer_r34 definition, BIAS-CORRECTED against each route's own straight-road reference")
    pr("  + = MORE lateral accel than openpilot asked for (oversteer). STEADY = 1.5 s after entry to the end of the curve.")
    pr("=" * 150)
    pr("  %-6s %7s %9s %9s %9s %9s %9s %9s" % ("arm", "curves", "os_pose_c", "os_vyaw_c", "os_m", "|des|", "outer i", "outer f"))
    summ = {}
    for name, tags in ARMS:
        rows = [x for t in tags for x in per[t][0]]
        summ[name] = dict(n=len(rows), os_pose_c=med([x["os_pose_c"] for x in rows]), os_vyaw_c=med([x["os_vyaw_c"] for x in rows]),
                          os_m=med([x["os_m"] for x in rows]), des=med([x["des"] for x in rows]),
                          i_out=med([x["i_out"] for x in rows]), f_out=med([x["f_out"] for x in rows]),
                          frac_over=float(np.mean([x["os_pose_c"] > 0 for x in rows if np.isfinite(x["os_pose_c"])])))
        s = summ[name]
        pr("  %-6s %7d %+9.3f %+9.3f %+9.3f %9.2f %+9.3f %+9.3f   (fraction of curves that OVERSHOOT: %.2f)"
           % (name, s["n"], s["os_pose_c"], s["os_vyaw_c"], s["os_m"], s["des"], s["i_out"], s["f_out"], s["frac_over"]))
    pr()
    pr("  DWELL: bias-corrected overshoot vs TIME SINCE CURVE ENTRY (mean over curves that are still in the curve at t)")
    pr("  %-6s %-9s %s" % ("arm", "channel", "  ".join("%5.1fs" % t for t in TS)))
    traj = {}
    for name, tags in ARMS:
        rows = [x for t in tags for x in per[t][0]]
        traj[name] = {}
        for ch, k in (("os_pose_c", 0), ("os_vyaw_c", 1), ("EPS I (dir)", 2), ("outer i", 3)):
            vals = []
            for tt in TS:
                v = [x["traj"][tt][k] for x in rows if tt in x["traj"] and np.isfinite(x["traj"][tt][k])]
                vals.append(float(np.mean(v)) if len(v) >= 4 else np.nan)
            traj[name][ch] = vals
            fmt = "%6.0f" if ch == "EPS I (dir)" else "%+6.3f"
            pr("  %-6s %-9s %s" % (name, ch, "  ".join(fmt % v if np.isfinite(v) else "     -" for v in vals)))
    pr()
    pr("  n curves still running at each t: " + "  ".join("%s %s" % (name, "/".join(
        "%d" % sum(1 for x in [y for t in tags for y in per[t][0]] if tt in x["traj"]) for tt in TS)) for name, tags in ARMS))
    with open(os.path.join(HERE, "_scratch", "oversteer_v283_pool.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    json.dump(dict(summary=summ, traj=traj, bias={t: [per[t][1], per[t][2]] for t in per}),
              open(os.path.join(HERE, "oversteer_v283_pool.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
