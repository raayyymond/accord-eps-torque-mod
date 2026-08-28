import numpy as np
from scipy import signal
FS=100.0; NW=128   # 1.28 s windows, 50% overlap
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    return dict(t=G('t'),ang=G('ang'),rate=G('cs_rate'),v=G('cs_v'),tq=G('cs_tq'),
                cmd=G('co_tqcan'),lat=G('cc_lat'),seg=G('seg'))
rows=[]
for r in ('21','22','23'):
    d=load(r); n=len(d['t'])
    for a in range(0,n-NW,NW//2):
        sl=slice(a,a+NW)
        if d['lat'][sl].mean()<0.99: continue
        x=d['tq'][sl]-np.mean(d['tq'][sl])
        f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
        b=(f>=6)&(f<=9); c=(f>=15)&(f<=30)
        rows.append((r,np.mean(np.abs(d['cmd'][sl])),np.mean(np.abs(d['ang'][sl])),
                     d['v'][sl].mean(),np.median(np.abs(d['tq'][sl])),
                     np.sqrt(np.sum(P[b])*(f[1]-f[0])),np.sqrt(np.sum(P[c])*(f[1]-f[0])),
                     np.mean(np.abs(d['cmd'][sl])>=4090),d['t'][a]))
R=np.array([[x[1],x[2],x[3],x[4],x[5],x[6],x[7]] for x in rows])
print("ALL ENGAGED 1.28 s WINDOWS, routes 21+22+23:  n=%d"%len(R))
print("\n6-9 Hz TORQUE RMS vs MEAN |cmd|  -- is there a JUMP at the rail, or a smooth ramp?")
print("  |cmd| bin        n    6-9Hz p50   p90     max   | 15-30Hz p50 | rail duty in bin")
edges=[0,256,512,1024,1536,2048,2560,3072,3584,4000,4097]
for i in range(len(edges)-1):
    s=(R[:,0]>=edges[i])&(R[:,0]<edges[i+1])
    if s.sum()<8: continue
    print("  %4d-%4d %8d   %8.0f %6.0f %7.0f  |  %8.0f    |   %.3f"
          %(edges[i],edges[i+1],s.sum(),np.percentile(R[s,4],50),np.percentile(R[s,4],90),
            R[s,4].max(),np.percentile(R[s,5],50),R[s,6].mean()))
print("\nSPLIT BY RAIL DUTY WITHIN THE WINDOW (the causal test):")
for lo,hi,lab in [(0.0,0.01,"never railed"),(0.01,0.5,"partly railed"),(0.5,1.01,"mostly railed")]:
    s=(R[:,6]>=lo)&(R[:,6]<hi)
    if s.sum()<5: continue
    print("   %-14s n=%5d   6-9Hz p50 %6.0f  p90 %6.0f  max %6.0f   |cmd| p50 %5.0f"
          %(lab,s.sum(),np.percentile(R[s,4],50),np.percentile(R[s,4],90),R[s,4].max(),
            np.percentile(R[s,0],50)))
print("\nMATCHED ON |cmd| 3000-4000 (high but NOT railed) vs RAILED >=4090:")
hi_not=(R[:,0]>=3000)&(R[:,0]<4000)&(R[:,6]<0.5)
rail=(R[:,6]>=0.5)
for lab,s in (("high, not railed",hi_not),("railed",rail)):
    if s.sum()>=5:
        print("   %-18s n=%4d  6-9Hz p50 %6.0f  p90 %6.0f  max %6.0f"
              %(lab,s.sum(),np.percentile(R[s,4],50),np.percentile(R[s,4],90),R[s,4].max()))
if hi_not.sum()>=5 and rail.sum()>=5:
    rng=np.random.default_rng(0)
    bs=[np.median(rng.choice(R[rail,4],rail.sum()))/max(np.median(rng.choice(R[hi_not,4],hi_not.sum())),1e-9)
        for _ in range(4000)]
    print("   RATIO railed/not = %.2fx   bootstrap 95%% CI [%.2f, %.2f]"
          %(np.median(R[rail,4])/max(np.median(R[hi_not,4]),1e-9),
            np.percentile(bs,2.5),np.percentile(bs,97.5)))
