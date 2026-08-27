"""RED-TEAM R2/R4: independent re-run of the band transfers on all four routes,
then price the boost at 6-9 Hz AND at grind-#1 (21.0-22.5 Hz) by BOTH criteria."""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import numpy as np, json
import _gate2_boost_lib as L

BANDS=[(2,4),(4,6),(6,9),(9,13),(15,18),(15,22),(21.0,22.5),(22,26)]
ROUTES=[("r85","V100 4x","SUM u"),("r95","V101 8x","SUM u"),("r96","V102 6x","LANE 6b4c"),("r9e","V103 6x","LANE 6b4c")]
NPER=int(round(4.0*L.FS))
out={}
print(f"{'route':6} {'target':10} {'band':>12} {'|H|':>8} {'phase':>8} {'coh2':>6} {'eps':>4}")
for tag,build,tgt in ROUTES:
    d=L.load(tag)
    x=d["tq"].astype(float)
    y=(d["x6b94"] if tgt.startswith("SUM") else d["x6b4c"]).astype(float)
    eps=L.episodes(d["cc_lat"].astype(bool))
    sp=L.episode_specs(x,y,eps,NPER)
    f=np.fft.rfftfreq(NPER,1/L.FS)
    out[tag]={}
    for lo,hi in BANDS:
        H,c=L.band_H(sp,f,lo,hi)
        out[tag][f"{lo}-{hi}"]=(abs(H),np.angle(H,deg=True),c)
        print(f"{tag:6} {tgt:10} {lo:5.1f}-{hi:4.1f} {abs(H):8.4f} {np.angle(H,deg=True):+8.1f} {c:6.3f} {len(sp):4d}")
    print()

print("=== POOLED (r85+r95 = SUM;  r96+r9e = LANE), inverse-variance-free simple pool ===")
def pool(tags,key):
    v=[out[t][key] for t in tags]
    z=np.mean([m*np.exp(1j*p*np.pi/180) for m,p,_ in v])
    return abs(z),np.angle(z,deg=True)
D=np.pi/180
Zbands={"6-9":(6873,-123.2),"15-22":(1379,108.6),"22-26":(1168,96.8)}
def Hb(f):
    import struct,os
    P=os.environ.get("ACCORD_FIRMWARE_ROOT","C:/Users/dudei/Desktop/Projects/accord-firmwares")
    b=open(os.path.join(P,"analysis-2020accord/stock_fw_dump/code.bin"),"rb").read()
    c1,c2,c3,c4=struct.unpack_from("<4f",b,0xC60A8)
    z=np.exp(-2j*np.pi*f/1000.0); return c4*(1+c3*z+z*z)/(1+c1*z+c2*z*z)

print(f"{'band':>10} {'|SUM|':>8} {'argSUM':>8} {'|LANE|':>8} {'argLANE':>8} {'a_solved':>9} {'|r24+26|':>9}")
for key in ("6-9","15-18","15-22","21.0-22.5","22-26"):
    sm,sp_=pool(["r85","r95"],key); lm,lp=pool(["r96","r9e"],key)
    res=sm*np.exp(1j*sp_*D)-lm*np.exp(1j*lp*D)
    print(f"{key:>10} {sm:8.4f} {sp_:+8.1f} {lm:8.4f} {lp:+8.1f} {-res.real:9.4f} {-res.imag:9.4f}")

print("\n=== R4: price a flat c4 BOOST in each band, BOTH criteria ===")
print("  dG(f) = -(k-1)*a(f)*H(f).  a(f) taken from the per-band residual real part (same method as 6-9).")
print(f"  {'band':>10} {'fc':>6} {'a(f)':>8} {'arg dG':>8} {'arg Z':>7} {'arg(dG*Z)':>10} {'Re(dG*Z)':>10} {'|u| ratio k=1.5':>16}")
for key,fc in [("6-9",7.5),("15-22",18.5),("21.0-22.5",21.7),("22-26",24.0)]:
    if key not in Zbands and key!="21.0-22.5": pass
    sm,sp_=pool(["r85","r95"],key); lm,lp=pool(["r96","r9e"],key)
    res=sm*np.exp(1j*sp_*D)-lm*np.exp(1j*lp*D); aa=-res.real
    zk = "15-22" if key in ("15-22","21.0-22.5") else ("22-26" if key=="22-26" else "6-9")
    Zm,Zp=Zbands[zk]; Z=Zm*np.exp(1j*Zp*D)
    H=Hb(fc); dG=-(0.5)*aa*H          # k = 1.5
    u=sm*np.exp(1j*sp_*D); ratio=abs(u+dG)/abs(u)
    print(f"  {key:>10} {fc:6.1f} {aa:8.4f} {np.angle(dG,deg=True):+8.1f} {Zp:+7.1f} "
          f"{np.angle(dG*Z,deg=True):+10.1f} {(dG*Z).real:+10.1f} {ratio:16.3f}")
json.dump({k:{kk:list(map(float,vv)) for kk,vv in v.items()} for k,v in out.items()},open("_scratch/out/_redteam_bands.json","w"),indent=1)
