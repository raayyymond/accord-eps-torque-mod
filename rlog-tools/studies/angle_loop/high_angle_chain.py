# -*- coding: utf-8 -*-
"""high_angle_chain.py -- where is a 1-5 Hz setpoint oscillation BORN in the fork?  For each window: band (1-5 Hz) rms
of model action curvature (modelV2, 20 Hz) -> controlsState desired curvature -> carControl actuators curvature ->
carControl steeringAngleDeg (pre-limiter) -> carOutput angle (= 0xE4) -> wheel, each curvature scaled to wheel-angle
degrees by its own window regression on cc_ang (gain printed).  ANALYSIS ONLY (2026-10-15).
    python high_angle_chain.py <route> t0:t1 [...]"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()] + [Path(__file__).resolve().parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import contextlib, io
import angle_loop_drive_read as D
import drive_read_v299 as V
FS = 100.0
route = sys.argv[1]
with contextlib.redirect_stdout(io.StringIO()):
    W = D.load_route(route)
FK, fm, _ = V.fork_cache(W, D._fr())
t = W["t"]; t0 = t[0]
I = lambda tk, k: np.interp(t, FK[tk], FK[k].astype(float))
sig = dict(model=I("t_md", "md_act_curv"), dcurv=I("t_ctl", "ctl_dcurv"), meas=I("t_ctl", "ctl_curv"), act=I("t_cc", "cc_curv"),
           angdes=I("t_ctl", "ang_des"), cc=I("t_cc", "cc_ang"), co=I("t_co", "co_ang"), wheel=W["theta"])
bp = signal.butter(2, [1.0, 5.0], btype="band", fs=FS, output="sos")
for w in sys.argv[2:]:
    a, b = (float(x) for x in w.split(":"))
    S = np.flatnonzero((t - t0 >= a) & (t - t0 < b))
    pad = slice(max(S[0] - 300, 0), S[-1] + 300); off = S[0] - pad.start
    out = []
    for k, x in sig.items():
        y = x[S]
        g = 1.0
        if k in ("model", "dcurv", "meas", "act"):
            c = sig["cc"][S]
            g = np.dot(y - y.mean(), c - c.mean()) / max(np.dot(y - y.mean(), y - y.mean()), 1e-18)
        bb = signal.sosfiltfilt(bp, np.nan_to_num(x[pad]))[off:off + len(S)] * g
        out.append("%s %.2f%s" % (k, np.std(bb), (" (x%.0f)" % g) if g != 1.0 else ""))
    print("%s %6.1f-%6.1f  1-5 Hz rms (deg-equivalent): %s" % (route.split("_")[1][:12], a, b, "  ".join(out)))
