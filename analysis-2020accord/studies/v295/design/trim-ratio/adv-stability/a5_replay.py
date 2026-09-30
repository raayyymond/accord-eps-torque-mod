# -*- coding: utf-8 -*-
"""a5_replay.py -- (d) byte-exact open-loop replay on r71b's own recorded command and 0x18F rate with MY IntLane:
V294 vs the 427 tap (reproduction R3), then b964 on the same inputs: fb-clamp C binding, P clamp, rail, int32 products,
the trim's peak, and where the extra trim sits (by band, hands-off engaged).  Inputs: plib's cache (x1k = 10x
resample_poly of the wire, idx/sgn/m from the kit's demand chain, tap alignment dms/sg) -- data, not code.
Output: a5_replay_out.txt"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import plib as PL  # noqa: E402

out = open(os.path.join(HERE, "a5_replay_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


d = PL.load()
V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
G3 = A.with_b(V294, 1701, "b1701")
cells = [V294, B964, G3]
L = A.IntLane(cells)
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
idx = d["idx"].astype(np.int64)
sgn = d["sgn"].astype(np.int64)
m = d["m"].astype(np.int64)
n = len(idx) * 10
T = np.zeros((3, n), np.int32)
r26 = np.zeros((3, n), np.int32)
cb = np.zeros((3, n), bool)
pb = np.zeros((3, n), bool)
mapt = L.map_tab[0]
for i in range(n):
    k = i // 10
    sp = int(sgn[k]) * int(mapt[idx[k]])
    t = L.tick(int(x1k[i]), sp, int(idx[k]), int(m[k]))
    T[:, i] = t
    r26[:, i] = L.last["r26"]
    cb[:, i] = L.cbind
    pb[:, i] = L.pbind
P("ticks", n, "int32 max |products| (all three lanes):", L.maxabs, " 2^31 =", 2 ** 31)
sg, dms = d["sg"], d["dms"]
tt = np.clip(d["tick_tap"], 0, n - 1)
ho100 = d["ho"]
ho_tap = ho100[d["j100"]]
res = d["T_tap"] - PL.quant(sg * T[0, tt])
P("R3: V294 march (MY lane) vs 427 tap, hands-off engaged: rms %.2f counts on %d tap frames (harness/plib: 3.64)" % (
    np.sqrt(np.mean(res[ho_tap] ** 2)), int(ho_tap.sum())))
P("    bit-exact vs plib's march T1k_live:", int(np.sum(sg * T[0] != d["T1k_live"])), "mismatching ticks of", n)
eng1k = np.repeat(d["eng"], 10)[:n]
ho1k = np.repeat(ho100, 10)[:n]
for j, c in enumerate(cells):
    P("%-6s engaged ticks: C (fb clamp %d) binds %.4f %% ; P clamp binds %.4f %% ; |T| at rail (>= 2400) %.4f %% ; max |T| %d ; "
      "max |r26| %d" % (c["name"], c["fb_clamp"], 100 * cb[j][eng1k].mean(), 100 * pb[j][eng1k].mean(),
                        100 * (np.abs(T[j][eng1k]) >= 2400).mean(), int(np.abs(T[j][eng1k]).max()), int(np.abs(r26[j][eng1k]).max())))
dtr = (T[1] - T[0]).astype(float)
P("b964 - V294 delivered torque on the SAME inputs (hands-off engaged): rms %.1f T, p99 |.| %.0f, max |.| %.0f" % (
    np.sqrt(np.mean(dtr[ho1k] ** 2)), np.percentile(np.abs(dtr[ho1k]), 99), np.abs(dtr[ho1k]).max()))
v1k = np.repeat(d["v"], 10)[:n]
for nm, lo, hi in PL.BANDS:
    mk = ho1k & (v1k >= lo) & (v1k < hi)
    if mk.sum() < 1000:
        continue
    tr0 = (T[0] - PL.march(d["sgn"], d["idx"], d["m"], PL.RC.v294_cells())[:n] if False else None)
    P("  band %-6s trim-diff rms %.1f T ; V294 |T| rms %.0f ; b964 C-bind %.4f %%" % (
        nm, np.sqrt(np.mean(dtr[mk] ** 2)), np.sqrt(np.mean(T[0][mk].astype(float) ** 2)), 100 * cb[1][mk].mean()))
out.close()
