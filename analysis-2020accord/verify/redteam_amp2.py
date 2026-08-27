"""RED-TEAM R6 + R2, corrected sign.
dG_boost = (k*H - H)*(gp6b82/T) = (k-1)*H*(-a) = -(k-1)*a*H   -> arg ~ +169.4 deg  [matches GATE2]
dG_null  = (0   - H)*(-a)       = +a*H                        -> arg ~  -10.6 deg  [matches GATE2 -461]
"""
import numpy as np
D=np.pi/180
def pol(m,d): return m*np.exp(1j*d*D)
G0_pooled=pol(0.0528,15.1); G0_r85=pol(0.0485,17.0); A0=pol(0.440,25.0)
a=0.098; H8=0.98861*np.exp(1j*(-10.61)*D); Z=pol(6873,-123.2)
def dG_boost(k,a=a): return -(k-1)*a*H8
def amp(k,A0=A0,G0=G0_pooled,a=a):
    kap=(A0-1.0)/G0
    return 1.0/abs(A0+kap*dG_boost(k,a))

print("=== R6.2 CORRECTED: 1/|A| vs k   (baseline 1/0.440 = 2.273) ===")
print(f"  {'k':>5} {'brief':>7} {'mine(pooled)':>13} {'mine(r85 kappa)':>16}")
brief={1.25:1.55,1.52:1.08,1.75:0.85,2.00:0.67}
for k in (1.0,1.25,1.5,1.52,1.75,2.0,2.5,3.0,4.0):
    print(f"  {k:5.2f} {brief.get(k,float('nan')):7.2f} {amp(k):13.3f} {amp(k,G0=G0_r85):16.3f}")
print("  -> the brief's ladder is REPRODUCED to within 2-8 %.  R6's central arithmetic SURVIVES.")

print("\n=== R6.3 CORRECTED worst case: |A0| in {0.183,0.440,0.570} x arg(A0) sweep ===")
print(f"  {'|A0|':>6} {'argA0':>6} {'|kG|':>6} " + " ".join(f"{k:>7}" for k in (1.0,1.25,1.5,1.75,2.0)) + "  verdict")
rel={}
for mA in (0.183,0.440,0.570):
    for ph in (-30,-10,0,10,25,40,60,80,100,120):
        A=pol(mA,ph); P0=A-1
        if not (0.512<=abs(P0)<=1.001): continue     # the published |kG| CI
        row=[amp(k,A0=A) for k in (1.0,1.25,1.5,1.75,2.0)]
        bad=any(r>row[0]*1.02 for r in row[1:])
        for k,r in zip((1.25,1.5,1.75,2.0),row[1:]): rel.setdefault(k,[]).append(r/row[0])
        print(f"  {mA:6.3f} {ph:6.0f} {abs(P0):6.3f} "+" ".join(f"{r:7.3f}" for r in row)
              +("  <-- WORSE" if bad else "  ok"))
print("\n  relative 6-9 Hz amplification vs that corner's own baseline:")
for k in (1.25,1.5,1.75,2.0):
    v=np.array(rel[k]); print(f"    k={k:4.2f}: best {v.min():.3f}x  worst {v.max():.3f}x  ({(v>1).sum()}/{len(v)} corners WORSE)")

print("\n=== R3b  Does using the MEASURED A = 0.44 flip Re(dG*Z)? ===")
for nm,dG in [("NULL (notch)",a*H8),("BOOST x1.44",dG_boost(1.44)),("BOOST x1.52",dG_boost(1.52)),
              ("BOOST x2.00",dG_boost(2.0))]:
    v1=(dG*Z).real; vA=(dG*Z/A0).real; vA2=(dG*Z/A0**2).real
    print(f"  {nm:14s} arg(dG) {np.angle(dG,deg=True):+7.1f}  Re(dG*Z) {v1:+9.1f}   "
          f"Re(dG*Z/A) {vA:+9.1f}   Re(dG*Z/A^2) {vA2:+9.1f}")
print("  arg(dG*Z)     = %+.1f deg  (favourable window is +-90)" % np.angle(dG_boost(1.5)*Z,deg=True))
print("  arg(dG*Z/A)   = %+.1f deg" % np.angle(dG_boost(1.5)*Z/A0,deg=True))
print("  arg(dG*Z/A^2) = %+.1f deg  <-- the textbook closed-loop sensitivity uses 1/A^2" % np.angle(dG_boost(1.5)*Z/A0**2,deg=True))

print("\n=== R2 CORRECTED: SUM-phase sensitivity ===")
LANE=pol(0.1982,41.4)
print(f"  {'dphi':>6} {'a':>8} {'|r24+26| ct':>12} {'1/|A| k=1.25':>13} {'k=1.5':>8} {'k=2.0':>8} {'argdG*Z':>9}")
for dphi in (-30,-20,-15,-10,0,10,15,20,30):
    G=pol(0.0528,15.1+dphi); res=G-LANE; aa=-res.real; r=-res.imag
    A=A0; kap=(A-1)/G
    row=[1/abs(A+kap*dG_boost(k,aa)) for k in (1.25,1.5,2.0)]
    print(f"  {dphi:+6.0f} {aa:8.4f} {r*396.4:12.1f} {row[0]:13.3f} {row[1]:8.3f} {row[2]:8.3f} "
          f"{np.angle(dG_boost(1.5,aa)*Z,deg=True):+9.1f}")
