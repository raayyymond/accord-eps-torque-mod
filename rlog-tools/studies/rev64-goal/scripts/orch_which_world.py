"""WHICH PLANT WORLD IS THE CAR IN?

The project has carried two incompatible damping estimates since the start:
   "mode"  b = 0.0006 flat        (light damping, zeta 0.2-0.35)
   "ident" b = 0.0018 - 0.0049    (BANDS, from the identification report)
Rev 6.4's headline result was quoted in the LIGHT world (fine-band delivery 0.86 -> 0.95).
In the identified world the same change reads 0.36 -> 0.45. The operator's expectation of how
much of his lane-centring correction reaches the road depends entirely on which is true.

Settle it: per-run bootstrap on the 0.25 s replay error, route 76, engaged, driver not pressing.
Then fit b and J freely per speed band and report the confidence interval.
"""
import math, sys
import numpy as np

SAT_A,SAT_B,SAT_C=(19.3,546.0,3.01)
K_BP=[2.,4.,6.,8.,10.,12.5,15.,17.5,20.,23.,28.]
K_V=[.0021,.0028,.0044,.0052,.0074,.0092,.0095,.0103,.0116,.0133,.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
def hold_torque(a,v):
    k=np.interp(v,K_BP,K_V)*np.interp(v,LVL_BP,LVL_V)
    s=SAT_A+SAT_B*math.exp(-max(v,0.)/SAT_C); return k*s*math.tanh(a/s)
BANDS={"1-8":dict(b=.00180,F=.0120),"8-15":dict(b=.00366,F=.0119),
       "15-22":dict(b=.00409,F=.0112),">22":dict(b=.00489,F=.0098)}
def band_for(v): return "1-8" if v<8 else "8-15" if v<15 else "15-22" if v<22 else ">22"

D=np.load('analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz',allow_pickle=True)
t=D['t_cs']; act=D['cs_active'].astype(bool)
FS=1.0/float(np.median(np.diff(t))); DT=1.0/FS
phi_m=np.interp(t,D['t_cst'],D['sa_deg']); rate_m=np.interp(t,D['t_cst'],D['sr_deg'])
v_m=np.interp(t,D['t_cst'],D['vego']); press=np.interp(t,D['t_cst'],D['spress'])>0.5
u_w=-np.interp(t,D['te4'],D['cmd'])/4096.0
good=act&~press
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

def step(phi,pd,u,v,b,F,J,hs):
    sp=hs*hold_torque(phi,v); Dt=u-sp-b*pd
    vf=pd+Dt/J*DT; dv=F/J*DT
    if pd==0.0: pd=0.0 if abs(u-sp)<=F else math.copysign(max(abs(vf)-dv,0.),u-sp)
    else:
        if abs(vf)<=dv and abs(u-sp)<=F: pd=0.0
        else: pd=(vf-math.copysign(dv,vf)) if abs(vf)>dv else 0.0
    return phi+pd*DT,pd

HOR=0.25; H=int(round(HOR*FS)); R=int(round(1.0*FS)); ND=int(round(0.04*FS))
def per_seg_errors(bfun,Fs,J,hs):
    """Return (run_index, squared error) per restart segment so we can bootstrap over RUNS."""
    out=[]
    for ri,(a,bb) in enumerate(RUNS):
        for s in range(a,bb-H,R):
            v=float(v_m[s]); bd=BANDS[band_for(v)]
            b=bfun(v,bd); F=bd['F']*Fs
            phi,pd=float(phi_m[s]),float(rate_m[s])
            for n in range(s,s+H): phi,pd=step(phi,pd,float(u_w[max(n-ND,0)]),v,b,F,J,hs)
            out.append((ri,(phi-phi_m[s+H])**2,(phi_m[s]+rate_m[s]*HOR-phi_m[s+H])**2))
    return np.array(out)

MODE  = lambda v,bd: 0.0006
IDENT = lambda v,bd: bd['b']
print("="*88); print("A. HEAD TO HEAD, bootstrapped over the 20 engaged runs (0.25 s horizon)"); print("="*88)
E_m=per_seg_errors(MODE,1.0,1e-4,1.0); E_i=per_seg_errors(IDENT,1.0,1e-4,1.0)
assert len(E_m)==len(E_i)
ri=E_m[:,0].astype(int); nR=len(RUNS)
def rms(mask,col,E): return math.sqrt(E[mask,col].mean())
allm=np.ones(len(E_m),bool)
print(f"  mode  (b=0.0006) RMS {rms(allm,1,E_m):.3f} deg")
print(f"  ident (b=BANDS)  RMS {rms(allm,1,E_i):.3f} deg")
print(f"  const-velocity   RMS {rms(allm,2,E_m):.3f} deg")
# bootstrap over runs
rng=np.random.default_rng(12345); diffs=[]
for _ in range(2000):
    pick=rng.integers(0,nR,nR)
    m=np.concatenate([np.where(ri==p)[0] for p in pick])
    diffs.append(math.sqrt(E_m[m,1].mean())-math.sqrt(E_i[m,1].mean()))
diffs=np.array(diffs)
lo,hi=np.percentile(diffs,[2.5,97.5])
print(f"\n  RMS(mode) - RMS(ident) = {diffs.mean():+.3f} deg   95% CI [{lo:+.3f}, {hi:+.3f}]")
print(f"  ident wins in {(diffs>0).mean()*100:.1f}% of bootstrap resamples")
print(f"  => {'IDENT is the car' if lo>0 else 'NOT SEPARATED -- cannot tell the worlds apart'}")

print()
print("="*88); print("B. FIT b FREELY PER SPEED BAND (what damping does the car actually want?)"); print("="*88)
print(f"  {'band':>8} {'bench mode':>11} {'bench ident':>12} {'fitted b':>10} {'fitted J':>10} {'RMS':>8} {'const-vel':>10}")
for bandkey,vrep in [("8-15",13.0),("15-22",19.0),(">22",25.0)]:
    sel=[(a,bb) for a,bb in RUNS if band_for(float(np.median(v_m[a:bb])))==bandkey]
    if not sel: print(f"  {bandkey:>8}   (no run in this band)"); continue
    saveRUNS=RUNS[:]
    globals()['RUNS']=sel
    best=None
    for b_abs in (0.0006,0.0012,0.0024,0.0036,0.0048,0.0072,0.0100):
        for J in (5e-5,1e-4,2e-4,3e-4,5e-4):
            E=per_seg_errors(lambda v,bd,B=b_abs: B,1.0,J,1.0)
            r=math.sqrt(E[:,1].mean())
            if best is None or r<best[0]: best=(r,b_abs,J,math.sqrt(E[:,2].mean()))
    globals()['RUNS']=saveRUNS
    print(f"  {bandkey:>8} {0.0006:11.4f} {BANDS[bandkey]['b']:12.4f} {best[1]:10.4f} {best[2]:10.0e} {best[0]:8.3f} {best[3]:10.3f}")
print()
print("  (bench 'mode' assumes 0.0006 at every speed; 'ident' is the BANDS column)")
