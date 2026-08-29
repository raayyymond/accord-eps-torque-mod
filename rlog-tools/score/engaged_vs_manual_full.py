# -*- coding: utf-8 -*-
"""Engaged vs manual, on the FULL 19-route corpus, per-route speed-matched.

The result was 7/7 engaged clearing their null and 0/7 manual, with a speed-matched ratio of
19.9x [4.82, 35.64] from only n=4 matched pairs.  The corpus holds 19 routes, so both the
presence/absence count and the ratio CI should sharpen.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
RNG = np.random.default_rng(303)
ROUTES = ['r78','r79','r7e','r7f','r81','r82','r85','r95','r96','r9e',
          'r21','ra4','ra5','ra6','r1e','r22','r97','r24','r77']

def arrs(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): return None
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(v),len(a)); return lat[:n],v[:n]*3.6,a[:n]

def band(tag,eng,lo,hi):
    d=arrs(tag)
    if d is None: return [],np.nan
    lat,kmh,a=d
    ok=(kmh>=lo)&(kmh<hi)&np.isfinite(a)&((lat>0.5) if eng else (lat<=0.5))
    dd=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(dd==1)[0],np.where(dd==-1)[0]
    segs,sp=[],[]
    for i,j in zip(st,en):
        for k in range(i,j-NPS+1,NPS//2):
            w=a[k:k+NPS]
            if np.std(w)>0: segs.append(w); sp.append(kmh[k:k+NPS].mean())
    return segs,(np.mean(sp) if sp else np.nan)

def overlap(tag):
    d=arrs(tag)
    if d is None: return None
    lat,kmh,_=d
    c=(kmh>=1.0)&(kmh<24.0)
    e=kmh[c&(lat>0.5)]; m=kmh[c&(lat<=0.5)]
    if len(e)<200 or len(m)<200: return None
    lo=max(np.percentile(e,5),np.percentile(m,5)); hi=min(np.percentile(e,95),np.percentile(m,95))
    return (lo,hi) if hi-lo>1.5 else None

def pooled(s):
    acc,f=[],None
    for x in s:
        f,P=signal.welch(x-x.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    return f,np.median(np.asarray(acc),0)

def exc(f,M,bd):
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use&=~((f>=lo)&(f<=hi))
    if use.sum()<6 or not np.all(np.isfinite(M[use])): return np.nan,np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    w=(f>=bd[0])&(f<=bd[1])
    return float(np.max(M[w]/bg[w])),float(c[0])

def coloured(n,beta):
    w=RNG.standard_normal(n); F=np.fft.rfft(w); fr=np.fft.rfftfreq(n,1.0/FS)
    g=np.ones_like(fr); g[1:]=fr[1:]**(-beta/2.0); g[0]=g[1]
    return np.fft.irfft(F*g,n)

def null95(sl,ns,bd,tr=100):
    o=[]
    for _ in range(tr):
        f,M=pooled([coloured(NPS,-sl) for _ in range(ns)])
        e,_=exc(f,M,bd)
        if np.isfinite(e): o.append(e)
    return float(np.percentile(o,95)) if o else np.nan

print('%-6s %-12s %-13s %-13s %-8s %s'%('route','band km/h','eng exc/null','man exc/null','ratio','gap'))
rat,ec,mc,n=[],0,0,0
for tag in ROUTES:
    ob=overlap(tag)
    if ob is None: continue
    lo,hi=ob
    es,se=band(tag,True,lo,hi); ms,sm=band(tag,False,lo,hi)
    if len(es)<4 or len(ms)<4: continue
    fe,Me=pooled(es); fm,Mm=pooled(ms)
    ee,sle=exc(fe,Me,RATCHET); em,slm=exc(fm,Mm,RATCHET)
    ne=null95(sle,len(es),RATCHET); nm=null95(slm,len(ms),RATCHET)
    gap=abs(se-sm); n+=1; ec+=ee>ne; mc+=em>nm
    r=ee/em if em>0 else np.nan
    print('%-6s %-12s %-13s %-13s %-8.2f %.1f%s'%(tag,'%.1f-%.1f'%(lo,hi),
          '%.1f / %.1f'%(ee,ne),'%.1f / %.1f'%(em,nm),r,gap,'' if gap<=2.0 else ' UNMATCHED'))
    if gap<=2.0 and np.isfinite(r): rat.append(r)
print('\n  engaged arm clears its null on %d/%d routes ; manual arm on %d/%d'%(ec,n,mc,n))
if len(rat)>=4:
    a=np.asarray(rat)
    b=[np.median(np.random.default_rng(s).choice(a,len(a))) for s in range(6000)]
    print('  speed-matched ratio (n=%d): median %.1fx  95%% CI [%.1f, %.1f]'
          %(len(a),np.median(a),np.percentile(b,2.5),np.percentile(b,97.5)))
    print('  earlier: n=4, median 19.9x [4.82, 35.64]')
