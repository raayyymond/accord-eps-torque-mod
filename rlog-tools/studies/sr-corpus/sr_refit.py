# -*- coding: utf-8 -*-
"""sr_refit.py -- re-run the FINE fixed-effects table (the one the 57410c3b4 knots were read from) on the
current pooled cache, and print old-vs-new per bin plus a leave-one-route-out check on the newest route.

Run: python sr_refit.py [route id to drop for the leave-out column]
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sr_episodes import P2  # noqa: E402
from sr_final import fe_fit  # noqa: E402
from sr_lib2 import FS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FINE = [(20, 28), (28, 36), (36, 45), (45, 55), (55, 70), (70, 85), (85, 105), (105, 130), (130, 165),
        (165, 210), (210, 270)]
SHIPPED = {(20, 28): 16.89, (28, 36): 16.91, (36, 45): 16.73, (45, 55): 16.45, (55, 70): 16.26,
           (70, 85): 15.97, (85, 105): 15.46, (105, 130): 15.02, (130, 165): 14.67,
           (165, 210): 14.45, (210, 270): 14.09}


def main():
    P = P2(os.path.join(HERE, "_scratch", "pooled.npz"))
    drop = sys.argv[1] if len(sys.argv) > 1 else None
    di = P.routes.index(drop) if drop in P.routes else -1
    print("routes in pool: %d   leave-out: %s (index %d)" % (len(P.routes), drop, di))
    win = np.sign(P.sa_deg) * P.rate > 0
    print("   |sa|      n(s) routes  FE-TLS  sprd  95%CI           shipped  delta | without-route  | wind-in  wind-out  mid")
    for lo, hi in FINE:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        r = fe_fit(P.u[ok], P.ang[ok], P.ri[ok])
        o2 = ok & (P.ri != di)
        r2 = fe_fit(P.u[o2], P.ang[o2], P.ri[o2], nboot=1)
        a = fe_fit(P.u[ok & win], P.ang[ok & win], P.ri[ok & win], nboot=1)
        b = fe_fit(P.u[ok & ~win], P.ang[ok & ~win], P.ri[ok & ~win], nboot=1)
        ci = ("[%5.2f,%5.2f]" % r["ci"]) if "ci" in r else "     --     "
        print("   %-8s %5.0f  %4d   %6.2f  %4.2f  %s   %6.2f  %+.3f |   %6.2f       | %6.2f   %6.2f  %6.2f"
              % ("%d-%d" % (lo, hi), ok.sum() / FS, r["nroutes"], r["tls"], r["spread"], ci, SHIPPED[(lo, hi)],
                 r["tls"] - SHIPPED[(lo, hi)], r2["tls"], a["tls"] if a else np.nan, b["tls"] if b else np.nan,
                 0.5 * (a["tls"] + b["tls"]) if a and b else np.nan))
    # shape statistic, joint over both bins with shared per-route intercepts
    for name, m in (("all", P.ri >= 0), ("without", P.ri != di)):
        lo_m = P.base & m & (P.asa >= 20) & (P.asa < 45)
        hi_m = P.base & m & (P.asa >= 130) & (P.asa < 165)
        rl = fe_fit(P.u[lo_m], P.ang[lo_m], P.ri[lo_m], nboot=1)
        rh = fe_fit(P.u[hi_m], P.ang[hi_m], P.ri[hi_m], nboot=1)
        print("   shape sR(20-45) - sR(130-165) [%s]: %.2f - %.2f = %.3f" % (name, rl["tls"], rh["tls"], rl["tls"] - rh["tls"]))


if __name__ == "__main__":
    main()
