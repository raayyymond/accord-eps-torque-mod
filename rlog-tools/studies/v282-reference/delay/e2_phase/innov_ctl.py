"""Validate the INNOVATION instrument on the closed-loop synthetic (where DIRECT was biased) and the open-loop one."""
import sys
import numpy as np
import common as C, estimate as E, synth as Y
route = sys.argv[1] if len(sys.argv) > 1 else "0000006c--68c6e94b17"
R = C.load_route(route); mask = C.handsoff_mask(R)
for name, kw in [("closed_F0_Ka.01_d.01", dict(F=0.0, closed=True, Kr=0.0006, Ka=0.01, dist_rms=0.01)),
                 ("closed_F.02_Ka.01_d.01", dict(F=0.02, closed=True, Kr=0.0006, Ka=0.01, dist_rms=0.01)),
                 ("closed_F.02_Kr.002_Ka.02_d.005", dict(F=0.02, closed=True, Kr=0.002, Ka=0.02, dist_rms=0.005)),
                 ("open_F.02", dict(F=0.02))]:
    for D in (0.03, 0.06):
        S = Y.simulate(R, mask, D, J=8e-5, b=0.003, **kw)
        S["innov"] = C.innovation(S, mask)
        f, rows = E.chunk_stack(S, mask, zkey="innov")
        for lo, hi in [(0, 8), (8, 15), (15, 99), (8, 99)]:
            rr = [r for r in rows if lo <= r["v"] < hi]
            line = f"{name} D{int(D*1e3)} v{lo}-{hi} n{len(rr)}"
            for est in ("direct", "iv"):
                x = E.fit_bin(f, rr, est=est, out="rate", nboot=0)
                ft = x["fit"] if x else None
                line += f" | {est} " + (f"{ft['D']*1e3:.1f} J{ft['J']:.1e} nb{ft['nbins']}" if ft else "--")
            print(line, flush=True)
        del S, rows
