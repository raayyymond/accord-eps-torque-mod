# -*- coding: utf-8 -*-
"""a3 -- (b) the 20 Hz question AGAINST THE ON-CAR RECORD.
Record (memory): V282's LKAS rate loop de-damped a ~20 Hz object to zeta ~0.016 (creep grind, 17-21 Hz); with the loop
OPEN there is no 18-22 Hz object, zeta_open >= 0.05; V294 flies clean (ring presence 0.5 %).
Method: (1) V282's linear lane on the RIGID family -- does the loop alone make a 15-25 Hz light pole?  (2) calibrate
two-mass stress members (three topologies x f2 x r2 x zeta2 x delay x base member x speed) so that V282 gives a 15-25 Hz
pole with zeta in [0.008, 0.03] while the open plant's flexible pole has zeta >= 0.05 -- the members CONSISTENT with the
record -- then put V294 and the candidate on exactly those members.  Plus the lane's gain AND phase at 13/16/20/25 Hz."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lin as AL  # noqa: E402
import v294_plant as VP  # noqa: E402

L294 = dict(fb_a=1011, fb_b=567, fb_op="diff", kp=960.0, kd=0.0, lag_a=992, lag_b=507, gain=5346)
LC = dict(L294, kp=1248.0)
L282 = dict(fb_a=923, fb_b=1560, fb_op="sum", kp=248.0, kd=128.0, lag_a=992, lag_b=507, gain=5346)
out = open(os.path.join(HERE, "a3_20hz_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


# ---- B3: gain and phase of the three lanes (T per x-count incl. output lag; phase of the OPPOSING torque per wheel rate,
# 0 = pure damping, -90 = spring-like, beyond -90 = anti-damping) with the rate former and a transport delay
P("B3  controller at HF: |P/x| (record metric) and the opposing-torque phase per wheel rate incl. 3 ms former + ZOH + tau")
f = np.array([13.0, 16.0, 20.0, 25.0])
zi = np.exp(-2j * np.pi * f * AL.DT)
RF = (1 - zi ** 3) / (3 * AL.DT)
s = 2j * np.pi * f
zoh = np.exp(-1j * np.pi * f * AL.DT) * np.sinc(f * AL.DT)
for nm, ln in (("V282", L282), ("V294", L294), ("cand", LC)):
    CT = AL.lane_CT(ln, f)
    for tau in (0, 2, 6, 9):
        opp = -8.0 * CT * RF / s * zoh * np.exp(-s * tau * AL.DT)          # T opposing per deg/s (census convention)
        P("  %-5s tau %d ms: |T/omega| %s  phase %s deg  (damping component %s T per deg/s)" % (
            nm, tau, np.round(np.abs(opp), 3), np.round(np.degrees(np.angle(opp)), 1), np.round(opp.real, 3)))

fam = VP.family()
# ---- (1) V282 on the rigid family
P("\n(1) V282 lane on RIGID members: closed-loop pairs 8-40 Hz (f, zeta)")
for nm in ("nominal", "b_lo", "J_lo", "J_hi", "light_b"):
    for v in (3.1, 8.0, 11.9):
        p = fam[nm].at(v)
        Ac, Bc, cs, _ = AL.plant_cont(p.J, p.b, p.k)
        for tau in (2, 6):
            osc, rho = AL.osc_poles(AL.closed_loop_A(Ac, Bc, cs, L282, tau=tau))
            P("  %-8s v %4.1f tau %d: rho %.4f  %s" % (nm, v, tau, rho, [(round(a, 2), round(b, 3)) for a, b in osc if 3 < a < 60]))

# ---- (2) anchored stress members
P("\n(2) stress members CONSISTENT with the record (V282 flex pole 15-25 Hz, zeta 0.008-0.03; open flex zeta >= 0.05)")
rows = []
for base in ("nominal", "light_b", "J_lo", "b_lo"):
    for v in (3.1, 8.0):
        p = fam[base].at(v)
        for top in ("T1", "T2", "T3"):
            for f2 in (16.0, 18.0, 20.0, 22.0, 24.0):
                for r2 in (0.1, 0.2, 0.3, 0.5, 0.7):
                    for z2 in (0.02, 0.03, 0.05, 0.08, 0.12, 0.2):
                        Ac, Bc, cs, _ = AL.plant_cont(p.J, p.b, p.k, top, f2, z2, r2)
                        for tau in (0, 2, 4, 6, 9):
                            oo, _ = AL.osc_poles(AL.closed_loop_A(Ac, Bc, cs, L294, tau=tau, lane_on=False))
                            fo = [(a, b) for a, b in oo if 12 < a < 30]
                            if not fo:
                                continue
                            fo = min(fo, key=lambda t: t[1])
                            if fo[1] < 0.05:
                                continue
                            o2, r282 = AL.osc_poles(AL.closed_loop_A(Ac, Bc, cs, L282, tau=tau))
                            c282 = [(a, b) for a, b in o2 if 15 < a < 25]
                            if not c282:
                                continue
                            c282 = min(c282, key=lambda t: t[1])
                            if not (0.008 <= c282[1] <= 0.03) or r282 >= 1:
                                continue
                            res = dict(base=base, v=v, top=top, f2=f2, r2=r2, z2=z2, tau=tau, open=fo, v282=c282)
                            for tag, ln in (("V294", L294), ("cand", LC)):
                                o3, rh = AL.osc_poles(AL.closed_loop_A(Ac, Bc, cs, ln, tau=tau))
                                c3 = [(a, b) for a, b in o3 if 12 < a < 30]
                                res[tag] = min(c3, key=lambda t: abs(t[0] - fo[0])) if c3 else (np.nan, np.nan)
                                res[tag + "_rho"] = rh
                            rows.append(res)
P("  consistent members found: %d" % len(rows))
if rows:
    d294 = np.array([r["V294"][1] - r["open"][1] for r in rows])
    dc = np.array([r["cand"][1] - r["open"][1] for r in rows])
    ratio = np.array([r["cand"][1] / r["V294"][1] for r in rows])
    P("  zeta shift from open:  V294 min %+.4f median %+.4f max %+.4f ;  cand min %+.4f median %+.4f max %+.4f" % (
        d294.min(), np.median(d294), d294.max(), dc.min(), np.median(dc), dc.max()))
    P("  cand zeta / V294 zeta: min %.4f median %.4f ; cases with cand below open by > 0.005: %d ; cand shift > 1.5x V294's (de-damping): %d" % (
        ratio.min(), np.median(ratio), int(np.sum(dc < -0.005)),
        int(np.sum((dc < 0) & (np.abs(dc) > 1.5 * np.abs(d294) + 1e-9)))))
    P("  min closed-loop flex zeta: V294 %.4f cand %.4f (open min %.4f) ; any unstable: %d" % (
        min(r["V294"][1] for r in rows), min(r["cand"][1] for r in rows), min(r["open"][1] for r in rows),
        sum(r["cand_rho"] >= 1 for r in rows)))
    by = {}
    for r in rows:
        by.setdefault((r["top"], r["tau"]), []).append(r)
    for k in sorted(by):
        rs = by[k]
        P("   %s tau %d: n %3d  open zeta %.3f-%.3f ; V282 %.3f-%.3f ; V294 shift %+.4f..%+.4f ; cand shift %+.4f..%+.4f" % (
            k[0], k[1], len(rs), min(r["open"][1] for r in rs), max(r["open"][1] for r in rs),
            min(r["v282"][1] for r in rs), max(r["v282"][1] for r in rs),
            min(r["V294"][1] - r["open"][1] for r in rs), max(r["V294"][1] - r["open"][1] for r in rs),
            min(r["cand"][1] - r["open"][1] for r in rs), max(r["cand"][1] - r["open"][1] for r in rs)))
    worst = sorted(rows, key=lambda r: r["cand"][1] - r["open"][1])[:8]
    P("  the 8 most de-damped by the candidate:")
    for r in worst:
        P("   ", {k: (tuple(round(x, 4) for x in v) if isinstance(v, tuple) else v) for k, v in r.items()})
json.dump(rows, open(os.path.join(HERE, "a3_20hz.json"), "w"), default=float)
out.close()
