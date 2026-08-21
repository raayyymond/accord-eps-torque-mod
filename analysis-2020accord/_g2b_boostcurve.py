"""ITEM 2 + 3: the boost curve, the knife edge, and the CLOSED-LOOP consequence via the identified c."""
import numpy as np, _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)
HO=L.honda_exact()
K=np.load('_g2b_kappa.npz'); c=complex(K['c']); P0=complex(K['P4']); G4=complex(K['G4']); Z4=complex(K['Z4'])
Z0=Z4*(1+P0)
Zm=complex(-3761,-5752)   # r9e measured Z at 6-9 Hz (the record's number)
print(f"identified:  c={abs(c):.2f}@{np.angle(c,deg=True):+.1f}   P0={abs(P0):.3f}@{np.angle(P0,deg=True):+.1f}   "
      f"A0={abs(1+P0):.3f}@{np.angle(1+P0,deg=True):+.1f}   Z0={abs(Z0):.0f}@{np.angle(Z0,deg=True):+.1f}")
print(f"baseline GAIN MARGIN: |P| at the arg(P)=180 crossing.  arg(P0)={np.angle(P0,deg=True):+.1f} deg, |P0|={abs(P0):.3f}"
      f"  => distance to the -1 point |1+P0| = {abs(1+P0):.3f}\n")

FC=8.0; a=0.098
Gm=complex(0.0526*np.cos(np.radians(15.4)),0.0526*np.sin(np.radians(15.4)))  # pooled sum 6-9

print("### (i) IDEALISED pure-magnitude boost (the prior analysis's parameterisation: dG=(B-1)*(-a*H_honda))")
print(f"{'B':>6}{'|dG|':>8}{'arg dG':>8}{'Re(dG.Z)':>10}{'|u_new|/|u|':>12}{'|dP|':>7}{'|P_new|':>9}{'argP_new':>10}{'|A_new|':>9}{'Re(Znew)':>10}{'stable?':>9}")
Hh=L.H_biquad(*HO,FC)
for B in [1.0,1.2,1.44,1.52,1.8,2.0,2.04,2.5,3.0,4.0]:
    dG=(B-1)*(-a*Hh)
    dP=c*dG; Pn=P0+dP; An=1+Pn; Zn=Z0/An
    ratio=abs(Gm+dG)/abs(Gm)
    stab = "OK" if (np.angle(Pn,deg=True)%360)<180 or abs(Pn)<1 else "ENCIRCLE"
    print(f"{B:6.2f}{abs(dG):8.4f}{np.angle(dG,deg=True):+8.1f}{(dG*Zm).real:+10.0f}{ratio:12.3f}"
          f"{abs(dP):7.2f}{abs(Pn):9.3f}{np.angle(Pn,deg=True)%360:+10.1f}{abs(An):9.3f}{Zn.real:+10.0f}{stab:>9}")

print("\n### (ii) REALISABLE biquad boost: poles at 8.05 Hz, zero parked at 300 Hz, sweep r")
print(f"{'r':>7}{'B=|Hn|/|Hh|':>12}{'argHn':>8}{'pk|H|dB':>9}{'tau_ms':>8}{'|dG|':>8}{'argdG':>8}{'Re(dG.Z)':>10}"
      f"{'|u_n|/|u|':>10}{'|dP|':>7}{'|P_new|':>9}{'argPn':>8}{'|A_new|':>9}{'Re(Znew)':>10}{'verdict':>10}")
for r in [0.0,0.60,0.80,0.90,0.94,0.960,0.970,0.980,0.985,0.990,0.995]:
    if r==0.0:
        Hn=Hh; d=(HO); lab='honda'
        a1,a2,b1,g=HO
    else:
        a1,a2,b1,g=[L.f32(v) for v in L.design_boost(8.05,r,300.0)]
        Hn=L.H_biquad(a1,a2,b1,g,FC)
    ff=np.geomspace(0.1,500,8001); pk=20*np.log10(np.abs(L.H_biquad(a1,a2,b1,g,ff)).max())
    tau=-1000/(1000*np.log(np.sqrt(a2))) if a2>0 else np.nan
    dG=-a*(Hn-Hh); dP=c*dG; Pn=P0+dP; An=1+Pn; Zn=Z0/An
    ratio=abs(Gm+dG)/abs(Gm)
    ap=np.angle(Pn,deg=True)%360
    verdict = "UNSTABLE" if (ap>180 and abs(Pn)>1) else ("tight" if abs(An)<0.5 else "ok")
    print(f"{r:7.3f}{abs(Hn)/abs(Hh):12.3f}{np.angle(Hn,deg=True):+8.1f}{pk:+9.2f}{tau:8.1f}{abs(dG):8.4f}"
          f"{np.angle(dG,deg=True):+8.1f}{(dG*Zm).real:+10.0f}{ratio:10.3f}{abs(dP):7.2f}{abs(Pn):9.3f}{ap:+8.1f}"
          f"{abs(An):9.3f}{Zn.real:+10.0f}{verdict:>10}")

print("\n### (iii) KNIFE EDGE on the AMPLITUDE criterion |u_new|=|u| (idealised boost, pooled sum)")
Lc=-a*Hh                                # the 6b86 lane's contribution to u/T
eps_star=(Gm*np.conj(Lc)).real/abs(Lc)**2
print(f"  lane L = a*H = {abs(Lc):.4f} at {np.angle(Lc,deg=True):+.1f} ; u = {abs(Gm):.4f} at {np.angle(Gm,deg=True):+.1f}")
print(f"  |u+xL| minimised at x = {-eps_star:+.3f}  => optimum boost B* = {1-eps_star:.3f}x , |u| -> {abs(Gm-eps_star*Lc)/abs(Gm):.3f}x")
print(f"  |u+xL| returns to |u| at x = {-2*eps_star:+.3f}  => KNIFE EDGE at B = {1-2*eps_star:.3f}x")
print(f"  proposed design achieves B = {abs(L.H_biquad(*[L.f32(v) for v in L.design_boost(8.05,0.980,300.0)],FC))/abs(Hh):.3f}x")
