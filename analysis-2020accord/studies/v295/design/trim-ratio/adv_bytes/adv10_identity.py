# -*- coding: utf-8 -*-
"""adv10_identity.py -- the design's wire read (1): "FF identity (v293_flight_read.identity_block, V293 cells) must stay
R2 >= 0.98 on all engaged frames and >= 0.997 at |acc| < 20 deg/s^2, because the surface is byte-identical.  Below 0.95
means a wrong image: stop."  The identity estimator has ZERO free parameters and NO trim term, so the trim is part of its
residual -- and b 964 makes the trim x1.7.  Does the CORRECT b 964 image still pass the pre-registered R2 >= 0.98?
Method: the real identity_block on the real r71b route object with r.g["T"] replaced by the fake b964 tap (real tap -
quant(V294 march) + quant(b964 march), the adversary mirror's march, bit-exact to plib), plus the |acc| split exactly as
r71b_attribution C1 does it.  Control row: the unmodified tap must reproduce 0.9868 / 0.9981."""
import contextlib
import io
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"), os.path.join(KIT, "rlog-tools", "studies", "grind"),
          os.path.join(KIT, "analysis-2020accord", "model"), os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant")):
    sys.path.insert(0, p)
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR
import r71b_cache as RC  # noqa: E402
import plib as P  # noqa: E402

d = P.load()
M = np.load(os.path.join(HERE, "_adv_march_r71b.npz"))
sg = int(M["sg"])
q567 = P.quant(sg * M["T567"][d["tick_tap"]])
q964 = P.quant(sg * M["T964"][d["tick_tap"]])
c293 = FR.cells_for("V293")
c294 = RC.v294_cells()


def lp1(xs, fc, fs=100.0):
    a = math.exp(-2 * math.pi * fc / fs)
    y = np.empty_like(xs)
    s = xs[0]
    for i, v in enumerate(xs):
        s = a * s + (1 - a) * v
        y[i] = s
    return y


def run(label, k=None):
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route("r71b_v294", "V293")
    g = r.g
    T = np.array(g["T"], float)
    tt = np.array(g["T_t"])
    # map plib's kept tap frames onto the route object's tap array (same timestamps)
    pos = np.searchsorted(tt, d["t_tap"])
    assert np.allclose(tt[pos], d["t_tap"]) and np.array_equal(T[pos], d["T_tap"].astype(float))
    if k is not None:
        T[pos] = T[pos] - q567 + q964 if k == 1.0 else (q964 + k * (T[pos] - q567))
    g["T"] = T
    with contextlib.redirect_stdout(io.StringIO()):
        ib = FR.identity_block(r, [("V293", c293)])
    best = ib["fits"]["V293/bar"]
    m100 = FR.fade_multiplier(c294, g["bar"], g["vego"], "bar")
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c294)
    idx100 = np.round(idx100)
    pred293, _ = FR.predict_tap(c293, idx100, sgn100, m100)
    j = np.searchsorted(g["t"], g["T_t"], side="right") - 1
    ok = (j >= 0) & (j < len(g["t"]))
    jj = np.clip(j + best["lag_frames"], 0, len(g["t"]) - 1)
    Racc = np.abs(np.gradient(lp1(np.nan_to_num(g["wire"]) / 8.0, 2.03)) * 100.0)
    sel_all = ok & g["eng"][jj]
    out = []
    for nm, thr in (("all engaged", 1e9), ("|acc|<20", 20)):
        sel = sel_all & (Racc[jj] < thr)
        y, yh = np.abs(g["T"][sel]), np.abs(pred293[jj[sel]])
        out.append("%s R2 %.4f (resid %.1f, n %d)" % (nm, FR.r2(y, yh), float(np.sqrt(np.mean((y - yh) ** 2))), sel.sum()))
    print("  %-30s best lag %+.0f ms | %s" % (label, best["lag_ms"], " | ".join(out)))


print("FF identity (identity_block, V293 cells, bar fade) on r71b:")
run("V294 real tap (control)")
run("b964 fake tap", 1.0)
run("b964 fake tap, residual x1.5", 1.5)
