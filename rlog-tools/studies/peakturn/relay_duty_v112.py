import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
RATE_SCALE=4.7121
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    d={k:G(k) for k in ('t','ang','cs_rate','cs_v','cs_tq','co_tqcan','cc_lat')}
    d['wire']=G('ab_mt'); d['wt']=G('ab_t1ab')
    w=51;pad=np.pad(np.abs(d['cs_tq']),(w//2,w-1-w//2),mode='edge')
    d['med']=np.median(sliding_window_view(pad,w),axis=-1)[:len(d['cs_tq'])]
    return d
KNEE={'21':600,'22':1800,'23':1800}
BUILD={'21':'V111','22':'V112','23':'V112'}
print("RELAY SATURATION DUTY on the 427 probe -- |gp-0x6abc| = wire * 1.6 raw counts")
print("saturates when |gp-0x6abc| >= knee/12.   V111 knee 600 -> 50 ct; V112 knee 1800 -> 150 ct\n")
print("  route build knee | regime 5-10 mph engaged |cmd|>=2048        | all engaged")
print("                   |    n    duty    p50 raw   p95 raw          |  duty")
for r in ('21','22','23'):
    d=load(r); knee=KNEE[r]; thr=knee/12.0
    # map CAN state onto the 1AB wire timebase
    v=np.interp(d['wt'],d['t'],d['cs_v'])*2.23694
    lat=np.interp(d['wt'],d['t'],d['cc_lat'])
    cmd=np.interp(d['wt'],d['t'],np.abs(d['co_tqcan']))
    med=np.interp(d['wt'],d['t'],d['med'])
    raw=d['wire']*1.6
    reg=(lat>0.9)&(v>=5)&(v<10)&(cmd>=2048)&(med<1200)
    eng=(lat>0.9)
    print("  r%-3s %-5s %4d |  %5d  %.4f  %8.0f  %8.0f          |  %.4f"
          %(r,BUILD[r],knee,reg.sum(),np.mean(raw[reg]>=thr) if reg.sum() else np.nan,
            np.percentile(raw[reg],50) if reg.sum() else np.nan,
            np.percentile(raw[reg],95) if reg.sum() else np.nan,
            np.mean(raw[eng]>=thr)))
print("\n  PREDICTED from route 21: knee 600 -> 0.7439 [0.669,0.815];  knee 1800 -> 0.2353")
print("\nWHERE DOES THE RELAY STILL SATURATE ON V112?  (candidate grind #1 triggers)")
for r in ('22','23'):
    d=load(r); thr=1800/12.0
    v=np.interp(d['wt'],d['t'],d['cs_v'])*2.23694
    lat=np.interp(d['wt'],d['t'],d['cc_lat'])
    cmd=np.interp(d['wt'],d['t'],np.abs(d['co_tqcan']))
    ang=np.interp(d['wt'],d['t'],np.abs(d['ang']))
    raw=d['wire']*1.6
    sat=(lat>0.9)&(raw>=thr)&(v<15)
    idx=np.where(sat)[0]
    if not len(idx): print("  r%s: none"%r); continue
    grp=[g for g in np.split(idx,np.where(np.diff(idx)>3)[0]+1) if len(g)>=3]
    print("  r%s: %d saturated samples, %d runs >=3 samples (>=60 ms).  Longest runs:"%(r,len(idx),len(grp)))
    for g in sorted(grp,key=lambda g:-len(g))[:8]:
        print("     t=%7.1f s  %5.0f ms  v %4.1f mph  |cmd| %5.0f  |ang| %5.1f  peak raw %5.0f"
              %(d['wt'][g[0]],len(g)*20.1,v[g].mean(),cmd[g].mean(),ang[g].mean(),raw[g].max()))
