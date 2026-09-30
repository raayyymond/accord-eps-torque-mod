# -*- coding: utf-8 -*-
"""rj21_curves.py -- lens robust-joint: before/after CURVE DATA for the orchestrator's artifact (no plotting here):
trim T/omega (magnitude, phase) 0.1-50 Hz; |P/x| 0.1-50 Hz; the delivered static surface T(wire) (golden-model march,
cold boot) at 0..3900 wire; closed-form alpha/cmd (inner loop closed) on nominal and light_b at 5/12/26.9 m/s; the inner
return ratio |L| on nominal/light_b at 12 m/s; the outer-loop GM by member x speed.  V294 vs the pick, same code.
Writes rj21_curves.json.  ANALYSIS ONLY."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rj_lin as RL, rj_cands as RC
from rj_lin import H
base = RC.base(); pick = base.replace(fb_b=1106, name="pick")
f = np.logspace(-1, np.log10(50), 200)
out = dict(f=f.tolist())
ctx = RL.Ctx()
for nm, c in (("V294", base), ("pick", pick)):
    Tw = H.trim_T_per_omega(c, f)
    out[nm] = dict(Tw_mag=np.abs(Tw).tolist(), Tw_ph=np.degrees(np.angle(Tw)).tolist(),
                   Px=np.abs(H.lane_ctf(c, f, kind="P")).tolist())
    idx = np.arange(0, 241, 4)
    S = H.surface(c, idx)
    out[nm]["surface_wire"] = (idx * H.WIRE_PER_IDX).tolist(); out[nm]["surface_T"] = [int(v) for v in S]
    lt = RL.LaneTF(c)
    F = RL.F_OUT
    for p in ("nominal", "light_b"):
        for v in (5.0, 12.0, 26.9):
            Lin = RL.inner_L(ctx, lt, p, v, "out", idx=30)
            A = ctx.s_out ** 2 * ctx.P_out[(p, v)] * lt.ff(F, 30) * ctx.zoh100 / (1 + Lin)
            out[nm]["alpha_cmd|%s|%g" % (p, v)] = dict(mag=np.abs(A).tolist(), ph=np.degrees(np.angle(A)).tolist())
            out[nm]["Lin|%s|%g" % (p, v)] = np.abs(Lin).tolist()
out["F_out"] = RL.F_OUT.tolist()
S0 = out["V294"]["surface_T"]; S1 = out["pick"]["surface_T"]
print("static surface identical V294 vs pick:", S0 == S1, " rail", max(S0), max(S1))
json.dump(out, open(os.path.join(HERE, "rj21_curves.json"), "w"))
print("saved rj21_curves.json")
