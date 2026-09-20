# -*- coding: utf-8 -*-
"""a2 -- ATTACK THE SHAKE PROXY.

The delivered cost number (x1.148) is a ratio of COMMAND power in 1.8-3.5 Hz, re-synthesised as
    U1 = UFF + UFB * (C1/C0) * rho        (frontier f5_frontier.py:run)
Three things that makes it, which this script measures instead of assuming:

  (A) UFF IS NOT EXOGENOUS.  latcontrol_torque.py:665-670 puts the 100 Hz rate loop
      (+g*(angle_des_rate - rate_meas), rate_meas = measured steeringRateDeg) and the disturbance
      observer (-accord_dob_torque, fed by measured angle AND measured rate) INSIDE pid.f, i.e.
      inside UFF.  The re-synthesis holds UFF frozen while the wheel moves more.
  (B) THE FELT QUANTITY IS WHEEL RATE, NOT COMMAND.  Predict the wheel-rate change directly with
      the MEASURED V293 command -> wheel-rate transfer:  SR1 = SR + Psr*(U1 - U).
  (C) THE WINDOWS ARE THE CALM ONES.  Everything is priced on >=15 m/s, hands-off, unsaturated,
      >=30 s runs.  Re-price inside demand-amplitude terciles and below 15 m/s.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)
BANDS = [("0.15-0.60", 0.15, 0.60), ("0.60-1.20", 0.60, 1.20), ("1.20-1.80", 1.20, 1.80),
         ("1.80-3.50", 1.80, 3.50), ("3.50-6.00", 3.50, 6.00)]


def bsel(f, lo, hi):
    return (f >= lo) & (f <= hi)


def resynth(W, kp, laf, ki, q, P):
    f, v = W["f"], W["v"]
    C0 = A.C_fb(f, v, **FLOWN)
    C1 = A.C_fb(f, v, kp, laf, ki, q)
    K = C1 / C0
    L0 = P[None, :] * C0
    L1 = L0 * K
    rho = (1.0 + L0) / (1.0 + L1)
    U1 = W["UFF"] + W["UFB"] * K * rho
    return U1, L0, L1, rho, K


def main():
    print("=" * 112)
    print("0. THE WINDOW SETS")
    Wt = A.cat([A.extract(r, nps=1024) for r in A.T64])
    Wv = A.cat([A.extract(r, nps=1024) for r in A.V282])
    Wlo = A.cat([A.extract(r, nps=1024, vmin=8.0) for r in A.T64])       # 8 m/s and up
    f = Wt["f"]
    print(f"   T64 >=15 m/s: {len(Wt['v'])} windows, {Wt['sec']:.0f} s   "
          f"T64 >=8 m/s: {len(Wlo['v'])} windows   V282 >=15: {len(Wv['v'])} windows")

    print()
    print("=" * 112)
    print("(A) IS UFF EXOGENOUS?  Coherent transfer from the MEASURED wheel rate SR to UFF, and the")
    print("    share of UFF's power that SR explains.  If UFF were the pure feedforward the")
    print("    re-synthesis assumes, both are ~0.")
    print(f"{'band':>12s} {'coh(SR,UFF)':>12s} {'|H| SR->UFF':>12s} {'expl. frac of UFF':>18s} "
          f"{'coh(SR,U)':>10s} {'coh(UFB,UFF)':>13s}")
    rowsA = {}
    for name, lo, hi in BANDS:
        s = bsel(f, lo, hi)
        SR, UFF, U, UFB = Wt["SR"][:, s], Wt["UFF"][:, s], Wt["U"][:, s], Wt["UFB"][:, s]
        Ssu = np.mean(np.conj(SR) * UFF)
        c = np.abs(Ssu) ** 2 / (np.mean(np.abs(SR) ** 2) * np.mean(np.abs(UFF) ** 2))
        H = Ssu / np.mean(np.abs(SR) ** 2)
        c2 = np.abs(np.mean(np.conj(SR) * U)) ** 2 / (np.mean(np.abs(SR) ** 2) * np.mean(np.abs(U) ** 2))
        c3 = np.abs(np.mean(np.conj(UFB) * UFF)) ** 2 / (np.mean(np.abs(UFB) ** 2) * np.mean(np.abs(UFF) ** 2))
        print(f"{name:>12s} {c.real:12.3f} {abs(H):12.3e} {c.real:18.3f} {c2.real:10.3f} {c3.real:13.3f}")
        rowsA[name] = dict(coh_sr_uff=float(c.real), H_sr_uff=float(abs(H)), coh_sr_u=float(c2.real))

    print()
    print("    TOTAL feedback vs PID-ONLY feedback.  Project the exogenous demand X out of U and of M,")
    print("    then regress: Ky = <M_perp, U_perp>/<M_perp,M_perp> is the WHOLE measurement->command")
    print("    path.  |Ky| / |C_fb_analytic| > 1 means the frontier's loop is missing feedback.")
    X, U, M = Wt["X"], Wt["U"], Wt["M"]
    bu = np.mean(np.conj(X) * U, axis=0) / np.maximum(np.mean(np.abs(X) ** 2, axis=0), 1e-300)
    bm = np.mean(np.conj(X) * M, axis=0) / np.maximum(np.mean(np.abs(X) ** 2, axis=0), 1e-300)
    Up, Mp = U - bu[None, :] * X, M - bm[None, :] * X
    Ky = np.mean(np.conj(Mp) * Up, axis=0) / np.maximum(np.mean(np.abs(Mp) ** 2, axis=0), 1e-300)
    cohK = (np.abs(np.mean(np.conj(Mp) * Up, axis=0)) ** 2
            / np.maximum(np.mean(np.abs(Mp) ** 2, axis=0) * np.mean(np.abs(Up) ** 2, axis=0), 1e-300))
    C0m = np.mean(np.abs(A.C_fb(f, Wt["v"], **FLOWN)), axis=0)
    print(f"{'band':>12s} {'|Ky|':>10s} {'|C_fb|':>10s} {'ratio':>8s} {'coh':>6s}")
    for name, lo, hi in BANDS:
        s = bsel(f, lo, hi)
        a, b = float(np.mean(np.abs(Ky[s]))), float(np.mean(C0m[s]))
        print(f"{name:>12s} {a:10.4f} {b:10.4f} {a/b:8.2f} {float(np.mean(cohK[s])):6.2f}")

    print()
    print("=" * 112)
    print("(B) THE FELT QUANTITY.  Command -> wheel-rate transfer Psr measured on EACH build, then")
    print("    the wheel-rate shake predicted directly:  SR1 = SR + Psr*(U1-U).")
    print()
    print("    first, the plant fact the brief quotes -- |SR/U| per band, V293 vs V282 (IV, instrument X)")
    print(f"{'band':>12s} {'V293 |Psr|':>11s} {'coh':>5s} {'V282 |Psr|':>11s} {'coh':>5s} {'ratio':>7s}")
    Psr_t = np.mean(np.conj(Wt["X"]) * Wt["SR"], axis=0) / np.mean(np.conj(Wt["X"]) * Wt["U"], axis=0)
    Psr_v = np.mean(np.conj(Wv["X"]) * Wv["SR"], axis=0) / np.mean(np.conj(Wv["X"]) * Wv["U"], axis=0)
    ct = A.coh(Wt["U"], Wt["SR"]); cv = A.coh(Wv["U"], Wv["SR"])
    for name, lo, hi in BANDS:
        s = bsel(f, lo, hi)
        a, b = float(np.mean(np.abs(Psr_t[s]))), float(np.mean(np.abs(Psr_v[s])))
        print(f"{name:>12s} {a:11.1f} {float(np.mean(ct[s])):5.2f} {b:11.1f} {float(np.mean(cv[s])):5.2f} {a/b:7.2f}")

    print()
    print("    NOW THE COST ITSELF.  Same doses, three cost measures on the SAME windows:")
    print("      cmd     = the delivered number, |U1|/|U| in 1.8-3.5 Hz")
    print("      wheel   = |SR1|/|SR| with SR1 = SR + Psr*(U1-U), Psr measured by IV (instrument X)")
    print("      wheelH1 = same with Psr by H1 (U->SR), the opposite-side bracket")
    Pm = A.identify(Wt, inst="X")
    shk = bsel(f, *A.SHAKE)
    Psr_h1 = np.mean(np.conj(Wt["U"]) * Wt["SR"], axis=0) / np.maximum(np.mean(np.abs(Wt["U"]) ** 2, axis=0), 1e-300)
    print(f"{'config':26s} {'cmd':>7s} {'wheel':>7s} {'wheelH1':>8s} {'|L|shk':>7s} {'|S|shk':>7s}")
    rowsB = []
    for lbl, kp, q in (("KP 1.0 Q1.0 (control)", 1.0, 1.0), ("KP 2.0 Q1.0 (ARM-KP)", 2.0, 1.0),
                       ("KP 3.0 Q1.0", 3.0, 1.0), ("KP 3.0 Q0.6 (ARM-KP2)", 3.0, 0.6),
                       ("KP 4.0 Q0.6", 4.0, 0.6), ("KP 5.0 Q0.6", 5.0, 0.6),
                       ("KP 6.0 Q0.6", 6.0, 0.6), ("KP 8.0 Q0.6", 8.0, 0.6)):
        U1, L0, L1, rho, K = resynth(Wt, kp, 14.0, 0.30, q, Pm["P"])
        dU = U1 - Wt["U"]
        SR1 = Wt["SR"] + Psr_t[None, :] * dU
        SR1b = Wt["SR"] + Psr_h1[None, :] * dU
        cmd = float(np.sqrt(np.sum(np.abs(U1[:, shk]) ** 2) / np.sum(np.abs(Wt["U"][:, shk]) ** 2)))
        wr = float(np.sqrt(np.sum(np.abs(SR1[:, shk]) ** 2) / np.sum(np.abs(Wt["SR"][:, shk]) ** 2)))
        wrb = float(np.sqrt(np.sum(np.abs(SR1b[:, shk]) ** 2) / np.sum(np.abs(Wt["SR"][:, shk]) ** 2)))
        Sm = float(np.mean(np.abs(1.0 / (1.0 + L1[:, shk]))))
        print(f"{lbl:26s} {cmd:7.3f} {wr:7.3f} {wrb:8.3f} {float(np.mean(np.abs(L1[:, shk]))):7.3f} {Sm:7.3f}")
        rowsB.append(dict(label=lbl, kp=kp, q=q, cmd=cmd, wheel=wr, wheel_h1=wrb))

    print()
    print("    THE SAME, WITH THE HIDDEN FEEDBACK PUT BACK.  The rate loop + observer inside UFF")
    print("    respond to the extra wheel motion:  dUFF = H_sr_uff * Psr * dU, iterated to fixed point.")
    Huf = np.mean(np.conj(Wt["SR"]) * Wt["UFF"], axis=0) / np.maximum(np.mean(np.abs(Wt["SR"]) ** 2, axis=0), 1e-300)
    print(f"{'config':26s} {'cmd frozen':>11s} {'cmd w/ inner':>13s} {'wheel frozen':>13s} {'wheel w/ inner':>15s}")
    for lbl, kp, q in (("KP 2.0 Q1.0 (ARM-KP)", 2.0, 1.0), ("KP 3.0 Q0.6 (ARM-KP2)", 3.0, 0.6),
                       ("KP 5.0 Q0.6", 5.0, 0.6), ("KP 8.0 Q0.6", 8.0, 0.6)):
        U1, L0, L1, rho, K = resynth(Wt, kp, 14.0, 0.30, q, Pm["P"])
        dU0 = U1 - Wt["U"]
        g = Huf[None, :] * Psr_t[None, :]          # dUFF per unit dU, through the measured wheel
        dU = dU0 / (1.0 - g)                       # fixed point of dU = dU0 + g*dU
        SR0 = Wt["SR"] + Psr_t[None, :] * dU0
        SR1 = Wt["SR"] + Psr_t[None, :] * dU
        f1 = lambda Z, R: float(np.sqrt(np.sum(np.abs(Z[:, shk]) ** 2) / np.sum(np.abs(R[:, shk]) ** 2)))
        print(f"{lbl:26s} {f1(Wt['U']+dU0, Wt['U']):11.3f} {f1(Wt['U']+dU, Wt['U']):13.3f} "
              f"{f1(SR0, Wt['SR']):13.3f} {f1(SR1, Wt['SR']):15.3f}")
    print(f"    |g| in 1.8-3.5 Hz = {float(np.mean(np.abs(g[0, shk]))):.3f}  "
          f"(the inner paths' return ratio on the command; >=1 would be divergent)")

    print()
    print("=" * 112)
    print("(C) THE WINDOWS ARE THE CALM ONES.  Demand-amplitude terciles, plant re-identified in each.")
    q1, q2 = np.quantile(Wt["amp"], [1 / 3, 2 / 3])
    tiers = [("low |X|", Wt["amp"] <= q1), ("mid |X|", (Wt["amp"] > q1) & (Wt["amp"] <= q2)),
             ("high|X|", Wt["amp"] > q2)]
    print(f"{'tercile':>8s} {'n':>4s} {'config':22s} {'cmd':>7s} {'wheel':>7s} {'|L|shk':>7s} {'|P|shk':>8s}")
    for tname, tsel in tiers:
        idt = A.identify(Wt, inst="X", vsel=tsel)
        Wsub = {k: (v[tsel] if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(Wt["v"]) else v)
                for k, v in Wt.items()}
        Wsub["f"] = f
        Psr_s = (np.mean(np.conj(Wsub["X"]) * Wsub["SR"], axis=0)
                 / np.mean(np.conj(Wsub["X"]) * Wsub["U"], axis=0))
        for lbl, kp, qq in (("as flown", 1.0, 1.0), ("ARM-KP2 KP3 Q0.6", 3.0, 0.6), ("KP 5.0 Q0.6", 5.0, 0.6)):
            U1, L0, L1, rho, K = resynth(Wsub, kp, 14.0, 0.30, qq, idt["P"])
            dU = U1 - Wsub["U"]
            SR1 = Wsub["SR"] + Psr_s[None, :] * dU
            cmd = float(np.sqrt(np.sum(np.abs(U1[:, shk]) ** 2) / np.sum(np.abs(Wsub["U"][:, shk]) ** 2)))
            wr = float(np.sqrt(np.sum(np.abs(SR1[:, shk]) ** 2) / np.sum(np.abs(Wsub["SR"][:, shk]) ** 2)))
            print(f"{tname:>8s} {int(tsel.sum()):4d} {lbl:22s} {cmd:7.3f} {wr:7.3f} "
                  f"{float(np.mean(np.abs(L1[:, shk]))):7.3f} {float(np.mean(np.abs(idt['P'][shk]))):8.4f}")

    print()
    print("    AND BELOW THE METRIC'S FLOOR: the same doses on 8-15 m/s windows, which the metric")
    print("    never scores but the car still drives.")
    sel8 = (Wlo["v"] >= 8.0) & (Wlo["v"] < 15.0)
    if sel8.sum() >= 6:
        Wl = {k: (v[sel8] if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(Wlo["v"]) else v)
              for k, v in Wlo.items()}
        Wl["f"] = f
        idl = A.identify(Wlo, inst="X", vsel=sel8)
        Psr_l = np.mean(np.conj(Wl["X"]) * Wl["SR"], axis=0) / np.mean(np.conj(Wl["X"]) * Wl["U"], axis=0)
        print(f"{'config':26s} {'cmd':>7s} {'wheel':>7s} {'|L|shk':>7s}  (n={int(sel8.sum())} windows 8-15 m/s)")
        for lbl, kp, qq in (("as flown", 1.0, 1.0), ("ARM-KP2 KP3 Q0.6", 3.0, 0.6), ("KP 5.0 Q0.6", 5.0, 0.6)):
            U1, L0, L1, rho, K = resynth(Wl, kp, 14.0, 0.30, qq, idl["P"])
            dU = U1 - Wl["U"]
            SR1 = Wl["SR"] + Psr_l[None, :] * dU
            cmd = float(np.sqrt(np.sum(np.abs(U1[:, shk]) ** 2) / np.sum(np.abs(Wl["U"][:, shk]) ** 2)))
            wr = float(np.sqrt(np.sum(np.abs(SR1[:, shk]) ** 2) / np.sum(np.abs(Wl["SR"][:, shk]) ** 2)))
            print(f"{lbl:26s} {cmd:7.3f} {wr:7.3f} {float(np.mean(np.abs(L1[:, shk]))):7.3f}")
    else:
        print(f"    only {int(sel8.sum())} windows at 8-15 m/s -- not enough, reported as a gap")

    json.dump(dict(A=rowsA, B=rowsB), open(OUT / "a2_shake.json", "w"), indent=1)


if __name__ == "__main__":
    main()
