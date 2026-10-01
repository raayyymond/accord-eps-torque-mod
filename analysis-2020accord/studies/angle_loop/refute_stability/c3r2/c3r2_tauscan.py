# -*- coding: utf-8 -*-
"""c3r2_tauscan.py -- the fork-integral time constant at which the ms_free family's curve-hold becomes linearly stable
again (rho < 1), and at which b_hi's outer-break GM reaches 6 dB.  -> tauscan_out.txt"""
import math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / 1.155), ("FB1.155", 1.155, 1 / 1.155))
out = []
for des in (M.C3R2P, M.C3R2F):
    for mem in ("ms_free", "b_lo*ms_free", "b_q*ms_free"):
        row = []
        for tau in (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0, None):
            mx = (0, None)
            for v in (11.0, 11.5, 11.75, 11.9, 12.0, 12.25, 12.5, 13.0):
                for a in (2.0, 2.25, 2.5):
                    pl0, ea = M.member(mem, v)
                    pl = M.Plant(pl0.J, pl0.b, pl0.k * (1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2), pl0.d)
                    for fn, kap, jb in FR:
                        for e in (0, 10):
                            r = M.Periodic(des, pl, v, e=e, kappa=kap, jb=jb, tau_o=tau).rho_ring()
                            if r[0] > mx[0]:
                                mx = (r[0], (v, a, fn, e, round(r[1], 2), round(r[2], 4)))
            row.append(f"tau {tau}: {mx[0]:.5f}")
            print(des.name, mem, tau, mx, flush=True)
        out.append(f"{des.name} {mem:13s}: " + " | ".join(row))
(M.OUT / "tauscan_out.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
