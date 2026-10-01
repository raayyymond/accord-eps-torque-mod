# -*- coding: utf-8 -*-
"""d1b_df -- the relay (a saturation: N(A) in [0, slope], zero phase) swept over k x the flown small-signal slope, at
pipes 22/42/62 ms, every member x speed; the first k at which the linear loop loses stability.  Plus the LSF-inflated
relay gain at 3-5 m/s against P, in torque units per m/s^2 of planner error."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d1_outer as D

fam = D.H.family(include_stress=False)
FG = np.logspace(-3, np.log10(25.0), 5000)
mults = [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 13, 16, 20, 25, 30]
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
fk = D.FORKS["r1"]
for v in (3.1, 4.0, 5.0, 8.0):
    g = 1 + D.lsf(v) / 0.9
    P("v %.1f: P %.3f  relay slope %.3f  (ratio %.3f)  Ki_eff %.3f /s  torque per m/s^2 of planner error; relay saturates at "
      "|e| = %.4f m/s^2 = %.1f deg of wheel" % (v, (0.9 + D.lsf(v)) / 14, 0.011 / 0.3 * g, 0.011 / 0.3 * g / ((0.9 + D.lsf(v)) / 14),
                                               0.3 * g / 14, 0.3 / g, 0.3 / g / D.kla(v)))
for pipe in (22, 42, 62):
    for (cfg, cn, fn) in D.CONFIGS:
        firsts = []
        for m in D.MEMBERS:
            for v in D.SPEEDS:
                G = D.G1_eps(D.CELLS[cn], fam[m].at(v), FG) * D.kla(v) * np.exp(-2j * np.pi * FG * pipe * 1e-3) * 4096.0
                first = 99
                for km in mults:
                    Lf = G * D.C_fork(D.FORKS[fn], v, FG, km)
                    if np.real(Lf[0] * 1j) < 0:
                        Lf = -Lf
                    mg = D.margins(FG, Lf)
                    if mg["GM"] <= 1.0 or mg["PM"] <= 0:
                        first = km
                        break
                firsts.append((first, m, v))
        firsts.sort()
        idf = [x for x in firsts if x[1] != "light_b"]
        P("pipe %2d %-11s worst: %s | identified-family worst: %s | 3-5 m/s worst: %s" % (
            pipe, cfg, firsts[:3], idf[:3], [x for x in firsts if x[2] <= 5.0][:3]))
open(os.path.join(HERE, "out", "d1b_df_out.txt"), "w").write("\n".join(L) + "\n")
