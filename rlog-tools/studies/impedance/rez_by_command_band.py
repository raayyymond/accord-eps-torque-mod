import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
print("WHERE DOES THE ENGAGED Re(Z) DEFICIT COME FROM?")
print("gp-0x6b26 is ALREADY 3x bigger engaged than manual (mode 26/27 Y = -29490 vs mode 24 -9830),")
print("yet ENGAGED is anti-damped and MANUAL is damped.  So the deficit is NOT this lane.\n")
print("Re(Z) by band, engaged vs manual, and the SPLIT BY COMMAND MAGNITUDE within engaged:")
BANDS=[(2,4),(4,6),(6,9),(9,12),(12,16),(16,20),(20,24)]
for r in ('21','22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    rate,tq,lat,v,cmd=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v','co_tqcan')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    def rez(m):
        if m.sum()<4000: return None
        x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
        f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
        H=Pxy/np.maximum(Pxx,1e-30)
        return f,H
    mov=v>1.0; ho=med<1200
    arms=[("MANUAL      ",(~(lat>0.5))&mov),
          ("ENG cmd<512 ",(lat>0.5)&mov&ho&(np.abs(cmd)<512)),
          ("ENG cmd>=512",(lat>0.5)&mov&ho&(np.abs(cmd)>=512))]
    print("  r%s"%r)
    for lab,m in arms:
        out=rez(m)
        if out is None: print("    %s  (too few: %d)"%(lab,m.sum())); continue
        f,H=out
        print("    %s n=%6d | %s"%(lab,m.sum(),
              " ".join("%4d-%-2d %6.0f"%(a,b,np.mean(H[(f>=a)&(f<b)].real)) for a,b in BANDS)))
