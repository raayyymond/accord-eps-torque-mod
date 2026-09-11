# -*- coding: utf-8 -*-
"""sr_analyze.py -- the corpus-wide true steering-ratio-vs-wheel-angle curve.

ESTIMATOR (openpilot's own vehicle model, inverted; contains NO steering ratio on the right):
    sR_true = curvature_factor(v) * sa / ( -yaw_cal/v - roll_comp(roll, v) )
fitted as a total-least-squares slope through the origin of  y = cfac*sa  on  x = denom.

FREE-INTERCEPT VARIANT (guard against the paramsd circularity: angleOffsetDeg is learned jointly
with a steer ratio).  Write the raw wheel angle as ang = sa + off:
    cfac*radians(ang) = sR*denom + cfac*radians(off)
so a 3-variable TLS of y' = cfac*radians(ang) on [denom, cfac] returns sR AND the offset, with
NOTHING from liveParameters.angleOffsetDeg used.

CI: cluster bootstrap over 2 s blocks within a route (samples are heavily autocorrelated).

Run: python sr_analyze.py
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sr_lib import tls_origin, tls_free, tls_ci, FS, _selfcheck  # noqa: E402
from sr_routes import BUILD, arm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAP_BP = [0.0, 48.0, 60.0, 76.0, 95.0, 121.0, 191.0, 236.0, 303.0, 380.0]
MAP_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
LEVEL = 16.33
BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 70), (70, 100),
        (100, 150), (150, 250), (250, 400)]
L = []


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def served(a):
    return float(np.interp(a, MAP_BP, MAP_V) * (LEVEL / 16.00))


class Pool:
    def __init__(self, path):
        z = np.load(path, allow_pickle=True)
        self.D = {k: z[k] for k in z.files if k not in ("routes", "meta_json")}
        self.routes = [str(x) for x in z["routes"]]
        self.meta = json.loads(str(z["meta_json"]))
        d = self.D
        self.sa_deg = d["sa_deg"].astype(np.float64)
        self.asa = np.abs(self.sa_deg)
        self.sa = np.radians(self.sa_deg)
        self.ang = np.radians(d["ang_deg"].astype(np.float64))
        self.cfac = d["cfac"].astype(np.float64)
        self.denom = d["denom"].astype(np.float64)
        self.v = d["v"].astype(np.float64)
        self.rate = d["rate"].astype(np.float64)
        self.drv = np.abs(d["drv"].astype(np.float64))
        self.eng = d["eng"] > 0.5
        self.pressed = d["pressed"] > 0.5
        self.calok = d["calok"] > 0.5
        self.stiff = d["stiff"].astype(np.float64)
        self.aoff = d["aoff"].astype(np.float64)
        self.ri = d["ri"]
        self.blk = d["blk"]
        self.y = self.cfac * self.sa
        self.yraw = self.cfac * self.ang
        self.build = np.array([BUILD.get(r) or "unknown" for r in self.routes])
        self.armv = np.array([arm(r) for r in self.routes])
        # CORE GATE
        self.base = (self.calok & (self.v > 4.0) & (np.abs(self.rate) < 20.0)
                     & (self.asa > 2.0) & np.isfinite(self.denom) & np.isfinite(self.cfac))

    def row(self, m, lo, hi, seed=0, nboot=400):
        ok = m & (self.asa >= lo) & (self.asa < hi)
        s, n, clo, chi = tls_ci(self.denom[ok], self.y[ok], self.blk[ok], seed=seed, nboot=nboot)
        nr = len(np.unique(self.ri[ok])) if ok.any() else 0
        return s, n, clo, chi, nr, ok


def table(P, m, title, note=""):
    pr("-" * 108)
    pr(title)
    if note:
        pr("   " + note)
    pr("   %-10s %9s %9s %9s %-16s %7s" % ("|sa| deg", "n(s)", "sR_true", "map@16.33", "95% CI", "routes"))
    rows = []
    for lo, hi in BINS:
        s, n, clo, chi, nr, ok = P.row(m, lo, hi)
        if n < 200:
            pr("   %-10s %9.0f %9s %9.2f %-16s %7d" % ("%d-%d" % (lo, hi), n / FS, "--",
                                                       served((lo + hi) / 2), "(n too small)", nr))
            continue
        pr("   %-10s %9.0f %9.2f %9.2f  [%5.2f, %5.2f] %7d"
           % ("%d-%d" % (lo, hi), n / FS, s, served((lo + hi) / 2), clo, chi, nr))
        rows.append((lo, hi, n / FS, s, clo, chi, nr))
    return rows


def split_table(P, base, groups, title, note=""):
    pr("-" * 132)
    pr(title)
    if note:
        pr("   " + note)
    hdr = "   %-10s" % "|sa| deg" + "".join("%26s" % g[0] for g in groups)
    pr(hdr)
    for lo, hi in BINS:
        cells = []
        any_row = False
        for _, gm in groups:
            s, n, clo, chi, nr, _ = P.row(base & gm, lo, hi)
            if n < 200:
                cells.append("%26s" % ("-- (%.0fs)" % (n / FS)))
            else:
                any_row = True
                cells.append("%26s" % ("%.2f [%.2f,%.2f] %.0fs" % (s, clo, chi, n / FS)))
        if any_row:
            pr("   %-10s%s" % ("%d-%d" % (lo, hi), "".join(cells)))


def main():
    assert _selfcheck()
    P = Pool(os.path.join(HERE, "_scratch", "pooled.npz"))
    d = P.D

    pr("=" * 132)
    pr("CORPUS-WIDE TRUE STEERING RATIO vs WHEEL ANGLE -- 2020 Honda Accord, dongle 75604b0a432fdc89")
    pr("Instrument: openpilot vehicle model inverted onto the DEVICE GYRO.  No controller channel enters the fit.")
    pr("=" * 132)
    pr("   routes pooled            : %d" % len(P.routes))
    pr("   samples cached           : %d  (%.0f s = %.1f h of valid frames)"
       % (len(P.sa_deg), len(P.sa_deg) / FS, len(P.sa_deg) / FS / 3600))
    pr("   after the CORE GATE      : %d  (%.0f s = %.1f h)"
       % (P.base.sum(), P.base.sum() / FS, P.base.sum() / FS / 3600))
    pr("   core gate = calStatus==calibrated & vEgo>4 & |steeringRateDeg|<20 & |sa|>2 deg & finite")
    pr("   NOT gated on steeringPressed or on engagement -- the relation is kinematic (see split C/D).")
    pr("")

    # ---- gate cost accounting
    pr("-" * 108)
    pr("0  WHAT EACH GATE COSTS  (applied one at a time to the cached frames, and cumulatively)")
    pr("-" * 108)
    gates = [("calStatus==calibrated", P.calok),
             ("vEgo > 4 m/s", P.v > 4.0),
             ("|steeringRateDeg| < 20", np.abs(P.rate) < 20.0),
             ("|sa| > 2 deg", P.asa > 2.0),
             ("finite denom/cfac", np.isfinite(P.denom) & np.isfinite(P.cfac))]
    tot = len(P.sa_deg)
    cum = np.ones(tot, bool)
    for nm, g in gates:
        cum = cum & g
        pr("   %-26s alone keeps %7.1f %%  (%8.0f s)   cumulative %7.1f %%  (%8.0f s)"
           % (nm, 100 * g.mean(), g.sum() / FS, 100 * cum.mean(), cum.sum() / FS))
    pr("")

    # ---- stiffnessFactor + angleOffset census
    pr("-" * 108)
    pr("1  CENSUS OF THE TWO paramsd QUANTITIES THE ESTIMATOR LEANS ON")
    pr("-" * 108)
    st = P.stiff[P.base]
    pr("   liveParameters.stiffnessFactor over gated frames: min %.4f  p1 %.4f  med %.4f  p99 %.4f  max %.4f"
       % (st.min(), np.percentile(st, 1), np.median(st), np.percentile(st, 99), st.max()))
    pr("   fraction of gated frames with |stiffnessFactor - 1| > 0.02 : %.4f" % np.mean(np.abs(st - 1) > 0.02))
    ao = P.aoff[P.base]
    pr("   liveParameters.angleOffsetDeg  over gated frames: min %.2f  p1 %.2f  med %.2f  p99 %.2f  max %.2f"
       % (ao.min(), np.percentile(ao, 1), np.median(ao), np.percentile(ao, 99), ao.max()))
    # per-route stiffness
    bad = []
    for i, r in enumerate(P.routes):
        m = P.base & (P.ri == i)
        if m.sum() < 500:
            continue
        s = np.median(P.stiff[m])
        if abs(s - 1.0) > 0.02:
            bad.append((r, s, m.sum() / FS))
    pr("   routes whose MEDIAN stiffnessFactor is off 1.0 by >2 %%: %d" % len(bad))
    for r, s, n in sorted(bad, key=lambda t: -t[2])[:12]:
        pr("      %-46s stiff %.3f  (%.0f s)  build %s" % (r, s, n, BUILD.get(r)))
    pr("")

    # ---- A: headline curve
    rows = table(P, P.base, "A  HEADLINE: POOLED OVER THE WHOLE CORPUS (every route, engaged or not, hands on or off)")
    pr("")

    # ---- B: free intercept
    pr("-" * 108)
    pr("2  THE angleOffsetDeg CIRCULARITY GUARD -- free-intercept TLS, per |sa| bin and globally")
    pr("   3-var TLS of cfac*radians(RAW steeringAngleDeg) on [denom, cfac]; angleOffsetDeg NEVER used.")
    pr("-" * 108)
    m_small = P.base & (P.asa < 12.0)
    sr_g, c_g = tls_free(P.denom[m_small], P.cfac[m_small], P.yraw[m_small])
    pr("   GLOBAL small-angle fit (|sa| 2-12 deg, %.0f s): sR = %.3f, implied offset = %+.3f deg"
       % (m_small.sum() / FS, sr_g, np.degrees(c_g)))
    pr("   median liveParameters.angleOffsetDeg on the same frames   = %+.3f deg" % np.median(P.aoff[m_small]))
    pr("   -> difference %+.3f deg" % (np.degrees(c_g) - np.median(P.aoff[m_small])))
    pr("")
    off_free = np.degrees(c_g)

    # rebuild y with the free offset
    sa_free = np.degrees(P.ang) - off_free
    y_free = P.cfac * np.radians(sa_free)
    asa_free = np.abs(sa_free)
    pr("   %-10s %9s %9s %9s %9s" % ("|sa| deg", "n(s)", "sR(paramsd)", "sR(free off)", "delta"))
    for lo, hi in BINS:
        okA = P.base & (P.asa >= lo) & (P.asa < hi)
        okB = P.base & (asa_free >= lo) & (asa_free < hi)
        if okA.sum() < 200:
            continue
        a = tls_origin(P.denom[okA], P.y[okA])
        b = tls_origin(P.denom[okB], y_free[okB])
        pr("   %-10s %9.0f %9.2f %9.2f %9.3f" % ("%d-%d" % (lo, hi), okA.sum() / FS, a, b, b - a))
    pr("")

    # ---- C: driver torque split
    ad = P.drv
    split_table(P, P.base, [("|drv| < 30", ad < 30), ("30 <= |drv| < 150", (ad >= 30) & (ad < 150)),
                            ("|drv| >= 150", ad >= 150)],
                "3  SPLIT BY |carState.steeringTorque| -- the kinematic-invariance check",
                "The relation is wheel-angle -> yaw-rate.  Who supplies the torque must not enter it.")
    pr("")

    # ---- D: engaged vs manual
    split_table(P, P.base, [("engaged (latActive)", P.eng), ("manual", ~P.eng),
                            ("manual, hands on", ~P.eng & P.pressed)],
                "4  ENGAGED vs MANUAL -- must agree; a disagreement is a finding",
                "`engaged` = carControl.latActive.  Used ONLY as a split label, never in the fit.")
    pr("")

    # ---- E: firmware arm
    armof = P.armv[P.ri]
    arms = [a for a in ["stock", "V52-V76", "V80-V122", "V276-V283", "V288-V289", "unknown"]
            if (armof == a).any()]
    split_table(P, P.base, [(a, armof == a) for a in arms],
                "5  SPLIT BY EPS FIRMWARE ARM -- the 'firmware-independent' claim, TESTED",
                "The rack is mechanical.  If an arm shifts the curve the instrument is seeing something it should not.")
    pr("")
    pr("   arm membership (gated seconds / routes):")
    for a in arms:
        m = P.base & (armof == a)
        pr("      %-12s %8.0f s   %2d routes" % (a, m.sum() / FS, len(np.unique(P.ri[m]))))
    pr("")

    # ---- F: angle x speed cross-tab
    pr("-" * 132)
    pr("6  |sa| x SPEED CROSS-TAB -- do the ROWS move (rack geometry) or the COLUMNS (bicycle-model artefact)?")
    pr("-" * 132)
    VB = [(4, 9), (9, 14), (14, 20), (20, 28), (28, 40)]
    AB = [(2, 6), (6, 12), (12, 25), (25, 60), (60, 150), (150, 400)]
    pr("   %-10s%s" % ("|sa| deg", "".join("%20s" % ("v %d-%d m/s" % vb) for vb in VB)))
    for lo, hi in AB:
        cells = []
        for vlo, vhi in VB:
            ok = P.base & (P.asa >= lo) & (P.asa < hi) & (P.v >= vlo) & (P.v < vhi)
            if ok.sum() < 200:
                cells.append("%20s" % ("-- (%.0fs)" % (ok.sum() / FS)))
            else:
                s = tls_origin(P.denom[ok], P.y[ok])
                cells.append("%20s" % ("%.2f / %.0fs" % (s, ok.sum() / FS)))
        pr("   %-10s%s" % ("%d-%d" % (lo, hi), "".join(cells)))
    pr("")
    pr("   Same table with the KINEMATIC curvature factor (1/wheelbase; slip term sf*v^2 removed):")
    ykin = (1.0 / 2.83) * P.sa
    pr("   %-10s%s" % ("|sa| deg", "".join("%20s" % ("v %d-%d m/s" % vb) for vb in VB)))
    for lo, hi in AB:
        cells = []
        for vlo, vhi in VB:
            ok = P.base & (P.asa >= lo) & (P.asa < hi) & (P.v >= vlo) & (P.v < vhi)
            if ok.sum() < 200:
                cells.append("%20s" % ("-- (%.0fs)" % (ok.sum() / FS)))
            else:
                s = tls_origin(P.denom[ok], ykin[ok])
                cells.append("%20s" % ("%.2f / %.0fs" % (s, ok.sum() / FS)))
        pr("   %-10s%s" % ("%d-%d" % (lo, hi), "".join(cells)))
    pr("")

    # ---- G: left vs right
    split_table(P, P.base, [("LEFT (sa > 0)", P.sa_deg > 0), ("RIGHT (sa < 0)", P.sa_deg < 0)],
                "7  LEFT vs RIGHT -- the rack is symmetric; asymmetry means an angle-offset problem")
    pr("")

    # ---- H: per-route scatter at a fixed band, to see route-level dispersion
    pr("-" * 108)
    pr("8  PER-ROUTE DISPERSION IN THE 2-12 deg BAND (how much of the CI is between-route?)")
    pr("-" * 108)
    vals = []
    for i, r in enumerate(P.routes):
        ok = P.base & (P.ri == i) & (P.asa >= 2) & (P.asa < 12)
        if ok.sum() < 3000:
            continue
        vals.append((tls_origin(P.denom[ok], P.y[ok]), ok.sum() / FS, r))
    v = np.array([x[0] for x in vals])
    pr("   %d routes with >=30 s in band: median %.3f  sd %.3f  p5 %.3f  p95 %.3f  min %.3f  max %.3f"
       % (len(v), np.median(v), v.std(), np.percentile(v, 5), np.percentile(v, 95), v.min(), v.max()))
    for s, n, r in sorted(vals)[:4] + sorted(vals)[-4:]:
        pr("      %-46s %.2f  (%.0f s)  build %s" % (r, s, n, BUILD.get(r)))
    pr("")

    # ---- I: deliverable knot set
    pr("=" * 108)
    pr("9  DELIVERABLE -- a replacement HONDA_ACCORD_STEER_RATIO_ANGLE_BP / _V")
    pr("=" * 108)
    pr("   %-10s %9s %9s %-16s %7s %10s" % ("|sa| deg", "n(s)", "sR_true", "95% CI", "routes", "CI width"))
    for lo, hi, n, s, clo, chi, nr in rows:
        pr("   %-10s %9.0f %9.2f  [%5.2f, %5.2f] %7d %10.3f"
           % ("%d-%d" % (lo, hi), n, s, clo, chi, nr, chi - clo))
    pr("")
    with open(os.path.join(HERE, "_scratch", "sr_corpus.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    json.dump([dict(lo=r[0], hi=r[1], n_s=r[2], sr=r[3], ci_lo=r[4], ci_hi=r[5], nroutes=r[6]) for r in rows],
              open(os.path.join(HERE, "_scratch", "sr_corpus_rows.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
