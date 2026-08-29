# -*- coding: utf-8 -*-
"""RETRACTED 2026-08-29 -- THIS METHOD IS INVALID AS WRITTEN.  Kept as a record.

It assumes every 2-byte-aligned pair in the calibration region is a u16 scalar.  It is not:
the region holds float32 values, packed structures and pointer tables.  Its apparently
stable ratchet hit 0xC4B58 (rho +0.783, 17/17 leave-one-out) takes values 1443, 1542, 12803,
14022, 14212, 60140, 60141 across builds -- jumping with no ordering, the signature of a
MANTISSA HALF -- and float32 reads of that region give -1.43e+26 and denormals at every
alignment.  Its grind hit 0xC40BC survives only 1 of 17 leave-one-out subsets, and both
verdicts flipped entirely on a two-route relabelling.

To make it valid, restrict candidates to cells VERIFIED as u16 cals -- by the knot-count
header, by a decompiled read site, or by sensible ordered values -- as
analysis-2020accord/verify/check_lever.py --record already does.

See cal_scan_stability.py for the leave-one-out analysis that condemned it.
"""

import glob, os, re, sys
import numpy as np
from scipy import stats
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'

# route -> (build, ratchet excess, grind excess), from the full-corpus scan
# HARD attributions only -- every one stated verbatim in memory or scored directly.
# r95 CORRECTED V102 -> V101 ("V101 flew it at 8x (7128) as route 0x95"); the earlier label
#   came from r95_v102_prereg.py, a pre-registration FOR V102 that USED route 95.
# r77 ADDED as V90 ("V90 flew as route 77") -- 97 windows, previously excluded as unknown.
# r21 / r23 / r97 DROPPED: filename-only inference, nothing states them.
DATA=[('r77',90,20.2,11.2),('r78',91,12.2,16.7),('r79',92,11.5,4.8),('r7e',96,31.0,15.7),
      ('r7f',96,39.2,6.4),('r81',98,243.7,9.9),('r82',99,237.2,17.8),('r85',100,58.7,10.8),
      ('r95',101,193.2,38.7),('r96',102,38.6,222.9),('r9e',103,38.1,286.9),('ra4',104,23.3,47.1),
      ('ra5',105,84.6,27.4),('ra6',106,29.0,11.8),('r1e',107,21.0,20.3),('r22',112,20.6,7.9),
      ('r24',122,38.3,15.5)]

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
