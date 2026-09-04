# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v283_gain.py -- the COMPOUND-GAIN hypothesis, tested against the
pure-integrator one on r36/r37/r38 (V283, Ki 50) vs r35 (V281 rev 3, Ki 0) and r34 (V280 rev 2, SR 16.1).

The hypothesis (orchestrator, 2026-09-03): Ki 50 removes the inner loop's DC droop (r35 settled at ~0.62 of
the requested rate), raising the command->rate DC gain by up to 1/0.62 = 1.61x; if the operator's SteerRatio
12.5 compensation (worth ~1.29x of outer-loop gain) is still in place, the outer loop now carries ~2.1x the
gain it was tuned for, and the remedy is a TUNE change (SR back toward 16.1) rather than removing Ki.

Discriminators, as briefed:
  compound gain -> oversteer proportional to the steady-state DC gain, PRESENT EVEN IN SLOWLY-VARYING curves
  integrator    -> excess at turn TRANSIENTS, torque still pushing after the rate error changes sign,
                   and a residual offset decaying at the 0.25 Hz corner

Sections
  A  the INNER loop's command->rate DC gain per route, matched by demand index and by speed
  B  the OUTER plant's gain: lateral accel per unit openpilot output torque (torqued's own TLS estimator,
     backcalc_laf_friction), against the 2.110 the controller assumes -- and the SIGN of the SteerRatio term
  C  QUASI-STATIC vs TRANSIENT curve frames (split on |d(desiredLateralAccel)/dt|), bias-corrected overshoot
  D  turn EXITS: bias-corrected overshoot after the curve, and the measured decay of the tap-implied I term
  E  the SPLIT: does the bias-corrected overshoot track the measured DC gain, or the I term's share?

Run: python oversteer_v283_gain.py
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
T_PER_S = O.T_PER_S
ARMS = (("r34", ("r34",)), ("r35", ("r35",)), ("V283", ("r36", "r37", "r38")))
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def main():
    routes, grids, sims = {}, {}, {}
    for tag in O.ROUTES:
        routes[tag] = V.Route(tag)
        grids[tag] = B.grid(B.load(tag))
        sims[tag] = O.sim(routes[tag], kp=O.KP_OF[tag], ki=O.KI_OF[tag])

    # ---------------------------------------------------------------- A. inner DC gain
    pr("=" * 170)
    pr("A -- THE INNER LOOP'S COMMAND->RATE DC GAIN (wheel rate / the map's reference), matched by demand index AND speed")
    pr("  frames: engaged, hands-light |tq_raw| < 400, |angle| > 5, command HELD (idx within +-15 %% for >= 0.4 s), the wheel's own reference > 3 deg/s")
    pr("  1.00 = a type-1 loop with zero steady-state rate error. r35's droop was the reason Ki 50 was cut.")
    pr("=" * 170)
    IDXB = ((5, 20), (20, 40), (40, 68), (68, 112), (112, 241))
    VB = ((0, 6), (6, 10), (10, 16), (16, 99))
    A = {}
    for tag in O.ROUTES:
        r = routes[tag]
        ref = sims[tag]["ref_deg"][r.i100]
        # "held" = the command steady over 0.4 s (rolling spread <= 25 % of the mean, or <= 4 counts)
        k = 40
        pad = np.pad(r.idx, (k // 2, k - k // 2), mode="edge")
        win = np.lib.stride_tricks.sliding_window_view(pad, k)[: len(r.idx)]
        spread = win.max(1) - win.min(1)
        held = (spread <= np.maximum(0.25 * win.mean(1), 4.0))
        base = r.eng & (np.abs(r.tq_raw) < 400) & (np.abs(r.ang) > 5) & (ref > 3)
        A.setdefault("_held", {})[tag] = float((base & held).sum() / FS)
        cells, cellsv = [], []
        for lo, hi in IDXB:
            m = base & (r.idx >= lo) & (r.idx < hi)
            cells.append("%3d-%3d %s (%5.1fs)" % (lo, hi, "%.2f" % med(np.abs(r.wire[m]) / CPD / ref[m]) if m.sum() > 100 else " -- ", m.sum() / FS))
        for lo, hi in VB:
            m = base & (r.vego >= lo) & (r.vego < hi) & (r.idx >= 20)
            cellsv.append("v %2d-%2d %s (%5.1fs)" % (lo, hi, "%.2f" % med(np.abs(r.wire[m]) / CPD / ref[m]) if m.sum() > 100 else " -- ", m.sum() / FS))
        g_all = med(np.abs(r.wire[base & (r.idx >= 20)]) / CPD / ref[base & (r.idx >= 20)])
        A[tag] = dict(all=g_all, byidx=[med(np.abs(r.wire[base & (r.idx >= lo) & (r.idx < hi)]) / CPD / ref[base & (r.idx >= lo) & (r.idx < hi)])
                                        if (base & (r.idx >= lo) & (r.idx < hi)).sum() > 100 else np.nan for lo, hi in IDXB])
        pr("  %-4s idx>=20 overall %.2f | %s" % (tag, g_all, " | ".join(cells)))
        pr("       %s" % " | ".join(cellsv))
    pr("  ratio V283 / r35 by idx bin: " + " | ".join(
        "%s %.2f" % ("%d-%d" % IDXB[i], np.nanmean([A[t]["byidx"][i] for t in ("r36", "r37", "r38")]) / A["r35"]["byidx"][i]) for i in range(len(IDXB))))
    pr("  ratio V283 / r34 by idx bin: " + " | ".join(
        "%s %.2f" % ("%d-%d" % IDXB[i], np.nanmean([A[t]["byidx"][i] for t in ("r36", "r37", "r38")]) / A["r34"]["byidx"][i]) for i in range(len(IDXB))))

    # ---------------------------------------------------------------- B. outer plant gain
    pr()
    pr("=" * 170)
    pr("B -- THE OUTER PLANT'S GAIN: lateral accel per unit openpilot output torque (torqued's own TLS estimator, backcalc_laf_friction)")
    pr("  The controller assumes latAccelFactor = 2.110 and closes on m = actualLateralAccel (steering angle -> vehicle model, SteerRatio).")
    pr("  LAF_meas > 2.110 => the plant delivers MORE lat accel per unit command than the tune assumes = outer loop over-gained.")
    pr("  m/pose is the MEASUREMENT bias: at the controller's own equilibrium m = des, so the ROAD gets des / (m/pose).")
    pr("=" * 170)
    Bx = {}
    DESB = ((0.3, 0.6), (0.6, 1.0), (1.0, 3.0))
    for tag in O.ROUTES:
        g = grids[tag]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(g["desiredLateralAccel"])
        cells = []
        for lo, hi in DESB:
            m = ok & (np.abs(g["desiredLateralAccel"]) >= lo) & (np.abs(g["desiredLateralAccel"]) < hi) & (g["v"] >= 8) & (g["v"] < 20)
            if m.sum() < 300:
                cells.append("|des| %.1f-%.1f: -- (%4.0fs)" % (lo, hi, m.sum() / FS)); continue
            d = np.sign(g["desiredLateralAccel"][m])
            cells.append("|des| %.1f-%.1f: out %.3f  pose/des %.2f  cmd %3.0f (%4.0fs)"
                         % (lo, hi, med(np.abs(g["output"][m])), med(g["lat_torqued"][m] * d / np.abs(g["desiredLateralAccel"][m])),
                            med(np.abs(g["cmd"][m])), m.sum() / FS))
        okv = ok & (g["v"] >= 6) & (g["v"] < 10) & (np.abs(g["desiredLateralAccel"]) > 0.5) & (np.abs(g["lat_torqued"]) > 0.5)
        mp = med(g["actualLateralAccel"][okv] / g["lat_torqued"][okv])
        o2 = ok & (g["v"] >= 8) & (g["v"] < 20) & (np.abs(g["output"]) > 0.05) & (np.abs(g["desiredLateralAccel"]) > 0.3)
        direct = med(np.abs(g["lat_torqued"][o2] / g["output"][o2]))
        Bx[tag] = dict(m_over_pose=mp, direct=direct, cells=cells)
        pr("  %-4s |pose/output| p50 (8-20 m/s, |des|>0.3) %6.2f  [the tune assumes LAF 2.110] | m/pose at 6-10 m/s %.3f" % (tag, direct, mp))
        pr("       matched by request size, 8-20 m/s:  %s" % "  |  ".join(cells))
    pr()
    pr("  NOTE: torqued's own TLS latAccelFactor estimator is NOT used here -- on the modded EPS openpilot's output torque is")
    pr("  too small to fill its buckets (memory of record), and the fit returns 9.6-122 across these routes, which is nonsense.")
    pr()
    pr("  SIGN CHECK on the SteerRatio term (EVIDENCE, arithmetic + measurement):")
    pr("    m = vehicle_model(angle, v, SR) and the loop drives m -> des.  Lower SR => HIGHER m for the same angle")
    pr("    (the measured vehicle-model constant scales exactly 16.1/12.5 = 1.288: r34 0.0208 vs r35/r36/r37/r38 0.0268/0.0274/0.0271/0.0268 at 6-9 m/s).")
    pr("    So at equilibrium the ANGLE, and therefore the ROAD's lat accel, is SMALLER at SR 12.5 -- SR 12.5 REDUCES achieved lat accel.")
    pr("    Measured: r34 (SR 16.1) steady rel_pose -0.127 ; r35 (SR 12.5) -0.238.  Going BACK to 16.1 would raise the achieved lat accel by ~1.29x")
    pr("    at the controller's equilibrium, i.e. it would make the OVERSTEER WORSE, not better.")

    # ---------------------------------------------------------------- C. quasi-static vs transient
    pr()
    pr("=" * 170)
    pr("C -- QUASI-STATIC vs TRANSIENT CURVE FRAMES (bias-corrected overshoot; + = more lat accel than asked)")
    pr("  quasi-static = |d(desiredLateralAccel)/dt| < 0.20 m/s^3 over a 0.5 s window AND >= 1.0 s into the curve")
    pr("  transient    = the first 1.0 s of a curve, or |d(des)/dt| >= 0.50 m/s^3")
    pr("  compound gain predicts the excess is present in the QUASI-STATIC bin; the integrator story predicts it concentrates in TRANSIENTS.")
    pr("=" * 170)
    C = {}
    for name, tags in ARMS:
        acc = {k: [] for k in ("qs_pose", "qs_vyaw", "tr_pose", "tr_vyaw", "qs_s", "tr_s", "qs_I", "tr_I")}
        for tag in tags:
            g = grids[tag]
            r = routes[tag]
            R = sims[tag]
            des = g["desiredLateralAccel"]
            pose = g["lat_torqued"]
            vyaw = g["v"] * g["yaw_cal"]
            ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
            st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
            bp, bv = med(pose[st] - des[st]), med(vyaw[st] - des[st])
            curve = ok & (np.abs(des) > CO.DES_THR)
            runs = CO.merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
            dd = np.abs(np.gradient(des) * FS)
            dd = np.convolve(dd, np.ones(50) / 50, "same")
            dirf = np.zeros(len(des))
            since = np.full(len(des), 1e9)
            for a, b in runs:
                dirf[a:b] = np.sign(np.median(des[a:b])) or 1.0
                since[a:b] = np.arange(b - a) / FS
            qs = (since >= 1.0) & (since < 1e8) & (dd < 0.20)
            tr = ((since < 1.0) | (dd >= 0.50)) & (since < 1e8)
            i100 = r.i100
            I_imp = (-r.T_meas / T_PER_S) * 256.0 / 254.0 - R["P"][i100] - R["D"][i100]
            sgn = np.sign(R["sp"][i100])
            n = min(len(qs), len(I_imp))
            for lab, m in (("qs", qs[:n]), ("tr", tr[:n])):
                acc[lab + "_pose"].append(((pose[:n][m] - des[:n][m]) * dirf[:n][m] - bp * dirf[:n][m]))
                acc[lab + "_vyaw"].append(((vyaw[:n][m] - des[:n][m]) * dirf[:n][m] - bv * dirf[:n][m]))
                acc[lab + "_s"].append(m.sum() / FS)
                acc[lab + "_I"].append(np.abs(I_imp[:n][m]))
        C[name] = dict(qs_pose=med(np.concatenate(acc["qs_pose"])), qs_vyaw=med(np.concatenate(acc["qs_vyaw"])),
                       tr_pose=med(np.concatenate(acc["tr_pose"])), tr_vyaw=med(np.concatenate(acc["tr_vyaw"])),
                       qs_s=sum(acc["qs_s"]), tr_s=sum(acc["tr_s"]),
                       qs_I=med(np.concatenate(acc["qs_I"])), tr_I=med(np.concatenate(acc["tr_I"])),
                       qs_over=float(np.mean(np.concatenate(acc["qs_vyaw"]) > 0)), tr_over=float(np.mean(np.concatenate(acc["tr_vyaw"]) > 0)))
        c = C[name]
        pr("  %-5s QUASI-STATIC (%5.0f s): os_pose %+.3f  os_vyaw %+.3f  (frames above zero %.2f)  |I_imp| p50 %5.0f"
           % (name, c["qs_s"], c["qs_pose"], c["qs_vyaw"], c["qs_over"], c["qs_I"]))
        pr("        TRANSIENT    (%5.0f s): os_pose %+.3f  os_vyaw %+.3f  (frames above zero %.2f)  |I_imp| p50 %5.0f"
           % (c["tr_s"], c["tr_pose"], c["tr_vyaw"], c["tr_over"], c["tr_I"]))
    pr("  DELTA vs r35 (V283 minus r35):  quasi-static os_vyaw %+.3f | transient os_vyaw %+.3f"
       % (C["V283"]["qs_vyaw"] - C["r35"]["qs_vyaw"], C["V283"]["tr_vyaw"] - C["r35"]["tr_vyaw"]))

    # ---------------------------------------------------------------- D. exits and the residual
    pr()
    pr("=" * 170)
    pr("D -- TURN EXITS and the MEASURED decay of the tap-implied I term")
    pr("  exit window = 0-2 s after the curve run closes.  decay = |I_implied| after the demand index falls below 5, still engaged.")
    pr("=" * 170)
    D = {}
    for name, tags in ARMS:
        ex_pose, ex_vyaw, dec = [], [], {t: [] for t in (0.0, 0.5, 1.0, 2.0, 3.0, 4.0)}
        for tag in tags:
            g = grids[tag]
            r = routes[tag]
            R = sims[tag]
            des = g["desiredLateralAccel"]
            pose = g["lat_torqued"]
            vyaw = g["v"] * g["yaw_cal"]
            ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
            stt = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
            bp, bv = med(pose[stt] - des[stt]), med(vyaw[stt] - des[stt])
            runs = CO.merge_runs(ok & (np.abs(des) > CO.DES_THR), int(1.5 * FS), int(0.3 * FS))
            for a, b in runs:
                if b + 200 >= len(des):
                    continue
                d = np.sign(np.median(des[a:b])) or 1.0
                w = slice(b, b + 200)
                ex_pose.append(med((pose[w] - des[w]) * d - bp * d))
                ex_vyaw.append(med((vyaw[w] - des[w]) * d - bv * d))
            i100 = r.i100
            I_imp = np.abs((-r.T_meas / T_PER_S) * 256.0 / 254.0 - R["P"][i100] - R["D"][i100])
            drop = r.eng & (r.idx < 5) & np.r_[False, (r.idx[:-1] >= 20)]
            for k in np.flatnonzero(drop):
                if k + 400 >= len(I_imp) or not r.eng[k:k + 400].all():
                    continue
                for tt in dec:
                    dec[tt].append(I_imp[k + int(tt * FS)])
        D[name] = dict(exit_pose=med(ex_pose), exit_vyaw=med(ex_vyaw), n_exit=len(ex_pose),
                       decay={str(t): med(v) for t, v in dec.items()}, n_drop=len(dec[0.0]))
        pr("  %-5s EXIT (n %3d): os_pose %+.3f  os_vyaw %+.3f | |I_implied| after the command drops below idx 5 (n %3d): %s"
           % (name, len(ex_pose), D[name]["exit_pose"], D[name]["exit_vyaw"], len(dec[0.0]),
              "  ".join("%.1fs %5.0f" % (t, med(v)) for t, v in sorted(dec.items()))))

    # ---------------------------------------------------------------- E. the split
    pr()
    pr("=" * 170)
    pr("E -- DOES THE OVERSTEER TRACK THE DC GAIN OR THE I SHARE?")
    pr("=" * 170)
    pool = json.load(open(os.path.join(HERE, "oversteer_v283_pool.json")))["summary"]
    pr("  %-6s %10s %10s %10s %10s %10s" % ("arm", "os_pose_c", "os_vyaw_c", "innerDC", "LAF_meas", "m/pose"))
    for name, tags in ARMS:
        dc = float(np.nanmean([A[t]["all"] for t in tags]))
        laf = float(np.nanmean([Bx[t]["laf"] for t in tags]))
        mp = float(np.nanmean([Bx[t]["m_over_pose"] for t in tags]))
        pr("  %-6s %+10.3f %+10.3f %10.2f %10.3f %10.3f" % (name, pool[name]["os_pose_c"], pool[name]["os_vyaw_c"], dc, laf, mp))
    with open(os.path.join(HERE, "_scratch", "oversteer_v283_gain.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    json.dump(dict(innerDC=A, outer=Bx, quasi=C, exits=D), open(os.path.join(HERE, "oversteer_v283_gain.json"), "w"), indent=1,
              default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))


if __name__ == "__main__":
    main()
