import numpy as np
def load(r):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    s=np.load('analysis-2020accord/_scratch/cache/r%s/r%s_spec.npz'%(r,r),allow_pickle=True)
    return (dict(t=G('t'),ang=G('ang'),rate=G('cs_rate'),v=G('cs_v'),tq=G('cs_tq'),
                 cmd=G('co_tqcan'),lat=G('cc_lat'),seg=G('seg')), dict(s))
BANDS=[(60,120),(120,250),(250,500),(500,1000),(1000,2000),(2000,4000)]
for r in ('22','23'):
    d,S=load(r)
    key=[k for k in S if S[k].ndim==2][0]; tk=[k for k in S if S[k].ndim==1 and len(S[k])==S[key].shape[0]]
    Sp=S[key]; st=S[tk[0]] if tk else None
    fk=[k for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[1]]
    fr=S[fk[0]] if fk else np.arange(Sp.shape[1])*3.90625
    print("\n%s r%s: spec %s  f %.1f..%.0f Hz  t %.1f..%.1f s"%("="*20,r,Sp.shape,fr[0],fr[-1],st[0],st[-1]))
    # map CAN state onto spectrogram frames
    v=np.interp(st,d['t'],d['v'])*2.23694
    lat=np.interp(st,d['t'],d['lat'])
    cmd=np.interp(st,d['t'],np.abs(d['cmd']))
    ang=np.interp(st,d['t'],np.abs(d['ang']))
    P=np.abs(Sp)**2 if np.iscomplexobj(Sp) else np.asarray(Sp,float)
    if P.max()<=0: print("  empty"); continue
    lo=(v>=5)&(v<10)
    eng=lo&(lat>0.9); man=lo&(lat<0.1)
    print("  5-10 mph frames: engaged %d  manual %d"%(eng.sum(),man.sum()))
    if eng.sum()<50 or man.sum()<50: print("  insufficient contrast"); continue
    print("  band Hz      engaged dB   manual dB   EXCESS dB   (engaged-minus-manual, within-drive)")
    ex={}
    for a,b in BANDS:
        bb=(fr>=a)&(fr<b)
        e=10*np.log10(np.mean(P[np.ix_(eng,bb)])+1e-30)
        m=10*np.log10(np.mean(P[np.ix_(man,bb)])+1e-30)
        ex[(a,b)]=e-m
        print("   %5d-%5d   %8.2f   %8.2f   %+8.2f"%(a,b,e,m,e-m))
    best=max(ex,key=lambda k:ex[k])
    bb=(fr>=best[0])&(fr<best[1])
    band_t=10*np.log10(np.mean(P[:,bb],axis=1)+1e-30)
    base=np.median(band_t[man]) if man.sum() else np.median(band_t)
    excess=band_t-base
    cand=np.where(eng&(excess>np.percentile(excess[eng],95)))[0]
    print("\n  LOUDEST band = %d-%d Hz (+%.2f dB engaged).  Top engaged 5-10 mph moments:"%(best[0],best[1],ex[best]))
    print("    t_s      excess dB   |cmd|   |ang|   v mph")
    grp=np.split(cand,np.where(np.diff(cand)>4)[0]+1) if len(cand) else []
    ev=[]
    for g in grp:
        if len(g)<2: continue
        i=g[np.argmax(excess[g])]
        ev.append((st[i],excess[i],cmd[i],ang[i],v[i],len(g)*0.05))
    for e in sorted(ev,key=lambda x:-x[1])[:12]:
        print("   %7.1f    %+8.2f   %6.0f  %6.1f   %5.1f   (%.2f s)"%(e[0],e[1],e[2],e[3],e[4],e[5]))
    if ev:
        E=np.array([[x[2],x[3],x[4],x[1]] for x in ev])
        print("    -> %d episodes; |cmd| p50 %.0f  |ang| p50 %.1f  v p50 %.1f mph"
              %(len(ev),np.median(E[:,0]),np.median(E[:,1]),np.median(E[:,2])))
