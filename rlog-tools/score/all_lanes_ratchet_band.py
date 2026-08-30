# -*- coding: utf-8 -*-
"""WHICH LANE PUMPS AT THE RATCHET? Score EVERY tapped lane on cos(phi) at 6-9 Hz.

The net-damping metric was developed for the notch and applied only there. Every other aggregator lane
that has ever been on the wire can be scored the same way -- and the ratchet at 7.79 Hz is the
operator's oldest unfixed symptom, so the question that matters is: WHICH LANE PUMPS AT 6-9 Hz?

Same convention throughout: cos(phase of the lane vs WHEEL RATE) < 0 = damping, > 0 = pumping,
fixed by the kit's own b26 result.

The taps, decoded from 0x55DF2 in each build's image:
    gp-0x6B26  r77 r78 r7d     gp-0x6B70  r7e r80 r81 r82   gp-0x6B94  r95  (the AGGREGATE)
    gp-0x6B4C  r96 r9e         gp-0x6B86  ra4 ra5 ra6       gp-0x6C2C  r1e
    gp-0x6ABC  r21 r22 r24
"""
import glob, os, struct, sys
import numpy as np
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
TAPS={'r77':'V90','r78':'V91','r7d':'V94','r7e':'V96','r80':'V97','r81':'V98','r82':'V99',
      'r95':'V101','r96':'V102','r9e':'V103','ra4':'V104','ra5':'V105','ra6':'V106','r1e':'V107',
      'r21':'V111','r22':'V112','r24':'V122'}
def im(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
def tap_of(build):
    b=im('_v%s_'%build[1:].lower())
    if b is None: return None
    return 0x10000-struct.unpack_from('<H',b,0x55DF2)[0]

BANDS=[(6,9),(9,12),(15,22),(22,30)]
def score(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float); T=np.asarray(z['tq']).astype(float)
    q=np.asarray(z['cs_tq']).astype(float) if 'cs_tq' in ks else None
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m)
    lane={b:[] for b in BANDS}; drv={b:[] for b in BANDS}
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,c1=coherence(x,y,fs=fs,nperseg=npg)
            if q is not None:
                yy=q[s]-q[s].mean()
                _,Pd=csd(x,yy,fs=fs,nperseg=npg); _,Pxx=welch(x,fs=fs,nperseg=npg)
                _,c2=coherence(x,yy,fs=fs,nperseg=npg)
            for bd in BANDS:
                sel=(f>=bd[0])&(f<bd[1])
                if c1[sel].mean()>=0.30:
                    lane[bd].append(np.cos(np.angle(Pxy[sel].mean())))
                if q is not None and c2[sel].mean()>=0.30:
                    drv[bd].append(float(np.real(Pd[sel]/np.maximum(Pxx[sel],1e-30)).mean()))
    return ({b:(np.median(v),len(v)) for b,v in lane.items() if len(v)>=5},
            {b:(np.median(v),len(v)) for b,v in drv.items() if len(v)>=5})

print('='*104)
print('  EVERY TAPPED LANE, scored on cos(phi vs wheel rate).  <0 = DAMPS,  >0 = PUMPS')
print('='*104)
print()
print('  %-5s %-6s %-11s %s' % ('route','build','tap',' '.join('%13s'%('%d-%d Hz'%b) for b in BANDS)))
rows={}
for tag,bld in sorted(TAPS.items(), key=lambda kv: kv[1]):
    tp=tap_of(bld)
    r=score(tag)
    if r is None or not r[0]: continue
    lane,drv=r
    rows.setdefault(tp,[]).append((tag,bld,lane))
    print('  %-5s %-6s gp-0x%04X   %s' % (tag,bld,tp,
        ' '.join(('%+8.3f n%-3d'%lane[b][:2]) if b in lane else '%13s'%'--' for b in BANDS)))
print()
print('  BY TAP (median over its routes):')
print('  %-12s %-6s %s' % ('lane','n rt',' '.join('%13s'%('%d-%d Hz'%b) for b in BANDS)))
for tp,rs in sorted(rows.items()):
    cells=[]
    for b in BANDS:
        v=[l[b][0] for _,_,l in rs if b in l]
        cells.append('%+13.3f'%np.median(v) if v else '%13s'%'--')
    print('  gp-0x%04X    %-6d %s' % (tp,len(rs),' '.join(cells)))
print()
print('  => a lane with cos > 0 at 6-9 Hz would be INJECTING energy at the ratchet.')
