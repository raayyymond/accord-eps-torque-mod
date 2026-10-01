# -*- coding: utf-8 -*-
"""g_explore1.py -- the first exploration (designer G): PM at the binding members of round 2 vs a Kd multiplier, a G
scale and Ki, on the stability refuter's engine c2r2_model with rev2-A P2 as the base.  Shared PM formula (no leading
crossings occur at these G).  ANALYSIS ONLY.  usage: python g_explore1.py  -> g_explore1_out.txt"""
import sys
from dataclasses import replace
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "refute_stability" / "c2r2"))
import c2r2_model as M
import numpy as np
D = M.load_designs()
P2 = D['P2']
def pm(des, m, v, kd_scale=1.0, gs=1.0, ki=None):
    d2 = replace(des)
    G0 = des.G(v)
    d2.G = (lambda vv, G0=G0: G0*gs)
    if ki is not None: d2.ki = ki
    pl = M.member(m, v)
    r,_ = M.lti_metrics(d2, pl, v, kd_scale=kd_scale)
    return r['pm'], r['fc'], r['gm_up']
for m,v in (('b_q*ms_free+h10',15.75),('b_q*ms_free',15.75),('b_lo*ms_free',10.5),('J_hi',1.0),('J_hi+h10',1.0),('ms_free+h10',9.0),('b_q*J1.0+h10',15.5),('b_lo*J_hi*tau6+h10',8.0)):
    print(m, v, 'G', P2.G(v))
    for kds in (0.83,1.0,1.155,1.4,1.7,2.0):
        row=[]
        for gs in (1.0,0.8,0.6):
            p,f,g = pm(P2,m,v,kd_scale=kds,gs=gs)
            row.append(f'gs{gs}:{p:5.1f}@{f:4.2f} gm{g:4.1f}')
        print(f'  kd x{kds}: '+' | '.join(row))
    for ki in (56,40,28,0):
        p,f,g = pm(P2,m,v,ki=ki)
        print(f'  ki {ki}: PM {p:5.1f}@{f:4.2f} gm{g:4.1f}')
