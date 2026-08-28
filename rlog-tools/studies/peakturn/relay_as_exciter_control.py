import numpy as np
from scipy import signal
THR=1800/12.0
rows=[]
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    g=lambda k:np.asarray(z[k]).astype(float)
    t,rate,lat,cmd,v=[g(k) for k in ('t','cs_rate','cc_lat','co_tqcan','cs_v')]
    w=g('ab_mt')*1.6; wt=g('ab_t1ab')
    sat=np.interp(t,wt,(w>=THR).astype(float))
    raw=np.interp(t,wt,w)
    for a in range(0,len(t)-128,64):
        sl=slice(a,a+128)
        if lat[sl].mean()<0.99: continue
        x=rate[sl]-np.mean(rate[sl])
        f,P=signal.welch(x,100.0,nperseg=128,noverlap=64)
        b=(f>=6)&(f<=9); lofb=(f>=0.5)&(f<3)
        rows.append((np.mean(sat[sl]),
                     np.sqrt(np.sum(P[b])*(f[1]-f[0])),      # 6-9 Hz
                     np.std(rate[sl]),                        # broadband rate
                     np.sqrt(np.sum(P[lofb])*(f[1]-f[0])),    # 0.5-3 Hz (the slow content)
                     np.median(raw[sl]), np.mean(np.abs(cmd[sl]))))
R=np.array(rows)
print("CONTROL: does relay duty still predict 6-9 Hz AFTER matching on overall rate magnitude?")
print("The relay threshold is on |rate|, so high-rate windows have both -- this is the confound.\n")
print("  rate sd cell     relay duty <0.05        relay duty >=0.30       ratio")
print("   (deg/s)        n   6-9Hz p50  p90   |  n   6-9Hz p50  p90")
for lo,hi in [(2,5),(5,10),(10,20),(20,60)]:
    s=(R[:,2]>=lo)&(R[:,2]<hi)
    a=s&(R[:,0]<0.05); b=s&(R[:,0]>=0.30)
    if a.sum()>=6 and b.sum()>=6:
        print("   %2d-%2d       %4d %8.2f %6.2f  | %3d %8.2f %6.2f   %6.2fx"
              %(lo,hi,a.sum(),np.percentile(R[a,1],50),np.percentile(R[a,1],90),
                b.sum(),np.percentile(R[b,1],50),np.percentile(R[b,1],90),
                np.percentile(R[b,1],50)/max(np.percentile(R[a,1],50),1e-9)))
    else:
        print("   %2d-%2d       n_lo=%d n_hi=%d -- too few"%(lo,hi,a.sum(),b.sum()))
print("\nBETTER CONTROL -- the SHAPE ratio 6-9 Hz / 0.5-3 Hz (scale-free, cancels overall rate):")
sh=R[:,1]/np.maximum(R[:,3],1e-9)
print("  relay duty     n     6-9/0.5-3 ratio p50   p90")
for lo,hi in [(0,0.01),(0.01,0.1),(0.1,0.3),(0.3,0.6),(0.6,1.01)]:
    s=(R[:,0]>=lo)&(R[:,0]<hi)
    if s.sum()>=8:
        print("   %.2f-%.2f     %5d        %8.3f      %6.3f"
              %(lo,hi,s.sum(),np.percentile(sh[s],50),np.percentile(sh[s],90)))
print("  corr(relay duty, SHAPE ratio) = %.3f"%np.corrcoef(R[:,0],sh)[0,1])
a=R[:,0]<0.05; b=R[:,0]>=0.30
rng=np.random.default_rng(0)
bs=[np.median(rng.choice(sh[b],b.sum()))/max(np.median(rng.choice(sh[a],a.sum())),1e-9) for _ in range(4000)]
print("  SHAPE ratio, relay>=0.30 vs <0.05:  %.2fx   bootstrap 95%% CI [%.2f, %.2f]"
      %(np.median(sh[b])/np.median(sh[a]),np.percentile(bs,2.5),np.percentile(bs,97.5)))
