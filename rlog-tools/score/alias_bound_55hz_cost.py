# -*- coding: utf-8 -*-
"""HOW MUCH DOES GIVING UP HONDA'S 55 Hz CUT ACTUALLY COST? A differential measurement.

The 55 Hz content cannot be recovered from a route where Honda's notch is in force -- |H| = 0.0063
there, so de-embedding means multiplying by 25,000, which is the numerically invalid operation caught
earlier. But there is a way in:

    ra4 (V104) runs HONDA's notch          -> 55 Hz cut 159x
    ra5 (V105) runs V105's ~25.5 Hz notch  -> 55 Hz LEFT ALONE

and ra4/ra5 share the SAME b26 lane dose (1.5x), so they differ in the notch and little else.

CAN samples at ~101 Hz, so 52-71 Hz FOLDS into 30-49 Hz. If the lane carries real 55-71 Hz energy,
ra5's folded band must exceed ra4's -- and the difference IS what Honda's notch removes, i.e. what
V235 gives back.
"""
import glob, os, struct, sys, cmath, math
import numpy as np
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS=1000.0; R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
A8=0xC60A8
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def imf(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
def C(b): return tuple(f32(b,A8+4*k) for k in range(4))
def H(c,f):
    a8,ac,b0,b4=c; z=cmath.exp(2j*math.pi*f/FS)
    return abs(b4*(z*z+b0*z+1.0)/(z*z+a8*z+ac))
HON=C(imf('_v122_')); V105=C(imf('_v105_')); V235=C(imf('_v235_'))
print('  |H| at the frequencies that ALIAS into the CAN 30-49 Hz band:')
print('  %-8s %10s %10s %10s %10s' % ('true Hz','aliases to','Honda','V105','V235'))
for f in (52,55,58,61,65,68,71):
    print('  %-8d %9.1f  %10.4f %10.4f %10.4f' % (f, abs(101.0-f), H(HON,f), H(V105,f), H(V235,f)))
print()
print('  => Honda CUTS this region hard; V105 passes it; V235 passes it too.')
print('     So ra5 minus ra4 in the folded band bounds what Honda removes -- and what V235 gives back.')
print()

def band_power(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    T=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m); acc=[]
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; y=T[s]-T[s].mean()
            f,P=welch(y,fs=fs,nperseg=min(len(s),int(round(4*fs))))
            acc.append(P)
    if not acc: return None
    return f, np.median(acc,axis=0), fs

BANDS=[('4-15',4,15),('15-30',15,30),('30-40',30,40),('40-49',40,49)]
print('  ENGAGED lane power, normalised to the 4-15 Hz band (which BOTH notches leave alone):')
print('  %-6s %-7s %s' % ('route','notch',' '.join('%12s'%b[0] for b in BANDS)))
res={}
for tag,lbl in (('ra4','Honda'),('ra5','V105')):
    r=band_power(tag)
    if r is None: print('  %-6s (no data)'%tag); continue
    f,P,fs=r
    ref=P[(f>=4)&(f<15)].sum()
    vals=[P[(f>=lo)&(f<hi)].sum()/ref for _,lo,hi in BANDS]
    res[tag]=vals
    print('  %-6s %-7s %s' % (tag,lbl,' '.join('%12.5f'%v for v in vals)))
if 'ra4' in res and 'ra5' in res:
    print()
    print('  ra5 / ra4 in each band  (>1 means V105\'s notch lets through what Honda cuts):')
    for i,(nm,_,_) in enumerate(BANDS):
        a,b=res['ra4'][i],res['ra5'][i]
        print('    %-8s %8.3fx' % (nm, b/max(a,1e-12)))
    i30=[k for k,(nm,_,_) in enumerate(BANDS) if nm=='30-40'][0]
    i40=[k for k,(nm,_,_) in enumerate(BANDS) if nm=='40-49'][0]
    fold=(res['ra5'][i30]+res['ra5'][i40])-(res['ra4'][i30]+res['ra4'][i40])
    tot=1.0+res['ra5'][1]+res['ra5'][i30]+res['ra5'][i40]
    print()
    print('  EXCESS in the folded band (ra5 - ra4), as a fraction of ra5\'s whole 4-49 Hz power:')
    print('    %+.4f  =  %+.2f %%' % (fold/tot, 100*fold/tot))
    print()
    if abs(fold/tot) < 0.02:
        print('  => Honda\'s 55 Hz notch is removing LESS THAN 2 %% of the lane\'s energy.')
        print('     V235 gives that back. MECHANICALLY the 55 Hz cost is negligible; whatever the')
        print('     operator may hear is acoustic, not a change in what the lane delivers.')
    else:
        print('  => the folded band carries real energy Honda is removing. The 55 Hz cost is NOT')
        print('     negligible mechanically, and the drive card must say so more sharply.')
