"""RED-TEAM R8/R0c: the SATURATION MIXTURE.  Where exactly does it bite, and can 0x9e see it?

Frame classes when c4 goes 1 -> k (k=1.85), in terms of the biquad input |gp-0x6b82| = m:
   m <= 12288/k        both builds unclipped        -> FULL boost, linear, model exact
   12288/k < m <= 12288  NEW clipping               -> lane's AC is KILLED = the REFUTED NULL   <-- harmful
   m > 12288           already clipped at k=1       -> no change (both pinned)
So the harmful support is the HALF-OPEN BAND  m in (12288/k, 12288].
"""
import numpy as np, struct, os
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
assert b[0xC60A8:0xC60AC].hex()=="f8c2c4bf"
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=np.array([0,15,40,80,120,160,200.])
def rec(mode,i):
    p=struct.unpack_from("<I",b,BASES[i]+mode*4)[0]
    return (np.array(struct.unpack_from("<9h",b,p+0x02),float),
            np.array(struct.unpack_from("<9h",b,p+0x14),float))
R=[rec(24,i) for i in range(7)]
def m_ext(T,X,Y):
    s9=(Y[-1]-Y[-2])/(X[-1]-X[-2]); return np.where(T<=X[-1],np.interp(T,X,Y),Y[-1]+s9*(T-X[-1]))
def m_of(T,v):
    i=np.clip(np.searchsorted(SPEEDS,v)-1,0,5).astype(int)
    w=(np.clip(v,SPEEDS[i],SPEEDS[i+1])-SPEEDS[i])/(SPEEDS[i+1]-SPEEDS[i])
    lo=np.array([m_ext(np.array([t]),*R[a])[0] for t,a in zip(T,i)])
    hi=np.array([m_ext(np.array([t]),*R[a+1])[0] for t,a in zip(T,i)])
    return (1-w)*lo+w*hi

mA={}
for tag in ("r85","r95","r96","r9e"):
    d=np.load(f"_cache_{tag}/{tag}.npz",allow_pickle=True); e=d["cc_lat"].astype(bool)
    T=np.minimum(np.abs(d["tq"].astype(float))*1.024,8192.)[e]
    v=d["cs_v"].astype(float)[e]; v=v*3.6 if v.max()<60 else v
    mA[tag]=m_of(T,v)
allm=np.concatenate([mA[t] for t in mA])
print(f"m (Branch-A scale) over ALL 4 routes, engaged: n={len(allm)} p50 {np.percentile(allm,50):.0f} "
      f"p99 {np.percentile(allm,99):.0f} max {allm.max():.0f}")

print("\n=== THE HARMFUL-WINDOW DUTY vs the UNKNOWN Branch-B scale S  (m_true = S * m_A) ===")
print("  harmful if  12288/k < S*m_A <= 12288   i.e.  m_A in (12288/(k*S), 12288/S]")
k=1.85
print(f"  {'S':>6} {'m_A window':>22} {'duty (harmful)':>15} {'duty (already clipped at k=1)':>30}")
for S in (1.0,1.5,1.8,2.0,2.5,3.0,3.34,4.0,6.0,10.0):
    lo,hi=12288/(k*S),12288/S
    duty=((allm>lo)&(allm<=hi)).mean(); pre=(allm>hi).mean()
    print(f"  {S:6.2f} ({lo:8.0f},{hi:8.0f}] {duty:15.6f} {pre:30.6f}")
print("\n  S = 1.0 is the Branch-A hypothesis (my ROM read).  S >= 3.34 is the ONLY range in which")
print("  clipping ALREADY occurs at k=1, i.e. the only range route 0x9e can test.")
print("  1.80 <= S < 3.34 is a BLIND BAND: the mechanism bites at k=1.85 and is INVISIBLE on every")
print("  drive in the corpus, because no existing build clips.")

print("\n=== effective dose under the mixture (harmful frames get k_eff = 0 on the AC) ===")
print("  Delta(u/T) = (1 - d_new) * (k-1) * a_true ; design assumed (1 - d_old) * (k-1) * a_true")
print(f"  {'S':>6} {'d_old':>9} {'d_new':>9} {'k_eff':>8} {'|u_new|/|u| @6-9':>18}")
u=0.0526*np.exp(1j*15.4*np.pi/180); a=0.098
for S in (1.0,1.8,2.0,2.5,3.0,3.34,4.0,6.0,10.0):
    d_old=(allm>12288/S).mean(); d_new=(allm>12288/(k*S)).mean()
    keff=1+(1-d_new)/(1-d_old)*(k-1) if d_old<1 else 1
    print(f"  {S:6.2f} {d_old:9.6f} {d_new:9.6f} {keff:8.3f} {abs(u-(keff-1)*a)/abs(u):18.3f}")
print("  NOTE the mixture DEGRADES the dose toward k=1; it does NOT drive k_eff to 0 globally.")
print("  It only reaches 0 for the SUBSET of frames in the harmful window.")

print("\n=== does the mixture ROTATE the lane's phase?  (this is the framework question) ===")
print("  clipped frame: lane contributes a CONSTANT (sign-following) -> 0 AC, no phase")
print("  unclipped:     lane contributes -a*H(f)  ->  angle 180 - arg H")
print("  mixture       = d*0 + (1-d)*(-a*H)  =  (1-d)*(-a*H)")
print("  => the mixture SCALES the lane, it does NOT rotate it.  a_meas = (1-d)*a_true.")
print("  => every PHASE in the budget survives a saturation mixture unchanged.")
print("  => and since BOTH the budget's target Re(u) and its sensitivity a carry the SAME (1-d),")
print("     the optimal dose k* = 1 + Re(u)/a_meas is UNBIASED for the frames that do not clip.")
