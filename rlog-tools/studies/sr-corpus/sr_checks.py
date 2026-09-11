# -*- coding: utf-8 -*-
"""sr_checks.py -- the three things sr_analyze.py's first pass got wrong or left open.

C1  ROUTE-LEVEL BOOTSTRAP.  sr_analyze resamples 2 s blocks, which captures WITHIN-route
    autocorrelation but NOT the between-route random effect -- and section 8 measured that
    effect at sd 0.69 in the 2-12 deg band against a 0.17 pooled CI.  Resample ROUTES.

C2  ERROR-MODEL BRACKET.  TLS sits between OLS(y|x) and 1/OLS(x|y).  When the bracket is wide
    the slope is NOT identified by the data and any TLS number is an assumption about the noise
    ratio, not a measurement.  This is the direct test of whether the low-|sa| bins mean anything.

C3  PER-ROUTE FREE-OFFSET GUARD.  angleOffsetDeg runs -9.4 .. +4.7 across the corpus, so a single
    global free offset (what the first pass fitted) cannot represent it.  Fit the offset PER ROUTE
    with a 3-var TLS and rebuild sa from it, using NOTHING from liveParameters.angleOffsetDeg.

C4  REGRESSION TEST against the orchestrator's r62/r63 rows.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sr_lib import tls_origin, tls_origin_gram, tls_free, block_grams, FS  # noqa: E402
from sr_routes import BUILD, arm  # noqa: E402
from sr_analyze import Pool, BINS, served  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = []


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def boot_ci(x, y, clus, nboot=600, seed=1):
    """cluster bootstrap over whatever `clus` is (2 s block, or route)."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    a, b, c, _ = block_grams(x, y, clus)
    nb = len(a)
    if nb < 5:
        return np.nan, np.nan, nb
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nb, size=(nboot, nb))
    out = tls_origin_gram(a[pick].sum(1), b[pick].sum(1), c[pick].sum(1))
    out = out[np.isfinite(out)]
    if len(out) < 20:
        return np.nan, np.nan, nb
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), nb


def bracket(x, y):
    """OLS(y|x) and 1/OLS(x|y), both through the origin.  TLS lies between them."""
    sxx = float(x @ x); sxy = float(x @ y); syy = float(y @ y)
    lo = sxy / sxx if sxx > 0 else np.nan          # y = lo * x
    hi = syy / sxy if sxy != 0 else np.nan         # x = (1/hi) * y
    return lo, hi


def main():
    P = Pool(os.path.join(HERE, "_scratch", "pooled.npz"))

    pr("=" * 128)
    pr("C1 + C2   THE HONEST CI: ROUTE-LEVEL BOOTSTRAP, BESIDE THE ERROR-MODEL BRACKET")
    pr("=" * 128)
    pr("   block CI  = resample 2 s blocks   (within-route autocorrelation only -- what the first pass reported)")
    pr("   route CI  = resample ROUTES       (adds the between-route random effect; this is the honest one)")
    pr("   bracket   = [OLS(y|x), 1/OLS(x|y)]; TLS lies between.  WIDE bracket => the slope is NOT")
    pr("               identified by the data and the TLS number is an assumption about the noise ratio.")
    pr("")
    pr("   %-10s %8s %7s %8s %-16s %-16s %-20s %6s" %
       ("|sa| deg", "n(s)", "sR", "map", "block CI", "route CI", "bracket [OLS, 1/OLS]", "routes"))
    rows = []
    for lo, hi in BINS:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        n = int(ok.sum())
        if n < 200:
            continue
        x, y = P.denom[ok], P.y[ok]
        s = tls_origin(x, y)
        blo, bhi, _ = boot_ci(x, y, P.blk[ok])
        rlo, rhi, nr = boot_ci(x, y, P.ri[ok])
        o1, o2 = bracket(x, y)
        rows.append((lo, hi, n / FS, s, blo, bhi, rlo, rhi, o1, o2, nr))
        pr("   %-10s %8.0f %7.2f %8.2f  [%5.2f,%5.2f]   [%5.2f,%5.2f]   [%5.2f, %5.2f]%s %6d"
           % ("%d-%d" % (lo, hi), n / FS, s, served((lo + hi) / 2), blo, bhi, rlo, rhi, o1, o2,
              "  WIDE" if (o2 - o1) > 1.0 else "      ", nr))
    pr("")
    pr("   READ: the bracket is the decisive column.  Where OLS and 1/OLS straddle by more than ~1.0")
    pr("   the measurement does not pin the ratio; where they nearly coincide the number is real.")
    pr("")

    # ---------------- C3 per-route free offset ----------------
    pr("=" * 128)
    pr("C3  PER-ROUTE FREE-OFFSET GUARD -- angleOffsetDeg NEVER used, offset re-fitted per route")
    pr("=" * 128)
    offs = {}
    for i, r in enumerate(P.routes):
        m = P.base & (P.ri == i) & (P.asa < 25.0)
        if m.sum() < 2000:
            continue
        sr_, c_ = tls_free(P.denom[m], P.cfac[m], P.yraw[m])
        offs[i] = (np.degrees(c_), sr_, float(np.median(P.aoff[m])), int(m.sum()))
    dd = np.array([offs[i][0] - offs[i][2] for i in offs])
    pr("   routes with a per-route free-offset fit: %d" % len(offs))
    pr("   free_offset - liveParameters.angleOffsetDeg:  med %+.3f deg  sd %.3f  p5 %+.3f  p95 %+.3f  |.|>1deg: %.0f %%"
       % (np.median(dd), dd.std(), np.percentile(dd, 5), np.percentile(dd, 95), 100 * np.mean(np.abs(dd) > 1.0)))
    sa_f = np.full(len(P.sa_deg), np.nan)
    for i, (off, _, _, _) in offs.items():
        m = P.ri == i
        sa_f[m] = np.degrees(P.ang[m]) - off
    have = np.isfinite(sa_f)
    y_f = P.cfac * np.radians(sa_f)
    asa_f = np.abs(sa_f)
    pr("")
    pr("   %-10s %9s %12s %12s %8s   %-16s" % ("|sa| deg", "n(s)", "sR(paramsd)", "sR(free)", "delta", "route CI (free)"))
    for lo, hi in BINS:
        okA = P.base & have & (P.asa >= lo) & (P.asa < hi)
        okB = P.base & have & (asa_f >= lo) & (asa_f < hi)
        if okA.sum() < 200 or okB.sum() < 200:
            continue
        a = tls_origin(P.denom[okA], P.y[okA])
        b = tls_origin(P.denom[okB], y_f[okB])
        rl, rh, _ = boot_ci(P.denom[okB], y_f[okB], P.ri[okB])
        pr("   %-10s %9.0f %12.2f %12.2f %8.3f   [%5.2f, %5.2f]"
           % ("%d-%d" % (lo, hi), okA.sum() / FS, a, b, b - a, rl, rh))
    pr("")

    # ---------------- C4 regression on r62/r63 ----------------
    pr("=" * 128)
    pr("C4  REGRESSION TEST -- reproduce the orchestrator's r62+r63 rows from this pipeline")
    pr("=" * 128)
    TGT = {(2, 5): (139, 17.14), (5, 10): (67, 16.83), (10, 20): (26, 16.43), (20, 35): (8, 16.56),
           (35, 50): (3, 16.12), (50, 70): (14, 15.94), (70, 100): (5, 15.63), (100, 150): (4, 14.72)}
    r62 = P.routes.index("75604b0a432fdc89_00000062--1c7daa54e8")
    r63 = P.routes.index("75604b0a432fdc89_00000063--1d4b188022")
    m = P.base & ((P.ri == r62) | (P.ri == r63))
    pr("   gate here: calibrated, v>4, |rate|<20, |sa|>2  (engagement and hands NOT gated, as in the target)")
    pr("   %-10s %8s %8s %8s %8s %8s %-16s" % ("|sa| deg", "n(s)", "TGT n", "sR", "TGT sR", "delta", "block CI"))
    for (lo, hi), (tn, ts) in TGT.items():
        ok = m & (P.asa >= lo) & (P.asa < hi)
        if ok.sum() < 100:
            pr("   %-10s %8.0f %8d %8s %8.2f" % ("%d-%d" % (lo, hi), ok.sum() / FS, tn, "--", ts))
            continue
        s = tls_origin(P.denom[ok], P.y[ok])
        bl, bh, _ = boot_ci(P.denom[ok], P.y[ok], P.blk[ok])
        flag = "" if (bl <= ts <= bh) else "   <-- TARGET OUTSIDE CI"
        pr("   %-10s %8.0f %8d %8.2f %8.2f %8.3f  [%5.2f, %5.2f]%s"
           % ("%d-%d" % (lo, hi), ok.sum() / FS, tn, s, ts, s - ts, bl, bh, flag))
    pr("")
    pr("   engaged+hands-off variant (the mask the orchestrator's sr_angle_sweep uses):")
    m2 = m & P.eng & ~P.pressed
    for (lo, hi), (tn, ts) in TGT.items():
        ok = m2 & (P.asa >= lo) & (P.asa < hi)
        if ok.sum() < 100:
            continue
        s = tls_origin(P.denom[ok], P.y[ok])
        pr("      %-10s %8.0f s   sR %.2f   (target %.2f, delta %+.3f)" % ("%d-%d" % (lo, hi), ok.sum() / FS, s, ts, s - ts))
    pr("")

    # ---------------- C5 the low-angle diagnosis ----------------
    pr("=" * 128)
    pr("C5  WHY THE LOW-|sa| BINS DISAGREE ACROSS EVERY SPLIT -- signal-to-noise in the denominator")
    pr("=" * 128)
    pr("   %-10s %9s %10s %10s %10s %10s" % ("|sa| deg", "n(s)", "med|denom|", "sd(denom)", "SNR", "bracket w"))
    for lo, hi in BINS:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        if ok.sum() < 200:
            continue
        x, y = P.denom[ok], P.y[ok]
        o1, o2 = bracket(x, y)
        # residual scatter about the TLS line, referred to x
        s = tls_origin(x, y)
        res = (y - s * x) / s
        pr("   %-10s %9.0f %10.5f %10.5f %10.2f %10.2f"
           % ("%d-%d" % (lo, hi), ok.sum() / FS, float(np.median(np.abs(x))), float(res.std()),
              float(np.median(np.abs(x)) / res.std()), o2 - o1))
    pr("")
    with open(os.path.join(HERE, "_scratch", "sr_checks.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
