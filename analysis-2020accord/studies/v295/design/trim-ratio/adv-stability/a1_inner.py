# -*- coding: utf-8 -*-
"""a1_inner.py -- (a) the inner acceleration-trim loop on every family member, stress member, delay x1..x3, J x0.5..2.5,
b corners, rate-former window 1..5 ms: stability, Ms, GM, PM and pole-by-pole damping, V294 vs b964.  MY closed loop
(exact ZOH plant) + MY return ratio.  Also R5: the designer's stress-zeta table and worst Ms at delay x1.5.
Output: a1_inner_out.txt, a1_inner.json"""
import json
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a1_inner_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
V293 = A.read_cells("V293")
fam = VP.family()
nom = fam["nominal"]
mem = dict(fam)
mem["J_0.3"] = replace(nom, name="J_0.3", J=np.full(5, 0.3))
mem["mode13"] = replace(nom.with_mode20(13.0, 0.1, 0.2), name="mode13")
mem["mode20"] = replace(nom.with_mode20(20.0, 0.05, 0.2), name="mode20")
mem["mode20_lo"] = replace(nom.with_mode20(20.0, 0.02, 0.5), name="mode20_lo")
mem["tau9"] = replace(nom, name="tau9", tau_ms=9)
# my extra stress corners (not refitted -- stress only)
mem["J_x0.5"] = replace(nom, name="J_x0.5", J=nom.J * 0.5)
mem["J_x2.5"] = replace(nom, name="J_x2.5", J=nom.J * 2.5)
mem["b_x0.5"] = replace(nom, name="b_x0.5", b=nom.b * 0.5)
mem["b_x0.5_Jx2.5"] = replace(nom, name="b_x0.5_Jx2.5", b=nom.b * 0.5, J=nom.J * 2.5)
mem["lb_mode20"] = replace(fam["light_b"].with_mode20(20.0, 0.05, 0.2), name="lb_mode20")
mem["lb_mode20_lo"] = replace(fam["light_b"].with_mode20(20.0, 0.02, 0.5), name="lb_mode20_lo")
mem["mode16_lo"] = replace(nom.with_mode20(16.5, 0.02, 0.5), name="mode16_lo")
mem["mode13_lo"] = replace(nom.with_mode20(13.0, 0.03, 0.5), name="mode13_lo")
speeds = (3.1, 5.0, 8.0, 12.0, 17.0, 25.0, 26.9)
f = np.concatenate([np.linspace(0.02, 1, 200), np.linspace(1.0, 60, 3000), np.linspace(60, 499, 800)])


def analyse(p, c, tau, w=3):
    Acl = A.closed_loop_A(p, c, tau=tau, w=w)
    rho, modes = A.modes_of(Acl)
    L = A.inner_L(p, c, f, tau=tau, w=w)
    mg = A.margins(f, L)
    return dict(rho=rho, modes=modes, **mg, L13=float(np.mean(np.abs(L[(f >= 1) & (f <= 3)]))))


def match(m1, m2, fmax=45.0):
    """pair each oscillatory mode of m1 (V294) with the nearest of m2 (cand) in (f, zeta); return list of
    (f1, z1, f2, z2) for modes below fmax with zeta < 0.4"""
    res = []
    for f1, z1 in m1:
        if f1 > fmax or z1 > 0.4:
            continue
        j = min(range(len(m2)), key=lambda k: abs(m2[k][0] - f1) / max(f1, 0.1) + abs(m2[k][1] - z1))
        res.append((f1, z1, m2[j][0], m2[j][1]))
    return res


rows = []
worst = dict(Ms15=(0, None), dz=(1, None), GM=(1e9, None))
P("member v tau w | V294: rho Ms GM PM |L|1-3 | b964: rho Ms GM PM |L|1-3 | least-damped osc pair (<45 Hz, zeta<.4): V294 -> b964")
for name, mb in mem.items():
    for v in speeds:
        p0 = mb.at(v)
        for mult in (1.0, 1.5, 2.0, 3.0):
            tau = int(round(p0.tau_ms * mult)) if p0.tau_ms > 0 else int(round(2 * (mult - 1)))
            for w in ((3,) if mult != 1.5 else (1, 3, 5)):
                r0 = analyse(p0, V294, tau, w)
                r1 = analyse(p0, B964, tau, w)
                pairs = match(r0["modes"], r1["modes"])
                dz = min([z2 - z1 for _, z1, _, z2 in pairs], default=0.0)
                lp0 = min(pairs, key=lambda t: t[1]) if pairs else None
                rows.append(dict(member=name, v=v, tau=tau, w=w, mult=mult, V294={k: r0[k] for k in ("rho", "Ms", "GM", "PM", "L13", "f_Ms")},
                                 b964={k: r1[k] for k in ("rho", "Ms", "GM", "PM", "L13", "f_Ms")}, pairs=pairs, dz_min=dz))
                flag = ""
                if r1["rho"] >= 1 and r0["rho"] < 1:
                    flag += " !!UNSTABLE-ONLY-ON-b964"
                if r1["Ms"] > 2.0 and r0["Ms"] <= 1.5:
                    flag += " !!Ms>2"
                bad = [(a, b, c_, d) for a, b, c_, d in pairs if d < 0.15 and d < b - 0.02]
                if bad:
                    flag += " !!DE-DAMPED %s" % [(round(a, 2), round(b, 3), round(c_, 2), round(d, 3)) for a, b, c_, d in bad]
                if mult == 1.5 and w == 3 and r1["Ms"] > worst["Ms15"][0]:
                    worst["Ms15"] = (r1["Ms"], (name, v, tau, r0["Ms"]))
                if dz < worst["dz"][0]:
                    worst["dz"] = (dz, (name, v, tau, w, pairs))
                if r1["GM"] < worst["GM"][0]:
                    worst["GM"] = (r1["GM"], (name, v, tau, w, r0["GM"]))
                if (mult in (1.0, 1.5, 3.0) and w == 3) or flag:
                    P("%-13s %5.1f %2d %d | %.5f %.3f %6.1f %5.1f %.3f | %.5f %.3f %6.1f %5.1f %.3f | %s -> %s%s" % (
                        name, v, tau, w, r0["rho"], r0["Ms"], r0["GM"], r0["PM"] if np.isfinite(r0["PM"]) else -1, r0["L13"],
                        r1["rho"], r1["Ms"], r1["GM"], r1["PM"] if np.isfinite(r1["PM"]) else -1, r1["L13"],
                        (round(lp0[0], 2), round(lp0[1], 3)) if lp0 else "-", (round(lp0[2], 2), round(lp0[3], 3)) if lp0 else "-", flag))
P()
P("WORST Ms at delay x1.5 (w 3) on b964:", worst["Ms15"])
P("WORST b964 GM:", worst["GM"])
P("MOST NEGATIVE matched-pole zeta change b964 - V294:", worst["dz"][0], worst["dz"][1][:4])
P("  pairs:", [(round(a, 2), round(b, 4), round(c_, 2), round(d, 4)) for a, b, c_, d in worst["dz"][1][4]])

# R5: designer's stress table (tau as member, w 3) -- flexible-mode zeta V294 / b964 / open, my exact-ZOH closed loop
P()
P("R5 stress flexible-mode zeta (mine, exact ZOH): member v : open / V294 / b964   (designer: mode20 .076/.099/.115 -> .077/.101/.116;"
  " mode13 .145/.171/.146 -> .150/.178/.147; mode20_lo .126/.226/.191 -> .128/.235/.193)")
for name in ("mode13", "mode20", "mode20_lo"):
    for v in (5.0, 12.0, 25.0):
        p0 = mem[name].at(v)
        res = []
        for c, on in ((V294, False), (V294, True), (B964, True)):
            Acl = A.closed_loop_A(p0, c, lane_on=on)
            _, md = A.modes_of(Acl)
            fl = [m for m in md if 8 < m[0] < 40]
            res.append(min(fl, key=lambda t: abs(t[0] - p0.f2)) if fl else (np.nan, np.nan))
        # second method: the plant study's own semi-implicit-Euler linear_poles
        vp = []
        for kw, on in (({}, False), ({}, True), ({"fb_b": 964}, True)):
            _, md = VP.linear_poles(p0, cells=None, lane_kw=kw, lane_on=on)
            fl = [(m[0], m[1]) for m in md if 8 < m[0] < 40]
            vp.append(min(fl, key=lambda t: abs(t[0] - p0.f2)) if fl else (np.nan, np.nan))
        P("%-10s %4.0f : mine %s | VP.linear_poles %s" % (name, v, " / ".join("%.2fHz z%.4f" % r for r in res),
                                                         " / ".join("%.2fHz z%.4f" % r for r in vp)))
json.dump(rows, open(os.path.join(HERE, "a1_inner.json"), "w"), default=float)
out.close()
