# -*- coding: utf-8 -*-
"""X4 -- IS TIER B'S CLOSURE A MEASUREMENT?  Two attacks on the number the probe would certify.

ATTACK 1 -- CONSTRUCTION DEPENDENCE.  The engine writes X-Y = A + V*D with D = Z-M the loop's own
error and A a residual, then scales D by the sensitivity ratio rho = (1+L0)/(1+L1).  EVERYTHING the
closure claims therefore rests on V, the measured M->Y leg.  V is a regression, and regressions of
two noisy signals have a direction.  I compute the SAME closure with four standard estimators of the
same V (H1, H2, and two instrumental variables) and report the spread.

ATTACK 2 -- FORWARD VALIDATION.  Run the identity between two configurations that were BOTH FLOWN on
the SAME EPS: predict r72 (SteerKP 0.85, Ki 0.6, no notch) from rev 6.4's windows, and rev 6.4 from
r72's.  A recipe that cannot predict a flown 1.2x controller change has not earned a 16x one.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
BAND = (0.15, 2.4)
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]


def grab(route):
    """X (model demand), Y (livePose accel), Z (shaped setpoint), M (controller measurement),
    UFB, UFF, U -- per window, >=15 m/s, runs >=30 s, unsaturated.  Nothing modelled."""
    import v282cmp as V
    S = V.load(route)
    lf = np.where(np.abs(S["out"]) > 5e-3, -(S["p"] + S["i"] + S["f"]) / S["out"], np.nan)
    laf = float(np.nanmedian(lf[S["active"]]))
    m = (S["active"] & ~S["pressed"] & (S["v"] >= 15.0) & np.isfinite(S["setpoint"])
         & np.isfinite(S["la_act"]) & np.isfinite(S["la_pose"]) & np.isfinite(S["model"])
         & np.isfinite(S["out"]))
    sig = dict(X=np.nan_to_num(S["model"]), Y=np.nan_to_num(S["la_pose"]),
               Z=np.nan_to_num(S["setpoint"]), M=np.nan_to_num(S["la_act"]),
               UFB=-(np.nan_to_num(S["p"]) + np.nan_to_num(S["i"])) / laf,
               UFF=-np.nan_to_num(S["f"]) / laf, U=np.nan_to_num(S["out"]))
    w = signal.get_window("hann", 1024)
    f = np.fft.rfftfreq(1024, A.DT)
    cols = {k: [] for k in sig}
    vm = []
    for a, b in V.runs(m, S["t"], min_s=30.0):
        for s in range(a, b - 1024 + 1, 512):
            e = s + 1024
            if float(np.mean(S["sat"][s:e])) > 0.02:
                continue
            for k, arr in sig.items():
                cols[k].append(np.fft.rfft(signal.detrend(arr[s:e]) * w))
            vm.append(float(np.median(S["v"][s:e])))
    del S
    return f, {k: np.array(v) for k, v in cols.items()}, np.array(vm)


def Vlegs(F):
    """Four estimators of the SAME leg V: M -> Y."""
    X = lambda a, b: np.mean(np.conj(F[a]) * F[b], axis=0)
    return dict(H1=X("M", "Y") / np.maximum(X("M", "M").real, 1e-300),
                H2=X("Y", "Y").real / np.conj(X("Y", "M")),
                IV_Z=X("Z", "Y") / X("Z", "M"),
                IV_X=X("X", "Y") / X("X", "M"))


def Pplant(F, vm):
    """Per-window plant from that window's speed bin (IV, instrument = the shaped setpoint Z)."""
    P = np.empty(F["Y"].shape, complex)
    for lo, hi in ((15.0, 22.0), (22.0, 99.0)):
        s = np.where((vm >= lo) & (vm < hi))[0]
        if len(s) < 4:
            s = np.arange(len(vm))
        Sz = lambda a, b: np.mean(np.conj(F["Z"][s]) * F[b][s], axis=0)
        P[(vm >= lo) & (vm < hi)] = Sz("Z", "M") / Sz("Z", "U")
    return P


def C_win(f, vm, kp, laf, ki, ki_hi, q):
    return np.array([A.C_fb(f, v, kp, laf, ki, ki_hi, q) for v in vm])


def J_of(F, b):
    E = F["X"] - F["Y"]
    return float(np.sum(np.abs(E[:, b]) ** 2) / np.sum(np.abs(F["X"][:, b]) ** 2))


def main():
    f = None
    pool = {}
    for r in T64 + V282:
        ff, F, vm = grab(r)
        f = ff
        pool[r] = (F, vm)
    b = (f >= BAND[0]) & (f <= BAND[1])
    cat = lambda rs, k: np.concatenate([pool[r][0][k] for r in rs], axis=0)
    FT = {k: cat(T64, k) for k in pool[T64[0]][0]}
    vT = np.concatenate([pool[r][1] for r in T64])
    FV = {k: cat(V282, k) for k in pool[V282[0]][0]}
    JT, JV = J_of(FT, b), J_of(FV, b)
    print(f"MY OWN METRIC:  rev 6.4 J = {JT:.4f}  (handed down 1.3512)   "
          f"V282 J = {JV:.4f}  (handed down 0.442)")
    print(f"   gap denominator used below = {JT - JV:.4f}")

    P = Pplant(FT, vT)
    C0 = C_win(f, vT, 1.0, 14.0, 0.3, 0.0, 1.0)
    L0 = P * C0
    D = FT["Z"] - FT["M"]
    E0 = FT["X"] - FT["Y"]
    px = float(np.sum(np.abs(FT["X"][:, b]) ** 2))
    VL = Vlegs(FT)

    print()
    print("=" * 120)
    print("ATTACK 1.  THE SAME CLOSURE, FOUR ESTIMATORS OF THE SAME LEG V (M -> Y).")
    print("   Each column is a standard, defensible estimator of one physical transfer.")
    print(f"   {'dose':26s} " + "".join(f"{k:>14s}" for k in VL) + f"{'spread':>10s}")
    doses = [("ARM-KP3   KP3.0 Q0.30", 3.0, 0.30, 0.6), ("TIER B    KP5.0 Q0.20", 5.0, 0.20, 0.3),
             ("TIER B    KP8.0 Q0.20", 8.0, 0.20, 0.3), ("TIER B    KP12  Q0.20", 12.0, 0.20, 0.3),
             ("TIER B    KP16  Q0.20", 16.0, 0.20, 0.3), ("ASYMPTOTE KP->inf", 1e6, 0.20, 0.3)]
    tab = {}
    for lbl, kp, q, ki in doses:
        C1 = C_win(f, vT, kp, 14.0, ki, 0.0, q)
        rho = (1.0 + L0) / (1.0 + P * C1)
        vals = []
        for nm, Vh in VL.items():
            E1 = E0 + Vh[None, :] * D * (rho - 1.0)
            J1 = float(np.sum(np.abs(E1[:, b]) ** 2)) / px
            vals.append(100.0 * (JT - J1) / (JT - JV))
        tab[lbl] = vals
        print(f"   {lbl:26s} " + "".join(f"{v:13.1f}%" for v in vals) +
              f"{max(vals)-min(vals):9.1f}pt")
    print()
    print("   |V| and arg V per estimator, averaged over 0.15-2.4 Hz -- these are the SAME transfer:")
    for nm, Vh in VL.items():
        print(f"      {nm:6s} |V| {np.mean(np.abs(Vh[b])):.3f}   arg {np.degrees(np.angle(np.mean(Vh[b]))):+7.1f} deg")
    print("   coh(M,Y) over the band: "
          f"{np.mean(np.abs(np.mean(np.conj(FT['M'])*FT['Y'],axis=0)[b])**2 / (np.mean(np.abs(FT['M'])**2,axis=0)[b]*np.mean(np.abs(FT['Y'])**2,axis=0)[b])):.3f}")

    print()
    print("=" * 120)
    print("ATTACK 2.  FORWARD VALIDATION BETWEEN TWO FLOWN CONFIGS ON THE SAME EPS.")
    print("   r72 flew SteerKP 0.85 / Ki 0.6 / no notch; rev 6.4 flew SteerKP 1.0 / Ki 0.3 / notch Q 1.0.")
    ff, F72, v72 = grab("00000072--8001fc3048")
    J72 = J_of(F72, b)
    C1 = C_win(f, vT, 0.85, 14.0, 0.6, 0.0, None)
    rho = (1.0 + L0) / (1.0 + P * C1)
    pred = {}
    for nm, Vh in VL.items():
        E1 = E0 + Vh[None, :] * D * (rho - 1.0)
        pred[nm] = float(np.sum(np.abs(E1[:, b]) ** 2)) / px
    print(f"   rev 6.4 -> r72 :  measured r72 J = {J72:.4f}    predicted " +
          "  ".join(f"{k} {v:.4f}" for k, v in pred.items()))
    print(f"                     prediction error " +
          "  ".join(f"{k} {v/J72:.2f}x" for k, v in pred.items()))
    P72 = Pplant(F72, v72)
    C072 = C_win(f, v72, 0.85, 14.0, 0.6, 0.0, None)
    L072 = P72 * C072
    D72 = F72["Z"] - F72["M"]
    E072 = F72["X"] - F72["Y"]
    px72 = float(np.sum(np.abs(F72["X"][:, b]) ** 2))
    VL72 = Vlegs(F72)
    C164 = C_win(f, v72, 1.0, 14.0, 0.3, 0.0, 1.0)
    rho2 = (1.0 + L072) / (1.0 + P72 * C164)
    pred2 = {}
    for nm, Vh in VL72.items():
        E1 = E072 + Vh[None, :] * D72 * (rho2 - 1.0)
        pred2[nm] = float(np.sum(np.abs(E1[:, b]) ** 2)) / px72
    print(f"   r72 -> rev 6.4 :  measured rev6.4 J = {JT:.4f}    predicted " +
          "  ".join(f"{k} {v:.4f}" for k, v in pred2.items()))
    print(f"                     prediction error " +
          "  ".join(f"{k} {v/JT:.2f}x" for k, v in pred2.items()))
    print()
    print("   NOTE the two directions must be consistent for the identity to be a model of the car:")
    print("   if rev6.4 -> r72 says 'better' and r72 -> rev6.4 also says 'better', the recipe is")
    print("   reading the ROUTE, not the controller.")
    json.dump(dict(JT=JT, JV=JV, J72=J72, tab=tab, pred=pred, pred2=pred2),
              open(OUT / "x4_closure.json", "w"), indent=1)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0, str(HERE.parents[1]))
    main()
