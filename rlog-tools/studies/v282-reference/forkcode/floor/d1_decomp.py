# -*- coding: utf-8 -*-
"""d1 -- THE EXACT FOUR-WAY DECOMPOSITION OF THE GOAL METRIC'S ERROR.

The identity, exact per window per FFT bin for ANY complex V(f):

    X - Y  =  (X - Z)   +   (1 - V)*Z   +   V*D   -   r
              ^ (b)          ^ (c)          ^ (a)     ^ (d)
              setpoint       wheel-angle    loop      incoherent motion
              chain          -> yaw leg     error     r = Y - V*M  (by definition of V)

    proof:  (X-Z) + Z - V*Z + V*Z - V*M - (Y - V*M) = X - V*M - Y + V*M = X - Y.   QED

REACHABILITY (this is the whole point):
    (a) V*D   scales by rho = (1+L_old)/(1+L_new);  rho -> 0 as loop gain -> inf.   REACHABLE.
    (b) X-Z   is the reference path; no feedback gain touches it.                   NOT reachable by gain.
    (c) (1-V)*Z  is the vehicle's own steer->yaw response vs the fork's static map.
        It is OUTSIDE the feedback loop (the loop's measurement is M, not Y).       NOT reachable at all.
    (d) r     is the motion the measured wheel angle does not explain.              NOT reachable.

Power accounting.  The four terms are complex and add coherently, so |E|^2 != sum |T_k|^2.  Two
readings are printed, both exact:
    own    :  sum|T_k|^2 / sum|E|^2      -- how big each term is on its own (can exceed 1 in total)
    share  :  sum Re(conj(E) T_k) / sum|E|^2   -- adds to EXACTLY 1; can be negative when a term
              partially cancels the total.  This is the honest allocation of the metric.

POSITIVE CONTROLS printed before anything else:
    P1  the metric reproduces the brief's 1.3512 (T64) and 0.442 (V282) from the same windows
    P2  the identity residual is at machine precision
    P3  the shares add to 1.000000
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
KEYS = ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR")


def gather(routes):
    cols = {k: [] for k in KEYS}
    vm, rid = [], []
    f = laf = None
    for n, r in enumerate(routes):
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        laf = float(D["laf"])
        for k in cols:
            cols[k].append(D[k])
        vm.append(D["vmed"])
        rid.append(np.full(len(D["vmed"]), n))
        del D
    return dict(f=f, laf=laf, v=np.concatenate(vm), rid=np.concatenate(rid),
                **{k: np.concatenate(v) for k, v in cols.items()})


def fit_V(W, kind="dir"):
    """Per-bin M -> Y transfer, pooled over the window set."""
    M, Y, X = W["M"], W["Y"], W["X"]
    if kind == "dir":
        return np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    if kind == "iv":
        return np.sum(np.conj(X) * Y, 0) / np.sum(np.conj(X) * M, 0)
    if kind == "rev":
        return np.sum(np.conj(Y) * Y, 0) / np.sum(np.conj(Y) * M, 0)
    raise ValueError(kind)


def terms(W, Vf):
    """The four complex terms, (nwin, nf) each."""
    X, Y, Z, M = W["X"], W["Y"], W["Z"], W["M"]
    Vb = Vf[None, :]
    return dict(b_setpoint=X - Z, c_wheel2yaw=(1.0 - Vb) * Z, a_loop=Vb * (Z - M),
                d_incoh=-(Y - Vb * M))


def account(E, T, sel, px):
    """own-power and projection-share of each term, plus the metric each carries."""
    pe = float(np.sum(np.abs(E[:, sel]) ** 2))
    out = {}
    tot = 0.0
    for k, A in T.items():
        own = float(np.sum(np.abs(A[:, sel]) ** 2))
        shr = float(np.sum(np.real(np.conj(E[:, sel]) * A[:, sel])))
        tot += shr
        out[k] = dict(own_J=own / px, own_fracE=own / pe, share=shr / pe, share_J=shr / px)
    out["_check_share_sum"] = tot / pe
    out["_J"] = pe / px
    return out


def boot_ci(vals, weights=None, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    v = np.asarray(vals)
    out = []
    for _ in range(n):
        idx = rng.integers(0, len(v), len(v))
        out.append(v[idx].mean())
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def cluster_boot(W, Vf, sel, n=2000, seed=0):
    """Route-clustered bootstrap of the J and of each term's share."""
    rng = np.random.default_rng(seed)
    rids = np.unique(W["rid"])
    E = W["X"] - W["Y"]
    T = terms(W, Vf)
    keys = list(T)
    acc = {k: [] for k in keys}
    acc["J"] = []
    for _ in range(n):
        pick = rng.choice(rids, len(rids), replace=True)
        rows = np.concatenate([np.where(W["rid"] == p)[0] for p in pick])
        # resample windows inside each picked route too
        rows = rows[rng.integers(0, len(rows), len(rows))]
        px = float(np.sum(np.abs(W["X"][np.ix_(rows, np.where(sel)[0])]) ** 2))
        pe = float(np.sum(np.abs(E[np.ix_(rows, np.where(sel)[0])]) ** 2))
        acc["J"].append(pe / px)
        for k in keys:
            A = T[k][np.ix_(rows, np.where(sel)[0])]
            acc[k].append(float(np.sum(np.real(np.conj(E[np.ix_(rows, np.where(sel)[0])]) * A))) / px)
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in acc.items()}


def main():
    res = {}
    for lab, routes in (("T64", T64), ("V282", V282)):
        W = gather(routes)
        f = W["f"]
        sel = (f >= BAND[0]) & (f <= BAND[1])
        X, Y = W["X"], W["Y"]
        E = X - Y
        px = float(np.sum(np.abs(X[:, sel]) ** 2))
        J = float(np.sum(np.abs(E[:, sel]) ** 2)) / px
        print(f"\n{'='*102}\n{lab}: {X.shape[0]} windows over {len(routes)} routes.  "
              f"P1 metric J = {J:.4f}")
        store = dict(J=J, nwin=int(X.shape[0]))
        for kind in ("dir", "iv", "rev"):
            Vf = fit_V(W, kind)
            T = terms(W, Vf)
            resid = T["b_setpoint"] + T["c_wheel2yaw"] + T["a_loop"] + T["d_incoh"] - E
            rel = float(np.sqrt(np.sum(np.abs(resid[:, sel]) ** 2) / np.sum(np.abs(E[:, sel]) ** 2)))
            A = account(E, T, sel, px)
            print(f"\n  V estimator '{kind}'   P2 identity rel-residual {rel:.1e}   "
                  f"P3 shares sum {A['_check_share_sum']:.6f}")
            print(f"    {'term':14s} {'own |T|^2/|X|^2':>16s} {'own /|E|^2':>11s} "
                  f"{'SHARE of J':>11s} {'share x J':>10s}")
            for k in ("a_loop", "b_setpoint", "c_wheel2yaw", "d_incoh"):
                a = A[k]
                print(f"    {k:14s} {a['own_J']:16.4f} {a['own_fracE']:11.3f} "
                      f"{a['share']:11.3f} {a['share_J']:10.4f}")
            store[kind] = dict(V=[list(map(float, Vf.real)), list(map(float, Vf.imag))],
                               acct=A, rel=rel)
            # per sub-band
            print(f"    per sub-band SHARE (of that band's own error power):")
            print(f"    {'band':12s} {'J_band':>8s} {'a loop':>8s} {'b setpt':>8s} {'c yaw':>8s} {'d incoh':>8s}")
            bands = {}
            for lo, hi in SUB:
                s = (f >= lo) & (f < hi)
                Ab = account(E, T, s, px)
                print(f"    {f'{lo:.2f}-{hi:.2f}':12s} {Ab['_J']*float(np.sum(np.abs(E[:,s])**2))/max(float(np.sum(np.abs(E[:,s])**2)),1e-300):8.4f}"
                      f" {Ab['a_loop']['share']:8.3f} {Ab['b_setpoint']['share']:8.3f}"
                      f" {Ab['c_wheel2yaw']['share']:8.3f} {Ab['d_incoh']['share']:8.3f}")
                bands[f"{lo}-{hi}"] = Ab
            store[kind]["bands"] = bands
        res[lab] = store
        # band J contributions (of the ONE denominator)
        print(f"\n  band contributions to J (one denominator):")
        for lo, hi in SUB:
            s = (f >= lo) & (f < hi)
            print(f"    {lo:.2f}-{hi:.2f} Hz  Jband {float(np.sum(np.abs(E[:, s])**2))/px:7.4f}"
                  f"   demand share {float(np.sum(np.abs(X[:, s])**2))/px:6.3f}")
        del W
    json.dump(res, open(OUT / "d1_decomp.json", "w"))
    print("\nwrote out/d1_decomp.json")


if __name__ == "__main__":
    main()
