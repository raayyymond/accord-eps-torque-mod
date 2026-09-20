# -*- coding: utf-8 -*-
"""K4 -- WHERE the integrator's authority actually is, and where the metric's power is.

The integrator's gain -> infinity as f -> 0, so there IS a band where it wins no matter what the
phase is (|S| ~ 1/|L|).  The question is whether that band overlaps the goal metric's 0.15-2.4 Hz
window and the demand power inside it.  Both are measured here.

out: K4-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402
from k1_iterm import CFG, lsf_of  # noqa: E402
from k3_why import route_pack, spectra, TORQ64, V282, KI_BP, MBAND  # noqa: E402


def main():
    print("=" * 120)
    print("K4  WHERE THE INTEGRATOR WINS, AND WHERE THE METRIC'S POWER IS")
    print("=" * 120)
    packs = {}
    for rk in TORQ64 + V282:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        P = route_pack(rk)
        if not P["wins"]:
            continue
        f, F, vm = spectra(P)
        packs[rk] = (f, F, vm, CFG[rk])
        del P

    print("\n1  DEMAND POWER inside the metric window, cumulative.  X = model desired lateral accel,")
    print("   >=15 m/s engaged hands-off.  Share of the 0.15-2.4 Hz denominator below each frequency.")
    fq = [0.20, 0.25, 0.30, 0.40, 0.60, 1.00, 1.50, 2.40]
    print(f"   {'route':10s} {'grp':5s} " + " ".join(f"{('<%.2f' % q):>7s}" for q in fq))
    for rk, (f, F, vm, c) in packs.items():
        s = (f >= MBAND[0]) & (f < MBAND[1])
        Pxx = np.sum(np.abs(F["X"][:, s]) ** 2, axis=0)
        ff = f[s]
        tot = Pxx.sum()
        print(f"   {rk[:8]:10s} {c['g']:5s} " +
              " ".join(f"{100*Pxx[ff < q].sum()/tot:7.1f}" for q in fq))

    print("\n2  errx(f) = |S_new(f)|/|S_old(f)| for the Ki doses, per bin, on the rev-6.4 routes")
    print("   (median over the four).  < 1 is a gain, > 1 is a loss.  The crossover frequency is where")
    print("   the integrator stops paying for its own phase.")
    from k3_why import spectra as _sp  # noqa: F401
    fq2 = [0.049, 0.098, 0.146, 0.195, 0.244, 0.293, 0.391, 0.488, 0.684, 0.977, 1.465, 2.246]
    doses = [("KiHigh 1.0", 1.0, 1.0), ("KiHigh 2.5", 2.5, 1.0), ("KiHigh 6.0", 6.0, 1.0),
             ("SteerKP 2.0", None, 2.0)]
    rows = {n: [] for n, _, _ in doses}
    Lstore = {}
    for rk, (f, F, vm, c) in packs.items():
        if rk not in TORQ64:
            continue
        xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
        E = F["Z"] - F["M"]
        See = xs(E, E).real
        CP = xs(E, F["p"]) / np.maximum(See, 1e-300)
        CI = xs(E, F["i"]) / np.maximum(See, 1e-300)
        U = F["p"] + F["i"] + F["ffwd"]
        G = xs(F["ffwd"], F["M"]) / xs(F["ffwd"], U)
        L0 = (CP + CI) * G
        v = float(np.median(vm)); lsf = float(lsf_of(v)); kp0 = c["kp"]
        ki0 = c["ki"] if c["kih"] <= 0 else float(np.interp(v, KI_BP, [c["ki"], c["kih"]]))
        Lstore[rk] = (f, L0)
        for name, kih, kpm in doses:
            ki1 = ki0 if kih is None else float(np.interp(v, KI_BP, [c["ki"], kih]))
            kp1 = kp0 * kpm
            sP = (kp1 + lsf) / (kp0 + lsf)
            sI = (ki1 / ki0) * (1 + lsf / kp1) / (1 + lsf / kp0)
            L1 = (CP * sP + CI * sI) * G
            rows[name].append(np.abs(1 / (1 + L1)) / np.abs(1 / (1 + L0)))
    f = list(Lstore.values())[0][0]
    idx = [int(np.argmin(np.abs(f - q))) for q in fq2]
    print(f"   {'lever':14s} " + " ".join(f"{f[j]:>7.3f}" for j in idx))
    for name, _, _ in doses:
        med = np.median(np.array(rows[name]), axis=0)
        print(f"   {name:14s} " + " ".join(f"{med[j]:7.3f}" for j in idx))
    print("\n   arg(L) at the same bins (median of the four rev-6.4 routes), for reading the table:")
    argL = np.median(np.array([np.degrees(np.angle(L)) for _, L in Lstore.values()]), axis=0)
    magL = np.median(np.array([np.abs(L) for _, L in Lstore.values()]), axis=0)
    print(f"   {'arg L deg':14s} " + " ".join(f"{argL[j]:7.0f}" for j in idx))
    print(f"   {'|L|':14s} " + " ".join(f"{magL[j]:7.2f}" for j in idx))

    print("\n3  THE SAME THING ON V282: is its integrator doing anything its P term is not?")
    print(f"   {'route':10s} {'band':12s} {'|C_P|':>7s} {'|C_I|':>7s} {'I/P':>6s} {'argL':>6s} "
          f"{'Re L':>6s} {'|S|':>6s} {'|S| if I=0':>11s}")
    for rk, (f, F, vm, c) in packs.items():
        xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
        E = F["Z"] - F["M"]
        See = xs(E, E).real
        CP = xs(E, F["p"]) / np.maximum(See, 1e-300)
        CI = xs(E, F["i"]) / np.maximum(See, 1e-300)
        U = F["p"] + F["i"] + F["ffwd"]
        G = xs(F["ffwd"], F["M"]) / xs(F["ffwd"], U)
        for (a_, b_) in [(0.15, 0.30), (0.30, 0.60)]:
            s = (f >= a_) & (f < b_); w = np.maximum(See[s], 1e-300)
            L0 = ((CP + CI) * G)[s]; Lp = (CP * G)[s]
            print(f"   {rk[:8]:10s} {('%.2f-%.2f' % (a_, b_)):12s} "
                  f"{np.average(np.abs(CP[s]), weights=w):7.3f} {np.average(np.abs(CI[s]), weights=w):7.3f} "
                  f"{np.average(np.abs(CI[s]/CP[s]), weights=w):6.2f} "
                  f"{np.average(np.degrees(np.angle(L0)), weights=w):6.0f} "
                  f"{np.average(L0.real, weights=w):6.2f} "
                  f"{np.average(np.abs(1/(1+L0)), weights=w):6.3f} "
                  f"{np.average(np.abs(1/(1+Lp)), weights=w):11.3f}")


if __name__ == "__main__":
    main()
