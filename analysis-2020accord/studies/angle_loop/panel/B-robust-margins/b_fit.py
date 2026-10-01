# -*- coding: utf-8 -*-
"""b_fit.py (panel B-robust-margins) -- fit a minimal-knot G(v) table UNDER the full-factorial envelope by LP, so the
cave's integer walk stays >= MARGIN under env(v) at every 0.25 m/s grid point (the GATE-2 grid, incl. the plant knots).
ANALYSIS ONLY.  maximise the tracking-weighted interpolated G subject to G_interp(v) <= env(v)*MARGIN.
usage: python b_fit.py <env_json> <knot_v_csv> [margin]   -> prints knots [(v,G)...] and the resulting cave surface."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "c1"))
import c1_lib as C                      # noqa: E402
import c1r2_members as M                # noqa: E402

def env_from_json(js):
    """env(v) = min over every GATED member (tier A + tier B) of that member's gmax at v (report members excluded)."""
    gated = set(M.TIER_A) | set(M.TIER_B)
    vs = sorted(float(k) for k in js)
    env = {}
    for k in js:
        row = js[k]
        env[float(k)] = min(row[n] for n in row if n in gated and row[n] > 0)
    return vs, env

def fit(env_json, knot_v, margin=0.96, wspeed=None):
    js = json.loads(Path(env_json).read_text())
    vs, env = env_from_json(js)
    vs = np.array(vs); envv = np.array([env[v] for v in vs])
    cap = envv * margin
    kv = np.array(sorted(knot_v))
    # interpolation weight matrix W (len vs x len kv): G_interp(v) = W @ Gknots
    W = np.zeros((len(vs), len(kv)))
    for i, v in enumerate(vs):
        if v <= kv[0]: W[i,0] = 1.0
        elif v >= kv[-1]: W[i,-1] = 1.0
        else:
            j = np.searchsorted(kv, v) - 1
            t = (v - kv[j]) / (kv[j+1] - kv[j]); W[i,j] = 1-t; W[i,j+1] = t
    # weight the objective toward speeds that matter for tracking (default: flat); maximise sum w_i * G_interp(v_i)
    w = np.ones(len(vs)) if wspeed is None else np.array([wspeed(v) for v in vs])
    c = -(w @ W)                          # minimise -objective
    A_ub = W; b_ub = cap
    bounds = [(128, 6000)] * len(kv)
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    Gk = np.round(r.x).astype(int)
    # round knots to integers and verify the INTEGER cave walk stays under the envelope
    knots = [(float(v), int(g)) for v, g in zip(kv, Gk)]
    tbl = C.make_table(knots)
    over = []
    for v in vs:
        g = C.G_at(v, tbl)
        if g > env[v] + 1e-9:
            over.append((round(v,2), g, env[v]))
    return knots, tbl, env, over

if __name__ == "__main__":
    env_json = sys.argv[1]
    knot_v = [float(x) for x in sys.argv[2].split(",")]
    margin = float(sys.argv[3]) if len(sys.argv) > 3 else 0.96
    knots, tbl, env, over = fit(env_json, knot_v, margin)
    print("KNOTS", knots)
    print("cave surface (Kp_eff = 112*G/256):")
    for v in (1,3.1,5,8,10,11.9,12.5,13,15,17,19,22,26,27,30):
        g = C.G_at(v, tbl); print(f"  v{v:5.1f} G{g:5d} Kp_eff{112*g/256:6.0f}  env{env.get(round(v,2),env.get(float(v),0)):5d}")
    print("INTEGER-WALK OVER-ENVELOPE POINTS:", len(over), over[:8])
    nb = len(knots)*6 + 6
    print(f"table bytes: {nb} ({len(knots)} knots + sentinel)")
