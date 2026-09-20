# -*- coding: utf-8 -*-
"""f2 -- reproduce the GOAL METRIC from the f1 windows, and check the X-Y = A + V*D identity.

METRIC (the brief's, unchanged): total X->Y error power over 0.15-2.4 Hz divided by total demand
power, ONE denominator across bands, >= 15 m/s, laterally engaged hands-off runs >= 30 s.

IDENTITY.  With V the MEASURED wheel-angle-measurement -> achieved-lateral-accel leg (H1, per family),
    X - Y  ==  A + V*D ,   D = Z - M (the loop's own error) ,   A := (X - Y) - V*D
A is a RESIDUAL BY CONSTRUCTION, so the identity is exact per window per bin; the only modelled step
downstream is that a loop change multiplies D by the sensitivity ratio and leaves A alone.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

BAND = (0.15, 2.4)
SHAKE = (1.8, 3.5)
FAMS = ["V282", "V282old", "T64", "T64B", "T5", "T4", "RF00T", "T2", "T3", "T3R"]


def load(route):
    D = np.load(OUT / f"f1_{route}.npz")
    return {k: D[k] for k in D.files}


def band_idx(f, lo, hi):
    return (f >= lo) & (f <= hi)


def main():
    meta = json.load(open(OUT / "f1_meta.json"))
    per = {}
    fam_acc = {}
    for route, m in meta.items():
        if m["nwin"] == 0:
            continue
        D = load(route)
        f = D["f"]
        b = band_idx(f, *BAND)
        X, Y, Z, M = D["X"], D["Y"], D["Z"], D["M"]
        # sign / alignment positive control: coherent gain of the achieved accel on the measurement
        num = np.sum(np.conj(M[:, b]) * Y[:, b])
        den = np.sum(np.abs(M[:, b]) ** 2)
        Vsc = num / den
        E = X - Y
        pe = float(np.sum(np.abs(E[:, b]) ** 2))
        px = float(np.sum(np.abs(X[:, b]) ** 2))
        pxall = float(np.sum(np.abs(X) ** 2))
        per[route] = dict(group=m["group"], nwin=m["nwin"], sec=m["sec"],
                          metric_inband=pe / px, metric_alldenom=pe / pxall,
                          Vscalar=complex(Vsc), pe=pe, px=px)
        g = m["group"]
        a = fam_acc.setdefault(g, dict(pe=0.0, px=0.0, pxall=0.0, n=0, sec=0.0))
        a["pe"] += pe; a["px"] += px; a["pxall"] += pxall; a["n"] += m["nwin"]; a["sec"] += m["sec"]
        del D

    print("PER ROUTE  (metric = in-band error power / in-band demand power)")
    print(f"{'route':24s} {'fam':8s} {'nwin':>5s} {'sec':>7s} {'metric':>8s} {'/allband':>9s} {'|V|':>6s} {'argV deg':>9s}")
    for r, p in per.items():
        v = p["Vscalar"]
        print(f"{r:24s} {p['group']:8s} {p['nwin']:5d} {p['sec']:7.1f} {p['metric_inband']:8.3f} "
              f"{p['metric_alldenom']:9.3f} {abs(v):6.3f} {np.degrees(np.angle(v)):9.1f}")
    print()
    print("POOLED PER FAMILY")
    print(f"{'fam':8s} {'nwin':>5s} {'sec':>7s} {'metric':>8s} {'/allband':>9s}")
    for g in FAMS:
        if g not in fam_acc:
            continue
        a = fam_acc[g]
        print(f"{g:8s} {a['n']:5d} {a['sec']:7.1f} {a['pe']/a['px']:8.3f} {a['pe']/a['pxall']:9.3f}")
    json.dump({k: {kk: (str(vv) if isinstance(vv, complex) else vv) for kk, vv in v.items()}
               for k, v in per.items()}, open(OUT / "f2_metric.json", "w"), indent=1)


if __name__ == "__main__":
    main()
