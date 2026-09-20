# -*- coding: utf-8 -*-
"""K6 -- VERIFY THE CRUX: arg(L) at 0.15-0.30 Hz, by THREE independent routes.

The whole finding rests on one number: the loop already lags ~50 deg where the gap is, so an extra
-90 deg term subtracts from Re(L).  If arg(L) there were near 0, the integrator would work.

  (a) IV with the FEEDFORWARD as instrument      L = (C_P+C_I) * S_fM/S_fU        (K1-K5's estimator)
  (b) IV with the SHAPED SETPOINT as instrument  L = (C_P+C_I) * S_ZM/S_ZU
  (c) NO controller model at all: arg of the measured closed loop T_ZM = S_ZM/S_ZZ, which must equal
      arg(L/(1+L)); arg(L) is then recovered as arg(T/(1-T)).  This uses only Z and M.
Plus the split-half stability of (a) and the instrument coherences.

out: K6-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402
from k1_iterm import CFG  # noqa: E402
from k3_why import route_pack, spectra, TORQ64, V282  # noqa: E402

BAND = (0.15, 0.30)


def main():
    print("=" * 118)
    print("K6  CRUX CHECK -- arg(L) at 0.15-0.30 Hz by three independent estimators")
    print("=" * 118)
    print(f"   {'route':10s} {'grp':5s} {'(a) ff-IV':>20s} {'(b) Z-IV':>20s} {'(c) T-only':>20s} "
          f"{'split-half (a)':>18s}")
    print(f"   {'':10s} {'':5s} " + " ".join(f"{'|L|   arg':>20s}" for _ in range(3)) +
          f" {'arg h1 / h2':>18s}")
    for rk in TORQ64 + V282:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        pk = route_pack(rk)
        if not pk["wins"]:
            continue
        f, F, vm = spectra(pk)
        del pk
        s = (f >= BAND[0]) & (f < BAND[1])

        def est(idx, instr):
            xs = lambda a, b: np.mean(np.conj(a[idx]) * b[idx], axis=0)
            E = F["Z"] - F["M"]
            See = xs(E, E).real
            C = (xs(E, F["p"]) + xs(E, F["i"])) / np.maximum(See, 1e-300)
            U = F["p"] + F["i"] + F["ffwd"]
            G = xs(F[instr], F["M"]) / xs(F[instr], U)
            return (C * G), See

        n = F["X"].shape[0]
        allw = np.arange(n)
        La, W = est(allw, "ffwd")
        Lb, _ = est(allw, "Z")
        # (c) controller-free: T = S_ZM/S_ZZ, L = T/(1-T)
        xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
        T = xs(F["Z"], F["M"]) / np.maximum(xs(F["Z"], F["Z"]).real, 1e-300)
        Lc = T / (1.0 - T)
        w = np.maximum(W[s], 1e-300)
        cells = []
        for L in (La, Lb, Lc):
            cells.append((np.average(np.abs(L[s]), weights=w),
                          np.average(np.degrees(np.angle(L[s])), weights=w)))
        h1, _ = est(allw[: n // 2], "ffwd")
        h2, _ = est(allw[n // 2:], "ffwd")
        a1 = np.average(np.degrees(np.angle(h1[s])), weights=w)
        a2 = np.average(np.degrees(np.angle(h2[s])), weights=w)
        print(f"   {rk[:8]:10s} {CFG[rk]['g']:5s} " +
              " ".join(f"{m:9.2f}{p:11.0f}" for m, p in cells) +
              f" {a1:9.0f} /{a2:7.0f}")
    print("\n   (c) uses NO logged controller term at all, so it is independent of the C_P/C_I model;")
    print("   it is the noisiest (it inverts a near-unity T), and it is reported unsmoothed.")


if __name__ == "__main__":
    main()
