import numpy as np, glob, os
from numpy.lib.stride_tricks import sliding_window_view
def sm(x,n=9):
    p=np.pad(x,(n//2,n-1-n//2),mode='edge'); return np.convolve(p,np.ones(n)/n,'valid')[:len(x)]
print("Is openpilot RAILED where it fails to get the rate?  (rail = |cmd|>=4090 of STEER_MAX 4096)\n")
print("%-5s | %s" % ("route"," ".join("%13s"%b for b in ("dem 5-15","dem 15-30","dem 30-60","dem 60+"))))
print("%-5s | %s" % ("     "," ".join("%13s"%"rail%  ach/dem" for _ in range(4))))
agg={}
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
    me=(lat>0.5)&ho&(v>1.0)
    fin=me&np.isfinite(dc)&np.isfinite(ang)
    if fin.sum()<3000: continue
    k=np.polyfit(dc[fin],ang[fin],1)
    dem=np.abs(np.gradient(sm(np.polyval(k,dc)),0.01)); ach=np.abs(rate); c=np.abs(cmd)
    m=me&np.isfinite(dem)&np.isfinite(ach)
    cells=[]
    for lo,hi in [(5,15),(15,30),(30,60),(60,1e9)]:
        s=m&(dem>=lo)&(dem<hi)
        if s.sum()>150:
            rl=np.mean(c[s]>=4090); rt=np.median(ach[s])/max(np.median(dem[s]),1e-9)
            cells.append("%5.1f%% %6.2f"%(100*rl,rt))
            agg.setdefault((lo,hi),[]).append((rl,rt,s.sum()))
        else: cells.append("      -      ")
    print("%-5s | %s" % (tag," ".join("%13s"%x for x in cells)))
print("\nCORPUS POOLED (weighted by n):")
for (lo,hi),vals in sorted(agg.items()):
    n=sum(x[2] for x in vals)
    rl=sum(x[0]*x[2] for x in vals)/n; rt=sum(x[1]*x[2] for x in vals)/n
    print("   demand %3d-%-4s n=%7d   RAIL DUTY %5.1f%%   ach/dem %.2f" %
          (lo,("%d"%hi if hi<1e8 else "inf"),n,100*rl,rt))
