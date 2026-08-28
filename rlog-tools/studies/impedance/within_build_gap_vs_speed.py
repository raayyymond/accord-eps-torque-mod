import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
print("WITHIN-BUILD DISCRIMINATOR -- no stock arm needed.")
print("Only ONE live cell is mode-gated: gp-0x6b26's Y row, x3.00 on engaged modes 26/27,")
print("byte-STOCK on mode 24 (manual).  Its speed LERP knots are 0 / 20 / 90 km/h with dose")
print("x3.00 / x3.00 / x8.14.  PREDICTION: if it drives the engaged-minus-manual Re(Z) gap,")
print("the gap must GROW with speed (flat to 20 km/h, then rising 2.7x by 90 km/h).\n")
SB=[(6,20),(20,35),(35,55),(55,80),(80,115)]
BANDS=[(6,9),(9,12),(12,16)]
for r in ('21','22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    kph=v*3.6
    def rz(m,band):
        if m.sum()<1500: return None
        x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
        f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
        H=Pxy/np.maximum(Pxx,1e-30); b=(f>=band[0])&(f<band[1])
        return np.mean(H[b].real)
    print("  r%s"%r)
    for band in BANDS:
        row=[]
        for lo,hi in SB:
            e=rz((lat>0.5)&(med<1200)&(kph>=lo)&(kph<hi),band)
            m=rz((lat<0.5)&(kph>=lo)&(kph<hi),band)
            row.append((e,m,None if (e is None or m is None) else e-m))
        print("    %2d-%2d Hz  ENG %s"%(band[0],band[1]," ".join(("%7.0f"%x[0]) if x[0] is not None else "      -" for x in row)))
        print("              MAN %s"%" ".join(("%7.0f"%x[1]) if x[1] is not None else "      -" for x in row))
        print("              GAP %s"%" ".join(("%7.0f"%x[2]) if x[2] is not None else "      -" for x in row))
    # n
    ne=[((lat>0.5)&(med<1200)&(kph>=lo)&(kph<hi)).sum()/FS for lo,hi in SB]
    nm=[((lat<0.5)&(kph>=lo)&(kph<hi)).sum()/FS for lo,hi in SB]
    print("        n eng %s"%" ".join("%7.0f"%x for x in ne))
    print("        n man %s"%" ".join("%7.0f"%x for x in nm))
    print("        bins  %s"%" ".join("%7s"%("%d-%d"%s) for s in SB))
    print()
