"""RED-TEAM R0: the gp-0x6b7e pedestal path -- read its rate table, price its 6-9 Hz transfer."""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
TP=0xBF000
assert b[0xC60A8:0xC60AC].hex()=="f8c2c4bf", "anchor"
print("=== the EMA rate LERP (from the decompile: X @tp+0x78fe..0x7904, Y @tp+0x7906..0x790c) ===")
for nm,off in [("X0",0x78fe),("X1",0x7900),("X2",0x7902),("X3",0x7904),
               ("Y0",0x7906),("Y1",0x7908),("Y2",0x790a),("Y3",0x790c)]:
    a=TP+off; print(f"   {nm}  tp+0x{off:04x} = 0x{a:X} = {struct.unpack_from('<H',b,a)[0]}")
print(f"   raw 0xC68F8..0xC6914: {b[0xC68F8:0xC6914].hex()}")
print(f"\n   cal(0xC6382) (the GATED alternative rate) = {struct.unpack_from('<H',b,0xC6382)[0]}")
print("   its gate is (iVar14 != 0 AND gp-0x6b62 != 0).  gp-0x6b62 != 0 has MEASURED duty")
print("   0.0000 over 75,227 engaged frames [memory: accord-return-centre-and-detent-dead-engaged]")
print("   => ENGAGED, the rate ALWAYS comes from the LERP.  0xC6382 is unreachable engaged.")

alphas=sorted({struct.unpack_from('<H',b,TP+o)[0] for o in (0x7906,0x7908,0x790a,0x790c)})
print("\n=== the pedestal's own transfer:  y[n] = y[n-1] + (x[n]-y[n-1])*alpha,  alpha = rate/2048 ===")
print("   (clamped to [2,204] at 0x359c2-0x359d4)")
print(f"   {'rate':>6} {'alpha':>9} {'corner Hz':>10} {'|H| @7.5Hz':>11} {'phase':>8} {'|H| @21.7':>10}")
for r in sorted(set(list(alphas)+[2,20,204])):
    al=r/2048.0
    def Hema(f):
        z=np.exp(-2j*np.pi*f/1000.0); return al/(1-(1-al)*z)
    print(f"   {r:6d} {al:9.6f} {al*1000/(2*np.pi):10.3f} {abs(Hema(7.5)):11.4f} "
          f"{np.angle(Hema(7.5),deg=True):+8.1f} {abs(Hema(21.7)):10.4f}")

print("\n=== R0: the lane splits into TWO paths with DIFFERENT k-sensitivity ===")
print("   gp-0x6b86 = clamp( k*H(z)*gp-0x6b82  +  gp-0x6b7e , +-12288 )")
print("   bVar3 = (thr < |gp-0x6b7a|)  is the MAGNITUDE-LIMITER flag, decided EVERY TICK.")
print()
print("   REGIME A  (limiter OFF, bVar3=0):  gp-0x6b82 = gp-0x6b7a  and  gp-0x6b84 = 0")
print("             => the pedestal DECAYS TO ZERO;  a_filt/a = 1.000 EXACTLY")
print("             => but then the lane's own slope is the ROM MAP SLOPE, 1.77-3.73, not 0.098")
print("   REGIME B  (limiter hard-saturated): gp-0x6b82 pinned => carries NO ac")
print("             => a_filt/a -> 0;  ALL ac goes via the pedestal at |H_ema| and ~-77 deg")
alpha=20/2048.
def Hema(f):
    z=np.exp(-2j*np.pi*f/1000.0); return alpha/(1-(1-alpha)*z)
print(f"             at alpha=20/2048: pedestal passes {abs(Hema(7.5)):.4f} of the residual at 7.5 Hz,")
print(f"             phase {np.angle(Hema(7.5),deg=True):+.1f} deg  => the lane would sit near QUADRATURE,")
print("             not at GATE2's assumed 180 deg -- which breaks the budget decomposition itself.")

print("\n=== the k required, vs a_filt/a  (k* = 1 + Re(u)/(a*(a_filt/a)),  Re(u)=0.0507, a=0.098) ===")
Reu=0.0507; a=0.098
print(f"   {'a_filt/a':>9} {'k* needed':>10} {'k where it stops helping':>25} {'|6b82| where +-12.0 bites':>26}")
for fr in (1.0,0.7,0.5,0.3,0.2,0.1):
    ks=1+Reu/(a*fr); print(f"   {fr:9.2f} {ks:10.3f} {1+2*Reu/(a*fr):25.3f} {12288/ks:26.0f}")
print("\n   BUILDABILITY BOUND: gp-0x6b82's structural ceiling is 12288, and the +-12.0 float clamp")
print("   bites at 12288/k.  A dose is only 'clean' if k <= 12288/max|gp-0x6b82| in the regime.")
print("   k=1.85 bites at 6642 = 54.0 % of the lane's range;  k=3.02 (a_filt/a=0.3) bites at 4069 = 33 %.")
print("   => the lever stops being buildable somewhere around a_filt/a ~ 0.3-0.5 REGARDLESS of sign.")
