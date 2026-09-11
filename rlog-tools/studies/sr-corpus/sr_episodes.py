# -*- coding: utf-8 -*-
"""sr_episodes.py -- the episode census and the corrected estimator suite, applied to any route set.

PRIMARY FIT (no paramsd angle offset anywhere):
    radians(steeringAngleDeg_RAW) = sR * u + off,     u = denom / curvature_factor
Reported three ways (TLS / OLS(y|u) / OLS(u|y) inverted).  Where the three disagree the bin is NOT
a measurement.  The fitted `off` is reported beside liveParameters.angleOffsetDeg, never taken from it.

Run:  python sr_episodes.py r64r65      -- the two new large-angle routes, first
      python sr_episodes.py corpus      -- all 82 routes
      python sr_episodes.py arms        -- firmware/engagement invariance on episodes
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sr_lib2 import fit3, boot, episodes, episode_stats, stationary, FS, MIN_CLUSTERS  # noqa: E402
from sr_routes import BUILD, arm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
L = []
R64 = "75604b0a432fdc89_00000064--ce6b0b0ebb"
R65 = "75604b0a432fdc89_00000065--b9f78988bd"
BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 70), (70, 100),
        (100, 150), (150, 250), (250, 400)]
SHIFTS = np.arange(-30, 31, 3)          # +-300 ms in 30 ms steps (100 Hz samples)


def pr(s=""):
    print(s, flush=True)
    L.append(s)


class P2:
    """pooled cache + per-route slices + the shift machinery."""

    def __init__(self, path):
        z = np.load(path, allow_pickle=True)
        g = lambda k: z[k].astype(np.float64)
        self.routes = [str(x) for x in z["routes"]]
        self.t = g("t"); self.sa_deg = g("sa_deg"); self.ang = np.radians(g("ang_deg"))
        self.cfac = g("cfac"); self.denom = g("denom"); self.v = g("v"); self.rate = g("rate")
        self.drv = np.abs(g("drv")); self.eng = z["eng"] > 0.5; self.pressed = z["pressed"] > 0.5
        self.calok = z["calok"] > 0.5; self.aoff = g("aoff"); self.ri = z["ri"].astype(int)
        self.blk = z["blk"]
        self.asa = np.abs(self.sa_deg)
        self.u = self.denom / self.cfac                      # <- the regressor; NO angle offset
        self.base = (self.calok & (self.v > 4.0) & (np.abs(self.rate) < 20.0)
                     & np.isfinite(self.u) & np.isfinite(self.ang))
        # route slices (arrays are concatenated in route order, time-sorted within a route)
        self.sl = {}
        for i in range(len(self.routes)):
            k = np.flatnonzero(self.ri == i)
            if len(k):
                self.sl[i] = (k[0], k[-1] + 1)

    def idx(self, names):
        return [self.routes.index(n) for n in names if n in self.routes]

    def shifted_u(self, k):
        """u sampled k samples LATER than the angle (k>0 => yaw lags angle), NaN where the
        shift crosses a time gap or a route boundary."""
        n = len(self.u)
        out = np.full(n, np.nan)
        src = np.arange(n) + k
        ok = (src >= 0) & (src < n)
        srcc = np.clip(src, 0, n - 1)
        ok &= self.ri[srcc] == self.ri
        dt = self.t[srcc] - self.t
        ok &= np.abs(dt - k / FS) < 0.02
        out[ok] = self.u[srcc[ok]]
        return out


def bin_report(P, m, title, bins=BINS, do_shift=True, seed=1):
    pr("=" * 150)
    pr(title)
    pr("=" * 150)
    pr("   ALL GATED FRAMES (quasi-static gate only)                    |  STEADY EPISODES (|sa| & v flat +-25%%, >=0.6 s)")
    pr("   %-9s %7s %7s %7s %7s %8s | %6s %7s %8s %7s %7s %7s %7s %8s | %-11s"
       % ("|sa| deg", "n(s)", "TLS", "OLSy", "OLSu", "spread", "n_ep", "tot(s)", "longest", "TLS", "OLSy", "OLSu", "spread", "off(deg)", "lead/lag"))
    rows = []
    for lo, hi in bins:
        ok = m & (P.asa >= lo) & (P.asa < hi)
        n = int(ok.sum())
        r = fit3(P.u[ok], P.ang[ok]) if n >= 200 else None
        # --- episodes, found per route then unioned
        emask = np.zeros(len(P.u), bool)
        eps_all = []
        for i in np.unique(P.ri[m]) if m.any() else []:
            a, b = P.sl[i]
            sub = slice(a, b)
            mm = m[sub]
            t_, asa_, v_, rate_ = P.t[sub], P.asa[sub], P.v[sub], P.rate[sub]
            asa2 = np.where(mm, asa_, np.nan)
            eps, _ = episodes(t_, asa2, v_, rate_, lo, hi)
            for (i0, i1) in eps:
                emask[a + i0:a + i1 + 1] = True
                eps_all.append(t_[i1] - t_[i0])
        est = fit3(P.u[emask], P.ang[emask]) if emask.sum() >= 200 else None
        n_ep = len(eps_all)
        tot = float(np.sum(eps_all)) if n_ep else 0.0
        lon = float(np.max(eps_all)) if n_ep else 0.0
        # --- lead/lag on the ALL-FRAMES mask (episodes are usually too thin to sweep)
        verdict = ""
        if do_shift and n >= 400:
            vals = []
            for k in SHIFTS:
                us = P.shifted_u(int(k))
                rr = fit3(us[ok], P.ang[ok])
                vals.append(np.nan if rr is None else rr["tls"])
            verdict, rng, at = stationary(SHIFTS / FS * 1000.0, vals)
            verdict = "%s d=%.2f" % (verdict.split(" (")[0].replace("MONOTONE", "MONO"), rng)
        f = lambda d, k: ("%7.2f" % d[k]) if d else "     --"
        pr("   %-9s %7.0f %s %s %s %8.2f | %6d %7.1f %8.2f %s %s %s %7s %8s | %-11s"
           % ("%d-%d" % (lo, hi), n / FS, f(r, "tls"), f(r, "ols_y"), f(r, "ols_u"),
              r["spread"] if r else np.nan, n_ep, tot, lon,
              f(est, "tls"), f(est, "ols_y"), f(est, "ols_u"),
              ("%.2f" % est["spread"]) if est else "--",
              ("%.2f" % np.degrees(est["off"])) if est else "--", verdict))
        rows.append(dict(lo=lo, hi=hi, n_s=n / FS, all=r, n_ep=n_ep, tot_s=tot, longest_s=lon,
                         ep=est, verdict=verdict,
                         npos=int((m & (P.sa_deg >= lo) & (P.sa_deg < hi)).sum()),
                         nneg=int((m & (-P.sa_deg >= lo) & (-P.sa_deg < hi)).sum())))
    pr("")
    pr("   SIGN BALANCE (n positive / n negative angle, gated frames):")
    pr("   " + "  ".join("%d-%d: %d/%d" % (r["lo"], r["hi"], r["npos"], r["nneg"]) for r in rows))
    pr("")
    return rows


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "r64r65"
    P = P2(os.path.join(HERE, "_scratch", "pooled.npz"))

    if what == "r64r65":
        ii = P.idx([R64, R65])
        pr("routes found: %s" % [P.routes[i] for i in ii])
        for nm, i in zip(("r64", "r65"), ii):
            m = P.base & (P.ri == i)
            tot = (P.ri == i).sum() / FS
            pr("")
            pr("%s = %s   cached %.0f s, gated %.0f s   max |sa| %.0f deg   engaged %.0f %%"
               % (nm, P.routes[i], tot, m.sum() / FS, P.asa[P.ri == i].max(),
                  100 * P.eng[P.ri == i].mean()))
        m = P.base & np.isin(P.ri, ii)
        pr("")
        pr("   |sa| > 45 deg, gated: %.1f s   (engaged %.1f s / manual %.1f s)"
           % ((m & (P.asa > 45)).sum() / FS, (m & (P.asa > 45) & P.eng).sum() / FS,
              (m & (P.asa > 45) & ~P.eng).sum() / FS))
        pr("")
        bin_report(P, m, "E1  r64 + r65 POOLED -- THE EPISODE CENSUS ABOVE 45 deg IS THE POINT")
        for nm, i in zip(("r64", "r65"), ii):
            bin_report(P, P.base & (P.ri == i), "E2  %s ALONE" % nm,
                       bins=[(45, 70), (70, 100), (100, 150), (150, 250), (250, 400)])
    elif what == "corpus":
        bin_report(P, P.base, "E3  WHOLE CORPUS (82 routes) -- episode census + three estimators")
    elif what == "arms":
        armof = np.array([arm(r) for r in P.routes])[P.ri]
        for a in ["stock", "V52-V76", "V80-V122", "V276-V283", "V288-V289"]:
            mm = P.base & (armof == a)
            if mm.sum() < 20000:
                continue
            bin_report(P, mm, "E4  ARM %s" % a, bins=[(20, 45), (45, 90), (90, 400)], do_shift=False)
        for lbl, mm in (("ENGAGED", P.base & P.eng), ("MANUAL", P.base & ~P.eng)):
            bin_report(P, mm, "E5  %s" % lbl, bins=[(20, 45), (45, 90), (90, 400)], do_shift=False)

    with open(os.path.join(HERE, "_scratch", "sr_episodes_%s.txt" % what), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
