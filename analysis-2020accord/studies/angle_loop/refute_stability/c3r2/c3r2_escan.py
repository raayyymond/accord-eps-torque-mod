# -*- coding: utf-8 -*-
"""c3r2_escan.py -- every hold offset e = -1..10 (age windows 0-9 .. 11-20) at the binding points (theta = 0 and a 2.5),
to confirm the e in {-1, 0, 10} sweep brackets the worst.  -> escan_out.txt"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
FR = {"FA.83": (0.83, 1.0), "FB.83": (0.83, 1 / 1.155), "nom": (1.0, 1.0)}
CASES = [("b_lo*ms_free", 11.9, 2.5, "FA.83"), ("b_q*ms_free", 12.5, 2.5, "FA.83"), ("ms_free", 11.9, 2.5, "FA.83"),
         ("b_lo*J_hi", 8.0, 2.5, "FB.83"), ("J1.0", 8.0, 2.5, "FA.83"), ("J_hi", 8.0, 2.5, "FB.83"),
         ("b_q*J1.0", 26.9, 0.0, "FB.83"), ("b_lo*ms_free", 11.9, 0.0, "FA.83"), ("J_hi", 1.0, 0.0, "FA.83")]
out = []
for des in (M.C3R2P, M.C3R2F):
    out.append(f"== {des.name}: PM (rho) per hold offset e = -1..10 ==")
    for mem, v, a, fr in CASES:
        pl0, ea = M.member(mem, v)
        s2 = 1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2 if a else 1.0
        pl = M.Plant(pl0.J, pl0.b, pl0.k * s2, pl0.d, pl0.mode)
        kap, jb = FR[fr]
        row = []
        for e in range(-1, 11):
            L, _ = M.loop_L(des, pl, v, e=e, kappa=kap, jb=jb)
            rho = M.Periodic(des, pl, v, e=e, kappa=kap, jb=jb).rho_ring()[0]
            row.append(f"{M.pm_gm(L)[0]:.1f}({rho:.4f})")
        out.append(f"  {mem:13s} @{v} a{a} {fr}: " + " ".join(row))
txt = "\n".join(out)
(M.OUT / "escan_out.txt").write_text(txt, encoding="utf-8")
print(txt)
