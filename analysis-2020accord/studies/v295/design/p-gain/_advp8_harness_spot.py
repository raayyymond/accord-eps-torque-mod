import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (HERE, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"), os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant")):
    sys.path.insert(0, p)
import v295_harness as H
import plib as P
Z = dict(np.load(os.path.join(HERE, "out", "_advp4_marches.npz")))
d = P.load()
N = 20000   # frames = 200,000 ticks, starting at an engaged stretch
k0 = int(np.flatnonzero(d["eng"])[0])
c = H.Cells.v294().replace(name="CAND", kp_x=(0, 8, 54, 100, 208), kp_y=(1248, 1248, 1104, 960, 960))
L = H.Lane([H.Cells.v294(), c])
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
idx = d["idx"].astype(np.int64); sgn = d["sgn"].astype(np.int64); m = d["m"].astype(np.int64)
sp = np.vstack([sgn * L.map_tab[i, idx] for i in range(2)])
T = L.march(np.repeat(x1k[None, :N * 10], 2, 0), sp[:, :N], np.repeat(idx[None, :N], 2, 0), np.repeat(m[None, :N], 2, 0))
for i, nm in enumerate(("V294", "CAND")):
    mine = Z[nm + "_live"][:N * 10]
    print(nm, "harness Lane vs adversary lane, first %d ticks: mismatches %d, max |diff| %d" % (N * 10, np.count_nonzero(T[i] != mine), np.abs(T[i] - mine).max()))
