# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_ltot_measured.py -- place the Kp candidates in the EMPIRICAL F7 bracket,
and measure |L_tot| at f0 from the ring s own Q (Ms ~ Q => |1-L| ~ 1/Q) with no composition rule.
stutter283, 2026-09-03."""
import os,sys,numpy as np
from scipy import signal
H=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,H)
import stutter_v283 as SV, strongturn_r32_r33 as ST
V,FS,CPD=SV.V,SV.FS,SV.CPD
R4=("r35","r36","r37","r38"); OLD=("r32","r33","r34")
rt={t:V.Route(t) for t in R4+OLD}
lt=lambda X,Y,i: np.interp(np.asarray(i,float),np.asarray(X,float),np.asarray(Y,float))
# ring population, sub-detector thr 60
ring=[]
for t in R4:
    r=rt[t]
    for e in ST.fixed_thr_episodes(r,thr=60):
        if e["ang"]>=30 and e["fdom"]>=6: ring.append(r.idx[int(e["t0"]*FS):int((e["t0"]+e["dur"])*FS)])
ring=np.concatenate(ring)
print("A -- WHERE EACH CANDIDATE SITS IN THE *EMPIRICAL* BRACKET (measurement only, no composition rule, no |L_tot|).")
print("   The bracket: F7 = 0.00 per 100 s at flat 248 on r35-r38 (4 routes, 206 s high-angle);")
print("   F7 = 4.3-8.1 at the stock LERP on r32/r33/r34, whose Kp over the ring population is:")
for nm,X,Y in [("flat 248",[0,68,112,136,208],[248]*5),("flat 341",[0,68,112,136,208],[341]*5),
               ("flat 400",[0,68,112,136,208],[400]*5),("M8* 0,32,36,44,88 K512",[0,32,36,44,88],[248,248,512,512,248]),
               ("BAND Y-only",[0,68,112,136,208],[248,512,512,248,248]),("stock LERP",[0,68,112,136,208],[248,512,645,696,696])]:
    k=lt(X,Y,ring)
    print("     %-24s Kp_eff over the ring: p10 %3.0f  p50 %3.0f  MEAN %3.0f  p90 %3.0f"%(nm,*np.percentile(k,[10,50]),k.mean(),np.percentile(k,90)))
print()
print("B -- A *MEASURED* CONSTRAINT ON |L_tot| THAT NEEDS NO COMPOSITION RULE: the ring's own sharpness.")
print("   A lightly damped closed-loop mode at f0 has a resonant peak Ms = max|1/(1-L)|, and Ms ~ Q for a")
print("   second-order peak.  So |1 - L(j f0)| ~ 1/Q -- a DISTANCE FROM THE +1 POINT, measured, not assumed.")
print("   Q = f0 / (half-power bandwidth) of the 6-8.5 Hz peak in the strong-turn rate spectrum (Welch 1024, 0.098 Hz bins).")
print("   %-5s %7s | %6s %6s %7s | %s"%("route","secs","f0 Hz","Q","|1-L|","implied |L| if arg(1-L) is 180 deg (L real >1) / 0 deg (L real <1)"))
for t in OLD+R4:
    r=rt[t]
    m=r.eng&(np.abs(r.ang)>=30)&(r.vego<=10)
    runs=V.runs(m,256)
    if runs.sum()<2048: print("   %-5s  too little exposure (%.1f s)"%(t,runs.sum()/FS)); continue
    f,P=signal.welch(r.wire[runs]-r.wire[runs].mean(),fs=FS,nperseg=1024)
    band=(f>=5.0)&(f<=10.0)
    j=np.flatnonzero(band)[np.argmax(P[band])]
    f0=f[j];pk=P[j]
    # half-power edges by walking out from the peak until P < pk/2 (local baseline removed)
    base=np.median(P[(f>=2)&(f<=25)])
    half=base+(pk-base)/2.0
    lo=j
    while lo>1 and P[lo]>half: lo-=1
    hi=j
    while hi<len(f)-2 and P[hi]>half: hi+=1
    bw=f[hi]-f[lo]
    Q=f0/bw if bw>0 else np.nan
    print("   %-5s %7.1f | %6.2f %6.2f %7.3f | %.3f  /  %.3f"%(t,runs.sum()/FS,f0,Q,1.0/Q if Q else np.nan,1+1.0/Q if Q else np.nan,1-1.0/Q if Q else np.nan))
print()
print("   (The two right-hand columns bracket |L| because Q alone gives the DISTANCE from +1, not the direction.")
print("    A loop just BELOW the boundary sits at |L| = 1 - 1/Q; one just ABOVE at 1 + 1/Q.  F7 = 0 on r35-r38 selects the lower branch.)")
