# -*- coding: utf-8 -*-
"""THE ALL-LANES SCAN, REDONE AGAINST TORQUE -- correcting my own measurement site.

My earlier scan scored cos(phase of lane vs cs_rate) at 6-9 Hz and concluded no lane is the ratchet's
source. But the record measures the ratchet's margin per channel as

    tq 7.62 · cs_tq 7.42 · ws_fr 4.41 · cs_rate 1.03 (CHANCE)

so cs_rate does not carry the ratchet at all, and that scan was looking in the wrong place.

It also means the ENERGY framing is wrong for this symptom. Power is torque x velocity; if there is no
6-9 Hz velocity, there is no 6-9 Hz energy flow. A ratchet that lives in torque with the column nearly
still is a stick-slip against a held wheel, not a resonance exchanging energy. So the right question is
not "does the lane pump" but:

    WHICH LANE CARRIES THE 6-9 Hz TORQUE OSCILLATION, AND DOES IT LEAD IT?

Coherence says carries; phase says lead or lag. A driver should LEAD; a lane merely responding lags.
"""
import numpy as np, os, sys
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TAPS=[('r77','V90','gp-0x6B26'),('r78','V91','gp-0x6B26'),('r7e','V96','gp-0x6B70'),
      ('r95','V101','gp-0x6B94'),('r96','V102','gp-0x6B4C'),('r9e','V103','gp-0x6B4C'),
      ('ra4','V104','gp-0x6B86'),('ra5','V105','gp-0x6B86'),('ra6','V106','gp-0x6B86'),
      ('r1e','V107','gp-0x6C2C'),('r21','V111','gp-0x6ABC'),('r22','V112','gp-0x6ABC'),
      ('r24','V122','gp-0x6ABC')]
BAND=(6,9); CTL=(30,40)
def scan(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_tq','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    lane=np.asarray(z['tq']).astype(float); q=np.asarray(z['cs_tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m); co=[];ph=[];coc=[]
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            w=run[k:k+n]; x=lane[w]-lane[w].mean(); y=q[w]-q[w].mean()
            npg=min(len(w),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            b=(f>=BAND[0])&(f<BAND[1]); c=(f>=CTL[0])&(f<CTL[1])
            co.append(cxy[b].mean()); coc.append(cxy[c].mean())
            ph.append(np.angle(Pxy[b].mean(),deg=True))
    if len(co)<5: return None
    return np.median(co),np.median(coc),np.median(ph),len(co)
print('='*100)
print('  EVERY TAPPED LANE vs cs_tq at 6-9 Hz -- the channel the ratchet actually lives in')
print('='*100)
print()
print('  %-5s %-6s %-11s %8s %8s %10s %6s  %s' %
      ('route','build','lane','coh 6-9','coh ctl','phase','n','reading'))
rows={}
for tag,bld,nm in TAPS:
    r=scan(tag)
    if r is None: continue
    co,coc,ph,n=r
    # scipy.csd(x,y) returns arg(Y)-arg(X); with x=lane, y=cs_tq a POSITIVE phase means cs_tq
    # LEADS the lane, i.e. the lane FOLLOWS torque. The first version of this script printed the
    # opposite and would have named every lane a driver.
    lead = 'lane LAGS cs_tq (follows)' if 0 < ph < 180 else 'lane LEADS cs_tq'
    spec = 'specific' if co>coc+0.10 else ('NOT specific' if co<=coc else 'weak')
    rows.setdefault(nm,[]).append((co,coc,ph))
    print('  %-5s %-6s %-11s %8.3f %8.3f %9.1f\u00b0 %6d  %s, %s' % (tag,bld,nm,co,coc,ph,n,spec,lead))
print()
print('  BY LANE (median). NOTE the uniformity below is itself the finding: every lane is a filtered')
print('  function of the SAME torque sensor, so high coherence with cs_tq is trivial and shared.')
print('  %-12s %-6s %9s %9s %10s  %s' % ('lane','n rt','coh 6-9','coh ctl','phase','verdict'))
for nm,v in sorted(rows.items(), key=lambda kv:-np.median([a[0] for a in kv[1]])):
    co=np.median([a[0] for a in v]); coc=np.median([a[1] for a in v]); ph=np.median([a[2] for a in v])
    band_specific = co > coc+0.10
    leads = not (0 < ph < 180)      # a DRIVER must lead, i.e. NEGATIVE phase by the convention above
    print('  %-12s %-6d %9.3f %9.3f %9.1f\u00b0  %s' % (nm,len(v),co,coc,ph,
        'CANDIDATE -- specific AND leads' if (band_specific and leads)
        else ('specific but FOLLOWS torque -- not a driver' if band_specific
              else 'not band-specific')))
