"""Summarise real-data xcorr peaks per route x speed bin and pooled, with block-bootstrap (within route) and
route-cluster bootstrap (pooled) 95 % CIs. Peak = sinc-interpolated lag of the positive extremum.
usage: python s04_summary_real.py [pair ...]   e.g. u_e4|acc_r
"""
import sys, json
import numpy as np
import xc_lib as X

rng = np.random.default_rng(7)
PAIRS = sys.argv[1:] or ["u_e4|acc_r", "u_e4|acc_a", "u_cs|acc_r", "u_cs|acc_a", "u_e4|ang", "u_e4|rate", "u_cs|ang"]
WIN = {"acc_r": (-50, 200), "acc_a": (-50, 200), "rate": (-50, 350), "ang": (-50, 400)}
NB = 400


def load(route):
    return dict(np.load(X.HERE / "_cache" / f"real_blocks_{route}.npz"))


def lag_of(C, Xs, Ys, win):
    if len(C) == 0:
        return np.nan, np.nan, np.nan
    cur = C.sum(0) / np.sqrt(Xs.sum() * Ys.sum())
    p, s, v = X.peak(cur, +1, *win)
    return p, s, v


def summarise(routes, pair, label):
    yk = pair.split("|")[1]; win = WIN[yk]
    B = {r: load(r) for r in routes}
    res = {}
    for bi in [0, 1, 2, None]:
        per_route = {}
        allC, allX, allY, owner = [], [], [], []
        for r in routes:
            m = np.ones(len(B[r]["bin"]), bool) if bi is None else (B[r]["bin"] == bi)
            C = B[r][pair + "|C"][m]; Xs = B[r][pair + "|X"][m]; Ys = B[r][pair + "|Y"][m]
            if len(C) == 0:
                continue
            p, s, v = lag_of(C, Xs, Ys, win)
            boots = []
            for _ in range(NB if len(C) >= 3 else 0):
                k = rng.integers(0, len(C), len(C))
                boots.append(lag_of(C[k], Xs[k], Ys[k], win)[1])
            ci = (np.percentile(boots, 2.5), np.percentile(boots, 97.5)) if boots else (np.nan, np.nan)
            per_route[r] = dict(par=p, sinc=s, corr=v, n=int(len(C)), ci=ci)
            allC.append(C); allX.append(Xs); allY.append(Ys); owner += [r] * len(C)
        if not allC:
            continue
        C = np.concatenate(allC); Xs = np.concatenate(allX); Ys = np.concatenate(allY); owner = np.array(owner)
        p, s, v = lag_of(C, Xs, Ys, win)
        rs = sorted(set(owner)); boots = []
        for _ in range(NB):
            pick = rng.choice(rs, len(rs))
            k = np.concatenate([np.where(owner == q)[0] for q in pick])
            boots.append(lag_of(C[k], Xs[k], Ys[k], win)[1])
        pooled = dict(par=p, sinc=s, corr=v, n=int(len(C)), nroutes=len(rs),
                      ci_route=(np.percentile(boots, 2.5), np.percentile(boots, 97.5)))
        res["all" if bi is None else X.BIN_NAMES[bi]] = dict(per_route=per_route, pooled=pooled)
    print(f"\n== {label}  {pair}  (lag ms: parabolic / sinc [95% CI], corr, blocks)")
    for bn, d in res.items():
        pp = d["pooled"]
        print(f"  bin {bn:5s} POOLED sinc {pp['sinc']:6.1f} par {pp['par']:6.1f} "
              f"route-CI [{pp['ci_route'][0]:5.1f},{pp['ci_route'][1]:5.1f}] corr {pp['corr']:+.3f} n{pp['n']} routes{pp['nroutes']}")
        for r, q in d["per_route"].items():
            print(f"      {r:22s} sinc {q['sinc']:6.1f} par {q['par']:6.1f} [{q['ci'][0]:5.1f},{q['ci'][1]:5.1f}] corr {q['corr']:+.3f} n{q['n']}")
    return res


if __name__ == "__main__":
    out = {}
    for pair in PAIRS:
        out["torque|" + pair] = summarise(X.TORQUE_ROUTES, pair, "TORQUE V293")
        out["v282|" + pair] = summarise(X.V282_ROUTES, pair, "V282 control")
    json.dump(out, open(X.HERE / "out" / "real_summary.json", "w"), indent=1, default=float)
