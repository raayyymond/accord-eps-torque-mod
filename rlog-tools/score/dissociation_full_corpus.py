# -*- coding: utf-8 -*-
"""The grind/ratchet DISSOCIATION, re-tested on the full corpus with build attribution.

The load-bearing result of this session is that the grind falls monotonically post-V102
(rho -0.94, p 0.005) while the ratchet does not move (rho -0.14, p 0.787).  It rested on
9 routes, 5 of them post-V102.  The corpus turns out to hold 19, and build attribution for
the new ones is recoverable from tool/doc names and from memory's own statements
("V98 FLEW (route 0x81)", "V91 (route 78) + V92 (route 79)").

r77 is left OUT: its candidates span V31-V91 and nothing disambiguates them.  Guessing an
attribution to gain a data point is exactly how a spurious trend gets manufactured.
"""
import os, sys
import numpy as np
from scipy import signal, stats
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)

# (route, build, source of attribution)
ROUTES = [
    ('r78',  91, 'session'), ('r79',  92, 'memory: V91 route78 + V92 route79'),
    ('r7e',  96, 'session'), ('r7f',  96, 'session'),
    ('r80',  97, 'SCORING-2026-08-12-v97-route80.md'),
    ('r81',  98, 'memory: V98 FLEW (route 0x81)'),
    ('r82',  99, 'v99_r82_score.py'),
    ('r85', 100, 'score_r85_v100.py'),
    ('r95', 102, 'r95_v102_prereg.py'), ('r96', 102, 'session'),
    ('r9e', 103, 'SCORING-2026-08-20-v103-route9e.md'),
    ('ra4', 104, 'session'), ('ra5', 105, 'ra5 tooling'),
    ('ra6', 106, 'session'), ('r1e', 107, 'session'),
    ('r21', 111, 'r21 tooling'),
    ('r22', 112, 'session'), ('r23', 112, 'r23 tooling'), ('r97', 112, 'r97 tooling'),
    ('r24', 122, 'session'),
]

def runs(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): return []
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(v),len(a)); lat,kmh,a=lat[:n],v[:n]*3.6,a[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    out=[]
    for i,j in zip(st,en):
        for k in range(i,j-NPS+1,NPS//2):
            w=a[k:k+NPS]
            if np.std(w)>0: out.append(w)
    return out

def exc_of(segs,band):
    acc,f=[],None
    for s in segs:
        f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    M=np.median(np.asarray(acc),0)
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use&=~((f>=lo)&(f<=hi))
    if use.sum()<6: return np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    w=(f>=band[0])&(f<=band[1])
    return float(np.max(M[w]/bg[w]))

print('%-7s %-7s %-9s %-11s %-11s %s'%('route','build','windows','RATCHET','GRIND','attribution'))
rows=[]
for tag,bld,src in ROUTES:
    s=runs(tag)
    if len(s)<6:
        print('%-7s V%-6d %-9d  -- too few windows'%(tag,bld,len(s))); continue
    r=exc_of(s,RATCHET); g=exc_of(s,GRIND)
    print('%-7s V%-6d %-9d %-11.1f %-11.1f %s'%(tag,bld,len(s),r,g,src))
    rows.append((bld,r,g))
b=np.array([x[0] for x in rows],float)
r=np.array([x[1] for x in rows],float); g=np.array([x[2] for x in rows],float)
print('\n  n = %d routes with attribution (was 9)'%len(rows))
for nm,y in (('RATCHET',r),('GRIND',g)):
    rho,p=stats.spearmanr(b,y)
    m=b>=102
    rho2,p2=stats.spearmanr(b[m],y[m])
    print('  %-8s full-range rho %+.2f p %.3f    post-V102 rho %+.2f p %.3f  (n=%d)'
          %(nm,rho,p,rho2,p2,m.sum()))
print('\n  earlier result at n=9: grind post-V102 rho -0.94 p 0.005 ; ratchet -0.14 p 0.787')
