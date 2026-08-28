import numpy as np
from scipy import signal
FS=100.0
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    return dict(t=G('t'),ang=G('ang'),rate=G('cs_rate'),v=G('cs_v'),tq=G('cs_tq'),
                cmd=G('co_tqcan'),lat=G('cc_lat'),seg=G('seg'))
def band_rms(x,lo,hi):
    if len(x)<64: return np.nan,np.nan
    x=x-np.mean(x); f,P=signal.welch(x,FS,nperseg=min(256,len(x)//2*2),noverlap=None)
    b=(f>=lo)&(f<hi)
    if not b.any(): return np.nan,np.nan
    return np.sqrt(np.sum(P[b])*(f[1]-f[0])), f[b][np.argmax(P[b])]

print("EVERY SUSTAINED COMMAND-RAIL EPISODE (|cmd|>=4090, engaged, >=0.4 s)")
print("route seg   t_start   dur   |ang|   v     rate rms  |  6-9Hz tq rms  peak Hz  |  12-30Hz")
allep=[]
for r in ('21','22','23'):
    try: d=load(r)
    except Exception as e: print(' ',r,'missing',e); continue
    m=(d['lat']>0.5)&(np.abs(d['cmd'])>=4090)
    dd=np.diff(np.concatenate(([0],m.view(np.int8),[0])))
    st,en=np.where(dd==1)[0],np.where(dd==-1)[0]
    for a,b in zip(st,en):
        dur=(b-a)/FS
        if dur<0.4: continue
        sl=slice(max(a-25,0),min(b+25,len(d['t'])))
        rms69,pk69=band_rms(d['tq'][sl],6,9)
        rms1230,_=band_rms(d['tq'][sl],12,30)
        allep.append((r,dur,rms69,pk69,np.abs(d['ang'][a:b]).mean(),d['v'][a:b].mean()))
        print("  %-3s  %2d  %8.2f  %5.2f  %6.1f %5.1f   %7.2f   |  %9.0f   %5.2f   |  %7.0f"
              %(r,int(d['seg'][a]),d['t'][a],dur,np.abs(d['ang'][a:b]).mean(),
                d['v'][a:b].mean(),np.std(d['rate'][a:b]),rms69,pk69,rms1230))
print("\n  %d rail episodes >=0.4 s across routes 21/22/23" % len(allep))
if allep:
    A=np.array([[e[1],e[2],e[4],e[5]] for e in allep],float)
    ok=np.isfinite(A[:,1])
    print("  duration p50 %.2f s  max %.2f s" % (np.median(A[:,0]),A[:,0].max()))
    print("  6-9 Hz torque rms during rail: p50 %.0f  p90 %.0f  max %.0f counts"
          %(np.percentile(A[ok,1],50),np.percentile(A[ok,1],90),A[ok,1].max()))
    print("  correlation(duration, 6-9Hz rms) = %.3f" % np.corrcoef(A[ok,0],A[ok,1])[0,1])
    print("  correlation(|ang|,    6-9Hz rms) = %.3f" % np.corrcoef(A[ok,2],A[ok,1])[0,1])
    print("  correlation(speed,    6-9Hz rms) = %.3f" % np.corrcoef(A[ok,3],A[ok,1])[0,1])
