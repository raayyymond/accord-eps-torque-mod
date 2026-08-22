import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(9)
NPS=512; WN=np.hanning(NPS); U=(WN**2).sum()
FINE=[(0.5,1.5),(1.5,3.0),(3.0,4.5),(4.5,6.0),(6.0,7.5),(7.5,9.0),(9.0,12.0),(12.0,16.0),(20.0,24.0)]

t,e4,y,m,meta=M.load("73")
z=dict(np.load('_cache_r73/r73.npz',allow_pickle=True))
ang=np.asarray(z["ang"],float)
eng=m["eng"]; off=eng&~m["press"]
blks=[]
for a,b in M.episodes(off,t,5.2):
    s=a;n=int(20*M.FS)
    while s+NPS<=b:
        e=min(s+n,b)
        if e-s>=NPS: blks.append((s,e))
        s=e
def F(sig):
    A=[]
    for a,b in blks:
        for s in range(a,b-NPS+1,NPS//2):
            x=sig[s:s+NPS]; A.append(np.fft.rfft((x-x.mean())*WN))
    return np.array(A)
E,Y,Z = F(e4),F(y),F(ang)
f=np.fft.rfftfreq(NPS,1/M.FS); nw=len(E)
bid=[]
for i,(a,b) in enumerate(blks):
    for s in range(a,b-NPS+1,NPS//2): bid.append(i)
bid=np.array(bid); nb=len(blks)

def spec(idx):
    S={}
    for k,A in (("E",E),("Y",Y),("Z",Z)):
        for k2,B in (("E",E),("Y",Y),("Z",Z)):
            S[k+k2]=(np.conj(A[idx])*B[idx]).mean(0)
    return S
def partial(S,lo,hi):
    b=M.band(f,lo,hi)
    EE,YY,ZZ = S["EE"][b].sum().real, S["YY"][b].sum().real, S["ZZ"][b].sum().real
    EY,EZ,ZY = S["EY"][b].sum(), S["EZ"][b].sum(), S["ZY"][b].sum()
    EYz = EY - EZ*ZY/ZZ
    EEz = EE - abs(EZ)**2/ZZ
    YYz = YY - abs(ZY)**2/ZZ
    c=float(np.mean(M.interp_corr(f[b])))
    g2 = abs(EYz)**2/max(EEz*YYz,1e-30)
    H  = abs(EYz)/max(EEz,1e-30)/np.sqrt(c)
    g2_raw = abs(EY)**2/max(EE*YY,1e-30)
    H_raw  = abs(EY)/max(EE,1e-30)/np.sqrt(c)
    g2_ez  = abs(EZ)**2/max(EE*ZZ,1e-30)
    return g2_raw,H_raw,g2,H,g2_ez

S0=spec(np.arange(nw))
print("ROUTE 73 (V88) HANDS-OFF SIGNED  win=%d blocks=%d 224 s"%(nw,nb))
print("  band        g2(e4,6b98)  H1     | g2(e4,ANGLE) | PARTIAL on ANGLE: g2  H  [boot 95%]   shufH_p95")
for lo,hi in FINE:
    g0,h0,gp,hp,gez = partial(S0,lo,hi)
    bo=[]
    for _ in range(400):
        pk=rng.integers(0,nb,nb); ii=np.concatenate([np.where(bid==q)[0] for q in pk])
        bo.append(partial(spec(ii),lo,hi)[3])
    sh=[]
    for _ in range(200):
        p=rng.permutation(nw); bad=bid[p]==bid
        if bad.any(): p[bad]=np.roll(p,1)[bad]
        Sp={}
        for k,A in (("E",E),("Y",Y[p]),("Z",Z)):
            for k2,B in (("E",E),("Y",Y[p]),("Z",Z)): Sp[k+k2]=(np.conj(A)*B).mean(0)
        sh.append(partial(Sp,lo,hi)[3])
    print("  %4.1f-%-5.1f  %8.4f  %6.3f  |   %6.4f     |   %7.4f  %6.3f [%5.3f,%5.3f]  %6.3f"%(
        lo,hi,g0,h0,gez,gp,hp,np.percentile(bo,2.5),np.percentile(bo,97.5),np.percentile(sh,95)))

# ---- FIT the arbitration IIR to the partial gain, 0.5-6 Hz, unknown loop rate fL
def iir(fq,fL,a=992/1024.,b0=507/1024.):
    zq=np.exp(-2j*np.pi*fq/fL)
    Hs=b0/(1-a*zq); Ho=Hs*(1+zq)/32.0
    dc=(b0/(1-a))*2/32.0
    return np.abs(Ho)/dc
lo_pts=[(1.0,),(2.25,),(3.75,),(5.25,)]
meas=[]
for lo,hi in FINE[:4]:
    meas.append(((lo+hi)/2, partial(S0,lo,hi)[3]))
G0=meas[0][1]
best=None
for fL in np.arange(50,1500,1.0):
    err=sum((G0*iir(fc,fL)-gm)**2 for fc,gm in meas)
    if best is None or err<best[1]: best=(fL,err)
fL=best[0]
print("\n  IIR fit (pole 992/1024, out=(s[n-1]+s[n])/32) to the PARTIAL gain over 0.5-6 Hz:")
print("    best loop rate fL = %.0f Hz   (tau = 31.5 cycles = %.1f ms, corner %.2f Hz)"%(fL,31.5/fL*1000,fL/(2*np.pi*31.5)))
for fc,gm in meas: print("      f=%5.2f Hz  measured %.3f   model %.3f"%(fc,gm,G0*iir(fc,fL)))
for fq in (6.0,7.5,8.0,9.0,21.0):
    print("      EXTRAPOLATED model gain at %5.2f Hz = %.4f  (x G0=%.3f -> %.4f ct/ct)"%(fq,iir(fq,fL),G0,G0*iir(fq,fL)))
