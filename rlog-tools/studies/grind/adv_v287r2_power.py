# -*- coding: utf-8 -*-
"""ADVERSARY B rev 2, part 2 -- audit of C3's power claim, using Appendix C's OWN onset extraction verbatim,
plus Q6 window availability and Q10 spread.  Analysis only."""
import os, sys, math
import numpy as np
from scipy import signal
HERE=os.path.dirname(os.path.abspath(__file__)); KIT=os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR=os.path.join(HERE,"_scratch")
sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","studies","v280"))
sys.path.insert(0,os.path.join(KIT,"analysis-2020accord","lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20, v280_map_profiles as V, grind_incident_r35 as GI
if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8",errors="replace")
OUT=[]
def pr(s=""):
    print(s,flush=True); OUT.append(s)
ROOT=os.environ["ACCORD_FIRMWARE_ROOT"]+"/analysis-2020accord/"
I287=ROOT+"_v287r2_V287R2-V282BASE-DCLAMP.7680-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
cells=GI.read_cells(I287); FS,FS1K=100.0,1000.0
LADDER=[10240,7680]
def runs_of(m,n):
    d=np.diff(np.r_[0,m.astype(int),0]); return [(a,b) for a,b in zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)) if b-a>=n]
G={t:C20.load(t) for t in ("r39","r3a","r3c")}
for t in G: G[t]["tr"]=G[t]["t"]-G[t]["t"][0]

pr("="*140)
pr("ADVERSARY B REV 2 -- AUDIT OF C3's POWER CLAIM, using Appendix C's OWN onset extraction verbatim")
pr("="*140)
ONS={}
for tag in ("r39","r3c"):
    g=G[tag]; ev={d:[] for d in LADDER}
    for a_,b_ in runs_of(g["eng"],1500)[:6]:
        b_=min(b_,a_+20000)
        for d in LADDER:
            old=V.D_CLAMP; V.D_CLAMP=d
            try: sN=GI.simulate(g,a_,b_,cells)
            finally: V.D_CLAMP=old
            dsp=np.abs(np.r_[0.0,np.diff(32.0*sN["sp"])]); nz=dsp[dsp>0]
            if len(nz)<100: continue
            thr=np.percentile(nz,99); starts=np.flatnonzero(dsp>=thr)
            for i in starts[:400]:
                if i+500<=len(sN["T"]): ev[d].append(C20.bamp(sN["T"][i:i+500],18.0,22.0,FS1K))
    ONS[tag]=ev
    e0=np.array(ev[10240]); e1=np.array(ev[7680]); n=len(e0)
    iqr=np.percentile(e0,75)-np.percentile(e0,25)
    se_norm=1.253*(iqr/1.349)/math.sqrt(n)
    bs=np.array([np.median(np.random.choice(e0,n)) for _ in range(4000)])
    se_boot=bs.std()
    pr("")
    pr("  ROUTE %s -- %d onset events (Appendix C reports %s)" % (tag, n, "435" if tag=="r39" else "229"))
    pr("    onset p50 %.2f -> %.2f = x%.4f   (Appendix C: %s)" % (
        np.median(e0), np.median(e1), np.median(e1)/np.median(e0), "x0.947" if tag=="r39" else "x0.930"))
    pr("    C3's SE, normal-theory 1.253*(IQR/1.349)/sqrt(n) = %.3f = %.1f %% of the median" % (se_norm,100*se_norm/np.median(e0)))
    pr("    BOOTSTRAP SE of the same median (4000 resamples)  = %.3f = %.1f %% of the median" % (se_boot,100*se_boot/np.median(e0)))
    pr("    skew check: p75/p50 = %.2f, p50/p25 = %.2f  (a symmetric pool gives ~equal ratios)" % (
        np.percentile(e0,75)/np.median(e0), np.median(e0)/np.percentile(e0,25)))
    # PAIRED ratio, available only in the mirror
    k=min(len(e0),len(e1)); pa=np.array(e1[:k])/np.maximum(np.array(e0[:k]),1e-9)
    bsp=np.array([np.median(np.random.choice(pa,k)) for _ in range(4000)])
    pr("    PAIRED (same events, both clamps -- the MIRROR can do this, one drive on the CAR cannot):")
    pr("        median ratio %.4f, bootstrap SE %.3f %%  -> resolvable at 2 SE beyond x%.4f" % (
        np.median(pa),100*bsp.std(),1.0-2*bsp.std()))
    # what the ON-CAR comparison actually costs
    seb=se_boot/np.median(e0)
    eff=1.0-(np.median(e1)/np.median(e0))
    n1=n*(seb/(eff/2.0))**2
    n2=n*(seb/(eff/(2.0*math.sqrt(2.0))))**2
    secs=g["eng"].sum()/FS
    pr("    UNPAIRED, which is what the DRIVE gives (V287 drive vs a V282 baseline drive):")
    pr("        effect %.1f %%; one-sample n for 2 SE = %.0f (%.0f min engaged); TWO-SAMPLE, both sides grown, n = %.0f each (%.0f min EACH)" % (
        100*eff, n1, n1/n*secs/60.0, n2, n2/n*secs/60.0))
    pr("        FLOOR: if the V282 baseline stays at n=%d (SE %.1f %%), 2*SE of the ratio >= %.1f %% > the %.1f %% effect" % (
        n,100*seb,2*100*seb,100*eff))
    pr("        -> the comparison NEVER resolves at any V287 drive length unless the BASELINE is also grown.")
if len(ONS)==2:
    m39=np.median(ONS["r39"][10240]); m3c=np.median(ONS["r3c"][10240])
    pr("")
    pr("  BETWEEN-ROUTE, SAME BUILD (both V282): r39 %.2f vs r3c %.2f = x%.2f -- %.0fx the x0.947 effect." % (
        m39,m3c,max(m39,m3c)/min(m39,m3c),(max(m39,m3c)/min(m39,m3c)-1)/0.053))

# ---- Q6 window availability and Q10 spread
pr("")
pr("="*140)
pr("Q6 and Q10 -- do their preconditions and thresholds survive their own noise?")
pr("="*140)
q6=lambda x: C20.bamp(x,33.0,49.9,FS)/max(1e-9,C20.bamp(x,2.0,6.0,FS))
pr("  Q6 requires >= 20 qualifying windows.  How many exist, on each reading of 'window'?")
for tag in ("r39","r3a","r3c"):
    g=G[tag]
    cm=g["eng"]&(g["vego"]>=1)&(g["vego"]<3)&(np.abs(g["bar"])<400)
    pr("    %-5s creep-stratum runs >= 2 s: %2d   |  engaged runs >= 2 s (route-wide): %3d  |  engaged 2 s tiles: %3d" % (
        tag, len(runs_of(cm,200)), len(runs_of(g["eng"],200)), int(g["eng"].sum()//200)))
pr("    -> on the CREEP reading Q6 can never reach 20 windows on one drive and so can never FAIL (unevaluable).")
pr("    -> on the ROUTE-WIDE reading it easily does.  C5 says 'every statistic is route-wide', so route-wide it is;")
pr("       the ambiguity is worth removing in the text before the drive.")
pr("")
pr("  Q6 pooled statistic per route, ROUTE-WIDE engaged (the reading that has the windows):")
vals=[]
for tag in ("r39","r3a","r3c"):
    g=G[tag]; x=np.concatenate([g["rate_x"][a_:b_] for a_,b_ in runs_of(g["eng"],200)])
    tiles=[q6(g["rate_x"][a_:a_+200]) for a_,b_ in runs_of(g["eng"],200) for a_ in [a_] if b_-a_>=200]
    vals.append(q6(x))
    pr("    %-5s pooled %.4f | 2 s tiles n=%d  p25 %.3f p50 %.3f p75 %.3f  -> SE of median %.1f %%" % (
        tag,q6(x),len(tiles),np.percentile(tiles,25),np.median(tiles),np.percentile(tiles,75),
        100*1.253*((np.percentile(tiles,75)-np.percentile(tiles,25))/1.349)/math.sqrt(len(tiles))/np.median(tiles)))
pr("    route-to-route spread of the pooled statistic: x%.2f   (C5 threshold x1.60)" % (max(vals)/min(vals)))
pr("")
pr("  Q10 (new, loaded stratum |ang|>60): 0x18F rate 6-9 Hz and 18-22 Hz.  C5 quotes spread x1.44 / x1.86,")
pr("  thresholds x1.9 / x2.3.  Recomputed:")
b69=[];b22=[]
for tag in ("r39","r3a","r3c"):
    g=G[tag]; m=g["eng"]&(np.abs(g["ang"])>60)
    x=np.concatenate([g["rate_x"][a_:b_] for a_,b_ in runs_of(m,200)])
    a=C20.bamp(x,6.0,9.0,FS); b=C20.bamp(x,18.0,22.0,FS); b69.append(a); b22.append(b)
    pr("    %-5s  6-9 Hz %.3f   18-22 Hz %.3f   (%.1f s of loaded stratum)" % (tag,a,b,m.sum()/FS))
pr("    route spread 6-9 x%.2f (threshold x1.9 -> margin x%.2f) ; 18-22 x%.2f (threshold x2.3 -> margin x%.2f)" % (
    max(b69)/min(b69),1.9/(max(b69)/min(b69)),max(b22)/min(b22),2.3/(max(b22)/min(b22))))
os.makedirs(SCR,exist_ok=True)
open(os.path.join(SCR,"adv_v287r2_power.txt"),"w",encoding="utf-8").write("\n".join(OUT)+"\n")
print("\nwrote _scratch/adv_v287r2_power.txt")
