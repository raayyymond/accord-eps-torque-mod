import numpy as np, glob, os
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal
def sm(x,n=9):
    p=np.pad(x,(n//2,n-1-n//2),mode='edge'); return np.convolve(p,np.ones(n)/n,'valid')[:len(x)]
FS=100.0; acc={}
for f in sorted(glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')):
    tag=os.path.basename(os.path.dirname(f))
    if os.path.basename(f)!=tag+'.npz': continue
    z=np.load(f,allow_pickle=True)
    need=('cs_v','cs_tq','cc_lat','cs_rate','ang','ct_dcurv','co_tqcan')
    if any(k not in z.files for k in need): continue
    G=lambda k:np.asarray(z[k]).astype(float)
    v,tq,lat,rate,ang,dc,cmd=[G(k) for k in need]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    ho=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]<1200
    me=(lat>0.5)&ho&(v>1.0); fin=me&np.isfinite(dc)&np.isfinite(ang)
    if fin.sum()<5000: continue
    k=np.polyfit(dc[fin],ang[fin],1); dr=np.gradient(sm(np.polyval(k,dc)),0.01)
    for nm,x,y in (("demandRate->CMD",dr,cmd),("demandRate->rate",dr,rate)):
        xx=np.nan_to_num(np.where(me,x,0.)); yy=np.nan_to_num(np.where(me,y,0.))
        fr,Pxy=signal.csd(xx,yy,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(xx,FS,nperseg=1024,noverlap=512)
        _,Pyy=signal.welch(yy,FS,nperseg=1024,noverlap=512)
        acc.setdefault(nm,[]).append((fr,np.abs(Pxy)/np.maximum(Pxx,1e-30),
                                      np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30),me.sum()))
    # command slew, engaged only
    d=np.abs(np.diff(cmd))[me[1:]]
    acc.setdefault("slew",[]).append((d,me.sum()))
BANDS=[(0.1,0.3),(0.3,0.6),(0.6,1.0),(1.0,2.0),(2.0,3.5),(3.5,5.0),(5.0,8.0),(8.0,12.0)]
for nm in ("demandRate->CMD","demandRate->rate"):
    lst=acc[nm]; fr=lst[0][0]; W=np.array([e[3] for e in lst],float); W/=W.sum()
    H=np.sum([w*e[1] for w,e in zip(W,lst)],axis=0); C=np.sum([w*e[2] for w,e in zip(W,lst)],axis=0)
    H0=None; print("  %-18s %d routes"%(nm,len(lst)))
    for lo,hi in BANDS:
        b=(fr>=lo)&(fr<hi); h=np.mean(H[b]); c=np.mean(C[b])
        if H0 is None: H0=h
        print("     %5.1f-%5.1f Hz  norm %6.3f (%+6.1f dB)  coh2 %.3f"%(lo,hi,h/H0,20*np.log10(max(h/H0,1e-9)),c))
d=np.concatenate([e[0] for e in acc["slew"]])
LIM=0.03*4096
print("\n=== openpilot COMMAND SLEW, engaged (limiter = STEER_DELTA 3.0/s x DT 0.01 x 4096 = %.2f ct/frame)"%LIM)
print("   p50 %.1f  p90 %.1f  p99 %.1f  max %.1f ct/frame"%(*np.percentile(d,[50,90,99]),d.max()))
for th in (0.5,0.9,0.99,1.0):
    print("   duty(|dcmd| >= %5.1f = %.0f%% of the limiter) = %.4f"%(th*LIM,100*th,np.mean(d>=th*LIM)))
print("\n   ** at the limiter, reaching full scale takes %.2f s; the median high-demand"%(4096/ (LIM*FS)))
print("      episode lasts 0.030 s, in which the command can move at most %.0f counts = %.1f%% of scale **"
      %(3*LIM, 100*3*LIM/4096))
