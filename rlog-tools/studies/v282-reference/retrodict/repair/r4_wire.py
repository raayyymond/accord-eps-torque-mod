# -*- coding: utf-8 -*-
"""r4 -- VERIFY THE CRUX ON THE WIRE: did the SteerFriction relay actually run, per route?

The gate turns on ONE source reading: that r73's back-filled stock SteerFriction 0.2120 ran as a
live error relay because its commit (e8e62f0e1) has no `friction_hyst > 0` guard.  That is a
decision-bearing claim, so it is re-derived here from the LOGS, not from the source.

pid_log.f (cs_f) = LAF * ff_torque = LAF * (plant_ff + friction*clip(arg/0.30) + inner).
plant_ff and inner depend only on the DESIRED angle / its rate / the MEASURED rate; the relay is the
only term that depends on the ERROR.  So regress

    cs_f ~ b0 + b1*hold(angle_des,v) + b2*move(angle_des_rate,v) + b3*rate_meas + b4*clip(arg/0.30)

and read b4.  PREDICTION, written before running: b4 = LAF * SteerFriction_effective, i.e.
   r71 0.154   r72 0.000   r73 2.968   6d 0.000 (guard)   75 0.000 (guard)   76 0.000
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r2_stat as R  # noqa: E402
from r1_ident import grid, runs_of  # noqa: E402

EPS_G_BP = [5.0, 12.5, 18.5, 28.5]
EPS_G_V = [550.0, 271.0, 246.0, 167.0]
HOLD_SAT = (19.3, 546.0, 3.01)
FF_RATE_RC = 0.10
MOVE_LIM_BP, MOVE_LIM_V = [8.0, 10.0], [1.0, 1.4]
ROUTES = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000075--6c8687d5bd", "00000076--d0b7ea7e4d",
          "00000064--ce6b0b0ebb", "00000065--b9f78988bd"]


def fofilt(x, rc, dt=0.01):
    a = dt / (rc + dt)
    y = np.empty_like(x)
    acc = x[0]
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def main():
    C = R.read_controllers()
    print("route                  label                  n_s   LAF  fric_eff  pred b4 |   b4 measured "
          "[95% CI]      R^2     b1/-LAF")
    out = {}
    for rt in ROUTES:
        g = grid(rt)
        m = (g["lat_active"] > 0.5) & (g["spress"] < 0.5) & (g["vego"] >= 15.0)
        if m.sum() < 3000:
            continue
        v = g["vego"]
        c = -float(np.polyfit(g["sa_deg"][m], g["cs_la_act"][m], 1)[0])
        ang_des = -g["cs_la_des"] / max(c, 1e-6)
        rate_des = fofilt(np.gradient(ang_des, 0.01), FF_RATE_RC)
        sat = HOLD_SAT[0] + HOLD_SAT[1] * np.exp(-v / HOLD_SAT[2])
        kv = np.interp(v, R.HOLD_V_BP, R.HOLD_K_V)
        hold = kv * sat * np.tanh(np.clip(ang_des, -400, 400) / sat)
        G = np.interp(v, EPS_G_BP, EPS_G_V)
        lim = np.interp(v, MOVE_LIM_BP, MOVE_LIM_V)
        move = np.clip(0.5 * rate_des / G, -lim, lim)
        rmeas = fofilt(g["sr_deg"], 0.01)
        arg = g["cs_err"] + 0.22 * g["cs_la_jerk"]
        X4 = np.clip(arg / 0.30, -1.0, 1.0)
        X = np.column_stack([np.ones(m.sum()), hold[m], move[m], rmeas[m], X4[m]])
        y = g["cs_f"][m] if "cs_f" in g else None
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ b
        s2 = res @ res / (len(y) - X.shape[1])
        cov = s2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
        r2 = 1 - res.var() / y.var()
        p = C[rt]
        pred = p["laf"] * (p["fric_param"] if p["relay"] else 0.0)
        print(f"{rt:22s} {p['lbl'][:20]:22s} {m.sum()*0.01:5.0f} {p['laf']:5.1f} "
              f"{(p['fric_param'] if p['relay'] else 0.0):9.4f} {pred:8.3f} | "
              f"{b[4]:9.3f} [{b[4]-1.96*se[4]:7.3f},{b[4]+1.96*se[4]:7.3f}] {r2:7.3f} {-b[1]/p['laf']:8.3f}")
        out[rt] = dict(b4=float(b[4]), se4=float(se[4]), pred=float(pred), r2=float(r2),
                       b1=float(b[1]), laf=p["laf"])
        del g
    json.dump(out, open(HERE / "out" / "r4_wire.json", "w"), indent=1)


if __name__ == "__main__":
    main()
