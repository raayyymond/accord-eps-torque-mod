# -*- coding: utf-8 -*-
"""A0 -- channel verification + reproduction of the claimed table from MY OWN extraction."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 75), (75, 120), (120, 400)]

print("=" * 110)
print("A0  CHANNEL CENSUS (my own extraction, independent of the optune cache)")
print("=" * 110)
G = {}
for t in TAGS:
    D = A.load(t)
    g = A.grid(D)
    G[t] = g
    dur = g["n"] / A.FS
    print("%-4s  %6.0f s  cs=%d lp=%d cal=%d lpar=%d  0x1D0=%s  CP.sR=%.2f sf=%.3e" % (
        t, dur, len(D["cs_t"]), len(D["lp_t"]), len(D["cal_t"]), len(D["lpar_t"]),
        "yes" if "yaw_ws" in g else "NO", D["cp"]["steerRatio"], g["sf"]))
    print("      calok %.1f%%  wvalid %.1f%%  posenetOK %.1f%%  lpar_valid %.1f%%  eng %.0f s  man %.0f s" % (
        100 * g["calok"].mean(), 100 * g["wvalid"].mean(), 100 * g["posenetOK"].mean(),
        100 * g["lpar_valid"].mean(), g["eng"].sum() / A.FS, g["man"].sum() / A.FS))
    print("      lpar.steerRatio  med %.3f  min %.3f max %.3f   stiffFactor med %.3f" % (
        np.nanmedian(g["lpar_sr"]), np.nanmin(g["lpar_sr"]), np.nanmax(g["lpar_sr"]), np.nanmedian(g["lpar_stiff"])))
    print("      angleOffsetDeg   med %+.3f  p5 %+.3f p95 %+.3f  sd %.3f   |aoff-aoffavg| med %.3f" % (
        np.nanmedian(g["aoff"]), np.nanpercentile(g["aoff"], 5), np.nanpercentile(g["aoff"], 95),
        np.nanstd(g["aoff"]), np.nanmedian(np.abs(g["aoff"] - g["aoffavg"]))))
    print("      carState.yawRate all-zero? %s" % (np.all(D["cs_yawrate_DEAD"] == 0)))

print()
print("=" * 110)
print("A1  REPRODUCTION of the claimed table (instrument as written: TLS through origin, aoff subtracted)")
print("    gate: engaged, not pressed, calibrated, v>4, |rate|<20, |sa|>2")
print("=" * 110)
print("   %-5s %-9s %7s %8s %8s %8s %8s" % ("route", "|sa|", "n(s)", "sR_TLS0", "n+", "n-", "imbal"))
for t in TAGS:
    g = G[t]
    for lo, hi in BINS:
        ok = (g["eng"] & (g["v"] > 4.0) & (np.abs(g["rate"]) < 20.0)
              & (np.abs(g["sa_deg"]) >= lo) & (np.abs(g["sa_deg"]) < hi) & np.isfinite(g["denom"]))
        if ok.sum() < 200:
            continue
        s, n = A.tls0(g["denom"][ok], g["cfac"][ok] * g["sa"][ok])
        npos = int((g["sa_deg"][ok] > 0).sum()); nneg = int((g["sa_deg"][ok] < 0).sum())
        imb = abs(npos - nneg) / max(npos + nneg, 1)
        print("   %-5s %-9s %7.0f %8.2f %8d %8d %8.2f" % (t, "%d-%d" % (lo, hi), n / A.FS, s, npos, nneg, imb))
    print()
