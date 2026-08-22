import sys, numpy as np, json
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(20260821)
WN=np.hanning(M.NPERSEG); U=(WN**2).sum(); NP=M.NPERSEG
def rms(S,b): return float(np.sqrt(2*S[b].sum()/(U*NP)))

BANDS=[("0.5-3",M.BAND_LO),("6-9",M.BAND_HI),("20-24",M.BAND_CT)]

def blocks(mask,t,blk=20.0,minfrac=1.0):
    """Contiguous engaged runs cut into ~blk-second blocks; each block is a bootstrap unit."""
    out=[]
    for a,b in M.episodes(mask,t,5.2):
        n=int(blk*M.FS)
        s=a
        while s+NP<=b:
            e=min(s+n,b)
            if e-s>=NP: out.append((s,e))
            s=e
    return out

def pooled(X,Y,idx):
    Sxx=(np.abs(X[idx])**2).mean(0); Syy=(np.abs(Y[idx])**2).mean(0)
    Sxy=(np.conj(X[idx])*Y[idx]).mean(0)
    return Sxx,Syy,Sxy

def bandstat(f,Sxx,Syy,Sxy,lo,hi):
    b=M.band(f,lo,hi)
    sxx=Sxx[b].sum(); syy=Syy[b].sum(); sxy=Sxy[b].sum()
    g2=abs(sxy)**2/max(sxx*syy,1e-30)
    c=float(np.mean(M.interp_corr(f[b])))
    H1=abs(sxy)/max(sxx,1e-30)/np.sqrt(c)
    return dict(g2=float(g2),H1=float(H1),ex_rms=rms(Sxx,b),out_rms=rms(Syy,b)/np.sqrt(c))

RES={}
for r in ["71","73","75","76"]:
    t,e4,y,m,meta=M.load(r)
    eng=m["eng"]
    for arm,msk in [("ALL",eng),("HANDS-OFF",eng&~m["press"]),("HANDS-ON",eng&m["press"])]:
        blks=blocks(msk,t)
        if not blks: continue
        # per-block window FFTs
        X=[];Y=[];bid=[]
        for i,(a,b) in enumerate(blks):
            for s in range(a,b-NP+1,NP//2):
                xs=e4[s:s+NP]; ys=y[s:s+NP]
                X.append(np.fft.rfft((xs-xs.mean())*WN)); Y.append(np.fft.rfft((ys-ys.mean())*WN)); bid.append(i)
        X=np.array(X);Y=np.array(Y);bid=np.array(bid)
        f=np.fft.rfftfreq(NP,1/M.FS)
        nb=len(blks); nw=len(X)
        if nw<8: continue
        Sxx,Syy,Sxy=pooled(X,Y,np.arange(nw))
        row={"route":r,"build":meta[0],"arm":arm,"nblocks":nb,"nwin":nw,
             "sec":float(sum((b-a) for a,b in blks)/M.FS)}
        for nm,(lo,hi) in BANDS: row[nm]=bandstat(f,Sxx,Syy,Sxy,lo,hi)
        # ---- CONTROL 1: shuffled pairs.  Y windows permuted ACROSS blocks.
        nullg={nm:[] for nm,_ in BANDS}
        for _ in range(200):
            perm=rng.permutation(nw)
            # forbid same-block pairing
            bad=bid[perm]==bid
            if bad.any(): perm[bad]=np.roll(perm,1)[bad]
            S2xx,S2yy,S2xy=pooled(X,Y[perm],np.arange(nw))
            for nm,(lo,hi) in BANDS: nullg[nm].append(bandstat(f,S2xx,S2yy,S2xy,lo,hi)["g2"])
        row["shuffled"]={nm:{"p50":float(np.median(v)),"p95":float(np.percentile(v,95))} for nm,v in nullg.items()}
        # ---- CONTROL 2: block bootstrap CI on g2 and H1
        boot={nm:{"g2":[],"H1":[]} for nm,_ in BANDS}
        for _ in range(400):
            pick=rng.integers(0,nb,nb)
            idx=np.concatenate([np.where(bid==p)[0] for p in pick])
            Sb=pooled(X,Y,idx)
            for nm,(lo,hi) in BANDS:
                st=bandstat(f,*Sb,lo,hi); boot[nm]["g2"].append(st["g2"]); boot[nm]["H1"].append(st["H1"])
        row["boot"]={nm:{k:[float(np.percentile(v,2.5)),float(np.percentile(v,97.5))] for k,v in d.items()} for nm,d in boot.items()}
        # ---- CONTROL 3: split-half null on the H1 band RATIO (6-9 / 0.5-3)
        sh=[]
        for _ in range(400):
            p=rng.permutation(nb); h1=set(p[:nb//2].tolist()); 
            if not h1 or len(h1)==nb: continue
            iA=np.where(np.isin(bid,list(h1)))[0]; iB=np.where(~np.isin(bid,list(h1)))[0]
            if len(iA)<4 or len(iB)<4: continue
            A=pooled(X,Y,iA); B=pooled(X,Y,iB)
            ra=bandstat(f,*A,*M.BAND_HI)["H1"]; rb=bandstat(f,*B,*M.BAND_HI)["H1"]
            sh.append(ra/max(rb,1e-30))
        row["splithalf_H1_69"]=[float(np.percentile(sh,2.5)),float(np.percentile(sh,97.5))] if sh else None
        RES[(r,arm)]=row
        print("route %s %-9s blocks=%2d win=%3d  %.0fs"%(r,arm,nb,nw,row["sec"]))
        for nm,_ in BANDS:
            s=row[nm]
            print("    %-6s g2=%.4f [%.4f,%.4f]  shuf p50 %.4f p95 %.4f | H1=%.4f [%.4f,%.4f] ct/ct | ex_rms %7.2f out_rms %8.2f"%(
                nm,s["g2"],*row["boot"][nm]["g2"],row["shuffled"][nm]["p50"],row["shuffled"][nm]["p95"],
                s["H1"],*row["boot"][nm]["H1"],s["ex_rms"],s["out_rms"]))
        print("    split-half H1(6-9) ratio null:",row["splithalf_H1_69"])
json.dump({("r%s|%s"%k):v for k,v in RES.items()},open('analysis-2020accord/_e4_6b98_coherence.json','w'),indent=1)
