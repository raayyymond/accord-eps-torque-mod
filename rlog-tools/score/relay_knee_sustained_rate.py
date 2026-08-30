# -*- coding: utf-8 -*-
"""THE RELAY-KNEE LADDER, RE-RUN WITH SUSTAINED-RATE WINDOWS -- the fix the record itself names.

The flown 3-point ladder on 0xC40BC (V111 600 / V112 1800 / V122 3000, same slope, onsets 50/150/250)
returned a null. But the memory recording it says outright:

    "a weak instrument that found nothing, not a strong one that proved nothing. Testing the knee
     properly needs windows selected by SUSTAINED rate, or a within-frame cave rung instead of a
     spectrum."

Instantaneous rate-gating fragments the signal into pieces shorter than a spectral window -- 3 of 4
rate bands returned ZERO usable windows. This selects whole windows by their SUSTAINED rate instead:
a window counts for a band only if the rate stays inside it for the entire window. That is the
estimator the collision demanded, and it has not been run.
"""
import numpy as np, os, sys
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LADDER=[('r21','V111',600,50),('r22','V112',1800,150),('r24','V122',3000,250)]
RATE_BANDS=[('creep 0-3',0.0,3.0),('low 3-8',3.0,8.0),('mid 8-15',8.0,15.0),('high 15+',15.0,1e9)]
SYM=[('ratchet 6-9',6,9),('mid 9-12',9,12),('grind 15-22',15,22)]
CTL=(30,40)
WIN=2.5
def run(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    r=np.asarray(z['cs_rate']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(WIN*fs)); idx=np.flatnonzero(m)
    out={b[0]:[] for b in RATE_BANDS}
    for runidx in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(runidx)-n+1,n//2):          # 50 % overlap
            w=runidx[k:k+n]; a=np.abs(r[w])
            for nm,lo,hi in RATE_BANDS:
                # SUSTAINED: the whole window inside the band, not the instantaneous sample
                frac=float(np.mean((a>=lo)&(a<hi)))
                if frac>=0.80:
                    x=r[w]-r[w].mean()
                    f,P=welch(x,fs=fs,nperseg=min(len(w),int(round(1.0*fs))))
                    c=P[(f>=CTL[0])&(f<CTL[1])].mean()
                    if c<=0: break
                    out[nm].append([P[(f>=lo2)&(f<hi2)].mean()/c for _,lo2,hi2 in SYM])
                    break
    return {k:(np.array(v) if v else np.zeros((0,3))) for k,v in out.items()}

print('='*100)
print('  RELAY-KNEE LADDER, SUSTAINED-rate windows: >=80 %% of a 2.5 s window inside the band')
print('='*100)
print()
res={}
for tag,bld,knee,onset in LADDER:
    d=run(tag)
    if d is None: print('  %s missing'%tag); continue
    res[bld]=d
    print('  %-6s %-6s knee %-5d onset %-4d  windows per sustained-rate band: %s'
          % (tag,bld,knee,onset, '  '.join('%s=%d'%(k.split()[0],len(v)) for k,v in d.items())))
print()
for nm,_,_ in RATE_BANDS:
    have=[b for b in res if len(res[b][nm])>=5]
    if len(have)<2:
        print('  %-12s under-powered (%s) -- skipped' % (nm, ', '.join('%s:%d'%(b,len(res[b][nm])) for b in res)))
        continue
    print('  %-12s  %s' % (nm, '  '.join('%14s'%s[0] for s in SYM)))
    for bld in ('V111','V112','V122'):
        if bld not in res or len(res[bld][nm])<5: continue
        med=np.median(res[bld][nm],axis=0)
        print('    %-8s n=%-5d %s' % (bld,len(res[bld][nm]),'  '.join('%14.3f'%v for v in med)))
    print()
print('  The ladder is only informative where the three knees actually DIFFER: above 50 counts of')
print('  rate. If the ratchet band shows no ordering even in the sustained HIGH-rate windows, the')
print('  knee is not the ratchet lever. If it orders there, the earlier null was the instrument.')
