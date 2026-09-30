# -*- coding: utf-8 -*-
"""a2 -- (a) the INNER acceleration loop, V294 (Kp 960) vs the candidate at its strongest trim (Kp 1248, idx <= 8),
on every family member, J x0.5..x2.5, b/Fc corners (linear: b), delay 0..18 ms, and two-mass stress modes in three
topologies.  Two methods: my exact-ZOH discrete eigenvalues and my Nyquist margins.  Pole tracking by continuation
in Kp 960 -> 1248.  Output: a2_inner_out.txt + a2_inner.json."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lin as AL  # noqa: E402
import v294_plant as VP  # noqa: E402   (parameters only: the identified family's numbers)

LANE294 = dict(fb_a=1011, fb_b=567, fb_op="diff", kp=960.0, kd=0.0, lag_a=992, lag_b=507, gain=5346)
LANEC = dict(LANE294, kp=1248.0)
F = np.concatenate([np.linspace(0.02, 1, 60), np.geomspace(1.0, 490.0, 2500)[1:]])

fam = VP.family()
speeds = [3.1, 8.0, 11.9, 17.0, 26.9]


def params(mem, v):
    p = mem.at(v)
    return p.J, p.b, p.k


members = {}
for nm in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "ms_free", "light_b"):
    members[nm] = fam[nm]
cases = []
for nm, mem in members.items():
    for v in speeds:
        J, b, k = params(mem, v)
        cases.append(dict(name=nm, v=v, J=J, b=b, k=k, top="rigid", tau=mem.tau_ms))
# J scaling x0.5 / x2.5 on nominal and light_b; b x0.5 on light_b (zeta ~0.15)
for nm in ("nominal", "light_b"):
    for v in speeds:
        J, b, k = params(members[nm], v)
        for sJ in (0.5, 2.5):
            cases.append(dict(name="%s_Jx%.1f" % (nm, sJ), v=v, J=J * sJ, b=b, k=k, top="rigid", tau=2))
        if nm == "light_b":
            cases.append(dict(name="light_b_bx0.5", v=v, J=J, b=b * 0.5, k=k, top="rigid", tau=2))
            cases.append(dict(name="light_b_kx0.35", v=v, J=J, b=b, k=k * 0.35, top="rigid", tau=2))   # soft spring (large angle)
# delays (transport, ticks) incl x1.5..x3 of 6 ms
for nm in ("nominal", "light_b", "J_hi2"):
    for v in (3.1, 11.9, 26.9):
        J, b, k = params(members[nm], v)
        for tau in (0, 4, 6, 9, 12, 18):
            cases.append(dict(name="%s_tau%d" % (nm, tau), v=v, J=J, b=b, k=k, top="rigid", tau=tau))
# two-mass stress modes
for nm in ("nominal", "light_b"):
    for v in (3.1, 11.9, 26.9):
        J, b, k = params(members[nm], v)
        for (f2, z2, r2) in ((13, 0.1, 0.2), (20, 0.05, 0.2), (20, 0.02, 0.5), (16, 0.03, 0.3), (25, 0.03, 0.3)):
            for top in ("T1", "T2", "T3"):
                for tau in (2, 6, 9):
                    cases.append(dict(name="%s+%s_%d_%.2f_%.1f" % (nm, top, f2, z2, r2), v=v, J=J, b=b, k=k, top=top,
                                      f2=f2, z2=z2, r2=r2, tau=tau))

rows = []
worst = dict(unstable=[], zeta_drop=[], Ms=[])
for cse in cases:
    Ac, Bc, cs, _ = AL.plant_cont(cse["J"], cse["b"], cse["k"], cse["top"], cse.get("f2", 0), cse.get("z2", 0.05),
                                  cse.get("r2", 0.2))
    r = dict(cse)
    for tag, lane in (("V294", LANE294), ("cand", LANEC), ("open", None)):
        A = AL.closed_loop_A(Ac, Bc, cs, lane or LANE294, tau=cse["tau"], lane_on=lane is not None)
        osc, rho = AL.osc_poles(A)
        r[tag + "_rho"] = rho
        r[tag + "_osc"] = osc
        if lane is not None:
            L = AL.inner_L(lane, Ac, Bc, cs, F, tau=cse["tau"])
            mg = AL.margins(F, L)
            r[tag + "_Ms"], r[tag + "_GM"], r[tag + "_fGM"] = mg["Ms"], mg["GM"], mg["f_GM"]
            band = (F >= 1) & (F <= 3)
            r[tag + "_L13"] = float(np.max(np.abs(L[band])))
    # continuation-tracked poles V294 -> cand: follow each V294 osc pole as kp rises
    kps = np.linspace(960, 1248, 19)
    trk = []
    A0 = AL.closed_loop_A(Ac, Bc, cs, LANE294, tau=cse["tau"])
    ev0 = np.linalg.eigvals(A0)
    cur = [z for z in ev0 if abs(z) > 1e-12 and np.log(z).imag > 0 and np.log(z).imag / (2 * np.pi * AL.DT) > 0.05
           and np.log(z).imag / (2 * np.pi * AL.DT) < 150]
    for kp in kps[1:]:
        A1 = AL.closed_loop_A(Ac, Bc, cs, dict(LANE294, kp=kp), tau=cse["tau"])
        ev1 = np.linalg.eigvals(A1)
        cur = [ev1[np.argmin(np.abs(ev1 - z))] for z in cur]
    for z0, z1 in zip([z for z in ev0 if abs(z) > 1e-12 and np.log(z).imag > 0 and 0.05 < np.log(z).imag / (2 * np.pi * AL.DT) < 150], cur):
        s0, s1 = np.log(z0) / AL.DT, np.log(z1) / AL.DT
        trk.append((float(s0.imag / 2 / np.pi), float(-s0.real / abs(s0)), float(s1.imag / 2 / np.pi), float(-s1.real / abs(s1))))
    r["tracked"] = trk
    rows.append(r)
    if r["cand_rho"] >= 1.0 > r["V294_rho"]:
        worst["unstable"].append(r)
    for (f0, z0, f1, z1) in trk:
        if z0 < 0.3 and z1 < 0.9 * z0:
            worst["zeta_drop"].append((cse["name"], cse["v"], cse["tau"], f0, z0, f1, z1))
    if r["cand_Ms"] > 2.0 or r["cand_Ms"] > 1.25 * r["V294_Ms"]:
        worst["Ms"].append((cse["name"], cse["v"], cse["tau"], r["V294_Ms"], r["cand_Ms"]))

out = open(os.path.join(HERE, "a2_inner_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


P("a2 inner loop: %d cases (member x speed x delay x topology)" % len(rows))
P("A1 candidate unstable where V294 stable: %d" % len(worst["unstable"]))
P("   any case unstable at all (V294 / cand): %d / %d" % (sum(r["V294_rho"] >= 1 for r in rows), sum(r["cand_rho"] >= 1 for r in rows)))
P("A2 tracked poles with zeta < 0.3 whose zeta falls below 0.9x V294's: %d" % len(worst["zeta_drop"]))
for w_ in worst["zeta_drop"][:40]:
    P("   ", w_)
P("A3 Ms > 2 or > 1.25x V294: %d" % len(worst["Ms"]))
for w_ in worst["Ms"][:40]:
    P("   ", w_)
P("\n-- summary by group: max Ms (V294 -> cand), min GM, max |L| 1-3 Hz, min tracked zeta (V294 -> cand)")
groups = {}
for r in rows:
    g = r["name"].split("_tau")[0] if "_tau" in r["name"] else r["name"]
    groups.setdefault(g, []).append(r)
for g, rs in groups.items():
    ms0 = max(r["V294_Ms"] for r in rs)
    ms1 = max(r["cand_Ms"] for r in rs)
    gm0 = min(r["V294_GM"] for r in rs)
    gm1 = min(r["cand_GM"] for r in rs)
    l0 = max(r["V294_L13"] for r in rs)
    l1 = max(r["cand_L13"] for r in rs)
    zt = [(t[1], t[3], t[0]) for r in rs for t in r["tracked"]]
    zmin0 = min(zt, key=lambda t: t[0]) if zt else None
    zmin1 = min(zt, key=lambda t: t[1]) if zt else None
    P("  %-34s Ms %.3f -> %.3f | GM %.2f -> %.2f | |L|1-3 %.2f -> %.2f | min zeta V294 %s ; cand %s" % (
        g, ms0, ms1, gm0, gm1, l0, l1,
        ("%.3f->%.3f @%.1fHz" % zmin0) if zmin0 else "-", ("%.3f->%.3f @%.1fHz" % zmin1) if zmin1 else "-"))
P("\n-- stress modes: the flexible pole (8-40 Hz) open / V294 / cand zeta, per topology, delay")
for r in rows:
    if r["top"] == "rigid":
        continue
    def fl(osc):
        c = [(f, z) for f, z in osc if 8 < f < 40]
        return min(c, key=lambda t: t[1]) if c else (float("nan"), float("nan"))
    o, a, c = fl(r["open_osc"]), fl(r["V294_osc"]), fl(r["cand_osc"])
    P("  %-32s v %4.1f tau %d : open %.2fHz z %.4f | V294 %.2fHz z %.4f (%+.4f) | cand %.2fHz z %.4f (%+.4f) | cand/V294 shift %.2f" % (
        r["name"], r["v"], r["tau"], o[0], o[1], a[0], a[1], a[1] - o[1], c[0], c[1], c[1] - o[1],
        (c[1] - o[1]) / (a[1] - o[1]) if abs(a[1] - o[1]) > 1e-7 else float("nan")))
out.close()
json.dump([{k: v for k, v in r.items()} for r in rows], open(os.path.join(HERE, "a2_inner.json"), "w"), default=float)
