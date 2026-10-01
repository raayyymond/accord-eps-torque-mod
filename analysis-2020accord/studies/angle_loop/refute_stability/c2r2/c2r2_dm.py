# -*- coding: utf-8 -*-
"""c2r2_dm.py -- EXACT (lifted, LPTV) delay margin at the binding points, as a cross-check that the averaged-hold PM
is not optimistic: equivalent PM = 360 * fc * DM.  Also the exact GM.  ANALYSIS ONLY."""
import sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M
D = M.load_designs()
def mk(dn, gs):
    d = replace(D[dn]); G0 = D[dn].G; d.G = (lambda v, G0=G0, gs=gs: G0(v) * gs); return d
cases = [("P2", "base", "b_q*J1.0+h10", 26.9, 1.0, 1.0, 1.0), ("P2", "base", "b_lo*J_hi*tau6+h10", 8.0, 1.0, 1.0, 1.0),
         ("P2", "base", "J_hi", 1.0, 1.0, 1.0, 1.0),
         ("P2", "FA", "b_lo*J_hi*tau6+h10", 8.0, 0.866, 1.0, 1.0), ("P2", "FA", "J_hi", 1.0, 0.866, 1.0, 1.0),
         ("P2", "FB", "b_q*J1.0+h10", 17.5, 1.0, 1.155, 1.155), ("P2", "FB", "b_lo*J_hi*tau6+h10", 8.0, 1.0, 1.155, 1.155),
         ("F2", "FA", "b_lo*J_hi*tau6+h10", 1.0, 0.866, 1.0, 1.0), ("F2", "FB", "b_q*J1.0+h10", 15.5, 1.0, 1.155, 1.155),
         ("B0r", "FB", "b_q*J1.0+h10", 17.5, 1.0, 1.155, 1.155), ("D2a", "FB", "b_q*J1.0+h10", 17.5, 1.0, 1.155, 1.155)]
print("design var member                 v     | avg PM  fc     | exact DM ms  -> equiv PM | exact GM dB")
for dn, var, m, v, kd, gs, ks in cases:
    des = mk(dn, gs)
    pl = M.member(m, v); pl.k *= ks
    r, _ = M.lti_metrics(des, pl, v, kd_scale=kd)
    dm = M.exact_delay_margin(des, pl, v, kd_scale=kd)
    gm = M.exact_gm_up(des, pl, v, kd_scale=kd)
    print(f"{dn:4s} {var:4s} {m:22s} {v:5.2f} | {r['pm']:5.1f}  {r['fc']:.2f} | {dm:7.2f}  -> {360 * r['fc'] * dm / 1000:5.1f} | {gm:5.1f}")
