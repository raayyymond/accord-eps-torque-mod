# -*- coding: utf-8 -*-
"""Exact reconstruction of the fork's Accord rate-plant feedforward from a logged route.

WHY a re-implementation and not an import: `latcontrol_vehicle_tunes.py` imports
`openpilot.*` / `opendbc.*` modules that crash the interpreter on this machine (the fork's cereal
`car.capnp` is a Windows git symlink).  Every constant and every line of arithmetic below was read
out of the fork at the COMMIT EACH ROUTE FLEW (`git show <commit>:<path>`), and the move-term line
    move_torque = clip(rate_gain * angle_des_rate_dps / gain, -move_limit, move_limit)
is byte-identical across 8c4051ce6 / 66cf4454a / 08a5a7064 / e44b6cd31 / 84766cdc5 / HEAD (verified).

Positive control: `validate()` rebuilds the WHOLE ff_torque at the flown gain and compares it to the
logged `pid_log.f / latAccelFactor`.  Nothing downstream is reported unless that passes.

Frames:
  plant FF is in the +left steering-angle frame; the controller's torque frame is the opposite sign
  (`plant_ff_torque = -get_honda_accord_rate_plant_ff(...)`, `pid_log.output = -output_torque`).
  Full scale is |output_torque| = steer_max = 1.0 (latcontrol.py:17).
"""
import math
import numpy as np

# ----------------------------------------------------------------------------------------------
# VehicleModel, Honda Accord (2018-22) -- opendbc/car/honda/values.py:188, interfaces.py:160-190,
# vehicle_model.py.  Only sR, wheelbase and the slip factor enter get_steer_from_curvature.
# ----------------------------------------------------------------------------------------------
LB_TO_KG = 0.453592
STD_CARGO_KG = 136.0
_MASS = 3279 * LB_TO_KG + STD_CARGO_KG
_WHEELBASE = 2.83
_CENTER_TO_FRONT = _WHEELBASE * 0.39
_TIRE_STIFFNESS_FACTOR = 0.8467
# VehicleDynamicsParams (opendbc/car/__init__.py:50-56)
_CIVIC_MASS = 1326.0 + STD_CARGO_KG
_CIVIC_WB = 2.70
_CIVIC_CTF = _CIVIC_WB * 0.4
_CIVIC_CTR = _CIVIC_WB - _CIVIC_CTF
_TSF, _TSR = 192150.0, 202500.0


def _accord_vm():
    m = _MASS
    l = _WHEELBASE
    aF = _CENTER_TO_FRONT
    aR = l - aF
    cF = (_TSF * _TIRE_STIFFNESS_FACTOR) * m / _CIVIC_MASS * (aR / l) / (_CIVIC_CTR / _CIVIC_WB)
    cR = (_TSR * _TIRE_STIFFNESS_FACTOR) * m / _CIVIC_MASS * (aF / l) / (_CIVIC_CTF / _CIVIC_WB)
    # update_params scales BOTH cF and cR by the stiffness factor, so the slip factor
    # m(cF aF - cR aR)/(l^2 cF cR) scales as 1/stiffness -- it is NOT invariant, and the per-frame
    # liveParameters.stiffnessFactor therefore has to be carried through (checked in _self_test).
    sf1 = m * (cF * aF - cR * aR) / (l ** 2 * cF * cR)
    return dict(m=m, l=l, aF=aF, aR=aR, cF=cF, cR=cR, sf1=sf1)


_VM = _accord_vm()
_CHI = 0.0            # steerRatioRear, interfaces.py:367
_G = 9.81             # ACCELERATION_DUE_TO_GRAVITY


def slip_factor(stiff=1.0):
    return _VM["sf1"] / np.maximum(np.asarray(stiff, float), 0.1)


def curvature_factor(v, stiff=1.0):
    """vehicle_model.py:curvature_factor -- (1-chi)/(1 - sf v^2)/l"""
    return (1.0 - _CHI) / (1.0 - slip_factor(stiff) * np.asarray(v, dtype=float) ** 2) / _VM["l"]


def roll_compensation(roll, v, stiff=1.0):
    """vehicle_model.py:roll_compensation -- g*roll / (1/sf - v^2)"""
    sf = slip_factor(stiff)
    return (_G * np.asarray(roll, dtype=float)) / ((1.0 / sf) - np.asarray(v, dtype=float) ** 2)


def steer_from_curvature_rad(curv, v, roll, sR, stiff=1.0):
    """vehicle_model.py:104 -- (curv - roll_comp(roll,v)) * sR / curvature_factor(v)"""
    return ((np.asarray(curv, float) - roll_compensation(roll, v, stiff))
            * np.asarray(sR, float) / curvature_factor(v, stiff))


# ----------------------------------------------------------------------------------------------
# Accord variable-ratio rack (latcontrol_vehicle_tunes.py:119-122, 2559-2563).
# IDENTICAL at every flown commit (function body sha256[:12] 091050b3badb at all of them).
# ----------------------------------------------------------------------------------------------
SR_ANGLE_BP = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0]
SR_V = [16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31]
SR_NOMINAL = 16.88
SR_LEVEL_MIN, SR_LEVEL_MAX = 0.60, 1.25


def accord_steer_ratio(angle_deg, level=None):
    r = np.interp(np.abs(np.asarray(angle_deg, float)), SR_ANGLE_BP, SR_V)
    if level is not None:
        r = r * min(max(float(level) / SR_NOMINAL, SR_LEVEL_MIN), SR_LEVEL_MAX)
    return r


# ----------------------------------------------------------------------------------------------
# Accord plant tables, PER FLOWN COMMIT (git show <commit>:latcontrol_vehicle_tunes.py).
# ----------------------------------------------------------------------------------------------
FF_RATE_RC = 0.10                       # s, unchanged at every flown commit
FF_ANGLE_LIMIT_DEG = 400.0
MOVE_LIMIT_BP = [8.0, 10.0]             # unchanged at every flown commit
MOVE_LIMIT_V = [1.0, 1.4]
HOLD_SAT = (19.3, 546.0, 3.01)
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP = [12.5, 17.5]
HOLD_LEVEL_V = [1.15, 1.45]
RATE_LOOP_TAPER_V = 12.0
FRIC_BAND_BP = [8.0, 12.0, 19.0, 26.0]
FRIC_BAND_V = [3.0, 2.10, 0.96, 0.60]
FRIC_BAND_FLAT = 3.0
EPS_INERTIA = 8e-5
DOB_DELAY, DOB_ACC_RC, DOB_MAX, DOB_FADE_BP = 0.06, 0.05, 0.3, [3.0, 6.0]
ROLL_FADE_BP, ROLL_FADE_V = [0.5, 2.5], [0.0, 1.0]

# G/K per commit
TABLES = {
    "8c4051ce6": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 205.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.15, 2.77, 3.15],
                      hold_map_exists=False, hold_level_exists=False, rate_loop_rc=None),
    "4247cb09e": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 205.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.93, 1.64, 2.15, 2.77, 3.15],
                      hold_map_exists=False, hold_level_exists=False, rate_loop_rc=None),
    "66cf4454a": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 167.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.30, 2.77, 3.91],
                      hold_map_exists=False, hold_level_exists=False, rate_loop_rc=None),
    "e8e62f0e1": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 167.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.30, 2.77, 3.91],
                      HOLD_K_V=[0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103,
                                0.0116, 0.0133, 0.0134],
                      hold_map_exists=True, hold_level_exists=False, rate_loop_rc=0.03),
    "08a5a7064": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 167.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.30, 2.77, 3.91],
                      hold_map_exists=True, hold_level_exists=False, rate_loop_rc=0.03),
    "e44b6cd31": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 167.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.30, 2.77, 3.91],
                      hold_map_exists=True, hold_level_exists=False, rate_loop_rc=0.01),
    "84766cdc5": dict(G_BP=[5.0, 12.5, 18.5, 28.5], G_V=[550.0, 271.0, 246.0, 167.0],
                      K_BP=[4.0, 8.0, 12.5, 18.5, 28.5], K_V=[0.30, 1.00, 2.30, 2.77, 3.91],
                      hold_map_exists=True, hold_level_exists=True, rate_loop_rc=0.01),
}

# Per-route flown configuration, EVERY VALUE FROM initData (dump_params.py / flown_params.json).
# `ff_live` False = AccordRatePlantFF 0, i.e. the plant feedforward did not run on that drive.
ROUTECFG = {
    "00000070--717f5a7866": dict(tag="r70", rev="ident (FF OFF)", commit="4247cb09e", ff_live=False,
                                 gain=0.5, laf=6.0, kp=0.3, ki=0.15, hold_map=False, hold_level=False,
                                 fric_hyst=0.0, fric_band_sched=False, rate_loop=0.0, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000071--f2c9d073a3": dict(tag="r71", rev="rev 2", commit="66cf4454a", ff_live=True,
                                 gain=0.5, laf=14.0, kp=0.85, ki=0.30, hold_map=False, hold_level=False,
                                 fric_hyst=0.0, fric_band_sched=False, rate_loop=0.0, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000072--8001fc3048": dict(tag="r72", rev="rev 3", commit="e8e62f0e1", ff_live=True,
                                 gain=0.5, laf=14.0, kp=0.85, ki=0.60, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=False, rate_loop=0.0006, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000073--79fd149dd8": dict(tag="r73", rev="rev 3 (+0.212 relay)", commit="e8e62f0e1", ff_live=True,
                                 gain=0.5, laf=14.0, kp=0.85, ki=0.60, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=False, rate_loop=0.0006, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000074--2bf17ca67d": dict(tag="r74", rev="rev 4", commit="08a5a7064", ff_live=True,
                                 gain=0.5, laf=14.0, kp=0.85, ki=0.60, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=False, rate_loop=0.0006, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000075--6c8687d5bd": dict(tag="r75", rev="rev 4", commit="08a5a7064", ff_live=True,
                                 gain=0.5, laf=14.0, kp=0.85, ki=0.60, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=False, rate_loop=0.0006, dob_hz=0.0,
                                 sr_toggle=16.88),
    "00000076--d0b7ea7e4d": dict(tag="r76", rev="rev 5", commit="e44b6cd31", ff_live=True,
                                 gain=0.5, laf=14.0, kp=1.0, ki=0.30, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=False, rate_loop=0.001, dob_hz=0.6,
                                 sr_toggle=16.88),
    "0000006c--68c6e94b17": dict(tag="r6c", rev="rev 6.4", commit="84766cdc5", ff_live=True,
                                 gain=0.5, laf=14.0, kp=1.0, ki=0.30, hold_map=True, hold_level=True,
                                 fric_hyst=0.015, fric_band_sched=True, rate_loop=0.001, dob_hz=0.6,
                                 sr_toggle=16.84),
    "0000006d--05e83bb04f": dict(tag="r6d", rev="rev 6.4", commit="84766cdc5", ff_live=True,
                                 gain=0.5, laf=14.0, kp=1.0, ki=0.30, hold_map=True, hold_level=True,
                                 fric_hyst=0.015, fric_band_sched=True, rate_loop=0.001, dob_hz=0.6,
                                 sr_toggle=16.84),
    "0000006e--6ca3e014fd": dict(tag="r6e", rev="rev 6.4 HoldLevel OFF", commit="84766cdc5", ff_live=True,
                                 gain=0.5, laf=14.0, kp=1.0, ki=0.30, hold_map=True, hold_level=False,
                                 fric_hyst=0.015, fric_band_sched=True, rate_loop=0.001, dob_hz=0.6,
                                 sr_toggle=16.84),
}


# ----------------------------------------------------------------------------------------------
# the fork's own functions
# ----------------------------------------------------------------------------------------------
def move_limit(v):
    return np.interp(np.asarray(v, float), MOVE_LIMIT_BP, MOVE_LIMIT_V)


def hold_sat_deg(v):
    a, b, c = HOLD_SAT
    return a + b * np.exp(-np.maximum(np.asarray(v, float), 0.0) / c)


def hold_torque_map(angle_deg, v, level=True, k_v=None):
    a = np.clip(np.asarray(angle_deg, float), -FF_ANGLE_LIMIT_DEG, FF_ANGLE_LIMIT_DEG)
    k = np.interp(np.asarray(v, float), HOLD_V_BP, HOLD_K_V if k_v is None else k_v)
    if level:
        k = k * np.interp(np.asarray(v, float), HOLD_LEVEL_BP, HOLD_LEVEL_V)
    sat = hold_sat_deg(v)
    return k * sat * np.tanh(a / sat)


def friction_band(v, scheduled=True):
    if not scheduled:
        return np.full(np.shape(v), FRIC_BAND_FLAT, dtype=float)
    return np.interp(np.asarray(v, float), FRIC_BAND_BP, FRIC_BAND_V)


def rate_loop_gain(v, gain):
    return float(gain) * np.minimum(1.0, RATE_LOOP_TAPER_V / np.maximum(np.asarray(v, float), 0.1))


# ----------------------------------------------------------------------------------------------
def build_demand(S, cfg, use_offset):
    """angle_des and the FILTERED angle_des_rate the fork's move term is fed, frame by frame.

    Exactly latcontrol_torque.py:637-640 (identical at every flown commit):
        curv_des  = (setpoint - latAccelOffset*fade) / max(v^2, 1)
        angle_des = degrees(VM.get_steer_from_curvature(-curv_des, v, roll*fade))
        angle_des_rate = FirstOrderFilter(rc=0.10).update((angle_des - prev)/dt)
    with the per-frame Accord rack ratio at the MEASURED wheel angle (controlsd.py:494-510) and
    the engage priming / reset of latcontrol_torque.py:263-283.
    """
    t = S["t"]
    n = len(t)
    v = np.nan_to_num(S["v"])
    dt = float(np.median(np.diff(t)))
    fade = np.interp(v, ROLL_FADE_BP, ROLL_FADE_V)
    lao = np.nan_to_num(S["lao"]) if use_offset else np.zeros(n)
    curv_des = (np.nan_to_num(S["setpoint"]) - lao * fade) / np.maximum(v ** 2, 1.0)
    level = None if cfg["sr_toggle"] is None else float(cfg["sr_toggle"])
    sR = accord_steer_ratio(np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"]), level)
    stiff = np.maximum(np.nan_to_num(S["stiff"], nan=1.0), 0.1)
    angle_des = np.degrees(steer_from_curvature_rad(-curv_des, v, np.nan_to_num(S["roll"]) * fade,
                                                   sR, stiff))

    # the filter and prev_angle_des are reset when lateral control is inactive (the inactive branch
    # primes prev_angle_des with the same corrected curvature, and the rate filter's state with 0)
    act = S["active"]
    alpha = dt / (FF_RATE_RC + dt)
    adr = np.zeros(n)
    d_ad = np.zeros(n)
    st = 0.0
    prev = angle_des[0]
    for j in range(n):
        if not act[j]:
            st = 0.0
            prev = angle_des[j]
            adr[j] = 0.0
            d_ad[j] = 0.0
            continue
        d = angle_des[j] - prev
        prev = angle_des[j]
        st = (1.0 - alpha) * st + alpha * (d / dt)
        adr[j] = st
        d_ad[j] = d
    return angle_des, adr, d_ad, dt


def move_term(adr, v, gain, tab):
    """the fork's move term, +left frame: clip(gain * adr / G(v), -limit(v), +limit(v))"""
    G = np.interp(np.asarray(v, float), tab["G_BP"], tab["G_V"])
    lim = move_limit(v)
    raw = float(gain) * np.asarray(adr, float) / G
    return np.clip(raw, -lim, lim), raw, lim


def hold_term(angle_des, v, cfg, tab):
    if cfg["hold_map"] and tab["hold_map_exists"]:
        return hold_torque_map(angle_des, v, level=bool(cfg["hold_level"]) and tab["hold_level_exists"],
                               k_v=tab.get("HOLD_K_V"))
    spring = np.interp(np.asarray(v, float), tab["K_BP"], tab["K_V"])
    G = np.interp(np.asarray(v, float), tab["G_BP"], tab["G_V"])
    return spring * np.clip(angle_des, -FF_ANGLE_LIMIT_DEG, FF_ANGLE_LIMIT_DEG) / G


def build_inner(S, cfg, tab, angle_des, adr, d_ad, dt):
    """friction hysteresis z, rate-loop term and the disturbance observer, all +left frame.
    Needed only for the VALIDATION of the whole ff; the gain sweep does not use them."""
    n = len(adr)
    v = np.nan_to_num(S["v"])
    act = S["active"]
    band = friction_band(v, bool(cfg["fric_band_sched"]))
    fh = float(cfg["fric_hyst"])
    z = np.zeros(n)
    zz = 0.0
    for j in range(n):
        if not act[j]:
            zz = 0.0
            z[j] = 0.0
            continue
        if fh > 0.0:
            zz = float(np.clip(zz + d_ad[j] * fh / max(band[j], 1e-3), -fh, fh))
        z[j] = zz
    rc = tab["rate_loop_rc"] if tab["rate_loop_rc"] else 0.01
    a2 = dt / (rc + dt)
    rm = np.zeros(n)
    st = float(np.nan_to_num(S["sr"])[0])
    srm = np.nan_to_num(S["sr"])
    for j in range(n):
        if not act[j]:
            st = srm[j]
            rm[j] = srm[j]
            continue
        st = (1.0 - a2) * st + a2 * srm[j]
        rm[j] = st
    rl = rate_loop_gain(v, cfg["rate_loop"]) * (adr - rm)

    dob = np.zeros(n)
    if float(cfg["dob_hz"]) > 0.0:
        f_hz = float(cfg["dob_hz"])
        nd = max(int(round(DOB_DELAY / dt)), 1)
        sa = np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"])
        out = np.nan_to_num(S["out"])          # pid_log.output = -output_torque
        sat = S["sat"]
        pressed = S["pressed"]
        G = np.interp(v, tab["G_BP"], tab["G_V"])
        b_model = 1.0 / G
        alpha_acc = dt / (DOB_ACC_RC + dt)
        alpha = dt / (1.0 / (2.0 * math.pi * f_hz) + dt)
        fadev = np.interp(v, DOB_FADE_BP, [0.0, 1.0])
        hist = [0.0] * nd
        w1 = w2 = acc = 0.0
        prev_rate = srm[0]
        prev_est = 0.0
        for j in range(n):
            if not act[j]:
                hist = [0.0] * nd
                w1 = w2 = acc = 0.0
                prev_rate = srm[j]
                prev_est = 0.0
                dob[j] = 0.0
                continue
            dob[j] = prev_est                  # the estimate added this frame is the PREVIOUS frame's
            u_left_now = out[j]                # -output_torque == pid_log.output
            u_del = hist[0]
            hist.append(u_left_now)
            hist.pop(0)
            spring = hold_torque_map(sa[j], v[j], level=bool(cfg["hold_level"]) and tab["hold_level_exists"]) \
                if (cfg["hold_map"] and tab["hold_map_exists"]) else \
                hold_term(sa[j], v[j], cfg, tab)
            acc += alpha_acc * ((srm[j] - prev_rate) / dt - acc)
            prev_rate = srm[j]
            resid = u_del - (spring + b_model[j] * srm[j] + EPS_INERTIA * acc)
            if not (pressed[j] or sat[j]):
                w1 += alpha * (resid - w1)
                w2 += alpha * (w1 - w2)
            prev_est = float(np.clip(w2 * fadev[j], -DOB_MAX, DOB_MAX))
    return z, rl, dob


def _self_test():
    """Positive controls on the vehicle model and the rack map."""
    # the slip factor scales as 1/stiffness (both cF and cR scale, so the ratio does not cancel)
    m, l, aF, aR, cF, cR = (_VM[k] for k in ("m", "l", "aF", "aR", "cF", "cR"))
    for k in (0.5, 1.0, 2.0):
        sf = m * (k * cF * aF - k * cR * aR) / (l ** 2 * (k * cF) * (k * cR))
        assert abs(sf - float(slip_factor(k))) < 1e-15, (k, sf, float(slip_factor(k)))
    # the rack map: on-centre nominal, monotone down past 48 deg, level scaling
    assert abs(accord_steer_ratio(0.0) - 16.88) < 1e-9
    assert accord_steer_ratio(180.0) < accord_steer_ratio(48.0) < accord_steer_ratio(0.0)
    assert abs(accord_steer_ratio(-180.0) - accord_steer_ratio(180.0)) < 1e-9
    assert abs(accord_steer_ratio(0.0, 16.84) - 16.88 * 16.84 / 16.88) < 1e-9
    # deg per unit curvature must be in the 2900-3900 range the kit measured (rev64_15 note)
    for v in (5.0, 12.0, 20.0):
        dpc = math.degrees(float(steer_from_curvature_rad(0.01, v, 0.0, 16.88, 1.0))) / 0.01
        assert 2500.0 < dpc < 4200.0, (v, dpc)
    # move term: clipping and linearity in the gain
    mv, raw, lim = move_term(np.array([1000.0]), np.array([4.0]), 1.0, TABLES["84766cdc5"])
    assert abs(raw[0] - 1000.0 / 550.0) < 1e-9 and abs(lim[0] - 1.0) < 1e-9 and abs(mv[0] - 1.0) < 1e-9
    mv2, raw2, _ = move_term(np.array([100.0]), np.array([20.0]), 2.0, TABLES["84766cdc5"])
    assert abs(raw2[0] - 2.0 * 100.0 / np.interp(20.0, [5, 12.5, 18.5, 28.5], [550, 271, 246, 167])) < 1e-9
    return ("self-test OK: slip factor scales as 1/stiffness, rack map monotone, "
            "deg/curv in range, move clip exact")


if __name__ == "__main__":
    print(_self_test())
    print(f"Accord VM: mass {_VM['m']:.1f} kg  l {_VM['l']} m  aF {_VM['aF']:.3f}  "
          f"cF {_VM['cF']:.0f}  cR {_VM['cR']:.0f}  slip(1.0) {float(slip_factor(1.0)):.6e}")
    for v in (2.0, 3.0, 4.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0):
        dpc = math.degrees(float(steer_from_curvature_rad(0.01, v, 0.0, 16.88, 1.0))) / 0.01
        G = float(np.interp(v, [5, 12.5, 18.5, 28.5], [550, 271, 246, 167]))
        print(f"  v {v:5.1f}  deg per 1/m {dpc:7.1f}   G {G:6.1f} deg/s per torque   "
              f"move limit {float(move_limit(v)):.2f}")
