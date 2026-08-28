import numpy as np, glob, os
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
BUILD={'97':('STOCK',0),'7e':('V96',0),'7f':('V96',0),'85':('V100',0),'95':('V101',0),
       '96':('V102',0),'9e':('V103',1),'a4':('V104',1),'a5':('V105',1),'a6':('V106',1),
       '1e':('V107',1),'21':('V111',1),'22':('V112',1),'23':('V112',1),
       '77':('V90',0),'78':('V91',0),'79':('V92',0),'81':('?',0),'82':('?',0)}
def rez(r):
    p='analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r)
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate','cs_tq','cc_lat','cs_v')): return None
    G=lambda k:np.asarray(z[k]).astype(float)
    rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    m=(lat>0.5)&(med<1200)&(v>1.0)
    if m.sum()<8000: return None
    x=np.nan_to_num(np.where(m,rate,0.)); y=np.nan_to_num(np.where(m,tq,0.))
    f,Pxy=signal.csd(x,y,FS,nperseg=2048,noverlap=1536)
    _,Pxx=signal.welch(x,FS,nperseg=2048,noverlap=1536)
    _,Pyy=signal.welch(y,FS,nperseg=2048,noverlap=1536)
    H=(Pxy/np.maximum(Pxx,1e-30)).real; C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
    out={}
    for lab,(lo,hi) in (('7-9',(7,9)),('9-12',(9,12)),('12-16',(12,16)),('16-19',(16,19))):
        b=(f>=lo)&(f<hi); out[lab]=(np.mean(H[b]),np.mean(C[b]))
    return out,m.sum()/FS
print("NATURAL EXPERIMENT: the biquad is armed from V103 onward (0xC649B 0->1 + code patch).")
print("If the 7-9 Hz anti-damped feature IS the biquad, it must appear at V103.\n")
print("  route build  biq |    7-9 Hz     9-12 Hz    12-16 Hz    16-19 Hz  | eng s")
rows=[]
for r in ['97','7e','7f','85','95','96','77','78','79','9e','a4','a5','a6','1e','21','22','23']:
    o=rez(r)
    if o is None: continue
    d,n=o; b,arm=BUILD.get(r,('?',0))
    rows.append((arm,d['7-9'][0],r,b,n))
    print("  r%-4s %-5s  %d  | %7.1f(%.2f) %7.1f(%.2f) %7.1f(%.2f) %7.1f(%.2f) | %5.0f"
          %(r,b,arm,d['7-9'][0],d['7-9'][1],d['9-12'][0],d['9-12'][1],
            d['12-16'][0],d['12-16'][1],d['16-19'][0],d['16-19'][1],n))
off=[x[1] for x in rows if x[0]==0]; on=[x[1] for x in rows if x[0]==1]
print("\n  7-9 Hz Re(Z):")
print("   biquad OFF (n=%d routes): %s   median %.1f"%(len(off),[round(v) for v in off],np.median(off)))
print("   biquad ON  (n=%d routes): %s   median %.1f"%(len(on),[round(v) for v in on],np.median(on)))
if off and on:
    from itertools import product
    # Mann-Whitney style: fraction of ON worse than OFF
    worse=sum(1 for a,b in product(on,off) if a<b)/(len(on)*len(off))
    print("   P(a biquad-ON route is more anti-damped than a biquad-OFF route) = %.3f"%worse)
    print("   difference of medians: %.1f"%(np.median(on)-np.median(off)))
