"""CORRECTION + the 0x9e falsification test.

CORRECTED aggregate:  frames in the harmful window get the NULL (+a*H), not zero change.
  Delta(u/T) = -a*H * [ (1-d_new)*(k-1)  -  (d_new - d_old) ]
                        ^ boost on unclipped     ^ NULL on newly-clipped
"""
import numpy as np, struct, os
D=np.pi/180
P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
BASES=[0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]; SPEEDS=np.array([0,15,40,80,120,160,200.])
def rec(m_,i):
    p=struct.unpack_from("<I",b,BASES[i]+m_*4)[0]
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
allm=[]
for tag in ("r85","r95","r96","r9e"):
    d=np.load(f"_cache_{tag}/{tag}.npz",allow_pickle=True); e=d["cc_lat"].astype(bool)
    T=np.minimum(np.abs(d["tq"].astype(float))*1.024,8192.)[e]
    v=d["cs_v"].astype(float)[e]; v=v*3.6 if v.max()<60 else v
    allm.append(m_of(T,v))
allm=np.concatenate(allm)

k=1.85; u=0.0526*np.exp(1j*15.4*D); a=0.098; H=0.98861*np.exp(-10.61j*D)
print("=== CORRECTED: the mixture with the NULL term included ===")
print(f"  {'S':>6} {'d_old':>8} {'d_new':>8} {'boost term':>11} {'NULL term':>10} {'net (k-1)':>10} "
      f"{'k_eff':>7} {'|u_new|/|u|':>12}")
worst=(None,0)
for S in (1.0,1.8,2.0,2.5,3.0,3.34,4.0,5.0,6.0,8.0,10.0,20.0):
    d_old=(allm>12288/S).mean(); d_new=(allm>12288/(k*S)).mean()
    bt=(1-d_new)*(k-1); nt=(d_new-d_old); net=bt-nt
    r=abs(u-net*a*abs(H))/abs(u)
    if r>worst[1]: worst=(S,r)
    print(f"  {S:6.2f} {d_old:8.5f} {d_new:8.5f} {bt:11.4f} {nt:10.4f} {net:10.4f} "
          f"{1+net:7.3f} {r:12.3f}")
print(f"  WORST over the whole S sweep: S={worst[0]}, |u_new|/|u| = {worst[1]:.3f}")
print("  => the mixture NEVER inverts the lever.  The null term is bounded by (d_new - d_old) <= ~0.22,")
print("     while the boost term is (1-d_new)*0.85.  The boost dominates at every S.")
print("  => and the newly-clipped frames are the HIGH-|T| frames, which are exactly the frames where")
print("     the ratchet is already suppressed 16.12x [5.29,41.29] ('applying torque kills the buzz').")

# ---------------------------------------------------------------- the 0x9e test
print("\n" + "="*100)
print("THE PRE-REGISTERED FALSIFICATION TEST on route 0x9e (V103, k=1)")
print("="*100)
print("PREDICTION under the GATE2 null model: frames where the lane is ALREADY clipped should show")
print("~2.83x MORE 6-9 Hz energy than matched unclipped frames.  Clipping at k=1 needs m_A >= 12288/S,")
print("so this test covers S >= 3.34 ONLY.  Identification is by a STEP (regression discontinuity),")
print("because any smooth trend in m is confounded with |T|, which suppresses the ratchet 16x.")
import _gate2_boost_lib as L
NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS); sel=(f>=6)&(f<9)
d=L.load("r9e"); eng=d["cc_lat"].astype(bool)
tq=d["tq"].astype(float); rate=np.abs(d["rate_f"].astype(float))
T=np.minimum(np.abs(tq)*1.024,8192.); v=d["cs_v"].astype(float); v=v*3.6 if v.max()<60 else v
m=m_of(T,v)
eps=L.episodes(eng); step=NPER//2; w=np.hanning(NPER+1)[:NPER]
rows=[]
for ei,(s,e) in enumerate(eps):
    for st in range(s,e-NPER+1,step):
        x=tq[st:st+NPER]
        if not np.all(np.isfinite(x)): continue
        X=np.fft.rfft((x-x.mean())*w)
        band=np.sqrt((np.abs(X[sel])**2).sum())
        rows.append((ei,band,m[st:st+NPER].max(),np.median(m[st:st+NPER]),
                     np.median(rate[st:st+NPER]),np.median(v[st:st+NPER])))
rows=np.array(rows)
print(f"\n  {len(rows)} windows in {len(eps)} episodes.  max-m range {rows[:,2].min():.0f}-{rows[:,2].max():.0f}")

def rd(theta, nboot=2000, seed=7):
    hi=rows[:,2]>=theta
    if hi.sum()<8 or (~hi).sum()<8: return None
    y=np.log(rows[:,1]+1e-9)
    Xd=np.column_stack([np.ones(len(rows)),np.log(rows[:,3]+1),np.log(rows[:,4]+0.5),
                        rows[:,5],hi.astype(float)])
    beta=np.linalg.lstsq(Xd,y,rcond=None)[0]
    rng=np.random.default_rng(seed); ne=int(rows[:,0].max())+1; bs=[]
    for _ in range(nboot):
        pick=rng.integers(0,ne,ne); idx=np.concatenate([np.flatnonzero(rows[:,0]==p) for p in pick])
        if len(idx)<12: continue
        try: bs.append(np.linalg.lstsq(Xd[idx],y[idx],rcond=None)[0][4])
        except Exception: pass
    return beta[4], np.percentile(bs,[2.5,97.5]), int(hi.sum())

print(f"\n  {'theta (m_A)':>12} {'implied S':>10} {'n_hi':>6} {'step in ln(6-9 RMS)':>21} {'95% CI':>22} {'ratio':>8}")
for th in (1500,2000,2500,2800,3000,3200,3400):
    r=rd(th)
    if r is None: print(f"  {th:12.0f} {12288/th:10.2f}      -   (too few windows on one side)"); continue
    bhat,ci,nh=r
    print(f"  {th:12.0f} {12288/th:10.2f} {nh:6d} {bhat:+21.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]  {np.exp(bhat):8.3f}x")
print(f"\n  PREDICTED under the null model: step = ln(2.83) = {np.log(2.83):+.3f}  (ratio 2.83x)")
