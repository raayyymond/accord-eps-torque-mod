# -*- coding: utf-8 -*-
"""sr_final.py -- FIXED-EFFECTS estimator: every route gets its OWN free intercept, one common
slope.  This is the correct answer to the pooling problem: it uses NOTHING from paramsd's
angleOffsetDeg (each route's offset is absorbed by its own intercept) and it does not require any
single route to identify the slope on its own.  Within-route demeaning, then TLS/OLS through the
origin on the demeaned data, with a route-level cluster bootstrap."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sr_episodes import P2, BINS
from sr_lib2 import episodes, stationary, FS, MIN_CLUSTERS
from sr_routes import arm
L = []
def pr(s=""):
    print(s, flush=True); L.append(s)

def demean(u, y, ri):
    uq, inv = np.unique(ri, return_inverse=True)
    n = np.bincount(inv, minlength=len(uq))
    mu = np.bincount(inv, weights=u, minlength=len(uq)) / n
    my = np.bincount(inv, weights=y, minlength=len(uq)) / n
    return u - mu[inv], y - my[inv], len(uq), (my - 0)  # offsets recovered later

def three(u, y):
    suu = float(u @ u); suy = float(u @ y); syy = float(y @ y)
    if suu <= 0 or suy == 0: return None
    oy = suy / suu; ou = syy / suy
    tr = suu + syy; disc = np.sqrt(max((suu - syy) ** 2 + 4 * suy * suy, 0.0))
    lam = 0.5 * (tr - disc)
    return dict(tls=float(-suy / (lam - suu)), ols_y=float(oy), ols_u=float(ou), spread=float(abs(ou - oy)))

def fe_fit(u, y, ri, nboot=600, seed=2):
    uc, yc, nr, _ = demean(u, y, ri)
    r = three(uc, yc)
    if r is None: return None
    r["nroutes"] = nr
    if nr >= MIN_CLUSTERS:
        uq, inv = np.unique(ri, return_inverse=True)
        order = np.argsort(inv); inv_s = inv[order]; uu = uc[order]; yy = yc[order]
        bnd = np.searchsorted(inv_s, np.arange(len(uq) + 1))
        A = np.array([uu[bnd[i]:bnd[i+1]] @ uu[bnd[i]:bnd[i+1]] for i in range(len(uq))])
        B = np.array([uu[bnd[i]:bnd[i+1]] @ yy[bnd[i]:bnd[i+1]] for i in range(len(uq))])
        C = np.array([yy[bnd[i]:bnd[i+1]] @ yy[bnd[i]:bnd[i+1]] for i in range(len(uq))])
        rng = np.random.default_rng(seed); p = rng.integers(0, len(uq), size=(nboot, len(uq)))
        a, b, c = A[p].sum(1), B[p].sum(1), C[p].sum(1)
        tr = a + c; disc = np.sqrt(np.maximum((a - c) ** 2 + 4 * b * b, 0)); lam = 0.5 * (tr - disc)
        with np.errstate(divide="ignore", invalid="ignore"):
            s = -b / (lam - a)
        s = s[np.isfinite(s)]
        if len(s) > nboot // 4:
            r["ci"] = (float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5)))
    return r

def main():
    P = P2(os.path.join(HERE, "_scratch", "pooled.npz"))
    armof = np.array([arm(x) for x in P.routes])[P.ri]
    pr("=" * 146)
    pr("G1  FIXED-EFFECTS FIT (per-route intercept, common slope) -- NO paramsd angle offset anywhere")
    pr("=" * 146)
    pr("   %-9s %7s %6s %7s %7s %7s %7s %-15s | %6s %7s %8s %7s %7s %-15s | %-22s"
       % ("|sa| deg", "n(s)", "route", "TLS", "OLSy", "OLSu", "spread", "95% CI (route)",
          "n_ep", "tot(s)", "longest", "TLS_ep", "sprd", "95% CI (ep)", "lead/lag"))
    rows = []
    for lo, hi in BINS:
        ok = P.base & (P.asa >= lo) & (P.asa < hi)
        if ok.sum() < 300: continue
        r = fe_fit(P.u[ok], P.ang[ok], P.ri[ok])
        emask = np.zeros(len(P.u), bool); eps_all = []
        for i in np.unique(P.ri[P.base]):
            a, b = P.sl[i]; sub = slice(a, b)
            asa2 = np.where(P.base[sub], P.asa[sub], np.nan)
            e, _ = episodes(P.t[sub], asa2, P.v[sub], P.rate[sub], lo, hi)
            for (i0, i1) in e:
                emask[a + i0:a + i1 + 1] = True; eps_all.append(P.t[sub][i1] - P.t[sub][i0])
        re = fe_fit(P.u[emask], P.ang[emask], P.ri[emask]) if emask.sum() >= 300 else None
        vals = []
        for k in np.arange(-30, 31, 3):
            us = P.shifted_u(int(k)); mm = ok & np.isfinite(us)
            rr = fe_fit(us[mm], P.ang[mm], P.ri[mm], nboot=1)
            vals.append(np.nan if rr is None else rr["tls"])
        vd, rng_, at = stationary(np.arange(-30, 31, 3) / FS * 1000, vals)
        ci = ("[%5.2f,%5.2f]" % r["ci"]) if r and "ci" in r else "(too few routes)"
        cie = ("[%5.2f,%5.2f]" % re["ci"]) if re and "ci" in re else "(too few routes)"
        pr("   %-9s %7.0f %6d %7.2f %7.2f %7.2f %7.2f %-15s | %6d %7.1f %8.2f %7s %7s %-15s | %s d=%.2f"
           % ("%d-%d" % (lo, hi), ok.sum() / FS, r["nroutes"], r["tls"], r["ols_y"], r["ols_u"],
              r["spread"], ci, len(eps_all), float(np.sum(eps_all)) if eps_all else 0,
              float(np.max(eps_all)) if eps_all else 0,
              ("%.2f" % re["tls"]) if re else "--", ("%.2f" % re["spread"]) if re else "--",
              cie, vd.split(" (")[0].replace("MONOTONE", "MONO"), rng_))
        rows.append(dict(lo=lo, hi=hi, n_s=ok.sum() / FS, fe=r, ep=re, n_ep=len(eps_all),
                         longest=float(np.max(eps_all)) if eps_all else 0.0, leadlag=vd, ll_range=rng_))
    pr("")
    pr("=" * 146)
    pr("G2  INVARIANCE ON THE FIXED-EFFECTS FIT -- firmware arm, engagement, driver torque, sign")
    pr("=" * 146)
    for band in ((20, 45), (45, 90), (90, 400)):
        lo, hi = band
        pr("   |sa| %d-%d deg" % band)
        groups = [("arm " + a, armof == a) for a in ["stock", "V52-V76", "V80-V122", "V276-V283", "V288-V289"]]
        groups += [("ENGAGED", P.eng), ("MANUAL", ~P.eng),
                   ("|drv|<30", P.drv < 30), ("|drv|>=150", P.drv >= 150),
                   ("LEFT", P.sa_deg > 0), ("RIGHT", P.sa_deg < 0)]
        for nm, gm in groups:
            ok = P.base & gm & (P.asa >= lo) & (P.asa < hi)
            if ok.sum() < 500:
                pr("      %-16s  -- (%.0f s)" % (nm, ok.sum() / FS)); continue
            r = fe_fit(P.u[ok], P.ang[ok], P.ri[ok])
            ci = ("[%5.2f,%5.2f]" % r["ci"]) if r and "ci" in r else "(%d routes, no CI)" % r["nroutes"]
            pr("      %-16s %7.2f  spread %5.2f  %-18s %7.0f s  %2d routes"
               % (nm, r["tls"], r["spread"], ci, ok.sum() / FS, r["nroutes"]))
        pr("")
    json.dump([dict(lo=r["lo"], hi=r["hi"], n_s=r["n_s"], tls=r["fe"]["tls"],
                    spread=r["fe"]["spread"], ci=r["fe"].get("ci"), n_ep=r["n_ep"],
                    longest=r["longest"], leadlag=r["leadlag"], ll_range=r["ll_range"],
                    tls_ep=r["ep"]["tls"] if r["ep"] else None) for r in rows],
              open(os.path.join(HERE, "_scratch", "sr_final.json"), "w"), indent=1)
    open(os.path.join(HERE, "_scratch", "sr_final.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")

if __name__ == "__main__":
    main()
