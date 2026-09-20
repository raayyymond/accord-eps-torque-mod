# -*- coding: utf-8 -*-
"""REGIME B stage 10: per-ROUTE breakdown of the two load-bearing numbers, so neither rests on one route.
usage: python b10_perroute.py > B10-OUT.txt"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
NRM1 = 16.0 / (3.0 * (W * 100.0) ** 2)
SPDN = ["0-8", "8-15", "15-22", "22+"]; SPD = [(0, 8), (8, 15), (15, 22), (22, 40)]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}
GRP = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
       "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
       "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
       "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2"}
d = np.sqrt((np.abs(D["X"][:, (FR >= .6) & (FR < 1.2)]) ** 2).sum(1) * NRM1)

print("PER-ROUTE |H| (0.60-1.20 Hz, X->Y), M_inc, and the demand-normalised incoherent wheel residual,")
print("at MATCHED in-band demand RMS.  Neither headline may rest on one route.\n")
print(f"{'route':22s} {'grp':6s} " + " ".join(f"{SPDN[i]+': n |H| Minc resA':>30s}" for i in (1, 2, 3)))
for rk in sorted(GRP, key=lambda r: (GRP[r] != "V282", GRP[r], r)):
    row = f"{rk:22s} {GRP[rk]:6s} "
    for i in (1, 2, 3):
        lo, hi = DSEL[i]
        k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & (D["route"] == rk) & (d >= lo) & (d < hi))
        if len(k) < 5:
            row += f" {len(k):4d}{'--':>26s}"; continue
        s = (FR >= .6) & (FR < 1.2)
        X = D["X"][k][:, s]; Y = D["Y"][k][:, s]; A = D["A"][k][:, s]
        Pxx = (np.abs(X) ** 2).sum(0); Pyy = (np.abs(Y) ** 2).sum(0); Pxy = (np.conj(X) * Y).sum(0)
        H = float(np.average(np.abs(Pxy) / np.maximum(Pxx, 1e-300), weights=Pxx))
        mi = float(np.sqrt(np.average(np.maximum(Pyy - np.abs(Pxy) ** 2 / np.maximum(Pxx, 1e-300), 0) /
                                      np.maximum(Pxx, 1e-300), weights=Pxx)))
        Paa = (np.abs(A) ** 2).sum(0); Pxa = (np.conj(X) * A).sum(0)
        ra = float(np.sqrt(max((Paa - np.abs(Pxa) ** 2 / np.maximum(Pxx, 1e-300)).sum(), 0) / len(k) * NRM1))
        row += f" {len(k):4d} {H:5.2f} {mi:5.2f} {ra/max(np.median(d[k]),1e-9):7.1f}"
    print(row)

print("\nPER-ROUTE kurtosis of the 0.3-4 Hz band-passed steering RATE, matched blocks (same recipe as B5).")
bp = lambda x, a, b: sg.sosfiltfilt(sg.butter(3, [a, b], btype="band", fs=100.0, output="sos"), x)
for rk, grp in sorted(GRP.items(), key=lambda kv: (kv[1] != "V282", kv[1], kv[0])):
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk); ok = np.isfinite(S["sr"]) & np.isfinite(S["model"]) & np.isfinite(S["v"])
    m = S["active"] & ~S["pressed"] & ok; n = 1024; acc = {1: [], 2: [], 3: []}
    for a, b in V.runs(m, S["t"], min_s=12.0):
        xb = bp(np.nan_to_num(S["model"][a:b]), 0.6, 1.2); rb = bp(np.nan_to_num(S["sr"][a:b]), 0.3, 4.0)
        for k in range(a + 200, b - 200 - n + 1, n // 2):
            sl = slice(k, k + n); rel = slice(k - a, k - a + n)
            vv = S["v"][sl]; vm = float(np.median(vv))
            i = next((q for q, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
            if i in (None, 0) or float(np.mean((vv >= SPD[i][0]) & (vv < SPD[i][1]))) < 0.8:
                continue
            lo, hi = DSEL[i]
            if not (lo <= float(np.sqrt(np.mean(xb[rel] ** 2))) < hi):
                continue
            z = rb[rel] - rb[rel].mean()
            if z.std() > 1e-9:
                acc[i].append(float((z ** 4).mean() / z.std() ** 4))
    print(f"  {rk:22s} {grp:6s} " + " ".join(
        f"{SPDN[i]}:n{len(acc[i]):3d} kurt {np.median(acc[i]):5.2f}" if len(acc[i]) >= 5 else f"{SPDN[i]}:n{len(acc[i]):3d}   --   "
        for i in (1, 2, 3)))
    del S
