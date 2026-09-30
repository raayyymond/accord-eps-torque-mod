# -*- coding: utf-8 -*-
"""adv7_band_scatter.py -- can ONE short symptomatic drive measure the design's EFFECT sentences?  The null sentences
(a)/(b) hinge on "matched-cell hard-turn 1.6-3 Hz wheel rate down >= 20 % vs r71b" vs "moved <= 10 %".  This measures the
within-drive scatter of that statistic (harness drive_metrics' hard16 definition: 1.6-3 Hz band-passed 0x18F wheel rate,
rms over frames with |la_plan| >= 1.5 m/s^2 or |angle| > 60 deg) on r71b's own hard-turn episodes, per speed band, and the
CI of the ratio a 15 s / 30 s / 60 s-of-hard-frames drive would read against r71b's whole-drive value if NOTHING changed.
Measured side only (no simulation)."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import v295_harness as H  # noqa: E402

d = H.route()
n = len(d["t"])
eng = d["eng"] & (d["cc_lat_active_f"] > 0.5)
v = d["v"]
rate = d["x18_f"] / 8.0
plan = d["ctl_des_curv_f"] * v ** 2
ang = d["th"]
bp = H._bp(np.nan_to_num(rate), 1.6, 3.0)
hard = eng & ((np.abs(plan) >= 1.5) | (np.abs(ang) > 60))
import plib as P  # noqa: E402

rng = np.random.default_rng(3)
print("r71b: engaged %.0f s ; hard frames %.0f s" % (eng.sum() / 100, hard.sum() / 100))
for nm, lo, hi in H.BANDS:
    mk = hard & (v >= lo) & (v < hi)
    eps = [(a, b) for a, b in P.runs(mk, 20)]           # hard episodes >= 0.2 s
    if not eps:
        print("  %-6s no hard episodes" % nm)
        continue
    whole = np.sqrt(np.mean(bp[mk] ** 2))
    per = np.array([np.sqrt(np.mean(bp[a:b] ** 2)) for a, b in eps])
    dur = np.array([(b - a) / 100 for a, b in eps])
    line = "  %-6s hard %5.1f s in %3d episodes (median %.1f s) | whole-drive hard16 %.2f deg/s | per-episode CV %.2f" % (
        nm, mk.sum() / 100, len(eps), np.median(dur), whole, np.std(per) / np.mean(per))
    # resample episodes until S seconds of hard frames: the ratio a new drive of that exposure reads vs the whole drive
    for S in (15.0, 30.0, 60.0):
        if mk.sum() / 100 < S:
            line += " | %2.0fs: n/a" % S
            continue
        rs = []
        for _ in range(2000):
            acc, tot = 0.0, 0.0
            while tot < S:
                k = rng.integers(0, len(eps))
                a, b = eps[k]
                acc += np.sum(bp[a:b] ** 2)
                tot += (b - a) / 100
            rs.append(np.sqrt(acc / (tot * 100)) / whole)
        rs = np.array(rs)
        line += " | %2.0fs: 5-95%% [%.2f, %.2f]" % (S, np.percentile(rs, 5), np.percentile(rs, 95))
    print(line)
