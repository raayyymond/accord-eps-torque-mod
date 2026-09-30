# as8b_sens_robust.py -- is the 0.5-1 Hz |S| rise (A vs V294) robust to relay on/off, pipe 22/40/62 ms and sR gain 1/1.4?
import os, sys, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import advlib as A, as4_outer_lib as OL, v294_plant as VP
c294 = A.read_cells("V294"); cA = dict(c294, b=1106)
fam = VP.family()
f = np.linspace(0.5, 1.0, 51)
rat = []
for name, v, relay, pipe, srg in itertools.product(("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_hi", "ms_free", "light_b"),
                                                  (3.1, 5.0, 8.0, 11.9), (0.0, 1.0), (22.0, 40.0, 62.0), (1.0, 1.4)):
    a = fam[name].arrays_at(np.array([v]))
    p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=fam[name].tau_ms, w=3)
    sV = np.abs(1 / (1 + OL.outer_L(c294, p, v, f, relay, pipe, srg))).max()
    sA = np.abs(1 / (1 + OL.outer_L(cA, p, v, f, relay, pipe, srg))).max()
    rat.append((sA / sV, name, v, relay, pipe, srg, sV, sA))
r = np.array([q[0] for q in rat])
print("0.5-1 Hz max|S| ratio A/V294 over %d cases (9 members x 3.1-11.9 m/s x relay x pipe x sR gain): min %.3f median %.3f max %.3f ; share > 1: %.2f" % (
    len(r), r.min(), np.median(r), r.max(), np.mean(r > 1)))
for q in sorted(rat)[:3] + sorted(rat)[-5:]:
    print("   x%.3f  %-8s v%4.1f relay %.0f pipe %2.0f srg %.1f  |S| %.2f -> %.2f" % q)
