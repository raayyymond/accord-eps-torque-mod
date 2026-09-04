# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v282_r39_roll.py -- SECTION L: the ROLL-TERM SENSITIVITY of every
headline number in OVERSTEER-V282-r39-2026-09-04.md, plus a reproduction of team-lead's crude cohort
statistic so the gap between the two is itemised rather than argued about.

Written 2026-09-04 after team-lead flagged that the achieved-side instrument was LABELLED "roll removed"
while the numbers matched the NO-roll construction, a 47 %-of-signal choice.

Two candidate achieved-side arrays, both SR-free:
    vyaw  = v * yaw_cal                      PATH / centripetal lateral accel  (no gravity term)
    pose  = v * yaw_cal - g*sin(roll_device) SPECIFIC FORCE in the car's lateral axis (torqued's)

L.0  the adjudication, from source
L.1  every headline number under BOTH arrays, side by side
L.2  the Q1 discriminators under BOTH arrays
L.3  team-lead's crude cohort statistic, and the ladder from it to the reported one

Run: python rlog-tools/studies/osc-highangle/oversteer_v282_r39_roll.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                                "analysis-2020accord", "studies", "optune"))
import oversteer_v282_r39 as M  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = M.FS
G = 9.81
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def bias(g, key):
    """The straight-road reference for THIS array (curve_oversteer_r34's construction)."""
    ok = M.curve_mask(g)
    st = ok & (np.abs(g["desiredLateralAccel"]) < 0.2) & (g["v"] > 10)
    return M.med(g[key][st] - g["desiredLateralAccel"][st])


def main():
    C = {t: M.curves(t)[0] for t in M.TAGS}

    pr("=" * 165)
    pr("SECTION L.0 -- WHICH ARRAY IS PHYSICALLY CORRECT FOR 'IS THE CAR TURNING MORE THAN ASKED?'  (EVIDENCE, from source)")
    pr("=" * 165)
    pr("  1. opendbc/car/vehicle_model.py:66-77, calc_curvature's own docstring:")
    pr("       \"Returns the curvature.  MULTIPLIED BY THE SPEED THIS WILL GIVE THE YAW RATE.\"")
    pr("     The controller's measurement is `measured_curvature * v**2` = yaw_rate * v -- a PATH / centripetal")
    pr("     quantity.  Its `roll_compensation` (line 106-121) returns a CURVATURE, `g*roll / (1/sf - u**2)`;")
    pr("     it models how bank changes the path a given steering angle produces.  It is NOT a gravity term")
    pr("     subtracted from a readout.")
    pr("  2. The ask, `desiredLateralAccel`, is `desired_curvature * v**2` (latcontrol_torque.py:234) -- also PATH.")
    pr("  3. selfdrive/locationd/torqued.py:199:  lateral_acc = (vego * yaw_rate) - sin(roll)*ACCELERATION_DUE_TO_GRAVITY")
    pr("     torqued subtracts gravity because it is fitting steer torque -> LATERAL FORCE (what the tyres must make).")
    pr("  4. `yaw_cal` comes from livePose.angularVelocityDevice -- a GYRO.  It contains no gravity to remove.")
    pr("  ==> For 'is the car turning more than asked', BOTH sides must be path quantities: use `vyaw`.")
    pr("      Subtracting g*sin(roll) makes it a specific force, which is the RIGHT array for the LAF/plant fit")
    pr("      (and is the array section 6.1's LAF sizing used, via torqued_points' lat_key='lat_torqued')")
    pr("      and the WRONG array for the tracking question.  team-lead's reasoning is CORRECT.")
    pr("  ==> The numbers reported were computed from `vyaw` (oversteer_v282_r39.py:245 and :616).  The LABEL")
    pr("      'roll removed' in the write-up header and in the report was WRONG and is corrected.")

    pr()
    pr("=" * 165)
    pr("SECTION L.1 -- EVERY HEADLINE NUMBER UNDER BOTH ARRAYS.  Tight curves (|des| > 0.5), steady window, curve as")
    pr("  the unit, each array bias-corrected by ITS OWN straight-road reference.")
    pr("=" * 165)
    pr("  straight-road bias by array: " + " | ".join(
        "%s vyaw %+.3f pose %+.3f" % (t, bias(M.gof(t)[0], "vyaw"), bias(M.gof(t)[0], "pose")) for t in M.TAGS))
    pr()
    pr("  %-5s %-7s %8s %11s %10s %10s %10s | %-18s" % (
        "route", "array", "n", "os (m/s^2)", "R_road", "R_m", "1/rho", "R_road 95% CI"))
    res = {}
    for key in ("vyaw", "pose"):
        for t in M.TAGS:
            g, _ = M.gof(t)
            des = g["desiredLateralAccel"]
            b = bias(g, key)
            bm = M.med(g["actualLateralAccel"][M.curve_mask(g) & (np.abs(des) < 0.2) & (g["v"] > 10)]
                       - des[M.curve_mask(g) & (np.abs(des) < 0.2) & (g["v"] > 10)])
            os_, rr, rm, ri = [], [], [], []
            for r in C[t]:
                if r["des"] <= 0.5 or r["b"] - r["a"] < int(2.5 * FS):
                    continue
                sl = slice(r["a"] + 150, r["b"])
                d = r["dir"]
                big = np.abs(des[sl]) > 0.5
                if big.sum() < 10:
                    continue
                os_.append(M.med((g[key][sl] - des[sl]) * d - b * d))
                ach = g[key][sl][big] - b
                mm = g["actualLateralAccel"][sl][big] - bm
                rr.append(M.med(ach / des[sl][big]))
                rm.append(M.med(mm / des[sl][big]))
                ri.append(M.med(ach / mm))
            lo, hi = M.boot_ci(rr)
            res[(key, t)] = rr
            pr("  %-5s %-7s %8d %+11.3f %10.3f %10.3f %10.3f | [%.3f, %.3f]" % (
                t, key, len(rr), M.med(os_), M.med(rr), M.med(rm), M.med(ri), lo, hi))
        pr()
    pr("  DELTA r39 - r35 (4000-resample bootstrap over curves, independent arms):")
    rng = np.random.default_rng(11)
    for key in ("vyaw", "pose"):
        d = np.array(res[(key, "r39")], float)
        e = np.array(res[(key, "r35")], float)
        bs = (np.median(d[rng.integers(0, len(d), (4000, len(d)))], 1)
              - np.median(e[rng.integers(0, len(e), (4000, len(e)))], 1))
        pr("    %-7s dR = %+0.3f, 95%% CI [%+0.3f, %+0.3f]   (r35 %.3f -> r39 %.3f)" % (
            key, M.med(d) - M.med(e), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)),
            M.med(e), M.med(d)))

    pr()
    pr("=" * 165)
    pr("SECTION L.2 -- THE Q1 DISCRIMINATORS UNDER BOTH ARRAYS.  Does 'equilibrium, not transient' survive the choice?")
    pr("=" * 165)
    pr("  L.2a dwell trajectory of R on the FIXED cohort (curves >= 5 s):")
    TT = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0)
    pr("       t (s)          " + " ".join("%7.2f" % x for x in TT))
    for key in ("vyaw", "pose"):
        for t in ("r35", "r39"):
            g, _ = M.gof(t)
            des = g["desiredLateralAccel"]
            b = bias(g, key)
            rows = [r for r in C[t] if r["dur"] >= 5.0]
            cols = []
            for tt in TT:
                k = int(tt * FS)
                v = [(g[key][r["a"] + k] - b) / des[r["a"] + k] for r in rows
                     if r["a"] + k < r["b"] and abs(des[r["a"] + k]) > 0.4]
                cols.append(np.nanmedian(v) if len(v) > 3 else np.nan)
            pr("       %-5s %-6s n=%2d " % (t, key, len(rows)) + " ".join("%7.3f" % x for x in cols))
    pr()
    pr("  L.2b quasi-static vs transient (oversteer_v283 section 9.3 definitions):")
    pr("       %-5s %-7s %26s %26s" % ("route", "array", "quasi-static os (frac>0)", "transient os (frac>0)"))
    for key in ("vyaw", "pose"):
        for t in M.TAGS:
            g, _ = M.gof(t)
            des = g["desiredLateralAccel"]
            b = bias(g, key)
            dd = np.r_[0.0, np.diff(des)] * FS
            into = np.zeros(len(des))
            dirf = np.zeros(len(des))
            inc = np.zeros(len(des), bool)
            for r in C[t]:
                into[r["a"]:r["b"]] = np.arange(r["b"] - r["a"]) / FS
                dirf[r["a"]:r["b"]] = r["dir"]
                inc[r["a"]:r["b"]] = True
            os_f = (g[key] - des) * dirf - b * dirf
            qs = inc & (into >= 1.0) & (np.abs(dd) < 0.20)
            tr = inc & ((into < 1.0) | (np.abs(dd) >= 0.50))
            pr("       %-5s %-7s %14.3f (%5.2f)      %14.3f (%5.2f)" % (
                t, key, M.med(os_f[qs]), float(np.mean(os_f[qs] > 0)), M.med(os_f[tr]), float(np.mean(os_f[tr] > 0))))
    pr()
    pr("  L.2c the ratio-free shape statistic peak/settled (section K.2) under both arrays:")
    pr("       %-5s %-7s %8s %14s %10s %10s" % ("route", "array", "n", "peak/settled", "p25", "p75"))
    for key in ("vyaw", "pose"):
        for t in M.TAGS:
            g, _ = M.gof(t)
            b = bias(g, key)
            rat = []
            for r in C[t]:
                if r["dur"] < 4.0 or r["des"] <= 0.4:
                    continue
                ach = (g[key][r["a"]:r["b"]] - b) * r["dir"]
                settled = np.nanmedian(ach[int(2.5 * FS):])
                if not np.isfinite(settled) or settled < 0.3:
                    continue
                rat.append(float(np.nanmax(ach[:int(2.5 * FS)])) / settled)
            pr("       %-5s %-7s %8d %14.3f %10.3f %10.3f" % (
                t, key, len(rat), M.med(rat), np.percentile(rat, 25), np.percentile(rat, 75)))

    pr()
    pr("=" * 165)
    pr("SECTION L.3 -- REPRODUCING team-lead's CRUDE COHORT (12 curves, median R 0.606, IQR [0.314, 1.023]) AND THE")
    pr("  LADDER TO THE REPORTED 1.116.  Each row adds ONE of the reported statistic's choices to the crude one.")
    pr("  Crude = contiguous curve runs >= 5 s, LAST 2 s of each, per-frame ratio, `pose`, NO bias correction,")
    pr("  NO |des| floor on the denominator.")
    pr("=" * 165)
    g, _ = M.gof("r39")
    des = g["desiredLateralAccel"]
    ok = M.curve_mask(g) & (np.abs(des) > M.DES_THR)
    variants = [
        ("crude: pose, last 2 s, no bias, no |des| floor", "pose", False, 0.0, True),
        ("+ |des| > 0.5 floor on the denominator", "pose", False, 0.5, True),
        ("+ bias correction", "pose", True, 0.5, True),
        ("+ steady window 1.5 s -> end (not last 2 s)", "pose", True, 0.5, False),
        ("+ vyaw instead of pose  == THE REPORTED NUMBER", "vyaw", True, 0.5, False),
    ]
    pr("  %-48s %8s %10s %10s %10s %10s" % ("variant", "curves", "median R", "IQR lo", "IQR hi", "IQR width"))
    for nm, key, do_bias, floor, last2 in variants:
        b = bias(g, key) if do_bias else 0.0
        runs = M.merge_runs(ok, int(5.0 * FS), int(0.3 * FS))
        vals = []
        for a, bb in runs:
            sl = slice(bb - int(2.0 * FS), bb) if last2 else slice(a + 150, bb)
            sel = np.abs(des[sl]) > floor
            if sel.sum() < 10:
                continue
            vals.append(M.med((g[key][sl][sel] - b) / des[sl][sel]))
        v = np.array(vals, float)
        pr("  %-48s %8d %10.3f %10.3f %10.3f %10.3f" % (
            nm, len(v), np.median(v), np.percentile(v, 25), np.percentile(v, 75),
            np.percentile(v, 75) - np.percentile(v, 25)))
    pr("  (the reported cohort also requires the curve's OWN median |des| > 0.5, which the ladder's last row does not,")
    pr("   so it lands near but not exactly on 1.116 -- section E's stratum is per-CURVE, this ladder is per-RUN.)")

    out = os.path.join(HERE, "_scratch", "oversteer_v282_r39_roll.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
