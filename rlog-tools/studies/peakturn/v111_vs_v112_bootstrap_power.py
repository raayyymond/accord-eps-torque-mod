import numpy as np
from scipy import signal
FS=100.0; NW=256
def wins(routes):
    out=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,lat,v,ang=[G(k) for k in ('cs_rate','cc_lat','cs_v','ang')]
        m=(lat>0.5)&(v>1.0)
        for a in range(0,len(rate)-NW,NW//2):
            sl=slice(a,a+NW)
            if m[sl].mean()<0.99: continue
            x=rate[sl]-np.mean(rate[sl])
            f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
            b=(f>=6)&(f<=9)
            out.append((np.sqrt(np.sum(P[b])*(f[1]-f[0])),np.mean(np.abs(ang[sl]))))
    return np.array(out)
A=wins(['21']); B=wins(['22','23'])
rng=np.random.default_rng(0)
print("IS THE V111-vs-V112 NULL DECISIVE, OR UNDERPOWERED?  bootstrap CIs on the p90 ratio\n")
print("   |ang|      n111  n112   p90 ratio    95% CI          verdict vs predicted 2-3x")
for lo,hi in ((0,5),(5,20),(20,60),(60,400)):
    a=A[(A[:,1]>=lo)&(A[:,1]<hi),0]; b=B[(B[:,1]>=lo)&(B[:,1]<hi),0]
    if len(a)<8 or len(b)<8: continue
    obs=np.percentile(b,90)/np.percentile(a,90)
    bs=[np.percentile(rng.choice(b,len(b)),90)/max(np.percentile(rng.choice(a,len(a)),90),1e-9) for _ in range(4000)]
    lo_ci,hi_ci=np.percentile(bs,[2.5,97.5])
    if hi_ci<2.0: v="EXCLUDES 2x -- prediction REFUTED"
    elif lo_ci>1.0: v="supports an increase"
    else: v="CI spans 1 and 2 -- UNDERPOWERED"
    print("   %3d-%3d    %4d  %4d   %6.2fx   [%.2f, %.2f]   %s"%(lo,hi,len(a),len(b),obs,lo_ci,hi_ci,v))
print("\n  (predicted ratio if the friction term drives the anti-damping: ~1.9x at 20 deg/s,")
print("   ~3.0x at 31.8+ deg/s, and ~1.0x at low rate)")
