# -*- coding: utf-8 -*-
"""d7_hard16 -- WHY does r2alt raise the plant-alone (lp) hard-turn 1.6-3 Hz wheel rate at 15-22 m/s when the linear
outer-loop sensitivity there moves by <= 0.5 %?  Decomposition on nominal, real fork controller, paired noise:
  (i)  the same run with the plant's Coulomb/static friction REMOVED (Fc = Fs = 0): if the excess vanishes it is
       friction-driven (stick-slip), if it stays it is linear;
  (ii) stick-slip events (stuck -> sliding transitions at the 100 Hz frames) and stuck fraction inside hard frames;
  (iii) the planner's own 1.6-3 Hz content in the same frames and the rate's coherence with it."""
import os, sys, json
from dataclasses import replace
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import d2_engine as E
import d4_drive as D4
import v295_harness as H

fam = H.family()
nom = fam["nominal"]
nof = replace(nom, name="nominal_nofric", Fc=np.zeros_like(nom.Fc), Fs=np.zeros_like(nom.Fs))
nof.kappa = False
fam_extra = {"nominal": nom, "nominal_nofric": nof}
_orig_family = H.family
H.family = lambda include_stress=True: dict(_orig_family(include_stress), nominal_nofric=nof)  # noqa: E731

chunks = H.route_chunks()
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
res = {}
for seed in (0, 5):
    for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
        R = D4.run_config(cfg, ["nominal", "nominal_nofric"], "lp", chunks, seed)
        for mi, m in enumerate(("nominal", "nominal_nofric")):
            rows = [mi * len(chunks) + k for k in range(len(chunks))]
            acc = dict(h=[], pl=[], ev=0, st=[], n=0)
            for j in rows:
                n = R["lens"][j]
                v, r, pl, ang, om = R["v"][j, :n], R["rate18"][j, :n], R["la_plan"][j, :n], R["ang"][j, :n], R["om"][j, :n]
                mk = (v >= 15) & (v < 22)
                cut = np.zeros(n, bool); cut[100:-100] = True
                hard = mk & cut & ((np.abs(pl) >= 1.5) | (np.abs(ang) > 60))
                acc["h"].append(H._bp(r, 1.6, 3.0)[hard])
                acc["pl"].append(H._bp(pl, 1.6, 3.0)[hard])
                stuck = om == 0.0
                ev = np.flatnonzero(stuck[:-1] & ~stuck[1:] & hard[1:])
                acc["ev"] += len(ev)
                acc["st"].append(stuck[hard])
                acc["n"] += int(hard.sum())
            h = np.concatenate(acc["h"]); pl = np.concatenate(acc["pl"]); st = np.concatenate(acc["st"])
            res[(seed, cfg, m)] = dict(hard16=float(np.sqrt(np.mean(h ** 2))), plan16=float(np.sqrt(np.mean(pl ** 2))),
                                       events_per_s=acc["ev"] / max(acc["n"] / 100.0, 1e-9), stuck=float(np.mean(st)),
                                       sec=acc["n"] / 100.0)
        print("done", seed, cfg, flush=True)
for seed in (0, 5):
    for m in ("nominal", "nominal_nofric"):
        a, b, c = (res[(seed, k, m)] for k in ("V294+r1", "V295+r1", "V295+r2alt"))
        P("seed %d %-15s hard16 V294r1 %.3f  V295r1 %.3f  r2alt %.3f  (r2alt/V295r1 x%.2f, r2alt/V294r1 x%.2f) | stick->slip events/s "
          "%.2f %.2f %.2f | stuck frac %.2f %.2f %.2f | planner 1.6-3 Hz rms %.3f | %.0f s" % (
              seed, m, a["hard16"], b["hard16"], c["hard16"], c["hard16"] / b["hard16"], c["hard16"] / a["hard16"],
              a["events_per_s"], b["events_per_s"], c["events_per_s"], a["stuck"], b["stuck"], c["stuck"], c["plan16"], c["sec"]))
open(os.path.join(HERE, "out", "d7_hard16_out.txt"), "w").write("\n".join(L) + "\n")
