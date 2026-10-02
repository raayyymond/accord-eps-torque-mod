# -*- coding: utf-8 -*-
r"""d2_common.py -- shared pieces for designer D2 (FORK-FIRST) of the V299 round (2026-10-02).

ANALYSIS ONLY.  Sends nothing, flashes nothing, edits no fork / firmware / golden-model file.

* the V298 image (sha256 177abf04...) read for the GB-P table, Kp, Kd, Ki, ICL, ramps   (EVIDENCE: bytes)
* G(v) = the cave's own walk (c1_lib.cave_G arithmetic, unsigned compares, sar 12)
* s(v) = the P stiffness on the wire, tap LSB per degree of error = 160 G/256 * 112/256 * 0.02003 (M1's measured
  tap LSB per S).  x8 = T per degree.  At the six knots it reproduces values.py's 52/64/33/25/47/96 T/deg.
* the fork's _update_angle limiter as a 100 Hz per-column function (vectorised over columns, recursive in time)
* the hands-off reaction-twist word (M3's fit, gp-0x4f60 = -0.69 a - 0.69 w - 163 tanh(w/2) - 61; BELIEF model)
"""
from __future__ import annotations

import glob
import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                   # .../studies/angle_loop
KIT = AL.parents[2]                                    # repo root
KIT_A = KIT / "analysis-2020accord"
CACHE = KIT_A / "_scratch" / "cache" / "v280"
OUT = KIT / "_scratch" / "v299_D2"
OUT.mkdir(parents=True, exist_ok=True)
FW = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord"
V298_SHA = "177abf04"

RAIL_T = 2461.0                                        # delivered lane rail, T (SCL 15360; EVIDENCE of record)
RAIL_TAP = RAIL_T / 8.0                                # 307.6 tap LSB
TAP_PER_S = 0.02003                                    # M1, measured tap LSB per lane S
SPD_PER_MPS = 3.6 * 64                                 # gp-0x6a5e counts per m/s


def v298_image():
    p = glob.glob(str(FW / "_v298_*_plain_image.bin"))
    assert len(p) == 1, p
    b = Path(p[0]).read_bytes()
    assert hashlib.sha256(b).hexdigest().startswith(V298_SHA), "V298 image sha mismatch"
    return b


def image_cells():
    b = v298_image()
    rows = [struct.unpack_from("<HHh", b, 0xC4C00 + 218 + 6 * i) for i in range(7)]
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]  # noqa: E731
    c = dict(rows=rows, kp=[u16(0xE5384 + 2 * i) for i in range(5)], kd=[u16(0xE5126 + 2 * i) for i in range(4)],
             ki=u16(0xC63E6), icl=u16(0xC61BA), dcl=u16(0xC61B6), ramp_in=u16(0xC63FC), ramp_out=u16(0xC63FA))
    assert rows[0] == (714, 1178, 1041) and rows[-1] == (65535, 2188, 0), rows
    assert set(c["kp"]) == {112} and set(c["kd"]) == {48} and c["ki"] == 40 and c["icl"] == 8192, c
    return c


CELLS = image_cells()
ROWS = CELLS["rows"]


def s32(x):
    x = np.asarray(x, np.int64)
    return ((x + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def G_walk(v_mps):
    """the cave's G walk on gp-0x6a5e = round(v * 230.4), vectorised; identical arithmetic to c1_lib.cave_G."""
    vc = np.round(np.asarray(v_mps, float) * SPD_PER_MPS).astype(np.int64) & 0xFFFF
    X = np.array([r[0] for r in ROWS], np.int64)
    Gk = np.array([r[1] for r in ROWS], np.int64)
    S = np.array([r[2] for r in ROWS], np.int64)
    i = np.clip(np.searchsorted(X, vc, side="left") - 1, 0, len(X) - 2)     # X[i] < v <= X[i+1]
    g = Gk[i] + (s32((vc - X[i]) * S[i]) >> 12)
    return np.where(vc <= X[0], Gk[0], g)


def s_tap_per_deg(v_mps):
    """P stiffness on the wire: tap LSB per degree of (theta_sp - theta) (EVIDENCE arithmetic x M1's tap/S)."""
    return 160.0 * G_walk(v_mps) / 256.0 * 112.0 / 256.0 * TAP_PER_S


# ---------------------------------------------------------------------------------------------------------------------
# the fork (opendbc honda values.py / carcontroller.py _update_angle @ Dom 2712e1336), CURRENT constants
# ---------------------------------------------------------------------------------------------------------------------
CUR = dict(cap=1.2, err_bp=(3.1, 8.0, 10.0, 11.75, 17.5, 26.9), err_v=(17.0, 15.5, 19.5, 17.0, 8.5, 4.5),
           on=600.0, off=500.0, hard=600.0, deb=0, lead_o1=0.06, take=0.0, acc=0.0)
MAX_LAT = 3.0 + 9.81 * 0.06                            # 3.589 (lateral.py MAX_LATERAL_JERK / MAX_LATERAL_ACCEL)


def fork_cp():
    F = np.load(CACHE / "r79_fork.npz")
    return json.loads(str(F["carparams_json"]))


def vm_steer_from_curv():
    cpj = fork_cp()
    m, l, aF = cpj["mass"], cpj["wheelbase"], cpj["centerToFront"]
    aR = l - aF
    cF, cR = cpj["tireStiffnessFront"], cpj["tireStiffnessRear"]
    sf = m * (cF * aF - cR * aR) / (l ** 2 * cF * cR)
    sR = cpj["steerRatio"]

    def f(curv, u):                                    # rad (opendbc vehicle_model get_steer_from_curvature, roll 0)
        return curv * sR * l * (1.0 - sf * u ** 2)     # = curv * sR / (1/(1 - sf u^2)/l)
    return f


STEER_FROM_CURV = vm_steer_from_curv()


def vm_dmax_jerk(v):
    v = np.maximum(np.asarray(v, float), 1.0)
    return np.degrees(STEER_FROM_CURV(MAX_LAT / v ** 2, v)) * 0.01          # deg / frame


def vm_amax(v):
    v = np.maximum(np.asarray(v, float), 1.0)
    return np.degrees(STEER_FROM_CURV(MAX_LAT / v ** 2, v))


def reaction_word(alpha, omega):
    """M3's hands-off fit (route 79, settled, no press, n 58 585, R^2 0.31): gp-0x4f60 (+ = pushes left).
    Sign EVIDENCE; model BELIEF."""
    return -0.69 * alpha - 0.69 * omega - 163.0 * np.tanh(omega / 2.0) - 61.0


def load_st():
    """the panel-2 COMMON time scorer (CandLane / Plant / sensors), by path, unchanged."""
    name = "p2_st_d2"
    if name in sys.modules:
        return sys.modules[name]
    for p in (AL / "panel", AL / "c1", AL / "c3" / "rev2B"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    spec = importlib.util.spec_from_file_location(name, AL / "panel2" / "score_time.py")
    ST = importlib.util.module_from_spec(spec)
    sys.modules[name] = ST
    spec.loader.exec_module(ST)
    return ST


def v298_cand(ST):
    """V298 = C3B-P (Ki 40, GB-P read from the IMAGE, A3 + sgn 300, fresh D Kd 48) + the direction-2 ramps 328 / 66.
    The fadeB2 record is neutralised to fadeB in V298, and fadeA2 == fadeA in the image, so fade2=False is V298's fade."""
    return ST.Cand("V298", "D2", tuple(tuple(r) for r in ROWS), "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3,
                   sgn_thr=300, ramp_in=CELLS["ramp_in"], ramp_out=CELLS["ramp_out"], note="V298 flown")
