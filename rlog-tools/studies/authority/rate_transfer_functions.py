import numpy as np, glob, os
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal
def sm(x,n=9):
    p=np.pad(x,(n//2,n-1-n//2),mode='edge'); return np.convolve(p,np.ones(n)/n,'valid')[:len(x)]
FS=100.0
def prep(f):
    z=np.load(f,allow_pickle=True)
    need=('cs_v','cs_tq','cc_lat','cs_rate','ang','ct_dcurv','co_tqcan')
    if any(k not in z.files for k in need): return None
    G=lambda k:np.asarray(z[k]).astype(float)
    v,tq,lat,rate,ang,dc,cmd=[G(k) for k in need]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    ho=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]<1200
    me=(lat>0.5)&ho&(v>1.0)
    fin=me&np.isfinite(dc)&np.isfinite(ang)
    if fin.sum()<5000: return None
    k=np.polyfit(dc[fin],ang[fin],1)
    return me,np.polyval(k,dc),ang,rate,cmd,tq,(lat>0.5)

print("=== HOW LONG DO HIGH-DEMAND EPISODES LAST? (route 21) ===")
r=prep('analysis-2020accord/_scratch/cache/r21/r21.npz')
me,des,ang,rate,cmd,tq,eng=r
dem=np.abs(np.gradient(sm(des),0.01))
for lo,hi in [(15,30),(30,60),(60,1e9)]:
    s=me&(dem>=lo)&(dem<hi)
    d=np.diff(np.concatenate(([0],s.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]; dur=(en-st)/FS
    if len(dur): print("   demand %3d-%-4s  %4d episodes  p50 %5.3f s  p90 %5.3f s  max %5.3f s  (5.05 Hz pole tau=0.0315 s)"
                       %(lo,("%d"%hi if hi<1e8 else "inf"),len(dur),np.median(dur),np.percentile(dur,90),dur.max()))

print("\n=== EMPIRICAL TRANSFER FUNCTIONS, pooled over routes (engaged, hands-off) ===")
print("    H1 = |Pxy|/Pxx , coherence gamma^2 ; Welch 1024-pt (10.24 s), 50% overlap\n")
acc={}
for f in sorted(glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')):
    tag=os.path.basename(os.path.dirname(f))
    if os.path.basename(f)!=tag+'.npz': continue
    r=prep(f)
    if r is None: continue
    me,des,ang,rate,cmd,tq,eng=r
    dr=np.gradient(sm(des),0.01)                 # demanded rate (signed)
    for nm,x,y,m in (("demandRate->rate",dr,rate,me),
                     ("LKAScmd->rate",cmd,rate,me),
                     ("drvTorque->rate",tq,rate,(~eng)&np.isfinite(rate))):
        xx=np.nan_to_num(np.where(m,x,0.0)); yy=np.nan_to_num(np.where(m,y,0.0))
        if m.sum()<5000: continue
        fr,Pxy=signal.csd(xx,yy,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(xx,FS,nperseg=1024,noverlap=512)
        _,Pyy=signal.welch(yy,FS,nperseg=1024,noverlap=512)
        H=np.abs(Pxy)/np.maximum(Pxx,1e-30); C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
        acc.setdefault(nm,[]).append((fr,H,C,m.sum()))
BANDS=[(0.1,0.3),(0.3,0.6),(0.6,1.0),(1.0,2.0),(2.0,3.5),(3.5,5.0),(5.0,8.0),(8.0,12.0),(12.0,20.0)]
for nm,lst in acc.items():
    fr=lst[0][0]; W=np.array([e[3] for e in lst],float); W/=W.sum()
    H=np.sum([w*e[1] for w,e in zip(W,lst)],axis=0); C=np.sum([w*e[2] for w,e in zip(W,lst)],axis=0)
    H0=None
    print("  %-18s  %d routes" % (nm,len(lst)))
    for lo,hi in BANDS:
        b=(fr>=lo)&(fr<hi)
        if not b.any(): continue
        h=np.mean(H[b]); c=np.mean(C[b])
        if H0 is None: H0=h
        print("     %5.1f-%5.1f Hz   |H| %9.4f   norm %6.3f (%+6.1f dB)   coh2 %.3f"
              %(lo,hi,h,h/H0,20*np.log10(max(h/H0,1e-9)),c))
