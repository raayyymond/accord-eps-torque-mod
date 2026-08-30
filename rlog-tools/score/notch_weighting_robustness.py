import sys, os
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import notch_vs_imu_profile as N

wf=np.arange(3.0,45.0,0.25)
curves=[np.interp(wf,f,c) for f,c in N.SP_curves()]
A=np.vstack(curves)
print('DOES V241\'s GEOMETRY SURVIVE A DIFFERENT WEIGHTING?  %d routes\n' % len(curves))

def search(w):
    best=None
    for zf in np.arange(20.0,34.01,0.25):
        for pf in np.arange(18.0,34.01,0.25):
            for r in (0.90,0.92,0.94,0.95,0.96,0.97,0.975,0.98):
                s,mx,lo=N.score(zf,pf,r,w,wf)
                if s is not None and (best is None or s<best[0]): best=(s,zf,pf,r)
    return best

WEIGHTS = {
 'MEDIAN (V241 used this)': np.clip(np.median(A,axis=0)-1,0,None),
 'MEAN'                   : np.clip(np.mean(A,axis=0)-1,0,None),
 'GEOMETRIC MEAN'         : np.clip(np.exp(np.mean(np.log(np.maximum(A,1e-6)),axis=0))-1,0,None),
 'WORST ROUTE (minimax)'  : np.clip(np.max(A,axis=0)-1,0,None),
 'p75 across routes'      : np.clip(np.percentile(A,75,axis=0)-1,0,None),
 'UNWEIGHTED (flat 22-30)': np.where((wf>=22)&(wf<30),1.0,0.0),
}
print('  %-26s %9s %9s %7s %10s' % ('weighting','zero Hz','pole Hz','r','cost'))
print('  '+'-'*66)
res={}
for name,w in WEIGHTS.items():
    if w.sum()<=0: continue
    b=search(w); res[name]=b[1:]
    mark=' <- V241' if (abs(b[1]-29.75)<.01 and abs(b[2]-22.50)<.01 and abs(b[3]-0.940)<.001) else ''
    print('  %-26s %9.2f %9.2f %7.3f %10.5f%s' % (name,b[1],b[2],b[3],b[0],mark))
print('  '+'-'*66)
same=sum(1 for v in res.values() if abs(v[0]-29.75)<.01 and abs(v[1]-22.50)<.01 and abs(v[2]-0.940)<.001)
print('  V241 geometry wins under %d of %d weightings' % (same,len(res)))
Z=np.array([v[0] for v in res.values()]); Pp=np.array([v[1] for v in res.values()])
print('  zero spread %.2f..%.2f   pole spread %.2f..%.2f' % (Z.min(),Z.max(),Pp.min(),Pp.max()))
print()
print('  a geometry that only wins under the MEDIAN is fitted to the median car.')
