"""Estimator-variant search on the synthetic positive control (bands, coherence gates, angle/rate/joint)."""
import sys, json, itertools
import numpy as np
import common as C, estimate as E, synth as Y
route = sys.argv[1] if len(sys.argv) > 1 else "0000006c--68c6e94b17"
R = C.load_route(route); mask = C.handsoff_mask(R)
plants = [("F.02_b.003_J8e-5", dict(J=8e-5, b=0.003, F=0.02)), ("F.02_b.005_J8e-5", dict(J=8e-5, b=0.005, F=0.02)),
          ("F.01_b.003_J8e-5", dict(J=8e-5, b=0.003, F=0.01)), ("F.02_b.003_J3e-4", dict(J=3e-4, b=0.003, F=0.02))]
bands = [(1.5, 8.0), (2.0, 10.0), (1.0, 6.0), (2.5, 10.0), (3.0, 12.0)]
out = {}
for pn, kw in plants:
    for D in (0.03, 0.06):
        S = Y.simulate(R, mask, D, **kw)
        f, rows = E.chunk_stack(S, mask, zkey="zexo")
        sel = [r for r in rows if r["v"] >= 8.0]
        Sx = E.combine(rows, [i for i, r in enumerate(rows) if r["v"] >= 8.0])
        Ha, ca = E.H_of(Sx, "direct", "angle"); Hr, cr = E.H_of(Sx, "direct", "rate")
        nave = len(sel) * 7
        for fb, cm in itertools.product(bands, (0.5, 0.7)):
            ra = C.fit_tf(f, -Ha, ca, nave, fband=fb, cmin=cm, out="angle")
            rr = C.fit_tf(f, -Hr, cr, nave, fband=fb, cmin=cm, out="rate")
            rj = C.fit_joint(f, -Ha, ca, -Hr, cr, nave, fband=fb, cmin=cm)
            g = lambda r: (round(r["D"] * 1e3 - D * 1e3, 1), f"{r['J']:.1e}") if r else None
            print(pn, int(D * 1e3), fb, cm, "angle", g(ra), "rate", g(rr), "joint", g(rj), flush=True)
        del S, rows
