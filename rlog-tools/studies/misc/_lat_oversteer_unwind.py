"""Over-steer risk + unwind-strength characterization. Report-only.
- Over-steer signature: actual angle OVERSHOOTS desired (|actual|>|desired|) during/after wind.
- Unwind strength: does actual return as fast as desired? residual offset? does controller actively push to center
  or rely on EPS self-return (output~0 while still turned)?"""
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
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))
from _lat_wind_unwind import collect, engaged_segments, stats, pctl, ROUTES


def ana(name, samples):
    runs = engaged_segments(samples)
    if not runs:
        return f"\n## {name}: no engaged\n"
    out=[f"\n## {name}"]
    eng=[s for r in runs for s in r]

    # OVERSHOOT: |actual| exceeds |desired| (same sign) by margin -> over-rotation
    over=[]; under=[]
    for s in eng:
        a=s["ps_psAngle"]; d=s["ps_psDesired"]
        if abs(d)>5 and a*d>0:  # turning, same direction
            over.append(abs(a)-abs(d))  # >0 overshoot, <0 undershoot(lag)
    if over:
        ov=[x for x in over if x>2]; un=[x for x in over if x<-2]
        out.append(f"  turning samples(|des|>5): {len(over)} | overshoot(>2deg) {len(ov)} ({100*len(ov)/len(over):.0f}%) | undershoot/lag(<-2) {len(un)} ({100*len(un)/len(over):.0f}%)")
        out.append(f"  (actual-desired) signed: mean {sum(over)/len(over):.2f} p10 {pctl(over,.1):.1f} p90 {pctl(over,.9):.1f} deg  [<0 = lagging behind desired]")

    # UNWIND STRENGTH detail: during return-to-center segments, controller output vs reliance on EPS self-return
    # classify return ticks: |desired| decreasing & |desired|>5
    ret_active=0; ret_passive=0; ret_total=0
    ret_lag=[]
    for r in runs:
        for k in range(1,len(r)):
            d0=r[k-1]["ps_psDesired"]; d1=r[k]["ps_psDesired"]
            if abs(d1)>5 and abs(d1)<abs(d0)-0.05:  # unwinding
                ret_total+=1
                o=r[k]["ps_output"]; a=r[k]["ps_psAngle"]
                # active return = controller output pushing toward center (opposite sign to actual angle)
                if abs(o)>0.1 and o*a<0:
                    ret_active+=1
                elif abs(o)<0.1 and abs(a)>10:
                    ret_passive+=1  # relying on EPS self-return
                ret_lag.append(abs(a)-abs(d1))
    if ret_total:
        out.append(f"\n  UNWIND ticks(|des|>5,decreasing): {ret_total}")
        out.append(f"   active controller return(|out|>0.1 toward center): {ret_active} ({100*ret_active/ret_total:.0f}%)")
        out.append(f"   passive (|out|<0.1 while wheel>10deg, EPS self-return): {ret_passive} ({100*ret_passive/ret_total:.0f}%)")
        out.append(f"   (actualAngle-desiredAngle) during unwind: mean {sum(ret_lag)/len(ret_lag):.2f} p90 {pctl(ret_lag,.9):.1f} deg  [>0 = wheel still out, trailing the return]")

    # at LOW speed (mall, the test): same metrics restricted to vEgo<6 m/s
    low=[s for s in eng if s["cs_vEgo"]<6]
    if len(low)>200:
        loverr=[abs(s["ps_angleError"]) for s in low]
        loout=[abs(s["ps_output"]) for s in low]
        out.append(f"\n  LOW-SPEED(<6m/s) engaged {len(low)}: angleErr mean {sum(loverr)/len(loverr):.1f} p90 {pctl(loverr,.9):.1f} | |output| mean {sum(loout)/len(loout):.3f} p90 {pctl(loout,.9):.3f}")
        # kp at low speed: kpBP [0,10,35] kpV [.006,.03,.06] -> at v<6, kp interpolates .006..~.022
        out.append(f"   (lat-B kp at v<6m/s interpolates 0.006->~0.020; this is the WEAKEST kp regime — relevant to the mall test)")

    return "\n".join(out)


def main():
    print("# Over-steer risk + unwind-strength")
    for name, segs in ROUTES.items():
        sys.stderr.write(f"{name}...\n")
        samples = collect(segs)
        print(ana(name, samples))


if __name__ == "__main__":
    main()
