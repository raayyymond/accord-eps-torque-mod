"""RED-TEAM R6 + R2: independent re-derivation of kappa, |A(k)|, and the phase sensitivity."""
import numpy as np
D=np.pi/180
def pol(m,d): return m*np.exp(1j*d*D)

# --- inputs, all from docs/review/GATE2-2026-08-20-notch-sign.md + HANDOFF-2026-08-21 sec 3
G0_pooled = pol(0.0528, 15.1)     # u/T_s pooled (r85 sum + r95 sum)
G0_r85    = pol(0.0485, 17.0)     # r85 alone (the ONLY route whose 427 lane is u AND the kappa solve's arm)
A0        = pol(0.440 , 25.0)     # 1 + kappa*G, from the 4x/8x step
a         = 0.098                 # lane gain, SOLVED not measured
H8        = 0.98861*np.exp(1j*(-10.61)*D)   # Honda's section at ~8 Hz (computed from the flash floats)
Z         = pol(6873, -123.2)

def amp(k, A0=A0, G0=G0_pooled, a=a, argdG=None):
    P0 = A0 - 1.0
    kap = P0/G0
    dG = (k-1)*a*H8
    if argdG is not None: dG = abs(dG)*np.exp(1j*argdG*D)
    return 1.0/abs(A0 + kap*dG)

print("=== R6.1  Re-derivation of kappa ===")
for nm,G0 in [("pooled 0.0528<15.1",G0_pooled),("r85 0.0485<17.0",G0_r85)]:
    P0=A0-1; kap=P0/G0
    print(f"  G0={nm:22s}  P0 = {abs(P0):.4f}<{np.angle(P0,deg=True):+.1f}   "
          f"|kappa| = {abs(kap):.3f} <{np.angle(kap,deg=True):+.1f}")
print("  (handoff sec 3.2 states |c| = 13.09 for dP = c*dG -> matches the r85 arm)")

print("\n=== R6.2  Amplification 1/|A| vs boost k  (baseline 1/0.440 = %.3f) ===" % (1/0.44))
print(f"  {'k':>5} {'brief':>7} {'mine(pooled)':>13} {'mine(r85)':>10} {'arg(dG)=180':>12}")
brief={1.25:1.55,1.52:1.08,1.75:0.85,2.00:0.67}
for k in (1.25,1.5,1.52,1.75,2.0,2.5,3.0):
    print(f"  {k:5.2f} {brief.get(k,float('nan')):7.2f} {amp(k):13.3f} {amp(k,G0=G0_r85):10.3f} "
          f"{amp(k,argdG=180):12.3f}")

print("\n=== R6.3  WORST CASE: sweep arg(A0) and |A0| (leave-one-out swing 0.183 / 0.440 / 0.570) ===")
print("  |A0| swing is ON RECORD; arg(A0) has NO published CI.  Sweeping it is the honest test.")
print(f"  {'|A0|':>6} {'arg(A0)':>8} " + " ".join(f"{k:>7}" for k in (1.0,1.25,1.5,1.75,2.0)) + "   verdict")
worst={}
for mA in (0.183,0.440,0.570):
    for ph in (-20,0,10,25,40,43,50,60,80,100):
        A=pol(mA,ph); P0=A-1
        if not (0.40 <= abs(P0) <= 1.10):   # keep |kappa*G| loosely inside the CI [0.512,1.001]
            continue
        row=[amp(k,A0=A) for k in (1.0,1.25,1.5,1.75,2.0)]
        base=row[0]; bad = any(r>base*1.02 for r in row[1:])
        for k,r in zip((1.25,1.5,1.75,2.0),row[1:]):
            worst.setdefault(k,[]).append(r/base)
        print(f"  {mA:6.3f} {ph:8.0f} " + " ".join(f"{r:7.3f}" for r in row)
              + ("   <-- BOOST MAKES 6-9 Hz WORSE" if bad else "   ok"))
print("\n  relative amplification (vs that corner's own baseline), min..max over the corners:")
for k in (1.25,1.5,1.75,2.0):
    v=np.array(worst[k]); print(f"    k={k:4.2f}:  best {v.min():.3f}x   worst {v.max():.3f}x")

print("\n=== R2  How much does the SUM's PHASE matter?  (2 and 3 episodes; NO real CI exists) ===")
print("  The sum phase enters twice: (i) it sets arg(kappa)=arg(P0)-arg(G0); (ii) it sets the")
print("  residual, hence 'a' and 'r24+r26' in the budget decomposition.")
LANE = pol(0.1982, 41.4)
print(f"  {'dphi':>6} {'a solved':>9} {'|r24+r26|':>10} {'ct r24+26':>10} {'1/|A| k=1.5':>12} {'k=2.0':>8}")
for dphi in (-30,-20,-15,-10,0,10,15,20,30):
    G=pol(0.0528, 15.1+dphi)
    res = G - LANE
    aa = -res.real            # gp-0x6b86 at angle 180 -> real part is -a
    r  = -res.imag            # r24+r26 at -90 -> imag part is -|r|
    print(f"  {dphi:+6.0f} {aa:9.4f} {r:10.4f} {r*396.4:10.1f} "
          f"{amp(1.5,G0=G,a=max(aa,1e-6)):12.3f} {amp(2.0,G0=G,a=max(aa,1e-6)):8.3f}")
print("  (brief-supplied independent bound on |r24+r26| is 40-61 ct)")

print("\n=== R3-adjacent: does using the MEASURED A = 0.44 instead of A ~ 1 flip Re(dG*Z)? ===")
for nm,k in [("NULL (notch)",0.0),("BOOST x1.44",1.44),("BOOST x1.50",1.50),("BOOST x2.0",2.0)]:
    dG = (k-1)*a*H8 if k>0 else (0-1)*a*H8*(-1)   # null: dG = +a*H
    if k==0.0: dG = a*H8
    for lbl,Aq in [("A=1",1.0+0j),("A=A0",A0)]:
        val=(dG*Z/Aq).real
        print(f"  {nm:14s} {lbl:5s}  Re(dG*Z/A) = {val:+9.1f}")
