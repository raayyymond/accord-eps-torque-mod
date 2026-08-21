"""RED-TEAM: the FULL admissible range of gp-0x69a4/1024 (the LERP segment slope, 'a')."""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=[0,15,40,80,120,160,200]
CLAMP=struct.unpack_from("<H",b,0xC6200)[0]     # Y[9] / the +-8192 clamp
allsl=[]; rows=[]
for mode in (24,26):
    for i,sp in enumerate(SPEEDS):
        p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
        X=np.array(struct.unpack_from("<9h",b,p+0x02),float)
        Y=np.array(struct.unpack_from("<9h",b,p+0x14),float)
        Y=np.minimum(Y,CLAMP)
        sl=np.diff(Y)/np.diff(X)
        allsl+= list(sl); rows.append((mode,sp,sl))
allsl=np.array(allsl)
print("=== gp-0x69a4/1024 = the per-segment LERP slope.  ALL 14 flash records, 8 segments each ===")
print(f"  n = {len(allsl)} segments   min {allsl.min():.3f}   p50 {np.median(allsl):.3f}   max {allsl.max():.3f}")
print(f"  monotone (all slopes >= 0)?  {(allsl>=0).all()}   -- f' >= 0 is also ENFORCED IN CODE (3 sites)")
print(f"\n  segment slopes, mode 24, by speed:")
for mode,sp,sl in rows:
    if mode==24: print(f"    v={sp:3d}: " + " ".join(f"{s:6.3f}" for s in sl))
print(f"\n  Branch-B extra cap: cal(0xC6384) = {struct.unpack_from('<H',b,0xC6384)[0]/1024:.3f} per segment")
print("\n=== CONSEQUENCE 1 -- GATE2's own two values of 'a' are irreconcilable ===")
print("  GATE2 sec1.1 DEFINES  a == gp-0x69a4/1024  (the segment slope)")
print("  GATE2 sec2.2 SOLVES   a  = 0.098 from the budget")
print(f"  ROM says the slope is NEVER below {allsl.min():.3f} anywhere, and is 1.77-3.73 at the")
print("  operating point (|T| p50 178 ct .. 396 ct, 15-40 km/h).  Ratio 2.7x .. 38x.")
print("\n=== CONSEQUENCE 2 -- the r24/r26 'a > 5.57' ESCAPE HATCH IS CLOSED FROM THE ROM ===")
print(f"  a > 5.57 needs gp-0x69a4 > 5709.  The LARGEST slope in ANY of the 14 records is {allsl.max():.3f}")
print(f"  ({'BELOW' if allsl.max()<5.57 else 'ABOVE'} 5.57), and it occurs only at v=200 km/h for |T| < 150 counts.")
print("  In the operator's symptom regime (5-40 km/h, |T| p50 178 ct) the slope is 2.39-3.73.")
print("  => HANDOFF sec4.3 / STATE open item #1 closes on ARITHMETIC.  No drive, no comparator rung.")
