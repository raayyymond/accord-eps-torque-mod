"""Orchestrator crux check on ROUTE 76 (rev 5 flight data).

Question the code comment answers with BELIEF and I want EVIDENCE for:
  "angles a 3 m/s^2 planner never reaches there [above 15 m/s], so the saturated
   tail is unexercised BELIEF above 15 m/s"
If the planner DOES reach past sat(v), the saturated tail is exercised and the
feedforward under-delivers exactly where the operator reports the caster symptom.
"""
import math
import numpy as np

D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t   = D['t_cs']; act = D['cs_active'].astype(bool)
la_des = D['cs_la_des']; la_act = D['cs_la_act']
ff = D['cs_f']; pp = D['cs_p']; ii = D['cs_i']; out = D['cs_out']
# steering angle & speed are on t_cst -- resample onto t_cs
sa = np.interp(t, D['t_cst'], D['sa_deg'])
v  = np.interp(t, D['t_cst'], D['vego'])
sr = np.interp(t, D['t_cst'], D['sr_deg'])

SAT_A, SAT_B, SAT_C = (19.3, 546.0, 3.01)
sat = SAT_A + SAT_B*np.exp(-v/SAT_C)

eng = act & (v > 5.0)
print(f"engaged frames: {eng.sum()} of {len(t)}  ({eng.sum()/len(t)*100:.1f}%)")
print(f"speed range engaged: {v[eng].min():.1f} - {v[eng].max():.1f} m/s")

print()
print("="*84)
print("A. MEASURED steering angle vs lateral accel  (engaged, |rate|<20 deg/s, quasi-static)")
print("="*84)
qs = eng & (np.abs(sr) < 20.0)
print(f"{'speed bin':>12} {'n':>7} | median |sw angle| at each |a_y_des| band (deg)")
print(f"{'':>12} {'':>7} | {'0.5-1':>7} {'1-2':>7} {'2-3':>7} {'3-4':>7} {'4+':>7}")
for lo, hi in [(8,12.5),(12.5,17.5),(17.5,22),(22,30)]:
    m = qs & (v>=lo) & (v<hi)
    row = []
    for alo, ahi in [(0.5,1),(1,2),(2,3),(3,4),(4,99)]:
        mm = m & (np.abs(la_des)>=alo) & (np.abs(la_des)<ahi)
        row.append(f"{np.median(np.abs(sa[mm])):7.1f}" if mm.sum()>=30 else f"{'n<30':>7}")
    print(f"{lo:5.1f}-{hi:<5.1f} {m.sum():7d} | " + " ".join(row))

print()
print("="*84)
print("B. IS THE SATURATED TAIL EXERCISED?  |angle| relative to sat(v), engaged, v>15 m/s")
print("="*84)
hs = eng & (v > 15.0)
r = np.abs(sa[hs]) / sat[hs]
print(f"n = {hs.sum()} engaged frames above 15 m/s   (sat median {np.median(sat[hs]):.1f} deg)")
for thr in [0.5, 1.0, 1.5, 2.0, 3.0]:
    f = (r > thr).mean()
    print(f"  |angle| > {thr:3.1f} x sat : {f*100:6.2f} %  of engaged highway frames  ({int((r>thr).sum()):7d} frames, {(r>thr).sum()/100.0:7.1f} s)")
print()
print(f"  percentiles of |angle|/sat : " + "  ".join(f"p{p}={np.percentile(r,p):.2f}" for p in [50,75,90,95,99,99.9]))
print(f"  percentiles of |angle| deg : " + "  ".join(f"p{p}={np.percentile(np.abs(sa[hs]),p):.1f}" for p in [50,75,90,95,99,99.9]))
print(f"  percentiles of |a_y_des|   : " + "  ".join(f"p{p}={np.percentile(np.abs(la_des[hs]),p):.2f}" for p in [50,75,90,95,99,99.9]))

print()
print("="*84)
print("C. HOW MUCH HOLD TORQUE THE MAP GIVES UP AT THE ANGLES ACTUALLY DRIVEN")
print("="*84)
print("   (delivered tanh map / linear-in-angle extrapolation of the same slope)")
ratio = np.ones_like(r)
nz = np.abs(sa[hs]) > 1e-6
x = np.abs(sa[hs])[nz]/sat[hs][nz]
ratio[nz] = np.tanh(x)/x
w = np.abs(la_des[hs])              # weight by how much lateral demand is at stake
print(f"  unweighted mean ratio over engaged highway frames : {ratio.mean():.3f}")
print(f"  DEMAND-WEIGHTED mean ratio (weight=|a_y_des|)     : {np.average(ratio, weights=w):.3f}")
for alo, ahi in [(0,1),(1,2),(2,3),(3,99)]:
    mm = (np.abs(la_des[hs])>=alo)&(np.abs(la_des[hs])<ahi)
    if mm.sum()>=30:
        print(f"    |a_y_des| {alo}-{ahi}: n={mm.sum():7d}  mean ratio {ratio[mm].mean():.3f}  "
              f"median |angle| {np.median(np.abs(sa[hs])[mm]):5.1f} deg")

print()
print("="*84)
print("D. WHO IS ACTUALLY SUPPLYING THE TORQUE vs ANGLE  (the smoking gun)")
print("="*84)
print("   If the FF saturates, P and I must cover the rest -- and I is slow.")
print(f"{'|sw angle| deg':>16} {'n':>7} {'|out|':>8} {'|ff|':>8} {'|P|':>8} {'|I|':>8} {'ff/out':>8} {'I/out':>8}")
hw = eng & (v>15.0)
for lo,hi in [(0,5),(5,10),(10,15),(15,20),(20,30),(30,40),(40,60),(60,200)]:
    m = hw & (np.abs(sa)>=lo) & (np.abs(sa)<hi)
    if m.sum()<50: 
        print(f"{lo:7d}-{hi:<8d} {m.sum():7d}   (too few)")
        continue
    ao,af,ap,ai = np.mean(np.abs(out[m])),np.mean(np.abs(ff[m])),np.mean(np.abs(pp[m])),np.mean(np.abs(ii[m]))
    print(f"{lo:7d}-{hi:<8d} {m.sum():7d} {ao:8.4f} {af:8.4f} {ap:8.4f} {ai:8.4f} {af/max(ao,1e-9):8.3f} {ai/max(ao,1e-9):8.3f}")

print()
print("="*84)
print("E. TRACKING GAIN vs ANGLE  (does it fall off where the map saturates?)")
print("="*84)
print(f"{'|sw angle| deg':>16} {'n':>7} {'slope act/des':>14} {'r':>7}")
for lo,hi in [(0,5),(5,10),(10,15),(15,20),(20,30),(30,40),(40,60),(60,200)]:
    m = hw & (np.abs(sa)>=lo) & (np.abs(sa)<hi) & np.isfinite(la_des) & np.isfinite(la_act)
    if m.sum()<200:
        print(f"{lo:7d}-{hi:<8d} {m.sum():7d}   (too few)"); continue
    xd, ya = la_des[m], la_act[m]
    slope = float(np.dot(xd,ya)/max(np.dot(xd,xd),1e-12))
    rr = float(np.corrcoef(xd,ya)[0,1])
    print(f"{lo:7d}-{hi:<8d} {m.sum():7d} {slope:14.3f} {rr:7.3f}")
