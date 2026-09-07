# -*- coding: utf-8 -*-
"""lane_centering_levers.py -- price EVERY lever in the fork's lane-centering stack against the
operator's own measured frames (r39 / r3a / r3c, V282).

Surface: selfdrive/controls/lib/lane_centering.py, its consumer controlsd.py:744-754, and its
toggles in starpilot/common/starpilot_variables.py:754-787.

Everything here re-runs `LaneCenteringController._raw_correction` LINE BY LINE on the cached
modelV2 frames, so a gate's duty is measured, not argued.  Conventions are inherited verbatim from
plan_vs_execution.py (device frame FRD, +y RIGHT, off_inside = off_right * sign(k_road)).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_vs_execution as P  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAGS = ("r39", "r3c", "r3a")
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


# ---- the fork's constants, quoted (lane_centering.py:8-25) --------------------------------------
MIN_V_EGO = 5.0
MIN_LANE_PROB = 0.6
MAX_LANE_STD = 0.3
MIN_LANE_WIDTH = 2.6
MAX_LANE_WIDTH = 4.8
MAX_OFFSET = 0.3
MIN_CENTER_TO_LINE = 1.1
MAX_RAW_CORRECTION = 0.004
MAX_GAIN = 0.30
SMOOTH_TAU = 0.4
CENTER_ERROR_DEADBAND = 0.08
E2E_MAX_PATH_STD = 0.35
E2E_BREAK_IN_START = 0.15
E2E_BREAK_IN_FULL = 0.50

DT = 0.05  # modelV2 / our frame grid, 20 Hz


def build(tag):
    """Add every per-frame quantity `_raw_correction` needs, at the fork's own lookahead."""
    f = P.prep_plan_offset(tag)
    if "lc_err" in f:
        return f
    z = np.load(os.path.join(P.SCR, "%s_modelv2.npz" % tag), allow_pickle=True)
    px = np.asarray(z["mdl_pos_x"], float)
    pystd = np.asarray(z["mdl_pos_ystd"], float)
    d = f["look_d"]
    x = f["x"]
    n = len(d)

    # lane width AT THE LOOKAHEAD (the fork gates on this, not on width at x=0)
    ll1 = f["ll1"]
    ll2 = f["ll2"]
    left_d = np.array([np.interp(d[i], x, ll1[i]) for i in range(n)])
    right_d = np.array([np.interp(d[i], x, ll2[i]) for i in range(n)])
    f["lc_width_d"] = right_d - left_d
    f["lc_pathstd_d"] = P._interp_row(px, pystd, d)

    # error = target_y - model_y,  target_y = 0.5*(left+right) + clip(offset, +-max_safe)
    # with LaneCenterOffset = 0 (the operator's value) target_y is the lane centre.
    f["lc_err"] = f["lane_y_d"] - f["path_y_d"]          # == -plan_off_right
    f["lc_maxsafe"] = np.minimum(MAX_OFFSET, np.maximum(0.0, f["lc_width_d"] * 0.5 - MIN_CENTER_TO_LINE))
    f["lc_poscovers"] = f["pos_xmax"] >= d
    return f


def raw_correction(f, offset=0.0, authority=1.0, deadband=CENTER_ERROR_DEADBAND,
                   max_raw=MAX_RAW_CORRECTION, gain=MAX_GAIN, brk_start=E2E_BREAK_IN_START,
                   brk_full=E2E_BREAK_IN_FULL, pathstd_max=E2E_MAX_PATH_STD):
    """Vectorised, line-for-line copy of LaneCenteringController._raw_correction (:94-155).
    Returns (valid, target_correction 1/m, err_after_deadband, kept, raw_before_clip)."""
    d = f["look_d"]
    off = np.clip(offset, -f["lc_maxsafe"], f["lc_maxsafe"])
    err = f["lane_y_d"] + off - f["path_y_d"]
    err_abs = np.abs(err)
    e = np.where(err_abs <= deadband, 0.0, np.copysign(err_abs - deadband, err))

    kept = np.ones_like(e)
    ps = f["lc_pathstd_d"]
    fade_on = np.isfinite(ps) & (ps >= 0.0) & (ps <= pathstd_max)
    brk = np.clip((err_abs - brk_start) / (brk_full - brk_start), 0.0, 1.0)
    kept = np.where(fade_on, 1.0 - authority * brk, 1.0)
    e = e * kept

    raw = 2.0 * e / d ** 2
    tgt = np.clip(raw, -max_raw, max_raw) * gain
    return tgt, e, kept, raw


def valid_mask(f):
    """the fork's validity gates, one boolean per gate (lane_centering.py:99-127)."""
    pr_ = f["llprob"]
    st = f["llstd"]
    g = {}
    g["v>=5"] = f["v"] >= MIN_V_EGO
    g["laneChange off"] = f["lcs"] < 0.5
    g["not pressed"] = f["pressed"] < 0.5
    g["prob>=0.6"] = (pr_[:, 1] >= MIN_LANE_PROB) & (pr_[:, 2] >= MIN_LANE_PROB)
    g["std<=0.3"] = (st[:, 1] <= MAX_LANE_STD) & (st[:, 2] <= MAX_LANE_STD)
    g["pos_x covers L"] = f["lc_poscovers"]
    g["width 2.6-4.8"] = (f["lc_width_d"] >= MIN_LANE_WIDTH) & (f["lc_width_d"] <= MAX_LANE_WIDTH)
    return g


def curve_frames(f):
    """engaged (lat active, not pressed, not in r3a's hole) + on a bend, the operator's complaint."""
    return f["eng"] & (np.abs(f["k_road"]) >= 0.0008) & (f["v"] >= 5.0) & np.isfinite(f["lc_err"])


# ================================================================================================
def sec_gates():
    pr("=" * 168)
    pr("SECTION A -- GATE DUTY.  How often each validity gate in `_raw_correction` KILLS the")
    pr("  correction, on the operator's own frames.  Denominator = LATERALLY ENGAGED frames")
    pr("  (CC.latActive & controlsState.active & not steeringPressed, r3a's 60 s hole masked).")
    pr("  'curve' additionally requires |k_road| >= 0.0008 and v >= 5.")
    pr("=" * 168)
    pr("  %-6s %-9s %7s | %s" % ("route", "subset", "secs", "  ".join("%16s" % k for k in
       ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8", "ALL PASS"))))
    for tag in TAGS:
        f = build(tag)
        g = valid_mask(f)
        allp = np.ones(len(f["t"]), bool)
        for k in ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8"):
            allp &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
        for name, base in (("engaged", f["eng"]), ("curve", curve_frames(f))):
            n = base.sum()
            row = []
            for k in ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8"):
                ok = np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
                row.append("%15.1f%%" % (100.0 * (base & ~ok).sum() / max(n, 1)))
            row.append("%15.1f%%" % (100.0 * (base & allp).sum() / max(n, 1)))
            pr("  %-6s %-9s %7.1f | %s" % (tag, name, n * DT, "  ".join(row)))
    pr()
    pr("  columns are the FRACTION KILLED by that gate alone; last column is the fraction where")
    pr("  ALL gates pass (the correction is computed at all).")


# ================================================================================================
def sec_clamps():
    pr("=" * 168)
    pr("SECTION B -- WHERE THE CORRECTION IS LOST.  Per curve frame (engaged, |k_road|>=0.0008,")
    pr("  v>=5, all validity gates passing), the four multiplicative losses between the raw lateral")
    pr("  error and the curvature actually added, at LaneCenteringE2EAuthority = 1.0 and 0.0.")
    pr("=" * 168)
    hdr = ("route", "auth", "secs", "med|err| m", "deadband kill", "med kept", "kept=0", "clip bind",
           "med |corr|", "med |k_road|", "corr/k_road")
    pr("  " + " ".join("%13s" % h for h in hdr))
    for tag in TAGS:
        f = build(tag)
        g = valid_mask(f)
        allp = np.ones(len(f["t"]), bool)
        for k in ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8"):
            allp &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
        m = curve_frames(f) & allp
        for auth in (1.0, 0.0):
            tgt, e, kept, raw = raw_correction(f, 0.0, auth)
            db_kill = np.abs(f["lc_err"]) <= CENTER_ERROR_DEADBAND
            clip = np.abs(raw) > MAX_RAW_CORRECTION
            vals = (
                "%13s" % tag, "%13.1f" % auth, "%13.1f" % (m.sum() * DT),
                "%13.3f" % np.nanmedian(np.abs(f["lc_err"][m])),
                "%12.1f%%" % (100.0 * (m & db_kill).sum() / max(m.sum(), 1)),
                "%13.3f" % np.nanmedian(kept[m]),
                "%12.1f%%" % (100.0 * (m & (kept <= 1e-9)).sum() / max(m.sum(), 1)),
                "%12.1f%%" % (100.0 * (m & clip).sum() / max(m.sum(), 1)),
                "%13.6f" % np.nanmedian(np.abs(tgt[m])),
                "%13.6f" % np.nanmedian(np.abs(f["k_road"][m])),
                "%13.3f" % (np.nanmedian(np.abs(tgt[m])) / np.nanmedian(np.abs(f["k_road"][m]))),
            )
            pr("  " + " ".join(vals))
    pr()
    pr("  'clip bind' = |2*err/L^2| > _MAX_RAW_CORRECTION 0.004 BEFORE the x0.30 gain.")
    pr("  NOTE the order in the code: deadband (:134-137) THEN the e2e fade (:149) THEN 2e/L^2 THEN")
    pr("  the clip (:81).  The fade shrinks the error before the clip sees it, so raising authority")
    pr("  to 0 moves load ONTO the clip.")


# ================================================================================================
def sec_clip_speed():
    pr("=" * 168)
    pr("SECTION C -- DOES `_MAX_RAW_CORRECTION` BIND, AND WHERE?  The clip is on 2*e/L^2 with")
    pr("  L = clip(v, 8, 35), so the error at which it engages is e* = 0.002 * L^2 metres -- tiny at")
    pr("  low speed.  Duty measured on curve frames, per speed band, at authority 1.0 and 0.0.")
    pr("=" * 168)
    pr("  %-6s %-9s %7s %9s %11s %11s %11s %11s" %
       ("route", "v m/s", "secs", "e* m", "med e a=1", "clip a=1", "med e a=0", "clip a=0"))
    for tag in TAGS:
        f = build(tag)
        g = valid_mask(f)
        allp = np.ones(len(f["t"]), bool)
        for k in ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8"):
            allp &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
        base = curve_frames(f) & allp
        t1, e1, k1, r1 = raw_correction(f, 0.0, 1.0)
        t0, e0, k0, r0 = raw_correction(f, 0.0, 0.0)
        for lo, hi in ((5, 9), (9, 14), (14, 20), (20, 40)):
            m = base & (f["v"] >= lo) & (f["v"] < hi)
            if m.sum() < 20:
                continue
            L = np.median(f["look_d"][m])
            pr("  %-6s %-9s %7.1f %9.3f %11.3f %10.1f%% %11.3f %10.1f%%" % (
                tag, "%d-%d" % (lo, hi), m.sum() * DT, 0.002 * L ** 2,
                np.nanmedian(np.abs(e1[m])), 100.0 * (m & (np.abs(r1) > MAX_RAW_CORRECTION)).sum() / m.sum(),
                np.nanmedian(np.abs(e0[m])), 100.0 * (m & (np.abs(r0) > MAX_RAW_CORRECTION)).sum() / m.sum()))


# ================================================================================================
def sec_pathstd():
    pr("=" * 168)
    pr("SECTION D -- THE `_E2E_MAX_PATH_STD 0.35` GATE.  Read the code (:143): the e2e fade is")
    pr("  applied ONLY when path_std <= 0.35.  Above it the fade is SKIPPED and the correction acts")
    pr("  in FULL.  It is therefore not a kill switch -- it is the escape hatch out of the fade.")
    pr("=" * 168)
    pr("  %-6s %-9s %7s %12s %12s %12s" % ("route", "subset", "secs", "med path_std", "frac >0.35", "frac fade ON"))
    for tag in TAGS:
        f = build(tag)
        for name, base in (("engaged", f["eng"]), ("curve", curve_frames(f))):
            ps = f["lc_pathstd_d"]
            ok = np.isfinite(ps) & base
            n = ok.sum()
            pr("  %-6s %-9s %7.1f %12.3f %11.1f%% %11.1f%%" % (
                tag, name, n * DT, np.nanmedian(ps[ok]),
                100.0 * (ok & (ps > E2E_MAX_PATH_STD)).sum() / max(n, 1),
                100.0 * (ok & (ps <= E2E_MAX_PATH_STD) & (ps >= 0)).sum() / max(n, 1)))


# ================================================================================================
def sec_perception():
    pr("=" * 168)
    pr("SECTION A2 -- WHY THE PERCEPTION GATES KILL SO MUCH.  Distribution of the two quantities")
    pr("  `_raw_correction` gates on (:103-106): laneLineProbs[1,2] against _MIN_LANE_PROB 0.6 and")
    pr("  laneLineStds[1,2] against _MAX_LANE_STD 0.3.  min over the two inner lines, engaged frames.")
    pr("=" * 168)
    pr("  %-6s %-9s %7s | %8s %8s %8s %8s | %8s %8s %8s %8s" %
       ("route", "subset", "secs", "prob p10", "p25", "p50", "p75", "std p25", "p50", "p75", "p90"))
    for tag in TAGS:
        f = build(tag)
        p = np.minimum(f["llprob"][:, 1], f["llprob"][:, 2])
        s = np.maximum(f["llstd"][:, 1], f["llstd"][:, 2])
        for name, base in (("engaged", f["eng"]), ("curve", curve_frames(f))):
            pr("  %-6s %-9s %7.1f | %8.3f %8.3f %8.3f %8.3f | %8.3f %8.3f %8.3f %8.3f" % (
                tag, name, base.sum() * DT,
                *[np.nanpercentile(p[base], q) for q in (10, 25, 50, 75)],
                *[np.nanpercentile(s[base], q) for q in (25, 50, 75, 90)]))
    pr()
    pr("  and the duty won back by loosening ONE gate at a time on CURVE frames (all other gates held):")
    pr("  %-6s %11s %11s %11s %11s %11s" %
       ("route", "as shipped", "prob>=0.4", "std<=0.5", "both", "both+0.3/0.6"))
    for tag in TAGS:
        f = build(tag)
        g = valid_mask(f)
        oth = np.ones(len(f["t"]), bool)
        for k in ("v>=5", "laneChange off", "pos_x covers L", "width 2.6-4.8"):
            oth &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
        base = curve_frames(f)
        n = max(base.sum(), 1)
        p = np.minimum(f["llprob"][:, 1], f["llprob"][:, 2])
        s = np.maximum(f["llstd"][:, 1], f["llstd"][:, 2])
        combos = ((0.6, 0.3), (0.4, 0.3), (0.6, 0.5), (0.4, 0.5), (0.3, 0.6))
        vals = ["%10.1f%%" % (100.0 * (base & oth & (p >= a) & (s <= b)).sum() / n) for a, b in combos]
        pr("  %-6s %s" % (tag, " ".join(vals)))


def sec_lead():
    pr("=" * 168)
    pr("SECTION E -- IS THERE HEADING LEAD IN THE ERROR?  This decides whether the lane-centering")
    pr("  loop is DAMPED or a pure oscillator, and it is the biggest single uncertainty in sizing.")
    pr("    err(L) = lane_centre(L) - path(L).  modelV2.position is expressed IN THE CAR FRAME, so")
    pr("    path_y(0) = 0 and the path leaves the car along the CAR'S OWN heading -- it cannot")
    pr("    contain an instantaneous heading correction.  If that holds, err(L) automatically")
    pr("    carries the -L*psi heading term and the loop is a damped pure-pursuit law.")
    pr("  E1  STRUCTURAL CHECK: the plan's own heading at the car, dpath_y/dx at x->0, in radians.")
    pr("      If this is ~0 on every frame the lead term is structural, not an assumption.")
    pr("=" * 168)
    pr("  %-6s %7s %12s %12s %12s %12s" % ("route", "secs", "med |slope|", "p90", "p99", "max"))
    for tag in TAGS:
        f = build(tag)
        z = np.load(os.path.join(P.SCR, "%s_modelv2.npz" % tag), allow_pickle=True)
        px = np.asarray(z["mdl_pos_x"], float)
        py = np.asarray(z["mdl_pos_y"], float)
        m = curve_frames(f)
        sl = np.abs((py[:, 2] - py[:, 0]) / np.maximum(px[:, 2] - px[:, 0], 1e-6))[m]
        sl = sl[np.isfinite(sl)]
        pr("  %-6s %7.1f %12.5f %12.5f %12.5f %12.5f" % (
            tag, m.sum() * DT, np.median(sl), *[np.percentile(sl, q) for q in (90, 99)], sl.max()))
    pr()
    pr("  E2  and the DIRECT question behind it: does the driving model pull BACK toward centre?")
    pr("  Slope of (PLAN_inside - CAR_inside) on CAR_inside.  A negative slope is restoring intent;")
    pr("  0 means the plan holds whatever offset it has (a pure integrator, no restoring force);")
    pr("  positive means the plan SEEKS further inside the further inside the car already is.")
    pr("  %-6s %7s %8s %10s %8s" % ("route", "secs", "slope", "intcpt cm", "R2"))
    for tag in TAGS:
        f = build(tag)
        m = curve_frames(f) & np.isfinite(f["plan_off_right"])
        sgn = np.sign(f["k_road"][m])
        car = f["off_right"][m] * sgn
        plan = f["plan_off_right"][m] * sgn
        A = np.stack([car, np.ones_like(car)], 1)
        c, *_ = np.linalg.lstsq(A, plan - car, rcond=None)
        res = (plan - car) - A @ c
        r2 = 1.0 - res.var() / max((plan - car).var(), 1e-12)
        pr("  %-6s %7.1f %8.3f %10.1f %8.3f" % (tag, m.sum() * DT, c[0], 100 * c[1], r2))


# ================================================================================================
def _sim(v, auth, e0=0.36, lead=1.0, deadband=CENTER_ERROR_DEADBAND, tau=SMOOTH_TAU,
         max_raw=MAX_RAW_CORRECTION, gain=MAX_GAIN, tmax=40.0, dt=0.01):
    e, psi, corr = e0, 0.0, 0.0
    L = float(np.clip(v, 8.0, 35.0))
    alpha = (1 - np.exp(-dt / tau)) if tau > 0 else 1.0
    tr = np.empty(int(tmax / dt))
    for i in range(tr.size):
        err = e - lead * L * psi
        ea = abs(err)
        ee = 0.0 if ea <= deadband else np.copysign(ea - deadband, err)
        brk = min(max((ea - E2E_BREAK_IN_START) / (E2E_BREAK_IN_FULL - E2E_BREAK_IN_START), 0.0), 1.0)
        ee *= 1.0 - auth * brk
        raw = 2.0 * ee / L ** 2
        tgt = min(max(raw, -max_raw), max_raw) * gain
        corr += alpha * (tgt - corr)
        psi += v * corr * dt
        e -= v * psi * dt
        tr[i] = e
    return tr


def sec_sim_valid():
    pr("=" * 168)
    pr("SECTION F0 -- SIM VALIDATION.  With the deadband, the clip and the smoothing all removed the")
    pr("  loop is exactly  e'' + (2*G*v^2/L^2)*(L/v)*e' + (2*G*v^2/L^2)*e = 0,  i.e. for v in [8,35]")
    pr("  (L = v) it is SPEED-INDEPENDENT with wn = sqrt(2*0.30) = 0.7746 rad/s (period 8.11 s) and")
    pr("  zeta = 0.5*sqrt(2*0.30) = 0.3873.  Released from e0 with e'(0)=0 the analytic trajectory is")
    pr("  e(t) = e0*exp(-z*wn*t)*(cos(wd t) + (z*wn/wd) sin(wd t)).  Sim vs analytic:")
    pr("=" * 168)
    wn = np.sqrt(2 * MAX_GAIN)
    z = 0.5 * np.sqrt(2 * MAX_GAIN)
    wd = wn * np.sqrt(1 - z ** 2)
    pr("  wn %.4f rad/s (T %.2f s)   zeta %.4f   wd %.4f   1/(z*wn) = %.2f s" % (wn, 2 * np.pi / wn, z, wd, 1 / (z * wn)))
    pr("  %6s %10s %10s %10s %10s" % ("t s", "sim v=12", "sim v=25", "analytic", "err"))
    for tt in (1.0, 2.0, 3.0, 4.4, 6.0, 8.0, 12.0):
        a = 0.36 * np.exp(-z * wn * tt) * (np.cos(wd * tt) + (z * wn / wd) * np.sin(wd * tt))
        s12 = _sim(12.0, 0.0, deadband=0.0, tau=0.0)[int(tt / 0.01)]
        s25 = _sim(25.0, 0.0, deadband=0.0, tau=0.0)[int(tt / 0.01)]
        pr("  %6.1f %10.4f %10.4f %10.4f %10.4f" % (tt, s12, s25, a, s12 - a))


def sec_authority():
    pr("=" * 168)
    pr("SECTION F1 -- AUTHORITY SWEEP, measured on the frames (not simulated).  Median |correction|")
    pr("  and its ratio to the road curvature it has to work against, on curve frames where every")
    pr("  validity gate passes, as LaneCenteringE2EAuthority is walked from 1.0 (shipped) to 0.0.")
    pr("=" * 168)
    pr("  %-6s %7s | %s" % ("route", "secs", " ".join("%14s" % ("auth %.2f" % a) for a in (1.0, 0.75, 0.5, 0.25, 0.0))))
    for tag in TAGS:
        f = build(tag)
        g = valid_mask(f)
        allp = np.ones(len(f["t"]), bool)
        for k in ("v>=5", "laneChange off", "prob>=0.6", "std<=0.3", "pos_x covers L", "width 2.6-4.8"):
            allp &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
        m = curve_frames(f) & allp
        kr = np.nanmedian(np.abs(f["k_road"][m]))
        row = []
        for a in (1.0, 0.75, 0.5, 0.25, 0.0):
            tgt, _, _, _ = raw_correction(f, 0.0, a)
            row.append("%14s" % ("%.6f/%.2f" % (np.nanmedian(np.abs(tgt[m])), np.nanmedian(np.abs(tgt[m])) / kr)))
        pr("  %-6s %7.1f | %s" % (tag, m.sum() * DT, " ".join(row)))
    pr("  each cell is  med|corr| 1/m  /  corr:k_road ratio.")


def sec_sim():
    pr("=" * 168)
    pr("SECTION F -- CLOSED-LOOP SIZING: how many cm can the lane-centering loop actually take out,")
    pr("  and how fast?  Simulated with the fork's OWN nonlinearities (deadband 0.08, e2e fade,")
    pr("  clip 0.004, gain 0.30, smooth_value tau 0.4 at 100 Hz) on a flat road-following plant:")
    pr("      err = e - LEAD*L*psi ;  psi_dot = v*(k_corr) ;  e_dot = -v*psi")
    pr("  LEAD = 0.0 is the PARALLEL-PLAN case (no damping, the loop rings); LEAD = 1.0 is the")
    pr("  PURE-PURSUIT case (zeta 0.39).  SECTION E measures which we are in.  The driving model is")
    pr("  assumed to hold its offset with no restoring intent -- SECTION E's second table tests that.")
    pr("  e0 = 0.36 m (the measured median inside offset on r39 curve frames).")
    pr("=" * 168)
    for lead in (1.0, 0.0):
        pr("  --- LEAD = %.1f  %s ---" % (lead, "(STRUCTURAL, see SECTION E1)" if lead else "(counterfactual: no lead)"))
        pr("  %6s %6s %9s %9s %9s %9s %9s %9s %9s" %
           ("v m/s", "auth", "e(3.3s)", "e(5.9s)", "e(10s)", "e(20s)", "1st min", "t to 0.15", "|e| 20-40s"))
        for v in (7.0, 12.0, 17.0, 25.0):
            for auth in (1.0, 0.5, 0.0):
                tr = _sim(v, auth, lead=lead)
                t15 = np.flatnonzero(np.abs(tr) <= 0.15)
                pr("  %6.0f %6.1f %9.3f %9.3f %9.3f %9.3f %9.3f %9s %9.3f" % (
                    v, auth, tr[330], tr[590], tr[1000], tr[2000], tr[:1200].min(),
                    ("%.1f" % (t15[0] * 0.01)) if t15.size else "never",
                    float(np.percentile(np.abs(tr[2000:]), 90))))
        pr()


# ================================================================================================
def sec_offsets():
    pr("=" * 168)
    pr("SECTION G -- THE STRAIGHT-LINE BIAS AND THE CONSTANT-OFFSET LEVERS.")
    pr("  off_right at x=0 on STRAIGHT engaged frames (|k_road| < 0.0008), and what a constant")
    pr("  lateral shift would cost.  LaneCenterOffset enters as target_y = lane_centre + offset,")
    pr("  so + offset moves the TARGET right => the car right.  It is clamped to")
    pr("  min(0.30, width/2 - 1.1) -- report how often that clamp is the binding one.")
    pr("=" * 168)
    pr("  %-6s %7s %11s %11s %11s %11s %11s" %
       ("route", "secs", "med off_right", "p25", "p75", "med maxsafe", "frac<0.30"))
    for tag in TAGS:
        f = build(tag)
        m = f["eng"] & (np.abs(f["k_road"]) < 0.0008) & (f["v"] >= 5.0) & np.isfinite(f["lc_maxsafe"])
        pr("  %-6s %7.1f %11.3f %11.3f %11.3f %11.3f %10.1f%%" % (
            tag, m.sum() * DT, np.nanmedian(f["off_right"][m]),
            np.nanpercentile(f["off_right"][m], 25), np.nanpercentile(f["off_right"][m], 75),
            np.nanmedian(f["lc_maxsafe"][m]),
            100.0 * (m & (f["lc_maxsafe"] < MAX_OFFSET)).sum() / max(m.sum(), 1)))
    pr()
    pr("  and the same on CURVE frames, where max_safe_offset matters more (narrower apparent lane):")
    pr("  %-6s %7s %11s %11s" % ("route", "secs", "med maxsafe", "frac<0.30"))
    for tag in TAGS:
        f = build(tag)
        m = curve_frames(f) & np.isfinite(f["lc_maxsafe"])
        pr("  %-6s %7.1f %11.3f %10.1f%%" % (
            tag, m.sum() * DT, np.nanmedian(f["lc_maxsafe"][m]),
            100.0 * (m & (f["lc_maxsafe"] < MAX_OFFSET)).sum() / max(m.sum(), 1)))


# ================================================================================================
def sec_signal():
    pr("=" * 168)
    pr("SECTION H -- THE PAUSE GATES.  `LaneCenteringPauseOnSignal` (blinker) and `driver_override`")
    pr("  (steeringPressed) both RESET or fade the correction.  Duty on engaged frames.")
    pr("=" * 168)
    pr("  %-6s %9s %14s %14s %14s" % ("route", "eng secs", "blinker%", "pressed%", "laneChange%"))
    for tag in TAGS:
        f = build(tag)
        g, _ = P.gof(tag)
        # blinker is not in the joined frame; take steeringPressed + laneChangeState which are.
        m = f["lat"] > 0.5
        n = max(m.sum(), 1)
        pr("  %-6s %9.1f %13.1f%% %13.1f%% %13.1f%%" % (
            tag, m.sum() * DT, float("nan"),
            100.0 * (m & (f["pressed"] > 0.5)).sum() / n,
            100.0 * (m & (f["lcs"] >= 0.5)).sum() / n))



# ================================================================================================
_AS = 1 - __import__("numpy").exp(-DT / SMOOTH_TAU)
_AR = 1 - __import__("numpy").exp(-DT / 0.20)


def _allp(f, prob=MIN_LANE_PROB, std=MAX_LANE_STD, perception=True):
    g = valid_mask(f)
    keys = ["v>=5", "laneChange off", "pos_x covers L", "width 2.6-4.8"]
    m = np.ones(len(f["t"]), bool)
    for k in keys:
        m &= np.nan_to_num(g[k].astype(float), nan=0.0).astype(bool)
    if perception:
        p = np.minimum(f["llprob"][:, 1], f["llprob"][:, 2])
        s = np.maximum(f["llstd"][:, 1], f["llstd"][:, 2])
        m &= (p >= prob) & (s <= std)
    return m


def _hard(f):
    """the RESET conditions of update() (:51-69): not enabled/latActive/model_valid, v<5,
    driver override, lane change.  On reset self._correction is set to 0, not faded."""
    return (f["lat"] > 0.5) & (f["pressed"] < 0.5) & (f["lcs"] < 0.5) & (f["v"] >= MIN_V_EGO)


def replay(tgt, ok, hard):
    """update()'s own state machine: hard reset -> 0, invalid -> fade with _CONFIDENCE_RELEASE_TAU,
    valid -> rise toward target with _SMOOTH_TAU.  Run at 20 Hz; the alphas are the same filter."""
    c = 0.0
    out = np.zeros(len(tgt))
    for i in range(len(tgt)):
        if not hard[i]:
            c = 0.0
        elif not ok[i]:
            c += _AR * (0.0 - c)
        elif np.isfinite(tgt[i]):
            c += _AS * (tgt[i] - c)
        out[i] = c
    return out


def sec_replay():
    pr("=" * 168)
    pr("SECTION I -- THE DECISIVE ONE: replay update()'s FULL state machine on the real frame")
    pr("  sequence.  Everything above prices the LAW; this prices what actually reaches")
    pr("  desiredCurvature once the gates chop the signal and the two taus fight each other.")
    pr("  I1  how long a valid run lasts on curve frames (the correction must build inside one):")
    pr("=" * 168)
    pr("  %-6s %7s %8s %8s %8s %8s %10s" % ("route", "n runs", "p25 s", "med s", "p75 s", "p90 s", "frac<0.8s"))
    for tag in TAGS:
        f = build(tag)
        m = curve_frames(f) & _allp(f)
        bl = P.blocks(m, 1, gap=0)
        d = np.array([(b - a) * DT for a, b in bl])
        pr("  %-6s %7d %8.2f %8.2f %8.2f %8.2f %9.0f%%" %
           (tag, len(d), *[np.percentile(d, q) for q in (25, 50, 75, 90)], 100 * (d < 0.8).mean()))
    pr("  _SMOOTH_TAU is 0.4 s.  A valid run shorter than ~1.2 s cannot reach 95 % of its target.")
    pr()
    pr("  I2  TIME-MEAN restoring curvature delivered on curve frames, signed toward the lane centre,")
    pr("      as a fraction of the road curvature it must work against.  'gates open' = the same law")
    pr("      with the laneLineProbs/Stds gate forced to pass: the price of that gate alone.")
    pr("  %-6s %5s | %11s %9s %7s | %11s %9s %7s | %9s" % (
        "route", "auth", "mean corr", "/k_road", "zero%", "gates open", "/k_road", "zero%", "gate cost"))
    for tag in TAGS:
        f = build(tag)
        ok = _allp(f)
        loose = _allp(f, perception=False)
        hard = _hard(f)
        cm = curve_frames(f)
        kr = np.nanmean(np.abs(f["k_road"][cm]))
        sg = np.sign(f["lc_err"])
        for auth in (1.0, 0.5, 0.25, 0.0):
            tgt, _, _, _ = raw_correction(f, 0.0, auth)
            A = replay(tgt, ok, hard)
            Bv = replay(tgt, loose, hard)
            ma = np.nanmean((A * sg)[cm])
            mb = np.nanmean((Bv * sg)[cm])
            pr("  %-6s %5.2f | %11.6f %9.3f %6.0f%% | %11.6f %9.3f %6.0f%% | %9.2f" % (
                tag, auth, ma, ma / kr, 100 * (np.abs(A[cm]) < 1e-9).mean(),
                mb, mb / kr, 100 * (np.abs(Bv[cm]) < 1e-9).mean(), ma / max(mb, 1e-12)))
    pr()
    pr("  I3  CURVE BLOCK DURATIONS -- how long the loop has to work, contiguous engaged curve runs:")
    pr("  %-6s %7s %8s %8s %8s %8s %8s" % ("route", "n", "p25 s", "med s", "p75 s", "p90 s", "tot s"))
    for tag in TAGS:
        f = build(tag)
        bl = P.blocks(curve_frames(f), 20)
        d = np.array([(b - a) * DT for a, b in bl])
        pr("  %-6s %7d %8.1f %8.1f %8.1f %8.1f %8.1f" %
           (tag, len(d), *[np.percentile(d, q) for q in (25, 50, 75, 90)], d.sum()))
    pr()
    pr("  I4  EFFECTIVE-GAIN CLOSED-LOOP SIZING.  G_eff = _MAX_GAIN * (mean corr delivered) /")
    pr("      (mean corr the law asks at authority 0 with the perception gate open), from I2 on r39.")
    pr("      Simulated at v = 16 m/s, LEAD = 1, cm of inside offset REMAINING.")
    pr("  %-40s %7s %8s %8s %8s %8s %8s" % ("configuration", "G_eff", "e@2.0s", "e@2.9s", "e@4.4s", "e@6.2s", "e@12s"))
    for e0 in (0.36, 0.59):
        pr("   --- e0 = %.2f m ---" % e0)
        for name, G in (("shipped: auth 1.0, gates as-is", 0.30 * 0.073),
                        ("auth 0.0, gates as-is", 0.30 * 0.330),
                        ("auth 0.0 + prob>=0.4 / std<=0.5", 0.30 * 0.330 * 48.8 / 37.2),
                        ("auth 0.0, perception gate open", 0.30),
                        ("auth 0.0, gate open, _MAX_GAIN 0.60", 0.60)):
            tr = _sim(16.0, 0.0, e0=e0, lead=1.0, gain=G)
            pr("  %-40s %7.3f %8.3f %8.3f %8.3f %8.3f %8.3f" %
               (name, G, tr[200], tr[290], tr[440], tr[620], tr[1200]))
    pr("  NOTE the 'shipped' row LINEARISES the fade into G_eff.  At |err| >= 0.50 m the shipped")
    pr("  configuration is EXACTLY zero (break_in = 1, kept = 0), so at e0 = 0.59 the true shipped")
    pr("  trajectory is a flat line at 0.59 m -- the loop cannot move at all until something else")
    pr("  brings the error under 0.50 m.")


def sec_straights():
    pr("=" * 168)
    pr("SECTION J -- THE STRAIGHT-LINE LEVER.  On straights the e2e fade barely bites (|err| ~ 0.12 m,")
    pr("  break_in ~ 0) and the perception gates pass far more often, so `LaneCenterOffset` is LIVE")
    pr("  there.  Mean applied correction and the lateral accel it buys, vs the offset asked for.")
    pr("=" * 168)
    pr("  %-6s %8s %9s | %10s %9s %11s %7s %10s" %
       ("route", "secs", "ALL PASS", "LaneCentOff", "med kept", "mean corr", "zero%", "cm/s^2"))
    for tag in TAGS:
        f = build(tag)
        ok = _allp(f)
        hard = _hard(f)
        st = f["eng"] & (np.abs(f["k_road"]) < 0.0008) & (f["v"] >= MIN_V_EGO) & np.isfinite(f["lc_err"])
        for off in (0.0, 0.12, 0.25):
            tgt, _, kept, _ = raw_correction(f, off, 1.0)
            A = replay(tgt, ok, hard)
            mc = np.nanmean(A[st])
            pr("  %-6s %8.1f %8.1f%% | %10.2f %9.3f %11.6f %6.0f%% %10.3f" % (
                tag, st.sum() * DT, 100.0 * (st & ok).sum() / st.sum(), off,
                np.nanmedian(kept[st]), mc, 100 * (np.abs(A[st]) < 1e-9).mean(),
                100 * mc * np.nanmean(f["v"][st]) ** 2))
    pr("  +LaneCenterOffset moves the TARGET right, so it moves the CAR right (:130, +y = RIGHT).")
    pr("  It SELF-LIMITS: asking for more inflates |error| into the e2e break-in and `kept` collapses,")
    pr("  so 0.25 buys no more than 0.12.")


def main():
    sec_gates()
    sec_perception()
    sec_clamps()
    sec_clip_speed()
    sec_pathstd()
    sec_lead()
    sec_sim_valid()
    sec_authority()
    sec_sim()
    sec_offsets()
    sec_replay()
    sec_straights()
    sec_signal()
    with open(os.path.join(P.SCR, "lane_centering_levers_out.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
