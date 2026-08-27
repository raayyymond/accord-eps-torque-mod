"""Separate controller-bound vs firmware-bound lag.
Key question: when output IS large (near clamp), does the wheel slew fast (firmware OK, controller was the limit)
or does it STILL slew slow (firmware/EPS rate-limited)? Report-only."""
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
sys.path.insert(0, str(Path(__file__).parents[2]))
from _lat_wind_unwind import collect, engaged_segments, stats, pctl, ROUTES


def fw(name, samples):
    runs = engaged_segments(samples)
    if not runs:
        return f"\n## {name}: no engaged\n"
    out=[f"\n## {name}"]

    # Build per-tick with derived actual slew
    ticks=[]
    for r in runs:
        for k in range(1,len(r)):
            dt=r[k]["t"]-r[k-1]["t"]
            if dt<=0 or dt>0.1: continue
            da=abs((r[k]["ps_psAngle"]-r[k-1]["ps_psAngle"])/dt)
            s=r[k]
            ticks.append(dict(out=abs(s["ps_output"]), aslew=da,
                              eps=abs(s["cs_sTorqueEps"]), tq=abs(s["cs_sTorque"]),
                              vego=s["cs_vEgo"], ae=abs(s["ps_angleError"]),
                              pressed=s["cs_sPressed"]))

    # 1) For HIGH output (>0.8, controller pushing hard), what is achievable wheel slew?
    hi=[t for t in ticks if t["out"]>0.8 and not t["pressed"]]
    if hi:
        sl=[t["aslew"] for t in hi]
        out.append(f"  HIGH output(>0.8), no driver: n={len(hi)} | achieved actualSlew mean {sum(sl)/len(sl):.1f} p50 {pctl(sl,.5):.1f} p90 {pctl(sl,.9):.1f} deg/s")
        out.append(f"    -> if this is HIGH, firmware can slew fast & controller(low kp) was limiting. if LOW, firmware/EPS rate-limited.")
    lo=[t for t in ticks if 0.2<t["out"]<0.5 and not t["pressed"]]
    if lo:
        sl=[t["aslew"] for t in lo]
        out.append(f"  MID output(0.2-0.5), no driver:  n={len(lo)} | achieved actualSlew mean {sum(sl)/len(sl):.1f} p50 {pctl(sl,.5):.1f} p90 {pctl(sl,.9):.1f} deg/s")

    # 2) output vs achieved-slew curve (controllability): bin by output
    obins=[(0.0,0.2),(0.2,0.4),(0.4,0.6),(0.6,0.8),(0.8,0.95),(0.95,1.01)]
    out.append("  output bin | n | actualSlew mean | p90 | EPStorque mean")
    for b in obins:
        sel=[t for t in ticks if b[0]<=t["out"]<b[1] and not t["pressed"]]
        if sel:
            sl=[t["aslew"] for t in sel]; ep=[t["eps"] for t in sel]
            out.append(f"   [{b[0]:.2f}-{b[1]:.2f}) | {len(sel):>5} | {sum(sl)/len(sl):>6.1f} | {pctl(sl,.9):>6.1f} | {sum(ep)/len(ep):>6.0f}")

    # 3) EPS measured torque vs commanded output (does firmware deliver?)
    # steeringTorqueEps is the EPS motor torque. If output high but eps torque flat -> firmware clamp/limit.
    paired=[(t["out"], t["eps"]) for t in ticks if t["out"]>0.05 and not t["pressed"]]
    if paired:
        for lo_,hi_ in [(0.1,0.3),(0.3,0.6),(0.6,0.9),(0.9,1.01)]:
            sel=[e for o,e in paired if lo_<=o<hi_]
            if sel:
                out.append(f"  output[{lo_:.1f}-{hi_:.1f}) -> EPS torque mean {sum(sel)/len(sel):.0f} p90 {pctl(sel,.9):.0f}")

    return "\n".join(out)


def main():
    print("# Firmware-bound vs controller-bound separation")
    print("# steeringTorqueEps = EPS motor torque (firmware delivered). output = controller cmd (+/-1).")
    for name, segs in ROUTES.items():
        sys.stderr.write(f"{name}...\n")
        samples = collect(segs)
        print(fw(name, samples))


if __name__ == "__main__":
    main()
