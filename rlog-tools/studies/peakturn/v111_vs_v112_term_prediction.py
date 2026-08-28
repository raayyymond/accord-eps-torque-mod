import numpy as np
from scipy import signal
FS=100.0; NW=256; RATE=4.7121
def term(d,knee,K1): return (K1/1024.0)*min(d*RATE*12.0/knee,1.0)
print("PREDICTION FROM THE K1 MECHANISM, testable on data already in hand.")
print("V111 (knee 600, K1 204) and V112 (knee 1800, K1 612) have the SAME small-signal gain,")
print("so the friction term is IDENTICAL at low rate and V112's is LARGER at high rate:")
for d in (3,10,20,31.8,60):
    a=term(d,600,204); b=term(d,1800,612)
    print("    %5.1f deg/s   V111 %.5f   V112 %.5f   ratio %.3f"%(d,a,b,b/a))
print("\n=> if the term drives the anti-damping, V112 should be WORSE than V111 at LARGE angle")
print("   (where |model| and rate are large) and EQUAL at small angle.\n")
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
            out.append((np.sqrt(np.sum(P[b])*(f[1]-f[0])),np.mean(np.abs(ang[sl])),np.std(rate[sl])))
    return np.array(out)
A=wins(['21']); B=wins(['22','23'])
print("6-9 Hz rate rms by ANGLE band -- V111 (route 21) vs V112 (routes 22+23)")
print("   |ang|       V111 n   p50    p90    max  |  V112 n   p50    p90    max  | p90 ratio")
for lo,hi in ((0,5),(5,20),(20,60),(60,400)):
    a=A[(A[:,1]>=lo)&(A[:,1]<hi)]; b=B[(B[:,1]>=lo)&(B[:,1]<hi)]
    if len(a)>=8 and len(b)>=8:
        print("   %3d-%3d    %5d %6.3f %6.3f %6.3f  | %5d %6.3f %6.3f %6.3f |  %5.2fx"
              %(lo,hi,len(a),np.percentile(a[:,0],50),np.percentile(a[:,0],90),a[:,0].max(),
                len(b),np.percentile(b[:,0],50),np.percentile(b[:,0],90),b[:,0].max(),
                np.percentile(b[:,0],90)/max(np.percentile(a[:,0],90),1e-9)))
    else:
        print("   %3d-%3d    n_V111=%d n_V112=%d -- too few"%(lo,hi,len(a),len(b)))
