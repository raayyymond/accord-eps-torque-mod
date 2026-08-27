"""Deep dive: verify slew-lag in high-command regime, output sign during unwind,
and quantify kp/kf demand vs delivery. Report-only."""
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
import sys, math
from pathlib import Path
import capnp
sys.path.insert(0, str(Path(__file__).parents[2]))
from _lat_wind_unwind import collect, engaged_segments, stats, pctl, ROUTES


def deep(name, samples):
    runs = engaged_segments(samples)
    eng = [s for r in runs for s in r]
    if not eng:
        return f"\n## {name}: no engaged\n"
    out = [f"\n## {name} (engaged {len(eng)})"]

    # 1) Slew lag in HIGH-COMMAND regime only (desiredSlew binned)
    bins = [(2,10),(10,30),(30,60),(60,120),(120,300),(300,2000)]
    bdata = {b:[] for b in bins}   # ratio actual/desired
    bdes = {b:[] for b in bins}
    bact = {b:[] for b in bins}
    for r in runs:
        for k in range(1,len(r)):
            dt=r[k]["t"]-r[k-1]["t"]
            if dt<=0 or dt>0.1: continue
            dd=abs((r[k]["ps_psDesired"]-r[k-1]["ps_psDesired"])/dt)
            da=abs((r[k]["ps_psAngle"]-r[k-1]["ps_psAngle"])/dt)
            for b in bins:
                if b[0]<=dd<b[1]:
                    bdata[b].append(da/dd if dd>0 else 0)
                    bdes[b].append(dd); bact[b].append(da)
                    break
    out.append("  desiredSlew bin | n | actual/desired (mean) | actualSlew mean | (deg/s)")
    for b in bins:
        if bdata[b]:
            out.append(f"   [{b[0]:>3}-{b[1]:>4}) | {len(bdata[b]):>5} | {sum(bdata[b])/len(bdata[b]):.2f} | {sum(bact[b])/len(bact[b]):.1f}")

    # 2) Output sign correctness vs angleError (the controller pushes toward reducing error)
    # correct = output sign == sign(angleError). angleError = desired - actual (openpilot convention check)
    sign_ok=0; tot=0; ae_pos_out=[]
    for s in eng:
        ae=s["ps_angleError"]; o=s["ps_output"]
        if abs(o)>0.02 and abs(ae)>0.5:
            tot+=1
            if (ae*o)>0: sign_ok+=1
    out.append(f"\n  output-sign matches angleError sign: {sign_ok}/{tot} ({100*sign_ok/tot:.0f}%)  [confirms angleError convention & no inversion]")

    # 3) kp headroom: what output would a middle-ground kp give vs current?
    # current p = kp*angleError. At v~10: kp=0.03 (lat-B). stock kp~0.06.
    # estimate effective kp from p/angleError where both nonzero
    kp_eff=[]
    for s in eng:
        ae=s["ps_angleError"]
        if abs(ae)>1.0 and abs(s["ps_p"])>1e-4:
            kp_eff.append(abs(s["ps_p"]/ae))
    if kp_eff:
        out.append(f"  effective kp (p/angleError): mean {sum(kp_eff)/len(kp_eff):.4f} p50 {pctl(kp_eff,.5):.4f}  (lat-B target ~0.03 at 10m/s)")

    # 4) how often is the controller demanding but output small (under-driving)?
    # large angleError but small output -> controller too weak
    weak=0; bigerr=0
    for s in eng:
        if abs(s["ps_angleError"])>10:
            bigerr+=1
            if abs(s["ps_output"])<0.5: weak+=1
    if bigerr:
        out.append(f"  big angleError(>10deg) with weak output(<0.5): {weak}/{bigerr} ({100*weak/bigerr:.0f}%)  [under-driven error]")

    # 5) f (feedforward) contribution share
    fshare=[]
    for s in eng:
        tot_=abs(s["ps_p"])+abs(s["ps_i"])+abs(s["ps_f"])
        if tot_>1e-3:
            fshare.append(abs(s["ps_f"])/tot_)
    if fshare:
        out.append(f"  feedforward share of |p|+|i|+|f|: mean {sum(fshare)/len(fshare):.2f}  (kf={2.4e-5})")

    # 6) EPS self-return signature: when output ~ 0 (controller relaxed) near a turn, does wheel return on its own?
    # find samples where |output|<0.1 but |actualAngle|>20 -> wheel held out with no controller torque
    relaxed_held=0; relaxed=0
    for s in eng:
        if abs(s["ps_output"])<0.1:
            relaxed+=1
            if abs(s["ps_psAngle"])>20: relaxed_held+=1
    if relaxed:
        out.append(f"  controller relaxed(|out|<0.1) while wheel out(>20deg): {relaxed_held}/{relaxed} ({100*relaxed_held/relaxed:.1f}%)  [EPS not self-centering fast]")

    # 7) torque CAN delivered vs output command (firmware response)
    can=[]
    for s in eng:
        oc=s.get("cc_torqueOutputCan")
        o=s.get("ps_output")
        if oc is not None and abs(o)>0.05:
            can.append((abs(oc), abs(o)))
    if can:
        ratios=[c/(o*4096) for c,o in can if o>0]
        out.append(f"  torqueOutputCan / (output*4096): mean {sum(ratios)/len(ratios):.2f}  (1.0 = full passthrough to CAN clamp)")
        out.append(f"  |torqueOutputCan| mean {sum(c for c,_ in can)/len(can):.0f}  max {max(c for c,_ in can):.0f}  (CAN clamp 4096)")

    return "\n".join(out)


def main():
    print("# Deep dive — slew lag, output sign, kp headroom, EPS self-return")
    for name, segs in ROUTES.items():
        sys.stderr.write(f"{name}...\n")
        samples = collect(segs)
        print(deep(name, samples))


if __name__ == "__main__":
    main()
