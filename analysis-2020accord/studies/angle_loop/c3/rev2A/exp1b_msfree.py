# -*- coding: utf-8 -*-
"""exp1b: operating-point min PM for ms_free members + worst credible-combined, across Ki x dip height."""
import math, os, sys
from pathlib import Path
from multiprocessing import Pool
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
import numpy as np
HERE=Path(__file__).resolve().parent; C3R1=HERE.parents[1]/"refute_stability"/"c3r1"
sys.path.insert(0,str(C3R1))
import c3r1_model as M, c3r1_sweep as S, c3r1_kop as K
D=M.designs(); CP=tuple(D["C3-P"].rows)
def rd(rows,g):
    r=[list(x) for x in rows]; j=[i for i,x in enumerate(r) if x[0]==2707][0]; r[j][1]=g
    def sl(i):
        n=(r[i+1][1]-r[i][1])*4096; d=r[i+1][0]-r[i][0]; q=abs(n)//abs(d); return -q if n<0 else q
    r[j-1][2]=sl(j-1); r[j][2]=sl(j); return tuple(tuple(x) for x in r)
TBLS={"orig462":CP,"r512":rd(CP,512),"r520":rd(CP,520)}
MEMS=("ms_free","b_lo*ms_free","b_q*ms_free","b_lo*J_hi","b_q*J1.0","J1.0")
AS=(1.0,1.5,2.0,2.5); SP=[round(v,1) for v in np.arange(8.0,26.91,0.5)]+[11.9,17.0,26.9]
FRS=[f for f in S.FRAMES if f[0] in ("nom","FA.83")]; F=S.F
def des(ki,rows): return M.Design("X","fresh",112.0,float(ki),48.0,rows)
def work(a):
    t,ki,m=a; dd=des(ki,TBLS[t]); mn=math.inf; at=None
    for v in SP:
        for aa in AS:
            th=K.theta_op(v,aa); s2=1-math.tanh(th/K.sat(v))**2; pl=M.member(m,v); pl.k*=s2
            for fn,kap,jb in FRS:
                Pt,Pw=M.plant_channels(pl,F,jb,0.0)
                for e in (0,10):
                    Cth,Cw,_=M.controller(dd,v,F,e,kap,noI=False)
                    PM,FC,GM=M.pm_gm(-M.Kout(F)*(Cth*Pt+Cw*Pw),F)
                    if PM<mn: mn=PM; at=(v,aa,fn,e)
    return (t,ki,m,round(mn,1),at)
if __name__=="__main__":
    jobs=[(t,ki,m) for t in TBLS for ki in (24,20,18,16) for m in MEMS]
    with Pool(14) as p: R=p.map(work,jobs,chunksize=1)
    for t in TBLS:
        print(f"\n=== {t} ===")
        for ki in (24,20,18,16):
            row={r[2]:r[3] for r in R if r[0]==t and r[1]==ki}
            print(f"  Ki {ki}: msf {row['ms_free']:5.1f}  blo*msf {row['b_lo*ms_free']:5.1f}  bq*msf {row['b_q*ms_free']:5.1f}"
                  f"  || blo*Jhi {row['b_lo*J_hi']:5.1f}  bq*J1.0 {row['b_q*J1.0']:5.1f}  J1.0 {row['J1.0']:5.1f}")
