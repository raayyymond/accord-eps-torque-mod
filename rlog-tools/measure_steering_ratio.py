#!/usr/bin/env python3
r"""MEASURE the 2020 Accord's steering ratio as a function of steering-wheel angle, from the car's
own logs.  Two independent yaw-rate estimators, every control run BEFORE the measurement.

    ratio(theta) = steering-wheel angle / road-wheel angle

METHOD A -- livePose.angularVelocityDevice.z (IMU + localizer, 20 Hz), per-route bias removed
            from STANDSTILL samples.  🛑 carState.yawRate is IDENTICALLY ZERO on this car
            (0 nonzero / 512,895) -- Method A is livePose, NOT carState.
METHOD B -- rear differential wheel speed, (ws_rr - ws_rl)/T_rear, CAN 0x1D0 src 1.  Fully
            independent of the IMU.  Rear wheels are undriven and unsteered on this FWD car.

KINEMATIC INVERSION -- EXACT, not the small-angle form:
        yaw = v * tan(delta) / (L + K v^2)      =>   delta = atan( yaw * (L + K v^2) / v )
    🛑 The `atan` matters enormously at the plateau: at delta ~ 26 deg the small-angle form
       over-reads the road-wheel angle by ~8 %, which alone fakes a ~8 % "ratio droop".
    🛑🛑 `v` IS THE REAR-AXLE SPEED (ws_rl+ws_rr)/2 -- NOT `vEgo`.  See `ratio_lib.derive`:
       vEgo averages all FOUR wheels and the front pair run at v/cos(delta), so vEgo/v_rear
       climbs from 0.989 at centre to 1.079 at 250-400 deg.  Using vEgo SUPPRESSED the measured
       notch by ~10 % (swing 1.109 instead of 1.227).  This is the single largest systematic
       found in the study and it was caught by the scale-free Method B2 cross-check.

THE SPEED CONFOUND IS STRUCTURALLY ABSENT FROM THE HEADLINE, BY CONSTRUCTION.
    Exposure beyond 120 deg of wheel exists ONLY below 5 m/s (see `exposure()`).  So the whole
    ratio curve -- centre floor AND plateau -- is measured INSIDE the 1-5 m/s band, where
    K v^2 <= 0.05 m against L = 2.83 m (<= 1.8 %) and tyre slip is negligible.  `K` is fitted
    only for the cross-band CONSISTENCY check, never for the headline number.

Usage:
    python measure_steering_ratio.py            # everything, writes _cache_ratio/results.json
    python measure_steering_ratio.py qa|fit|curve|controls
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ratio_lib as R  # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_cache_ratio"
RESULTS = {}

# The firmware's compensation table at 0xC6B64 (virgin across all 96 builds), for comparison.
FW_X = np.array([0, 340, 640, 850, 1000, 1200]) / 10.0            # deg (first 6 knots)
FW_Y = np.array([899, 908, 981, 1060, 1083, 1084]) / 1024.0       # Q10 -> gain
FW_SWING = 1084.0 / 899.0

# Analysis bins on |theta_corrected| (deg).  Log-ish: fine near centre, coarse at the plateau.
BINS = np.array([1, 3, 5, 8, 11, 15, 20, 26, 34, 43, 54, 68, 85, 105, 130, 165, 210, 265, 340, 400],
                float)
PLATEAU_LO = 120.0     # the rack is nominally constant-ratio beyond here


# ======================================================================================
#  0.  LOAD + NUISANCE CORRECTIONS
# ======================================================================================
def prep(win_s=0.5):
    A = R.load()
    A = R.derive(A, win_s=win_s)

    # ---- per-route IMU yaw bias, from STANDSTILL.  A direct measurement, not a fit.
    ms = (A["lp_valid"] > 0) & (A["std"] > 0.5) & (A["v"] < 0.05)
    bias = np.zeros(len(A["t"]))
    biases = {}
    for r in np.unique(A["route"]):
        q = ms & (A["route"] == r)
        if q.sum() > 100:
            b = float(np.median(A["yawA"][q]))
            bias[A["route"] == r] = b
            biases[f"{int(r):03x}"] = b
    A["yawA0"] = A["yawA"] - bias
    RESULTS["imu_bias_rad_s"] = {"per_route": biases,
                                 "median_abs": float(np.median(np.abs(list(biases.values())))),
                                 "max_abs": float(np.max(np.abs(list(biases.values())))),
                                 "standstill_seconds": float(ms.sum() * R.DT)}

    # ---- Method B rear-radius mismatch beta: (rr-rl) = T*yaw + beta*v.  Fit on STRAIGHT driving
    #      (|yawA0| < 0.01 rad/s) at speed, so the T*yaw term is ~0.
    st = R.base_mask(A, vmin=8.0, vmax=40.0) & (np.abs(A["yawA0"]) < 0.01)
    dif = (A["ws_rr"] - A["ws_rl"])[st]
    vv = A["v_ref"][st]
    beta = float(np.sum(dif * vv) / np.sum(vv * vv))
    A["yawB0"] = (A["ws_rr"] - A["ws_rl"] - beta * A["v_ref"]) / R.T_REAR
    RESULTS["methodB_beta"] = {"beta": beta, "n_straight": int(st.sum()),
                               "note": "rear tyre radius mismatch, dimensionless; "
                                       "(rr-rl) = T*yaw + beta*v"}
    return A


def delta_deg(yaw, v, K=0.0):
    """EXACT steady-state inversion -> road-wheel angle in degrees (signed)."""
    return np.arctan(yaw * (R.L_WB + K * v * v) / v) * R.RAD


# ======================================================================================
#  1.  QA -- the sign convention and the two channels' agreement, MEASURED
# ======================================================================================
def qa(A):
    m = R.base_mask(A, vmin=5.0) & R.steady_mask(A)
    o = {
        "n_rows_total": int(len(A["t"])),
        "minutes_total": float(len(A["t"]) * R.DT / 60),
        "carState_yawRate_nonzero": int(np.count_nonzero(A["yaw"])),
        "corr_ang_avz": float(np.corrcoef(A["ang"][m], A["avz"][m])[0, 1]),
        "corr_yawA_yawB": float(np.corrcoef(A["yawA0"][m], A["yawB0"][m])[0, 1]),
        "corr_yawA_rawgyro": float(np.corrcoef(A["yawA0"][m], A["s_gyx"][m])[0, 1]),
        "slope_yawB_on_yawA": float(np.polyfit(A["yawA0"][m], A["yawB0"][m], 1)[0]),
        "op_angleOffsetAverageDeg_median": float(np.nanmedian(A["par_offavg"][m])),
        "op_steerRatio_median": float(np.nanmedian(A["par_sr"][m])),
    }
    RESULTS["qa"] = o
    print("\n=== QA ===")
    for k, v in o.items():
        print(f"  {k:38s} {v}")
    return o


def exposure(A):
    m = R.base_mask(A) & R.steady_mask(A)
    th = np.abs(A["s_ang"][m] - RESULTS.get("theta0", {}).get("theta0_deg", -4.28))
    v = A["v_ref"][m]
    ab = [0, 5, 10, 20, 34, 50, 85, 120, 200, 400]
    vb = [1, 3, 5, 8, 12, 16, 20, 25, 40]
    H, _, _ = np.histogram2d(th, v, bins=[ab, vb])
    print("\n=== EXPOSURE (seconds), steady + valid ===")
    print("  |th|\\v   " + "".join(f"{vb[j]:>7d}" for j in range(len(vb) - 1)))
    for i in range(len(ab) - 1):
        print(f"  {ab[i]:>3d}-{ab[i+1]:<4d} " +
              "".join(f"{H[i, j] * R.DT:7.0f}" for j in range(len(vb) - 1)))
    RESULTS["exposure_seconds"] = {"angle_bins": ab, "speed_bins": vb,
                                   "grid": (H * R.DT).round(1).tolist()}


# ======================================================================================
#  2.  FIT theta0 (the angle-sensor centre offset) -- the ONE nuisance the notch is sensitive to
# ======================================================================================
def fit_theta0(A, method="A"):
    """delta(theta) crosses zero at theta0.  Robust local linear fit in |theta| < 25 deg,
    at speeds where yaw SNR is good.  Reported per speed band as its own consistency check."""
    yaw = A["yawA0"] if method == "A" else A["yawB0"]
    rows, ests = [], []
    for lo, hi in ((1, 5), (5, 12), (12, 20), (20, 40)):
        m = (R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
             & (np.abs(A["s_ang"]) < 25))
        if m.sum() < 500:
            continue
        d = delta_deg(yaw[m], A["v_ref"][m])
        p = np.polyfit(A["s_ang"][m], d, 1)
        z = float(-p[1] / p[0])
        rows.append((lo, hi, int(m.sum()), z, float(1 / p[0])))
        ests.append(z)
    th0 = float(np.median(ests))
    o = {"theta0_deg": th0, "per_band": [{"v_lo": r[0], "v_hi": r[1], "n": r[2],
                                          "theta0": r[3], "local_ratio_at_centre": r[4]}
                                         for r in rows],
         "spread_deg": float(np.max(ests) - np.min(ests)),
         "op_angleOffsetAverageDeg": RESULTS["qa"]["op_angleOffsetAverageDeg_median"]}
    RESULTS[f"theta0_{method}"] = o
    if method == "A":
        RESULTS["theta0"] = o
    print(f"\n=== CENTRE OFFSET theta0, method {method} ===")
    for r in rows:
        print(f"  v {r[0]:>2d}-{r[1]:<2d} m/s  n={r[2]:6d}   theta0 = {r[3]:+7.3f} deg   "
              f"(local ratio at centre {r[4]:.2f})")
    print(f"  ⇒ theta0 = {th0:+.3f} deg   [openpilot's own learned "
          f"angleOffsetAverageDeg = {o['op_angleOffsetAverageDeg']:+.3f}]")
    return th0


# ======================================================================================
#  3.  THE CURVE
# ======================================================================================
def curve_from(th_c, dlt, bins=BINS, fold=True):
    """Binned median curve -> (centres, secant ratio, local ratio, n).  `fold` mirrors R onto L."""
    if fold:
        s = np.sign(th_c)
        s[s == 0] = 1
        a, d = th_c * s, dlt * s
    else:
        a, d = th_c, dlt
    ta, td, nn = [], [], []
    for i in range(len(bins) - 1):
        q = (a >= bins[i]) & (a < bins[i + 1])
        n = int(q.sum())
        nn.append(n)
        if n < 25:
            ta.append(np.nan); td.append(np.nan); continue
        ta.append(float(np.median(a[q]))); td.append(float(np.median(d[q])))
    ta, td = np.array(ta), np.array(td)
    sec = ta / td
    loc = np.full(len(ta), np.nan)
    for i in range(len(ta)):
        j, k = max(0, i - 1), min(len(ta) - 1, i + 1)
        if np.isfinite(ta[j]) and np.isfinite(ta[k]) and k > j:
            dd = td[k] - td[j]
            loc[i] = (ta[k] - ta[j]) / dd if abs(dd) > 1e-9 else np.nan
    return ta, sec, loc, np.array(nn)


def curve_boot(A, m, th0, yawkey, K=0.0, nboot=600, seed=0, bins=BINS, fold=True):
    """The binned curve with BLOCK (episode) bootstrap CIs, normalised to its own plateau."""
    th_c = A["s_ang"][m] - th0
    dlt = delta_deg(A[yawkey][m], A["v_ref"][m], K)
    blk = A["blk"][m]
    ta, sec, loc, nn = curve_from(th_c, dlt, bins, fold)
    plat = np.nanmedian(sec[(ta >= PLATEAU_LO)])
    plat_l = np.nanmedian(loc[(ta >= PLATEAU_LO)])

    rng = np.random.default_rng(seed)
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    bnds = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    by = [order[bnds[i]:bnds[i + 1]] for i in range(len(ub))]
    S, Lo, Sn, Ln, P, Pl = [], [], [], [], [], []
    for _ in range(nboot):
        pick = rng.integers(0, len(ub), len(ub))
        sel = np.concatenate([by[p] for p in pick])
        t2, s2, l2, _ = curve_from(th_c[sel], dlt[sel], bins, fold)
        p2 = np.nanmedian(s2[t2 >= PLATEAU_LO]); pl2 = np.nanmedian(l2[t2 >= PLATEAU_LO])
        S.append(s2); Lo.append(l2); Sn.append(s2 / p2); Ln.append(l2 / pl2)
        P.append(p2); Pl.append(pl2)
    S, Lo, Sn, Ln = map(np.array, (S, Lo, Sn, Ln))

    def ci(M):
        with np.errstate(invalid="ignore"):
            return (np.nanpercentile(M, 2.5, axis=0), np.nanpercentile(M, 97.5, axis=0))
    o = {"n_blocks": int(len(ub)), "n_samples": int(m.sum()), "seconds": float(m.sum() * R.DT),
         "theta": ta.tolist(), "n_bin": nn.tolist(),
         "secant": sec.tolist(), "secant_lo": ci(S)[0].tolist(), "secant_hi": ci(S)[1].tolist(),
         "local": loc.tolist(), "local_lo": ci(Lo)[0].tolist(), "local_hi": ci(Lo)[1].tolist(),
         "plateau_secant": float(plat), "plateau_local": float(plat_l),
         "plateau_secant_ci": [float(np.nanpercentile(P, 2.5)), float(np.nanpercentile(P, 97.5))],
         "plateau_local_ci": [float(np.nanpercentile(Pl, 2.5)), float(np.nanpercentile(Pl, 97.5))],
         "secant_norm": (sec / plat).tolist(),
         "secant_norm_lo": ci(Sn)[0].tolist(), "secant_norm_hi": ci(Sn)[1].tolist(),
         "local_norm": (loc / plat_l).tolist(),
         "local_norm_lo": ci(Ln)[0].tolist(), "local_norm_hi": ci(Ln)[1].tolist()}
    return o


def show_curve(o, title):
    print(f"\n--- {title}   ({o['seconds']:.0f} s, {o['n_blocks']} blocks) ---")
    print("   |th| deg      n    SECANT ratio  [95% CI]        norm      "
          "LOCAL ratio  [95% CI]        norm")
    for i, th in enumerate(o["theta"]):
        if not np.isfinite(th):
            continue
        print(f"  {th:8.1f} {o['n_bin'][i]:7d}   "
              f"{o['secant'][i]:7.2f} [{o['secant_lo'][i]:6.2f},{o['secant_hi'][i]:6.2f}] "
              f"{o['secant_norm'][i]:7.3f}   "
              f"{o['local'][i]:7.2f} [{o['local_lo'][i]:6.2f},{o['local_hi'][i]:6.2f}] "
              f"{o['local_norm'][i]:7.3f}")
    print(f"  plateau (|th| >= {PLATEAU_LO:.0f}): secant {o['plateau_secant']:.3f} "
          f"{o['plateau_secant_ci']}   local {o['plateau_local']:.3f} {o['plateau_local_ci']}")


# ======================================================================================
#  4.  CONTROLS
# ======================================================================================
def plateau_flatness(o, key="local"):
    """⭐ THE POSITIVE CONTROL.  Beyond 120 deg the rack is constant-ratio; the estimator MUST
    return a flat curve there.  Test: does every plateau bin's 95 % CI cover the plateau median,
    and is the max/min spread of the plateau bins < 10 %?"""
    th = np.array(o["theta"]); r = np.array(o[key], float)
    lo = np.array(o[key + "_lo"], float); hi = np.array(o[key + "_hi"], float)
    q = np.isfinite(th) & (th >= PLATEAU_LO) & np.isfinite(r)
    med = float(np.nanmedian(r[q]))
    covers = bool(np.all((lo[q] <= med) & (hi[q] >= med)))
    spread = float(np.nanmax(r[q]) / np.nanmin(r[q]))
    return {"key": key, "n_plateau_bins": int(q.sum()), "plateau_median": med,
            "all_CIs_cover_median": covers, "max_over_min": spread,
            "PASS": bool(covers and spread < 1.10),
            "bins": [{"theta": float(t), "ratio": float(x), "ci": [float(a), float(b)]}
                     for t, x, a, b in zip(th[q], r[q], lo[q], hi[q])]}


def shuffle_control(A, m, th0, yawkey, nrep=200, seed=1):
    """NEGATIVE CONTROL: shuffle the angle<->yaw pairing WITHIN speed bins.  The notch must die."""
    th_c = A["s_ang"][m] - th0
    dlt = delta_deg(A[yawkey][m], A["v_ref"][m])
    v = A["v_ref"][m]
    vb = np.digitize(v, [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    rng = np.random.default_rng(seed)
    real = curve_from(th_c, dlt, BINS)
    sw_real = _swing(real[0], real[2])
    outs = []
    for _ in range(nrep):
        d2 = dlt.copy()
        for b in np.unique(vb):
            q = np.flatnonzero(vb == b)
            d2[q] = dlt[rng.permutation(q)]
        t2, s2, l2, _ = curve_from(th_c, d2, BINS)
        s = _swing(t2, l2)
        if np.isfinite(s):
            outs.append(s)
    outs = np.array(outs)
    return {"real_local_swing": float(sw_real), "shuffled_median": float(np.median(outs)),
            "shuffled_95pct": [float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5))],
            "n_rep": int(len(outs)),
            "PASS": bool(sw_real > np.percentile(outs, 97.5))}


def _swing(th, ratio, centre_hi=15.0):
    """swing = (centre-floor ratio) / (plateau ratio).  Centre floor = median of bins below
    `centre_hi` deg; plateau = median of bins beyond PLATEAU_LO."""
    th = np.asarray(th, float); ratio = np.asarray(ratio, float)
    c = np.isfinite(th) & (th < centre_hi) & np.isfinite(ratio)
    p = np.isfinite(th) & (th >= PLATEAU_LO) & np.isfinite(ratio)
    if not c.any() or not p.any():
        return np.nan
    return float(np.nanmedian(ratio[c]) / np.nanmedian(ratio[p]))


def swing_boot(A, m, th0, yawkey, K=0.0, nboot=1500, seed=2, key="local", centre_hi=15.0):
    """The headline number -- swing, with a BLOCK bootstrap CI."""
    th_c = A["s_ang"][m] - th0
    dlt = delta_deg(A[yawkey][m], A["v_ref"][m], K)
    blk = A["blk"][m]
    idx = 2 if key == "local" else 1
    pt = _swing(*[curve_from(th_c, dlt, BINS)[i] for i in (0, idx)], centre_hi=centre_hi)
    rng = np.random.default_rng(seed)
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    bnds = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    by = [order[bnds[i]:bnds[i + 1]] for i in range(len(ub))]
    outs = []
    for _ in range(nboot):
        pick = rng.integers(0, len(ub), len(ub))
        sel = np.concatenate([by[p] for p in pick])
        c = curve_from(th_c[sel], dlt[sel], BINS)
        s = _swing(c[0], c[idx], centre_hi=centre_hi)
        if np.isfinite(s):
            outs.append(s)
    outs = np.array(outs)
    return {"key": key, "swing": float(pt),
            "ci95": [float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5))],
            "n_blocks": int(len(ub)), "n_boot": int(len(outs))}


# ======================================================================================
def main():
    A = prep()
    qa(A)
    th0 = fit_theta0(A, "A")
    fit_theta0(A, "B")
    exposure(A)

    # ---------- THE PRIMARY MEASUREMENT: the 1-5 m/s band, where the WHOLE curve lives
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)
    cA = curve_boot(A, prim, th0, "yawA0")
    show_curve(cA, "METHOD A (livePose IMU), v 1-5 m/s -- PRIMARY")
    RESULTS["curve_A_primary"] = cA

    primB = prim & (A["v_ref"] > 2.0)
    cB = curve_boot(A, primB, th0, "yawB0")
    show_curve(cB, "METHOD B (rear differential wheel speed), v 2-5 m/s")
    RESULTS["curve_B_primary"] = cB

    # ---------- CONTROL 1: plateau flatness (POSITIVE CONTROL -- decides everything)
    print("\n=== ⭐ CONTROL 1 -- PLATEAU FLATNESS (positive control) ===")
    for tag, c in (("A", cA), ("B", cB)):
        for key in ("secant", "local"):
            f = plateau_flatness(c, key)
            RESULTS[f"plateau_flatness_{tag}_{key}"] = f
            print(f"  method {tag} / {key:6s}: {f['n_plateau_bins']} bins, median "
                  f"{f['plateau_median']:.3f}, max/min {f['max_over_min']:.4f}, "
                  f"CIs cover {f['all_CIs_cover_median']}  ->  "
                  f"{'PASS' if f['PASS'] else 'FAIL'}")

    # ---------- CONTROL 2: within-band speed sub-stratification (the PRIMARY THREAT)
    print("\n=== CONTROL 2 -- WITHIN-BAND SPEED STRATIFICATION ===")
    RESULTS["speed_substrat"] = {}
    for lo, hi in ((1.0, 2.5), (2.5, 3.5), (3.5, 5.0)):
        mm = R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
        c = curve_boot(A, mm, th0, "yawA0", nboot=300, seed=7)
        s = swing_boot(A, mm, th0, "yawA0", nboot=800, seed=7)
        RESULTS["speed_substrat"][f"{lo}-{hi}"] = {"swing": s,
                                                   "plateau_local": c["plateau_local"],
                                                   "seconds": c["seconds"]}
        print(f"  v {lo}-{hi} m/s: {c['seconds']:6.0f} s   local swing "
              f"{s['swing']:.3f} {np.round(s['ci95'], 3).tolist()}   "
              f"plateau_local {c['plateau_local']:.2f}")

    # ---------- CONTROL 3: shuffle (negative control)
    print("\n=== CONTROL 3 -- SHUFFLE (negative control) ===")
    sh = shuffle_control(A, prim, th0, "yawA0")
    RESULTS["shuffle_control"] = sh
    print(f"  real local swing {sh['real_local_swing']:.3f}   shuffled "
          f"{sh['shuffled_median']:.3f} {np.round(sh['shuffled_95pct'], 3).tolist()}  ->  "
          f"{'PASS' if sh['PASS'] else 'FAIL'}")

    # ---------- CONTROL 4: left vs right (the offset's own check)
    print("\n=== CONTROL 4 -- LEFT vs RIGHT ===")
    RESULTS["left_right"] = {}
    for sgn, lab in ((+1, "LEFT"), (-1, "RIGHT")):
        mm = prim & (np.sign(A["s_ang"] - th0) == sgn)
        c = curve_boot(A, mm, th0, "yawA0", nboot=300, seed=11)
        s = swing_boot(A, mm, th0, "yawA0", nboot=800, seed=11)
        RESULTS["left_right"][lab] = {"swing": s, "plateau_local": c["plateau_local"],
                                      "seconds": c["seconds"], "curve": c}
        print(f"  {lab:5s}: {c['seconds']:6.0f} s  local swing {s['swing']:.3f} "
              f"{np.round(s['ci95'], 3).tolist()}  plateau_local {c['plateau_local']:.2f}")

    # ---------- CONTROL 5: engaged vs manual (a plant property must not care)
    print("\n=== CONTROL 5 -- ENGAGED vs MANUAL ===")
    RESULTS["engaged_manual"] = {}
    for on, lab in ((1, "ENGAGED"), (0, "MANUAL")):
        mm = prim & ((A["lat"] > 0.5) if on else (A["lat"] < 0.5))
        if mm.sum() < 2000:
            print(f"  {lab}: only {mm.sum() * R.DT:.0f} s -- NO POWER at 1-5 m/s")
            RESULTS["engaged_manual"][lab] = {"seconds": float(mm.sum() * R.DT),
                                              "verdict": "no power"}
            continue
        c = curve_boot(A, mm, th0, "yawA0", nboot=300, seed=13)
        s = swing_boot(A, mm, th0, "yawA0", nboot=800, seed=13)
        RESULTS["engaged_manual"][lab] = {"swing": s, "plateau_local": c["plateau_local"],
                                          "seconds": c["seconds"]}
        print(f"  {lab:8s}: {c['seconds']:6.0f} s  local swing {s['swing']:.3f} "
              f"{np.round(s['ci95'], 3).tolist()}  plateau_local {c['plateau_local']:.2f}")

    # ---------- THE HEADLINE
    print("\n=== ⭐ HEADLINE ===")
    RESULTS["swing"] = {}
    for tag, mm, yk in (("A", prim, "yawA0"), ("B", primB, "yawB0")):
        for key in ("local", "secant"):
            s = swing_boot(A, mm, th0, yk, key=key)
            RESULTS["swing"][f"{tag}_{key}"] = s
            print(f"  method {tag} / {key:6s} swing = {s['swing']:.3f} "
                  f"{np.round(s['ci95'], 3).tolist()}   vs FIRMWARE {FW_SWING:.3f}")

    RESULTS["firmware_table"] = {"X_deg": FW_X.tolist(), "Y_gain": FW_Y.tolist(),
                                 "swing": FW_SWING}
    (OUT / "results.json").write_text(json.dumps(RESULTS, indent=1, default=float))
    print(f"\nwrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
