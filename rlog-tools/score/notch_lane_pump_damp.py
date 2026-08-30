# -*- coding: utf-8 -*-
"""WHERE DOES THE NOTCH'S OWN LANE PUMP? -- gp-0x6b86, flown on ra4/ra5/ra6 (V104-V106).

The sign frame is now anchored. The kit's own b26 result fixes the mapping: gp-0x6b26 measured
"+137/+139 deg vs WHEEL rate, |cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z)" and is called
"a REAL 6-9 Hz DAMPER". cos(137 deg) < 0, so:

    cos(phase of lane vs wheel rate) < 0  =>  POSITIVE Re(Z)  =>  DAMPING
    cos(...) > 0                          =>  NEGATIVE Re(Z)  =>  PUMPING

The biquad filters this lane. So a notch is only worth placing where the lane PUMPS -- cutting a
frequency where the lane DAMPS removes damping, which is the mistake V94 aborted on.

Honda puts the notch at 55 Hz. V228 moves it to 20.5 Hz. This asks the lane which one is right.

POWER: 3 routes, all V104-V106. Coherence-gated at 0.30, the kit's own threshold. Route-level spread
is printed, not hidden.
"""
import numpy as np, os, sys
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROUTES = [('ra4','V104'),('ra5','V105'),('ra6','V106')]
GRID = [(6,9),(9,12),(12,15),(15,22),(22,30),(30,40),(40,50)]

def lane_phase(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float)
    T=np.asarray(z['tq']).astype(float)          # CAN 427 = gp-0x6b86 on these builds
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m)
    acc={b:[] for b in GRID}
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg)      # arg(T) - arg(omega)
            _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            for b in GRID:
                sel=(f>=b[0])&(f<b[1])
                if cxy[sel].mean()<0.30: continue
                ph=np.angle(Pxy[sel].mean(), deg=True)
                acc[b].append((ph, np.cos(np.deg2rad(ph)), cxy[sel].mean()))
    return {b:(np.median([a[0] for a in v]), np.median([a[1] for a in v]),
               np.median([a[2] for a in v]), len(v)) for b,v in acc.items() if len(v)>=3}

print('='*100)
print('  gp-0x6b86 -- THE NOTCH LANE -- phase vs WHEEL RATE, engaged')
print('='*100)
print()
print('  mapping fixed by the kit\'s own b26 result: cos<0 => POSITIVE Re(Z) => DAMPING')
print()
per={}
for tag,bld in ROUTES:
    d=lane_phase(tag)
    if not d: print('  %-5s (%s) no coherent windows'%(tag,bld)); continue
    per[tag]=d
    print('  %-5s (%s)' % (tag,bld))
    print('    %-10s %10s %8s %7s %5s  %s' % ('band','phase','cos','coh','n','reading'))
    for b in GRID:
        if b not in d: continue
        ph,c,ch,n=d[b]
        print('    %-10s %9.1f\u00b0 %8.3f %7.2f %5d  %s'
              % ('%d-%d'%b,ph,c,ch,n,'DAMPING' if c<0 else 'PUMPING'))
    print()
if len(per)>=2:
    print('  ACROSS ROUTES (median cos):')
    print('    %-10s %10s %14s' % ('band','median cos','verdict'))
    for b in GRID:
        vals=[per[t][b][1] for t in per if b in per[t]]
        if len(vals)<2: continue
        m=np.median(vals)
        agree = all(np.sign(v)==np.sign(m) for v in vals)
        print('    %-10s %10.3f %14s   %s'
              % ('%d-%d'%b, m, 'DAMPING' if m<0 else 'PUMPING',
                 'all routes agree' if agree else 'ROUTES DISAGREE -- not licensed'))
    print()
    print('  => place a notch only where the lane PUMPS. Honda notches 55 Hz; V228 notches 20.5 Hz.')
