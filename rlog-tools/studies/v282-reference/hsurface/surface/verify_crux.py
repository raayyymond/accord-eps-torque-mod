# -*- coding: utf-8 -*-
"""Independent check of the two headline cells by a TIME-DOMAIN method that shares no code with surface.py:
band-pass, find the lag by cross-correlation, align, then least-squares regress achieved on desired.
Must reproduce the spectral |H| and lag for 0.30-0.60 Hz / 15-22 m/s and 0.15-0.30 Hz / 15-22 m/s.
ANALYSIS ONLY. usage: python verify_crux.py
"""
import math, sys
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V

GR = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
      "TORQ": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
               "00000076--d0b7ea7e4d", "00000075--6c8687d5bd", "00000072--8001fc3048",
               "00000073--79fd149dd8", "00000070--717f5a7866", "00000071--f2c9d073a3"],
      "T64F": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd"]}
CELLS = [(0.30, 0.60, 15.0, 22.0, 0.0, 0.3), (0.30, 0.60, 15.0, 22.0, 0.3, 1.0),
         (0.15, 0.30, 15.0, 22.0, 0.0, 0.3), (0.30, 0.60, 8.0, 15.0, 0.0, 0.3)]
print("cell (band, speed, p95|model| stratum) -> time-domain gain and lag, vs the spectral surface")
for f1, f2, vlo, vhi, alo, ahi in CELLS:
    print(f"\n  {f1:.2f}-{f2:.2f} Hz, v {vlo:.0f}-{vhi:.0f} m/s, amp {alo}-{ahi} m/s^2")
    for gn, rl in GR.items():
        sos = signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
        XS, YS = [], []
        for rk in rl:
            S = V.load(rk)
            m = V.usable(S, vlo, vhi) & np.isfinite(S["model"]) & np.isfinite(S["la_pose"])
            for a, b in V.runs(m, S["t"], min_s=12.0):
                # same amplitude stratum rule as the surface: p95 |model| over a 10.24 s window
                n = 1024
                for k in range(a, b - n + 1, n // 2):
                    ap = float(np.percentile(np.abs(np.nan_to_num(S["model"][k:k + n])), 95))
                    if not (alo <= ap < ahi):
                        continue
                    x = signal.sosfiltfilt(sos, np.nan_to_num(S["model"][k - 100 if k >= 100 else k:k + n + 100]))
                    y = signal.sosfiltfilt(sos, np.nan_to_num(S["la_pose"][k - 100 if k >= 100 else k:k + n + 100]))
                    o = 100 if k >= 100 else 0
                    XS.append(x[o:o + n]); YS.append(y[o:o + n])
            del S
        if len(XS) < 6:
            print(f"     {gn:6s} n={len(XS)} windows -- too thin"); continue
        best = (-1e9, 0)
        for L in range(0, 81):
            num = den1 = den2 = 0.0
            for x, y in zip(XS, YS):
                xa, ya = x[:len(x) - L], y[L:]
                num += float(np.dot(xa, ya)); den1 += float(np.dot(xa, xa)); den2 += float(np.dot(ya, ya))
            r = num / math.sqrt(den1 * den2 + 1e-30)
            if r > best[0]:
                best = (r, L)
        L = best[1]
        num = den = 0.0
        for x, y in zip(XS, YS):
            xa, ya = x[:len(x) - L], y[L:]
            num += float(np.dot(xa, ya)); den += float(np.dot(xa, xa))
        # route-cluster bootstrap on the gain
        rid = []
        print(f"     {gn:6s} n={len(XS):4d} windows   lag {L*10:4d} ms  r {best[0]:+.3f}   "
              f"aligned regression gain {num/den:.3f}")
