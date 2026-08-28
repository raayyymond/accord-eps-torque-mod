import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
rng=np.random.default_rng(0)
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    return rate,tq,(lat>0.5)&(med<1200),v*3.6
def rez_of(rate,tq,mask,band=(6,9)):
    if mask.sum()<1200: return np.nan
    x=np.nan_to_num(np.where(mask,rate,0.)); y=np.nan_to_num(np.where(mask,tq,0.))
    f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
    _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
    H=Pxy/np.maximum(Pxx,1e-30)
    b=(f>=band[0])&(f<band[1])
    return np.mean(H[b].real)
rate,tq,base,kph=load('97')
print("IS THE LOW-SPEED PEAK AN ARTIFACT OF THIN STOCK DATA?")
print("Stock n: 20-32 km/h = 25 s, 90-115 km/h = 182 s.  Subsample the RICH bins to 25 s")
print("and see how much the Re(Z) estimate moves.\n")
for lo,hi in [(20,32),(32,50),(50,70),(70,90),(90,115)]:
    m=base&(kph>=lo)&(kph<hi)
    full=rez_of(rate,tq,m)
    n=int(m.sum())
    idx=np.where(m)[0]
    # contiguous 25 s blocks drawn from this bin
    target=int(25*FS)
    ests=[]
    if n>target+200:
        for _ in range(200):
            s=rng.integers(0,n-target)
            mm=np.zeros_like(m); mm[idx[s:s+target]]=True
            e=rez_of(rate,tq,mm)
            if np.isfinite(e): ests.append(e)
    if ests:
        print("  %3d-%3d km/h  n=%5.0f s  FULL %7.1f  |  25 s subsamples: p50 %7.1f  p5 %7.1f  p95 %7.1f  spread %.1fx"
              %(lo,hi,n/FS,full,np.percentile(ests,50),np.percentile(ests,5),np.percentile(ests,95),
                abs(np.percentile(ests,5)/max(abs(np.percentile(ests,95)),1e-9))))
    else:
        print("  %3d-%3d km/h  n=%5.0f s  FULL %7.1f  |  (too few for subsampling)"%(lo,hi,n/FS,full))
print("\n  => if a 25 s window can swing the estimate by several-fold, the 20-32 km/h stock")
print("     value (-7, from 25 s) cannot support a 6-8x ratio claim.")
