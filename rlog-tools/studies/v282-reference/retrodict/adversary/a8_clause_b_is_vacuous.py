"""A8 - clause (b) SEPARATION: can it fail?

On a COMMON plant the statistic is |L_i| = |C_i| * |G_anchor * P_shape * M * e^{-jwD}| evaluated at
each controller's own -180 crossing.  The plant anchor is the SAME factor for both controllers, so
the r71 / r72 ratio is (almost) a deterministic function of the flown parameters and the anchor's
sampling error cancels.  Quantified here by a block bootstrap of the anchor.
"""
import math
import os
import numpy as np
from scipy import signal
import a4_repaired_statistic as R

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
KEY = "00000072--8001fc3048"

z = np.load(os.path.join(CACHE, KEY + ".npz"))
t = z["t_cs"]
ok = (z["cs_active"] > 0.5)
v = np.interp(t, z["t_cst"], z["vego"])
sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
u = z["cs_out"]
y = np.interp(t, z["t_cst"], z["sa_deg"])
del z
m = ok & ~sp & (v >= 15.0)
d = np.diff(m.astype(int))
st = np.flatnonzero(d == 1) + 1
en = np.flatnonzero(d == -1) + 1
if m[0]:
    st = np.r_[0, st]
if m[-1]:
    en = np.r_[en, len(m)]
blocks = []
for s, e in zip(st, en):
    for a in range(s, e - 2048, 2048):
        blocks.append((a, a + 2048))
print(f"r72: {len(blocks)} independent 20.5 s blocks of engaged hands-off >=15 m/s")


def anchor(bl):
    Pyu = 0j
    Puu = 0.0
    for a, b in bl:
        uu = u[a:b] - u[a:b].mean()
        yy = y[a:b] - y[a:b].mean()
        f, c = signal.csd(uu, yy, fs=100.0, nperseg=2048)
        _, p = signal.welch(uu, fs=100.0, nperseg=2048)
        i = int(np.argmin(np.abs(f - 0.20)))
        Pyu += c[i]
        Puu += p[i]
    return abs(Pyu / Puu)


def ratio(T):
    out = {}
    for cn in ("r71   (LIMIT CYCLE)", "r72   (clean)"):
        w, L = R.loop(R.CTRL[cn], T, 25.0, 0.065, 0.20)
        out[cn] = R.crossing(w, L)[1]
    return out["r71   (LIMIT CYCLE)"] / out["r72   (clean)"]


rng = np.random.default_rng(3)
T0 = anchor(blocks)
r0 = ratio(T0)
boots = []
for _ in range(300):
    bl = [blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]
    boots.append(ratio(anchor(bl)))
boots = np.array(boots)
print(f"anchor |T(0.20)| = {T0:.2f} deg/torque")
print(f"statistic ratio r71/r72 on r72's plant = {r0:.4f}")
print(f"block-bootstrap 95% CI of that RATIO   = [{np.percentile(boots,2.5):.4f}, {np.percentile(boots,97.5):.4f}]"
      f"   (width {np.percentile(boots,97.5)-np.percentile(boots,2.5):.4f})")
print("\nNOTE: r71 is ONE route and r72 is ONE route, so a ROUTE-CLUSTER bootstrap has n=1 cluster")
print("per arm and returns a zero-width interval.  Clause (b) as written cannot fail.")
