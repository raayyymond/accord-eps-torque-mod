# -*- coding: utf-8 -*-
"""as6b_hunting.py -- robustness of the as6 finding "on light_b at 12 m/s, A raises on-centre hunting (0.5-5 Hz rate
x1.25-1.50, 0.59 Hz line, stick-slip jumps 0.5 -> 0.86 deg)": speeds 6..20 m/s, crowns 0/+15/-40 T, three planner-
wander seeds, x noise 1.93 and 0 (CRN within each pair), members light_b / nominal / b_lo / F_hi / light_b with the
friction halved and doubled (to find what drives it).  Same loop as as6 (ForkPort + limiter + MyLane + PlantBatch)."""
import os, sys, json, time
import numpy as np
from dataclasses import replace
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v295_harness as H
import importlib.util
spec = importlib.util.spec_from_file_location("as6", os.path.join(HERE, "as6_synth.py"))
# re-use as6's run() / bp / peakprom / stickslip without executing its scenarios: exec the definitions only
src = open(os.path.join(HERE, "as6_synth.py")).read().split("out = {}")[0]
ns = {"__file__": os.path.join(HERE, "as6_synth.py")}
exec(compile(src, "as6_defs", "exec"), ns)
run, bp, peakprom, stickslip = ns["run"], ns["bp"], ns["peakprom"], ns["stickslip"]

c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106
fam = H.family()
lb = fam["light_b"]
mem = {"light_b": lb, "nominal": fam["nominal"], "b_lo": fam["b_lo"], "F_hi": fam["F_hi"],
       "light_b_F05": replace(lb, name="light_b_F05", Fc=lb.Fc * 0.5, Fs=lb.Fs * 0.5),
       "light_b_F0": replace(lb, name="light_b_F0", Fc=lb.Fc * 0.0, Fs=lb.Fs * 0.0),
       "light_b_b2": replace(lb, name="light_b_b2", b=lb.b * 2.0)}
for m in mem.values():
    m.kappa = False
secs = 40
NF = secs * 100
bw, aw = signal.butter(1, 0.5 / 50.0)
rows = []
for seed in (3, 4, 5):
    rng = np.random.default_rng(seed)
    w = signal.lfilter(bw, aw, rng.normal(0, 1, NF)); w = w / w.std() * 0.03
    for mname in mem:
        for v in (6.0, 8.0, 10.0, 12.0, 14.0, 17.0, 20.0):
            for cr in (0.0, 15.0, -40.0):
                rows.append((seed, mname, v, cr, w))
B = len(rows)
V = np.array([[r[2]] * NF for r in rows], float)
LA = np.array([r[4] for r in rows])
members = [mem[r[1]] for r in rows]
crown = np.array([r[3] for r in rows])
res = {}
t0 = time.time()
for nz in (1.93, 0.0):
    for tag, c in (("V294", c294), ("A", cA)):
        res[(nz, tag)] = run(c, members, V, LA, crown, seed=21, x_noise=nz)
    print("noise %.2f simulated (%d rows) %.0f s" % (nz, B, time.time() - t0))
s = slice(500, NF)
table = {}
for nz in (1.93, 0.0):
    RV, RA = res[(nz, "V294")], res[(nz, "A")]
    for j, (seed, mname, v, cr, _) in enumerate(rows):
        a1, a2 = RV["ang"][j, s].std(), RA["ang"][j, s].std()
        r1 = np.sqrt(np.mean(bp(RV["rate"][j], 0.3, 2.0)[s] ** 2)); r2 = np.sqrt(np.mean(bp(RA["rate"][j], 0.3, 2.0)[s] ** 2))
        s1 = stickslip(RV["rate"][j, s], RV["ang"][j, s]); s2 = stickslip(RA["rate"][j, s], RA["ang"][j, s])
        table.setdefault((nz, mname, v), []).append((a2 / max(a1, 1e-9), r2 / max(r1, 1e-9), s1[0], s2[0], s1[1], s2[1], a1, a2))
print("\non-centre hold: A / V294, median [min, max] over 3 seeds x 3 crowns; stick-slip events summed, mean jump deg")
print("  noise member        v  | angle std ratio        | rate 0.3-2 Hz ratio    | events V294 -> A | jump V294 -> A | angle std V294 (deg)")
for (nz, mname, v), L in table.items():
    ar = [q[0] for q in L]; rr = [q[1] for q in L]
    e1, e2 = sum(q[2] for q in L), sum(q[3] for q in L)
    j1 = np.mean([q[4] for q in L if q[2]]) if e1 else 0; j2 = np.mean([q[5] for q in L if q[3]]) if e2 else 0
    flag = "  <-- A worse" if np.median(rr) > 1.10 or np.median(ar) > 1.10 else ""
    print("  %.2f  %-12s %4.0f | %.2f [%.2f, %.2f] | %.2f [%.2f, %.2f] | %3d -> %3d | %.2f -> %.2f | %.3f%s" % (
        nz, mname, v, np.median(ar), min(ar), max(ar), np.median(rr), min(rr), max(rr), e1, e2, j1, j2, np.median([q[6] for q in L]), flag))
json.dump({"%s|%s|%s" % k: v for k, v in table.items()}, open(os.path.join(HERE, "as6b_hunting.json"), "w"), default=float)
