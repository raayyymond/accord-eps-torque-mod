# -*- coding: utf-8 -*-
"""studies/grind/modeld_rate_ci.py -- BOUND THE "KICK SETS THE RATE" READING.
Subagent `modelrate`, 2026-09-10.  ANALYSIS ONLY.

The one thing that could overturn the verdict: if the camera-locked comb is a phase-locked KICK that
re-triggers a free mode rather than a tone that adds to it, it sets episode RATE, not amplitude.
V288 is then a natural experiment, because V288 is the one build on which the comb's phase lock in
delivered torque demonstrably collapsed (bar R2_deb 0.501 -> 0.292 raw-floor-corrected, split-half
phase -29.5/-29.9 deg -> -67/+89 deg).  If the kick reading is right, V288 should show a LOWER
episode rate.  Observed: it does not -- it is slightly higher.  This file puts a CI on that.

Recipe matched to GRIND1-CENSUS-V288-R5E-2026-09-08.md SS 3 so the numbers are comparable:
  * episodes  = grind1_census_v282.py's recipe (2 s windows / 0.5 s step; present = 15-26 Hz peak
                prominence >= 8 AND 18-22 Hz bar amplitude >= 40 raw; episode = contiguous >= 0.5 s
                present run inside an engaged run).  Both arms are V282-family, so the 18-22 gate is
                the right gate for BOTH and no band-aware substitution is needed
                (`fvlc_lib.BAND` only departs from 18-22 for V289, which is not in this contrast).
  * exposure  = engaged seconds; reported also for the matched grinding regime (engaged & v < 12).
  * CI        = block bootstrap over 30 s engaged blocks, the census's own recipe -- extended here to
                the RATIO, which the census never computed, and to a ROUTE-CLUSTER bootstrap that
                also resamples the three V282 routes (the honest one, because the V282 arm's
                route-to-route scatter is 97-323 ep/h and there is only ONE V288 route).

Run: python modeld_rate_ci.py     (writes _scratch/modeld_rate_ci.txt)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import modeld_cadence_vs_ring as MC   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC.BAND["r3a"] = (18.0, 22.0)
MC.BAND["r3c"] = (18.0, 22.0)
ARMS = {"V282": ["r39", "r3a", "r3c"], "V288": ["r5e_v288"]}
BLK = 30.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def blocks_of(g, eps, mask, blk=BLK):
    """cut the stratum into contiguous `blk`-second blocks; each carries (exposure_s, n_episode_starts)."""
    P = g["P18"]
    n = int(round(blk / P))
    starts = np.array([a for a, b, f in eps], int)
    out = []
    for a, b in MC.runs(mask, 1):
        for s in range(a, b, n):
            e = min(s + n, b)
            expo = float(mask[s:e].sum()) * P
            if expo <= 0:
                continue
            k = int(((starts >= s) & (starts < e)).sum())
            out.append((expo, k))
    return np.array(out, float) if out else np.zeros((0, 2))


def rate_ci(B, nboot=20000, seed=11):
    rng = np.random.default_rng(seed)
    if len(B) == 0:
        return np.nan, np.nan, np.nan
    r = B[:, 1].sum() / B[:, 0].sum() * 3600.0
    idx = rng.integers(0, len(B), size=(nboot, len(B)))
    num = B[idx, 1].sum(1)
    den = B[idx, 0].sum(1)
    d = np.where(den > 0, num / den * 3600.0, np.nan)
    return float(r), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


def ratio_ci(Bnum, Bden, nboot=20000, seed=23, cluster=None):
    """CI on rate(num)/rate(den).  If `cluster` is a list of per-route block arrays for the DEN arm,
    the denominator also resamples ROUTES with replacement (cluster bootstrap)."""
    rng = np.random.default_rng(seed)
    r = (Bnum[:, 1].sum() / Bnum[:, 0].sum()) / (Bden[:, 1].sum() / Bden[:, 0].sum())
    out = []
    for _ in range(nboot):
        i = rng.integers(0, len(Bnum), len(Bnum))
        nn, nd = Bnum[i, 1].sum(), Bnum[i, 0].sum()
        if cluster is None:
            j = rng.integers(0, len(Bden), len(Bden))
            dn, dd = Bden[j, 1].sum(), Bden[j, 0].sum()
        else:
            pick = rng.integers(0, len(cluster), len(cluster))
            dn = dd = 0.0
            for p in pick:
                Bp = cluster[p]
                j = rng.integers(0, len(Bp), len(Bp))
                dn += Bp[j, 1].sum(); dd += Bp[j, 0].sum()
        if nd > 0 and dd > 0 and dn > 0:
            out.append((nn / nd) / (dn / dd))
    out = np.array(out)
    return float(r), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), out


def main():
    G, E = {}, {}
    cache = dict(np.load(os.path.join(SCR, "modeld_hotmask.npz"))) \
        if os.path.exists(os.path.join(SCR, "modeld_hotmask.npz")) else {}
    for arm, tags in ARMS.items():
        for tag in tags:
            pr("loading %s ..." % tag)
            G[tag] = MC.load(tag)
            eps, hot = MC.episodes_of(G[tag])
            E[tag] = eps
            pr("  %d episodes, engaged %.1f s" % (len(eps), G[tag]["eng"].sum() * G[tag]["P18"]))

    pr()
    pr("=" * 118)
    pr("EPISODE RATE, PER ARM -- reproducing GRIND1-CENSUS-V288-R5E SS 3's recipe and extending it")
    pr("=" * 118)
    pr("%-10s %-7s %6s %9s %9s %20s | %6s %9s %20s" %
       ("route", "build", "n eps", "eng s", "ep/eng h", "CI (30 s blocks)",
        "n v<12", "eng v<12 s", "ep/h in v<12 [CI]"))
    pr("-" * 118)
    STORE = {}
    for arm, tags in ARMS.items():
        for tag in tags:
            g, eps = G[tag], E[tag]
            Ball = blocks_of(g, eps, g["eng"])
            mlow = g["eng"] & (g["vego"] < 12)
            epl = [e for e in eps if mlow[e[0]:e[1]].mean() > 0.5]
            Blow = blocks_of(g, epl, mlow)
            r, lo, hi = rate_ci(Ball)
            rl, ll, hl = rate_ci(Blow)
            pr("%-10s %-7s %6d %9.1f %9.1f %9.1f-%-9.1f | %6d %9.1f %7.1f %5.1f-%-5.1f" %
               (tag, arm, len(eps), g["eng"].sum() * g["P18"], r, lo, hi,
                len(epl), mlow.sum() * g["P18"], rl, ll, hl))
            STORE[tag] = (Ball, Blow)
    pr()
    for lab, k in (("engaged (census definition)", 0), ("matched regime: engaged & v < 12 m/s", 1)):
        pr("=" * 118)
        pr("THE RATE RATIO  V288 / V282  --  %s" % lab)
        pr("=" * 118)
        Bn = np.vstack([STORE[t][k] for t in ARMS["V288"]])
        per = [STORE[t][k] for t in ARMS["V282"]]
        Bd = np.vstack(per)
        rn, ln, hn = rate_ci(Bn)
        rd, ld, hd = rate_ci(Bd)
        pr("  V288 arm : %.1f ep/h [%.1f, %.1f]   (%d blocks, %.0f s)" %
           (rn, ln, hn, len(Bn), Bn[:, 0].sum()))
        pr("  V282 pool: %.1f ep/h [%.1f, %.1f]   (%d blocks, %.0f s, 3 routes)" %
           (rd, ld, hd, len(Bd), Bd[:, 0].sum()))
        pr()
        for clab, cl in (("blocks only (treats route-to-route scatter as zero)", None),
                         ("ROUTE-CLUSTER (also resamples the 3 V282 routes) -- the honest one", per)):
            r, lo, hi, draws = ratio_ci(Bn, Bd, cluster=cl)
            pr("  ratio %.3f   95%% CI [%.3f, %.3f]   -- %s" % (r, lo, hi, clab))
            pr("     => a rate REDUCTION is excluded below %.0f %% (the CI's lower bound is x%.3f)."
               % (100 * (1 - lo), lo))
            for cut in (0.50, 0.70, 0.75, 0.80):
                verdict = "EXCLUDED" if lo > cut else "NOT excluded"
                pr("        a %2d %% reduction (ratio %.2f): %-12s  P(ratio <= %.2f) = %.4f"
                   % (round(100 * (1 - cut)), cut, verdict, cut, float(np.mean(draws <= cut))))
            pr()
    pr("=" * 118)
    pr("WHAT WOULD BE NEEDED")
    pr("=" * 118)
    Bn = np.vstack([STORE[t][0] for t in ARMS["V288"]])
    Bd = np.vstack([STORE[t][0] for t in ARMS["V282"]])
    # per-30 s-block episode counts -> overdispersion, then the exposure needed for a target CI width
    for lab, B in (("V288 (1 route)", Bn), ("V282 pool (3 routes)", Bd)):
        k = B[:, 1]
        mu, var = k.mean(), k.var(ddof=1)
        pr("  %-22s  %d blocks  mean %.3f ep/block  var %.3f  overdispersion %.2f"
           % (lab, len(B), mu, var, var / max(mu, 1e-9)))
    pr()
    pr("  For a Poisson-with-overdispersion count, the relative SE of a rate is sqrt(phi/N_ep).")
    pr("  Detecting a rate RATIO of x with 95 %% confidence needs, in EACH arm, roughly")
    pr("      N_ep  >=  phi * (1.96 / ln(x))^2 * 2")
    for x in (0.70, 0.80, 0.90):
        k = Bn[:, 1]
        phi = max(k.var(ddof=1) / max(k.mean(), 1e-9), 1.0)
        need = phi * (1.96 / abs(np.log(x))) ** 2 * 2
        pr("      ratio %.2f (a %2d %% reduction): N_ep >= %5.0f per arm  =>  ~%.1f routes like r5e (46 ep)"
           % (x, round(100 * (1 - x)), need, need / 46.0))
    with open(os.path.join(SCR, "modeld_rate_ci.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/modeld_rate_ci.txt")


if __name__ == "__main__":
    main()
