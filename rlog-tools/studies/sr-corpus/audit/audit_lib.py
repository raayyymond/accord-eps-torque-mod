# -*- coding: utf-8 -*-
"""audit_lib.py -- independent grid builder for the SR instrument adversarial pass."""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
FS = 100.0
G = 9.81
TRACK_REAR = 1.585  # 2020 Accord rear track, m (nominal; the fit below reports the effective value)


def rot_from_euler(e):
    r, p, y = e
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def hold(ts, vs, t):
    idx = np.searchsorted(ts, t, side="right") - 1
    out = np.full(len(t), np.nan); ok = idx >= 0; out[ok] = np.asarray(vs)[idx[ok]]
    return out


def load(tag):
    z = np.load(os.path.join(SCR, tag + "_audit.npz"), allow_pickle=True)
    D = {k: z[k] for k in z.files}
    D["cp"] = json.loads(str(D["carParams_json"]))
    return D


def grid(D, stiff_scale=1.0):
    t0 = float(D["cs_t"][0]); t1 = float(D["cs_t"][-1])
    t = np.arange(0, t1 - t0, 1 / FS)
    g = dict(t=t, n=len(t))
    T = lambda k: D[k] - t0
    for k in ("v", "ang", "rate", "drv"):
        g[k] = np.interp(t, T("cs_t"), D["cs_" + k])
    g["pressed"] = hold(T("cs_t"), D["cs_pressed"], t)
    g["lat"] = hold(T("cc_t"), D["cc_lat"], t)
    # --- calibrated yaw, rebuilt from rpyCalib myself
    lp_t = T("lp_t"); w = np.stack([D["lp_wx"], D["lp_wy"], D["lp_wz"]], 1)
    cal_t = T("cal_t")
    ci = np.searchsorted(cal_t, lp_t, side="right") - 1
    yaw_cal = np.full(len(lp_t), np.nan); cal_ok = np.zeros(len(lp_t), bool)
    Rcache = {}
    for i in range(len(lp_t)):
        j = ci[i]
        if j < 0:
            continue
        if j not in Rcache:
            Rcache[j] = rot_from_euler([D["cal_r"][j], D["cal_p"][j], D["cal_y"][j]]).T
        yaw_cal[i] = (Rcache[j] @ w[i])[2]
        cal_ok[i] = D["cal_ok"][j] > 0
    g["lp_t"] = lp_t
    g["yaw_cal"] = np.interp(t, lp_t, yaw_cal)
    g["yaw_raw"] = np.interp(t, lp_t, D["lp_wz"])
    g["roll_dev"] = np.interp(t, lp_t, D["lp_ox"])
    g["calok"] = hold(lp_t, cal_ok.astype(float), t) > 0.5
    g["wvalid"] = hold(lp_t, D["lp_wvalid"].astype(float), t) > 0.5
    g["posenetOK"] = hold(lp_t, D["lp_posenetOK"].astype(float), t) > 0.5
    # --- liveParameters
    lpt = T("lpar_t")
    g["proll"] = np.interp(t, lpt, D["lpar_roll"])
    g["aoff"] = np.interp(t, lpt, D["lpar_aoff"])
    g["aoffavg"] = np.interp(t, lpt, D["lpar_aoffavg"])
    g["lpar_sr"] = np.interp(t, lpt, D["lpar_sr"])
    g["lpar_stiff"] = np.interp(t, lpt, D["lpar_stiff"])
    g["lpar_valid"] = hold(lpt, D["lpar_valid"].astype(float), t) > 0.5
    # --- gyro-free yaw from raw CAN 0x1D0 rear wheels
    if "w_t" in D and len(D["w_t"]) > 100:
        wt = T("w_t")
        rl = np.interp(t, wt, D["w_rl"]); rr = np.interp(t, wt, D["w_rr"])
        fl = np.interp(t, wt, D["w_fl"]); fr = np.interp(t, wt, D["w_fr"])
        g["yaw_ws"] = (rr - rl) / TRACK_REAR          # +ve = ? sign resolved by fit against yaw_cal
        g["v_ws"] = 0.5 * (rl + rr)
        g["w_fl"], g["w_fr"] = fl, fr
    # --- bicycle model
    cp = D["cp"]
    m_, L_, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    cF, cR = cp["tireStiffnessFront"] * stiff_scale, cp["tireStiffnessRear"] * stiff_scale
    aR = L_ - aF
    sf = m_ * (cF * aF - cR * aR) / (L_ ** 2 * cF * cR)
    g["sf"] = sf; g["L"] = L_
    v = g["v"]
    g["cfac"] = 1.0 / (1.0 - sf * v ** 2) / L_
    g["cfac_kin"] = np.full_like(v, 1.0 / L_)
    g["rollc"] = (G * g["proll"]) / ((1.0 / sf) - v ** 2)
    g["denom"] = (-g["yaw_cal"] / np.maximum(v, 1e-3)) - g["rollc"]
    g["ang_rad"] = np.radians(g["ang"])               # RAW, no offset removed
    g["sa_deg"] = g["ang"] - g["aoff"]
    g["sa"] = np.radians(g["sa_deg"])
    g["eng"] = (g["lat"] > 0.5) & (g["pressed"] < 0.5) & g["calok"]
    g["man"] = (g["lat"] < 0.5) & g["calok"]
    return g


def tls0(x, y):
    """TLS slope through the origin (the instrument's estimator)."""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[m], np.asarray(y)[m]
    if len(x) < 50:
        return np.nan, len(x)
    _, _, V = np.linalg.svd(np.stack([x, y], 1), full_matrices=False)
    n = V[-1]
    return float(-n[0] / n[1]), len(x)


def ols_yx(x, y, icpt=False):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[m], np.asarray(y)[m]
    if len(x) < 50:
        return (np.nan, np.nan, len(x))
    A = np.c_[x, np.ones_like(x)] if icpt else x[:, None]
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    return (float(c[0]), float(c[1]) if icpt else 0.0, len(x))
