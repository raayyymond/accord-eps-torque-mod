# -*- coding: utf-8 -*-
"""The CHANNEL survey on the full corpus.  This is the most load-bearing result of the session.

It set the scorer's channel: cs_tq at margin 7.42 against cs_rate at 1.03 (chance), which is
why score_band_excess.py was switched and why "every prior 6-9 Hz endpoint read the wrong
channel" is claimed.  It rested on FOUR routes.  Two other n<=9 claims have already fallen on
the full corpus, so this one must be re-tested before it is trusted further.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
RNG = np.random.default_rng(909)
CHANS = ['tq','cs_tq','ws_fl','ws_fr','cs_rate','cs_ang','ang','wang','sc_tq','co_tqcan','cc_req']
ROUTES = ['r78','r79','r7e','r7f','r81','r82','r85','r95','r96','r9e',
          'r21','r77','ra4','ra5','ra6','r1e','r22','r97','r24']

def segs(tag, ch):
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

_NULLC={}
def null95(sl,ns,bd,tr=60):
    # memoised: the null depends only on the spectral slope and the window count, and many
    # channel/route pairs share both.  Without this the sweep is 11 x 19 nulls and times out.
    key=(round(sl,1), min(ns,60)//4*4, bd)
    if key in _NULLC: return _NULLC[key]
    o=[]
    for _ in range(tr):
        f,M=pooled([coloured(NPS,-key[0]) for _ in range(max(key[1],4))])
        e,_=exc(f,M,bd)
        if np.isfinite(e): o.append(e)
    v=float(np.percentile(o,95)) if o else np.nan
    _NULLC[key]=v
    return v

print('RATCHET 5-12 Hz margin (excess / slope-matched null), FULL corpus\n')
print('%-10s %-8s %-11s %-11s %-11s %s'%('channel','routes','mean margin','median','min','n=4 result'))
OLD={'tq':7.62,'cs_tq':7.42,'ws_fr':4.41,'ws_fl':3.95,'cs_rate':1.03,
     'cs_ang':0.79,'ang':0.83,'wang':0.83,'sc_tq':0.56,'co_tqcan':0.59,'cc_req':0.67}
res={}
for ch in CHANS:
    m=[]
    for tag in ROUTES:
        s=segs(tag,ch)
        if len(s)<6: continue
        f,M=pooled(s); e,sl=exc(f,M,RATCHET)
        if not np.isfinite(e): continue
        p95=null95(sl,len(s),RATCHET)
        if p95>0: m.append(e/p95)
    if not m: print('%-10s  -- unavailable'%ch); continue
    res[ch]=np.mean(m)
    print('%-10s %-8d %-11.2f %-11.2f %-11.2f %.2f'%(ch,len(m),np.mean(m),np.median(m),np.min(m),OLD.get(ch,float('nan'))))
print('\nranked on the full corpus:')
for ch,v in sorted(res.items(), key=lambda kv:-kv[1]):
    print('  %-10s %.2f'%(ch,v))
