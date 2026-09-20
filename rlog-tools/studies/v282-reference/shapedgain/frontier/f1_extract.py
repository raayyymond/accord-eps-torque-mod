# -*- coding: utf-8 -*-
"""f1 -- per-window FFTs of everything the frontier needs, ONE ROUTE AT A TIME (RAM).

Window set = the GOAL METRIC's own population: laterally engaged, hands off, >= 15 m/s,
contiguous runs >= 30 s, unsaturated.  nperseg 1024 (10.24 s), hop 512, Hann, detrended.

Stored per window (complex spectra on one rfft grid) :
    X   model desired lateral accel   (cs_des_curv * v^2)   -- the GOAL's reference
    Y   achieved lateral accel        (livePose yaw * v)    -- the GOAL's output
    Z   the controller's shaped setpoint (cs_la_des)
    M   the controller's own measurement (cs_la_act = static angle map)
    UFB -(p+i)/LAF   the feedback part of the command
    UFF -f/LAF       the feedforward part
    U   out          the command
plus each window's median speed and the route's measured LAF.

EVIDENCE: everything here is a logged signal; nothing is modelled.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import v282cmp as V           # noqa: E402
import lp_lib as LP           # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
NPS, HOP = 1024, 512
VMIN = 15.0
RUN_S = 30.0


def do_route(route):
    S = V.load(route)
    laf_frame = np.where(np.abs(S["out"]) > 5e-3, -(S["p"] + S["i"] + S["f"]) / S["out"], np.nan)
    act = S["active"]
    laf = float(np.nanmedian(laf_frame[act]))
    m = (S["active"] & ~S["pressed"] & (S["v"] >= VMIN)
         & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"]) & np.isfinite(S["la_pose"])
         & np.isfinite(S["model"]) & np.isfinite(S["out"]))
    sig = dict(X=np.nan_to_num(S["model"]), Y=np.nan_to_num(S["la_pose"]),
               Z=np.nan_to_num(S["setpoint"]), M=np.nan_to_num(S["la_act"]),
               UFB=-(np.nan_to_num(S["p"]) + np.nan_to_num(S["i"])) / laf,
               UFF=-np.nan_to_num(S["f"]) / laf, U=np.nan_to_num(S["out"]),
               SR=np.nan_to_num(S["sr"]))
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / V.FS)
    cols = {k: [] for k in sig}
    vmed, secs = [], 0.0
    for a, b in V.runs(m, S["t"], min_s=RUN_S):
        secs += (S["t"][b - 1] - S["t"][a])
        for s in range(a, b - NPS + 1, HOP):
            e = s + NPS
            if float(np.mean(S["sat"][s:e])) > 0.02:
                continue
            vv = S["v"][s:e]
            if not np.isfinite(vv).all():
                continue
            for k, arr in sig.items():
                cols[k].append(np.fft.rfft(signal.detrend(arr[s:e]) * w))
            vmed.append(float(np.median(vv)))
    n = len(vmed)
    print(f"{route:24s} {LP.GROUPS[route]:8s} laf {laf:6.3f}  runs_sec {secs:7.1f}  windows {n}")
    if n:
        np.savez_compressed(OUT / f"f1_{route}.npz", f=f, vmed=np.array(vmed), laf=laf,
                            **{k: np.array(v) for k, v in cols.items()})
    del S, sig, cols
    return dict(route=route, group=LP.GROUPS[route], laf=laf, sec=secs, nwin=n)


if __name__ == "__main__":
    meta = {}
    for route in LP.GROUPS:
        if not (V.CACHE / f"{route}.npz").exists():
            continue
        meta[route] = do_route(route)
    json.dump(meta, open(OUT / "f1_meta.json", "w"), indent=1)
