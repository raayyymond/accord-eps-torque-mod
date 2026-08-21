"""Verify the proposed boost design and compute dG / Re(dG.Z) at 8 Hz and 21.7 Hz."""
import numpy as np, _gate2_boost_lib as L
HO=L.honda_exact()

def rpt(a1,a2,b1,g,name):
    f=np.geomspace(0.1,500,20001)
    H=L.H_biquad(a1,a2,b1,g,f)
    i=np.argmax(np.abs(H))
    p=np.roots([1,a1,a2]); z=np.roots([1,b1,1])
    print(f"--- {name}: a1={a1:.9f} a2={a2:.9f} b1={b1:.9f} g={g:.9f}")
    print(f"    poles |r|={abs(p[0]):.6f} @ {abs(np.angle(p[0]))/(2*np.pi)*1000:.4f} Hz | "
          f"zeros |r|={abs(z[0]):.6f} @ {abs(np.angle(z[0]))/(2*np.pi)*1000:.4f} Hz")
    print(f"    DC={abs(L.H_biquad(a1,a2,b1,g,0.0)):.6f}  peak|H| 0.1-500 = {20*np.log10(abs(H[i])):+.3f} dB @ {f[i]:.2f} Hz"
          f"   tau_ring={-1/(1000*np.log(abs(p[0])))*1000:.2f} ms")
    for ff in [3,6,7.4,8.05,9,15,21.0,21.73,22.5,23,26]:
        h=L.H_biquad(a1,a2,b1,g,ff)
        print(f"      {ff:6.2f} Hz  |H|={abs(h):.5f}  {20*np.log10(abs(h)):+7.2f} dB  {np.angle(h,deg=True):+7.2f} deg")
    return

print("=== HONDA STOCK (baseline as flown on V103) ===")
rpt(*HO,'honda')
print()
print("=== PROPOSED BOOST: poles 8.05 Hz r=0.980, zero parked 300 Hz ===")
D=L.design_boost(8.05,0.980,300.0)
Df=tuple(L.f32(v) for v in D)
print("   float32 LE bytes:", [L.le_bytes(v) for v in D])
rpt(*Df,'boost f0=8.05 r=0.980 zero@300')
print()
print("   brief quoted:  a1=-1.957493400 a2=+0.960400000 b1=+0.618033989 g=+0.001110222")
print("   my design   :  a1=%.9f a2=%.9f b1=%.9f g=%.9f"%D)

# ---------------- sign arithmetic
print("\n\n================ SIGN ARITHMETIC ================")
Z89  = -3761 + 1j*5752*-1     # measured r9e 6-9 Hz  (Re,Im)
Z89  = complex(-3761,-5752)
Z217 = complex(-349, 1211)    # measured r9e 21.0-22.5 Hz
print(f"Z(6-9)     = {abs(Z89):.0f} at {np.angle(Z89,deg=True):+.1f} deg   Re={Z89.real:.0f}")
print(f"Z(21-22.5) = {abs(Z217):.0f} at {np.angle(Z217,deg=True):+.1f} deg   Re={Z217.real:.0f}")

for fc,Z,lab in [(8.0,Z89,'8.0 Hz  (6-9 band Z)'),(21.73,Z217,'21.73 Hz (21-22.5 band Z)')]:
    Ho=L.H_biquad(*HO,fc); Hn=L.H_biquad(*Df,fc)
    dH=Hn-Ho
    print(f"\n--- {lab}")
    print(f"    H_honda = {abs(Ho):.5f} at {np.angle(Ho,deg=True):+.2f} deg")
    print(f"    H_new   = {abs(Hn):.5f} at {np.angle(Hn,deg=True):+.2f} deg   ({20*np.log10(abs(Hn)/abs(Ho)):+.2f} dB vs honda)")
    print(f"    dH      = {abs(dH):.5f} at {np.angle(dH,deg=True):+.2f} deg")
    for a in [0.05,0.098,0.117,0.3,0.644]:
        dG = -a*dH                       # dG = d(u/T) = (H_new-H_old)*(gp-0x6b82/T) = (H_new-H_old)*(-a)
        v  = (dG*Z).real
        print(f"      a={a:5.3f}  dG={abs(dG):.5f} at {np.angle(dG,deg=True):+7.2f} deg   "
              f"arg(dG)+arg(Z)={np.angle(dG,deg=True)+np.angle(Z,deg=True):+8.2f} deg   Re(dG.Z)={v:+9.1f}  "
              f"{'BETTER (less anti-damping)' if v>0 else 'WORSE (more anti-damping)'}")
    # the sign is a-invariant; state the arg window
    argZ=np.angle(Z,deg=True); argdG=np.angle(-dH,deg=True)
    print(f"    SIGN IS INDEPENDENT OF a (a>0 real).  arg(dG)={argdG:+.2f}, arg(Z)={argZ:+.2f}, sum={argdG+argZ:+.2f} deg")
    lo=-90-argZ; hi=90-argZ
    print(f"    favourable iff arg(dG) in ({lo:+.1f},{hi:+.1f}) deg (mod 360)")
