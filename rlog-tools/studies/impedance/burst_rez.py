"""Is V102's 22-26 Hz ANTI-DAMPING present only during BURSTS?
route-v102 finds V102's line is intermittent (p90/p50 = 59.5) where V101's is continuous (2.74).
I find V102 flips 22-26 Hz from damped (stock) to anti-damped.  If the flip is burst-conditional,
the two results are the same phenomenon seen from two sides.

CIRCULARITY GUARD: windows are ranked by the 21.5-25.5 Hz band power of `rate_c` (0x14A), while
Re(Z) is computed from `tq` x `rate_f` (0x18F) -- a DIFFERENT CAN message, so the conditioning
variable shares no quantisation with the estimate.  26-31 Hz is carried as a band control: a
generic selection artefact would move it too."""
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
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
import decode_v90_probe as P
import v102_xb_lib as L
C=Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
DEG2RAD=np.pi/180.0; RNG=np.random.default_rng(97_2026)
BANDS=[("6-9",6.,9.),("18-22",18.,22.),("22-26",22.,26.),("26-31",26.,31.)]
for rt,nm in (("97","STOCK 1x"),("96","V102 6x"),("85","V100 4x")):
    z=np.load(C/("r"+rt)/("r"+rt+".npz"),allow_pickle=True)
    t=np.asarray(z["t"],float); tq=np.asarray(z["tq"],float)
    rf=np.asarray(z["rate_f"],float)*DEG2RAD
    rc=np.asarray(z["rate_c"],float)
    lat=np.asarray(z["cc_lat"],float)>0.5
    pr=np.asarray(z["cs_press"],float)>0.5
    v=np.abs(np.asarray(z["cs_v"],float))
    fs=1.0/float(np.median(np.diff(t)))
    W=P._wins(lat&(~pr)&(v>0.5),t,P.NW_Z,P.HOP_Z,(rf,tq,v,rc))
    if len(W)<18: print("\n  %-10s only %d windows -- NOT SCOREABLE"%(nm,len(W))); continue
    wn=np.hanning(P.NW_Z)
    burst=np.array([L.bandrms(w[3],fs,21.5,25.5,wn) for w in W])
    q=np.percentile(burst,[33.3,66.7])
    grp={"LOW  tercile":burst<=q[0],"MID  tercile":(burst>q[0])&(burst<=q[1]),"HIGH tercile":burst>q[1]}
    print("\n  === %s : %d windows, burst rank = rate_c 21.5-25.5 band-RMS (deg/s) ==="%(nm,len(W)))
    print("      p50 %.3f  p90/p50 %.2f  p99/p50 %.2f"%(np.median(burst),
          np.percentile(burst,90)/np.median(burst),np.percentile(burst,99)/np.median(burst)))
    print("      %-14s %5s"%("subset","n")+"".join("%22s"%("Re(Z) "+b) for b,_,_ in BANDS))
    for gn,m in grp.items():
        sel=[w for w,k in zip(W,m) if k]
        if len(sel)<6: print("      %-14s %5d  -- too few"%(gn,len(sel))); continue
        pairs=[(w[0],w[1]) for w in sel]
        row="      %-14s %5d"%(gn,len(sel))
        for bn,lo,hi in BANDS:
            r=P._band_transfer(pairs,fs,P.NW_Z,[(bn,lo,hi)])[bn]
            bs=[P._band_transfer([pairs[k] for k in RNG.integers(0,len(pairs),len(pairs))],fs,P.NW_Z,[(bn,lo,hi)])[bn]["re_over_sxx"] for _ in range(150)]
            blo,bhi=np.percentile(bs,[2.5,97.5])
            row+="%9.0f[%5.0f,%5.0f]"%(r["re_over_sxx"],blo,bhi)
        print(row)
