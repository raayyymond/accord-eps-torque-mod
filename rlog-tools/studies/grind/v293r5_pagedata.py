# -*- coding: utf-8 -*-
"""v293r5_pagedata.py -- numbers and traces for the rev-5 Artifact page (orchestrator's own, 2026-09-15).
argv: [rc]  the rate-measurement RC the shipping fork uses (default 0.03).  Writes _scratch/v293r5_pagedata.json."""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3
import v293r5_design as D
import v293r5_design_pred as P
import v293r5_design_jerk as J
import v293r5_loopshape as LS

RC = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
DT = S.DT
out = {"rc": RC}

# (a) Q(f) of the observer, two identical poles
f = np.logspace(math.log10(0.05), 1.0, 120)
def Q(fq):
    s = 1j * 2 * math.pi * f
    q = (1.0 / (1 + s / (2 * math.pi * fq))) ** 2
    return {"f": f.round(4).tolist(), "mag": np.abs(q).round(4).tolist(), "phase_deg": np.degrees(np.angle(q)).round(1).tolist(),
            "re": np.real(q).round(4).tolist()}
out["Q"] = {"0.6": Q(0.6), "0.8": Q(0.8)}

# (b) damping budget vs frequency (torque per deg/s) at 12 and 26 m/s, lightly damped world
def rl_damp(kv, rc, v, td=0.06):
    w = 2 * math.pi * f
    taper = min(1.0, 12.0 / v)
    return kv * taper * np.cos(w * td + np.arctan(w * rc))
out["damping"] = {}
for v in (6.0, 12.0, 26.0):
    db = D.b_ident(v) - 0.0006
    q6 = np.real((1.0 / (1 + 1j * f / 0.6)) ** 2); q8 = np.real((1.0 / (1 + 1j * f / 0.8)) ** 2)
    out["damping"][str(int(v))] = {
        "f": f.round(4).tolist(), "plant_b_mode": 0.0006, "plant_b_ident": D.b_ident(v),
        "rl_r4": rl_damp(0.0006, 0.03, v).round(6).tolist(), "rl_r5": rl_damp(0.001, RC, v).round(6).tolist(),
        "dob_0.6": (db * q6).round(6).tolist(), "dob_0.8": (db * q8).round(6).tolist(),
        "mode_hz_open": float(R3.mode_hz(v)),
    }

# (c) time traces, lightly damped world, R4 vs SHIP
world = P.WORLDS["mode (b .0006, J 1e-4)"]
R4 = D.mk("R4-flown"); SHIP = J.mk("SHIP", kp=1.0, kv=0.001, rc=RC, dob=0.6)
def traces(cfgf, v, curv_fn, T, Fscale=1.0, dist_fn=None):
    o = P.run(cfgf, v, curv_fn, T=T, world=world, need=1.0, Fscale=Fscale, dist_fn=dist_fn)
    k = slice(0, None, 2)   # 50 Hz for the page
    return {"t": o[k, 0].round(3).tolist(), "u": o[k, 1].round(4).tolist(), "meas": o[k, 3].round(4).tolist(),
            "rate": o[k, 5].round(2).tolist(), "dob": o[k, 10].round(4).tolist(), "i": o[k, 4].round(4).tolist()}
out["traces"] = {}
for v in (8.0, 19.0):
    la = 1.0
    step = lambda t, v=v, la=la: (la if t >= 1.0 else 0.0) / v ** 2
    des = [(la if t >= 1.0 else 0.0) for t in np.arange(0, 6.0, DT)[::2]]
    out["traces"]["step_%d" % int(v)] = {"des": des, "R4": traces(R4, v, step, 6.0), "R5": traces(SHIP, v, step, 6.0)}
    def prof(t, v=v):
        if t < 1.0: x = 0.0
        elif t < 2.5: x = 2.5 * (t - 1.0) / 1.5
        elif t < 5.0: x = 2.5
        elif t < 6.5: x = 2.5 * (6.5 - t) / 1.5
        else: x = 0.0
        return x / v ** 2
    out["traces"]["hard_%d" % int(v)] = {"des": [prof(t) * v ** 2 for t in np.arange(0, 9.0, DT)[::2]],
                                          "R4": traces(R4, v, prof, 9.0, Fscale=1.5), "R5": traces(SHIP, v, prof, 9.0, Fscale=1.5)}
    dist = lambda t: 0.03 if t >= 2.0 else 0.0
    out["traces"]["dist_%d" % int(v)] = {"R4": traces(R4, v, lambda t: 0.0, 8.0, dist_fn=dist), "R5": traces(SHIP, v, lambda t: 0.0, 8.0, dist_fn=dist)}

# (d) linear loop shape of the P/I(/notch) loop, both worlds' b, R4 vs R5 gains (the observer is not in this loop)
out["loopshape"] = {}
for v in (8.0, 12.0, 19.0, 26.0):
    row = {}
    for name, kp, ki, kv in (("R4", 0.85, D.ki_sched(v, 0.6, 2.5), 0.0006), ("R5", 1.0, 0.3, 0.001)):
        for bname, b in (("mode", 0.0006), ("ident", D.b_ident(v))):
            r = LS.loop(v, kp, ki, kv, 1.0, b, rl_rc=(0.03 if name == "R4" else RC))
            row["%s_%s" % (name, bname)] = {k: float(x) for k, x in r.items() if isinstance(x, (int, float, np.floating)) and not isinstance(x, bool)}
    out["loopshape"][str(int(v))] = row

def _default(o):
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, (np.floating, np.integer)): return float(o)
    raise TypeError(str(type(o)))
json.dump(out, open(os.path.join(HERE, "_scratch", "v293r5_pagedata.json"), "w"), separators=(",", ":"), default=_default)
print("written _scratch/v293r5_pagedata.json", len(json.dumps(out)) // 1024, "KB")
