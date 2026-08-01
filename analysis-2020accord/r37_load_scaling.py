#!/usr/bin/env python3
"""Does V62's effect on each band depend on DRIVER LOAD?

THE QUESTION. V62 doubles the torsion-bar torque-rate (Kd) lead lane at two sites:
`0x3AC20` (lane r24, plain `dtorque x gain_B`, no load term) and `0x3AB76` (lane r26, whose
`stage1 = (avg2 * dtorque) >> 10` carries a DRIVER-TORQUE-MAGNITUDE multiplier `gp-0x69a4`).
If the 18-22 Hz grinding suppression is FLAT in driver effort it is consistent with r24; if it
GROWS with effort, r26 is carrying part of it and reverting `0x3AB76` would cost part of the fix.

METHOD, and the two things that make it trustworthy:
  * CLUSTER BOOTSTRAP OVER EPISODES, never over windows. Windows inside one contiguous engaged
    run are correlated; bootstrapping windows would shrink every CI by ~sqrt(windows/episode)
    and manufacture significance. Episodes are the independent unit.
  * TWO NULL CONTROLS, run through the identical pipeline:
      - SPLIT-HALF within each build (episodes split by parity) -- must return ratio ~ 1 with a
        CI covering 1. If it does not, the pipeline itself is broken and no verdict is valid.
      - A NEGATIVE-CONTROL BAND (30-40 Hz) where neither effect lives -- tests specificity.
    A cross-build ratio is only interesting to the extent it exceeds what these two produce.

SPEED IS NOT A NUISANCE, IT IS A CONFOUND. Every effort comparison is standardized: inside each
effort bin the ratio is computed per speed sub-bin and combined as a weighted geometric mean
(weights = V62 window counts), so a speed-distribution difference between routes cannot
masquerade as a load effect. Cells with too few windows on either side are dropped, not filled.

🛑 ORDER-TRACK CEILINGS (wheel order 1 = 0.489*v, order 2 = 0.978*v):
      6-12 Hz  is clean only below v = 6/0.489  = 12.27 m/s  (order 1 enters at 6 Hz)
      18-22 Hz is clean only below v = 18/0.978 = 18.40 m/s  (order 2 enters at 18 Hz)
    Both are enforced; the unrestricted numbers are printed alongside so the cost is visible.

Conventions from _r31_common: latActive engagement, SUSTAINED effort (3 Hz lowpass) never raw
|tq|, disjoint runs never spliced, prominence + presence rather than mean Welch power.

Usage:  python r37_load_scaling.py [nfft]
"""
import os
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from _r31_common import peak_prom, runs_of, sustained  # noqa: E402

BUILDS = {
    "V62": ("_cache_r37", "r37s", list(range(15))),
    "V59": ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    "V64": ("_cache_r35", "r35s", [0, 1, 2]),
}
GRIND = (18.0, 22.0)
RATCHET = (6.0, 12.0)
NEG = (30.0, 40.0)          # negative-control band: neither effect should live here
V_CEIL = {"grind": 18.40, "ratchet": 12.27, "neg": np.inf}

EFFORT_BINS = [0, 100, 200, 350, 600, 1000, 1500, 2500, np.inf]
SPEED_BINS = [0, 2, 4, 7, 11, 16, 22, np.inf]
RATE_BINS = [0, 1, 2, 4, 8, 16, 32, np.inf]
PRESENCE = 10.0             # prominence threshold for "the mode is present"
NBOOT = 4000
RNG = np.random.default_rng(20260731)


def psd_of(x, fs, nfft):
    """One-sided PSD (counts^2/Hz) of one detrended Hann-windowed block."""
    if len(x) != nfft or not np.all(np.isfinite(x)):
        return None
    r = np.arange(nfft)
    c = np.polyfit(r, x, 1)
    x = x - (c[0] * r + c[1])
    w = np.hanning(nfft)
    P = np.abs(np.fft.rfft(x * w)) ** 2 / (fs * np.sum(w ** 2))
    P[1:-1] *= 2
    return P


def harvest(build, nfft):
    """Non-overlapping engaged windows with band power, prominence, effort, speed, rate."""
    cd, pfx, segs = BUILDS[build]
    out = []
    for s in segs:
        p = ROOT / cd / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = np.load(p)
        fs = 1.0 / np.median(np.diff(d["t"]))
        f = np.fft.rfftfreq(nfft, 1 / fs)
        df = f[1] - f[0]
        mask = d["cc_lat"] > 0.5
        for ep, (a, b) in enumerate(runs_of(mask, d["t"], nfft)):
            tq = d["tq"][a:b]
            sus = sustained(tq, fs)              # over the contiguous run, per convention
            for i in range(0, len(tq) - nfft + 1, nfft):
                P = psd_of(tq[i:i + nfft], fs, nfft)
                if P is None:
                    continue
                sl = slice(a + i, a + i + nfft)
                rec = dict(build=build, seg=s, ep=f"{s}:{ep}", t0=float(d["t"][a + i]),
                           eff=float(np.mean(sus[i:i + nfft])),
                           v=float(np.mean(d["cs_v"][sl])),
                           rate=float(np.mean(np.abs(d["rate_f"][sl]))))
                for nm, (lo, hi) in (("grind", GRIND), ("ratchet", RATCHET), ("neg", NEG)):
                    m = (f >= lo) & (f <= hi)
                    rec[nm + "_bp"] = float(np.sum(P[m]) * df)
                    f0, pr = peak_prom(f, P, lo, hi)
                    rec[nm + "_f0"], rec[nm + "_prom"] = f0, pr
                out.append(rec)
    return out


def med(w, key):
    v = np.array([r[key] for r in w], float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else np.nan


def by_episode(w):
    eps = {}
    for r in w:
        eps.setdefault(r["ep"], []).append(r)
    return eps


def boot_median(w, key, rng, nboot=NBOOT):
    """Cluster bootstrap of the median over EPISODES (windows within an episode move together)."""
    eps = list(by_episode(w).values())
    if not eps:
        return np.array([])
    k = len(eps)
    out = np.empty(nboot)
    for i in range(nboot):
        pick = rng.integers(0, k, k)
        vals = [r[key] for j in pick for r in eps[j]]
        vals = [x for x in vals if np.isfinite(x)]
        out[i] = np.median(vals) if vals else np.nan
    return out


def standardized_ratio(A, B, key, speed_bins=SPEED_BINS, min_n=3):
    """Weighted geometric mean of per-speed-bin median ratios. Weights = V62 window counts.

    Returns (ratio, n_cells_used, n_A_used, n_B_used). NaN if no cell has support on both sides.
    """
    rs, ws, na, nb = [], [], 0, 0
    for lo, hi in zip(speed_bins[:-1], speed_bins[1:]):
        a = [r for r in A if lo <= r["v"] < hi]
        b = [r for r in B if lo <= r["v"] < hi]
        if len(a) < min_n or len(b) < min_n:
            continue
        ma, mb = med(a, key), med(b, key)
        if not (np.isfinite(ma) and np.isfinite(mb)) or mb <= 0 or ma <= 0:
            continue
        rs.append(np.log(ma / mb)); ws.append(len(a)); na += len(a); nb += len(b)
    if not rs:
        return np.nan, 0, 0, 0
    return float(np.exp(np.average(rs, weights=ws))), len(rs), na, nb


def boot_std_ratio(A, B, key, rng, nboot=NBOOT):
    """Cluster bootstrap of the SPEED-STANDARDIZED ratio, resampling episodes on both sides."""
    ea, eb = list(by_episode(A).values()), list(by_episode(B).values())
    if not ea or not eb:
        return np.array([])
    out = np.full(nboot, np.nan)
    for i in range(nboot):
        ra = [r for j in rng.integers(0, len(ea), len(ea)) for r in ea[j]]
        rb = [r for j in rng.integers(0, len(eb), len(eb)) for r in eb[j]]
        out[i] = standardized_ratio(ra, rb, key)[0]
    return out[np.isfinite(out)]


def ci(b, lo=2.5, hi=97.5):
    if not len(b):
        return (np.nan, np.nan)
    return float(np.percentile(b, lo)), float(np.percentile(b, hi))


def fmt_ci(r, b):
    if not np.isfinite(r):
        return "     n/a        "
    l, h = ci(b)
    return f"{r:7.3f} [{l:6.3f},{h:7.3f}]"


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main():
    nfft = int(sys.argv[1]) if len(sys.argv) > 1 else 256
    W = {b: harvest(b, nfft) for b in BUILDS}
    print(f"NFFT = {nfft}  ({nfft / 100.4:.2f} s, {100.4 / nfft:.3f} Hz bins)")
    for b, w in W.items():
        eps = by_episode(w)
        print(f"   {b}: {len(w):5d} windows, {len(eps):3d} episodes, "
              f"{sum(len(v) for v in eps.values()) / max(len(eps), 1):5.1f} win/episode, "
              f"effort p50={med(w, 'eff'):7.1f}  v p50={med(w, 'v'):5.2f}  "
              f"|rate| p50={med(w, 'rate'):5.2f}")

    # ---------------- NULL CONTROL 1: split-half within build --------------------------------
    # 🛑 The question is NOT "does the CI cover 1" -- with this many episodes almost anything
    # covers 1. It is HOW WIDE the null CI is, because that width is the smallest effect this
    # design can resolve. A 45x-wide null CI means a 3x real effect is invisible.
    hdr("NULL CONTROL 1 -- SPLIT-HALF WITHIN BUILD (episodes split by parity)")
    print(f"   {'build':>5s} {'band':>8s} | {'ratio [95% CI]':>26s} | {'CI width':>9s} | "
          f"{'covers 1?':>9s}")
    widths = []
    for b in ("V62", "V59"):
        eps = sorted(by_episode(W[b]).items())
        A = [r for i, (_, v) in enumerate(eps) if i % 2 == 0 for r in v]
        B = [r for i, (_, v) in enumerate(eps) if i % 2 == 1 for r in v]
        for nm in ("grind", "ratchet", "neg"):
            k = nm + "_bp"
            r, *_ = standardized_ratio(A, B, k)
            bs = boot_std_ratio(A, B, k, np.random.default_rng(1), 1500)
            l, h = ci(bs)
            cov = (l <= 1 <= h) if np.isfinite(l) else False
            wd = h / l if np.isfinite(l) and l > 0 else np.inf
            widths.append(wd)
            print(f"   {b:>5s} {nm:>8s} | {fmt_ci(r, bs):>26s} | {wd:8.1f}x | "
                  f"{'YES' if cov else '*** NO':>9s}")
    wmed = float(np.median([w for w in widths if np.isfinite(w)]))
    print(f"\n   median null CI width = {wmed:.1f}x  =>  RESOLUTION FLOOR ~ {np.sqrt(wmed):.1f}x")
    print(f"   Any cross-build ratio inside [{1 / np.sqrt(wmed):.2f}, {np.sqrt(wmed):.2f}] is "
          f"INDISTINGUISHABLE FROM NOISE in this design.")

    # ---------------- NULL CONTROL 2: V59 vs V64, a TRUE CROSS-ROUTE null ---------------------
    # The kit established V64 == V59 spectrally: V64's probe read a constant 0x87 for all 14,980
    # frames, the oscillation detector never armed, so its two gated cal edits were never in
    # force for one frame (memory accord-v64-null-is-on-the-gate). Two different DRIVES of the
    # same effective firmware => any V59/V64 ratio is pure route + driving variance. This is a
    # far stronger null than split-half, which shares a route.
    hdr("NULL CONTROL 2 -- V59 / V64 (V64 is spectrally IDENTICAL to V59: detector never armed)")
    print("   Any departure from 1.00 here is ROUTE/DRIVING variance, not firmware.")
    print(f"   {'band':>8s} {'subset':>16s} | {'nA/ep':>10s} {'nB/ep':>10s} | "
          f"{'V59/V64 [95% CI]':>27s}")
    for nm in ("grind", "ratchet", "neg"):
        ceil = V_CEIL[nm]
        for lbl, sel in (("all v<ceil", lambda r, c=ceil: r["v"] < c),
                         ("creep v<=5", lambda r: r["v"] <= 5.0)):
            A = [r for r in W["V59"] if sel(r)]
            B = [r for r in W["V64"] if sel(r)]
            if len(A) < 3 or len(B) < 3:
                print(f"   {nm:>8s} {lbl:>16s} | insufficient")
                continue
            k = nm + "_bp"
            r, *_ = standardized_ratio(A, B, k)
            bs = boot_std_ratio(A, B, k, np.random.default_rng(7), 1500)
            print(f"   {nm:>8s} {lbl:>16s} | {len(A):4d}/{len(by_episode(A)):2d}ep "
                  f"{len(B):4d}/{len(by_episode(B)):2d}ep | {fmt_ci(r, bs):>27s}")

    # ---------------- COARSE bins: what the episode count can actually support ----------------
    hdr("COARSE EFFORT SCAN -- 3 bins, the finest the 12 control episodes support")
    COARSE = [0, 200, 1000, np.inf]
    for nm, band in (("grind", GRIND), ("ratchet", RATCHET), ("neg", NEG)):
        ceil = V_CEIL[nm]
        A0 = [r for r in W["V62"] if r["v"] < ceil]
        B0 = [r for r in W["V59"] if r["v"] < ceil]
        print(f"\n   {nm.upper()} {band[0]:.0f}-{band[1]:.0f} Hz   (v < {ceil:.2f} m/s)")
        for lo, hi in zip(COARSE[:-1], COARSE[1:]):
            A = [r for r in A0 if lo <= r["eff"] < hi]
            B = [r for r in B0 if lo <= r["eff"] < hi]
            lbl = f"effort {lo:.0f}-{'inf' if hi == np.inf else f'{hi:.0f}'}"
            if len(A) < 3 or len(B) < 3:
                print(f"      {lbl:>18s} | insufficient")
                continue
            k = nm + "_bp"
            r, ncell, na, nb = standardized_ratio(A, B, k)
            bs = boot_std_ratio(A, B, k, RNG, 2000)
            print(f"      {lbl:>18s} | nA={len(A):3d}/{len(by_episode(A)):2d}ep "
                  f"nB={len(B):3d}/{len(by_episode(B)):2d}ep  cells={ncell} | "
                  f"V62/V59 = {fmt_ci(r, bs)}")

    # ---------------- CREEP: the regime where both symptoms were reported --------------------
    hdr("CREEP ONLY (v <= 5 m/s) -- the regime the operator's reports come from")
    for nm, band in (("grind", GRIND), ("ratchet", RATCHET), ("neg", NEG)):
        A0 = [r for r in W["V62"] if r["v"] <= 5.0]
        B0 = [r for r in W["V59"] if r["v"] <= 5.0]
        k = nm + "_bp"
        r, ncell, na, nb = standardized_ratio(A0, B0, k, speed_bins=[0, 1, 2, 3, 4, 5])
        bs = boot_std_ratio(A0, B0, k, RNG, 2000)
        print(f"   {nm:>8s} {band[0]:.0f}-{band[1]:.0f} Hz | "
              f"nA={len(A0):3d}/{len(by_episode(A0)):2d}ep nB={len(B0):3d}/"
              f"{len(by_episode(B0)):2d}ep | medA={med(A0, k):9.3g} medB={med(B0, k):9.3g} | "
              f"V62/V59 = {fmt_ci(r, bs)}")
        for lo, hi in zip(COARSE[:-1], COARSE[1:]):
            A = [x for x in A0 if lo <= x["eff"] < hi]
            B = [x for x in B0 if lo <= x["eff"] < hi]
            if len(A) < 3 or len(B) < 3:
                print(f"            effort {lo:.0f}-{hi:.0f}: insufficient "
                      f"(nA={len(A)}, nB={len(B)})")
                continue
            rr, *_ = standardized_ratio(A, B, k, speed_bins=[0, 1, 2, 3, 4, 5])
            bb = boot_std_ratio(A, B, k, RNG, 1500)
            print(f"            effort {lo:.0f}-{'inf' if hi == np.inf else f'{hi:.0f}':>4s}: "
                  f"nA={len(A):3d}/{len(by_episode(A)):2d}ep nB={len(B):3d}/"
                  f"{len(by_episode(B)):2d}ep  {fmt_ci(rr, bb)}")

    # ---------------- confound structure ------------------------------------------------------
    hdr("CONFOUND STRUCTURE -- effort vs motor rate")
    print(f"   {'build':>5s} {'n':>6s} | {'spearman(eff,|rate|)':>21s} {'spearman(eff,v)':>16s} "
          f"{'spearman(|rate|,v)':>19s}")
    for b, w in W.items():
        e = np.array([r["eff"] for r in w]); ra = np.array([r["rate"] for r in w])
        v = np.array([r["v"] for r in w])
        if len(w) < 5:
            print(f"   {b:>5s} {len(w):6d} |  (too few windows)")
            continue
        print(f"   {b:>5s} {len(w):6d} | {stats.spearmanr(e, ra).statistic:21.3f} "
              f"{stats.spearmanr(e, v).statistic:16.3f} "
              f"{stats.spearmanr(ra, v).statistic:19.3f}")
    print("\n   Partial Spearman (rank-residual) of band power on each axis, V62 vs V59 pooled:")
    for nm in ("grind", "ratchet"):
        for b in ("V62", "V59"):
            w = [r for r in W[b] if np.isfinite(r[nm + "_bp"]) and r[nm + "_bp"] > 0]
            if len(w) < 20:
                continue
            y = stats.rankdata([np.log(r[nm + "_bp"]) for r in w])
            e = stats.rankdata([r["eff"] for r in w])
            ra = stats.rankdata([r["rate"] for r in w])
            # residualise each predictor on the other, then correlate with y
            re_ = e - np.polyval(np.polyfit(ra, e, 1), ra)
            rr_ = ra - np.polyval(np.polyfit(e, ra, 1), e)
            print(f"      {nm:>8s} {b}: partial rho(effort | rate) = "
                  f"{stats.spearmanr(re_, y).statistic:+.3f}   "
                  f"partial rho(rate | effort) = {stats.spearmanr(rr_, y).statistic:+.3f}")

    # ---------------- the main effort scan ----------------------------------------------------
    for nm, band in (("grind", GRIND), ("ratchet", RATCHET), ("neg", NEG)):
        ceil = V_CEIL[nm]
        for ctrl in ("V59", "V64"):
            hdr(f"{nm.upper()} {band[0]:.0f}-{band[1]:.0f} Hz  --  V62 / {ctrl}, "
                f"speed-standardized, v < {ceil:.2f} m/s (order-track ceiling)")
            A0 = [r for r in W["V62"] if r["v"] < ceil]
            B0 = [r for r in W[ctrl] if r["v"] < ceil]
            print(f"   {'effort bin':>13s} | {'nA':>4s} {'epA':>4s} {'nB':>4s} {'epB':>4s} | "
                  f"{'medA':>10s} {'medB':>10s} | {'ratio V62/'+ctrl+' [95% CI]':>27s} | "
                  f"{'promA':>6s} {'promB':>6s} | {'presA':>6s} {'presB':>6s}")
            for lo, hi in zip(EFFORT_BINS[:-1], EFFORT_BINS[1:]):
                A = [r for r in A0 if lo <= r["eff"] < hi]
                B = [r for r in B0 if lo <= r["eff"] < hi]
                lbl = f"{lo:.0f}-{'inf' if hi == np.inf else f'{hi:.0f}'}"
                if len(A) < 3 or len(B) < 3:
                    print(f"   {lbl:>13s} | {len(A):4d} {len(by_episode(A)):4d} {len(B):4d} "
                          f"{len(by_episode(B)):4d} |   (insufficient support)")
                    continue
                k = nm + "_bp"
                r, ncell, na, nb = standardized_ratio(A, B, k)
                bs = boot_std_ratio(A, B, k, RNG, 1500)
                pa = np.array([x[nm + "_prom"] for x in A], float)
                pb = np.array([x[nm + "_prom"] for x in B], float)
                pa, pb = pa[np.isfinite(pa)], pb[np.isfinite(pb)]
                print(f"   {lbl:>13s} | {len(A):4d} {len(by_episode(A)):4d} {len(B):4d} "
                      f"{len(by_episode(B)):4d} | {med(A, k):10.3g} {med(B, k):10.3g} | "
                      f"{fmt_ci(r, bs):>27s} | "
                      f"{np.median(pa) if len(pa) else np.nan:6.1f} "
                      f"{np.median(pb) if len(pb) else np.nan:6.1f} | "
                      f"{100 * (pa >= PRESENCE).mean() if len(pa) else np.nan:5.0f}% "
                      f"{100 * (pb >= PRESENCE).mean() if len(pb) else np.nan:5.0f}%")

    # ---------------- effort vs rate: which axis does the RATIO track? ------------------------
    hdr("WHICH AXIS DOES THE EFFECT SIZE TRACK?  V62/V59 ratio binned by EFFORT vs by |RATE|")
    for nm in ("grind", "ratchet"):
        ceil = V_CEIL[nm]
        A0 = [r for r in W["V62"] if r["v"] < ceil]
        B0 = [r for r in W["V59"] if r["v"] < ceil]
        k = nm + "_bp"
        print(f"\n   {nm.upper()}  (v < {ceil:.2f} m/s)")
        for axis, bins in (("effort", EFFORT_BINS), ("|rate|", RATE_BINS)):
            key = "eff" if axis == "effort" else "rate"
            for lo, hi in zip(bins[:-1], bins[1:]):
                A = [r for r in A0 if lo <= r[key] < hi]
                B = [r for r in B0 if lo <= r[key] < hi]
                lbl = f"{lo:.0f}-{'inf' if hi == np.inf else f'{hi:.0f}'}"
                if len(A) < 3 or len(B) < 3:
                    print(f"      by {axis:>7s} {lbl:>9s}: insufficient "
                          f"(nA={len(A)}, nB={len(B)})")
                    continue
                r, *_ = standardized_ratio(A, B, k)
                bs = boot_std_ratio(A, B, k, RNG, 1500)
                print(f"      by {axis:>7s} {lbl:>9s}: nA={len(A):3d}/{len(by_episode(A)):2d}ep "
                      f"nB={len(B):3d}/{len(by_episode(B)):2d}ep  {fmt_ci(r, bs)}")

    # ---------------- THE DECISIVE TEST: effort WITHIN a fixed motor-rate stratum -------------
    # If the load hypothesis is right, effort must move the ratio AT FIXED MOTOR RATE. Effort and
    # rate are correlated (spearman ~0.5), so an unconditioned effort trend proves nothing.
    hdr("DECISIVE TEST -- does EFFORT move the ratio INSIDE a fixed motor-rate stratum?")
    RSTRAT = [(0.0, 4.0, "rate<4"), (4.0, np.inf, "rate>=4")]
    ESTRAT = [(0.0, 200.0, "eff<200"), (200.0, np.inf, "eff>=200")]
    for nm in ("grind", "ratchet"):
        ceil = V_CEIL[nm]
        k = nm + "_bp"
        print(f"\n   {nm.upper()}  (v < {ceil:.2f} m/s)")
        for rlo, rhi, rl in RSTRAT:
            for elo, ehi, el in ESTRAT:
                A = [r for r in W["V62"] if r["v"] < ceil and rlo <= r["rate"] < rhi
                     and elo <= r["eff"] < ehi]
                B = [r for r in W["V59"] if r["v"] < ceil and rlo <= r["rate"] < rhi
                     and elo <= r["eff"] < ehi]
                if len(A) < 3 or len(B) < 3:
                    print(f"      {rl:>8s} x {el:>9s} | insufficient (nA={len(A)}, nB={len(B)})")
                    continue
                r, *_ = standardized_ratio(A, B, k)
                bs = boot_std_ratio(A, B, k, RNG, 2000)
                print(f"      {rl:>8s} x {el:>9s} | nA={len(A):3d}/{len(by_episode(A)):2d}ep "
                      f"nB={len(B):3d}/{len(by_episode(B)):2d}ep | V62/V59 = {fmt_ci(r, bs)}")


if __name__ == "__main__":
    main()
