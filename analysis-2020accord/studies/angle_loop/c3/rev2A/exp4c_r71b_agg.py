# -*- coding: utf-8 -*-
"""exp4c: r71b tracking by the DESIGN method (OLS over CONCATENATED runs per band, worst member), matching c3nl_r71b."""
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
IMPLS=["C3-P","R1-P40","R1-P44","P2"]; MEMS=("nominal","bc","F_hi","b_lo*J_hi")
RUNS=RB.runs(); sos=signal.butter(4,0.5,"lowpass",fs=100.0,output="sos")
XY={}  # (impl,band,member) -> [X, Y] concatenated
for mb in MEMS:
    cols=[dict(impl=i,member=mb,v=RUNS[k]["v"],run=k) for k in range(len(RUNS)) for i in IMPLS]
    idx=[c["run"] for c in cols]; nf=int(max(RUNS[i]["dur"] for i in set(idx))*100)+2
    REF=np.stack([np.pad(RUNS[i]["ref"],(0,nf-len(RUNS[i]["ref"])),mode="edge") for i in idx],1)
    ref=lambda t: REF[min(int(round(t*100)),nf-1)]
    t0=time.time(); r=S.run(cols,S.Scn(dur=max(RUNS[i]["dur"] for i in set(idx))+0.5,ref=ref,th0=REF[0].copy()))
    th=r["th"].astype(float); n=th.shape[0]; plan=r["plan"].astype(float); th100=th[::10]
    for j,c in enumerate(cols):
        L=min(len(RUNS[c["run"]]["ref"]),th100.shape[0],plan.shape[0])
        x=signal.sosfiltfilt(sos,plan[:L,j])[400:]; y=signal.sosfiltfilt(sos,th100[:L,j])[400:]
        key=(c["impl"],RUNS[c["run"]]["band"],mb); XY.setdefault(key,[[],[]])
        XY[key][0].append(x); XY[key][1].append(y)
    print(f"  {mb} {time.time()-t0:.0f}s",flush=True)
def slope(X,Y):
    X=np.concatenate(X); Y=np.concatenate(Y); xm=X-X.mean(); return float((xm*(Y-Y.mean())).sum()/max((xm**2).sum(),1e-12))
for band in ("8-15","15-22",">22"):
    print(f"band {band} (worst member):",flush=True)
    for im in IMPLS:
        sls=[slope(*XY[(im,band,mb)]) for mb in MEMS if (im,band,mb) in XY]
        print(f"   {im}: worst {min(sls):.3f}  (members {'/'.join(f'{s:.3f}' for s in sls)})",flush=True)
