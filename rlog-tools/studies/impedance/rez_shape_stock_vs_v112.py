import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
def spec(routes,lab):
    X=[];Y=[];n=0
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
        w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
        med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
        m=(lat>0.5)&(med<1200)&(v>1.0)
        n+=m.sum()
        X.append(np.nan_to_num(np.where(m,rate,0.))); Y.append(np.nan_to_num(np.where(m,tq,0.)))
    x=np.concatenate(X);y=np.concatenate(Y)
    f,Pxy=signal.csd(x,y,FS,nperseg=2048,noverlap=1536)
    _,Pxx=signal.welch(x,FS,nperseg=2048,noverlap=1536)
    _,Pyy=signal.welch(y,FS,nperseg=2048,noverlap=1536)
    return f,(Pxy/np.maximum(Pxx,1e-30)).real,np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30),n/FS,lab
A=spec(['97'],'STOCK'); B=spec(['22','23'],'V112')
print("IS THE 8-12 Hz ANTI-DAMPED FEATURE PRESENT ON STOCK?  (0.5 Hz bins)")
print("  STOCK engaged %.0f s   |   V112 engaged %.0f s\n"%(A[3],B[3]))
print("    Hz   |   STOCK Re(Z)  coh2  |   V112 Re(Z)  coh2  |  V112/STOCK")
edges=np.arange(3,26.01,1.0)
for i in range(len(edges)-1):
    lo,hi=edges[i],edges[i+1]
    ba=(A[0]>=lo)&(A[0]<hi); bb=(B[0]>=lo)&(B[0]<hi)
    ra=np.mean(A[1][ba]); ca=np.mean(A[2][ba])
    rb=np.mean(B[1][bb]); cb=np.mean(B[2][bb])
    rat="%8.2f"%(rb/ra) if abs(ra)>0.5 else "       -"
    print("  %4.1f-%4.1f |  %9.1f  %.3f  |  %9.1f  %.3f  | %s"%(lo,hi,ra,ca,rb,cb,rat))
for nm,S in (('STOCK',A),('V112',B)):
    f,H,C,n,lab=S
    sel=(f>=3)&(f<=30)
    ff=f[sel];hh=H[sel]
    print("\n  %s: most anti-damped %.1f Hz at %.1f  |  zero crossing above 10 Hz: "%(nm,ff[np.argmin(hh)],hh.min()),end="")
    z=[ff[i]+ (ff[i+1]-ff[i])*(-hh[i])/(hh[i+1]-hh[i]) for i in range(len(hh)-1) if ff[i]>10 and hh[i]<0<=hh[i+1]]
    print("%.2f Hz"%z[0] if z else "none")
