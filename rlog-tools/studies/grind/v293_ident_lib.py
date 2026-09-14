# -*- coding: utf-8 -*-
"""v293_ident_lib.py -- shared loading / alignment / estimators for the V293 plant identification.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

Everything is resampled onto ONE 100 Hz grid with previous-value (ZOH) semantics, which is what the
control loop actually sees, except the raw gyro (a smooth physical signal sampled at ~93 Hz, well above
the 0.1-5 Hz band of interest) which is linearly interpolated.

🛑 CLOSED LOOP.  The applied EPS torque `u` is NOT exogenous -- it is openpilot's output, which depends
on the measured angle.  Every plant estimate here therefore uses the planner's desired curvature as an
INSTRUMENT (joint input-output / IV form  H = S_zy / S_zu), never a direct u->y regression, and the
direct form is computed alongside ONLY to show the bias.  `tau_identify.py`'s argument applies: the
planner's lookahead cancels, and `desiredCurvature` comes from the camera and the road.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
SCRATCH = os.path.join(HERE, "_scratch")

FS = 100.0
CPD = 8.0                       # raw 0x18F counts per deg/s  (the kit's measured yardstick)
BANDS = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
BANDNAME = ["<8", "8-15", "15-22", ">22"]


def pr_factory(buf):
    def pr(s=""):
        print(s, flush=True); buf.append(s)
    return pr


def zoh(t_grid, t_src, y_src):
    """previous-value hold: the value the consumer would have had at t_grid."""
    j = np.searchsorted(t_src, t_grid, side="right") - 1
    out = np.full(len(t_grid), np.nan)
    ok = j >= 0
    out[ok] = np.asarray(y_src)[j[ok]]
    return out


def lin(t_grid, t_src, y_src):
    return np.interp(t_grid, t_src, y_src, left=np.nan, right=np.nan)


def tap_decode(b0, b1):
    """the CAN-427 delivered-torque tap:  fld = ((b0&3)<<8)|b1 ; T = sign * (fld & 0x1ff) << 3.
    sign bit is bit 9 of the field.  8 counts per LSB."""
    fld = ((b0.astype(np.int64) & 3) << 8) | b1.astype(np.int64)
    mag = (fld & 0x1FF) * 8
    sgn = np.where((fld >> 9) & 1, -1.0, 1.0)
    return sgn * mag


def load(tag="r70_v293"):
    D = dict(np.load(os.path.join(CACHE, tag + "_ident.npz")))
    with open(os.path.join(CACHE, tag + "_ident_meta.json")) as fh:
        meta = json.load(fh)

    t0 = min(D["t18"][0], D["t_cc"][0])
    t1 = max(D["t18"][-1], D["t_cc"][-1])
    tg = np.arange(0.0, t1 - t0, 1.0 / FS)
    ta = tg + t0
    g = {"t": tg, "n": len(tg), "meta": meta, "tag": tag}

    # --- CAN, ZOH -------------------------------------------------------------------------------
    g["bar"] = zoh(ta, D["t18"], D["tq"])              # driver-torque bar (torsion bar), raw counts
    g["wire"] = zoh(ta, D["t18"], D["rate"])           # wheel rate, raw counts (CPD = 8/deg/s)
    g["sca"] = zoh(ta, D["t18"], D["sca"])
    g["ang"] = zoh(ta, D["t14"], D["ang"])             # steering angle, deg (+left, kit convention)
    g["cmd"] = zoh(ta, D["te4"], D["cmd"])             # 0xE4 LKAS torque command, raw counts
    g["req"] = zoh(ta, D["te4"], D["req"])             # STEER_REQUEST
    Ttap = tap_decode(D["b0"], D["b1"])
    g["tap_t"] = D["t1ab"] - t0
    g["tap"] = Ttap
    g["T"] = zoh(ta, D["t1ab"], Ttap)                  # delivered lane torque, counts (50 Hz, ZOH)

    # --- openpilot, ZOH -------------------------------------------------------------------------
    for k_src, k_dst in (("lat_active", "lat_active"), ("cc_curv_cmd", "curv_cmd"),
                         ("cc_torque", "op_torque"), ("cc_curv_now", "curv_now"),
                         ("cc_yaw", "pose_yaw"), ("cc_enabled", "enabled")):
        g[k_dst] = zoh(ta, D["t_cc"], D[k_src])
    for k_src, k_dst in (("cs_des_curv", "des_curv"), ("cs_curv", "cs_curv"),
                         ("cs_la_des", "la_des"), ("cs_la_act", "la_act"), ("cs_out", "out"),
                         ("cs_err", "err"), ("cs_f", "f"), ("cs_p", "p"), ("cs_i", "i"),
                         ("cs_sat", "sat"), ("cs_active", "cs_active")):
        g[k_dst] = zoh(ta, D["t_cs"], D[k_src])
    for k_src, k_dst in (("vego", "v"), ("sa_deg", "sa"), ("sr_deg", "sr"), ("spress", "press"),
                         ("storque", "storque"), ("cs_standstill", "standstill"),
                         ("storque_eps", "storque_eps"), ("cs_yaw", "cs_yaw")):
        if k_src in D:
            g[k_dst] = zoh(ta, D["t_cst"], D[k_src])
    for k_src, k_dst in (("lpar_sr", "sr_ratio"), ("lpar_stiff", "stiff"), ("lpar_ao", "angle_off")):
        g[k_dst] = zoh(ta, D["t_lpar"], D[k_src])
    g["mv_curv"] = zoh(ta, D["t_mv"], D["mv_curv"])
    for k_src, k_dst in (("ld_delay", "ld_delay"), ("ld_est", "ld_est"), ("ld_blocks", "ld_blocks")):
        g[k_dst] = zoh(ta, D["t_ld"], D[k_src])

    # --- gyro, linear (smooth physical signal at 93 Hz) ------------------------------------------
    # the x axis negated is the yaw rate: slope -1.0046 corr -0.9965 vs the calibrated yaw (TAU sec.2)
    g["gyro_yaw"] = -lin(ta, D["t_gy"], D["gy_x"])
    g["co_yaw"] = zoh(ta, D["t_co"], D["co_rot_z"])

    # --- derived ---------------------------------------------------------------------------------
    g["rate_dps"] = g["wire"] / CPD                     # wheel rate, deg/s (from 0x18F)
    g["eng"] = (g["req"] > 0.5) & (g["sca"] > 0.5)      # LATERAL engaged (the kit's definition)
    g["idx_raw"] = np.abs(g["cmd"]) / 16.1876           # demand index, taper 254 (see below)
    g["raw"] = D
    return g


# ======================================================================================================
# masks and stretches
# ======================================================================================================
def clean_mask(g, hands_off=True, min_v=0.0, buffer_s=2.0):
    """lagd's own gate: laterally engaged AND not pressed AND not saturated, with a recovery buffer."""
    m = g["eng"] & (g["v"] > min_v) & np.isfinite(g["v"])
    if hands_off:
        m &= (g["press"] < 0.5)
    m &= (g["sat"] < 0.5)
    for k in ("la_act", "la_des", "op_torque", "T", "ang", "rate_dps"):
        m &= np.isfinite(g[k])
    if buffer_s > 0:
        bad = ~m
        w = int(buffer_s * FS)
        badf = np.convolve(bad.astype(float), np.ones(w), mode="full")[:len(bad)] > 0
        m = m & ~badf
    return m


def stretches(mask, min_len):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def band_of(v):
    for k, (lo, hi) in enumerate(BANDS):
        if lo <= v < hi:
            return k
    return len(BANDS) - 1


# ======================================================================================================
# frequency-domain estimators
# ======================================================================================================
def welch_cross(u, y, fs=FS, nper=1024, nover=None):
    nover = nover if nover is not None else nper // 2
    f, Puu = signal.welch(u, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Pyy = signal.welch(y, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Puy = signal.csd(u, y, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    coh = np.abs(Puy) ** 2 / np.maximum(Puu * Pyy, 1e-30)
    return f, Puu, Pyy, Puy, coh


def iv_tf(z, u, y, fs=FS, nper=1024):
    """JOINT INPUT-OUTPUT transfer estimate  H = S_zy / S_zu  with z the exogenous instrument.
    Consistent under closed loop; the direct S_uy/S_uu form is biased by the feedback.
    Returns f, H, coherence(z,u), coherence(z,y)."""
    nover = nper // 2
    f, Szu = signal.csd(z, u, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Szy = signal.csd(z, y, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Pzz = signal.welch(z, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Puu = signal.welch(u, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    _, Pyy = signal.welch(y, fs=fs, nperseg=nper, noverlap=nover, detrend="linear")
    H = Szy / np.where(np.abs(Szu) < 1e-30, np.nan, Szu)
    czu = np.abs(Szu) ** 2 / np.maximum(Pzz * Puu, 1e-30)
    czy = np.abs(Szy) ** 2 / np.maximum(Pzz * Pyy, 1e-30)
    return f, H, czu, czy


def bandpass(x, lo, hi, fs=FS, order=4):
    sos = signal.butter(order, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def ncc_lag(u, y, fs=FS, lo=0.0, hi=0.65):
    """normalised cross-correlation peak lag of y behind u, parabolic interpolation."""
    u = u - u.mean(); y = y - y.mean()
    nu, ny = np.linalg.norm(u), np.linalg.norm(y)
    if nu == 0 or ny == 0:
        return np.nan, np.nan
    n = len(u)
    c = signal.correlate(y, u, mode="full") / (nu * ny)
    lags = signal.correlation_lags(n, n, mode="full") / fs
    sel = (lags >= lo) & (lags <= hi)
    if sel.sum() < 3:
        return np.nan, np.nan
    cs, ls = c[sel], lags[sel]
    k = int(np.argmax(cs))
    if 0 < k < len(cs) - 1:
        d = (cs[k - 1] - cs[k + 1]) / (2 * (cs[k - 1] - 2 * cs[k] + cs[k + 1]) + 1e-30)
        lag = ls[k] + d / fs
    else:
        lag = ls[k]
    return float(lag), float(cs[k])


def r2(y, yhat):
    y = np.asarray(y, float); yhat = np.asarray(yhat, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1.0 - np.sum((y - yhat) ** 2) / ss) if ss > 0 else np.nan
