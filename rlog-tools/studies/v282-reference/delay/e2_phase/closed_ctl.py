"""Closed-loop bias test: synthetic plant + a feedback controller on the measurement (D_ctl 11 ms) + disturbance torque.
DIRECT (u->y) vs IV (exogenous command -> y). Friction off and on."""
import sys
import numpy as np
import common as C, estimate as E, synth as Y
route = sys.argv[1] if len(sys.argv) > 1 else "0000006c--68c6e94b17"
R = C.load_route(route); mask = C.handsoff_mask(R)
for name, kw in [("F0_Kr6e-4_Ka0.01_d0.01", dict(F=0.0, closed=True, Kr=0.0006, Ka=0.01, dist_rms=0.01)),
                 ("F0_Kr6e-4_Ka0_d0.003", dict(F=0.0, closed=True, Kr=0.0006, Ka=0.0, dist_rms=0.003)),
                 ("F.02_Kr6e-4_Ka0.01_d0.01", dict(F=0.02, closed=True, Kr=0.0006, Ka=0.01, dist_rms=0.01))]:
    for D in (0.03, 0.06):
        S = Y.simulate(R, mask, D, J=8e-5, b=0.003, **kw)
        f, rows = E.chunk_stack(S, mask, zkey="zexo")
        for lo, hi in [(0, 8), (8, 99)]:
            rr = [r for r in rows if lo <= r["v"] < hi]
            for est in ("direct", "iv"):
                x = E.fit_bin(f, rr, est=est, out="rate", nboot=0)
                ft = x["fit"] if x else None
                print(name, int(D*1e3), f"v{lo}-{hi}", est, "n", len(rr),
                      (round(ft["D"]*1e3, 1), f"{ft['J']:.1e}", f"b{ft['b']:.1e}", ft["nbins"]) if ft else None, flush=True)
        del S, rows
