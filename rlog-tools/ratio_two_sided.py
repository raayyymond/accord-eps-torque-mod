#!/usr/bin/env python3
r"""PER-SIDE (UNFOLDED) steering-ratio curves, and the ONE question that decides them:
is the LEFT/RIGHT LEVEL difference REAL, or an artefact of the fitted centre offset theta0?

EXTENDS `ratio_final2.py` -- same corpus, same masks, same v_ref (REAR AXLE), same block
bootstrap.  Nothing about the established method is re-litigated here.

🛑 SIGN CONVENTION -- STATED, THEN VERIFIED (see `sign_sanity`).
   SENSOR frame (operator-confirmed):  steeringAngleDeg > theta0  =  LEFT turn
                                       steeringAngleDeg < theta0  =  RIGHT turn
   Vehicle yaw, positive-left, yaw_A = -avz  (device z is DOWN).
   ⇒ on a LEFT turn we must observe  yaw_A > 0  AND  (ws_rr - ws_rl) > 0  (right rear is OUTER).
   Both are asserted numerically before any curve is built.

   The output carries THREE angle axes so nothing can be silently swapped:
     theta          = |theta - theta0|, the folded axis (identical bins to final2.json)
     theta_sensor   = SIGNED in the SENSOR frame  (LEFT +, RIGHT -)   <- physically correct
     theta_plot     = signed as the brief asked    (LEFT -, RIGHT +)  <- = -theta_sensor

WHY theta0 IS THE PRIME SUSPECT: a centre-offset error moves the two sides in OPPOSITE
directions, so it is exactly the shape of a spurious left/right split.  Test = sweep it.
   If some theta0 in the plausible range makes the sides COINCIDE -> artefact.
   If the difference is flat, or is minimised nowhere near zero  -> real.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_steering_ratio as M  # noqa: E402
import ratio_final2 as F2           # noqa: E402
import ratio_lib as R               # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_cache_ratio"
BINS = M.BINS
SIDES = ((+1, "LEFT"), (-1, "RIGHT"))


# ======================================================================================
#  0.  SIGN SANITY -- assert the mapping before anything depends on it
# ======================================================================================
def sign_sanity(A, th0, prim):
    """Everything downstream is a left/right claim, so the mapping is CHECKED, not assumed."""
    thc = A["s_ang"] - th0
    o = {}
    for sgn, lab in SIDES:
        q = prim & (np.sign(thc) == sgn) & (np.abs(thc) > 50)
        o[lab] = {"n": int(q.sum()),
                  "median_yawA_pos_left": float(np.median(A["yawA0"][q])),
                  "median_ws_rr_minus_rl": float(np.median((A["ws_rr"] - A["ws_rl"])[q])),
                  "median_delta_A_deg": float(np.median(
                      np.degrees(np.arctan(A["yawA0"][q] * R.L_WB / A["v_ref"][q]))))}
    ok = (o["LEFT"]["median_yawA_pos_left"] > 0 > o["RIGHT"]["median_yawA_pos_left"]
          and o["LEFT"]["median_ws_rr_minus_rl"] > 0 > o["RIGHT"]["median_ws_rr_minus_rl"])
    o["PASS"] = bool(ok)
    print("\n=== SIGN SANITY (|theta-theta0| > 50 deg) ===")
    for lab in ("LEFT", "RIGHT"):
        d = o[lab]
        print(f"  {lab:5s} n={d['n']:6d}  yaw(+left) {d['median_yawA_pos_left']:+.4f} rad/s   "
              f"(ws_rr-ws_rl) {d['median_ws_rr_minus_rl']:+.4f} m/s   "
              f"delta {d['median_delta_A_deg']:+6.2f} deg")
    print(f"  mapping (sensor angle > theta0 == LEFT):  {'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit("sign mapping FAILED -- refusing to produce left/right curves")
    return o


# ======================================================================================
#  1.  PER-SIDE CURVE + LEVEL SCALARS
# ======================================================================================
def side_curve(thc, d, sgn, bins=BINS):
    """Curve for ONE side, on |theta| bins.  Multiply BOTH channels by the side sign so this is
    literally the folded pipeline restricted to one side -- no second code path."""
    q = np.sign(thc) == sgn
    return M.curve_from(thc[q] * sgn, d[q] * sgn, bins, fold=False), q


def levels(ta, loc):
    """Level scalars on the LOCAL ratio.  `geo` is deliberately left to the caller to compute on a
    COMMON bin set, so a bin missing on one side cannot fake a level difference."""
    def med(m):
        v = loc[m & np.isfinite(loc)]
        return float(np.median(v)) if v.size else np.nan
    o = {"near_3_20": med((ta >= 3) & (ta < 20)),
         "floor_3_50": med((ta >= 3) & (ta < 50)),
         "mid_50_120": med((ta >= 50) & (ta < 120)),
         "ref120": med((ta >= 105) & (ta < 165)),
         "lock_320": med(ta >= 320)}
    o["swing_0_120"] = o["floor_3_50"] / o["ref120"]        # the SHAPE statistic
    o["droop_120_380"] = o["ref120"] / o["lock_320"]
    return o


LEVEL_KEYS = ("near_3_20", "floor_3_50", "mid_50_120", "ref120", "lock_320",
              "swing_0_120", "droop_120_380")


OUTER_I = 13          # BINS index whose left edge is 105 deg -- indices 13..18 are the OUTER region


def geo_common(locL, locR, sl=None):
    """Geometric-mean level ratio L/R over bins finite on BOTH sides.  `sl` restricts to a BIN-INDEX
    slice (stable across bootstrap reps, unlike a cut on the bin's median theta)."""
    a = np.asarray(locL, float); b = np.asarray(locR, float)
    if sl is not None:
        a, b = a[sl], b[sl]
    q = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    if q.sum() < 3:
        return np.nan, 0
    return float(np.exp(np.mean(np.log(a[q] / b[q])))), int(q.sum())


def blocks_of(blk):
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    b = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    return [order[b[i]:b[i + 1]] for i in range(len(ub))]


def two_sided(A, m, th0, dlt, nboot=800, seed=17, bins=BINS):
    """Both sides + their DIFFERENCE, from ONE PAIRED block bootstrap (blocks resampled jointly,
    so the difference CI is paired and not the difference of two independent CIs)."""
    thc = (A["s_ang"] - th0)[m]
    d = dlt[m]
    by = blocks_of(A["blk"][m])

    res = {}
    curves = {}
    for sgn, lab in SIDES:
        (ta, sec, loc, nn), q = side_curve(thc, d, sgn, bins)
        curves[lab] = (ta, loc)
        res[lab] = {"theta": ta.tolist(), "local": loc.tolist(), "secant": sec.tolist(),
                    "n_bin": nn.tolist(), "seconds": float(q.sum() * R.DT),
                    "levels": levels(ta, loc)}
    g, nb = geo_common(curves["LEFT"][1], curves["RIGHT"][1])
    gi, nbi = geo_common(curves["LEFT"][1], curves["RIGHT"][1], slice(0, OUTER_I))
    go, nbo = geo_common(curves["LEFT"][1], curves["RIGHT"][1], slice(OUTER_I, None))
    diff_pt = {"geo_L_over_R": g, "geo_inner_L_over_R": gi, "geo_outer_L_over_R": go,
               "n_common_bins": nb, "n_inner_bins": nbi, "n_outer_bins": nbo}
    for k in res["LEFT"]["levels"]:
        diff_pt[k + "_L_over_R"] = res["LEFT"]["levels"][k] / res["RIGHT"]["levels"][k]

    rng = np.random.default_rng(seed)
    accL = {"local": [], "secant": []}
    accR = {"local": [], "secant": []}
    accD = {k: [] for k in diff_pt if not k.startswith("n_")}
    accLR = []                                     # per-bin log ratio L/R
    for _ in range(nboot):
        sel = np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])
        t2, l2 = {}, {}
        for sgn, lab in SIDES:
            (ta, sec, loc, _), _ = side_curve(thc[sel], d[sel], sgn, bins)
            t2[lab], l2[lab] = ta, loc
            (accL if lab == "LEFT" else accR)["local"].append(loc)
            (accL if lab == "LEFT" else accR)["secant"].append(sec)
        for key, sl in (("geo_L_over_R", None), ("geo_inner_L_over_R", slice(0, OUTER_I)),
                        ("geo_outer_L_over_R", slice(OUTER_I, None))):
            gg, _ = geo_common(l2["LEFT"], l2["RIGHT"], sl)
            if np.isfinite(gg):
                accD[key].append(gg)
        lvL = levels(t2["LEFT"], l2["LEFT"])
        lvR = levels(t2["RIGHT"], l2["RIGHT"])
        for k in LEVEL_KEYS:
            a, b = lvL[k], lvR[k]
            if np.isfinite(a) and np.isfinite(b) and b > 0:
                accD[k + "_L_over_R"].append(a / b)
        with np.errstate(invalid="ignore", divide="ignore"):
            accLR.append(np.log(l2["LEFT"] / l2["RIGHT"]))

    def ci(arr):
        A_ = np.array(arr, float)
        with np.errstate(invalid="ignore"):
            return (np.nanpercentile(A_, 2.5, axis=0), np.nanpercentile(A_, 97.5, axis=0))

    for lab, acc in (("LEFT", accL), ("RIGHT", accR)):
        lo, hi = ci(acc["local"])
        res[lab]["local_lo"], res[lab]["local_hi"] = lo.tolist(), hi.tolist()
        lo, hi = ci(acc["secant"])
        res[lab]["secant_lo"], res[lab]["secant_hi"] = lo.tolist(), hi.tolist()
    lo, hi = ci(accLR)
    res["per_bin_log_L_over_R"] = {
        "theta": res["LEFT"]["theta"],
        "point": np.log(np.array(curves["LEFT"][1]) / np.array(curves["RIGHT"][1])).tolist(),
        "lo": lo.tolist(), "hi": hi.tolist()}
    res["difference"] = {k: {"point": float(diff_pt[k]),
                             "ci95": [float(np.percentile(accD[k], 2.5)),
                                      float(np.percentile(accD[k], 97.5))]}
                         for k in accD if len(accD[k]) > 20}
    res["difference"] |= {"n_common_bins": nb, "n_inner_bins": nbi, "n_outer_bins": nbo}
    res["n_blocks"] = len(by)
    return res


# ======================================================================================
#  2.  PER-SIDE theta0 -- refit INDEPENDENTLY on each side
# ======================================================================================
def fit_theta0_side(A, sgn, th0_ref, lo_deg=2.0, hi_deg=25.0):
    """delta(theta) crosses zero at theta0.  Using ONE side only makes this an EXTRAPOLATION to
    the crossing, so the CI is honestly wide -- that is the point, not a defect."""
    thc = A["s_ang"] - th0_ref
    ests, rows = [], []
    for lo, hi in ((1, 5), (5, 12), (12, 20), (20, 40)):
        m = (R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
             & (np.sign(thc) == sgn) & (np.abs(thc) >= lo_deg) & (np.abs(thc) <= hi_deg))
        if m.sum() < 500:
            continue
        d = M.delta_deg(A["yawA0"][m], A["v_ref"][m])
        p = np.polyfit(A["s_ang"][m], d, 1)
        z = float(-p[1] / p[0])
        ests.append(z)
        rows.append({"v_lo": lo, "v_hi": hi, "n": int(m.sum()), "theta0": z,
                     "local_ratio": float(1 / p[0])})
    return (float(np.median(ests)) if ests else np.nan), rows


def fit_theta0_side_boot(A, sgn, th0_ref, nboot=300, seed=23):
    """Block bootstrap on the one-sided theta0 fit."""
    thc = A["s_ang"] - th0_ref
    bands = ((1, 5), (5, 12), (12, 20), (20, 40))
    masks = [(R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A) & (np.sign(thc) == sgn)
              & (np.abs(thc) >= 2.0) & (np.abs(thc) <= 25.0)) for lo, hi in bands]
    idxs = [np.flatnonzero(mm) for mm in masks]
    idxs = [i for i in idxs if len(i) >= 500]
    blk = A["blk"]
    rng = np.random.default_rng(seed)
    outs = []
    for _ in range(nboot):
        ests = []
        for ii in idxs:
            by = blocks_of(blk[ii])
            sel = ii[np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])]
            d = M.delta_deg(A["yawA0"][sel], A["v_ref"][sel])
            p = np.polyfit(A["s_ang"][sel], d, 1)
            if abs(p[0]) > 1e-9:
                ests.append(-p[1] / p[0])
        if ests:
            outs.append(float(np.median(ests)))
    return [float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5))]


# ======================================================================================
#  3.  ⭐ THE theta0 SWEEP -- the test that decides artefact vs real
# ======================================================================================
def theta0_sweep(A, m, dlt, grid):
    """For each candidate theta0, rebuild BOTH sides from scratch and report the L/R level ratio.
    A centre-offset error biases the sides in OPPOSITE directions, so if the asymmetry is an
    offset artefact there MUST be a theta0 in the plausible range at which it vanishes."""
    ang = A["s_ang"][m]
    d = dlt[m]
    rows = []
    for t0 in grid:
        thc = ang - t0
        cur = {}
        for sgn, lab in SIDES:
            (ta, sec, loc, nn), _ = side_curve(thc, d, sgn)
            cur[lab] = (ta, loc)
        g, nb = geo_common(cur["LEFT"][1], cur["RIGHT"][1])
        gi, _ = geo_common(cur["LEFT"][1], cur["RIGHT"][1], slice(0, OUTER_I))
        go, _ = geo_common(cur["LEFT"][1], cur["RIGHT"][1], slice(OUTER_I, None))
        lv = {lab: levels(*cur[lab]) for lab in ("LEFT", "RIGHT")}
        rows.append({"theta0": float(t0), "geo_L_over_R": g, "n_common_bins": nb,
                     "geo_inner_L_over_R": gi, "geo_outer_L_over_R": go,
                     **{f"{k}_L_over_R": float(lv["LEFT"][k] / lv["RIGHT"][k])
                        for k in lv["LEFT"]},
                     **{f"LEFT_{k}": float(lv["LEFT"][k]) for k in lv["LEFT"]},
                     **{f"RIGHT_{k}": float(lv["RIGHT"][k]) for k in lv["RIGHT"]}})
    return rows


# ======================================================================================
#  4.  CONFOUNDS
# ======================================================================================
def speed_matched(A, m, th0, dlt, bins=BINS,
                  vsub=(1.0, 1.75, 2.25, 2.75, 3.25, 4.0, 5.0)):
    """EXPOSURE MATCHING.  Within every |theta| bin, recompute each side's median delta as a
    weighted combination over SPEED sub-bins with weights COMMON to both sides (w = min(nL,nR)),
    and use a COMMON theta per bin (pooled median) so the numerator of the local ratio is
    identical for the two sides.  Any surviving difference is in delta alone."""
    thc = (A["s_ang"] - th0)[m]
    d = dlt[m]
    v = A["v_ref"][m]
    vb = np.digitize(v, np.array(vsub[1:-1], float))
    a = np.abs(thc)
    sg = np.sign(thc)
    ta, tdL, tdR, wtot = [], [], [], []
    for i in range(len(bins) - 1):
        q = (a >= bins[i]) & (a < bins[i + 1])
        if q.sum() < 50:
            ta.append(np.nan); tdL.append(np.nan); tdR.append(np.nan); wtot.append(0); continue
        ta.append(float(np.median(a[q])))
        num = {+1: 0.0, -1: 0.0}
        den = 0.0
        for j in np.unique(vb[q]):
            qq = q & (vb == j)
            med, n = {}, {}
            for sgn in (+1, -1):
                s = qq & (sg == sgn)
                n[sgn] = int(s.sum())
                med[sgn] = float(np.median(np.abs(d[s]))) if n[sgn] >= 15 else np.nan
            w = min(n[+1], n[-1])
            if w >= 15 and np.isfinite(med[+1]) and np.isfinite(med[-1]):
                num[+1] += w * med[+1]; num[-1] += w * med[-1]; den += w
        if den == 0:
            tdL.append(np.nan); tdR.append(np.nan); wtot.append(0); continue
        tdL.append(num[+1] / den); tdR.append(num[-1] / den); wtot.append(int(den))
    ta = np.array(ta)

    def loc_of(td):
        td = np.array(td, float)
        loc = np.full(len(ta), np.nan)
        for i in range(len(ta)):
            j, k = max(0, i - 1), min(len(ta) - 1, i + 1)
            if np.isfinite(ta[j]) and np.isfinite(ta[k]) and k > j:
                dd = td[k] - td[j]
                loc[i] = (ta[k] - ta[j]) / dd if abs(dd) > 1e-9 else np.nan
        return loc
    lL, lR = loc_of(tdL), loc_of(tdR)
    g, nb = geo_common(lL, lR)
    return {"theta": ta.tolist(), "local_LEFT": lL.tolist(), "local_RIGHT": lR.tolist(),
            "w_bin": wtot, "geo_L_over_R": g, "n_common_bins": nb,
            "levels_LEFT": levels(ta, lL), "levels_RIGHT": levels(ta, lR)}


def exposure_per_side(A, m, th0):
    thc = (A["s_ang"] - th0)[m]
    v = A["v_ref"][m]
    ab = [0, 5, 20, 50, 120, 400]
    vbb = [1, 2, 3, 4, 5]
    o = {}
    for sgn, lab in SIDES:
        q = np.sign(thc) == sgn
        H, _, _ = np.histogram2d(np.abs(thc[q]), v[q], bins=[ab, vbb])
        o[lab] = {"seconds": float(q.sum() * R.DT),
                  "median_v": float(np.median(v[q])),
                  "median_abs_theta": float(np.median(np.abs(thc[q]))),
                  "grid_seconds": (H * R.DT).round(1).tolist()}
    o["angle_bins"], o["speed_bins"] = ab, vbb
    return o


def inject_control(A, m, th0, dlt, f, nboot=400, seed=51):
    """⭐ POSITIVE CONTROL / POWER.  Scale the RIGHT side's delta by `f`, which multiplies the
    TRUE L/R ratio by exactly `f`, and push it through the IDENTICAL pipeline.  f = 1.00 is the
    negative control.  This answers "could this design SEE a 5 % split if there were one?" --
    without it a null over the L/R difference is uninterpretable."""
    d = dlt.copy()
    q = (A["s_ang"] - th0) < 0
    d[q] = d[q] * f
    t = two_sided(A, m, th0, d, nboot=nboot, seed=seed)
    return {"f": f, "expected_geo_L_over_R_multiplier": f,
            "difference": t["difference"]}


def route_heterogeneity(A, m, th0, dlt, min_s=60.0, nboot=200, seed=61):
    """Cochran's Q on the per-route L/R level: is the between-route spread larger than each
    route's OWN block-bootstrap noise?  Road crown is a property of the ROAD and must be
    heterogeneous; a rack asymmetry must not be."""
    thc = (A["s_ang"] - th0)[m]
    d = dlt[m]
    rt = A["route"][m]
    blk = A["blk"][m]
    rng = np.random.default_rng(seed)
    rows = []
    for r in np.unique(rt):
        q = np.flatnonzero(rt == r)
        if len(q) * R.DT < min_s:
            continue
        cur = {}
        for sgn, lab in SIDES:
            (ta, sec, loc, nn), _ = side_curve(thc[q], d[q], sgn)
            cur[lab] = loc
        g, nb = geo_common(cur["LEFT"], cur["RIGHT"])
        if not (np.isfinite(g) and nb >= 4):
            continue
        by = blocks_of(blk[q])
        outs = []
        for _ in range(nboot):
            sel = q[np.concatenate([by[p] for p in rng.integers(0, len(by), len(by))])]
            c2 = {}
            for sgn, lab in SIDES:
                (t2, s2, l2, _), _ = side_curve(thc[sel], d[sel], sgn)
                c2[lab] = l2
            gg, _ = geo_common(c2["LEFT"], c2["RIGHT"])
            if np.isfinite(gg):
                outs.append(np.log(gg))
        if len(outs) < 30:
            continue
        rows.append({"route": f"{int(r):08x}", "seconds": float(len(q) * R.DT),
                     "n_common_bins": nb, "geo_L_over_R": g,
                     "log_geo": float(np.log(g)), "se_log": float(np.std(outs, ddof=1)),
                     "ci95": [float(np.exp(np.percentile(outs, 2.5))),
                              float(np.exp(np.percentile(outs, 97.5)))]})
    if len(rows) < 3:
        return rows, {}
    y = np.array([r["log_geo"] for r in rows])
    s = np.array([r["se_log"] for r in rows])
    w = 1.0 / s ** 2
    ybar = float(np.sum(w * y) / np.sum(w))
    Q = float(np.sum(w * (y - ybar) ** 2))
    df = len(rows) - 1
    return rows, {"pooled_geo": float(np.exp(ybar)), "Q": Q, "df": df, "Q_over_df": Q / df,
                  "verdict": ("HETEROGENEOUS across routes (Q/df > 2) -- road-dependent"
                              if Q / df > 2 else
                              "HOMOGENEOUS across routes (Q/df <= 2) -- no road dependence seen")}


def per_route(A, m, th0, dlt, min_s=60.0):
    """CROWN / ROAD test.  Road camber is a property of the ROAD; a rack asymmetry is not.
    A crown-driven level split must VARY across routes; a rack one must not."""
    thc = (A["s_ang"] - th0)[m]
    d = dlt[m]
    rt = A["route"][m]
    rows = []
    for r in np.unique(rt):
        q = rt == r
        if q.sum() * R.DT < min_s:
            continue
        cur = {}
        for sgn, lab in SIDES:
            (ta, sec, loc, nn), _ = side_curve(thc[q], d[q], sgn)
            cur[lab] = loc
        g, nb = geo_common(cur["LEFT"], cur["RIGHT"])
        if np.isfinite(g) and nb >= 4:
            rows.append({"route": f"{int(r):08x}", "seconds": float(q.sum() * R.DT),
                         "n_common_bins": nb, "geo_L_over_R": g})
    return rows


# ======================================================================================
def main():
    A = M.prep()
    M.qa(A)
    A["v_front"] = R.smooth_blocks(A, 0.5 * (A["ws_fl"] + A["ws_fr"]), 0.5)
    gam = F2.gamma_front_rear(A)
    th0 = M.fit_theta0(A, "A")
    D = F2.deltas(A, gam)
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)

    OUTJ = {"theta0_joint": th0, "gamma_front_rear": gam,
            "sign_convention": {
                "sensor": "steeringAngleDeg > theta0 == LEFT turn (operator-confirmed)",
                "theta_sensor": "signed, SENSOR frame: LEFT positive, RIGHT negative",
                "theta_plot": "signed as the brief asked: LEFT NEGATIVE, RIGHT POSITIVE "
                              "(= -theta_sensor); use theta_sensor for anything physical"}}
    OUTJ["sign_sanity"] = sign_sanity(A, th0, prim)

    # ---------------- the two curves
    print("\n" + "=" * 100)
    print("  PER-SIDE LOCAL RATIO CURVES (estimator A, v 1-5 m/s, paired block bootstrap)")
    print("=" * 100)
    T = two_sided(A, prim, th0, D["A"], nboot=800)
    for sgn, lab in SIDES:
        s = T[lab]
        s["theta_sensor"] = [(t * sgn if np.isfinite(t) else None) for t in s["theta"]]
        s["theta_plot"] = [(-t * sgn if np.isfinite(t) else None) for t in s["theta"]]
    OUTJ["curves"] = {k: T[k] for k in ("LEFT", "RIGHT")}
    OUTJ["per_bin_log_L_over_R"] = T["per_bin_log_L_over_R"]
    OUTJ["difference"] = T["difference"]
    OUTJ["n_blocks_primary"] = T["n_blocks"]

    print("\n  |th|deg |          LEFT  local  [95% CI]      n |         RIGHT  local  [95% CI]"
          "      n |  L/R   [95% CI]")
    L, Rt = T["LEFT"], T["RIGHT"]
    lr = T["per_bin_log_L_over_R"]
    for i, t in enumerate(L["theta"]):
        if not np.isfinite(t):
            continue
        def f(s, i):
            return (f"{s['local'][i]:7.2f} [{s['local_lo'][i]:6.2f},{s['local_hi'][i]:6.2f}] "
                    f"{s['n_bin'][i]:6d}") if np.isfinite(s["local"][i]) else " " * 31
        rat = np.exp(lr["point"][i]) if np.isfinite(lr["point"][i]) else np.nan
        rlo, rhi = np.exp(lr["lo"][i]), np.exp(lr["hi"][i])
        print(f"  {t:7.1f} | {f(L,i)} | {f(Rt,i)} | {rat:6.3f} [{rlo:.3f},{rhi:.3f}]")

    print("\n  LEVELS (local ratio)         LEFT     RIGHT     L/R      [95% CI]")
    for k in LEVEL_KEYS:
        dd = T["difference"].get(k + "_L_over_R")
        print(f"    {k:14s} {L['levels'][k]:9.3f} {Rt['levels'][k]:9.3f} "
              f"{dd['point']:8.4f}  [{dd['ci95'][0]:.4f}, {dd['ci95'][1]:.4f}]")
    g = T["difference"]["geo_L_over_R"]
    for lab, key, nk in (("geo(all bins)", "geo_L_over_R", "n_common_bins"),
                         ("geo(<105 deg)", "geo_inner_L_over_R", "n_inner_bins"),
                         ("geo(>=105 deg)", "geo_outer_L_over_R", "n_outer_bins")):
        d_ = T["difference"][key]
        print(f"    {lab:14s} {'':9s} {'':9s} {d_['point']:8.4f}  "
              f"[{d_['ci95'][0]:.4f}, {d_['ci95'][1]:.4f}]   over "
              f"{T['difference'][nk]} bins")

    # ---------------- per-side theta0
    print("\n=== PER-SIDE theta0, REFITTED INDEPENDENTLY ===")
    OUTJ["theta0_per_side"] = {}
    for sgn, lab in SIDES:
        z, rows = fit_theta0_side(A, sgn, th0)
        ci = fit_theta0_side_boot(A, sgn, th0)
        OUTJ["theta0_per_side"][lab] = {"theta0": z, "ci95": ci, "per_band": rows}
        print(f"  {lab:5s} theta0 = {z:+.3f} deg  [{ci[0]:+.3f}, {ci[1]:+.3f}]   "
              f"(bands: " + ", ".join(f"{r['v_lo']}-{r['v_hi']}:{r['theta0']:+.2f}"
                                      for r in rows) + ")")
    zl = OUTJ["theta0_per_side"]["LEFT"]["theta0"]
    zr = OUTJ["theta0_per_side"]["RIGHT"]["theta0"]
    print(f"  joint fit {th0:+.3f}   |LEFT - RIGHT| = {abs(zl - zr):.3f} deg   "
          f"midpoint {(zl + zr) / 2:+.3f}")

    # a one-sided fit is an EXTRAPOLATION along a chord; on a curved delta(theta) the two chords
    # must split SYMMETRICALLY about the true centre, and the split must SHRINK as the window
    # narrows.  If it does not shrink, the split is an on-centre asymmetry, not a fit artefact.
    print("\n  window test -- does the L/R theta0 split shrink as the fit window narrows?")
    OUTJ["theta0_per_side_window"] = []
    for hi in (8.0, 12.0, 18.0, 25.0, 40.0):
        zs = {lab: fit_theta0_side(A, sgn, th0, hi_deg=hi)[0] for sgn, lab in SIDES}
        OUTJ["theta0_per_side_window"].append(
            {"window_hi_deg": hi, "LEFT": zs["LEFT"], "RIGHT": zs["RIGHT"],
             "split": zs["LEFT"] - zs["RIGHT"], "midpoint": (zs["LEFT"] + zs["RIGHT"]) / 2})
        print(f"    |theta-theta0| <= {hi:4.0f} deg:  LEFT {zs['LEFT']:+.3f}  "
              f"RIGHT {zs['RIGHT']:+.3f}   split {zs['LEFT'] - zs['RIGHT']:+.3f}   "
              f"midpoint {(zs['LEFT'] + zs['RIGHT']) / 2:+.3f}")

    # ---------------- ⭐ the sweep
    print("\n" + "=" * 100)
    print("  ⭐ theta0 SWEEP -- does ANY plausible centre make the two sides coincide?")
    print("=" * 100)
    grid = np.round(np.arange(-7.0, -1.4, 0.25), 3)
    sw = theta0_sweep(A, prim, D["A"], grid)
    OUTJ["theta0_sweep"] = sw
    print("   theta0 |  geo ALL | geo INNER | geo OUTER | floor3-50 |  ref120 | lock320 | bins")
    for r in sw:
        mark = "  <- joint fit" if abs(r["theta0"] - th0) < 0.13 else ""
        print(f"  {r['theta0']:+7.2f} | {r['geo_L_over_R']:8.4f} | "
              f"{r['geo_inner_L_over_R']:9.4f} | {r['geo_outer_L_over_R']:9.4f} |"
              f" {r['floor_3_50_L_over_R']:9.4f} |"
              f" {r['ref120_L_over_R']:7.4f} | {r['lock_320_L_over_R']:7.4f} |"
              f" {r['n_common_bins']:4d}{mark}")
    OUTJ["theta0_sweep_summary"] = {"grid": grid.tolist()}
    for key in ("geo_L_over_R", "geo_inner_L_over_R", "geo_outer_L_over_R"):
        geo = np.array([r[key] for r in sw])
        i = int(np.nanargmin(np.abs(np.log(geo))))
        print(f"  {key:22s}  minimised at theta0 = {grid[i]:+.2f} deg (value {geo[i]:.4f});  "
              f"sweep range {np.nanmin(geo):.4f} .. {np.nanmax(geo):.4f}")
        OUTJ["theta0_sweep_summary"][key] = {
            "theta0_minimising_asymmetry": float(grid[i]), "value_at_min": float(geo[i]),
            "sweep_range": [float(np.nanmin(geo)), float(np.nanmax(geo))],
            "crosses_1_in_range": bool(np.nanmin(geo) < 1 < np.nanmax(geo))}

    # ---------------- ⭐ POWER: can this design see a split at all?
    print("\n" + "=" * 100)
    print("  ⭐ POWER / POSITIVE CONTROL -- inject a KNOWN L/R split and try to recover it")
    print("=" * 100)
    OUTJ["inject_control"] = []
    for f in (1.00, 0.98, 0.95, 0.90):
        ic = inject_control(A, prim, th0, D["A"], f, nboot=400)
        OUTJ["inject_control"].append(ic)
        print(f"  inject f={f:.2f}   (truth = observed x {f:.2f})")
        for lab, key in (("geo all   ", "geo_L_over_R"), ("geo inner ", "geo_inner_L_over_R"),
                         ("geo outer ", "geo_outer_L_over_R"), ("ref120    ", "ref120_L_over_R"),
                         ("lock_320  ", "lock_320_L_over_R")):
            q = ic["difference"][key]
            sig = "CI EXCLUDES 1" if not (q["ci95"][0] <= 1 <= q["ci95"][1]) else "covers 1"
            print(f"      {lab} {q['point']:7.4f} [{q['ci95'][0]:.4f},{q['ci95'][1]:.4f}]  {sig}")

    # ---------------- confound: other estimators (does the split need the IMU?)
    print("\n=== CONFOUND -- OTHER ESTIMATORS (A/D use the IMU; B/C do NOT) ===")
    OUTJ["estimators"] = {}
    for k in ("A", "D", "B", "C"):
        mm = prim
        if k == "B":
            mm = prim & (A["v_ref"] > 2.0)
        if k == "C":
            mm = prim & (np.abs(A["s_ang"] - th0) >= 60)
        t = two_sided(A, mm, th0, D[k], nboot=400, seed=41)
        OUTJ["estimators"][k] = {"difference": t["difference"],
                                 "levels_LEFT": t["LEFT"]["levels"],
                                 "levels_RIGHT": t["RIGHT"]["levels"]}
        gg = t["difference"].get("geo_L_over_R", {})
        go = t["difference"].get("geo_outer_L_over_R", {})
        print(f"  {k}: geo ALL {gg.get('point', float('nan')):.4f} "
              f"{np.round(gg.get('ci95', [np.nan, np.nan]), 4).tolist()}   "
              f"geo OUTER {go.get('point', float('nan')):.4f} "
              f"{np.round(go.get('ci95', [np.nan, np.nan]), 4).tolist()}")

    # ---------------- confound: additive delta bias (kills SECANT, cancels in LOCAL)
    print("\n=== CONFOUND -- ADDITIVE delta BIAS (a residual yaw bias shows in SECANT, "
          "cancels in LOCAL) ===")
    secL = np.array(L["secant"], float); secR = np.array(Rt["secant"], float)
    gs, nbs = geo_common(secL, secR)
    OUTJ["secant_geo_L_over_R"] = {"point": gs, "n_common_bins": nbs}
    print(f"  local  geo L/R = {g['point']:.4f}      secant geo L/R = {gs:.4f}  ({nbs} bins)")

    # ---------------- confound: exposure
    print("\n=== CONFOUND -- EXPOSURE per side ===")
    ex = exposure_per_side(A, prim, th0)
    OUTJ["exposure"] = ex
    for lab in ("LEFT", "RIGHT"):
        print(f"  {lab:5s} {ex[lab]['seconds']:7.1f} s   median v {ex[lab]['median_v']:.2f} m/s  "
              f"median |theta| {ex[lab]['median_abs_theta']:.1f} deg")
        print("        angle x speed seconds " + str(ex[lab]["grid_seconds"]))
    sm = speed_matched(A, prim, th0, D["A"])
    OUTJ["speed_matched"] = sm
    print(f"  SPEED-MATCHED + COMMON-theta rebuild:  geo L/R = {sm['geo_L_over_R']:.4f} "
          f"({sm['n_common_bins']} bins)   "
          f"ref120 L {sm['levels_LEFT']['ref120']:.2f} / R {sm['levels_RIGHT']['ref120']:.2f}   "
          f"lock L {sm['levels_LEFT']['lock_320']:.2f} / R {sm['levels_RIGHT']['lock_320']:.2f}")
    print("    per-bin (matched):  |th|   L_local   R_local   L/R    weight")
    for i, t in enumerate(sm["theta"]):
        if not np.isfinite(t) or not np.isfinite(sm["local_LEFT"][i]):
            continue
        print(f"                      {t:6.1f} {sm['local_LEFT'][i]:9.2f} "
              f"{sm['local_RIGHT'][i]:9.2f} "
              f"{sm['local_LEFT'][i] / sm['local_RIGHT'][i]:7.3f} {sm['w_bin'][i]:7d}")

    # ---------------- confound: the OUTER region's own speed imbalance
    # In the >120 deg row the two sides are NOT matched in speed (LEFT sits at 1-2 m/s, RIGHT is
    # spread to 5).  Front-tyre slip grows with speed and DEPRESSES the achieved yaw, which
    # INFLATES the apparent ratio -- so the faster-driven side reads slower.  That is exactly the
    # sign of the observed residual, so it must be tested INSIDE narrow speed bands.
    print("\n=== CONFOUND -- OUTER-REGION SPEED IMBALANCE (narrow speed bands) ===")
    OUTJ["outer_speed_bands"] = {}
    for lo, hi in ((1.0, 2.0), (2.0, 3.0), (1.0, 3.0), (3.0, 5.0)):
        mm = R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
        t = two_sided(A, mm, th0, D["A"], nboot=400, seed=47)
        go = t["difference"].get("geo_outer_L_over_R", {})
        ga = t["difference"].get("geo_L_over_R", {})
        OUTJ["outer_speed_bands"][f"{lo}-{hi}"] = {
            "geo_all": ga, "geo_outer": go,
            "seconds_LEFT": t["LEFT"]["seconds"], "seconds_RIGHT": t["RIGHT"]["seconds"],
            "n_outer_bins": t["difference"].get("n_outer_bins")}
        print(f"  v {lo}-{hi} m/s  L {t['LEFT']['seconds']:6.0f} s / R "
              f"{t['RIGHT']['seconds']:6.0f} s   geo ALL {ga.get('point', float('nan')):.4f} "
              f"{np.round(ga.get('ci95', [np.nan, np.nan]), 4).tolist()}   "
              f"geo OUTER {go.get('point', float('nan')):.4f} "
              f"{np.round(go.get('ci95', [np.nan, np.nan]), 4).tolist()} "
              f"({t['difference'].get('n_outer_bins')} bins)")

    # ---------------- confound: engaged vs manual
    print("\n=== CONFOUND -- ENGAGED vs MANUAL, per side ===")
    OUTJ["engaged_manual"] = {}
    for lab, mm in (("ENGAGED", prim & (A["lat"] > 0.5)), ("MANUAL", prim & (A["lat"] < 0.5))):
        if mm.sum() < 2000:
            print(f"  {lab}: {mm.sum() * R.DT:.0f} s -- NO POWER")
            OUTJ["engaged_manual"][lab] = {"seconds": float(mm.sum() * R.DT),
                                           "verdict": "no power"}
            continue
        t = two_sided(A, mm, th0, D["A"], nboot=400, seed=43)
        OUTJ["engaged_manual"][lab] = {"difference": t["difference"],
                                       "levels_LEFT": t["LEFT"]["levels"],
                                       "levels_RIGHT": t["RIGHT"]["levels"],
                                       "seconds_LEFT": t["LEFT"]["seconds"],
                                       "seconds_RIGHT": t["RIGHT"]["seconds"]}
        gg = t["difference"].get("geo_L_over_R", {})
        go = t["difference"].get("geo_outer_L_over_R", {})
        print(f"  {lab:8s} L {t['LEFT']['seconds']:6.0f} s / R {t['RIGHT']['seconds']:6.0f} s   "
              f"geo ALL {gg.get('point', float('nan')):.4f} "
              f"{np.round(gg.get('ci95', [np.nan, np.nan]), 4).tolist()}   "
              f"geo OUTER {go.get('point', float('nan')):.4f} "
              f"{np.round(go.get('ci95', [np.nan, np.nan]), 4).tolist()}")

    # ---------------- confound: route heterogeneity (road crown)
    print("\n=== CONFOUND -- PER-ROUTE (road crown must VARY across roads) ===")
    pr, het = route_heterogeneity(A, prim, th0, D["A"])
    OUTJ["per_route"] = pr
    OUTJ["route_heterogeneity"] = het
    vals = np.array([r["geo_L_over_R"] for r in pr])
    for r in sorted(pr, key=lambda x: -x["seconds"]):
        print(f"  route {r['route']}  {r['seconds']:6.0f} s  {r['n_common_bins']:2d} bins   "
              f"geo L/R {r['geo_L_over_R']:.4f} [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]")
    if het:
        print(f"  Cochran Q = {het['Q']:.2f} on df = {het['df']}  (Q/df = {het['Q_over_df']:.2f})"
              f"   pooled {het['pooled_geo']:.4f}")
        print(f"  ⇒ {het['verdict']}")
    print(f"  n_routes {len(vals)}   median {np.median(vals):.4f}   "
          f"IQR [{np.percentile(vals, 25):.4f}, {np.percentile(vals, 75):.4f}]   "
          f"frac < 1 = {float(np.mean(vals < 1)):.3f}")
    OUTJ["per_route_summary"] = {"n_routes": len(vals), "median": float(np.median(vals)),
                                 "iqr": [float(np.percentile(vals, 25)),
                                         float(np.percentile(vals, 75))],
                                 "frac_below_1": float(np.mean(vals < 1)),
                                 "min": float(vals.min()), "max": float(vals.max())}

    (OUT / "two_sided.json").write_text(json.dumps(OUTJ, indent=1, default=float))
    print(f"\nwrote {OUT / 'two_sided.json'}")


if __name__ == "__main__":
    main()
