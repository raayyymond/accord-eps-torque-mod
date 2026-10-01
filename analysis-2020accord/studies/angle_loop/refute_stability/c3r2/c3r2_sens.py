# -*- coding: utf-8 -*-
"""c3r2_sens.py -- how robust is the declared 'rho < 1' of the ms_free family (and the margins of the gated binding members)
to modelling choices the brief leaves open?  At each design's binding points: the motor-rate sample as an instantaneous
velocity vs a 1-tick backward difference; +1 ms transport; sat(v) x0.9 / x1.1 (sat is the prior, BELIEF); lateral
accel past the design's a <= 2.5 envelope (2.75 / 3.0); the speed at a 0.05 grid around the binding speed.
-> sens_out.txt"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FA1.155": (1.155, 1.0), "FB.83": (0.83, 1 / 1.155),
      "FB1.155": (1.155, 1 / 1.155), "FAc": (1 / 1.155, 1.0)}


def pt(des, mem, v, a, fr, e, satx=1.0, wmode="inst", xd=0):
    pl0, ea = M.member(mem, v)
    s2 = 1 - math.tanh(M.theta_op(v, a) / (M.sat(v) * satx)) ** 2 if a else 1.0
    pl = M.Plant(pl0.J, pl0.b, pl0.k * s2, pl0.d + xd, pl0.mode)
    kap, jb = FR[fr]
    L, _ = M.loop_L(des, pl, v, e=e + ea, kappa=kap, jb=jb)
    PM = M.pm_gm(L)[0]
    rho, f, z = M.Periodic(des, pl, v, e=e + ea, kappa=kap, jb=jb, wmode=wmode).rho_ring()
    return PM, rho, f, z


out = []
P = out.append
CASES = [("b_lo*ms_free", 11.9, "FA.83", 10), ("b_q*ms_free", 12.5, "FA.83", 10), ("ms_free", 11.9, "FA.83", 10),
         ("ms_free", 11.9, "nom", 0), ("b_lo*J_hi", 8.0, "FB.83", 10), ("J1.0", 8.0, "FA.83", 10),
         ("b_q*J1.0", 12.5, "FA.83", 10), ("J_hi", 8.0, "FB.83", 10), ("b_hi", 11.75, "FA.83", 0)]
for des in (M.C3R2P, M.C3R2F):
    P(f"== {des.name} ==")
    for mem, v, fr, e in CASES:
        base = pt(des, mem, v, 2.5, fr, e)
        P(f"  {mem:13s} @{v} a2.5 {fr} e{e}: base PM {base[0]:5.1f} rho {base[1]:.5f} ({base[2]:.2f} Hz z{base[3]:+.3f})")
        for lab, kw in (("w = 1-tick backward diff", dict(wmode="bd1")), ("+1 ms transport", dict(xd=1)),
                        ("sat x0.9", dict(satx=0.9)), ("sat x1.1", dict(satx=1.1))):
            r = pt(des, mem, v, 2.5, fr, e, **kw)
            P(f"      {lab:26s} PM {r[0]:5.1f} rho {r[1]:.5f} ({r[2]:.2f} Hz z{r[3]:+.3f})" + ("   <<< rho>=1" if r[1] >= 1 else ""))
        for a in (2.75, 3.0):
            r = pt(des, mem, v, a, fr, e)
            P(f"      a = {a:<22} PM {r[0]:5.1f} rho {r[1]:.5f} ({r[2]:.2f} Hz z{r[3]:+.3f}) th_op {M.theta_op(v, a):.0f} deg"
              + ("   <<< rho>=1" if r[1] >= 1 else ""))
    # fine speed scan of the worst ms_free product, a 2.5, every gated frame / e
    best = (0, None)
    for mem in ("b_lo*ms_free", "b_q*ms_free", "ms_free"):
        for v in np.arange(10.5, 14.01, 0.05):
            for fr in ("FA.83", "FB.83", "nom", "FA1.155", "FB1.155"):
                for e in (-1, 0, 10):
                    r = pt(des, mem, float(v), 2.5, fr, e)
                    if r[1] > best[0]:
                        best = (r[1], (mem, round(float(v), 2), fr, e, r))
    P(f"  fine scan max rho (a 2.5, v 10.5..14 @0.05, gated frames, e -1/0/10): {best[0]:.5f} at {best[1]}")
txt = "\n".join(out)
(M.OUT / "sens_out.txt").write_text(txt, encoding="utf-8")
print(txt)
