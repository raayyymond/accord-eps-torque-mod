import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    d=dict(t=G('t'),ang=G('ang'),rate=G('cs_rate'),v=G('cs_v'),tq=G('cs_tq'),
           cmd=G('co_tqcan'),lat=G('cc_lat'),seg=G('seg'))
    w=51;pad=np.pad(np.abs(d['tq']),(w//2,w-1-w//2),mode='edge')
    d['ho']=np.median(sliding_window_view(pad,w),axis=-1)[:len(d['tq'])]<1200
    return d
D={r:load(r) for r in ('21','22','23')}

print("=== 1. THE OPERATOR'S EVENT: is the driver DRIVING the 7.42 Hz, or REACTING to it? ===")
d=D['23']; w=(d['t']>=445.4)&(d['t']<=448.4)
tq=d['tq'][w]; rate=d['rate'][w]; ang=d['ang'][w]
print("   hands-off mask during the event: %.3f (rolling-median |tq| < 1200)"%d['ho'][w].mean())
print("   |tq| p50 %.0f  p95 %.0f  max %.0f"%(np.percentile(np.abs(tq),50),
      np.percentile(np.abs(tq),95),np.abs(tq).max()))
zc=np.sum(np.diff(np.sign(tq))!=0)/ (len(tq)/FS)
print("   torque SIGN CROSSINGS: %.1f per second => %.2f Hz fundamental"%(zc,zc/2))
print("   ** a human cannot apply +-2400 ct alternating at 7.4 Hz -- this is the PLANT/LOOP,")
print("      and the driver's grip is what it is reacting against. **")

print("\n=== 2. DOES THE MODE FREQUENCY MOVE WITH SPEED? (a resonance does) ===")
rows=[]
for r in ('21','22','23'):
    d=D[r]; m=(d['lat']>0.5)&(np.abs(d['cmd'])>=4090)
    dd=np.diff(np.concatenate(([0],m.view(np.int8),[0])))
    for a,b in zip(np.where(dd==1)[0],np.where(dd==-1)[0]):
        if (b-a)/FS<0.4: continue
        sl=slice(max(a-25,0),min(b+25,len(d['t'])))
        x=d['tq'][sl]-np.mean(d['tq'][sl])
        if len(x)<128: continue
        f,P=signal.welch(x,FS,nperseg=min(256,len(x)//2*2))
        bb=(f>=5)&(f<=12)
        rows.append((d['v'][a:b].mean(),f[bb][np.argmax(P[bb])],
                     np.sqrt(np.sum(P[bb])*(f[1]-f[0])),r))
A=np.array([[x[0],x[1],x[2]] for x in rows])
ok=np.isfinite(A[:,1])
print("   n=%d episodes   corr(speed, peak Hz) = %.3f"%(ok.sum(),np.corrcoef(A[ok,0],A[ok,1])[0,1]))
for lo,hi in [(0,3),(3,6),(6,9),(9,20)]:
    s=ok&(A[:,0]>=lo)&(A[:,0]<hi)
    if s.sum()>=3:
        print("     v %2d-%2d m/s  n=%2d  peak Hz p50 %5.2f   6-9Hz rms p50 %5.0f"
              %(lo,hi,s.sum(),np.median(A[s,1]),np.median(A[s,2])))

print("\n=== 3. V111 (r21) vs V112 (r22,r23): is the rail-oscillation better? ===")
for r in ('21','22','23'):
    d=D[r]; eng=d['lat']>0.5
    m=eng&(np.abs(d['cmd'])>=4090)
    dd=np.diff(np.concatenate(([0],m.view(np.int8),[0])))
    ep=[(b-a)/FS for a,b in zip(np.where(dd==1)[0],np.where(dd==-1)[0]) if (b-a)/FS>=0.4]
    eng_s=eng.sum()/FS
    rr=[x[2] for x in rows if x[3]==r and np.isfinite(x[2])]
    print("   r%-3s  engaged %6.1f s  rail duty %.4f  episodes>=0.4s %2d (%.2f per engaged min)"
          "  6-9Hz rms p50 %5.0f p90 %5.0f"
          %(r,eng_s,np.mean(np.abs(d['cmd'][eng])>=4090),len(ep),len(ep)/(eng_s/60),
            np.median(rr) if rr else -1,np.percentile(rr,90) if rr else -1))

print("\n=== 4. GRIND #1 HUNT: 5-10 mph, engaged, strong command -- band energy ===")
for r in ('21','22','23'):
    d=D[r]; mph=d['v']*2.23694
    m=(d['lat']>0.5)&(mph>=5)&(mph<10)
    strong=m&(np.abs(d['cmd'])>=2048)
    if strong.sum()<200: print("   r%s too few"%r); continue
    idx=np.where(strong)[0]
    segs=np.split(idx,np.where(np.diff(idx)>10)[0]+1)
    out=[]
    for s in segs:
        if len(s)<128: continue
        x=d['tq'][s]-np.mean(d['tq'][s])
        f,P=signal.welch(x,FS,nperseg=min(256,len(x)//2*2))
        b1=(f>=6)&(f<=9); b2=(f>=15)&(f<=30)
        out.append((np.sqrt(np.sum(P[b1])*(f[1]-f[0])),np.sqrt(np.sum(P[b2])*(f[1]-f[0])),
                    d['t'][s[0]],len(s)/FS))
    if not out: print("   r%s no windows"%r); continue
    O=np.array([[o[0],o[1]] for o in out])
    print("   r%-3s  n=%2d windows  6-9Hz rms p50 %5.0f p90 %5.0f max %5.0f | 15-30Hz p50 %4.0f p90 %4.0f"
          %(r,len(out),np.percentile(O[:,0],50),np.percentile(O[:,0],90),O[:,0].max(),
            np.percentile(O[:,1],50),np.percentile(O[:,1],90)))
    worst=sorted(out,key=lambda o:-o[0])[:3]
    for o in worst:
        print("        worst: t=%7.1f s  dur %.2f s  6-9Hz %5.0f  15-30Hz %4.0f"%(o[2],o[3],o[0],o[1]))
