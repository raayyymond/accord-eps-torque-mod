# -*- coding: utf-8 -*- 
"""ADVERSARY B rev 2 -- F3 re-run: paired authority test at 7680.  Analysis only."""
import os,sys
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); KIT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","studies","v280"))
sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20, v280_map_profiles as V, grind_incident_r35 as GI
ROOT=os.environ["ACCORD_FIRMWARE_ROOT"]+"/analysis-2020accord/"
cells=GI.read_cells(ROOT+"_v287r2_V287R2-V282BASE-DCLAMP.7680-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
FS=100.0
G={t:C20.load(t) for t in ("r39","r3a","r3c")}
print("F3 RE-RUN -- PAIRED AUTHORITY AT 7680 (same steps, 10240 vs 7680)")
print("  %-5s %5s | %8s %8s %8s %6s | %s" % ("route","n","0-50ms","0-100ms","0-200ms","peak","95% CI on 0-100 ms"))
for tag in ("r39","r3a","r3c"):
    g=G[tag]; idx=g["idx"]; d=np.r_[0.0,np.diff(idx)]
    thr=np.percentile(np.abs(d[g["eng"]]),97.0)
    hit=g["eng"]&(np.abs(d)>=thr)&(np.abs(g["bar"])<300)
    ks=[];last=-999
    for k in np.flatnonzero(hit):
        if k-last<40 or k<60 or k>len(idx)-40: continue
        ks.append(k); last=k
    R={w:[] for w in (50,100,200)}; pk=[]
    for k in ks[:200]:
        a_,b_=k-5,k+40
        try:
            V.D_CLAMP=10240; s0=GI.simulate(g,a_,b_,cells)
            V.D_CLAMP=7680;  s1=GI.simulate(g,a_,b_,cells)
        finally: V.D_CLAMP=10240
        j0=(k-s0["seg"].start)*10
        for w in (50,100,200):
            A=np.abs(s0["T"][j0:j0+w]); B=np.abs(s1["T"][j0:j0+w])
            if len(A)<w or np.median(A)<20: continue
            R[w].append(np.median(B)/np.median(A))
        A=np.abs(s0["T"][j0:j0+200]); B=np.abs(s1["T"][j0:j0+200])
        if len(A)==200 and A.max()>20: pk.append(B.max()/A.max())
    if not R[100]: continue
    r=np.array(R[100]); bs=np.array([np.median(np.random.choice(r,len(r))) for _ in range(2000)])
    print("  %-5s %5d | %8.4f %8.4f %8.4f %6.3f | [%.4f, %.4f]" % (
        tag,len(r),np.median(R[50]),np.median(R[100]),np.median(R[200]),np.median(pk),
        np.percentile(bs,2.5),np.percentile(bs,97.5)))
