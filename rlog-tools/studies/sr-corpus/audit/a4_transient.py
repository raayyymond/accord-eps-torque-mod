# -*- coding: utf-8 -*-
"""A4 -- F6 (transient/lag), F3 (bicycle model leverage), F8 (estimator/binning)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
G = {t: A.grid(A.load(t)) for t in TAGS}


def shift(x, k):
    """x advanced by k samples (k>0 = take yaw from k samples LATER)."""
    out = np.full_like(x, np.nan)
    if k == 0:
        return x.copy()
    if k > 0:
        out[:-k] = x[k:]
    else:
        out[-k:] = x[:k]
    return out


print("=" * 120)
print("A4a  |sa| DISTRIBUTION inside the load-bearing bins, and the cfac leverage there.")
print("     cfac = 1/(1 - sf v^2)/L.  If cfac is ~1/L at these speeds, the bicycle-model tyre")
print("     stiffnesses (F3) have NO leverage on the high-angle number and cannot explain it.")
print("=" * 120)
for t in TAGS:
    g = G[t]
    for lo, hi in ((2, 5), (50, 400), (120, 400)):
        m = (g["eng"] & (g["v"] > 4) & (np.abs(g["rate"]) < 20) & (np.abs(g["sa_deg"]) >= lo)
             & (np.abs(g["sa_deg"]) < hi) & np.isfinite(g["denom"]))
        if m.sum() < 100:
            continue
        cf = g["cfac"][m] * g["L"]
        print("   %-5s |sa| %3d-%3d  n=%5.1fs  med|sa| %6.1f deg  med v %5.1f  cfac*L: med %.4f  (1.0 = pure kinematic)"
              % (t, lo, hi, m.sum() / A.FS, float(np.median(np.abs(g["sa_deg"][m]))), float(np.median(g["v"][m])), float(np.median(cf))))

print()
print("=" * 120)
print("A4b  LEAD / LAG SWEEP (F5, F6).  Re-measure with the yaw channel shifted +/- up to 300 ms.")
print("     The high-angle bins are 0.2-0.9 s transits; a slope built on transits is exquisitely")
print("     sensitive to alignment.  A bin whose sR moves a lot with lag is NOT a static measurement.")
print("=" * 120)
LAGS = [-30, -20, -10, -5, 0, 5, 10, 20, 30]
print("   %-5s %-9s %s" % ("route", "|sa|", "".join("%8s" % ("%+dms" % (k * 10)) for k in LAGS)))
for t in TAGS:
    g = G[t]
    for lo, hi in ((2, 5), (5, 10), (10, 35), (35, 120), (120, 400)):
        row = []
        for k in LAGS:
            yk = shift(g["yaw_cal"], k)
            den = (-yk / np.maximum(g["v"], 1e-3)) - g["rollc"]
            m = (g["eng"] & (g["v"] > 4) & (np.abs(g["rate"]) < 20) & (np.abs(g["sa_deg"]) >= lo)
                 & (np.abs(g["sa_deg"]) < hi) & np.isfinite(den))
            if m.sum() < 200:
                row.append(np.nan); continue
            s, _ = A.tls0(den[m], g["cfac"][m] * g["sa"][m])
            row.append(s)
        if not np.any(np.isfinite(row)):
            continue
        print("   %-5s %-9s %s" % (t, "%d-%d" % (lo, hi), "".join("%8.2f" % x if np.isfinite(x) else "%8s" % "--" for x in row)))
    print()

print("=" * 120)
print("A4c  STEADY-STATE SEARCH (F6).  Every window in the corpus -- ENGAGED OR MANUAL, no engagement")
print("     gate at all -- where |sa| stays inside +/-15% of its mean, v inside +/-15%, |rate| < 15 deg/s,")
print("     for at least 1.0 s.  This is the only frame in which 'the rack quickens' is separable from")
print("     'the yaw lags the wheel'.  One row per window, ratio = cfac*sa / (yaw/v) at the window mean.")
print("=" * 120)
rows = []
for t in TAGS:
    g = G[t]
    ok = (np.abs(g["rate"]) < 15) & (g["v"] > 3.0) & np.isfinite(g["denom"]) & g["calok"] & (np.abs(g["sa_deg"]) > 2)
    W = int(1.0 * A.FS)
    i = 0
    while i < len(ok) - W:
        if not ok[i]:
            i += 1; continue
        j = i
        while j < len(ok) and ok[j]:
            j += 1
        if j - i >= W:
            # slide sub-windows
            k = i
            while k + W <= j:
                sl = slice(k, k + W)
                sa = g["sa_deg"][sl]; v = g["v"][sl]
                if (np.ptp(sa) < 0.30 * abs(np.mean(sa))) and (np.ptp(v) < 0.30 * abs(np.mean(v))) and abs(np.mean(sa)) > 2:
                    r = float(np.mean(g["cfac"][sl] * g["sa"][sl]) / np.mean(g["denom"][sl]))
                    rows.append((t, float(np.mean(sa)), float(np.mean(v)), r,
                                 float(np.mean(g["eng"][sl])), (k + W / 2) / A.FS))
                    k += W
                else:
                    k += 10
        i = j
rows = np.array([(r[1], r[2], r[3], r[4]) for r in rows]) if rows else np.zeros((0, 4))
tagsr = [r[0] for r in []]
print("   total steady windows found: %d" % len(rows))
if len(rows):
    for lo, hi in ((2, 5), (5, 10), (10, 20), (20, 35), (35, 60), (60, 120), (120, 400)):
        m = (np.abs(rows[:, 0]) >= lo) & (np.abs(rows[:, 0]) < hi) & np.isfinite(rows[:, 2])
        m &= (rows[:, 2] > 5) & (rows[:, 2] < 40)
        if m.sum() < 3:
            print("   |sa| %3d-%3d : n=%3d   (too few)" % (lo, hi, m.sum()))
            continue
        print("   |sa| %3d-%3d : n=%3d windows  med sR %6.2f  [p25 %5.2f p75 %5.2f]  med v %5.1f  eng frac %.2f"
              % (lo, hi, m.sum(), float(np.median(rows[m, 2])), float(np.percentile(rows[m, 2], 25)),
                 float(np.percentile(rows[m, 2], 75)), float(np.median(rows[m, 1])), float(np.mean(rows[m, 3]))))

print()
print("=" * 120)
print("A4d  ESTIMATOR CHOICE (F8), pooled r62+r63, same gate.  TLS0 vs OLS both ways.")
print("=" * 120)
gs = [G["r62"], G["r63"]]
P = {k: np.concatenate([g[k] for g in gs]) for k in ("denom", "cfac", "sa", "sa_deg", "v", "rate", "eng")}
P["eng"] = P["eng"].astype(bool)
print("   %-9s %8s %9s %9s %9s" % ("|sa|", "n(s)", "TLS0", "OLS y|x", "OLS x|y^-1"))
for lo, hi in ((2, 5), (5, 10), (10, 20), (20, 35), (35, 120), (120, 400)):
    m = (P["eng"] & (P["v"] > 4) & (np.abs(P["rate"]) < 20) & (np.abs(P["sa_deg"]) >= lo)
         & (np.abs(P["sa_deg"]) < hi) & np.isfinite(P["denom"]))
    if m.sum() < 200:
        continue
    x = P["denom"][m]; y = (P["cfac"] * P["sa"])[m]
    s0, _ = A.tls0(x, y)
    s1, _, _ = A.ols_yx(x, y)
    s2, _, _ = A.ols_yx(y, x)
    print("   %-9s %8.0f %9.2f %9.2f %9.2f" % ("%d-%d" % (lo, hi), m.sum() / A.FS, s0, s1, 1.0 / s2 if s2 else np.nan))
