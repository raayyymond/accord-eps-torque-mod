# -*- coding: utf-8 -*-
"""c2r2_remedy.py -- NOT a design; a feasibility probe for the orchestrator: does re-sizing Kd for the measured frame
ratio close FA/FB without breaking the other end of the angle range?  P2/F2 tables unchanged, Kd scaled.
Prints min PM over the gated set (tier A / tier B) per case; exact rho max.  ANALYSIS ONLY."""
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M
import c2r2_sweep as SW
D = M.load_designs()
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
mem = [(m, "A") for m in SW.SINGLE] + [(m + "+h10", "B") for m in SW.SINGLE] + [(m, "B") for m in SW.COMBINED] + \
      [(m + "+h10", "B") for m in SW.COMBINED]
def run(dn, kd_new, ratio, gs, ks, vmax=35.0, label=""):
    des = replace(D[dn]); G0 = D[dn].G; des.G = (lambda v, G0=G0: G0(v) * gs)
    kds = kd_new / D[dn].kd * ratio
    wa = wb = (1e9, None); rmax = 0
    for m, t in mem:
        for v in GRID:
            if v > vmax: continue
            pl = M.member(m, v); pl.k *= ks
            r, _ = M.lti_metrics(des, pl, v, kd_scale=kds)
            if t == "A" and r["pm"] < wa[0]: wa = (r["pm"], (m, v))
            if t == "B" and r["pm"] < wb[0]: wb = (r["pm"], (m, v))
    print(f"{dn} Kd {kd_new} {label:34s} tierA min {wa[0]:5.1f} {wa[1]}  tierB min {wb[0]:5.1f} {wb[1]}")
for dn, kd0 in (("P2", 34), ("F2", 20)):
    kd1 = round(kd0 * 1.155)
    run(dn, kd1, 1 / 1.155, 1.0, 1.0, label="FA centre (ratio 1.155)")
    run(dn, kd1, 1.0, 1.155, 1.155, label="FB centre")
    run(dn, kd1, 1 / 0.964, 1.0, 1.0, vmax=10.0, label="FA outward (0.964), v <= 10 only")
    run(dn, kd1, 1.0, 0.964, 0.964, vmax=10.0, label="FB outward, v <= 10 only")
