# -*- coding: utf-8 -*-
"""as3b_record_filter.py -- every plant on which A fired F-IN-2 (rigid) or F-IN-3 (two-mass) in as2, and the 2 F-HF-1
plants of as3: what does the SAME plant predict for the FLOWN builds V282 (sum operand, Kd 128; flew: ground at 20 Hz,
zeta 0.016 [0.013, 0.022], stable) and V294 (flew clean)?  A plant on which V282 would have been UNSTABLE, or would have
rung at a zeta < 0.010, or on which V294 would itself have rung (zeta < 0.03 anywhere 5-40 Hz), is CONTRADICTED by the
on-car record.  Reports the surviving (record-consistent) hits."""
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


def verdict(p):
    m2, r2 = A.closed_poles(c282, p)
    mV, rV = A.closed_poles(c294, p)
    mA, rA = A.closed_poles(cA, p)
    w2, wV, wA = weakest(m2), weakest(mV), weakest(mA)
    ok282 = (r2 < 1.0) and (w2[1] >= 0.010)
    okV = (rV < 1.0) and (wV[1] >= 0.03)
    return dict(rho282=r2, w282=w2, w294=wV, wA=wA, consistent=bool(ok282 and okV))


# ---- F-IN-3 two-mass hits
tm = d["twomass"]
ratio = lambda t: t["zA"] / min(t["zV"], t["z_open"])
hits = [t for t in tm if np.isfinite(t["zA"]) and np.isfinite(t["zV"]) and ratio(t) < 0.8 and t["zA"] < 0.10]
print("F-IN-3 two-mass hits from as2: %d" % len(hits))
surv = []
by_tau = {}
for t in hits:
    a = fam[t["base"]].arrays_at(np.array([t["v"]]))
    p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=t["tau"], f2=t["f2"], zeta2=t["z2"], r2=t["r2"], w=3)
    vd = verdict(p)
    by_tau.setdefault(t["tau"], [0, 0])[0] += 1
    if vd["consistent"]:
        by_tau[t["tau"]][1] += 1
        surv.append((t, vd))
for tau, (n, k) in sorted(by_tau.items()):
    print("  tau %2d: %d hits, %d consistent with the V282 + V294 flights" % (tau, n, k))
# show what V282 does on the hits (the reason they are excluded)
print("  examples (V282 rho / weakest mode; V294 weakest; A weakest):")
for t in sorted(hits, key=ratio)[:12]:
    a = fam[t["base"]].arrays_at(np.array([t["v"]]))
    p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=t["tau"], f2=t["f2"], zeta2=t["z2"], r2=t["r2"], w=3)
    vd = verdict(p)
    print("   %-8s v%4.1f f2 %2d z2 %.2f r2 %.1f tau %2d | V282 rho %.4f weakest %.1f Hz z %.4f | V294 %.1f/%.4f | A %.1f/%.4f | consistent %s" % (
        t["base"], t["v"], t["f2"], t["z2"], t["r2"], t["tau"], vd["rho282"], vd["w282"][0], vd["w282"][1], vd["w294"][0], vd["w294"][1],
        vd["wA"][0], vd["wA"][1], vd["consistent"]))
print("  SURVIVING (record-consistent) F-IN-3 hits: %d" % len(surv))
for t, vd in surv[:20]:
    print("   %-8s v%4.1f f2 %2d z2 %.2f r2 %.1f tau %2d | open %.4f V294 %.4f A %.4f | V282 weakest %.1f/%.4f" % (
        t["base"], t["v"], t["f2"], t["z2"], t["r2"], t["tau"], t["z_open"], t["zV"], t["zA"], vd["w282"][0], vd["w282"][1]))

# ---- F-IN-2 rigid hits
print("\nF-IN-2 rigid hits from as2:")
rows = d["rows"]
r2hits = [r for r in rows if (r["V_GM"] >= 3 and r["A_GM"] < 2) or r["A_PM"] < 45 or r["A_Ms"] > 2.0]
for r in r2hits:
    parts = r["case"].split()
    name, v, tau, Jx, bx = parts[0], float(parts[1][1:]), int(parts[2][3:]), float(parts[3][2:]), float(parts[4][2:])
    a = fam[name].arrays_at(np.array([v]))
    p = dict(J=float(a["J"][0]) * Jx, b=float(a["b"][0]) * bx, k=float(a["k"][0]), tau_ms=tau, w=3)
    vd = verdict(p)
    print("   %-38s A GM %.2f Ms %.2f | V282 rho %.4f weakest %.1f/%.4f | V294 weakest %.1f/%.4f | consistent %s" % (
        r["case"], r["A_GM"], r["A_Ms"], vd["rho282"], vd["w282"][0], vd["w282"][1], vd["w294"][0], vd["w294"][1], vd["consistent"]))

# ---- the smallest transport delay at which V282 goes unstable on the RIGID identified family (what the record bounds)
print("\nV282 on the rigid family by delay (it FLEW: stable, 20 Hz ring zeta ~0.016): rho and weakest 5-45 Hz mode")
for name in ("nominal", "light_b", "J_lo", "J_hi", "b_lo"):
    for v in (3.1, 11.9):
        line = []
        for tau in (0, 2, 3, 4, 6, 9, 12, 18):
            a = fam[name].arrays_at(np.array([v]))
            p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=tau, w=3)
            m2, r2 = A.closed_poles(c282, p)
            w2 = weakest(m2)
            line.append("t%d:%s%.1f/%.3f" % (tau, "U " if r2 >= 1 else "", w2[0], w2[1]))
        print("   %-8s v%4.1f  %s" % (name, v, "  ".join(line)))
