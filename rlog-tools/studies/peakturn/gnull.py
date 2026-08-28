import numpy as np
rng=np.random.default_rng(0)
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    S=dict(np.load('analysis-2020accord/_scratch/cache/r%s/r%s_spec.npz'%(r,r),allow_pickle=True))
    Sp=[S[k] for k in S if S[k].ndim==2][0]
    st=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[0]][0]
    fr=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[1]][0]
    P=np.asarray(Sp,float)
    v=np.interp(st,G('t'),G('cs_v'))*2.23694; lat=np.interp(st,G('t'),G('cc_lat'))
    lo=(v>=5)&(v<10); eng=lo&(lat>0.9); man=lo&(lat<0.1)
    band=(fr>=120)&(fr<250)
    x=10*np.log10(np.mean(P[:,band],axis=1)+1e-30)
    obs=np.mean(x[eng])-np.mean(x[man])
    # NULL 1: split the MANUAL frames in two disjoint halves -- no engagement involved
    mi=np.where(man)[0]; n2=len(mi)//2
    nulls=[]
    for _ in range(2000):
        p=rng.permutation(mi); a,b=p[:n2],p[n2:2*n2]
        nulls.append(np.mean(x[a])-np.mean(x[b]))
    # NULL 2: block-shuffle the engagement label in 5 s blocks (preserves autocorrelation)
    blk=100  # 5 s at 20 Hz frames
    idx=np.where(lo)[0]; lab=lat[idx]>0.9
    nb=len(idx)//blk
    nulls2=[]
    for _ in range(2000):
        perm=rng.permutation(nb)
        L=np.concatenate([lab[perm[k]*blk:(perm[k]+1)*blk] for k in range(nb)])
        xi=x[idx[:nb*blk]]
        if L.sum()<20 or (~L).sum()<20: continue
        nulls2.append(np.mean(xi[L])-np.mean(xi[~L]))
    print("r%s  120-250 Hz engaged-minus-manual at 5-10 mph"%r)
    print("   OBSERVED %+.3f dB   (n_eng %d, n_man %d)"%(obs,eng.sum(),man.sum()))
    print("   NULL 1 disjoint manual halves : p50 %+.3f  p95 %+.3f  p99 %+.3f  => %s"
          %(np.percentile(nulls,50),np.percentile(nulls,95),np.percentile(nulls,99),
            "PASSES" if obs>np.percentile(nulls,95) else "FAILS its own null"))
    if nulls2:
        print("   NULL 2 block-shuffled label  : p50 %+.3f  p95 %+.3f  p99 %+.3f  => %s"
              %(np.percentile(nulls2,50),np.percentile(nulls2,95),np.percentile(nulls2,99),
                "PASSES" if obs>np.percentile(nulls2,95) else "FAILS its own null"))
