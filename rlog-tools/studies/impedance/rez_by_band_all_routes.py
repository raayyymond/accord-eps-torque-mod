import numpy as np, glob, os
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal
FS=100.0
def rez(f):
    z=np.load(f,allow_pickle=True)
    need=('cs_v','cs_tq','cc_lat','cs_rate')
    if any(k not in z.files for k in need): return None
    G=lambda k:np.asarray(z[k]).astype(float)
    v,tq,lat,rate=[G(k) for k in need]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    ho=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]<1200
    out={}
    for nm,m in (('ENG',(lat>0.5)&ho&(v>1.0)), ('MAN',(lat<0.5)&(v>1.0))):
        if m.sum()<4000: out[nm]=None; continue
        x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
        fr,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
        _,Pyy=signal.welch(y,FS,nperseg=1024,noverlap=512)
        out[nm]=(fr,(Pxy/np.maximum(Pxx,1e-30)),np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30),m.sum())
    return out
BANDS=[(2,4),(4,6),(6,9),(9,12),(12,16),(16,20),(20,24),(24,28),(28,34),(34,42)]
print("Re(Z) = Re(  H1[rate -> column torque]  ).   Re(Z) < 0 = ANTI-DAMPED.")
print("%-5s %-4s | %s" % ("route","arm"," ".join("%8s"%("%d-%d"%b) for b in BANDS)))
f0s={}
for f in sorted(glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')):
    tag=os.path.basename(os.path.dirname(f))
    if os.path.basename(f)!=tag+'.npz': continue
    r=rez(f)
    if r is None: continue
    for arm in ('ENG','MAN'):
        if r[arm] is None: continue
        fr,H,C,n=r[arm]
        cells=[]
        for lo,hi in BANDS:
            b=(fr>=lo)&(fr<hi)
            cells.append("%8.0f"%np.mean(H[b].real))
        print("%-5s %-4s | %s" % (tag,arm," ".join(cells)))
        if arm=='ENG':
            # zero crossing of Re(Z) scanning upward from 10 Hz
            band=(fr>=10)&(fr<=40); ff=fr[band]; hh=H[band].real
            cross=[ff[i] + (ff[i+1]-ff[i])*(-hh[i])/(hh[i+1]-hh[i])
                   for i in range(len(hh)-1) if hh[i]<0<=hh[i+1]]
            f0s[tag]=cross[0] if cross else np.nan
print("\nf0 = FIRST upward Re(Z) zero crossing above 10 Hz, ENGAGED (the instability boundary):")
for k,v in sorted(f0s.items()):
    print("   %-5s  %s" % (k, ("%.2f Hz"%v) if np.isfinite(v) else "none in 10-40 Hz"))
vals=np.array([v for v in f0s.values() if np.isfinite(v)])
if len(vals): print("   corpus: n=%d  p50 %.2f  min %.2f  max %.2f Hz"%(len(vals),np.median(vals),vals.min(),vals.max()))
