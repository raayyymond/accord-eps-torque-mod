"""EXP D: ENGAGE UNDER LOAD -- the driver holds a curve (theta0, the spring loaded by k*theta0), the lane engages
(request 1, ramp +33/tick from 0 -> full in 0.99 s, the PID runs from the first tick under A2), the fork sends the
measured angle at the engage frame and then HOLDS it (spec C3/C5 as the design assumes), and the driver lets go over
0.2 s, t_lag after the engage edge.  The design states the engage init (I = 0, E_prev reset, ramp-in) but never
simulates a hand-over under load.  Reports the droop (deg the wheel falls toward centre below theta_sp), the overshoot
past theta_sp, slips (stuck >= 100 ms then >= 0.1 deg), and the peak T."""
import sys, json, time
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
CASES = {3.0: 45.0, 5.0: 25.0, 8.0: 15.0, 12.5: 6.0, 19.0: 2.5, 26.0: 1.5}
LAGS = (0.0, 0.3, 1.0)
TE = 2.0
DUR = TE + 6.0
def hand(th0, lag):
    def h(t):
        if t < TE + lag:
            return (2000.0, 30.0, th0)
        frac = min(1.0, (t - TE - lag) / 0.2)
        if frac >= 1.0:
            return None
        return (2000.0 * (1 - frac), 30.0 * (1 - frac), th0)
    return h
cols = []
for v, th0 in CASES.items():
    for lag in LAGS:
        cols.append(dict(member="nominal", v=v, th0=th0, lag=lag, ref=lambda t: 0.0, hand=hand(th0, lag),
                         mode=lambda t: "off" if t < TE else "engage_ramp",
                         sp_src=lambda t: "meas" if t < TE + 0.011 else "hold"))
t0 = time.time()
rec = F.run(cols, DUR, rec_I=True)
tt = np.arange(rec["th"].shape[0]) * 1e-3
w = tt >= TE
res = []
print("[%.0f s]" % (time.time() - t0))
print("  v  theta0 lag | sp at engage | droop deg (t)  | overshoot deg | slips | peak|T| | I at 1 s (T) | |th-sp| at TE+4 s")
for j, c in enumerate(cols):
    th = rec["th"][:, j].astype(float); sp = rec["sp"][:, j].astype(float); T = rec["T"][:, j].astype(float)
    I = rec["I"][:, j].astype(float)
    spE = sp[int((TE + 0.05) * 1000)]
    e = (sp - th)[w] * np.sign(c["th0"])
    k = np.argmax(e)
    droop = e.max()
    ovs = (-e).max()
    sl = F.slips(rec, TE, DUR)[j]
    Ik = I[int((TE + 1.0) * 1000)] * 5346 / 32768.0
    res.append(dict(v=c["v"], th0=c["th0"], lag=c["lag"], droop=float(droop), t_droop=float(k * 1e-3), overshoot=float(ovs), slips=int(sl), peakT=float(np.abs(T[w]).max()), e_end=float(abs(e[-1]))))
    print("%5.1f %5.1f %4.1f | %6.2f | %6.2f (%4.2f s) | %6.2f | %3d | %5.0f | %5.0f | %5.2f" % (c["v"], c["th0"], c["lag"], spE, droop, k * 1e-3, ovs, sl, np.abs(T[w]).max(), Ik, abs(e[-1])))
(OUT / "expD.json").write_text(json.dumps(res))
