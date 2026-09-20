# -*- coding: utf-8 -*-
"""K5 -- if the integrator costs phase it cannot pay for, what does TURNING IT DOWN buy?

AccordTorqueKi floor is 0.05 (starpilot_variables.py:826).  Same machinery as K3: the metric via the
exact identity X-Y = A + V*D with D multiplied by the measured complex (1+L0)/(1+L1), and the shake
by exact command re-synthesis.  Also: the low-frequency PHASE cost of AccordErrorNotchQ, which sits
on the SAME error the P and I terms share -- a cross-check for the notch stream.

out: K5-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402
from k1_iterm import CFG, ki_of, lsf_of, notch_resp, DT, FS  # noqa: E402
from k3_why import route_pack, spectra, TORQ64, V282, KI_BP, MBAND  # noqa: E402

HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / 8e-5) / (2.0 * np.pi)


def main():
    print("=" * 122)
    print("K5  TURNING THE INTEGRATOR DOWN, AND THE NOTCH'S LOW-FREQUENCY PHASE COST")
    print("=" * 122)
    P = {}
    for rk in TORQ64 + V282:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        pk = route_pack(rk)
        if not pk["wins"]:
            continue
        f, F, vm = spectra(pk)
        P[rk] = dict(f=f, F=F, vm=vm, c=CFG[rk], laf=pk["laf"], segs=pk["wins"],
                     e=pk["e"], p=pk["p"], i=pk["i"], ffwd=pk["ffwd"], v=pk["v"])
        del pk

    base_met, ref_met = {}, {}
    for rk, d in P.items():
        f, F = d["f"], d["F"]
        s = (f >= MBAND[0]) & (f < MBAND[1])
        m = float(np.sum(np.abs(F["X"][:, s] - F["Y"][:, s]) ** 2) / np.sum(np.abs(F["X"][:, s]) ** 2))
        (base_met if rk in TORQ64 else ref_met)[rk] = m
    base = float(np.median(list(base_met.values())))
    ref = float(np.median(list(ref_met.values())))
    print(f"\n   baseline (rev 6.4 median) {base:.3f}   V282 reference {ref:.3f}   gap {base-ref:.3f}")

    doses = [("as flown (Ki 0.30)", 0.30, 1.0), ("Ki 0.15", 0.15, 1.0), ("Ki 0.05 (floor)", 0.05, 1.0),
             ("SteerKP 2.0", 0.30, 2.0), ("SteerKP 2.0 + Ki 0.05", 0.05, 2.0),
             ("SteerKP 3.0", 0.30, 3.0), ("SteerKP 3.0 + Ki 0.05", 0.05, 3.0)]
    sos = signal.butter(4, [1.8, 3.5], btype="band", fs=FS, output="sos")
    print(f"\n   {'lever':24s} " + " ".join(f"{r[:8]:>9s}" for r in TORQ64) +
          f" {'median':>8s} {'closed':>8s} {'shake x':>9s}")
    for name, ki1v, kpm in doses:
        cells, shk = [], []
        for rk in TORQ64:
            if rk not in P:
                continue
            d = P[rk]; f, F, c = d["f"], d["F"], d["c"]
            xs = lambda a, b: np.mean(np.conj(a) * b, axis=0)
            E = F["Z"] - F["M"]
            See = xs(E, E).real
            CP = xs(E, F["p"]) / np.maximum(See, 1e-300)
            CI = xs(E, F["i"]) / np.maximum(See, 1e-300)
            U = F["p"] + F["i"] + F["ffwd"]
            G = xs(F["ffwd"], F["M"]) / xs(F["ffwd"], U)
            v = float(np.median(d["vm"])); lsf = float(lsf_of(v)); kp0 = c["kp"]; ki0 = c["ki"]
            kp1 = kp0 * kpm
            sP = (kp1 + lsf) / (kp0 + lsf)
            sI = (ki1v / ki0) * (1 + lsf / kp1) / (1 + lsf / kp0)
            L0 = (CP + CI) * G
            L1 = (CP * sP + CI * sI) * G
            r = (1 + L0) / (1 + L1)
            Vleg = xs(F["M"], F["Y"]) / np.maximum(xs(F["M"], F["M"]).real, 1e-300)
            Dw = F["Z"] - F["M"]
            Aw = (F["X"] - F["Y"]) - Vleg * Dw
            s = (f >= MBAND[0]) & (f < MBAND[1])
            cells.append(float(np.sum(np.abs(Aw[:, s] + Vleg[s] * Dw[:, s] * r[s]) ** 2) /
                               np.sum(np.abs(F["X"][:, s]) ** 2)))
            num = den = 0.0
            for a, b in d["segs"]:
                e = d["e"][a:b]
                se = (1 + lsf / kp1) / (1 + lsf / kp0)
                p0, i0, f0 = d["p"][a:b], d["i"][a:b], d["ffwd"][a:b]
                i1 = i0[0] + np.cumsum(np.full(b - a, ki1v) * DT * e * se)
                u0 = (p0 + i0 + f0) / d["laf"]
                u1 = (p0 * kpm * se + i1 + f0) / d["laf"]
                num += float(np.sum(signal.sosfiltfilt(sos, u1) ** 2))
                den += float(np.sum(signal.sosfiltfilt(sos, u0) ** 2))
            shk.append(np.sqrt(num / max(den, 1e-30)))
        m = float(np.median(cells))
        print(f"   {name:24s} " + " ".join(f"{x:9.3f}" for x in cells) +
              f" {m:8.3f} {100*(base-m)/max(base-ref,1e-9):7.1f}% {np.median(shk):9.3f}")

    print("\n2  AccordErrorNotchQ: the EXACT discrete notch (HondaAccordErrorNotch coefficients) at the")
    print("   0.15-0.30 Hz band centre, for the mode frequency at the rev-6.4 routes' median speed.")
    v = float(np.median([np.median(d['vm']) for rk, d in P.items() if rk in TORQ64]))
    fn = mode_hz(v)
    print(f"   median speed {v:.1f} m/s -> mode {fn:.2f} Hz.  The notch sits on the SHARED error, so it")
    print("   moves the P term, the I term and the friction term together.")
    print(f"   {'Q':>6s} " + " ".join(f"{('%.2f Hz' % q):>16s}" for q in (0.20, 0.30, 0.60, 1.20, 2.00, 2.60)))
    print(f"   {'':6s} " + " ".join(f"{'|N|   arg deg':>16s}" for _ in range(6)))
    for q in (4.0, 1.5, 1.0, 0.7, 0.5, 0.35):
        line = f"   {q:6.2f} "
        for qq in (0.20, 0.30, 0.60, 1.20, 2.00, 2.60):
            n = notch_resp(np.array([qq]), fn, q)[0]
            line += f"{abs(n):8.3f}{np.degrees(np.angle(n)):8.1f} "
        print(line)
    print("\n   A LOWER Q is a WIDER notch: it costs magnitude AND phase LAG at 0.2-0.6 Hz, which is the")
    print("   same Re(L) currency the integrator fails on.  Flagged for the notch stream -- not scored here.")


if __name__ == "__main__":
    main()
