# -*- coding: utf-8 -*-
"""ADV8: the dose, re-priced on the plant the car presents WHERE THE INSTABILITY LIVES.

ADV7 measured that the identified plant gain rises 1.24-1.71x from the low to the high demand-amplitude
tercile -- the signature of the Coulomb friction the fork already models.  A dose sized on pooled windows
is therefore sized at the pooled amplitude.  r71's limit cycle appeared 'on hard curves above 20 m/s',
i.e. in the HIGH-amplitude tercile.  This re-prices |L| in the shake band and Ms, per tercile, per dose.
"""
import json
import sys

import numpy as np

import advlib as A
from adv4_loop import C_of, NPS, SHAKE
from adv7_verdict import T64, pack

def main():
    fr, sp, vs, rkl, am = pack(T64, NPS)
    X, M, U = sp["X"], sp["M"], sp["U"]
    sel = A.bandsel(fr)
    ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])
    metas = {rk: A.FLOWN[rk] for rk in T64}
    q1, q2 = np.percentile(am, [33.3, 66.7])
    terciles = [("low  |X|", am <= q1), ("pooled  ", np.ones(len(am), bool)), ("high |X|", am > q2)]

    print("SHAKE-BAND LOOP GAIN AND Ms, PER DEMAND-AMPLITUDE TERCILE, PER DOSE")
    print("  (plant re-identified inside each tercile; controller exact from source)")
    print(f"  {'tercile':>9s} {'SteerKP':>8s} {'|L| 1.8-3.5':>12s} {'max|S| in band':>15s} {'f of Ms peak':>13s}")
    res = {}
    for lab, msk in terciles:
        P = np.sum(np.conj(X[msk]) * M[msk], 0) / np.sum(np.conj(X[msk]) * U[msk], 0)
        w = np.abs(X[msk]) ** 2
        res[lab.strip()] = {}
        for kpm in (1.0, 2.0, 2.5, 3.0):
            L = P[None, :] * np.array([C_of(fr, v, dict(metas[rk], kp=metas[rk]["kp"] * kpm))
                                       for v, rk in zip(vs[msk], np.array(rkl)[msk])])
            Sm = np.abs(1.0 / (1.0 + L))[:, sel]
            i, j = np.unravel_index(np.argmax(Sm), Sm.shape)
            lsh = float(np.average(np.abs(L[:, ssh]), weights=w[:, ssh]))
            print(f"  {lab:>9s} {kpm:8.1f} {lsh:12.3f} {Sm.max():15.2f} {fr[sel][j]:12.2f} Hz")
            res[lab.strip()][kpm] = dict(L=lsh, Ms=float(Sm.max()), f=float(fr[sel][j]))
    print("\n  r71 limit-cycled at a shake-band |L| of 0.46 (its own flown value, quoted by the programme).")
    for kpm in (2.0, 2.5, 3.0):
        hi = res["high |X|"][kpm]["L"]; po = res["pooled"][kpm]["L"]
        print(f"    SteerKP {kpm}: pooled |L| {po:.3f} but {hi:.3f} on high-demand windows "
              f"({hi/po:.2f}x) -> {100*hi/0.46:.0f} % of the flown limit-cycle anchor")
    json.dump(res, open(A.OUT / "adv8_amp.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
