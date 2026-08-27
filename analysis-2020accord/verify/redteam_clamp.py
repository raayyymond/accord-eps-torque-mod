"""RED-TEAM R5b: the NEW saturation a flat c4 boost creates, and the DC step bound."""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
c1,c2,c3,c4=struct.unpack_from("<4f",b,0xC60A8)
def H(f):
    z=np.exp(-2j*np.pi*np.asarray(f,float)/1000.); return c4*(1+c3*z+z*z)/(1+c1*z+c2*z*z)
fg=np.linspace(0.05,500,200000); peak=np.abs(H(fg)).max()
print("=== The biquad's OWN output clamp: fVar38 clamped to +-12.0, then *1024 ===")
print(f"  stock peak |H| over 0.05-500 Hz = {peak:.6f}  ->  clamp reachable only if |gp-0x6b82| > {12288/peak:.1f}")
print(f"  gp-0x6b82's own structural range = +-12288 (min(m,0x2FFF) then the limiter, decompile 0x35xxx)")
print("  => HONDA PLACED THE CLAMP EXACTLY AT THE LANE'S OWN CEILING.  It CANNOT bind at k=1.\n")
print(f"  {'k':>6} {'|gp-0x6b82| at which the +-12.0 clamp starts to bind':>52}")
for k in (1.0,1.10,1.25,1.5,1.75,2.0):
    print(f"  {k:6.2f} {12288/(k*peak):52.0f}")
print("\n  A hard clamp on an assist lane = the FLATTEN-A-CURVE-INTO-A-RELAY class")
print("  (BUILD-LINEAGE 'THREE NEW RELAY HAZARDS'; V80 = the worst grinding in this car's history).")
print("  Clip duty is UNCOMPUTABLE: |gp-0x6b82| is not on the wire on ANY of the 13 routes.")

print("\n=== The DC step at engagement (the biquad is ENGAGED-ONLY on V103) ===")
print("  gp-0x6b86 = clamp( k*H*gp-0x6b82 + gp-0x6b7e , +-12288 )   [decompile, 0x35a2c-0x35ad0]")
print("  gp-0x6b7e (the slow EMA recovery of the clipped part) is NOT multiplied by k.")
print("  => step at engagement = (k-1) * |gp-0x6b82|, applied/removed in ONE 1 kHz tick.\n")
print("  measured |u| = |gp-0x6b94| engaged, route 0x85: p50 102.4  p90 499.2  p99 1113.6  max 1587.2 ct")
print(f"  {'k':>6} {'step if |6b82|=100':>19} {'=500':>8} {'=2000':>8} {'=6000':>8} {'=12288':>8}")
for k in (1.25,1.5,1.75,2.0):
    print(f"  {k:6.2f} " + " ".join(f"{(k-1)*v:>8.0f}" for v in (100,500,2000,6000,12288)).rjust(19+8*4))
print("\n  |gp-0x6b82| is UNMEASURED.  V104's spec contains the rung that would measure it")
print("  (b6 = |gp-0x6b86| >= |gp-0x6b82|), which is an admission that it is unknown.")
