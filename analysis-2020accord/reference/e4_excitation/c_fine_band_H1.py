import sys, numpy as np, json
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(7)
NP=M.NPERSEG; WN=np.hanning(NP); U=(WN**2).sum()

def prep(route, arm):
    t,e4,y,m,meta=M.load(route)
    eng=m["eng"]
    msk = eng if arm=="ALL" else (eng&~m["press"] if arm=="HANDS-OFF" else eng&m["press"])
    blks=[]
    for a,b in M.episodes(msk,t,5.2):
        s=a; n=int(20*M.FS)
        while s+NP<=b:
            e=min(s+n,b)
            if e-s>=NP: blks.append((s,e))
            s=e
    X=[];Y=[];bid=[]
    for i,(a,b) in enumerate(blks):
        for s in range(a,b-NP+1,NP//2):
            xs=e4[s:s+NP]; ys=y[s:s+NP]
            X.append(np.fft.rfft((xs-xs.mean())*WN)); Y.append(np.fft.rfft((ys-ys.mean())*WN)); bid.append(i)
    return np.fft.rfftfreq(NP,1/M.FS), np.array(X), np.array(Y), np.array(bid), len(blks), meta

def pooled(X,Y,idx):
    return (np.abs(X[idx])**2).mean(0),(np.abs(Y[idx])**2).mean(0),(np.conj(X[idx])*Y[idx]).mean(0)

def bs(f,Sxx,Syy,Sxy,lo,hi):
    b=M.band(f,lo,hi); sxx=Sxx[b].sum(); syy=Syy[b].sum(); sxy=Sxy[b].sum()
    c=float(np.mean(M.interp_corr(f[b])))
    return abs(sxy)**2/max(sxx*syy,1e-30), abs(sxy)/max(sxx,1e-30)/np.sqrt(c)

FINE=[(0.5,1.5),(1.5,3.0),(3.0,4.5),(4.5,6.0),(6.0,7.5),(7.5,9.0),(9.0,12.0),(12.0,16.0),(16.0,20.0),(20.0,24.0)]

for route,arm in [("73","HANDS-OFF"),("73","ALL"),("75","ALL"),("76","ALL")]:
    f,X,Y,bid,nb,meta=prep(route,arm)
    nw=len(X)
    Sxx,Syy,Sxy=pooled(X,Y,np.arange(nw))
    print("="*104)
    print("ROUTE %s (%s) %s  blocks=%d windows=%d   [SIGNED 427]" % (route,meta[0],arm,nb,nw) if route=="73"
          else "ROUTE %s (%s) %s  blocks=%d windows=%d   [RECTIFIED 427]"%(route,meta[0],arm,nb,nw))
    print("  band        g2      shufG2_p95   H1(ct/ct)  shufH1_p50  shufH1_p95   H1_boot95CI      ex_rms")
    # shuffled null (200 draws) and block bootstrap (400) per fine band
    NS=200; NBOOT=400
    sg={k:[] for k in range(len(FINE))}; sh1={k:[] for k in range(len(FINE))}
    for _ in range(NS):
        p=rng.permutation(nw); bad=bid[p]==bid
        if bad.any(): p[bad]=np.roll(p,1)[bad]
        S=pooled(X,Y[p],np.arange(nw))
        for k,(lo,hi) in enumerate(FINE):
            g,h=bs(f,*S,lo,hi); sg[k].append(g); sh1[k].append(h)
    bh={k:[] for k in range(len(FINE))}
    for _ in range(NBOOT):
        pick=rng.integers(0,nb,nb); idx=np.concatenate([np.where(bid==q)[0] for q in pick])
        S=pooled(X,Y,idx)
        for k,(lo,hi) in enumerate(FINE):
            bh[k].append(bs(f,*S,lo,hi)[1])
    for k,(lo,hi) in enumerate(FINE):
        g,h=bs(f,Sxx,Syy,Sxy,lo,hi)
        b=M.band(f,lo,hi); ex=float(np.sqrt(2*Sxx[b].sum()/(U*NP)))
        print("  %5.1f-%-5.1f %7.4f   %8.4f   %8.4f   %8.4f   %8.4f   [%6.3f,%6.3f]  %8.2f"%(
            lo,hi,g,np.percentile(sg[k],95),h,np.median(sh1[k]),np.percentile(sh1[k],95),
            np.percentile(bh[k],2.5),np.percentile(bh[k],97.5),ex))
