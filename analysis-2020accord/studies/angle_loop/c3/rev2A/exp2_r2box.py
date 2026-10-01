# -*- coding: utf-8 -*-
"""exp2_r2box.py -- rev2A: does lower Ki + raised-dip table keep the R2-box (theta=0) GATE-2 clean and M20 <= V295?
Reuses the refuter's model. PID + PI.D0 (rate-invalid-as-written=D0) loops, credible set + ms_free, frames box,
hold ages -1..10, speed grid. Reports PM fails (<45 single e0 / <30 else), min PM, worst M20, peak |T| 5-30."""
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

D=M.designs()
CP_ROWS=tuple(D["C3-P"].rows)
def raise_dip(rows,newG=540):
    r=[list(x) for x in rows]; j=[i for i,x in enumerate(r) if x[0]==2707][0]; r[j][1]=newG
    def sl(i):
        num=(r[i+1][1]-r[i][1])*4096; den=r[i+1][0]-r[i][0]; q=abs(num)//abs(den); return -q if num<0 else q
    r[j-1][2]=sl(j-1); r[j][2]=sl(j); return tuple(tuple(x) for x in r)
TBLS={"C3-P":CP_ROWS,"raised540":raise_dip(CP_ROWS,540),"raised520":raise_dip(CP_ROWS,520)}
MEMBERS=S.SINGLE+S.COMBINED   # credible + the two ms_free combos
SP=sorted(set([round(x,2) for x in np.arange(2.0,32.01,1.0)]+[3.1,8.0,11.9,17.0,26.9]
              +[round(x,2) for x in np.arange(9.0,13.01,0.25)]))
FRAMES=[f for f in S.FRAMES if f[0] in ("nom","FA.83","FA1.155","FB.83","FB1.155")]
ES=tuple(range(-1,11))
F=S.F; I20=int(np.argmin(abs(F-20.0))); B530=(F>=5)&(F<=30)
KIS=(24,20)
def des(ki,rows): return M.Design("X","fresh",kp=112.0,ki=float(ki),kd=48.0,rows=rows)

def work(args):
    tname,ki,mem=args
    dd=des(ki,TBLS[tname]); DV=D["V295"]
    sfail=0; cfail=0; minpm=math.inf; at=None; worstl20=0.0; worstpk=-99.0
    for v in SP:
        pl=M.member(mem,v)
        chans={jb:M.plant_channels(pl,F,jb,0.0) for jb in sorted(set(f[2] for f in FRAMES))}
        for e in ES:
            CthV,CwV,_=M.controller(DV,v,F,e,1.0)
            for fn,kap,jb in FRAMES:
                Pt,Pw=chans[jb]
                Cth,Cw,_=M.controller(dd,v,F,e,kap,noI=False)
                L=-M.Kout(F)*(Cth*Pt+Cw*Pw)
                PM,FC,GM=M.pm_gm(L,F)
                Sx=1/(1+L)
                pk=20*math.log10(max(np.abs(L*Sx)[B530].max(),1e-9))
                LV=-M.Kout(F)*kap*(CwV*Pw)
                l20=abs(L[I20])/abs(LV[I20])
                single=(mem in S.SINGLE and e==0)
                bar=45 if single else 30
                if PM<bar:
                    if single: sfail+=1
                    else: cfail+=1
                if PM<minpm: minpm=PM; at=(v,e,fn,round(FC,2))
                worstl20=max(worstl20,l20); worstpk=max(worstpk,pk)
    return (tname,ki,mem,sfail,cfail,minpm,at,worstl20,worstpk)

if __name__=="__main__":
    jobs=[(t,ki,m) for t in TBLS for ki in KIS for m in MEMBERS]
    with Pool(14) as p:
        R=p.map(work,jobs,chunksize=1)
    for t in TBLS:
        gmin=min(M.walk_G(TBLS[t],vw) for vw in range(0,12001))
        print(f"\n=== table {t} (dip min G={gmin}) ===")
        for ki in KIS:
            rows=[r for r in R if r[0]==t and r[1]==ki]
            sf=sum(r[3] for r in rows); cf=sum(r[4] for r in rows)
            wm=min(rows,key=lambda r:r[5]); wl=max(rows,key=lambda r:r[7]); wp=max(rows,key=lambda r:r[8])
            print(f"  Ki {ki}: R2box PM fails single {sf} combined {cf} | min PM {wm[5]:.1f} ({wm[2]}@v{wm[6][0]} e{wm[6][1]} {wm[6][2]} fc{wm[6][3]})")
            print(f"         worst M20 {wl[7]:.3f} ({wl[2]}) | worst peak|T|5-30 {wp[8]:.2f} dB ({wp[2]})")
            # list any failing member
            for r in rows:
                if r[3] or r[4]:
                    print(f"           FAIL {r[2]}: single {r[3]} comb {r[4]} minPM {r[5]:.1f}")
