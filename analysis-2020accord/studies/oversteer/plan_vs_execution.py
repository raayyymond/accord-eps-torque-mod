# -*- coding: utf-8 -*-
"""plan_vs_execution.py -- IS THE OVERSTEER IN THE PLAN OR IN THE EXECUTION?  (2026-09-05)

Every prior measurement in this kit compared ACHIEVED lat accel against the CONTROLLER'S OWN
SETPOINT.  That tests execution and is blind to a planner that cuts the corner.  This script adds
the missing reference: the ROAD, taken from modelV2's own lane lines.

Conventions, all verified in SECTION V:
  * device frame is FRD -> +y is to the RIGHT of the car.  laneLines[1] is LEFT (mean y -1.56 m),
    laneLines[2] is RIGHT (+1.69).  (controlsd's own comment: curvature positive = RIGHT turn.)
  * lane centre in car frame  y_c(x) = 0.5*(ll1_y + ll2_y);  y_c(0) > 0 means the lane centre is to
    the RIGHT of the car, i.e. the CAR IS LEFT OF CENTRE.  So  off_right = -y_c(0).
  * off_inside = off_right * sign(kappa_road): positive = the car sits toward the INSIDE of the bend.

Three curvatures, all 1/m, all positive-right:
  K_ROAD    cubic fit of the lane centre over x in [0, FIT_M]; c2 is the curvature AT THE CAR, c3 the
            clothoid rate, so K_road(d) = c2 + c3*d is the road curvature d metres ahead.  PLANNER-FREE.
  K_PLAN    modelV2.action.desiredCurvature -- what the driving model ASKS FOR.
  K_ACH     yaw_cal / v -- what the car DID (livePose, calibrated; SR-free, no roll model).
  (plus K_PATH, the cubic fit of modelV2.position, the model's own planned path.)

  K_PLAN vs K_ROAD  ->  is the PLAN over-turning?      (planner)
  K_ACH  vs K_PLAN  ->  is the loop over-delivering?   (controller + plant)  [this kit's R_road]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "osc-highangle"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import oversteer_v282_r39 as M   # noqa: E402  (gof/curve_mask/straight_bias/boot_ci, the published pipeline)
import backcalc_laf_friction as B  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = os.path.join(HERE, "_scratch")
FS = M.FS
TAGS = ("r39", "r3c", "r3a")
MODEL = {"r39": "rdf43", "r3c": "tsfdo", "r3a": "tsfdo"}
LAF = {"r39": 2.11, "r3c": 3.6, "r3a": 4.0}
FIT_M = 50.0           # cubic fit window for the lane-centre / path curvature
LINES = []

M.TUNE.update({"r3a": dict(kp=0.8, laf=4.0, fric=0.03, sr="MAP", note="V282 LAF4.0"),
               "r3c": dict(kp=0.8, laf=3.6, fric=0.03, sr="MAP", note="V282 LAF3.6")})


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def boot(vals, n=4000, seed=7):
    return M.boot_ci(vals, n, seed)


# ---------------------------------------------------------------- gap guard (r3a is missing segment 10)
_gof0 = M.gof
GAPS = {}


def gof(tag):
    g, cp = _gof0(tag)
    if "gapok" not in g:
        D = B.load(tag)
        ct = D["co_t"] - D["co_t"][0]
        ok = np.ones(len(g["t"]), bool)
        holes = []
        for i in np.where(np.diff(ct) > 1.0)[0]:
            a, b = float(ct[i]), float(ct[i + 1])
            holes.append((a, b))
            ok &= ~((g["t"] > a - 0.5) & (g["t"] < b + 0.5))
        g["gapok"] = ok
        GAPS[tag] = holes
    return g, cp


M.gof = gof
_cm0 = M.curve_mask
M.curve_mask = lambda g: _cm0(g) & g["gapok"]


# --------------------------------------------- cubic fit of y(x): y = c0 + c1 x + c2/2 x^2 + c3/6 x^3
def cubic_curv(x, Y, xmax):
    """Vectorised over rows of Y.  Returns (c2, c3): curvature at x=0 and its rate, 1/m and 1/m^2."""
    sel = (x >= 0) & (x <= xmax)
    xs = x[sel]
    A = np.stack([np.ones_like(xs), xs, 0.5 * xs ** 2, (1.0 / 6.0) * xs ** 3], 1)
    Ys = np.where(np.isfinite(Y[:, sel]), Y[:, sel], 0.0)
    coef, *_ = np.linalg.lstsq(A, Ys.T, rcond=None)
    bad = ~np.isfinite(Y[:, sel]).all(axis=1)
    c2 = coef[2].copy()
    c3 = coef[3].copy()
    c2[bad] = np.nan
    c3[bad] = np.nan
    return c2, c3


def path_curv_from_pos(px, py, xmax):
    """position is TIME-parameterised, so x differs per frame -- fit each row on its own x."""
    n = px.shape[0]
    c2 = np.full(n, np.nan)
    c3 = np.full(n, np.nan)
    for i in range(n):
        x = px[i]
        y = py[i]
        ok = np.isfinite(x) & np.isfinite(y) & (x >= 0) & (x <= xmax)
        if ok.sum() < 6 or x[ok].max() < 0.6 * xmax:
            continue
        xs = x[ok]
        A = np.stack([np.ones_like(xs), xs, 0.5 * xs ** 2, (1.0 / 6.0) * xs ** 3], 1)
        try:
            c, *_ = np.linalg.lstsq(A, y[ok], rcond=None)
        except Exception:
            continue
        c2[i], c3[i] = c[2], c[3]
    return c2, c3


# ---------------------------------------------------------------- build the joined 20 Hz model frame
FR = {}


def frame(tag):
    if tag in FR:
        return FR[tag]
    g, cp = gof(tag)
    D = B.load(tag)
    t0 = float(D["co_t"][0])
    z = np.load(os.path.join(SCR, "%s_modelv2.npz" % tag), allow_pickle=True)
    mt = z["mdl_t"] - t0
    x = np.asarray(z["mdl_ll1_x"][0], float)              # X_IDXS, constant (asserted in SECTION V)
    ll1 = np.asarray(z["mdl_ll1_y"], float)
    ll2 = np.asarray(z["mdl_ll2_y"], float)
    re0 = np.asarray(z["mdl_re0_y"], float)
    re1 = np.asarray(z["mdl_re1_y"], float)
    yc = 0.5 * (ll1 + ll2)
    f = dict(t=mt, tag=tag, x=x, yc=yc, ll1=ll1, ll2=ll2)
    f["ll1_0"] = ll1[:, 0]
    f["ll2_0"] = ll2[:, 0]
    f["lane_w"] = ll2[:, 0] - ll1[:, 0]
    f["off_right"] = -yc[:, 0]                            # + = car right of lane centre
    f["re_w"] = re1[:, 0] - re0[:, 0]
    f["off_right_re"] = -0.5 * (re0[:, 0] + re1[:, 0])
    c2, c3 = cubic_curv(x, yc, FIT_M)
    f["k_road"] = c2
    f["k_road_rate"] = c3
    f["k_road20"] = cubic_curv(x, yc, 20.0)[0]
    f["k_plan"] = np.asarray(z["mdl_descurv"], float)
    pc2, pc3 = path_curv_from_pos(np.asarray(z["mdl_pos_x"], float), np.asarray(z["mdl_pos_y"], float), FIT_M)
    f["k_path"] = pc2
    f["k_path_rate"] = pc3
    f["llprob"] = np.asarray(z["mdl_llprob"], float)
    f["llstd"] = np.asarray(z["mdl_llstd"], float)
    f["lcs"] = np.asarray(z["mdl_lcs"], float)
    f["pos_xmax"] = np.nanmax(np.asarray(z["mdl_pos_x"], float), axis=1)
    f["params"] = json.loads(str(z["params_json"]))
    for k in ("v", "lat", "pressed", "active", "sa_deg", "yaw_cal", "desiredLateralAccel",
              "actualLateralAccel", "descurv", "curv", "proll", "error", "i", "p", "f",
              "saturated", "gapok"):
        f[k] = np.interp(mt, g["t"], np.asarray(g[k], float))
    f["k_ach"] = f["yaw_cal"] / np.maximum(f["v"], 1.0)
    f["k_ctl"] = f["descurv"]                              # controlsState.desiredCurvature = POST-StarPilot
    f["eng"] = (f["lat"] > 0.5) & (f["active"] > 0.5) & (f["pressed"] < 0.5) & (f["gapok"] > 0.5)
    f["ll_ok"] = ((f["llprob"][:, 1] > 0.5) & (f["llprob"][:, 2] > 0.5)
                  & (f["llstd"][:, 1] < 0.5) & (f["llstd"][:, 2] < 0.5)
                  & (f["lane_w"] > 2.6) & (f["lane_w"] < 4.8)
                  & (f["lcs"] < 0.5))                      # laneChangeState == off
    FR[tag] = f
    return f


def blocks(mask, minlen, gap=5):
    """contiguous runs of `mask`, merged across short gaps -- the bootstrap unit."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    out = [[idx[0], idx[0] + 1]]
    for i in idx[1:]:
        if i - out[-1][1] <= gap:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return [(a, b) for a, b in out if b - a >= minlen]


def blockmed(mask, vals, minlen=10):
    """per-block medians of `vals` over contiguous runs of `mask` -- a decorrelated sample."""
    out = []
    for a, b in blocks(mask, minlen):
        sub = vals[a:b]
        sub = sub[np.isfinite(sub)]
        if sub.size:
            out.append(float(np.median(sub)))
    return out



K_BANDS = (("straight <0.0008", 0.0000, 0.0008), ("gentle .0008-.003", 0.0008, 0.0030),
           ("medium .003-.010", 0.0030, 0.0100), ("tight  >=.010", 0.0100, 1.0))
V_BANDS = ((2, 5), (5, 9), (9, 14), (14, 20), (20, 40))
DT_M = 0.05     # modelV2 is 20 Hz


def decomp(tag, rows):
    """oversteer_v282_r3a3c.decomp, verbatim -- the PUBLISHED execution estimator."""
    g, _ = gof(tag)
    des = g["desiredLateralAccel"]
    sb = M.straight_bias(g)
    out = dict(rm=[], rr=[], ri=[])
    for r in rows:
        if r["des"] <= 0.5 or r["b"] - r["a"] < int(2.5 * FS):
            continue
        sl = slice(r["a"] + 150, r["b"])
        big = np.abs(des[sl]) > 0.5
        if big.sum() < 10:
            continue
        m_ = g["actualLateralAccel"][sl][big] - sb["m"]
        rd = g["vyaw"][sl][big] - sb["vyaw"]
        dd = des[sl][big]
        out["rm"].append(med(m_ / dd))
        out["rr"].append(med(rd / dd))
        out["ri"].append(med(rd / m_))
    return out


def sectionV():
    pr("=" * 170)
    pr("SECTION V -- PIPELINE VALIDATION.  Nothing below is trusted until this passes.")
    pr("=" * 170)
    d = decomp("r39", M.curves("r39")[0])
    lo1, hi1 = boot(d["rm"])
    lo2, hi2 = boot(d["rr"])
    pr("  V.1  r39 EXECUTION numbers re-derived through the imported pipeline (STATE.md publishes")
    pr("       R_m 1.123 [1.083,1.180] | R_road 1.116 [1.029,1.205] | 1/rho 0.988 | n 20 curves):")
    pr("       THIS RUN : n %2d curves | R_m %.3f [%.3f,%.3f] | R_road %.3f [%.3f,%.3f] | 1/rho %.3f"
       % (len(d["rm"]), med(d["rm"]), lo1, hi1, med(d["rr"]), lo2, hi2, med(d["ri"])))
    ok = (abs(med(d["rm"]) - 1.123) < 5e-4 and abs(med(d["rr"]) - 1.116) < 5e-4
          and abs(med(d["ri"]) - 0.988) < 5e-4 and len(d["rm"]) == 20)
    pr("       -> %s" % ("REPRODUCED EXACTLY" if ok else "*** MISMATCH -- DO NOT TRUST WHAT FOLLOWS ***"))
    pr("")
    pr("  V.2  frame / sign conventions, read off the data (not assumed):")
    pr("       %-5s %9s %9s %9s %8s | %9s %9s | %8s %8s %8s" % (
        "route", "ll1_y[0]", "ll2_y[0]", "lane w", "reW", "corr kp,ka", "corr kr,ka", "sd kp", "sd kr", "sd ka"))
    for t in TAGS:
        f = frame(t)
        m = f["eng"] & f["ll_ok"] & (f["v"] > 5)
        kp, kr, ka = f["k_plan"][m], f["k_road"][m], f["k_ach"][m]
        gd = np.isfinite(kp) & np.isfinite(kr) & np.isfinite(ka)
        pr("       %-5s %9.3f %9.3f %9.3f %8.2f | %9.3f %9.3f | %8.5f %8.5f %8.5f" % (
            t, med(f["ll1_0"][m]), med(f["ll2_0"][m]), med(f["lane_w"][m]), med(f["re_w"][m]),
            np.corrcoef(kp[gd], ka[gd])[0, 1], np.corrcoef(kr[gd], ka[gd])[0, 1],
            np.std(kp[gd]), np.std(kr[gd]), np.std(ka[gd])))
    pr("       ll1 < 0 < ll2 confirms +y = RIGHT.  Positive corr with the ACHIEVED yaw confirms all three")
    pr("       curvatures are positive-RIGHT and the lane-line fit is measuring the same road.")
    pr("")
    pr("  V.3  X_IDXS constancy + laneLine validity exposure:")
    for t in TAGS:
        z = np.load(os.path.join(SCR, "%s_modelv2.npz" % t), allow_pickle=True)
        xs = np.asarray(z["mdl_ll1_x"], float)
        f = frame(t)
        pr("       %-5s  max|x - x[0]| = %.3e   frames %6d   engaged %6d (%6.1f s)   ll_ok&eng %6d (%6.1f s)"
           % (t, np.nanmax(np.abs(xs - xs[0])), len(f["t"]), int(f["eng"].sum()), f["eng"].sum() * DT_M,
              int((f["eng"] & f["ll_ok"]).sum()), (f["eng"] & f["ll_ok"]).sum() * DT_M))
    pr("")
    pr("  V.4  INDEPENDENT CHECK of the lane-line curvature instrument: on well-centred, steady, engaged")
    pr("       curve frames the ROAD curvature must equal the ACHIEVED path curvature (the car is holding")
    pr("       its lane, so it must be tracing the road).  A ratio far from 1.00 would condemn K_ROAD.")
    pr("       %-5s %7s %10s %10s %10s   %s" % ("route", "n", "med k_road", "med k_ach", "ratio", "95% CI (block boot)"))
    for t in TAGS:
        f = frame(t)
        m = (f["eng"] & f["ll_ok"] & (f["v"] > 8) & (np.abs(f["off_right"]) < 0.15)
             & (np.abs(f["k_road"]) > 0.002) & (np.abs(f["k_road_rate"]) < 5e-5))
        bm_r = blockmed(m, np.abs(f["k_road"]))
        bm_a = blockmed(m, np.abs(f["k_ach"]))
        rat = [a / r for r, a in zip(bm_r, bm_a) if r > 1e-4]
        lo, hi = boot(rat)
        pr("       %-5s %7d %10.5f %10.5f %10.3f   [%.3f, %.3f]  (%d blocks)"
           % (t, int(m.sum()), med(np.abs(f["k_road"][m])), med(np.abs(f["k_ach"][m])), med(rat), lo, hi, len(rat)))
    pr("")


# ================================================================================================ 1
def section1():
    pr("=" * 170)
    pr("SECTION 1 -- LATERAL POSITION IN THE LANE.  off_inside > 0  =>  the car sits toward the INSIDE")
    pr("  of the bend.  Straights carry no turn direction, so they are reported as off_right and are the")
    pr("  CONTROL: a camera / mounting bias shows up there and NOT as a sign-flipping inside bias.")
    pr("  Unit of inference = a contiguous >=0.5 s block; CI = block bootstrap of the median.  cm.")
    pr("=" * 170)
    for t in TAGS:
        f = frame(t)
        pr("  --- %s  (model %s, SteerLatAccel %.2f) ---" % (t, MODEL[t], LAF[t]))
        pr("      %-18s %-9s %7s %8s %10s %18s %9s  %s" % ("|k_road| band", "v m/s", "secs", "blocks",
                                                           "value cm", "95% CI", "|k| med", "what"))
        for nm, klo, khi in K_BANDS:
            for vlo, vhi in V_BANDS:
                m = (f["eng"] & f["ll_ok"] & (f["v"] >= vlo) & (f["v"] < vhi)
                     & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi))
                if m.sum() < 20:
                    continue
                if nm.startswith("straight"):
                    val = f["off_right"]
                    lab = "off_right"
                else:
                    val = f["off_right"] * np.sign(f["k_road"])
                    lab = "off_inside"
                bm = blockmed(m, val * 100.0)
                if len(bm) < 4:
                    continue
                lo, hi = boot(bm)
                pr("      %-18s %-9s %7.1f %8d %10.1f %18s %9.4f  %s"
                   % (nm, "%d-%d" % (vlo, vhi), m.sum() * DT_M, len(bm), med(bm),
                      "[%+6.1f, %+6.1f]" % (lo, hi), med(np.abs(f["k_road"][m])), lab))
        pr("")


# ================================================================================================ 3
def section3():
    pr("=" * 170)
    pr("SECTION 3 -- TURNS EARLY?  K_road(d) = c2 + c3*d is the road curvature d metres ahead, from the")
    pr("  SAME lane-centre cubic.  For each d we correlate K_PLAN with K_road(d) over engaged curve frames;")
    pr("  d* = argmax R^2 is the lookahead the plan is actually steering to.  The JUSTIFIED lookahead is")
    pr("  v * (lat_delay 0.200 + DT_MDL 0.050 + DT_MDL/2 0.025 + LAT_SMOOTH 0.100) = v * 0.375 s.")
    pr("=" * 170)
    DS = np.arange(0.0, 65.0, 2.5)
    for t in TAGS:
        f = frame(t)
        pr("  --- %s  (model %s) ---" % (t, MODEL[t]))
        pr("      %-9s %7s | %8s %8s %8s | %10s %10s %10s %9s" % (
            "v m/s", "secs", "d* m", "t* s", "R2(d*)", "just. d m", "just. t s", "excess m", "excess s"))
        for vlo, vhi in V_BANDS:
            m = (f["eng"] & f["ll_ok"] & (f["v"] >= vlo) & (f["v"] < vhi)
                 & (np.abs(f["k_road"]) >= 0.002) & np.isfinite(f["k_road_rate"]))
            if m.sum() < 200:
                continue
            kp = f["k_plan"][m]
            c2 = f["k_road"][m]
            c3 = f["k_road_rate"][m]
            best = (-1.0, np.nan)
            for d in DS:
                kr = c2 + c3 * d
                gd = np.isfinite(kr) & np.isfinite(kp)
                if gd.sum() < 100:
                    continue
                r = np.corrcoef(kr[gd], kp[gd])[0, 1] ** 2
                if r > best[0]:
                    best = (r, d)
            vm = med(f["v"][m])
            dj = vm * 0.375
            pr("      %-9s %7.1f | %8.1f %8.3f %8.3f | %10.1f %10.3f %10.1f %9.3f"
               % ("%d-%d" % (vlo, vhi), m.sum() * DT_M, best[1], best[1] / max(vm, 1e-6), best[0],
                  dj, 0.375, best[1] - dj, best[1] / max(vm, 1e-6) - 0.375))
        pr("")
    pr("  3b  TIME-LAG cross-correlation, K_PLAN(t) vs K_ROAD-at-the-car(t).  A positive lead means the")
    pr("      plan moves BEFORE the road curves under the car.  Engaged, all speeds.")
    pr("      %-5s %8s %10s %10s %10s" % ("route", "n", "lead s", "peak corr", "corr at 0"))
    for t in TAGS:
        f = frame(t)
        m = f["eng"] & f["ll_ok"] & np.isfinite(f["k_road"])
        kp = np.where(m, f["k_plan"], np.nan)
        kr = np.where(m, f["k_road"], np.nan)
        best = (-2.0, np.nan)
        c0 = np.nan
        n = len(kp)
        for lag in range(-60, 61):   # +-3 s at 20 Hz; positive lag = plan leads
            if lag >= 0:
                a = kp[:n - lag] if lag else kp
                b = kr[lag:]
            else:
                a = kp[-lag:]
                b = kr[:n + lag]
            gd = np.isfinite(a) & np.isfinite(b)
            if gd.sum() < 500:
                continue
            c = np.corrcoef(a[gd], b[gd])[0, 1]
            if lag == 0:
                c0 = c
            if c > best[0]:
                best = (c, lag * DT_M)
        pr("      %-5s %8d %10.3f %10.3f %10.3f" % (t, int(m.sum()), best[1], best[0], c0))
    pr("")


# ================================================================================================ 4
def section4():
    pr("=" * 170)
    pr("SECTION 4 -- DOES THE MODEL SWAP MOVE ANY OF IT?  r39 = rdf43; r3c + r3a = tsfdo.  SPEED-MATCHED")
    pr("  to 9-20 m/s, the band all three share.  If the planner is the cause this contrast should be the")
    pr("  largest effect in the dataset.  LAF also differs (2.11 / 3.6 / 4.0) but LAF is a CONTROLLER gain")
    pr("  and cannot touch K_PLAN/K_ROAD, so that column isolates the model swap.")
    pr("=" * 170)
    pr("      %-5s %-7s %7s %7s | %10s %18s | %-22s %-22s" % (
        "route", "model", "secs", "blocks", "off_inside", "95% CI cm", "K_PLAN/K_ROAD", "K_ACH/K_ROAD"))
    for t in TAGS:
        f = frame(t)
        base = f["eng"] & f["ll_ok"] & (f["v"] >= 9) & (f["v"] < 20)
        m1 = base & (np.abs(f["k_road"]) >= 0.003)
        bm = blockmed(m1, f["off_right"] * np.sign(f["k_road"]) * 100.0)
        lo, hi = boot(bm)
        m2 = m1 & (np.abs(f["off_right"]) < 0.20)
        rows = []
        for a, b in blocks(m2, 10):
            kr = med(np.abs(f["k_road"][a:b]))
            kp = med(np.abs(f["k_plan"][a:b]))
            ka = med(np.abs(f["k_ach"][a:b]))
            if kr > 1e-4:
                rows.append((kp / kr, ka / kr))
        R = np.array(rows) if rows else np.zeros((0, 2))
        c = []
        for j in range(2):
            l2, h2 = boot(R[:, j]) if len(R) >= 4 else (np.nan, np.nan)
            c.append("%6.3f [%5.3f,%5.3f]" % (med(R[:, j]) if len(R) else np.nan, l2, h2))
        pr("      %-5s %-7s %7.1f %7d | %10.1f %18s | %-22s %-22s"
           % (t, MODEL[t], m1.sum() * DT_M, len(bm), med(bm), "[%+6.1f, %+6.1f]" % (lo, hi), c[0], c[1]))
    pr("")
    pr("  4b  the same offset statistic on STRAIGHTS (|k_road| < 0.0008), 9-20 m/s -- the CONTROL:")
    pr("      %-5s %-7s %7s %7s | %10s %18s" % ("route", "model", "secs", "blocks", "off_right", "95% CI cm"))
    for t in TAGS:
        f = frame(t)
        m = f["eng"] & f["ll_ok"] & (f["v"] >= 9) & (f["v"] < 20) & (np.abs(f["k_road"]) < 0.0008)
        bm = blockmed(m, f["off_right"] * 100.0)
        lo, hi = boot(bm)
        pr("      %-5s %-7s %7.1f %7d | %10.1f %18s"
           % (t, MODEL[t], m.sum() * DT_M, len(bm), med(bm), "[%+6.1f, %+6.1f]" % (lo, hi)))
    pr("")


# ================================================================================================ 5
def section5():
    pr("=" * 170)
    pr("SECTION 5 -- LATERAL-OFFSET TOGGLES, read from initData.params on each route.")
    pr("=" * 170)
    keys = ("CameraOffset", "LaneCentering", "LaneCenterOffset", "LaneCenteringE2EAuthority",
            "LaneCenteringPauseOnSignal", "SteerOffset", "Model", "DrivingModel", "DrivingModelVersion",
            "SteerLatAccel", "SteerKP", "SteerFriction", "SteerDelay", "SteerRatio", "NNFFModelName",
            "NudgelessLaneChange", "LaneChanges")
    pr("      %-28s %-18s %-18s %-18s" % ("param", "r39", "r3c", "r3a"))
    for k in keys:
        vals = [str(frame(t)["params"].get(k, "<absent>")) for t in TAGS]
        flag = "   <-- DIFFERS" if len(set(vals)) > 1 else ""
        pr("      %-28s %-18s %-18s %-18s%s" % (k, vals[0], vals[1], vals[2], flag))
    pr("")
    pr("  5b  LaneCentering is ON (=1) on all three, offset 0.0, E2E authority 1.0.  From the flown fork,")
    pr("      selfdrive/controls/lib/lane_centering.py:130-153 and controlsd.py:743-753:")
    pr("        target_y = 0.5*(left + right) + clip(LaneCenterOffset, ...)      # LaneCenterOffset = 0.0")
    pr("        error    = target_y - model_path_y(lookahead)   [deadband 0.08 m]")
    pr("        error   *= 1 - e2e_authority * clip((|error|-0.15)/0.35, 0, 1)   # authority 1.0")
    pr("        corr     = clip(2*error/lookahead^2, +-0.004) * 0.30            # then tau=0.4 s smoothing")
    pr("      => a CENTERING feedback with NO constant bias (offset is 0), DISABLED for |error| >= 0.50 m")
    pr("         by the e2e break-in, ceiling 1.2e-3 1/m.  A fixed camera or path offset would instead")
    pr("         show as a NON-ZERO off_right ON STRAIGHTS -- see section 4b.")
    pr("")
    pr("  5c  measured size of the StarPilot-added curvature (K_CTL - K_PLAN), engaged, by band:")
    pr("      %-5s %-18s %8s %12s %12s %12s" % ("route", "|k_road| band", "secs", "med |dK|", "p95 |dK|", "med dK*sign"))
    for t in TAGS:
        f = frame(t)
        dk = f["k_ctl"] - f["k_plan"]
        for nm, klo, khi in K_BANDS:
            m = f["eng"] & f["ll_ok"] & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi) & (f["v"] > 5)
            if m.sum() < 50:
                continue
            pr("      %-5s %-18s %8.1f %12.6f %12.6f %12.6f"
               % (t, nm, m.sum() * DT_M, med(np.abs(dk[m])),
                  float(np.nanpercentile(np.abs(dk[m]), 95)), med(dk[m] * np.sign(f["k_road"][m]))))
    pr("")




# ================================================================================ 1b / 2b / 2c
def _lookahead(f):
    """the fork's own lane-centering lookahead: clip(v, 8, 35) metres (lane_centering.py:119)."""
    return np.clip(f["v"], 8.0, 35.0)


def _interp_row(xrow, yrow, d):
    n = len(d)
    out = np.full(n, np.nan)
    for i in range(n):
        x = xrow[i]
        y = yrow[i]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 4 or x[ok].max() < d[i]:
            continue
        out[i] = np.interp(d[i], x[ok], y[ok])
    return out


def prep_plan_offset(tag):
    """plan_off_right(d) = path_y(d) - lane_centre_y(d).  + = the PLAN sits right of lane centre."""
    f = frame(tag)
    if "plan_off_right" in f:
        return f
    z = np.load(os.path.join(SCR, "%s_modelv2.npz" % tag), allow_pickle=True)
    px = np.asarray(z["mdl_pos_x"], float)
    py = np.asarray(z["mdl_pos_y"], float)
    d = _lookahead(f)
    path_y = _interp_row(px, py, d)
    x = f["x"]
    yc = f["yc"]
    lane_y = np.array([np.interp(d[i], x, yc[i]) for i in range(len(d))])
    f["look_d"] = d
    f["path_y_d"] = path_y
    f["lane_y_d"] = lane_y
    f["plan_off_right"] = path_y - lane_y
    # 30 m fixed lookahead, for a speed-independent read
    d30 = np.full(len(d), 30.0)
    f["plan_off_right30"] = _interp_row(px, py, d30) - np.array([np.interp(30.0, x, yc[i]) for i in range(len(d))])
    return f


def section1b():
    pr("=" * 170)
    pr("SECTION 1b -- IS THE INSIDE BIAS REAL?  Three ways to break it.")
    pr("  (i) LEFT vs RIGHT turns separately.  A constant camera/mounting bias cannot produce a positive")
    pr("      off_inside on BOTH sides; it produces +b on one and -b on the other.")
    pr("  (ii) the ROAD-EDGE head instead of the lane-line head (a different model output).")
    pr("  (iii) the raw distances to the inside and outside lane line, in metres -- a plausibility check.")
    pr("=" * 170)
    pr("      %-5s %-18s %-6s %7s %7s | %9s %16s | %9s | %7s %7s" % (
        "route", "|k_road| band", "turn", "secs", "blocks", "off_inside", "95% CI cm",
        "edge-based", "d_in m", "d_out m"))
    for t in TAGS:
        f = frame(t)
        for nm, klo, khi in K_BANDS[1:]:
            for turn, sgn in (("LEFT", -1.0), ("RIGHT", +1.0)):
                m = (f["eng"] & f["ll_ok"] & (f["v"] >= 5)
                     & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi)
                     & (np.sign(f["k_road"]) == sgn))
                if m.sum() < 40:
                    continue
                ins = f["off_right"] * np.sign(f["k_road"])
                bm = blockmed(m, ins * 100.0)
                if len(bm) < 4:
                    continue
                lo, hi = boot(bm)
                ins_re = f["off_right_re"] * np.sign(f["k_road"])
                bre = blockmed(m & (f["re_w"] > 4.0) & (f["re_w"] < 30.0), ins_re * 100.0)
                # inside / outside lane-line distance
                d_in = np.where(f["k_road"] > 0, f["ll2_0"], -f["ll1_0"]) - f["off_right"] * np.sign(f["k_road"]) * 0
                d_in = 0.5 * f["lane_w"] - ins
                d_out = 0.5 * f["lane_w"] + ins
                pr("      %-5s %-18s %-6s %7.1f %7d | %9.1f %16s | %9.1f | %7.2f %7.2f"
                   % (t, nm, turn, m.sum() * DT_M, len(bm), med(bm), "[%+6.1f,%+6.1f]" % (lo, hi),
                      med(bre) if len(bre) else np.nan, med(d_in[m]), med(d_out[m])))
    pr("")
    pr("  1b-iv  DISTRIBUTION of off_inside on engaged curve frames (|k_road| >= 0.0008, v >= 5) -- this is")
    pr("         why SECTION 2's original |off_right| < 0.20 m gate returned nothing:")
    pr("      %-5s %8s %8s %8s %8s %8s %8s   %s" % ("route", "p5", "p25", "p50", "p75", "p95", "secs",
                                                    "frac |off|<0.20 m"))
    for t in TAGS:
        f = frame(t)
        m = f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0008)
        ins = (f["off_right"] * np.sign(f["k_road"]))[m] * 100.0
        pr("      %-5s %8.1f %8.1f %8.1f %8.1f %8.1f %8.1f   %.3f"
           % (t, *[float(np.nanpercentile(ins, p)) for p in (5, 25, 50, 75, 95)],
              m.sum() * DT_M, float(np.mean(np.abs(ins) < 20.0))))
    pr("")


def section2():
    pr("=" * 170)
    pr("SECTION 2 -- THE DELIVERABLE: IS THE PLAN CUTTING, OR IS THE EXECUTION?")
    pr("  PLAN_inside  = (path_y(d) - lane_centre_y(d)) * sign(k_road), d = the fork's own lookahead")
    pr("                 clip(v,8,35) m.  This is where the MODEL WANTS TO BE, independent of where the")
    pr("                 car currently is.  > 0 => the PLAN itself is aimed at the inside of the bend.")
    pr("  CAR_inside   = off_inside now (SECTION 1).")
    pr("  ARRIVED      = CAR_inside sampled d/v seconds LATER, i.e. where the car actually ended up at the")
    pr("                 point the plan was aiming at.  PLAN vs ARRIVED separates planner from tracking:")
    pr("                   ARRIVED ~ PLAN   -> the car goes where it is told  => THE PLAN.")
    pr("                   ARRIVED > PLAN   -> the car overshoots the plan     => THE EXECUTION.")
    pr("  All in cm, block-bootstrapped, engaged + lane-lines-valid only.")
    pr("=" * 170)
    pr("      %-5s %-18s %-9s %7s %6s | %9s %16s | %9s %16s | %9s %16s" % (
        "route", "|k_road| band", "v m/s", "secs", "blk", "PLAN_ins", "95% CI",
        "CAR_ins", "95% CI", "ARRIVED", "95% CI"))
    for t in TAGS:
        f = prep_plan_offset(t)
        n = len(f["t"])
        # arrival index: the car reaches the lookahead point d/v seconds later
        j = np.clip(np.arange(n) + np.round(f["look_d"] / np.maximum(f["v"], 1.0) / DT_M).astype(int), 0, n - 1)
        sg = np.sign(f["k_road"])
        plan_ins = f["plan_off_right"] * sg
        car_ins = f["off_right"] * sg
        arr_ins = (f["off_right"][j]) * sg
        arr_ok = f["eng"][j] & f["ll_ok"][j]
        for nm, klo, khi in K_BANDS[1:]:
            for vlo, vhi in V_BANDS[1:]:
                m = (f["eng"] & f["ll_ok"] & (f["v"] >= vlo) & (f["v"] < vhi)
                     & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi)
                     & np.isfinite(f["plan_off_right"]))
                if m.sum() < 40:
                    continue
                b1 = blockmed(m, plan_ins * 100.0)
                b2 = blockmed(m, car_ins * 100.0)
                b3 = blockmed(m & arr_ok, arr_ins * 100.0)
                if min(len(b1), len(b2), len(b3)) < 4:
                    continue
                c = []
                for b in (b1, b2, b3):
                    lo, hi = boot(b)
                    c.append((med(b), "[%+6.1f,%+6.1f]" % (lo, hi)))
                pr("      %-5s %-18s %-9s %7.1f %6d | %9.1f %16s | %9.1f %16s | %9.1f %16s"
                   % (t, nm, "%d-%d" % (vlo, vhi), m.sum() * DT_M, len(b1),
                      c[0][0], c[0][1], c[1][0], c[1][1], c[2][0], c[2][1]))
        pr("")
    pr("  2b  PAIRED difference ARRIVED - PLAN (cm), the execution overshoot on top of the plan, and")
    pr("      PLAN - 0, the planner's own inside bias.  Both block-bootstrapped on the SAME blocks.")
    pr("      %-5s %-18s %7s %6s | %11s %16s | %11s %16s" % (
        "route", "|k_road| band", "secs", "blk", "PLAN_ins", "95% CI", "ARRIVED-PLAN", "95% CI"))
    for t in TAGS:
        f = prep_plan_offset(t)
        n = len(f["t"])
        j = np.clip(np.arange(n) + np.round(f["look_d"] / np.maximum(f["v"], 1.0) / DT_M).astype(int), 0, n - 1)
        sg = np.sign(f["k_road"])
        plan_ins = f["plan_off_right"] * sg
        arr_ins = f["off_right"][j] * sg
        arr_ok = f["eng"][j] & f["ll_ok"][j]
        for nm, klo, khi in K_BANDS[1:]:
            m = (f["eng"] & f["ll_ok"] & arr_ok & (f["v"] >= 5)
                 & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi)
                 & np.isfinite(f["plan_off_right"]))
            if m.sum() < 40:
                continue
            b1 = blockmed(m, plan_ins * 100.0)
            b2 = blockmed(m, (arr_ins - plan_ins) * 100.0)
            if min(len(b1), len(b2)) < 4:
                continue
            l1, h1 = boot(b1)
            l2, h2 = boot(b2)
            pr("      %-5s %-18s %7.1f %6d | %11.1f %16s | %11.1f %16s"
               % (t, nm, m.sum() * DT_M, len(b1), med(b1), "[%+6.1f,%+6.1f]" % (l1, h1),
                  med(b2), "[%+6.1f,%+6.1f]" % (l2, h2)))
    pr("")
    pr("  2c  the CURVATURE ratios, ungated on position (the original gate found no frames -- see 1b-iv).")
    pr("      K_PLAN/K_ROAD > 1 = the model asks for more bend than the road has.  K_ACH/K_CTL = execution.")
    pr("      %-5s %-9s %7s %6s | %-22s %-22s %-22s" % (
        "route", "v m/s", "secs", "blk", "K_PLAN/K_ROAD planner", "K_CTL/K_PLAN starpilot", "K_ACH/K_CTL exec"))
    for t in TAGS:
        f = frame(t)
        for vlo, vhi in V_BANDS[1:]:
            m = (f["eng"] & f["ll_ok"] & (f["v"] >= vlo) & (f["v"] < vhi)
                 & (np.abs(f["k_road"]) >= 0.0015))
            bl = blocks(m, 10)
            rows = []
            for a, b in bl:
                kr = med(np.abs(f["k_road"][a:b]))
                kp = med(np.abs(f["k_plan"][a:b]))
                kc = med(np.abs(f["k_ctl"][a:b]))
                ka = med(np.abs(f["k_ach"][a:b]))
                if kr > 1e-4 and kp > 1e-4 and kc > 1e-4:
                    rows.append((kp / kr, kc / kp, ka / kc))
            if len(rows) < 4:
                continue
            R = np.array(rows)
            c = []
            for jx in range(3):
                lo, hi = boot(R[:, jx])
                c.append("%6.3f [%5.3f,%5.3f]" % (med(R[:, jx]), lo, hi))
            pr("      %-5s %-9s %7.1f %6d | %-22s %-22s %-22s"
               % (t, "%d-%d" % (vlo, vhi), m.sum() * DT_M, len(R), c[0], c[1], c[2]))
    pr("")


def section2d():
    pr("=" * 170)
    pr("SECTION 2d -- TIME COURSE THROUGH A CURVE.  If the inside bias is EXECUTION (turning in too hard")
    pr("  and then holding), it should GROW from curve entry.  If it is the PLAN's chosen path, PLAN_inside")
    pr("  should already be positive at entry and the car should simply follow it.  t = 0 is the first frame")
    pr("  of a >=3 s engaged block with |k_road| >= 0.0015.  cm, median over blocks.")
    pr("=" * 170)
    TS = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
    for t in TAGS:
        f = prep_plan_offset(t)
        sg = np.sign(f["k_road"])
        plan_ins = f["plan_off_right"] * sg
        car_ins = f["off_right"] * sg
        m = f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0015)
        bl = [(a, b) for a, b in blocks(m, int(3.0 / DT_M))]
        if len(bl) < 4:
            pr("  --- %s: only %d qualifying curve blocks ---" % (t, len(bl)))
            continue
        pr("  --- %s  (%d curve blocks >= 3 s) ---" % (t, len(bl)))
        pr("      %-10s %s" % ("t in curve", " ".join("%8.1f" % x for x in TS)))
        for lab, arr in (("CAR_inside", car_ins), ("PLAN_inside", plan_ins), ("k_road x1e3", f["k_road"] * sg * 1e3)):
            vals = []
            for ts in TS:
                k = int(round(ts / DT_M))
                v = [arr[a + k] for a, b in bl if a + k < b]
                sc = 100.0 if lab != "k_road x1e3" else 1.0
                vals.append(med(np.asarray(v) * sc) if v else np.nan)
            pr("      %-10s %s" % (lab, " ".join("%8.1f" % x for x in vals)))
        pr("")




# ================================================================================================ 6
def section6():
    pr("=" * 170)
    pr("SECTION 6 -- THE THREE DISCRIMINATORS THAT DECIDE PLAN vs EXECUTION.")
    pr("=" * 170)
    pr("  6a  RESTORING INTENT.  If the model merely CORRECTED an over-delivering controller it would still")
    pr("      aim its PATH at the lane centre, so PLAN_inside would sit BELOW CAR_inside (a path bending")
    pr("      back out).  If the model has CHOSEN the inside line, PLAN_inside ~ CAR_inside.  Paired per")
    pr("      block on identical frames.  A value of -X cm means the plan aims X cm further OUT than the")
    pr("      car currently is; 0 means the plan is content to stay exactly where it is.")
    pr("      %-5s %-18s %7s %5s | %11s %16s | %13s %16s" % (
        "route", "|k_road| band", "secs", "blk", "CAR_inside", "95% CI", "PLAN - CAR", "95% CI"))
    for t in TAGS:
        f = prep_plan_offset(t)
        sg = np.sign(f["k_road"])
        d = (f["plan_off_right"] - f["off_right"]) * sg
        for nm, klo, khi in K_BANDS[1:]:
            m = (f["eng"] & f["ll_ok"] & (f["v"] >= 5) & np.isfinite(f["plan_off_right"])
                 & (np.abs(f["k_road"]) >= klo) & (np.abs(f["k_road"]) < khi))
            if m.sum() < 40:
                continue
            b1 = blockmed(m, f["off_right"] * sg * 100.0)
            b2 = blockmed(m, d * 100.0)
            if min(len(b1), len(b2)) < 4:
                continue
            l1, h1 = boot(b1)
            l2, h2 = boot(b2)
            pr("      %-5s %-18s %7.1f %5d | %11.1f %16s | %13.1f %16s"
               % (t, nm, m.sum() * DT_M, len(b1), med(b1), "[%+6.1f,%+6.1f]" % (l1, h1),
                  med(b2), "[%+6.1f,%+6.1f]" % (l2, h2)))
    pr("")
    pr("  6b  CURVATURE RATIOS ON STEADY CURVE FRAMES ONLY (|dk/dx| < 5e-5 per m, i.e. not curve entry or")
    pr("      exit).  SECTION 2c pooled entry transients and biased every ratio low.  Cutting a corner is a")
    pr("      LARGER radius, so K_PLAN/K_ROAD < 1 is the SIGNATURE of corner-cutting, not a contradiction.")
    pr("      %-5s %-9s %7s %5s | %-22s %-22s %-22s" % (
        "route", "v m/s", "secs", "blk", "K_PLAN/K_ROAD planner", "K_CTL/K_PLAN starpilot", "K_ACH/K_CTL exec"))
    for t in TAGS:
        f = frame(t)
        for vlo, vhi in ((5, 14), (14, 40)):
            m = (f["eng"] & f["ll_ok"] & (f["v"] >= vlo) & (f["v"] < vhi)
                 & (np.abs(f["k_road"]) >= 0.0015) & (np.abs(f["k_road_rate"]) < 5e-5))
            rows = []
            for a, b in blocks(m, 10):
                kr = med(np.abs(f["k_road"][a:b]))
                kp = med(np.abs(f["k_plan"][a:b]))
                kc = med(np.abs(f["k_ctl"][a:b]))
                ka = med(np.abs(f["k_ach"][a:b]))
                if kr > 1e-4 and kp > 1e-4 and kc > 1e-4:
                    rows.append((kp / kr, kc / kp, ka / kc))
            if len(rows) < 4:
                continue
            R = np.array(rows)
            c = []
            for jx in range(3):
                lo, hi = boot(R[:, jx])
                c.append("%6.3f [%5.3f,%5.3f]" % (med(R[:, jx]), lo, hi))
            pr("      %-5s %-9s %7.1f %5d | %-22s %-22s %-22s"
               % (t, "%d-%d" % (vlo, vhi), m.sum() * DT_M, len(R), c[0], c[1], c[2]))
    pr("")
    pr("  6c  PRE-ENTRY TIME COURSE.  t = 0 is the first frame of a >= 3 s block with |k_road| >= 0.0015;")
    pr("      NEGATIVE t is the approach, before the road has bent.  If the car is already displaced inward")
    pr("      before the curve, that is TURNING IN EARLY, in metres of lane, not in seconds of phase.")
    pr("      Routes pooled by driving model.  cm (k_road x1e3).")
    for lab, tags in (("rdf43 (r39)", ("r39",)), ("tsfdo (r3c+r3a)", ("r3c", "r3a"))):
        TS = (-3.0, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0)
        acc = {k: {ts: [] for ts in TS} for k in ("CAR_inside", "PLAN_inside", "k_road x1e3")}
        nb = 0
        for t in tags:
            f = prep_plan_offset(t)
            sg = np.sign(f["k_road"])
            m = f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0015)
            for a, b in blocks(m, int(3.0 / DT_M)):
                s0 = sg[a]
                nb += 1
                for ts in TS:
                    k = a + int(round(ts / DT_M))
                    if k < 0 or k >= len(f["t"]) or (ts > 0 and k >= b):
                        continue
                    if not (f["eng"][k] and f["ll_ok"][k]):
                        continue
                    acc["CAR_inside"][ts].append(f["off_right"][k] * s0 * 100.0)
                    acc["PLAN_inside"][ts].append(f["plan_off_right"][k] * s0 * 100.0)
                    acc["k_road x1e3"][ts].append(f["k_road"][k] * s0 * 1e3)
        pr("      --- %s   (%d curve entries) ---" % (lab, nb))
        pr("      %-12s %s" % ("t in curve s", " ".join("%7.1f" % x for x in TS)))
        for k in ("k_road x1e3", "CAR_inside", "PLAN_inside"):
            pr("      %-12s %s" % (k, " ".join("%7.1f" % med(acc[k][ts]) for ts in TS)))
        pr("      %-12s %s" % ("n", " ".join("%7d" % len(acc["CAR_inside"][ts]) for ts in TS)))
    pr("")
    pr("  6d  THE MODEL CONTRAST, pooled: rdf43 (r39) vs tsfdo (r3c + r3a), 9-20 m/s, |k_road| >= 0.0008.")
    pr("      This is the only manipulation in the dataset that can move a PLANNER statistic.")
    pr("      %-16s %7s %5s | %11s %16s | %11s %16s" % (
        "model", "secs", "blk", "CAR_inside", "95% CI", "PLAN_inside", "95% CI"))
    for lab, tags in (("rdf43 (r39)", ("r39",)), ("tsfdo (r3c+r3a)", ("r3c", "r3a"))):
        b1, b2, secs = [], [], 0.0
        for t in tags:
            f = prep_plan_offset(t)
            sg = np.sign(f["k_road"])
            m = (f["eng"] & f["ll_ok"] & (f["v"] >= 9) & (f["v"] < 20)
                 & (np.abs(f["k_road"]) >= 0.0008) & np.isfinite(f["plan_off_right"]))
            b1 += blockmed(m, f["off_right"] * sg * 100.0)
            b2 += blockmed(m, f["plan_off_right"] * sg * 100.0)
            secs += m.sum() * DT_M
        l1, h1 = boot(b1)
        l2, h2 = boot(b2)
        pr("      %-16s %7.1f %5d | %11.1f %16s | %11.1f %16s"
           % (lab, secs, len(b1), med(b1), "[%+6.1f,%+6.1f]" % (l1, h1),
              med(b2), "[%+6.1f,%+6.1f]" % (l2, h2)))
    pr("")
    pr("  6e  THE LANE-CENTERING CORRECTION'S OWN ERROR SIGNAL, and how often the e2e break-in kills it.")
    pr("      error = lane_centre_y(L) - path_y(L) = -plan_off_right;  the correction is faded to ZERO for")
    pr("      |error| >= 0.50 m (break-in ends at 0.50 with e2e_authority = 1.0), i.e. exactly where the")
    pr("      offset is largest.  Engaged, lane-lines valid, |k_road| >= 0.0008, v >= 5.")
    pr("      %-5s %8s %11s %11s %11s %11s" % (
        "route", "secs", "med |err| m", "p75 |err|", "frac >=0.50", "frac <=0.08"))
    for t in TAGS:
        f = prep_plan_offset(t)
        m = (f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0008)
             & np.isfinite(f["plan_off_right"]))
        e = np.abs(f["plan_off_right"][m])
        pr("      %-5s %8.1f %11.3f %11.3f %11.3f %11.3f"
           % (t, m.sum() * DT_M, float(np.median(e)), float(np.percentile(e, 75)),
              float(np.mean(e >= 0.50)), float(np.mean(e <= 0.08))))
    pr("")




# ================================================================================================ 7
def section7():
    pr("=" * 170)
    pr("SECTION 7 -- ROBUSTNESS, ENTRY OVERSHOOT, AND THE ONE REACHABLE LEVER.")
    pr("=" * 170)
    pr("  7a  ROBUSTNESS of the inside offset to the perception gate.  If the offset were a lane-line")
    pr("      artefact it should shrink under a tighter confidence gate.  BASE = probs > 0.5, std < 0.5,")
    pr("      width 2.6-4.8 m.  TIGHT = probs > 0.90, std < 0.20, width 3.2-3.9 m.  |k_road| >= 0.0008, v >= 5.")
    pr("      %-5s %-7s %8s %5s | %11s %16s" % ("route", "gate", "secs", "blk", "CAR_inside", "95% CI cm"))
    for t in TAGS:
        f = frame(t)
        sg = np.sign(f["k_road"])
        base = f["eng"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0008) & (f["lcs"] < 0.5)
        tight = (base & (f["llprob"][:, 1] > 0.90) & (f["llprob"][:, 2] > 0.90)
                 & (f["llstd"][:, 1] < 0.20) & (f["llstd"][:, 2] < 0.20)
                 & (f["lane_w"] > 3.2) & (f["lane_w"] < 3.9))
        for lab, m in (("BASE", base & f["ll_ok"]), ("TIGHT", tight)):
            b = blockmed(m, f["off_right"] * sg * 100.0)
            if len(b) < 4:
                pr("      %-5s %-7s %8.1f %5d | %11s" % (t, lab, m.sum() * DT_M, len(b), "too few blocks"))
                continue
            lo, hi = boot(b)
            pr("      %-5s %-7s %8.1f %5d | %11.1f %16s"
               % (t, lab, m.sum() * DT_M, len(b), med(b), "[%+6.1f,%+6.1f]" % (lo, hi)))
    pr("")
    pr("  7b  ENTRY OVERSHOOT vs the ROAD (not vs the setpoint).  Per curve entry, the PEAK of")
    pr("      K_ACH/K_ROAD in the first 2 s and the STEADY value from 2 s on.  > 1 means the car bends")
    pr("      harder than the lane centre line does.  This is the transient the operator feels as")
    pr("      'turn too much'; the standing inside offset in SECTION 2 is a different, larger thing.")
    pr("      %-5s %6s | %10s %16s | %10s %16s" % ("route", "n", "peak 0-2s", "95% CI", "steady 2s+", "95% CI"))
    for t in TAGS:
        f = frame(t)
        m = f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0015)
        pk, st = [], []
        for a, b in blocks(m, int(3.0 / DT_M)):
            w = slice(a, min(b, a + int(2.0 / DT_M)))
            r = f["k_ach"][w] / np.where(np.abs(f["k_road"][w]) > 1e-4, f["k_road"][w], np.nan)
            r = r[np.isfinite(r)]
            if r.size:
                pk.append(float(np.max(r)))
            w2 = slice(min(b, a + int(2.0 / DT_M)), b)
            r2 = f["k_ach"][w2] / np.where(np.abs(f["k_road"][w2]) > 1e-4, f["k_road"][w2], np.nan)
            r2 = r2[np.isfinite(r2)]
            if r2.size:
                st.append(float(np.median(r2)))
        if len(pk) < 4:
            pr("      %-5s %6d | %10s" % (t, len(pk), "too few curve entries"))
            continue
        l1, h1 = boot(pk)
        l2, h2 = boot(st)
        pr("      %-5s %6d | %10.3f %16s | %10.3f %16s"
           % (t, len(pk), med(pk), "[%.3f,%.3f]" % (l1, h1), med(st), "[%.3f,%.3f]" % (l2, h2)))
    pr("")
    pr("  7c  THE e2e BREAK-IN FADE, evaluated frame by frame exactly as lane_centering.py:144-149 does")
    pr("      with e2e_authority = 1.0:   kept = 1 - clip((|err| - 0.15)/0.35, 0, 1).")
    pr("      kept = 1.00 means the lane-centering correction acts in full; 0.00 means it is switched off.")
    pr("      %-5s %8s %10s %10s %10s %10s" % ("route", "secs", "med kept", "mean kept", "frac kept=0", "frac kept=1"))
    for t in TAGS:
        f = prep_plan_offset(t)
        m = (f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0008)
             & np.isfinite(f["plan_off_right"]))
        e = np.abs(f["plan_off_right"][m])
        kept = 1.0 - np.clip((e - 0.15) / 0.35, 0.0, 1.0)
        pr("      %-5s %8.1f %10.3f %10.3f %10.3f %10.3f"
           % (t, m.sum() * DT_M, float(np.median(kept)), float(np.mean(kept)),
              float(np.mean(kept <= 1e-9)), float(np.mean(kept >= 1 - 1e-9))))
    pr("")
    pr("  7d  SIZE of the correction the fork WOULD apply with the break-in removed (e2e_authority = 0),")
    pr("      against the road curvature it has to work against.  corr = clip(2*err/L^2, +-0.004)*0.30,")
    pr("      L = clip(v, 8, 35).  Deadband 0.08 m applied.  Reported signed so + = steers OUT of the bend.")
    pr("      %-5s %8s %13s %13s %13s %13s" % ("route", "secs", "corr NOW 1/m", "corr e2e=0", "med |k_road|",
                                               "e2e=0 / k_road"))
    for t in TAGS:
        f = prep_plan_offset(t)
        m = (f["eng"] & f["ll_ok"] & (f["v"] >= 5) & (np.abs(f["k_road"]) >= 0.0008)
             & np.isfinite(f["plan_off_right"]))
        err = -f["plan_off_right"][m]                     # lane_centering.py:132, right-positive
        L = f["look_d"][m]
        ea = np.abs(err)
        err_db = np.where(ea <= 0.08, 0.0, np.copysign(ea - 0.08, err))
        keep = 1.0 - np.clip((ea - 0.15) / 0.35, 0.0, 1.0)
        c_now = np.clip(2.0 * (err_db * keep) / L ** 2, -0.004, 0.004) * 0.30
        c_off = np.clip(2.0 * err_db / L ** 2, -0.004, 0.004) * 0.30
        sg = np.sign(f["k_road"][m])
        kr = med(np.abs(f["k_road"][m]))
        pr("      %-5s %8.1f %13.6f %13.6f %13.6f %13.3f"
           % (t, m.sum() * DT_M, med(-c_now * sg), med(-c_off * sg), kr, abs(med(-c_off * sg)) / kr))
    pr("")


def main():
    sectionV()
    section1()
    section1b()
    section2()
    section2d()
    section6()
    section7()
    section3()
    section5()
    with open(os.path.join(SCR, "plan_vs_execution_out.txt"), "w", encoding="utf-8") as fh:
        fh.write(chr(10).join(LINES) + chr(10))


if __name__ == "__main__":
    main()
