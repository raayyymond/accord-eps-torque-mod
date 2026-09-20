"""Real-data xcorr: command (sendcan 0xE4 clock AND controlsState clock) vs steering acceleration (from rate, from
angle) and vs angle, hands-off lateral-engaged, 12 s blocks (1 s filter edge each side -> 10 s scored), per speed bin.
Writes _cache/real_blocks_<route>.npz ; summary printed by s04.
usage: python s02_real_xcorr.py [routes...]
"""
import sys
import numpy as np
import xc_lib as X

PAIRS = [("u_e4", "acc_r"), ("u_e4", "acc_a"), ("u_e4", "ang"), ("u_e4", "rate"),
         ("u_cs", "acc_r"), ("u_cs", "acc_a"), ("u_cs", "ang")]
BLK = 1200


def blocks_of(G, vmin=0.0):
    out = []
    for a, b in X.runs(G["ok"] & (G["v"] > 0.5), BLK):
        for s in range(a, b - BLK + 1, BLK):
            out.append((s, s + BLK))
    return out


def run(route):
    R = X.load_route(route); G = X.grid_route(R); del R
    Y = X.responses(G["sa"], G["sr"])
    acc = {p: X.XC() for p in PAIRS}
    meta = []
    for s, e in blocks_of(G):
        vmed = float(np.median(G["v"][s:e]))
        bi = next(i for i, (lo, hi) in enumerate(X.SPEED_BINS) if lo <= vmed < hi)
        for (uk, yk) in PAIRS:
            acc[(uk, yk)].add(G[uk][s:e], Y[yk][s:e], bi, route)
        meta.append((s, e, vmed, bi))
    out = {}
    for (uk, yk), xc in acc.items():
        out[f"{uk}|{yk}|C"] = np.array([b[2] for b in xc.blocks])
        out[f"{uk}|{yk}|X"] = np.array([b[3] for b in xc.blocks])
        out[f"{uk}|{yk}|Y"] = np.array([b[4] for b in xc.blocks])
    out["bin"] = np.array([m[3] for m in meta]); out["vmed"] = np.array([m[2] for m in meta])
    out["s"] = np.array([m[0] for m in meta]); out["tstart"] = G["t"][out["s"]] if len(meta) else np.array([])
    np.savez(X.HERE / "_cache" / f"real_blocks_{route}.npz", **out)
    print(route, "blocks", len(meta), "per bin", np.bincount(out["bin"], minlength=3) if len(meta) else 0, flush=True)


if __name__ == "__main__":
    for r in (sys.argv[1:] or X.TORQUE_ROUTES + X.V282_ROUTES):
        run(r)
