"""CORRECTION to redteam_k185.py: X[9]=6000 for v>=80 km/h, so |Tc| (<=8192) CAN exceed it
and the extrapolation branch IS structurally reachable at high speed.  Redo the ceiling."""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=np.array([0,15,40,80,120,160,200.])
def rec(mode,i):
    p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
    return (np.array(struct.unpack_from("<9h",b,p+0x02),float),
            np.array(struct.unpack_from("<9h",b,p+0x14),float))
R=[rec(24,i) for i in range(7)]
def m_ext(T,X,Y):
    """LERP with the firmware's linear extrapolation above X[9] using slope[9]."""
    s9=(Y[-1]-Y[-2])/(X[-1]-X[-2])
    return np.where(T<=X[-1], np.interp(T,X,Y), Y[-1]+s9*(T-X[-1]))
print("=== CORRECTED lane ceiling m(|Tc|=8192), extrapolation INCLUDED ===")
print(f"  {'v':>5} {'X[9]':>7} {'Y[9]':>7} {'slope[9]':>9} {'m(8192)':>9} {'k where +-12.0 bites':>21}")
mx=0
for i,sp in enumerate(SPEEDS):
    X,Y=R[i]; s9=(Y[-1]-Y[-2])/(X[-1]-X[-2]); mm=float(m_ext(np.array([8192.]),X,Y)[0]); mx=max(mx,mm)
    print(f"  {sp:5.0f} {X[-1]:7.0f} {Y[-1]:7.0f} {s9:9.3f} {mm:9.0f} {12288/mm:21.3f}")
print(f"  => STRUCTURAL worst corner: m_max = {mx:.0f} at 200 km/h & |T| = 8192  =>  clamp bites at k = {12288/mx:.3f}")
print("     At k = 1.85 the clamp bites once m > 6642, i.e. only above ~200 km/h AND |T| > ~7700 ct.")

print("\n=== OBSERVED: does any real frame get near it? ===")
def m_of(T,v):
    i=np.clip(np.searchsorted(SPEEDS,v)-1,0,5).astype(int)
    w=(np.clip(v,SPEEDS[i],SPEEDS[i+1])-SPEEDS[i])/(SPEEDS[i+1]-SPEEDS[i])
    lo=np.array([m_ext(np.array([t]),*R[a])[0] for t,a in zip(T,i)])
    hi=np.array([m_ext(np.array([t]),*R[a+1])[0] for t,a in zip(T,i)])
    return (1-w)*lo+w*hi
tot=0; over=0
for tag in ("r85","r95","r96","r9e"):
    d=np.load(f"_cache_{tag}/{tag}.npz",allow_pickle=True); e=d["cc_lat"].astype(bool)
    T=np.minimum(np.abs(d["tq"].astype(float))*1.024,8192.)[e]
    v=d["cs_v"].astype(float)[e]; v=v*3.6 if v.max()<60 else v
    m=m_of(T,v); tot+=len(m); over+=(m>6642).sum()
    print(f"  {tag}: m p50 {np.percentile(m,50):5.0f} p99 {np.percentile(m,99):5.0f} max {m.max():5.0f} "
          f" v_max {v.max():5.1f} km/h  |T|_max {T.max():5.0f}  n(m>6642)={int((m>6642).sum())}")
print(f"  TOTAL engaged frames across the 4 routes: {tot}, of which m > 6642: {over}  ({over/tot:.6f})")
print("\n=== the DC step at k = 1.85, using m as the (upper-bound) proxy for |gp-0x6b82| ===")
d=np.load("_cache_r85/r85.npz",allow_pickle=True); e=d["cc_lat"].astype(bool)
u=np.abs(d["x6b94"].astype(float))[e]
T=np.minimum(np.abs(d["tq"].astype(float))*1.024,8192.)[e]
v=d["cs_v"].astype(float)[e]; v=v*3.6 if v.max()<60 else v
m=m_of(T,v); step=0.85*m
for q in (50,90,99):
    print(f"  p{q}: step {np.percentile(step,q):7.0f} ct   |u| {np.percentile(u,q):7.0f} ct   "
          f"ratio {np.percentile(step,q)/np.percentile(u,q):6.2f}x")
print(f"  intended in-band effect at k=1.85: (k-1)*a*|T_s| = {0.85*0.098*396.4:.1f} ct  (band |u| = 20.9 ct)")
print(f"  => broadband/in-band effect ratio at the median: {np.percentile(step,50)/(0.85*0.098*396.4):.0f}x")
