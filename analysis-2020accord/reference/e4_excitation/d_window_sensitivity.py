import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(11)

t,e4,y,m,meta=M.load("73")
eng=m["eng"]; off=eng&~m["press"]

def run(msk,NPS,label,sel=None):
    WN=np.hanning(NPS); U=(WN**2).sum()
    blks=[]
    for a,b in M.episodes(msk,t,NPS/M.FS+0.1):
        s=a; n=int(20*M.FS)
        while s+NPS<=b:
            e=min(s+n,b)
            if e-s>=NPS: blks.append((s,e))
            s=e
    X=[];Y=[];bid=[]
    for i,(a,b) in enumerate(blks):
        for s in range(a,b-NPS+1,NPS//2):
            xs=e4[s:s+NPS]; ys=y[s:s+NPS]
            X.append(np.fft.rfft((xs-xs.mean())*WN)); Y.append(np.fft.rfft((ys-ys.mean())*WN)); bid.append(i)
    X=np.array(X);Y=np.array(Y);bid=np.array(bid); f=np.fft.rfftfreq(NPS,1/M.FS); nw=len(X); nb=len(blks)
    keep=np.arange(nw)
    if sel is not None:
        b69=M.band(f,6,9); p=(np.abs(X[:,b69])**2).sum(1)
        keep=np.where(p>=np.percentile(p,sel))[0]
    def po(idx): return (np.abs(X[idx])**2).mean(0),(np.abs(Y[idx])**2).mean(0),(np.conj(X[idx])*Y[idx]).mean(0)
    def st(S,lo,hi):
        b=M.band(f,lo,hi); sxx=S[0][b].sum(); syy=S[1][b].sum(); sxy=S[2][b].sum()
        c=float(np.mean(M.interp_corr(f[b])))
        return (abs(sxy)**2/max(sxx*syy,1e-30), abs(sxy)/max(sxx,1e-30)/np.sqrt(c),
                float(np.sqrt(2*sxx/(U*NPS))), float(np.sqrt(2*syy/(U*NPS))/np.sqrt(c)))
    S=po(keep)
    print("  %-34s NPS=%4d df=%.3f  blocks=%2d win=%3d(kept %3d)"%(label,NPS,M.FS/NPS,nb,nw,len(keep)))
    out={}
    for nm,(lo,hi) in [("0.5-3",(0.5,3.0)),("4.5-6",(4.5,6.0)),("6-9",(6.0,9.0)),("20-24",(20.0,24.0))]:
        g,h,ex,oy=st(S,lo,hi)
        # shuffled H1 null
        sh=[]
        for _ in range(200):
            p=rng.permutation(len(keep)); idx=keep[p]; bad=bid[idx]==bid[keep]
            if bad.any(): idx[bad]=np.roll(idx,1)[bad]
            sh.append(st(((np.abs(X[keep])**2).mean(0),(np.abs(Y[idx])**2).mean(0),(np.conj(X[keep])*Y[idx]).mean(0)),lo,hi)[1])
        # block bootstrap
        bo=[]
        for _ in range(400):
            pk=rng.integers(0,nb,nb); ii=np.concatenate([np.where(bid[keep]==q)[0] for q in pk])
            if len(ii)<4: continue
            bo.append(st(po(keep[ii]),lo,hi)[1])
        print("      %-6s g2=%.4f  H1=%.4f [%.3f,%.3f]  shufH1 p50 %.3f p95 %.3f | ex_rms %7.2f  out_rms %8.2f"%(
            nm,g,h,np.percentile(bo,2.5),np.percentile(bo,97.5),np.median(sh),np.percentile(sh,95),ex,oy))
        out[nm]=(g,h,ex,oy)
    return out

print("ROUTE 73 (V88), SIGNED gp-0x6b98, window-length + selection sensitivity")
for NPS in (256,512,1024):
    run(off,NPS,"HANDS-OFF, all windows")
run(off,512,"HANDS-OFF, top-25%% 6-9Hz excitation",sel=75)
run(eng,512,"ALL ENGAGED, all windows")
