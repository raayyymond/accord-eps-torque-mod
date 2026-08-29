# -*- coding: utf-8 -*-
"""Driven vs self-excited, on the FULL 19-route corpus.

At n=7 this was inconclusive: band-specific coupling was specific on 6/9 routes but the
pooled 95 % CI [-0.021, +0.176] crossed zero.  The only well-powered route (r1e, 14 windows)
gave +0.522 against a shuffled p95 of +0.097 -- the signature of a real effect seen at
insufficient power.  The corpus turns out to be twice what I used, so this is the test that
power was missing for.

Statistic unchanged: coherence(7-10.5 Hz) minus coherence(30-40 Hz control band), command
-> cs_tq, against phase-shuffled surrogates that preserve the spectrum and destroy timing.
"""
import os, sys
import numpy as np
from scipy import signal, stats
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
BAND, CTRL = (7.0, 10.5), (30.0, 40.0)
ROUTES = ['r78','r7e','r7f','r96','ra4','ra6','r1e','r22','r24',
          'r21','r77','r79','r81','r82','r85','r95','r97','r9e','ra5']

def segs(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq','sc_tq')): return []
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float); c=np.asarray(z['sc_tq']).astype(float)
    n=min(len(lat),len(v),len(a),len(c)); lat,kmh,a,c=lat[:n],v[:n]*3.6,a[:n],c[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)&np.isfinite(c)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    return [(c[i:j],a[i:j]) for i,j in zip(st,en) if (j-i)>=NPS and np.std(a[i:j])>0 and np.std(c[i:j])>0]

def spec(pairs):
    acc,f=[],None
    for x,y in pairs:
        f,C=signal.coherence(x-x.mean(),y-y.mean(),FS,nperseg=NPS//2,noverlap=NPS//4)
        acc.append(C)
    M=np.median(np.asarray(acc),0)
    return float(np.max(M[(f>=BAND[0])&(f<=BAND[1])])-np.max(M[(f>=CTRL[0])&(f<=CTRL[1])]))

def shuf(a,rng):
    F=np.fft.rfft(a-a.mean()); ph=rng.uniform(0,2*np.pi,len(F)); ph[0]=0
    return np.fft.irfft(np.abs(F)*np.exp(1j*ph),len(a))

print('%-7s %-7s %-11s %-11s %s'%('route','pairs','specificity','shuf p95','verdict'))
vals,wins=[],[]
for tag in ROUTES:
    s=segs(tag)
    if len(s)<4: continue
    v=spec(s)
    rng=np.random.default_rng(0)
    null=[spec([(shuf(x,rng),y) for x,y in s]) for _ in range(30)]
    p95=float(np.percentile(null,95))
    ok=v>p95
    print('%-7s %-7d %-+11.3f %-+11.3f %s'%(tag,len(s),v,p95,'SPECIFIC' if ok else '-'))
    vals.append(v); wins.append(len(s))
vals=np.asarray(vals)
b=[np.median(np.random.default_rng(s).choice(vals,len(vals))) for s in range(6000)]
lo,hi=np.percentile(b,2.5),np.percentile(b,97.5)
print('\n  n = %d routes (was 7)'%len(vals))
print('  median specificity %+.4f   95%% CI [%+.4f, %+.4f]'%(np.median(vals),lo,hi))
print('  CI %s zero  =>  %s'%('EXCLUDES' if lo>0 else 'still crosses',
      'DRIVEN: the command drives the ratchet' if lo>0 else 'still inconclusive'))
w=np.asarray(wins,float)
r,pv=stats.spearmanr(w,vals)
print('  specificity vs window count: rho %+.2f p %.3f  (%s)'%(r,pv,
      'more windows => larger effect, as an underpowered real effect predicts' if r>0 else 'no such trend'))
