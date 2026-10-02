# -*- coding: utf-8 -*-
r"""m2_authority_budget.py -- M2, THE AUTHORITY BUDGET of route 79 (V298, the first firmware angle loop).

    python analysis-2020accord/studies/angle_loop/v298_flight/m2_authority_budget.py

ANALYSIS ONLY.  Reads the v280 caches (r79_a1f5d2_al.npz wire, r79_fork.npz fork side, r6c / r39 / r71b_v294 refs)
and the V298 image's cells; writes only _scratch/out/r79/m2/.  No rlog is read; every stage is vectorised (the one
scalar loop is the 4000-step integer march of the output-lag pole on a CONSTANT input, and a 12001-entry G LUT).

Question: for every HARD manoeuvre (lateral active and |theta| > 30 deg, or |rate| > 60 deg/s, or |kappa_des| v^2 > 2
m/s^2) where in the demand chain was the demand lost?
  (i)   planner      model action kappa -> controlsState.desiredCurvature (clip_curvature: 5 m/s^3, 3.0 m/s^2 + roll,
                     0.2 1/m; lane-change jerk factor 0.111)                       [drive_helpers.clip_curvature]
  (ii)  angle ctrl   desiredCurvature -> steeringAngleDesiredDeg (no clip; saturation flag)  [latcontrol_angle.update]
  (iii) fork limiter carControl.actuators.steeringAngleDeg -> carOutput.actuatorsOutput.steeringAngleDeg, RECOMPUTED
                     frame by frame from the fork source with the LOGGED previous output (memoryless given
                     apply_angle_last), validated against the logged output        [carcontroller._update_angle,
                     lateral.apply_steer_angle_limits_vm, values.CarControllerParams]
  (iv)  firmware     E = 16(theta_sp - theta) -> E' = (E G)>>8 -> P = (E' 112)>>8 ; the 0x1AB tap vs the rail
  (v)   EPS          achieved angle rate / acceleration vs the setpoint's and the demand's.

ALIGNMENT (EVIDENCE, fork source selfdrive/car/card.py step/state_publish): carOutput row i is published at card step i
with last_actuators_output = the result of step i-1's controls_update(CS[i-1], latest carControl).  So the limiter for
co[i] runs on cs[i-1], the carControl latest before t_cs[i-1], and apply_angle_last = co[i-1].  The script tries
carControl offsets -1..+1 and keeps the one that reproduces the logged output best (reported).
"""
from __future__ import annotations

import glob
import json
import math
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T_START = time.time()
KIT = Path(__file__).resolve().parents[4]
CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
OUT = KIT / "_scratch" / "out" / "r79" / "m2"
OUT.mkdir(parents=True, exist_ok=True)
FW = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
IMG = Path(glob.glob(str(FW / "analysis-2020accord" / "_v298_*plain_image.bin"))[0])
G_ACC = 9.81                       # opendbc ACCELERATION_DUE_TO_GRAVITY
TP = 0xBF000
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(str(s))


# =====================================================================================================================
# 1. THE IMAGE (EVIDENCE: little-endian reads of the V298 image)
# =====================================================================================================================
img = IMG.read_bytes()
import hashlib
SHA = hashlib.sha256(img).hexdigest()
u16 = lambda a: struct.unpack_from("<H", img, a)[0]
i16 = lambda a: struct.unpack_from("<h", img, a)[0]
SCL, OCL, FWD = u16(TP + 0x71BE), u16(TP + 0x71B4), i16(TP + 0x7CD0)
OA, OB = i16(TP + 0x73EC), u16(TP + 0x73EE)
PCL, ICL, DCL, KI = u16(TP + 0x71BC), u16(TP + 0x71BA), u16(TP + 0x71B6), u16(TP + 0x73E6)
_ti = img.find(struct.pack("<HHh", 714, 1178, 1041), 0xC4C00, 0xC4D00)
GB = [struct.unpack_from("<HHh", img, _ti + 6 * k) for k in range(7)]
KP = 112                            # Kp Y 0xE5384 (sel 7): checked below
_kp_ptr = struct.unpack_from("<I", img, 0xCB994 + 4 * 7)[0]
KP_ROW = [u16(_kp_ptr + 2 + 2 * 5 + 2 * i) for i in range(5)]
assert all(k == KP for k in KP_ROW), KP_ROW


def walk_G(v):
    """the cave's integer walk (C3-rev2 §1.4 / nl_cave.walk_G), v = gp-0x6a5e."""
    v &= 0xFFFF
    if v <= GB[0][0]:
        return GB[0][1]
    i = 0
    while v > GB[i + 1][0]:
        i += 1
    X, Gk, S = GB[i]
    return Gk + (((v - X) * S) >> 12)


GLUT = np.array([walk_G(v) for v in range(0, 12001)], float)


def G_of_v(v):
    """gp-0x6a5e ~= vEgo * 3.6 * 64 (BELIEF, inherited from angle_loop_drive_read.G_of_v)."""
    return GLUT[np.clip(np.round(np.asarray(v, float) * 230.4), 0, 12000).astype(int)]


# output-lag DC + forward gain, integer-marched on a constant Sc (0x2A174..0x2A1B0, 0x2A1EE..)
def _lag_ss(Sc):
    ol, y = 0, 0
    for _ in range(4000):
        on = ((Sc * OB) >> 10) + ((OA * ol) >> 10)
        y = (ol + on) >> 5
        ol = on
    return y


Y_RAIL = _lag_ss(SCL)
T_RAIL = (((Y_RAIL * 32767) >> 15) * FWD) >> 15            # ramp at full (32767), pol magnitude 1
LAGDC = _lag_ss(10000) / 10000.0
F_REST = ((255 * 255) & 0xFFFF) >> 8                          # fadeA2 x fadeB2 hands-off = 254
KOUT = (F_REST / 256.0) * LAGDC * FWD / 32768.0               # T per S-unit, hands-off
TAP_RAIL = T_RAIL / 8.0
R_PRE = 300.0                                                 # the pre-registered rail threshold (tap LSB)
S_PER_DEG = lambda G: 160.0 * G * KP / 65536.0                # P in S-units per deg of (theta_sp - theta)

# =====================================================================================================================
# 2. THE FORK'S CONSTANTS (EVIDENCE: source at Dom 2712e1336, cited by function)
# =====================================================================================================================
EMAX_BP = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9]                 # values.CarControllerParams.ANGLE_ERROR_MAX_BP
EMAX_V = [17.0, 15.5, 19.5, 17.0, 8.5, 4.5]                   # .ANGLE_ERROR_MAX_V
MAX_ANGLE_RATE = 1.2                                          # .ANGLE_LIMITS.MAX_ANGLE_RATE deg/frame
LAT_ACC_CC = 3.0 + G_ACC * 0.06                               # lateral.MAX_LATERAL_ACCEL = 3.589
LAT_JERK_CC = 3.0 + G_ACC * 0.06                              # lateral.MAX_LATERAL_JERK = 3.589
OVR_ON, OVR_OFF, OVR_LEAD = 600.0, 500.0, 0.06
PL_JERK, PL_ACC, PL_MAXC = 5.0, 3.0, 0.2                      # drive_helpers MAX_LATERAL_JERK / _ACCEL_NO_ROLL / MAX_CURVATURE

F = dict(np.load(CACHE / "r79_fork.npz"))
CP = json.loads(str(F["carparams_json"]))
TG = json.loads(str(F["sp_toggles_json"]))
SR_CP = CP["steerRatio"]                                      # carcontroller's VM = VehicleModel(CP): sR 16.33, sf 1.0
_l, _aF = CP["wheelbase"], CP["centerToFront"]
_aR = _l - _aF
_cF, _cR, _m, _chi = CP["tireStiffnessFront"], CP["tireStiffnessRear"], CP["mass"], CP["steerRatioRear"]
SF = _m * (_cF * _aF - _cR * _aR) / (_l ** 2 * _cF * _cR)    # vehicle_model.calc_slip_factor


def curv_factor(u):
    return (1.0 - _chi) / (1.0 - SF * u ** 2) / _l              # vehicle_model.curvature_factor


def steer_from_curv_deg(curv, u, sR=SR_CP):
    return np.degrees(curv * sR / curv_factor(u))             # get_steer_from_curvature(curv, u, roll=0)


def emax_of(v):
    return np.interp(v, EMAX_BP, EMAX_V)


# =====================================================================================================================
# 3. THE GRID: carState rows (100 Hz) -- the wire cache's tcs, identical row for row (fork README)
# =====================================================================================================================
W = dict(np.load(CACHE / "r79_a1f5d2_al.npz"))
t = F["t_cs"]
N = len(t)
assert np.array_equal(t, W["tcs"])
theta = F["cs_ang"]; rate_cs = F["cs_rate"]; v = F["cs_vego"]; vraw = F["cs_vegoraw"]; tqd = F["cs_tq"]


def latest(t_src, t_dst, off=0):
    j = np.searchsorted(t_src, t_dst, side="right") - 1 + off
    return np.clip(j, 0, len(t_src) - 1), j >= 0


def zoh(t_src, x, t_dst, off=0):
    j, ok = latest(t_src, t_dst, off)
    y = np.asarray(x)[j].astype(float)
    y[~ok] = np.nan
    return y


# wire onto the grid
th14 = np.interp(t, W["t14"], W["ang"])                       # 0x14A angle, deg (carState sign)
w18 = -np.interp(t, W["t18"], W["rate"]) / 8.0                # 0x18F rate deg/s, sign of d(theta)/dt
bar = np.interp(t, W["t18"], W["tq"]) * 1.024                 # 0x18F hand torque, kit wire units
raw = zoh(W["te4"], W["cmd"], t)                              # 0xE4 as the EPS received it (bus 129)
req = zoh(W["te4"], W["req"], t) > 0.5
sca = zoh(W["t18"], W["sca"], t) > 0.5
fld = ((W["b0"].astype(int) & 3) << 8) | W["b1"].astype(int)
TAP = np.where(fld >= 512, -1.0, 1.0) * (fld & 511)           # field LSB = T/8, sign +sign(raw)
tap = zoh(W["t1ab"], TAP, t)
eng_w = req & sca

# fork onto the grid
lat = zoh(F["t_cc"], F["cc_latActive"], t) > 0.5
cc_ang = zoh(F["t_cc"], F["cc_ang"], t)
dk = zoh(F["t_ctl"], F["ctl_dcurv"], t)
ang_des = zoh(F["t_ctl"], F["ang_des"], t)
ang_sat = zoh(F["t_ctl"], F["ang_sat"], t) > 0.5
kmod = zoh(F["t_md"], F["md_act_curv"], t)
lcs = zoh(F["t_md"], F["md_lcstate"], t)
roll = np.nan_to_num(zoh(F["t_lp"], F["lp_roll"], t))
aoff = np.nan_to_num(zoh(F["t_lp"], F["lp_aoff"], t))
sd_en = zoh(F["t_sd"], F["sd_enabled"], t) > 0.5
aol = zoh(F["t_spcs"], F["spcs_aol_en"], t) > 0.5
pr(f"M2 authority budget -- route 79, image {IMG.name[:40]}... sha {SHA[:12]}")
pr(f"  image cells: SCL {SCL} OCL {OCL} fwd {FWD} oa {OA} ob {OB} PCL {PCL} ICL {ICL} DCL {DCL} Ki {KI} Kp {KP_ROW} "
   f"GB {GB}")
pr(f"  lag DC {LAGDC:.4f}  fade at rest {F_REST}/256  kout {KOUT:.5f} T/S  RAIL: Sc {SCL} -> y {Y_RAIL} -> T {T_RAIL} "
   f"= tap {TAP_RAIL:.1f} LSB (pre-registered threshold {R_PRE:.0f})")

# =====================================================================================================================
# 4. STAGE (iii): THE FORK LIMITER, recomputed vectorised on the logged previous output, validated
# =====================================================================================================================
co_ang = F["co_ang"]; co_raw = F["co_tqcan"]
i = np.arange(1, N)                                            # co[i] computed at step i-1
m = i - 1                                                      # cs row used
th_m, v_m, tq_m, r_m = theta[m], vraw[m], np.abs(tqd[m]), rate_cs[m]
best = None
for off in (-1, 0, 1):
    jcc, okc = latest(F["t_cc"], t[m], off)
    lat_m = F["cc_latActive"][jcc] & okc
    inp = F["cc_ang"][jcc]
    # override hysteresis (carcontroller._update_angle): set > 600, clear <= 500 or not latActive, else hold
    dec = np.full(len(m), np.nan)
    dec[lat_m & (tq_m > OVR_ON)] = 1.0
    dec[(~lat_m) | (tq_m <= OVR_OFF)] = 0.0
    idx = np.where(~np.isnan(dec), np.arange(len(m)), 0)
    np.maximum.accumulate(idx, out=idx)
    ovr = np.nan_to_num(dec[idx]) > 0.5
    was = np.r_[False, ovr[:-1]]
    last = co_ang[i - 1].copy()
    rel = was & ~ovr
    last[rel] = th_m[rel]
    ve = np.maximum(v_m, 1.0)
    d_jerk = steer_from_curv_deg(LAT_JERK_CC / ve ** 2, ve) * 0.01   # get_max_angle_delta_vm (STEER_STEP 1)
    d = np.minimum(d_jerk, MAX_ANGLE_RATE)
    a1 = np.clip(inp, last - d, last + d)
    maxang = steer_from_curv_deg(LAT_ACC_CC / ve ** 2, ve)       # get_max_angle_vm
    a2 = np.clip(a1, -maxang, maxang)
    a2 = np.where(lat_m, a2, th_m)
    a2 = np.clip(a2, -400, 400)
    a2o = np.where(lat_m & ovr, th_m + r_m * OVR_LEAD, a2)
    em = emax_of(v_m)
    a3 = np.where(lat_m, np.clip(a2o, th_m - em, th_m + em), a2o)
    a3 = np.where(lat_m, np.clip(a3, -400, 400), a3)
    match = np.abs(a3 - co_ang[i]) < 0.01
    fr_lat = match[lat_m].mean()
    if best is None or fr_lat > best[0]:
        best = (fr_lat, off, dict(lat_m=lat_m, inp=inp, ovr=ovr, last=last, d=d, d_jerk=d_jerk, a1=a1, a2=a2, a2o=a2o,
                                  a3=a3, em=em, maxang=maxang, match=match, jcc=jcc))
fr_lat, OFF, L = best
pr(f"\nSTAGE (iii) LIMITER RECOMPUTE: carControl offset {OFF:+d}; reproduces logged co_ang within 0.01 deg on "
   f"{100 * fr_lat:.2f} % of latActive frames ({100 * L['match'].mean():.2f} % of all)")
# flags on the cs grid (row m)
def onm(x, fill=False):
    y = np.full(N, fill, dtype=np.asarray(x).dtype)
    y[m] = x
    return y


latL = onm(L["lat_m"]); ovrL = onm(L["ovr"])
rate_bind = onm(L["lat_m"] & ~L["ovr"] & (np.abs(L["inp"] - L["last"]) > L["d"] + 1e-6))
rel_edge = onm(np.r_[False, L["ovr"][:-1]] & ~L["ovr"])
jerk_is_cap = onm(L["d_jerk"] < MAX_ANGLE_RATE)                # which bound sets d
acc_bind = onm(L["lat_m"] & ~L["ovr"] & (np.abs(L["a1"]) > L["maxang"] + 1e-6))
ecl_bind = onm(L["lat_m"] & ~L["ovr"] & (np.abs(L["a2o"] - th_m) > L["em"] + 1e-6))
ecl_loss = onm(np.where(L["lat_m"] & ~L["ovr"], np.abs(L["a2o"] - L["a3"]), 0.0), 0.0)
rate_loss = onm(np.where(L["lat_m"] & ~L["ovr"], np.abs(L["inp"] - L["a1"]), 0.0), 0.0)
co_on_m = onm(co_ang[i], np.nan)                               # the applied setpoint computed at step m
inp_on_m = onm(L["inp"], np.nan)
em_on_m = onm(L["em"], np.nan)
dmax_on_m = onm(L["d"] * 100.0, np.nan)                        # deg/s cap at step m
mis = L["lat_m"] & ~L["match"]
pr(f"  mismatch frames (latActive): {int(mis.sum())}; |a3 - co| p50/p99 on them "
   f"{np.percentile(np.abs(L['a3'] - co_ang[i])[mis], 50) if mis.any() else 0:.3f} / "
   f"{np.percentile(np.abs(L['a3'] - co_ang[i])[mis], 99) if mis.any() else 0:.3f} deg")
# raw sanity: the EPS received raw = floor(-10 co + .5)
rr = np.floor(-10.0 * co_ang + 0.5)
pr(f"  co_tqcan == floor(-10 co_ang + .5) on latActive rows: "
   f"{np.mean(rr[i][L['lat_m']] == co_raw[i][L['lat_m']]) * 100:.2f} %")

# =====================================================================================================================
# 5. STAGE (i): THE PLANNER (clip_curvature), bound-binding detected on the logged output, + memoryless replay
# =====================================================================================================================
tc = F["t_ctl"]; K = len(tc)
jcs, _ = latest(t, tc)                                         # controlsd's CS
vk = np.maximum(v[jcs], 1.0)
rollk = np.nan_to_num(zoh(F["t_lp"], F["lp_roll"], tc))
kd_ = F["ctl_dcurv"]; latk = F["cc_latActive"]
kmk = zoh(F["t_md"], F["md_act_curv"], tc)
lck = zoh(F["t_md"], F["md_lcstate"], tc)
step = PL_JERK / vk ** 2 * 0.01
dkd = np.r_[0.0, np.diff(kd_)]
pl_jerk = latk & (np.abs(dkd) >= 0.98 * step) & (np.abs(dkd) > 1e-7)
hi = (PL_ACC + rollk * G_ACC) / vk ** 2
lo = (-PL_ACC + rollk * G_ACC) / vk ** 2
pl_acc = latk & ((kd_ >= hi - 0.002 * np.abs(hi)) | (kd_ <= lo + 0.002 * np.abs(lo)))
pl_maxc = latk & (np.abs(kd_) >= PL_MAXC - 1e-6)
# lane-change smoothing window (jerk factor < 1): states 2/3 plus the 1 s release (LANE_CHANGE_SMOOTH_RELEASE_T, BELIEF)
lc_on = ((lck == 2) | (lck == 3)) & (v[jcs] >= float(TG.get('minimum_lane_change_speed', 8.9408)))
lc_win = np.convolve(lc_on.astype(float), np.ones(100), "full")[:K] > 0
# memoryless replay with new = the model action: kappa_hat = clip(km, prev +- step) then the accel clip
prev = np.r_[kd_[0], kd_[:-1]]
kh = np.clip(np.clip(kmk, prev - step, prev + step), lo, hi)
kh = np.clip(kh, -PL_MAXC, PL_MAXC)
rep_ok = np.abs(kh - kd_) < 1e-6
pr(f"\nSTAGE (i) PLANNER: latActive frames {int(latk.sum())}; clip_curvature bound binding: jerk "
   f"{100 * pl_jerk[latk].mean():.2f} %, accel {100 * pl_acc[latk].mean():.2f} %, max-curv {100 * pl_maxc[latk].mean():.3f} %;"
   f" lane-change window {100 * lc_win[latk].mean():.1f} %")
pr(f"  memoryless replay new = model action reproduces desiredCurvature (1e-6) on {100 * rep_ok[latk].mean():.1f} % of "
   f"latActive frames (the rest: hold / turn lead / lane centering / LC jerk factor modified the input)")
plj = zoh(tc, pl_jerk, t) > 0.5; pla = zoh(tc, pl_acc, t) > 0.5; plm = zoh(tc, pl_maxc, t) > 0.5
lcw = zoh(tc, lc_win, t) > 0.5

# =====================================================================================================================
# 6. STAGE (iv): THE FIRMWARE P on the received setpoint and on the unclipped demand; the tap vs the rail
# =====================================================================================================================
Gv = G_of_v(v)
sp_rx = -raw / 10.0                                            # theta_sp the EPS received
E_rx = sp_rx - th14                                            # deg; firmware E = 16 x this in 0.1-deg counts
E_un = cc_ang - th14                                           # the demand had the fork not limited it
E_rl = inp_on_m - th14                                         # (same as cc_ang, on the limiter's own row)
fB = np.interp(np.minimum(np.abs(bar) / 32.0, 255.0), (16, 26, 38, 48, 64, 96), (255, 243, 218, 179, 77, 77))
f_now = np.floor(255 * fB / 256.0)                             # fadeA2 255 at rest x fadeB2(|tq|>>5) >> 8


def P_T(E_deg):
    """P in T counts: clamp((E*G)>>8 * 112 >> 8, +-PCL), x fade, clamped at SCL, x lag DC x fwd (float mirror)."""
    P = np.clip(160.0 * E_deg * Gv * KP / 65536.0, -PCL, PCL)
    S = np.clip(P * f_now / 256.0, -SCL, SCL)
    return S * LAGDC * FWD / 32768.0


PT_rx, PT_un = P_T(E_rx), P_T(E_un)
cap_T = S_PER_DEG(Gv) * emax_of(v) * KOUT                      # the error clip's P cap, T counts

# =====================================================================================================================
# 7. STAGE (v): rates and accelerations (Savitzky-Golay, 100 Hz)
# =====================================================================================================================
def sg(x, deriv, win=15):
    x = np.nan_to_num(np.asarray(x, float))
    return signal.savgol_filter(x, win, 3, deriv=deriv, delta=0.01)


th_d1, th_d2 = w18, sg(th14, 2, 21)
sp_d1, sp_d2 = sg(sp_rx, 1), sg(sp_rx, 2, 21)
cc_d1 = sg(cc_ang, 1)
th_d3 = sg(th14, 3, 31); sp_d3 = sg(sp_rx, 3, 31)

# =====================================================================================================================
# 8. HARD MANOEUVRES
# =====================================================================================================================
alat = np.abs(dk) * v ** 2
hard = lat & ((np.abs(theta) > 30) | (np.abs(rate_cs) > 60) | (alat > 2.0))
hard &= np.isfinite(dk)


def runs(mask, gap=100, minlen=20):
    mask = np.asarray(mask, bool)
    d = np.diff(np.r_[0, mask.astype(int), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    if not len(a):
        return []
    out = [[a[0], b[0]]]
    for x, y in zip(a[1:], b[1:]):
        if x - out[-1][1] <= gap:
            out[-1][1] = y
        else:
            out.append([x, y])
    return [(x, y) for x, y in out if y - x >= minlen]


EV = runs(hard)
handsoff = np.abs(bar) < 500.0


def pct(x):
    return 100.0 * float(np.mean(x)) if len(x) else float("nan")


rows = []
for k, (a, b) in enumerate(EV):
    s = slice(a, b)
    sgn = np.sign(np.nanmedian(theta[s])) or 1.0
    vv = v[s]
    hm = lat[s]
    planner = plj[s] | pla[s] | plm[s]
    lim = rate_bind[s] | acc_bind[s]
    ecl = ecl_bind[s]
    rail = np.abs(tap[s]) >= R_PRE
    ovr = ovrL[s]
    none = ~(planner | lim | ecl | rail | ovr)
    # planner deficit in lateral accel (model vs desired, same direction)
    am, ad = np.abs(kmod[s]) * vv ** 2, np.abs(dk[s]) * vv ** 2
    same = np.sign(kmod[s]) == np.sign(dk[s])
    pl_def = float(np.nanmax(np.where(same, am - ad, 0.0))) if np.any(same) else 0.0
    # limiter loss in degrees (demand cc_ang vs applied co)
    gap_cc_co = np.abs(cc_ang[s] - co_on_m[s])
    j_pk = a + int(np.nanargmax(np.abs(cc_ang[s] - th14[s])))
    rows.append(dict(
        k=k, t0=float(t[a]), dur=float((b - a) * 0.01), v_mean=float(np.mean(vv)), v_min=float(vv.min()),
        v_max=float(vv.max()), pk_theta=float(np.max(np.abs(theta[s]))), pk_rate=float(np.max(np.abs(rate_cs[s]))),
        pk_w18=float(np.max(np.abs(w18[s]))), pk_alat_des=float(np.nanmax(ad)), pk_alat_mod=float(np.nanmax(am)),
        handsoff=pct(handsoff[s]), override=pct(ovr), engaged=pct(sd_en[s]), aol=pct(aol[s] & ~sd_en[s]),
        pl_pct=pct(planner), pl_jerk=pct(plj[s]), pl_acc=pct(pla[s]), lc=pct(lcw[s]), pl_def=pl_def,
        sat=pct(ang_sat[s]),
        lim_pct=pct(lim), rate120=pct(rate_bind[s] & ~jerk_is_cap[s]), jerkvm=pct(rate_bind[s] & jerk_is_cap[s]),
        accvm=pct(acc_bind[s]), ecl_pct=pct(ecl), rail_pct=pct(rail), ovr_pct=pct(ovr), none_pct=pct(none),
        pk_dem_err=float(np.nanmax(np.abs(E_un[s]))), pk_rx_err=float(np.nanmax(np.abs(E_rx[s]))),
        emax=float(np.nanmedian(em_on_m[s])), pk_gap=float(np.nanmax(gap_cc_co)),
        pk_ecl_loss=float(np.max(ecl_loss[s])), pk_rate_loss=float(np.max(rate_loss[s])),
        pk_tap=float(np.nanmax(np.abs(tap[s]))), p95_tap=float(np.nanpercentile(np.abs(tap[s]), 95)),
        pk_PT_rx=float(np.nanmax(np.abs(PT_rx[s]))), pk_PT_un=float(np.nanmax(np.abs(PT_un[s]))),
        cap_T=float(np.nanmedian(cap_T[s])),
        pk_sp_rate=float(np.max(np.abs(sp_d1[s]))), pk_cc_rate=float(np.nanmax(np.abs(cc_d1[s]))),
        pk_th_acc=float(np.max(np.abs(th_d2[s]))), pk_sp_acc=float(np.max(np.abs(sp_d2[s]))),
        pk_th_jerk=float(np.max(np.abs(th_d3[s]))), pk_sp_jerk=float(np.max(np.abs(sp_d3[s]))),
        dmax=float(np.nanmedian(dmax_on_m[s])),
        G=float(np.median(Gv[s])),
    ))

# =====================================================================================================================
# 9. POOLED over all hard-manoeuvre frames, split hands-off / override
# =====================================================================================================================
Hm = np.zeros(N, bool)
for a, b in EV:
    Hm[a:b] = True
HO = Hm & handsoff & ~ovrL
pr(f"\nHARD MANOEUVRES: {len(EV)} events, {Hm.sum() / 100:.1f} s; hands-off & no override {HO.sum() / 100:.1f} s; "
   f"latActive total {lat.sum() / 100:.0f} s, engaged (sd_enabled) {sd_en.sum() / 100:.0f} s")


def pool(mask, tag):
    planner = (plj | pla | plm)[mask]
    lim = (rate_bind | acc_bind)[mask]
    ecl = ecl_bind[mask]
    rail = (np.abs(tap) >= R_PRE)[mask]
    ov = ovrL[mask]
    none = ~(planner | lim | ecl | rail | ov)
    d = dict(tag=tag, s=mask.sum() / 100.0, planner=pct(planner), pl_jerk=pct(plj[mask]), pl_acc=pct(pla[mask]),
             lc=pct(lcw[mask]), limiter=pct(lim), rate120=pct((rate_bind & ~jerk_is_cap)[mask]),
             jerkvm=pct((rate_bind & jerk_is_cap)[mask]), accvm=pct(acc_bind[mask]), eclip=pct(ecl),
             rail=pct(rail), override=pct(ov), none=pct(none),
             tap_pk=float(np.nanmax(np.abs(tap[mask]))) if mask.any() else np.nan,
             tap_p99=float(np.nanpercentile(np.abs(tap[mask]), 99)) if mask.any() else np.nan,
             tap_p95=float(np.nanpercentile(np.abs(tap[mask]), 95)) if mask.any() else np.nan,
             PTun_p95=float(np.nanpercentile(np.abs(PT_un[mask]), 95)) if mask.any() else np.nan,
             PTrx_p95=float(np.nanpercentile(np.abs(PT_rx[mask]), 95)) if mask.any() else np.nan)
    return d


POOL = [pool(Hm, "all hard"), pool(HO, "hard, hands-off, no override"), pool(Hm & ovrL, "hard, override"),
        pool(lat & ~Hm, "latActive, not hard")]
for d in POOL:
    pr("  %-30s %6.1f s  planner %5.1f (jerk %4.1f acc %4.1f LC %4.1f)  limiter %5.1f (120 %4.1f jerkVM %4.1f accVM %4.1f)"
       "  eclip %5.1f  rail %4.1f  override %5.1f  none %5.1f | tap pk %.0f p99 %.0f p95 %.0f  P_un p95 %.0f T  P_rx p95 %.0f T"
       % (d["tag"], d["s"], d["planner"], d["pl_jerk"], d["pl_acc"], d["lc"], d["limiter"], d["rate120"], d["jerkvm"],
          d["accvm"], d["eclip"], d["rail"], d["override"], d["none"], d["tap_pk"], d["tap_p99"], d["tap_p95"],
          d["PTun_p95"], d["PTrx_p95"]))

# whole-route rail check
pr(f"\nTAP over the whole route: |tap| max {np.nanmax(np.abs(TAP)):.0f} LSB = {np.nanmax(np.abs(TAP)) * 8:.0f} T = "
   f"{100 * np.nanmax(np.abs(TAP)) / TAP_RAIL:.0f} % of the {T_RAIL} T rail; frames >= 300: {int(np.sum(np.abs(TAP) >= 300))}")

# =====================================================================================================================
# 10. THE ERROR CLIP'S P CAP per band (image G walk x fork clip), vs the values.py comment
# =====================================================================================================================
pr("\nERROR-CLIP P CAP (P only, hands-off, ramp full): s(v) x clip(v)")
vs = np.array(EMAX_BP)
CLAIM = [36, 40, 26, 17, 16, 18]
cap_rows = []
for vk_, cl in zip(vs, CLAIM):
    Gk = G_of_v(vk_)
    sT = S_PER_DEG(Gk) * KOUT
    cap = sT * emax_of(vk_)
    cap_rows.append(dict(v=float(vk_), G=float(Gk), s=sT, clip=float(emax_of(vk_)), capT=cap,
                         pct_rail=100 * cap / T_RAIL, pct_2461=100 * cap / 2461.0, claim=cl,
                         err_for_rail=T_RAIL / sT))
    pr(f"  v {vk_:5.2f}  G {Gk:5.0f}  s {sT:5.1f} T/deg  clip {emax_of(vk_):4.1f} deg  cap {cap:5.0f} T = "
       f"{100 * cap / T_RAIL:4.1f} % of {T_RAIL} ({100 * cap / 2461:4.1f} % of 2461; values.py {cl} %)  "
       f"error for P alone to reach the rail {T_RAIL / sT:5.1f} deg")
BANDS = (("<5", 0, 5), ("5-8", 5, 8), ("8-10", 8, 10), ("10-12.5", 10, 12.5), ("12.5-15", 12.5, 15),
         ("15-22", 15, 22), (">22", 22, 99))
band_rows = []
for nm, lo_, hi_ in BANDS:
    vg = np.linspace(max(lo_, 0.5), min(hi_, 35.0), 200)
    capv = S_PER_DEG(G_of_v(vg)) * KOUT * emax_of(vg)
    mk = lat & (v >= lo_) & (v < hi_)
    mh = Hm & (v >= lo_) & (v < hi_)
    band_rows.append(dict(band=nm, cap_min=100 * capv.min() / T_RAIL, cap_max=100 * capv.max() / T_RAIL,
                          lat_s=mk.sum() / 100, hard_s=mh.sum() / 100,
                          ecl_lat=pct(ecl_bind[mk]) if mk.any() else np.nan,
                          ecl_hard=pct(ecl_bind[mh]) if mh.any() else np.nan,
                          tap_pk=float(np.nanmax(np.abs(tap[mk & eng_w]))) if (mk & eng_w).any() else np.nan,
                          tap_p99=float(np.nanpercentile(np.abs(tap[mk & eng_w]), 99)) if (mk & eng_w).any() else np.nan))
pr("  per band: cap % of rail (min..max over the band) | latActive s, hard s | error clip active % (lat / hard) | tap pk/p99")
for r in band_rows:
    pr("  %-8s %4.1f..%4.1f %%  | %6.1f s %5.1f s | %5.1f / %5.1f %% | %s / %s" % (
        r["band"], r["cap_min"], r["cap_max"], r["lat_s"], r["hard_s"], r["ecl_lat"], r["ecl_hard"],
        "%.0f" % r["tap_pk"] if np.isfinite(r["tap_pk"]) else "-", "%.0f" % r["tap_p99"] if np.isfinite(r["tap_p99"]) else "-"))

# =====================================================================================================================
# 11. REFERENCES -- same unit (tap field LSB), engaged (req & sca), hard by angle/rate only (no fork data on refs)
# =====================================================================================================================
def ref_stats(tag):
    D = dict(np.load(CACHE / (tag + ".npz")))
    tt = D["t18"]
    th = np.interp(tt, D["t14"], D["ang"])
    w = -D["rate"] / 8.0
    rq = zoh(D["te4"], D["req"], tt) > 0.5
    en = rq & (D["sca"] > 0.5)
    fl = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    tp = np.where(fl >= 512, -1.0, 1.0) * (fl & 511)
    tp100 = zoh(D["t1ab"], tp, tt)
    vv = np.interp(tt, D["tcs"], D["vego"])
    br = np.abs(D["tq"] * 1.024)
    hd = en & ((np.abs(th) > 30) | (np.abs(w) > 60))
    ho = hd & (br < 500)
    acc = sg(th, 2, 21)

    def st(mk):
        if not mk.any():
            return dict(s=0.0)
        a = np.abs(tp100[mk])
        return dict(s=mk.sum() / 100.0, pk=float(np.nanmax(a)), p99=float(np.nanpercentile(a, 99)),
                    p999=float(np.nanpercentile(a, 99.9)), p95=float(np.nanpercentile(a, 95)),
                    rail=100.0 * float(np.mean(a >= R_PRE)), w_pk=float(np.max(np.abs(w[mk]))),
                    w_p99=float(np.percentile(np.abs(w[mk]), 99)), th_pk=float(np.max(np.abs(th[mk]))),
                    acc_p99=float(np.percentile(np.abs(acc[mk]), 99)))
    return dict(tag=tag, eng=st(en), hard=st(hd), hard_ho=st(ho))


REF = {}
for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294"):
    REF[tag] = ref_stats(tag)
pr("\nREFERENCES (tap field LSB; engaged = 0xE4 req & 0x18F SCA; hard = engaged & (|theta|>30 | |w18|>60))")
for tag, R in REF.items():
    for sub in ("eng", "hard", "hard_ho"):
        d = R[sub]
        if d.get("s", 0) == 0:
            pr(f"  {tag:14s} {sub:8s} (none)")
            continue
        pr("  %-14s %-8s %7.1f s  tap pk %3.0f p99.9 %3.0f p99 %3.0f p95 %3.0f  >=300 %5.2f %%  |w18| pk %4.0f p99 %4.0f  "
           "|theta| pk %4.0f  |acc| p99 %5.0f deg/s2" % (tag, sub, d["s"], d["pk"], d["p999"], d["p99"], d["p95"], d["rail"],
                                                    d["w_pk"], d["w_p99"], d["th_pk"], d["acc_p99"]))

# =====================================================================================================================
# 12. THE PER-MANOEUVRE TABLE
# =====================================================================================================================
pr("\nPER MANOEUVRE (t = logMonoTime s; % of the event's frames; deg / deg/s / T / tap LSB)")
hdr = ("  k   t0     dur  v(mean,min-max)  |th| |rate| aD  aM | HO%  ov% | plan% jrk acc LC def | lim% 120 jVM aVM | "
       "ecl% emax | rail% none% | dmdE rxE gap | PTun PTrx tap | spR ccR dmax thR | thA spA sat")
pr(hdr)
for r in rows:
    pr("  %2d %6.1f %4.1f %4.1f(%4.1f-%4.1f) %4.0f %4.0f %4.1f %4.1f | %3.0f %4.0f | %4.0f %3.0f %3.0f %3.0f %4.1f | %4.0f %3.0f "
       "%3.0f %3.0f | %4.0f %4.1f | %4.0f %4.0f | %4.1f %4.1f %4.1f | %4.0f %4.0f %3.0f | %4.0f %4.0f %4.0f %4.0f | %5.0f %5.0f %3.0f" % (
           r["k"], r["t0"], r["dur"], r["v_mean"], r["v_min"], r["v_max"], r["pk_theta"], r["pk_rate"], r["pk_alat_des"],
           r["pk_alat_mod"], r["handsoff"], r["override"], r["pl_pct"], r["pl_jerk"], r["pl_acc"], r["lc"], r["pl_def"],
           r["lim_pct"], r["rate120"], r["jerkvm"], r["accvm"], r["ecl_pct"], r["emax"], r["rail_pct"], r["none_pct"],
           r["pk_dem_err"], r["pk_rx_err"], r["pk_gap"], r["pk_PT_un"], r["pk_PT_rx"], r["pk_tap"], r["pk_sp_rate"],
           r["pk_cc_rate"], r["dmax"], r["pk_w18"], r["pk_th_acc"], r["pk_sp_acc"], r["sat"]))

# =====================================================================================================================
# 13. A SECOND METHOD for the limiter verdict: count by the LOGGED signals only (no recompute)
#     error-clip active <=> |co - theta| at the clip value; rate-limit active <=> |co[i] - co[i-1]| at d
# =====================================================================================================================
co_m = co_on_m
ecl2 = latL & ~ovrL & (np.abs(np.abs(co_m - theta) - em_on_m) < 0.011) & (np.abs(cc_ang - theta) > em_on_m)
dco = np.abs(np.r_[0.0, np.diff(co_m)]) * 100.0
rate2 = latL & ~ovrL & ~rel_edge & (np.abs(dco - dmax_on_m) < 0.01) & (np.abs(cc_ang - co_m) > 0.05)
rb_nr = rate_bind & ~rel_edge & ~acc_bind
pr(f"\nSECOND METHOD (logged signals only, hard frames): error clip at its bound {pct(ecl2[Hm]):.1f} % "
   f"(recompute {pct(ecl_bind[Hm]):.1f} %); rate step at the cap {pct(rate2[Hm]):.1f} % (recompute, release edges + accel-clip frames removed {pct(rb_nr[Hm]):.1f} %; all {pct(rate_bind[Hm]):.1f} %)")
pr(f"  same, hands-off & no override: error clip {pct(ecl2[HO]):.1f} % (recompute {pct(ecl_bind[HO]):.1f} %), "
   f"rate {pct(rate2[HO]):.1f} % (recompute {pct(rb_nr[HO]):.1f} % / all {pct(rate_bind[HO]):.1f} %)")
dco_free = dco[latL & ~ovrL & ~rel_edge]
pr(f"  max per-frame setpoint step, latActive, no override, no release edge: {dco_free.max():.4f} deg/s-equivalent "
   f"(= {dco_free.max() / 100:.5f} deg/frame; MAX_ANGLE_RATE 1.2 deg/frame)")

# tap vs P on the received error, hands-off hard frames (how much of the delivered torque is P)
ok = HO & np.isfinite(tap) & np.isfinite(PT_rx)
if ok.sum() > 50:
    b = np.polyfit(PT_rx[ok], tap[ok] * 8.0, 1)
    pr(f"  hands-off hard: tap*8 vs P_T(received error): slope {b[0]:.2f}, intercept {b[1]:.0f} T, "
       f"corr {np.corrcoef(PT_rx[ok], tap[ok])[0, 1]:.2f}; |tap*8| / |P_T(unclipped)| median "
       f"{np.nanmedian(np.abs(tap[ok] * 8) / np.maximum(np.abs(PT_un[ok]), 1)):.2f}")

# achieved vs setpoint rate in hands-off hard frames
pr(f"  hands-off hard: |w18| p99 {np.percentile(np.abs(w18[HO]), 99):.0f} deg/s, |d sp/dt| p99 "
   f"{np.percentile(np.abs(sp_d1[HO]), 99):.0f}, |d cc/dt| p99 {np.nanpercentile(np.abs(cc_d1[HO]), 99):.0f}; "
   f"|theta''| p99 {np.percentile(np.abs(th_d2[HO]), 99):.0f} deg/s2 vs |sp''| p99 {np.percentile(np.abs(sp_d2[HO]), 99):.0f}")

# =====================================================================================================================
# 14. EXTRAS: (ii) the angle controller; the VM jerk rate cap by speed; who steered the override frames; the firmware's
#     own hand-torque fade; the tap in the theta frame vs P and D; matched reference comparisons
# =====================================================================================================================
EXTRA = {}
# (ii) cc_ang == ang_des on latActive rows (row-paired ctl/cc), and the effective ratio of the setpoint
latc = F["cc_latActive"]
d_cc = np.abs(F["cc_ang"] - F["ang_des"])[latc]
EXTRA["cc_eq_angdes_frac"] = float(np.mean(d_cc < 1e-3))
kdc = F["ctl_dcurv"]; vctl = np.maximum(v[jcs], 1.0)
base1 = np.degrees(-kdc / curv_factor(vctl))                     # angle per unit sR at roll 0 (get_steer(-kappa))
srx = (F["ang_des"] - np.nan_to_num(zoh(F["t_lp"], F["lp_aoff"], tc))) / np.where(np.abs(base1) > 1e-9, base1, np.nan)
for lo_, hi_ in ((5, 30), (30, 90), (90, 180), (180, 400)):
    mk = latc & (np.abs(F["ang_des"]) >= lo_) & (np.abs(F["ang_des"]) < hi_) & (vctl > 1.5)
    EXTRA[f"sr_eff_{lo_}_{hi_}"] = float(np.nanmedian(srx[mk])) if mk.any() else float("nan")
pr(f"\nSTAGE (ii) ANGLE CONTROLLER: cc_ang == ang_des (1e-3 deg) on {100 * EXTRA['cc_eq_angdes_frac']:.2f} % of latActive rows; "
   "effective ratio (ang_des - offset) / (kappa-model angle per unit sR, roll 0) median by |ang_des|: "
   + "  ".join(f"{k[7:]} {EXTRA[k]:.2f}" for k in list(EXTRA) if k.startswith("sr_eff")))
pr(f"  angleState.saturated on hard frames {pct(ang_sat[Hm]):.1f} %, hands-off hard {pct(ang_sat[HO]):.1f} %")
# VM jerk-limited setpoint rate vs the 120 deg/s cap, by speed (carcontroller VM = VehicleModel(CP), sR 16.33)
vv_ = np.array([3.1, 5.0, 8.0, 9.0, 10.0, 11.75, 15.0, 17.5, 20.0, 26.9])
rcap = np.minimum(steer_from_curv_deg(LAT_JERK_CC / vv_ ** 2, vv_), 120.0)
acap = steer_from_curv_deg(LAT_ACC_CC / vv_ ** 2, vv_)
EXTRA["rate_cap"] = dict(zip(map(float, vv_), map(float, rcap)))
EXTRA["angle_cap"] = dict(zip(map(float, vv_), map(float, acap)))
pr("  fork setpoint RATE cap min(VM 3.589 m/s^3, 120 deg/s) by v: " + "  ".join(f"{a:.1f}:{b:.0f}" for a, b in zip(vv_, rcap)))
pr("  fork setpoint ANGLE cap (VM 3.589 m/s^2) by v:             " + "  ".join(f"{a:.1f}:{b:.0f}" for a, b in zip(vv_, acap)))
# who steered the override frames: hand torque toward the planner's demand (helping a slow wheel) or against it
ovh = Hm & ovrL & np.isfinite(cc_ang)
agree = np.sign(tqd) == np.sign(cc_ang - theta)
toward_wheel = np.sign(tqd) == np.sign(w18)
EXTRA["ovr_hand_toward_demand"] = pct(agree[ovh]); EXTRA["ovr_hand_with_motion"] = pct(toward_wheel[ovh])
pr(f"  override frames in hard manoeuvres ({ovh.sum() / 100:.1f} s): hand torque toward the planner's demand "
   f"{EXTRA['ovr_hand_toward_demand']:.0f} %, in the direction of wheel motion {EXTRA['ovr_hand_with_motion']:.0f} %; "
   f"|bar| p50/p90 {np.percentile(np.abs(bar[ovh]), 50):.0f}/{np.percentile(np.abs(bar[ovh]), 90):.0f}")
# firmware fade (fadeB2 keyed min(|tq|>>5,255); gp-0x4f68 ~ |bar| BELIEF) and the A3 hard freeze (|tq| > 512)
EXTRA["fade_ovr_p50"] = float(np.percentile(f_now[ovh] / 256.0, 50)) if ovh.any() else np.nan
EXTRA["fade_ovr_p10"] = float(np.percentile(f_now[ovh] / 256.0, 10)) if ovh.any() else np.nan
EXTRA["freeze_hard"] = pct((np.abs(bar) > 512)[Hm])
pr(f"  firmware hand-torque fade on those frames: median x{EXTRA['fade_ovr_p50']:.2f}, p10 x{EXTRA['fade_ovr_p10']:.2f}; "
   f"I hard-frozen (|bar| > 512) on {EXTRA['freeze_hard']:.0f} % of hard frames")
# the tap in the theta frame (u_theta = -tap: tap sign = +sign(raw), raw = -10 theta_sp) vs P(E_rx) and w18
tapth = -tap * 8.0
okh = HO & np.isfinite(tapth)
best_l = None
for lag in range(0, 9):
    Pl = np.r_[np.full(lag, np.nan), PT_rx[:N - lag]] if lag else PT_rx
    wl = np.r_[np.full(lag, np.nan), w18[:N - lag]] if lag else w18
    mk = okh & np.isfinite(Pl) & np.isfinite(wl)
    X = np.c_[Pl[mk], wl[mk], np.ones(mk.sum())]
    bb, *_ = np.linalg.lstsq(X, tapth[mk], rcond=None)
    r2 = 1 - np.var(tapth[mk] - X @ bb) / np.var(tapth[mk])
    if best_l is None or r2 > best_l[2]:
        best_l = (lag, bb, r2, np.corrcoef(Pl[mk], tapth[mk])[0, 1])
EXTRA["tap_fit"] = dict(lag=best_l[0], cP=float(best_l[1][0]), cW=float(best_l[1][1]), c0=float(best_l[1][2]),
                        r2=float(best_l[2]), corrP=float(best_l[3]))
pr(f"  hands-off hard, theta frame: tap*8 = {best_l[1][0]:.2f} P_T(E_rx) {best_l[1][1]:+.2f} T/(deg/s) w18 {best_l[1][2]:+.0f} "
   f"(lag {best_l[0]} frames, R2 {best_l[2]:.2f}; corr with P alone {best_l[3]:.2f})")
EXTRA["un_rail_ho"] = pct((np.abs(PT_un) >= 0.97 * T_RAIL)[HO])
pr(f"  hands-off hard: frames where the UNCLIPPED demand's P would reach the rail {EXTRA['un_rail_ho']:.0f} %; "
   f"delivered |tap*8| p50 {np.percentile(np.abs(tapth[okh]), 50):.0f} / p95 {np.percentile(np.abs(tapth[okh]), 95):.0f} / "
   f"max {np.max(np.abs(tapth[okh])):.0f} T = {100 * np.max(np.abs(tapth[okh])) / T_RAIL:.0f} % of rail")


def ref_matched(tag):
    D = dict(np.load(CACHE / (tag + ".npz")))
    tt = D["t18"]
    th = np.interp(tt, D["t14"], D["ang"]); w = -D["rate"] / 8.0
    rq = zoh(D["te4"], D["req"], tt) > 0.5
    en = rq & (D["sca"] > 0.5)
    fl = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    tp = np.abs(zoh(D["t1ab"], np.where(fl >= 512, -1.0, 1.0) * (fl & 511), tt))
    vv = np.interp(tt, D["tcs"], D["vego"]); ho = np.abs(D["tq"] * 1.024) < 500
    j3 = np.abs(sg(th, 3, 31)); a2 = np.abs(sg(th, 2, 21))
    out = {}
    for nm, mk in (("eng ho v<10 |th|30-90", en & ho & (vv < 10) & (np.abs(th) >= 30) & (np.abs(th) < 90)),
                   ("eng ho v<10 |th|>=90", en & ho & (vv < 10) & (np.abs(th) >= 90)),
                   ("eng ho |w|>60", en & ho & (np.abs(w) > 60)),
                   ("eng ho v>=10 |th|>=10", en & ho & (vv >= 10) & (np.abs(th) >= 10))):
        if mk.sum() < 50:
            out[nm] = dict(s=mk.sum() / 100.0)
            continue
        out[nm] = dict(s=mk.sum() / 100.0, tap_p50=float(np.nanpercentile(tp[mk], 50)), tap_p95=float(np.nanpercentile(tp[mk], 95)),
                       tap_pk=float(np.nanmax(tp[mk])), w_p95=float(np.percentile(np.abs(w[mk]), 95)),
                       a_p95=float(np.percentile(a2[mk], 95)), j_p95=float(np.percentile(j3[mk], 95)))
    return out


MATCH = {tag: ref_matched(tag) for tag in ("r79_a1f5d2_al", "r6c", "r39", "r71b_v294")}
pr("\nMATCHED CONDITIONS (engaged, hands-off): tap p50/p95/pk LSB | |w18| p95 deg/s | |th2| p95 deg/s2 | |th3| p95 deg/s3")
for nm in next(iter(MATCH.values())):
    for tag, M in MATCH.items():
        d = M[nm]
        if "tap_p50" not in d:
            pr(f"  {nm:24s} {tag:14s} {d['s']:6.1f} s (too few)")
            continue
        pr("  %-24s %-14s %6.1f s  tap %3.0f/%3.0f/%3.0f | w %4.0f | a %5.0f | j %6.0f" % (
            nm, tag, d["s"], d["tap_p50"], d["tap_p95"], d["tap_pk"], d["w_p95"], d["a_p95"], d["j_p95"]))
EXTRA["matched"] = MATCH
# how far the applied setpoint fell behind the demand (hands-off, no override, hard), and how long the 120 cap needs
gap_ho = np.abs(cc_ang - co_on_m)[HO]
gap_ho = gap_ho[np.isfinite(gap_ho)]
EXTRA["gap_ho"] = dict(p50=float(np.percentile(gap_ho, 50)), p95=float(np.percentile(gap_ho, 95)), max=float(gap_ho.max()),
                       gt10=pct(gap_ho > 10.0), gt30=pct(gap_ho > 30.0))
pr(f"  hands-off hard: |demand - applied setpoint| p50 {EXTRA['gap_ho']['p50']:.1f} / p95 {EXTRA['gap_ho']['p95']:.1f} / max "
   f"{EXTRA['gap_ho']['max']:.0f} deg; > 10 deg on {EXTRA['gap_ho']['gt10']:.0f} %, > 30 deg on {EXTRA['gap_ho']['gt30']:.0f} % "
   f"(at 120 deg/s, 30 deg = 0.25 s behind)")
# rail cells identical across V282 / V294 / V295 / V298 (EVIDENCE: image reads)
RAILX = {}
for tagi, patn in (("V282", "_v282_*plain_image.bin"), ("V294", "_v294_*plain_image.bin"), ("V298", "_v298_*plain_image.bin")):
    fs = glob.glob(str(FW / "analysis-2020accord" / patn))
    if fs:
        im = Path(fs[0]).read_bytes()
        RAILX[tagi] = dict(SCL=struct.unpack_from("<H", im, TP + 0x71BE)[0], fwd=struct.unpack_from("<h", im, TP + 0x7CD0)[0],
                           oa=struct.unpack_from("<h", im, TP + 0x73EC)[0], ob=struct.unpack_from("<H", im, TP + 0x73EE)[0])
EXTRA["rail_cells"] = RAILX
pr("  rail cells by image: " + "  ".join(f"{k} SCL {d['SCL']} fwd {d['fwd']} oa {d['oa']} ob {d['ob']}" for k, d in RAILX.items()))

RT = time.time() - T_START
pr(f"\nwall time {RT:.2f} s")
json.dump(dict(image=IMG.name, sha=SHA, rail=dict(SCL=SCL, OCL=OCL, Y=Y_RAIL, T=T_RAIL, tap=TAP_RAIL, kout=KOUT,
                                                   lagdc=LAGDC),
               limiter_reproduction=dict(off=OFF, frac_lat=fr_lat), events=rows, pool=POOL, caps=cap_rows,
               bands=band_rows, refs=REF, extra=EXTRA, wall_s=RT),
          open(OUT / "m2_authority_budget.json", "w"), indent=1, default=float)
open(OUT / "m2_authority_budget.txt", "w").write("\n".join(LOG) + "\n")
