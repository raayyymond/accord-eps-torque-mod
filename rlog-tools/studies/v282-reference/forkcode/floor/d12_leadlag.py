# -*- coding: utf-8 -*-
"""d12 -- is there a CAUSAL setpoint filter that survives the instrument correction at low shake?

A true lead at unity magnitude is NON-CAUSAL (Bode gain-phase: a causal stable all-pass has negative
phase).  Every causal lead buys its phase with high-frequency GAIN.  So scan the causal lead-lag
    W(s) = (1 + s T1) / (1 + s T2),   T1 > T2,   HF gain T1/T2
over a grid, and require:
    (i)  it improves the INSTRUMENT-CORRECTED metric (else it is buying back the 102 ms), and
    (ii) the command's 1.8-3.5 Hz RMS ratio stays <= a stated ceiling.
Anything that fails (i) is an instrument artefact; anything that fails (ii) is paid in shake.
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
from d8_refladder import Ref, T64, JREF, JFLOWN  # noqa

R = Ref(T64, corrected=False)
Rc = Ref(T64, corrected=True)
f = R.f
rows = []
for T1 in np.arange(0.02, 0.51, 0.01):
    for T2 in np.arange(0.005, T1, 0.005):
        s = 2j * np.pi * f
        W = (1 + s * T1) / (1 + s * T2)
        J, sh = R.apply(W)
        Jc, _ = Rc.apply(W)
        rows.append((T1, T2, J, Jc, sh, T1 / T2))
rows = np.array(rows)
print("=" * 100)
print("CAUSAL LEAD-LAG ON THE SETPOINT.  best J at each command-shake ceiling,")
print("with the instrument-corrected J shown beside it (it must also fall, else the lever is the lag).")
print(f"{'shake ceil':>11s} {'T1 s':>6s} {'T2 s':>6s} {'HF gain':>8s} {'J':>8s} {'closure':>8s} "
      f"{'J corr':>8s} {'corr vs 0.9994':>15s}")
for ceil in (1.00, 1.02, 1.05, 1.10, 1.20, 1.40, 1.70, 2.00):
    ok = rows[rows[:, 4] <= ceil]
    if not len(ok):
        continue
    b = ok[int(np.argmin(ok[:, 2]))]
    print(f"{ceil:11.2f} {b[0]:6.2f} {b[1]:6.3f} {b[5]:8.2f} {b[2]:8.4f} "
          f"{(JFLOWN-b[2])/(JFLOWN-JREF)*100:7.1f}% {b[3]:8.4f} {(b[3]-0.9994)/0.9994*100:+14.1f}%")
print()
print("NOW RANK ON THE INSTRUMENT-CORRECTED METRIC INSTEAD (the honest objective):")
print(f"{'shake ceil':>11s} {'T1 s':>6s} {'T2 s':>6s} {'HF gain':>8s} {'J corr':>8s} "
      f"{'corr gain':>10s} {'J raw':>8s} {'raw closure':>12s}")
best = None
for ceil in (1.00, 1.02, 1.05, 1.10, 1.20, 1.40):
    ok = rows[rows[:, 4] <= ceil]
    if not len(ok):
        continue
    b = ok[int(np.argmin(ok[:, 3]))]
    print(f"{ceil:11.2f} {b[0]:6.2f} {b[1]:6.3f} {b[5]:8.2f} {b[3]:8.4f} "
          f"{(0.9994-b[3])/0.9994*100:9.1f}% {b[2]:8.4f} {(JFLOWN-b[2])/(JFLOWN-JREF)*100:11.1f}%")
    if ceil == 1.05:
        best = b
json.dump(dict(best_shake105=list(map(float, best))), open(OUT / "d12.json", "w"), indent=1)
print("\nwrote out/d12.json")
