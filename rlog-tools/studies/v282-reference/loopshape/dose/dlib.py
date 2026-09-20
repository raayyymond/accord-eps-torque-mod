# -*- coding: utf-8 -*-
"""Shared definitions for the DOSE stream (loop shaping / SteerKP sizing).

Everything here is MEASUREMENT machinery plus algebra on the fork's own published constants.
Nothing predicts how the car will feel.

Frames (all verified against the fork source at the flown commits):
  pid_log.output = -output_torque          (latcontrol_torque.py:837)
  output_torque  = clip(p+i+f, +/-LAF)/LAF (torque_from_lateral_accel is x/LAF, linear, offset off)
  measurement    = -calc_curvature(sa-aoff, v, roll) * v^2      -> M = -k_m(v) * angle_deg
  error          = setpoint - measurement
  P (pid.p)      = SteerKP * notch(error * (1 + lsf/SteerKP))   -> effective P gain = (kp + lsf)
  U              = p + i + f  == output lateral accel (m/s^2 equivalent), pre-clip

So, with e = Z - M:
  U = U_ff(r) - K_tot(jw) * M          K_tot = -dU/dM  (positive = negative feedback)
  M = P_la(jw) * U                     P_la  = plant from U (m/s^2 cmd) to M (m/s^2 measured)
  L = K_tot * P_la
"""
import sys, math
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]                      # .../studies/v282-reference
KIT = STUDY.parents[2]                       # .../accord-eps-torque-mod
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "ffgain_ceiling"))

import v282cmp as V                          # noqa: E402

FS = 100.0
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v282ref"
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------------------------
# Every route's flown config, read from hsurface/surface/params_all.json (initData), never a label.
# kp/laf/ki/rate_loop/dob are the values the FORK read that drive; 'ABSENT' -> the code default.
# ---------------------------------------------------------------------------------------------
ROUTES = {
    # counter--hash            group     kp    laf    ki   ki_hi  rateloop  dob  notchQ ratePlantFF
    "00000039--f56039af87": dict(g="V282old", kp=0.8, laf=2.11, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=False),
    "0000003a--283a39a1d6": dict(g="V282old", kp=0.8, laf=4.00, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=False),
    "0000003c--927965c2b4": dict(g="V282old", kp=0.8, laf=3.60, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=False),
    "00000064--ce6b0b0ebb": dict(g="V282",    kp=0.9, laf=6.00, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=True),
    "00000065--b9f78988bd": dict(g="V282",    kp=0.9, laf=6.00, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=True),
    "0000006c--2bc842dbac": dict(g="V282",    kp=0.9, laf=6.00, ki=0.30, ki_hi=0.0, rl=0.0,    dob=0.0, nq=0.0, pff=True),
    "00000070--717f5a7866": dict(g="T-ident", kp=0.30, laf=6.00, ki=0.15, ki_hi=0.0, rl=0.0,   dob=0.0, nq=0.0, pff=False),
    "00000071--f2c9d073a3": dict(g="T2",      kp=0.85, laf=14.0, ki=0.30, ki_hi=0.0, rl=0.0,   dob=0.0, nq=0.0, pff=True),
    "00000072--8001fc3048": dict(g="T3",      kp=0.85, laf=14.0, ki=0.60, ki_hi=0.0, rl=0.0006, dob=0.0, nq=1.0, pff=True),
    "00000073--79fd149dd8": dict(g="T3r",     kp=0.85, laf=14.0, ki=0.60, ki_hi=0.0, rl=0.0006, dob=0.0, nq=1.0, pff=True),
    "00000075--6c8687d5bd": dict(g="T4",      kp=0.85, laf=14.0, ki=0.60, ki_hi=2.5, rl=0.0006, dob=0.0, nq=1.0, pff=True),
    "00000076--d0b7ea7e4d": dict(g="T5",      kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0, rl=0.001, dob=0.6, nq=1.0, pff=True),
    "0000006c--68c6e94b17": dict(g="T64",     kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0, rl=0.001, dob=0.6, nq=1.0, pff=True),
    "0000006d--05e83bb04f": dict(g="T64",     kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0, rl=0.001, dob=0.6, nq=1.0, pff=True),
    "0000006e--6ca3e014fd": dict(g="T64B",    kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0, rl=0.001, dob=0.6, nq=1.0, pff=True),
}
TORQ = [r for r, c in ROUTES.items() if c["g"].startswith("T")]
V282 = [r for r, c in ROUTES.items() if c["g"] == "V282"]
V282O = [r for r, c in ROUTES.items() if c["g"] == "V282old"]

# fork constants (latcontrol_torque.py:34-40, latcontrol_vehicle_tunes.py)
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
MIN_SPEED = 0.3
RATE_LOOP_TAPER_V = 12.0
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP, HOLD_LEVEL_V = [12.5, 17.5], [1.15, 1.45]
EPS_G_BP, EPS_G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]
EPS_INERTIA = 8e-5
DOB_DELAY, DOB_ACC_RC = 0.06, 0.05
RATE_LOOP_RC = 0.01


def low_speed_factor(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, MIN_SPEED)) ** 2


def load(route):
    """v282cmp.load, but tolerant of routes not in its ROUTES table."""
    if route not in V.ROUTES:
        V.ROUTES[route] = dict(group=ROUTES[route]["g"], eps="?", fork="?", note="")
    return V.load(route)


# ---------------------------------------------------------------------------------------------
# Instrumental-variable (closed-loop) transfer estimate.
#
#   y = P u + d,  u = F r - K y,  d independent of the instrument r
#   =>  S_ry / S_ru = P   EXACTLY, whatever F and K are, and whatever d is.
# The naive H1 ratio S_uy/S_uu is biased by d (that is the bias the study already paid for).
# ---------------------------------------------------------------------------------------------
def iv_transfer(segs, nperseg=1024, fs=FS):
    """segs = [(r, u, y), ...]; returns f, P_hat (complex), plus diagnostics.
    Weighted by segment length; cross-spectra summed BEFORE the ratio (never ratio-then-average)."""
    segs = [s for s in segs if len(s[0]) >= nperseg]
    if not segs:
        return None
    acc = dict(ru=None, ry=None, rr=None, uu=None, yy=None, uy=None)
    fr = None
    sec = 0.0
    for r, u, y in segs:
        r, u, y = r - r.mean(), u - u.mean(), y - y.mean()
        w = len(r)
        kw = dict(fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
        f, Sru = signal.csd(r, u, **kw)
        _, Sry = signal.csd(r, y, **kw)
        _, Srr = signal.welch(r, **kw)
        _, Suu = signal.welch(u, **kw)
        _, Syy = signal.welch(y, **kw)
        _, Suy = signal.csd(u, y, **kw)
        for k, vv in (("ru", Sru), ("ry", Sry), ("rr", Srr), ("uu", Suu), ("yy", Syy), ("uy", Suy)):
            acc[k] = vv * w if acc[k] is None else acc[k] + vv * w
        fr = f
        sec += w / fs
    P = acc["ry"] / acc["ru"]
    coh_ru = np.abs(acc["ru"]) ** 2 / np.maximum(acc["rr"] * acc["uu"], 1e-30)
    coh_ry = np.abs(acc["ry"]) ** 2 / np.maximum(acc["rr"] * acc["yy"], 1e-30)
    P_h1 = acc["uy"] / np.maximum(acc["uu"], 1e-30)          # the BIASED naive estimate, for contrast
    return dict(f=fr, P=P, P_h1=P_h1, coh_ru=coh_ru, coh_ry=coh_ry, sec=sec, n=len(segs),
                Srr=acc["rr"], Suu=acc["uu"], Syy=acc["yy"])


BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]   # the study's own exposure bands


def loop_metrics(f, L, valid=None, fmin=0.08, fmax=6.0, bands=BANDS):
    """Decision-relevant loop numbers from an identified L(jw).

    fc / pm : the HIGHEST-frequency downward 0 dB crossing of |L| and its phase margin (the one
              that governs stability; a shallow low-frequency dip through 1 is not a crossover).
    Ms      : peak of |S| = |1/(1+L)| over the valid band.  Ms bounds both margins:
              GM >= Ms/(Ms-1), PM >= 2*asin(1/(2Ms)).
    S_band  : power-mean |S| in each exposure band -- how much the feedback attenuates the
              tracking error there.  |S| < 1 = the loop helps, > 1 = the loop makes it worse.
    """
    m = (f >= fmin) & (f <= fmax) & np.isfinite(L)
    if valid is not None:
        m = m & valid
    fl, Ll = f[m], L[m]
    mag = np.abs(Ll)
    if mag.size < 4:
        return None
    ph = np.unwrap(np.angle(Ll))
    fc = pm = float("nan")
    for i in range(len(mag) - 2, -1, -1):           # highest-frequency downward crossing
        if mag[i] >= 1.0 > mag[i + 1]:
            a = np.log(mag[i]) / (np.log(mag[i]) - np.log(mag[i + 1]))
            fc = math.exp(math.log(fl[i]) + a * (math.log(fl[i + 1]) - math.log(fl[i])))
            phc = ph[i] + a * (ph[i + 1] - ph[i])
            pm = 180.0 + math.degrees(phc)
            while pm > 360:
                pm -= 360
            while pm < -180:
                pm += 360
            break
    S = 1.0 / (1.0 + Ll)
    T = Ll / (1.0 + Ll)
    Ms = float(np.max(np.abs(S)))
    out = dict(fc=float(fc), pm=float(pm), Ms=Ms, f_Ms=float(fl[int(np.argmax(np.abs(S)))]),
               Tp=float(np.max(np.abs(T))), mag_max=float(mag.max()))
    for (a, b) in bands:
        bm = (fl >= a) & (fl < b)
        out[f"S{a:g}_{b:g}"] = float(np.sqrt(np.mean(np.abs(S[bm]) ** 2))) if bm.sum() else float("nan")
        out[f"L{a:g}_{b:g}"] = float(np.sqrt(np.mean(np.abs(Ll[bm]) ** 2))) if bm.sum() else float("nan")
    return out


crossover_pm = loop_metrics   # backwards name used by the control script


def smooth_c(x, k=5):
    return x if k <= 1 else np.convolve(x, np.ones(k) / k, mode="same")


def C_pid(f, kp, ki, lsf, nq=0.0, f_notch=0.0):
    """-dU/dM through the PID, in lat-accel/lat-accel units.
       p = (kp+lsf)*e_notched ; i = ki*(1+lsf/kp)/s * e_notched"""
    w = 2 * np.pi * np.asarray(f, float)
    s = 1j * w
    g = (kp + lsf) + ki * (1.0 + lsf / max(kp, 1e-3)) / np.where(np.abs(s) < 1e-12, 1e-12, s)
    if nq > 0.0 and f_notch > 0.0:
        wn = 2 * np.pi * f_notch
        g = g * (s ** 2 + wn ** 2) / (s ** 2 + (wn / nq) * s + wn ** 2)
    return g


def C_rate(f, laf, rl_gain, v, k_m, rc=RATE_LOOP_RC):
    """-dU/dM through the 100 Hz rate loop.  U gets +LAF*g*F_rc(s)*rate_meas, rate = -sM/k_m,
       so -dU/dM = +LAF*g*s*F_rc(s)/k_m : a pure LEAD (damping) rolled off by the 0.01 s filter."""
    if rl_gain <= 0:
        return np.zeros_like(np.asarray(f, float), dtype=complex)
    s = 1j * 2 * np.pi * np.asarray(f, float)
    g = float(rl_gain) * min(1.0, RATE_LOOP_TAPER_V / max(v, 0.1))
    return laf * g * s / (1.0 + s * rc) / k_m


def dob_terms(f, laf, dob_hz, v, k_m, hold_level=True):
    """The disturbance observer, split into
         num  = -dU/dM through the observer's internal MODEL   (state feedback)
         den  = (1 - Q(s) e^{-sTd}) , the observer's own output-recycling loop
       so K_tot = (C_pid + C_rate + num) / den.  Q = two poles at dob_hz.
       At DC Q->1 and den->0: the DOB is an INTEGRATOR on the model mismatch (that is what it is for)."""
    fa = np.asarray(f, float)
    s = 1j * 2 * np.pi * fa
    if dob_hz <= 0:
        return np.zeros_like(fa, dtype=complex), np.ones_like(fa, dtype=complex)
    tau = 1.0 / (2 * np.pi * dob_hz)
    Q = 1.0 / (1.0 + s * tau) ** 2
    fade = float(np.interp(v, [3.0, 6.0], [0.0, 1.0]))
    k_spring = float(np.interp(v, HOLD_V_BP, HOLD_K_V))
    if hold_level:
        k_spring *= float(np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V))
    b_model = 1.0 / float(np.interp(v, EPS_G_BP, EPS_G_V))
    Qacc = 1.0 / (1.0 + s * DOB_ACC_RC)
    dmodel_dangle = k_spring + b_model * s + EPS_INERTIA * s ** 2 * Qacc
    # angle = -M/k_m, and U += -LAF*dob  =>  -dU/dM = +LAF*Q*fade*dmodel/dangle * (1/k_m)... sign:
    # dob = Q*(u_del - model(angle)),  U += -LAF*dob  =>  dU/dM = +LAF*Q*fade*dmodel/dangle*dangle/dM
    #      dangle/dM = -1/k_m  =>  dU/dM = -LAF*Q*fade*dmodel/k_m  =>  -dU/dM = +LAF*Q*fade*dmodel/k_m
    num = laf * Q * fade * dmodel_dangle / k_m
    # u path: U += -LAF*Q*fade*u_del ; u_left = pid_log.output = -output_torque = -U/LAF
    #      => U += +Q*fade*e^{-sTd}*U
    den = 1.0 - Q * fade * np.exp(-s * (DOB_DELAY + 0.01))
    return num, den


def k_m_measured(S, mask):
    """m/s^2 of `measurement` per degree of (steeringAngle - offset), measured by regression.
       M = -k_m * angle, so k_m is returned POSITIVE."""
    a = np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"])
    M = np.nan_to_num(S["la_act"])
    a, M = a[mask], M[mask]
    a, M = a - a.mean(), M - M.mean()
    return float(-np.dot(a, M) / max(np.dot(a, a), 1e-12))


def band_rms(x, f1, f2, fs=FS, order=4):
    sos = signal.butter(order, [f1, f2], btype="band", fs=fs, output="sos")
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos, x) ** 2)))
