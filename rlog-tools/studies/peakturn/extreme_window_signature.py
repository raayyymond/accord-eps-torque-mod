import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0; NW=256
STOCK_MAX=3.748
rows=[]
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    t,rate,tq,lat,v,cmd,ang=[G(k) for k in ('t','cs_rate','cs_tq','cc_lat','cs_v','co_tqcan','ang')]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
    wire=G('ab_mt')*1.6; wt=G('ab_t1ab')
    sat=np.interp(t,wt,(wire>=150).astype(float))     # V112 relay saturation
    m=(lat>0.5)&(v>1.0)
    for a in range(0,len(rate)-NW,NW//2):
        sl=slice(a,a+NW)
        if m[sl].mean()<0.99: continue
        x=rate[sl]-np.mean(rate[sl])
        f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
        b=(f>=6)&(f<=9)
        rows.append((r,t[a],np.sqrt(np.sum(P[b])*(f[1]-f[0])),
                     np.mean(np.abs(cmd[sl])),np.median(med[sl]),np.mean(np.abs(ang[sl])),
                     v[sl].mean()*2.23694,np.mean(sat[sl]),np.std(rate[sl])))
R=np.array([[x[2],x[3],x[4],x[5],x[6],x[7],x[8]] for x in rows])
ex=R[:,0]>STOCK_MAX
print("WINDOWS BEYOND STOCK'S ENTIRE RANGE (6-9 Hz rms > %.3f, stock's all-time max)"%STOCK_MAX)
print("  V112 windows: %d of %d  (%.2f%%)   -- stock has ZERO by construction\n"%(ex.sum(),len(R),100*ex.mean()))
print("  the %d extreme windows:"%ex.sum())
print("   route      t      6-9Hz   |cmd|   grip   |ang|   mph   relay   rate sd")
for i in np.where(ex)[0][np.argsort(-R[ex,0])]:
    print("    %-4s %7.1f  %6.2f  %6.0f  %5.0f  %6.1f %5.1f  %.3f  %6.1f"
          %(rows[i][0],rows[i][1],R[i,0],R[i,1],R[i,2],R[i,3],R[i,4],R[i,5],R[i,6]))
print("\n  CONTRAST: extreme windows vs all other engaged windows")
oth=~ex
names=['|cmd|','grip','|ang|','mph','relay duty','rate sd']
print("   feature        extreme p50   other p50    ratio")
for j,nm in enumerate(names,start=1):
    a=np.median(R[ex,j]); b=np.median(R[oth,j])
    print("   %-13s %11.2f %11.2f  %7.2fx"%(nm,a,b,a/max(b,1e-9)))
