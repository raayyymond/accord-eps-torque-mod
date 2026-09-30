# -*- coding: utf-8 -*-
"""a4 -- where r71b (V294) actually sat: |angle|, idx, lat accel by speed band and regime, hands-off engaged.
Uses the harness's route() arrays (the kit's byte-exact march grid; data only)."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H  # noqa: E402

d = H.route()
th, v, idx, eng, ho = d["th"], d["v"], d["idx"], d["eng"], d["ho"]
la = d["ctl_la_des"]
m = eng & ho & np.isfinite(th) & np.isfinite(v)
out = open(os.path.join(HERE, "a4_oppoints_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


P("hands-off engaged frames: %d (%.0f s)" % (m.sum(), m.sum() / 100))
for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 22), (22, 99)):
    b = m & (v >= lo) & (v < hi)
    if b.sum() < 50:
        continue
    a = np.abs(th[b])
    ii = idx[b]
    lab = np.abs(la[b])
    P("v %2d-%2d: n %6d | |angle| p50 %.1f p90 %.1f p99 %.1f deg | idx p50 %.0f p90 %.0f p99 %.0f max %.0f | |la_des| p50 %.2f p90 %.2f" % (
        lo, hi, b.sum(), *np.percentile(a, [50, 90, 99]), *np.percentile(ii, [50, 90, 99]), ii.max(), *np.percentile(lab, [50, 90])))
    for ilo, ihi in ((0, 9), (9, 30), (30, 60), (60, 100), (100, 241)):
        c = b & (idx >= ilo) & (idx < ihi)
        if c.sum() < 20:
            continue
        P("      idx %3d-%3d: %5.1f %% of band, |angle| p50 %.1f p90 %.1f ; secant T/|angle| is lane-surface based below" % (
            ilo, ihi, 100.0 * c.sum() / b.sum(), *np.percentile(np.abs(th[c]), [50, 90])))
# sustained curves at speed: |la_des| > 1.0 for >= 5 s runs, v > 15
P("\nsustained curves (|la_des| > 1.0 m/s^2) by speed: angle and idx")
for lo, hi in ((15, 19), (19, 22), (22, 99)):
    c = m & (v >= lo) & (v < hi) & (np.abs(la) > 1.0)
    if c.sum() < 20:
        P("  v %d-%d: n %d (too few)" % (lo, hi, c.sum()))
        continue
    P("  v %d-%d: n %d (%.0f s) |angle| p10 %.1f p50 %.1f p90 %.1f ; idx p10 %.0f p50 %.0f p90 %.0f" % (
        lo, hi, c.sum(), c.sum() / 100, *np.percentile(np.abs(th[c]), [10, 50, 90]), *np.percentile(idx[c], [10, 50, 90])))
out.close()
