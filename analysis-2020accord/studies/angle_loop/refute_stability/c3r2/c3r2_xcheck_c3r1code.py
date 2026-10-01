# -*- coding: utf-8 -*-
"""c3r2_xcheck_c3r1code.py -- cross-code check of the decisive outer-loop numbers on the ROUND-1 refuter's independent model
(c3r1_model, the code rev2-B's own rb_gate2 uses), built exactly as rb_gate2 builds C3B-P/F, with the outer loop closed the
way c3r1_outer.py closes it (outer break, T_ref * e^{-s 0.06} * (0.01/tau)/(1 - z_f^-1)).  -> xcheck_out.txt"""
import math, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "c3r1")); sys.path.insert(0, str(HERE.parents[1] / "c3" / "rev2B")); sys.path.insert(0, str(HERE))
import c3r1_model as R
import rb_table as T
import c3r2_model as M
F = np.unique(np.concatenate([np.logspace(-2.5, math.log10(49.0), 3000), np.linspace(0.05, 3, 1500)]))
DES = {"P": R.Design("C3B-P", "fresh", kd=48, ki=40.0, rows=tuple(T.GB_P)), "F": R.Design("C3B-F", "held", kd=24, ki=40.0, rows=tuple(T.GB_F))}
zf = np.exp(-2j * np.pi * F * 0.01)
out = []
for W, mem, v, a, kap, jb, e, tau in (("P", "b_hi", 11.75, 2.5, 1.155, 1.0, 0, 1.0), ("P", "b_hi", 11.75, 2.5, 1.155, 1.0, 10, 1.0),
                                      ("P", "J1.0", 11.75, 2.5, 0.83, 1.0, 10, 1.0), ("P", "nominal", 11.75, 2.5, 1.155, 1.0, 0, 1.0),
                                      ("P", "b_lo*ms_free", 11.9, 2.5, 0.83, 1.0, 10, 1.0), ("P", "ms_free", 11.9, 2.5, 0.83, 1.0, 10, 1.0),
                                      ("F", "b_hi", 11.9, 2.5, 1.155, 1.0, 0, 1.0)):
    pl = R.member(mem, v)
    pl.k *= 1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2
    Pt, Pw = R.plant_channels(pl, F, jb, 0.0)
    Cth, Cw, Cref = R.controller(DES[W], v, F, e, kap)
    K = R.Kout(F)
    L = -K * (Cth * Pt + Cw * Pw)
    Tr = K * Cref * Pt / (1 + L)
    Lo = Tr * np.exp(-2j * np.pi * F * 0.060) * (0.01 / tau) / (1 - zf)
    pm_o = R.pm_gm(Lo, F)
    # mine
    pl2, ea = M.member(mem, v)
    pl2 = M.Plant(pl2.J, pl2.b, pl2.k * (1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2), pl2.d)
    des = M.C3R2P if W == "P" else M.C3R2F
    Lm, KCP = M.loop_L(des, pl2, v, e=e + ea, kappa=kap, jb=jb)
    w = 2 * np.pi * M.F
    Lom = KCP / (1 + Lm) * np.exp(-1j * w * 0.06) * (0.01 / tau) / (1 - np.exp(-1j * w * 0.01))
    mine = M.pm_gm(Lom)
    out.append(f"{W} {mem:13s} @{v} a{a} k{kap} jb{jb:.3f} e{e} tau {tau}: c3r1-code outer PM {pm_o[0]:.1f} GM {pm_o[2]:.1f} dB | "
               f"mine outer PM {mine[0]:.1f} GM {mine[2]:.1f} dB")
    print(out[-1], flush=True)
(M.OUT / "xcheck_out.txt").write_text("\n".join(out), encoding="utf-8")
