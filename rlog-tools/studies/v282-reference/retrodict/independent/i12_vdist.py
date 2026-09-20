# -*- coding: utf-8 -*-
"""i12 -- the FRAME-LEVEL speed histogram of each route's engaged hands-off >=15 m/s population.

The error notch recomputes its centre every frame from that frame's speed, so the transfer that acts
over a stretch of driving is the frame-weighted average of the per-speed notches.  This dumps the
weights.  Also dumps the within-10.24 s-window speed spread, which is what actually smears a single
spectral estimate.

ANALYSIS ONLY.  python i12_vdist.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

EDGES = np.arange(14.0, 36.01, 1.0)


def run(route):
    S = V.load(route)
    m = S["active"] & ~S["pressed"] & ~S["sat"] & (S["v"] >= 15.0) & np.isfinite(S["v"])
    v = S["v"][m]
    h, _ = np.histogram(v, bins=EDGES)
    # within-window spread
    spreads = []
    for a, b in V.runs(m, S["t"], min_s=10.24):
        for s in range(a, b - 1024 + 1, 512):
            vv = S["v"][s:s + 1024]
            spreads.append(float(vv.max() - vv.min()))
    out = dict(n=int(m.sum()), v_med=float(np.median(v)), v_iqr=[float(np.percentile(v, 25)),
               float(np.percentile(v, 75))], centers=list(map(float, 0.5 * (EDGES[:-1] + EDGES[1:]))),
               weights=list(map(float, h / max(h.sum(), 1))),
               win_spread_med=float(np.median(spreads)) if spreads else None,
               win_spread_p90=float(np.percentile(spreads, 90)) if spreads else None)
    del S
    return out


if __name__ == "__main__":
    res = {}
    for r in sys.argv[1:]:
        d = run(r)
        res[r] = d
        print(f"{r}  n {d['n']:7d}  v {d['v_med']:5.1f} [{d['v_iqr'][0]:.1f}-{d['v_iqr'][1]:.1f}]  "
              f"within-window spread med {d['win_spread_med']:.1f} p90 {d['win_spread_p90']:.1f} m/s")
    json.dump(res, open(HERE / "out_i12_vdist.json", "w"), indent=1)
