"""J railed at the top of my grid (5e-4) against the bench's fitted 7.2e-5 - 1e-4.
A 5x disagreement is not a tuning detail -- it means the model is absorbing something.

HYPOTHESIS: an unmodelled first-order LAG between the commanded torque and the torque the
motor actually delivers looks exactly like extra inertia at low frequency. The bench's J was
fitted BAND-PASSED (high frequency, where a lag and an inertia separate); my replay is a 0.25 s
point prediction (low frequency, where they do not). If a lag is what is missing, adding one
should pull J back down toward the band-passed value AND improve the fit.

If true, this is a real missing steering dynamic -- exactly what the operator asked to model in
the 100 Hz loop -- and it would also mean the error notch (which sits at sqrt(k/J)/2pi) is placed
off the true mode.
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

def score(runs,b,J,tau_lag,F_scale=1.0):
    """tau_lag: first-order lag (s) on the applied torque. 0 = none (the bench's assumption)."""
    al = DT/(tau_lag+DT) if tau_lag>0 else 1.0
    se=[]; sb=[]
    for a,bb in runs:
        for s in range(a,bb-H,R):
            v=float(v_m[s]); bd=BANDS[band_for(v)]; F=bd['F']*F_scale
            phi,pd=float(phi_m[s]),float(rate_m[s])
            ul=float(u_w[max(s-ND,0)])
            for n in range(s,s+H):
                ul += al*(float(u_w[max(n-ND,0)])-ul)
                sp=hold_t(phi,v); Dt=ul-sp-b*pd
                vf=pd+Dt/J*DT; dv=F/J*DT
                if pd==0.0: pd=0.0 if abs(ul-sp)<=F else math.copysign(max(abs(vf)-dv,0.),ul-sp)
                else:
                    if abs(vf)<=dv and abs(ul-sp)<=F: pd=0.0
                    else: pd=(vf-math.copysign(dv,vf)) if abs(vf)>dv else 0.0
                phi+=pd*DT
            se.append((phi-phi_m[s+H])**2); sb.append((phi_m[s]+rate_m[s]*HOR-phi_m[s+H])**2)
    return math.sqrt(np.mean(se)), math.sqrt(np.mean(sb)), len(se)

print("="*100)
print("Does an explicit torque LAG explain the inflated inertia?   0.25 s replay, route 76, unpressed")
print("="*100)
for bandkey,vlab in [("8-15","8-15 m/s"),("15-22","15-22 m/s"),(">22",">22 m/s")]:
    sel=[(a,bb) for a,bb in ALLRUNS if band_for(float(np.median(v_m[a:bb])))==bandkey]
    if not sel: continue
    _,cv,nn = score(sel, 0.0036, 1e-4, 0.0)
    print(f"\n  {vlab}   ({len(sel)} runs, {nn} segments)   constant-velocity baseline = {cv:.3f} deg")
    print(f"  {'tau_lag':>8} {'best b':>9} {'best J':>9} {'RMS':>8} {'vs const-vel':>13}   {'mode Hz':>8}")
    best_overall=None
    for tl in (0.0, 0.02, 0.05, 0.10, 0.20, 0.35):
        best=None
        for b in (0.0012,0.0024,0.0036,0.0048,0.0072,0.0100,0.0150):
            for J in (5e-5,1e-4,2e-4,3e-4,5e-4,8e-4,1.2e-3):
                r,_,_=score(sel,b,J,tl)
                if best is None or r<best[0]: best=(r,b,J)
        kk=float(np.interp({'8-15':13.0,'15-22':19.0,'>22':25.0}[bandkey],K_BP,K_V))
        modehz=math.sqrt(kk/best[2])/(2*math.pi)
        flag='' if best[2] not in (5e-5,1.2e-3) else '  <- railed'
        print(f"  {tl:8.2f} {best[1]:9.4f} {best[2]:9.1e} {best[0]:8.3f} {1-best[0]/cv:+13.1%}   {modehz:8.2f}{flag}")
        if best_overall is None or best[0]<best_overall[0]: best_overall=(best[0],tl,best[1],best[2])
    print(f"  -> best: tau_lag={best_overall[1]:.2f}s  b={best_overall[2]:.4f}  J={best_overall[3]:.1e}  RMS={best_overall[0]:.3f}")
print()
print("  Bench assumes: J = 8e-5 (mode 1.0-2.1 Hz), no torque lag.")
print("  AccordErrorNotchQ is placed at get_honda_accord_mode_hz = sqrt(k/8e-5)/2pi.")
