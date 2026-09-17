"""Is J actually IDENTIFIABLE from this test, or is the fit railing because J -> infinity
degenerates toward the constant-velocity baseline (which is already good)?

Two checks:
  1. RMS vs J over a wide range at the fitted b. Peaked = identified. Flat/monotone = NOT.
  2. Term ablation: drop the spring, drop the friction, drop the damping. If removing a term
     costs nothing, the test does not constrain that term and I must not report a value for it.
"""
import math
import numpy as np

SAT_A,SAT_B,SAT_C=(19.3,546.0,3.01)
K_BP=[2.,4.,6.,8.,10.,12.5,15.,17.5,20.,23.,28.]
K_V=[.0021,.0028,.0044,.0052,.0074,.0092,.0095,.0103,.0116,.0133,.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
def hold_t(a,v):
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
def mkruns(mask,minlen=400):
    out,n,i=[],len(mask),0
    while i<n:
        if not mask[i]: i+=1; continue
        j=i
        while j+1<n and mask[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if j+1-i>minlen: out.append((i,j+1))
        i=j+1
    return out
ALLRUNS=mkruns(good)
HOR=0.25; H=int(round(HOR*FS)); R=int(round(1.0*FS)); ND=int(round(0.04*FS))

def score(runs,b,J,F_scale=1.0,spring=True,fric=True,damp=True):
    se=[];sb=[]
    for a,bb in runs:
        for s in range(a,bb-H,R):
            v=float(v_m[s]); bd=BANDS[band_for(v)]; F=bd['F']*F_scale if fric else 0.0
            bq=b if damp else 0.0
            phi,pd=float(phi_m[s]),float(rate_m[s])
            for n in range(s,s+H):
                u=float(u_w[max(n-ND,0)]); sp=hold_t(phi,v) if spring else 0.0
                Dt=u-sp-bq*pd; vf=pd+Dt/J*DT; dv=F/J*DT
                if F<=0.0: pd=vf
                elif pd==0.0: pd=0.0 if abs(u-sp)<=F else math.copysign(max(abs(vf)-dv,0.),u-sp)
                else:
                    if abs(vf)<=dv and abs(u-sp)<=F: pd=0.0
                    else: pd=(vf-math.copysign(dv,vf)) if abs(vf)>dv else 0.0
                phi+=pd*DT
            se.append((phi-phi_m[s+H])**2); sb.append((phi_m[s]+rate_m[s]*HOR-phi_m[s+H])**2)
    return math.sqrt(np.mean(se)), math.sqrt(np.mean(sb))

BANDSEL={}
for k in ("8-15","15-22",">22"):
    BANDSEL[k]=[(a,bb) for a,bb in ALLRUNS if band_for(float(np.median(v_m[a:bb])))==k]
FITB={"8-15":0.0024,"15-22":0.0048,">22":0.0072}

print("="*96)
print("1. IS J IDENTIFIED?   RMS vs J (b at its fitted value). Peaked = yes. Monotone = no.")
print("="*96)
Js=[5e-5,1e-4,2e-4,4e-4,8e-4,1.6e-3,3.2e-3,6.4e-3,1.3e-2,1e-1,1e1]
for k,sel in BANDSEL.items():
    if not sel: continue
    _,cv=score(sel,FITB[k],1e-4)
    vals=[score(sel,FITB[k],J)[0] for J in Js]
    print(f"\n  {k:>6} m/s   const-vel = {cv:.3f}")
    print("    " + "".join(f"{J:>9.0e}" for J in Js))
    print("    " + "".join(f"{x:>9.3f}" for x in vals))
    imin=int(np.argmin(vals))
    tail = "MONOTONE -> J NOT identified above the knee" if imin>=len(Js)-2 else f"minimum at J={Js[imin]:.0e}"
    # where does it come within 2% of its asymptote?
    asym=vals[-1]
    knee=next((J for J,x in zip(Js,vals) if x<=asym*1.02), None)
    print(f"    -> {tail};  J=inf (pure const-vel+spring) gives {asym:.3f};  within 2% of that from J>={knee:.0e}")

print()
print("="*96)
print("2. TERM ABLATION at the fitted parameters -- which terms actually earn their place?")
print("="*96)
for k,sel in BANDSEL.items():
    if not sel: continue
    J=8e-4; b=FITB[k]
    full,cv=score(sel,b,J)
    nos,_=score(sel,b,J,spring=False)
    nof,_=score(sel,b,J,fric=False)
    nod,_=score(sel,b,J,damp=False)
    print(f"\n  {k:>6} m/s   const-vel {cv:.3f}   full model {full:.3f}  ({1-full/cv:+.1%} vs baseline)")
    for lbl,val in [('no spring',nos),('no friction',nof),('no damping',nod)]:
        print(f"      {lbl:>12}: {val:7.3f}   ({'costs' if val>full else 'IMPROVES'} {abs(val-full)/full*100:5.1f}%)")
