# -*- coding: utf-8 -*-
"""as8_sensitivity.py -- the outer-loop SENSITIVITY trade the design did not score: |S| (lat-accel error per plan) and
|T| (act per plan) in 0.3-1.2 Hz, for the trim dose b = 0 (V293), 567 (V294), 850 (point B), 1106 (A), every member x
speed (my outer_L, relay small-signal, and the relay describing function at 0.25/0.5/0.75 of its slope for the GM);
then the mode-B replay (harness sim, CRN) of V293 / V294 / A: lat-accel error by sub-band at 0-15 m/s."""
import os, sys, json
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import as4_outer_lib as OL
import v294_plant as VP
import v295_harness as H

c294 = A.read_cells("V294")
doses = {"V293(b0)": 0, "V294": 567, "B(b850)": 850, "A(b1106)": 1106}
cells = {k: dict(c294, b=v) for k, v in doses.items()}
fam = VP.family()
f = np.linspace(0.3, 1.2, 91)
print("max over 0.5-1.0 Hz of |S| and |T| (relay small-signal, pipe 22 ms), per member x speed:")
print("  member    v   | " + " | ".join("%-17s" % k for k in doses))
rise = []
for name in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_hi", "ms_free", "light_b"):
    for v in (3.1, 5.0, 8.0, 11.9, 17.0, 26.9):
        a = fam[name].arrays_at(np.array([v]))
        p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=fam[name].tau_ms, w=3)
        cols = []
        vals = {}
        for k, c in cells.items():
            L = OL.outer_L(c, p, v, f)
            S, T = np.abs(1 / (1 + L)), np.abs(L / (1 + L))
            m = (f >= 0.5) & (f <= 1.0)
            vals[k] = (S[m].max(), T[m].max())
            cols.append("S %.2f T %.2f" % vals[k])
        rise.append((name, v, vals))
        print("  %-8s %4.1f | %s" % (name, v, " | ".join("%-17s" % s for s in cols)))
print("\nratio A / V294 of max |S| in 0.5-1 Hz: min %.3f max %.3f ; V294 / V293: min %.3f max %.3f" % (
    min(r[2]["A(b1106)"][0] / r[2]["V294"][0] for r in rise), max(r[2]["A(b1106)"][0] / r[2]["V294"][0] for r in rise),
    min(r[2]["V294"][0] / r[2]["V293(b0)"][0] for r in rise), max(r[2]["V294"][0] / r[2]["V293(b0)"][0] for r in rise)))
print("  speeds where A/V294 > 1.05:", [(r[0], r[1], round(r[2]["A(b1106)"][0] / r[2]["V294"][0], 3)) for r in rise if r[2]["A(b1106)"][0] / r[2]["V294"][0] > 1.05])

# relay describing-function sweep for GM (A vs V294), light_b and nominal, all speeds
F = np.logspace(np.log10(0.02), np.log10(49.9), 3000)
print("\nrelay describing function: outer GM at relay gain fraction 0/0.25/0.5/0.75/1 of the small-signal slope, V294 -> A")
for name in ("nominal", "b_lo", "light_b"):
    for v in (3.1, 8.0, 17.0, 26.9):
        a = fam[name].arrays_at(np.array([v]))
        p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=fam[name].tau_ms, w=3)
        s = []
        for rl in (0.0, 0.25, 0.5, 0.75, 1.0):
            gv = A.margins(F, OL.outer_L(cells["V294"], p, v, F, relay=rl))["GM"]
            ga = A.margins(F, OL.outer_L(cells["A(b1106)"], p, v, F, relay=rl))["GM"]
            s.append("%.2f->%.2f" % (gv, ga))
        print("  %-8s %4.1f  %s" % (name, v, "  ".join(s)))

# mode-B replay: V293 / V294 / A, lat-accel error by sub-band
base = H.Cells.v294()
cl = {"V293(b0)": base.replace(fb_clamp=0, name="V293eq"), "V294": base, "A(b1106)": base.replace(fb_b=1106, name="A")}
hf = H.family()
MEM = ["nominal", "light_b", "b_lo", "J_hi2"]
chunks = H.route_chunks(); nC = len(chunks)


def bp(x, lo, hi):
    b, a = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
    return signal.filtfilt(b, a, x)


print("\nmode-B replay (CRN): plan-act lat-accel error rms in 0.5-1 Hz / 1-2.4 Hz, bands 0-5 / 5-10 / 10-15 m/s")
for dist in ("lp", "full"):
    R = {k: H.simulate([c], [hf[m] for m in MEM], chunks, H.SimOpts(mode="B", dist=dist, seed=0)) for k, c in cl.items()}
    for mi, m in enumerate(MEM):
        line = []
        for bn, lo, hi in H.BANDS[:3]:
            vals = {}
            for k in cl:
                acc = {"b": [], "c": []}
                for kk in range(nC):
                    j = mi * nC + kk
                    n = R[k]["lens"][j]
                    v = R[k]["v"][j, :n]
                    mk = (v >= lo) & (v < hi); mk[:100] = False; mk[-100:] = False
                    if mk.sum() < 100:
                        continue
                    e = R[k]["la_plan"][j, :n] - R[k]["la_act"][j, :n]
                    acc["b"].append(bp(e, 0.5, 1.0)[mk]); acc["c"].append(bp(e, 1.0, 2.4)[mk])
                vals[k] = tuple(np.sqrt(np.mean(np.concatenate(acc[q]) ** 2)) for q in ("b", "c"))
            line.append("%s: 0.5-1 %s | 1-2.4 %s" % (bn, "/".join("%.4f" % vals[k][0] for k in cl), "/".join("%.4f" % vals[k][1] for k in cl)))
        print("  %-4s %-8s (V293/V294/A)  %s" % (dist, m, "  ||  ".join(line)))
