# -*- coding: utf-8 -*-
import os, sys, math, numpy as np
HERE=os.path.abspath('.'); KIT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","studies","v280"))
sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20, v280_map_profiles as V, grind_incident_r35 as GI
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,FS1K,FST=100.0,1000.0,50.0
ROOT=os.environ["ACCORD_FIRMWARE_ROOT"]+"/analysis-2020accord/"
IMG=ROOT+"_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
cells=GI.read_cells(IMG)
def runs_of(m,n):
    d=np.diff(np.r_[0,m.astype(int),0])
    return [(a,b) for a,b in zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)) if b-a>=n]
W=1000  # 1.0 s onset window -> 50 tap samples
print("Q2 PAIRED, 1.0 s onset windows.  B-term = MEASURED tap vs the 10240-MIRROR on the SAME events (V282).")
print("That ratio's spread IS the paired noise the on-car statistic carries.")
for tag in ("r39","r3c"):
    C20.BUILD[tag]="V282"; g=C20.load(tag)
    A_r=[]; B_r=[]
    for a_,b_ in runs_of(g["eng"],1500)[:6]:
        b_=min(b_,a_+20000)
        S={}
        for d in (10240,7680):
            old=V.D_CLAMP; V.D_CLAMP=d
            try: S[d]=GI.simulate(g,a_,b_,cells)
            finally: V.D_CLAMP=old
        s0=S[10240]; t1k=s0["t1k"]; dt=t1k[1]-t1k[0]
        dsp=np.abs(np.r_[0.0,np.diff(32.0*s0["sp"])]); nz=dsp[dsp>0]
        if len(nz)<100: continue
        thr=np.percentile(nz,99)
        for i in np.flatnonzero(dsp>=thr)[:400]:
            if i+W>len(s0["T"]): continue
            e0=C20.bamp(S[10240]["T"][i:i+W],18.,22.,FS1K); e1=C20.bamp(S[7680]["T"][i:i+W],18.,22.,FS1K)
            if e0>1e-6: A_r.append(e1/e0)
            sel=(g["T_t"]>=t1k[i])&(g["T_t"]<=t1k[i+W-1])
            if sel.sum()<40: continue
            j=np.clip(np.round((g["T_t"][sel]-t1k[0])/dt).astype(int),0,len(s0["T"])-1)
            em=C20.bamp(g["T"][sel],18.,22.,FST); ep=C20.bamp(s0["T"][j],18.,22.,FST)
            if ep>1e-6 and em>1e-6 and np.isfinite(em/ep): B_r.append(em/ep)
    for lbl,r in (("A  dose term (mirror/mirror)",A_r),("B  MEASURED tap / mirror",B_r)):
        r=np.array(r)
        if len(r)<10: print("  %-5s %-30s n=%d too few"%(tag,lbl,len(r))); continue
        iqr=np.percentile(r,75)-np.percentile(r,25); sd_eq=iqr/1.349
        se=1.253*sd_eq/math.sqrt(len(r))
        print("  %-5s %-30s n=%4d  median %.4f  IQR %.4f  SE(median) %.4f = %.2f %%"%(
            tag,lbl,len(r),np.median(r),iqr,se,100*se/np.median(r)))
        if lbl.startswith("B"):
            eff=abs(1-0.947)*np.median(r)
            need=(2*1.253*sd_eq/eff)**2
            print("        => to resolve x0.947 at 2 SE: n >= %.0f events (%.0f s engaged at r39's 435/880 s rate)"%(
                need, need/435.0*880.0))
