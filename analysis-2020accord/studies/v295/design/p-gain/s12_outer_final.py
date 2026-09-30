# -*- coding: utf-8 -*-
"""s12_outer_final.py -- the OUTER loop (fork r1 unchanged, linearised by the harness's outer_frf) at every band's
operating point, for V294, the finalists and the two single-knob references (flat x1.3, map x1.3), on the identified
members and the light_b prior, relay on and off.  pg_lib.outer_local puts the candidate's true local slope and Kp(idx_op)
into the linearisation (the harness's own M_DRIVE outer is at idx 60 with map*Kp' omitted -- exact for flat Kp only).
Adds two low-speed operating points (3.1 m/s, the low-speed-factor region).  ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
from s4_shape_sweep import OPS  # noqa: E402
from s8_finalists import finalists  # noqa: E402
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
OPS2 = [("low-speed straight", 3.1, 14), ("low-speed turn", 3.1, 62)] + OPS


def main():
    base, F = finalists()
    refs = [base.replace(kp_y=(1248,) * 5, name="flat x1.3"),
            base.replace(map_y=tuple(min(int(round(y * 1.3)), 1032) for y in base.map_y), name="map x1.3")]
    cl = [base] + refs + F
    fam = H.family()
    ff = np.logspace(-2, np.log10(20.0), 1200)
    res = {}
    for p in ("nominal", "b_lo", "F_hi", "J_hi", "tau6", "light_b"):
        print("\n== %s  (Ms / GM / PM, relay on)" % p)
        print("  %-19s " % "op point" + "".join("%-22s" % c.name for c in cl))
        for lab, v, io in OPS2:
            pp = fam[p].at(v)
            row = []
            for c in cl:
                for relay in (True, False):
                    mg = H.margins(ff, G.outer_local(c, pp, v, ff, io, relay=relay))
                    res[(p, lab, c.name, relay)] = dict(Ms=mg["Ms"], GM=mg["GM_min"], PM=mg["PM_min"], fMs=mg["f_Ms"])
                x = res[(p, lab, c.name, True)]
                row.append("%.2f/%.2f/%3.0f" % (x["Ms"], x["GM"], x["PM"]) + " " * 7)
            print("  %-12s v%4.1f i%3d " % (lab[:12], v, io) + "".join("%-22s" % r for r in row))
    json.dump(H.to_jsonable(res), open(os.path.join(OUT, "s12_outer_final_all.json"), "w"), indent=1)
    names = [c.name for c in cl if c.name in ("V294", "flat x1.3", "map x1.3", "R1.3_8_100")]
    labs = [l for l, _, _ in OPS2]
    fig = dict(labels=labs, names=names, Ms_light_b={nm: [res[("light_b", l, nm, True)]["Ms"] for l in labs] for nm in names})
    json.dump(fig, open(os.path.join(OUT, "s12_outer_final.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
