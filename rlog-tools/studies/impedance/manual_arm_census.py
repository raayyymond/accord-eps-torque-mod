import numpy as np, glob, os
FS=100.0
SB=[(6,20),(20,35),(35,55),(55,80),(80,115)]
print("MANUAL-ARM CENSUS ACROSS THE WHOLE CACHED CORPUS (seconds, not engaged, moving)")
print("  route  %s   TOTAL man >=35 km/h"%" ".join("%8s"%("%d-%d"%s) for s in SB))
tot=np.zeros(len(SB))
rows=[]
for f in sorted(glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')):
    tag=os.path.basename(os.path.dirname(f))
    if os.path.basename(f)!=tag+'.npz': continue
    z=np.load(f,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v')): continue
    G=lambda k:np.asarray(z[k]).astype(float)
    lat,v=G('cc_lat'),G('cs_v')*3.6
    n=[((lat<0.5)&(v>=lo)&(v<hi)).sum()/FS for lo,hi in SB]
    tot+=np.array(n)
    rows.append((tag,n,sum(n[2:])))
for tag,n,hi in sorted(rows,key=lambda r:-r[2]):
    print("  %-5s  %s   %8.0f"%(tag," ".join("%8.0f"%x for x in n),hi))
print("  %-5s  %s   %8.0f"%("TOTAL"," ".join("%8.0f"%x for x in tot),sum(tot[2:])))
print("\n  => manual driving above 35 km/h across the ENTIRE corpus: %.0f s"%sum(tot[2:]))
print("     A within-build engaged-vs-manual test at 35-90 km/h needs ~120 s per arm.")
