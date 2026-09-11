# -*- coding: utf-8 -*-
"""A7 -- the curve I WOULD stand behind: steady-state frames only, pooled, all four estimators."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
FR = {k: [] for k in ("denom", "cfac", "sa", "sa_deg", "ang_rad", "v", "eng")}
EPI = []          # (tag, mean|sa|, dur_s)
for t in TAGS:
    g = A.grid(A.load(t))
    ok = (np.abs(g["rate"]) < 25) & (g["v"] > 3.0) & np.isfinite(g["denom"]) & g["calok"] & (np.abs(g["sa_deg"]) > 2)
    keep = np.zeros(len(ok), bool)
    W = int(0.6 * A.FS); i = 0
    while i < len(ok) - W:
        if not ok[i]:
            i += 1; continue
        j = i
        while j < len(ok) and ok[j]:
            j += 1
        k = i
        while k + W <= j:
            sl = slice(k, k + W)
            sa = g["sa_deg"][sl]; v = g["v"][sl]
            if np.ptp(sa) < 0.5 * abs(np.mean(sa)) and np.ptp(v) < 0.5 * abs(np.mean(v)) and abs(np.mean(sa)) > 2:
                keep[sl] = True
                EPI.append((t, abs(float(np.mean(sa))), 0.6))
                k += W
            else:
                k += 10
        i = j
    # merge contiguous kept samples into distinct episodes
    d = np.diff(keep.astype(int)); st = np.flatnonzero(d == 1) + 1; en = np.flatnonzero(d == -1) + 1
    if keep[0]: st = np.r_[0, st]
    if keep[-1]: en = np.r_[en, len(keep)]
    for a, b in zip(st, en):
        EPI.append((t + "#", float(np.mean(np.abs(g["sa_deg"][a:b]))), (b - a) / A.FS))
    for q in FR:
        FR[q].append(g[q][keep])
P = {q: np.concatenate(v) for q, v in FR.items()}
P["eng"] = P["eng"].astype(bool)
EP = [e for e in EPI if e[0].endswith("#")]

BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 60), (60, 120), (120, 400)]
print("=" * 128)
print("A7  THE CURVE I WOULD STAND BEHIND.  Steady-state frames ONLY (0.6 s windows, |rate|<25 deg/s,")
print("    |sa| and v flat within +/-25%), pooled r62+r63+r39+r35+r97, ENGAGED OR MANUAL.")
print("    free = joint free-intercept fit  radians(steeringAngleDeg_RAW) = sR*u + off,  u = denom/cfac")
print("           -> uses NO liveParameters.angleOffsetDeg at all.  off_fit is printed as the tell:")
print("           inside a narrow bin slope and intercept are collinear, so |off_fit| >> 1 deg means")
print("           the free fit is NOT identified in that bin and should be ignored there.")
print("=" * 128)
print("   %-9s %7s %6s %7s %6s | %7s %8s %9s %7s %8s | %s" % (
    "|sa| deg", "n(s)", "n_epi", "longest", "med v", "TLS0", "OLS y|x", "OLS x|y^-1", "free", "off_fit", "spread"))
for lo, hi in BINS:
    m = (np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi) & np.isfinite(P["denom"])
    eps = [e for e in EP if lo <= e[1] < hi]
    if m.sum() < 60:
        print("   %-9s %7.1f %6d %7s  -- insufficient --" % ("%d-%d" % (lo, hi), m.sum() / A.FS, len(eps),
              "%.2f" % max([e[2] for e in eps]) if eps else "-"))
        continue
    x = P["denom"][m]; y = (P["cfac"] * P["sa"])[m]
    s0, _ = A.tls0(x, y)
    s1, _, _ = A.ols_yx(x, y)
    s2, _, _ = A.ols_yx(y, x)
    sf_, off, _ = A.ols_yx((P["denom"] / P["cfac"])[m], P["ang_rad"][m], icpt=True)
    ests = [s0, s1, 1.0 / s2 if s2 else np.nan]
    spread = np.nanmax(ests) - np.nanmin(ests)
    print("   %-9s %7.1f %6d %7.2f %6.1f | %7.2f %8.2f %9.2f %7.2f %8.2f | %5.2f" % (
        "%d-%d" % (lo, hi), m.sum() / A.FS, len(eps), max([e[2] for e in eps]) if eps else 0,
        float(np.median(P["v"][m])), s0, s1, 1.0 / s2, sf_, np.degrees(off), spread))
print()
print("   engaged fraction per bin:", " ".join("%d-%d:%.2f" % (lo, hi, P["eng"][(np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi)].mean())
                                               for lo, hi in BINS if ((np.abs(P["sa_deg"]) >= lo) & (np.abs(P["sa_deg"]) < hi)).sum() > 60))
