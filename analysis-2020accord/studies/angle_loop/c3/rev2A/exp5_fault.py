# -*- coding: utf-8 -*-
"""exp5_fault.py -- F3: rate-invalid (gp-0x6abe=0x7FFF sustained while engaged). R1-P (E:=0 -> inert) vs C3-P (D=0, P+I
runs -> the refuter's unstable PI-only state). Direct 1 kHz loop on an unstable member (b_lo*J_hi, b_q*ms_free)."""
import os,sys
from pathlib import Path
import numpy as np
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import rev2a_lane as RL
import c3nl_sim as S

def faultrun(impls, member, v, fault_t=2.0, dur=8.0):
    B=len(impls); lane=RL.Rev2ALane(impls)
    pl=S.Plant([member]*B, np.full(B,v))
    pl.th[:]=0.0
    nT=int(dur*1000); FRAME=S.FRAME
    held_th=np.floor(10*pl.th+0.5).astype(np.int64); held_x=np.zeros(B,np.int64)
    st=np.zeros(B,np.int64); olag=np.zeros(B)
    rng=np.random.default_rng(3)
    ramp=np.full(B,0x8000,np.int64); fifo=[]
    sp_deg=8.0   # a modest commanded curve
    peakT=np.zeros(B); lastwin=np.zeros((2000,B))
    cmd=np.zeros(B,np.int64); Trec=np.zeros((nT,B))
    for n in range(nT):
        t=n*1e-3; sen=False
        if n%10==0:
            plan=sp_deg*np.interp(t,[0,0.5,1.5,999],[0,0,1,1])*np.ones(B)
            raw=S.s16(-np.floor(10.0*plan+0.5).astype(np.int64)); cmd=np.clip(S.s32(-(raw<<2)),-0x4000,0x4000)
        vw=np.round(v*3.6*64).astype(np.int64)*np.ones(B,np.int64)
        om_m=pl.om/FRAME.kappa(pl.th)
        g4f50=S.s16(np.round(S.ABE_PER*om_m+rng.normal(0,2.8,B)).astype(np.int64))
        st=st+(((g4f50*1024-st)*37)>>7)
        abe=S.s16(st>>10)
        if t>=fault_t: abe=np.full(B,0x7FFF,np.int64)      # rate sensor invalid
        T=lane.tick(held_th,abe,held_x,cmd,np.zeros(B,np.int64),ramp,1,1,vw)
        q=np.floor(10.0*pl.th+0.5).astype(np.int64); x_now=np.clip(-((S.s16(st>>10)*48*1159)>>15),-12000,12000)
        fifo.append((q,x_now)); fifo=fifo[-11:]
        if n%10==4: held_th=q; held_x=x_now
        pl.step(-T.astype(float))
        Trec[n]=T
        if t>=fault_t: peakT=np.maximum(peakT,np.abs(T))
    # growth: compare rms of T in [fault+1,fault+2] vs [fault+4,fault+5]
    a=slice(int((fault_t+1)*1000),int((fault_t+2)*1000)); b=slice(int((fault_t+3)*1000),int((fault_t+4)*1000))
    r1=np.sqrt((Trec[a]**2).mean(0)); r2=np.sqrt((Trec[b]**2).mean(0))
    return peakT, r1, r2

for member in ("b_lo*J_hi","bc"):
    for v in (12.0,):
        pk,r1,r2=faultrun(["R1-P","C3-P"],member,v)
        print(f"{member} @{v} m/s rate-invalid from t=2s:")
        print(f"   R1-P : peak|T| after fault {pk[0]:6.0f}  rms(3-4s)/rms(1-2s after) = {r2[0]:.0f}/{r1[0]:.0f} (ratio {r2[0]/max(r1[0],1e-6):.2f})")
        print(f"   C3-P : peak|T| after fault {pk[1]:6.0f}  rms(3-4s)/rms(1-2s after) = {r2[1]:.0f}/{r1[1]:.0f} (ratio {r2[1]/max(r1[1],1e-6):.2f})")
