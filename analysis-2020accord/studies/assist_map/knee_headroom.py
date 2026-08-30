# -*- coding: utf-8 -*-
"""Is the grind's confirmed lever SATURATED at the flying value, or is there headroom?

0xC40BC, the Coulomb relay knee, is the ONLY cell surviving a family-wise-controlled scan of
94 varying cals against the grind (rho -0.715), and it is independently the cell structural
reasoning identified (rho -0.69, p 0.039).  Higher knee => lower grind.

The flying build V122 sits at 3000, the highest value in the corpus.  If the relationship is
still falling at 3000 there is headroom; if it has flattened, the lever is spent.  That is a
shape question, not a correlation question, so plot the actual values.

Mechanism, for interpreting the shape:
    fVar13 = clamp(POL * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)
Raising the knee widens the LINEAR (viscous) region and shrinks the Coulomb one; saturation
moves to |gp-0x6abc| >= knee/12, so 3000 saturates at 250 counts.
"""
import glob, os, re, sys
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
DATA=[('r78',91,12.2,16.7),('r79',92,11.5,4.8),('r7e',96,31.0,15.7),('r7f',96,39.2,6.4),
      ('r81',98,243.7,9.9),('r82',99,237.2,17.8),('r85',100,58.7,10.8),('r95',101,193.2,38.7)  # r95 CORRECTED V102 -> V101 (8x/7128, Lever B removed); matches cal_association_scan.py + cal_scan_stability.py, which were fixed earlier,
      ('r96',102,38.6,222.9),('r9e',103,38.1,286.9),('ra4',104,23.3,47.1),('ra5',105,84.6,27.4),
      ('ra6',106,29.0,11.8),('r1e',107,21.0,20.3),('r21',111,27.2,9.1),('r22',112,20.6,7.9),
      ('r97',112,4.4,2.2),('r24',122,38.3,15.5)]
imgs={}
for p in glob.glob(os.path.join(R,'*plain_image*.bin')):
    m=re.search(r'_v(\d+)',os.path.basename(p).lower())
    if m: imgs.setdefault(int(m.group(1)),p)
def u16(a,o): return int(a[o])|(int(a[o+1])<<8)
rows=[]
for tag,b,rat,grd in DATA:
    if b not in imgs: continue
    a=np.fromfile(imgs[b],dtype=np.uint8)
    rows.append((u16(a,0xC40BC),b,tag,rat,grd))
rows.sort()
print('%-8s %-7s %-7s %-11s %-11s %s'%('knee','build','route','GRIND exc','RATCHET exc','saturates at |6abc|'))
for k,b,t,rat,grd in rows:
    print('%-8d V%-6d %-7s %-11.1f %-11.1f %.0f ct'%(k,b,t,grd,rat,k/12.0))
ks=sorted({r[0] for r in rows})
print('\n%-8s %-7s %-11s %s'%('knee','n','grind med','ratchet med'))
for k in ks:
    g=[r[4] for r in rows if r[0]==k]; rr=[r[3] for r in rows if r[0]==k]
    print('%-8d %-7d %-11.1f %.1f'%(k,len(g),np.median(g),np.median(rr)))
print()
print('SHAPE: is it still falling at the flying value (3000)?')
hi=[r for r in rows if r[0]>=1800]
lo=[r for r in rows if r[0]<=600]
if hi and lo:
    print('  knee <= 600  : grind median %.1f  (n=%d)'%(np.median([r[4] for r in lo]),len(lo)))
    print('  knee >= 1800 : grind median %.1f  (n=%d)'%(np.median([r[4] for r in hi]),len(hi)))
mid=[r for r in rows if 1800<=r[0]<3000]; top=[r for r in rows if r[0]>=3000]
if mid and top:
    print('  knee 1800-2999: grind median %.1f (n=%d)'%(np.median([r[4] for r in mid]),len(mid)))
    print('  knee >= 3000  : grind median %.1f (n=%d)'%(np.median([r[4] for r in top]),len(top)))
    print('  => %s'%('STILL FALLING at 3000 -- headroom may exist'
          if np.median([r[4] for r in top])<np.median([r[4] for r in mid])
          else 'FLAT or rising at 3000 -- the lever looks spent'))
