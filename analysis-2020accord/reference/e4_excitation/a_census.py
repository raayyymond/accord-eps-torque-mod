import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
np.set_printoptions(suppress=True)

for r in ["71","73","75","76"]:
    t,e4,y,m,meta = M.load(r)
    build,src,lsb,signed = meta
    eng=m["eng"]
    print("="*90)
    print("ROUTE %s  build=%s  427<-%s  %.1f ct/LSB  signed=%s   N=%d  dur=%.1fs"%(r,build,src,lsb,signed,len(t),t[-1]-t[0]))
    if "lat" in m:
        agree = np.mean(m["lat"]==eng)
        print("   e4req vs cc_lat agreement: %.4f"%agree)
    print("   engaged frames %d (%.1f s, %.1f%%)  | hands-on within engaged %.3f"%(
        eng.sum(), eng.sum()/M.FS, 100*eng.mean(), m["press"][eng].mean() if eng.any() else np.nan))
    eps = M.episodes(eng,t,3.0)
    dur=[(t[b-1]-t[a]) for a,b in eps]
    print("   episodes>=3s: %d   total %.1fs   median %.1fs  max %.1fs"%(len(eps),sum(dur),np.median(dur) if dur else 0,max(dur) if dur else 0))
    eps5=M.episodes(eng,t,5.2)
    print("   episodes>=5.2s (1 window): %d  total %.1fs"%(len(eps5), sum((t[b-1]-t[a]) for a,b in eps5)))
    v=m["v"][eng]
    print("   engaged speed km/h: p10 %.1f p50 %.1f p90 %.1f  | frac>=50: %.3f"%(
        np.percentile(v,10),np.percentile(v,50),np.percentile(v,90),(v>=50).mean()))
    print("   427 SATURATED frames within engaged: %.4f"%(m["sat"][eng].mean()))
    print("   e4tq engaged: p50|.| %.1f  p95|.| %.1f  max|.| %.1f  rail(|.|>=4090) %.4f"%(
        np.percentile(np.abs(e4[eng]),50),np.percentile(np.abs(e4[eng]),95),
        np.abs(e4[eng]).max(), (np.abs(e4[eng])>=4090).mean()))
    print("   427 counts engaged: p50 %.1f p95 %.1f max %.1f"%(
        np.percentile(np.abs(y[eng]),50),np.percentile(np.abs(y[eng]),95),np.abs(y[eng]).max()))
    # per-window input spectrum: is there ANY 6-9 Hz content in e4?
    W = M.windows(t,e4,y,eps5)
    if W is None: print("   NO WINDOWS"); continue
    f,X,Y,ep = W
    print("   windows %d over %d episodes"%(len(X),len(set(ep.tolist()))))
    Sxx=(np.abs(X)**2).mean(0); Syy=(np.abs(Y)**2).mean(0)
    for nm,(lo,hi) in [("0.5-3",M.BAND_LO),("6-9",M.BAND_HI),("20-24",M.BAND_CT)]:
        b=M.band(f,lo,hi)
        # convert to rms counts in band: Welch scaling with hann
        wn=np.hanning(M.NPERSEG); U=(wn**2).sum()
        rx=np.sqrt(2*Sxx[b].sum()/U); ry=np.sqrt(2*Syy[b].sum()/U)
        print("      band %-6s  e4 rms %8.3f ct   427 rms %8.3f ct"%(nm,rx,ry))
