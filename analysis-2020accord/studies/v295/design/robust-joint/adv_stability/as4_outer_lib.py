# -*- coding: utf-8 -*-
"""as4_outer_lib.py -- the outer-loop return ratio of as4_outer.py as an importable function (same code, no scan)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v295_harness as H

VMc = H._vm_consts()
KP, KI, LAF, FR, THR = 0.9, 0.3, 14.0, float(np.float32(0.011)), 0.30
SR0 = 16.84
WIRE_PER_IDX = 2 ** 22 / (4 * 65025)


def ff_lane(c, f):
    zi = np.exp(-2j * np.pi * np.asarray(f) * 1e-3)
    slope = (c["mapY"][-1] - c["mapY"][0]) / (c["mapX"][-1] - c["mapX"][0])
    sp_w = slope / WIRE_PER_IDX
    S = (254 / 256.0) * (c["kpY"][0] / 256.0) * (2 ** c["sh"]) * sp_w
    y = (c["lb"] / 1024.0) * (1 + zi) / (32 * (1 - (c["la"] / 1024.0) * zi)) * S
    return y * c["gain"] / 32768.0


def outer_L(c, p, v, f, relay=1.0, pipe_ms=22.0, srg=1.0):
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    Lin = A.inner_L(c, p, f)
    zoh1k = np.exp(-1j * np.pi * f * 1e-3) * np.sinc(f * 1e-3)
    Pcl = A.plant_theta_per_u(p, f) * zoh1k / (1 + Lin)
    z100 = np.exp(s * 0.01)
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
    Cf = (KP + KI * 0.01 / (1 - 1 / z100) + relay * FR * LAF / THR) * (1 + lsf / KP)
    cf = (1 - VMc["chi"]) / (1 - VMc["sf"] * v ** 2) / VMc["l"]
    kla = cf * v ** 2 * np.pi / 180.0 / SR0 * srg
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    return kla * Cf * (4096.0 / LAF) * zoh100 * np.exp(-s * pipe_ms * 1e-3) * ff_lane(c, f) * Pcl
