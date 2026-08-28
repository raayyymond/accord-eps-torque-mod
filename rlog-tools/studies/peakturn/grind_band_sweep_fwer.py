import numpy as np
rng=np.random.default_rng(0)
EDGES=[(20,40),(40,80),(80,120),(120,160),(160,220),(220,300),(300,400),(400,550),
       (550,750),(750,1000),(1000,1400),(1400,2000)]
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    S=dict(np.load('analysis-2020accord/_scratch/cache/r%s/r%s_spec.npz'%(r,r),allow_pickle=True))
    Sp=[S[k] for k in S if S[k].ndim==2][0]
    st=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[0]][0]
    fr=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[1]][0]
    P=np.asarray(Sp,float)
    v=np.interp(st,G('t'),G('cs_v'))*2.23694; lat=np.interp(st,G('t'),G('cc_lat'))
    cmd=np.interp(st,G('t'),np.abs(G('co_tqcan')))
    lo=(v>=5)&(v<12)
    eng=lo&(lat>0.9)&(cmd>=1024); man=lo&(lat<0.1)
    print("\nr%s  ENGAGED(cmd>=1024) n=%d   MANUAL n=%d   -- band sweep, %d bands"
          %(r,eng.sum(),man.sum(),len(EDGES)))
    if eng.sum()<60 or man.sum()<60: print("   too few"); continue
    obs=[];curves=[]
    for a,b in EDGES:
        bb=(fr>=a)&(fr<b)
        x=10*np.log10(np.mean(P[:,bb],axis=1)+1e-30)
        curves.append(x); obs.append(np.mean(x[eng])-np.mean(x[man]))
    obs=np.array(obs)
    # MAX-STATISTIC null: circularly shift the engaged label, recompute ALL bands, keep the max
    idx=np.where(lo)[0]; lab=(lat[idx]>0.9)&(cmd[idx]>=1024); labm=(lat[idx]<0.1)
    maxnull=[]
    for _ in range(3000):
        k=rng.integers(1,len(idx))
        L=np.roll(lab,k); M=np.roll(labm,k)
        if L.sum()<30 or M.sum()<30: continue
        st_=[np.mean(c[idx][L])-np.mean(c[idx][M]) for c in curves]
        maxnull.append(max(st_))
    thr95=np.percentile(maxnull,95)
    print("   max-statistic null (family-wise) p95 = %+.3f dB"%thr95)
    print("   band Hz        observed dB    verdict")
    for (a,b),o in zip(EDGES,obs):
        print("   %5d-%5d      %+7.3f     %s"%(a,b,o,"** PASSES FWER **" if o>thr95 else ""))
    print("   best band %d-%d Hz at %+.3f dB"%(EDGES[int(np.argmax(obs))][0],
          EDGES[int(np.argmax(obs))][1],obs.max()))
