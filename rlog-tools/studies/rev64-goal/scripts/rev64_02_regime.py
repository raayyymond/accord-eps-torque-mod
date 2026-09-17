"""WHERE does the operator actually drive large angles and large angle RATES?
His notes 3/4/5 are all about large angle and large rate transients. If those live at
8-15 m/s rather than on the highway, that is where every fix must be aimed and measured.
"""
import math, numpy as np
CA='analysis-2020accord/_scratch/cache/tau/'
SAT=lambda v: 19.3+546.0*np.exp(-v/3.01)
K_BP=[2.,4.,6.,8.,10.,12.5,15.,17.5,20.,23.,28.]
K_V=[.0021,.0028,.0044,.0052,.0074,.0092,.0095,.0103,.0116,.0133,.0160]

def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t, FS=1.0/float(np.median(np.diff(t))),
                act=D['cs_active'].astype(bool),
                sa=np.interp(t,D['t_cst'],D['sa_deg']), sr=np.interp(t,D['t_cst'],D['sr_deg']),
                v=np.interp(t,D['t_cst'],D['vego']), pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                lad=D['cs_la_des'], laa=D['cs_la_act'])
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz')
# pool the two rev 6.4 routes
P={k:(np.concatenate([A[k],B[k]]) if isinstance(A[k],np.ndarray) else A[k]) for k in A}
P['FS']=A['FS']
good=P['act']&~P['pr']; FS=P['FS']
v,sa,sr=P['v'],P['sa'],P['sr']

print("="*100)
print("REV 6.4 POOLED (routes 6c+6d, %.0f s usable engaged) -- WHERE THE BIG ANGLES AND RATES ARE" % (good.sum()/FS))
print("="*100)
print(f"  {'speed':>11} {'time s':>8} | {'|angle| deg':^28} | {'|rate| deg/s':^28} | {'angle/sat':>10}")
print(f"  {'':>11} {'':>8} | {'p50':>6} {'p90':>6} {'p99':>7} {'max':>7} | {'p50':>6} {'p90':>6} {'p99':>7} {'max':>7} | {'p99':>10}")
for lo,hi in [(0,5),(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,34)]:
    m=good&(v>=lo)&(v<hi)
    if m.sum()<200: print(f"  {lo:5.1f}-{hi:<5.1f} {m.sum()/FS:8.0f} |  (too few)"); continue
    a=np.abs(sa[m]); r=np.abs(sr[m]); rs=a/SAT(v[m])
    print(f"  {lo:5.1f}-{hi:<5.1f} {m.sum()/FS:8.0f} | {np.percentile(a,50):6.1f} {np.percentile(a,90):6.1f} "
          f"{np.percentile(a,99):7.1f} {a.max():7.1f} | {np.percentile(r,50):6.1f} {np.percentile(r,90):6.1f} "
          f"{np.percentile(r,99):7.1f} {r.max():7.1f} | {np.percentile(rs,99):10.2f}")

print()
print("="*100)
print("HOLD-MAP DELIVERY at the angles he ACTUALLY drives  (tanh map / physics-linear reference)")
print("="*100)
print(f"  {'speed':>11} {'time s':>8} {'demand-wt ratio':>16} {'ratio at p99 angle':>20}   note")
for lo,hi in [(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,34)]:
    m=good&(v>=lo)&(v<hi)
    if m.sum()<200: continue
    x=np.abs(sa[m])/SAT(v[m])
    ratio=np.where(x>1e-6,np.tanh(np.maximum(x,1e-6))/np.maximum(x,1e-6),1.0)
    w=np.abs(P['lad'][m])+1e-6
    xp=np.percentile(np.abs(sa[m]),99)/np.median(SAT(v[m]))
    dw=np.average(ratio,weights=w)
    note='SATURATING' if dw<0.85 else ('mild' if dw<0.97 else '')
    print(f"  {lo:5.1f}-{hi:<5.1f} {m.sum()/FS:8.0f} {dw:16.3f} {math.tanh(xp)/xp:20.3f}   {note}")

print()
print("="*100)
print("WHERE THE BIG RATE TRANSIENTS ARE  (|steering rate| percentile by speed)")
print("="*100)
hi_rate = np.abs(sr) > np.percentile(np.abs(sr[good]), 97)
print(f"  97th-percentile |rate| threshold = {np.percentile(np.abs(sr[good]),97):.1f} deg/s")
tot=(good&hi_rate).sum()
for lo,hi in [(0,8),(8,15),(15,22),(22,34)]:
    m=good&hi_rate&(v>=lo)&(v<hi)
    print(f"    {lo:2d}-{hi:<2d} m/s : {m.sum()/FS:6.1f} s  = {m.sum()/max(tot,1)*100:5.1f}% of all large-rate frames")
