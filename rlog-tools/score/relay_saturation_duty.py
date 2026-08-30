# -*- coding: utf-8 -*-
"""DOES THE COULOMB RELAY SATURATE ON THE CAR? Measured from data already in hand.

Decompiled FUN_0003b8f6:

    iVar20 = gp-0x6752 (polarity, +-1) * gp-0x6abc * 12
    uVar8  = cal(0xC40BC)                      the gate
    ratio  = iVar20 / uVar8
    relay  = clamp(ratio, -1, +1)              SATURATED when |ratio| >= 1

so the relay saturates when |gp-0x6abc| >= cal(0xC40BC)/12. And gp-0x6abc is ALREADY TAPPED on
r21 (V111, cal 600 -> onset 50), r22 (V112, 1800 -> 150) and r24 (V122, 3000 -> 250, THE CAR).

That is the ladder's own onset column, derived independently from the decompile, and it means the
saturation duty is measurable from the existing caches with NO build at all.

The question that matters: does it saturate WHILE THE RATCHET IS PRESENT?
"""
import numpy as np, os, sys
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LAD=[('r21','V111',600),('r22','V112',1800),('r24','V122',3000)]
print('='*100)
print('  COULOMB RELAY SATURATION DUTY -- |gp-0x6abc| >= cal(0xC40BC)/12')
print('='*100)
print()
for tag,bld,cal in LAD:
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): print('  %s missing'%tag); continue
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if 'tq' not in ks: print('  %s no tap'%tag); continue
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    x=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    a=np.abs(x[m]); onset=cal/12.0
    print('  %-5s %-6s cal %-5d onset %6.1f   n_eng %6d' % (tag,bld,cal,onset,m.sum()))
    pc=np.percentile(a,[50,75,90,99])
    print('        |gp-0x6abc| percentiles: p50 %7.1f  p75 %7.1f  p90 %7.1f  p99 %7.1f  max %7.1f'
          % (pc[0],pc[1],pc[2],pc[3],a.max()))
    print('        SATURATION DUTY at its own onset: %.4f  (%.2f %% of engaged frames)'
          % (np.mean(a>=onset), 100*np.mean(a>=onset)))
    print()
print('  => a duty near 1.0 means a PURE RELAY (always saturated); near 0 means it never relays.')
print()
# the decisive conditional: does it saturate WHERE THE RATCHET IS?
print('='*100)
print('  CONDITIONED ON THE RATCHET -- duty in the windows with the MOST 6-9 Hz energy')
print('='*100)
print()
for tag,bld,cal in LAD:
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): continue
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'tq','cs_rate','cc_lat'} <= ks: continue
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    x=np.asarray(z['tq']).astype(float); r=np.asarray(z['cs_rate']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(4*fs)); idx=np.flatnonzero(m); rows=[]
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            w=run[k:k+n]; y=r[w]-r[w].mean()
            f,P=welch(y,fs=fs,nperseg=min(len(w),int(round(2*fs))))
            c=P[(f>=30)&(f<40)].mean()
            if c<=0: continue
            rows.append((P[(f>=6)&(f<9)].mean()/c, np.mean(np.abs(x[w])>=cal/12.0)))
    if len(rows)<20: print('  %-5s too few windows'%tag); continue
    rr=np.array(rows); q=np.quantile(rr[:,0],[0.25,0.75])
    lo=rr[rr[:,0]<=q[0],1]; hi=rr[rr[:,0]>=q[1],1]
    print('  %-5s %-6s n=%-4d   duty in LOW-ratchet windows %.4f   in HIGH-ratchet windows %.4f   %s'
          % (tag,bld,len(rr),lo.mean(),hi.mean(),
             'HIGHER when ratcheting' if hi.mean()>lo.mean() else 'lower when ratcheting'))
