"""RED-TEAM R0b / R8 at k=1.85: when does the +-12.0 clamp actually bite?"""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
assert b[0xC60A8:0xC60AC].hex()=="f8c2c4bf"
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=np.array([0,15,40,80,120,160,200.])
def rec(mode,i):
    p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
    return (np.array(struct.unpack_from("<9h",b,p+0x02),float),
            np.array(struct.unpack_from("<9h",b,p+0x14),float))
R24=[rec(24,i) for i in range(7)]
CLAMP=struct.unpack_from("<H",b,0xC6200)[0]

print("=== THE HARD CEILING ON |gp-0x6b82| FROM THE ROM ===")
print(f"  |Tc| = |clamp(gp-0x4f60, +-cal(0xC6200))| = +-{CLAMP}  (0x354ce)")
print("  X[9] of every record is 6000-14490 > 8192  =>  |Tc| NEVER exceeds X[9]  =>  the")
print("  extrapolation branch (rise = a*(|Tc|-X[9])) is UNREACHABLE, and m <= Y(8192).")
print(f"  {'v km/h':>7} {'X[9]':>7} {'m(8192) = the lane ceiling':>27}")
for i,sp in enumerate(SPEEDS):
    X,Y=R24[i]; print(f"  {sp:7.0f} {X[-1]:7.0f} {np.interp(8192.,X,Y):27.0f}")
mmax=max(np.interp(8192.,*R24[i][::1]) if False else np.interp(8192.,R24[i][0],R24[i][1]) for i in range(7))
print(f"  => m <= {mmax:.0f} counts anywhere in the ROM (200 km/h); <= 5081 at <=80 km/h.")
print(f"\n  The +-12.0 float clamp bites at |gp-0x6b82| > 12288/k:")
for k in (1.25,1.5,1.85,2.0,2.088,2.42,3.0):
    print(f"    k={k:5.3f} -> {12288/k:7.0f}   {'BITES' if 12288/k < mmax else 'UNREACHABLE (m_max=%.0f)'%mmax}")
print("  => AT k = 1.85 THE CLAMP CANNOT BITE, at any speed or torque, IF the Branch-B table")
print("     shares Branch-A's scale.  First bite is k = 2.088 (200 km/h) / 2.42 (<=80 km/h).")
print("\n  CONTRA, and it is not resolvable from here: Honda wrote  min(m, 0x3000) = min(m,12288)")
print("  at 0x355d4-0x355e0.  A ceiling of 12288 on a quantity that structurally maxes at 5886")
print("  is dead code.  Either the min is defensive boilerplate, or Branch-B's untraced SCALE")
print("  makes m_B > m_A.  ONLY A MEASUREMENT OF |gp-0x6b82| SETTLES IT.")

print("\n=== IF the Branch-A scale holds: clamp duty on the REAL drives, k = 1.85 ===")
def m_of(T,v):
    i=np.clip(np.searchsorted(SPEEDS,v)-1,0,5); w=(np.clip(v,SPEEDS[i],SPEEDS[i+1])-SPEEDS[i])/(SPEEDS[i+1]-SPEEDS[i])
    out=np.empty_like(T)
    for j in range(7):
        pass
    lo=np.array([np.interp(t,R24[a][0],R24[a][1]) for t,a in zip(T,i)])
    hi=np.array([np.interp(t,R24[a+1][0],R24[a+1][1]) for t,a in zip(T,i)])
    return (1-w)*lo+w*hi
for tag in ("r85","r95","r96","r9e"):
    d=np.load(f"_cache_{tag}/{tag}.npz",allow_pickle=True)
    e=d["cc_lat"].astype(bool)
    T=np.minimum(np.abs(d["tq"].astype(float))*1.024,8192.)[e]
    v=d["cs_v"].astype(float)[e]; v=v*3.6 if v.max()<60 else v
    m=m_of(T,v)
    print(f"  {tag}: n={e.sum():6d}  m p50 {np.percentile(m,50):6.0f} p99 {np.percentile(m,99):6.0f} "
          f"max {m.max():6.0f}  frac(m>6642) = {(m>6642).mean():.6f}   frac(m>12288) = {(m>12288).mean():.6f}")

print("\n=== THE LINEARITY QUESTION AT k=1.85 (R8) ===")
print("  The clamp acts on the TOTAL (DC pedestal + ac), not the ac alone, and an assist lane is")
print("  DC-dominant.  So it is NOT a smooth describing function -- it is a HARD REGIME SWITCH:")
print("      |gp-0x6b82| < 12288/k :  lever fully ON,  incremental gain exactly k   (LINEAR)")
print("      |gp-0x6b82| > 12288/k :  output PINNED,   incremental gain exactly 0   (LEVER OFF)")
print("  A(k) is a straight line in the first regime and FROZEN AT A(1) in the second.")
print("  => the monotonicity / 'no bad corner' result is EXACT where the clamp does not bite")
print("     and VACUOUS where it does.  It never inverts -- the lever just stops existing.")
print("  => the nasty trap the orchestrator feared (safest dose = least valid model) does NOT")
print("     materialise for a SYMMETRIC clamp.  It WOULD have for the half-clamp, which is refuted.")
