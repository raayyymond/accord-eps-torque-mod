# -*- coding: utf-8 -*-
"""exp4_track.py -- rev2A tracking trade-off: r71b REAL paths + S-bend + small-signal + turn-hold, R1-P at Ki 36/40/44
vs C3-P (Ki56) vs P2.  Finds the Ki that keeps the goal's tracking (0.95-1.05) while F1 stays >= bars (Ki<=44)."""
import os,sys,time
from pathlib import Path
import numpy as np
from scipy import signal
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import rev2a_lane as RL
import c3nl_sim as S
import c3nl_lens as LN
import c3nl_r71b as RB
S.Lane=RL.Rev2ALane

IMPLS=["C3-P","R1-P36","R1-P40","R1-P44","P2"]
MEMS=("nominal","bc","F_hi","b_lo*J_hi")

# ---- r71b real-path tracking (the goal's PRIMARY tracking metric) ----
print("====== r71b real-path tracking slope (mode med = const median speed), worst member per band ======")
RUNS=RB.runs()
def r71b_track(member):
    cols=[dict(impl=i,member=member,v=RUNS[k]["v"],run=k) for k in range(len(RUNS)) for i in IMPLS]
    idx=[c["run"] for c in cols]
    nf=int(max(RUNS[i]["dur"] for i in set(idx))*100)+2
    REF=np.stack([np.pad(RUNS[i]["ref"],(0,nf-len(RUNS[i]["ref"])),mode="edge") for i in idx],1)
    ref=lambda t: REF[min(int(round(t*100)),nf-1)]
    dur=max(RUNS[i]["dur"] for i in set(idx))+0.5
    scn=S.Scn(dur=dur,ref=ref,th0=REF[0].copy())
    r=S.run(cols,scn); th=r["th"].astype(float); n=th.shape[0]; plan=r["plan"].astype(float)
    sos=signal.butter(4,0.5,"lowpass",fs=100.0,output="sos"); th100=th[::10]
    out={}
    for j,c in enumerate(cols):
        L=min(len(RUNS[c["run"]]["ref"]),th100.shape[0],plan.shape[0])
        x=signal.sosfiltfilt(sos,plan[:L,j]); y=signal.sosfiltfilt(sos,th100[:L,j])
        xs=x[400:]-x[400:].mean(); ys=y[400:]-y[400:].mean()
        sl=float((xs*ys).sum()/max((xs**2).sum(),1e-12))
        out.setdefault((c["impl"],RUNS[c["run"]]["band"]),[]).append(sl)
    return out
agg={}
for mb in MEMS:
    o=r71b_track(mb)
    for k,v in o.items(): agg.setdefault(k,[]).append(min(v))   # worst run in band
for band in ("8-15","15-22",">22"):
    row=" ".join(f"{im}:{min(agg.get((im,band),[9])):.3f}" for im in IMPLS)
    print(f"  band {band}: {row}")

# ---- S-bend 0.1 Hz (scurve_1.5) worst slope over members at 15-17.5 ----
print("\n====== S-bend 0.1Hz slope (worst member), 15-17.5 m/s ======")
for name in ("scurve_1.5","scurve_2"):
    worst={im:9.0 for im in IMPLS}
    for mb in MEMS:
        cols=[dict(impl=i,member=mb,v=v) for v in [15.0,16.0,17.0,17.5] for i in IMPLS]
        scn,meta=LN.build(name,cols); r=S.run(cols,scn); m=LN.metrics(name,meta,r,cols)
        for k,c in enumerate(cols): worst[c["impl"]]=min(worst[c["impl"]],m["slope"][k])
    print(f"  {name}: "+" ".join(f"{im}:{worst[im]:.3f}" for im in IMPLS))

# ---- small-signal +-0.5deg 0.2Hz gain in the dip (worst over 11-12.5) ----
print("\n====== small-signal +-0.5deg 0.2Hz in-phase gain, min over 11-12.5 window ======")
for name in ("small_0.5_0.2","small_0.3_0.1"):
    worst={im:9.0 for im in IMPLS}
    for mb in ("nominal","bc","F_hi"):
        cols=[dict(impl=i,member=mb,v=v) for v in [11.0,11.5,11.75,12.0,12.5] for i in IMPLS]
        scn,meta=LN.build(name,cols); r=S.run(cols,scn); m=LN.metrics(name,meta,r,cols)
        for k,c in enumerate(cols): worst[c["impl"]]=min(worst[c["impl"]],m["gain"][k])
    print(f"  {name}: "+" ".join(f"{im}:{worst[im]:.2f}" for im in IMPLS))

# ---- turn-hold: constant curve sized to a_lat, settled wheel/ref over 8..22 ----
print("\n====== turn-hold (constant curve a_lat 2.0, settled wheel/ref), min over 8-22 m/s ======")
def turnhold(member,a):
    speeds=[8.0,10.0,12.5,15.0,18.0,22.0]
    cols=[dict(impl=i,member=member,v=v) for v in speeds for i in IMPLS]
    B=len(cols); sp=np.array([LN.S.tgt_alat(c["v"],a) for c in cols])
    ref=lambda t: sp*np.interp(t,[0,0.5,2.0,999],[0,0,1,1])
    scn=S.Scn(dur=8.0,ref=ref); r=S.run(cols,scn); th=r["th"].astype(float)
    hold=th[-1500:].mean(0)/sp
    out={}
    for k,c in enumerate(cols): out.setdefault(c["impl"],[]).append(hold[k])
    return out
agg2={im:9.0 for im in IMPLS}
for mb in MEMS:
    o=turnhold(mb,2.0)
    for im in IMPLS: agg2[im]=min(agg2[im],min(o[im]))
print("  "+" ".join(f"{im}:{agg2[im]:.3f}" for im in IMPLS))
