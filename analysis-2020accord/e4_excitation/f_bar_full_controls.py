import sys, numpy as np, json
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(1234)
NPS=512; WN=np.hanning(NPS); U=(WN**2).sum()
BANDS=[("0.5-3",(0.5,3.0)),("6-9",(6.0,9.0)),("9-12",(9.0,12.0)),("20-24",(20.0,24.0))]
OUT={}
for route in ["73","75","76","71"]:
    t,e4,y,m,meta=M.load(route)
    z=dict(np.load('_cache_r%s/r%s.npz'%(route,route),allow_pickle=True))
    tq=np.asarray(z["tq"],float)
    eng=m["eng"]; off=eng&~m["press"]
    for arm,msk in [("HANDS-OFF",off),("HANDS-ON",eng&m["press"])]:
        blks=[]
        for a,b in M.episodes(msk,t,5.2):
            s=a;n=int(20*M.FS)
            while s+NPS<=b:
                e=min(s+n,b)
                if e-s>=NPS: blks.append((s,e)); 
                s=e
        if len(blks)<4: continue
        E=[];T=[];bid=[];spd=[]
        for i,(a,b) in enumerate(blks):
            for s in range(a,b-NPS+1,NPS//2):
                x=e4[s:s+NPS]; q=tq[s:s+NPS]
                E.append(np.fft.rfft((x-x.mean())*WN)); T.append(np.fft.rfft((q-q.mean())*WN))
                bid.append(i); spd.append(m["v"][s:s+NPS].mean()*3.6)
        E=np.array(E);T=np.array(T);bid=np.array(bid);spd=np.array(spd)
        f=np.fft.rfftfreq(NPS,1/M.FS); nw=len(E); nb=len(blks)
        def st(idx,lo,hi,Tm=None):
            Tm=T if Tm is None else Tm; b=M.band(f,lo,hi)
            sxx=(np.abs(E[idx][:,b])**2).mean(0); syy=(np.abs(Tm[idx][:,b])**2).mean(0)
            sxy=(np.conj(E[idx][:,b])*Tm[idx][:,b]).mean(0)
            g=abs(sxy.sum())**2/max(sxx.sum()*syy.sum(),1e-30)
            H=sxy.sum()/max(sxx.sum(),1e-30)
            # group delay from the per-bin phase slope
            ph=np.unwrap(np.angle(sxy)); sl=np.polyfit(f[b]*2*np.pi,ph,1)[0]
            return g, abs(H), np.degrees(np.angle(H)), -sl*1000.0, float(np.sqrt(2*syy.sum()/(U*NPS)))
        rec={"route":route,"build":meta[0],"arm":arm,"nblocks":nb,"nwin":nw,
             "sec":float(sum(b-a for a,b in blks)/M.FS),
             "speed_kph":{"p10":float(np.percentile(spd,10)),"p50":float(np.percentile(spd,50)),"p90":float(np.percentile(spd,90))}}
        print("="*104)
        print("ROUTE %s (%s) %s  e4 -> TORSION BAR  blocks=%d win=%d %.0fs  speed p10/50/90 = %.0f/%.0f/%.0f km/h"%(
            route,meta[0],arm,nb,nw,rec["sec"],rec["speed_kph"]["p10"],rec["speed_kph"]["p50"],rec["speed_kph"]["p90"]))
        for nm,(lo,hi) in BANDS:
            g,H,ph,gd,ry=st(np.arange(nw),lo,hi)
            # shuffled null
            sh=[]
            for _ in range(300):
                p=rng.permutation(nw); bad=bid[p]==bid
                if bad.any(): p[bad]=np.roll(p,1)[bad]
                sh.append(st(np.arange(nw),lo,hi,Tm=T[p])[0])
            # block bootstrap
            bo=[];bH=[]
            for _ in range(400):
                pk=rng.integers(0,nb,nb); ii=np.concatenate([np.where(bid==q)[0] for q in pk])
                r=st(ii,lo,hi); bo.append(r[0]); bH.append(r[1])
            # split-half null on g2
            sp=[]
            for _ in range(300):
                p=rng.permutation(nb); h=set(p[:nb//2].tolist())
                iA=np.where(np.isin(bid,list(h)))[0]; iB=np.where(~np.isin(bid,list(h)))[0]
                if len(iA)<4 or len(iB)<4: continue
                sp.append(st(iA,lo,hi)[0]/max(st(iB,lo,hi)[0],1e-9))
            print("  %-6s g2=%.4f [%.4f,%.4f]  shufNULL p50 %.4f p95 %.4f  ratio-to-null %5.1fx | |H|=%.4f [%.3f,%.3f] bar-ct/e4-ct  phase %+7.1f deg  grpdelay %+6.1f ms | bar rms %8.3f"%(
                nm,g,np.percentile(bo,2.5),np.percentile(bo,97.5),np.median(sh),np.percentile(sh,95),
                g/max(np.median(sh),1e-9),H,np.percentile(bH,2.5),np.percentile(bH,97.5),ph,gd,ry))
            if sp: print("         split-half g2 ratio null (95%%): [%.2f, %.2f]"%(np.percentile(sp,2.5),np.percentile(sp,97.5)))
            rec[nm]={"g2":float(g),"g2_ci":[float(np.percentile(bo,2.5)),float(np.percentile(bo,97.5))],
                     "shuf_p50":float(np.median(sh)),"shuf_p95":float(np.percentile(sh,95)),
                     "H":float(H),"H_ci":[float(np.percentile(bH,2.5)),float(np.percentile(bH,97.5))],
                     "phase_deg":float(ph),"grpdelay_ms":float(gd),"bar_rms":float(ry),
                     "splithalf_null":[float(np.percentile(sp,2.5)),float(np.percentile(sp,97.5))] if sp else None}
        OUT["r%s|%s"%(route,arm)]=rec
json.dump(OUT,open('analysis-2020accord/_e4_to_bar_69hz.json','w'),indent=1)
print("\nwrote analysis-2020accord/_e4_to_bar_69hz.json")
