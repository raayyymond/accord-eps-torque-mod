import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
z=np.load('analysis-2020accord/_scratch/cache/r21/r21.npz',allow_pickle=True)
G=lambda k:np.asarray(z[k]).astype(float)
v,tq,lat,rate,ang,cmd=[G(k) for k in ('cs_v','cs_tq','cc_lat','cs_rate','ang','co_tqcan')]
w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
ho=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]<1200
me=(lat>0.5)&ho&(v>1.0); mph=v*2.23694
def sm(x,n=9):
    p=np.pad(x,(n//2,n-1-n//2),mode='edge'); return np.convolve(p,np.ones(n)/n,'valid')[:len(x)]

print("CHANNEL CHECK on the engaged subset (corr with measured angle):")
for k in ('ct_curv','cc_ccurv','cc_curv','ct_dcurv'):
    a=G(k); f=me&np.isfinite(a)&np.isfinite(ang)
    print("   %-9s r=%.5f   %s" % (k,np.corrcoef(a[f],ang[f])[0,1],
        {'ct_curv':'controlsState.curvature  = CURRENT (circular!)',
         'cc_ccurv':'carControl.currentCurvature = CURRENT',
         'cc_curv':'carControl.actuators.curvature = THE DEMAND',
         'ct_dcurv':'controlsState.desiredCurvature = THE DEMAND'}[k]))

ach=np.abs(rate)
for dk in ('ct_dcurv','cc_curv'):
    dc=G(dk); fin=me&np.isfinite(dc)&np.isfinite(ang)
    k=np.polyfit(dc[fin],ang[fin],1)
    dem=np.abs(np.gradient(sm(np.polyval(k,dc)),0.01))
    m=me&np.isfinite(dem)&np.isfinite(ach)
    print("\n=== DEMAND FROM %s   (ang = %.1f*x + %.2f) ===" % (dk,k[0],k[1]))
    for lo,hi in [(0,5),(5,15),(15,30),(30,60),(60,120),(120,400)]:
        s=m&(dem>=lo)&(dem<hi)
        if s.sum()>60:
            print("   demand %3d-%3d  n=%6d  ACHIEVED p50 %6.1f p90 %6.1f max %6.1f   ach/dem(p50) %.2f"
                  %(lo,hi,s.sum(),*np.percentile(ach[s],[50,90]),ach[s].max(),
                    np.median(ach[s])/max(np.median(dem[s]),1e-9)))
    print("   demand  : p50 %.1f p90 %.1f p99 %.1f p99.9 %.1f max %.1f"%(*np.percentile(dem[m],[50,90,99,99.9]),dem[m].max()))
    print("   achieved: p50 %.1f p90 %.1f p99 %.1f p99.9 %.1f max %.1f"%(*np.percentile(ach[m],[50,90,99,99.9]),ach[m].max()))
    # low speed, where he complains
    s=m&(mph>=5)&(mph<15)
    print("   5-15 mph only: demand p99 %.1f p99.9 %.1f max %.1f | achieved p99 %.1f p99.9 %.1f max %.1f"
          %(*np.percentile(dem[s],[99,99.9]),dem[s].max(),*np.percentile(ach[s],[99,99.9]),ach[s].max()))
    # RAILED command: what is being demanded there?
    r=m&(np.abs(cmd)>=4090)
    print("   AT RAILED CMD 4096: n=%d  demand p50 %.1f p90 %.1f max %.1f | achieved p50 %.1f p90 %.1f max %.1f"
          %(r.sum(),*np.percentile(dem[r],[50,90]),dem[r].max(),*np.percentile(ach[r],[50,90]),ach[r].max()))
