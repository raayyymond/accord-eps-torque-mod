"""Mandatory positive control: recover a KNOWN D (30, 60 ms) from the synthetic plant driven by a real logged command.

usage: python control.py [route] [maxchunks]
"""
import sys, json, time
from pathlib import Path
import numpy as np
import common as C, estimate as E, synth as Y

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
route = sys.argv[1] if len(sys.argv) > 1 else "0000006c--68c6e94b17"
R = C.load_route(route)
mask = C.handsoff_mask(R)
res = {}
cases = [
    ("open_F0.02_J8e-5", dict(J=8e-5, b=0.003, F=0.02)),
    ("open_F0_J8e-5", dict(J=8e-5, b=0.003, F=0.0)),
    ("open_F0.02_J3e-4", dict(J=3e-4, b=0.003, F=0.02)),
    ("open_F0.02_J8e-5_b0.005", dict(J=8e-5, b=0.005, F=0.02)),
    ("closed_Kr6e-4_Ka0.01_dist0.01", dict(J=8e-5, b=0.003, F=0.02, closed=True, Kr=0.0006, Ka=0.01, dist_rms=0.01)),
]
only = sys.argv[2] if len(sys.argv) > 2 else None
for name, kw in cases:
    if only and only not in name:
        continue
    for D in (0.030, 0.060):
        t0 = time.time()
        S = Y.simulate(R, mask, D, **kw)
        rows_f, rows = E.chunk_stack(S, mask, zkey="zexo")
        f = rows_f
        for lo, hi in C.SPEED_BINS:
            rr = [r for r in rows if lo <= r["v"] < hi]
            for est in ("direct", "iv"):
                for out in ("angle", "rate"):
                    x = E.fit_bin(f, rr, est=est, out=out, nboot=40)
                    key = f"{name}|D{int(D*1000)}|v{lo:.0f}-{hi:.0f}|{est}|{out}"
                    if x and x.get("fit"):
                        ft = x["fit"]
                        print(f"{key:60s} n{x['n_chunks']:3d} D {ft['D']*1e3:6.1f} ms  CI {[round(c*1e3,1) for c in x.get('D_boot_ci95',[np.nan,np.nan])]}"
                              f"  J {ft['J']:.2e} b {ft['b']:.2e} k {ft['k']:.2e}  corrDJ {ft['corr_D_J']:+.2f} bins {ft['nbins']}"
                              f"  gd_raw {x['group_delay_raw']['tau']*1e3 if x['group_delay_raw'] else float('nan'):6.1f}"
                              f"  gd_corr {x['group_delay_plant_removed']['tau']*1e3 if x['group_delay_plant_removed'] else float('nan'):6.1f}", flush=True)
                    else:
                        print(f"{key:60s} n{len(rr):3d} no coherent fit", flush=True)
                    res[key] = x
        print(f"  [{name} D={D}] {time.time()-t0:.0f} s", flush=True)
        del S, rows
(OUT / f"control_{route}.json").write_text(json.dumps(res, indent=1, default=float))
