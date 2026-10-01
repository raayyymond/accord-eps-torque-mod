# -*- coding: utf-8 -*-
"""Stage 2: characterise the sub-bar combined members (CL pole freq/zeta, GM), check R3 coverage,
Re(T/omega) vs V294/V295, and the fork outer-loop stand-in."""
import math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import refute_c1_ind as R

def cl_peak_and_pole(G, kp, ki, kd, disc, d=2, age=0, fmin=0.1, fmax=40.0, npts=4000):
    """closed-loop T_ref = L/(1+L); return (peak|T| in 0.5-30Hz, freq, and the worst CL resonance f/zeta from 1+L roots)."""
    f = np.logspace(math.log10(fmin), math.log10(fmax), npts)
    L = R.loop_L(G, kp, ki, kd, disc, f, d=d, age=age)
    T = L / (1 + L)
    band = (f >= 0.5) & (f <= 30)
    pk = float(np.max(np.abs(T[band]))); fpk = float(f[band][np.argmax(np.abs(T[band]))])
    S = 1.0 / (1 + L)
    Ms = float(np.max(np.abs(S)))
    # estimate dominant CL ring from |S| peak location/sharpness
    fS = float(f[np.argmax(np.abs(S))])
    return pk, fpk, Ms, fS

def exact_gm(G, kp, ki, kd, disc, d=2, age=0):
    # bisection on a scalar gain multiplier g until marginal (|L|=1 at -180)
    f = np.logspace(math.log10(0.02), math.log10(120), 6000)
    L = R.loop_L(G, kp, ki, kd, disc, f, d=d, age=age)
    ph = np.unwrap(np.angle(L)) * 180 / math.pi
    mag = np.abs(L)
    gm = float('inf')
    for i in range(len(f) - 1):
        w0 = (ph[i] + 180) / 360; w1 = (ph[i + 1] + 180) / 360
        if math.floor(w0) != math.floor(w1):
            t = (math.floor(max(w0, w1)) - w0) / (w1 - w0) if w1 != w0 else 0
            m = mag[i] + t * (mag[i + 1] - mag[i])
            g = -20 * math.log10(max(m, 1e-12))
            if g < gm:
                gm = g
    return gm

def member_full(name, v, extra_age=0):
    J, b, k, d, age = R.member_params(name, v)
    disc = R.rigid_disc(J, b, k)
    G = R.CL.G_at(v, R.TBL)
    pm, gm0 = R.margins(G, R.KP_BASE, R.KI_BASE, R.KD, disc, d=d, age=age + extra_age)
    pk, fpk, Ms, fS = cl_peak_and_pole(G, R.KP_BASE, R.KI_BASE, R.KD, disc, d=d, age=age + extra_age)
    egm = exact_gm(G, R.KP_BASE, R.KI_BASE, R.KD, disc, d=d, age=age + extra_age)
    return dict(J=J, b=b, k=k, d=d, age=age + extra_age, G=G, Kp=R.KP_BASE*G/256, pm=pm, gm=egm, Tpk=pk, fpk=fpk, Ms=Ms, fS=fS)

print("="*110)
print("STAGE 2A: the undeclared sub-30 combined members -- CL ring freq (for R3's 3.5-5.5 Hz band) + exact GM")
print("  R3 catches a growing/sustained 3.5-5.5 Hz oscillation at >=12.5 m/s.  A ring BELOW 3.5 Hz is NOT in R3's band.")
print("="*110)
cases = [("b_q*J_hi", [13,15,17,19,22,26]),
         ("b_q*J1.0", [13,15,17,19,22,26]),
         ("b_q0*J_hi", [15,17,19]),
         ("b_lo*J_hi*tau6", [10,11,11.9]),
         ("b_q", [15,17,19,26,27]),            # the design-gated reference (nominal J)
         ("J1.0", [11,11.9,12]),
         ("b_q*J_hi+hA", [15,17]),
         ("b_q+hA", [26,27]),
         ("b_lo*J_hi*tau6+hA", [10,11]) ]
for nm, vs in cases:
    print(f"\n  {nm}:")
    for v in vs:
        try:
            r = member_full(nm, v)
        except Exception as e:
            print(f"    v{v}: ERR {e}"); continue
        inR3 = 3.5 <= r['fpk'] <= 5.5
        unst = r['pm'] <= 0 or r['gm'] <= 0
        tag = "UNSTABLE" if unst else ("PM<30" if r['pm']<30 else "ok")
        r3 = "R3-band" if inR3 else "BELOW/ABOVE R3 band"
        print(f"    v{v:5.1f} J{r['J']:.2f} b{r['b']:5.2f} k{r['k']:5.1f} Kp{r['Kp']:5.0f} | PM {r['pm']:6.1f} GM {r['gm']:5.1f}dB | "
              f"|T_ref|pk {r['Tpk']:4.2f}@{r['fpk']:4.2f}Hz Ms {r['Ms']:4.2f} | {tag:8s} | ring {r3}")

print("\n"+"="*110)
print("STAGE 2B: Re(T/omega) 5-25 Hz, C1 worst-over-speed vs V294/V295 (design rule: Re(T/w)20 <= V295 at every speed)")
print("  also with 10-tick hold aging on C1 (design's torque_per_rate used age 0 only)")
print("="*110)
freqs = [5,7,10,13,15,17,20,25]
# V294/V295 rate controllers
def tpr_rate(name, f, age=0):
    if name=="V295": a,b,op,kp,kd = 1011,1050,"diff",960,0
    else: a,b,op,kp,kd = 1011,567,"diff",960,0
    return R.torque_per_rate_rate(a,b,op,kp,kd,f,d=2,age=age)
# C1 worst over speed = highest G (>=26.9 m/s)
vgrid = [round(x,3) for x in np.arange(5.0, 30.01, 0.5)]
print("  freq:        " + "".join(f"{f:>8d}" for f in freqs))
v294 = [tpr_rate("V294",f).real for f in freqs]
v295 = [tpr_rate("V295",f).real for f in freqs]
print("  V294 Re    : " + "".join(f"{x:+8.3f}" for x in v294))
print("  V295 Re    : " + "".join(f"{x:+8.3f}" for x in v295))
# C1 worst (most negative) over speed, age 0
c1w0 = []
for f in freqs:
    vals = [R.torque_per_rate_C1(R.CL.G_at(v,R.TBL), R.KP_BASE, R.KI_BASE, R.KD, f, d=2, age=0).real for v in vgrid]
    c1w0.append(min(vals))
print("  C1 w age0  : " + "".join(f"{x:+8.3f}" for x in c1w0))
c1w10 = []
for f in freqs:
    vals = [R.torque_per_rate_C1(R.CL.G_at(v,R.TBL), R.KP_BASE, R.KI_BASE, R.KD, f, d=2, age=10).real for v in vgrid]
    c1w10.append(min(vals))
print("  C1 w age10 : " + "".join(f"{x:+8.3f}" for x in c1w10))
print("  ratio C1age0/V295 @20Hz: %.3f  (design claims 0.997; >1 would be a REGRESSION vs V295)" % (c1w0[freqs.index(20)]/v295[freqs.index(20)]))
print("  ratio C1age10/V295@20Hz: %.3f" % (c1w10[freqs.index(20)]/v295[freqs.index(20)]))
# where does the C1 age0 20Hz worst occur?
f=20; vals=[(R.torque_per_rate_C1(R.CL.G_at(v,R.TBL),R.KP_BASE,R.KI_BASE,R.KD,f,d=2,age=0).real,v) for v in vgrid]
print("  C1 20Hz worst age0: %.4f @ %.1f m/s" % min(vals))

print("\n"+"="*110)
print("STAGE 2C: fork outer-loop stand-in L_o = T_ref * e^{-0.06s}/(tau_o s); GM on the worst combined members")
print("="*110)
def outer_gm(name, v, tau_o=1.0, delay=0.06):
    J,b,k,d,age = R.member_params(name, v); disc = R.rigid_disc(J,b,k); G=R.CL.G_at(v,R.TBL)
    f = np.logspace(math.log10(0.02), math.log10(20), 4000)
    L = R.loop_L(G, R.KP_BASE, R.KI_BASE, R.KD, disc, f, d=d, age=age)
    Tref = L/(1+L)
    w = 2*math.pi*f
    Lo = Tref * np.exp(-1j*w*delay) / (1j*w*tau_o)
    mag=np.abs(Lo); ph=np.unwrap(np.angle(Lo))*180/math.pi
    gm=float('inf')
    for i in range(len(f)-1):
        w0=(ph[i]+180)/360; w1=(ph[i+1]+180)/360
        if math.floor(w0)!=math.floor(w1):
            t=(math.floor(max(w0,w1))-w0)/(w1-w0) if w1!=w0 else 0
            m=mag[i]+t*(mag[i+1]-mag[i]); g=-20*math.log10(max(m,1e-12))
            if 0<g<gm: gm=g
    return gm
for nm in ["b_q*J_hi","b_q*J1.0","b_lo*J_hi*tau6","b_q"]:
    for tau in (1.0, 0.5):
        gms=[]
        for v in [13,15,17,19,26]:
            try: gms.append(outer_gm(nm,v,tau_o=tau))
            except: gms.append(float('nan'))
        print(f"  {nm:16s} tau_o {tau}: outer GM by v [13,15,17,19,26] = {['%.1f'%g for g in gms]}")
