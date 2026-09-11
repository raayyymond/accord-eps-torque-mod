# -*- coding: utf-8 -*-
"""A2 -- the angle-offset circularity test (FAIL criteria F1, F2, F8).

If a residual angle-offset error d remains after subtracting liveParameters.angleOffsetDeg, then
the frame-wise truth is  sa_true = sa_used + d, so the instrument measures
    sR_meas = sR_true * (1 + d / <sa>)
which (a) INFLATES at small |sa| and vanishes at large |sa| -- the claimed shape exactly, and
(b) moves in OPPOSITE directions for left and right turns.  Splitting by sign therefore both
detects d and SOLVES for it:
    sR+ = sR_true*(1 + d/<sa>+),  sR- = sR_true*(1 + d/<sa>-)   (<sa>- negative)
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 75), (75, 120), (120, 400)]
G = {t: A.grid(A.load(t)) for t in TAGS}


def gate(g, lo, hi, off_key="aoff", dperturb=0.0, eng=True):
    sa_deg = g["ang"] - g[off_key] - dperturb
    m = ((g["eng"] if eng else g["man"]) & (g["v"] > 4.0) & (np.abs(g["rate"]) < 20.0)
         & (np.abs(sa_deg) >= lo) & (np.abs(sa_deg) < hi) & np.isfinite(g["denom"]))
    return m, sa_deg


print("=" * 122)
print("A2a  SIGN-SPLIT.  sR fitted on LEFT-turn frames and RIGHT-turn frames separately, same bin.")
print("     A real rack property is sign-symmetric.  A residual angle offset d splits them, by d/<sa>.")
print("     d_implied solves the two equations; it is the offset error in DEGREES still in the data.")
print("=" * 122)
print("   %-5s %-8s %8s %8s %8s %8s %9s %9s %9s" % ("route", "|sa|", "n+(s)", "n-(s)", "sR+", "sR-", "split", "d_impl", "sR_true"))
for t in TAGS:
    g = G[t]
    for lo, hi in BINS:
        m, sa_deg = gate(g, lo, hi)
        sa = np.radians(sa_deg)
        for_ = m & (sa_deg > 0); rev = m & (sa_deg < 0)
        if for_.sum() < 300 or rev.sum() < 300:
            continue
        sp, _ = A.tls0(g["denom"][for_], g["cfac"][for_] * sa[for_])
        sm, _ = A.tls0(g["denom"][rev], g["cfac"][rev] * sa[rev])
        ap = float(np.mean(sa_deg[for_])); am = float(np.mean(sa_deg[rev]))
        # sR+ = S*(1+d/ap) ; sR- = S*(1+d/am)  ->  solve
        den = (sp / ap) - (sm / am)
        if abs(den) < 1e-12:
            continue
        d = (sm - sp) / den * -1.0
        d = (sp - sm) / ((sp / ap) - (sm / am)) if abs((sp / ap) - (sm / am)) > 1e-12 else np.nan
        S = sp / (1 + d / ap)
        print("   %-5s %-8s %8.0f %8.0f %8.2f %8.2f %9.2f %9.3f %9.2f" % (
            t, "%d-%d" % (lo, hi), for_.sum() / A.FS, rev.sum() / A.FS, sp, sm, sp - sm, d, S))
    print()

print("=" * 122)
print("A2b  FREE-INTERCEPT JOINT FIT -- no paramsd offset used at all.")
print("     Model:  radians(steeringAngleDeg_RAW) = sR * u + offset_rad,   u = denom / cfac")
print("     This estimates sR and the TRUE offset JOINTLY from the same data the instrument uses,")
print("     with NO input from the Kalman filter that co-estimates offset with a steer ratio.")
print("=" * 122)
print("   %-5s %-14s %8s %9s %9s %9s %10s" % ("route", "band", "n(s)", "sR_free", "off_fit", "off_paramsd", "sR_TLS0"))
for t in TAGS:
    g = G[t]
    u = g["denom"] / g["cfac"]
    for lbl, lo, hi in (("|sa| 2-10", 2, 10), ("|sa| 2-35", 2, 35), ("|sa| 2-400", 2, 400),
                        ("|sa| 10-400", 10, 400), ("|sa| 35-400", 35, 400)):
        m, sa_deg = gate(g, lo, hi)
        if m.sum() < 500:
            continue
        s_free, off, n = A.ols_yx(u[m], g["ang_rad"][m], icpt=True)
        s_tls, _ = A.tls0(g["denom"][m], g["cfac"][m] * np.radians(sa_deg[m]))
        print("   %-5s %-14s %8.0f %9.2f %9.3f %9.3f %10.2f" % (
            t, lbl, n / A.FS, s_free, np.degrees(off), float(np.mean(g["aoff"][m])), s_tls))
    print()

print("=" * 122)
print("A2c  PERTURBATION.  Re-run the instrument with the paramsd offset shifted by +/- d.")
print("     d = 0.25 deg is well inside the filter's own spread (angleOffsetDeg sd was 0.18-0.85 deg).")
print("=" * 122)
for t in ("r62", "r63"):
    g = G[t]
    print("   %s" % t)
    print("     %-9s %8s %8s %8s %8s %8s" % ("|sa|", "d=-0.50", "d=-0.25", "d=0", "d=+0.25", "d=+0.50"))
    for lo, hi in BINS:
        row = []
        for d in (-0.5, -0.25, 0.0, 0.25, 0.5):
            m, sa_deg = gate(g, lo, hi, dperturb=d)
            if m.sum() < 200:
                row.append(np.nan); continue
            s, _ = A.tls0(g["denom"][m], g["cfac"][m] * np.radians(sa_deg[m]))
            row.append(s)
        if not np.any(np.isfinite(row)):
            continue
        print("     %-9s %s" % ("%d-%d" % (lo, hi), "".join("%8.2f" % x if np.isfinite(x) else "%8s" % "--" for x in row)))
    print()

print("=" * 122)
print("A2d  angleOffsetAverageDeg (slow state only, no fast term) instead of angleOffsetDeg")
print("=" * 122)
print("   %-5s %-9s %8s %8s %8s" % ("route", "|sa|", "sR(aoff)", "sR(avg)", "delta"))
for t in TAGS:
    g = G[t]
    for lo, hi in BINS:
        m1, s1d = gate(g, lo, hi, "aoff"); m2, s2d = gate(g, lo, hi, "aoffavg")
        if m1.sum() < 200 or m2.sum() < 200:
            continue
        a, _ = A.tls0(g["denom"][m1], g["cfac"][m1] * np.radians(s1d[m1]))
        b, _ = A.tls0(g["denom"][m2], g["cfac"][m2] * np.radians(s2d[m2]))
        print("   %-5s %-9s %8.2f %8.2f %8.2f" % (t, "%d-%d" % (lo, hi), a, b, b - a))
    print()
