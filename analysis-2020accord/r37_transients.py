#!/usr/bin/env python3
"""Is V62's transient behaviour a REGRESSION, or within the family of V59/V61?

THE QUESTION. The operator's new symptom is marked by TRANSIENTS, not by a mode: route 37's
instant #1 carries the route's only |d(tq)| > 2000 counts/10 ms burst (max 3,694). Band power
cannot answer whether that is out of family. This does.

STATISTIC. g = |tq[i+1] - tq[i]| on the ~100 Hz torsion-bar channel, engaged (latActive) only,
inside contiguous runs. Reported as an EXCURSION RATE (events per engaged second) so routes of
different length are comparable, plus the full percentile distribution.

🛑 g IS A HIGH-PASS OF tq, NOT AN INDEPENDENT MEASUREMENT. For a sinusoid at f, amplitude A,
g ~ 2*pi*f*A*dt: a 21 Hz mode contributes ~1.32*A per 10 ms, an 8 Hz ratchet only ~0.50*A. So g
is dominated by the SAME 18-22 Hz content the band-power pass showed V62 suppressing ~8-42x.
The prior is therefore that V62's g should FALL. Finding V62 at or above the controls would mean
transient content grew enough to outrun a large drop in the mode -- which is why this is a sharp
test rather than a restatement.

DIRECT STANDARDIZATION, not a ratio-of-ratios. Rates with zero counts make geometric means blow
up, so both builds are re-weighted onto V62's speed (or rate) exposure distribution over the
COMMON SUPPORT, and the ratio is taken of the two standardized rates. A stratum with no exposure
on either side is dropped, never imputed.

CONTROLS, all through the identical pipeline:
  * SPLIT-HALF within build (episodes by parity) -> the noise floor for a rate ratio.
  * V59 vs V64 -> true cross-route null (V64 == V59 spectrally, detector never armed). Thin.
  * A THRESHOLD LADDER 200/500/1000/2000/3000. If V62/control is ~1 at 200 (ordinary steering
    activity) and only departs in the tail, the effect is specific to transients. If it is
    shifted at every threshold, it is a global scale difference between routes. This is the
    transient analogue of the 30-40 Hz negative band.

Usage:  python r37_transients.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from _r31_common import runs_of  # noqa: E402

BUILDS = {
    "V62": ("_cache_r37", "r37s", list(range(15))),
    "V59": ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    "V61": ("_cache_r31", "r31s", [0, 1, 2, 3]),
    "V64": ("_cache_r35", "r35s", [0, 1, 2]),
}
THRESH = [200, 500, 1000, 2000, 3000]
SPEED_BINS = [0, 2, 4, 7, 11, 16, 22, np.inf]
RATE_BINS = [0, 1, 2, 4, 8, 16, 32, np.inf]
MIN_SEC = 2.0            # per-stratum exposure floor on BOTH sides
NBOOT = 3000
RNG = np.random.default_rng(20260731)


def harvest(build, min_run=100):
    """Frame-pair records inside contiguous engaged runs: gap, speed, |rate|, dt, episode."""
    cd, pfx, segs = BUILDS[build]
    g, sd, v, ra, dt, ep = [], [], [], [], [], []
    k = 0
    for s in segs:
        p = ROOT / cd / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = np.load(p)
        mask = d["cc_lat"] > 0.5
        for a, b in runs_of(mask, d["t"], min_run):
            tq = d["tq"][a:b]
            t = d["t"][a:b]
            g.append(np.abs(np.diff(tq)))
            sd.append(np.diff(tq))
            dt.append(np.diff(t))
            v.append(0.5 * (d["cs_v"][a:b - 1] + d["cs_v"][a + 1:b]))
            ra.append(0.5 * (np.abs(d["rate_f"][a:b - 1]) + np.abs(d["rate_f"][a + 1:b])))
            ep.append(np.full(b - a - 1, k))
            k += 1
    if not g:
        return None
    return dict(g=np.concatenate(g), sd=np.concatenate(sd), v=np.concatenate(v),
                rate=np.concatenate(ra),
                dt=np.concatenate(dt), ep=np.concatenate(ep), nep=k)


def sub(D, m):
    return {k: (D[k][m] if isinstance(D[k], np.ndarray) else D[k]) for k in D}


def rate_of(D, thr):
    """Excursions per engaged second."""
    sec = float(D["dt"].sum())
    return (float((D["g"] > thr).sum()) / sec if sec > 0 else np.nan), sec


def std_rate_ratio(A, B, thr, bins, key):
    """Direct standardization: both builds re-weighted onto A's exposure over common support.

    Returns (ratio, rateA_std, rateB_std, n_strata, secA_used, secB_used).
    """
    numA = numB = den = 0.0
    nst = 0
    sa = sb = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        ma = (A[key] >= lo) & (A[key] < hi)
        mb = (B[key] >= lo) & (B[key] < hi)
        seca, secb = float(A["dt"][ma].sum()), float(B["dt"][mb].sum())
        if seca < MIN_SEC or secb < MIN_SEC:
            continue
        ra = float((A["g"][ma] > thr).sum()) / seca
        rb = float((B["g"][mb] > thr).sum()) / secb
        numA += seca * ra
        numB += seca * rb
        den += seca
        nst += 1
        sa += seca
        sb += secb
    if den <= 0:
        return (np.nan,) * 3 + (0, 0.0, 0.0)
    ra_s, rb_s = numA / den, numB / den
    # Haldane-style guard so a zero-count control gives a finite, clearly-flagged bound
    ratio = ra_s / rb_s if rb_s > 0 else np.inf
    return ratio, ra_s, rb_s, nst, sa, sb


def boot_ratio(A, B, thr, bins, key, rng, nboot=NBOOT):
    """Cluster bootstrap over EPISODES on both sides."""
    ea = [np.flatnonzero(A["ep"] == i) for i in range(A["nep"])]
    eb = [np.flatnonzero(B["ep"] == i) for i in range(B["nep"])]
    ea = [x for x in ea if len(x)]
    eb = [x for x in eb if len(x)]
    out = np.full(nboot, np.nan)
    for i in range(nboot):
        ia = np.concatenate([ea[j] for j in rng.integers(0, len(ea), len(ea))])
        ib = np.concatenate([eb[j] for j in rng.integers(0, len(eb), len(eb))])
        out[i] = std_rate_ratio(sub(A, ia), sub(B, ib), thr, bins, key)[0]
    out = out[np.isfinite(out)]
    return out


def ci(b):
    return (np.percentile(b, 2.5), np.percentile(b, 97.5)) if len(b) else (np.nan, np.nan)


def fmt(r, b):
    if not np.isfinite(r):
        return "      inf (control had 0)"
    lo, hi = ci(b)
    return f"{r:7.3f} [{lo:6.3f},{hi:8.3f}]"


def hdr(t):
    print("\n" + "=" * 120)
    print(t)
    print("=" * 120)


def main():
    D = {b: harvest(b) for b in BUILDS}

    hdr("A. RAW |d(tq)| DISTRIBUTION, ENGAGED ONLY (no stratification)")
    print(f"   {'build':>5s} {'episodes':>9s} {'engaged s':>10s} | "
          f"{'p50':>6s} {'p90':>6s} {'p99':>7s} {'p99.9':>7s} {'max':>7s} | "
          + " ".join(f"{'>'+str(t):>9s}" for t in THRESH))
    for b, d in D.items():
        if d is None:
            continue
        sec = float(d["dt"].sum())
        rates = [f"{(d['g'] > t).sum() / sec:9.4f}" for t in THRESH]
        print(f"   {b:>5s} {d['nep']:9d} {sec:10.1f} | "
              f"{np.percentile(d['g'], 50):6.0f} {np.percentile(d['g'], 90):6.0f} "
              f"{np.percentile(d['g'], 99):7.0f} {np.percentile(d['g'], 99.9):7.0f} "
              f"{d['g'].max():7.0f} | " + " ".join(rates))
    print("   (last five columns are EXCURSIONS PER ENGAGED SECOND at each threshold)")
    print("\n   raw counts:")
    for b, d in D.items():
        if d is None:
            continue
        print(f"   {b:>5s} " + "  ".join(f">{t}: {int((d['g'] > t).sum()):5d}" for t in THRESH))

    hdr("B. NULL CONTROLS")
    print("   B1. SPLIT-HALF within build (episodes by parity) -- the noise floor for a rate ratio")
    print(f"   {'build':>5s} {'thr':>6s} | {'ratio [95% CI]':>26s} | {'CI width':>9s}")
    widths = []
    for b in ("V62", "V59", "V61"):
        d = D[b]
        even = np.flatnonzero(d["ep"] % 2 == 0)
        odd = np.flatnonzero(d["ep"] % 2 == 1)
        A, B = sub(d, even), sub(d, odd)
        A["nep"] = B["nep"] = d["nep"]
        for thr in (1000, 2000):
            r, *_ = std_rate_ratio(A, B, thr, SPEED_BINS, "v")
            bs = boot_ratio(A, B, thr, SPEED_BINS, "v", np.random.default_rng(3), 1200)
            lo, hi = ci(bs)
            w = hi / lo if lo > 0 else np.inf
            widths.append(w)
            print(f"   {b:>5s} {thr:6d} | {fmt(r, bs):>26s} | {w:8.1f}x")
    fin = [w for w in widths if np.isfinite(w)]
    floor = np.sqrt(np.median(fin)) if fin else np.inf
    print(f"\n   median null CI width = {np.median(fin):.1f}x  =>  RESOLUTION FLOOR ~ {floor:.1f}x")
    print(f"   Any ratio inside [{1 / floor:.2f}, {floor:.2f}] is indistinguishable from noise.")

    print("\n   B2. V59 / V64 -- true cross-route null (V64 is spectrally identical to V59)")
    for thr in THRESH:
        r, ra, rb, nst, sa, sb = std_rate_ratio(D["V59"], D["V64"], thr, SPEED_BINS, "v")
        bs = boot_ratio(D["V59"], D["V64"], thr, SPEED_BINS, "v", np.random.default_rng(9), 1200)
        print(f"      >{thr:5d} | strata={nst} secA={sa:6.1f} secB={sb:6.1f} | "
              f"V59/V64 = {fmt(r, bs)}")

    hdr("C. THE THRESHOLD LADDER -- V62 vs each control, speed-standardized")
    print("   Specificity read: ~1 at low thresholds + departure only in the tail = a genuine")
    print("   transient effect. Shifted at EVERY threshold = a global scale difference.")
    for ctrl in ("V59", "V61"):
        print(f"\n   V62 / {ctrl}   (standardized onto V62's speed exposure, common support)")
        print(f"      {'thr':>6s} | {'strata':>6s} {'secA':>7s} {'secB':>7s} | "
              f"{'rateA':>8s} {'rateB':>8s} | {'ratio [95% CI]':>26s}")
        for thr in THRESH:
            r, ra, rb, nst, sa, sb = std_rate_ratio(D["V62"], D[ctrl], thr, SPEED_BINS, "v")
            bs = boot_ratio(D["V62"], D[ctrl], thr, SPEED_BINS, "v", RNG, 2000)
            print(f"      {thr:6d} | {nst:6d} {sa:7.1f} {sb:7.1f} | {ra:8.4f} {rb:8.4f} | "
                  f"{fmt(r, bs):>26s}")

    hdr("D. STRATIFIED BY SPEED, then by MOTOR RATE  (threshold 1000 and 2000)")
    for key, bins, lbl in (("v", SPEED_BINS, "speed m/s"), ("rate", RATE_BINS, "|rate| deg/s")):
        for thr in (1000, 2000):
            print(f"\n   by {lbl}, excursions >{thr}/s   "
                  f"[cnt/sec per build; ratio only where both have >= {MIN_SEC}s]")
            print(f"      {'bin':>12s} | {'V62 n/sec':>16s} {'V59 n/sec':>16s} "
                  f"{'V61 n/sec':>16s} | {'V62/V59':>9s} {'V62/V61':>9s}")
            for lo, hi in zip(bins[:-1], bins[1:]):
                cells, rates = {}, {}
                for b in ("V62", "V59", "V61"):
                    d = D[b]
                    m = (d[key] >= lo) & (d[key] < hi)
                    sec = float(d["dt"][m].sum())
                    c = int((d["g"][m] > thr).sum())
                    cells[b] = (c, sec)
                    rates[b] = c / sec if sec >= MIN_SEC else np.nan
                lbl2 = f"{lo:.0f}-{'inf' if hi == np.inf else f'{hi:.0f}'}"
                rr = []
                for ctrl in ("V59", "V61"):
                    x = (rates["V62"] / rates[ctrl]
                         if np.isfinite(rates["V62"]) and np.isfinite(rates[ctrl])
                         and rates[ctrl] > 0 else np.nan)
                    rr.append(f"{x:9.3f}" if np.isfinite(x) else
                              ("     inf" if np.isfinite(rates["V62"]) and rates["V62"] > 0
                               and np.isfinite(rates[ctrl]) else "      n/a"))
                print(f"      {lbl2:>12s} | " + " ".join(
                    f"{cells[b][0]:5d}/{cells[b][1]:7.1f}s" for b in ("V62", "V59", "V61"))
                    + " | " + " ".join(rr))

    hdr("E. IS THE BIG EXCURSION A STEP OR AN OSCILLATION?")
    print("   For every g > 2000 event: how many of the surrounding +/-5 samples also exceed")
    print("   1000, and what fraction of the local d(tq) sequence alternates sign. A sustained")
    print("   near-Nyquist oscillation alternates and has many loud neighbours; an isolated")
    print("   mechanical step does not.")
    print(f"   {'build':>5s} {'n(>2000)':>9s} {'median loud neighbours':>23s} "
          f"{'median sign-alternation':>24s}")
    for b, d in D.items():
        if d is None:
            continue
        # rebuild signed diffs per episode to measure alternation
        idx = np.flatnonzero(d["g"] > 2000)
        if not len(idx):
            print(f"   {b:>5s} {0:9d} {'-':>23s} {'-':>24s}")
            continue
        # 🛑 sign alternation needs the SIGNED difference; |d(tq)| has thrown the sign away.
        # An earlier version averaged (g > 500) here and labelled it "alternation" -- that is a
        # loudness fraction, not alternation, and it cannot distinguish a step from a limit cycle.
        nb, alt = [], []
        for i in idx:
            lo, hi = max(0, i - 5), min(len(d["g"]), i + 6)
            if not np.all(d["ep"][lo:hi] == d["ep"][i]):
                continue
            nb.append(int((d["g"][lo:hi] > 1000).sum()) - 1)
            s = np.sign(d["sd"][lo:hi])
            s = s[s != 0]
            if len(s) > 1:
                alt.append(float(np.mean(np.diff(s) != 0)))
        print(f"   {b:>5s} {len(idx):9d} {np.median(nb) if nb else np.nan:23.1f} "
              f"{np.median(alt) if alt else np.nan:24.2f}")


if __name__ == "__main__":
    main()
