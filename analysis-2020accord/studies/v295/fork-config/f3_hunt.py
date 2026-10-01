# -*- coding: utf-8 -*-
"""f3: the on-centre HUNT test (gate G4), time domain: Karnopp plant + the fork port (relay + integrator) + the
byte-exact lane + the Honda limiter + a 22 ms pipe, zero planner demand, constant crown torque c0 = crown x Fs.
First: does the instrument discriminate?  r1 on V294 and V295, plus deliberate extremes (a hot relay, a hot Ki, a hot
KiHigh, LAF 9) as positive controls -- a relay of F 0.05 (x4.5 r1) should hunt if anything does."""
import sys, json, time
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

c294, c295 = H.Cells.v294(), F.cells_v295()
MEM = ["nominal", "b_lo", "F_hi", "J_hi", "light_b"]
SPD = (3.1, 4.0, 5.0, 8.0, 12.0, 17.0, 22.0, 27.0)
CROWN = (0.0, 0.6, 1.5)
pairs = [(c294, F.Fork("V294_r1")), (c295, F.Fork("r1")),
         (c295, F.Fork("F0.05", fric=0.05)), (c295, F.Fork("F0", fric=0.0)),
         (c295, F.Fork("Ki1.2", ki=1.2)), (c295, F.Fork("KiH3", ki_high=3.0)),
         (c295, F.Fork("LAF9", laf=9.0))]
t0 = time.time()
res = F.hunt(pairs, MEM, SPD, CROWN, secs=60.0)
print("hunt: %d lanes, %.1f s" % (len(res), time.time() - t0))
for crown in CROWN:
    print("\n=== crown c0 = %.1f x Fs  -- angle p-p (deg) over the last 30 s / rate rms deg/s / peak Hz" % crown)
    for m in MEM:
        print("  %-8s" % m)
        for _, fk in pairs:
            s = "    %-8s" % fk.name
            for v in SPD:
                r = res[(fk.name, m, v, crown)]
                s += " %4.1f:%5.2f/%5.2f/%4.2f%s" % (v, r["pp"], r["rate_rms"], r["f_pk"], "!" if r["diverged"] else "")
            print(s)
json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open("out/f3_hunt.json", "w"), indent=0)
