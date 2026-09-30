"""b6_identity.py -- ADV-B step 6 (I5): the V294 attribution's FF identity (v293_flight_read.identity_block, V293
cells, |tap| vs surface(idx) x fade, ZERO free parameters, no trim term) run on:
  the REAL r71b tap (V294), a synthetic V295 tap (PA: tap + quant(L5) - quant(L4)), a stressed V295 tap (PB2:
  quant(L5 + 1.852*(tap_mid - L4)), the whole residual scaled with b), and the INVERTED-operand V295 tap (INV5).
Also the same identity restricted to frames where my V294 trim is small (|L4 - N4| < 8 counts), which is the
b-independent form of the gate.
Run: python b6_identity.py > b6_identity_out.txt
"""
import contextlib
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, KIT + "/rlog-tools/studies/grind")
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR  # noqa: E402


def quant(T):
    T = np.asarray(T, dtype=np.int64)
    return np.sign(T) * ((np.abs(T) >> 3) << 3)


M = dict(np.load(os.path.join(HERE, "_scratch", "marches_d+4_lin.npz")))
tt = np.clip(M["tap_tick"], 0, len(M["L4"]) - 1)
tap = M["tap_T"].astype(np.int64)
L4 = M["L4"].astype(np.int64)[tt]; L5 = M["L5"].astype(np.int64)[tt]; N4 = M["N4"].astype(np.int64)[tt]
I5 = M["I5"].astype(np.int64)[tt]
tap_mid = tap + 4 * np.sign(tap)
series = dict(NULL=tap, PA=tap + quant(L5) - quant(L4), PB2=quant(np.round(L5 + (1050 / 567) * (tap_mid - L4))),
              INV5=tap + quant(I5) - quant(L4))

with contextlib.redirect_stdout(io.StringIO()):
    r = FR.load_route("r71b_v294", "V293")
g = r.g
tt_k = g["T_t"]
assert len(tt_k) == len(M["tap_t"]), "frame count differs"
pick = np.arange(len(tt_k))
dtt = (tt_k - M["tap_t"]) * 1000
print("kit tap frames %d == my tap frames %d ; kit (dejittered) minus raw time: median %+.2f ms, p1 %+.2f p99 %+.2f ;"
      " equal tap values by index: %.5f" % (len(tt_k), len(M["tap_t"]), np.median(dtt), np.percentile(dtt, 1),
                                           np.percentile(dtt, 99), np.mean(g["T"] == tap)))
assert np.mean(g["T"] == tap) > 0.9999
small_trim = np.abs(L4 - N4)[pick] < 8
c293 = FR.cells_for("V293")
c282 = FR.cells_for("V282")
T_orig = g["T"].copy()
for nm, s in series.items():
    for sub_nm, mask in (("all engaged", None), ("|V294 trim| < 8 counts", small_trim)):
        g["T"] = s[pick].astype(float).copy()
        if mask is not None:
            # frames outside the mask are removed from the estimator by setting them outside engagement:
            # identity_block selects ok & eng; we zero-weight by replacing the tap time with NaN-free exclusion
            keep_t = g["T_t"]
            g["T_t"] = keep_t[mask]
            g["T"] = g["T"][mask]
        with contextlib.redirect_stdout(io.StringIO()):
            ib = FR.identity_block(r, [("V293", c293), ("V282", c282)])
        if mask is not None:
            g["T_t"] = keep_t
        row = ib["fits"]["V293/bar"]; row2 = ib["fits"]["V282/bar"]
        print("%-5s %-24s identity V293/bar R2 %.4f resid %.1f lag %+d ms n %d | V282 cells R2 %.3f"
              % (nm, sub_nm, row["r2"], row["resid"], row["lag_ms"], row["n"], row2["r2"]))
g["T"] = T_orig
