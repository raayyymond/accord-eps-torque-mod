# -*- coding: utf-8 -*-
"""ADVERSARY B, REV 2 -- V287 rev 2 (0xC61B6 10240 -> 7680) against my own F1-F4 and against prereg C5.
Analysis only.  Builds nothing, sends nothing, flashes nothing.
Run: python adv_v287r2_b_units_strata.py  -> _scratch/adv_v287r2_b_units_strata.txt
"""
import os, sys, struct, hashlib
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20
import v280_map_profiles as V
import grind_incident_r35 as GI
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT=[]
def pr(s=""):
    print(s, flush=True); OUT.append(s)

ROOT = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
I282 = ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
I287 = ROOT + "_v287r2_V287R2-V282BASE-DCLAMP.7680-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
A=open(I282,"rb").read(); Bi=open(I287,"rb").read()
u16=lambda b,a: struct.unpack_from("<H", b, a)[0]
FS, FS1K, KD = 100.0, 1000.0, 128.0

pr("="*140)
pr("ADVERSARY B REV 2 -- V287 rev 2, 0xC61B6 = %d, read FROM THE BUILT IMAGE" % u16(Bi,0xC61B6))
pr("="*140)
pr("  sha256 %s" % hashlib.sha256(Bi).hexdigest())
d=[i for i in range(len(A)) if A[i]!=Bi[i]]
pr("  full-file diff vs V282: %d bytes -> %s" % (len(d), ", ".join("0x%06X %02x->%02x"%(i,A[i],Bi[i]) for i in d)))
pr("  = the D-clamp high byte (0x28->0x1e, 10240->7680) plus the 4-byte cal-page CRC at 0xC6FFC.  Nothing else moved.")
for a,n in [(0xC61B4,"out clamp"),(0xC61B8,"deadband"),(0xC61BA,"anti-windup"),(0xC61BC,"P clamp"),
            (0xC61BE,"sum clamp"),(0xC63EC,"lag a2"),(0xC63EE,"lag b2"),(0xC62E6,"fb clamp"),(0xC6446,"r24 gain")]:
    assert u16(A,a)==u16(Bi,a)
pr("  every other chain cell byte-identical to V282 [EVIDENCE, full-file diff].")

# cells for the mirror come from the REV 2 image
cells = GI.read_cells(I287)
pr("")
pr("  F1 RE-RUN AT 7680.  D = 16*dE -> 7680 rails at |dE| = %.0f." % (7680/16.0))
a_fb,b_fb = cells["fb_a"]/1024.0, cells["fb_b"]/1024.0
FB_DC = 2.0*b_fb/(1.0-a_fb)
def dfb_per_x(f):
    z=np.exp(-1j*2*np.pi*f/FS1K)
    return abs(b_fb*(1+z)/(1-a_fb*z))*abs(1-z)
pr("    fb DC gain %.4f, %.2f counts per deg/s (unchanged -- no fb cell moved)." % (FB_DC, FB_DC*V.CPD))
pr("    feedback part alone rails 7680 at: %.0f deg/s^2 sustained | %.1f deg/s at 7.3 Hz | %.1f deg/s at 20.3 Hz" % (
    480.0/(FB_DC*V.CPD)*1000.0, 480.0/(dfb_per_x(7.3)*V.CPD), 480.0/(dfb_per_x(20.3)*V.CPD)))
pr("    setpoint part: |dE_sp| = 32*|d(sp)| rails at |d(sp)| = %.0f map counts = %.1f demand counts" % (
    480.0/32.0, 480.0/32.0/4.30))
pr("    -> at 7680 it takes a ~3.5-count command step to rail (2560 took 2, today's 10240 takes ~4.7).")

G={}
for tag in ("r39","r3a","r3c"):
    G[tag]=C20.load(tag); G[tag]["tr"]=G[tag]["t"]-G[tag]["t"][0]

def runs_of(m,minlen):
    d=np.diff(np.r_[0,m.astype(int),0])
    return [(a,b) for a,b in zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)) if b-a>=minlen]

STRATA=[("CREEP hands-off",            lambda g: g["eng"]&(g["vego"]>=1)&(g["vego"]<3)&(np.abs(g["bar"])<400)),
        ("LOW-MID 3-8 m/s",            lambda g: g["eng"]&(g["vego"]>=3)&(g["vego"]<8)&(np.abs(g["bar"])<400)),
        ("SUBURBAN 8-15 m/s",          lambda g: g["eng"]&(g["vego"]>=8)&(g["vego"]<15)&(np.abs(g["bar"])<400)),
        ("HIGHWAY >15 m/s",            lambda g: g["eng"]&(g["vego"]>=15)&(np.abs(g["bar"])<400)),
        ("HANDS-ON |bar|>700",         lambda g: g["eng"]&(np.abs(g["bar"])>700)),
        ("HANDS-ON HARD |bar|>1500",   lambda g: g["eng"]&(np.abs(g["bar"])>1500)),
        ("LOADED |ang|>60",            lambda g: g["eng"]&(np.abs(g["ang"])>60)),
        ("FAST WHEEL >25 deg/s",       lambda g: g["eng"]&(np.abs(g["rate_x"])>25))]
DOSES=[10240,7680]

def collect(name, sel):
    """pooled over r39+r3a+r3c, as Appendix C does"""
    Ds=[];Df=[];Dr=[]
    for tag in ("r39","r3a","r3c"):
        g=G[tag]; m=sel(g)&g["eng"]
        for a_,b_ in runs_of(m,100)[:80]:
            b_=min(b_,a_+4000)
            try: s0=GI.simulate(g,a_,b_,cells)
            except Exception: continue
            inm=np.zeros(len(g["t"]),bool); inm[a_:b_]=True
            live=np.repeat((g["eng"]&inm)[s0["seg"]],10)
            if live.sum()<100: continue
            sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
            Ds.append(np.floor(dsp*KD/8.0)[live]);Df.append(np.floor(-dfb*KD/8.0)[live])
            Dr.append(np.floor((dsp-dfb)*KD/8.0)[live])
    if not Ds: return None
    return np.concatenate(Ds),np.concatenate(Df),np.concatenate(Dr)

pr("")
pr("="*140)
pr("F2 RE-RUN -- ADMISSIBILITY AT 7680, MY MACHINERY, POOLED r39+r3a+r3c (Appendix C's pooling)")
pr("  admissibility = D_sp-dominance >= 80 %% on binding ticks AND p99|D_fb|/clamp < 1")
pr("="*140)
pr("  %-26s %7s | %-24s | %-24s | %s" % ("stratum","s","10240 (today)","7680 (V287 rev 2)","verdict at 7680"))
pr("  %-26s %7s | %6s %8s %7s | %6s %8s %7s |" % ("","","dom%","p99/clp","bind%","dom%","p99/clp","bind%"))
POOL={}
for name,sel in STRATA:
    r=collect(name,sel)
    if r is None: continue
    Ds,Df,Dr=r
    row=[name,len(Ds)/FS1K]
    vals={}
    for dd in DOSES:
        bm=np.abs(Dr)>dd
        dom=100.0*(np.abs(Ds[bm])>np.abs(Df[bm])).mean() if bm.any() else 100.0
        rat=np.percentile(np.abs(Df),99)/dd
        row+= [dom,rat,100.0*bm.mean()]; vals[dd]=(dom,rat)
    ok = "ADMISSIBLE" if (vals[7680][0]>=80.0 and vals[7680][1]<1.0) else ("borderline (dom %.1f)"%vals[7680][0] if vals[7680][1]<1.0 else "NOT admissible")
    POOL[name]=vals
    pr("  %-26s %7.1f | %6.1f %8.2f %7.2f | %6.1f %8.2f %7.2f | %s" % tuple(row+[ok]))

# ----------------------------------------------------------------------------------------------------------------
pr("")
pr("="*140)
pr("F2b -- EFFECTIVE Kd MULTIPLIER AT 7680 (the ring question).  C4 gates on the 6-9 Hz multiplier in LOADED.")
pr("="*140)
pr("  %-26s %-5s %7s | %-17s | %-17s" % ("stratum","route","s","10240 (today)","7680 (rev 2)"))
pr("  %-26s %-5s %7s | %8s %8s | %8s %8s" % ("","","","6-9 Hz","18-22 Hz","6-9 Hz","18-22 Hz"))
MULT={}
for name,sel in STRATA:
    for tag in ("r39","r3a","r3c"):
        g=G[tag]; m=sel(g)&g["eng"]; segs=[]
        for a_,b_ in runs_of(m,300)[:50]:
            b_=min(b_,a_+4000)
            try: s0=GI.simulate(g,a_,b_,cells)
            except Exception: continue
            inm=np.zeros(len(g["t"]),bool); inm[a_:b_]=True
            live=np.repeat((g["eng"]&inm)[s0["seg"]],10)
            if live.sum()<600: continue
            sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
            segs.append(np.floor((dsp-dfb)*KD/8.0)[live])
        tot=sum(len(s) for s in segs)
        if tot<5000: continue
        row=[name,tag,tot/FS1K]
        for dd in DOSES:
            for lo,hi in ((6.0,9.0),(18.0,22.0)):
                num=den=0.0
                for D in segs:
                    if len(D)<512: continue
                    num+=C20.bamp(np.clip(D,-dd,dd),lo,hi,FS1K)**2*len(D); den+=C20.bamp(D,lo,hi,FS1K)**2*len(D)
                row.append(np.sqrt(num/den) if den>0 else np.nan)
        MULT[(name,tag)]=row
        pr("  %-26s %-5s %7.1f | %8.4f %8.4f | %8.4f %8.4f" % tuple(row))

pr("")
pr("  C4's ring construction uses the LOADED 6-9 Hz multiplier.  Appendix C: m = 0.951 (10240) -> 0.941 (7680),")
pr("  Kd_eff 121.7 -> 120.4, |L_tot| 0.980 -> 0.983 = EXACTLY the gate.  My loaded 6-9 Hz multipliers:")
for tag in ("r39","r3a","r3c"):
    k=("LOADED |ang|>60",tag)
    if k in MULT:
        r=MULT[k]
        pr("      %-5s  10240 %.4f -> 7680 %.4f   (relative %.4f ; Kd_eff %.1f -> %.1f)" % (
            tag, r[3], r[5], r[5]/r[3], 128*r[3], 128*r[5]))

# ----------------------------------------------------------------------------------------------------------------
pr("")
pr("="*140)
pr("F4 RE-RUN -- Q2's POWER.  C3 claims n ~ 1,150 onsets ~ 38 min gives 2 SE on x0.947.  Two questions:")
pr("  (i) is the within-route SE arithmetic right, and (ii) is the WITHIN-route SE the right variance at all,")
pr("      given Q2 compares a V287 drive against a V282 BASELINE FROM A DIFFERENT DRIVE?")
pr("="*140)
def onset_stat(tag, dose, cellsX):
    g=G[tag]
    Ts=[]; tt=[]
    for a_,b_ in runs_of(g["eng"],200):
        b_=min(b_,a_+4000)
        try:
            V.D_CLAMP=dose; s0=GI.simulate(g,a_,b_,cellsX)
        finally: V.D_CLAMP=10240
        inm=np.zeros(len(g["t"]),bool); inm[a_:b_]=True
        live=np.repeat((g["eng"]&inm)[s0["seg"]],10)
        if live.sum()<600: continue
        sp32=32.0*s0["sp"]; dsp=np.abs(np.r_[0.0,np.diff(sp32)])
        env=np.abs(signal.hilbert(C20.bandpass(s0["T"],18.0,22.0,FS1K)))
        Ts.append((dsp,env,live))
    if not Ts: return None,None,None
    nz=np.concatenate([d[d>0] for d,_,_ in Ts])
    thr=np.percentile(nz,99.0)
    on=[];st=[]
    for dsp,env,live in Ts:
        k=np.flatnonzero((dsp>=thr)&live)
        last=-10**9
        for j in k:
            if j-last<250: continue
            last=j
            if j+500<len(env): on.append(np.median(env[j:j+500]))
        step=np.zeros(len(env),bool)
        for j in np.flatnonzero(dsp>np.median(nz)):
            step[max(0,j-300):j+300]=True
        s=live&~step
        if s.sum()>500: st.append(np.median(env[s]))
    return np.array(on), np.array(st), thr

BASE={}; NEW={}
for tag in ("r39","r3a","r3c"):
    on0,st0,thr = onset_stat(tag,10240,cells)
    on1,st1,_   = onset_stat(tag,7680,cells)
    if on0 is None or len(on0)<20: continue
    n=min(len(on0),len(on1))
    m0,m1=np.median(on0),np.median(on1[:n] if len(on1)>=n else on1)
    bs=np.array([np.median(np.random.choice(on0,len(on0))) for _ in range(2000)])
    se=bs.std()/m0
    BASE[tag]=(m0,len(on0),se); NEW[tag]=m1
    pr("  %-5s  onset events n = %4d | median envelope 10240 %7.3f -> 7680 %7.3f  = x%.4f | SE of the median %.2f %%" % (
        tag, len(on0), m0, m1, m1/m0, 100*se))
    pr("        steady control: 10240 %7.3f -> 7680 %7.3f = x%.4f" % (np.median(st0), np.median(st1), np.median(st1)/np.median(st0)))
if len(BASE)>=2:
    ms=[BASE[t][0] for t in BASE]
    pr("")
    pr("  BETWEEN-ROUTE spread of the SAME statistic on the SAME build (all V282): %s  -> x%.2f" % (
        " / ".join("%.3f"%m for m in ms), max(ms)/min(ms)))
    pr("  The predicted effect is x0.947, i.e. 5.3 %%.  The between-route spread is %.0f %% -- %.0f x the effect." % (
        100*(max(ms)/min(ms)-1), (max(ms)/min(ms)-1)/0.053))
    for t in BASE:
        m0,n0,se=BASE[t]
        need_paired = n0*(se/0.0265)**2
        need_2samp  = n0*(se/(0.0265/np.sqrt(2)))**2
        pr("  %-5s  n=%d SE=%.2f%% -> n for 2 SE on x0.947 ONE-SAMPLE %.0f (%.0f min); TWO-SAMPLE (V287 vs a V282 drive) %.0f (%.0f min)" % (
            t, n0, 100*se, need_paired, need_paired/n0*(G[t]["eng"].sum()/FS)/60.0,
            need_2samp, need_2samp/n0*(G[t]["eng"].sum()/FS)/60.0))
