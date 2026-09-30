# -*- coding: utf-8 -*-
"""rj4_grid2.py -- lens robust-joint, STAGE 1b: the joint grid WITH the pre-registered M_SAFE constraints included.

Stage 1 (rj3_grid) ignored H-SAFE-2/3.  They bind (the int32 margin at a*s couples b to the fb pole, and the restart
pulse scales with Kp*b), so this pass adds, per candidate (harness functions, byte-exact lane):
  int32 minimum margin >= 2.0 (H.int32_margins) ; restart pulse at 100 deg/s <= 2 x V294's (H.restart_pulse) ;
  trim cap <= 2 x V294's 616 T (closed form C*Kp(0) through the taper/lag/gain, checked vs H.m_safe on finalists).
New knobs vs stage 1: C in {640, 768, 896, 1024} (C < 1024 bounds the restart pulse and the trim cap) and kmap in {1, 2}
(Kp x kmap with the assist-map Y / kmap: the FF is unchanged, b is divided by kmap -> relaxes the int32 bound CAL-ONLY).
Kd is dropped (stage 1: < 0.01 of objective; it raises the rail unless the sum clamp is cut, and no wire instrument
separates D).  e_shift stays 2 (no opcode) -- the opcode is only reached if a cal-only point cannot be found.
ANALYSIS ONLY."""
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _init():
    global CTX, BC, EV0, RL, RC, H, R0
    import rj_lin as RL_
    import rj_cands as RC_
    RL, RC, H = RL_, RC_, RL_.H
    CTX = RL.Ctx()
    b0 = RC.base()
    BC = RL.base_cache(CTX, b0)
    EV0 = RL.evaluate(CTX, b0, BC)
    R0 = H.restart_pulse(b0)


def make2(g, t, ffb, flag, C, sched, s, kmap):
    c = RC.make(g=g * kmap, t=t, f_fb=ffb, f_lag=flag, sched=sched, s=s, C=C, allow_opcode=False)
    if c is None:
        return None
    if kmap != 1:
        b0 = RC.base()
        my = tuple(int(round(y / kmap)) for y in b0.map_y)
        c = c.replace(map_y=my, name=c.name + "_kmap%d" % kmap)
    return c


def trim_cap_T(c):
    """closed form: |T| at zero command with r26 at +-C (P = C*Kp(0)/256, taper 254, lag DC, gain)."""
    kp0 = float(H.lerp_table(c.kp_x, c.kp_y)[0])
    dc = 2 * c.lag_b / ((1024 - c.lag_a) * 32.0)
    return c.fb_clamp * kp0 / 256.0 * 254 / 256.0 * dc * c.gain / 32768.0


def _one(p):
    g, t, ffb, flag, C, sched, s, kmap = p
    c = make2(g, t, ffb, flag, C, sched, s, kmap)
    if c is None:
        return dict(p=p, ok=False, why="b > 0.95 b_max")
    i32 = min(v["margin"] for v in H.int32_margins(c).values())
    rp = H.restart_pulse(c, rates_dps=(100.0,))[100.0]["peak"]
    tc = trim_cap_T(c)
    ev = RL.evaluate(CTX, c, BC)
    S = RC.summarise(ev, EV0)
    safe = dict(H_SAFE2=(i32 >= 2.0 and not c.problems()), H_SAFE3=(rp <= 2 * R0[100.0]["peak"] and tc <= 2 * 616))
    S["fails"] = S["fails"] + [k for k, v in safe.items() if not v]
    S["feasible"] = S["feasible"] and all(safe.values())
    # which outer (member, v) binds the Ms / GM constraint
    worst_key, worst = None, 0.0
    for k, x in ev["outer"].items():
        x0 = EV0["outer"][k]
        r = max(x["Ms"] / max(1.1 * x0["Ms"], 1.5), min(x0["GM"], 2.0) * 0.95 / x["GM"])
        if r > worst:
            worst, worst_key = r, k
    S.update(p=p, ok=True, name=c.name, i32=i32, restart100=rp, trim_cap=tc, J=RC.objective(S), fb_a=c.fb_a, fb_b=c.fb_b,
             kp_y=list(c.kp_y), map_y=list(c.map_y), lag=(c.lag_a, c.lag_b), outer_bind=str(worst_key), outer_bind_r=worst,
             HF=max(S["HF_P"], S["HF_T"]))
    return S


def pareto(rows, keys):
    X = np.array([[s * r[k] for k, s in keys] for r in rows])
    keep = []
    for i in range(len(rows)):
        dom = np.all(X <= X[i], axis=1) & np.any(X < X[i], axis=1)
        if not dom.any():
            keep.append(i)
    return [rows[i] for i in keep]


def main():
    G = (1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3)
    T = (1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 2.95)
    FB = (1.4, 1.7, 2.03, 2.4, 2.8, 3.4)
    LAG = (5.05, 7.0)
    CC = (640, 768, 896, 1024)
    SCH = (("flat", 1.0), ("lowboost", 1.15))
    KM = (1, 2)
    grid = list(itertools.product(G, T, FB, LAG, CC, [s[0] for s in SCH], [1.0], KM))
    grid = [(g, t, fb, lg, C, sc, (1.15 if sc == "lowboost" else 1.0), km) for g, t, fb, lg, C, sc, _, km in grid]
    print("grid: %d candidates" % len(grid))
    t0 = time.time()
    with Pool(8, initializer=_init) as pool:
        rows = pool.map(_one, grid, chunksize=30)
    print("evaluated in %.0f s" % (time.time() - t0))
    ok = [r for r in rows if r["ok"]]
    json.dump(ok, open(os.path.join(HERE, "_scratch", "rj4_grid2.json"), "w"), default=float)
    feas = [r for r in ok if r["feasible"]]
    from collections import Counter
    print("constructible %d (b <= 0.95 b_max), feasible %d" % (len(ok), len(feas)))
    print("infeasibility reasons:", Counter(tuple(r["fails"]) for r in ok if not r["feasible"]).most_common(12))
    print("outer-constraint binding keys among infeasible H_LOOP2:",
          Counter(r["outer_bind"] for r in ok if "H_LOOP2" in r["fails"]).most_common(8))
    front = pareto(feas, (("J", 1), ("HF", 1), ("out_gm_rel", -1)))
    front.sort(key=lambda r: r["J"])
    print("feasible Pareto front (J, HF, outer GM rel): %d points; best 30 by J:" % len(front))
    hdr = ("name", "J", "HF", "out_gm_rel", "out_gm_lb_hwy", "jerk_worst", "jerk_nom", "jerk_lb", "loose_lo_worst",
           "loose_hw_worst", "track_worst", "in_Ms", "i32", "restart100", "trim_cap", "outer_bind_r")
    for r in front[:30]:
        print("  %-62s J %.3f HF %.2f oGM %.2f lbH %.2f jerk %.3f/%.3f/%.3f lo %+.4f hw %+.4f tr %+.4f inMs %.2f i32 %.2f rp %d cap %d ob %.2f"
              % tuple(r[k] for k in hdr))
    print("\nbest feasible by (sched, kmap, lag):")
    for key in sorted(set((r["p"][5], r["p"][7], r["p"][3]) for r in feas)):
        sub = [r for r in feas if (r["p"][5], r["p"][7], r["p"][3]) == key]
        b = min(sub, key=lambda r: r["J"])
        print("  %-9s kmap %d lag %.2f: %-62s J %.3f HF %.2f oGM %.2f jerk %.3f lo %+.4f hw %+.4f tr %+.4f rp %d"
              % (key[0], key[1], key[2], b["name"], b["J"], b["HF"], b["out_gm_rel"], b["jerk_worst"], b["loose_lo_worst"],
                 b["loose_hw_worst"], b["track_worst"], b["restart100"]))
    print("\nslice flat, kmap 1, lag 5.05, C 1024: best J over fb per (g, t)  [x = infeasible at every fb; reason of the fb 2.03 row]")
    print("        " + " ".join("t%-7.2f" % t for t in T))
    for g in G:
        line = []
        for t in T:
            sub = [x for x in ok if x["p"][0] == g and x["p"][1] == t and x["p"][3] == 5.05 and x["p"][4] == 1024
                   and x["p"][5] == "flat" and x["p"][7] == 1]
            fs = [x for x in sub if x["feasible"]]
            if fs:
                b = min(fs, key=lambda r: r["J"])
                line.append("%+.3f@%.1f" % (b["J"], b["p"][2]))
            else:
                r203 = [x for x in sub if x["p"][2] == 2.03]
                line.append("x" + (",".join(f[2:] for f in r203[0]["fails"]) if r203 else "--"))
        print("  g%.2f " % g + " ".join("%-12s" % s for s in line))


if __name__ == "__main__":
    main()
