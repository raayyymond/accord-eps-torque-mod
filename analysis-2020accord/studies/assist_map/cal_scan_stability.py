# -*- coding: utf-8 -*-
"""Cal-scan stability, vectorised.  Spearman == Pearson on ranks, so rank once and do the
whole permutation null as a matrix product -- the per-cell scipy loop was ~1000x slower and
timed out."""
import glob, os, re, sys
import numpy as np
from scipy.stats import rankdata
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
DATA=[('r77',90,20.2,11.2),('r78',91,12.2,16.7),('r79',92,11.5,4.8),('r7e',96,31.0,15.7),
      ('r7f',96,39.2,6.4),('r81',98,243.7,9.9),('r82',99,237.2,17.8),('r85',100,58.7,10.8),
      ('r95',101,193.2,38.7),('r96',102,38.6,222.9),('r9e',103,38.1,286.9),('ra4',104,23.3,47.1),
      ('ra5',105,84.6,27.4),('ra6',106,29.0,11.8),('r1e',107,21.0,20.3),('r22',112,20.6,7.9),
      ('r24',122,38.3,15.5)]
imgs={}
for p in glob.glob(os.path.join(R,'*plain_image*.bin')):
    m=re.search(r'_v(\d+)',os.path.basename(p).lower())
    if m: imgs.setdefault(int(m.group(1)),p)
arr={b:np.fromfile(imgs[b],dtype=np.uint8) for _,b,_,_ in DATA if b in imgs}
builds=sorted(arr); cand=[]
for LO,HI in [(0xC4000,0xCD000),(0xD6000,0xD8000),(0xE4000,0xE6000)]:
    st=np.stack([arr[b][LO:HI] for b in builds]); d=np.any(st!=st[0],axis=0)
    cand += [LO+o for o in range(0,HI-LO-1,2) if d[o] or d[o+1]]
X=np.zeros((len(DATA),len(cand)))
for j,off in enumerate(cand):
    for i,(_,b,_,_) in enumerate(DATA):
        a=arr[b]; X[i,j]=int(a[off])|(int(a[off+1])<<8)
keep=[j for j in range(len(cand)) if len(set(X[:,j]))>=3]
X=X[:,keep]; cells=np.array([cand[j] for j in keep])
yr=np.array([d[2] for d in DATA]); yg=np.array([d[3] for d in DATA])

def zr(a):
    r=np.apply_along_axis(rankdata,0,a).astype(float)
    return (r-r.mean(0))/(r.std(0)+1e-12)

def survivors(Xs,y,seed,perm=400):
    Z=zr(Xs); n=len(y)
    zy=(rankdata(y)-rankdata(y).mean())/(rankdata(y).std()+1e-12)
    rho=(Z*zy[:,None]).sum(0)/n
    rng=np.random.default_rng(seed)
    P=np.stack([rng.permutation(zy) for _ in range(perm)])       # perm x n
    mx=np.max(np.abs(P@Z/n),axis=1)
    thr=np.percentile(mx,95)
    return set(cells[np.abs(rho)>thr]), thr, rho

print('LEAVE-ONE-ROUTE-OUT stability, %d cells, %d routes\n'%(len(cells),len(DATA)))
for nm,y in (('RATCHET',yr),('GRIND',yg)):
    full,thr,rho=survivors(X,y,3)
    counts={}
    for i in range(len(DATA)):
        m=[k for k in range(len(DATA)) if k!=i]
        s,_,_=survivors(X[m,:],y[m],10+i,300)
        for c in s: counts[c]=counts.get(c,0)+1
    print('%s  threshold %.3f  full-sample survivors: %s'
          %(nm,thr,sorted('0x%05X'%c for c in full) or 'none'))
    if counts:
        print('  cell        survives in N of %d leave-one-out subsets'%len(DATA))
        for c,n in sorted(counts.items(), key=lambda kv:-kv[1])[:5]:
            print('    0x%05X    %2d / %d%s'%(c,n,len(DATA),'   <- full-sample hit' if c in full else ''))
    else:
        print('  NO cell survives in ANY leave-one-out subset')
    print()
