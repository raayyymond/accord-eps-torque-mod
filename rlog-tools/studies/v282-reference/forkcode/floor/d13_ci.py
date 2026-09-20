# -*- coding: utf-8 -*-
"""d13 -- confidence intervals on the headline decomposition, by a bootstrap over BOTH nuisance
sources at once: the window set (route-clustered) and the screened V (its own 600-draw bootstrap)."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
BAND = (0.15, 2.4); TAU = 0.102; JREF = 0.442
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]

cols = {k: [] for k in ("X", "Y", "Z", "M")}; rid = []
for n, r in enumerate(T64):
    D = np.load(FRONT / f"f1_{r}.npz"); f = D["f"]
    for k in cols: cols[k].append(D[k])
    rid.append(np.full(D["X"].shape[0], n)); del D
W = {k: np.concatenate(v) for k, v in cols.items()}; rid = np.concatenate(rid)
Dv = np.load(OUT / "d3_broadV.npz"); fv, H1, boots = Dv["f"], Dv["H1"], Dv["boots"]
onto = lambda H: np.interp(f, fv, np.abs(H)) * np.exp(1j * np.interp(f, fv, np.unwrap(np.angle(H))))
sel = np.where((f >= BAND[0]) & (f <= BAND[1]))[0]
ph = np.exp(2j * np.pi * f * TAU)[None, :]
E = W["X"] - W["Y"]; Dl = W["Z"] - W["M"]
rng = np.random.default_rng(11); acc = []
for it in range(2000):
    pick = rng.choice([0, 1], 2, replace=True)
    rows = np.concatenate([np.where(rid == p)[0] for p in pick])
    rows = rows[rng.integers(0, len(rows), len(rows))]
    Vc = onto(boots[rng.integers(0, len(boots))])[None, :] * ph
    ix = np.ix_(rows, sel)
    Ee = E[ix]; px = float(np.sum(np.abs(W["X"][ix]) ** 2)); pe = float(np.sum(np.abs(Ee) ** 2))
    T = {"a": (Vc * Dl)[ix], "b": (W["X"] - W["Z"])[ix], "c": ((1 - Vc) * W["Z"])[ix],
         "d": (-(W["Y"] * ph - Vc * W["M"]))[ix], "e": (W["Y"] * ph - W["Y"])[ix]}
    sh = {k: float(np.sum(np.real(np.conj(Ee) * v))) / pe for k, v in T.items()}
    J = pe / px
    acc.append(dict(J=J, Jinf=float(np.sum(np.abs(Ee - T["a"]) ** 2)) / px,
                    **{k: v * J for k, v in sh.items()}))
A = {k: np.array([a[k] for a in acc]) for k in acc[0]}
JF = 1.3512; GAP = JF - JREF
print("HEADLINE DECOMPOSITION OF J = 1.3512, with 95 % CI (route cluster x V bootstrap, n=2000)")
print(f"  {'term':14s} {'x J':>18s} {'% of J':>16s} {'% of the 0.909 gap':>22s}")
for k, nm in (("a", "a loop error"), ("b", "b setpoint chain"), ("c", "c wheel->yaw"),
              ("d", "d incoherent"), ("e", "e instrument")):
    v = A[k]; lo, hi = np.percentile(v, [2.5, 97.5])
    print(f"  {nm:14s} {np.median(v):7.4f} [{lo:.3f},{hi:.3f}] "
          f"{100*np.median(v)/JF:7.1f} [{100*lo/JF:.1f},{100*hi/JF:.1f}] "
          f"{100*np.median(v)/GAP:11.1f} [{100*lo/GAP:.1f},{100*hi/GAP:.1f}]")
lo, hi = np.percentile(A["Jinf"], [2.5, 97.5])
print(f"\n  J_inf (loop gain -> infinity) = {np.median(A['Jinf']):.4f}  95% CI [{lo:.4f}, {hi:.4f}]")
print(f"  closure vs the brief's V282 0.442  = {100*(JF-np.median(A['Jinf']))/GAP:.1f}% "
      f"[{100*(JF-hi)/GAP:.1f}, {100*(JF-lo)/GAP:.1f}]")
print(f"  closure vs this kit's own 0.4705   = {100*(JF-np.median(A['Jinf']))/(JF-0.4705):.1f}%")
lo, hi = np.percentile(A["J"], [2.5, 97.5])
print(f"  (positive control: J reproduces at {np.median(A['J']):.4f} [{lo:.3f},{hi:.3f}])")
json.dump({k: [float(np.median(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
           for k, v in A.items()}, open(OUT / "d13.json", "w"), indent=1)
