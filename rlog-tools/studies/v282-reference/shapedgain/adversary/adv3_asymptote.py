# -*- coding: utf-8 -*-
"""ADV3: ATTACK THE 109 % ASYMPTOTE.

The claim: under the identity  X - Y = A + V*D  (A the setpoint chain, V the measured wheel->yaw leg,
D the loop's error), driving the loop gain to infinity drives D -> 0, leaving J_inf = sum|A|^2/sum|X|^2,
and that residual is BELOW V282's 0.442, hence 'closure 109 %'.

Three independent things have to be true for that number, and each is tested here.

  (1) WHAT GOES INTO A.  Two readings of 'A = the setpoint chain' give different answers:
        A_res = (X - Y) - V*D             -- residual; the identity is then EXACT by construction,
                                             and everything the wheel angle does not explain
                                             (road disturbance, pose noise, model error in V, the
                                             incoherent 76 %) is INSIDE A.
        A_con = (X - Z) + (1 - V)*Z       -- constructed from the setpoint chain and the wheel->yaw
                                             deficit.  A_con + V*D = X - V*M, which is NOT X - Y:
                                             it silently DROPS r = Y - V*M.
      If the asymptote was computed with A_con, it is understated by exactly the power of r.
  (2) HOW D IS SCALED.  D = S*W with S = 1/(1+L).  Scaling the controller by k gives
      D_k = D * (1+L)/(1+kL), a COMPLEX factor.  A and V*D add coherently, so replacing that factor
      by its MAGNITUDE changes the cross-term.  Both are computed.
  (3) WHETHER V IS AN ESTIMATE THE ANSWER SURVIVES.  Three estimators for V, reported as a spread.

Outputs J_inf and the implied closure for every combination, so the reader can see the range the
single number '109 %' was drawn from.
"""
import json
import sys

import numpy as np

import advlib as A

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
NPS = 1024           # the setting that reproduces the handed-down pair to 2.5 % (ADV2)
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]


def gather(rks):
    sp = {k: [] for k in ("X", "Z", "M", "Y", "U")}
    vs = []
    fr = None
    for rk in rks:
        N = A.load_nodes(rk)
        f, s, v = A.windows(N, nperseg=NPS, overlap=0.5, minrun=30.0)
        fr = f
        for k in sp:
            sp[k].append(s[k])
        vs.append(v)
        del N, s
    return fr, {k: np.concatenate(v_) for k, v_ in sp.items()}, np.concatenate(vs)


def estimate_V(sp, kind):
    """Per-bin wheel-angle(M) -> achieved(Y) transfer, pooled over windows."""
    M, Y, X = sp["M"], sp["Y"], sp["X"]
    if kind == "dir":                      # least squares Y on M
        return np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    if kind == "iv":                       # instrument X (exogenous to road / pose noise)
        return np.sum(np.conj(X) * Y, 0) / np.sum(np.conj(X) * M, 0)
    if kind == "rev":                      # reverse regression: the other side of the EIV bracket
        return np.sum(np.conj(Y) * Y, 0) / np.sum(np.conj(Y) * M, 0)
    raise ValueError(kind)


def band_report(fr, sp, Vh, label):
    print(f"\n  {label}: |V| (wheel-angle -> achieved), coherence(M,Y), and the share of Y it explains")
    M, Y = sp["M"], sp["Y"]
    for b1, b2 in BANDS:
        s = (fr >= b1) & (fr < b2)
        num = np.abs(np.sum(np.conj(M[:, s]) * Y[:, s])) ** 2
        coh = num / (np.sum(np.abs(M[:, s]) ** 2) * np.sum(np.abs(Y[:, s]) ** 2))
        r = Y[:, s] - Vh[None, s] * M[:, s]
        w = np.abs(M[:, s]) ** 2
        vmag = float(np.average(np.abs(Vh[s]), weights=w.sum(0)))
        print(f"    {b1:5.2f}-{b2:4.2f}  |V| {vmag:5.3f}  coh(M,Y) {float(coh):5.3f}  "
              f"unexplained |r|^2/|Y|^2 {float(np.sum(np.abs(r)**2)/np.sum(np.abs(Y[:, s])**2)):5.3f}")


def main():
    res = {}
    for lab, rks in (("T64", T64), ("V282", V282)):
        fr, sp, vs = gather(rks)
        sel = A.bandsel(fr)
        X, Z, M, Y = sp["X"], sp["Z"], sp["M"], sp["Y"]
        E = X - Y
        D = Z - M
        J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / np.sum(np.abs(X[:, sel]) ** 2))
        den = float(np.sum(np.abs(X[:, sel]) ** 2))
        print(f"\n{'='*100}\n{lab}: {len(vs)} windows, J as flown = {J0:.3f}")
        store = dict(J0=J0)
        for kind in ("dir", "iv", "rev"):
            Vh = estimate_V(sp, kind)
            band_report(fr, sp, Vh, f"V estimator '{kind}'")
            A_res = E - Vh[None, :] * D
            A_con = (X - Z) + (1.0 - Vh[None, :]) * Z
            r = Y - Vh[None, :] * M
            j_res = float(np.sum(np.abs(A_res[:, sel]) ** 2) / den)
            j_con = float(np.sum(np.abs(A_con[:, sel]) ** 2) / den)
            j_r = float(np.sum(np.abs(r[:, sel]) ** 2) / den)
            # exactness check of each reading of the identity
            e_res = float(np.sqrt(np.sum(np.abs((A_res + Vh[None, :] * D - E)[:, sel]) ** 2) /
                                  np.sum(np.abs(E[:, sel]) ** 2)))
            e_con = float(np.sqrt(np.sum(np.abs((A_con + Vh[None, :] * D - E)[:, sel]) ** 2) /
                                  np.sum(np.abs(E[:, sel]) ** 2)))
            print(f"    J_inf with A_res (identity exact, rel err {e_res:.1e}) = {j_res:.3f}")
            print(f"    J_inf with A_con (identity DROPS r, rel err {e_con:.3f}) = {j_con:.3f}"
                  f"   [the dropped r alone is worth {j_r:.3f} of J]")
            store[kind] = dict(j_res=j_res, j_con=j_con, j_r=j_r, e_res=e_res, e_con=e_con,
                               Vmag=[float(np.average(np.abs(Vh[(fr >= b1) & (fr < b2)]),
                                                      weights=np.sum(np.abs(M[:, (fr >= b1) & (fr < b2)]) ** 2, 0)))
                                     for b1, b2 in BANDS])
        res[lab] = store
        del sp, X, Z, M, Y, E, D

    print(f"\n{'='*100}\nTHE ASYMPTOTE, AND THE CLOSURE IT IMPLIES")
    Jf, Jv = res["T64"]["J0"], res["V282"]["J0"]
    print(f"  as flown J {Jf:.3f}   V282 J {Jv:.3f}   gap {Jf-Jv:.3f}")
    print(f"  {'A definition':>14s} {'V est':>6s} {'J_inf':>7s} {'closure %':>10s}")
    for kind in ("dir", "iv", "rev"):
        for nm, key in (("A_res (exact)", "j_res"), ("A_con (drops r)", "j_con")):
            ji = res["T64"][kind][key]
            print(f"  {nm:>14s} {kind:>6s} {ji:7.3f} {100*(Jf-ji)/(Jf-Jv):10.1f}")
    print("\n  For reference, the same residual computed on the V282 routes (what the asymptote would be")
    print("  if V282 ITSELF had infinite loop gain) -- the honest floor of the whole class:")
    for kind in ("dir", "iv", "rev"):
        print(f"    V est {kind:>4s}:  A_res {res['V282'][kind]['j_res']:.3f}   A_con {res['V282'][kind]['j_con']:.3f}")
    json.dump(res, open(A.OUT / "adv3_asymptote.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
