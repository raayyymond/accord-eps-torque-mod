"""RED-TEAM R5 (corrected): x6b94 is ALREADY signed counts."""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=[0,15,40,80,120,160,200]
def rec(mode,i):
    p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
    return (np.array(struct.unpack_from("<9h",b,p+0x02),float),
            np.array(struct.unpack_from("<9h",b,p+0x14),float))
def lerp_at(mode,vkph,T):
    """speed-blend the two adjacent records, as FUN_000382d8 does."""
    i=int(np.clip(np.searchsorted(SPEEDS,vkph)-1,0,5)
          ) if vkph<200 else 5
    lo,hi=SPEEDS[i],SPEEDS[i+1]; w=(np.clip(vkph,lo,hi)-lo)/(hi-lo)
    X0,Y0=rec(mode,i); X1,Y1=rec(mode,i+1)
    return (1-w)*np.interp(T,X0,Y0)+w*np.interp(T,X1,Y1)

print("=== MEASURED |u| = |gp-0x6b94| (counts), route 0x85 = V100, 4x, packs the SUM ===")
d=np.load("_cache_r85/r85.npz",allow_pickle=True)
u=d["x6b94"].astype(float); eng=d["cc_lat"].astype(bool)
T=np.abs(d["tq"].astype(float))*1.024; v=d["cs_v"].astype(float)*3.6 if d["cs_v"].max()<60 else d["cs_v"].astype(float)
for nm,m in [("ALL",np.ones(len(u),bool)),("ENGAGED",eng),("ENGAGED <20km/h",eng&(v<20)),("ENGAGED >70km/h",eng&(v>70))]:
    s=np.abs(u[m])
    if m.sum()<10: continue
    print(f"  {nm:18s} n={m.sum():6d}  |u| p50 {np.percentile(s,50):7.1f} p90 {np.percentile(s,90):7.1f} "
          f"p99 {np.percentile(s,99):7.1f} max {s.max():7.1f} rms {np.sqrt((s**2).mean()):7.1f}")
print(f"  speed range engaged: {v[eng].min():.1f} - {v[eng].max():.1f} km/h, p50 {np.percentile(v[eng],50):.1f}")

print("\n=== THE LANE BEING MULTIPLIED: static value m(|T|) from the ROM map (Branch-A scale) ===")
print("   (Branch B applies an extra SCALE that is NOT resolved; Branch-A is the same ROM record,")
print("    and Branch B's own per-segment slope cap cal(0xC6384)=2.000 forbids it being ~0.098.)")
Tq=[100,178,396,894,1608,3186,8192]
print(f"   {'|T| ct':>8} " + " ".join(f"{s:>8}" for s in ["v=0","v=15","v=40","v=80","v=120"]))
for t in Tq:
    row=[lerp_at(24,s,t) for s in [0,15,40,80,120]]
    print(f"   {t:8d} " + " ".join(f"{r:8.0f}" for r in row))

print("\n=== THE STEP A FLAT c4 BOOST PUTS ON THE AGGREGATOR, engaged-only ===")
print("   step = (k-1) * m(|T|).  Compare against measured |u| p50/p90/p99 above.")
up50,up90,up99=[np.percentile(np.abs(u[eng]),q) for q in (50,90,99)]
for k in (1.25,1.5,1.75,2.0):
    for t,lab in [(178,"|T| p50"),(894,"|T| rms"),(1608,"|T| p90")]:
        m=lerp_at(24,15,t); st=(k-1)*m
        print(f"   k={k:4.2f} {lab:8s} m={m:7.0f} ct -> step {st:7.0f} ct "
              f"= {st/up50:6.1f}x |u|p50  {st/up90:5.2f}x |u|p90  {st/up99:5.2f}x |u|p99")
print(f"\n   For reference the INTENDED in-band effect: (k-1)*a*|T_s| with a=0.098, |T_s|=396.4 (6-9Hz RMS)")
for k in (1.25,1.5,1.75,2.0):
    print(f"   k={k:4.2f} -> {(k-1)*0.098*396.4:7.1f} ct of 6-9 Hz change  (band |u| = {0.0528*396.4:.1f} ct)")
