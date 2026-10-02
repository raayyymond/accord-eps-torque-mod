# -*- coding: utf-8 -*-
"""d1_gate2_table.py -- the per-operating-point GATE-2 table for the doc: PM / GM_up / Ms (= max|S|) / fc, nominal member,
frame 'nom', hold offset e = 0, PID and I-frozen PD, theta = 0 and the physical curve-hold point (a = 2.0 m/s^2, capped
at 360 deg), on c3r1_model (unchanged).  D1c's small-signal loop IS V298's (no Kp/Ki/Kd/G cell changes): one table
serves both; G0-1400 is the optional low-speed row.  Also the worst member at each point (credible set).  Wall < 10 s."""
import math, sys, time
from pathlib import Path
import numpy as np
t0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d1_gate2 as G
M, S = G.M, G.S
F = G.F
rows = []
for dn in ("V298", "G0-1400"):
    for v in (3.1, 5.0, 8.0, 11.75, 17.5, 26.9):
        for a in (0.0, 2.0):
            th = min(G.theta_of_a(v, a), 360.0) if a else 0.0
            for noI in (False, True):
                best = None
                for mem in ("nominal",) + tuple(G.GATED):
                    pl = M.member(mem, v)
                    if th:
                        pl.k *= 1 - math.tanh(th / G.sat(v)) ** 2
                    Pt, Pw = M.plant_channels(pl, F, 1.0, 0.0)
                    Cth, Cw, Cref = M.controller(G.DES[dn], v, F, 0, 1.0, noI=noI)
                    L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                    PM, FC, GMu = M.pm_gm(L, F)
                    Ms = float(np.abs(1 / (1 + L)).max())
                    rec = (mem, PM, GMu, Ms, FC)
                    if mem == "nominal":
                        nom = rec
                    if best is None or PM - G.bar(mem, 0) < best[1] - G.bar(best[0], 0):
                        best = rec
                rows.append((dn, v, th, "PD" if noI else "PID", nom, best))
out = ["design v(m/s) theta_op loop | nominal: PM GMup Ms fc(Hz) | worst credible member (frame nom, e 0): PM GMup Ms"]
for dn, v, th, lp, nom, b in rows:
    out.append(f"{dn:8s} {v:5.2f} {th:6.0f} {lp:3s} | {nom[1]:5.1f} {nom[2]:5.1f} {nom[3]:4.2f} {nom[4]:5.2f} | "
               f"{b[0]:12s} {b[1]:5.1f} {b[2]:5.1f} {b[3]:4.2f}")
out.append(f"wall {time.time()-t0:.1f} s")
(HERE / "out" / "d1_gate2_table.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
