# -*- coding: utf-8 -*-
"""fvlc_lib.py -- shared loader/derivations for the FORCED vs LIMIT-CYCLE vs RESONANCE study
(subagent cyclekind, 2026-09-10).  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

Reuses the V282 census pipeline verbatim where it exists (C20.load, GI.demand_live, GI.line_of,
GI.envelope, GI.band, wire_0xe4_20hz.episodes_of) so every number is on the kit's own yardstick.
"""
import os
import pickle
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import wire_0xe4_20hz as W4                   # noqa: E402

FS = 100.0
IMG = {
    "V282":   LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V288":   LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V289":   LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V280r2": LG.FW + LG.IMAGES["V280r2"],
    "V278r3": LG.FW + LG.IMAGES["V278r3"],
}
BUILD = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r5e_v288": "V288",
         "r62_v289": "V289", "r63_v289": "V289", "r35": "V281r3",
         "r32": "V280r2", "r33": "V280r2", "r34": "V280r2", "r31": "V278r3"}
ROUTES = ("r31", "r32", "r33", "r34", "r35", "r39", "r3a", "r3c", "r5e_v288", "r62_v289", "r63_v289")
# per-build census band for the GRINDING line.  STATE correction #2: the 18-22 gate is BLIND to V289.
# V289's relocated grinding line sits at 16.2-16.9 Hz (STATE 2026-09-09 demand-gated median 16.47
# [15.81-16.91]); the LOW-demand road line sits at 12.4-13.8 Hz on EVERY build.  13-18 would straddle
# both, so V289's detection band starts at 15.0.
BAND = {b: ((15.0, 18.5) if b == "V289" else (18.0, 22.0)) for b in IMG}
# a neighbour band used as the EXCITATION yardstick: above the mode, clear of 2f0 and 3f0-alias.
#   V282 family f0 ~ 20.0 -> 2f0 = 40.1, 3f0 = 60.1 aliases to 39.9 : both land at ~40, so use 26-34.
#   V289        f0 ~ 16.3 -> 2f0 = 32.6, 3f0 = 48.9                 : use 36-46.
NEIGH = {b: ((36.0, 46.0) if b == "V289" else (26.0, 34.0)) for b in IMG}
_CELLS = {}


def cells(build):
    if build not in _CELLS:
        _CELLS[build] = GI.read_cells(IMG[build])
    return _CELLS[build]


def kp_of(c, idx):
    return np.interp(idx, c["kp_X"], c["kp_Y"])


def bp(x, lo, hi, fs=FS):
    return C20.bandpass(np.asarray(x, float), lo, hi, fs)


def env_of(x, lo, hi, fs=FS):
    return np.abs(signal.hilbert(bp(x, lo, hi, fs)))


def rms_win(x, n):
    """running rms over a centred window of n samples (uniform)."""
    x = np.asarray(x, float) ** 2
    k = np.ones(n) / n
    return np.sqrt(np.convolve(x, k, mode="same"))


def load(tag, force=False):
    cf = os.path.join(SCR, "fvlc_%s.pkl" % tag)
    if os.path.exists(cf) and not force:
        with open(cf, "rb") as fh:
            return pickle.load(fh)
    b = BUILD[tag]
    c = cells(b)
    g = W4.load_route(tag, c)                        # C20.load + raw 0xE4 + demand_live idx
    g["build"] = b
    g["kp"] = kp_of(c, g["idx"])
    lo, hi = BAND[b]
    nlo, nhi = NEIGH[b]
    for ch, src in (("bar", g["bar"]), ("rate", -g["wire"] / V.CPD), ("ang", g["ang"])):
        g["env_" + ch] = env_of(src, lo, hi)
        g["nen_" + ch] = env_of(src, nlo, nhi)
        g["lfe_" + ch] = env_of(src, 2.0, 6.0)
    g["slew"] = rms_win(np.r_[0.0, np.diff(g["cmd"])], 50)
    eps, hot = W4.episodes_of(g)
    g["eps"], g["hot"] = eps, hot
    keep = {k: v for k, v in g.items() if k not in ("e4",)}
    keep["e4_cmd"] = g["e4"]["cmd"]; keep["e4_t"] = g["e4"]["t"]; keep["e4_eng"] = g["e4"]["eng"]
    with open(cf, "wb") as fh:
        pickle.dump(keep, fh, protocol=4)
    return keep


def boot_ci(x, fn=np.median, n=4000, seed=0, lo=2.5, hi=97.5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = np.array([fn(x[rng.integers(0, len(x), len(x))]) for _ in range(n)])
    return float(fn(x)), float(np.percentile(b, lo)), float(np.percentile(b, hi))
