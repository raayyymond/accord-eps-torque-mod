# -*- coding: utf-8 -*-
"""s4_outer.py -- adversary `stability`, attack surface (c), linear half: the fork's r1 law UNCHANGED around the EPS,
V294 vs A1017, with my own outer return ratio (advlin.outer_L: exact-ZOH plant, inner loop closed by my own model).

1. cross-check against the harness outer_frf at the design's two anchor cells (V294 nominal 8 m/s: Ms 1.185 GM 10.5
   PM 145; light_b 26.9 m/s: Ms 3.066 GM 1.69 PM 31);
2. grid: members x speeds 3.1..26.9 x J x{0.5,1,1.5,2.5} x inner delay {2,6,12} ms x pipe {22,44} ms x
   SteerFriction slope fraction {0, 0.25, 0.5, 0.75, 1} (the saturation's describing function spans (0, 1] x the
   small-signal slope: scanning it IS the DF limit-cycle test) x SR {16.84 centre, 13.5 hard-turn angle};
3. F-c: GM_A < 0.9 GM_V, Ms_A > 1.1 Ms_V, a DF crossing (min over the relay fraction of GM < 1) for A1017 absent for V294.
"""
import itertools
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import advlin as AL  # noqa: E402
import v295_harness as H  # noqa: E402

LV = AL.LaneLin(1011, 567, name="V294")
LA = AL.LaneLin(1017, 567, name="A1017")
FF = np.logspace(-2, np.log10(20.0), 1500)


def mg(L):
    m = AL.margins(FF, L)
    return m["Ms"], m["GM_min"], m["PM_min"], m["fMs"]


def main():
    t0 = time.time()
    fam = H.family()
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base = H.Cells.v294()
    for nm, v in (("nominal", 8.0), ("light_b", 26.9), ("nominal", 26.9), ("light_b", 8.0), ("light_b", 17.0)):
        p = fam[nm].at(v)
        pl = AL.Plant(p.J, p.b, p.k)
        Lh = H.outer_frf(base, p, v, FF, relay=True)
        Lm = AL.outer_L(LV, pl, v, FF, tau=p.tau_ms)
        mh, mm = H.margins(FF, Lh), mg(Lm)
        La = AL.outer_L(LA, pl, v, FF, tau=p.tau_ms)
        ma = mg(La)
        Lha = H.outer_frf(base.replace(fb_a=1017), p, v, FF, relay=True)
        mha = H.margins(FF, Lha)
        pr("cross-check %-8s v %4.1f  V294 harness Ms %.3f GM %.2f PM %.1f | mine Ms %.3f GM %.2f PM %.1f  ||  A1017 harness "
           "Ms %.3f GM %.2f PM %.1f | mine Ms %.3f GM %.2f PM %.1f" % (nm, v, mh["Ms"], mh["GM_min"], mh["PM_min"], mm[0], mm[1], mm[2],
                                                                     mha["Ms"], mha["GM_min"], mha["PM_min"], ma[0], ma[1], ma[2]))
    members = ("nominal", "J_lo", "J_hi", "J_hi2", "J_0.3", "b_lo", "b_hi", "ms_free", "light_b", "mode13", "mode20", "mode20_lo")
    speeds = (3.1, 5.0, 8.0, 12.0, 17.0, 22.0, 26.9)
    rows = []
    for mn, v, js, tau, pipe, sr in itertools.product(members, speeds, (0.5, 1.0, 1.5, 2.5), (2, 6, 12), (22.0, 44.0), (16.84, 13.5)):
        p = fam[mn].at(v)
        pl = AL.Plant(p.J * js, p.b, p.k, p.f2, p.zeta2, p.r2, "motor")
        res = {}
        for tag, lane in (("V", LV), ("A", LA)):
            per = []
            for rf in (0.0, 0.25, 0.5, 0.75, 1.0):
                per.append(mg(AL.outer_L(lane, pl, v, FF, tau=tau, pipe_ms=pipe, relay_frac=rf, sr=sr)))
            res[tag] = dict(Ms=per[-1][0], GM=per[-1][1], PM=per[-1][2], fMs=per[-1][3],
                            GM_df=min(x[1] for x in per), Ms_df=max(x[0] for x in per), PM_df=min(x[2] for x in per))
        rows.append(dict(m=mn, v=v, J=js, tau=tau, pipe=pipe, sr=sr, **res))
    pr("grid %d cells in %.0f s" % (len(rows), time.time() - t0))
    f1 = [r for r in rows if r["A"]["GM_df"] < 0.9 * r["V"]["GM_df"]]
    f2 = [r for r in rows if r["A"]["Ms_df"] > 1.1 * r["V"]["Ms_df"]]
    f3 = [r for r in rows if r["A"]["GM_df"] < 1.0 <= r["V"]["GM_df"]]
    unV = [r for r in rows if r["V"]["GM_df"] < 1.0]
    pr("F-c: GM_A < 0.9 GM_V: %d cells ; Ms_A > 1.1 Ms_V: %d ; DF crossing (GM < 1 at some relay fraction) for A only: %d ; "
       "V294 itself GM < 1 somewhere: %d cells" % (len(f1), len(f2), len(f3), len(unV)))
    for lab, ff_ in (("GM", f1), ("Ms", f2), ("DF", f3)):
        for r in ff_[:12]:
            pr("   %s %-9s v %4.1f J x%.1f tau %2d pipe %2.0f sr %.2f | V GM %.2f Ms %.3f PM %.1f | A GM %.2f Ms %.3f PM %.1f" % (
                lab, r["m"], r["v"], r["J"], r["tau"], r["pipe"], r["sr"], r["V"]["GM_df"], r["V"]["Ms_df"], r["V"]["PM_df"],
                r["A"]["GM_df"], r["A"]["Ms_df"], r["A"]["PM_df"]))
    gr = np.array([r["A"]["GM_df"] / r["V"]["GM_df"] for r in rows])
    mr = np.array([r["A"]["Ms_df"] / r["V"]["Ms_df"] for r in rows])
    pr("GM ratio A/V (DF-min): min %.3f p5 %.3f median %.3f max %.3f ; Ms ratio A/V (DF-max): min %.3f median %.3f p95 %.3f max %.3f" % (
        gr.min(), np.percentile(gr, 5), np.median(gr), gr.max(), mr.min(), np.median(mr), np.percentile(mr, 95), mr.max()))
    worst = sorted(rows, key=lambda r: r["A"]["GM_df"] / r["V"]["GM_df"])[:10]
    pr("the 10 worst GM ratios:")
    for r in worst:
        pr("   %-9s v %4.1f J x%.1f tau %2d pipe %2.0f sr %.2f | V GM %.2f Ms %.3f | A GM %.2f Ms %.3f" % (
            r["m"], r["v"], r["J"], r["tau"], r["pipe"], r["sr"], r["V"]["GM_df"], r["V"]["Ms_df"], r["A"]["GM_df"], r["A"]["Ms_df"]))
    worstm = sorted(rows, key=lambda r: -r["A"]["Ms_df"] / r["V"]["Ms_df"])[:10]
    pr("the 10 worst Ms ratios:")
    for r in worstm:
        pr("   %-9s v %4.1f J x%.1f tau %2d pipe %2.0f sr %.2f | V GM %.2f Ms %.3f @%.2f Hz | A GM %.2f Ms %.3f @%.2f Hz" % (
            r["m"], r["v"], r["J"], r["tau"], r["pipe"], r["sr"], r["V"]["GM_df"], r["V"]["Ms_df"], r["V"]["fMs"], r["A"]["GM_df"],
            r["A"]["Ms_df"], r["A"]["fMs"]))
    pr("\nper member x speed, nominal corner (J x1, tau 2, pipe 22, sr 16.84, relay full): V294 | A1017  Ms / GM / PM, and DF-min GM")
    for r in rows:
        if r["J"] == 1.0 and r["tau"] == 2 and r["pipe"] == 22.0 and r["sr"] == 16.84:
            pr("  %-9s v %4.1f | Ms %.3f GM %6.2f PM %6.1f GMdf %6.2f | Ms %.3f GM %6.2f PM %6.1f GMdf %6.2f" % (
                r["m"], r["v"], r["V"]["Ms"], r["V"]["GM"], r["V"]["PM"], r["V"]["GM_df"], r["A"]["Ms"], r["A"]["GM"], r["A"]["PM"],
                r["A"]["GM_df"]))
    pr("\nlight_b worst corners (pipe 44, sr 13.5, J x2.5 / x0.5): V294 | A1017")
    for r in rows:
        if r["m"] == "light_b" and r["pipe"] == 44.0 and r["sr"] == 13.5 and r["tau"] == 6 and r["J"] in (0.5, 2.5):
            pr("  J x%.1f v %4.1f | Ms %.3f GMdf %.2f PMdf %.1f | Ms %.3f GMdf %.2f PMdf %.1f" % (
                r["J"], r["v"], r["V"]["Ms_df"], r["V"]["GM_df"], r["V"]["PM_df"], r["A"]["Ms_df"], r["A"]["GM_df"], r["A"]["PM_df"]))
    json.dump(rows, open(os.path.join(HERE, "s4_outer.json"), "w"))
    open(os.path.join(HERE, "s4_outer_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
