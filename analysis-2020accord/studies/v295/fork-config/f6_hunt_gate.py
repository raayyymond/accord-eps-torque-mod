# -*- coding: utf-8 -*-
"""f6: gate G4 (on-centre hunt, time domain) for the finalists, as pre-registered:
FAIL if, in the last 30 s of a 60 s straight at constant speed with zero planner demand and a constant crown torque
(0, 0.6, 1.5 x Fs), the angle p-p > 2 x V295+r1's at the same (member, speed, crown) point, or > 1.0 deg where r1 is
< 0.5 deg.  Two noise seeds (the result must hold on both).  Members: every identified member + light_b.
Usage: python f6_hunt_gate.py <spec.json>  (spec: {"forks": [Fork kwargs...]})."""
import sys, json, time
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

c295 = F.cells_v295()
MEM = ["nominal", "b_lo", "b_hi", "F_lo", "F_hi", "J_lo", "J_hi", "tau6", "light_b"]
SPD = (3.1, 4.0, 5.0, 8.0, 12.0, 17.0, 22.0, 27.0)
CROWN = (0.0, 0.6, 1.5)
spec = json.load(open(sys.argv[1]))
forks = [F.Fork(**d) for d in spec["forks"]]
pairs = [(c295, F.Fork("r1"))] + [(c295, f) for f in forks if f.name != "r1"]
verdict = {f.name: [] for _, f in pairs}
verdict_raw = {f.name: [] for _, f in pairs}      # extra hits of the AS-WRITTEN rule (no quantisation floor)
allres = {}
for seed in (3, 11):
    t0 = time.time()
    # split so a batch stays <= ~700 lanes
    per = len(MEM) * len(SPD) * len(CROWN)
    nb = max(1, int(__import__("os").environ.get("HUNT_LANES", "700")) // per)
    cand = pairs[1:]
    for s in range(0, len(cand), max(1, nb - 1)):
        grp = [pairs[0]] + cand[s:s + max(1, nb - 1)]          # every batch carries its OWN r1 (noise is per row)
        res = F.hunt(grp, MEM, SPD, CROWN, secs=60.0, seed=seed)
        for (_, fk) in grp[1:]:
            for m in MEM:
                for v in SPD:
                    for c in CROWN:
                        a = res[(fk.name, m, v, c)]
                        b = res[("r1", m, v, c)]
                        bad = (a["pp"] > 2.0 * b["pp"] and a["pp"] > 0.25) or (b["pp"] < 0.5 and a["pp"] > 1.0) or a["diverged"]
                        raw = (a["pp"] > 2.0 * b["pp"]) or (b["pp"] < 0.5 and a["pp"] > 1.0) or a["diverged"]
                        if raw and not bad:
                            verdict_raw[fk.name].append("seed%d %s v%.1f crown%.1f pp %.2f (r1 %.2f)" %
                                                        (seed, m, v, c, a["pp"], b["pp"]))
                        if bad:
                            verdict[fk.name].append("seed%d %s v%.1f crown%.1f pp %.2f (r1 %.2f) f %.2f Hz" %
                                                    (seed, m, v, c, a["pp"], b["pp"], a["f_pk"]))
        allres.update({("s%d" % seed,) + k: v for k, v in res.items()})
    print("seed %d: %.1f s" % (seed, time.time() - t0), flush=True)
print("\nG4 verdicts (the 0.25 deg floor = 2.5 quantisation LSBs: below it a 'x2' is the 0.1 deg LSB)")
for (_, fk) in pairs[1:]:
    v = verdict[fk.name]
    print("  %-26s %-40s %s" % (fk.name, fk.short(), "PASS" if not v else "FAIL (%d): %s" % (len(v), "; ".join(v[:4]))))
    if verdict_raw[fk.name]:
        print("      as written (no floor) adds %d sub-0.25-deg hits, e.g. %s" % (len(verdict_raw[fk.name]),
                                                                              "; ".join(verdict_raw[fk.name][:3])))
# summary: worst p-p per speed over members/crowns, r1 vs each
print("\nworst angle p-p (deg) over members x crowns x seeds, by speed:")
for (_, fk) in pairs:
    s = "  %-26s" % fk.name
    for v in SPD:
        w = max(allres[(sd, fk.name, m, v, c)]["pp"] for sd in ("s3", "s11") for m in MEM for c in CROWN)
        s += " %4.1f:%4.2f" % (v, w)
    print(s)
json.dump({"|".join(map(str, k)): v for k, v in allres.items()}, open(sys.argv[1].replace("_spec.json", "_hunt.json"), "w"))
