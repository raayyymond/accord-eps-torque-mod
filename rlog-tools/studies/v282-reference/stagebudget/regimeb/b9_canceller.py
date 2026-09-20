# -*- coding: utf-8 -*-
"""REGIME B stage 9: pin candidate (iv).  The measured |H_XZ| bump against the fork's DOCUMENTED stage.

The fork documents the delay-compensation stage as
    setpoint = u(t-D) + F_j(s) * (u(t) - u(t-D))   =>   H(s) = e^{-sD} + F_j(s)*(1 - e^{-sD})
with F_j a first-order low-pass at HONDA_ACCORD_JERK_LP_HZ (4.0 on rev 6.4) or the generic
LP_FILTER_CUTOFF_HZ = 1.2 on every earlier commit; AccordRefFilter adds two cascaded first-order
lags of RC seconds after it.  This is ARITHMETIC ON THE DOCUMENTED STAGE evaluated at each route's own
FLOWN D (liveDelay.lateralDelay, read from the log) and its own flown toggles -- it is a cross-check of a
MEASURED transfer against the stage that is supposed to produce it, not a prediction of the car.

usage: python b9_canceller.py > B9-OUT.txt
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

GRP = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
       "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4",
       "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
       "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2"}
PAR = json.load(open(HERE.parents[1] / "hsurface" / "surface" / "params_all.json"))


def H_stage(f, Dlag, fj, rc):
    s = 2j * np.pi * f
    e = np.exp(-s * Dlag)
    F = 1.0 / (1.0 + s / (2 * np.pi * fj))
    H = e + F * (1 - e)
    if rc > 0:
        H = H / (1 + s * rc) ** 2
    return H


print("Flown lateralDelay (liveDelay), engaged frames only, and the flown toggles:")
dl = {}
for rk, g in GRP.items():
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk)
    m = S["active"] & np.isfinite(S["lat_delay"])
    d = float(np.median(S["lat_delay"][m])) if m.sum() else float("nan")
    dl.setdefault(g, []).append(d)
    p = PAR[rk]
    print(f"  {rk} {g:5s} D={d:.3f}s  AccordRefFilter={str(p.get('AccordRefFilter')):6s} "
          f"AccordJerkLpHz={str(p.get('AccordJerkLpHz')):6s}")
    del S

print("\nPredicted |H_XZ| of the DOCUMENTED stage at each rev's flown D / F_j / RC, vs the MEASURED |H_XZ|")
print("(measured = b4 T8, 15-22 m/s band averages).")
CFG = {"V282": (None, 1.2, 0.0), "T2": (None, 1.2, 0.0), "T3": (None, 1.2, 0.12),
       "T4": (None, 1.2, 0.12), "T5": (None, 1.2, 0.12), "T64": (None, 4.0, 0.06)}
MEAS = {  # band -> {rev: measured |H_XZ|}  (from B4-OUT.txt, 15-22 m/s)
    (0.10, 0.20): dict(V282=1.030, T2=1.038, T3=1.035, T4=1.046, T5=1.044, T64=1.000),
    (0.30, 0.45): dict(V282=1.145, T2=1.144, T3=1.054, T4=1.073, T5=1.054, T64=1.038),
    (0.45, 0.60): dict(V282=1.227, T2=1.230, T3=1.070, T4=1.089, T5=1.066, T64=1.065),
    (0.60, 0.80): dict(V282=1.332, T2=1.337, T3=1.040, T4=1.030, T5=0.970, T64=1.063),
    (0.80, 1.00): dict(V282=1.373, T2=1.385, T3=0.873, T4=0.844, T5=0.864, T64=1.010),
    (1.00, 1.20): dict(V282=1.335, T2=1.333, T3=0.651, T4=0.660, T5=0.671, T64=0.882),
    (1.20, 1.50): dict(V282=1.197, T2=1.220, T3=0.449, T4=0.430, T5=0.418, T64=0.696),
}
revs = ["V282", "T2", "T3", "T4", "T5", "T64"]
print(f"  {'band Hz':>11s} " + " ".join(f"{r+' pred/meas':>16s}" for r in revs))
for (f1, f2), mm in MEAS.items():
    fc = 0.5 * (f1 + f2)
    row = f"  {f1:.2f}-{f2:.2f}   "
    for r in revs:
        Dm = float(np.median(dl[r])) if r in dl else float("nan")
        _, fj, rc = CFG[r]
        pr = abs(H_stage(fc, Dm, fj, rc))
        row += f" {pr:7.3f}/{mm[r]:7.3f}"
    print(row)
print("\n  D used (median of each rev's flown liveDelay): " +
      "  ".join(f"{r}={np.median(dl[r]):.3f}s" for r in revs if r in dl))
