"""Run the ORCHESTRATOR'S estimator (orch_crux.py section 4: xcorr of 1-6 Hz band-passed sent 0xE4 vs d(rate)/dt on the
100 Hz carState grid, 10 ms lags, runs >30 s, v>3) on the synthetic plant with KNOWN D, and on the real route; plus a
relaxed-dwell eq-error config on the same synthetic cases (does more data keep the control passing?)."""
import sys, os, math, json
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E, synth
route = sys.argv[1]
Z = np.load(f"{synth.CACHE}/{route}.npz")
t_u = Z["t_e4"]; e4 = Z["e4_cmd"]; u = -e4 / 4089.0
t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
mask = act & ~press
real_rate = Z["sr_deg"]; del Z
rr = E.runs(mask, t_cs); t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
sos = signal.butter(4, [1.0, 6.0], btype="band", fs=100.0, output="sos")

def orch_xcorr(rate, cmd_on_cs):
    acc = np.gradient(rate) * 100.0   # V.deriv assumed central difference
    num = {}; cnt = 0
    for a, b in E.runs(mask & (v > 3.0), t_cs, min_s=30.0):
        c = signal.sosfiltfilt(sos, cmd_on_cs[a:b]); y = signal.sosfiltfilt(sos, acc[a:b])
        for L in range(-5, 26):
            ca, ya = (c[:len(c) - L], y[L:]) if L >= 0 else (c[-L:], y[:len(y) + L])
            num[L] = num.get(L, 0.0) + float(np.dot(ca, ya)) / math.sqrt(float(np.dot(ca, ca) * np.dot(ya, ya)) + 1e-12)
        cnt += 1
    Ls = sorted(num); vals = np.array([num[L] / cnt for L in Ls]); ib = int(np.argmax(np.abs(vals))); ineg = int(np.argmin(vals))
    return Ls[ib] * 10, float(vals[ib]), Ls[ineg] * 10, float(vals[ineg])

res = {}
# orchestrator interpolates e4 (sendcan) onto the controlsState clock; here onto carState clock (same 100 Hz cadence)
cmd_cs = np.interp(t_cs, t_u, e4)
res["real"] = orch_xcorr(real_rate, cmd_cs)
print("real xcorr", res["real"], flush=True)
relaxed = dict(variant="rate", band=(None, 4.0), guard=2, demean_block=True, rmin=1.0)
for D in (0.030, 0.060):
    for J in (8e-5, 3e-4, 1e-3):
        for tau in (0.0,):
            a, r, us = synth.simulate(t_u, u, t_cs, v, D, J, 0.003, 0.02, t0=t0, t1=t1, tau=tau)
            ok = np.isfinite(a); a = np.nan_to_num(a); r = np.nan_to_num(r)
            xc = orch_xcorr(r, np.interp(t_cs, t_u, -us * 4089.0))
            bl, _ = E.accumulate(t_cs, a, r, v, mask & ok, t_u, us, **relaxed)
            ds = [round(E.argmin_sub(E.solve([x for x in bl if x["bin"] == bi])[0])[0], 1) for bi in range(3)]
            key = f"D{D*1e3:.0f}_J{J:g}_tau{tau*1e3:.0f}"
            res[key] = dict(orch_xcorr=xc, eqerr_relaxed=ds)
            print(key, res[key], flush=True)
json.dump(res, open(f"xcorr_on_control2_{route}.json", "w"), indent=1)
