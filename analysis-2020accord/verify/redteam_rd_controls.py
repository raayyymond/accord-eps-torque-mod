"""CONTROLS for the 0x9e regression-discontinuity result.  Kit rule: run the control FIRST.

C1  a real RD needs the step at ONE threshold; a positive step at EVERY threshold = smooth trend
C2  include a flexible SMOOTH in log(max_m); does the step survive?
C3  PLACEBO predictor: same step, but on max|rate| instead of max_m (activity confound)
C4  PLACEBO bands: 2.5-4.5, 15-18, 22-26 Hz -- the mechanism is BAND-SPECIFIC via Re(dG.Z)
C5  episode-label permutation null
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import numpy as np, struct, os
import _gate2_boost_lib as L
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

NPER=int(round(4*L.FS)); f=np.fft.rfftfreq(NPER,1/L.FS)
d=L.load("r9e"); eng=d["cc_lat"].astype(bool)
tq=d["tq"].astype(float); rate=np.abs(d["rate_f"].astype(float))
T=np.minimum(np.abs(tq)*1.024,8192.); v=d["cs_v"].astype(float); v=v*3.6 if v.max()<60 else v
m=m_of(T,v)
BANDS={"6-9":(6,9),"2.5-4.5":(2.5,4.5),"15-18":(15,18),"22-26":(22,26)}
eps=L.episodes(eng); step=NPER//2; win=np.hanning(NPER+1)[:NPER]
E,MX,MM,RT,VV,MXR = [],[],[],[],[],[]
BD={k:[] for k in BANDS}
for ei,(s,e) in enumerate(eps):
    for st in range(s,e-NPER+1,step):
        x=tq[st:st+NPER]
        if not np.all(np.isfinite(x)): continue
        X=np.fft.rfft((x-x.mean())*win)
        for k_,(lo,hi) in BANDS.items():
            sl=(f>=lo)&(f<hi); BD[k_].append(np.sqrt((np.abs(X[sl])**2).sum()))
        E.append(ei); MX.append(m[st:st+NPER].max()); MM.append(np.median(m[st:st+NPER]))
        RT.append(np.median(rate[st:st+NPER])); VV.append(np.median(v[st:st+NPER]))
        MXR.append(rate[st:st+NPER].max())
E=np.array(E); MX=np.array(MX); MM=np.array(MM); RT=np.array(RT); VV=np.array(VV); MXR=np.array(MXR)
BD={k_:np.array(vv) for k_,vv in BD.items()}
n=len(E); ne=int(E.max())+1
print(f"{n} windows / {ne} episodes.  max_m {MX.min():.0f}-{MX.max():.0f}, max|rate| {MXR.min():.1f}-{MXR.max():.1f}")

def fit(y, dummy, smooth_deg=0, extra=None):
    cols=[np.ones(n), np.log(MM+1), np.log(RT+0.5), VV]
    lm=np.log(MX+1)
    for p in range(1,smooth_deg+1): cols.append(lm**p)
    if extra is not None: cols.append(extra)
    cols.append(dummy.astype(float))
    Xd=np.column_stack(cols)
    beta,*_=np.linalg.lstsq(Xd,y,rcond=None)
    return beta[-1], Xd

def boot(y, Xd, nboot=2000, seed=11):
    rng=np.random.default_rng(seed); out=[]
    for _ in range(nboot):
        pick=rng.integers(0,ne,ne); idx=np.concatenate([np.flatnonzero(E==p) for p in pick])
        if len(idx)<15: continue
        try: out.append(np.linalg.lstsq(Xd[idx],y[idx],rcond=None)[0][-1])
        except Exception: pass
    return np.percentile(out,[2.5,97.5])

y69=np.log(BD["6-9"]+1e-9)
print("\n=== C1+C2: does the step SURVIVE a smooth in log(max_m)?  (a real RD must) ===")
print(f"  {'theta':>7} {'n_hi':>5} {'deg0 step':>10} {'deg1':>8} {'deg2':>8} {'deg3':>8}  (ratio at deg3)")
for th in (1500,2000,2500,2800,3000,3200):
    hi=MX>=th
    if hi.sum()<8 or (~hi).sum()<8: continue
    r=[fit(y69,hi,dg)[0] for dg in (0,1,2,3)]
    print(f"  {th:7.0f} {hi.sum():5d} {r[0]:+10.3f} {r[1]:+8.3f} {r[2]:+8.3f} {r[3]:+8.3f}   {np.exp(r[3]):.3f}x")
print("  -> a step that collapses as the smooth order rises was CURVATURE, not a discontinuity.")

print("\n=== C3: PLACEBO predictor -- the same step on max|rate| (nothing to do with clipping) ===")
print(f"  {'pctile':>7} {'thresh':>8} {'n_hi':>5} {'deg0 step':>10} {'95% CI':>20} {'ratio':>8}")
for q in (30,50,60,70,80):
    th=np.percentile(MXR,q); hi=MXR>=th
    bh,Xd=fit(y69,hi,0); ci=boot(y69,Xd)
    print(f"  {q:7d} {th:8.1f} {hi.sum():5d} {bh:+10.3f} [{ci[0]:+.3f},{ci[1]:+.3f}] {np.exp(bh):8.3f}x")

print("\n=== C4: PLACEBO BANDS -- the mechanism is band-specific via Re(dG.Z); a generic")
print("    activity confound is NOT.  Step at theta = 2800 (the strongest m threshold): ===")
for k_,_ in BANDS.items():
    yy=np.log(BD[k_]+1e-9); hi=MX>=2800
    bh,Xd=fit(yy,hi,0); ci=boot(yy,Xd)
    bh3,_=fit(yy,hi,3)
    print(f"  {k_:>8} Hz:  deg0 {bh:+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}] = {np.exp(bh):.3f}x   deg3 {bh3:+.3f} = {np.exp(bh3):.3f}x")

print("\n=== C5: episode-label permutation null for the deg0 step at theta = 2800 ===")
hi=MX>=2800; bh,Xd=fit(y69,hi,0)
rng=np.random.default_rng(3); null=[]
for _ in range(4000):
    perm=rng.permutation(n)
    Xp=Xd.copy(); Xp[:,-1]=Xd[perm,-1]
    null.append(np.linalg.lstsq(Xp,y69,rcond=None)[0][-1])
null=np.array(null)
print(f"  real {bh:+.3f}   shuffled null p50 {np.median(null):+.3f}  p95 {np.percentile(null,95):+.3f} "
      f" p99 {np.percentile(null,99):+.3f}   -> p = {(null>=bh).mean():.4f}")
print("  (this null only breaks the dummy's alignment; it does NOT break the m<->activity link)")
