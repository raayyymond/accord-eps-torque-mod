"""Confound check 1: leave-one-route-out on rE_pD (pose-based relative error, 0.6-1.2 Hz),
speed bins 2-8 and 8-15 m/s, tercile 'all' and 'hi'. Uses the already-reduced s1_goal/_red/*.npz
(same channels the original finding used), so no rlog reload needed. Tests whether the headline
group numbers are driven by one route (esp. the 62-segment V282 route 0000006c--2bc842dbac).
"""
import json, glob
from pathlib import Path
import numpy as np
from scipy import signal

RED = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/_red')
S1 = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal')
OUT = Path(__file__).resolve().parent
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]
VB = ["2-8", "8-15", "15-22", ">22"]
BI = 3  # 0.60-1.20 Hz
rng = np.random.default_rng(7)

R1 = json.load(open(S1 / "s1_results.json"))
TERC_EDGES = R1["tercile_edges"]
ROUTE_META = R1["meta"]  # route -> {group, ...}


def load_route(f):
    D = np.load(f, allow_pickle=True)
    meta = json.loads(str(D["meta"]))
    s = D[f"b{BI}_valid"] & (D["vb"] >= 0)
    out = dict(route=meta["route"], group=meta["group"],
               vb=D["vb"][s], env=D[f"b{BI}_env"][s], x=D[f"b{BI}_x"][s], pD=D[f"b{BI}_pD"][s],
               run=D["run"][s], chunk=D["chunk"][s])
    return out


def chunk_sums(d, sel):
    key = d["run"][sel].astype(np.int64) * 10 ** 9 + d["chunk"][sel]
    uk, inv = np.unique(key, return_inverse=True)
    x = d["x"][sel].astype(np.float64); y = d["pD"][sel].astype(np.float64)
    cols = [np.ones_like(x), x * x, x * y, y * y]
    A = np.stack([np.bincount(inv, weights=c, minlength=len(uk)) for c in cols], 1)
    return A


def rE(A):
    n, Sxx, Sxy, Syy = A[:, 0].sum(), A[:, 1].sum(), A[:, 2].sum(), A[:, 3].sum()
    err = max(Syy - 2 * Sxy + Sxx, 0)
    return float(np.sqrt(err / max(Sxx, 1e-12))), float(n * 4 / 100.0)


def boot_rE(routes, A, nb=1000):
    ur = np.unique(routes)
    if len(ur) == 0:
        return (np.nan, np.nan)
    idx_by_r = [np.where(routes == r)[0] for r in ur]
    vals = []
    for _ in range(nb):
        rs = rng.integers(0, len(ur), len(ur))
        tot = np.zeros(4)
        for ri in rs:
            ii = idx_by_r[ri]
            tot += A[ii[rng.integers(0, len(ii), len(ii))]].sum(0)
        n, Sxx, Sxy, Syy = tot
        err = max(Syy - 2 * Sxy + Sxx, 0)
        vals.append(np.sqrt(err / max(Sxx, 1e-12)))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    files = sorted(glob.glob(str(RED / "*.npz")))
    routedata = {}
    for f in files:
        d = load_route(f)
        routedata[d["route"]] = d
        print("loaded", d["route"], d["group"], len(d["x"]), flush=True)

    results = []
    for vname, vi in [("2-8", 0), ("8-15", 1)]:
        for tname in ("all", "hi"):
            if tname == "hi":
                e1, e2 = TERC_EDGES[f"{vname}|0.6-1.2"]
            for g in GROUPS:
                routes_in_g = [rk for rk, m in ROUTE_META.items() if m["group"] == g and rk in routedata]
                if not routes_in_g:
                    continue
                # pooled (all routes in group)
                parts = []
                for rk in routes_in_g:
                    d = routedata[rk]
                    sel = (d["vb"] == vi)
                    if tname == "hi":
                        sel = sel & (d["env"] >= e2)
                    if sel.sum() < 10:
                        continue
                    A = chunk_sums(d, sel)
                    key = d["run"][sel].astype(np.int64) * 10 ** 9 + d["chunk"][sel]
                    uk = np.unique(key)
                    routeids = np.full(len(uk), rk)
                    parts.append((routeids, A))
                if not parts:
                    continue
                routeids_all = np.concatenate([p[0] for p in parts])
                A_all = np.concatenate([p[1] for p in parts], 0)
                pooled_rE, pooled_sec = rE(A_all)
                ci_lo, ci_hi = boot_rE(routeids_all, A_all)
                # leave-one-route-out (only meaningful if >=2 routes)
                loro = []
                for rk_drop in routes_in_g:
                    keep = routeids_all != rk_drop
                    if keep.sum() < 5 or (len(np.unique(routeids_all[keep])) == 0):
                        continue
                    A_k = A_all[keep]
                    e, s = rE(A_k)
                    loro.append(dict(dropped=rk_drop, rE=e, sec=s, nroutes_left=int(len(np.unique(routeids_all[keep])))))
                # single-route breakdown
                per_route = []
                for rk in routes_in_g:
                    d = routedata[rk]
                    sel = (d["vb"] == vi)
                    if tname == "hi":
                        sel = sel & (d["env"] >= e2)
                    if sel.sum() < 10:
                        per_route.append(dict(route=rk, rE=None, sec=float(sel.sum() * 4 / 100.0)))
                        continue
                    A = chunk_sums(d, sel)
                    e, s = rE(A)
                    per_route.append(dict(route=rk, rE=e, sec=s))
                results.append(dict(vb=vname, terc=tname, group=g, rE_pooled=pooled_rE, ci=[ci_lo, ci_hi],
                                     sec=pooled_sec, nroutes=len(routes_in_g), loro=loro, per_route=per_route))
                print(f"{vname:6s} {tname:4s} {g:8s} pooled rE={pooled_rE:.3f} [{ci_lo:.3f},{ci_hi:.3f}] "
                      f"sec={pooled_sec:.0f} nroutes={len(routes_in_g)}", flush=True)
                for L in loro:
                    print(f"    drop {L['dropped']:24s} -> rE={L['rE']:.3f} sec={L['sec']:.0f} routes_left={L['nroutes_left']}")
                for pr in per_route:
                    if pr['rE'] is not None:
                        print(f"    solo {pr['route']:24s} -> rE={pr['rE']:.3f} sec={pr['sec']:.0f}")
                    else:
                        print(f"    solo {pr['route']:24s} -> (too few samples, {pr['sec']:.0f}s)")

    json.dump(results, open(OUT / "v1_loro_results.json", "w"), indent=1)
    print("wrote v1_loro_results.json")


if __name__ == "__main__":
    main()
