# -*- coding: utf-8 -*-
"""rj3_grid.py -- lens robust-joint, STAGE 1: the coarse JOINT grid on the fast linear scorer (worst family member).

Knobs (rj_cands.make): g (FF gain), t (HF trim gain = Kp*b), f_fb (fb pole), f_lag (output lag, DC held), kd (Kd level,
with D clamp 4096 and sum clamp 15240 to hold the rail), sched (Kp idx schedule).  Ki is EXCLUDED (census: it integrates
the command with no leak; see the report).  C stays 1024 here (it does not enter the linear loop; sized in stage 3).
Writes rj3_grid.json (one row per candidate) and prints the feasible Pareto front.
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

_CTX = None


def _init():
    global _CTX, _BC, _EV0, RL, RC
    import rj_lin as RL_
    import rj_cands as RC_
    RL, RC = RL_, RC_
    _CTX = RL.Ctx()
    b0 = RC.base()
    _BC = RL.base_cache(_CTX, b0)
    _EV0 = RL.evaluate(_CTX, b0, _BC)


def _one(p):
    g, t, ffb, flag, kd, sched, s = p
    c = RC.make(g=g, t=t, f_fb=ffb, f_lag=flag, kd=kd, sched=sched, s=s)
    if c is None:
        return dict(p=p, ok=False)
    probs = c.problems()
    ev = RL.evaluate(_CTX, c, _BC)
    S = RC.summarise(ev, _EV0)
    S = {k: v for k, v in S.items()}
    S.update(p=p, ok=True, name=c.name, problems=probs, J=RC.objective(S), e_shift=c.e_shift, fb_a=c.fb_a, fb_b=c.fb_b,
             kp_y=list(c.kp_y), lag=(c.lag_a, c.lag_b))
    return S


def pareto(rows, keys):
    """rows minimising every key in keys (tuples of (key, sign)); returns the non-dominated subset."""
    X = np.array([[s * r[k] for k, s in keys] for r in rows])
    keep = []
    for i in range(len(rows)):
        dom = np.all(X <= X[i], axis=1) & np.any(X < X[i], axis=1)
        if not dom.any():
            keep.append(i)
    return [rows[i] for i in keep]


def main():
    G = (0.9, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4)
    T = (1.0, 1.5, 2.0, 2.25, 2.5, 2.75, 2.95, 3.5, 4.0)
    FB = (0.8, 1.0, 1.4, 2.03, 2.8, 4.0)
    LAG = (3.5, 5.05, 7.0, 10.0)
    KD = (0, 48)
    SCH = (("flat", 1.0), ("lowboost", 1.15), ("lowboost", 1.3), ("turnboost", 1.15))
    grid = [(g, t, fb, lg, kd, sc, s) for g, t, fb, lg, kd, (sc, s) in itertools.product(G, T, FB, LAG, KD, SCH)]
    print("grid: %d candidates" % len(grid))
    t0 = time.time()
    with Pool(8, initializer=_init) as pool:
        rows = pool.map(_one, grid, chunksize=40)
    print("evaluated in %.0f s" % (time.time() - t0))
    rows = [r for r in rows if r["ok"]]
    json.dump(rows, open(os.path.join(HERE, "_scratch", "rj3_grid.json"), "w"), default=float)
    feas = [r for r in rows if r["feasible"] and not r["problems"]]
    print("constructible %d, feasible %d" % (len(rows), len(feas)))
    from collections import Counter
    print("infeasibility reasons:", Counter(tuple(r["fails"]) for r in rows if not r["feasible"]))
    # Pareto: benefit (-J) vs HF exposure vs outer margin
    for r in feas:
        r["HF"] = max(r["HF_P"], r["HF_T"])
    front = pareto(feas, (("J", 1), ("HF", 1), ("out_gm_rel", -1)))
    front.sort(key=lambda r: r["J"])
    print("feasible Pareto front (J, HF, outer GM rel): %d points; best 40 by J:" % len(front))
    hdr = ("name", "J", "HF", "out_gm_rel", "out_gm_lb_hwy", "jerk_worst", "jerk_nom", "jerk_lb", "loose_lo_worst",
           "loose_hw_worst", "track_worst", "in_Ms", "stress_rel", "e_shift")
    print("  " + "  ".join(hdr))
    for r in front[:40]:
        print("  %-52s %.3f %.2f %.2f %.2f  %.3f %.3f %.3f  %+.4f %+.4f %+.4f  %.2f %.2f %d"
              % tuple(r[k] for k in hdr))
    # best feasible by J per (sched, kd) and per e_shift, and the flat / kd0 / lag 5.05 / fb 2.03 slice
    print("\nbest feasible J by structure:")
    for key in sorted(set((r["p"][5], r["p"][6], r["p"][4], r["e_shift"]) for r in feas)):
        sub = [r for r in feas if (r["p"][5], r["p"][6], r["p"][4], r["e_shift"]) == key]
        b = min(sub, key=lambda r: r["J"])
        print("  sched %-9s s %.2f kd %2d e %d: best %-52s J %.3f HF %.2f outGM %.2f jerk %.3f lo %+.4f hw %+.4f tr %+.4f"
              % (key[0], key[1], key[2], key[3], b["name"], b["J"], max(b["HF_P"], b["HF_T"]), b["out_gm_rel"], b["jerk_worst"],
                 b["loose_lo_worst"], b["loose_hw_worst"], b["track_worst"]))
    print("\nslice flat, kd 0, lag 5.05, fb 2.03 (only g, t move): J [feasible?]")
    print("       " + " ".join("t%-6.2f" % t for t in T))
    for g in G:
        line = []
        for t in T:
            r = [x for x in rows if x["p"] == (g, t, 2.03, 5.05, 0, "flat", 1.0)]
            line.append(("%+.3f%s" % (r[0]["J"], "" if r[0]["feasible"] else "x")) if r else "  --   ")
        print("  g%.2f " % g + " ".join("%-7s" % s for s in line))


if __name__ == "__main__":
    main()
