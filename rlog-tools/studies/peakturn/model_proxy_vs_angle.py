import numpy as np
FS=100.0
for r in ('22','23'):
    z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    G=lambda k:np.asarray(z[k]).astype(float)
    b7=np.asarray(z['raw14_b7']).astype(int)
    ang=np.abs(G('ang')); lat=G('cc_lat'); v=G('cs_v'); cmd=np.abs(G('co_tqcan'))
    # raw14 is off-by-one vs the row index -- the kit's recorded trap. Use raw14_t pairing.
    n=min(len(b7),len(ang))
    b7=b7[:n]; ang=ang[:n]; lat=lat[:n]; v=v[:n]; cmd=cmd[:n]
    m=(lat>0.5)&(v>1.0)
    print("\n=== route %s : 0x14A byte7 bit duties vs |ang|, engaged (n=%d) ==="%(r,m.sum()))
    print("  bit | overall |  ang<5   5-20   20-60  60-400  | trend")
    for bit in range(8):
        d=((b7>>bit)&1).astype(float)
        cells=[]
        for lo,hi in ((0,5),(5,20),(20,60),(60,400)):
            s=m&(ang>=lo)&(ang<hi)
            cells.append(d[s].mean() if s.sum()>200 else np.nan)
        tr=""
        if all(np.isfinite(c) for c in cells):
            if cells[3]>cells[0]*1.5: tr="RISES with angle"
            elif cells[3]<cells[0]*0.67: tr="FALLS with angle"
        print("   b%d  | %7.4f | %6.4f %6.4f %6.4f %6.4f | %s"
              %(bit,d[m].mean(),*cells,tr))
