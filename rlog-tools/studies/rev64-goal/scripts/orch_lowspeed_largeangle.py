"""Route 76 has NO large-angle highway content. But it DOES have large angles at 8-15 m/s.
sat(v) is large at low speed (39 deg at 10 m/s) but angles there are larger still.
Test the operator's note 3 where the data actually lives.
"""
import math
import numpy as np

D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t = D['t_cs']; act = D['cs_active'].astype(bool)
la_des, la_act = D['cs_la_des'], D['cs_la_act']
sa = np.interp(t, D['t_cst'], D['sa_deg'])
sr = np.interp(t, D['t_cst'], D['sr_deg'])
v  = np.interp(t, D['t_cst'], D['vego'])
SAT = lambda vv: 19.3 + 546.0*np.exp(-vv/3.01)
sat = SAT(v)
eng = act & (v > 5.0)

print("="*88)
print("A. WHERE DO LARGE ANGLES OCCUR AT ALL ON ROUTE 76?  (engaged)")
print("="*88)
print(f"{'speed m/s':>12} {'n':>7} {'p50':>6} {'p90':>6} {'p99':>6} {'max':>7} | {'sat':>6} | {'p99/sat':>8} {'%>sat':>7}")
for lo,hi in [(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,32)]:
    m = eng&(v>=lo)&(v<hi)
    if m.sum()<100: print(f"{lo:5.1f}-{hi:<6.1f} {m.sum():7d}  (too few)"); continue
    a=np.abs(sa[m]); s=np.median(sat[m])
    print(f"{lo:5.1f}-{hi:<6.1f} {m.sum():7d} {np.percentile(a,50):6.1f} {np.percentile(a,90):6.1f} "
          f"{np.percentile(a,99):6.1f} {a.max():7.1f} | {s:6.1f} | {np.percentile(a,99)/s:8.2f} {(a>sat[m]).mean()*100:6.2f}%")

print()
print("="*88)
print("B. HOLD-MAP DELIVERY RATIO (tanh/linear) AT THE ANGLES ACTUALLY DRIVEN, BY SPEED")
print("="*88)
print("   1.00 = map is linear here (no loss).  0.40 = map gives 40% of a linear spring.")
print(f"{'speed m/s':>12} {'n':>7} {'demand-wt ratio':>16} {'ratio at p99 angle':>20}")
for lo,hi in [(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,32)]:
    m = eng&(v>=lo)&(v<hi)
    if m.sum()<100: continue
    x = np.abs(sa[m])/sat[m]
    ratio = np.where(x>1e-6, np.tanh(np.maximum(x,1e-6))/np.maximum(x,1e-6), 1.0)
    w = np.abs(la_des[m])+1e-6
    xp = np.percentile(np.abs(sa[m]),99)/np.median(sat[m])
    print(f"{lo:5.1f}-{hi:<6.1f} {m.sum():7d} {np.average(ratio,weights=w):16.3f} {math.tanh(xp)/xp:20.3f}")

print()
print("="*88)
print("C. THE OPERATOR'S NOTE 3 TEST: tracking gain vs ANGLE, at speeds with large-angle data")
print("="*88)
print("   slope = regression of actual lateral accel on desired. <1 = under-turning (his symptom).")
print("   quasi-static only (|steering rate| < 20 deg/s) so this is a HOLD test, not a transient test.")
for lo,hi in [(5,10),(10,15),(15,22),(22,32)]:
    print(f"\n  speed {lo}-{hi} m/s")
    print(f"  {'|angle| deg':>14} {'n':>7} {'slope':>8} {'r':>7} {'mean|a_des|':>12} {'x/sat':>7} {'map ratio':>10}")
    for alo,ahi in [(0,2),(2,5),(5,10),(10,20),(20,40),(40,80),(80,400)]:
        m = eng&(v>=lo)&(v<hi)&(np.abs(sa)>=alo)&(np.abs(sa)<ahi)&(np.abs(sr)<20.0)
        if m.sum()<150: 
            if m.sum()>0: print(f"  {alo:5d}-{ahi:<8d} {m.sum():7d}   (too few)")
            continue
        xd,ya = la_des[m], la_act[m]
        if np.dot(xd,xd) < 1e-9: continue
        slope=float(np.dot(xd,ya)/np.dot(xd,xd)); rr=float(np.corrcoef(xd,ya)[0,1])
        xs = np.median(np.abs(sa[m])/sat[m])
        print(f"  {alo:5d}-{ahi:<8d} {m.sum():7d} {slope:8.3f} {rr:7.3f} {np.mean(np.abs(xd)):12.3f} "
              f"{xs:7.2f} {math.tanh(xs)/xs if xs>1e-6 else 1.0:10.3f}")

print()
print("="*88)
print("D. SIGN OF THE ERROR AT LARGE ANGLE -- does the car fall TOWARD CENTRE?")
print("="*88)
print("   err_toward_centre = |a_des| - |a_act|  ; positive = under-turning = returning to centre")
for lo,hi in [(5,10),(10,15),(15,22),(22,32)]:
    row=[]
    for alo,ahi in [(0,2),(2,5),(5,10),(10,20),(20,40),(40,80),(80,400)]:
        m = eng&(v>=lo)&(v<hi)&(np.abs(sa)>=alo)&(np.abs(sa)<ahi)&(np.abs(sr)<20.0)
        if m.sum()<150: row.append(f"{'--':>8}"); continue
        e = np.abs(la_des[m])-np.abs(la_act[m])
        row.append(f"{np.median(e):8.3f}")
    print(f"  {lo:2d}-{hi:<3d} m/s : " + " ".join(row))
print(f"  {'angle bin':>11} : " + " ".join(f"{b:>8}" for b in ['0-2','2-5','5-10','10-20','20-40','40-80','80+']))
