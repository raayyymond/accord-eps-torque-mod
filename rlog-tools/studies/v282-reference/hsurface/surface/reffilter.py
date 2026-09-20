# -*- coding: utf-8 -*-
"""Pin the setpoint lag to AccordRefFilter, PER ROUTE, against each route's own flown value.

Two cascaded first-order filters of RC seconds have a low-frequency group delay of exactly 2*RC, so the
prediction is: X->Z lag ~= 2*AccordRefFilter + the jerk-filter residual, and ~0 where the toggle is 0/absent.
ANALYSIS ONLY. usage: python reffilter.py
"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V

P = json.load(open(HERE / "params_all.json"))
LAGS = np.arange(-20, 81)
print(f"{'route':24s} {'RefFilter':>9s} {'2*RC pred':>9s} {'JerkLpHz':>8s} {'latDelay':>8s} "
      f"{'X->Z lag @0.15-0.3':>19s} {'|Hxz|':>6s} {'X->Z @0.3-0.6':>14s} {'commit':>9s}")
for rk in sorted(P):
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        continue
    S = V.load(rk)
    ok = np.isfinite(S["model"]) & np.isfinite(S["setpoint"])
    outs = []
    for f1, f2 in [(0.15, 0.30), (0.30, 0.60)]:
        sos = signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
        acc = np.zeros(len(LAGS)); n = 0; g = 0.0
        for a, b in V.runs(V.usable(S) & ok, S["t"], min_s=20.0):
            x = signal.sosfiltfilt(sos, np.nan_to_num(S["model"][a:b]))[150:-150]
            z = signal.sosfiltfilt(sos, np.nan_to_num(S["setpoint"][a:b]))[150:-150]
            if len(x) < 400:
                continue
            nx = math.sqrt(float(np.dot(x, x) * np.dot(z, z))) + 1e-30
            for k, L in enumerate(LAGS):
                xa, za = (x[:len(x) - L], z[L:]) if L >= 0 else (x[-L:], z[:len(z) + L])
                acc[k] += float(np.dot(xa, za)) / nx
            g += math.sqrt(float(np.dot(z, z) / max(np.dot(x, x), 1e-30))); n += 1
        outs.append((LAGS[int(np.argmax(acc))] * 10 if n else float('nan'), g / n if n else float('nan'), n))
    rf = P[rk].get("AccordRefFilter", "ABSENT")
    pred = f"{2*float(rf)*1000:.0f} ms" if rf not in ("ABSENT",) else "n/a"
    print(f"{rk:24s} {rf:>9s} {pred:>9s} {P[rk].get('AccordJerkLpHz','ABSENT'):>8s} "
          f"{np.median(S['lat_delay'][np.isfinite(S['lat_delay'])]):8.3f} "
          f"{outs[0][0]:14.0f} ms (n{outs[0][2]:3d}) {outs[0][1]:6.3f} {outs[1][0]:9.0f} ms(n{outs[1][2]:3d}) "
          f"{P[rk]['GitCommit'][:8]:>9s}")
    del S
