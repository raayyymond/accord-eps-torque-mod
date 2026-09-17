"""The evidence relocated the problem from quasi-static holds to TRANSIENTS.
Operator note 5: "slow, steady angle rates decent, medium-to-large rate transients not handled well."
Test it directly on route 76 (rev 5).
"""
import numpy as np

D = np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz', allow_pickle=True)
t = D['t_cs']; act = D['cs_active'].astype(bool)
la_des, la_act = D['cs_la_des'], D['cs_la_act']
f_, p_, i_ = D['cs_f'], D['cs_p'], D['cs_i']
des_curv, curv = D['cs_des_curv'], D['cs_curv']
sa = np.interp(t, D['t_cst'], D['sa_deg'])
sr = np.interp(t, D['t_cst'], D['sr_deg'])
v  = np.interp(t, D['t_cst'], D['vego'])
dt = float(np.median(np.diff(t)))
print(f"frame dt = {dt*1000:.2f} ms   ({1/dt:.1f} Hz)")

eng = act & (v > 5.0)

# --- empirical angle-per-curvature, so desired curvature -> desired ANGLE without VM assumptions
print()
print("="*88)
print("A. EMPIRICAL angle-per-curvature (deg per 1/m), fitted from engaged data by speed")
print("="*88)
sp_bp, apc = [], []
for lo,hi in [(5,8),(8,10),(10,12.5),(12.5,15),(15,17.5),(17.5,22),(22,26),(26,32)]:
    m = eng&(v>=lo)&(v<hi)&(np.abs(curv)>1e-4)
    if m.sum()<300: continue
    s = float(np.dot(curv[m],sa[m])/np.dot(curv[m],curv[m]))
    sp_bp.append((lo+hi)/2); apc.append(s)
    print(f"  {lo:5.1f}-{hi:<5.1f} m/s  n={m.sum():6d}  {s:8.1f} deg per (1/m)   r={np.corrcoef(curv[m],sa[m])[0,1]:.3f}")
sp_bp, apc = np.array(sp_bp), np.array(apc)
ang_des = des_curv * np.interp(v, sp_bp, apc)
# desired angle RATE, same causal filter the fork uses (FF_RATE_RC = 0.10 s)
raw_rate = np.gradient(ang_des, t)
alpha = dt/(0.10+dt)
filt = np.zeros_like(raw_rate)
for n in range(1,len(raw_rate)):
    filt[n] = filt[n-1] + alpha*(raw_rate[n]-filt[n-1])

print()
print("="*88)
print("B. RATE-TRANSIENT TRACKING  (the operator's note 5)")
print("="*88)
print("   desired angle rate from the model, achieved from the wheel. Binned by |desired rate|.")
hs = eng & (v > 12.0)
q = np.abs(raw_rate[hs])
bnds = [np.percentile(q,x) for x in [50,75,90,97,99.5]]
print(f"   percentile boundaries of |desired angle rate| (deg/s): "
      + " ".join(f"p{x}={b:.1f}" for x,b in zip([50,75,90,97,99.5],bnds)))
print()
print(f"   {'band':>22} {'n':>7} {'gain(ach/des)':>14} {'r':>7} {'lag ms':>8}")
edges = [0]+bnds+[1e9]
names = ['0-p50 (slow/steady)','p50-p75','p75-p90','p90-p97 (medium)','p97-p99.5 (large)','>p99.5 (largest)']
for k in range(len(edges)-1):
    m = hs.copy(); m[hs] = (q>=edges[k])&(q<edges[k+1])
    if m.sum()<200: print(f"   {names[k]:>22} {m.sum():7d}   (too few)"); continue
    xd, ya = raw_rate[m], sr[m]
    g = float(np.dot(xd,ya)/max(np.dot(xd,xd),1e-12)); rr=float(np.corrcoef(xd,ya)[0,1])
    # lag by cross-correlation over +/-0.5 s on the contiguous mask
    best, bl = -9, 0
    for L in range(0,51):
        a = raw_rate[:-L] if L else raw_rate
        b = sr[L:] if L else sr
        mm = m[:-L] if L else m
        if mm.sum()<200: continue
        c = float(np.corrcoef(a[mm], b[mm])[0,1])
        if c>best: best, bl = c, L
    print(f"   {names[k]:>22} {m.sum():7d} {g:14.3f} {rr:7.3f} {bl*dt*1000:8.0f}")

print()
print("="*88)
print("C. WHO SUPPLIES THE COMMAND DURING TRANSIENTS  (shares in lat-accel space, f/(f+p+i))")
print("="*88)
print("   FF is instant. P is fast. I is SLOW. If FF's share collapses on transients, the")
print("   response is being carried by the slow path -- that is 'jerky, not smooth and gradual'.")
tot = f_+p_+i_
ok = hs & (np.abs(tot)>1e-3)
print(f"   {'band':>22} {'n':>7} {'FF share':>10} {'P share':>10} {'I share':>10} {'|f+p+i|':>10}")
for k in range(len(edges)-1):
    m = ok.copy(); m[ok] = (np.abs(raw_rate[ok])>=edges[k])&(np.abs(raw_rate[ok])<edges[k+1])
    if m.sum()<200: continue
    sf = np.mean(np.abs(f_[m])/np.abs(tot[m])); sp = np.mean(np.abs(p_[m])/np.abs(tot[m])); si = np.mean(np.abs(i_[m])/np.abs(tot[m]))
    print(f"   {names[k]:>22} {m.sum():7d} {sf:10.3f} {sp:10.3f} {si:10.3f} {np.mean(np.abs(tot[m])):10.4f}")

print()
print("="*88)
print("D. WHAT THE 0.10 s FF-RATE FILTER + rate_gain=0.5 COST ON THOSE TRANSIENTS")
print("="*88)
print("   delivered move term is  0.5 * filt(rate) ; the plant model asks for 1.0 * rate")
for k in range(len(edges)-1):
    m = hs.copy(); m[hs] = (q>=edges[k])&(q<edges[k+1])
    if m.sum()<200: continue
    ratio_filt = np.mean(np.abs(filt[m]))/max(np.mean(np.abs(raw_rate[m])),1e-9)
    print(f"   {names[k]:>22} {m.sum():7d}  filter keeps {ratio_filt:5.3f} of |rate|, "
          f"x0.5 gain -> FF supplies {0.5*ratio_filt:5.3f} of the modelled move torque")

print()
print("="*88)
print("E. POSITIVE CONTROL: slow steady rates should track near 1.0 (operator says 'decent')")
print("="*88)
m = hs.copy(); m[hs] = q < bnds[0]
xd, ya = raw_rate[m], sr[m]
print(f"   slow band gain = {float(np.dot(xd,ya)/np.dot(xd,xd)):.3f}  (if this is far from ~1, the instrument is wrong)")
