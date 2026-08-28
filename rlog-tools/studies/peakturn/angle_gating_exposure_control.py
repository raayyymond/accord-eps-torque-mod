import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0; NW=256
def wins(routes):
    out=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v,cmd,ang=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v','co_tqcan','ang')]
        m=(lat>0.5)&(v>1.0)
        for a in range(0,len(rate)-NW,NW//2):
            sl=slice(a,a+NW)
            if m[sl].mean()<0.99: continue
            x=rate[sl]-np.mean(rate[sl])
            f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
            b=(f>=6)&(f<=9)
            out.append((np.sqrt(np.sum(P[b])*(f[1]-f[0])),np.mean(np.abs(ang[sl])),
                        np.mean(np.abs(cmd[sl])),v[sl].mean()*2.23694))
    return np.array(out)
A=wins(['97']); B=wins(['22','23'])
print("THE EXPOSURE CONTROL: does STOCK ever drive the regime the extremes live in?")
print("  extreme regime = |ang| >= 20 deg AND |cmd| >= 1500, engaged\n")
for arr,lab in ((A,'STOCK'),(B,'V112')):
    reg=(arr[:,1]>=20)&(arr[:,2]>=1500)
    print("  %-6s  %4d engaged windows,  %3d in the extreme regime (%.2f%%)"
          %(lab,len(arr),reg.sum(),100*reg.mean()))
    if reg.sum():
        print("           |ang| p50 %.1f  max %.1f  |  |cmd| p50 %.0f  |  6-9Hz p50 %.3f max %.3f"
              %(np.median(arr[reg,1]),arr[reg,1].max(),np.median(arr[reg,2]),
                np.median(arr[reg,0]),arr[reg,0].max()))
print("\n  STOCK's engaged |ang| distribution: p50 %.1f  p90 %.1f  p99 %.1f  max %.1f"
      %(*np.percentile(A[:,1],[50,90,99]),A[:,1].max()))
print("  V112's  engaged |ang| distribution: p50 %.1f  p90 %.1f  p99 %.1f  max %.1f"
      %(*np.percentile(B[:,1],[50,90,99]),B[:,1].max()))
print("\n  MATCHED COMPARISON where both arms have data:")
for lo,hi in [(0,5),(5,20),(20,60),(60,400)]:
    a=A[(A[:,1]>=lo)&(A[:,1]<hi)]; b=B[(B[:,1]>=lo)&(B[:,1]<hi)]
    if len(a)>=8 and len(b)>=8:
        print("   |ang| %3d-%3d  STOCK n=%3d p90 %6.3f max %6.3f  |  V112 n=%3d p90 %6.3f max %6.3f  | p90 ratio %5.2fx"
              %(lo,hi,len(a),np.percentile(a[:,0],90),a[:,0].max(),
                len(b),np.percentile(b[:,0],90),b[:,0].max(),
                np.percentile(b[:,0],90)/max(np.percentile(a[:,0],90),1e-9)))
    else:
        print("   |ang| %3d-%3d  STOCK n=%3d  V112 n=%3d  -- too few for a matched read"%(lo,hi,len(a),len(b)))
