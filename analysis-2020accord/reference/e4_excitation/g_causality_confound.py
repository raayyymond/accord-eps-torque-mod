import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(5)
NPS=512; WN=np.hanning(NPS); U=(WN**2).sum()

def bp(x,lo,hi,fs=100.0):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/fs)
    X[(f<lo)|(f>hi)]=0
    return np.fft.irfft(X,len(x))

for route in ["73","75","76"]:
    t,e4,y,m,meta=M.load(route)
    z=dict(np.load('_cache_r%s/r%s.npz'%(route,route),allow_pickle=True))
    tq=np.asarray(z["tq"],float); ang=np.asarray(z["ang"],float)
    rate=np.asarray(z["rate_c"],float)
    eng=m["eng"]; off=eng&~m["press"]
    blks=[]
    for a,b in M.episodes(off,t,5.2):
        s=a;n=int(20*M.FS)
        while s+NPS<=b:
            e=min(s+n,b)
            if e-s>=NPS: blks.append((s,e))
            s=e
    def F(sig):
        A=[]
        for a,b in blks:
            for s in range(a,b-NPS+1,NPS//2):
                x=sig[s:s+NPS]; A.append(np.fft.rfft((x-x.mean())*WN))
        return np.array(A)
    E,T,A,R,Yv = F(e4),F(tq),F(ang),F(rate),F(y)
    f=np.fft.rfftfreq(NPS,1/M.FS); nw=len(E)
    bidl=[]
    for i,(a,b) in enumerate(blks):
        for s in range(a,b-NPS+1,NPS//2): bidl.append(i)
    bid=np.array(bidl)
    def g2(X,Y,lo,hi):
        b=M.band(f,lo,hi)
        sxx=(np.abs(X[:,b])**2).mean(0).sum(); syy=(np.abs(Y[:,b])**2).mean(0).sum()
        sxy=(np.conj(X[:,b])*Y[:,b]).mean(0).sum()
        return abs(sxy)**2/max(sxx*syy,1e-30)
    print("="*100)
    print("ROUTE %s (%s) HANDS-OFF  win=%d   WHAT IS e4tq COHERENT WITH at 6-9 Hz?"%(route,meta[0],nw))
    for nm,(lo,hi) in [("0.5-3",(0.5,3.0)),("6-9",(6.0,9.0)),("9-12",(9.0,12.0)),("20-24",(20,24))]:
        print("  %-6s  e4~bar %.4f   e4~ANGLE %.4f   e4~ANGRATE %.4f   e4~6b98 %.4f   bar~ANGLE %.4f"%(
            nm,g2(E,T,lo,hi),g2(E,A,lo,hi),g2(E,R,lo,hi),g2(E,Yv,lo,hi),g2(T,A,lo,hi)))
    # ---- CAUSALITY: lagged cross-correlation of 6-9 Hz bandpassed e4 vs bar, per block
    lags=np.arange(-40,41)   # +-400 ms
    acc=np.zeros(len(lags)); nrm=0
    for a,b in blks:
        xe=bp(e4[a:b]-e4[a:b].mean(),6,9); xt=bp(tq[a:b]-tq[a:b].mean(),6,9)
        sx=np.std(xe); st=np.std(xt)
        if sx<1e-9 or st<1e-9: continue
        c=np.correlate(xt/st,xe/sx,'full')/len(xe)
        mid=len(xe)-1
        acc+=c[mid+lags]; nrm+=1
    acc/=max(nrm,1)
    k=np.argmax(np.abs(acc))
    print("  6-9 Hz cross-corr  peak |r|=%.4f at lag %+d ms  (positive lag = BAR LAGS e4 = e4 causes bar)"%(abs(acc[k]),lags[k]*10))
    print("   ",' '.join('%+d:%+.3f'%(l*10,v) for l,v in zip(lags[::4],acc[::4]) if abs(l)<=20))
