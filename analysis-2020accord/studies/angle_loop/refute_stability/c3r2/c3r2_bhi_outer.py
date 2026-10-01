# -*- coding: utf-8 -*-
"""c3r2_bhi_outer.py -- the tier-A b_hi and nominal members under the fork outer integral: outer-break PM/GM, actuator PM,
exact ring, over a / frame / tau_o, at the GB-P dip speeds.  -> bhi_outer_out.txt"""
import math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
F = M.F; w = 2 * np.pi * F
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / 1.155), ("FB1.155", 1.155, 1 / 1.155), ("FAc", 1/1.155, 1.0))
out = []
for des in (M.C3R2P, M.C3R2F):
    for mem in ("b_hi", "nominal", "J_hi"):
        out.append(f"== {des.name} {mem}: outer-break PM/GM | actuator PM | exact rho, ring Hz, zeta  (e0 / ages 1-10) ==")
        for tau in (1.0, 1.5, 2.0):
            for a in (1.5, 2.0, 2.5):
                for v in (10.0, 11.0, 11.75, 12.5, 14.0):
                    pl0, ea = M.member(mem, v)
                    s2 = 1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2
                    pl = M.Plant(pl0.J, pl0.b, pl0.k * s2, pl0.d)
                    row = []
                    for fn, kap, jb in FR:
                        L, KCP = M.loop_L(des, pl, v, e=0, kappa=kap, jb=jb)
                        Lo = KCP / (1 + L) * np.exp(-1j * w * 0.06) * (0.01 / tau) / (1 - np.exp(-1j * w * 0.01))
                        pmo, _, gmo, _ = M.pm_gm(Lo)
                        Lt, _ = M.loop_L(des, pl, v, e=0, kappa=kap, jb=jb, tau_o=tau)
                        pma = M.pm_gm(Lt)[0]
                        rho, fq, z = M.Periodic(des, pl, v, e=0, kappa=kap, jb=jb, tau_o=tau).rho_ring()
                        row.append((gmo, pmo, pma, rho, fq, z, fn))
                    g = min(row)
                    zmin = min(row, key=lambda r: r[5])
                    out.append(f"  tau {tau} a{a} v{v:5.2f}: min outer GM {g[0]:4.1f} dB ({g[6]}; PM {g[1]:.1f}) | min act PM "
                               f"{min(r[2] for r in row):5.1f} | least-damped ring {zmin[4]:.2f} Hz z {zmin[5]:+.3f} rho {zmin[3]:.4f} ({zmin[6]})")
txt = "\n".join(out)
(M.OUT / "bhi_outer_out.txt").write_text(txt, encoding="utf-8")
print(txt)
