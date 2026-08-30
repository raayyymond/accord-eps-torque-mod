# -*- coding: utf-8 -*-
"""DOES THE AGGREGATE PUMP WHERE THE LANE PUMPS? The check that decides whether cutting is worth it.

gp-0x6b86 (the notch lane) is ONE of about six lanes summed into the aggregator: the model gives the
add order at 0x3acc8-0x3ace6 as r26+r24 -> +6b86 -> +6bd0 -> +6bbe -> +6b26 -> +[6b62/6ade].

So the lane pumping at 19-32 Hz is necessary but not sufficient. If the other lanes cancel it at the
SUM, then notching the lane buys nothing that reaches the motor.

r95 (V101) carries HONDA's biquad and taps gp-0x6b94, the aggregator, so it can answer this directly --
a second route AND a second observable.

Same sign convention throughout: cos(phase of signal vs WHEEL RATE) < 0 = damping, > 0 = pumping.
"""
import glob, os, struct, sys
import numpy as np
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
def imf(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
b=imf('_v101_')
print('  V101 427 tap: gp-0x%04X   shift 0x%02X   biquad %s'
      % (0x10000-struct.unpack_from('<H',b,0x55DF2)[0], b[0x55E10], b[0xC60A8:0xC60A8+16].hex()))
hon=imf('_v122_')[0xC60A8:0xC60A8+16].hex()
print('  V122 (Honda) biquad %s   -> %s' % (hon, 'SAME' if b[0xC60A8:0xC60A8+16].hex()==hon else 'DIFFERENT'))
print()
BANDS=[(6,9),(9,12),(12,15),(15,19),(19,22),(22,26),(26,32),(32,40)]
def phases(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat','tq'} <= ks: return None
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float); T=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m)
    acc={b:[] for b in BANDS}
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,Pyy=welch(y,fs=fs,nperseg=npg)
            _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            for bd in BANDS:
                sel=(f>=bd[0])&(f<bd[1])
                if cxy[sel].mean()<0.30: continue
                ph=np.angle(Pxy[sel].mean(),deg=True)
                acc[bd].append((np.cos(np.deg2rad(ph)), Pyy[sel].mean(), cxy[sel].mean()))
    return {bd:(np.median([a[0] for a in v]), np.median([a[1] for a in v]),
                np.median([a[2] for a in v]), len(v)) for bd,v in acc.items() if len(v)>=3}

print('  %-9s | %-28s | %-28s' % ('band','r95  gp-0x6b94  THE SUM','ra4  gp-0x6b86  THE LANE'))
print('  %-9s | %8s %8s %6s | %8s %8s %6s' % ('','cos','pow %','coh','cos','pow %','coh'))
A=phases('r95'); B=phases('ra4')
if A and B:
    ta=sum(v[1] for v in A.values()); tb=sum(v[1] for v in B.values())
    agree=0; n=0
    for bd in BANDS:
        if bd not in A or bd not in B: continue
        a,bq=A[bd],B[bd]; n+=1
        same=(np.sign(a[0])==np.sign(bq[0])); agree+=same
        print('  %-9s | %8.3f %7.1f%% %6.2f | %8.3f %7.1f%% %6.2f  %s'
              % ('%d-%d'%bd, a[0],100*a[1]/ta,a[2], bq[0],100*bq[1]/tb,bq[2],
                 '' if same else '<- DISAGREE'))
    print()
    print('  sign agreement: %d of %d bands' % (agree,n))
    pump=[bd for bd in BANDS if bd in A and A[bd][0]>0]
    print('  the SUM pumps in: %s' % (', '.join('%d-%d'%b for b in pump) if pump else 'NO band'))
    key=[bd for bd in ((19,22),(22,26),(26,32)) if bd in A]
    if key:
        c=np.mean([A[bd][0] for bd in key])
        print('  aggregate 19-32 Hz mean cos = %+.3f  => the SUM %s there'
              % (c, 'PUMPS -- cutting the lane reaches the motor' if c>0 else
                    'DAMPS -- the other lanes DOMINATE, and cutting the notch lane may buy nothing'))
