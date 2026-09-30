# -*- coding: utf-8 -*-
"""h3b_port_gate.py -- gate H3b: the vectorised ForkPort == the REAL LatControlTorque (<= 1e-9 on p, i, f, output),
(1) on the whole r71b replay (the exact inputs h3_fork_replay.py fed the real code; its outputs are in _scratch), and
(2) on CLOSED-LOOP trajectories: the real controller drives the harness plant + lane, the port shadows it on the same
inputs with its own state never re-synchronised, so any deviation accumulates.  Run h3_fork_replay.py first."""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402


def main():
    z = dict(np.load(os.path.join(HERE, "_scratch", "h3_replay.npz")))
    d = H.route()
    tg = d["toggles"]
    import fork_real as FK
    port = H.ForkPort(1, tg)
    real = FK.RealController(tg)          # re-run the real code here so its FLOAT64 internals can be compared (the
    #                                       torqueState fields h3 saved are capnp Float32 read-backs)
    n = len(z["in_t"])
    keys = ("p", "i", "f", "torque", "la_des", "la_act")
    out = {k: np.zeros(n) for k in keys}
    ref = {k: np.zeros(n) for k in keys}
    act = np.zeros(n, bool)
    lim = False
    t0 = time.time()
    L = real.LaC
    for k in range(n):
        a = (bool(z["in_active"][k]), float(z["in_v"][k]), float(z["in_ang"][k]), bool(z["in_pressed"][k]),
             float(z["in_off"][k]), float(z["in_roll"][k]), float(z["in_des_curv"][k]), float(z["in_delay"][k]),
             float(z["in_laf_off"][k]))
        rr = real.step(a[0], a[1], a[2], 0.0, a[3], a[4], a[5], a[6], a[7], a[8], lim)
        r = port.step(np.array([a[0]]), a[1], a[2], np.array([a[3]]), a[4], a[5], a[6], a[7], a[8], np.array([lim]))
        for kk in keys:
            out[kk][k] = r[kk][0]
        ref["p"][k], ref["i"][k], ref["f"][k] = L.pid.p, L.pid.i, L.pid.f
        ref["torque"][k] = rr["torque"]
        ref["la_des"][k] = L.prev_desired_lateral_accel
        ref["la_act"][k] = L.previous_measurement
        act[k] = a[0]
        if z["in_sd_active"][k]:
            lim = abs(z["in_cc_torque"][k] - z["in_co_torque_latest"][k]) > 1e-2
    dtr = time.time() - t0
    worst = 0.0
    print("H3b PORT GATE  (%d frames, real + port %.1f s); real = LatControlTorque's float64 internals" % (n, dtr))
    for kk in keys:
        m = act if kk in ("la_des",) else np.ones(n, bool)
        e = float(np.max(np.abs(out[kk][m] - ref[kk][m])))
        ex = float(np.mean(out[kk][m] == ref[kk][m]))
        worst = max(worst, e)
        print("  replay   %-7s max |port - real| %.3g   bit-identical frames %.6f" % (kk, e, ex))
    e_saved = float(np.max(np.abs(ref["torque"] - z["torque"])))
    print("  (this re-run of the real code vs h3's saved run: max |d torque| %.3g)" % e_saved)
    # closed loop, real controller in the loop, port shadowing
    fam = H.family()
    ch = H.route_chunks(max_s=20.0)
    pick = [ch[i] for i in np.linspace(0, len(ch) - 1, 4).astype(int)]
    o = H.SimOpts(mode="B", real_fork=True)
    t0 = time.time()
    R = H.simulate([H.Cells.v294()], [fam["nominal"], fam["light_b"]], pick, o)
    print("  closed loop: %d lanes x %.0f s, real fork driving (%.1f s): max |port - real| per lane %s"
          % (len(R["lens"]), R["lens"].max() / 100.0, time.time() - t0,
             ", ".join("%.2g" % v for v in R["port_vs_real_maxdev"])))
    worst = max(worst, float(np.max(R["port_vs_real_maxdev"])))
    g = worst <= 1e-9
    print("H3b %s (worst %.3g)" % ("PASS" if g else "FAIL", worst))


if __name__ == "__main__":
    main()
