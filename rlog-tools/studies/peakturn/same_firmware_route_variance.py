import numpy as np
from scipy import signal
FS=100.0; NW=256
def wins(routes):
    out=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,lat,v,ang=[G(k) for k in ('cs_rate','cc_lat','cs_v','ang')]
        m=(lat>0.5)&(v>1.0)
        for a in range(0,len(rate)-NW,NW//2):
            sl=slice(a,a+NW)
            if m[sl].mean()<0.99: continue
            x=rate[sl]-np.mean(rate[sl])
            f,P=signal.welch(x,FS,nperseg=NW,noverlap=NW//2)
            b=(f>=6)&(f<=9)
            out.append((np.sqrt(np.sum(P[b])*(f[1]-f[0])),np.mean(np.abs(ang[sl]))))
    return np.array(out)
rng=np.random.default_rng(0)
print("THE CONTROL: r22 and r23 are BOTH V112 -- identical firmware, different drives.")
print("If they differ as much as V111-vs-V112 did, the 'residue' is route variation.\n")
sets={'r21 (V111)':wins(['21']),'r22 (V112)':wins(['22']),'r23 (V112)':wins(['23'])}
print("   |ang| band      %s"%"  ".join("%-12s"%k for k in sets))
for lo,hi in ((0,5),(5,20),(20,60)):
    cells=[]
    for k,A in sets.items():
        a=A[(A[:,1]>=lo)&(A[:,1]<hi),0]
        cells.append("%5d p90 %5.3f"%(len(a),np.percentile(a,90)) if len(a)>=8 else "     too few")
    print("   %3d-%3d        %s"%(lo,hi,"  ".join(cells)))
print("\n  SAME-FIRMWARE ratio r23/r22 (both V112) vs the cross-build ratio V112/V111:")
for lo,hi in ((0,5),(5,20),(20,60)):
    a=sets['r22 (V112)']; b=sets['r23 (V112)']; c=sets['r21 (V111)']
    aa=a[(a[:,1]>=lo)&(a[:,1]<hi),0]; bb=b[(b[:,1]>=lo)&(b[:,1]<hi),0]; cc=c[(c[:,1]>=lo)&(c[:,1]<hi),0]
    if min(len(aa),len(bb),len(cc))<8: continue
    same=np.percentile(bb,90)/np.percentile(aa,90)
    bs=[np.percentile(rng.choice(bb,len(bb)),90)/max(np.percentile(rng.choice(aa,len(aa)),90),1e-9) for _ in range(4000)]
    pooled=np.concatenate([aa,bb])
    cross=np.percentile(pooled,90)/np.percentile(cc,90)
    print("   %3d-%3d   SAME-FW r23/r22 = %5.2fx  [%.2f, %.2f]   |  cross-build V112/V111 = %5.2fx"
          %(lo,hi,same,np.percentile(bs,2.5),np.percentile(bs,97.5),cross))
print("\n  => if the same-firmware ratio brackets the cross-build ratio, the difference is DRIVE,")
print("     not FIRMWARE, and the 0-5 deg 'residue' dissolves.")
