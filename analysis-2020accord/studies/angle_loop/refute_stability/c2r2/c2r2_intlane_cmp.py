# -*- coding: utf-8 -*-
"""c2r2_intlane_cmp.py -- integer lane vs the linear exact-periodic model on the SAME 2 deg setpoint step:
trajectory difference, the same ring estimator on both, and the settled 0.5-5 Hz / 5-30 Hz residue of the integer lane
(an integer limit cycle at the ring frequency would show here).  ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M
import c2r2_intlane as IL

def linear_step(des, pl, v, sp_deg=2.0, n=6000):
    per = M.Periodic(des, pl, v)
    mats = [per.tick_matrix(k) for k in range(10)]
    X = np.zeros(per.n)
    th = []
    ix = per.idx["xp"]
    for k in range(n):
        th.append(float(per.Ct @ X[ix]))
        A, b = mats[k % 10]
        X = A @ X + b * sp_deg
    return np.array(th)

def band_amp(y, lo, hi):
    y = y - y.mean()
    Y = np.fft.rfft(y * np.hanning(len(y)))
    f = np.fft.rfftfreq(len(y), 1e-3)
    b = (f >= lo) & (f <= hi)
    return float(np.abs(Y[b]).max() / (len(y) / 4)) if b.any() else 0.0

D = M.load_designs()
cases = [("P2", "b_q*J1.0+h10", 26.9), ("P2", "b_q*J1.0", 15.5), ("P2", "b_q*J1.0+h10", 15.75),
         ("F2", "b_q*J1.0+h10", 15.5), ("F2", "b_q*J1.0", 15.5), ("P2", "b_lo*J_hi*tau6+h10", 8.0),
         ("P2", "J1.0+h10", 1.0), ("B0r", "b_q*J1.0+h10", 15.5), ("D2a", "b_q*J1.0+h10", 26.9)]
print("case | lin ring f/zeta | int ring f/zeta | max|th_int-th_lin| first 3 s | int tail(last 3 s) 0.5-5 Hz amp / 5-30 Hz amp (deg)")
for dn, mn, v in cases:
    pl = M.member(mn, v)
    thl = linear_step(D[dn], pl, v, n=8000)
    thi, T = IL.sim(D[dn], pl, v, sp_deg=2.0, n_ticks=8000)
    fl, zl, _ = IL.ring_fit(thl)
    fi, zi, _ = IL.ring_fit(thi)
    dmax = float(np.max(np.abs(thi[:3000] - thl[:3000])))
    print(f"{dn} {mn:20s} {v:5.2f} | {fl:5.2f} {zl:.3f} | {fi:5.2f} {zi:.3f} | {dmax:.3f} | "
          f"{band_amp(thi[-3000:], 0.5, 5):.4f} / {band_amp(thi[-3000:], 5, 30):.5f}")
