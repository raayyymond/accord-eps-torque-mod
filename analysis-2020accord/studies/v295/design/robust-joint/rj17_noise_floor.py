# -*- coding: utf-8 -*-
"""rj17_noise_floor.py -- lens robust-joint: the harness draws the 1.93-count x noise per BATCH ROW (PlantBatch.rng.normal
over B), so a candidate and its same-batch V294 see DIFFERENT noise realisations.  Null control: three byte-identical
copies of V294 under different names in one sweep_drive batch (nominal and light_b, lp and full) -> the ratio of each
metric between identical cells IS the harness's own floor for 'ratio vs V294'.  ANALYSIS ONLY."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rj_cands as RC
from rj_lin import H
base = RC.base()
cl = [base.replace(name="V294_copy%d" % i) for i in (1, 2, 3)]
out = {}
for p in ("nominal", "light_b"):
    S = H.sweep_drive(cl, plants=(p,), dists=("lp", "full"))
    for dist in ("lp", "full"):
        for c in cl:
            a, b = S[(dist, c.name, p)], S[(dist, "V294", p)]
            line = []
            for bd in ("5-10", "10-15", "15-22", "22+"):
                for k in ("hard16", "r_mid", "track_gain"):
                    try:
                        v = a[bd][k] / b[bd][k] if k != "track_gain" else a[bd][k] - b[bd][k]
                    except Exception:
                        v = float("nan")
                    out["%s|%s|%s|%s|%s" % (dist, c.name, p, bd, k)] = v
                    line.append("%s %s %s" % (bd, k, ("x%.3f" % v) if k != "track_gain" else ("%+.4f" % v)))
            print("  %-8s %-4s %-10s %s" % (p, dist, c.name, "  ".join(line)), flush=True)
json.dump(out, open(os.path.join(HERE, "rj17_noise_floor.json"), "w"), indent=1)
