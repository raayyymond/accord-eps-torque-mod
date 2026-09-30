# -*- coding: utf-8 -*-
"""as3c_consistent_all.py -- over ALL 3768 two-mass plants of as2 and all 1360 rigid cases: keep the ones on which the
FLOWN builds behave as flown (V282 stable with every 5-45 Hz mode zeta >= 0.010; V294 every 5-45 Hz mode >= 0.03), then
report A's worst damping ratios there, by delay; and the rigid-family margins restricted to the family proper."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import advlib as A
import v294_plant as VP
c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106; c282 = A.read_cells("V282")
fam = VP.family()
d = json.load(open(os.path.join(HERE, "as2_inner.json")))


def weakest(md, lo=5.0, hi=45.0):
    c = [m for m in md if lo < m[0] < hi]
    return min(c, key=lambda t: t[1]) if c else (np.nan, 1.0)


keep = []
n282u = 0
for t in d["twomass"]:
    if not (np.isfinite(t["zA"]) and np.isfinite(t["zV"])):
        continue
    a = fam[t["base"]].arrays_at(np.array([t["v"]]))
    p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=t["tau"], f2=t["f2"], zeta2=t["z2"], r2=t["r2"], w=3)
    m2, r2 = A.closed_poles(c282, p)
    if r2 >= 1 or weakest(m2)[1] < 0.010:
        n282u += 1
        continue
    mV, _ = A.closed_poles(c294, p)
    if weakest(mV)[1] < 0.03:
        continue
    mA, rA = A.closed_poles(cA, p)
    t = dict(t); t["wA"] = weakest(mA); t["wV"] = weakest(mV); t["w282"] = weakest(m2)
    keep.append(t)
print("two-mass: %d plants; V282 unstable or zeta < 0.010 on %d (excluded by the record); consistent %d" % (len(d["twomass"]), n282u, len(keep)))
for tau in (2, 6, 9, 18):
    s = [t for t in keep if t["tau"] == tau]
    if not s:
        print("  tau %2d: no consistent plant" % tau); continue
    w1 = min(s, key=lambda t: t["zA"] / t["z_open"]); w2 = min(s, key=lambda t: t["zA"] / t["zV"]); w3 = min(s, key=lambda t: t["wA"][1])
    print("  tau %2d: n %4d | worst flex zeta A/open %.3f (A %.4f open %.4f V294 %.4f; %s f2 %d z2 %.2f r2 %.1f v%.1f) | worst A/V294 %.3f | "
          "weakest A mode anywhere 5-45 Hz %.1f Hz zeta %.4f (V294 weakest there %.4f)" % (
              tau, len(s), w1["zA"] / w1["z_open"], w1["zA"], w1["z_open"], w1["zV"], w1["base"], w1["f2"], w1["z2"], w1["r2"], w1["v"],
              w2["zA"] / w2["zV"], w3["wA"][0], w3["wA"][1], w3["wV"][1]))
fin3 = [t for t in keep if t["zA"] < 0.8 * min(t["zV"], t["z_open"]) and t["zA"] < 0.10]
print("F-IN-3 on the record-consistent two-mass set: %d" % len(fin3))
print("overall consistent: min A/open %.3f, min A/V294 %.3f, min zeta_A (flex) %.4f" % (
    min(t["zA"] / t["z_open"] for t in keep), min(t["zA"] / t["zV"] for t in keep), min(t["zA"] for t in keep)))

# rigid: the family proper (Jx = bx = 1), every member x speed x delay; and the record filter for the corners
rows = d["rows"]
fp = [r for r in rows if "Jx1.00 bx1.00" in r["case"]]
for tau in (0, 2, 3, 4, 6, 9, 12, 18):
    s = [r for r in fp if (" tau%d " % tau) in r["case"]]
    wm = max(s, key=lambda r: r["A_Ms"]); wg = min(s, key=lambda r: r["A_GM"])
    print("rigid family proper, tau %2d: A Ms max %.3f (%s; V294 %.3f) | A GM min %.2f (%s; V294 %.2f)" % (
        tau, wm["A_Ms"], wm["case"], wm["V_Ms"], wg["A_GM"], wg["case"], wg["V_GM"]))
# corners with the record filter (V282 stable, weakest >= 0.010)
bad = []
for r in rows:
    parts = r["case"].split()
    name, v, tau, Jx, bx = parts[0], float(parts[1][1:]), int(parts[2][3:]), float(parts[3][2:]), float(parts[4][2:])
    a = fam[name].arrays_at(np.array([v]))
    p = dict(J=float(a["J"][0]) * Jx, b=float(a["b"][0]) * bx, k=float(a["k"][0]), tau_ms=tau, w=3)
    m2, r2 = A.closed_poles(c282, p)
    if r2 < 1 and weakest(m2)[1] >= 0.010:
        bad.append(r)
wm = max(bad, key=lambda r: r["A_Ms"]); wg = min(bad, key=lambda r: r["A_GM"]); wp = min(bad, key=lambda r: r["A_PM"])
print("rigid incl. J x0.5-2.5 / b corners, RECORD-CONSISTENT (%d of %d): A Ms max %.3f (%s, V294 %.3f) ; GM min %.2f (%s, V294 %.2f) ; PM min %.1f (%s)" % (
    len(bad), len(rows), wm["A_Ms"], wm["case"], wm["V_Ms"], wg["A_GM"], wg["case"], wg["V_GM"], wp["A_PM"], wp["case"]))
ld = []
for r in bad:
    for fA, zA in r["A_modes"]:
        zV = min([z for f, z in r["V_modes"] if abs(f - fA) <= 0.4 * fA], default=np.nan)
        if np.isfinite(zV) and zA < zV - 1e-3:
            ld.append((r["case"], fA, zA, zV))
if ld:
    w = min(ld, key=lambda t: t[2] / t[3])
    print("rigid record-consistent: %d modes less damped with A than V294; worst %s %.2f Hz zeta A %.4f V294 %.4f (x%.3f); min zeta_A among them %.4f" % (
        len(ld), w[0], w[1], w[2], w[3], w[2] / w[3], min(t[2] for t in ld)))
