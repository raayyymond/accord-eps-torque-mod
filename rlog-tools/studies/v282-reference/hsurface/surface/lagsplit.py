# -*- coding: utf-8 -*-
"""Stage 4: WHERE the extra lag is. The surface says torque mode's miss is almost all phase, so split the
model->achieved lag into the two legs the log lets us see:

    X = model desired lat accel  --(fork reference shaping, incl. its delay compensation)-->  Z = setpoint
    Z = setpoint                 --(the rest: command, EPS, plant, sensing)               -->  Y = achieved

Measured two independent ways per leg: the band cross-phase (wrap-limited) and an unwrapped time-domain
cross-correlation over +-800 ms. Plus each route's OWN flown liveDelay.lateralDelay, because the fork's
lead is a logged parameter and a lead difference is not a plant difference.

ANALYSIS ONLY, read-only.  usage: python lagsplit.py > LAGSPLIT-OUT.txt
"""
import math, sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

SPDN = ["0-8", "8-15", "15-22", "22+"]
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
BANDS = [(0.06, 0.15, 40.96), (0.15, 0.30, 20.48), (0.30, 0.60, 10.24), (0.60, 1.20, 10.24)]
# grouped by the ONE toggle that sets the setpoint lag (AccordRefFilter, read from each route's initData),
# so the EPS-mode effect can be separated from the toggle's effect:
RT = {"V282 RF0": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
      "V282old RF0": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
      "TORQ RF0": ["00000070--717f5a7866", "00000071--f2c9d073a3"],
      "TORQ RF.06": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd"],
      "TORQ RF.12": ["00000076--d0b7ea7e4d", "00000075--6c8687d5bd", "00000072--8001fc3048",
                     "00000073--79fd149dd8"]}

print("=" * 132)
print("0. EACH ROUTE'S OWN FLOWN LEAD: liveDelay.lateralDelay (s), read from that route's log. A lead difference")
print("   between the two builds is a PARAMETER difference, not a plant difference.")
print("=" * 132)
for g, rl in RT.items():
    for rk in rl:
        S = V.load(rk)
        u = V.usable(S)
        ld = S["lat_delay"][u]
        ld = ld[np.isfinite(ld)]
        print(f"   {g:12s} {rk:24s} lateralDelay median {np.median(ld) if len(ld) else float('nan'):.4f} s  "
              f"p5/p95 {np.percentile(ld,5) if len(ld) else float('nan'):.4f}/"
              f"{np.percentile(ld,95) if len(ld) else float('nan'):.4f}  n {len(ld)}")
        del S

print("\n" + "=" * 132)
print("1. UNWRAPPED time-domain lag per leg, per speed bin, per band. Cross-correlation peak over +-800 ms of")
print("   band-passed signals, accumulated over every usable run >=20 s, normalised per run.")
print("   X->Z is the fork's own shaping (positive = the setpoint LAGS the plan; NEGATIVE = the fork LEADS).")
print("=" * 132)
LAGS = np.arange(-80, 81)
res = {}
for g, rl in RT.items():
    for rk in rl:
        S = V.load(rk)
        ok = np.isfinite(S["model"]) & np.isfinite(S["la_pose"]) & np.isfinite(S["setpoint"])
        for bi, (f1, f2, _) in enumerate(BANDS):
            sos = signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
            for si, (lo, hi) in enumerate(SPD):
                m = V.usable(S, lo, hi) & ok
                for a, b in V.runs(m, S["t"], min_s=20.0):
                    sig = [signal.sosfiltfilt(sos, np.nan_to_num(S[k][a:b]))[150:-150]
                           for k in ("model", "setpoint", "la_pose")]
                    if len(sig[0]) < 400:
                        continue
                    for leg, (p, q) in enumerate(((0, 2), (0, 1), (1, 2))):
                        x, y = sig[p], sig[q]
                        nx = math.sqrt(float(np.dot(x, x) * np.dot(y, y))) + 1e-30
                        key = (g, bi, si, leg)
                        if key not in res:
                            res[key] = [np.zeros(len(LAGS)), 0]
                        for k, L in enumerate(LAGS):
                            xa, ya = (x[:len(x) - L], y[L:]) if L >= 0 else (x[-L:], y[:len(y) + L])
                            res[key][0][k] += float(np.dot(xa, ya)) / nx
                        res[key][1] += 1
        del S

LEGN = ["X->Y model->achieved", "X->Z model->setpoint", "Z->Y setpoint->achieved"]
for bi, (f1, f2, _) in enumerate(BANDS):
    print(f"\n   band {f1:.2f}-{f2:.2f} Hz")
    print(f"      {'speed':7s} {'group':12s} " + "  ".join(f"{n:>26s}" for n in LEGN) + "   runs")
    for si in range(4):
        for g in RT:
            row = []
            nr = 0
            for leg in range(3):
                r = res.get((g, bi, si, leg))
                if not r or r[1] == 0:
                    row.append("      --          "); continue
                c = r[0] / r[1]
                k = int(np.argmax(c))
                row.append(f"{LAGS[k]*10:+5d} ms  r{c[k]:+.2f}      ")
                nr = r[1]
            if nr:
                print(f"      {SPDN[si]:7s} {g:12s} " + "  ".join(row) + f"   {nr}")
