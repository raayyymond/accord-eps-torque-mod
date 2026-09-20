# -*- coding: utf-8 -*-
"""ADV6: the blind band, the notch, and where the sensitivity peak actually goes.

  (1) ADMISSIBILITY.  Per route, coherence of the plant estimate and the resulting |P|, band by band.
      If two routes flying the SAME controller disagree about |P| by more than the difference the
      safety envelope is built on, the envelope is not measuring anything.
  (2) THE NOTCH, tested rather than argued.  AccordErrorNotchQ enters the loop as an exact transfer;
      Q is swept with everything else held, so the metric change and the shake-band |L| change are
      read off the same identity used for the gain sweep.
  (3) WHERE Ms GOES.  The peak of |S| at each dose, and the frequency it sits at -- inside the band
      the logs can see, or outside it.
  (4) THE ASYMPTOTE RESTRICTED TO THE ADMISSIBLE BAND, with the rest declared unknown instead of zero.
"""
import json
import sys

import numpy as np

import advlib as A
from adv4_loop import BANDS, C_of, NPS, SHAKE, gather

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
PAIRS = [("00000071--f2c9d073a3", "00000072--8001fc3048"),          # same kp/LAF 0.0607, notch off both
         ("0000006c--68c6e94b17", "0000006d--05e83bb04f")]          # identical rev 6.4 config


def route_plant(rk):
    N = A.load_nodes(rk)
    fr, sp, vs = A.windows(N, nperseg=NPS, overlap=0.5, minrun=30.0)
    X, M, U = sp["X"], sp["M"], sp["U"]
    P = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    coh = np.abs(np.sum(np.conj(X) * U, 0)) ** 2 / (np.sum(np.abs(X) ** 2, 0) * np.sum(np.abs(U) ** 2, 0))
    w = np.sum(np.abs(X) ** 2, 0)
    del N, sp, X, M, U
    return fr, P, coh, w, len(vs)


def main():
    print("(1) ADMISSIBILITY OF THE PLANT ESTIMATE, PER ROUTE")
    print(f"  {'route':>9s} {'nwin':>5s} " + "".join(f"{f'{b1}-{b2}':>17s}" for b1, b2 in BANDS + [SHAKE]))
    print(f"  {'':>9s} {'':>5s} " + "".join(f"{'|P|  coh':>17s}" for _ in BANDS + [SHAKE]))
    store = {}
    for rk in [r for r, m in A.FLOWN.items() if m["eps"] == "V293"]:
        fr, P, coh, w, n = route_plant(rk)
        store[rk] = (fr, P, coh, w)
        line = f"  {rk[:8]:>9s} {n:5d} "
        for b1, b2 in BANDS + [SHAKE]:
            s = (fr >= b1) & (fr < b2)
            line += f"{np.average(np.abs(P[s]), weights=w[s]):9.2f}{np.average(coh[s], weights=w[s]):8.2f}"
        print(line, flush=True)
    print("\n  SAME-CONTROLLER PAIRS -- how much the SAME plant moves between two routes:")
    for a_, b_ in PAIRS:
        fa, Pa, _, wa = store[a_]; fb, Pb, _, wb = store[b_]
        for b1, b2 in [(0.15, 0.60), (1.20, 2.40), SHAKE]:
            s = (fa >= b1) & (fa < b2)
            ra = np.average(np.abs(Pa[s]), weights=wa[s]); rb = np.average(np.abs(Pb[s]), weights=wb[s])
            print(f"    {a_[:8]} vs {b_[:8]}  {b1:.2f}-{b2:.2f} Hz: |P| {ra:6.2f} vs {rb:6.2f} "
                  f"= {max(ra,rb)/min(ra,rb):.2f}x apart")

    # ---------------------------------------------------------------- loop machinery, T64
    fr, sp, vs, rkl = gather(T64)
    sel = A.bandsel(fr)
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    JV = 0.444
    P_iv = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    coh_XU = np.abs(np.sum(np.conj(X) * U, 0)) ** 2 / (np.sum(np.abs(X) ** 2, 0) * np.sum(np.abs(U) ** 2, 0))
    Vh = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    metas = {rk: A.FLOWN[rk] for rk in T64}
    wl = np.abs(X) ** 2
    ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])

    def loop(kp_mult, q):
        Cw = np.array([C_of(fr, v, dict(metas[rk], kp=metas[rk]["kp"] * kp_mult), q=q)
                       for v, rk in zip(vs, rkl)])
        return P_iv[None, :] * Cw

    L1 = loop(1.0, 1.0)
    Ares = E - Vh[None, :] * D

    def J_of(L2):
        Ek = Ares + Vh[None, :] * (D * (1.0 + L1) / (1.0 + L2))
        return float(np.sum(np.abs(Ek[:, sel]) ** 2) / den)

    print("\n(2) THE NOTCH, PUT THROUGH THE SAME IDENTITY (AccordErrorNotchQ; source: it IS live --")
    print("    params_keys.h declares it, known() is default_values.__contains__, so the gate passes)")
    print(f"  {'SteerKP':>8s} {'Q':>5s} {'J':>7s} {'closure %':>10s} {'|L| 0.15-0.6':>13s} {'|L| 1.8-3.5':>12s} {'max|S| band':>12s}")
    for kpm in (1.0, 2.0):
        for q in (1.0, 0.7, 0.5, 0.3, 0.0):
            L2 = loop(kpm, q)
            j = J_of(L2)
            slo = (fr >= 0.15) & (fr < 0.60)
            print(f"  {kpm:8.1f} {q:5.2f} {j:7.3f} {100*(J0-j)/(J0-JV):10.1f} "
                  f"{np.average(np.abs(L2[:, slo]), weights=wl[:, slo]):13.3f} "
                  f"{np.average(np.abs(L2[:, ssh]), weights=wl[:, ssh]):12.3f} "
                  f"{np.max(np.abs(1/(1+L2[:, sel]))):12.2f}")
    print("  NOTE the notch centre at these speeds: " +
          ", ".join(f"{v:.0f} m/s -> {__import__('adv4_loop').mode_hz(v):.2f} Hz" for v in (15, 20, 25, 29)))

    print("\n(3) WHERE THE SENSITIVITY PEAK GOES WITH DOSE (in-band peak of |S|, and its frequency)")
    print(f"  {'SteerKP':>8s} {'max|S|':>8s} {'f of peak':>10s} {'coh(X,u) there':>15s} {'|S| @2.4Hz':>11s}")
    for kpm in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0):
        L2 = loop(kpm, 1.0)
        Sm = np.abs(1.0 / (1.0 + L2))[:, sel]
        i, j = np.unravel_index(np.argmax(Sm), Sm.shape)
        fpk = fr[sel][j]
        print(f"  {kpm:8.1f} {Sm.max():8.2f} {fpk:9.2f} Hz {coh_XU[sel][j]:15.2f} "
              f"{np.average(np.abs(1/(1+L2))[:, (fr>2.3)&(fr<=2.4)]):11.2f}")

    print("\n(4) THE ASYMPTOTE, SPLIT INTO THE BAND THE LOGS CAN SEE AND THE BAND THEY CANNOT")
    print("    (admissible = coh(X,u) >= 0.7 AND coh(M,Y) >= 0.7, both measured here)")
    cohMY = np.abs(np.sum(np.conj(M) * Y, 0)) ** 2 / (np.sum(np.abs(M) ** 2, 0) * np.sum(np.abs(Y) ** 2, 0))
    adm = (coh_XU >= 0.7) & (cohMY >= 0.7)
    print(f"    admissible bins inside 0.15-2.4 Hz: {int((adm & sel).sum())} of {int(sel.sum())} "
          f"(up to {fr[adm & sel].max():.2f} Hz)")
    pE = np.abs(E) ** 2; pA = np.abs(Ares) ** 2
    for lab, msk in (("admissible", adm & sel), ("INADMISSIBLE", (~adm) & sel)):
        print(f"    {lab:>13s}: flown error {100*pE[:, msk].sum()/pE[:, sel].sum():5.1f} % of J ; "
              f"asymptotic residual {100*pA[:, msk].sum()/pA[:, sel].sum():5.1f} % of J_inf ; "
              f"J part {pE[:, msk].sum()/den:6.3f} -> {pA[:, msk].sum()/den:6.3f}")
    ja = float(pA[:, adm & sel].sum() + pE[:, (~adm) & sel].sum()) / den
    print(f"    => if the inadmissible band is credited with NO improvement (the honest floor),")
    print(f"       J_inf = {ja:.3f}, closure {100*(J0-ja)/(J0-JV):.1f} %  (vs {100*(J0-float(pA[:, sel].sum())/den)/(J0-JV):.1f} %"
          f" when it is credited in full)")
    json.dump(dict(J0=J0, Jinf_full=float(pA[:, sel].sum()) / den, Jinf_admissible_only=ja),
              open(A.OUT / "adv6_blind.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
