"""Counterfactual (open-loop part only): on the T64/T64B matched-jerk events, replay the rev 6.4 setpoint chain with
AccordRefFilter 0.06 (flown, control), 0.03 and 0.0, and measure (a) model->setpoint event lag (s2 fixed_lag, 3 Hz LP) and
(b) the setpoint's 1.5-3.5 Hz content (rms of band-passed setpoint over the event window, relative to flown).
The closed-loop consequence (setpoint->achieved) is NOT predicted here -- open-loop dose predictors on this car were falsified."""
import sys, json, gc
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "s2_jerk"))
import v282cmp as V
from s2_common import load_all
from s2_extract import fixed_lag
from lagmod import simulate_setpoint
rows, _t = load_all(); del _t
SOS = signal.butter(4, [1.5, 3.5], btype="band", fs=100.0, output="sos")
out = {}
for rk in ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]:
    R = [r for r in rows if r["route"] == rk and r["vb"] >= 1]
    S = V.load(rk); t, v = S["t"], S["v"]
    ld = np.nan_to_num(S["lat_delay"], nan=0.2)
    D = np.load(V.CACHE / f"{rk}.npz"); curv = D["cs_des_curv"]; act = D["cs_active"] > 0.5; del D
    x = V.lowpass(np.nan_to_num(S["model"]), 3.0); del S
    V282 = rk.startswith("00000064") or rk.startswith("00000065") or "2bc842" in rk
    sims = {}
    for nm, fc, rc in (("flown64_rc.06", 4.0, 0.06), ("rc.03", 4.0, 0.03), ("rc0", 4.0, 0.0), ("V282chain", 1.2, 0.0)):
        sims[nm] = simulate_setpoint(curv, v, act, ld, fc, rc)
    res = {nm: dict(lag=[], hf=[]) for nm in sims}
    for r in R:
        k = r["k"]; i0, i1 = k - 100, k + 250
        for nm, sp in sims.items():
            spn = np.nan_to_num(sp)
            L, g, c = fixed_lag(x, V.lowpass(spn, 3.0), i0, i1)
            res[nm]["lag"].append(L)
            res[nm]["hf"].append(float(np.sqrt(np.mean(signal.sosfiltfilt(SOS, spn[i0 - 100:i1 + 100])[100:-100] ** 2))))
    summ = {nm: dict(n=len(d["lag"]), lag_med=float(np.median(d["lag"])) if d["lag"] else None,
                     hf_rel_to_flown64=float(np.median(np.array(d["hf"]) / np.maximum(np.array(res["flown64_rc.06"]["hf"]), 1e-9))) if d["hf"] else None)
            for nm, d in res.items()}
    out[rk] = summ
    print(rk, {nm: (s["n"], s["lag_med"], round(s["hf_rel_to_flown64"], 2) if s["hf_rel_to_flown64"] else None) for nm, s in summ.items()}, flush=True)
    del sims, curv, v, act, x; gc.collect()
json.dump(out, open(HERE / "s08_refoff_counterfactual.json", "w"), indent=1)
