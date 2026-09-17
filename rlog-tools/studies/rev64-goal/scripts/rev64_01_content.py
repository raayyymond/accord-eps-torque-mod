"""What is actually IN the two rev 6.4 routes, and does the corpus support the questions we need to ask?
Route 76 (rev 5) failed on both counts: 462 s engaged, zero samples >20 deg above 15 m/s.
"""
import math, numpy as np
CA='analysis-2020accord/_scratch/cache/tau/'
R={'6c':np.load(CA+'r6c_rev64_ident.npz'),'6d':np.load(CA+'r6d_rev64_ident.npz'),
   '76(rev5)':np.load(CA+'r76_v293_ident.npz',allow_pickle=True)}
SAT=lambda v: 19.3+546.0*np.exp(-v/3.01)

for tag,D in R.items():
    t=D['t_cs']; FS=1.0/float(np.median(np.diff(t)))
    act=D['cs_active'].astype(bool)
    sa=np.interp(t,D['t_cst'],D['sa_deg']); sr=np.interp(t,D['t_cst'],D['sr_deg'])
    v=np.interp(t,D['t_cst'],D['vego']); pr=np.interp(t,D['t_cst'],D['spress'])>0.5
    good=act&~pr
    def runs(mask,minlen=200):
        out,n,i=[],len(mask),0
        while i<n:
            if not mask[i]: i+=1; continue
            j=i
            while j+1<n and mask[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
            if j+1-i>minlen: out.append((i,j+1))
            i=j+1
        return out
    RU=runs(good); L=np.array([(b-a)/FS for a,b in RU]) if RU else np.array([0.])
    print("="*94)
    print(f"ROUTE {tag}   {len(t)/FS:.0f} s logged   engaged {act.sum()/FS:.0f} s   "
          f"pressed {(act&pr).sum()/FS:.0f} s   usable {good.sum()/FS:.0f} s")
    print(f"  usable runs: {len(RU)}   >=20s: {(L>=20).sum()}  >=40s: {(L>=40).sum()}  "
          f">=60s: {(L>=60).sum()}  longest {L.max():.0f}s")
    hs=good&(v>15.0)
    if hs.sum()>100:
        a=np.abs(sa[hs])
        print(f"  ABOVE 15 m/s ({hs.sum()/FS:.0f} s usable):  |angle| p50={np.percentile(a,50):.1f} "
              f"p90={np.percentile(a,90):.1f} p99={np.percentile(a,99):.1f} max={a.max():.1f} deg")
        for thr in (20,25,30,40,60):
            n=(a>thr).sum()
            print(f"      |angle| > {thr:2d} deg : {n:6d} samples = {n/FS:7.1f} s   {'<-- ENOUGH' if n/FS>2 else ''}")
        r=a/SAT(v[hs])
        print(f"      |angle|/sat(v):  p90={np.percentile(r,90):.2f} p99={np.percentile(r,99):.2f} max={r.max():.2f}"
              f"   frames above sat: {(r>1).sum()/FS:.1f} s")
    print(f"  speed spread (usable): " + " ".join(
        f"{lo}-{hi}:{((v>=lo)&(v<hi)&good).sum()/FS:.0f}s" for lo,hi in [(0,8),(8,15),(15,22),(22,28),(28,40)]))
    print()
