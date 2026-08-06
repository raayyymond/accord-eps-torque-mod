#!/usr/bin/env python3
"""D6c -- Q4 powered properly.  V73 (route 5a) vs V72 (route 59), engaged creep.

D6b's Q4 ran on runs >= 5.12 s and got 2 runs per arm, which left burst rate and the p99 envelopes
"underpowered". This drops the run floor to 2.56 s, adds every 5.12 s WINDOW as a unit inside an
episode bootstrap, and quotes every ratio against a SPLIT-HALF NULL computed inside V72 with the
identical estimator. Speed census per arm, because a creep contrast between two single drives is
exactly where a speed mismatch manufactures an effect.

V73's live levers vs V72: friction lane x1.5 (`0xD2A44`) and clamp `0xC407E` 511 -> 850. The rate-lane
surface is V72's byte for byte (`_r5a_lib`), so this IS a friction/clamp contrast.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from d6_events import analytic, bp, runs  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

OUT = ROOT / "_d6c_v73.json"
RNG = np.random.default_rng(73722026)
CARRIER, RATCHET = (12.0, 28.0), (5.0, 12.0)
NF = 512


def harvest(build, vhi=4.0):
    """Per-window records + per-run burst stats for one build, engaged, below `vhi`."""
    wins, runstats = [], []
    for _, s, a, b, d, fs in runs(build, 0.0, vhi, True, 256):
        x = np.asarray(d["tq"][a:b], float)
        vv = np.abs(np.asarray(d["cs_v"][a:b], float))
        eff = np.abs(C.sustained(x, fs, 3.0))
        rat_e = np.abs(analytic(bp(x, fs, *RATCHET)))
        car_e = np.abs(analytic(bp(x, fs, *CARRIER)))
        bs = bursts(rat_e, fs)
        runstats.append(dict(run=(build, s, a), sec=(b - a) / fs, nb=len(bs),
                             rate=len(bs) / ((b - a) / fs),
                             duty=float(sum(j - i for i, j, _ in bs) / (b - a)),
                             v=float(np.mean(vv))))
        f = np.fft.rfftfreq(NF, 1 / fs)
        for i in range(0, len(x) - NF + 1, NF // 2):
            P = C.periodogram(x[i:i + NF], fs, NF, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            f0, p0 = G.locate(f, P, 5, 12, R=R)
            wins.append(dict(run=(build, s, a), build=build,
                             v=float(np.mean(vv[i:i + NF])), eff=float(np.mean(eff[i:i + NF])),
                             rat=float(np.percentile(rat_e[i:i + NF], 99)),
                             ring=float(np.percentile(car_e[i:i + NF], 99)),
                             f0=f0, prom=p0))
    return wins, runstats


def ep_ratio(A, B, key, nboot=4000, agg=np.median):
    """median(A)/median(B) with both sides resampled over RUNS."""
    def units(X):
        by = {}
        for r in X:
            by.setdefault(r["run"], []).append(r.get(key, np.nan))
        return [np.array(v, float) for v in by.values()]
    ua, ub = units(A), units(B)
    if len(ua) < 2 or len(ub) < 2:
        return (np.nan,) * 3 + (len(ua), len(ub))
    ga = np.concatenate(ua)
    gb = np.concatenate(ub)
    ga, gb = ga[np.isfinite(ga)], gb[np.isfinite(gb)]
    pt = agg(ga) / max(agg(gb), 1e-12)
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        va = np.concatenate([ua[i] for i in RNG.integers(0, len(ua), len(ua))])
        vb = np.concatenate([ub[i] for i in RNG.integers(0, len(ub), len(ub))])
        va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
        if len(va) and len(vb):
            dr[k] = agg(va) / max(agg(vb), 1e-12)
    return (float(pt), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)),
            len(ua), len(ub))


def split_half(X, key, nrep=400, agg=np.median):
    by = {}
    for r in X:
        by.setdefault(r["run"], []).append(r.get(key, np.nan))
    u = [np.array(v, float) for v in by.values()]
    if len(u) < 4:
        return np.nan, np.nan, np.nan
    out = []
    for _ in range(nrep):
        p = RNG.permutation(len(u))
        h = len(u) // 2
        a = np.concatenate([u[i] for i in p[:h]])
        b = np.concatenate([u[i] for i in p[h:]])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and agg(b) > 0:
            out.append(agg(a) / agg(b))
    if not out:
        return np.nan, np.nan, np.nan
    return (float(np.median(out)), float(np.percentile(out, 2.5)),
            float(np.percentile(out, 97.5)))


def main():
    L.install_fs()
    res = {}
    W, S = {}, {}
    for b in ("V72/r59", "V73/r5a"):
        W[b], S[b] = harvest(b)

    L.hdr("D6c Q4  SPEED / EXPOSURE CENSUS -- the arms must match before any ratio is read")
    print(f"  {'build':<10}{'runs':>6}{'sec':>8}{'windows':>9}{'v p25':>8}{'v med':>8}{'v p75':>8}"
          f"{'eff med':>10}")
    for b in W:
        v = np.array([r["v"] for r in W[b]])
        e = np.array([r["eff"] for r in W[b]])
        print(f"  {b:<10}{len(S[b]):>6}{sum(r['sec'] for r in S[b]):>8.1f}{len(W[b]):>9}"
              f"{np.percentile(v,25):>8.2f}{np.median(v):>8.2f}{np.percentile(v,75):>8.2f}"
              f"{np.median(e):>10.0f}")
        res.setdefault("census", {})[b] = dict(runs=len(S[b]), sec=sum(r["sec"] for r in S[b]),
                                               nwin=len(W[b]), vmed=float(np.median(v)),
                                               effmed=float(np.median(e)))

    L.hdr("D6c Q4  RATE vs AMPLITUDE vs RING -- V73 / V72, engaged, < 4 m/s")
    print(f"  {'quantity':<32}{'V73':>11}{'V72':>11}{'ratio V73/V72':>26}{'runs':>10}")
    A, B = W["V73/r5a"], W["V72/r59"]
    for lab, key in (("RATCHET p99 env 5-12 (counts)", "rat"),
                     ("RING    p99 env 12-28 (counts)", "ring"),
                     ("line frequency f0 (Hz)", "f0"),
                     ("line prominence", "prom")):
        r_, l_, h_, na, nb = ep_ratio(A, B, key)
        va = np.median([x[key] for x in A if np.isfinite(x[key])])
        vb = np.median([x[key] for x in B if np.isfinite(x[key])])
        print(f"  {lab:<32}{va:>11.2f}{vb:>11.2f}{r_:>14.3f}x [{l_:.2f},{h_:.2f}]{na:>5d}/{nb:<5d}")
        res.setdefault("q4", {})[lab] = dict(v73=float(va), v72=float(vb), r=r_, lo=l_, hi=h_)
    for lab, key in (("burst ONSETS per second", "rate"), ("burst DUTY cycle", "duty")):
        a = np.array([r[key] for r in S["V73/r5a"]], float)
        b = np.array([r[key] for r in S["V72/r59"]], float)
        dr = np.array([np.median(a[RNG.integers(0, len(a), len(a))]) /
                       max(np.median(b[RNG.integers(0, len(b), len(b))]), 1e-9)
                       for _ in range(4000)])
        lo, hi = np.nanpercentile(dr, [2.5, 97.5])
        print(f"  {lab:<32}{np.median(a):>11.3f}{np.median(b):>11.3f}"
              f"{np.median(a)/max(np.median(b),1e-9):>14.3f}x [{lo:.2f},{hi:.2f}]"
              f"{len(a):>5d}/{len(b):<5d}")
        res["q4"][lab] = dict(v73=float(np.median(a)), v72=float(np.median(b)),
                              r=float(np.median(a) / max(np.median(b), 1e-9)),
                              lo=float(lo), hi=float(hi))

    L.hdr("D6c Q4  THE NULL -- split-half inside V72 alone, identical estimator")
    for lab, key in (("RATCHET p99 env 5-12", "rat"), ("RING p99 env 12-28", "ring"),
                     ("line frequency f0", "f0")):
        n = split_half(B, key)
        print(f"  {lab:<26} null {n[0]:.3f} [{n[1]:.3f}, {n[2]:.3f}]")
        res.setdefault("null", {})[lab] = list(n)
    print("\n  A ratio inside its own build's null interval is not distinguishable from route noise.")

    # speed-matched replicate: restrict BOTH arms to the overlapping speed band
    L.hdr("D6c Q4b  SPEED-MATCHED REPLICATE -- both arms restricted to 1.5-3.5 m/s")
    A2 = [r for r in A if 1.5 <= r["v"] < 3.5]
    B2 = [r for r in B if 1.5 <= r["v"] < 3.5]
    print(f"  V73 windows {len(A2)}   V72 windows {len(B2)}")
    for lab, key in (("RATCHET p99 env 5-12", "rat"), ("RING p99 env 12-28", "ring"),
                     ("line frequency f0", "f0")):
        r_, l_, h_, na, nb = ep_ratio(A2, B2, key)
        print(f"  {lab:<26} {r_:>8.3f}x [{l_:.2f}, {h_:.2f}]   runs {na}/{nb}")
        res.setdefault("q4b", {})[lab] = dict(r=r_, lo=l_, hi=h_, na=na, nb=nb)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
