"""Summarise model-based xcorr runs (s06): blind plant selection by pooled rate-response correlation, then the delay
at that plant per speed bin and per route, with CIs.
usage: python s09_mb_summary.py <tag> [<tag> ...]
"""
import sys, json
import numpy as np
import xc_lib as X

rng = np.random.default_rng(11)
NB = 300


def rho(M, sel, si, pi=None):
    num = M["num"][:, sel, si, :].sum(1)                       # (P, d)
    nx = M["nx"][:, sel, si].sum(1)                            # (P,)
    ny = M["ny"][sel, si].sum()
    r = num / np.sqrt(nx[:, None] * ny + 1e-30)
    return r if pi is None else r[pi]


def dpeak(r, dgrid):
    i = int(np.argmax(r))
    if 0 < i < len(r) - 1:
        a, b, c = r[i - 1], r[i], r[i + 1]
        den = a - 2 * b + c
        d = 0.5 * (a - c) / den if den != 0 else 0.0
    else:
        d = 0.0
    step = (dgrid[1] - dgrid[0]) * 1e3
    return float(dgrid[i] * 1e3 + d * step), float(r[i])


def summarise(tag):
    M = dict(np.load(X.HERE / "_cache" / f"mb_{tag}.npz"))
    sigs = list(M["sigs"]); dg = M["dgrid"]; P = M["plants"]; nblk = len(M["bin"])
    allb = np.ones(nblk, bool)
    out = dict(tag=tag, truth=M["truth"].tolist())
    # blind plant selection on the rate response, all blocks pooled
    rr = rho(M, allb, sigs.index("rate"))
    best_rho = rr.max(1); order = np.argsort(-best_rho)
    pb = int(order[0])
    out["plant_rank"] = [dict(J=float(P[i][0]), b=float(P[i][1]), F=float(P[i][2]), ks=float(P[i][3]),
                              rho=float(best_rho[i]), D=dpeak(rr[i], dg)[0]) for i in order[:8]]
    # bootstrap the plant choice (route-cluster) -> set of plausible plants and the D spread across them
    routes = sorted(set(M["route"]))
    picks = []
    for _ in range(NB):
        sel_r = rng.choice(routes, len(routes))
        idx = np.concatenate([np.where(M["route"] == q)[0] for q in sel_r])
        num = M["num"][:, idx, sigs.index("rate"), :].sum(1); nx = M["nx"][:, idx, sigs.index("rate")].sum(1)
        ny = M["ny"][idx, sigs.index("rate")].sum()
        r = num / np.sqrt(nx[:, None] * ny)
        pi = int(np.argmax(r.max(1))); picks.append(pi)
    uniq, cnt = np.unique(picks, return_counts=True)
    out["plant_bootstrap"] = [dict(J=float(P[i][0]), b=float(P[i][1]), F=float(P[i][2]), frac=float(c / NB),
                                   D_all_rate=dpeak(rr[i], dg)[0]) for i, c in sorted(zip(uniq, cnt), key=lambda z: -z[1])]
    res = {}
    for sig in sigs:
        si = sigs.index(sig); res[sig] = {}
        for bi, bn in list(enumerate(X.BIN_NAMES)) + [(None, "all")]:
            sel = allb if bi is None else (M["bin"] == bi)
            if sel.sum() == 0:
                continue
            D0, r0 = dpeak(rho(M, sel, si, pb), dg)
            # route-cluster bootstrap at the chosen plant AND with plant re-selection inside each resample
            rs = sorted(set(M["route"][sel])); bs_fixed, bs_resel = [], []
            for _ in range(NB):
                pick = rng.choice(rs, len(rs))
                idx = np.concatenate([np.where((M["route"] == q) & sel)[0] for q in pick])
                s2 = np.zeros(nblk, bool); s2[idx] = True
                # duplicates matter: sum with multiplicity
                num = M["num"][:, idx, si, :].sum(1); nx = M["nx"][:, idx, si].sum(1); ny = M["ny"][idx, si].sum()
                r = num / np.sqrt(nx[:, None] * ny)
                bs_fixed.append(dpeak(r[pb], dg)[0])
                numr = M["num"][:, idx, sigs.index("rate"), :].sum(1); nxr = M["nx"][:, idx, sigs.index("rate")].sum(1)
                nyr = M["ny"][idx, sigs.index("rate")].sum()
                pr = int(np.argmax((numr / np.sqrt(nxr[:, None] * nyr)).max(1)))
                bs_resel.append(dpeak(r[pr], dg)[0])
            per_route = {}
            for q in rs:
                sq = sel & (M["route"] == q)
                Dq, rq = dpeak(rho(M, sq, si, pb), dg)
                ib = np.where(sq)[0]; bb = []
                for _ in range(NB if len(ib) >= 3 else 0):
                    idx = rng.choice(ib, len(ib))
                    num = M["num"][pb, idx, si, :].sum(0); nx = M["nx"][pb, idx, si].sum(); ny = M["ny"][idx, si].sum()
                    bb.append(dpeak(num / np.sqrt(nx * ny), dg)[0])
                per_route[q] = dict(D=Dq, rho=rq, n=int(sq.sum()),
                                    ci=[float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))] if bb else None)
            res[sig][bn] = dict(D=D0, rho=r0, n=int(sel.sum()), nroutes=len(rs),
                                ci_fixed_plant=[float(np.percentile(bs_fixed, 2.5)), float(np.percentile(bs_fixed, 97.5))],
                                ci_with_plant_reselection=[float(np.percentile(bs_resel, 2.5)), float(np.percentile(bs_resel, 97.5))],
                                per_route=per_route)
    out["res"] = res
    json.dump(out, open(X.HERE / "out" / f"mb_summary_{tag}.json", "w"), indent=1)
    print(f"\n==== {tag} truth {out['truth']}")
    print("  plant rank (rate):", "; ".join(f"J{p['J']:g} b{p['b']:g} F{p['F']:g} rho{p['rho']:.3f} D{p['D']:.1f}" for p in out["plant_rank"][:5]))
    print("  plant bootstrap:", "; ".join(f"J{p['J']:g} b{p['b']:g} F{p['F']:g} {p['frac']:.2f} D{p['D_all_rate']:.1f}" for p in out["plant_bootstrap"][:5]))
    for sig in sigs:
        for bn, d in res[sig].items():
            pr = " ".join(f"{q[:8]}:{v['D']:.1f}" + (f"[{v['ci'][0]:.0f},{v['ci'][1]:.0f}]" if v["ci"] else "") for q, v in d["per_route"].items())
            print(f"  {sig:5s} {bn:5s} D {d['D']:6.1f} rho {d['rho']:.3f} CI(fixed) [{d['ci_fixed_plant'][0]:.1f},{d['ci_fixed_plant'][1]:.1f}]"
                  f" CI(reselect) [{d['ci_with_plant_reselection'][0]:.1f},{d['ci_with_plant_reselection'][1]:.1f}] n{d['n']}  | {pr}")


if __name__ == "__main__":
    for t in sys.argv[1:]:
        summarise(t)
