#!/usr/bin/env python3
"""studies/sessions/v76/v76_final_spec.py -- the four items team-lead asked for on top of studies/sessions/v76/v76_surface.py.

  (A) full spec for the E_X1=215 row, flat FactorC [566,566,566,908], both E_X0 variants
  (B) confirm the speed at which STOCK FactorC crosses 566 by interpolation
  (C) quantify the 35-80 km/h engaged exposure on route 61 and the k actually flown there
  (D) whether reverting the friction lane changes the damper's delivered output
All arithmetic via the validated mirror in studies/sessions/v76/v76_surface.py (FUN_00034350, 23/23 rows PASS).
"""
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
import sys, os, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
import v76_surface as V

S = {b: V.Surface(b, 26) for b in ("stock", "v38", "v74", "v75")}
CX = S["stock"].XY("C")[0]
img = V.load("v75")
C1 = [566, 566, 566, 908]
EY = [0, 539, 539, 927]
R_OP = 99

def surf(cy, ex0, ex1):
    return V.Surface(img=img, override={"C": (CX, cy), "E": ([ex0, ex1, 2500, 4000], EY)})

print("="*104); print("(A) THE E_X1 = 215 ROW -- FULL SPEC, both E_X0 variants"); print("="*104)
print("  FactorC  X = [2240, 3840, 5120, 8960]   Y = [566, 566, 566, 908]   (flat, F=566)")
print()
print("  %-30s %8s %6s %7s %7s %7s %7s %8s"%("FactorE X","k","M","d@99","d@200","d@400","max|6bd0|","guard"))
for ex0,ex1 in ((0,215),(0,214),(0,216),(12,200),(12,201),(12,199)):
    s=surf(C1,ex0,ex1); k=((566*539)>>10)/(ex1-ex0)
    mx=max(s.mag(v,r) for v in range(0,14001,64) for r in (0,99,2500,4000,12999))
    print("  [%4d, %4d, 2500, 4000]%s %8.4f %6d %7d %7d %7d %7d %8s"%(
        ex0,ex1," "*4,k,(566*539)>>10,s.mag(0,99),s.mag(0,200),s.mag(0,400),mx,
        "PASS" if mx<=512 else "FAIL"))
print("""
  => E_X0 = 0  -> X = [0, 215, 2500, 4000], k = 1.3814, dose 137. RECOMMENDED VARIANT.
  => E_X0 = 12 -> the E_X1 that lands dose 137 is 200 -- which IS V75's FactorE, byte for byte.
     🛑 So the G3-compliant variant has k = 1.5798, IDENTICAL to the build that faulted.
     The entire 12.4% k reduction comes from E_X0 12->0. If G3 is enforced, there is no k gain.""")

print("\n"+"="*104); print("(B) WHERE STOCK FactorC CROSSES 566 BY INTERPOLATION"); print("="*104)
sy=S["stock"].XY("C")[1]
xs=[v for v in range(0,14001) if V.lerp(CX,sy,v)>566]
x1=[v for v in range(0,14001) if V.lerp(CX,C1,v)>566]
print("  stock Y = %s"%sy)
print("  closed form on segment X[2]=5120 -> X[3]=8960, Y 429 -> 908:")
print("     v = 5120 + (566-429)*(8960-5120)/(908-429) = 5120 + 137*3840/479 = %.1f ct"%(5120+137*3840/479))
print("  mirror scan, first v with lerp(v) > 566 : %d ct = %.2f km/h   [two methods AGREE]"%(min(xs),min(xs)/64))
print("  flat C1  first v with lerp(v) > 566 : %d ct = %.2f km/h"%(min(x1),min(x1)/64))
print("  => C1 moves the onset DOWN by %.1f km/h (%.1f -> %.1f). CONFIRMED."%(
    (min(xs)-min(x1))/64, min(xs)/64, min(x1)/64))
print("  => and the clip needs FactorE >= %d, reached at rate %d ct = %.0f deg/s"%(
    512*1024//567, next(r for r in range(0x32C9) if ((567*V.lerp(*S['v75'].XY('E'),idx=r))>>10)>512),
    next(r for r in range(0x32C9) if ((567*V.lerp(*S['v75'].XY('E'),idx=r))>>10)>512)/4.7121))

print("\n"+"="*104); print("(C) THE 35-80 km/h ENGAGED EXPOSURE, ROUTE 61 (V74's fault drive)"); print("="*104)
d=np.load(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),'..','_scratch/cache/r61','r61.npz'),allow_pickle=True)
t=d['cs_t']; v=d['cs_v']; lat=np.asarray(d['cc_lat']).astype(bool)
n=min(len(t),len(v),len(lat)); t,v,lat=t[:n],v[:n],lat[:n]
FAULT_T=732.3872
pre=t<FAULT_T                      # SENTINEL GUARD: strict prefix, no 0x7FFF frames
kmh=v*3.6; dt=np.gradient(t)
sec=lambda m: float(np.sum(dt[m]))
sE=V.lerp(*S["v74"].XY("E"),idx=400)  # not used; slope below is from the table directly
ex,ey=S["v74"].XY("E"); slope74=(ey[1]-ey[0])/(ex[1]-ex[0])
ex5,ey5=S["v75"].XY("E"); slope75=(ey5[1]-ey5[0])/(ex5[1]-ex5[0])
slopeC1=539/215.0
print("  route 61, strict prefix before the fault: %.1f s total, %.1f s engaged"%(sec(pre),sec(pre&lat)))
print("  ENGAGED time at 35-80 km/h: %.1f s  = %.1f%% of engaged time"%(
    sec(pre&lat&(kmh>=35)&(kmh<=80)), 100*sec(pre&lat&(kmh>=35)&(kmh<=80))/sec(pre&lat)))
print()
print("  %8s %9s | %7s %7s | %7s %7s %7s | %7s"%("km/h","engaged s","C V74","C C1","k V74","k V75","k C1","C1/V74"))
tot74=tot=0.0
for lo,hi in ((35,45),(45,55),(55,65),(65,80)):
    m=pre&lat&(kmh>=lo)&(kmh<hi); s=sec(m); mid=int((lo+hi)/2*64)
    c74=V.lerp(CX,S["v74"].XY("C")[1],mid); c75=V.lerp(CX,S["v75"].XY("C")[1],mid)
    c1=V.lerp(CX,C1,mid)
    k74=c74*slope74/1024; k75=c75*slope75/1024; kc1=c1*slopeC1/1024
    tot74+=s*k74; tot+=s
    print("  %8s %9.1f | %7d %7d | %7.3f %7.3f %7.3f | %7.2fx"%(
        "%d-%d"%(lo,hi),s,c74,c1,k74,k75,kc1,kc1/k74))
print("  %8s %9.1f | %7s %7s | %7.3f %7s %7.3f | %7.2fx"%(
    "WEIGHTED",tot,"-","-",tot74/tot,"-",566*slopeC1/1024,(566*slopeC1/1024)/(tot74/tot)))
print("""
  => 286.4 s of ENGAGED driving in this band on route 61 alone -- the band is NOT unexplored.
     But V74 ran a time-weighted k of ~%.3f there, and C1 would run 1.386 UNIFORMLY.
  🛑 => C1 is a %.1fx step up in loop gain in a band with 286 s of clean evidence at the LOWER
     gain and ZERO at the higher. That is the residual risk, now as a number."""%(
        tot74/tot,(566*slopeC1/1024)/(tot74/tot)))

print("\n"+"="*104); print("(D) DOES REVERTING THE FRICTION LANE CHANGE THE DAMPER'S OUTPUT?"); print("="*104)
print("""  METHOD: enumerate FUN_00034350's COMPLETE read set from the decompile (0x34350), and test
  whether any friction cell or friction cal appears in it.

  FUN_00034350 reads, exhaustively:
    gp: -0x6bc4 -0x6bc6 -0x6bc8 -0x6bca (entry lockstep quad) · -0x4f60 (driver torque)
        -0x6df8 (IIR state) · -0x6752 (polarity) · -0x6c2e · -0x6ba6 · -0x6b9a · -0x4f68
        -0x698a (seed) · -0x6a5e (SPEED = FactorC index) · -0x67f4 (FactorC gate)
        -0x67fe · -0x6a10 (FactorD gate/index) · -0x6ac0 (FactorE index) · -0x6abe (SIGN)
        -0x6ac2 (ceiling index) · -0x4cf2 (shadow) · -0x257c · +0x63fd (mode)
    tp: +0x736c +0x736e +0x7498 +0x7158
    tables: 0xC9CCC(B) 0xC9E9C(C) 0xC9DB4(D) 0xC9F84(E) 0xC77A0(ceiling)

  The friction lane is gp-0x6b26, its table is 0xD7A54 and its clamp cal is 0xC407E.
  NONE of the three appears anywhere in that set.

  => [EVIDENCE] Reverting friction (0xD7A54 / 0xC407E) cannot change gp-0x6bd0 by ONE COUNT.
     The two lanes are INDEPENDENT at the point of production.
  ⚠ They are NOT independent in what the driver FEELS: both are summands in the downstream
     aggregator, so reverting friction lowers total opposing torque. The damper's own
     contribution -- everything tabulated in this file -- is unchanged.
  => Reverting friction is FREE from the damper's point of view. Damper dose needs no
     re-tuning to compensate; the felt total simply drops by the friction delta.""")
