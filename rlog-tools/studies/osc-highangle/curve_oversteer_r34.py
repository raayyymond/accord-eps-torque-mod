#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/curve_oversteer_r34.py -- the operator's r34 note "the car oversteers on everything outside of a
straight lane" (new tune: LAF 2.11, friction 0.03, SteerRatio 16.1 explicit -> no 14/16.33 model scale), vs r32/r33 (old tune).
Subagent lanechange34, 2026-09-03.  Reads the backcalc grids (studies/optune/_scratch/<tag>_backcalc.npz via backcalc_laf_friction.grid).

CURVE = latActive & torque controller active & not steeringPressed & |torqueState.desiredLateralAccel| > 0.3 m/s^2, runs >= 1.5 s
(gaps < 0.3 s merged).  dir = sign(median desired).  ENTRY = first 1.0 s of the run, STEADY = 1.5 s -> end.
Signed OVERSHOOT (positive = more lateral accel than asked, in the curve's direction) with three 'actual' instruments:
   m     = torqueState.actualLateralAccel   (the controller's own: steering angle -> vehicle model, SR 16.1 on r34 / 14.0 on r32-r33)
   pose  = livePose yaw_cal * v - g sin(roll_device)   (torqued's instrument; includes the road-crown term)
   vyaw  = livePose yaw_cal * v                          (no roll term)
Decomposition of the command in the same windows (lat-accel units; -output*LAF = p + i + f): f (feedforward incl. friction), p, i,
each projected on dir; FF share f/(p+i+f); 'fighting' = fraction of frames with sign(p) == -sign(f) / sign(i) == -sign(f);
integrator excursion within the window and its 63 % time.  Then the aligned mean trajectory (t = 0..3 s from entry) and the
frame-pooled overshoot binned by |steering angle| (0-20, 20-50, 50-120, >120 deg) and by speed (<10, 10-20, 20-30, >=30 m/s),
entry and steady separately, with relative overshoot actual/desired - 1 where |des| > 0.5.

Run:  python curve_oversteer_r34.py   (writes CURVE-OVERSTEER-r34.txt and curve_oversteer_r34.json beside itself)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import highangle_stutter as H  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
DES_THR = 0.3
TAGS = ("r32", "r33", "r34")
LAF = {"r32": 1.689, "r33": 1.689, "r34": 2.11}
ANG_BINS = ((0, 20), (20, 50), (50, 120), (120, 1e9))
V_BINS = ((0, 10), (10, 20), (20, 30), (30, 1e9))
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def merge_runs(mask, minlen, gap):
    runs = H.runs_of(mask, 1)
    out = []
    for a, b in runs:
        if out and a - out[-1][1] < gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= minlen]


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def analyse(tag):
    g = B.grid(B.load(tag))
    des = g["desiredLateralAccel"]; m = g["actualLateralAccel"]; pose = g["lat_torqued"]; vyaw = g["v"] * g["yaw_cal"]
    ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
    curve = ok & (np.abs(des) > DES_THR)
    runs = merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
    pr("=" * 130)
    pr("ROUTE %s  LAF %.3f  curves (|des|>%.1f, >=1.5 s, hands off): %d, %.0f s ; engaged hands-off %.0f s" % (
        tag, LAF[tag], DES_THR, len(runs), sum(b - a for a, b in runs) / FS, ok.sum() / FS))
    rows = []
    for a, b in runs:
        d = np.sign(np.median(des[a:b])); d = d if d != 0 else 1.0
        e = slice(a, a + int(1.0 * FS)); s = slice(a + int(1.5 * FS), b) if b - a >= int(2.5 * FS) else None
        r = dict(t0=float(g["t"][a]), dur=float((b - a) / FS), dir=int(d), v=med(g["v"][a:b]), ang=med(np.abs(g["ang"][a:b])), ang_max=float(np.abs(g["ang"][a:b]).max()),
                 des=med(np.abs(des[a:b])), des_max=float(np.abs(des[a:b]).max()))
        for nm, sl in (("entry", e), ("steady", s)):
            if sl is None:
                for k in ("os_m", "os_pose", "os_vyaw", "rel_m", "rel_pose", "rel_vyaw", "f", "p", "i", "ff_share", "fight_p", "fight_i"):
                    r[nm + "_" + k] = np.nan
                continue
            r[nm + "_os_m"] = med((m[sl] - des[sl]) * d); r[nm + "_os_pose"] = med((pose[sl] - des[sl]) * d); r[nm + "_os_vyaw"] = med((vyaw[sl] - des[sl]) * d)
            big = np.abs(des[sl]) > 0.5
            r[nm + "_rel_m"] = med(m[sl][big] / des[sl][big] - 1) if big.sum() > 10 else np.nan
            r[nm + "_rel_pose"] = med(pose[sl][big] / des[sl][big] - 1) if big.sum() > 10 else np.nan
            r[nm + "_rel_vyaw"] = med(vyaw[sl][big] / des[sl][big] - 1) if big.sum() > 10 else np.nan
            f_, p_, i_ = g["f"][sl] * d, g["p"][sl] * d, g["i"][sl] * d
            r[nm + "_f"], r[nm + "_p"], r[nm + "_i"] = med(f_), med(p_), med(i_)
            tot = f_ + p_ + i_
            r[nm + "_ff_share"] = med(f_[np.abs(tot) > 0.05] / tot[np.abs(tot) > 0.05]) if (np.abs(tot) > 0.05).sum() > 10 else np.nan
            r[nm + "_fight_p"] = float(np.mean((np.sign(p_) == -np.sign(f_)) & (np.abs(f_) > 0.05)))
            r[nm + "_fight_i"] = float(np.mean((np.sign(i_) == -np.sign(f_)) & (np.abs(f_) > 0.05)))
        ii = g["i"][a:b] * d
        r["i_entry"] = float(ii[0]); r["i_exc"] = float(np.nanmax(np.abs(ii - ii[0]))); r["i_end"] = float(ii[-1])
        # 63 % time of i's move from entry to its window-end value
        tgt = ii[0] + 0.63 * (ii[-1] - ii[0])
        k = np.where(np.sign(ii[-1] - ii[0]) * (ii - tgt) >= 0)[0]
        r["i_t63"] = float(k[0] / FS) if len(k) and abs(ii[-1] - ii[0]) > 0.02 else np.nan
        r["out_pk"] = float(np.nanmax(np.abs(g["output"][a:b])))
        rows.append(r)
    pr("   #    t0   dur dir    v  |ang| angmax |des| desmax | ENTRY os: m   pose  vyaw | rel m  pose | f     p     i   ffsh fightP fightI | STEADY os: m   pose  vyaw | rel m  pose | f     p     i   ffsh fightP fightI | i0   iexc  iend  t63 | out pk")
    for k, r in enumerate(rows):
        pr("  %2d %6.1f %5.1f %+d %5.1f %5.0f %5.0f %5.2f %5.2f | %+.3f %+.3f %+.3f | %+.2f %+.2f | %+.3f %+.3f %+.3f %5.2f %4.2f %4.2f | %+.3f %+.3f %+.3f | %+.2f %+.2f | %+.3f %+.3f %+.3f %5.2f %4.2f %4.2f | %+.3f %.3f %+.3f %4.1f | %.3f" % (
            k, r["t0"], r["dur"], r["dir"], r["v"], r["ang"], r["ang_max"], r["des"], r["des_max"],
            r["entry_os_m"], r["entry_os_pose"], r["entry_os_vyaw"], r["entry_rel_m"], r["entry_rel_pose"], r["entry_f"], r["entry_p"], r["entry_i"], r["entry_ff_share"], r["entry_fight_p"], r["entry_fight_i"],
            r["steady_os_m"], r["steady_os_pose"], r["steady_os_vyaw"], r["steady_rel_m"], r["steady_rel_pose"], r["steady_f"], r["steady_p"], r["steady_i"], r["steady_ff_share"], r["steady_fight_p"], r["steady_fight_i"],
            r["i_entry"], r["i_exc"], r["i_end"], r["i_t63"], r["out_pk"]))
    summ = {}
    for nm in ("entry", "steady"):
        for k in ("os_m", "os_pose", "os_vyaw", "rel_m", "rel_pose", "rel_vyaw", "f", "p", "i", "ff_share", "fight_p", "fight_i"):
            summ[nm + "_" + k] = med([r[nm + "_" + k] for r in rows])
    summ["i_exc"] = med([r["i_exc"] for r in rows]); summ["i_t63"] = med([r["i_t63"] for r in rows]); summ["n"] = len(rows)
    for side in (-1, 1):
        rs = [r for r in rows if r["dir"] == side]
        summ["steady_os_pose_dir%+d" % side] = med([r["steady_os_pose"] for r in rs]); summ["entry_os_pose_dir%+d" % side] = med([r["entry_os_pose"] for r in rs]); summ["n_dir%+d" % side] = len(rs)
    pr("  MEDIAN over curves: ENTRY os m/pose/vyaw %+.3f/%+.3f/%+.3f  rel m/pose %+.2f/%+.2f  f/p/i %+.3f/%+.3f/%+.3f ffsh %.2f fightP/I %.2f/%.2f | STEADY os %+.3f/%+.3f/%+.3f rel %+.2f/%+.2f f/p/i %+.3f/%+.3f/%+.3f ffsh %.2f fightP/I %.2f/%.2f | i exc %.3f t63 %.1f s | by dir: steady os_pose L(-1) %+.3f (n %d) R(+1) %+.3f (n %d); entry L %+.3f R %+.3f" % (
        summ["entry_os_m"], summ["entry_os_pose"], summ["entry_os_vyaw"], summ["entry_rel_m"], summ["entry_rel_pose"], summ["entry_f"], summ["entry_p"], summ["entry_i"], summ["entry_ff_share"], summ["entry_fight_p"], summ["entry_fight_i"],
        summ["steady_os_m"], summ["steady_os_pose"], summ["steady_os_vyaw"], summ["steady_rel_m"], summ["steady_rel_pose"], summ["steady_f"], summ["steady_p"], summ["steady_i"], summ["steady_ff_share"], summ["steady_fight_p"], summ["steady_fight_i"],
        summ["i_exc"], summ["i_t63"], summ["steady_os_pose_dir-1"], summ["n_dir-1"], summ["steady_os_pose_dir+1"], summ["n_dir+1"], summ["entry_os_pose_dir-1"], summ["entry_os_pose_dir+1"]))
    # aligned mean trajectory from entry
    pr("  ALIGNED MEAN TRAJECTORY from curve entry (curves >= 3 s; n=%d):  t | |des|  os_m  os_vyaw  os_pose  f.dir  p.dir  i.dir  |out|" % sum(1 for a, b in runs if b - a >= 300))
    traj = {}
    for tt in (0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0):
        k = int(tt * FS); vals = []
        for a, b in runs:
            if b - a < 300:
                continue
            d = np.sign(np.median(des[a:b])) or 1.0
            j = a + k
            vals.append((abs(des[j]), (m[j] - des[j]) * d, (vyaw[j] - des[j]) * d, (pose[j] - des[j]) * d, g["f"][j] * d, g["p"][j] * d, g["i"][j] * d, abs(g["output"][j])))
        if vals:
            v_ = np.nanmean(np.array(vals), 0); traj[tt] = v_.tolist()
            pr("   %4.2f | %5.2f  %+.3f  %+.3f  %+.3f  %+.3f  %+.3f  %+.3f  %.3f" % (tt, *v_))
    # frame-pooled bins
    pr("  FRAME-POOLED overshoot by |angle| and by speed (median; rel = actual/des - 1 at |des|>0.5):")
    pr("    phase   bin            secs |  os_m   os_pose  os_vyaw |  rel_m  rel_pose rel_vyaw | |des| p50  v p50 | f.dir  p.dir  i.dir")
    bins = {}
    entry_m = np.zeros(len(des), bool); steady_m = np.zeros(len(des), bool); dirf = np.zeros(len(des))
    for a, b in runs:
        d = np.sign(np.median(des[a:b])) or 1.0
        entry_m[a:a + 100] = True; steady_m[a + 150:b] = True; dirf[a:b] = d
    for phase, pm in (("entry", entry_m), ("steady", steady_m), ("all", entry_m | steady_m)):
        for kind, edges, key in (("ang", ANG_BINS, np.abs(g["ang"])), ("v", V_BINS, g["v"])):
            for lo, hi in edges:
                sel = pm & (key >= lo) & (key < hi)
                if sel.sum() < 50:
                    continue
                d = dirf[sel]; big = np.abs(des[sel]) > 0.5
                row = dict(secs=float(sel.sum() / FS), os_m=med((m[sel] - des[sel]) * d), os_pose=med((pose[sel] - des[sel]) * d), os_vyaw=med((vyaw[sel] - des[sel]) * d),
                           rel_m=med(m[sel][big] / des[sel][big] - 1) if big.sum() > 20 else np.nan, rel_pose=med(pose[sel][big] / des[sel][big] - 1) if big.sum() > 20 else np.nan, rel_vyaw=med(vyaw[sel][big] / des[sel][big] - 1) if big.sum() > 20 else np.nan,
                           des=med(np.abs(des[sel])), v=med(g["v"][sel]), f=med(g["f"][sel] * d), p=med(g["p"][sel] * d), i=med(g["i"][sel] * d))
                bins["%s %s %g-%g" % (phase, kind, lo, hi)] = row
                pr("    %-7s %-4s %-9s %5.0f | %+.3f  %+.3f  %+.3f | %+.2f  %+.2f  %+.2f | %5.2f  %5.1f | %+.3f %+.3f %+.3f" % (
                    phase, kind, "%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), row["secs"], row["os_m"], row["os_pose"], row["os_vyaw"], row["rel_m"], row["rel_pose"], row["rel_vyaw"], row["des"], row["v"], row["f"], row["p"], row["i"]))
    # entry overshoot vs |des| and vs |angle| (regressions across curves)
    x1 = np.array([r["des_max"] for r in rows]); x2 = np.array([r["ang_max"] for r in rows]); y = np.array([r["entry_os_pose"] for r in rows]); y2 = np.array([r["steady_os_pose"] for r in rows])
    okk = np.isfinite(y)
    if okk.sum() > 5:
        s1 = np.polyfit(x1[okk], y[okk], 1); s2 = np.polyfit(x2[okk], y[okk], 1)
        c1 = np.corrcoef(x1[okk], y[okk])[0, 1]; c2 = np.corrcoef(x2[okk], y[okk])[0, 1]
        pr("  ACROSS CURVES: entry os_pose vs |des|max slope %+.3f per m/s^2 (r %+.2f) ; vs |ang|max slope %+.4f per deg (r %+.2f)" % (s1[0], c1, s2[0], c2))
        summ["entry_slope_des"], summ["entry_r_des"], summ["entry_slope_ang"], summ["entry_r_ang"] = float(s1[0]), float(c1), float(s2[0]), float(c2)
    ok2 = np.isfinite(y2)
    if ok2.sum() > 5:
        s1 = np.polyfit(x1[ok2], y2[ok2], 1); s2 = np.polyfit(x2[ok2], y2[ok2], 1)
        c1 = np.corrcoef(x1[ok2], y2[ok2])[0, 1]; c2 = np.corrcoef(x2[ok2], y2[ok2])[0, 1]
        pr("  ACROSS CURVES: steady os_pose vs |des|max slope %+.3f per m/s^2 (r %+.2f) ; vs |ang|max slope %+.4f per deg (r %+.2f)" % (s1[0], c1, s2[0], c2))
        summ["steady_slope_des"], summ["steady_r_des"], summ["steady_slope_ang"], summ["steady_r_ang"] = float(s1[0]), float(c1), float(s2[0]), float(c2)
    # straight-road reference: pose - des on |des| < 0.2 (road crown / instrument bias), signed by nothing
    st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
    pr("  STRAIGHT reference (|des|<0.2, v>10, %.0f s): pose-des p50 %+.3f, m-des p50 %+.3f, vyaw-des %+.3f  (the crown/instrument bias that direction-folding cancels only if L/R curves balance)" % (
        st.sum() / FS, med(pose[st] - des[st]), med(m[st] - des[st]), med(vyaw[st] - des[st])))
    summ["straight_pose_bias"] = med(pose[st] - des[st]); summ["straight_m_bias"] = med(m[st] - des[st])
    return dict(curves=rows, summary=summ, traj=traj, bins=bins)


def main():
    out = {t: analyse(t) for t in TAGS}
    pr(); pr("=" * 130); pr("SIDE BY SIDE (medians over curves)  [r32/r33 old tune: LAF 1.689 fr 0.212 model SR 14.0 | r34 new: LAF 2.11 fr 0.03 SR 16.1]")
    keys = ["n", "entry_os_m", "entry_os_vyaw", "entry_os_pose", "entry_rel_m", "entry_rel_vyaw", "entry_rel_pose", "entry_f", "entry_p", "entry_i", "entry_ff_share", "entry_fight_p", "entry_fight_i",
            "steady_os_m", "steady_os_vyaw", "steady_os_pose", "steady_rel_m", "steady_rel_vyaw", "steady_rel_pose", "steady_f", "steady_p", "steady_i", "steady_ff_share", "steady_fight_p", "steady_fight_i", "i_exc", "i_t63",
            "entry_slope_des", "entry_slope_ang", "steady_slope_des", "steady_slope_ang", "straight_pose_bias", "straight_m_bias"]
    pr("  %-18s %10s %10s %10s" % ("", "r32", "r33", "r34"))
    for k in keys:
        pr("  %-18s %10s %10s %10s" % (k, *["%+.3f" % out[t]["summary"].get(k, np.nan) if k != "n" else "%d" % out[t]["summary"][k] for t in TAGS]))
    for ph in ("steady", "entry", "all"):
        pr("  BINS %s os_m / rel_m | os_vyaw / rel_vyaw by |angle| [secs]:" % ph)
        for lo, hi in ANG_BINS:
            cells = []
            for t in TAGS:
                r = out[t]["bins"].get("%s ang %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f | %+.3f/%+.2f [%3.0f]" % (r["os_m"], r["rel_m"], r["os_vyaw"], r["rel_vyaw"], r["secs"]) if r else "              --                ")
            pr("    ang %-8s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
    pr("  BINS steady os_pose / rel_pose by |angle| (secs):")
    for lo, hi in ANG_BINS:
        cells = []
        for t in TAGS:
            r = out[t]["bins"].get("steady ang %g-%g" % (lo, hi))
            cells.append("%+.3f / %+.2f [%3.0f]" % (r["os_pose"], r["rel_pose"], r["secs"]) if r else "        --        ")
        pr("    ang %-8s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
    pr("  BINS steady os_m / rel_m | os_vyaw / rel_vyaw by speed [secs]:")
    for lo, hi in V_BINS:
        cells = []
        for t in TAGS:
            r = out[t]["bins"].get("steady v %g-%g" % (lo, hi))
            cells.append("%+.3f/%+.2f | %+.3f/%+.2f [%3.0f]" % (r["os_m"], r["rel_m"], r["os_vyaw"], r["rel_vyaw"], r["secs"]) if r else "              --                ")
        pr("    v %-10s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
    pr("  BINS entry os_pose / rel_pose by |angle| (secs):")
    for lo, hi in ANG_BINS:
        cells = []
        for t in TAGS:
            r = out[t]["bins"].get("entry ang %g-%g" % (lo, hi))
            cells.append("%+.3f / %+.2f [%3.0f]" % (r["os_pose"], r["rel_pose"], r["secs"]) if r else "        --        ")
        pr("    ang %-8s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
    open(os.path.join(HERE, "CURVE-OVERSTEER-r34.txt"), "w", encoding="utf-8").write("\n".join(LINES))
    json.dump(out, open(os.path.join(HERE, "curve_oversteer_r34.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))


if __name__ == "__main__":
    main()
