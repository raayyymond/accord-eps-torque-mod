# -*- coding: utf-8 -*-
"""ADV7: the four things left, then the verdict arithmetic.

  (1) Is the asymptote robust to the window length, and to a V estimator built from the two brackets
      where each is admissible?  (An adversary reports the attacks that MISS as well.)
  (2) NONLINEARITY: split the windows by demand amplitude and re-identify the plant and the loop.
      A gain sized on pooled windows is only valid if the plant does not move with amplitude.
  (3) The sign of the closed-loop correction to the shake cost: |S| in the shake band vs dose.
  (4) The ceiling arithmetic: what dose each closure level needs, against the toggle ceiling and
      against the one flown instability anchor.
"""
import json
import sys

import numpy as np

import advlib as A
from adv4_loop import BANDS, C_of, NPS, SHAKE, gather

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]


def pack(rks, nps):
    sp = {k: [] for k in ("X", "Z", "M", "Y", "U")}
    vs, rkl, am = [], [], []
    fr = None
    for rk in rks:
        N = A.load_nodes(rk)
        f, s, v = A.windows(N, nperseg=nps, overlap=0.5, minrun=30.0)
        fr = f
        for k in sp:
            sp[k].append(s[k])
        vs.append(v); rkl += [rk] * len(v)
        # per-window demand amplitude, from the spectrum itself (Parseval on the band)
        sel = A.bandsel(f)
        am.append(np.sqrt(np.sum(np.abs(s["X"][:, sel]) ** 2, 1)))
        del N, s
    return fr, {k: np.concatenate(v_) for k, v_ in sp.items()}, np.concatenate(vs), np.array(rkl), np.concatenate(am)


def asym(fr, sp, kind="dir", cohcut=None):
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    sel = A.bandsel(fr)
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    Vd = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    Vi = np.sum(np.conj(X) * Y, 0) / np.sum(np.conj(X) * M, 0)
    cohMY = np.abs(np.sum(np.conj(M) * Y, 0)) ** 2 / (np.sum(np.abs(M) ** 2, 0) * np.sum(np.abs(Y) ** 2, 0))
    Vh = {"dir": Vd, "iv": Vi, "hybrid": np.where(cohMY >= 0.7, Vi, Vd)}[kind]
    J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    Ji = float(np.sum(np.abs((E - Vh[None, :] * D)[:, sel]) ** 2) / den)
    return J0, Ji


def main():
    print("(1) IS THE ASYMPTOTE ROBUST TO THE CHOICES THAT ARE NOT WRITTEN DOWN?")
    print(f"  {'nperseg':>8s} {'J_T64':>7s} {'J_V282':>7s} {'V est':>7s} {'J_inf':>7s} {'closure %':>10s}")
    keep = None
    for nps in (512, 1024, 2048):
        frT, spT, vsT, rklT, amT = pack(T64, nps)
        frV, spV, _, _, _ = pack(V282, nps)
        JV, _ = asym(frV, spV)
        for kind in ("dir", "hybrid", "iv"):
            J0, Ji = asym(frT, spT, kind)
            print(f"  {nps:8d} {J0:7.3f} {JV:7.3f} {kind:>7s} {Ji:7.3f} {100*(J0-Ji)/(J0-JV):10.1f}")
        if nps == NPS:
            keep = (frT, spT, vsT, rklT, amT, J0, JV)
        del spV
    fr, sp, vs, rkl, am, J0, JV = keep

    print("\n  PER-ROUTE asymptote (the number is quoted as one figure; here is its route scatter):")
    for rk in T64 + V282:
        fr1, sp1, _, _, _ = pack([rk], NPS)
        j0, ji = asym(fr1, sp1)
        print(f"    {rk[:8]} {A.FLOWN[rk]['fam']:7s} J {j0:6.3f}  J_inf {ji:6.3f}  own-route closure vs V282 pooled "
              f"{100*(j0-ji)/(j0-JV):6.1f} %")
        del sp1

    print("\n(2) NONLINEARITY: the plant re-identified inside amplitude terciles of the SAME routes")
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    q1, q2 = np.percentile(am, [33.3, 66.7])
    labs = [("low  |X|", am <= q1), ("mid  |X|", (am > q1) & (am <= q2)), ("high |X|", am > q2)]
    print(f"  {'tercile':>9s} {'n':>4s} {'med |X|':>8s} " + "".join(f"{f'|P| {b1}-{b2}':>14s}" for b1, b2 in BANDS[:3]))
    Ps = {}
    for lab, msk in labs:
        P = np.sum(np.conj(X[msk]) * M[msk], 0) / np.sum(np.conj(X[msk]) * U[msk], 0)
        Ps[lab] = P
        w = np.sum(np.abs(X[msk]) ** 2, 0)
        print(f"  {lab:>9s} {int(msk.sum()):4d} {np.median(am[msk]):8.2f} " +
              "".join(f"{np.average(np.abs(P[(fr>=b1)&(fr<b2)]), weights=w[(fr>=b1)&(fr<b2)]):14.2f}"
                      for b1, b2 in BANDS[:3]))
    for b1, b2 in BANDS[:3]:
        s = (fr >= b1) & (fr < b2)
        w = np.sum(np.abs(X) ** 2, 0)[s]
        r = [np.average(np.abs(Ps[l][s]), weights=w) for l, _ in labs]
        print(f"    {b1:.2f}-{b2:.2f} Hz: high/low |P| = {r[2]/r[0]:.2f}x   "
              f"(=1.00 would mean the plant is amplitude-linear there)")

    print("\n(3) THE CLOSED-LOOP CORRECTION TO THE SHAKE COST -- its SIGN")
    P_iv = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    metas = {rk: A.FLOWN[rk] for rk in T64}
    wl = np.abs(X) ** 2
    ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])
    base = None
    print(f"  {'SteerKP':>8s} {'|S| 1.8-3.5':>12s} {'ratio to flown':>15s} {'|S| peak 2.05Hz':>16s}")
    for kpm in (1.0, 1.5, 2.0, 2.5, 3.0):
        Cw = np.array([C_of(fr, v, dict(metas[rk], kp=metas[rk]["kp"] * kpm)) for v, rk in zip(vs, rkl)])
        L = P_iv[None, :] * Cw
        Sm = np.abs(1.0 / (1.0 + L))
        s_band = float(np.average(Sm[:, ssh], weights=wl[:, ssh]))
        pk = float(np.average(Sm[:, (fr > 2.0) & (fr < 2.1)]))
        if base is None:
            base = s_band
        print(f"  {kpm:8.1f} {s_band:12.3f} {s_band/base:15.3f} {pk:16.3f}")
    print("  => the loop AMPLIFIES in this band and amplifies MORE with dose, so the closed-loop")
    print("     correction to a command-side shake estimate is upward, not the quoted downward one.")

    print("\n(4) CEILING ARITHMETIC")
    Vh = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    E, D = X - Y, Z - M
    sel = A.bandsel(fr)
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    Ares = E - Vh[None, :] * D
    C1 = np.array([C_of(fr, v, metas[rk]) for v, rk in zip(vs, rkl)])
    L1 = P_iv[None, :] * C1
    l1sh = float(np.average(np.abs(L1[:, ssh]), weights=wl[:, ssh]))

    def J_k(k):
        L2 = P_iv[None, :] * np.array([C_of(fr, v, dict(metas[rk], kp=metas[rk]["kp"] * k))
                                       for v, rk in zip(vs, rkl)])
        Ek = Ares + Vh[None, :] * (D * (1 + L1) / (1 + L2))
        return float(np.sum(np.abs(Ek[:, sel]) ** 2) / den), float(np.average(np.abs(L2[:, ssh]), weights=wl[:, ssh])), \
            float(np.max(np.abs(1 / (1 + L2))[:, sel]))

    print(f"  {'closure %':>10s} {'needs SteerKP':>14s} {'|L| shake':>10s} {'max|S|':>8s} {'verdict':>34s}")
    ks = np.arange(1.0, 12.01, 0.05)
    cache = {}
    for target in (20, 25, 30, 39.3, 45, 50, 60, 75, 100):
        kk = None
        for k in ks:
            if k not in cache:
                cache[k] = J_k(k)
            j, lsh, ms = cache[k]
            if 100 * (J0 - j) / (J0 - JV) >= target:
                kk = (k, lsh, ms); break
        if kk is None:
            print(f"  {target:10.1f} {'>12':>14s}")
            continue
        k, lsh, ms = kk
        v = []
        if k > 3.0:
            v.append("ABOVE the toggle ceiling 3.0")
        if lsh > 0.46:
            v.append("ABOVE r71's limit-cycle |L|")
        if ms > 2.0:
            v.append("Ms>2")
        print(f"  {target:10.1f} {k:14.2f} {lsh:10.3f} {ms:8.2f} {(' + '.join(v) if v else 'inside both anchors'):>34s}")
    print(f"\n  flown shake-band |L| = {l1sh:.3f}; toggle ceiling SteerKP 3.0 (0.6*5.0);"
          f" r71 limit-cycled at |L| 0.46.")
    json.dump(dict(J0=J0, JV=JV, Lshake=l1sh), open(A.OUT / "adv7.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
