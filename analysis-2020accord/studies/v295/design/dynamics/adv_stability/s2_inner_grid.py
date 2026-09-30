# -*- coding: utf-8 -*-
"""s2_inner_grid.py -- adversary `stability`, attack surface (a): the INNER acceleration-trim loop on every rigid family
member x speed x J scale x delay x b scale, V294 vs A1017, two methods:
  (1) eigenvalues of my exact-ZOH closed-loop state matrix (advlin.inner_A) -> stability, least-damped pairs;
  (2) Nyquist of my return ratio (advlin.inner_L) -> GM, PM, Ms.
Plus the delay tau in {0, 2, 3, 4, 6, 9, 12} ms (x1 .. x3 of the ~4 ms measured sensing+transport), J x {0.5, 1, 1.5, 2.5},
b x {0.5, 1}.  FAIL rule F-a in ADV-stability-CRITERIA.md.
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
FG = np.concatenate([np.logspace(-2, np.log10(45.0), 1800), np.linspace(45, 499, 400)])


def analyse(lane, pl, tau):
    md, rho = AL.modes_of(AL.inner_A(lane, pl, tau=tau))
    L = AL.inner_L(lane, pl, FG, tau=tau)
    mg = AL.margins(FG, L)
    lo = [(f, z) for f, z in md if 0.05 < f < 8.0]
    hi = [(f, z) for f, z in md if 8.0 <= f < 45.0]
    return dict(rho=rho, lo=min(lo, key=lambda t: t[1]) if lo else (np.nan, np.nan),
                hi=min(hi, key=lambda t: t[1]) if hi else (np.nan, np.nan), all_lo=lo,
                GM=mg["GM_min"], PM=mg["PM_min"], Ms=mg["Ms"], fMs=mg["fMs"])


def main():
    t0 = time.time()
    fam = H.family()
    members = ("nominal", "J_lo", "J_hi", "J_hi2", "J_0.3", "b_lo", "b_hi", "ms_free", "light_b")
    speeds = (3.1, 8.0, 12.0, 17.0, 26.9)
    taus = (0, 2, 3, 4, 6, 9, 12)
    Js = (0.5, 1.0, 1.5, 2.5)
    bs = (0.5, 1.0)
    rows = []
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    # method cross-check on the harness's own linear tools for one cell (sanity, not a dependency)
    p = fam["nominal"].at(12.0)
    pl = AL.Plant(p.J, p.b, p.k)
    Lh = H.loop_frf(H.Cells.v294(), p, np.array([1.0, 2.0, 5.0, 13.0, 20.0]))
    Lm = AL.inner_L(LV, pl, np.array([1.0, 2.0, 5.0, 13.0, 20.0]), tau=2)
    pr("cross-check nominal 12 m/s, |L| mine %s vs harness %s ; phase mine %s vs harness %s" % (
        np.round(np.abs(Lm), 4).tolist(), np.round(np.abs(Lh), 4).tolist(), np.round(np.degrees(np.angle(Lm)), 1).tolist(),
        np.round(np.degrees(np.angle(Lh)), 1).tolist()))
    mh = H.closed_loop_modes(p, H.Cells.v294())[0]
    mm = AL.modes_of(AL.inner_A(LV, pl, tau=2))[0]
    pr("   modes (<45 Hz) harness %s\n   modes (<45 Hz) mine    %s" % ([(round(f, 2), round(z, 3)) for f, z in mh if 0.1 < f < 45],
                                                                    [(round(f, 2), round(z, 3)) for f, z in mm if 0.1 < f < 45]))
    for mn, v, tau, js, bsc in itertools.product(members, speeds, taus, Js, bs):
        p = fam[mn].at(v)
        pl = AL.Plant(p.J * js, p.b * bsc, p.k)
        rv = analyse(LV, pl, tau)
        ra = analyse(LA, pl, tau)
        rows.append(dict(m=mn, v=v, tau=tau, J=js, b=bsc, V=rv, A=ra))
    pr("grid %d cells in %.0f s" % (len(rows), time.time() - t0))
    # ---------------- F-a evaluation
    unstA = [r for r in rows if r["A"]["rho"] >= 1 and r["V"]["rho"] < 1]
    unstV = [r for r in rows if r["V"]["rho"] >= 1]
    pr("A1017 unstable where V294 stable: %d cells ; V294 unstable cells: %d" % (len(unstA), len(unstV)))
    for r in unstA[:10]:
        pr("   ", r["m"], r["v"], r["tau"], r["J"], r["b"], "rhoV %.5f rhoA %.5f" % (r["V"]["rho"], r["A"]["rho"]))
    gmfail = [r for r in rows if (r["A"]["GM"] < 3 or r["A"]["PM"] < 30) and r["V"]["GM"] >= 6]
    pr("A1017 GM < 3 or PM < 30 where V294 GM >= 6: %d cells" % len(gmfail))
    for r in gmfail[:10]:
        pr("   ", r["m"], r["v"], r["tau"], r["J"], r["b"], "V GM %.2f PM %.1f | A GM %.2f PM %.1f" % (
            r["V"]["GM"], r["V"]["PM"], r["A"]["GM"], r["A"]["PM"]))
    light = []
    for r in rows:
        zV, zA = r["V"]["lo"][1], r["A"]["lo"][1]
        if np.isfinite(zA) and zA < 0.3 and (not np.isfinite(zV) or zA < 0.9 * zV):
            light.append(r)
    ident_nom = [r for r in light if r["m"] != "light_b" and r["tau"] in (2, 4) and r["J"] == 1.0 and r["b"] == 1.0]
    pr("least-damped <8 Hz pair: zeta_A < 0.3 and < 0.9 zeta_V: %d of %d cells (%.1f %%); on identified members at nominal "
       "delay/J/b: %d" % (len(light), len(rows), 100.0 * len(light) / len(rows), len(ident_nom)))
    for r in light[:25]:
        pr("   %-8s v %4.1f tau %2d J x%.1f b x%.1f  V %s  A %s" % (r["m"], r["v"], r["tau"], r["J"], r["b"],
                                                                  np.round(r["V"]["lo"], 3).tolist(), np.round(r["A"]["lo"], 3).tolist()))
    # ---------------- summaries
    pr("\nsummary by member (all speeds/taus/J/b): min GM V/A, min PM V/A, max Ms V/A, min zeta_lo V/A, min zeta_hi V/A")
    for mn in members:
        rr = [r for r in rows if r["m"] == mn]
        f = lambda k, w, fn: fn([r[w][k] for r in rr if np.isfinite(r[w][k])], default=np.inf)  # noqa: E731
        zl = lambda w: min([r[w]["lo"][1] for r in rr if np.isfinite(r[w]["lo"][1])], default=np.nan)  # noqa: E731
        zh = lambda w: min([r[w]["hi"][1] for r in rr if np.isfinite(r[w]["hi"][1])], default=np.nan)  # noqa: E731
        pr("  %-8s GM %.2f/%.2f  PM %.1f/%.1f  Ms %.3f/%.3f  zeta_lo %.3f/%.3f  zeta_hi %.3f/%.3f" % (
            mn, f("GM", "V", min), f("GM", "A", min), f("PM", "V", min), f("PM", "A", min), f("Ms", "V", max), f("Ms", "A", max),
            zl("V"), zl("A"), zh("V"), zh("A")))
    pr("\nnominal-delay (tau 2 and 4), J x1, b x1: per member x speed -- V294 | A1017: GM, PM, Ms, least-damped <8 Hz pair")
    for r in rows:
        if r["tau"] in (2, 4) and r["J"] == 1.0 and r["b"] == 1.0:
            pr("  %-8s v %4.1f tau %d | GM %6.2f PM %6.1f Ms %.3f lo %s | GM %6.2f PM %6.1f Ms %.3f lo %s" % (
                r["m"], r["v"], r["tau"], r["V"]["GM"], r["V"]["PM"], r["V"]["Ms"], np.round(r["V"]["lo"], 3).tolist(),
                r["A"]["GM"], r["A"]["PM"], r["A"]["Ms"], np.round(r["A"]["lo"], 3).tolist()))
    # zeta change distribution of the least-damped low pair
    dz = np.array([r["A"]["lo"][1] - r["V"]["lo"][1] for r in rows if np.isfinite(r["A"]["lo"][1]) and np.isfinite(r["V"]["lo"][1])])
    pr("\nzeta_lo(A) - zeta_lo(V) over %d cells with a pair in both: min %.3f p5 %.3f median %.3f p95 %.3f max %.3f; "
       "fraction < 0: %.2f" % (len(dz), dz.min(), np.percentile(dz, 5), np.median(dz), np.percentile(dz, 95), dz.max(),
                               np.mean(dz < 0)))
    worst = sorted([r for r in rows if np.isfinite(r["A"]["lo"][1]) and np.isfinite(r["V"]["lo"][1])],
                   key=lambda r: r["A"]["lo"][1] - r["V"]["lo"][1])[:12]
    pr("the 12 largest zeta_lo DROPS:")
    for r in worst:
        pr("   %-8s v %4.1f tau %2d J x%.1f b x%.1f  V %s  A %s" % (r["m"], r["v"], r["tau"], r["J"], r["b"],
                                                              np.round(r["V"]["lo"], 3).tolist(), np.round(r["A"]["lo"], 3).tolist()))
    json.dump([dict(m=r["m"], v=r["v"], tau=r["tau"], J=r["J"], b=r["b"],
                    V={k: (list(x) if isinstance(x, tuple) else x) for k, x in r["V"].items() if k != "all_lo"},
                    A={k: (list(x) if isinstance(x, tuple) else x) for k, x in r["A"].items() if k != "all_lo"}) for r in rows],
              open(os.path.join(HERE, "s2_inner_grid.json"), "w"))
    open(os.path.join(HERE, "s2_inner_grid_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
