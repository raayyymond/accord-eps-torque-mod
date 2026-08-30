# -*- coding: utf-8 -*-
"""Does the gp-0x6b26 lane -- the one V230's alpha2 cut acts on -- carry 15-22 Hz at all?

V230 cuts that lane 2.53x at 18.5 Hz. That is worth nothing if the lane has no 15-22 Hz content, or if
its content is unrelated to the steering dynamics. Three flown routes carry gp-0x6b26 directly on CAN
427 (r77/V90, r78/V91, r7d/V94), decoded from 0x55DF2 in each image.

Two questions, both scale-free so the per-build wire scaling does not matter:
  1. band SHARE of the lane's own engaged power
  2. COHERENCE with wheel rate -- is the lane participating in the dynamics, or just carrying noise?
"""
import numpy as np, os, sys
from scipy.signal import welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BANDS = [(6,9),(9,12),(15,22),(22,30),(30,40),(40,50)]
ROUTES = [('r77','V90'),('r78','V91'),('r7d','V94')]

print('='*96)
print('  gp-0x6b26 (the V230 lane) -- band share and coherence with wheel rate, ENGAGED')
print('='*96)
rows=[]
for tag,bld in ROUTES:
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): continue
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    x=np.asarray(z['tq']).astype(float)
    r=np.asarray(z['cs_rate']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    idx=np.flatnonzero(m)
    if len(idx)<int(8*fs): continue
    nps=int(round(8*fs))
    P=[];C=[]
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        if len(run)<nps: continue
        xa=x[run]-x[run].mean(); ra=r[run]-r[run].mean()
        f,pp=welch(xa,fs=fs,nperseg=nps); _,cc=coherence(xa,ra,fs=fs,nperseg=nps)
        P.append(pp); C.append(cc)
    if not P: continue
    P=np.mean(P,axis=0); C=np.mean(C,axis=0)
    tot=P[(f>=4)&(f<50)].sum()
    print()
    print('  %s (%s)  fs %.1f Hz, %d engaged windows' % (tag,bld,fs,len(C)))
    print('    %-10s %10s %10s' % ('band','share of 4-50Hz','coh w/ rate'))
    row={}
    for lo,hi in BANDS:
        b=(f>=lo)&(f<hi)
        sh=P[b].sum()/tot; ch=C[b].mean()
        row[(lo,hi)]=(sh,ch)
        print('    %-10s %13.1f%% %10.3f' % ('%d-%d'%(lo,hi), 100*sh, ch))
    rows.append((tag,row))
if rows:
    print()
    print('  ACROSS ROUTES (median):')
    print('    %-10s %16s %12s' % ('band','share','coh w/ rate'))
    for lo,hi in BANDS:
        sh=np.median([r[1][(lo,hi)][0] for r in rows])
        ch=np.median([r[1][(lo,hi)][1] for r in rows])
        flag=''
        if (lo,hi)==(15,22): flag='  <== V230 cuts this 2.53x'
        print('    %-10s %15.1f%% %12.3f%s' % ('%d-%d'%(lo,hi),100*sh,ch,flag))
    print()
    print('  Coherence gate: the kit treats <0.30 as not interpretable.')
