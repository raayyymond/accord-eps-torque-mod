# -*- coding: utf-8 -*-
"""Score the WHOLE-ROUTE caches I never used.  The corpus is twice what I worked with.

I scored 9 routes.  There are ~19 whole-route caches with the core channels, and several
carry far more engaged-creep windows than anything I used -- r77 has 97 against r1e's 42.
The sNN entries are per-segment sub-caches of the same drives, so they are NOT independent
and are excluded.

This matters most for the one question left open on power: driven vs self-excited, whose
pooled CI crossed zero at n=7 and whose only well-powered route (r1e, 14 windows) showed a
5x specific margin.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
RNG = np.random.default_rng(101)
SCORED = ['r78','r7e','r7f','r96','ra4','ra6','r1e','r22','r24']
NEW    = ['r21','r77','r79','r81','r82','r85','r95','r97','r9e','ra5','r23','r1b','r80']

def runs(tag, ch='cs_tq'):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v',ch)): return []
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z[ch]).astype(float)
    n=min(len(lat),len(v),len(a)); lat,kmh,a=lat[:n],v[:n]*3.6,a[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    out=[]
    for i,j in zip(st,en):
        for k in range(i,j-NPS+1,NPS//2):
            w=a[k:k+NPS]
            if np.std(w)>0: out.append(w)
    return out

def pooled(segs):
    acc,f=[],None
    for s in segs:
        f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    return f,np.median(np.asarray(acc),0)

def exc(f,M,band):
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use&=~((f>=lo)&(f<=hi))
    if use.sum()<6 or not np.all(np.isfinite(M[use])): return np.nan,np.nan,np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    w=(f>=band[0])&(f<=band[1]); r=M[w]/bg[w]
    return float(np.max(r)),float(c[0]),float(f[w][int(np.argmax(r))])

def coloured(n,beta):
    w=RNG.standard_normal(n); F=np.fft.rfft(w); fr=np.fft.rfftfreq(n,1.0/FS)
    g=np.ones_like(fr); g[1:]=fr[1:]**(-beta/2.0); g[0]=g[1]
    return np.fft.irfft(F*g,n)

def null95(slope,nseg,band,trials=120):
    out=[]
    for _ in range(trials):
        f,M=pooled([coloured(NPS,-slope) for _ in range(nseg)])
        e,_,_=exc(f,M,band)
        if np.isfinite(e): out.append(e)
    return float(np.percentile(out,95)) if out else np.nan

print('%-7s %-6s %-9s %-13s %-13s %s'%('route','new?','windows','RATCHET/null','GRIND/null','peak Hz'))
tot=0
for tag in SCORED+NEW:
    s=runs(tag)
    if len(s)<6:
        continue
    f,M=pooled(s)
    er,sl,pk=exc(f,M,RATCHET); eg,_,_=exc(f,M,GRIND)
    nr=null95(sl,len(s),RATCHET); ng=null95(sl,len(s),GRIND)
    print('%-7s %-6s %-9d %-13s %-13s %.2f'%(tag,'NEW' if tag in NEW else '',len(s),
          '%.1f / %.1f'%(er,nr),'%.1f / %.1f'%(eg,ng),pk))
    tot+=1
print('\n  routes scoreable with >=6 windows: %d  (was 9)'%tot)
