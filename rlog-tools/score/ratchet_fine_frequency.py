# -*- coding: utf-8 -*-
"""Is the ratchet frequency an exact SUBMULTIPLE of 100 Hz, or a mechanical resonance?

Every peak frequency I have quoted -- 7.81, 8.01, 8.20, 8.40, 8.59, 8.79 -- is an exact FFT
bin centre at 0.1953 Hz spacing (nperseg=512 at 100 Hz).  I have never resolved the true
frequency, only which bin it lands in.

That matters because 100/12 = 8.3333 Hz sits inside the measured range.  If the mode is at
an exact submultiple of the 100 Hz frame rate, it is a FIRMWARE CYCLE -- something running
every 12th frame -- and the lever is that structure, not the plant.  If it is at an
arbitrary frequency, it is mechanical and only its amplification can be reduced.

Method: take the LONGEST continuous engaged-creep runs available (r77 has the most windows
in the corpus) and Welch them at the longest nperseg the runs support, then interpolate the
peak parabolically.  Compare against the nearest submultiples 100/11, 100/12, 100/13.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 100.0
ROUTES = ['r77','r21','ra6','r1e','ra4','r7e','r7f','r95','r81','r82',
          'r78','r79','r85','r96','r9e','ra5','r22','r24','r97']

def runs(tag, minlen):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): return []
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(v),len(a)); lat,kmh,a=lat[:n],v[:n]*3.6,a[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    return [a[i:j] for i,j in zip(st,en) if (j-i)>=minlen and np.std(a[i:j])>0]

def peak_interp(f, P, lo, hi):
    """Parabolic interpolation of the peak -- resolves BELOW the bin spacing."""
    m=(f>=lo)&(f<=hi)
    idx=np.where(m)[0]
    k=idx[int(np.argmax(P[idx]))]
    if k<=0 or k>=len(P)-1: return f[k]
    a,b,c=np.log(P[k-1]+1e-30),np.log(P[k]+1e-30),np.log(P[k+1]+1e-30)
    d=0.5*(a-c)/(a-2*b+c) if (a-2*b+c)!=0 else 0.0
    return f[k]+d*(f[1]-f[0])

for NPS in (512, 1024):
    print('nperseg=%d  (%.1f s window, df=%.4f Hz)'%(NPS,NPS/FS,FS/NPS))
    ests=[]
    for tag in ROUTES:
        segs=runs(tag,NPS)
        if len(segs)<3: continue
        acc=[]
        for s in segs:
            f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2)
            acc.append(P)
        M=np.median(np.asarray(acc),0)
        pk=peak_interp(f,M,6.5,10.5)
        print('   %-6s %2d runs   peak %.4f Hz'%(tag,len(segs),pk))
        ests.append(pk)
    if ests:
        e=np.array(ests)
        print('   => %d routes, mean %.4f Hz, sd %.4f, range %.4f-%.4f'
              %(len(e),e.mean(),e.std(),e.min(),e.max()))
        for k in (11,12,13):
            sub=100.0/k
            print('      100/%d = %.4f Hz : %s (%.1f%% away, %.1f sd)'
                  %(k,sub,'MATCH' if abs(e.mean()-sub)<2*e.std()/max(len(e)**0.5,1) else 'no',
                    100*abs(e.mean()-sub)/sub, abs(e.mean()-sub)/(e.std()+1e-9)))
    print()
