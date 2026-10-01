# -*- coding: utf-8 -*-
"""d3_portcheck -- spot check of the DESIGNER's VecPort (fc_lib) under r2alt (KiHigh 0.8) against the REAL controller,
in closed loop on r71b chunks (the harness's real_fork mode: the REAL LatControlTorque drives the loop, the port shadows it
on the same inputs with its own state never re-synchronised, so any mismatch accumulates)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import d2_engine as E
import v295_harness as H
import fc_lib as FL

d = H.route()
chunks = H.route_chunks()
vm = [float(np.mean(d["v"][a:b])) for a, b in chunks]
order = np.argsort(vm)
pick = [chunks[i] for i in (order[2], order[len(order) // 2], order[-3], order[-1])]
print("chunks (mean v):", [(c, round(float(np.mean(d["v"][c[0]:c[1]])), 1)) for c in pick])
fam = H.family()
tg0 = d["toggles"]
for kih in (0.8, 0.0):
    rows = [FL.Fork("x", ki_high=kih)] * (2 * len(pick))
    H.ForkPort = lambda B, tg: FL.VecPort(B, tg0, rows)  # noqa: E731
    d["toggles"] = dict(tg0, accord_torque_ki_high=kih)       # the REAL controllers are built from this
    try:
        R = H.simulate([E.CELLS["V295"]], [fam["nominal"], fam["light_b"]], pick,
                       H.SimOpts(mode="B", dist="lp", real_fork=True, null_shadow=False))
    finally:
        H.ForkPort = FL._OrigPort
        d["toggles"] = tg0
    print("KiHigh %.1f: port-vs-real max |dev| per lane over (torque,p,i,f,la_des,la_act,output):" % kih,
          np.array2string(R["port_vs_real_maxdev"], precision=3))
