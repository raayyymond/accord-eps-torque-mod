# -*- coding: utf-8 -*-
"""A5 -- crux verification + relaxed steady state + the stiffness that would null the effect."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
G = {t: A.grid(A.load(t)) for t in TAGS}

print("=" * 116)
print("A5a  CRUX CHECK on the wheel-speed instrument I used to arbitrate the gyro: does 0x1D0")
print("     reproduce vEgo?  If the decode is wrong, every wheel-speed conclusion above is void.")
print("=" * 116)
for t in TAGS:
    g = G[t]
    m = np.isfinite(g["v_ws"]) & (g["v"] > 5)
    r = g["v_ws"][m] / g["v"][m]
    print("   %-5s v_ws/vEgo  med %.4f  p1 %.4f p99 %.4f   corr %.6f" % (
        t, float(np.median(r)), float(np.percentile(r, 1)), float(np.percentile(r, 99)),
        float(np.corrcoef(g["v_ws"][m], g["v"][m])[0, 1])))

print()
print("=" * 116)
print("A5b  RELAXED STEADY STATE -- 0.6 s windows, |rate| < 25 deg/s, +/-25% flatness, engaged OR")
print("     manual.  Deliberately loosened to give the high-angle bins ANY steady support at all.")
print("=" * 116)
allrows = []
for t in TAGS:
    g = G[t]
    ok = (np.abs(g["rate"]) < 25) & (g["v"] > 3.0) & np.isfinite(g["denom"]) & g["calok"] & (np.abs(g["sa_deg"]) > 2)
    W = int(0.6 * A.FS)
    i = 0
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
            if np.ptp(sa) < 0.50 * abs(np.mean(sa)) and np.ptp(v) < 0.50 * abs(np.mean(v)) and abs(np.mean(sa)) > 2:
                r = float(np.mean(g["cfac"][sl] * g["sa"][sl]) / np.mean(g["denom"][sl]))
                allrows.append((t, float(np.mean(sa)), float(np.mean(v)), r, float(np.mean(g["eng"][sl]))))
                k += W
            else:
                k += 10
        i = j
R = np.array([[r[1], r[2], r[3], r[4]] for r in allrows])
tg = np.array([r[0] for r in allrows])
print("   total windows: %d" % len(R))
print("   %-10s %6s %8s %8s %8s %7s %7s" % ("|sa|", "n", "med sR", "p25", "p75", "med v", "eng"))
for lo, hi in ((2, 5), (5, 10), (10, 20), (20, 35), (35, 60), (60, 120), (120, 400)):
    m = (np.abs(R[:, 0]) >= lo) & (np.abs(R[:, 0]) < hi) & np.isfinite(R[:, 2]) & (R[:, 2] > 5) & (R[:, 2] < 40)
    if m.sum() < 3:
        print("   %-10s %6d  (too few)" % ("%d-%d" % (lo, hi), m.sum())); continue
    print("   %-10s %6d %8.2f %8.2f %8.2f %7.1f %7.2f" % (
        "%d-%d" % (lo, hi), m.sum(), float(np.median(R[m, 2])), float(np.percentile(R[m, 2], 25)),
        float(np.percentile(R[m, 2], 75)), float(np.median(R[m, 1])), float(np.mean(R[m, 3]))))
print()
print("   per-route, the two ends only:")
for t in TAGS:
    for lo, hi in ((2, 10), (35, 400)):
        m = (tg == t) & (np.abs(R[:, 0]) >= lo) & (np.abs(R[:, 0]) < hi) & (R[:, 2] > 5) & (R[:, 2] < 40)
        if m.sum() < 3:
            continue
        print("     %-5s |sa| %3d-%3d  n=%3d  med sR %6.2f  eng frac %.2f" % (
            t, lo, hi, m.sum(), float(np.median(R[m, 2])), float(np.mean(R[m, 3]))))

print()
print("=" * 116)
print("A5c  WHAT stiffnessFactor WOULD NULL THE EFFECT (F3)?  Re-run the whole table with the")
print("     carParams tyre stiffnesses scaled by k, pooled r62+r63.  openpilot's own valid band is")
print("     [0.2, 5.0]; it LEARNED 1.018 on r97 (the one route with auto-tune on).")
print("=" * 116)
print("   %-6s %s" % ("k", "".join("%10s" % b for b in ("2-5", "5-10", "10-20", "20-35", "35-120", "120-400"))))
for k in (0.35, 0.45, 0.6, 0.8, 1.0, 1.5):
    gs = [A.grid(A.load(t), stiff_scale=k) for t in ("r62", "r63")]
    P = {q: np.concatenate([g[q] for g in gs]) for q in ("denom", "cfac", "sa", "sa_deg", "v", "rate", "eng")}
    P["eng"] = P["eng"].astype(bool)
    row = []
    for lo, hi in ((2, 5), (5, 10), (10, 20), (20, 35), (35, 120), (120, 400)):
        m = (P["eng"] & (P["v"] > 4) & (np.abs(P["rate"]) < 20) & (np.abs(P["sa_deg"]) >= lo)
             & (np.abs(P["sa_deg"]) < hi) & np.isfinite(P["denom"]))
        s, _ = A.tls0(P["denom"][m], (P["cfac"] * P["sa"])[m]) if m.sum() >= 200 else (np.nan, 0)
        row.append(s)
    print("   %-6.2f %s" % (k, "".join("%10.2f" % x if np.isfinite(x) else "%10s" % "--" for x in row)))
