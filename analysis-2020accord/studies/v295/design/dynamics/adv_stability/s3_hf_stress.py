# -*- coding: utf-8 -*-
"""s3_hf_stress.py -- adversary `stability`, attack surface (b): the 20 Hz question.
Two-mass stress plants on the nominal family (collocated = the physical sensing; NON-collocated = a harsher case that is
not the physical sensing), f2/zeta2/r2 grid incl. the harness's three members and mine, speeds 5/12/25 m/s, transport
delay 2..12 ms.  Closed-loop least-damped pair in 8-45 Hz for: OPEN (lane muted), V294, A1017, V282 (the on-car
de-damper, the scale anchor: it took the real 20 Hz mode to zeta 0.016).  Eigenvalues of my exact-ZOH loop.
FAIL F-b: zeta_A1017 < 0.9 x zeta_V294 on any cell; SANITY: V282 must de-damp mode20 hard on the collocated members.
"""
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import advlin as AL  # noqa: E402
import v295_harness as H  # noqa: E402

LANES = dict(OPEN=AL.LaneLin(1011, 0, name="open"), V294=AL.LaneLin(1011, 567, name="V294"),
             A1017=AL.LaneLin(1017, 567, name="A1017"),
             V282=AL.LaneLin(923, 1560, op="sum", kp=248, kd=128, name="V282"))
MODES = [(13.0, 0.10, 0.2, "h-mode13"), (20.0, 0.05, 0.2, "h-mode20"), (20.0, 0.02, 0.5, "h-mode20_lo"),
         (16.0, 0.02, 0.5, "m16z02r5"), (25.0, 0.03, 0.3, "m25z03r3"), (13.0, 0.05, 0.5, "m13z05r5"),
         (20.0, 0.05, 0.8, "m20z05r8"), (16.0, 0.05, 0.2, "m16z05r2"), (18.0, 0.03, 0.5, "m18z03r5"),
         (22.0, 0.02, 0.5, "m22z02r5")]


def hf_mode(lane, pl, tau, f2):
    md, rho = AL.modes_of(AL.inner_A(lane, pl, tau=tau))
    c = [(f, z) for f, z in md if 8.0 <= f < 45.0]
    if not c:
        return (np.nan, np.nan, rho)
    f, z = min(c, key=lambda t: abs(t[0] - f2) + 10 * t[1])  # the pair nearest the structural mode, lightest first
    return (f, z, rho)


def main():
    fam = H.family()
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    # cross-check vs the harness stress_damping on its own members (collocated, tau 2)
    for nm, band in (("mode13", (8, 20)), ("mode20", (14, 30)), ("mode20_lo", (14, 30))):
        for v in (5.0, 12.0, 25.0):
            p = fam[nm].at(v)
            (fh, zh), _ = H.stress_damping(H.Cells.v294(), p, band)
            pl = AL.Plant(p.J, p.b, p.k, p.f2, p.zeta2, p.r2, "motor")
            f, z, _ = hf_mode(LANES["V294"], pl, p.tau_ms, p.f2)
            pr("cross-check %-9s v %4.1f  V294 zeta harness %.4f @%.2f Hz  mine %.4f @%.2f Hz" % (nm, v, zh, fh, z, f))
    rows = []
    fails = []
    for (f2, z2, r2, name), sense, v, tau in itertools.product(MODES, ("motor", "wheel"), (5.0, 12.0, 25.0), (2, 3, 6, 9, 12)):
        p = fam["nominal"].at(v)
        pl = AL.Plant(p.J, p.b, p.k, f2, z2, r2, sense)
        r = {k: hf_mode(L, pl, tau, f2) for k, L in LANES.items()}
        rows.append((name, sense, v, tau, r))
        zV, zA = r["V294"][1], r["A1017"][1]
        if np.isfinite(zV) and (not np.isfinite(zA) or zA < 0.9 * zV or r["A1017"][2] >= 1):
            fails.append((name, sense, v, tau, r))
    pr("\nper cell: zeta of the structural pair (f Hz) -- OPEN | V294 | A1017 | V282 ; A1017/V294")
    for name, sense, v, tau, r in rows:
        if v == 12.0 or tau in (2, 12):
            pr("  %-11s %-5s v %4.1f tau %2d | open %.4f | V294 %.4f | A1017 %.4f | V282 %s | A/V %.4f  (f %.2f)" % (
                name, sense, v, tau, r["OPEN"][1], r["V294"][1], r["A1017"][1],
                ("%.4f" % r["V282"][1]) + ("" if r["V282"][2] < 1 else " UNSTABLE rho %.4f" % r["V282"][2]),
                r["A1017"][1] / r["V294"][1], r["A1017"][0]))
    ratio = np.array([r["A1017"][1] / r["V294"][1] for _, _, _, _, r in rows if np.isfinite(r["V294"][1])])
    col = np.array([r["A1017"][1] / r["V294"][1] for _, s, _, _, r in rows if s == "motor" and np.isfinite(r["V294"][1])])
    pr("\nzeta ratio A1017/V294 over %d cells: min %.4f max %.4f ; collocated only: min %.4f max %.4f" % (
        len(ratio), ratio.min(), ratio.max(), col.min(), col.max()))
    dA = np.array([r["A1017"][1] - r["V294"][1] for _, _, _, _, r in rows if np.isfinite(r["V294"][1])])
    d2 = np.array([r["V282"][1] - r["V294"][1] for _, s, _, _, r in rows if np.isfinite(r["V294"][1]) and np.isfinite(r["V282"][1])])
    pr("zeta change A1017 - V294: min %+.5f max %+.5f ; V282 - V294 (the anchor): min %+.4f median %+.4f max %+.4f" % (
        dA.min(), dA.max(), d2.min(), np.median(d2), d2.max()))
    v282_unst = [(n, s, v, t) for n, s, v, t, r in rows if r["V282"][2] >= 1]
    pr("V282 unstable cells (the de-damper went all the way): %d of %d, e.g. %s" % (len(v282_unst), len(rows), v282_unst[:6]))
    sanity = [r for n, s, v, t, r in rows if n == "h-mode20" and s == "motor"]
    pr("SANITY (h-mode20, collocated): V282 zeta %s vs open %s" % (
        [round(r["V282"][1], 4) for r in sanity], [round(r["OPEN"][1], 4) for r in sanity]))
    pr("\nF-b FAIL cells (zeta_A < 0.9 zeta_V or A unstable): %d" % len(fails))
    for x in fails[:20]:
        pr("   ", x[0], x[1], x[2], x[3], {k: (round(v[0], 2), round(v[1], 4)) for k, v in x[4].items()})
    open(os.path.join(HERE, "s3_hf_stress_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
