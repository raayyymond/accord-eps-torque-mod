# -*- coding: utf-8 -*-
"""a14 -- record-consistency filter for the (a) stress cases: V282 flew for months (a 20 Hz ring at zeta ~0.016, never a
divergence), so a stress member on which MY V282 linear lane is UNSTABLE (rho >= 1) is excluded by the on-car record.
Re-rank the candidate/V294 flexible-pole damping ratio over the record-consistent stress cases only."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lin as AL
import v294_plant as VP
L282 = dict(fb_a=923, fb_b=1560, fb_op="sum", kp=248.0, kd=128.0, lag_a=992, lag_b=507, gain=5346)
R = json.load(open(os.path.join(HERE, "a2_inner.json")))
fam = VP.family()
out = open(os.path.join(HERE, "a14_record_filter_out.txt"), "w")
def P(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n")
def fl(osc):
    c = [(f, z) for f, z in osc if 8 < f < 40]
    return min(c, key=lambda t: t[1]) if c else (float("nan"), float("nan"))
rows = []
for r in R:
    if r["top"] == "rigid":
        continue
    Ac, Bc, cs, _ = AL.plant_cont(r["J"], r["b"], r["k"], r["top"], r["f2"], r["z2"], r["r2"])
    _, rho = AL.osc_poles(AL.closed_loop_A(Ac, Bc, cs, L282, tau=r["tau"]))
    o, a, c = fl(r["open_osc"]), fl(r["V294_osc"]), fl(r["cand_osc"])
    trk = [t for t in r["tracked"] if t[1] < 0.3]
    worst_trk = min([t[3] / t[1] for t in trk], default=float("nan"))
    rows.append(dict(name=r["name"], v=r["v"], tau=r["tau"], v282_rho=rho, open=o, V294=a, cand=c,
                     ratio=c[1] / a[1] if a[1] == a[1] else float("nan"), trk_ratio=worst_trk))
cons = [x for x in rows if x["v282_rho"] < 1.0]
P("stress cases: %d ; record-consistent (V282 linear lane stable): %d ; excluded (V282 unstable): %d" % (len(rows), len(cons), len(rows) - len(cons)))
for lab, S in (("ALL", rows), ("RECORD-CONSISTENT", cons)):
    rr = sorted([x for x in S if x["ratio"] == x["ratio"]], key=lambda x: x["ratio"])
    tt = sorted([x for x in S if x["trk_ratio"] == x["trk_ratio"]], key=lambda x: x["trk_ratio"])
    P("\n%s: min flex-pole zeta ratio cand/V294 %.3f ; min tracked-pole (zeta<0.3) ratio %.3f ; cases < 0.9 (tracked): %d" % (
        lab, rr[0]["ratio"], tt[0]["trk_ratio"], sum(x["trk_ratio"] < 0.9 for x in tt)))
    for x in rr[:6]:
        P("   %-28s v %4.1f tau %d V282 rho %.4f | open %.2f/%.4f V294 %.2f/%.4f cand %.2f/%.4f ratio %.3f" % (
            x["name"], x["v"], x["tau"], x["v282_rho"], *x["open"], *x["V294"], *x["cand"], x["ratio"]))
    lo = [x for x in S if x["V294"][1] < 0.06]
    if lo:
        P("   flex poles with V294 zeta < 0.06: %d ; min cand zeta %.4f ; max de-damping cand vs open %.4f ; cand vs V294 %.4f" % (
            len(lo), min(x["cand"][1] for x in lo), min(x["cand"][1] - x["open"][1] for x in lo), min(x["cand"][1] - x["V294"][1] for x in lo)))
out.close()
