# -*- coding: utf-8 -*-
"""a7 -- a light_b-shaped world CALIBRATED on the on-car record, then the candidate in it.
World = light_b (prior hold map k(v)*sat*tanh, J 0.21, b 1.575) with b x beta and J x gamma.
Constraints from the record:
  (A) r71-old: V293 (no trim) + fork rev 2 (Kp 0.85, relay live) at 21.8 m/s on 16-29 deg curves LIMIT-CYCLED at 2.34 Hz
      -> require GM < 1.05 at some theta0 in 16..29 with the -180 crossing in 1.8..2.9 Hz;
  (B) r71b: V294 + r1 did not limit-cycle on its 15-19 / 19-22 / 22+ curves -> require GM > 1.0 there;
  (C) r71b 22+ straights: at most a weak 2.3-2.7 Hz excess (+1.2..+2.9 dB on 15 s; a synthetic Ms~3 line reads +4.4..+6.2)
      -> reported, used as a SOFT filter (V294 straight 22+ Ms <= 2.5).
For every (beta, gamma) that satisfies A and B: V294 vs candidate at the drive's op points (same hold torque)."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lib as A  # noqa: E402
import adv_lin as AL  # noqa: E402
import adv_outer as AO  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a7_calibrated_world_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


sfc = np.load(os.path.join(HERE, "a1_surface.npz"))
S294, Sc = sfc["S294"].astype(float), sfc["Sc"].astype(float)
KPC = A.table(A.CAND_X, A.CAND_Y)
R1 = dict(kp=0.9, ki=0.3, laf=14.0, fric=0.011)
REV2 = dict(kp=0.85, ki=0.3, laf=14.0, fric=0.011)
F = np.concatenate([np.linspace(0.05, 1.0, 30), np.geomspace(1.0, 30.0, 500)[1:]])
lb = VP.family()["light_b"]


def mg(L):
    m = AL.margins(F, L)
    return m["Ms"], m["GM"], m["f_GM"]


ops = [("straight 22+", 26.9, 0.6, 5), ("hold 22+ (idx18)", 26.9, 5.0, 18), ("curve 22+", 26.9, 11.0, 33),
       ("straight 15-22", 17.0, 0.6, 5), ("curve 15-19", 17.0, 18.4, 38), ("curve 19-22", 20.5, 9.8, 38),
       ("straight 10-15", 12.0, 0.6, 5), ("hold 10-15", 12.0, 9.6, 36), ("straight 5-10", 8.0, 1.2, 5),
       ("hard 5-10", 8.0, 76.0, 75), ("straight 0-5", 3.1, 1.5, 5), ("low-speed turn", 3.1, 161.0, 80)]
P("beta (b x) gamma (J x) | (A) r71-old min GM @f over 16-29 deg | (B) V294 curves GM | (C) V294 straight22+ Ms | pass")
worlds = []
for beta in (0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0):
    for gamma in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        def par(v):
            p = lb.at(v)
            return p.J * gamma, p.b * beta, p.k, AO.sat_prior(v)
        J, b, k, sat = par(21.8)
        a_gm = []
        for th0 in (16.0, 19.0, 22.0, 25.0, 29.0):
            T0 = k * sat * np.tanh(th0 / sat)
            i0 = AO.idx_for_torque(S294, T0)
            L = AO.outer_L(F, 21.8, th0, J, b, k, sat, 0.0, AO.slope_at(S294, i0), REV2, trim=False)
            a_gm.append(mg(L)[1:])
        amin = min(a_gm, key=lambda t: t[0])
        okA = amin[0] < 1.05 and 1.8 <= amin[1] <= 2.9
        bgm = []
        for lab, v, th0, i0 in ops[:6]:
            if "curve" not in lab:
                continue
            J2, b2, k2, s2 = par(v)
            L = AO.outer_L(F, v, th0, J2, b2, k2, s2, 960.0, AO.slope_at(S294, i0), R1)
            bgm.append(mg(L)[1])
        okB = min(bgm) > 1.0
        J2, b2, k2, s2 = par(26.9)
        msC = mg(AO.outer_L(F, 26.9, 0.6, J2, b2, k2, s2, 960.0, AO.slope_at(S294, 5), R1))[0]
        okC = msC <= 2.5
        P("  beta %4.2f gamma %4.2f | A GM %.2f@%.2f %s | B min GM %.2f %s | C Ms %.2f %s | %s" % (
            beta, gamma, amin[0], amin[1], "ok" if okA else "--", min(bgm), "ok" if okB else "--", msC, "ok" if okC else "--",
            "A+B+C" if okA and okB and okC else ("A+B" if okA and okB else "")))
        if okA and okB:
            worlds.append((beta, gamma, okC))

P("\nworlds consistent with A and B: %d (%d also meet the soft C)" % (len(worlds), sum(w[2] for w in worlds)))
P("candidate vs V294 in every such world (same hold torque -> each build's own idx), relay on, pipe 22:")
summary = []
for beta, gamma, okC in worlds:
    rows = []
    for lab, v, th0, i294 in ops:
        p = lb.at(v)
        J, b, k, sat = p.J * gamma, p.b * beta, p.k, AO.sat_prior(v)
        T0 = S294[i294]
        ic = AO.idx_for_torque(Sc, T0)
        a = mg(AO.outer_L(F, v, th0, J, b, k, sat, 960.0, AO.slope_at(S294, i294), R1))
        c = mg(AO.outer_L(F, v, th0, J, b, k, sat, float(KPC[ic]), AO.slope_at(Sc, ic), R1))
        rows.append((lab, a[0], a[1], c[0], c[1]))
        summary.append((beta, gamma, okC, lab, a[0], a[1], c[0], c[1]))
    worst = min(rows, key=lambda r: r[4] / r[2])
    P("  beta %.2f gamma %.2f %s | %s" % (beta, gamma, "(C ok)" if okC else "(C no)",
                                          " ; ".join("%s %.2f/%.2f->%.2f/%.2f" % (r[0], r[1], r[2], r[3], r[4]) for r in rows[:6])))
    P("        %s | worst GM ratio %.3f at %s" % (" ; ".join("%s %.2f/%.2f->%.2f/%.2f" % (r[0], r[1], r[2], r[3], r[4]) for r in rows[6:]),
                                                worst[4] / worst[2], worst[0]))
S = [s for s in summary]
if S:
    P("\nacross all A+B worlds: min cand GM %.2f (V294 %.2f) at %s beta %.2f gamma %.2f ; cand GM < 1.2: %d ; cand GM < V294 GM: %d of %d ; max Ms ratio %.3f" % (
        min(s[7] for s in S), min(S, key=lambda s: s[7])[5], min(S, key=lambda s: s[7])[3], min(S, key=lambda s: s[7])[0],
        min(S, key=lambda s: s[7])[1], sum(s[7] < 1.2 for s in S), sum(s[7] < s[5] for s in S), len(S), max(s[6] / s[4] for s in S)))
    for lab in [o[0] for o in ops]:
        L_ = [s for s in S if s[3] == lab]
        P("   %-18s GM ratio cand/V294 min %.3f max %.3f ; Ms ratio min %.3f max %.3f ; min cand GM %.2f" % (
            lab, min(s[7] / s[5] for s in L_), max(s[7] / s[5] for s in L_), min(s[6] / s[4] for s in L_),
            max(s[6] / s[4] for s in L_), min(s[7] for s in L_)))
json.dump(summary, open(os.path.join(HERE, "a7_calibrated_world.json"), "w"), default=float)
out.close()
