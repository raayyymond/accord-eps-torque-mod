import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0; NW=256   # 2.56 s windows
def windows(routes,lab):
    out=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
        w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
        med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
        m=(lat>0.5)&(v>1.0)
        for a in range(0,len(rate)-NW,NW//2):
            sl=slice(a,a+NW)
            if m[sl].mean()<0.99: continue
            x=rate[sl]-np.mean(rate[sl])
            f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
            b=(f>=6)&(f<=9)
            out.append(np.sqrt(np.sum(P[b])*(f[1]-f[0])))
    return np.array(out),lab
A,_=windows(['97'],'STOCK'); B,_=windows(['22','23'],'V112')
print("6-9 Hz RATE rms in 2.56 s windows -- the TAIL is the right statistic for a RARE symptom")
print("  arm     n     p50     p90     p99   p99.9     max")
for arr,lab in ((A,'STOCK'),(B,'V112')):
    print("  %-6s %4d  %6.3f  %6.3f  %6.3f  %6.3f  %6.3f"
          %(lab,len(arr),*np.percentile(arr,[50,90,99,99.9]),arr.max()))
print("\n  RATIO V112/STOCK at each quantile:")
for q in (50,90,99,99.9):
    a=np.percentile(A,q); b=np.percentile(B,q)
    print("     p%-5s  %6.3f -> %6.3f   =  %5.2fx"%(q,a,b,b/a))
print("     max     %6.3f -> %6.3f   =  %5.2fx"%(A.max(),B.max(),B.max()/A.max()))
rng=np.random.default_rng(0)
bs=[np.percentile(rng.choice(B,len(B)),99)/np.percentile(rng.choice(A,len(A)),99) for _ in range(4000)]
print("\n  p99 ratio bootstrap 95%% CI: [%.2f, %.2f]"%(np.percentile(bs,2.5),np.percentile(bs,97.5)))
print("\n  fraction of windows above STOCK's own p99 (%.3f):"%np.percentile(A,99))
t=np.percentile(A,99)
print("     STOCK %.4f   V112 %.4f   =>  %.1fx more often"
      %(np.mean(A>t),np.mean(B>t),np.mean(B>t)/max(np.mean(A>t),1e-9)))
