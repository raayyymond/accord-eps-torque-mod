# -*- coding: utf-8 -*-
"""d1c_sens -- linear predictor for (d): the outer-loop sensitivity |S| = |1/(1+L)| averaged over 1.6-3 Hz and the
closed-loop wheel-mode resonance (peak |T| = |L/(1+L)| and its frequency), r2alt vs V295+r1 vs V294+r1, pipe 22/42."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d1_outer as D

fam = D.H.family(include_stress=False)
FG = np.linspace(0.02, 8.0, 4000)
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
for pipe in (22, 42):
    P("pipe %d ms:  member v | mean|S| 1.6-3 Hz  V294r1 V295r1 r2alt (r2alt/V295r1) | peak|T| (f)  V294r1 V295r1 r2alt" % pipe)
    for m in ("nominal", "b_lo", "J_hi", "light_b"):
        for v in (5.0, 8.0, 12.0, 17.0, 19.0, 22.0, 26.9):
            vals = {}
            for (cfg, cn, fn) in D.CONFIGS:
                G = D.G1_eps(D.CELLS[cn], fam[m].at(v), FG) * D.kla(v) * np.exp(-2j * np.pi * FG * pipe * 1e-3) * 4096.0
                Lf = G * D.C_fork(D.FORKS[fn], v, FG, 1.0)
                if np.real(Lf[0] * 1j) < 0:
                    Lf = -Lf
                S = 1 / (1 + Lf)
                T = Lf / (1 + Lf)
                band = (FG >= 1.6) & (FG <= 3.0)
                hf = FG > 0.8
                k = np.argmax(np.abs(T[hf]))
                vals[cfg] = (float(np.mean(np.abs(S[band]))), float(np.abs(T[hf][k])), float(FG[hf][k]))
            a, b, c = vals["V294+r1"], vals["V295+r1"], vals["V295+r2alt"]
            P("   %-8s %4.1f | %.3f %.3f %.3f (x%.3f) | %.2f(%.2f) %.2f(%.2f) %.2f(%.2f)" % (
                m, v, a[0], b[0], c[0], c[0] / b[0], a[1], a[2], b[1], b[2], c[1], c[2]))
open(os.path.join(HERE, "out", "d1c_sens_out.txt"), "w").write("\n".join(L) + "\n")
