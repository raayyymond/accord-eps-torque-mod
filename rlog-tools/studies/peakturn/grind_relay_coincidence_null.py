import numpy as np
rng=np.random.default_rng(0)
RAW_THR=1800/12.0
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    S=dict(np.load('analysis-2020accord/_scratch/cache/r%s/r%s_spec.npz'%(r,r),allow_pickle=True))
    Sp=[S[k] for k in S if S[k].ndim==2][0]
    st=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[0]][0]
    fr=[S[k] for k in S if S[k].ndim==1 and len(S[k])==Sp.shape[1]][0]
    P=np.asarray(Sp,float)
    v=np.interp(st,G('t'),G('cs_v'))*2.23694; lat=np.interp(st,G('t'),G('cc_lat'))
    band=(fr>=120)&(fr<250)
    x=10*np.log10(np.mean(P[:,band],axis=1)+1e-30)
    # relay saturation on the wire timebase -> resample to spectrogram frames
    raw=G('ab_mt')*1.6; wt=G('ab_t1ab')
    satw=(raw>=RAW_THR).astype(float)
    sat=np.interp(st,wt,satw)>0.5
    eng=(lat>0.9)&(v<15)
    if eng.sum()<100: print("r%s too few"%r); continue
    base=np.median(x[eng&~sat]); 
    obs=np.mean(x[eng&sat])-np.mean(x[eng&~sat])
    # NULL: circularly rotate the saturation mask (preserves its run structure & duty)
    idx=np.where(eng)[0]; xs=x[idx]; ss=sat[idx]
    nulls=[]
    for _ in range(4000):
        k=rng.integers(1,len(ss))
        sr=np.roll(ss,k)
        if sr.sum()<10 or (~sr).sum()<10: continue
        nulls.append(np.mean(xs[sr])-np.mean(xs[~sr]))
    p=np.mean(np.array(nulls)>=obs)
    print("r%s  120-250 Hz during RELAY SATURATION vs not, engaged <15 mph"%r)
    print("   n_sat %d  n_notsat %d"%((eng&sat).sum(),(eng&~sat).sum()))
    print("   OBSERVED %+.3f dB   circular-shift null p50 %+.3f p95 %+.3f p99 %+.3f   p = %.4f  => %s"
          %(obs,np.percentile(nulls,50),np.percentile(nulls,95),np.percentile(nulls,99),p,
            "PASSES" if p<0.05 else "fails"))
