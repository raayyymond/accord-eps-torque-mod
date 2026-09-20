# -*- coding: utf-8 -*-
"""i6 -- the command -> wheel-angle plant PROFILE over the identifiable band, per route and speed bin.

Prints |P_th| and its phase at a ladder of frequencies with the instrument coherence beside each, so
the band where the estimate means anything is visible rather than assumed.  A pure spring-mass
J*th'' + b*th' + k*th = torque behind a transport delay has phase ~ -w*tau at low frequency (-4 deg
at 0.2 Hz for tau = 60 ms).  Anything more than that is extra plant lag the physical model does not
carry, and it has to be either found or bracketed -- it is the single biggest lever on where the
-180 deg crossing lands.

ANALYSIS ONLY.  python i6_profile.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from i5_plant import ffts, BINS  # noqa: E402

FREQS = [0.098, 0.146, 0.195, 0.244, 0.293, 0.391, 0.488, 0.635, 0.781, 0.977, 1.27, 1.56, 1.95, 2.34, 2.93]


def profile(F, sel):
    f = F["f"]
    Z, SA, U = F["Z"][sel], F["SA"][sel], F["U"][sel]
    xs = lambda A, B: np.mean(np.conj(A) * B, axis=0)
    P = xs(Z, SA) / xs(Z, U)
    coh = lambda A, B: np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)
    czu, czs = coh(Z, U), coh(Z, SA)
    rows = []
    for q in FREQS:
        j = int(np.argmin(np.abs(f - q)))
        rows.append(dict(f=float(f[j]), mag=float(abs(P[j])), ph=float(np.degrees(np.angle(P[j]))),
                         coh_zu=float(czu[j]), coh_zsa=float(czs[j])))
    return rows


if __name__ == "__main__":
    out = {}
    for route in sys.argv[1:]:
        F = ffts(route)
        if F is None:
            continue
        out[route] = {}
        for tag, lo, hi in BINS:
            if tag not in ("15+", "5-15"):
                continue
            sel = (F["vmed"] >= lo) & (F["vmed"] < hi)
            if sel.sum() < 6:
                continue
            rows = profile(F, sel)
            v = float(np.median(F["vmed"][sel]))
            out[route][tag] = dict(v=v, n=int(sel.sum()), rows=rows)
            print(f"\n=== {route}  bin {tag}  n {sel.sum()}  v {v:.1f} m/s ===")
            print("     f      |P|      phase   coh(Z,U) coh(Z,SA)")
            for r in rows:
                print(f"  {r['f']:6.3f} {r['mag']:9.2f} {r['ph']:9.1f} "
                      f"{r['coh_zu']:9.2f} {r['coh_zsa']:9.2f}")
        del F
    json.dump(out, open(HERE / "out_i6_profile.json", "w"), indent=1)
