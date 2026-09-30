# -*- coding: utf-8 -*-
"""ab8_identity_gate.py -- would the V294 flight attribution's C1 FF-IDENTITY read (v293_flight_read.identity_block,
|tap| vs surface(idx) x fade, NO trim term) misfire on the CORRECT candidate-A image?  Real r71b tap (V294) vs a
synthetic A tap (my byte-exact A march + the real r71b residual), same frames, same estimator.  ANALYSIS ONLY."""
import contextlib
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, KIT + "/analysis-2020accord/studies/v295/plant")
import plib as PL  # noqa: E402

src = open(os.path.join(HERE, "ab4_observe.py")).read().split("x_rp = d[\"x1k\"]")[0]
exec(src)                                             # d, sg, c294, cA, march(), quant()
T294 = march(c294, d["x1k"])
TA = march(cA, d["x1k"])
tt = d["tick_tap"]
resid = d["T_tap"] - quant(T294[tt])
synA = quant(TA[tt]) + resid

FR = PL._fr()
with contextlib.redirect_stdout(io.StringIO()):
    r = FR.load_route("r71b_v294", "V293")
g = r.g
n = len(d["t"])
t100 = g["t"][:n]
keep = (g["T_t"] > t100[0]) & (g["T_t"] < t100[-1])
assert keep.sum() == len(tt) and np.array_equal(g["T"][keep], d["T_tap"]), "frame alignment with plib"
c293 = FR.cells_for("V293")
c282 = FR.cells_for("V282")
for nm, series in (("V294 real tap", d["T_tap"]), ("candidate A synthetic tap", synA)):
    T_orig = g["T"].copy()
    g["T"] = T_orig.copy()
    g["T"][keep] = series
    with contextlib.redirect_stdout(io.StringIO()):
        ib = FR.identity_block(r, [("V293", c293), ("V282", c282)])
    g["T"] = T_orig
    row = ib["fits"]["V293/bar"]
    print("%-28s identity_block V293/bar: R2 %.4f resid %.1f counts lag %+d ms (V294 flight-read F1 line: FAIL if R2 < 0.90)"
          % (nm, row["r2"], row["resid"], row["lag_ms"]))
