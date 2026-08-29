# -*- coding: utf-8 -*-
"""Data-driven lever search: does ANY cal that varied track the measured ratchet?

Every lever so far came from reasoning about structure.  With 18 build-attributed routes and
each build's image on disk, the complementary search is available: for every 16-bit cal that
actually VARIES across those builds, correlate its value against the route's ratchet excess.

MULTIPLE COMPARISONS ARE THE WHOLE DIFFICULTY.  With dozens of varying cells and n=18,
spurious hits are guaranteed, so the control is a PERMUTATION null: shuffle the route->build
mapping many times, recompute the best |rho| over ALL cells each time, and keep only cells
whose real |rho| beats the 95th percentile of that maximum.  That controls the family-wise
error rate rather than the per-test rate.
"""
import glob, os, re, sys
import numpy as np
from scipy import stats
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'

# route -> (build, ratchet excess, grind excess), from the full-corpus scan
DATA=[('r78',91,12.2,16.7),('r79',92,11.5,4.8),('r7e',96,31.0,15.7),('r7f',96,39.2,6.4),
      ('r81',98,243.7,9.9),('r82',99,237.2,17.8),('r85',100,58.7,10.8),('r95',102,193.2,38.7),
      ('r96',102,38.6,222.9),('r9e',103,38.1,286.9),('ra4',104,23.3,47.1),('ra5',105,84.6,27.4),
      ('ra6',106,29.0,11.8),('r1e',107,21.0,20.3),('r21',111,27.2,9.1),('r22',112,20.6,7.9),
      ('r97',112,4.4,2.2),('r24',122,38.3,15.5)]

imgs={}
for p in glob.glob(os.path.join(R,'*plain_image*.bin')):
    m=re.search(r'_v(\d+)',os.path.basename(p).lower())
    if m: imgs.setdefault(int(m.group(1)),p)
builds=sorted({b for _,b,_,_ in DATA})
missing=[b for b in builds if b not in imgs]
if missing: print('no image for builds: %s'%missing)
arr={b:np.fromfile(imgs[b],dtype=np.uint8) for b in builds if b in imgs}
DATA=[d for d in DATA if d[1] in arr]
print('routes with an image: %d over %d builds'%(len(DATA),len({d[1] for d in DATA})))

# every u16 cal in the calibration region that VARIES across these builds
# The first pass covered only 0xC4000-0xCD000.  The 278 bytes this kit has changed also span
# 0xD7000 (the damper records -- V158's own lever) and 0xE4000/0xE5000 (V38's arbitration
# setpoint limits), so those were invisible to it.  Scan every region that has ever changed.
REGIONS=[(0xC4000,0xCD000),(0xD6000,0xD8000),(0xE4000,0xE6000)]
cand=[]
for LO,HI in REGIONS:
    stack=np.stack([arr[b][LO:HI] for b in builds if b in arr])
    diff=np.any(stack!=stack[0],axis=0)
    for off in range(0,HI-LO-1,2):
        if diff[off] or diff[off+1]: cand.append(LO+off)
print('u16 cells varying across these builds: %d  (regions %s)'%(len(cand),
      ' '.join('0x%05X-0x%05X'%r for r in REGIONS)))

y_r=np.array([d[2] for d in DATA],float)
y_g=np.array([d[3] for d in DATA],float)
bl=[d[1] for d in DATA]
X=np.zeros((len(DATA),len(cand)))
for j,off in enumerate(cand):
    for i,b in enumerate(bl):
        a=arr[b]; X[i,j]=int(a[off])|(int(a[off+1])<<8)
keep=[j for j in range(len(cand)) if len(set(X[:,j]))>=3]
X=X[:,keep]; cells=[cand[j] for j in keep]
print('cells with >=3 distinct values: %d'%len(cells))

def best_rho(y):
    out=[]
    for j in range(X.shape[1]):
        r,_=stats.spearmanr(X[:,j],y)
        out.append(0.0 if not np.isfinite(r) else r)
    return np.array(out)

for nm,y in (('RATCHET',y_r),('GRIND',y_g)):
    rho=best_rho(y)
    rng=np.random.default_rng(7)
    maxnull=[]
    for _ in range(400):
        yp=rng.permutation(y)
        maxnull.append(np.max(np.abs(best_rho(yp))))
    thr=float(np.percentile(maxnull,95))
    hits=[(cells[j],rho[j]) for j in np.argsort(-np.abs(rho)) if abs(rho[j])>thr]
    print('\n%s  family-wise 95%% threshold on |rho| = %.3f'%(nm,thr))
    print('  strongest cells:')
    for j in np.argsort(-np.abs(rho))[:6]:
        mark=' *** SURVIVES ***' if abs(rho[j])>thr else ''
        print('    0x%05X  rho %+.3f%s'%(cells[j],rho[j],mark))
    print('  cells surviving family-wise control: %d'%len(hits))
