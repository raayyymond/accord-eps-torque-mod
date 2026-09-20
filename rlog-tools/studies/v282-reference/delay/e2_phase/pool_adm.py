"""Pooled D_act over the ADMISSIBLE bins only.

Admissibility (declared before looking at D): a route x speed bin is admissible only if the fitted
exp(-jwD)*ZOH*1/(Js^2+bs+k) reproduces the measured phase within +/-15 deg over the coherent band AND the
model-free plant-removed group delay is POSITIVE. Bins whose measured |H| is flat-or-rising while the phase LEADS
with frequency are rejected: no causal minimum-phase system can do that, so no delay can be read from them.
By that rule the admissible set is {0000006c--68c6e94b17, 0000006e--6ca3e014fd} x v<8 m/s (+ 00000075 marginal).

Reports the pooled fit and a route-cluster bootstrap (routes resampled with replacement, chunks resampled inside
each drawn route).
"""
import numpy as np
import common as C, estimate as E

SETS = {
    "admissible_v0-8": [("0000006c--68c6e94b17", 0, 8), ("0000006e--6ca3e014fd", 0, 8)],
    "admissible_plus_75_v0-8": [("0000006c--68c6e94b17", 0, 8), ("0000006e--6ca3e014fd", 0, 8),
                                ("00000075--6c8687d5bd", 0, 8)],
}


def load(route):
    Z = np.load(f"out/spectra_{route}.npz")
    ks = [k for k in Z.files if k.startswith("S")]
    return Z["f"], [dict(v=float(Z["v"][i]), **{k: Z[k][i] for k in ks}) for i in range(len(Z["v"]))]


cache = {}
for name, spec in SETS.items():
    per = {}
    for route, lo, hi in spec:
        if route not in cache:
            cache[route] = load(route)
        f, rows = cache[route]
        per[route] = [r for r in rows if lo <= r["v"] < hi]
    pooled = [r for v in per.values() for r in v]
    x = E.fit_bin(f, pooled, est="direct", out="rate", nboot=0,
                  jgrid=[2e-5, 4e-5, 8e-5, 1.5e-4, 3e-4])
    ft = x["fit"]
    print(f"\n== {name}: routes {len(per)} chunks {len(pooled)}")
    print(f"   D {ft['D']*1e3:.1f} ms  sdD {ft['sdD']*1e3:.1f}  J {ft['J']:.2e}  b {ft['b']:.1e}  k {ft['k']:.1e} "
          f"corrDJ {ft['corr_D_J']:+.2f}  bins {ft['nbins']}  f {ft['fmin']:.1f}-{ft['fmax']:.1f}")
    print(f"   group delay raw {x['group_delay_raw']['tau']*1e3:+.1f} ms  plant-removed "
          f"{x['group_delay_plant_removed']['tau']*1e3:+.1f} ms")
    print("   J-profile (J, D ms, cost):", [(f"{p['J']:.0e}", round(p["D"] * 1e3, 1), round(p["cost"], 1))
                                            for p in x["J_profile"]])
    rng = np.random.default_rng(11)
    names = list(per)
    Ds = []
    for _ in range(300):
        pick = rng.choice(names, len(names))
        rb = []
        for t in pick:
            cand = per[t]
            rb += [cand[i] for i in rng.integers(0, len(cand), len(cand))]
        xb = E.fit_bin(f, rb, est="direct", out="rate", nboot=0)
        if xb and xb.get("fit"):
            Ds.append(xb["fit"]["D"])
    Ds = np.array(Ds) * 1e3
    print(f"   route-cluster bootstrap n={len(Ds)}  median {np.median(Ds):.1f}  "
          f"CI95 [{np.percentile(Ds,2.5):.1f}, {np.percentile(Ds,97.5):.1f}] ms")
