import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
def prep(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    d={k:G(k) for k in ('t','ang','cs_rate','cs_v','cs_tq','co_tqcan','cc_lat','ct_dcurv')}
    w=51;pad=np.pad(np.abs(d['cs_tq']),(w//2,w-1-w//2),mode='edge')
    d['med']=np.median(sliding_window_view(pad,w),axis=-1)[:len(d['cs_tq'])]
    return d
BUILD={'21':'V111','22':'V112','23':'V112','1e':'V107','ra6':'V106'}
print("COMMAND AUTHORITY: how much wheel motion does one count of LKAS command buy?")
print("  H1[cmd -> rate], engaged + low-torque + moving.  Higher = the command outpaces the plant.\n")
print("  route build |  0.1-0.5   0.5-1.0    1-2      2-3.5    3.5-5 Hz  | coh2 @1-2Hz")
for r in ('21','22','23'):
    d=prep(r)
    m=(d['cc_lat']>0.5)&(d['med']<1200)&(d['cs_v']>1.0)
    x=np.nan_to_num(np.where(m,d['co_tqcan'],0.)); y=np.nan_to_num(np.where(m,d['cs_rate'],0.))
    f,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
    _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
    _,Pyy=signal.welch(y,FS,nperseg=1024,noverlap=512)
    H=np.abs(Pxy)/np.maximum(Pxx,1e-30); C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
    cells=[]
    for lo,hi in [(0.1,0.5),(0.5,1.0),(1.0,2.0),(2.0,3.5),(3.5,5.0)]:
        b=(f>=lo)&(f<hi); cells.append(np.mean(H[b]))
    b=(f>=1)&(f<2)
    print("  r%-4s %-5s | %s | %.3f   (n=%d s engaged)"
          %(r,BUILD[r]," ".join("%8.5f"%c for c in cells),np.mean(C[b]),int(m.sum()/FS)))

print("\nDELIVERED RATE PER 1000 COUNTS OF COMMAND, by command band (engaged, low-torque, moving)")
print("  route build |  cmd 512-1024  1024-2048  2048-3584  3584-4097   (deg/s per 1000 ct)")
for r in ('21','22','23'):
    d=prep(r)
    m=(d['cc_lat']>0.5)&(d['med']<1200)&(d['cs_v']>1.0)
    c=np.abs(d['co_tqcan'])[m]; rt=np.abs(d['cs_rate'])[m]
    cells=[]
    for lo,hi in [(512,1024),(1024,2048),(2048,3584),(3584,4097)]:
        s=(c>=lo)&(c<hi)
        cells.append(1000*np.median(rt[s])/np.median(c[s]) if s.sum()>50 else np.nan)
    print("  r%-4s %-5s | %s"%(r,BUILD[r]," ".join("%11.2f"%x for x in cells)))

print("\nTRACKING vs openpilot's OWN DEMAND (the number that answers 'is 6x delivering')")
def sm(x,n=9):
    p=np.pad(x,(n//2,n-1-n//2),mode='edge'); return np.convolve(p,np.ones(n)/n,'valid')[:len(x)]
print("  route build | ach/dem at demand 5-15  15-30  30-60  60+ Hz-free deg/s bands")
for r in ('21','22','23'):
    d=prep(r)
    m=(d['cc_lat']>0.5)&(d['med']<1200)&(d['cs_v']>1.0)
    fin=m&np.isfinite(d['ct_dcurv'])&np.isfinite(d['ang'])
    k=np.polyfit(d['ct_dcurv'][fin],d['ang'][fin],1)
    dem=np.abs(np.gradient(sm(np.polyval(k,d['ct_dcurv'])),0.01)); ach=np.abs(d['cs_rate'])
    cells=[]
    for lo,hi in [(5,15),(15,30),(30,60),(60,1e9)]:
        s=m&(dem>=lo)&(dem<hi)&np.isfinite(ach)
        cells.append(np.median(ach[s])/max(np.median(dem[s]),1e-9) if s.sum()>100 else np.nan)
    print("  r%-4s %-5s | %s"%(r,BUILD[r]," ".join("%20.3f"%x if i==0 else "%6.3f"%x for i,x in enumerate(cells))))
