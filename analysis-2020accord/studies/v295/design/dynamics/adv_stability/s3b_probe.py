import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import advlin as AL, v295_harness as H
from s3_hf_stress import LANES, MODES
fam = H.family()
out = []
for sense, tau in (("motor", 6), ("wheel", 9), ("motor", 2)):
    p = fam["nominal"].at(12.0)
    pl = AL.Plant(p.J, p.b, p.k, 20.0, 0.05, 0.8, sense)
    for k in ("OPEN", "V294", "A1017", "V282"):
        md, rho = AL.modes_of(AL.inner_A(LANES[k], pl, tau=tau))
        out.append("m20z05r8 %s tau %d %-5s rho %.5f modes %s" % (sense, tau, k, rho, [(round(f, 2), round(z, 4)) for f, z in md if 0.1 < f < 60]))
# robust ratio summary over all cells: take, for each lane, the least-damped pair in 5-45 Hz
import itertools
rat = []
for (f2, z2, r2, name), sense, v, tau in itertools.product(MODES, ("motor", "wheel"), (5.0, 12.0, 25.0), (2, 3, 6, 9, 12)):
    p = fam["nominal"].at(v)
    pl = AL.Plant(p.J, p.b, p.k, f2, z2, r2, sense)
    zz = {}
    for k in ("V294", "A1017"):
        md, rho = AL.modes_of(AL.inner_A(LANES[k], pl, tau=tau))
        c = [z for f, z in md if 5.0 <= f < 45.0]
        zz[k] = (min(c) if c else np.nan, rho)
    rat.append((name, sense, v, tau, zz["V294"][0], zz["A1017"][0], zz["V294"][1], zz["A1017"][1]))
r = np.array([a[5] / a[4] for a in rat if np.isfinite(a[4]) and np.isfinite(a[5])])
out.append("least-damped pair 5-45 Hz, A1017/V294 over %d cells: min %.4f p1 %.4f median %.4f max %.4f ; A1017 unstable cells %d ; V294 unstable %d" % (
    len(r), r.min(), np.percentile(r, 1), np.median(r), r.max(), sum(a[7] >= 1 for a in rat), sum(a[6] >= 1 for a in rat)))
worst = sorted([a for a in rat if np.isfinite(a[4]) and np.isfinite(a[5])], key=lambda a: a[5] / a[4])[:8]
for a in worst:
    out.append("   worst %s %s v %.0f tau %d  zeta V294 %.4f A1017 %.4f" % a[:6])
open(os.path.join(HERE, "s3b_probe_out.txt"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
