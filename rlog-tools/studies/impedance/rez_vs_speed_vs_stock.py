import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
BUILD={'97':'STOCK','21':'V111','22':'V112','23':'V112','ra6':'V106','a6':'V106'}
def rez_bins(r,bands,speed_bins):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    need=('cs_rate','cs_tq','cc_lat','cs_v')
    if any(k not in z.files for k in need): return None
    rate,tq,lat,v=[G(k) for k in need]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    kph=v*3.6
    out={}
    for lo,hi in speed_bins:
        m=(lat>0.5)&(med<1200)&(kph>=lo)&(kph<hi)
        if m.sum()<3000: out[(lo,hi)]=None; continue
        x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
        f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
        _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
        H=Pxy/np.maximum(Pxx,1e-30)
        out[(lo,hi)]=({b:np.mean(H[(f>=b[0])&(f<b[1])].real) for b in bands},int(m.sum()/FS))
    return out
BANDS=[(6,9),(9,12),(12,16),(22,26)]
SB=[(0,15),(15,29),(29,50),(50,70),(70,86),(86,115)]
print("Re(Z) BY SPEED AND BUILD -- where does our multiplication of Honda's anti-damping live?")
print("(engaged, low-torque; negative = anti-damped; units per deg/s)\n")
res={}
for r in ('97','21','22','23'):
    o=rez_bins(r,BANDS,SB)
    if o is None: print("  r%s missing fields"%r); continue
    res[r]=o
    print("  r%-3s %-5s | %s"%(r,BUILD.get(r,'?'),
        "  ".join("%d-%d km/h"%(a,b) for a,b in SB)))
    for band in BANDS:
        cells=[]
        for sb in SB:
            cells.append("%9.0f"%o[sb][0][band] if o[sb] else "        -")
        print("        %2d-%2d Hz |%s"%(band[0],band[1]," ".join(cells)))
    print("        n (s)    |%s"%" ".join(("%9d"%o[sb][1]) if o[sb] else "        -" for sb in SB))
    print()
if '97' in res:
    print("MULTIPLICATION vs STOCK (mod / stock), 6-9 Hz -- only where BOTH arms have data:")
    for r in ('21','22','23'):
        if r not in res: continue
        cells=[]
        for sb in SB:
            a=res['97'][sb]; b=res[r][sb]
            if a and b and abs(a[0][(6,9)])>1e-9:
                cells.append("%9.2f"%(b[0][(6,9)]/a[0][(6,9)]))
            else: cells.append("        -")
        print("   r%-3s %-5s |%s"%(r,BUILD[r]," ".join(cells)))
    print("\n   the kit's published stock-vs-6x table: 2.60x @29-58, 2.39x @58-86, 0.69x @86-115 km/h")
