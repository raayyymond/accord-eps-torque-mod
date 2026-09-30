# -*- coding: utf-8 -*-
"""s2_idx_census.py -- where the r71b drive sits on the Kp / map X axis (the demand index), by speed band and by the
regime each complaint lives in.  Measured side only (the drive's own 0xE4 -> idx via the byte-exact demand chain in plib's
cache; hands-off laterally engaged chunks = the harness's route_chunks, and all engaged frames).
Also: how often a flat Kp multiple g would reach the P rail (idx >= 238/g) on this drive.
ANALYSIS ONLY."""
import os
import sys

import numpy as np

HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
import v295_harness as H  # noqa: E402


def main():
    d = H.route()
    ch = H.route_chunks()
    ho = np.zeros(len(d["t"]), bool)
    for a, b in ch:
        ho[a:b] = True
    eng = d["eng"]
    idx = d["idx"].astype(int)
    v = d["v"]
    plan = d["ctl_des_curv_f"] * v ** 2
    dpl = np.gradient(plan) * 100
    wire = d["e4_f"]
    print("frames: engaged %d, hands-off chunks %d (%.0f s)" % (eng.sum(), ho.sum(), ho.sum() / 100))
    print("check: harness idx vs wire/16.13 on hands-off frames: median |idx - |wire|/16.13| = %.2f" %
          np.median(np.abs(idx[ho] - np.abs(wire[ho]) / H.WIRE_PER_IDX)))
    for mnm, m in (("hands-off", ho), ("engaged", eng)):
        print("\n== %s ==" % mnm)
        print("band    sec   idx p10 p25 p50 p75 p90 p99 max | frac idx<3 <6 <12 <24 <32 | turn-hold idx p25/p50/p75 (n) | hard idx p50/p90")
        for nm, lo, hi in H.BANDS:
            mk = m & (v >= lo) & (v < hi)
            if mk.sum() < 100:
                continue
            q = np.percentile(idx[mk], [10, 25, 50, 75, 90, 99])
            fr = [np.mean(idx[mk] < t) for t in (3, 6, 12, 24, 32)]
            th = mk & (np.abs(plan) >= 0.8) & (np.abs(plan) < 1.5) & (np.abs(dpl) < 0.5)
            tq = np.percentile(idx[th], [25, 50, 75]) if th.sum() > 50 else [np.nan] * 3
            hard = mk & ((np.abs(plan) >= 1.5) | (np.abs(d["th"]) > 60))
            hq = np.percentile(idx[hard], [50, 90]) if hard.sum() > 50 else [np.nan] * 2
            print("%-6s %5.0f   %s %4d | %s | %s (%d) | %s" % (nm, mk.sum() / 100, " ".join("%3.0f" % x for x in q), idx[mk].max(),
                  " ".join("%.2f" % x for x in fr), "/".join("%.0f" % x for x in tq), th.sum(), "/".join("%.0f" % x for x in hq)))
        print("  P-rail reach on this drive for a flat multiple g (idx >= ceil(238/g)):")
        for g in (1.15, 1.3, 1.5, 1.75, 2.0):
            thr = int(np.ceil(238 / g))
            print("    g %.2f: rail from idx %d; frames at/above: %.3f %% (%d frames)" % (g, thr, 100 * np.mean(idx[m] >= thr), np.sum(idx[m] >= thr)))
    # the small-signal regime: |wire| < 100 counts (the metric's deficit band)
    for nm, lo, hi in H.BANDS:
        mk = ho & (v >= lo) & (v < hi)
        if mk.sum() < 100:
            continue
        print("  %-6s hands-off: frac |wire|<100 %.2f, <300 %.2f ; straight (|plan|<0.4) frac %.2f, idx p50 on straights %.0f" % (
            nm, np.mean(np.abs(wire[mk]) < 100), np.mean(np.abs(wire[mk]) < 300), np.mean(np.abs(plan[mk]) < 0.4),
            np.median(idx[mk & (np.abs(plan) < 0.4)]) if (mk & (np.abs(plan) < 0.4)).sum() > 50 else np.nan))


if __name__ == "__main__":
    main()
