import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
print("IS Re(Z) AMPLITUDE-DEPENDENT?  (a describing-function effect of the Coulomb relay)")
print("If yes, more gain -> more amplitude -> more anti-damping, WITHOUT any linear loop change.")
print("That reconciles 'the gain scales excitation' with Re(Z) tracking the gain.\n")
def analyse(routes,lab):
    seg=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
        w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
        med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
        m=(lat>0.5)&(med<1200)&(v>1.0)
        # 10.24 s blocks, classified by their own band-limited rate amplitude
        N=1024
        for a in range(0,len(rate)-N,N//2):
            sl=slice(a,a+N)
            if m[sl].mean()<0.99: continue
            x=rate[sl]-np.mean(rate[sl]); y=tq[sl]-np.mean(tq[sl])
            f,P=signal.welch(x,FS,nperseg=256,noverlap=128)
            b=(f>=6)&(f<=12)
            amp=np.sqrt(np.sum(P[b])*(f[1]-f[0]))
            seg.append((amp,x,y))
    if len(seg)<40: print("  %s: too few blocks (%d)"%(lab,len(seg))); return
    amps=np.array([s[0] for s in seg])
    qs=np.percentile(amps,[0,25,50,75,100])
    print("  %s  n=%d blocks   6-12 Hz rate amplitude quartiles: %s"
          %(lab,len(seg),np.round(qs,2)))
    print("    amp band        n     Re(Z) 7-9 Hz   Re(Z) 9-12 Hz   coh2")
    for i in range(4):
        lo,hi=qs[i],qs[i+1]
        grp=[s for s in seg if lo<=s[0]<=hi]
        if len(grp)<10: continue
        X=np.concatenate([g[1] for g in grp]); Y=np.concatenate([g[2] for g in grp])
        f,Pxy=signal.csd(X,Y,FS,nperseg=1024,noverlap=768)
        _,Pxx=signal.welch(X,FS,nperseg=1024,noverlap=768)
        _,Pyy=signal.welch(Y,FS,nperseg=1024,noverlap=768)
        H=(Pxy/np.maximum(Pxx,1e-30)).real; C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
        b1=(f>=7)&(f<9); b2=(f>=9)&(f<12)
        print("    Q%d %5.2f-%5.2f %5d      %8.1f        %8.1f      %.3f"
              %(i+1,lo,hi,len(grp),np.mean(H[b1]),np.mean(H[b2]),np.mean(C[b1])))
analyse(['22','23'],'V112')
analyse(['97'],'STOCK')
