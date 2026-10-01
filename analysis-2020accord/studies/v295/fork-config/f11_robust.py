# -*- coding: utf-8 -*-
"""f11: ROBUSTNESS of the finalists (pre-registered method rules): the WHOLE identified family + light_b, two sensor-noise
seeds, the two warm-start forms (logged r1 integrator, and x LAF/14 -- identical at LAF 14, so the second warm form here
is the first 3 s of every chunk EXCLUDED), both disturbance models.  Every gate G5-G11 and the win are re-applied on
each (seed, warm) replicate; a finalist is robust only if it passes on ALL of them.
Output: out/f11_robust.json + out/f4_s4seed<k>[_skip3].json (f7_gates-compatible)."""
import sys, json, time
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
import f7_gates as G
H = F.H

c294, c295 = H.Cells.v294(), F.cells_v295()
MEM = ["nominal", "b_lo", "b_hi", "F_lo", "F_hi", "J_lo", "J_hi", "tau0", "tau6", "light_b"]
FIN = [F.Fork("A_Kp0.75_Ki0.40_0.8", kp=0.75, ki=0.4, ki_high=0.8),
       F.Fork("B_Kp0.75_Ki0.40_0.6", kp=0.75, ki=0.4, ki_high=0.6),
       F.Fork("C_Kp0.90_Ki0.30_0.8", kp=0.9, ki=0.3, ki_high=0.8),
       F.Fork("D_Kp0.70_Ki0.40_0.8", kp=0.7, ki=0.4, ki_high=0.8),
       F.Fork("E_Kp0.90_Ki0.50_flat", kp=0.9, ki=0.5)]
import os
if os.environ.get("FIN_SPEC"):
    FIN = [F.Fork(**d) for d in json.load(open(os.environ["FIN_SPEC"]))["forks"]]
TAGP = os.environ.get("ROBUST_TAG", "s4")
pairs = [(c295, F.Fork("r1"))] + [(c295, f) for f in FIN] + [(c294, F.Fork("V294_r1")), (c295, F.Fork("r1dup"))]
summary = {}
t0 = time.time()
for seed in (0, 5):
    out = {False: {}, True: {}}
    for dist in ("lp", "full"):
        nb = 2
        for s in range(0, len(pairs), nb):
            grp = pairs[s:s + nb]
            R, idx = F.sim(grp, MEM, dist=dist, seed=seed)
            for _, fk in grp:
                for m in MEM:
                    out[False][(dist, fk.name, m)] = F.metrics(R, idx[(fk.name, m)])
                    out[True][(dist, fk.name, m)] = F.metrics(R, idx[(fk.name, m)], skip_s=3.0)
            print("  seed %d %s %d/%d  %.0f s" % (seed, dist, min(s + nb, len(pairs)), len(pairs), time.time() - t0), flush=True)
    for skip in (False, True):
        tag = "%sseed%d%s" % (TAGP, seed, "_skip3" if skip else "")
        meta = {f.name: F.asdict(f) for _, f in pairs}
        json.dump(dict(meta=meta, res={"|".join(k): v for k, v in out[skip].items()}), open("out/f4_%s.json" % tag, "w"))
        g = G.gates(meta, out[skip])
        summary[tag] = g
        print("\n== %s" % tag)
        for n, gg in g.items():
            w = " ".join("%s:%+.3f/%+.3f/%+.3f" % (m, *v) for m, v in gg["win"].items())
            print("  %-24s %-4s %-30s %s" % (n, "WIN" if gg["is_win"] else "-", "PASS" if not gg["fails"] else
                                              "FAIL " + "; ".join(gg["fails"][:5]), w), flush=True)
json.dump(summary, open("out/f11_robust_%s.json" % TAGP, "w"), indent=1)
print("\nROBUST (pass + win on all 4 replicates):")
for _, fk in pairs[1:len(FIN) + 1]:
    ok = all((not summary[t][fk.name]["fails"]) and summary[t][fk.name]["is_win"] for t in summary)
    print("  %-24s %s" % (fk.name, "ROBUST" if ok else "not robust: " + ", ".join(
        t for t in summary if summary[t][fk.name]["fails"] or not summary[t][fk.name]["is_win"])))
