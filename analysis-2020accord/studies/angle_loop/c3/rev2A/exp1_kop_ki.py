# -*- coding: utf-8 -*-
"""exp1_kop_ki.py -- REVISER-1 rev2A: F1 (stability) resolution probe (parallel, refuter's own S.F grid).
Operating-point GATE-2 PM (plant stiffness k*sech^2(theta_op/sat)) vs Ki and vs the raised-dip table."""
import math, os, sys
from pathlib import Path
from multiprocessing import Pool
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
import numpy as np
HERE=Path(__file__).resolve().parent
C3R1=HERE.parents[1]/"refute_stability"/"c3r1"
sys.path.insert(0,str(C3R1))
import c3r1_model as M
import c3r1_sweep as S
import c3r1_kop as K

D=M.designs()
CP_ROWS=tuple(D["C3-P"].rows)
def raise_dip(rows, newG=540):
    r=[list(x) for x in rows]
    j=[i for i,x in enumerate(r) if x[0]==2707][0]
    r[j][1]=newG
    def slope(i):
        num=(r[i+1][1]-r[i][1])*4096; den=r[i+1][0]-r[i][0]
        q=abs(num)//abs(den); return -q if (num<0) else q
    r[j-1][2]=slope(j-1); r[j][2]=slope(j)
    return tuple(tuple(x) for x in r)
RAISED=raise_dip(CP_ROWS,540)
SINGLE_DEC=("b_hi","J_hi","ms_free")
COMB_DEC=("J1.0","b_q*J1.0","b_q*J_hi","b_lo*J_hi","b_lo*ms_free","b_q*ms_free")
AS=(1.0,1.5,2.0,2.5)
SP=[round(v,1) for v in np.arange(8.0,26.91,1.0)]+[11.9,17.0,26.9]
FRS=[f for f in S.FRAMES if f[0] in ("nom","FA.83")]
F=S.F
KIS=(56,36,28,24,20)
TBLS={"C3-P":CP_ROWS,"raised540":RAISED}

def des(ki,rows): return M.Design("X","fresh",kp=112.0,ki=float(ki),kd=48.0,rows=rows)

def work(args):
    tname,ki,mem=args
    rows=TBLS[tname]; dd=des(ki,rows)
    mn=math.inf; at=None
    for v in SP:
        for a in AS:
            th=K.theta_op(v,a); s2=1-math.tanh(th/K.sat(v))**2
            pl=M.member(mem,v); pl.k*=s2
            for fn,kap,jb in FRS:
                Pt,Pw=M.plant_channels(pl,F,jb,0.0)
                for e in (0,10):
                    Cth,Cw,_=M.controller(dd,v,F,e,kap,noI=False)
                    L=-M.Kout(F)*(Cth*Pt+Cw*Pw)
                    PM,FC,GM=M.pm_gm(L,F)
                    if PM<mn: mn=PM; at=(v,a,fn,e,round(FC,2))
    return (tname,ki,mem,mn,at)

if __name__=="__main__":
    jobs=[(t,ki,m) for t in TBLS for ki in KIS for m in (SINGLE_DEC+COMB_DEC)]
    with Pool(14) as p:
        R=p.map(work,jobs,chunksize=2)
    for t in TBLS:
        gmin=min(M.walk_G(TBLS[t],vw) for vw in range(0,12001))
        print(f"\n=== table {t}  (dip min G 0..12000 = {gmin}) ===")
        for ki in KIS:
            rows=[r for r in R if r[0]==t and r[1]==ki]
            sing=[r for r in rows if r[2] in SINGLE_DEC]
            comb=[r for r in rows if r[2] in COMB_DEC]
            sc=[r for r in sing if r[2]!="ms_free"]; cc=[r for r in comb if "ms_free" not in r[2]]
            ws=min(sing,key=lambda r:r[3]); wsc=min(sc,key=lambda r:r[3])
            wc=min(comb,key=lambda r:r[3]); wcc=min(cc,key=lambda r:r[3])
            print(f"  Ki {ki:3d}: SINGLE all {ws[3]:5.1f} ({ws[2]}@{ws[4]}) cred {wsc[3]:5.1f} ({wsc[2]}@{wsc[4]}) "
                  f"| COMB all {wc[3]:5.1f} ({wc[2]}@{wc[4]}) cred {wcc[3]:5.1f} ({wcc[2]}@{wcc[4]})")
        # per-member table at Ki 28 and 24
        for ki in (28,24):
            print(f"  -- per-member at Ki {ki}:")
            for m in SINGLE_DEC+COMB_DEC:
                r=[x for x in R if x[0]==t and x[1]==ki and x[2]==m][0]
                print(f"       {m:14s} minPM {r[3]:5.1f} at v{r[4][0]} a{r[4][1]} {r[4][2]} e{r[4][3]} fc{r[4][4]}")
