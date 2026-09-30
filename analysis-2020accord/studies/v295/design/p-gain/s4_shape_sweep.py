# -*- coding: utf-8 -*-
"""s4_shape_sweep.py -- p-gain lens: every shape of s3 (flat Kp g, Kp(idx) schedules, demand-map shapes) scored in
ONE batch with V294 (harness rule 1): mode-B closed loop, the fork UNCHANGED, dist lp AND full, on nominal / light_b /
b_lo; plus the OUTER loop linearised at each band's own operating point (pg_lib.outer_local: the true local slope and
Kp(idx_op)) on nominal / light_b / b_lo / J_hi, relay on.  Output out/s4_*.json and a printed digest.
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
from s3_shapes import cands  # noqa: E402
H = G.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# (label, v, idx_op): the r71b census's operating points (s2_idx_census_out.txt)
OPS = [("straight 0-10", 5.0, 10), ("hold 5-10", 8.0, 50), ("hard 5-10", 8.0, 75), ("hold 10-15", 12.0, 36),
       ("straight 10+", 17.0, 6), ("hold 15-22", 17.0, 34), ("hard 15-22", 17.0, 50), ("hold 22+", 26.9, 18),
       ("straight 22+", 26.9, 6)]


def main():
    C = cands()
    base = C[0]
    cs = C[1:]
    t0 = time.time()
    S = H.sweep_drive(cs, plants=("nominal", "light_b", "b_lo"), dists=("lp", "full"))
    print("sweep %.0f s" % (time.time() - t0))
    json.dump(H.to_jsonable(S), open(os.path.join(OUT, "s4_shape_sweep_drive.json"), "w"), indent=1)
    names = [c.name for c in cs] + ["V294"]
    for dist in ("lp", "full"):
        for p in ("nominal", "light_b", "b_lo"):
            print("\n=== %s %s  (candidate - V294: track / hold / straight / J_err / ish / rate1-3 %% / hard16 %%)" % (dist, p))
            ref = S[(dist, "V294", p)]
            for nm in names:
                r = S[(dist, nm, p)]
                row = []
                for b in ("0-5", "5-10", "10-15", "15-22", "22+"):
                    x, y = r.get(b), ref.get(b)
                    if x is None:
                        continue
                    row.append("%s %+.3f/%+.3f/%+.2f/%+.3f/%+.2f/%+.0f%%/%s" % (
                        b, x["track_gain"] - y["track_gain"], x["turn_hold"] - y["turn_hold"],
                        x["straight_delivery"] - y["straight_delivery"], x["J_err"] - y["J_err"], x["i_share"] - y["i_share"],
                        100 * (x["r_mid"] / y["r_mid"] - 1),
                        ("%+.0f%%" % (100 * (x["hard16"] / y["hard16"] - 1))) if np.isfinite(y["hard16"]) else "-"))
                lc = r["limit_cycle"]
                print("  %-11s %s | lc %.2fHz %+.1fdB" % (nm, "  ".join(row), lc["f"], lc["dB"]))
    fam = H.family()
    ff = np.logspace(-2, np.log10(20.0), 800)
    lin = {}
    print("\n=== OUTER loop at each band's operating point (relay on): Ms / GM   [V294 first]")
    for p in ("nominal", "light_b", "b_lo", "J_hi"):
        print(" plant %s" % p)
        for lab, v, io in OPS:
            pp = fam[p].at(v)
            row = []
            for c in [base] + cs:
                mg = H.margins(ff, G.outer_local(c, pp, v, ff, io))
                lin[(p, lab, c.name)] = dict(Ms=mg["Ms"], GM=mg["GM_min"], PM=mg["PM_min"], fMs=mg["f_Ms"])
                row.append("%s %.2f/%.2f" % (c.name, mg["Ms"], mg["GM_min"]))
            print("   %-13s v%4.1f idx%3d  %s" % (lab, v, io, "  ".join(row)))
    json.dump(H.to_jsonable(lin), open(os.path.join(OUT, "s4_shape_outer.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
