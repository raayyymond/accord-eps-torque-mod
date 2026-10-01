# -*- coding: utf-8 -*-
"""exp1c: operating-point GATE-2 with the REFUTER'S bar logic (single corner at e0 -> 45; aged singles + all combined -> 30).
Find the HIGHEST Ki that clears all CREDIBLE members (ms_free ruled report-only, J~2 > ident 1.3). raised520 table."""
import math,os,sys
from pathlib import Path
from multiprocessing import Pool
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
import numpy as np
HERE=Path(__file__).resolve().parent; C3R1=HERE.parents[1]/"refute_stability"/"c3r1"
sys.path.insert(0,str(C3R1)); import c3r1_model as M,c3r1_sweep as S,c3r1_kop as K
D=M.designs(); CP=tuple(D["C3-P"].rows)
def rd(rows,g):
    r=[list(x) for x in rows]; j=[i for i,x in enumerate(r) if x[0]==2707][0]; r[j][1]=g
    def sl(i):
        n=(r[i+1][1]-r[i][1])*4096; d=r[i+1][0]-r[i][0]; q=abs(n)//abs(d); return -q if n<0 else q
    r[j-1][2]=sl(j-1); r[j][2]=sl(j); return tuple(tuple(x) for x in r)
ROWS=rd(CP,520)
CRED_S=("nominal","J_lo","J_hi","b_lo","b_hi","tau0","tau6","mode13","mode20")  # credible singles (NO ms_free)
CRED_C=("b_lo*J_hi","b_lo*tau6","J1.0","b_q","b_q*J_hi","b_q*J1.0","b_q*tau6")   # credible combined (NO ms_free combos)
MSF=("ms_free","b_lo*ms_free","b_q*ms_free")
AS=(1.0,1.5,2.0,2.5); SP=[round(v,1) for v in np.arange(8.0,26.91,0.5)]+[11.9,17.0,26.9]
FRS=[f for f in S.FRAMES if f[0] in ("nom","FA.83","FA1.155","FB.83","FB1.155")]; F=S.F
def des(ki): return M.Design("X","fresh",112.0,float(ki),48.0,ROWS)
def work(a):
    ki,mem=a; dd=des(ki)
    worst_e0=math.inf; worst_other=math.inf; ate0=None; ato=None
    for v in SP:
        for aa in AS:
            th=K.theta_op(v,aa); s2=1-math.tanh(th/K.sat(v))**2; pl=M.member(mem,v); pl.k*=s2
            for fn,kap,jb in FRS:
                Pt,Pw=M.plant_channels(pl,F,jb,0.0)
                for e in (0,10):
                    Cth,Cw,_=M.controller(dd,v,F,e,kap,noI=False)
                    PM,FC,GM=M.pm_gm(-M.Kout(F)*(Cth*Pt+Cw*Pw),F)
                    single_e0=(mem in CRED_S and e==0)
                    if single_e0:
                        if PM<worst_e0: worst_e0=PM; ate0=(v,aa,fn)
                    else:
                        if PM<worst_other: worst_other=PM; ato=(v,aa,fn,e)
    return (ki,mem,round(worst_e0,1),ate0,round(worst_other,1),ato)
if __name__=="__main__":
    jobs=[(ki,m) for ki in (56,48,44,40,36,32) for m in CRED_S+CRED_C+MSF]
    with Pool(14) as p: R=p.map(work,jobs,chunksize=1)
    for ki in (56,48,44,40,36,32):
        rows=[r for r in R if r[0]==ki]
        cred=[r for r in rows if r[1] in CRED_S+CRED_C]
        # single-e0 bar 45 (only credible singles have e0 entries that matter); other bar 30
        e0fail=[r for r in cred if r[1] in CRED_S and r[2]<45]
        otherfail=[r for r in cred if r[4]<30]
        w_e0=min((r for r in cred if r[1] in CRED_S),key=lambda r:r[2])
        w_ot=min(cred,key=lambda r:r[4])
        msf_ot=min([r for r in rows if r[1] in MSF],key=lambda r:r[4])
        print(f"Ki {ki:3d}: CRED single-e0 min {w_e0[2]:5.1f}({w_e0[1]}) {'OK' if not e0fail else 'FAIL '+str([r[1] for r in e0fail])}"
              f" | CRED other(aged+comb) min {w_ot[4]:5.1f}({w_ot[1]}@{w_ot[5]}) {'OK' if not otherfail else 'FAIL '+str([(r[1],r[4]) for r in otherfail])}"
              f" || ms_free other min {msf_ot[4]:.1f}({msf_ot[1]})")
