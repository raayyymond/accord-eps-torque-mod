"""Two guards on the J = 1e-3 finding, which contradicts the bench's J = 8e-5 by ~25x.

GUARD 1 (reconciliation). The bench's J came from a 2.34 Hz limit cycle seen on route 71:
J = k/omega^2 = 0.01661/(2*pi*2.34)^2 = 7.7e-5 -- which is exactly the bench's 8e-5.
But a limit-cycle frequency in a DELAYED CLOSED LOOP is where the loop phase crosses -180 deg,
NOT the plant's natural mode. If a plant with J = 2e-3 plus the fork's measured 60 ms loop delay
and its P gain also crosses -180 deg near 2.34 Hz, then both observations are consistent and the
prior identification conflated a closed-loop crossover with an open-loop resonance.

GUARD 2 (stability). Real dynamics give the same J at every prediction horizon. A J that is
absorbing closed-loop structure will drift with horizon.
"""
import math
import numpy as np

K_BP=[2.,4.,6.,8.,10.,12.5,15.,17.5,20.,23.,28.]
K_V=[.0021,.0028,.0044,.0052,.0074,.0092,.0095,.0103,.0116,.0133,.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
def k_at(v): return float(np.interp(v,K_BP,K_V))*float(np.interp(v,LVL_BP,LVL_V))

print("="*94)
print("GUARD 1 -- where does the loop cross -180 deg, for each candidate J?")
print("="*94)
print("  Plant  P(s) = 1 / (J s^2 + b s + k)   [torque -> angle]")
print("  Loop   L(s) = Kp_eff * P(s) * exp(-Td s),  Td = 0.060 s (measured CAN->torque round trip)")
print()
for v, b_fit in [(13.0,0.0024),(19.0,0.0048),(25.0,0.0072)]:
    k=k_at(v)
    print(f"  v = {v} m/s,  k = {k:.5f} torque/deg")
    print(f"    {'J':>10} {'nat mode Hz':>12} {'zeta':>7} {'-180 crossing Hz':>18}  note")
    for J,lbl in [(8e-5,'bench'),(2e-3,'fitted')]:
        wn=math.sqrt(k/J); fn=wn/(2*math.pi); zeta=b_fit/(2*math.sqrt(k*J))
        # find f where angle(P) - 2*pi*f*Td = -pi
        cross=None
        for f in np.arange(0.05,6.0,0.001):
            w=2*math.pi*f
            ph=math.atan2(-b_fit*w, k-J*w*w)      # phase of 1/(Js^2+bs+k)
            tot=ph-w*0.060
            if tot<=-math.pi: cross=f; break
        print(f"    {J:10.1e} {fn:12.2f} {zeta:7.3f} {(f'{cross:.2f}' if cross else '>6'):>18}  {lbl}")
    print()
print("  Route 71's observed limit cycle: 2.34 Hz.")
print("  -> If the FITTED J's -180 crossing lands near 2.34 Hz, both observations are consistent")
print("     and J = 8e-5 was a misattribution of a closed-loop crossover to the plant's own mode.")

# ---------------- GUARD 2
SAT_A,SAT_B,SAT_C=(19.3,546.0,3.01)
def hold_t(a,v):
    s=SAT_A+SAT_B*math.exp(-max(v,0.)/SAT_C); return k_at(v)*s*math.tanh(a/s)
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
ALLRUNS=mkruns(good); ND=int(round(0.04*FS))
def score(runs,b,J,HOR):
    H=int(round(HOR*FS)); R=int(round(1.0*FS)); se=[];sb=[]
    for a,bb in runs:
        for s in range(a,bb-H,R):
            v=float(v_m[s]); F=BANDS[band_for(v)]['F']
            phi,pd=float(phi_m[s]),float(rate_m[s])
            for n in range(s,s+H):
                u=float(u_w[max(n-ND,0)]); sp=hold_t(phi,v)
                Dt=u-sp-b*pd; vf=pd+Dt/J*DT; dv=F/J*DT
                if pd==0.0: pd=0.0 if abs(u-sp)<=F else math.copysign(max(abs(vf)-dv,0.),u-sp)
                else:
                    if abs(vf)<=dv and abs(u-sp)<=F: pd=0.0
                    else: pd=(vf-math.copysign(dv,vf)) if abs(vf)>dv else 0.0
                phi+=pd*DT
            se.append((phi-phi_m[s+H])**2); sb.append((phi_m[s]+rate_m[s]*HOR-phi_m[s+H])**2)
    return math.sqrt(np.mean(se)),math.sqrt(np.mean(sb))
print()
print("="*94)
print("GUARD 2 -- is the fitted J stable across prediction horizons?")
print("="*94)
Js=[1e-4,2e-4,4e-4,8e-4,1.6e-3,3.2e-3,6.4e-3]
for bk,bfit in [("15-22",0.0048),(">22",0.0072)]:
    sel=[(a,bb) for a,bb in ALLRUNS if band_for(float(np.median(v_m[a:bb])))==bk]
    if not sel: continue
    print(f"\n  {bk} m/s")
    print(f"    {'horizon':>8} " + "".join(f"{J:>9.0e}" for J in Js) + f"{'argmin J':>11}")
    for HOR in (0.15,0.25,0.40,0.60):
        vals=[score(sel,bfit,J,HOR)[0] for J in Js]
        print(f"    {HOR:8.2f} " + "".join(f"{x:>9.3f}" for x in vals) + f"{Js[int(np.argmin(vals))]:>11.0e}")
