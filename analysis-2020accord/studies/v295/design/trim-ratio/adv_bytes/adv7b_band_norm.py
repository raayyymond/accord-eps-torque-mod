# adv7b_band_norm.py -- same resampling as adv7, for an EXCITATION-NORMALISED jerk statistic: rms(1.6-3 Hz wheel rate) /
# rms(1.6-3 Hz 0xE4 command) over the same hard frames, and the trim's own share rms(1.6-3 Hz T_trim)/rms(1.6-3 Hz T_null).
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import v295_harness as H
import plib as P
d = H.route()
eng = d["eng"] & (d["cc_lat_active_f"] > 0.5)
v = d["v"]; plan = d["ctl_des_curv_f"] * v ** 2
hard = eng & ((np.abs(plan) >= 1.5) | (np.abs(d["th"]) > 60))
br = H._bp(np.nan_to_num(d["x18_f"] / 8.0), 1.6, 3.0)
bc = H._bp(np.nan_to_num(d["e4_f"].astype(float)), 1.6, 3.0)
rng = np.random.default_rng(5)
for nm, lo, hi in H.BANDS[1:2] + H.BANDS[3:4]:
    mk = hard & (v >= lo) & (v < hi)
    eps = P.runs(mk, 20)
    whole = np.sqrt(np.sum(br[mk] ** 2) / np.sum(bc[mk] ** 2))
    line = "  %-6s rate/cmd (deg/s per wire count, 1.6-3 Hz) whole %.4f" % (nm, whole)
    for S in (15.0, 30.0):
        if mk.sum() / 100 < S:
            line += " | %2.0fs n/a" % S; continue
        rs = []
        for _ in range(2000):
            ar = ac = tot = 0.0
            while tot < S:
                a, b = eps[rng.integers(0, len(eps))]
                ar += np.sum(br[a:b] ** 2); ac += np.sum(bc[a:b] ** 2); tot += (b - a) / 100
            rs.append(np.sqrt(ar / ac) / whole)
        line += " | %2.0fs: no-change ratio 5-95%% [%.2f, %.2f]" % (S, np.percentile(rs, 5), np.percentile(rs, 95))
    print(line)
