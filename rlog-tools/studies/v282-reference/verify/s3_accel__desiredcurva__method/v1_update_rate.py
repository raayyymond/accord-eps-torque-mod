"""ADVERSARIAL CHECK: is desiredCurvature a native-100Hz-updating signal, or a held/stepped signal whose
sample-to-sample update RATE differs between fork versions? If torque-mode routes update cs_des_curv less
often (bigger hold steps) than V282 routes, differentiating it will inject an ARTIFACT of elevated 1-3 Hz
"rate" power that has nothing to do with a physical planner-in-the-loop effect. This would undercut the
finding's magnitude claim, not just its causal ("planner in the loop") reading.

Method: per route, restrict to the same usable mask as s3_refloop.py (active & ~pressed & 2.5<=v<8),
count the fraction of consecutive controlsState ticks where desiredCurvature changed at all (any float
delta), the fraction where it changed by more than a small threshold, and the median/most-common inter-
update gap in samples (a stepped signal held at 20 Hz on a 100 Hz clock would show ~5-sample gaps).
"""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V

print(f"{'route':24s} {'group':7s} {'n_us':>6s} {'frac_any_chg':>12s} {'frac_chg>1e-6':>13s} {'med_gap':>7s} {'p90_gap':>7s}")
for rk in V.ROUTES:
    S = V.load(rk)
    u = V.usable(S, 2.5, 8.0)
    k = np.nan_to_num(S["model"]) / np.maximum(np.nan_to_num(S["v"]), 0.5) ** 2  # raw desired curvature, 1/m
    if u.sum() < 200:
        print(f"{rk:24s} {S['meta'].get('group','?'):7s}  (too little usable data: {u.sum()})")
        continue
    # look only within contiguous usable runs so a mask edge doesn't fake a "gap"
    gaps = []
    n_any = 0; n_big = 0; n_tot = 0
    for a, b in V.runs(u, S["t"], min_s=2.0):
        kk = k[a:b]
        d = np.diff(kk)
        n_any += int(np.sum(d != 0.0))
        n_big += int(np.sum(np.abs(d) > 1e-6))
        n_tot += len(d)
        chg_idx = np.where(d != 0.0)[0]
        if len(chg_idx) > 1:
            gaps.append(np.diff(chg_idx))
    if n_tot == 0:
        print(f"{rk:24s} {S['meta'].get('group','?'):7s}  (no runs >=2s)")
        continue
    allgaps = np.concatenate(gaps) if gaps else np.array([np.nan])
    print(f"{rk:24s} {S['meta'].get('group','?'):7s} {n_tot:6d} {n_any/n_tot:12.3f} {n_big/n_tot:13.3f} "
          f"{np.nanmedian(allgaps):7.1f} {np.nanpercentile(allgaps,90):7.1f}")
    del S
