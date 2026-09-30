# -*- coding: utf-8 -*-
"""s10_fe_seeds.py -- adversary `stability`: adjudicate F-e.  In s5 (harness engine, dist lp, one noise seed) the
hard-turn 1.6-3 Hz ratio A1017/V294 exceeded 1.05 on b_hi 15-22 (1.055) and nom_J0.5nr 5-10 (1.053) -- my pre-registered
F-e fires AS WRITTEN.  Is it noise?  V294 and A1017 are different batch rows, so they get different x-noise draws.
Re-run those members (plus controls) under lp with x_noise 0 (deterministic, paired) and with 3 more noise seeds."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import v295_harness as H  # noqa: E402
from s5_sweep_family import members  # noqa: E402


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base = H.Cells.v294()
    cand = base.replace(fb_a=1017, name="A1017")
    fam = members()
    names = ["b_hi", "nom_J0.5nr", "J_hi2", "lb_J2.5x", "nominal", "light_b"]
    mem = [fam[n] for n in names]
    chunks = H.route_chunks()
    runs = [("xn0", H.SimOpts(mode="B", dist="lp", x_noise=0.0))] + \
           [("seed%d" % s, H.SimOpts(mode="B", dist="lp", seed=s)) for s in (1, 2, 3)]
    out = {}
    for tag, o in runs:
        R = H.simulate([base, cand], mem, chunks, o)
        nM, nK = len(mem), len(chunks)
        for ci, cn in enumerate(("V294", "A1017")):
            for mi, mn in enumerate(names):
                rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
                out[(tag, cn, mn)] = H.drive_metrics(H.drive_series_sim(R, rows))
        pr("%s done" % tag)
    for mn in names:
        for b in ("5-10", "15-22", "22+"):
            h = [out[(tag, "A1017", mn)][b]["hard16"] / out[(tag, "V294", mn)][b]["hard16"] for tag, _ in runs]
            rm = [out[(tag, "A1017", mn)][b]["r_mid"] / out[(tag, "V294", mn)][b]["r_mid"] for tag, _ in runs]
            pr("  %-11s %-6s hard16 ratio xn0 %.3f, seeds %s | r_mid xn0 %.3f seeds %s | V294 hard16 abs %.3f deg/s" % (
                mn, b, h[0], np.round(h[1:], 3).tolist(), rm[0], np.round(rm[1:], 3).tolist(), out[("xn0", "V294", mn)][b]["hard16"]))
    open(os.path.join(HERE, "s10_fe_seeds_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
