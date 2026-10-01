# -*- coding: utf-8 -*-
"""c3r2_validate.py -- positive controls for c3r2_model against the published anchors (round-1 C3 at Ki 56 / G-P48, and
rev2-B's Ki-40 op-point numbers).  Output: _scratch/angle_loop/refute-c3r2-stability/validate_out.txt"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FA1.155": (1.155, 1.0), "FB.83": (0.83, 1 / 1.155),
      "FB1.155": (1.155, 1 / 1.155)}
out = []


def pm_at(des, mem, v, a, fr, e):
    pl, ea = M.member(mem, v)
    if a:
        pl.k *= 1 - math.tanh(M.theta_op(v, a) / M.sat(v)) ** 2
    kap, jb = FR[fr]
    L, _ = M.loop_L(des, pl, v, e=e + ea, kappa=kap, jb=jb)
    PM, FC, gmu, gmd = M.pm_gm(L)
    P = M.Periodic(des, pl, v, e=e + ea, kappa=kap, jb=jb)
    rho, fr_, z = P.rho_ring()
    return PM, FC, gmu, rho, fr_, z


def worst(des, mem, v, a, frs=FR, es=(-1, 0, 10)):
    r = []
    for fr in frs:
        for e in es:
            PM, FC, gmu, rho, f, z = pm_at(des, mem, v, a, fr, e)
            r.append((PM, fr, e, rho, f, z))
    return min(r)


A = [  # (des, member, v, a, frame, e, published PM, source)
    (M.C3P56, "ms_free", 12.0, 2.0, "nom", 0, 24.4, "C3-r1 F1 table / Ki probe"),
    (M.C3P56, "ms_free", 12.0, 2.5, "nom", 0, 15.1, "C3-r1 Ki probe"),
    (M.C3P56, "b_lo*ms_free", 12.0, 2.5, "FA.83", 0, 3.6, "C3-r1 Ki probe (|signed PM| -3.6, rho 1.0008 0.57 Hz)"),
    (M.C3P56, "b_q*J1.0", 26.9, 0.0, "FA.83", 0, 40.6, "C3-r1 Ki probe (theta = 0)"),
    (M.C3P56, "J_hi", 1.0, 0.0, "FA.83", 0, 51.7, "C3-r1 sec 1.2"),
    (M.C3P56, "J_hi+h10", None, 0.0, None, 0, 47.1, "C3-r1 sec 1.2 (min over v, frames)"),
    (M.C3P56, "b_q*J1.0+h10", 26.9, 0.0, "FB.83", 0, 34.2, "C3-r1 sec 1.2"),
]
out.append("== anchors (round-1 C3-P, Ki 56, G-P48) ==")
for des, mem, v, a, fr, e, pub, src in A:
    if v is None:
        best = min((pm_at(des, mem, vv, a, f, e)[0], vv, f) for vv in [x / 4 for x in range(4, 141)] for f in FR)
        out.append(f"  {mem:14s} min over v/frames  mine {best[0]:6.1f} at {best[1]} {best[2]}   published {pub}   [{src}]")
        continue
    PM, FC, gmu, rho, f, z = pm_at(des, mem, v, a, fr, e)
    out.append(f"  {mem:14s} @{v} a{a} {fr:6s} e{e}: mine PM {PM:6.1f} fc {FC:.2f} Hz rho {rho:.4f} ring {f:.2f} Hz "
               f"zeta {z:+.3f}   published {pub}   [{src}]")

out.append("== rev2-B opbreak Ki 40 anchors (worst over 5 frames x e in {-1,0,10}) ==")
B = [(M.C3R2P, "J_hi", 8.0, 2.5, 48.6), (M.C3R2P, "b_hi", 11.9, 2.5, 48.5), (M.C3R2P, "b_lo*J_hi", 8.0, 2.5, 32.8),
     (M.C3R2P, "J1.0", 8.0, 2.5, 34.7), (M.C3R2P, "ms_free", 11.9, 2.5, 21.2),
     (M.C3R2P, "b_lo*ms_free", 11.9, 2.5, 4.6), (M.C3R2P, "b_q*ms_free", 12.5, 2.5, 8.2),
     (M.C3R2F, "b_lo*ms_free", 11.9, 2.5, 1.1), (M.C3R2F, "b_q*J1.0", 12.5, 2.5, 30.3)]
for des, mem, v, a, pub in B:
    PM, fr, e, rho, f, z = worst(des, mem, v, a)
    out.append(f"  {des.name:10s} {mem:14s} @{v} a{a}: mine worst PM {PM:6.1f} ({fr}, e{e}) rho {rho:.4f} ring {f:.2f} Hz "
               f"zeta {z:+.3f}   published {pub}")

txt = "\n".join(out)
(M.OUT / "validate_out.txt").write_text(txt, encoding="utf-8")
print(txt)
