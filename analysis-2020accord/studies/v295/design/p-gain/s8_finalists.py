# -*- coding: utf-8 -*-
"""s8_finalists.py -- p-gain lens: the finalists through the SHARED score() (so the four designs are comparable), the
on-centre hunting sim (s5), and the wire-attribution positive control (s6's method, plus the identity on the
candidate's OWN march).

Finalists (all cal-only, the Kp bank 0xCB994 only, all 28 records):
  R1.3_8_100    X [0, 8, 54, 100, 208]  Y [1248, 1248, 1104, 960, 960]    (plateau x1.3 to idx 8, linear taper to V294 at 100)
  R1.35_4_100   X [0, 4, 52, 100, 208]  Y [1296, 1296, 1128, 960, 960]
  R-offset      X [0, 24, 50, 100, 208] Y [1248, 1248, 1097, 1029, 993]   (x1.3 to idx 24, then ~constant +74 T offset)
  g1.2          flat 1152                                                 (the best FLAT multiple that still wins)
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def finalists():
    b = H.Cells.v294()
    return b, [b.replace(kp_x=(0, 8, 54, 100, 208), kp_y=(1248, 1248, 1104, 960, 960), name="R1.3_8_100"),
               b.replace(kp_x=(0, 4, 52, 100, 208), kp_y=(1296, 1296, 1128, 960, 960), name="R1.35_4_100"),
               b.replace(kp_x=(0, 24, 50, 100, 208), kp_y=(1248, 1248, 1097, 1029, 993), name="R-offset"),
               b.replace(kp_y=(1152,) * 5, name="g1.2")]


def main():
    base, F = finalists()
    which = sys.argv[1:] or ["score", "oncentre"]
    if "score" in which:
        for c in F:
            t0 = time.time()
            r = H.score(c)
            json.dump(H.to_jsonable(r), open(os.path.join(OUT, "s8_score_%s.json" % c.name), "w"))
            with open(os.path.join(OUT, "s8_score_%s.txt" % c.name), "w", encoding="utf-8") as fh:
                H.print_score(r, file=fh)
            print("score %s %.0f s  hash %s" % (c.name, time.time() - t0, r["meta"]["hash"][:16]), flush=True)
    if "oncentre" in which:
        from s5_oncentre import run
        fam = H.family()
        mem = [fam[p] for p in ("nominal", "F_hi", "light_b", "b_lo")]
        res = run([base] + F, mem, [3.0, 6.0, 12.0, 20.0, 27.0], [15.0, 60.0])
        json.dump(res, open(os.path.join(OUT, "s8_oncentre.json"), "w"), indent=1)
        idx = {(r["cells"], r["plant"], r["v"], r["d0"]): r for r in res}
        for p in ("nominal", "F_hi", "light_b", "b_lo"):
            for d0 in (15.0, 60.0):
                print("== on-centre %s d0 %g: breakaways/min at 3/6/12/20/27 m/s ; max line dB ; r1-3 max" % (p, d0))
                for c in [base] + F:
                    rr = [idx[(c.name, p, v, d0)] for v in (3.0, 6.0, 12.0, 20.0, 27.0)]
                    print("   %-12s bk %s  line max %+.0f dB  r1-3 max %.2f" % (c.name, [round(x["breakaways_per_min"]) for x in rr],
                                                                              max(x["line_dB"] for x in rr), max(x["r_1_3"] for x in rr)))


if __name__ == "__main__":
    main()
