# -*- coding: utf-8 -*-
"""HOW MUCH DRIVING ACTUALLY SITS WHERE V236's CAP BINDS?

V236 lowers the assist map's slope cap, and I have been telling the operator it costs "25 % less assist
at small inputs". But the cap binds only over X 0-100 of the map's axis:

    X   0   25   60  100  150  250  450  900  1800  4150
    Y   0  154  338  460  549  635  702  766   824   857
    cap 2.000 BINDS 3 of 9 segments, all inside X 0-100

The map is fed by the driver torque sensor (gp-0x4f60, clamped +-8192). So the question is what
fraction of real driving has |torque| under 100 -- and that is measurable from cs_tq on every route.

SCALE CHECK FIRST: if cs_tq and the map's X axis are the same units, cs_tq's observed maximum should
land near the map's last knot (4150) and inside the clamp (8192). Checked below rather than assumed.
"""
import glob, numpy as np, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
X=[0,25,60,100,150,250,450,900,1800,4150]
ROUTES=['r77','r78','r7e','r95','r96','r9e','ra4','ra5','ra6','r1e','r21','r22','r24']
print('='*100)
print('  SCALE CHECK -- does cs_tq live on the map\'s X axis?')
print('='*100)
print()
print('  %-6s %8s %8s %8s %8s %8s' % ('route','p50','p90','p99','max','n_eng'))
allq=[]
for tag in ROUTES:
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): continue
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'cs_tq','cc_lat'} <= ks: continue
    q=np.abs(np.asarray(z['cs_tq']).astype(float))
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    a=q[m]
    if len(a)<500: continue
    allq.append(a)
    pc=np.percentile(a,[50,90,99])
    print('  %-6s %8.0f %8.0f %8.0f %8.0f %8d' % (tag,pc[0],pc[1],pc[2],a.max(),len(a)))
A=np.concatenate(allq)
print()
print('  pooled n=%d   max %.0f   vs map last knot %d, clamp 8192' % (len(A),A.max(),X[-1]))
print('  => %s' % ('scale is CONSISTENT: the observed max lands between the last knot and the clamp.'
                   if X[-1]*0.5 < A.max() < 8192*1.2 else
                   'SCALE MISMATCH -- cs_tq is not on the map axis; the exposure below is NOT valid.'))
print()
print('='*100)
print('  EXPOSURE -- fraction of ENGAGED driving inside each map segment')
print('='*100)
print()
print('  %-14s %10s %10s   %s' % ('segment','fraction','cumul','cap binds here?'))
cum=0.0
for i in range(len(X)-1):
    lo,hi=X[i],X[i+1]
    f=float(np.mean((A>=lo)&(A<hi))); cum+=f
    binds = hi<=100
    print('  %5d - %-6d %9.1f%% %9.1f%%   %s' % (lo,hi,100*f,100*cum,'YES -- V236 cuts assist here' if binds else ''))
print('  %5d +      %9.1f%% %9.1f%%' % (X[-1],100*float(np.mean(A>=X[-1])),100*(cum+float(np.mean(A>=X[-1])))))
print()
binds=float(np.mean(A<100))
print('  TOTAL ENGAGED TIME WITH |torque| < 100, i.e. where V236 reduces assist: %.1f %%' % (100*binds))
print()
if binds>0.5:
    print('  => MOST driving sits in the capped region. The 25 %% assist cut is felt most of the time,')
    print('     and the cost is as expensive as it sounds.')
elif binds>0.15:
    print('  => a SUBSTANTIAL minority of driving is in the capped region. Real, but not constant.')
else:
    print('  => only a SMALL fraction of driving is in the capped region, so the effort penalty is')
    print('     confined to a sliver of operation and the trade is cheaper than "25 %% less assist".')
