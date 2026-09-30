# as3d_absolute.py -- over the record-consistent two-mass set (as3c's filter, recomputed): the absolute damping of every
# mode A makes < 0.8 x min(V294, open), the largest absolute zeta loss, and the designer's r2 <= 0.5 / tau <= 9 sub-scan.
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import advlib as A, v294_plant as VP
c282 = A.read_cells("V282"); c294 = A.read_cells("V294")
fam = VP.family()
d = json.load(open(os.path.join(HERE, "as2_inner.json")))
def weakest(md, lo=5.0, hi=45.0):
    c = [m for m in md if lo < m[0] < hi]
    return min(c, key=lambda t: t[1]) if c else (np.nan, 1.0)
keep = []
for t in d["twomass"]:
    if not (np.isfinite(t["zA"]) and np.isfinite(t["zV"])): continue
    a = fam[t["base"]].arrays_at(np.array([t["v"]]))
    p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=t["tau"], f2=t["f2"], zeta2=t["z2"], r2=t["r2"], w=3)
    m2, r2 = A.closed_poles(c282, p)
    if r2 >= 1 or weakest(m2)[1] < 0.010: continue
    mV, _ = A.closed_poles(c294, p)
    if weakest(mV)[1] < 0.03: continue
    keep.append(t)
bad = [t for t in keep if t["zA"] < 0.8 * min(t["zV"], t["z_open"])]
print("record-consistent two-mass plants: %d ; A < 0.8 x min(V294, open) on %d ; min zeta_A among those %.4f" % (len(keep), len(bad), min([t["zA"] for t in bad], default=np.nan)))
dz = max(keep, key=lambda t: t["zV"] - t["zA"])
print("largest absolute zeta loss A vs V294: %.4f (%s f2 %d z2 %.2f r2 %.1f tau %d v %.1f: open %.4f V294 %.4f A %.4f)" % (
    dz["zV"] - dz["zA"], dz["base"], dz["f2"], dz["z2"], dz["r2"], dz["tau"], dz["v"], dz["z_open"], dz["zV"], dz["zA"]))
lo = [t for t in keep if t["z_open"] < 0.10]
w = min(lo, key=lambda t: t["zA"] / t["z_open"])
print("modes with zeta_open < 0.10 (the grinding class): n %d ; worst A/open %.3f (%s f2 %d z2 %.2f r2 %.1f tau %d v %.1f: open %.4f V294 %.4f A %.4f) ; min zeta_A %.4f" % (
    len(lo), w["zA"] / w["z_open"], w["base"], w["f2"], w["z2"], w["r2"], w["tau"], w["v"], w["z_open"], w["zV"], w["zA"], min(t["zA"] for t in lo)))
sub = [t for t in d["twomass"] if t["r2"] <= 0.5 and t["tau"] <= 9 and np.isfinite(t["zA"]) and np.isfinite(t["zV"])]
w = min(sub, key=lambda t: t["zA"] / min(t["zV"], t["z_open"]))
print("designer-like sub-scan (r2 <= 0.5, tau <= 9, no record filter): worst A/min %.3f (%s f2 %d z2 %.2f r2 %.1f tau %d v %.1f: open %.4f V294 %.4f A %.4f)" % (
    w["zA"] / min(w["zV"], w["z_open"]), w["base"], w["f2"], w["z2"], w["r2"], w["tau"], w["v"], w["z_open"], w["zV"], w["zA"]))
