"""Step 3 (events): lag budget on s2_jerk's matched high-desired-jerk events (>= 8 m/s), logged and common lead, plus the
per-event COUNTERFACTUAL shaping lag (the setpoint chain is open loop from the model, so it can be replayed exactly under
any chain: lagmod.simulate_setpoint, validated against every route's logged setpoint in s01).

Event set, windows and matcher are s2_jerk's (s2_common.load_all / match; events from s2_extract: V.jerk_events thr 0.4,
window [-1.0, +2.5] s).  Lag estimator: s2_extract.fixed_lag (achieved segment fixed, input slid, Pearson per lag,
-0.5..+0.8 s), all channels zero-phase lowpassed at 3 Hz (so no filter lag is added).
Pairs: x->sp, sp->act, act->pose, x->act, x->pose; COMMON lead xc(t) = x(t - (ld - 0.20)): xc->sp, xc->pose;
counterfactual: x->sp under the V282 chain (1.2 Hz jerk LP, no ref filter, liveDelay 0.20) and under the flown chain but
liveDelay 0.20; control: x delayed 0.30 s.
CIs: (a) events with replacement; (b) routes with replacement on BOTH sides (V282 routes and torque routes), then pairs.
out: s06_events.json, s06_events.txt
"""
import sys, json, gc
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "s2_jerk"))
import v282cmp as V
from s2_common import load_all, match, vbin
from s2_extract import fixed_lag
from lagmod import simulate_setpoint, ROUTE_CFG, COMMITS

rows, _tr = load_all(); del _tr
byroute = {}
for r in rows:
    byroute.setdefault(r["route"], []).append(r)
PRE, POST = 100, 250
for rk, R in byroute.items():
    S = V.load(rk)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    ld_arr = np.nan_to_num(S["lat_delay"], nan=0.2)
    ld = float(np.nanmedian(S["lat_delay"][m]))
    dsh = int(round((ld - 0.20) * 100))
    x = np.nan_to_num(S["model"]); sp = np.nan_to_num(S["setpoint"])
    act = np.nan_to_num(S["la_act"]); pose = np.nan_to_num(S["la_pose"])
    D = np.load(V.CACHE / f"{rk}.npz"); curv = D["cs_des_curv"]; active = D["cs_active"] > 0.5; del D
    cfg = ROUTE_CFG[rk]
    sp_v282chain = simulate_setpoint(curv, v, active, np.full(len(t), 0.2), 1.2, 0.0)
    sp_ld20 = simulate_setpoint(curv, v, active, np.full(len(t), 0.2), COMMITS[cfg["commit"]]["jerk_fc"], cfg["ref_rc"])
    sp_flown = simulate_setpoint(curv, v, active, ld_arr, COMMITS[cfg["commit"]]["jerk_fc"], cfg["ref_rc"])
    del S
    LP = lambda y: V.lowpass(np.nan_to_num(y), 3.0)
    C = dict(x=LP(x), sp=LP(sp), act=LP(act), pose=LP(pose), cf=LP(sp_v282chain), cf20=LP(sp_ld20), sim=LP(sp_flown))
    C["xc"] = np.concatenate([np.full(max(dsh, 0), C["x"][0]), C["x"][:len(x) - max(dsh, 0)]])
    C["ctl"] = np.concatenate([np.full(30, C["x"][0]), C["x"][:-30]])
    for r in R:
        k = r["k"]; i0, i1 = k - PRE, k + POST
        if i0 - 100 < 0 or i1 + 100 > len(x):
            r["ok"] = False; continue
        r["ok"] = True; r["ld"] = ld
        for a, b, nm in (("x", "sp", "x_sp"), ("sp", "act", "sp_act"), ("act", "pose", "act_pose"), ("x", "act", "x_act"),
                         ("x", "pose", "x_pose"), ("xc", "sp", "xc_sp"), ("xc", "pose", "xc_pose"), ("xc", "act", "xc_act"),
                         ("x", "cf", "x_cfV282chain"), ("x", "cf20", "x_cfFlownLd20"), ("x", "sim", "x_simflown"), ("x", "ctl", "ctl")):
            L, g, c = fixed_lag(C[a], C[b], i0, i1)
            r["lag_" + nm] = L; r["corr_" + nm] = c
    print(rk, V.ROUTES[rk]["group"], "events", len(R), "ld", round(ld, 3), "shift", dsh, flush=True)
    del C, x, sp, act, pose, curv, sp_v282chain, sp_ld20, sp_flown; gc.collect()

rows = [r for r in rows if r.get("ok")]
KEYS = ["lag_x_sp", "lag_sp_act", "lag_act_pose", "lag_x_act", "lag_x_pose", "lag_xc_sp", "lag_xc_act", "lag_xc_pose",
        "lag_x_cfV282chain", "lag_x_cfFlownLd20", "lag_x_simflown", "lag_ctl"]
rng = np.random.default_rng(11)


def boot2(P, key, n=3000):
    d = np.array([p[1][key] - p[0][key] for p in P]); rr = np.array([p[0]["route"] for p in P]); tt = np.array([p[1]["route"] for p in P])
    if len(d) < 3:
        return dict(n=len(d), med=float("nan"), ci_ev=[float("nan")] * 2, ci_rt2=[float("nan")] * 2, mean=float("nan"))
    be = [np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(n)]
    ur, ut = np.unique(rr), np.unique(tt); br = []
    for _ in range(n):
        wr = {u: c for u, c in zip(*np.unique(rng.choice(ur, len(ur)), return_counts=True))}
        wt = {u: c for u, c in zip(*np.unique(rng.choice(ut, len(ut)), return_counts=True))}
        w = np.array([wr.get(a, 0) * wt.get(b, 0) for a, b in zip(rr, tt)], float)
        if w.sum() == 0:
            continue
        idx = rng.choice(len(d), len(d), p=w / w.sum())
        br.append(np.median(d[idx]))
    return dict(n=int(len(d)), med=float(np.median(d)), mean=float(np.mean(d)), ci_ev=[float(x) for x in np.percentile(be, [2.5, 97.5])],
                ci_rt2=[float(x) for x in np.percentile(br, [2.5, 97.5])])


REF = [r for r in rows if r["group"] == "V282"]
STRATA = {">=8": [1, 2, 3], "8-15": [1], "15-22": [2], ">=22": [3]}
out = {}
txt = []
for tqg in (["T64"], ["T64B"], ["T64", "T64B"], ["T5"], ["T4"], ["V282old"]):
    name = "+".join(tqg)
    TQ = [r for r in rows if r["group"] in tqg]
    pairs = match(REF, TQ)
    out[name] = {}
    txt.append(f"\n##### {name} minus V282 (matched high-jerk events; median paired diff, s; [event CI] [route-2-sided CI])")
    for sn, vbs in STRATA.items():
        P = [p for p in pairs if p[1]["vb"] in vbs]
        d = dict(n_pairs=len(P), n_tq=sum(r["vb"] in vbs for r in TQ),
                 match=dict(jerk=[float(np.median([p[i]["jerk"] for p in P])) if P else None for i in (0, 1)],
                            v=[float(np.median([p[i]["v"] for p in P])) if P else None for i in (0, 1)],
                            step=[float(np.median([p[i]["step"] for p in P])) if P else None for i in (0, 1)]))
        for key in KEYS:
            b = boot2(P, key)
            b["ref_med"] = float(np.median([p[0][key] for p in P])) if P else float("nan")
            b["tq_med"] = float(np.median([p[1][key] for p in P])) if P else float("nan")
            d[key] = b
        out[name][sn] = d
        txt.append(f"  -- {sn}: pairs {d['n_pairs']} of {d['n_tq']} tq events; match jerk {d['match']['jerk']} v {d['match']['v']} step {d['match']['step']}")
        for key in KEYS:
            b = d[key]
            if b["n"] < 3:
                continue
            txt.append(f"     {key:22s} V282 {b['ref_med']:+.3f}  T {b['tq_med']:+.3f}  diff {b['med']:+.3f} (mean {b['mean']:+.3f}) ev[{b['ci_ev'][0]:+.3f},{b['ci_ev'][1]:+.3f}] rt2[{b['ci_rt2'][0]:+.3f},{b['ci_rt2'][1]:+.3f}]")
json.dump(dict(results=out, rows=[{k: r[k] for k in ["route", "group", "k", "v", "jerk", "step", "type", "ld"] + KEYS + ["corr_x_sp", "corr_sp_act", "corr_x_pose"]} for r in rows]),
          open(HERE / "s06_events.json", "w"), indent=1, default=float)
open(HERE / "s06_events.txt", "w").write("\n".join(txt))
print("\n".join(txt))
