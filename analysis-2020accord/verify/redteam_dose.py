"""RED-TEAM R1 + R4 (the decisive tables)."""
import numpy as np, struct, os
D=np.pi/180
def pol(m,d): return m*np.exp(1j*d*D)
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
c1,c2,c3,c4=struct.unpack_from("<4f",b,0xC60A8)
def Hb(f):
    z=np.exp(-2j*np.pi*np.asarray(f,float)/1000.0); return c4*(1+c3*z+z*z)/(1+c1*z+c2*z*z)

u = pol(0.0526,15.4)      # my own re-measure of the pooled SUM at 6-9 Hz (GATE2: 0.0528<15.1)
print("=== R1a  THE OPTIMAL DOSE IS k = 1 + Re(u)/a  -- INVERSELY proportional to 'a' ===")
print(f"   Re(u) = {u.real:.4f}   so  k* = 1 + {u.real:.4f}/a")
print(f"   {'a':>8} {'k* (optimal)':>13} {'k where boost stops helping':>29}")
for a in (0.02,0.03,0.05,0.098,0.15,0.2,0.3,0.5,1.0,1.767,2.0):
    print(f"   {a:8.3f} {1+u.real/a:13.3f} {1+2*u.real/a:29.3f}")

print("\n=== R1b  WHAT IF 'a' IS WRONG?  |u_new|/|u| at 6-9 Hz for the DESIGN dose ===")
print("   (dose is chosen for a = 0.098; the table sweeps the TRUE a)")
hdr=[1.25,1.5,1.52,1.75,2.0]
print(f"   {'true a':>8} " + " ".join(f"{'k='+str(k):>9}" for k in hdr))
for a in (0.02,0.033,0.05,0.098,0.15,0.196,0.25,0.3,0.5,1.0,1.767):
    row=[abs(u-(k-1)*a)/abs(u) for k in hdr]
    flag="  <-- WORSE THAN BASELINE" if any(r>1.0 for r in row) else ""
    print(f"   {a:8.3f} " + " ".join(f"{r:9.3f}" for r in row) + flag)
print("   ASYMMETRY: under-estimating 'a' by 2x turns the k=1.52 dose into a NULL;")
print("              under-estimating by 3x makes 6-9 Hz ~2x WORSE than baseline.")

print("\n=== R4  Price the SAME flat c4 boost in EVERY band, with the structurally-required a >= 0 ===")
print("   a(f) = 0.098 at all f (c4 is frequency-flat; the LERP slope cannot be negative -- ")
print("   enforced by 8 ungated Y[i]=max(Y[i],Y[i-1]) rungs in FUN_000382d8 + 2 in FUN_000389ec).")
SUM={"6-9":(0.0526,15.4,7.5),"15-18":(0.1168,-121.2,16.5),"15-22":(0.2030,-105.1,18.5),
     "21.0-22.5":(0.2616,-99.8,21.7),"22-26":(0.2815,-84.5,24.0)}
Zb={"6-9":(6873,-123.2),"15-18":(1379,108.6),"15-22":(1379,108.6),"21.0-22.5":(1379,108.6),"22-26":(1168,96.8)}
print(f"   {'band':>10} {'fc':>5} {'argdG':>7} {'argZ':>7} {'arg(dGZ)':>9} {'Re(dGZ)':>9} "
      f"{'|u|k=1.25':>10} {'k=1.5':>7} {'k=2.0':>7}  verdict")
for k_,(m,p,fc) in SUM.items():
    uu=pol(m,p); Z=pol(*Zb[k_])
    dG15=-(1.5-1)*0.098*Hb(fc)
    r=[abs(uu-(kk-1)*0.098*Hb(fc))/abs(uu) for kk in (1.25,1.5,2.0)]
    rez=(dG15*Z).real
    print(f"   {k_:>10} {fc:5.1f} {np.angle(dG15,deg=True):+7.1f} {Zb[k_][1]:+7.1f} "
          f"{np.angle(dG15*Z,deg=True):+9.1f} {rez:+9.1f} {r[0]:10.3f} {r[1]:7.3f} {r[2]:7.3f}"
          f"  {'BETTER' if rez>0 else 'MORE ANTI-DAMPING'}")
print("\n   -> BOTH criteria are UNFAVOURABLE at 15-26 Hz.  They do NOT disagree.")
print("      The 'disagreement' in the brief comes from a per-band 'a(f)' solved as NEGATIVE")
print("      (-0.29 to -0.35), which the firmware forbids.  See R1c.")

print("\n=== R1c  THE NEGATIVE CONTROL THE BUDGET-CLOSURE METHOD FAILS ===")
LANE={"6-9":(0.1969,41.8),"15-18":(0.2134,154.2),"15-22":(0.3543,-166.7),
      "21.0-22.5":(0.4397,-153.2),"22-26":(0.3882,-135.7)}
print(f"   {'band':>10} {'a_solved':>10}   structurally admissible (a>=0)?")
for k_ in SUM:
    res=pol(*SUM[k_][:2])-pol(*LANE[k_]); a_s=-res.real
    print(f"   {k_:>10} {a_s:10.4f}   {'YES' if a_s>=0 else 'NO  <-- IMPOSSIBLE'}")
print("   The SAME two-equation closure, run on the SAME four routes with the SAME method,")
print("   returns a NEGATIVE LERP slope in 4 of 5 bands.  It has no internal way to detect this.")
