import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(3)
NPS=512; WN=np.hanning(NPS); U=(WN**2).sum()
BANDS=[("0.5-3",(0.5,3.0)),("4.5-6",(4.5,6.0)),("6-9",(6.0,9.0)),("9-12",(9.0,12.0)),("20-24",(20.0,24.0))]

def fft_set(sig,blks):
    A=[]
    for a,b in blks:
        for s in range(a,b-NPS+1,NPS//2):
            x=sig[s:s+NPS]; A.append(np.fft.rfft((x-x.mean())*WN))
    return np.array(A)

for route in ["73","75","76"]:
    t,e4,y,m,meta=M.load(route)
    z=dict(np.load('_cache_r%s/r%s.npz'%(route,route),allow_pickle=True))
    tq=np.asarray(z["tq"],float)
    eng=m["eng"]; off=eng&~m["press"]
    for arm,msk in [("HANDS-OFF",off),("ALL",eng)]:
        blks=[]
        for a,b in M.episodes(msk,t,5.2):
            s=a;n=int(20*M.FS)
            while s+NPS<=b:
                e=min(s+n,b)
                if e-s>=NPS: blks.append((s,e))
                s=e
        if len(blks)<4: continue
        bid=[]
        for i,(a,b) in enumerate(blks):
            for s in range(a,b-NPS+1,NPS//2): bid.append(i)
        bid=np.array(bid)
        E=fft_set(e4,blks); Yv=fft_set(y,blks); T=fft_set(tq,blks)
        f=np.fft.rfftfreq(NPS,1/M.FS); nw=len(E)
        def pair(A,B,lo,hi,idx=None):
            idx=np.arange(len(A)) if idx is None else idx
            b=M.band(f,lo,hi)
            sxx=(np.abs(A[idx][:,b])**2).mean(0).sum(); syy=(np.abs(B[idx][:,b])**2).mean(0).sum()
            sxy=(np.conj(A[idx][:,b])*B[idx][:,b]).mean(0).sum()
            return abs(sxy)**2/max(sxx*syy,1e-30), abs(sxy)/max(sxx,1e-30), float(np.sqrt(2*syy/(U*NPS)))
        def shufnull(A,B,lo,hi,n=200):
            out=[]
            for _ in range(n):
                p=rng.permutation(nw); bad=bid[p]==bid
                if bad.any(): p[bad]=np.roll(p,1)[bad]
                b=M.band(f,lo,hi)
                sxx=(np.abs(A[:,b])**2).mean(0).sum(); syy=(np.abs(B[p][:,b])**2).mean(0).sum()
                sxy=(np.conj(A[:,b])*B[p][:,b]).mean(0).sum()
                out.append(abs(sxy)**2/max(sxx*syy,1e-30))
            return np.percentile(out,95)
        print("="*100)
        print("ROUTE %s (%s) %s  blocks=%d win=%d   [tq = TORSION BAR from 0x14A, same grid as t]"%(route,meta[0],arm,len(blks),nw))
        for nm,(lo,hi) in BANDS:
            g1,h1,ry = pair(E,Yv,lo,hi)      # e4 -> 6b98
            g2,h2,rt = pair(E,T ,lo,hi)      # e4 -> bar
            g3,h3,_  = pair(Yv,T,lo,hi)      # 6b98 -> bar (CLOSED LOOP, biased)
            n1=shufnull(E,Yv,lo,hi); n2=shufnull(E,T,lo,hi); n3=shufnull(Yv,T,lo,hi)
            print("  %-6s  e4->6b98 g2=%.4f(null %.4f)  e4->bar g2=%.4f(null %.4f)  6b98->bar g2=%.4f(null %.4f) | 6b98rms %7.2f ct  bar rms %7.3f ct"%(
                nm,g1,n1,g2,n2,g3,n3,ry,rt))
            if nm=="6-9":
                print("        IV |H(bar/6b98)| = |S_e4,bar|/|S_e4,6b98| = %.5f bar-ct per 6b98-ct"%(h2/max(h1,1e-30)))
