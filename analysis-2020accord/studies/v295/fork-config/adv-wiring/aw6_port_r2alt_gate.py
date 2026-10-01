# -*- coding: utf-8 -*-
"""aw6_port_r2alt_gate.py -- ADV "wiring+observability", W2: did the DESIGN simulate the r2alt the fork will actually run?
The design's control (f1) proved VecPort == the harness ForkPort bit-for-bit for r1 rows only; the harness gate H3b proved
ForkPort == the real LatControlTorque for r1 only.  Nothing compared VecPort with KiHigh 0.8 against the REAL fork with
accord_torque_ki_high 0.8.  This does: the h3 replay inputs (r71b, pre-registered alignment) fed frame by frame to
  real = fork_real.RealController(r71b runtime toggles, accord_torque_ki_high = 0.8)       (the fork's own code)
  port = fc_lib.VecPort(1, toggles, [Fork('r2alt', kp 0.9, ki 0.3, ki_high 0.8)])         (what every design sim ran)
with neither state ever re-synchronised.  PASS = max |port - real| <= 1e-9 on p, i, f, torque (the H3b bar).
ANALYSIS ONLY.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
HARN = os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "fork-config"))
sys.path.insert(0, HARN)
import fc_lib as F  # noqa: E402

H = F.H
import fork_real as FK  # noqa: E402

z = dict(np.load(os.path.join(HARN, "_scratch", "h3_replay.npz")))
d = H.route()
tg = dict(d["toggles"])
out_lines = []
for label, kih in (("r1 (control)", 0.0), ("r2alt", 0.8)):
    tgr = dict(tg)
    tgr["accord_torque_ki_high"] = kih
    real = FK.RealController(tgr)
    port = F.VecPort(1, tg, [F.Fork(label, kp=0.9, ki=0.3, ki_high=kih)])
    L = real.LaC
    n = len(z["in_t"])
    dev = {k: 0.0 for k in ("p", "i", "f", "torque")}
    lim = False
    t0 = time.time()
    for k in range(n):
        a = (bool(z["in_active"][k]), float(z["in_v"][k]), float(z["in_ang"][k]), bool(z["in_pressed"][k]),
             float(z["in_off"][k]), float(z["in_roll"][k]), float(z["in_des_curv"][k]), float(z["in_delay"][k]),
             float(z["in_laf_off"][k]))
        rr = real.step(a[0], a[1], a[2], 0.0, a[3], a[4], a[5], a[6], a[7], a[8], lim)
        r = port.step(np.array([a[0]]), a[1], a[2], np.array([a[3]]), a[4], a[5], a[6], a[7], a[8], np.array([lim]))
        dev["p"] = max(dev["p"], abs(r["p"][0] - L.pid.p))
        dev["i"] = max(dev["i"], abs(r["i"][0] - L.pid.i))
        dev["f"] = max(dev["f"], abs(r["f"][0] - L.pid.f))
        dev["torque"] = max(dev["torque"], abs(r["torque"][0] - rr["torque"]))
        if z["in_sd_active"][k]:
            lim = abs(z["in_cc_torque"][k] - z["in_co_torque_latest"][k]) > 1e-2
    s = "%-13s %d frames (%.0f s): max |VecPort - real fork| p %.3g  i %.3g  f %.3g  torque %.3g  -> %s" % (
        label, n, time.time() - t0, dev["p"], dev["i"], dev["f"], dev["torque"],
        "PASS" if max(dev.values()) <= 1e-9 else "FAIL")
    print(s)
    out_lines.append(s)
open(os.path.join(HERE, "out", "aw6_port_r2alt_gate_out.txt"), "w", encoding="utf-8").write("\n".join(out_lines) + "\n")
