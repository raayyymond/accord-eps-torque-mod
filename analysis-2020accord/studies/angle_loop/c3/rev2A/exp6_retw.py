# -*- coding: utf-8 -*-
"""exp6_retw.py -- F4: Re(T/omega) (controller torque per deg/s of motor rate; >0 damps) at the PHYSICAL kappa (0.866)
and at ages 0-9 AND 1-10, for R1-P (Ki40, raised dip, Kd48 fresh) vs V295 vs C3-P. Uses the refuter's own retw()."""
import os,sys
from pathlib import Path
import numpy as np
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent; C3R1=HERE.parents[1]/"refute_stability"/"c3r1"
sys.path.insert(0,str(C3R1)); import c3r1_model as M
D=M.designs(); CP=tuple(D["C3-P"].rows)
def rd(rows,g):
    r=[list(x) for x in rows]; j=[i for i,x in enumerate(r) if x[0]==2707][0]; r[j][1]=g
    def sl(i):
        n=(r[i+1][1]-r[i][1])*4096; d=r[i+1][0]-r[i][0]; q=abs(n)//abs(d); return -q if n<0 else q
    r[j-1][2]=sl(j-1); r[j][2]=sl(j); return tuple(tuple(x) for x in r)
R1=M.Design("R1-P","fresh",112.0,40.0,48.0,rd(CP,520))
FR=[5,7,10,13,15,17,20,25]; SPD=np.arange(1.0,35.01,1.0)
def worst(des,fq,kappa,e):
    # worst (most negative = most anti-damping) over speed, per the refuter's retw
    return min(float(np.atleast_1d(M.retw(des,v,fq,e=e,kappa=kappa))[0]) for v in SPD)
print("Re(T/omega), worst over 1-35 m/s (>0 damps; <0 anti-damps)")
for kap,ages,elabel in ((0.866,(1,10),"kappa 0.866, ages 1-10"),(0.866,(0,9),"kappa 0.866, ages 0-9"),(1.0,(1,10),"kappa 1.0, ages 1-10")):
    e=ages[0]-1  # Hhold(f,e): e=-1 ages 0..9, e=0 ages 1..10
    print(f"\n-- {elabel} (e={e}) --")
    print("  Hz : "+" ".join(f"{f:>6}" for f in FR))
    for nm,des in (("V295",D["V295"]),("C3-P",D["C3-P"]),("R1-P",R1)):
        vals=[worst(des,f,kap,e) for f in FR]
        print(f"  {nm:5}: "+" ".join(f"{v:6.2f}" for v in vals))
    # ratio R1-P / V295 at 13 and 20 Hz
    for f in (13,20):
        r1=worst(R1,f,kap,e); v295=worst(D["V295"],f,kap,e)
        print(f"   {f}Hz R1-P/V295 = {r1/v295:.2f}x (R1 {r1:.2f}, V295 {v295:.2f})")
