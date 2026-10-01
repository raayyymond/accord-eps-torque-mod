import math,os,sys
from pathlib import Path
from multiprocessing import Pool
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
import numpy as np
HERE=Path(__file__).resolve().parent; C3R1=HERE.parents[1]/"refute_stability"/"c3r1"
sys.path.insert(0,str(C3R1)); import c3r1_model as M, c3r1_sweep as S
D=M.designs(); CP=tuple(D["C3-P"].rows)
def rd(rows,g):
    r=[list(x) for x in rows]; j=[i for i,x in enumerate(r) if x[0]==2707][0]; r[j][1]=g
    def sl(i):
        n=(r[i+1][1]-r[i][1])*4096; d=r[i+1][0]-r[i][0]; q=abs(n)//abs(d); return -q if n<0 else q
    r[j-1][2]=sl(j-1); r[j][2]=sl(j); return tuple(tuple(x) for x in r)
ROWS=rd(CP,520); MEMBERS=S.SINGLE+S.COMBINED
SP=sorted(set([round(x,2) for x in np.arange(2.0,32.01,1.0)]+[3.1,8.0,11.9,17.0,26.9]+[round(x,2) for x in np.arange(9.0,13.01,0.25)]))
FRAMES=[f for f in S.FRAMES if f[0] in ("nom","FA.83","FA1.155","FB.83","FB1.155")]; ES=tuple(range(-1,11))
F=S.F; I20=int(np.argmin(abs(F-20.0))); B530=(F>=5)&(F<=30)
def des(ki): return M.Design("X","fresh",112.0,float(ki),48.0,ROWS)
def work(mem):
    dd=des(18); DV=D["V295"]; sf=cf=0; mn=math.inf; at=None; wl=0.0; wp=-99
    for v in SP:
        pl=M.member(mem,v); ch={jb:M.plant_channels(pl,F,jb,0.0) for jb in sorted(set(f[2] for f in FRAMES))}
        for e in ES:
            CthV,CwV,_=M.controller(DV,v,F,e,1.0)
            for fn,kap,jb in FRAMES:
                Pt,Pw=ch[jb]; Cth,Cw,_=M.controller(dd,v,F,e,kap,noI=False)
                L=-M.Kout(F)*(Cth*Pt+Cw*Pw); PM,FC,GM=M.pm_gm(L,F); Sx=1/(1+L)
                pk=20*math.log10(max(np.abs(L*Sx)[B530].max(),1e-9))
                l20=abs(L[I20])/abs(-M.Kout(F)*kap*(CwV*Pw))[I20]
                single=(mem in S.SINGLE and e==0); bar=45 if single else 30
                if PM<bar: sf+=single; cf+=(not single)
                if PM<mn: mn=PM; at=(v,e,fn,round(FC,2))
                wl=max(wl,l20); wp=max(wp,pk)
    return (mem,sf,cf,mn,at,wl,wp)
if __name__=="__main__":
    with Pool(14) as p: R=p.map(work,MEMBERS)
    print(f"Ki 18 + raised520:  single fails {sum(r[1] for r in R)}  combined fails {sum(r[2] for r in R)}")
    wm=min(R,key=lambda r:r[3]); print(f"  min PM {wm[3]:.1f} ({wm[0]}@v{wm[4][0]} e{wm[4][1]} {wm[4][2]} fc{wm[4][3]})")
    print(f"  worst M20 {max(r[5] for r in R):.3f}  worst peak|T|5-30 {max(r[6] for r in R):.2f} dB")
    for r in R:
        if r[1] or r[2]: print(f"   FAIL {r[0]} s{r[1]} c{r[2]} minPM{r[3]:.1f}")
