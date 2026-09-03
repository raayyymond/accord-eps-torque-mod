# -*- coding: utf-8 -*-
"""backcalc_laf_friction.py -- back-calculate the IDEAL StarPilot torque-controller params (latAccelFactor, friction)
from route data, by (1) reproducing torqued's fit offline and (2) fitting the CAR (lateral accel vs commanded torque)
without torqued's truncations.  Subagent opfit, 2026-09-02.  Reads _scratch/<tag>_backcalc.npz from backcalc_extract.py.

Controller math inverted here (StarPilot `Dom` @ 3d4c625de, read from the code, not from a brief):
  torqued.py           steer = -carOutput.torque delayed by liveDelay.lateralDelay; lat = vEgo*yaw_cal - g*sin(roll_dev)
                       qualify: latActive over [t-2, t+lag], no steeringPressed, vEgo>15, |steer|>0.02, |lat|<=1
                       buckets on steer (8 bounds, FIFO 1500), fit = TLS via SVD of [x, 1, y]; friction = 1.5*std(spread)
                       caps: LAF in [0.7, 1.3]*1.689 = [1.18, 2.196]; friction in [0.5, 1.5]*0.212 = [0.106, 0.318]
  latcontrol_torque.py ff = future_lat_acc*accord_scale - roll - offset + friction*LAF*clip((err_lsf + 0.22*jerk)/0.30, +-1)
                       out_torque = (kp*err_lsf + ki*I + ff)/LAF ; kp = SteerKP (flat 0.6 on the wire), ki = 0.15
                       err_lsf = err*(1 + lsf/kp), lsf = (interp(v,[0,10,20,30],[12,10.5,8,5])/v)^2
                       friction threshold = max(interp(v mph,[1,20,75],[.16,.19,.27]), 0.30) = 0.30 at every speed
  small-signal torque per m/s^2 of error (linear band):  Gc = (kp + lsf)/LAF + friction/0.30
  loop DC gain through the car:                          L0 = Gc * LAF_true = (kp+lsf)*LAF_true/LAF + friction*LAF_true/0.30
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
G = 9.81
# torqued constants (copied)
MIN_VEL, STEER_MIN, LAT_ACC_THR, FRICTION_FACTOR = 15.0, 0.02, 1.0, 1.5
BOUNDS = [(-0.5, -0.3), (-0.3, -0.2), (-0.2, -0.1), (-0.1, 0), (0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.5)]
MIN_BUCKET = np.array([100, 300, 500, 500, 500, 500, 300, 100]); PER_BUCKET = 1500; MIN_TOTAL = 4000; FIT_PTS = 2000
ENGAGE_BUF = 2.0
LAF0, FRIC0 = 1.6893333799149202, 0.2120497022936265
FACTOR_SANITY, FRICTION_SANITY = 0.3, 0.5
# controller constants
KP, KI, FRIC_THR = 0.6, 0.15, 0.30
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
TAGS = ["r22", "r97", "r31", "r32", "r33"]


def rot_from_euler(e):
    """openpilot common.transformations.orientation.rot_from_euler: R = Rz(yaw) Ry(pitch) Rx(roll)."""
    r, p, y = e
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def hold(ts, vs, t):
    idx = np.searchsorted(ts, t, side="right") - 1
    out = np.full(len(t), np.nan); ok = idx >= 0; out[ok] = vs[idx[ok]]; return out


def lsf(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, 0.3)) ** 2


def tls(points):
    """torqued.estimate_params on rows [x, 1, y]."""
    _, _, v = np.linalg.svd(points, full_matrices=False)
    slope, offset = -v.T[0:2, 2] / v.T[2, 2]
    sin = np.sqrt(slope ** 2 / (slope ** 2 + 1)); cos = np.sqrt(1 / (slope ** 2 + 1))
    rot = np.array([[cos, -sin], [sin, cos]])
    _, spread = np.matmul(points[:, [0, 2]], rot).T
    return float(slope), float(offset), float(np.std(spread) * FRICTION_FACTOR)


def load(tag):
    z = np.load(os.path.join(SCR, "%s_backcalc.npz" % tag), allow_pickle=True)
    D = {k: z[k] for k in z.files}
    D["cp"] = json.loads(str(D["carParams_json"]))
    return D


def grid(D):
    t0 = D["co_t"][0]; t1 = D["co_t"][-1]
    t = np.arange(0, t1 - t0, 1 / FS)
    g = dict(t=t)
    T = lambda k: D[k] - t0
    g["tq"] = np.interp(t, T("co_t"), D["co_tq"])                 # openpilot torque (+ = left)
    g["can"] = hold(T("co_t"), D["co_can"], t)
    g["cmd"] = hold(T("e4_t"), D["e4_cmd"], t); g["req"] = hold(T("e4_t"), D["e4_req"], t)
    g["sca"] = hold(T("f18_t"), D["f18_sca"], t); g["rate18"] = np.interp(t, T("f18_t"), D["f18_rate"]); g["drv18"] = np.interp(t, T("f18_t"), D["f18_tq"])
    for k in ("v", "drv", "ang", "rate"):
        g[k] = np.interp(t, T("cs_t"), D["cs_" + k])
    g["pressed"] = hold(T("cs_t"), D["cs_pressed"], t)
    g["lat"] = hold(T("cc_t"), D["cc_lat"], t)
    for k in ("active", "error", "p", "i", "d", "f", "output", "actualLateralAccel", "desiredLateralAccel", "desiredLateralJerk", "descurv", "curv"):
        g[k] = hold(T("ctl_t"), D["ctl_" + k], t)
    # livePose (20 Hz) -> calibrated yaw rate, exactly torqued's PoseCalibrator
    lp_t = T("lp_t"); w = np.stack([D["lp_wx"], D["lp_wy"], D["lp_wz"]], 1); roll_dev = D["lp_ox"]
    cal_idx = np.searchsorted(T("cal_t"), lp_t, side="right") - 1
    yaw_cal = np.full(len(lp_t), np.nan); cal_ok = np.zeros(len(lp_t), bool)
    for i in range(len(lp_t)):
        j = cal_idx[i]
        if j < 0:
            continue
        Rc = rot_from_euler([D["cal_r"][j], D["cal_p"][j], D["cal_y"][j]]).T   # calib_from_device
        yaw_cal[i] = (Rc @ w[i])[2]; cal_ok[i] = D["cal_ok"][j] > 0
    g["lp_t"] = lp_t; g["lp_yaw_cal"] = yaw_cal; g["lp_yaw_raw"] = D["lp_wz"]; g["lp_roll"] = roll_dev; g["lp_calok"] = cal_ok
    g["yaw_cal"] = np.interp(t, lp_t, yaw_cal); g["yaw_raw"] = np.interp(t, lp_t, D["lp_wz"]); g["roll_dev"] = np.interp(t, lp_t, roll_dev)
    g["lag"] = hold(T("ld_t"), D["ld_lag"], t); g["lag"][np.isnan(g["lag"])] = 0.2
    g["proll"] = np.interp(t, T("lpar_t"), D["lpar_roll"]); g["aoff"] = np.interp(t, T("lpar_t"), D["lpar_aoff"])
    for k in ("latAccelFactorRaw", "frictionCoefficientRaw", "latAccelOffsetRaw", "latAccelFactorFiltered", "frictionCoefficientFiltered",
              "latAccelOffsetFiltered", "liveValid", "useParams", "totalBucketPoints", "calPerc"):
        g["ltp_" + k] = hold(T("ltp_t"), D["ltp_" + k], t)
        g["ltpv_" + k] = D["ltp_" + k]
    g["ltp_t"] = T("ltp_t")
    # torqued's lateral accel (its own instrument) and the two alternatives
    g["lat_torqued"] = g["v"] * g["yaw_cal"] - np.sin(g["roll_dev"]) * G
    g["lat_yawraw"] = g["v"] * g["yaw_raw"] - np.sin(g["roll_dev"]) * G
    g["lat_vm"] = g["actualLateralAccel"]          # controller's steering-angle vehicle-model measurement (0 when inactive)
    # engaged flags
    g["eng_wire"] = (g["sca"] > 0.5) & (g["req"] > 0.5)
    g["eng"] = g["lat"] > 0.5
    return g


def delayed(x, t, lag):
    """value of x at t - lag (torqued pairs torque from lag earlier with the pose now)."""
    return np.interp(t - lag, t, x)


def torqued_points(g, lag=None, min_vel=MIN_VEL, lat_thr=LAT_ACC_THR, steer_min=STEER_MIN, lat_key="lat_torqued"):
    """Reproduce handle_log's qualification at every livePose tick; returns x(steer), y(lat), t, v and the window mask."""
    t = g["t"]; lagv = g["lag"] if lag is None else np.full(len(t), lag)
    steer = -delayed(g["tq"], t, lagv)
    n_win = int(round((ENGAGE_BUF + np.nanmedian(lagv)) * FS))
    lat_ok = np.convolve((g["lat"] > 0.5).astype(int), np.ones(n_win, int), "full")[:len(t)] >= n_win
    prs_ok = np.convolve((g["pressed"] > 0.5).astype(int), np.ones(n_win, int), "full")[:len(t)] == 0
    y = g[lat_key]
    q = lat_ok & prs_ok & (g["v"] > min_vel) & (np.abs(steer) > steer_min) & ~np.isnan(y)
    q_lat = q & (np.abs(y) <= lat_thr)
    # sample at livePose ticks (20 Hz) like torqued
    lp = np.searchsorted(t, g["lp_t"]); lp = lp[(lp > 0) & (lp < len(t))]
    m = np.zeros(len(t), bool); m[lp] = True
    return steer, y, q & m, q_lat & m


def emulate_torqued(g, steer, y, qmask):
    """FIFO buckets exactly as torqued, fit at each liveTorqueParameters tick on ALL bucket points (and on a 2000 subsample)."""
    from collections import deque
    buckets = {b: deque(maxlen=PER_BUCKET) for b in BOUNDS}
    idx = np.where(qmask)[0]; ti = g["t"][idx]
    out_t, out_fit, out_n = [], [], []
    ltp_t = g["ltp_t"]; k = 0
    def fit_now():
        pts = np.vstack([np.array(list(v)) for v in buckets.values() if len(v)]) if any(len(v) for v in buckets.values()) else None
        if pts is None or len(pts) < 10 or not all(len(v) > 0 for v in buckets.values()):
            return None
        return tls(pts), len(pts)
    for i, tt in zip(idx, ti):
        x, yy = steer[i], y[i]
        for b in BOUNDS:
            if b[0] <= x < b[1]:
                buckets[b].append([x, 1.0, yy]); break
        while k < len(ltp_t) and ltp_t[k] <= tt:
            r = fit_now()
            if r is not None:
                out_t.append(ltp_t[k]); out_fit.append(r[0]); out_n.append(r[1])
            k += 1
    final = fit_now()
    counts = {b: len(v) for b, v in buckets.items()}
    return np.array(out_t), np.array(out_fit), np.array(out_n), final, counts


def car_fit(x, y, rate):
    """The CAR: y = lat accel, x = steer (= -torque, delayed).  OLS slope/intercept, TLS, and the coulomb split
    x = y/LAF + b + c*sign(rate)  (c = torque needed before lat accel responds = hysteresis half-width, in torque units)."""
    o = dict(n=int(len(x)))
    if len(x) < 50:
        return o
    A = np.c_[x, np.ones_like(x)]; s, b = np.linalg.lstsq(A, y, rcond=None)[0]
    o["ols_slope"], o["ols_icpt"] = float(s), float(b)
    o["r"] = float(np.corrcoef(x, y)[0, 1])
    o["tls_slope"], o["tls_off"], o["tls_fric"] = tls(np.c_[x, np.ones_like(x), y])
    sg = np.sign(rate); ok = sg != 0
    if ok.sum() > 50:
        A2 = np.c_[y[ok], np.ones(ok.sum()), sg[ok]]
        a, bb, c = np.linalg.lstsq(A2, x[ok], rcond=None)[0]
        o["inv_LAF"], o["inv_bias"], o["coulomb_tq"] = float(1 / a) if a != 0 else np.nan, float(bb), float(c)
        res = x[ok] - A2 @ np.array([a, bb, c]); o["inv_resid_tq"] = float(np.std(res))
        # torque-on-lat OLS without the sign term, for the residual comparison
        A3 = A2[:, :2]; a3, b3 = np.linalg.lstsq(A3, x[ok], rcond=None)[0]
        o["inv_resid_nosign_tq"] = float(np.std(x[ok] - A3 @ np.array([a3, b3])))
        # hysteresis on lat-accel: intercept split when regressing y on x per rate sign
        for nm, sel in (("pos", sg > 0), ("neg", sg < 0)):
            if sel.sum() > 30:
                ss, ib = np.linalg.lstsq(np.c_[x[sel], np.ones(sel.sum())], y[sel], rcond=None)[0]
                o["slope_" + nm], o["icpt_" + nm] = float(ss), float(ib)
        if "icpt_pos" in o and "icpt_neg" in o:
            o["hyst_lat"] = float(abs(o["icpt_pos"] - o["icpt_neg"]))
            o["hyst_tq"] = float(o["hyst_lat"] / max(o["ols_slope"], 1e-6))
    return o


def piecewise(x, y, rate, v):
    rows = []
    for lo, hi in ((0, 0.1), (0.1, 0.3), (0.3, 1.0)):
        m = (np.abs(x) >= lo) & (np.abs(x) < hi)
        rows.append(("|tq| %.1f-%.1f" % (lo, hi), car_fit(x[m], y[m], rate[m])))
    for lo, hi in ((10, 20), (20, 30), (30, 45)):
        m = (v >= lo) & (v < hi)
        rows.append(("v %d-%d" % (lo, hi), car_fit(x[m], y[m], rate[m])))
    return rows


def binned_curve(x, y, edges):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (x >= lo) & (x < hi)
        if m.sum() >= 20:
            out.append((0.5 * (lo + hi), int(m.sum()), float(np.mean(y[m])), float(np.median(y[m])), float(np.std(y[m]))))
    return out


def fir_dc(g, lat_key="lat_torqued", n_taps=30, min_vel=MIN_VEL, dt=0.05):
    """Dynamic fit on 20 Hz samples: y[k] = sum_j h[j]*x[k-j] + b over j=0..n_taps-1 (1.5 s), x = steer = -torque (undelayed).
    DC gain = sum(h).  Closed-loop data, but the integrator pins y = des at DC so sum(h) is the plant's DC lat-accel per
    unit torque; the lag scan's slope-vs-lag rise is the same fact seen one tap at a time.  Also a first-order + delay
    fit (tau, Td, K) by grid search on the same samples, K from OLS at each (tau, Td)."""
    t = g["t"]; step = int(round(dt * FS)); idx = np.arange(0, len(t), step)
    x = -g["tq"][idx]; y = g[lat_key][idx]; v = g["v"][idx]
    eng = (g["lat"][idx] > 0.5) & (g["pressed"][idx] < 0.5) & (v > min_vel) & ~np.isnan(y) & (np.abs(y) <= 3)
    ok = np.convolve(eng.astype(int), np.ones(n_taps, int), "full")[:len(eng)] >= n_taps
    rows = np.where(ok)[0]
    if len(rows) < 200:
        return None
    X = np.stack([x[rows - j] for j in range(n_taps)], 1); X = np.c_[X, np.ones(len(rows))]
    h = np.linalg.lstsq(X, y[rows], rcond=None)[0]
    res = np.std(y[rows] - X @ h)
    # first-order + delay grid
    best = None
    for Td in np.arange(0, 0.8, 0.05):
        for tau in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
            a = np.exp(-dt / tau); xf = np.zeros(len(x))
            for k in range(1, len(x)):
                xf[k] = a * xf[k - 1] + (1 - a) * x[k - 1]
            nd = int(round(Td / dt)); xs = np.r_[np.zeros(nd), xf[:len(xf) - nd]] if nd else xf
            A = np.c_[xs[rows], np.ones(len(rows))]; K, b = np.linalg.lstsq(A, y[rows], rcond=None)[0]
            r = np.std(y[rows] - A @ np.array([K, b]))
            if best is None or r < best[3]:
                best = (float(K), float(tau), float(Td), float(r), float(b))
    return dict(n=int(len(rows)), dc=float(h[:-1].sum()), bias=float(h[-1]), resid=float(res), h=h[:-1].tolist(),
                fo_K=best[0], fo_tau=best[1], fo_Td=best[2], fo_resid=best[3], fo_bias=best[4])


def spectral_gain(g, min_vel=MIN_VEL, min_run=20.0):
    """H1 transfer estimate lat accel / torque on contiguous engaged runs: |P(f)| at fixed frequencies, two instruments.
    The 100 Hz steering-angle vehicle-model lat accel reaches the 7-8 Hz ring band; the 20 Hz pose instrument stops at 10 Hz."""
    from scipy import signal
    x = -g["tq"]; eng = (g["lat"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > min_vel) & (g["active"] > 0.5)
    edges = np.diff(np.r_[0, eng.astype(int), 0]); runs = [(s, e) for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]) if (e - s) >= min_run * FS]
    if not runs:
        return None
    F = np.array([0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 7.5, 8.0])
    out = dict(f=F.tolist(), n_runs=len(runs), secs=float(sum(e - s for s, e in runs) / FS))
    for key, nm, fs_ in (("lat_vm", "vm", 100.0), ("lat_torqued", "pose", 20.0)):
        step = int(round(FS / fs_)); nper = int(10.24 * fs_)
        Pxx = Pyy = Pxy = None
        for s, e in runs:
            xs = x[s:e:step]; ys = g[key][s:e:step]
            if len(xs) < nper or np.isnan(ys).any():
                continue
            xs = xs - xs.mean(); ys = ys - ys.mean()
            f, pxx = signal.welch(xs, fs=fs_, nperseg=nper); _, pyy = signal.welch(ys, fs=fs_, nperseg=nper); _, pxy = signal.csd(xs, ys, fs=fs_, nperseg=nper)
            w = len(xs)
            Pxx = pxx * w if Pxx is None else Pxx + pxx * w; Pyy = pyy * w if Pyy is None else Pyy + pyy * w; Pxy = pxy * w if Pxy is None else Pxy + pxy * w
        if Pxx is None:
            out["P_" + nm] = [np.nan] * len(F); out["coh_" + nm] = [np.nan] * len(F); continue
        H = np.abs(Pxy) / Pxx; coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
        out["P_" + nm] = [float(np.interp(ff, f, H)) if ff <= fs_ / 2 else np.nan for ff in F]
        out["coh_" + nm] = [float(np.interp(ff, f, coh)) if ff <= fs_ / 2 else np.nan for ff in F]
    return out


def live_values(g):
    """What the controller actually used: liveTorqueParameters *Filtered (what controlsd feeds update_live_torque_params
    when useParams), cross-checked against -(p+i+d+f)/output = LAF and a regression of f for friction*LAF."""
    a = (g["active"] > 0.5) & (np.abs(g["output"]) > 0.05) & ~np.isnan(g["output"])
    o = {}
    if a.sum() > 50:
        laf_chk = -(g["p"] + g["i"] + g["d"] + g["f"])[a] / g["output"][a]
        o["LAF_from_pid_p50"] = float(np.nanmedian(laf_chk)); o["LAF_from_pid_p5"], o["LAF_from_pid_p95"] = [float(x) for x in np.nanpercentile(laf_chk, [5, 95])]
        kp_chk = g["p"][a] / g["error"][a]; kp_chk = kp_chk[np.abs(g["error"][a]) > 0.02]
        o["kp_p50"] = float(np.nanmedian(kp_chk))
        # friction*LAF from f: f = base + F*clip((err+0.22*jerk)/0.3); base ~ desiredLateralAccel*scale - roll
        e = g["error"][a] + 0.22 * g["desiredLateralJerk"][a]
        clipv = np.clip(e / FRIC_THR, -1, 1)
        des = g["desiredLateralAccel"][a]; roll = g["proll"][a] * G
        A = np.c_[des, roll, clipv, np.ones_like(des)]
        coef = np.linalg.lstsq(A, g["f"][a], rcond=None)[0]
        o["f_fit_des_coef"], o["f_fit_roll_coef"], o["fricLAF_from_f"], o["f_fit_bias"] = [float(c) for c in coef]
        o["f_fit_resid"] = float(np.std(g["f"][a] - A @ coef))
        o["friction_from_f"] = o["fricLAF_from_f"] / o["LAF_from_pid_p50"] if o["LAF_from_pid_p50"] else np.nan
    for k in ("latAccelFactorFiltered", "frictionCoefficientFiltered", "latAccelOffsetFiltered", "latAccelFactorRaw", "frictionCoefficientRaw",
              "latAccelOffsetRaw", "liveValid", "useParams", "totalBucketPoints", "calPerc"):
        v = g["ltp_" + k]; v = v[~np.isnan(v)]
        if len(v):
            o[k + "_first"], o[k + "_last"], o[k + "_p50"] = float(v[0]), float(v[-1]), float(np.median(v))
    return o


def gain(laf, fric, v, laf_true):
    """small-signal: Gc torque per m/s^2 error (linear band); L0 = loop DC gain through the car."""
    l = lsf(np.asarray(v, float))
    Gc_p = (KP + l) / laf; Gc_f = fric / FRIC_THR
    return dict(Gc=Gc_p + Gc_f, Gc_p=Gc_p, Gc_f=Gc_f, L0=(Gc_p + Gc_f) * laf_true, frac_f=Gc_f / (Gc_p + Gc_f))


def fmt(o, keys):
    return "  ".join("%s=%s" % (k, ("%.4g" % o[k]) if isinstance(o.get(k), float) else o.get(k)) for k in keys if k in o)


def analyse(tag):
    D = load(tag); g = grid(D); build = str(D["build"])
    cp = D["cp"]
    R = dict(tag=tag, build=build, cp=cp)
    print("\n" + "=" * 110 + "\n%s  %s  build=%s   %.0f s, engaged(latActive) %.0f s, wire-engaged %.0f s, calib ok %.2f"
          % (tag, str(D["prefix"]), build, g["t"][-1], g["eng"].sum() / FS, g["eng_wire"].sum() / FS, np.nanmean(g["lp_calok"])))
    print("carParams.lateralTuning.%s: LAF %.4f friction %.4f offset %.3f deadzone %.2f deg; steerRatio %.2f; actuatorDelay %.2f; torqueBP %s"
          % (cp["which"], cp.get("latAccelFactor", np.nan), cp.get("friction", np.nan), cp.get("latAccelOffset", np.nan),
             cp.get("steeringAngleDeadzoneDeg", np.nan), cp["steerRatio"], cp["steerActuatorDelay"], cp["torqueBP"]))
    lagm = float(np.nanmedian(g["lag"][g["eng"]])) if g["eng"].any() else float(np.nanmedian(g["lag"]))
    print("liveDelay.lateralDelay engaged median %.3f s;  0xE4 counts per unit torque: %.1f (from torqueOutputCan)" % (lagm, _counts_per_tq(g)))
    # ---- live values
    L = live_values(g); R["live"] = L
    print("LIVE (liveTorqueParameters): LAF filtered first/last %.3f/%.3f  friction filtered %.3f/%.3f  offset %.3f/%.3f | raw LAF %.3f/%.3f  raw fric %.3f/%.3f  raw offset %.3f/%.3f | liveValid %.0f->%.0f useParams %.0f points %.0f->%.0f calPerc %.0f->%.0f"
          % tuple(L.get(k, np.nan) for k in ("latAccelFactorFiltered_first", "latAccelFactorFiltered_last", "frictionCoefficientFiltered_first", "frictionCoefficientFiltered_last",
                                              "latAccelOffsetFiltered_first", "latAccelOffsetFiltered_last", "latAccelFactorRaw_first", "latAccelFactorRaw_last",
                                              "frictionCoefficientRaw_first", "frictionCoefficientRaw_last", "latAccelOffsetRaw_first", "latAccelOffsetRaw_last",
                                              "liveValid_first", "liveValid_last", "useParams_last", "totalBucketPoints_first", "totalBucketPoints_last", "calPerc_first", "calPerc_last")))
    print("  cross-check from torqueState: LAF = -(p+i+d+f)/output p5/p50/p95 %.3f/%.3f/%.3f ; kp = p/error p50 %.3f ; friction*LAF from f-regression %.3f (-> friction %.3f; des coef %.3f roll coef %.3f resid %.3f)"
          % tuple(L.get(k, np.nan) for k in ("LAF_from_pid_p5", "LAF_from_pid_p50", "LAF_from_pid_p95", "kp_p50", "fricLAF_from_f", "friction_from_f", "f_fit_des_coef", "f_fit_roll_coef", "f_fit_resid")))
    # ---- torqued replication
    steer, y, q_all, q_lat = torqued_points(g)
    ot, of, on, final, counts = emulate_torqued(g, steer, y, q_lat)
    R["torqued"] = dict(n_qualified=int(q_lat.sum()), n_qualified_nolatthr=int(q_all.sum()), counts={str(k): v for k, v in counts.items()})
    print("TORQUED REPLICATION: qualified points this route (|lat|<=1) %d (without the |lat|<=1 cut: %d); bucket counts %s"
          % (q_lat.sum(), q_all.sum(), [counts[b] for b in BOUNDS]))
    if final is not None:
        (s, o_, f), n = final
        R["torqued"].update(my_LAF=s, my_offset=o_, my_friction=f, n_fit=n)
        rng = np.random.default_rng(0)
        pts = np.vstack([np.array(list(v)) for v in _rebuild_buckets(steer, y, q_lat).values() if len(v)])
        sub = [tls(pts[rng.choice(len(pts), min(len(pts), FIT_PTS), replace=False)]) for _ in range(20)]
        sub = np.array(sub)
        print("  my fit on ALL bucket points at route end: LAF %.3f offset %.3f friction %.3f (n=%d); 2000-pt subsample x20: LAF %.3f+-%.3f friction %.3f+-%.3f"
              % (s, o_, f, n, sub[:, 0].mean(), sub[:, 0].std(), sub[:, 2].mean(), sub[:, 2].std()))
        lr = L.get("latAccelFactorRaw_last", np.nan); fr = L.get("frictionCoefficientRaw_last", np.nan); orr = L.get("latAccelOffsetRaw_last", np.nan)
        print("  torqued's LOGGED raw at route end: LAF %.3f offset %.3f friction %.3f -> residual (mine - logged): LAF %+.3f (%+.1f%%) friction %+.3f (%+.1f%%)"
              % (lr, orr, fr, s - lr, 100 * (s - lr) / lr, f - fr, 100 * (f - fr) / fr))
        R["torqued"].update(logged_LAF_raw_last=lr, logged_friction_raw_last=fr, resid_LAF=s - lr, resid_friction=f - fr)
        if len(ot):
            # trajectory comparison at each liveTorqueParameters tick
            lg_laf = np.interp(ot, g["ltp_t"], g["ltpv_latAccelFactorRaw"]); lg_fr = np.interp(ot, g["ltp_t"], g["ltpv_frictionCoefficientRaw"])
            d_laf = of[:, 0] - lg_laf; d_fr = of[:, 2] - lg_fr
            m2 = on >= 2000
            print("  trajectory over %d ticks (mine on this route's points only; logged carries cached points from earlier routes): LAF diff p50 %+.3f (ticks with >=2000 pts: %+.3f), friction diff p50 %+.3f (%+.3f)"
                  % (len(ot), np.median(d_laf), np.median(d_laf[m2]) if m2.any() else np.nan, np.median(d_fr), np.median(d_fr[m2]) if m2.any() else np.nan))
            R["torqued"].update(traj_dLAF_p50=float(np.median(d_laf)), traj_dfric_p50=float(np.median(d_fr)))
        print("  torqued's caps: LAF clip to [%.3f, %.3f], friction clip to [%.3f, %.3f]; logged raw LAF %.3f is %s the cap"
              % ((1 - FACTOR_SANITY) * LAF0, (1 + FACTOR_SANITY) * LAF0, (1 - FRICTION_SANITY) * FRIC0, (1 + FRICTION_SANITY) * FRIC0, lr,
                 "ABOVE" if lr > (1 + FACTOR_SANITY) * LAF0 else "within"))
    # ---- the CAR: lat accel vs commanded torque, all three instruments, torqued's lag, no |lat|<=1 cut, |lat|<=3
    print("THE CAR (steer = -torque delayed by liveDelay; qualified as torqued but no |lat|<=1 cut, |lat|<=3, v>15):")
    rate = g["rate"]
    R["car"] = {}
    for key, nm in (("lat_torqued", "torqued pose (calibrated yaw x v - g sin roll)"), ("lat_yawraw", "uncalibrated device yaw x v"), ("lat_vm", "steering-angle vehicle model (torqueState.actualLateralAccel)")):
        st, yy, qa, ql = torqued_points(g, lat_key=key, lat_thr=3.0)
        m = ql
        o = car_fit(st[m], yy[m], rate[m]); R["car"][key] = o
        print("  [%s] n=%d  OLS slope %.3f icpt %+.3f r %.3f | TLS slope %.3f off %+.3f fric(1.5sd) %.3f | inverse: LAF %.3f coulomb %+.4f tq (resid %.4f vs %.4f no-sign) | hyst(icpt split) %.3f m/s2 = %.4f tq"
              % (nm, o.get("n", 0), o.get("ols_slope", np.nan), o.get("ols_icpt", np.nan), o.get("r", np.nan), o.get("tls_slope", np.nan), o.get("tls_off", np.nan), o.get("tls_fric", np.nan),
                 o.get("inv_LAF", np.nan), o.get("coulomb_tq", np.nan), o.get("inv_resid_tq", np.nan), o.get("inv_resid_nosign_tq", np.nan), o.get("hyst_lat", np.nan), o.get("hyst_tq", np.nan)))
    # lag scan on the torqued instrument
    st0, yy0, qa0, ql0 = torqued_points(g, lat_key="lat_torqued", lat_thr=3.0)
    best = []
    for lagv in np.arange(0, 0.61, 0.05):
        st, yy, qa, ql = torqued_points(g, lag=lagv, lat_key="lat_torqued", lat_thr=3.0)
        if ql.sum() > 100:
            best.append((lagv, float(np.corrcoef(st[ql], yy[ql])[0, 1]), float(np.polyfit(st[ql], yy[ql], 1)[0])))
    if best:
        b = max(best, key=lambda r: r[1]); R["lag_scan"] = best
        print("  lag scan (torque lead vs lat accel): best r at lag %.2f s (r %.3f, slope %.3f); at liveDelay %.2f: r %.3f slope %.3f"
              % (b[0], b[1], b[2], lagm, *[(r[1], r[2]) for r in best if abs(r[0] - round(lagm / 0.05) * 0.05) < 1e-6][0]))
    # instrumental-variable slope: desired lat accel (setpoint, exogenous from the model path) as the instrument -> immune to
    # the closed-loop bias that pulls OLS/FIR down when the road-crown disturbance feeds back into the command
    iv = {}
    for lagv in (0.2, 0.5, 0.8):
        st, yy, qa, ql = torqued_points(g, lag=lagv, lat_key="lat_torqued", lat_thr=3.0)
        des = delayed(g["desiredLateralAccel"], g["t"], lagv)
        m = ql & ~np.isnan(des) & (g["active"] > 0.5)
        if m.sum() > 200:
            dx = st[m] - st[m].mean(); dy = yy[m] - yy[m].mean(); dz = des[m] - des[m].mean()
            iv[lagv] = float((dz * dy).sum() / (dz * dx).sum())
    R["iv"] = iv
    print("  IV slope (instrument = torqueState.desiredLateralAccel, same lag on both): " + "  ".join("lag %.1f: %.3f" % (k, v) for k, v in iv.items()))
    F = fir_dc(g); R["fir"] = F
    if F:
        print("  DYNAMIC FIT (20 Hz, 30-tap FIR 0-1.5 s, engaged v>15, n=%d): DC gain sum(h) %.3f m/s2 per unit torque, bias %+.3f, resid %.3f | first-order+delay: K %.3f tau %.2f s Td %.2f s resid %.3f"
              % (F["n"], F["dc"], F["bias"], F["resid"], F["fo_K"], F["fo_tau"], F["fo_Td"], F["fo_resid"]))
        hh = np.array(F["h"]); print("    cumulative h at 0.2/0.5/1.0/1.5 s: %.2f / %.2f / %.2f / %.2f" % tuple(hh[:k].sum() for k in (4, 10, 20, 30)))
    S = spectral_gain(g); R["spectral"] = S
    if S:
        print("  SPECTRAL |P(f)| lat accel per unit torque (H1 = Pxy/Pxx, Welch 10.24 s, engaged v>15 runs >= 20 s, %d runs %.0f s):" % (S["n_runs"], S["secs"]))
        print("    f Hz      : " + " ".join("%6.2f" % f for f in S["f"]))
        print("    |P| vm100 : " + " ".join("%6.2f" % a for a in S["P_vm"]) + "   (steering-angle vehicle model, 100 Hz)")
        print("    coh vm100 : " + " ".join("%6.2f" % a for a in S["coh_vm"]))
        print("    |P| pose20: " + " ".join("%6.2f" % a for a in S["P_pose"]) + "   (torqued pose instrument, 20 Hz; nan above 10 Hz)")
        print("    coh pose20: " + " ".join("%6.2f" % a for a in S["coh_pose"]))
    # piecewise
    st, yy, qa, ql = torqued_points(g, lat_key="lat_torqued", lat_thr=3.0, min_vel=10.0)
    print("  PIECEWISE (torqued pose instrument, v>10 for the speed rows):")
    R["piecewise"] = {}
    for nm, o in piecewise(st[ql], yy[ql], rate[ql], g["v"][ql]):
        R["piecewise"][nm] = o
        print("    %-14s n=%6d  OLS slope %.3f icpt %+.3f r %.3f | inverse LAF %.3f coulomb %+.4f | hyst %.4f tq"
              % (nm, o.get("n", 0), o.get("ols_slope", np.nan), o.get("ols_icpt", np.nan), o.get("r", np.nan), o.get("inv_LAF", np.nan), o.get("coulomb_tq", np.nan), o.get("hyst_tq", np.nan)))
    # binned curve (for the doc)
    st, yy, qa, ql = torqued_points(g, lat_key="lat_torqued", lat_thr=3.0)
    edges = np.array([-0.5, -0.3, -0.2, -0.15, -0.1, -0.07, -0.05, -0.03, -0.02, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3, 0.5])
    R["curve"] = binned_curve(st[ql], yy[ql], edges)
    print("  BINNED lat accel by steer (=-torque): " + "; ".join("%.3f:%+.2f(n%d)" % (c, mu, n) for c, n, mu, md, sd in R["curve"]))
    # what torqued's |lat|<=1 truncation does to the slope on THIS car
    o1 = car_fit(st[ql & (np.abs(yy) <= 1)], yy[ql & (np.abs(yy) <= 1)], rate[ql & (np.abs(yy) <= 1)])
    print("  with torqued's |lat|<=1 cut: n=%d OLS slope %.3f TLS slope %.3f (vs %.3f / %.3f without)" % (o1.get("n", 0), o1.get("ols_slope", np.nan), o1.get("tls_slope", np.nan),
                                                                                                          R["car"]["lat_torqued"].get("ols_slope", np.nan), R["car"]["lat_torqued"].get("tls_slope", np.nan)))
    R["car"]["lat_torqued_latcut1"] = o1
    # |torque| and speed distributions engaged
    e = g["eng"]
    print("  engaged |torque| p50/p90/p99 %.3f/%.3f/%.3f ; vEgo p10/p50/p90 %.1f/%.1f/%.1f ; |lat| p50/p90 %.2f/%.2f"
          % (*np.percentile(np.abs(g["tq"][e]), [50, 90, 99]), *np.percentile(g["v"][e], [10, 50, 90]), *np.nanpercentile(np.abs(g["lat_torqued"][e]), [50, 90])))
    return R


def _counts_per_tq(g):
    a = np.abs(g["tq"]) > 0.05
    return float(np.nanmedian(-g["can"][a] / g["tq"][a])) if a.any() else np.nan


def _rebuild_buckets(steer, y, q):
    from collections import deque
    buckets = {b: deque(maxlen=PER_BUCKET) for b in BOUNDS}
    for i in np.where(q)[0]:
        for b in BOUNDS:
            if b[0] <= steer[i] < b[1]:
                buckets[b].append([steer[i], 1.0, y[i]]); break
    return buckets


def main():
    tags = [t for t in sys.argv[1:] if t in TAGS] or TAGS
    res = {}
    for tag in tags:
        if not os.path.exists(os.path.join(SCR, "%s_backcalc.npz" % tag)):
            print("missing", tag); continue
        res[tag] = analyse(tag)
    # ---- torqued CHAIN emulation r31 -> r32 -> r33 (the device restores the bucket points between routes)
    chain = [t for t in ("r31", "r32", "r33") if t in res]
    if len(chain) >= 2:
        from collections import deque
        buckets = {b: deque(maxlen=PER_BUCKET) for b in BOUNDS}
        print("\n" + "=" * 110 + "\nTORQUED CHAIN EMULATION (buckets carried %s, as the on-device cache does; the cache also held points from BEFORE r31):" % "->".join(chain))
        for tag in chain:
            g = grid(load(tag)); steer, y, qa, ql = torqued_points(g)
            for i in np.where(ql)[0]:
                for b in BOUNDS:
                    if b[0] <= steer[i] < b[1]:
                        buckets[b].append([steer[i], 1.0, y[i]]); break
            calc = all(len(v) > 0 for v in buckets.values())
            pts = np.vstack([np.array(list(v)) for v in buckets.values() if len(v)])
            lr = res[tag]["live"].get("latAccelFactorRaw_last", np.nan); fr = res[tag]["live"].get("frictionCoefficientRaw_last", np.nan)
            if calc:
                s_, o_, f_ = tls(pts)
                print("  after %s: buckets %s calculable=%s -> my TLS LAF %.3f off %+.3f fric %.3f | logged raw at route end LAF %.3f fric %.3f | resid LAF %+.3f fric %+.3f"
                      % (tag, [len(buckets[b]) for b in BOUNDS], calc, s_, o_, f_, lr, fr, s_ - lr, f_ - fr))
                res[tag]["chain"] = dict(LAF=s_, off=o_, fric=f_, n=int(len(pts)), counts=[len(buckets[b]) for b in BOUNDS])
            else:
                print("  after %s: buckets %s NOT calculable on this route's own points (outer buckets empty) | logged raw LAF %.3f fric %.3f (from cached points)"
                      % (tag, [len(buckets[b]) for b in BOUNDS], lr, fr))
                res[tag]["chain"] = dict(calculable=False, counts=[len(buckets[b]) for b in BOUNDS])
    # ---- pooled car fits per build
    print("\n" + "=" * 110 + "\nPOOLED BY BUILD (torqued pose instrument, v>15, |lat|<=3):")
    pools = {}
    for tag, R in res.items():
        pools.setdefault(R["build"], []).append(tag)
    for build, tags_ in pools.items():
        xs, ys, rs, vs = [], [], [], []
        for tag in tags_:
            g = grid(load(tag)); st, yy, qa, ql = torqued_points(g, lat_key="lat_torqued", lat_thr=3.0, min_vel=10.0)
            xs.append(st[ql]); ys.append(yy[ql]); rs.append(g["rate"][ql]); vs.append(g["v"][ql])
        x = np.concatenate(xs); y = np.concatenate(ys); r = np.concatenate(rs); v = np.concatenate(vs)
        m = v > 15
        o = car_fit(x[m], y[m], r[m]); P = dict(all=o)
        print("  %-7s %s n=%d OLS slope %.3f icpt %+.3f r %.3f | inverse LAF %.3f coulomb %+.4f | hyst %.4f tq | TLS %.3f" % (build, tags_, o.get("n", 0), o.get("ols_slope", np.nan), o.get("ols_icpt", np.nan), o.get("r", np.nan), o.get("inv_LAF", np.nan), o.get("coulomb_tq", np.nan), o.get("hyst_tq", np.nan), o.get("tls_slope", np.nan)))
        for nm, oo in piecewise(x, y, r, v):
            P[nm] = oo
            print("    %-14s n=%6d OLS slope %.3f icpt %+.3f r %.3f | inverse LAF %.3f coulomb %+.4f | hyst %.4f tq" % (nm, oo.get("n", 0), oo.get("ols_slope", np.nan), oo.get("ols_icpt", np.nan), oo.get("r", np.nan), oo.get("inv_LAF", np.nan), oo.get("coulomb_tq", np.nan), oo.get("hyst_tq", np.nan)))
        res.setdefault("_pooled", {})[build] = P
    json.dump(res, open(os.path.join(SCR, "backcalc_results.json"), "w"), indent=1, default=float)
    # ---- gain table
    print("\n" + "=" * 110 + "\nGAIN (small-signal torque per m/s^2 error, linear friction band; L0 = through the car's measured DC LAF):")
    for tag, R in res.items():
        if tag.startswith("_"):
            continue
        car = R["car"]["lat_torqued"]; laf_true = (R.get("fir") or {}).get("dc", car.get("ols_slope", np.nan)); c = car.get("coulomb_tq", np.nan)
        L = R["live"]; laf_live = L.get("latAccelFactorFiltered_last", np.nan); fr_live = L.get("frictionCoefficientFiltered_last", np.nan)
        for v in (15, 25, 32):
            cur = gain(laf_live, fr_live, v, laf_true); ideal = gain(laf_true, abs(c), v, laf_true); sug = gain(laf_live, 0.08, v, laf_true)
            sug2 = gain(2.53, 0.08, v, laf_true)
            print("  %s %-7s v=%2d  LAF_true %.2f coulomb %.3f | live (LAF %.2f fr %.3f): Gc %.3f L0 %.2f fric-share %.0f%% | ideal (LAF %.2f fr %.3f): Gc %.3f L0 %.2f | 'fr 0.08': L0 %.2f | 'LAF 2.53 fr 0.08': L0 %.2f"
                  % (tag, R["build"], v, laf_true, c, laf_live, fr_live, cur["Gc"], cur["L0"], 100 * cur["frac_f"], laf_true, abs(c), ideal["Gc"], ideal["L0"], sug["L0"], sug2["L0"]))


if __name__ == "__main__":
    main()
