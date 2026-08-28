import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
BUILD={'97':'STOCK','21':'V111','22':'V112','23':'V112'}
def curve(r,bands,sb):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    if any(k not in z.files for k in ('cs_rate','cs_tq','cc_lat','cs_v')): return None
    rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    kph=v*3.6; out={}
    for lo,hi in sb:
        m=(lat>0.5)&(med<1200)&(kph>=lo)&(kph<hi)
        if m.sum()<2500: out[(lo,hi)]=None; continue
        x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
        f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
        H=Pxy/np.maximum(Pxx,1e-30)
        out[(lo,hi)]=({b:np.mean(H[(f>=b[0])&(f<b[1])].real) for b in bands},int(m.sum()/FS))
    return out
# LOCKOUT-SAFE bins: stock's steer lockout is ~5 km/h (cal 0xC62EA = 320), so start at 6
SB=[(6,12),(12,20),(20,32),(32,50),(50,70),(70,90),(90,115)]
BANDS=[(6,9),(9,12)]
res={r:curve(r,BANDS,SB) for r in ('97','21','22','23')}
print("Re(Z) ABOVE THE LOCKOUT (>=6 km/h) -- removes the not-like-for-like 0-5 km/h contamination")
print("  build |" + " ".join("%8s"%("%d-%d"%s) for s in SB))
for band in BANDS:
    print("  --- %d-%d Hz ---"%band)
    for r in ('97','21','22','23'):
        o=res[r]
        if o is None: continue
        print("  r%-3s %-5s|%s"%(r,BUILD[r]," ".join(("%8.0f"%o[s][0][band]) if o[s] else "       -" for s in SB)))
    if res['97']:
        for r in ('21','22','23'):
            if not res[r]: continue
            cells=[]
            for s in SB:
                a=res['97'][s]; b=res[r][s]
                cells.append("%8.2f"%(b[0][band]/a[0][band]) if (a and b and abs(a[0][band])>1e-9) else "       -")
            print("    x vs stock  %-5s|%s"%(BUILD[r]," ".join(cells)))
print("\n  n (s) per bin:")
for r in ('97','21','22','23'):
    o=res[r]
    if o: print("  r%-3s |%s"%(r," ".join(("%8d"%o[s][1]) if o[s] else "       -" for s in SB)))
print("\n  gp-0x6b26 Y-row dose vs stock by speed knot: x3.00 @0 km/h, x3.00 @20, x8.14 @90")
print("  (X knots 0/1280/5760 ct at 64 ct per km/h = 0 / 20 / 90 km/h)")
