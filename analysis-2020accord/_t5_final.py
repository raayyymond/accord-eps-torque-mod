#!/usr/bin/env python3
"""Task #5 -- the headline: the GROUP ladder re-priced at the measured rateKey, its monotonicity,
the V70-vs-V62/V67 contrast, and the two refutation checks the brief asked for.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r50_lib as R50           # noqa: E402
import _t5_ratekey_lib as T      # noqa: E402
import _t5_samples as S          # noqa: E402
from _t5_analyze import IMG, NOMINAL, ORDER, ZERO_LANE, hdr, slab   # noqa: E402
from _t5_ladder import RNG, ep_median_ci, spearman, split_half_null  # noqa: E402
from _t5_ladder import _WRECS, wrec_response                         # noqa: E402

VHI = 20 / 3.6                    # the stratum the RECORDED ladder used
GROUPS = [("V61  both taps ZEROED", ["V61/r31"]),
          ("stock rate lane", ["V59/r2c", "V64/r35", "V58/r2b"]),
          ("V62/V65  sar x2 (r24+r26)", ["V62/r37", "V65/r3a", "V65/r3b"]),
          ("V67/V68  LKAS arm (r24)", ["V67/r47", "V68/r4e"]),
          ("V70  table x2 (r24)", ["V70/r50"]),
          ("V69  table x4 (r24)", ["V69/r4f"])]


def repriced(store, b, scale=T.SCALE_A, band="env18", thr=300.0, vhi=VHI):
    if b in ZERO_LANE:
        return 0.0
    sl = slab(store, b, eng=1, vhi=vhi)
    m = sl[band] >= thr
    if m.sum() < 20:
        m = np.ones(len(sl[band]), bool)
    sc = T.speed_counts(sl["v"][m]).astype(np.int64)
    rk = (sl["rate"][m] * scale).astype(np.int64)
    return float(np.median(T.delivered(IMG[b], sc, rk, np.ones(len(sc), bool))))


def main():
    store = S.load()

    # ---------------------------------------------------------------------------------------------
    hdr("PART G1 -- THE LADDER, pooled the way the RECORD pools it, re-priced at the MEASURED rateKey")
    print("  Response = median e_18-22 over engaged windows below 20 km/h -- the stratum that")
    print("  reproduces the ladder on file (V61 2501 / stock 879 / V62-V65 168 / V67-V68 109 /")
    print("  V69 746). Dose = median per-sample delivered multiplier over that group's OWN grind-#1")
    print("  burst samples. Both axis scales are shown; they agree to 3 decimals here.")
    rows = []
    print(f"\n    {'group':28s} {'nom@603':>8s} {'repA':>7s} {'repB':>7s} | {'median':>8s} "
          f"{'[95% CI]':>20s} {'nwin':>6s} {'nep':>4s} | {'split-half null':>24s}")
    for gname, gb in GROUPS:
        v = np.concatenate([wrec_response(b, "e_18-22", 1, 0.0, VHI)[0] for b in gb])
        ep = np.concatenate([wrec_response(b, "e_18-22", 1, 0.0, VHI)[1] for b in gb])
        m, lo, hi, n, nep = ep_median_ci(v, ep)
        nl, nlo, nhi = split_half_null(v, ep)
        nom = float(np.mean([NOMINAL[b] for b in gb]))
        rA = float(np.mean([repriced(store, b, T.SCALE_A) for b in gb]))
        rB = float(np.mean([repriced(store, b, T.SCALE_B) for b in gb]))
        rows.append(dict(g=gname, nom=nom, rA=rA, rB=rB, m=m, v=v, ep=ep))
        print(f"    {gname:28s} {nom:8.3f} {rA:7.3f} {rB:7.3f} | {m:8.1f} "
              f"{'[%7.1f, %7.1f]' % (lo, hi):>20s} {n:6d} {nep:4d} | "
              f"{('%.3f [%.3f, %.3f]' % (nl, nlo, nhi)) if np.isfinite(nl) else 'n/a (<4 episodes)':>24s}")

    print("\n    THE LADDER AS A SEQUENCE (dose -> response):")
    for lab, k in (("nominal @603", "nom"), ("re-priced A", "rA"), ("re-priced B", "rB")):
        o = sorted(rows, key=lambda r: r[k])
        print(f"      {lab:14s}  " + "   ".join(f"{r[k]:.3f}x->{r['m']:.0f}" for r in o))

    print("\n    MONOTONICITY (Spearman rho; -1 = perfectly monotone decreasing = 'more dose is")
    print("    always better'). CI resamples EPISODES inside each group and re-ranks.")
    for lab, k in (("nominal @603", "nom"), ("re-priced A", "rA"), ("re-priced B", "rB")):
        x = np.array([r[k] for r in rows], float)
        y = np.array([r["m"] for r in rows], float)
        rho = spearman(x, y)
        dr = []
        for _ in range(4000):
            yy = []
            for r in rows:
                ue = np.unique(r["ep"])
                per = [r["v"][r["ep"] == e] for e in ue]
                i = RNG.integers(0, len(per), len(per))
                yy.append(np.median(np.concatenate([per[j] for j in i])))
            dr.append(spearman(x, np.array(yy)))
        dr = np.array(dr)
        print(f"      {lab:14s} rho = {rho:+.3f}  [{np.percentile(dr, 2.5):+.3f}, "
              f"{np.percentile(dr, 97.5):+.3f}]   P(perfectly monotone, rho<=-0.999) = "
              f"{(dr <= -0.999).mean():.3f}")

    # ---------------------------------------------------------------------------------------------
    hdr("PART G2 -- refutation check (a): do grind-#1 bursts sit BELOW rateKey 400?")
    print("  400 is the top of the FLAT segment that V69/V70 raised. Below it, their dose is")
    print("  delivered in FULL (4.000x / 2.000x); at 1500 they are byte-identical to stock.")
    print("  Fraction of grind-#1 burst SAMPLES (env18 >= 300, engaged, <20 km/h) by rateKey band:")
    print(f"    {'build':10s} {'n':>7s} | " + "".join(f"{c:>12s}" for c in
          ("A: <400", "400-1400", ">=1400", "B: <400", "B: >=400")))
    tot = {k: 0 for k in ("a1", "a2", "a3", "b1", "b2")}
    N = 0
    for b in ORDER:
        sl = slab(store, b, eng=1, vhi=VHI)
        m = sl["env18"] >= 300
        if m.sum() < 20:
            continue
        rc = sl["rate"][m]
        a, bb = rc * T.SCALE_A, rc * T.SCALE_B
        c = [(a < 400).mean(), ((a >= 400) & (a < 1400)).mean(), (a >= 1400).mean(),
             (bb < 400).mean(), (bb >= 400).mean()]
        for k, key in zip(c, ("a1", "a2", "a3", "b1", "b2")):
            tot[key] += k * m.sum()
        N += m.sum()
        print(f"    {b:10s} {int(m.sum()):7d} | " + "".join(f"{100 * x:11.3f}%" for x in c))
    print(f"    {'POOLED':10s} {N:7d} | " + "".join(f"{100 * tot[k] / N:11.3f}%"
                                                    for k in ("a1", "a2", "a3", "b1", "b2")))

    print("\n  And the ceiling: the LARGEST |rate_c| anywhere in the corpus, engaged or not,")
    print("  against the rateKey the collapse needs.")
    mx = 0.0
    for b in ORDER:
        for r in store[b]:
            mx = max(mx, float(r["rate"].max()))
    print(f"    max |rate_c| over every cached frame of every build = {mx:.0f} deg/s")
    print(f"      -> rateKey  {mx * T.SCALE_A:.0f} on scale A   |   {mx * T.SCALE_B:.0f} on scale B")
    print(f"    rateKey 1500 (where V69/V70 revert to stock) needs {1500 / T.SCALE_A:.0f} deg/s"
          f" on scale A, {1500 / T.SCALE_B:.0f} deg/s on scale B")

    # ---------------------------------------------------------------------------------------------
    hdr("PART G3 -- refutation check (c): can the corpus separate 'collapses at HIGH RATE' from")
    print("  'collapses at HIGH SPEED'?  V69/V70's surface decays in BOTH. Split the delivered")
    print("  multiplier into its two factors at the measured burst population.")
    print(f"\n    {'build':10s} {'deliv @ measured (speed,rate)':>30s} "
          f"{'deliv @ measured speed, rate:=0':>32s} {'deliv @ 0 km/h, measured rate':>31s}")
    for b in ORDER:
        if b in ZERO_LANE:
            continue
        sl = slab(store, b, eng=1, vhi=VHI)
        m = sl["env18"] >= 300
        if m.sum() < 20:
            continue
        sc = T.speed_counts(sl["v"][m]).astype(np.int64)
        rk = (sl["rate"][m] * T.SCALE_A).astype(np.int64)
        one = np.ones(len(sc), bool)
        a = np.median(T.delivered(IMG[b], sc, rk, one))
        bq = np.median(T.delivered(IMG[b], sc, np.zeros_like(rk), one))
        c = np.median(T.delivered(IMG[b], np.zeros_like(sc), rk, one))
        print(f"    {b:10s} {a:30.3f} {bq:32.3f} {c:31.3f}")
    print("\n    Reading: column 2 isolates the SPEED factor (rate pinned to the flat segment),")
    print("    column 3 the RATE factor (speed pinned to 0). If col2 == col1 and col3 == 1.000")
    print("    the rate axis contributed NOTHING at the grind and the two are separable here.")

    # ---------------------------------------------------------------------------------------------
    hdr("PART G4 -- GRIND #2: is its rateKey elevation real WITHIN a route, and is it >= 1126?")
    print("  Within-route contrast: median |rate_c| during 40-49 Hz bursts vs the SAME route's")
    print("  engaged baseline in the SAME speed stratum. A route-level median is not a control.")
    for vlo, vhi, vlab in ((0.0, 4.0, "creep <14.4 km/h"), (14.0, 1e9, "highway >=50 km/h")):
        print(f"\n    --- {vlab} ---")
        print(f"    {'build':10s} {'nburst':>7s} {'burst rate p50':>15s} {'base rate p50':>14s} "
              f"{'ratio':>7s} | {'A rk p50':>9s} {'%>=1126':>8s} {'%>=1500':>8s} | {'deliv':>7s}")
        for b in ORDER:
            sl = slab(store, b, eng=1, vlo=vlo, vhi=vhi)
            if sl is None:
                continue
            m = sl["env40"] >= 150
            if m.sum() < 20:
                continue
            rb, ra = sl["rate"][m], sl["rate"][~m]
            rkA = rb * T.SCALE_A
            d = (0.0 if b in ZERO_LANE else
                 float(np.median(T.delivered(IMG[b],
                                             T.speed_counts(sl["v"][m]).astype(np.int64),
                                             (rb * T.SCALE_A).astype(np.int64),
                                             np.ones(int(m.sum()), bool)))))
            base = np.median(ra) if len(ra) else np.nan
            print(f"    {b:10s} {int(m.sum()):7d} {np.median(rb):15.1f} {base:14.1f} "
                  f"{(np.median(rb) / base if base else np.nan):7.2f} | "
                  f"{np.percentile(rkA, 50):9.1f} {100 * (rkA >= 1126).mean():7.2f}% "
                  f"{100 * (rkA >= 1500).mean():7.2f}% | {d:7.3f}")

    # ---------------------------------------------------------------------------------------------
    hdr("PART G5 -- V70 vs its neighbours on grind #1: the record's OWN stratified estimator")
    print("  `_grind2_lib.boot_cellwise` -- log-ratio stratified on (eng, speed bin, effort bin,")
    print("  rate bin), episode-resampled, weighted by the smaller episode count per cell.")
    print("  Each contrast is quoted against BOTH arms' split-half nulls.")
    rec = {b: [r for r in _WRECS[b] if r["eng"] == 1 and r["v"] < VHI] for b in ORDER}
    pairs = [("V70/r50", "V62/r37"), ("V70/r50", "V67/r47"), ("V70/r50", "V69/r4f"),
             ("V70/r50", "V59/r2c"), ("V69/r4f", "V62/r37"), ("V69/r4f", "V59/r2c"),
             ("V62/r37", "V59/r2c"), ("V67/r47", "V59/r2c")]
    print(f"\n    {'contrast':24s} {'ratio':>7s} {'[95% CI]':>18s} {'ncell':>6s} "
          f"{'nepA':>5s} {'nepB':>5s} | {'null A':>22s} {'null B':>22s}")
    for a, b in pairs:
        r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(rec[a], rec[b], "e_18-22", RNG, nboot=1500)
        nA = split_half_null(np.array([x["e_18-22"] for x in rec[a]]),
                             np.array([str(x["ep"]) for x in rec[a]]))
        nB = split_half_null(np.array([x["e_18-22"] for x in rec[b]]),
                             np.array([str(x["ep"]) for x in rec[b]]))
        f = lambda t: ("%.2f [%.2f, %.2f]" % t) if np.isfinite(t[0]) else "n/a"
        print(f"    {a + ' / ' + b:24s} {r:7.3f} {'[%.3f, %.3f]' % (lo, hi):>18s} {nc:6d} "
              f"{na:5d} {nb:5d} | {f(nA):>22s} {f(nB):>22s}")


if __name__ == "__main__":
    main()
