# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v282_r39.py -- THE OUTER-LOOP READ OF r39 (V282, SteerKP 0.8 +
the variable-ratio SteerRatio MAP), against r35 (V281 rev 3, SteerKP 0.6, SR 12.5 fixed) and r34.

Operator on r39, verbatim: "various grinding moments ... worst-case over-steer on turn at 20+ mph;
general over-steer on curves at medium and at high speed; solid, stable lane keep on straights;
amazing authority".  He has ruled the over-steer an OUTER-LOOP (openpilot) responsibility.

Instruments and strata are REUSED from oversteer_v283.py / curve_oversteer_r34.py / v281r3_read_r35.py
verbatim where they exist -- same curve definition, same entry/steady windows, same bias correction,
same SR-free achieved instrument (livePose yaw_cal * v, roll removed).

Sections
  A  the tune AS RUN, and the SR TRAP: which steering ratio did VM.calc_curvature actually use?
     (memory accord-liveparameters-steerratio-is-published-upstream-of-the-accord-scale)
  B  Q1 THE DISCRIMINATOR -- equilibrium error vs transient overshoot (dwell trajectory, fixed cohort)
  C  Q2 the "20+ mph worst case" -- what actually distinguishes those episodes
  D  Q3 the outer integrator's state and headroom; f/p/i decomposition
  E  Q5 achieved / asked in the tight-curve stratum, r35 vs r39, computed identically
  F  Q4 the gain arithmetic behind the tune recommendation (low_speed_factor is the crux)

Run: python rlog-tools/studies/osc-highangle/oversteer_v282_r39.py
Needs analysis-2020accord/studies/optune/_scratch/r3{4,5,9}_backcalc.npz
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import backcalc_laf_friction as B  # noqa: E402
import highangle_stutter as H  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
G = 9.81
DES_THR = 0.3                      # curve_oversteer_r34.DES_THR
TAGS = ("r34", "r35", "r39")
# the tune AS SET on each drive (toggle backups; r39 = toggle-backup_V282_20260904)
TUNE = {"r34": dict(kp=0.6, laf=2.11, fric=0.03, sr="12.5->16.1 fixed", note="V280r2"),
        "r35": dict(kp=0.6, laf=2.11, fric=0.03, sr="12.5 fixed", note="V281r3"),
        "r39": dict(kp=0.8, laf=2.11, fric=0.03, sr="MAP", note="V282")}
# StarPilot HEAD (commit 8a28dcef8, the commit r39 RAN -- read from initData)
ANGLE_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
RATIO_V = [16.00, 16.00, 15.02, 14.52, 13.97, 13.75, 13.50, 12.81, 11.67, 11.06]
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
MIN_SPEED = 1.0                    # latcontrol_torque MIN_SPEED
ANG_BINS = ((0, 20), (20, 50), (50, 120), (120, 1e9))
V_BINS = ((0, 10), (10, 20), (20, 30), (30, 1e9))
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def q(x, p):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, p)) if len(x) else np.nan


def merge_runs(mask, minlen, gap):
    """curve_oversteer_r34.merge_runs, verbatim."""
    runs = H.runs_of(mask, 1)
    out = []
    for a, b in runs:
        if out and a - out[-1][1] < gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= minlen]


def tls(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 20:
        return np.nan
    sxx, syy, sxy = float(x @ x), float(y @ y), float(x @ y)
    return float((syy - sxx + np.hypot(syy - sxx, 2 * sxy)) / (2 * sxy)) if sxy != 0 else np.nan


def boot_ci(vals, n=4000, seed=7):
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    if len(v) < 4:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    s = np.median(v[rng.integers(0, len(v), size=(n, len(v)))], axis=1)
    return (float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5)))


GRIDS, CPS = {}, {}


def gof(tag):
    if tag not in GRIDS:
        D = B.load(tag)
        g = B.grid(D)
        cp = D["cp"]
        # the vehicle model exactly as openpilot runs it (chi = steerRatioRear = 0, stiffness pinned 1.0
        # by ForceAutoTuneOff) -- straight_understeer_sr.py's derivation, same constants
        m_, L, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
        aR = L - aF
        cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
        sf = m_ * (cF * aF - cR * aR) / (L ** 2 * cF * cR)
        v = g["v"]
        g["cfac"] = 1.0 / (1.0 - sf * v ** 2) / L
        g["rollcomp"] = (G * g["proll"]) / ((1.0 / sf) - v ** 2)
        g["sa_deg"] = g["ang"] - g["aoff"]
        g["sa"] = np.radians(g["sa_deg"])
        g["sr_map"] = np.interp(np.abs(g["sa_deg"]), ANGLE_BP, RATIO_V)
        g["lpar_sr"] = np.interp(g["t"], D["lpar_t"] - D["co_t"][0], D["lpar_sr"])
        # B.grid does not carry ctl_saturated; add it with the same zero-order hold
        g["saturated"] = B.hold(D["ctl_t"] - D["co_t"][0], D["ctl_saturated"], g["t"])
        g["errorRate"] = B.hold(D["ctl_t"] - D["co_t"][0], D["ctl_errorRate"], g["t"])
        g["lsf"] = (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2
        g["vyaw"] = v * g["yaw_cal"]                     # SR-FREE achieved lat accel, no roll term
        g["pose"] = g["lat_torqued"]                     # SR-FREE, roll removed (torqued's own)
        GRIDS[tag], CPS[tag] = g, cp
    return GRIDS[tag], CPS[tag]


def curve_mask(g):
    """curve_oversteer_r34: latActive & torque controller active & not pressed & |des| > 0.3."""
    return (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(g["desiredLateralAccel"])


def straight_bias(g):
    """The road-crown + instrument offset that direction-folding only cancels if L/R balance."""
    ok = curve_mask(g)
    st = ok & (np.abs(g["desiredLateralAccel"]) < 0.2) & (g["v"] > 10)
    return dict(pose=med(g["pose"][st] - g["desiredLateralAccel"][st]),
                vyaw=med(g["vyaw"][st] - g["desiredLateralAccel"][st]),
                m=med(g["actualLateralAccel"][st] - g["desiredLateralAccel"][st]),
                secs=float(st.sum() / FS))


# ================================================================================================ A
def sectionA():
    pr("=" * 178)
    pr("SECTION A -- THE TUNE AS RUN, AND THE STEERING-RATIO TRAP")
    pr("  The achieved side of every ratio below is SR-FREE (livePose yaw_cal * v), and desiredLateralAccel is planner")
    pr("  curvature * v^2, also SR-FREE.  SR still decides what the CONTROLLER thinks it measured, so it must be pinned.")
    pr("  TEST (memory accord-liveparameters-steerratio-is-published-upstream-of-the-accord-scale): reconstruct")
    pr("  measurement = -(cfac(v)*sa/sR + rollcomp(roll,v)) * v^2 under each candidate sR and TLS it on the LOGGED")
    pr("  torqueState.actualLateralAccel.  Slope 1.000 identifies the ratio VM.calc_curvature actually ran.")
    pr("=" * 178)
    out = {}
    pr("  %-5s %-22s %8s %8s %8s %8s | %10s %10s %10s %10s" % (
        "route", "build / tune", "lparSR", "kp(wire)", "LAF", "fric", "sR=lparSR", "sR=MAP", "sR=.857lp", "sR=12.5"))
    for tag in TAGS:
        g, cp = gof(tag)
        o = B.live_values(g)
        base = curve_mask(g) & (np.abs(g["sa_deg"]) > 1.5) & (g["v"] > 5) & np.isfinite(g["actualLateralAccel"])
        y = g["actualLateralAccel"][base]
        cands = {}
        for nm, sr in (("lpar", g["lpar_sr"]), ("map", g["sr_map"]),
                       ("857", 0.857 * g["lpar_sr"]), ("125", np.full(len(g["t"]), 12.5))):
            rec = -(g["cfac"] * g["sa"] / sr + g["rollcomp"]) * g["v"] ** 2
            cands[nm] = tls(rec[base], y)
        row = dict(lpar=med(g["lpar_sr"]), kp=o.get("kp_p50", np.nan), laf=o.get("LAF_from_pid_p50", np.nan),
                   fric=o.get("friction_from_f", np.nan), n=int(base.sum()), **{"tls_" + k: v for k, v in cands.items()})
        out[tag] = row
        pr("  %-5s %-22s %8.2f %8.3f %8.3f %8.3f | %10.4f %10.4f %10.4f %10.4f" % (
            tag, "%s / %s" % (TUNE[tag]["note"], TUNE[tag]["sr"]), row["lpar"], row["kp"], row["laf"], row["fric"],
            cands["lpar"], cands["map"], cands["857"], cands["125"]))
    pr("  (slope 1.000 = that ratio reproduces the logged measurement; r34/r35 are the known-good controls -- both fixed-SR routes)")

    # the SR-free true ratio, and the map's own shape, measured
    pr()
    pr("  sR_true, MEASURED SR-FREE (straight_understeer_sr.py's inversion: sR_true = cfac*sa / (-yaw_cal/v - rollcomp)),")
    pr("  TLS through the origin, engaged / not pressed / v > 15 / |steeringRate| < 10 deg/s, by |sa| stratum:")
    pr("  %-5s %10s %12s %12s %12s %12s %10s" % ("route", "sR_param", "sR_true all", "|sa|1.5-5", "5-15", ">15", "n(s)"))
    for tag in TAGS:
        g, cp = gof(tag)
        curv_road = -g["yaw_cal"] / np.maximum(g["v"], 1e-3)
        denom = curv_road - g["rollcomp"]
        j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
        ok = (curve_mask(g) & (g["v"] > 15.0) & g["lp_calok"][j] & (np.abs(g["rate"]) < 10.0)
              & (np.abs(g["sa_deg"]) > 1.5) & np.isfinite(denom))
        yv = g["cfac"] * g["sa"]
        cells = [tls(denom[ok], yv[ok])]
        for lo, hi in ((1.5, 5.0), (5.0, 15.0), (15.0, 999.0)):
            s = ok & (np.abs(g["sa_deg"]) >= lo) & (np.abs(g["sa_deg"]) < hi)
            cells.append(tls(denom[s], yv[s]))
        pr("  %-5s %10s %12.2f %12.2f %12.2f %12.2f %10.0f" % (
            tag, TUNE[tag]["sr"], cells[0], cells[1], cells[2], cells[3], ok.sum() / FS))
        out[tag]["sr_true"] = cells[0]
        out[tag]["sr_true_bins"] = cells[1:]
    pr("  ('SR-free' here means the ROAD side carries no steering ratio.  sR_true absorbs tyre-model error via cfac --")
    pr("   the EFFECTIVE ratio, not the geometric one; the memory records the two differ by ~1.04.)")

    pr()
    pr("  STRAIGHT-ROAD REFERENCE (|des|<0.2, v>10) -- the crown/instrument bias subtracted everywhere below:")
    for tag in TAGS:
        sb = straight_bias(gof(tag)[0])
        pr("    %-5s pose %+.3f  vyaw %+.3f  m(controller) %+.3f   [%.0f s]" % (tag, sb["pose"], sb["vyaw"], sb["m"], sb["secs"]))
        out[tag]["bias"] = sb
    return out


# ================================================================================================ B
def curves(tag):
    g, cp = gof(tag)
    des = g["desiredLateralAccel"]
    ok = curve_mask(g)
    runs = merge_runs(ok & (np.abs(des) > DES_THR), int(1.5 * FS), int(0.3 * FS))
    sb = straight_bias(g)
    rows = []
    for a, b in runs:
        d = np.sign(np.median(des[a:b])) or 1.0
        sl_e = slice(a, a + int(1.0 * FS))
        sl_s = slice(a + int(1.5 * FS), b) if b - a >= int(2.5 * FS) else None
        r = dict(tag=tag, a=int(a), b=int(b), t0=float(g["t"][a]), dur=float((b - a) / FS), dir=int(d),
                 v=med(g["v"][a:b]), v_max=float(g["v"][a:b].max()), ang=med(np.abs(g["ang"][a:b])),
                 ang_max=float(np.abs(g["ang"][a:b]).max()), des=med(np.abs(des[a:b])),
                 des_max=float(np.abs(des[a:b]).max()), lsf=med(g["lsf"][a:b]))
        for nm, sl in (("entry", sl_e), ("steady", sl_s)):
            if sl is None:
                for k in ("os_vyaw", "os_pose", "os_m", "R_vyaw", "R_pose", "f", "p", "i", "out"):
                    r[nm + "_" + k] = np.nan
                continue
            r[nm + "_os_vyaw"] = med((g["vyaw"][sl] - des[sl]) * d) - sb["vyaw"] * d * 0 + 0
            # bias correction is applied in the DIRECTION-FOLDED frame: subtract the folded bias
            r[nm + "_os_vyaw"] = med((g["vyaw"][sl] - des[sl]) * d - sb["vyaw"] * d)
            r[nm + "_os_pose"] = med((g["pose"][sl] - des[sl]) * d - sb["pose"] * d)
            r[nm + "_os_m"] = med((g["actualLateralAccel"][sl] - des[sl]) * d - sb["m"] * d)
            big = np.abs(des[sl]) > 0.5
            r[nm + "_R_vyaw"] = med((g["vyaw"][sl][big] - sb["vyaw"]) / des[sl][big]) if big.sum() > 10 else np.nan
            r[nm + "_R_pose"] = med((g["pose"][sl][big] - sb["pose"]) / des[sl][big]) if big.sum() > 10 else np.nan
            r[nm + "_f"] = med(g["f"][sl] * d); r[nm + "_p"] = med(g["p"][sl] * d); r[nm + "_i"] = med(g["i"][sl] * d)
            r[nm + "_out"] = med(g["output"][sl] * d)
        # transient signature: the PEAK of the folded overshoot in the first 2 s, vs the steady value
        w = slice(a, min(b, a + int(2.0 * FS)))
        os_t = (g["vyaw"][w] - des[w]) * d - sb["vyaw"] * d
        r["peak_os_vyaw"] = float(np.nanmax(os_t)) if np.isfinite(os_t).any() else np.nan
        r["t_peak"] = float(np.nanargmax(os_t) / FS) if np.isfinite(os_t).any() else np.nan
        r["overshoot_frac"] = r["peak_os_vyaw"] - r["steady_os_vyaw"]
        ii = g["i"][a:b] * d
        r["i_end"] = float(ii[-1]); r["i_exc"] = float(np.nanmax(np.abs(ii - ii[0])))
        r["sat"] = float(np.mean(g["saturated"][a:b] > 0.5))
        rows.append(r)
    return rows, runs


def sectionB(A):
    pr("\n" + "=" * 178)
    pr("SECTION B -- Q1 THE DISCRIMINATOR: EQUILIBRIUM ERROR or TRANSIENT OVERSHOOT?")
    pr("  Curve = latActive & torque-controller active & not steeringPressed & |desiredLateralAccel| > 0.3, runs >= 1.5 s,")
    pr("  gaps < 0.3 s merged (curve_oversteer_r34, verbatim).  ENTRY = first 1.0 s, STEADY = 1.5 s -> end.")
    pr("  ACHIEVED is SR-FREE: vyaw = livePose yaw_cal * v ; pose = vyaw - g*sin(roll_device).  ASKED = desiredLateralAccel.")
    pr("  + = MORE lateral accel than asked.  All numbers bias-corrected by that route's own straight-road reference.")
    pr("=" * 178)
    C = {t: curves(t)[0] for t in TAGS}
    pr("  %-5s %6s %8s | %9s %9s %9s | %9s %9s | %9s %9s %9s | %8s" % (
        "route", "curves", "secs", "ENTRYos_vy", "STEADYvy", "STEADYpose", "R_vyaw", "R_pose", "peak-steady", "t_peak(s)",
        "frac over", "sat"))
    for t in TAGS:
        rows = C[t]
        pr("  %-5s %6d %8.0f | %+9.3f %+9.3f %+9.3f | %9.3f %9.3f | %+9.3f %9.2f %9.2f | %8.3f" % (
            t, len(rows), sum(r["dur"] for r in rows),
            med([r["entry_os_vyaw"] for r in rows]), med([r["steady_os_vyaw"] for r in rows]),
            med([r["steady_os_pose"] for r in rows]), med([r["steady_R_vyaw"] for r in rows]),
            med([r["steady_R_pose"] for r in rows]), med([r["overshoot_frac"] for r in rows]),
            med([r["t_peak"] for r in rows]), float(np.mean([r["steady_os_vyaw"] > 0 for r in rows if np.isfinite(r["steady_os_vyaw"])])),
            med([r["sat"] for r in rows])))
    lo, hi = boot_ci([r["steady_os_vyaw"] for r in C["r39"]])
    lo5, hi5 = boot_ci([r["steady_os_vyaw"] for r in C["r35"]])
    pr("  bootstrap 95%% CI on the median steady os_vyaw (curve as the unit): r39 [%+.3f, %+.3f]  r35 [%+.3f, %+.3f]" % (lo, hi, lo5, hi5))

    pr()
    pr("  B.1 THE DWELL TRAJECTORY -- FIXED COHORT (only curves surviving to 5.0 s, so the same curves are in every column).")
    pr("      If this is a TRANSIENT it peaks early and decays toward R = 1.  If it is an EQUILIBRIUM error it is flat.")
    TT = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
    traj = {}
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        rows = [r for r in C[t] if r["dur"] >= 5.0]
        cols_os, cols_R = [], []
        for tt in TT:
            k = int(tt * FS); vo, vr = [], []
            for r in rows:
                j = r["a"] + k
                if j >= r["b"]:
                    continue
                d = r["dir"]
                vo.append((g["vyaw"][j] - des[j]) * d - sb["vyaw"] * d)
                if abs(des[j]) > 0.4:
                    vr.append((g["vyaw"][j] - sb["vyaw"]) / des[j])
            cols_os.append(np.nanmean(vo) if vo else np.nan)
            cols_R.append(np.nanmedian(vr) if len(vr) > 3 else np.nan)
        traj[t] = dict(os=cols_os, R=cols_R, n=len(rows))
        pr("      %-5s n=%2d  os_vyaw  " % (t, len(rows)) + " ".join("%+7.3f" % x for x in cols_os))
        pr("      %-5s        R=ach/ask" % "" + " ".join("%7.3f" % x for x in cols_R))
    pr("      t (s)              " + " ".join("%7.2f" % x for x in TT))

    pr()
    pr("  B.2 QUASI-STATIC vs TRANSIENT frames (oversteer_v283 section 9.3's definition, verbatim):")
    pr("      quasi-static = >= 1.0 s into the curve AND |d(des)/dt| < 0.20 m/s^3 ; transient = first 1.0 s OR |d(des)/dt| >= 0.50")
    pr("      %-5s %26s %26s" % ("route", "quasi-static os_vyaw (frac>0)", "transient os_vyaw (frac>0)"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        dd = np.r_[0.0, np.diff(des)] * FS
        into = np.zeros(len(des)); dirf = np.zeros(len(des)); inc = np.zeros(len(des), bool)
        for r in C[t]:
            a, b = r["a"], r["b"]
            into[a:b] = np.arange(b - a) / FS; dirf[a:b] = r["dir"]; inc[a:b] = True
        os_f = (g["vyaw"] - des) * dirf - sb["vyaw"] * dirf
        qs = inc & (into >= 1.0) & (np.abs(dd) < 0.20)
        tr = inc & ((into < 1.0) | (np.abs(dd) >= 0.50))
        pr("      %-5s %14.3f (%5.2f)      %14.3f (%5.2f)" % (
            t, med(os_f[qs]), float(np.mean(os_f[qs] > 0)), med(os_f[tr]), float(np.mean(os_f[tr] > 0))))

    pr()
    pr("  B.3 STRATIFIED steady overshoot (frame-pooled, direction-folded, bias-corrected):")
    pr("      %-5s %-10s %8s %10s %10s %10s %8s %8s" % ("route", "stratum", "secs", "os_vyaw", "os_pose", "R_vyaw", "|des|", "v"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        stm = np.zeros(len(des), bool); dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True; dirf[r["a"]:r["b"]] = r["dir"]
        strata = ([("v %g-%g" % (a_, b_), (g["v"] >= a_) & (g["v"] < b_)) for a_, b_ in V_BINS] +
                  [("ang %g-%g" % (a_, b_), (np.abs(g["ang"]) >= a_) & (np.abs(g["ang"]) < b_)) for a_, b_ in ANG_BINS] +
                  [("des %g-%g" % (a_, b_), (np.abs(des) >= a_) & (np.abs(des) < b_)) for a_, b_ in ((0.3, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 9.0))])
        for nm, sel0 in strata:
            sel = stm & sel0
            if sel.sum() < 50:
                continue
            d = dirf[sel]; big = np.abs(des[sel]) > 0.5
            pr("      %-5s %-10s %8.0f %+10.3f %+10.3f %10.3f %8.2f %8.1f" % (
                t, nm, sel.sum() / FS, med((g["vyaw"][sel] - des[sel]) * d - sb["vyaw"] * d),
                med((g["pose"][sel] - des[sel]) * d - sb["pose"] * d),
                med((g["vyaw"][sel][big] - sb["vyaw"]) / des[sel][big]) if big.sum() > 20 else np.nan,
                med(np.abs(des[sel])), med(g["v"][sel])))
    return C, traj


# ================================================================================================ C
def sectionC(C):
    pr("\n" + "=" * 178)
    pr("SECTION C -- Q2 THE '20+ mph WORST CASE'.  What distinguishes the episodes he felt?")
    pr("  The SR map gives ~16.0 only below 48 deg and falls to 13.5 by 191 deg, so a pure-map story predicts the worst")
    pr("  excess NEAR CENTRE.  SteerKP is ALSO not the obvious culprit at 9 m/s -- see section F: low_speed_factor makes")
    pr("  the P term kp*e + lsf*e, so 0.6 -> 0.8 is +10 % of P at 9 m/s and +30 % at 25 m/s.")
    pr("=" * 178)
    rows = sorted([r for r in C["r39"] if np.isfinite(r["steady_os_vyaw"])], key=lambda r: -r["steady_os_vyaw"])
    pr("  r39, the 15 curves with the LARGEST steady over-delivery (bias-corrected, SR-free):")
    pr("    %8s %6s %4s %6s %6s %7s %6s %6s | %8s %8s %8s %7s | %7s %7s %7s %6s" % (
        "t0(s)", "dur", "dir", "v", "v_max", "|ang|", "angmx", "|des|", "entry_os", "steady", "R_vyaw", "pk-st",
        "f", "p", "i", "sat"))
    for r in rows[:15]:
        pr("    %8.1f %6.1f %+4d %6.1f %6.1f %7.0f %6.0f %6.2f | %+8.3f %+8.3f %8.3f %+7.3f | %+7.3f %+7.3f %+7.3f %6.2f" % (
            r["t0"], r["dur"], r["dir"], r["v"], r["v_max"], r["ang"], r["ang_max"], r["des"],
            r["entry_os_vyaw"], r["steady_os_vyaw"], r["steady_R_vyaw"], r["overshoot_frac"],
            r["steady_f"], r["steady_p"], r["steady_i"], r["sat"]))
    pr("  and the 8 MOST under-delivering, for contrast:")
    for r in rows[-8:]:
        pr("    %8.1f %6.1f %+4d %6.1f %6.1f %7.0f %6.0f %6.2f | %+8.3f %+8.3f %8.3f %+7.3f | %+7.3f %+7.3f %+7.3f %6.2f" % (
            r["t0"], r["dur"], r["dir"], r["v"], r["v_max"], r["ang"], r["ang_max"], r["des"],
            r["entry_os_vyaw"], r["steady_os_vyaw"], r["steady_R_vyaw"], r["overshoot_frac"],
            r["steady_f"], r["steady_p"], r["steady_i"], r["sat"]))

    pr()
    pr("  C.1 WHAT PREDICTS THE OVERSTEER?  Rank correlation of the per-curve steady os_vyaw against each candidate axis")
    pr("      (Spearman rho over r39's curves; r35's shown as the control):")
    axes = ("v", "ang", "ang_max", "des", "des_max", "lsf", "dur", "steady_i", "steady_f", "steady_p")
    pr("      %-12s %10s %10s" % ("axis", "r39 rho", "r35 rho"))
    for ax in axes:
        cells = []
        for t in ("r39", "r35"):
            xs = np.array([r[ax] for r in C[t]], float)
            ys = np.array([r["steady_os_vyaw"] for r in C[t]], float)
            ok = np.isfinite(xs) & np.isfinite(ys)
            if ok.sum() < 6:
                cells.append(np.nan); continue
            rx = np.argsort(np.argsort(xs[ok])); ry = np.argsort(np.argsort(ys[ok]))
            cells.append(float(np.corrcoef(rx, ry)[0, 1]))
        pr("      %-12s %10.3f %10.3f" % (ax, cells[0], cells[1]))

    pr()
    pr("  C.2 THE SPEED x ANGLE CELL -- steady os_vyaw, frame-pooled, r39 (and the map's ratio in that |angle| cell):")
    g, _ = gof("r39")
    des = g["desiredLateralAccel"]; sb = straight_bias(g)
    stm = np.zeros(len(des), bool); dirf = np.zeros(len(des))
    for r in C["r39"]:
        stm[r["a"] + 150:r["b"]] = True; dirf[r["a"]:r["b"]] = r["dir"]
    pr("      %-12s" % "v \\ |ang|" + "".join("%18s" % ("%g-%s deg" % (a_, "inf" if b_ > 1e8 else "%g" % b_)) for a_, b_ in ANG_BINS))
    for va, vb in V_BINS:
        cells = []
        for aa, ab in ANG_BINS:
            sel = stm & (g["v"] >= va) & (g["v"] < vb) & (np.abs(g["ang"]) >= aa) & (np.abs(g["ang"]) < ab)
            if sel.sum() < 50:
                cells.append("%18s" % "--"); continue
            d = dirf[sel]
            cells.append("%18s" % ("%+.3f [%3.0fs SR%.1f]" % (
                med((g["vyaw"][sel] - des[sel]) * d - sb["vyaw"] * d), sel.sum() / FS, med(g["sr_map"][sel]))))
        pr("      %-12s" % ("%g-%s m/s" % (va, "inf" if vb > 1e8 else "%g" % vb)) + "".join(cells))
    pr("      (SRx.x = the median ratio the MAP served in that cell.  r35 served a flat 12.5 everywhere.)")

    pr()
    pr("  C.3 THE 20 mph BAND ISOLATED (7-11 m/s = 16-25 mph), steady frames, r39 vs r35 vs r34:")
    pr("      %-5s %8s %10s %10s %10s %9s %9s %9s %9s %9s" % ("route", "secs", "os_vyaw", "os_pose", "R_vyaw", "|des|", "|ang|", "f", "p", "i"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        stm = np.zeros(len(des), bool); dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True; dirf[r["a"]:r["b"]] = r["dir"]
        sel = stm & (g["v"] >= 7) & (g["v"] < 11)
        if sel.sum() < 50:
            pr("      %-5s %8.0f  (too few frames)" % (t, sel.sum() / FS)); continue
        d = dirf[sel]; big = np.abs(des[sel]) > 0.5
        pr("      %-5s %8.0f %+10.3f %+10.3f %10.3f %9.2f %9.0f %+9.3f %+9.3f %+9.3f" % (
            t, sel.sum() / FS, med((g["vyaw"][sel] - des[sel]) * d - sb["vyaw"] * d),
            med((g["pose"][sel] - des[sel]) * d - sb["pose"] * d),
            med((g["vyaw"][sel][big] - sb["vyaw"]) / des[sel][big]) if big.sum() > 20 else np.nan,
            med(np.abs(des[sel])), med(np.abs(g["ang"][sel])),
            med(g["f"][sel] * d), med(g["p"][sel] * d), med(g["i"][sel] * d)))


# ================================================================================================ D
def sectionD(C):
    pr("\n" + "=" * 178)
    pr("SECTION D -- Q3 THE OUTER INTEGRATOR: state, headroom, and the f/p/i decomposition")
    pr("  PIDController limits are +- latAccelFactor (2.110 on all three routes), so |i| <= 2.110 by construction.")
    pr("  i is in LATERAL-ACCELERATION units; output_torque = output_lataccel / latAccelFactor.")
    pr("=" * 178)
    pr("  %-5s %10s %9s %9s %9s %9s %9s | %11s %11s %11s | %10s" % (
        "route", "engaged s", "max|i|", "p99|i|", "p90|i|", "p50|i|", "bound", "med i*sgn(f)", "frac i vs f",
        "med |out|", "saturated"))
    for t in TAGS:
        g, _ = gof(t)
        ok = curve_mask(g)
        i_ = g["i"][ok]; f_ = g["f"][ok]
        laf = TUNE[t]["laf"]
        pr("  %-5s %10.0f %9.3f %9.3f %9.3f %9.3f %9.3f | %+11.3f %11.3f %11.3f | %10.4f" % (
            t, ok.sum() / FS, float(np.nanmax(np.abs(i_))), q(np.abs(i_), 99), q(np.abs(i_), 90), q(np.abs(i_), 50), laf,
            med(i_ * np.sign(f_)), float(np.mean((np.sign(i_) == -np.sign(f_)) & (np.abs(f_) > 0.05))),
            med(np.abs(g["output"][ok])), float(np.mean(g["saturated"][ok] > 0.5))))
    pr()
    pr("  D.1 f / p / i in the CURVE STEADY stratum (direction-folded medians, lat-accel units; out = -(f+p+i+d)):")
    pr("      %-5s %8s %9s %9s %9s %9s %9s %10s %10s" % ("route", "secs", "f", "p", "i", "d", "sum", "ff share", "i fights f"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool); dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True; dirf[r["a"]:r["b"]] = r["dir"]
        d = dirf[stm]
        f_, p_, i_, d_ = g["f"][stm] * d, g["p"][stm] * d, g["i"][stm] * d, g["d"][stm] * d
        tot = f_ + p_ + i_ + d_
        ok2 = np.abs(tot) > 0.05
        pr("      %-5s %8.0f %+9.3f %+9.3f %+9.3f %+9.3f %+9.3f %10.2f %10.2f" % (
            t, stm.sum() / FS, med(f_), med(p_), med(i_), med(d_), med(tot),
            med(f_[ok2] / tot[ok2]), float(np.mean((np.sign(i_) == -np.sign(f_)) & (np.abs(f_) > 0.05)))))
    pr()
    pr("  D.2 the integrator's HEADROOM, expressed as the inner-loop DC scale error it can absorb:")
    pr("      i can supply at most (bound - |i|_now) of lat accel; as a fraction of the median |f| in curve frames:")
    for t in TAGS:
        g, _ = gof(t)
        ok = curve_mask(g) & (np.abs(g["desiredLateralAccel"]) > 0.3)
        f50 = med(np.abs(g["f"][ok])); imax = float(np.nanmax(np.abs(g["i"][ok])))
        pr("      %-5s max|i| %.3f of bound %.3f (%.1f %% used) ; med|f| %.3f ; spare i / med|f| = %.2f" % (
            t, imax, TUNE[t]["laf"], 100 * imax / TUNE[t]["laf"], f50, (TUNE[t]["laf"] - imax) / max(f50, 1e-6)))


# ================================================================================================ E
def sectionE(C):
    pr("\n" + "=" * 178)
    pr("SECTION E -- Q5 ACHIEVED / ASKED IN THE TIGHT-CURVE STRATUM, computed identically on every route")
    pr("  oversteer_v283 section 10.1's stratum, verbatim: TIGHT curves = |des| > 0.5 m/s^2, steady window,")
    pr("  bias-corrected, CURVE as the unit.  R = achieved / asked on the SR-FREE instrument.")
    pr("=" * 178)
    pr("  %-5s %8s %12s %12s %12s %12s | %14s" % ("route", "n curves", "os_vyaw", "os_pose", "R_vyaw", "R_pose", "R_vyaw 95% CI"))
    Rs = {}
    for t in TAGS:
        g, _ = gof(t)
        rows = [r for r in C[t] if r["des"] > 0.5 and np.isfinite(r["steady_R_vyaw"])]
        rv = [r["steady_R_vyaw"] for r in rows]
        Rs[t] = rv
        lo, hi = boot_ci(rv)
        pr("  %-5s %8d %+12.3f %+12.3f %12.3f %12.3f | [%.3f, %.3f]" % (
            t, len(rows), med([r["steady_os_vyaw"] for r in rows]), med([r["steady_os_pose"] for r in rows]),
            med(rv), med([r["steady_R_pose"] for r in rows]), lo, hi))
    d = np.array(Rs["r39"], float)
    e = np.array(Rs["r35"], float)
    rng = np.random.default_rng(11)
    bs = (np.median(d[rng.integers(0, len(d), (4000, len(d)))], 1) - np.median(e[rng.integers(0, len(e), (4000, len(e)))], 1))
    pr("  Delta R (r39 - r35) = %+.3f, 95%% CI [%+.3f, %+.3f]  (4000-resample bootstrap over curves, independent arms)" % (
        med(Rs["r39"]) - med(Rs["r35"]), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))))

    pr()
    pr("  E.1 rho = m / pose (the controller's own instrument over the road), which is what the SR change was meant to fix.")
    pr("      Regression through the origin on well-conditioned frames (|pose| > 1.0 m/s^2, 9-25 m/s).  rho = 1 means the")
    pr("      controller measures the road correctly; R_eq = 1/rho is the equilibrium delivery the loop settles at.")
    pr("      %-5s %10s %10s %10s %10s" % ("route", "rho", "R_eq=1/rho", "n(s)", "r^2"))
    for t in TAGS:
        g, _ = gof(t)
        ok = curve_mask(g) & (np.abs(g["pose"]) > 1.0) & (g["v"] > 9) & (g["v"] < 25) & np.isfinite(g["actualLateralAccel"])
        x, y = g["pose"][ok], g["actualLateralAccel"][ok]
        if ok.sum() < 50:
            pr("      %-5s  (only %.1f s qualifies)" % (t, ok.sum() / FS)); continue
        rho = float(x @ y / (x @ x))
        r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
        pr("      %-5s %10.3f %10.3f %10.1f %10.3f" % (t, rho, 1 / rho, ok.sum() / FS, r2))

    pr()
    pr("  E.2 THE MAP'S OWN EXPOSURE -- how much of r39's engaged curve time the map actually re-scaled vs the old 12.5:")
    g, _ = gof("r39")
    ok = curve_mask(g) & (np.abs(g["desiredLateralAccel"]) > DES_THR)
    srm = g["sr_map"][ok]
    pr("      |sa| p50 %.0f deg, p90 %.0f, p99 %.0f  ->  SR served p50 %.2f, p90 %.2f, p99(low) %.2f" % (
        q(np.abs(g["sa_deg"][ok]), 50), q(np.abs(g["sa_deg"][ok]), 90), q(np.abs(g["sa_deg"][ok]), 99),
        q(srm, 50), q(srm, 90), q(srm, 1)))
    for lo, hi in ((16.0, 16.01), (15.0, 16.0), (14.0, 15.0), (13.0, 14.0), (0.0, 13.0)):
        s = (srm >= lo) & (srm < hi) if hi > lo + 1e-6 else (srm >= 15.999)
        pr("      SR in [%5.2f, %5.2f): %6.1f s = %5.1f %% of curve time   (ratio vs the old fixed 12.5: %.2fx)" % (
            lo, hi, s.sum() / FS, 100.0 * s.mean(), med(srm[s]) / 12.5 if s.sum() else np.nan))


# ================================================================================================ F
def sectionF(C):
    pr("\n" + "=" * 178)
    pr("SECTION F -- Q4 THE GAIN ARITHMETIC BEHIND THE TUNE RECOMMENDATION")
    pr("  latcontrol_torque.py:283-286   low_speed_factor = (interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v,1))^2")
    pr("                                 error_with_lsf   = error * (1 + low_speed_factor / kp)")
    pr("  so the PID's p = kp * error_with_lsf = (kp + lsf) * error.  THE lsf TERM IS kp-INDEPENDENT.")
    pr("  And i = ki * INTEGRAL(error_with_lsf) with ki = 0.15 flat, so RAISING kp WEAKENS the integrator.")
    pr("  torque_from_lateral_accel (opendbc/car/interfaces.py:329) = lateral_accel / latAccelFactor  -> LAF is a DIVISOR.")
    pr("  get_friction (opendbc/car/lateral.py:190-198) saturates at +- friction * latAccelFactor, so raising LAF raises")
    pr("  the friction term in lat-accel units and then divides it back out: friction's TORQUE contribution is LAF-free.")
    pr("=" * 178)
    pr("  %8s %8s | %10s %10s %10s | %10s %10s %10s | %10s" % (
        "v (m/s)", "v (mph)", "lsf", "P@kp0.6", "P@kp0.8", "dP 0.6->0.8", "ki_eff@0.6", "ki_eff@0.8", "d ki_eff"))
    for v in (5, 7, 9, 11, 13, 15, 18, 20, 25, 30):
        lsf = (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, MIN_SPEED)) ** 2
        p6, p8 = 0.6 + lsf, 0.8 + lsf
        k6, k8 = 0.15 * (1 + lsf / 0.6), 0.15 * (1 + lsf / 0.8)
        pr("  %8.0f %8.1f | %10.3f %10.3f %10.3f | %9.1f %% %10.3f %10.3f | %9.1f %%" % (
            v, v * 2.23694, lsf, p6, p8, 100 * (p8 / p6 - 1), k6, k8, 100 * (k8 / k6 - 1)))
    pr("  => SteerKP 0.6 -> 0.8 bought +6-10 %% of proportional gain at 20 mph and +25-30 %% at highway speed.")
    pr("     It is NOT a plausible sole cause of a 20 mph worst case.")
    pr()
    pr("  F.1 the measured share of the command each term carries, engaged curve frames (direction-folded):")
    pr("      already in section D.1; the tune move is sized against it there.")
    pr()
    pr("  F.2 What each candidate knob does to the DELIVERED torque, from the code, with the direction spelled out:")
    pr("      SteerKP      up  -> p up, i(effective) DOWN, transient only. Ceiling 0.9 (= 1.5 x 0.6 stock). At 20 mph a 0.6->0.9")
    pr("                       move is only +14 %% of P because lsf dominates there.")
    pr("      SteerLatAccel up -> output_torque = lat_accel / LAF, so DELIVERED TORQUE FALLS as 1/LAF; the PID's own")
    pr("                       clamp (+- LAF) WIDENS, and the friction term rises in lat-accel space by exactly the same")
    pr("                       factor it is then divided by, so friction's torque contribution is unchanged.")
    pr("                       => raising LAF is a PURE, UNIFORM authority cut on f, p and i together.")
    pr("      SteerFriction up -> more torque near zero error only (saturating at +- friction*LAF within +- 0.30 of error).")
    laf_stock = 1.689333438873291
    pr("      LIVE CEILING: min = 0.5 x %.4f = %.4f ; max = LAT_ACCEL_FACTOR_MAX_MULT x %.4f" % (laf_stock, 0.5 * laf_stock, laf_stock))
    pr("        with MULT = 1.5 (the OLD constant): %.3f" % (1.5 * laf_stock))
    pr("        with MULT = 10  (commit 8a28dcef8): %.3f" % (10.0 * laf_stock))
    pr()
    pr("  F.3 WHY NO GAIN KNOB MOVES AN EQUILIBRIUM ERROR -- the arithmetic, stated once.")
    pr("      The outer loop has an integrator (ki 0.15, unsaturated on r39: max|i| 0.909 of a 2.110 bound, section D).")
    pr("      An unsaturated integrator drives its own error to zero, i.e. it forces  m -> des  regardless of kp, LAF or")
    pr("      friction.  Those three set HOW FAST it gets there and how it behaves in the transient; they do NOT set")
    pr("      WHERE it settles.  Where it settles is  road = des * (m/road)^-1 = des / rho, and rho is a pure function of")
    pr("      the ratio and the tyre model.  So:")
    pr("        - if the excess is EQUILIBRIUM (R_m ~ 1, R_road > 1), SteerKP / SteerLatAccel / SteerFriction cannot fix it;")
    pr("        - if the excess is LOOP GAIN (R_m > 1 as well), they can.")
    pr("      Section G measures R_m directly.  The LAF table that stood here in the first draft applied an OPEN-loop")
    pr("      1/LAF scaling to R and is WITHDRAWN: it would only be right if the integrator were saturated, which it is not.")


# ================================================================================================ G
def sectionG(C):
    pr("")
    pr("=" * 178)
    pr("SECTION G -- THE IDENTIFYING DECOMPOSITION:   R_road = R_m  x  (1 / rho)")
    pr("  R_m    = m / des          the controller's OWN tracking ratio (m = torqueState.actualLateralAccel).")
    pr("                            R_m > 1 means the loop overshoots its own target -> LOOP GAIN, a gain knob acts.")
    pr("  1/rho  = road / m         the measurement scale error (rho = m / road).  A RATIO / TYRE-MODEL error.")
    pr("                            No gain knob touches it while the integrator is unsaturated.")
    pr("  road   = livePose yaw_cal * v (SR-FREE).  Same tight-curve steady stratum as section E, curve as the unit.")
    pr("=" * 178)
    pr("  %-5s %8s %10s %10s %10s %10s | %12s %12s" % (
        "route", "n curves", "R_m", "R_road", "1/rho", "R_m*(1/rho)", "R_m 95% CI", "R_road 95% CI"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        rm, rr, ri = [], [], []
        for r in C[t]:
            if r["des"] <= 0.5 or r["b"] - r["a"] < int(2.5 * FS):
                continue
            sl = slice(r["a"] + 150, r["b"])
            big = np.abs(des[sl]) > 0.5
            if big.sum() < 10:
                continue
            m_ = g["actualLateralAccel"][sl][big] - sb["m"]
            rd = g["vyaw"][sl][big] - sb["vyaw"]
            dd = des[sl][big]
            rm.append(med(m_ / dd)); rr.append(med(rd / dd)); ri.append(med(rd / m_))
        lo1, hi1 = boot_ci(rm); lo2, hi2 = boot_ci(rr)
        pr("  %-5s %8d %10.3f %10.3f %10.3f %10.3f | [%.3f,%.3f] [%.3f,%.3f]" % (
            t, len(rm), med(rm), med(rr), med(ri), med(rm) * med(ri), lo1, hi1, lo2, hi2))
    pr()
    pr("  G.1 the same split along the DWELL axis (fixed cohort, curves >= 5.0 s) -- does R_m settle at 1?")
    TT = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0)
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        rows = [r for r in C[t] if r["dur"] >= 5.0]
        cm, cr = [], []
        for tt in TT:
            k = int(tt * FS); vm, vr = [], []
            for r in rows:
                j = r["a"] + k
                if j >= r["b"] or abs(des[j]) < 0.4:
                    continue
                vm.append((g["actualLateralAccel"][j] - sb["m"]) / des[j])
                vr.append((g["vyaw"][j] - sb["vyaw"]) / des[j])
            cm.append(np.nanmedian(vm) if len(vm) > 3 else np.nan)
            cr.append(np.nanmedian(vr) if len(vr) > 3 else np.nan)
        pr("      %-5s n=%2d  R_m   " % (t, len(rows)) + " ".join("%7.3f" % x for x in cm))
        pr("      %-5s        R_road" % "" + " ".join("%7.3f" % x for x in cr))
    pr("      t (s)              " + " ".join("%7.2f" % x for x in TT))
    pr()
    pr("  G.2 SCALE vs OFFSET: regress achieved on asked over all curve-steady frames (direction-folded, bias-corrected).")
    pr("      A pure SCALE error gives slope > 1 with intercept ~ 0.  A gain/transient artefact does not scale with the ask.")
    pr("      %-5s %10s %10s %10s %10s %8s" % ("route", "slope", "intercept", "r", "slope(TLS)", "secs"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]; sb = straight_bias(g)
        stm = np.zeros(len(des), bool); dirf = np.zeros(len(des))
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True; dirf[r["a"]:r["b"]] = r["dir"]
        x = des[stm] * dirf[stm]
        y = (g["vyaw"][stm] - sb["vyaw"]) * dirf[stm]
        A = np.c_[x, np.ones_like(x)]
        sl, ic = np.linalg.lstsq(A, y, rcond=None)[0]
        pr("      %-5s %10.3f %10.3f %10.3f %10.3f %8.0f" % (
            t, sl, ic, float(np.corrcoef(x, y)[0, 1]), tls(x, y), stm.sum() / FS))
    pr()
    pr("  G.3 IS THE INTEGRATOR CONVERGED in the steady window?  (if it is still moving, the equilibrium is not reached)")
    pr("      %-5s %12s %12s %12s" % ("route", "med |di/dt|", "p90 |di/dt|", "frac |di/dt|>0.05 /s"))
    for t in TAGS:
        g, _ = gof(t)
        des = g["desiredLateralAccel"]
        stm = np.zeros(len(des), bool)
        for r in C[t]:
            stm[r["a"] + 150:r["b"]] = True
        di = np.abs(np.r_[0.0, np.diff(g["i"])]) * FS
        pr("      %-5s %12.4f %12.4f %12.3f" % (t, med(di[stm]), q(di[stm], 90), float(np.mean(di[stm] > 0.05))))


def main():
    A = sectionA()
    C, traj = sectionB(A)
    sectionC(C)
    sectionD(C)
    sectionE(C)
    sectionF(C)
    sectionG(C)
    out = os.path.join(HERE, "_scratch", "oversteer_v282_r39.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES))
    json.dump({"A": A, "curves": {t: C[t] for t in TAGS}, "traj": traj},
              open(os.path.join(HERE, "oversteer_v282_r39.json"), "w"), indent=1,
              default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    pr("\nwrote %s" % out)


if __name__ == "__main__":
    main()
