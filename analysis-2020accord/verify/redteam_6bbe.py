"""RED-TEAM: attack the gp-0x6bbe challenger.  Read its REAL cals; price it against u."""
import numpy as np, struct, os
D=np.pi/180
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
assert b[0xC60A8:0xC60AC].hex()=="f8c2c4bf"
TP=0xBF000
def u32(a): return struct.unpack_from("<I",b,a)[0]
def u16(a): return struct.unpack_from("<H",b,a)[0]
def s16(a): return struct.unpack_from("<h",b,a)[0]

print("=== FUN_00034a72's mode-indexed pointer arrays, modes 24 and 26 ===")
for nm,base in [("K1  PTR_DAT_000ca324",0xCA324),("clampBound PTR_DAT_000c7a58",0xC7A58),
                ("finalBound PTR_DAT_000c7970",0xC7970),("targetLERP DAT_000ca23c",0xCA23C),
                ("rateGain PTR_LAB_000ca154",0xCA154),("blend PTR_DAT_000ca06c",0xCA06C),
                ("byteGain PTR_DAT_000ca40c",0xCA40C),("errLERP DAT_000ca4f4",0xCA4F4)]:
    row=[]
    for m in (24,26):
        p=u32(base+m*4); row.append((m,p))
    print(f"  {nm:30s} m24 -> 0x{row[0][1]:X}   m26 -> 0x{row[1][1]:X}")

print("\n=== K1 (sVar7 = *(short*)ptr) ===")
for m in (24,26):
    p=u32(0xCA324+m*4); print(f"  mode {m}: ptr 0x{p:X}  K1 = {s16(p)}   (first 8 shorts: "
          f"{[s16(p+2*i) for i in range(8)]})")
print("\n=== the SATURATING clamp on the K1 product: **(ushort**)(PTR_DAT_000c7a58 + mode*4) ===")
for m in (24,26):
    p=u32(0xC7A58+m*4); print(f"  mode {m}: ptr 0x{p:X}  bound = {u16(p)}")
print("\n=== the FINAL bound: LERP over PTR_DAT_000c7970[mode], keyed on gp-0x6a62 ===")
for m in (24,26):
    p=u32(0xC7970+m*4)
    X=[u16(p+2+2*i) for i in range(5)]; Y=[u16(p+0xc+2*i) for i in range(5)]
    print(f"  mode {m}: ptr 0x{p:X}  X {X}  Y {Y}")
print(f"  fallback when gp-0x6a62 > 32000:  cal(tp+0x715a) = 0x{TP+0x715a:X} = {u16(TP+0x715a)}")

print("\n=== SIZING: price a k-x boost of gp-0x6bbe against the MEASURED sum ===")
u=0.0526*np.exp(1j*15.4*D)                     # my pooled re-measure
Z=6873*np.exp(1j*-123.2*D)
# V92 measured gp-0x6bbe vs WHEEL RATE: 92.0 ct/(rad/s) at +13.9 deg, 6-9 Hz
L = (92.0*np.exp(1j*13.9*D)) / Z               # -> counts of 6bbe per count of driver torque
print(f"  gp-0x6bbe / T_s at 6-9 Hz = |{abs(L):.4f}| < {np.angle(L,deg=True):+.1f} deg")
print(f"    (from V92's 92.0 ct/(rad/s) < +13.9 deg divided by Z = 6873 < -123.2)")
print(f"  it is {abs(L)/abs(u)*100:.0f} % of the SUM's magnitude, and {abs(L)/0.1173*100:.0f} % of the")
print(f"    'r24+r26(+6bbe)' quadrature bucket it was ASSUMED into.")
A0=0.440*np.exp(1j*25*D); kap=(A0-1)/(0.0528*np.exp(1j*15.1*D))
print(f"\n  {'k':>6} {'K1':>5} {'|u_new|/|u|':>12} {'1/|A|':>8} {'lane p99 ct':>12} {'max ct':>8} {'clips?':>7}")
for k in (1.0,1.3,1.5,2.0,3.11,5.0,10.0):
    un=abs(u+(k-1)*L)/abs(u); A=A0+kap*(k-1)*L
    p99=268.8*k; mx=390.4*k
    print(f"  {k:6.2f} {43*k:5.0f} {un:12.3f} {1/abs(A):8.3f} {p99:12.0f} {mx:8.0f} "
          f"{'YES' if mx>512 else 'no':>7}")
# optimum
eps=-( (u*np.conj(L)).real )/abs(L)**2
print(f"\n  BEST POSSIBLE at 6-9 Hz: k* = {1+eps:.3f}  ->  |u| ratio {abs(u+eps*L)/abs(u):.3f}")
print(f"  (the lane sits {abs(np.angle(u/L,deg=True)):.0f} deg off u, so it can only cancel the projection)")
print(f"  compare: the c4 boost reaches 0.27x because gp-0x6b86 sits ~165 deg from u.")
print("\n=== the +-512 headroom claim, checked against the MEASURED lane distribution (V92, route 79) ===")
print("  memory accord-gp6bbe-is-viscous-plus-dc-pedestal: engaged & moving |gp-0x6bbe|")
print("  p50 76.8 · p90 144.0 · p99 268.8 · MAX 390.4 · nonzero 99.40 %")
for lim in (512,):
    print(f"  => clips at k = {lim/390.4:.2f} (observed max), {lim/268.8:.2f} (p99), {lim/144.0:.2f} (p90)")
print("  The quoted '~6x headroom' used 20-79 ct = the VISCOUS PART in the 13-50 deg/s band,")
print("  NOT the measured lane, which carries a ~74 ct DC PEDESTAL on top.  GATE 3 violation.")
