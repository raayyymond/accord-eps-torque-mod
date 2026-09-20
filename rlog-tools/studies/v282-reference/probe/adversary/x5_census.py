# -*- coding: utf-8 -*-
"""X5 -- A DRIVE BEATS A PATCH, IF IT WORKS.  Census the existing routes for identification quality.

The probe's whole claim is that the planner puts too little power above ~1 Hz.  Before writing code
that shakes the reference, measure what the existing drives ALREADY contain:

  1. per-window coherence of the shaped setpoint Z against the loop error, the measurement and the
     command, in every band -- so the deficit is located, not assumed;
  2. the DISTRIBUTION of in-band reference power across windows -- how far the richest windows
     already are above the median, against the (c*-c0)/((1-c*)c0) factor the probe has to supply;
  3. what a rich window looks like (speed, demand amplitude, curvature activity), i.e. what to
     ask the operator to DRIVE.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
BANDS = [("0.15-0.60", 0.15, 0.60), ("0.60-1.20", 0.60, 1.20), ("1.20-2.40", 1.20, 2.40),
         ("2.40-3.40", 2.40, 3.40), ("3.40-4.90", 3.40, 4.90)]
RTS = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
       "00000072--8001fc3048", "00000073--79fd149dd8", "00000071--f2c9d073a3",
       "00000075--6c8687d5bd", "00000076--d0b7ea7e4d", "00000070--717f5a7866"]
_W = float(np.sum(np.hanning(1024) ** 2))


def brms(X, s):
    return np.sqrt(2.0 * np.sum(np.abs(X[:, s]) ** 2, axis=1) / (1024 * _W))


def main():
    print("=" * 126)
    print("1. WHERE THE IDENTIFICATION ACTUALLY FAILS.  Coherence of the shaped setpoint Z against")
    print("   the loop error e = Z-M, the measurement M, the command U and the achieved accel Y.")
    print("   Pooled over each route's >=15 m/s metric windows.")
    print(f"   {'route':14s} {'n':>3s} {'band':11s} {'coh(Z,e)':>9s} {'coh(Z,M)':>9s} "
          f"{'coh(Z,U)':>9s} {'Szz/Srr for c*=0.7':>19s}")
    rich = []
    for rt in RTS:
        L = A.load(rt)
        f, F, vm, am = A.spectra(L)
        idx = np.where(vm >= 15.0)[0]
        if len(idx) < 6:
            del L, F
            continue
        R = F["r"][idx]
        M = F["y"][idx] * 0
        # the controller's own measurement M is la_act; e = Z - M is the loop error.  advlib2's
        # spectra carries y = la_act (the controller measurement) and x = the model demand.
        M = F["y"][idx]
        U = F["u"][idx]
        E = R - M
        cf = lambda Aa, Bb: (np.abs(np.mean(np.conj(Aa) * Bb, axis=0)) ** 2 /
                             np.maximum(np.mean(np.abs(Aa) ** 2, axis=0) *
                                        np.mean(np.abs(Bb) ** 2, axis=0), 1e-300))
        cze, czm, czu = cf(R, E), cf(R, M), cf(R, U)
        for nm, lo, hi in BANDS:
            s = (f >= lo) & (f <= hi)
            c0 = float(np.mean(czu[s]))
            need = (0.7 - c0) / (0.3 * max(c0, 1e-6))
            print(f"   {rt[:10]:14s} {len(idx):3d} {nm:11s} {np.mean(cze[s]):9.3f} "
                  f"{np.mean(czm[s]):9.3f} {c0:9.3f} "
                  f"{('already met' if need <= 0 else f'{need:8.2f}x'):>19s}")
            rich.append(dict(rt=rt, band=nm, p=brms(R, s), v=vm[idx], amp=am[idx],
                             sr=brms(F["sr"][idx], s)))
        print()
        del L, F

    print("=" * 126)
    print("2. HOW MUCH RICHER THE RICHEST WINDOWS ALREADY ARE.  Per band, the distribution of")
    print("   in-band REFERENCE rms across every window in the census, and the power ratio of the")
    print("   top decile to the median -- the factor a TARGETED DRIVE can supply for free.")
    print(f"   {'band':11s} {'nwin':>5s} {'med rms':>9s} {'p90 rms':>9s} {'max rms':>9s} "
          f"{'p90/med POWER':>14s} {'max/med POWER':>14s}")
    agg = {}
    for r in rich:
        agg.setdefault(r["band"], []).append(r)
    for nm, lo, hi in BANDS:
        P = np.concatenate([r["p"] for r in agg[nm]])
        med, p90, mx = np.median(P), np.percentile(P, 90), P.max()
        print(f"   {nm:11s} {len(P):5d} {med:9.5f} {p90:9.5f} {mx:9.5f} "
              f"{(p90/med)**2:13.2f}x {(mx/med)**2:13.2f}x")

    print()
    print("=" * 126)
    print("3. WHAT A RICH WINDOW IS.  Top-decile vs bottom-decile windows by in-band reference rms.")
    print(f"   {'band':11s} {'decile':7s} {'n':>4s} {'speed m/s':>10s} {'demand rms':>11s} "
          f"{'steer-rate rms':>15s}")
    for nm, lo, hi in BANDS:
        P = np.concatenate([r["p"] for r in agg[nm]])
        V = np.concatenate([r["v"] for r in agg[nm]])
        Am = np.concatenate([r["amp"] for r in agg[nm]])
        SR = np.concatenate([r["sr"] for r in agg[nm]])
        for lbl, sel in (("top", P >= np.percentile(P, 90)), ("bottom", P <= np.percentile(P, 10))):
            print(f"   {nm:11s} {lbl:7s} {sel.sum():4d} {np.median(V[sel]):10.1f} "
                  f"{np.median(Am[sel]):11.4f} {np.median(SR[sel]):15.4f}")
    json.dump({nm: dict(med=float(np.median(np.concatenate([r['p'] for r in agg[nm]]))),
                        p90=float(np.percentile(np.concatenate([r['p'] for r in agg[nm]]), 90)))
               for nm, _, _ in BANDS}, open(OUT / "x5_census.json", "w"), indent=1)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main()
