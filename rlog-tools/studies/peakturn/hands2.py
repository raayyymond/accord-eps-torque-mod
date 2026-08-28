import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0; NW=128
rows=[]
for r in ('21','22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    t,ang,rate,v,tq,cmd,lat=[G(k) for k in ('t','ang','cs_rate','cs_v','cs_tq','co_tqcan','cc_lat')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    for a in range(0,len(t)-NW,NW//2):
        sl=slice(a,a+NW)
        if lat[sl].mean()<0.99: continue
        f,Pr=signal.welch(rate[sl]-np.mean(rate[sl]),FS,nperseg=NW,noverlap=NW//2)
        f,Pt=signal.welch(tq[sl]-np.mean(tq[sl]),FS,nperseg=NW,noverlap=NW//2)
        b=(f>=6)&(f<=9); df=f[1]-f[0]
        rows.append((r,t[a],np.mean(np.abs(cmd[sl])),np.median(med[sl]),v[sl].mean(),
                     np.sqrt(np.sum(Pr[b])*df), np.sqrt(np.sum(Pt[b])*df)))
R=np.array([[x[2],x[3],x[4],x[5],x[6]] for x in rows])
print("THE SAME CONTRAST, BUT THE OSCILLATION MEASURED ON **RATE** (different sensor from the split)")
print("  |cmd| band   low-torque (med<1200)        high-torque (med>=1200)      ratio")
print("               n   6-9Hz rate p50  p90  |   n   6-9Hz rate p50  p90")
for lo,hi in [(256,1024),(1024,2048),(2048,3584),(3584,4097)]:
    s=(R[:,0]>=lo)&(R[:,0]<hi); off=s&(R[:,1]<1200); on=s&(R[:,1]>=1200)
    if off.sum()>=5 and on.sum()>=5:
        print("  %4d-%4d  %4d %10.2f %6.2f  | %3d %10.2f %6.2f   %6.2fx"
              %(lo,hi,off.sum(),np.percentile(R[off,3],50),np.percentile(R[off,3],90),
                on.sum(),np.percentile(R[on,3],50),np.percentile(R[on,3],90),
                np.percentile(R[on,3],50)/max(np.percentile(R[off,3],50),1e-9)))
s=R[:,0]>=1024; off=s&(R[:,1]<1200); on=s&(R[:,1]>=1200)
rng=np.random.default_rng(0)
bs=[np.median(rng.choice(R[on,3],on.sum()))/max(np.median(rng.choice(R[off,3],off.sum())),1e-9) for _ in range(4000)]
print("\nPOOLED |cmd|>=1024, RATE-based:  low-tq n=%d p50 %.2f | high-tq n=%d p50 %.2f"
      %(off.sum(),np.percentile(R[off,3],50),on.sum(),np.percentile(R[on,3],50)))
print("   ratio %.2fx   bootstrap 95%% CI [%.2f, %.2f]"
      %(np.percentile(R[on,3],50)/max(np.percentile(R[off,3],50),1e-9),
        np.percentile(bs,2.5),np.percentile(bs,97.5)))
print("\n  torque-based ratio was 0.17x [0.14,0.22] -- compare.")
print("  correlation(6-9Hz RATE rms, 6-9Hz TORQUE rms) = %.3f"%np.corrcoef(R[:,3],R[:,4])[0,1])
print("\nAND THE OPERATOR'S EVENT ON THE RATE INSTRUMENT:")
for i,x in enumerate(rows):
    if x[0]=='23' and 444.0<=x[1]<=447.5:
        print("   t=%.1f  6-9Hz RATE %6.2f deg/s   6-9Hz TORQUE %6.0f   |cmd| %4.0f  med|tq| %5.0f"
              %(x[1],R[i,3],R[i,4],R[i,2] if False else x[2],x[3]))
print("   corpus 6-9Hz RATE: p50 %.2f  p90 %.2f  p99 %.2f  max %.2f"
      %(np.percentile(R[:,3],50),np.percentile(R[:,3],90),np.percentile(R[:,3],99),R[:,3].max()))
