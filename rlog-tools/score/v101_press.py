"""Do MY reported V101 band ratios survive splitting on hands-ON?  I reported 22-26 = 29.85x stock."""
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
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
import numpy as np, v102_xb_lib as L
L.ROUTES["97"]=L._mk("97","V9b-STOCK",gain=891,clamp=512,leverB=False,idcode=0,bits="stock")
L.ROUTES["96"]=L._mk("96","V102",gain=5346,clamp=3072,leverB=False,idcode=3,bits="v102")
ARMS=[("97","STOCK"),("85","V100"),("95","V101"),("96","V102")]
W={}
for rt,_ in ARMS:
    r=L.windows(rt,nfft=256,hop=128,engaged=True,keep_raw=True)
    for rec in r:
        b,s=rec["_blk"],rec["_sl"]
        rec["press"]=float(np.mean(b["cs_press"][s]>0.5))
        rec["dtq"]=float(np.median(np.abs(b["tq"][s])))
    W[rt]=r
print("arm / subset / n / mean press / |tq| p50 / 6-9 Hz p50 / 22-26 Hz p50")
for rt,nm in ARMS:
    for tag,sub in (("ALL",W[rt]),
                    ("hands-OFF",[r for r in W[rt] if r["press"]<0.02]),
                    ("hands-ON ",[r for r in W[rt] if r["press"]>0.98])):
        if len(sub)<5: print("  %-8s %-10s n=%d  -- too few"%(nm,tag,len(sub))); continue
        print("  %-8s %-10s n=%4d  press %.3f  |tq|p50 %7.1f   6-9 %8.1f   22-26 %8.1f"%(
            nm,tag,len(sub),np.mean([r["press"] for r in sub]),np.median([r["dtq"] for r in sub]),
            np.median([r["tq|6-9"] for r in sub]),np.median([r["tq|22-26"] for r in sub])))
print("\n=== ratio to STOCK, HANDS-OFF WINDOWS ONLY (press<0.02), matched speed x rate ===")
import stock_r97_resonance as R
A=[r for r in W["97"] if r["press"]<0.02]
for rt,nm in ARMS:
    if rt=="97": continue
    B=[r for r in W[rt] if r["press"]<0.02]
    for bn in ("6-9","18-22","22-26","32-38"):
        m=R._matched_boot(A,B,"tq|"+bn)
        print("   %-6s %-7s %s"%(nm,bn,("%8.2fx [%6.2f,%6.2f] (%d cells)"%(m["r"],m["lo"],m["hi"],m["cells"])) if m else "no matched cell"))
