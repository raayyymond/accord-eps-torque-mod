# -*- coding: utf-8 -*-
"""rj5_fine.py -- lens robust-joint, STAGE 1c: fine local search around the stage-1b front, C held at 1024 and the output
lag held (both unreadable / not worth their HF budget, see the report), flat Kp, e_shift 2, kmap 1 -- i.e. only the
cells that the wire can attribute: Kp bank level (g), b (t), and the fb pole a.  Prints the per-member detail of the
best points so the binding constraint is visible.  ANALYSIS ONLY."""
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj4_grid2 as G2  # noqa: E402


def main():
    G = tuple(np.round(np.arange(1.0, 1.351, 0.025), 3))
    T = tuple(np.round(np.arange(1.5, 2.051, 0.05), 3))
    FB = (1.7, 1.85, 2.03, 2.2, 2.4)
    grid = [(g, t, fb, 5.05, 1024, "flat", 1.0, 1) for g, t, fb in itertools.product(G, T, FB)]
    print("fine grid: %d" % len(grid))
    t0 = time.time()
    with Pool(8, initializer=G2._init) as pool:
        rows = pool.map(G2._one, grid, chunksize=20)
    print("evaluated in %.0f s" % (time.time() - t0))
    ok = [r for r in rows if r["ok"]]
    json.dump(ok, open(os.path.join(HERE, "_scratch", "rj5_fine.json"), "w"), default=float)
    feas = [r for r in ok if r["feasible"]]
    print("feasible %d of %d" % (len(feas), len(ok)))
    feas.sort(key=lambda r: r["J"])
    for r in feas[:12]:
        print("  %-48s J %.3f HF %.2f oGM %.2f lbH %.2f jerk %.3f/%.3f/%.3f lo %+.4f hw %+.4f tr %+.4f inMs %.2f i32 %.2f rp %d cap %d ob %.2f %s"
              % (r["name"], r["J"], r["HF"], r["out_gm_rel"], r["out_gm_lb_hwy"], r["jerk_worst"], r["jerk_nom"], r["jerk_lb"],
                 r["loose_lo_worst"], r["loose_hw_worst"], r["track_worst"], r["in_Ms"], r["i32"], r["restart100"],
                 r["trim_cap"], r["outer_bind_r"], r["outer_bind"]))
    print("\nper (g): the best feasible t/fb and its J (the g-direction of the front)")
    for g in G:
        fs = [r for r in feas if abs(r["p"][0] - g) < 1e-9]
        if not fs:
            inf = [r for r in ok if abs(r["p"][0] - g) < 1e-9]
            from collections import Counter
            print("  g %.3f: none feasible; reasons %s; binding outer key %s" % (
                g, Counter(tuple(r["fails"]) for r in inf).most_common(3),
                Counter(r["outer_bind"] for r in inf if "H_LOOP2" in r["fails"]).most_common(2)))
            continue
        b = min(fs, key=lambda r: r["J"])
        print("  g %.3f: t %.2f fb %.2f  J %.3f  jerk %.3f  lo %+.4f hw %+.4f tr %+.4f  oGM %.2f  rp %d  i32 %.2f  ob %.2f %s"
              % (g, b["p"][1], b["p"][2], b["J"], b["jerk_worst"], b["loose_lo_worst"], b["loose_hw_worst"], b["track_worst"],
                 b["out_gm_rel"], b["restart100"], b["i32"], b["outer_bind_r"], b["outer_bind"]))


if __name__ == "__main__":
    main()
