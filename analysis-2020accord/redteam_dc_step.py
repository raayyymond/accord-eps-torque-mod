"""RED-TEAM R5/R1: what does a FLAT c4 boost actually do?

1. Show c4-scaling == a flat k-x gain on the whole lane (the biquad is a red herring).
2. Read the ROM assist map, get the STATIC slope + the STATIC lane value at the operating point.
3. Compare to the measured aggregator sum |u| from route 0x85 (V100 packed gp-0x6b94).
"""
import numpy as np, struct, os, json
P = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
b = open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()

def H(c1,c2,c3,c4,f,fs=1000.0):
    z=np.exp(-2j*np.pi*np.asarray(f,float)/fs)
    return c4*(1+c3*z+z*z)/(1+c1*z+c2*z*z)
c1,c2,c3,c4 = struct.unpack_from("<4f", b, 0xC60A8)

print("=== 1. IS c4 A FLAT GAIN? |H| of Honda's shipped section ===")
ff=np.array([0.1,0.5,1,2,4,6,7.79,9,12,15,21,23,26,30,42.3,50,55.2,60,100,200,400,500])
h=H(c1,c2,c3,c4,ff)
for f,v in zip(ff,h):
    print(f"  {f:6.2f} Hz  |H| {abs(v):9.6f}  ({20*np.log10(abs(v)):+7.3f} dB)  {np.angle(v,deg=True):+8.2f} deg")
print(f"  DC gain = {abs(H(c1,c2,c3,c4,1e-9)):.6f}")
print("  -> scaling c4 by k scales |H| by EXACTLY k at every f (c4 is a pure scalar in the numerator).")

print("\n=== 2. THE ROM ASSIST MAP: static slope at the operating point ===")
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=[0,15,40,80,120,160,200]
def rec(mode,i):
    p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
    X=list(struct.unpack_from("<9h",b,p+0x02)); Y=list(struct.unpack_from("<9h",b,p+0x14))
    return np.array(X,float),np.array(Y,float)
CAP = struct.unpack_from("<H",b,0xC6384)[0]/1024.0
print(f"  per-segment slope cap cal(0xC6384) = {CAP:.3f}   (Branch-B build loop)")
print(f"  {'v':>4} {'m(396)':>9} {'slope@396':>10} {'slope@0+':>9} {'mean slope':>11} {'m(8192)':>9}")
for mode in (24,26):
    print(f"  -- mode {mode} --")
    for i,sp in enumerate(SPEEDS):
        X,Y=rec(mode,i)
        m396=np.interp(396.,X,Y); 
        k=np.searchsorted(X,396.)-1
        s396=(Y[k+1]-Y[k])/(X[k+1]-X[k])
        s0=(Y[1]-Y[0])/(X[1]-X[0])
        m8192=np.interp(8192.,X,Y)
        print(f"  {sp:4d} {m396:9.1f} {s396:10.3f} {s0:9.3f} {m8192/8192:11.3f} {m8192:9.1f}")

print("\n=== 3. MEASURED |u| = |gp-0x6b94|, route 0x85 (V100), engaged only ===")
d=np.load("_cache_r85/r85.npz",allow_pickle=True)
x=d["x6b94"].astype(float); eng=d["cc_lat"].astype(bool); tq=d["tq"].astype(float)
CPL=12.8   # counts per LSB, from r85_lane427.json
u=x*CPL
for nm,msk in [("ALL",np.ones(len(u),bool)),("ENGAGED",eng)]:
    s=u[msk]
    print(f"  {nm:8s} n={msk.sum():6d}  p50 {np.percentile(s,50):8.1f}  p90 {np.percentile(s,90):8.1f} "
          f" p99 {np.percentile(s,99):8.1f}  max {s.max():8.1f}  mean {s.mean():8.1f}")
print("  (x6b94 is a MAGNITUDE field: sar 6 of |gp-0x6b94|)")

print("\n=== 4. |tq| (driver torque, CAN counts) engaged, and the firmware-frame |T| = 1.024*tq ===")
for tag in ["r85","r95","r96","r9e"]:
    dd=np.load(f"_cache_{tag}/{tag}.npz",allow_pickle=True)
    t=np.abs(dd["tq"].astype(float))*1.024; e=dd["cc_lat"].astype(bool)
    s=t[e]
    print(f"  {tag}: engaged n={e.sum():6d}  |T| p50 {np.percentile(s,50):7.1f} p90 {np.percentile(s,90):7.1f} "
          f"p99 {np.percentile(s,99):7.1f} rms {np.sqrt((s**2).mean()):7.1f}")
