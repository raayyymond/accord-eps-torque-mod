# -*- coding: utf-8 -*-
"""m6_common.py -- M6 goal scoring: a VECTORISED wire loader on the v280 cache (no rlog read, no per-sample loop).

Builds the same W fields as angle_loop_drive_read.make_wire/derive (theta, theta_sp, ew, w18, eng, handsoff,
pressed, T100) but with the per-sample integral loop replaced by np.cumsum.  Frame axis = creep20_loop_id.load
(the 0x18F frame grid, dejittered) -- imported unchanged so the axis is identical to the drive read's.
ANALYSIS ONLY.  Reads the cache; writes nothing.
"""
from __future__ import annotations
import contextlib, io, os, sys
from pathlib import Path
import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
REPO = _d.parent if (_d.parent / "rlog-tools").exists() else _d
for _p in [REPO / "rlog-tools" / "studies" / "grind", REPO / "rlog-tools" / "studies" / "angle_loop",
           REPO / "rlog-tools", REPO / "rlog-tools" / "lib", REPO / "analysis-2020accord",
           REPO / "analysis-2020accord" / "lib", REPO / "analysis-2020accord" / "studies" / "angle_loop",
           REPO / "analysis-2020accord" / "studies" / "angle_loop" / "refute_c2r2_nonlinear"]:
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

CACHE = REPO / "analysis-2020accord" / "_scratch" / "cache" / "v280"
FS = 100.0
HANDSOFF_BAR = 500.0          # drive-read THR handsoff_bar


def _zoh(t_src, x_src, t_dst):
    j = np.searchsorted(t_src, t_dst, side="right") - 1
    out = np.asarray(x_src, float)[np.clip(j, 0, max(len(x_src) - 1, 0))].copy()
    out[j < 0] = np.nan
    return out


def runs(mask, minlen):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def load(tag):
    with contextlib.redirect_stdout(io.StringIO()):
        import creep20_loop_id as C20
    g = C20.load(tag)
    D = np.load(CACHE / (tag + ".npz"))
    t = g["t"]
    W = dict(tag=tag, t=t, ang=g["ang"], raw=np.round(g["cmd"]), req=np.asarray(g["req"]) > 0.5,
             sca=np.asarray(g["sca"]) > 0.5, bar=g["bar"], wire=g["wire"], vego=g["vego"],
             T_t=g["T_t"], T=g["T"], have=np.asarray(g["have18"], bool))
    W["pressed"] = _zoh(D["tcs"], D["cs_press"], t) if "cs_press" in D.files else np.full(len(t), np.nan)
    W["eng"] = W["req"] & W["sca"] & W["have"]
    W["theta"] = W["ang"]
    W["theta_sp"] = -W["raw"] / 10.0
    W["f14a"] = -10.0 * W["ang"]
    W["ew"] = W["raw"] - W["f14a"]
    W["w18"] = -W["wire"] / 8.0
    W["handsoff"] = np.abs(W["bar"]) < HANDSOFF_BAR
    W["T100"] = _zoh(W["T_t"], W["T"] / 8.0, t)
    # hands-off for the goal = not steeringPressed where carState has it (drive-read _goal_runs), else |bar| < 500
    W["free"] = ~(np.nan_to_num(W["pressed"]) > 0.5) if np.isfinite(W["pressed"]).any() else W["handsoff"]
    return W


def load_fork():
    return dict(np.load(CACHE / "r79_fork.npz", allow_pickle=True))
