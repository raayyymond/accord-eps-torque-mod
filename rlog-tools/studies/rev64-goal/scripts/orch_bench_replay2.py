"""Hardened version of orch_bench_replay.py. Same test, with every confound I can control:
  - driver-pressed frames EXCLUDED (an unmodelled hand on the wheel is an unmodelled torque)
  - transport delay tau SCANNED, not assumed
  - hold scale, damping multiplier and friction scale SCANNED (give the model its best shot)
  - angle offset removed
  - reported against BOTH baselines, at a short horizon where road disturbance cannot dominate
If the BEST-FITTED plant still loses to a straight line, the bench does not model this car.
"""
import math, sys
import numpy as np
SC='/tmp/claude-0/-home-user-accord-eps-torque-mod/1835f72d-a78b-5e09-987d-1aaf14b661eb/scratchpad'

SAT_A,SAT_B,SAT_C=(19.3,546.0,3.01)
K_BP=[2.,4.,6.,8.,10.,12.5,15.,17.5,20.,23.,28.]
K_V=[.0021,.0028,.0044,.0052,.0074,.0092,.0095,.0103,.0116,.0133,.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
def hold_torque(ang,v,level=True):
    k=np.interp(v,K_BP,K_V)*(np.interp(v,LVL_BP,LVL_V) if level else 1.0)
    s=SAT_A+SAT_B*math.exp(-max(v,0.)/SAT_C)
    return k*s*math.tanh(ang/s)
BANDS={"1-8":dict(b=.00180,F=.0120),"8-15":dict(b=.00366,F=.0119),
       "15-22":dict(b=.00409,F=.0112),">22":dict(b=.00489,F=.0098)}
def band_for(v): return "1-8" if v<8 else "8-15" if v<15 else "15-22" if v<22 else ">22"

D=np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz',allow_pickle=True)
t=D['t_cs']; act=D['cs_active'].astype(bool)
FS=1.0/float(np.median(np.diff(t))); DT=1.0/FS
phi_m=np.interp(t,D['t_cst'],D['sa_deg'])
rate_m=np.interp(t,D['t_cst'],D['sr_deg'])
v_m=np.interp(t,D['t_cst'],D['vego'])
press=np.interp(t,D['t_cst'],D['spress'])>0.5
u_wire=-np.interp(t,D['te4'],D['cmd'])/4096.0     # sign settled empirically in v1

good = act & ~press
print(f"engaged {act.sum()}  pressed {(act&press).sum()} ({(act&press).sum()/max(act.sum(),1)*100:.1f}%)  usable {good.sum()}")

def runs(mask,minlen=400):
    out,n,i=[],len(mask),0
    while i<n:
        if not mask[i]: i+=1; continue
        j=i
        while j+1<n and mask[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if j+1-i>minlen: out.append((i,j+1))
        i=j+1
    return out
RUNS=runs(good)
print(f"usable runs: {len(RUNS)}, total {sum(b-a for a,b in RUNS)/FS:.0f} s")

def step(phi,pd,u,v,b,F,J,hs,level):
    spring=hs*hold_torque(phi,v,level)
    Dt=u-spring-b*pd
    vf=pd+Dt/J*DT; dvf=F/J*DT
    if pd==0.0:
        pd = 0.0 if abs(u-spring)<=F else math.copysign(max(abs(vf)-dvf,0.),u-spring)
    else:
        if abs(vf)<=dvf and abs(u-spring)<=F: pd=0.0
        else: pd=(vf-math.copysign(dvf,vf)) if abs(vf)>dvf else 0.0
    return phi+pd*DT, pd

def replay(bmul,Fs,J,hs,tau,horiz,level=True,restart=1.0,world='ident'):
    nd=int(round(tau*FS)); H=int(round(horiz*FS)); R=int(round(restart*FS))
    e=[];bp=[];bv=[]
    for a,bb in RUNS:
        for s in range(a,bb-H,R):
            v=float(v_m[s]); bd=BANDS[band_for(v)]
            b=(0.0006 if world=='mode' else bd['b'])*bmul; F=bd['F']*Fs
            phi,pd=float(phi_m[s]),float(rate_m[s])
            for n in range(s,s+H):
                phi,pd=step(phi,pd,float(u_wire[max(n-nd,0)]),v,b,F,J,hs,level)
            e.append(phi-phi_m[s+H]); bp.append(phi_m[s]-phi_m[s+H])
            bv.append(phi_m[s]+rate_m[s]*horiz-phi_m[s+H])
    e=np.array(e)
    return np.sqrt(np.mean(e**2)),np.sqrt(np.mean(np.array(bp)**2)),np.sqrt(np.mean(np.array(bv)**2)),len(e)

HOR=0.25
print()
print("="*92)
print(f"GIVE THE MODEL ITS BEST SHOT -- grid search at {HOR}s horizon, pressed frames excluded")
print("="*92)
r0=replay(1,1,1e-4,1.0,0.04,HOR)
print(f"  baselines:  persistence {r0[1]:.3f} deg   constant-velocity {r0[2]:.3f} deg   (n={r0[3]})")
print()
best=None; rows=[]
for world in ('mode','ident'):
  for bmul in (1.0, 2.0, 4.0, 8.0):
    for Fs in (0.5, 1.0):
      for J in (5e-5, 1e-4, 3e-4):
        for hs in (0.7, 1.0, 1.3):
          for tau in (0.0, 0.04, 0.08):
            r=replay(bmul,Fs,J,hs,tau,HOR,world=world)
            rows.append((r[0],world,bmul,Fs,J,hs,tau))
            if best is None or r[0]<best[0]: best=(r[0],world,bmul,Fs,J,hs,tau)
rows.sort()
print(f"  {'rank':>4} {'RMS deg':>9} {'world':>6} {'b x':>5} {'F x':>5} {'J':>8} {'hold x':>7} {'tau':>5} {'skill vs const-vel':>19}")
for i,r in enumerate(rows[:8]):
    print(f"  {i+1:4d} {r[0]:9.3f} {r[1]:>6} {r[2]:5.1f} {r[3]:5.1f} {r[4]:8.0e} {r[5]:7.2f} {r[6]:5.2f} {1-r[0]/r0[2]:19.3f}")
print(f"  ...")
print(f"  {'WORST':>4} {rows[-1][0]:9.3f} {rows[-1][1]:>6} {rows[-1][2]:5.1f} {rows[-1][3]:5.1f} {rows[-1][4]:8.0e} {rows[-1][5]:7.2f} {rows[-1][6]:5.2f}")
print()
print(f"  BEST of {len(rows)} parameter combinations : {best[0]:.3f} deg")
print(f"  constant-velocity straight line            : {r0[2]:.3f} deg")
if best[0] < r0[2]:
    print(f"  => the plant model BEATS a straight line by {(1-best[0]/r0[2])*100:.0f}% at its best fit.")
else:
    print(f"  => EVEN AT ITS BEST FIT the plant model is {best[0]/r0[2]:.2f}x WORSE than a straight line.")
    print(f"     The bench does not model this car's short-horizon response.")
print()
print("  b multiplier that wins, by world (does the car want MORE damping than either world assumes?)")
for world in ('mode','ident'):
    sub=[r for r in rows if r[1]==world]; sub.sort()
    print(f"    {world:>6}: best b x{sub[0][2]:.1f}  (RMS {sub[0][0]:.3f})   "
          f"b x1 best: {min(r[0] for r in sub if r[2]==1.0):.3f}")
