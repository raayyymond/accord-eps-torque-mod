# -*- coding: utf-8 -*-
"""Is the GRIND measurable in MANUAL creep?  If so, it discriminates V158 from V172.

Both levers act at 15-25 Hz and both are on the fly-first build, so a grind change needs
attributing.  They act through different lanes AND different gates:

    V158  gp-0x6bd0, the damper lane   -- ENGAGED MODES 26/27 ONLY
    V172  gp-0x6b86, the assist map    -- ALWAYS ACTIVE, engaged or not

=> if the grind also falls in MANUAL creep, that is V172's filter.
   if it falls only when engaged, that is V158's damper.

That discriminator is free -- the manual pass is already on the drive card as optional --
but it only works if the grind is actually PRESENT in manual to begin with.  The ratchet is
not (0/7 routes).  Test the grind the same way.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
RNG = np.random.default_rng(77)
ROUTES = [('r78','V91'),('r7e','V96'),('r7f','V96'),('r96','V102'),
          ('ra6','V106'),('r1e','V107'),('r22','V112'),('r24','V122')]

def pooled(segs):
    acc,f=[],None
    for s in segs:
        f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    return f, np.median(np.asarray(acc),0)
def exc(f,M,band):
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use &= ~((f>=lo)&(f<=hi))
    if use.sum()<6 or not np.all(np.isfinite(M[use])): return np.nan,np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    w=(f>=band[0])&(f<=band[1])
    return float(np.max(M[w]/bg[w])), float(c[0])
def coloured(n,beta):
    w=RNG.standard_normal(n); F=np.fft.rfft(w); fr=np.fft.rfftfreq(n,1.0/FS)
    g=np.ones_like(fr); g[1:]=fr[1:]**(-beta/2.0); g[0]=g[1]
    return np.fft.irfft(F*g,n)
def null95(slope,nseg,band,trials=150):
    out=[]
    for _ in range(trials):
        f,M=pooled([coloured(NPS,-slope) for _ in range(nseg)])
        e,_=exc(f,M,band)
        if np.isfinite(e): out.append(e)
    return float(np.percentile(out,95)) if out else np.nan
def segs(tag,eng):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(v),len(a)); lat,kmh,a=lat[:n],v[:n]*3.6,a[:n]
    ok=(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)&((lat>0.5) if eng else (lat<=0.5))
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    return [a[i:j] for i,j in zip(st,en) if (j-i)>=NPS and np.std(a[i:j])>0]

print('GRIND 15-25 Hz, engaged vs MANUAL creep\n')
print('%-6s %-6s %-15s %-15s %s'%('route','build','engaged exc/null','manual exc/null','manual real?'))
nman=0; tot=0
for tag,bld in ROUTES:
    e,m=segs(tag,True),segs(tag,False)
    if len(e)<4 or len(m)<4:
        print('%-6s %-6s  -- arms too small (eng %d, man %d)'%(tag,bld,len(e),len(m))); continue
    fe,Me=pooled(e); fm,Mm=pooled(m)
    ee,sle=exc(fe,Me,GRIND); em,slm=exc(fm,Mm,GRIND)
    ne=null95(sle,len(e),GRIND); nm=null95(slm,len(m),GRIND)
    real = em>nm; nman+=real; tot+=1
    print('%-6s %-6s %-15s %-15s %s'%(tag,bld,'%.1f / %.1f'%(ee,ne),'%.1f / %.1f'%(em,nm),
          'YES' if real else 'no'))
print('\n  grind clears its null in MANUAL on %d of %d routes'%(nman,tot))
print('  (the RATCHET clears it in manual on 0 of 7 -- measured earlier)')
