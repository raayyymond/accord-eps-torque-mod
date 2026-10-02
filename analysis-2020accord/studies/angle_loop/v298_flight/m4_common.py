# -*- coding: utf-8 -*-
r"""m4_common.py -- M4 (SMOOTHNESS / STUTTER) shared loader for the V298 route-79 flight read.

ANALYSIS ONLY.  Reads the v280 wire caches, the drive-read's extras cache and the fork-side cache; writes only a
compact grid cache under _scratch/out/r79/m4/.  Never reads an rlog, never sends CAN, never flashes.

THE GRID is the drive-read's own: creep20_loop_id.load(tag) (de-jittered 0x18F frame axis, 100 Hz), so every number
here sits on the same samples the kit instrument used (angle_loop_drive_read.load_route -> make_wire -> derive).
Units / signs (EVIDENCE, angle_loop_drive_read docstring "UNITS AND SIGNS"):
  theta    = 0x14A angle, deg, carState sign (+ left)            theta_sp = -raw/10 deg (0xE4 bus 129, angle mode)
  w18      = -wire/8 deg/s, sign of d(theta)/dt                   bar      = 0x18F STEER_TORQUE_SENSOR x 1.024
  tap      = 0x1AB field LSB = T/8 (T = gp-0x6b38), sign +sign(raw); motor torque on the wheel u = -T
  err      = theta_sp - theta (deg); the firmware's E = 16*(theta_sp - theta) in 0.1-deg counts  (= -1.6 * e_w)
Fork-side fields (r79_fork.npz) are ZOH-aligned by logMonoTime (np.searchsorted, side='right').
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
KIT_AN = _d                                                   # analysis-2020accord
REPO = KIT_AN.parent
AL = KIT_AN / "studies" / "angle_loop"
for _p in [REPO / "rlog-tools" / "studies" / "grind", REPO / "rlog-tools" / "studies" / "angle_loop",
           REPO / "rlog-tools" / "lib", REPO / "rlog-tools", REPO / "rlog-tools" / "decode",
           REPO / "rlog-tools" / "studies" / "osc-highangle", KIT_AN / "studies" / "v280", KIT_AN / "lib",
           AL / "refute_c2r2_nonlinear", AL / "c3" / "rev2B", AL, AL / "panel", AL / "c1",
           AL.parent / "v295" / "plant", AL.parent / "v295" / "lib"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

CACHE = KIT_AN / "_scratch" / "cache" / "v280"
OUT = REPO / "_scratch" / "out" / "r79" / "m4"
OUT.mkdir(parents=True, exist_ok=True)
EXTRAS = REPO / "_scratch" / "angle_loop" / "drive-read" / "routes" / "75604b0a432fdc89_00000079--a1f5d2a272_extras.npz"
FS = 100.0
DT = 0.01
TAG79 = "r79_a1f5d2_al"
REFS = ("r6c", "r39", "r71b_v294")
REF_BUILD = {"r6c": "V282", "r39": "V282", "r71b_v294": "V294", TAG79: "V298"}
SYM_BANDS = (("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-20", 10.0, 20.0), (">20", 20.0, 99.0))
CP_BANDS = (("<5", 0.0, 5.0), ("5-8", 5.0, 8.0), ("8-10", 8.0, 10.0), ("10-12.5", 10.0, 12.5),
            ("12.5-15", 12.5, 15.0), ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))

# the fork's limiter constants (opendbc honda/values.py CarControllerParams + lateral.py), read from source @2712e1336
ANGLE_ERROR_MAX_BP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
ANGLE_ERROR_MAX_V = np.array([17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
MAX_ANGLE_RATE = 1.2           # deg/frame
OVR_ON, OVR_OFF, OVR_LEAD = 600.0, 500.0, 0.06
MAX_LAT_JERK = 3.0 + 9.81 * 0.06       # 3.589 m/s^3 (lateral.py MAX_LATERAL_JERK)
MAX_LAT_ACCEL = 3.0 + 9.81 * 0.06      # 3.589 m/s^2 (ISO 3.0 + g * AVERAGE_ROAD_ROLL)


def runs(mask, minlen=1):
    d = np.diff(np.r_[0, np.asarray(mask, np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    k = (b - a) >= minlen
    return np.c_[a[k], b[k]]


def zoh(t_src, x_src, t_dst, fill=np.nan):
    j = np.searchsorted(t_src, t_dst, side="right") - 1
    x = np.asarray(x_src)
    out = x[np.clip(j, 0, max(len(x) - 1, 0))].astype(float)
    out[j < 0] = fill
    return out


def _c20():
    with contextlib.redirect_stdout(io.StringIO()):
        import creep20_loop_id as C20
    return C20


def build_grid(tag, force=False):
    """-> dict of 100 Hz arrays on the drive-read's grid.  Cached to OUT/grid_<tag>.npz."""
    p = OUT / ("grid_%s.npz" % tag)
    if p.exists() and not force:
        return dict(np.load(p))
    g = _c20().load(tag)
    t = g["t"]
    G = dict(t=t, theta=g["ang"], wire=g["wire"], bar=g["bar"], sca=(g["sca"] > 0.5), req=g["req"],
             raw=np.round(g["cmd"]), vego=g["vego"], have=g["have18"].astype(bool), T_t=g["T_t"], T=g["T"])
    G["eng"] = G["req"] & G["sca"] & G["have"]
    G["w18"] = -G["wire"] / 8.0
    G["theta_sp"] = -G["raw"] / 10.0
    G["err"] = G["theta_sp"] - G["theta"]
    G["tap"] = zoh(G["T_t"], G["T"] / 8.0, t)
    # raw 0x14A field on its own native axis (no interpolation) for quantisation work
    D = np.load(CACHE / (tag + ".npz"))
    G["t14"], G["ang14"] = D["t14"], D["ang"]
    G["te4"], G["cmd_e4"], G["req_e4"] = D["te4"], D["cmd"], D["req"]
    if "cs_press" in D.files:
        G["pressed"] = zoh(D["tcs"], D["cs_press"], t)
    bp = CACHE / (tag + "_b4.npz")
    if bp.exists():
        B = np.load(bp)
        G["b4"] = zoh(B["t14b"], B["b4"], t)
    if tag == TAG79 and EXTRAS.exists():
        E = np.load(EXTRAS)
        st = np.round(np.interp(t, E["t18"], E["st18"]))       # the drive-read's own read of STEER_STATUS
        G["status"] = (st.astype(int) >> 4).astype(float)
        G["st18_byte"] = zoh(E["t18"], E["st18"], t)
    np.savez(p, **G)
    return G


def fork_cache():
    return dict(np.load(CACHE / "r79_fork.npz"))


# ---------------------------------------------------------------------------------------------------------------------
# the fork's VehicleModel (opendbc vehicle_model.py) at CarParams values -- the carcontroller builds VehicleModel(CP),
# so its sR is CP.steerRatio (16.33), not liveParameters' 16.84 (EVIDENCE: honda/carcontroller.py __init__ self.VM).
# ---------------------------------------------------------------------------------------------------------------------
def vm_from_cp(cpj):
    m, l, aF = cpj["mass"], cpj["wheelbase"], cpj["centerToFront"]
    aR = l - aF
    cF, cR = cpj["tireStiffnessFront"], cpj["tireStiffnessRear"]
    sf = m * (cF * aF - cR * aR) / (l ** 2 * cF * cR)
    sR = cpj["steerRatio"]

    def steer_from_curv(curv, u):            # rad
        cfac = 1.0 / (1.0 - sf * u ** 2) / l
        return curv * sR / cfac
    return steer_from_curv, dict(sf=sf, sR=sR, l=l)


def limiter_reconstruct(F):
    """Re-run the fork's _update_angle limiter VECTORISED on the fork's own frame axis (carOutput row i pairs with
    carState row i -- same card loop -- and the latest carControl before it).  apply_angle_last is the PUBLISHED
    co_ang[i-1] (not recursive), so every stage is a closed form per frame.  Returns per-frame arrays on t_co."""
    cpj = json.loads(str(F["carparams_json"]))
    steer_from_curv, vm = vm_from_cp(cpj)
    t = F["t_co"]
    n = len(t)
    # ... and on the carControl BEFORE the latest one (EVIDENCE: co_ang == cc_ang[jc-1] on 78.9 % of latActive
    # frames vs 51.9 % for cc_ang[jc] and 52.4 % for [jc-2], where jc = the latest t_cc <= t_co)
    jc = np.clip(np.searchsorted(F["t_cc"], t, side="right") - 2, 0, len(F["t_cc"]) - 1)
    lat = F["cc_latActive"][jc].astype(bool)
    des = F["cc_ang"][jc].astype(float)
    # carOutput row i is CREATED before carState row i in the same card loop (t_co[i] < t_cs[i]); the CarController
    # ran on the PREVIOUS carState (EVIDENCE: inactive co_ang == cs_ang[i-1] on 98.9 % of frames vs 79.8 % for [i])
    sh = lambda x: np.r_[x[:1], x[:-1]].astype(float)   # noqa: E731
    th = sh(F["cs_ang"])
    rate = sh(F["cs_rate"])
    tq = np.abs(sh(F["cs_tq"]))
    vraw = sh(F["cs_vegoraw"])
    v = np.maximum(vraw, 1.0)
    co = F["co_ang"].astype(float)
    # override hysteresis (on only while latActive): state = last crossing of ON (->1) or OFF (->0)
    ev = np.full(n, -1, np.int8)
    ev[tq > OVR_ON] = 1
    ev[tq <= OVR_OFF] = 0
    ev[~lat] = 0
    idx = np.where(ev >= 0, np.arange(n), -1)
    last = np.maximum.accumulate(idx)
    ovr = np.where(last >= 0, ev[np.maximum(last, 0)], 0).astype(bool)
    ovr_prev = np.r_[False, ovr[:-1]]
    released = ovr_prev & ~ovr
    co_prev = np.r_[th[0], co[:-1]]
    alast = np.where(released, th, co_prev)
    dmax_jerk = np.degrees(steer_from_curv(MAX_LAT_JERK / v ** 2, v)) * DT
    dmax = np.minimum(dmax_jerk, MAX_ANGLE_RATE)
    r1 = np.clip(des, alast - dmax, alast + dmax)
    amax = np.degrees(steer_from_curv(MAX_LAT_ACCEL / v ** 2, v))
    r2 = np.clip(r1, -amax, amax)
    r3 = np.where(ovr, th + rate * OVR_LEAD, r2)
    emax = np.interp(vraw, ANGLE_ERROR_MAX_BP, ANGLE_ERROR_MAX_V)
    r4 = np.clip(r3, th - emax, th + emax)
    r4 = np.clip(r4, -400, 400)
    rec = np.where(lat, r4, th)
    tol = 1e-3
    st = np.zeros(n, np.int8)            # 0 free, 1 rate/jerk-limited, 2 accel clip, 3 override O1, 4 error clip
    st[lat & (np.abs(r1 - des) > tol)] = 1
    st[lat & (np.abs(r2 - r1) > tol)] = 2
    st[lat & ovr] = 3
    st[lat & (np.abs(r4 - r3) > tol)] = 4
    return dict(t=t, lat=lat, des=des, co=co, rec=rec, res=co - rec, ovr=ovr & lat, released=released & lat,
                stage=st, dmax=dmax, dmax_jerk=dmax_jerk, emax=emax, amax=amax, th=th, rate=rate, tq=tq, v=v, vm=vm)


STAGE_NAMES = {0: "free", 1: "rate/jerk", 2: "accel-clip", 3: "override-O1", 4: "error-clip"}


def timer():
    t0 = time.time()
    return lambda: time.time() - t0
