# -*- coding: utf-8 -*-
"""sr_knots.py -- the deliverable.

C5 established that the estimator only identifies the ratio where the denominator SNR is high:
bracket width [OLS(y|x), 1/OLS(x|y)] is 1.81 at |sa| 2-5 deg but <= 0.11 from 20 deg up.  So:
  * fine knots are placed only where the bracket is tight;
  * the low-|sa| end is reported with its honest (wide) interval and marked NOT SUPPORTED.

Also settles whether the firmware-arm and left/right disagreements seen at 35-70 deg are real or
a SPEED-COMPOSITION confound -- different arms drove different route mixes, and the |sa| x speed
cross-tab already showed speed moving the 25-60 deg row.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sr_lib import tls_origin, FS  # noqa: E402
from sr_checks import boot_ci, bracket  # noqa: E402
from sr_analyze import Pool  # noqa: E402
from sr_routes import BUILD, arm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = []
MAP_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
MAP_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
LEVEL = 16.33

FINE = [(2, 5), (5, 10), (10, 20), (20, 28), (28, 36), (36, 45), (45, 55), (55, 70),
        (70, 85), (85, 105), (105, 130), (130, 165), (165, 210), (210, 270), (270, 400)]


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def main():
    P = Pool(os.path.join(HERE, "_scratch", "pooled.npz"))
    armof = P.armv[P.ri]

    pr("=" * 132)
    pr("K1  FINE SWEEP -- every bin, with the identifiability verdict beside it")
    pr("=" * 132)
    pr("   %-10s %8s %8s %7s %-16s %-16s %8s %7s %8s" %
       ("|sa| deg", "n(s)", "med|sa|", "sR", "route CI (95%)", "bracket", "brkt w", "routes", "verdict"))
    out = []
    for lo, hi in FINE:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        n = int(ok.sum())
        if n < 300:
            pr("   %-10s %8.0f  (n too small)" % ("%d-%d" % (lo, hi), n / FS))
            continue
        x, y = P.denom[ok], P.y[ok]
        s = tls_origin(x, y)
        rlo, rhi, nr = boot_ci(x, y, P.ri[ok])
        o1, o2 = bracket(x, y)
        w = o2 - o1
        v = "SOLID" if w < 0.15 else ("OK" if w < 0.40 else "NOT ID")
        msa = float(np.median(P.asa[ok]))
        out.append(dict(lo=lo, hi=hi, med_sa=msa, n_s=n / FS, sr=s, ci_lo=rlo, ci_hi=rhi,
                        brk_lo=o1, brk_hi=o2, brk_w=w, routes=nr, verdict=v))
        pr("   %-10s %8.0f %8.1f %7.2f  [%5.2f, %5.2f]  [%5.2f, %5.2f] %8.2f %7d %8s"
           % ("%d-%d" % (lo, hi), n / FS, msa, s, rlo, rhi, o1, o2, w, nr, v))
    pr("")

    pr("=" * 132)
    pr("K2  IS THE 35-70 deg ARM DISAGREEMENT REAL, OR SPEED COMPOSITION?")
    pr("    Same |sa| band, but ALSO holding speed inside one narrow window.  If the arms converge")
    pr("    once speed is held, the disagreement was composition and the rack claim survives.")
    pr("=" * 132)
    arms = ["V52-V76", "V80-V122", "V276-V283", "V288-V289"]
    for alo, ahi in ((25, 60), (60, 150), (150, 400)):
        pr("   |sa| %d-%d deg" % (alo, ahi))
        pr("      %-16s %26s %26s %26s" % ("arm", "ALL speeds", "v 4-9 m/s", "v 9-14 m/s"))
        for a in arms:
            cells = []
            for vlo, vhi in ((0, 99), (4, 9), (9, 14)):
                ok = (P.base & (armof == a) & (P.asa >= alo) & (P.asa < ahi)
                      & (P.v >= vlo) & (P.v < vhi))
                if ok.sum() < 300:
                    cells.append("%26s" % ("-- (%.0fs)" % (ok.sum() / FS)))
                else:
                    s = tls_origin(P.denom[ok], P.y[ok])
                    rl, rh, _ = boot_ci(P.denom[ok], P.y[ok], P.ri[ok])
                    cells.append("%26s" % ("%.2f [%.2f,%.2f] %.0fs" % (s, rl, rh, ok.sum() / FS)))
            pr("      %-16s%s" % (a, "".join(cells)))
        # speed composition of each arm in this band
        comp = []
        for a in arms:
            ok = P.base & (armof == a) & (P.asa >= alo) & (P.asa < ahi)
            comp.append("%s med v %.1f" % (a, float(np.median(P.v[ok])) if ok.sum() else np.nan))
        pr("      speed composition: " + " | ".join(comp))
        pr("")

    pr("=" * 132)
    pr("K3  SAME QUESTION FOR DRIVER TORQUE AND FOR LEFT/RIGHT, IN THE IDENTIFIED REGION ONLY")
    pr("=" * 132)
    pr("   %-12s %24s %24s %24s" % ("|sa| deg", "|drv|<30", "30-150", ">=150"))
    ad = P.drv
    for alo, ahi in ((20, 45), (45, 90), (90, 400)):
        cells = []
        for dlo, dhi in ((0, 30), (30, 150), (150, 1e9)):
            ok = P.base & (P.asa >= alo) & (P.asa < ahi) & (ad >= dlo) & (ad < dhi)
            if ok.sum() < 300:
                cells.append("%24s" % ("-- (%.0fs)" % (ok.sum() / FS)))
            else:
                s = tls_origin(P.denom[ok], P.y[ok])
                rl, rh, _ = boot_ci(P.denom[ok], P.y[ok], P.ri[ok])
                cells.append("%24s" % ("%.2f [%.2f,%.2f] %.0fs" % (s, rl, rh, ok.sum() / FS)))
        pr("   %-12s%s" % ("%d-%d" % (alo, ahi), "".join(cells)))
    pr("")
    pr("   %-12s %24s %24s %14s" % ("|sa| deg", "LEFT", "RIGHT", "L-R"))
    for alo, ahi in ((20, 45), (45, 90), (90, 400)):
        vals = []
        cells = []
        for lbl, sm in (("L", P.sa_deg > 0), ("R", P.sa_deg < 0)):
            ok = P.base & sm & (P.asa >= alo) & (P.asa < ahi)
            if ok.sum() < 300:
                cells.append("%24s" % "--"); vals.append(np.nan); continue
            s = tls_origin(P.denom[ok], P.y[ok])
            rl, rh, _ = boot_ci(P.denom[ok], P.y[ok], P.ri[ok])
            vals.append(s)
            cells.append("%24s" % ("%.2f [%.2f,%.2f] %.0fs" % (s, rl, rh, ok.sum() / FS)))
        pr("   %-12s%s %14.3f" % ("%d-%d" % (alo, ahi), "".join(cells), vals[0] - vals[1]))
    pr("")

    pr("=" * 132)
    pr("K4  PROPOSED REPLACEMENT MAP -- HONDA_ACCORD_STEER_RATIO_ANGLE_BP / _V")
    pr("=" * 132)
    pr("   Knots are placed at the MEDIAN |sa| of each SOLID/OK bin, valued at that bin's sR_true.")
    pr("   Below 20 deg the corpus does NOT identify the ratio (bracket > 0.3), so the low end is")
    pr("   pinned to the 20-28 deg value rather than to an unidentified measurement.")
    pr("")
    good = [r for r in out if r["verdict"] in ("SOLID", "OK") and r["lo"] >= 20]
    bp = [0.0] + [round(r["med_sa"], 0) for r in good]
    vv = [good[0]["sr"]] + [round(r["sr"], 2) for r in good]
    # monotone-decreasing cleanup (the rack ratio cannot rise with angle)
    vv2 = list(vv)
    for i in range(1, len(vv2)):
        vv2[i] = min(vv2[i], vv2[i - 1])
    pr("   raw     BP = %s" % ([float(b) for b in bp],))
    pr("           V  = %s" % ([round(float(x), 2) for x in vv],))
    pr("   monotone V = %s" % ([round(float(x), 2) for x in vv2],))
    pr("")
    pr("   %-10s %8s %8s %10s %10s %-16s %8s" % ("knot deg", "n(s)", "routes", "MEASURED", "CURRENT", "95% CI", "delta"))
    for b, v in zip(bp, vv2):
        cur = float(np.interp(b, MAP_BP, MAP_V) * (LEVEL / 16.00))
        rr = [r for r in good if abs(r["med_sa"] - b) < 0.51]
        n = rr[0]["n_s"] if rr else np.nan
        nr = rr[0]["routes"] if rr else 0
        ci = "[%5.2f, %5.2f]" % (rr[0]["ci_lo"], rr[0]["ci_hi"]) if rr else "(pinned)"
        pr("   %-10.0f %8.0f %8d %10.2f %10.2f %-16s %8.3f" % (b, n, nr, v, cur, ci, v - cur))
    pr("")
    pr("   NOT SUPPORTED BY THE CORPUS (reported for completeness, do NOT knot on these):")
    for r in out:
        if r["verdict"] == "NOT ID" or r["lo"] < 20:
            pr("      %-10s n %6.0f s   sR %.2f   route CI [%.2f, %.2f]   bracket [%.2f, %.2f] width %.2f"
               % ("%d-%d deg" % (r["lo"], r["hi"]), r["n_s"], r["sr"], r["ci_lo"], r["ci_hi"],
                  r["brk_lo"], r["brk_hi"], r["brk_w"]))
    pr("")
    pr("   Knots in the CURRENT fork map that the corpus still cannot support:")
    for b in MAP_BP:
        cov = [r for r in out if r["lo"] <= b < r["hi"]]
        if not cov:
            pr("      %6.0f deg -- NO DATA IN ANY BIN COVERING IT" % b)
        elif cov[0]["verdict"] == "NOT ID":
            pr("      %6.0f deg -- covered by %d-%d deg, bracket width %.2f: NOT IDENTIFIED"
               % (b, cov[0]["lo"], cov[0]["hi"], cov[0]["brk_w"]))
        else:
            pr("      %6.0f deg -- supported (%d-%d deg bin, %.0f s, %s)"
               % (b, cov[0]["lo"], cov[0]["hi"], cov[0]["n_s"], cov[0]["verdict"]))
    json.dump(out, open(os.path.join(HERE, "_scratch", "sr_knots.json"), "w"), indent=1)
    with open(os.path.join(HERE, "_scratch", "sr_knots.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
