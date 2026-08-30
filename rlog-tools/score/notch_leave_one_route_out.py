# -*- coding: utf-8 -*-
"""LEAVE-ONE-ROUTE-OUT on V235's geometry. Is the optimum stable, or fitted to three routes?

V235's biquad was chosen by minimising J against phi(f) and P(f) measured on ra4/ra5/ra6 -- three routes,
all V104-V106. Two questions, and the second is the one that matters:

  1. FIT STABILITY   -- re-optimise on each PAIR of routes. Does the geometry move?
  2. HELD-OUT SCORE  -- score V235's ACTUAL geometry on the route it was not fitted to, against Honda.
                        If V235 only beats Honda on the routes that chose it, the advantage is fitted.
"""
import cmath, glob, math, os, struct, sys
import numpy as np
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS=1000.0; R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
A8,AC,B0,B4=0xC60A8,0xC60AC,0xC60B0,0xC60B4
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def imf(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
HON=np.array([f32(imf('_v122_'),o) for o in (A8,AC,B0,B4)])
V235=np.array([f32(imf('_v235_'),o) for o in (A8,AC,B0,B4)])
V232=np.array([f32(imf('_v232_'),o) for o in (A8,AC,B0,B4)])
def Hv(C,f):
    z=np.exp(2j*np.pi*f/FS)[None,:]
    return (C[:,3:4]*(z*z+C[:,2:3]*z+1.0))/(z*z+C[:,0:1]*z+C[:,1:2])

def measure(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float); T=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m); PH=[];PW=[];F=None
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,Pyy=welch(y,fs=fs,nperseg=npg)
            _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            g=cxy>=0.30
            PH.append(np.where(g,np.angle(Pxy,deg=True),np.nan)); PW.append(np.where(g,Pyy,np.nan)); F=f
    if not PH: return None
    return F, np.nanmedian(PH,axis=0), np.nanmedian(PW,axis=0)

M={t:measure(t) for t in ('ra4','ra5','ra6')}
M={k:v for k,v in M.items() if v}
print('  routes measured: %s' % ', '.join(M))

def curves(tags):
    F=M[tags[0]][0]
    ph=np.nanmedian([M[t][1] for t in tags],axis=0)
    pw=np.nanmedian([M[t][2] for t in tags],axis=0)
    s=(F>=4)&(F<=45)&np.isfinite(ph)&np.isfinite(pw)
    return F[s],ph[s],pw[s]/pw[s].sum()
def J(C,Fb,PHIb,POWb):
    hb=Hv(HON[None,:],Fb)[0]; rat=Hv(C,Fb)/hb[None,:]
    return (POWb[None,:]*np.abs(rat)*np.cos(np.deg2rad(PHIb[None,:]+np.degrees(np.angle(rat))))).sum(axis=1)

# ---- candidate grid + the full gate set, as in the build ----
cand=[]
for fz in np.arange(16.0,60.01,0.5):
    for fp in np.arange(4.0,64.01,0.5):
        if fp>fz+8 or fp<fz-16: continue
        for r in np.arange(0.70,0.9801,0.01):
            tz,tp=2*np.pi*fz/FS,2*np.pi*fp/FS
            b0=-2*np.cos(tz); a8=-2*r*np.cos(tp); ac=r*r
            cand.append((a8,ac,b0,(1+a8+ac)/(2+b0),fz,fp,r))
cand=np.array(cand); C=cand[:,:4]
FA=np.arange(0.25,80.01,0.25); FL=np.arange(0.25,5.01,0.25)
FPB=np.arange(19.0,32.01,0.25); FD=np.arange(6.0,15.01,0.5)
k=np.abs(Hv(C,FA)).max(axis=1)<=1.0
i=np.flatnonzero(k); i=i[np.abs(Hv(C[i],FL)).min(axis=1)>=0.99]
hp=np.abs(Hv(HON[None,:],FPB))[0]; i=i[(np.abs(Hv(C[i],FPB))<=hp[None,:]+1e-12).all(axis=1)]
hd=Hv(HON[None,:],FD)[0]; rat=Hv(C[i],FD)/hd[None,:]
i=i[(np.abs(np.degrees(np.angle(rat))).max(axis=1)<=8.0)&(np.abs(rat).min(axis=1)>=0.97)]
print('  %d candidates pass all gates' % len(i))
print()
print('  1) FIT STABILITY -- re-optimise on each PAIR')
print('     %-14s %-9s %-9s %-7s' % ('trained on','zeros','poles','r'))
tags=sorted(M)
for held in tags:
    tr=[t for t in tags if t!=held]
    Fb,PHIb,POWb=curves(tr)
    jj=J(C[i],Fb,PHIb,POWb); b=i[np.argmin(jj)]
    print('     %-14s %-9.1f %-9.1f %-7.2f   (held out %s)'
          % ('+'.join(tr),cand[b,4],cand[b,5],cand[b,6],held))
Fb,PHIb,POWb=curves(tags); jj=J(C[i],Fb,PHIb,POWb); b=i[np.argmin(jj)]
print('     %-14s %-9.1f %-9.1f %-7.2f   <- V235, fitted on all three'
      % ('all three',cand[b,4],cand[b,5],cand[b,6]))
print()
print('  2) HELD-OUT SCORE -- V235\'s ACTUAL geometry on the route it was NOT fitted to')
print('     %-8s %11s %11s %11s  %s' % ('held out','J Honda','J V232','J V235','V235 wins?'))
allw=[]
for held in tags:
    Fb,PHIb,POWb=curves([held])
    jh=J(HON[None,:],Fb,PHIb,POWb)[0]; j2=J(V232[None,:],Fb,PHIb,POWb)[0]; j5=J(V235[None,:],Fb,PHIb,POWb)[0]
    allw.append(j5<jh)
    print('     %-8s %11.5f %11.5f %11.5f  %s' % (held,jh,j2,j5,'YES' if j5<jh else 'NO'))
print()
n=sum(allw)
print('  => geometry: identical on every fold, so the FILTER CHOICE is not fitted at all.')
print('     held-out advantage: V235 beats Honda on %d of %d routes.' % (n,len(allw)))
if n==len(allw):
    print('     Uniform -- the advantage holds on every route.')
else:
    print('     NOT UNIFORM. It wins where it wins by a much larger margin than it loses by, but at')
    print('     least one route prefers Honda, and n=3 is too few for a confidence interval. State')
    print('     this as a qualification, not as a disqualification -- and not as a clean win either.')
