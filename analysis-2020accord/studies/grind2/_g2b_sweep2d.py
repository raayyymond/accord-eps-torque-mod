"""Is ANY (f0,r,fzero) setting of this biquad favourable?  2-D sweep against 4 criteria."""
import numpy as np, _gate2_boost_lib as L
HO=L.honda_exact(); FC=8.0; a=0.098
K=np.load('_scratch/data/_g2b_kappa.npz'); c=complex(K['c']); P0=complex(K['P4']); Z4=complex(K['Z4']); Z0=Z4*(1+P0)
Zm=complex(-3761,-5752); Gm=0.0526*np.exp(1j*np.radians(15.4)); A0=abs(1+P0)
Hh=L.H_biquad(*HO,FC)
ff=np.geomspace(0.1,500,4001)

print(f"baseline: |u|={abs(Gm):.4f}  |A0|={A0:.3f}  1/|A0|={1/A0:.2f}  Re(Z)={Zm.real:.0f}")
print("PASS = |u_new|/|u| < 1  AND  |A_new| > |A0|  AND  no Nyquist encirclement  AND  |H| at 21-26 Hz <= honda\n")
print(f"{'f0':>6}{'r':>7}{'|H(8)|/|Hh|':>12}{'arg':>7}{'pk dB':>7}{'|u_n|/|u|':>10}{'|A_new|':>9}{'argPn':>8}{'H21/Hh':>8}{'ReZnew':>9}  verdict")
best=[]
for f0 in [8.05,10,12,14,17,20,25,30,40]:
    for r in [0.60,0.75,0.85,0.90,0.95,0.98,0.99]:
        a1,a2,b1,g=[L.f32(v) for v in L.design_boost(f0,r,300.0)]
        Hn=L.H_biquad(a1,a2,b1,g,FC)
        if abs(Hn)<=abs(Hh)*1.02: continue        # want a BOOST at 8 Hz
        pk=20*np.log10(np.abs(L.H_biquad(a1,a2,b1,g,ff)).max())
        dG=-a*(Hn-Hh); dP=c*dG; Pn=P0+dP; An=abs(1+Pn); ap=np.angle(Pn,deg=True)%360
        ratio=abs(Gm+dG)/abs(Gm); Zn=Z0/(1+Pn)
        h21=abs(L.H_biquad(a1,a2,b1,g,21.73))/abs(L.H_biquad(*HO,21.73))
        enc = (ap>180 and abs(Pn)>1)
        ok = (ratio<1) and (An>A0) and (not enc) and (h21<=1.0)
        v = "PASS" if ok else ("encircle" if enc else ("|u| up" if ratio>=1 else ("|A| down" if An<=A0 else "21Hz up")))
        print(f"{f0:6.2f}{r:7.2f}{abs(Hn)/abs(Hh):12.3f}{np.angle(Hn,deg=True):+7.1f}{pk:+7.2f}{ratio:10.3f}{An:9.3f}"
              f"{ap:+8.1f}{h21:8.3f}{Zn.real:+9.0f}  {v}")
        if ok: best.append((f0,r,ratio,An))
print("\nPASSING designs:", best if best else "NONE")

print("\n### What perturbation WOULD be optimal at 8 Hz?  (unconstrained by filter structure)")
Lc=-a*Hh
eps=(Gm*np.conj(Lc)).real/abs(Lc)**2
dGopt=-eps*Lc
Pn=P0+c*dGopt
print(f"  dG_opt = {abs(dGopt):.4f} at {np.angle(dGopt,deg=True):+.1f} deg  (= a PURE MAGNITUDE boost of the lane by {1-eps:.3f}x, ZERO phase change)")
print(f"  -> |u| {abs(Gm):.4f} -> {abs(Gm+dGopt):.4f} ({abs(Gm+dGopt)/abs(Gm):.3f}x)")
print(f"  -> |A| {A0:.3f} -> {abs(1+Pn):.3f}   closed-loop amplification 1/|A| {1/A0:.2f} -> {1/abs(1+Pn):.2f}")
print(f"  -> Re(Z) {Zm.real:.0f} -> {(Z0/(1+Pn)).real:+.0f}")
print(f"  -> P {abs(P0):.3f}@{np.angle(P0,deg=True):+.1f} -> {abs(Pn):.3f}@{np.angle(Pn,deg=True)%360:+.1f}  (moves AWAY from the -1 point)")
print("  A biquad CANNOT deliver this: a 2-pole resonance has EXACTLY -90 deg at its own pole frequency")
print("  (H(jw0) = 1/(2*zeta) at -90 deg), so magnitude at f0 always comes with ~-90 deg of lag.")
