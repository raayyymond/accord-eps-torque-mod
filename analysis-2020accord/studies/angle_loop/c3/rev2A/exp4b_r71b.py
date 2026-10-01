# -*- coding: utf-8 -*-
"""exp4b: r71b REAL-path tracking (goal PRIMARY metric), mode med, members nominal+bc, impls C3-P/R1-P40/R1-P44/P2."""
import os,sys,time
from pathlib import Path
import numpy as np
from scipy import signal
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import rev2a_lane as RL
import c3nl_sim as S
import c3nl_r71b as RB
S.Lane=RL.Rev2ALane
IMPLS=["C3-P","R1-P40","R1-P44","P2"]
RUNS=RB.runs()
print(f"{len(RUNS)} runs",flush=True)
def track(member):
    cols=[dict(impl=i,member=member,v=RUNS[k]["v"],run=k) for k in range(len(RUNS)) for i in IMPLS]
    idx=[c["run"] for c in cols]
    nf=int(max(RUNS[i]["dur"] for i in set(idx))*100)+2
    REF=np.stack([np.pad(RUNS[i]["ref"],(0,nf-len(RUNS[i]["ref"])),mode="edge") for i in idx],1)
    ref=lambda t: REF[min(int(round(t*100)),nf-1)]
    dur=max(RUNS[i]["dur"] for i in set(idx))+0.5
    t0=time.time(); r=S.run(cols,S.Scn(dur=dur,ref=ref,th0=REF[0].copy())); 
    th=r["th"].astype(float); n=th.shape[0]; plan=r["plan"].astype(float)
    sos=signal.butter(4,0.5,"lowpass",fs=100.0,output="sos"); th100=th[::10]
    out={}
    for j,c in enumerate(cols):
        L=min(len(RUNS[c["run"]]["ref"]),th100.shape[0],plan.shape[0])
        x=signal.sosfiltfilt(sos,plan[:L,j]); y=signal.sosfiltfilt(sos,th100[:L,j])
        xs=x[400:]-x[400:].mean(); ys=y[400:]-y[400:].mean()
        sl=float((xs*ys).sum()/max((xs**2).sum(),1e-12))
        out.setdefault((c["impl"],RUNS[c["run"]]["band"]),[]).append(sl)
    print(f"  {member} done {time.time()-t0:.0f}s",flush=True)
    return out
agg={}
for mb in ("nominal","bc"):
    o=track(mb)
    for k,v in o.items(): agg.setdefault(k,[]).append(min(v))
for band in ("8-15","15-22",">22"):
    print(f"  band {band}: "+" ".join(f"{im}:{min(agg.get((im,band),[9])):.3f}" for im in IMPLS),flush=True)
