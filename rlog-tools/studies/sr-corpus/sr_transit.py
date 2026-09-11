# -*- coding: utf-8 -*-
"""sr_transit.py -- the four pre-registered transit tests, on the fixed-effects estimator.

T4  regress sR on |d|sa|/dt| within each bin, extrapolate to rate -> 0.   (rate gate RELAXED to 60)
T2  wind-in vs wind-out split (sign of d|sa|/dt = sign(sa)*rate); midpoint is the unbiased value.
T1  long-episode-only subset fit + the episode-duration distribution.
T3  one-sided lag sweep tau in [0, +250 ms] (negative shifts are physically inadmissible),
    against the pre-registered thresholds: plateau if total variation < 0.30, transit if >= 0.80.
(c) dwell-time stratification: sR vs the duration of the episode each frame sits in.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sr_episodes import P2  # noqa: E402
from sr_final import fe_fit  # noqa: E402
from sr_lib2 import episodes, FS  # noqa: E402

L = []
BANDS = [(20, 45), (45, 70), (70, 100), (100, 130), (130, 165), (165, 250)]
R64 = "75604b0a432fdc89_00000064--ce6b0b0ebb"
R65 = "75604b0a432fdc89_00000065--b9f78988bd"


def pr(s=""):
    print(s, flush=True)
    L.append(s)


def val(P, m):
    if m.sum() < 400:
        return None
    return fe_fit(P.u[m], P.ang[m], P.ri[m])


def main():
    P = P2(os.path.join(HERE, "_scratch", "pooled.npz"))
    relax = (P.calok & (P.v > 4.0) & (np.abs(P.rate) < 60.0)
             & np.isfinite(P.u) & np.isfinite(P.ang))
    dsa = np.sign(P.sa_deg) * P.rate
    res = {}

    pr("=" * 140)
    pr("T4  sR vs WIND RATE, EXTRAPOLATED TO RATE -> 0   (|rate| gate relaxed to 60 deg/s for leverage)")
    pr("    Sub-bin by |d|sa|/dt|, fit each sub-bin, then weighted least squares of the sub-bin values")
    pr("    on their median rate.  Intercept = the rate-zero ratio.  No rate dependence => objection dies.")
    pr("=" * 140)
    RB = [(0, 5), (5, 10), (10, 16), (16, 24), (24, 36), (36, 60)]
    pr("   %-10s %s %10s %14s %10s" % ("|sa| deg", "".join("%14s" % ("r %d-%d" % r) for r in RB),
                                       "slope/10", "intercept", "raw(<20)"))
    for lo, hi in BANDS:
        cells, xs, ys, ws = [], [], [], []
        for rlo, rhi in RB:
            m = relax & (P.asa >= lo) & (P.asa < hi) & (np.abs(dsa) >= rlo) & (np.abs(dsa) < rhi)
            r = val(P, m)
            if r is None:
                cells.append("%14s" % "--")
                continue
            cells.append("%14s" % ("%.2f/%.0fs" % (r["tls"], m.sum() / FS)))
            xs.append(float(np.median(np.abs(dsa[m]))))
            ys.append(r["tls"])
            ws.append(m.sum())
        if len(xs) >= 3:
            x = np.array(xs, float); y = np.array(ys, float); w = np.array(ws, float)
            A = np.stack([np.ones_like(x), x], 1)
            W = np.diag(w / w.sum())
            b = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ y, rcond=None)[0]
            icept, slope = float(b[0]), float(b[1])
            js = []
            for k in range(len(x)):
                kk = [i for i in range(len(x)) if i != k]
                if len(kk) < 3:
                    continue
                A2 = A[kk]
                W2 = np.diag(w[kk] / w[kk].sum())
                js.append(float(np.linalg.lstsq(A2.T @ W2 @ A2, A2.T @ W2 @ y[kk], rcond=None)[0][0]))
            se = float(np.std(js)) * np.sqrt(max(len(js) - 1, 1)) if js else np.nan
        else:
            icept = slope = se = np.nan
        raw = val(P, P.base & (P.asa >= lo) & (P.asa < hi))
        res.setdefault((lo, hi), {})
        res[(lo, hi)]["t4_icept"] = icept
        res[(lo, hi)]["t4_slope"] = slope
        res[(lo, hi)]["t4_se"] = se
        res[(lo, hi)]["raw"] = raw["tls"] if raw else np.nan
        pr("   %-10s %s %10.3f %7.2f +-%-4.2f %10.2f"
           % ("%d-%d" % (lo, hi), "".join(cells), slope * 10, icept, se,
              raw["tls"] if raw else np.nan))
    pr("")
    pr("   slope/10 = change in sR per 10 deg/s of wind rate.  |slope/10| < 0.05 => no rate dependence.")
    pr("")

    pr("=" * 140)
    pr("T2  WIND-IN vs WIND-OUT  (sign of d|sa|/dt).  Steady state => they agree.  Lag => they split")
    pr("    symmetrically, wind-in HIGH, and the MIDPOINT is the unbiased value.")
    pr("=" * 140)
    pr("   %-10s %18s %18s %10s %10s %10s" % ("|sa| deg", "wind-IN", "wind-OUT", "IN-OUT", "midpoint", "raw"))
    for lo, hi in BANDS:
        b = P.base & (P.asa >= lo) & (P.asa < hi)
        ri_ = val(P, b & (dsa > 2.0))
        ro = val(P, b & (dsa < -2.0))
        if ri_ and ro:
            mid = 0.5 * (ri_["tls"] + ro["tls"])
            res[(lo, hi)]["t2_mid"] = mid
            res[(lo, hi)]["t2_split"] = ri_["tls"] - ro["tls"]
            pr("   %-10s %8.2f (%5.0fs) %8.2f (%5.0fs) %10.3f %10.2f %10.2f"
               % ("%d-%d" % (lo, hi), ri_["tls"], (b & (dsa > 2)).sum() / FS, ro["tls"],
                  (b & (dsa < -2)).sum() / FS, ri_["tls"] - ro["tls"], mid, res[(lo, hi)]["raw"]))
        else:
            pr("   %-10s  (one half too thin)" % ("%d-%d" % (lo, hi)))
    pr("")

    pr("=" * 140)
    pr("T1  EPISODE-DURATION DISTRIBUTION AND THE LONG-EPISODE-ONLY FIT")
    pr("=" * 140)
    pr("   %-10s %7s %6s %7s %8s %9s %9s %10s %10s %10s"
       % ("|sa| deg", "n_ep", "med", "p90", "longest", "s in>1s", "s in>3s", "fit all", "fit >1s", "fit >3s"))
    for lo, hi in BANDS:
        mall = np.zeros(len(P.u), bool)
        m1 = np.zeros(len(P.u), bool)
        m3 = np.zeros(len(P.u), bool)
        durs = []
        for i in np.unique(P.ri[P.base]):
            a, b0 = P.sl[i]
            sub = slice(a, b0)
            e, _ = episodes(P.t[sub], np.where(P.base[sub], P.asa[sub], np.nan),
                            P.v[sub], P.rate[sub], lo, hi)
            for (i0, i1) in e:
                d = P.t[sub][i1] - P.t[sub][i0]
                durs.append(d)
                mall[a + i0:a + i1 + 1] = True
                if d > 1.0:
                    m1[a + i0:a + i1 + 1] = True
                if d > 3.0:
                    m3[a + i0:a + i1 + 1] = True
        durs = np.array(durs) if durs else np.array([0.0])
        fa, f1, f3 = val(P, mall), val(P, m1), val(P, m3)
        g = lambda r: ("%10.2f" % r["tls"]) if r else "%10s" % "--"
        res[(lo, hi)]["t1_long"] = (f3["tls"] if f3 else (f1["tls"] if f1 else np.nan))
        pr("   %-10s %7d %6.2f %7.2f %8.2f %9.1f %9.1f %s %s %s"
           % ("%d-%d" % (lo, hi), len(durs), np.median(durs), np.percentile(durs, 90), durs.max(),
              durs[durs > 1].sum(), durs[durs > 3].sum(), g(fa), g(f1), g(f3)))
    pr("")

    pr("=" * 140)
    pr("T3  ONE-SIDED LAG SWEEP  tau in [0, +250 ms]  (negative shifts physically inadmissible)")
    pr("    pre-registered: PLATEAU if total variation < 0.30 ; TRANSIT-dominated if >= 0.80")
    pr("=" * 140)
    TAU = np.arange(0, 26, 2)
    pr("   %-10s %s %10s %8s %-11s" % ("|sa| deg", "".join("%8s" % ("%dms" % (t * 10)) for t in TAU[::2]),
                                       "variation", "argmin", "VERDICT"))
    for lo, hi in BANDS:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        vals = []
        for k in TAU:
            us = P.shifted_u(int(k))
            mm = ok & np.isfinite(us)
            r = fe_fit(us[mm], P.ang[mm], P.ri[mm], nboot=1) if mm.sum() > 400 else None
            vals.append(np.nan if r is None else r["tls"])
        v = np.array(vals, float)
        if np.isfinite(v).sum() < 4:
            pr("   %-10s (too thin)" % ("%d-%d" % (lo, hi)))
            continue
        var = float(np.nanmax(v) - np.nanmin(v))
        am = float(TAU[int(np.nanargmin(v))] * 10)
        vd = "PLATEAU" if var < 0.30 else ("TRANSIT" if var >= 0.80 else "ambiguous")
        res[(lo, hi)]["t3_var"] = var
        res[(lo, hi)]["t3_min"] = float(np.nanmin(v))
        pr("   %-10s %s %10.2f %8.0f %-11s"
           % ("%d-%d" % (lo, hi),
              "".join("%8s" % ("%.2f" % x if np.isfinite(x) else "--") for x in v[::2]), var, am, vd))
    pr("")

    pr("=" * 140)
    pr("(c) DWELL-TIME STRATIFICATION -- sR vs the duration of the episode each frame sits in")
    pr("=" * 140)
    DB = [(0.6, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 4.0), (4.0, 100.0)]
    pr("   %-10s %s" % ("|sa| deg", "".join("%17s" % ("dwell %.1f-%.1f s" % d) for d in DB)))
    for lo, hi in BANDS:
        masks = {d: np.zeros(len(P.u), bool) for d in DB}
        for i in np.unique(P.ri[P.base]):
            a, b0 = P.sl[i]
            sub = slice(a, b0)
            e, _ = episodes(P.t[sub], np.where(P.base[sub], P.asa[sub], np.nan),
                            P.v[sub], P.rate[sub], lo, hi)
            for (i0, i1) in e:
                d = P.t[sub][i1] - P.t[sub][i0]
                for dd in DB:
                    if dd[0] <= d < dd[1]:
                        masks[dd][a + i0:a + i1 + 1] = True
        cells = []
        for dd in DB:
            r = val(P, masks[dd])
            cells.append("%17s" % ("%.2f / %.0fs" % (r["tls"], masks[dd].sum() / FS) if r else "--"))
        pr("   %-10s%s" % ("%d-%d" % (lo, hi), "".join(cells)))
    pr("")

    pr("=" * 140)
    pr("SYSTEMATIC BAND -- spread across {raw, T4 rate-0, T2 midpoint, T1 long-episode, T3 lag-min}")
    pr("=" * 140)
    pr("   %-10s %9s %9s %9s %9s %9s %9s   %-18s"
       % ("|sa| deg", "raw", "T4 r->0", "T2 mid", "T1 long", "T3 min", "SPREAD", "recommended +- sys"))
    out = {}
    for lo, hi in BANDS:
        d = res.get((lo, hi), {})
        cands = [d.get(k) for k in ("raw", "t4_icept", "t2_mid", "t1_long", "t3_min")]
        cc = np.array([c for c in cands if c is not None and np.isfinite(c)], float)
        if len(cc) < 2:
            continue
        spread = float(cc.max() - cc.min())
        centre = float(np.median(cc))
        out["%d-%d" % (lo, hi)] = dict(centre=centre, spread=spread, raw=d.get("raw"),
                                       t4=d.get("t4_icept"), t2=d.get("t2_mid"),
                                       t1=d.get("t1_long"), t3=d.get("t3_min"),
                                       t4_slope=d.get("t4_slope"), t3_var=d.get("t3_var"))
        f = lambda x: ("%9.2f" % x) if x is not None and np.isfinite(x) else "%9s" % "--"
        pr("   %-10s %s %s %s %s %s %9.2f   %5.2f +- %.2f"
           % ("%d-%d" % (lo, hi), f(d.get("raw")), f(d.get("t4_icept")), f(d.get("t2_mid")),
              f(d.get("t1_long")), f(d.get("t3_min")), spread, centre, spread / 2))
    pr("")
    pr("=" * 140)
    pr("r64 / r65 CONTRIBUTION TO THE >=130 deg BINS")
    pr("=" * 140)
    ii = P.idx([R64, R65])
    nm = np.isin(P.ri, ii)
    for lo, hi in [(130, 165), (165, 250), (250, 400)]:
        m = P.base & (P.asa >= lo) & (P.asa < hi)
        pr("   %-10s corpus %6.1f s   r64+r65 %5.1f s (%4.1f %%)   without them %6.1f s"
           % ("%d-%d" % (lo, hi), m.sum() / FS, (m & nm).sum() / FS,
              100 * (m & nm).sum() / max(m.sum(), 1), (m & ~nm).sum() / FS))
    json.dump(out, open(os.path.join(HERE, "_scratch", "sr_transit.json"), "w"), indent=1)
    open(os.path.join(HERE, "_scratch", "sr_transit.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
