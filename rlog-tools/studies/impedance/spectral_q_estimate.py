import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
def spec(routes,lab):
    X=[];n=0
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
        w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
        med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
        m=(lat>0.5)&(med<1200)&(v>1.0)
        n+=m.sum()
        X.append(np.nan_to_num(np.where(m,rate,0.)))
    x=np.concatenate(X)
    f,P=signal.welch(x,FS,nperseg=4096,noverlap=3072)
    return f,P,n/FS,lab
A=spec(['97'],'STOCK'); B=spec(['22','23'],'V112')
print("CLOSED-LOOP Q FROM THE RATE AUTOSPECTRUM PEAK -- far more data than the n=1 ring-down")
print("  STOCK %.0f s engaged   |   V112 %.0f s engaged\n"%(A[2],B[2]))
for f,P,n,lab in (A,B):
    # local peak in 5-11 Hz above a smooth baseline (median-filtered spectrum)
    base=signal.medfilt(P,kernel_size=101)
    band=(f>=5)&(f<=11)
    ex=P[band]/np.maximum(base[band],1e-30)
    fb=f[band]
    i=int(np.argmax(ex))
    f0=fb[i]; pk=ex[i]
    # -3 dB width of the EXCESS over baseline
    half=pk/2.0
    lo=i
    while lo>0 and ex[lo]>half: lo-=1
    hi=i
    while hi<len(ex)-1 and ex[hi]>half: hi+=1
    bw=fb[hi]-fb[lo]
    Q=f0/bw if bw>0 else np.nan
    zeta=1/(2*Q) if Q and np.isfinite(Q) else np.nan
    print("  %-6s f0 %5.2f Hz   peak/baseline %5.2f   -3dB width %5.2f Hz   Q %6.2f   zeta %.4f"
          %(lab,f0,pk,bw,Q,zeta))
print("\n  the kit's n=1 ring-down: STOCK f0 7.42 Hz zeta 0.0275-0.0321 Q 15.6-18.2")
print("                           V102  f0 7.81 Hz zeta 0.059 -0.072  Q  7.0- 8.5")
print("\n  ABSOLUTE 6-9 Hz band power (deg/s rms) -- the amplitude claim, on this corpus:")
for f,P,n,lab in (A,B):
    b=(f>=6)&(f<=9); df=f[1]-f[0]
    print("    %-6s %8.4f deg/s rms"%(lab,np.sqrt(np.sum(P[b])*df)))
