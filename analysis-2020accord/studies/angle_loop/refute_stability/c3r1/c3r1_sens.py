# -*- coding: utf-8 -*-
"""c3r1_sens.py -- sensitivity of the binding points to the two sensor facts the scorers do not model: the rate-former
lag (resolver-delta window mean, rf 0.5 / 1.5 / 3 ms) and a one-tick-late fresh read (C3-P), plus the PI-only (rate
invalid, D = 0) loop and a gain ladder (fade) for PID / PD at the binding points.
python c3r1_sens.py -> _scratch/.../sens_out.txt"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_kop as K  # noqa: E402

D = M.designs()
S_C = 1.155
FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FB.83": (0.83, 1 / S_C), "FA1.155": (1.155, 1.0), "FB1.155": (1.155, 1 / S_C)}
PTS = [("C3-P", "b_q*J1.0", 26.9, 10, "FB.83", 0.0), ("C3-P", "b_lo*ms_free", 9.0, 10, "FA.83", 0.0),
       ("C3-P", "b_q*ms_free", 15.75, 10, "FA.83", 0.0), ("C3-P", "J_hi", 1.0, 0, "FA.83", 0.0),
       ("C3-P", "J_hi", 1.0, 10, "FA.83", 0.0),
       ("C3-P", "ms_free", 12.0, 0, "nom", 2.0), ("C3-P", "ms_free", 12.0, 0, "FA.83", 1.5),
       ("C3-P", "b_lo*ms_free", 12.0, 0, "FA.83", 2.5),
       ("C3-F", "b_q*J1.0", 27.0, 10, "FB.83", 0.0), ("C3-F", "b_lo*ms_free", 8.75, 10, "FB.83", 0.0),
       ("C3-F", "J_hi", 1.0, 0, "FA.83", 0.0), ("C3-F", "ms_free", 12.0, 0, "nom", 2.0)]
out = []
P = lambda *a: (out.append(" ".join(str(x) for x in a)), print(out[-1], flush=True))  # noqa: E731


def plant_at(mem, v, a):
    pl = M.member(mem, v)
    if a > 0:
        pl.k *= 1 - math.tanh(K.theta_op(v, a) / K.sat(v)) ** 2
    return pl


P("(1) rate-former window rf (ms) and a one-tick-late fresh read: PM (LTI) and exact rho at the binding points")
for dn, mem, v, e, fr, a in PTS:
    kap, jb = FR[fr]
    pl = plant_at(mem, v, a)
    row = []
    for rf in (0.0, 0.5, 1.5, 3.0):
        L, *_ = M.loop(D[dn], pl, v, e=e, kappa=kap, jb=jb, rf_ms=rf)
        row.append(f"rf{rf}:{M.pm_gm(L)[0]:5.1f}")
    if dn == "C3-P":
        L, *_ = M.loop(D[dn], pl, v, e=e, kappa=kap, jb=jb, abe_late=1)
        row.append(f"late1:{M.pm_gm(L)[0]:5.1f}")
        L, *_ = M.loop(D[dn], pl, v, e=e, kappa=kap, jb=jb, abe_late=1, rf_ms=1.5)
        row.append(f"late1+rf1.5:{M.pm_gm(L)[0]:5.1f}")
    P(f"  {dn} {mem}@{v} e{e} {fr} a{a}: " + "  ".join(row))

P("\n(2) gain ladder (the fade / grab-rate / hands-on floors): exact rho of PID and PD at each gain")
for dn, mem, v, e, fr, a in PTS:
    kap, jb = FR[fr]
    pl = plant_at(mem, v, a)
    s = []
    for noI in (False, True):
        rr = [M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb, noI=noI, fade=g).rho_ring()[0]
              for g in (0.05, 0.1, 0.2, 76 / 254, 0.5, 204 / 254, 1.0, 1.5, 2.0)]
        s.append(("PD " if noI else "PID") + " " + " ".join(f"{x:.4f}" for x in rr))
    P(f"  {dn} {mem}@{v} e{e} {fr} a{a}: gains 0.05/0.1/0.2/0.297/0.5/0.80/1/1.5/2 -> " + " | ".join(s))

P("\n(3) rate-invalid state (D = 0, Honda's guard): PM / exact rho over speed, nominal and J_hi, e0, kappa irrelevant")
for dn in ("C3-P", "C3-F"):
    for mem in ("nominal", "J_hi", "b_lo", "ms_free", "b_q*J1.0"):
        worst = (math.inf, None)
        nun = 0
        for v in np.arange(1.0, 35.01, 1.0):
            pl = M.member(mem, v)
            L, *_ = M.loop(D[dn], pl, v, e=0, kd_scale=0.0)
            pm = M.pm_gm(L)[0]
            rho = M.Periodic(D[dn], pl, v, e=0, kd_scale=0.0).rho_ring()[0]
            nun += rho >= 1
            if pm < worst[0]:
                worst = (pm, v, rho)
        P(f"  {dn} {mem:9s} D=0: min PM {worst[0]:6.1f} at {worst[1]} m/s (rho {worst[2]:.4f}); unstable speeds: {nun}/35")
(Path(M.OUT) / "sens_out.txt").write_text("\n".join(out), encoding="utf-8")
