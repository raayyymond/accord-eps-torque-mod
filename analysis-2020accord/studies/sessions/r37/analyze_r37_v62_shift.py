#!/usr/bin/env python3
"""THE FREQUENCY-SHIFT TEST -- does omega_n^2 stay linear in Kd?  V59 / V61 / V62, both modes.

studies/models/rate_lane_damping_model.py derives, for a LAGGED derivative lane,
    d(omega_n^2)/omega_n^2 ~ Kd*k*tau/J_c        -- FREQUENCY-INDEPENDENT
so omega_n^2 = A + B*Kd, and every mode in the loop shifts by the same FRACTION. V61 (Kd=0) and V59
(Kd=1) fix A and B; V62 (Kd=2) is the out-of-sample point:

    f(V62) = sqrt( 2*f(V59)^2 - f(V61)^2 )

FOUR THINGS THIS FILE ADDS over a plain median-of-f0 comparison, each because the plain version can
give a confident wrong answer:

  S1  THREE INDEPENDENT ESTIMATORS per window -- periodogram sub-bin peak, band-passed upward
      zero-crossing rate, and the first autocorrelation maximum. Only the first uses an rfft bin
      index. If a shift is real all three see it; if only one does, the estimator is the finding.

  S2  A FREQUENCY RESOLUTION FLOOR, measured, not assumed. Episodes of ONE build are split at
      random into halves and the two halves' median f0 compared, 4000 times. The spread of that
      ratio is the smallest frequency shift this data can resolve. An amplitude floor (~2.2x) says
      nothing about frequency; they are different statistics on different estimators.

  S3  SPEED STANDARDISATION. 🛑 THE RATCHET FREQUENCY RISES WITH SPEED (7.2 Hz at 1 m/s -> 8.4 Hz
      at 3.3 m/s on route 37 alone). Route 37's engaged-creep arm is weighted to 1-2 m/s and route
      2c's to 2-4 m/s, so a POOLED V62-vs-V59 ratchet comparison is measuring the speed histogram,
      not the build. Every f0 here is computed per speed sub-bin and recombined on a COMMON weight
      vector. This is the single correction that flips the reported direction of the ratchet shift.

  S4  THE V62 GRINDING f0 IS LARGELY UNMEASURABLE and that is reported as such, not papered over:
      V62's residual 12-30 Hz peak is dominated by the 2nd/3rd/4th harmonic of a large 7.2 Hz
      ratchet (integer-locked in 65% of windows, 100% in the parking lot; notching the harmonic
      ladder collapses it). Both the raw and harmonic-excluded estimates are reported.

Usage:  python studies/sessions/r37/analyze_r37_v62_shift.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import NFFT, fs_of, load, peak_prom, periodogram, runs_of, sustained  # noqa: E402
from analyze_r37_v62_creep import BUILDS, GRIND, RATCH, hdr  # noqa: E402
from analyze_r37_v62_harmonic import notched_peak  # noqa: E402

RNG = np.random.default_rng(20260731)
NBOOT = 4000
PROM_GATE = 10.0
BINS = [(1.0, 2.0), (2.0, 3.0), (3.0, 4.0)]
BUILDS_USED = ["V59 r2c", "V61 r31", "V62 r37"]
KD = {"V61 r31": 0.0, "V59 r2c": 1.0, "V62 r37": 2.0}


# ---------------------------------------------------------------- estimators -------------------
def bandpass(x, fs, lo, hi):
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))


def f_zerocross(y, fs):
    """Upward zero crossings, sub-sample interpolated. Period = mean spacing. No rfft bin index."""
    s = np.signbit(y)
    idx = np.flatnonzero(s[:-1] & ~s[1:])
    if len(idx) < 3:
        return np.nan
    frac = -y[idx] / (y[idx + 1] - y[idx])
    tcr = (idx + frac) / fs
    return 1.0 / np.mean(np.diff(tcr))


def f_autocorr(y, fs, lo, hi):
    """First autocorrelation maximum inside the lag range allowed by [lo,hi] Hz."""
    y = y - y.mean()
    n = len(y)
    ac = np.correlate(y, y, "full")[n - 1:]
    a, b = int(np.floor(fs / hi)), int(np.ceil(fs / lo))
    if b >= len(ac) or b <= a + 1:
        return np.nan
    j = int(np.argmax(ac[a:b + 1])) + a
    if 0 < j < len(ac) - 1:
        y0, y1, y2 = ac[j - 1], ac[j], ac[j + 1]
        den = y0 - 2 * y1 + y2
        j = j + (0.5 * (y0 - y2) / den if den != 0 else 0.0)
    return fs / j if j > 0 else np.nan


# ---------------------------------------------------------------- records ----------------------
ALL = {}


def get(build):
    if build not in ALL:
        B = BUILDS[build]
        out = []
        for s in B["segs"]:
            d = load(s, B["cache"], B["pfx"])
            fs = fs_of(d)
            v = np.abs(d["cs_v"])
            m = (d["cc_lat"] > 0.5) & (v >= 0.3) & (v <= 5.35)
            if not m.any():
                continue
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            for a, b in runs_of(m, d["t"], NFFT):
                x = d["tq"][a:b]
                for i in range(0, len(x) - NFFT + 1, NFFT):
                    w = x[i:i + NFFT]
                    P = periodogram(w, fs, NFFT, True)
                    if P is None:
                        continue
                    sl = slice(a + i, a + i + NFFT)
                    rec = dict(f=f, P=P, seg=int(s), run=(int(a), int(b)),
                               v=float(np.mean(v[sl])),
                               eff=float(np.mean(np.abs(sustained(d["tq"][sl], fs)))))
                    for lab, (lo, hi) in (("g", GRIND), ("r", RATCH)):
                        f0, pr = peak_prom(f, P, lo, hi)
                        y = bandpass(w, fs, lo, hi)
                        rec[lab + "_f0"], rec[lab + "_prom"] = f0, pr
                        rec[lab + "_zc"] = f_zerocross(y, fs)
                        rec[lab + "_ac"] = f_autocorr(y, fs, lo, hi)
                        rec[lab + "_sd"] = float(np.std(y))
                    rec["fr"] = rec["r_f0"]
                    rec["n_f0"], rec["n_prom"] = notched_peak(rec, harmonics=(2, 3, 4))
                    out.append(rec)
        ALL[build] = out
    return ALL[build]


def eps(recs):
    g = {}
    for r in recs:
        g.setdefault((r["seg"], r["run"]), []).append(r)
    return list(g.values())


def sel(build, vlo, vhi, mode, gate=PROM_GATE):
    """Windows in a speed bin where THAT mode is solidly present."""
    key = {"g": ("g_f0", "g_prom"), "r": ("r_f0", "r_prom"), "n": ("n_f0", "n_prom")}[mode]
    return [r for r in get(build) if vlo <= r["v"] < vhi
            and np.isfinite(r[key[1]]) and r[key[1]] >= gate and np.isfinite(r[key[0]])]


def boot_f0(recs, field, nboot=NBOOT):
    """(median, lo, hi) resampling EPISODES."""
    E = eps(recs)
    if not E:
        return np.nan, np.nan, np.nan, 0, 0
    per = [np.array([r[field] for r in e], float) for e in E]
    allv = np.concatenate(per)
    allv = allv[np.isfinite(allv)]
    if not len(allv):
        return np.nan, np.nan, np.nan, 0, len(E)
    dr = np.empty(nboot)
    for k in range(nboot):
        vv = np.concatenate([per[i] for i in RNG.integers(0, len(per), len(per))])
        vv = vv[np.isfinite(vv)]
        dr[k] = np.median(vv) if len(vv) else np.nan
    return (float(np.median(allv)), float(np.nanpercentile(dr, 2.5)),
            float(np.nanpercentile(dr, 97.5)), len(allv), len(E))


# ---------------------------------------------------------------- S1 ---------------------------
def s1_estimators():
    hdr("S1.  THREE INDEPENDENT ESTIMATORS -- do they agree on where each mode is?")
    print("   sub-bin = log-parabolic periodogram peak (uses an rfft bin index)")
    print("   zc      = upward zero-crossing rate of the band-passed signal (no rfft bin index)")
    print("   ac      = first autocorrelation maximum in the band  (no rfft bin index)")
    print("   Windows gated on that mode's own prominence >= 10x.\n")
    for mode, lab, band in (("r", "RATCHET 6-9 Hz", "r"), ("g", "GRINDING 12-30 Hz", "g")):
        print(f"   ==== {lab} ====")
        print(f"   {'bin':>9s} {'build':9s} {'ep':>3s} {'win':>4s} {'sub-bin':>18s} {'zc':>18s} "
              f"{'ac':>18s}")
        for vlo, vhi in BINS:
            for b in BUILDS_USED:
                r = sel(b, vlo, vhi, mode)
                if not r:
                    continue
                cells = []
                for fld in (f"{band}_f0", f"{band}_zc", f"{band}_ac"):
                    m, lo, hi, n, ne = boot_f0(r, fld)
                    cells.append(f"{m:5.2f}[{lo:5.2f},{hi:5.2f}]")
                m, lo, hi, n, ne = boot_f0(r, f"{band}_f0")
                print(f"   {vlo:4.1f}-{vhi:<4.1f} {b:9s} {ne:3d} {n:4d} "
                      + " ".join(f"{c:>18s}" for c in cells))
            print()


# ---------------------------------------------------------------- S2 ---------------------------
def s2_floor():
    hdr("S2.  THE FREQUENCY RESOLUTION FLOOR -- split-half-by-episode, within one build")
    print("   Episodes of a single build are split at random into two halves and the halves' median")
    print("   f0 compared, 4000 times. Any V62/V59 ratio inside this interval is NOISE. This is a")
    print("   DIFFERENT floor from the amplitude one (~2.2x): frequency is a far tighter statistic.\n")
    print(f"   {'bin':>9s} {'mode':8s} {'build':9s} {'ep':>3s} {'win':>4s} {'ratio p2.5':>11s} "
          f"{'p50':>7s} {'p97.5':>8s} {'=> resolvable shift':>22s}")
    for vlo, vhi in BINS:
        for mode, mlab, fld in (("r", "ratchet", "r_f0"), ("g", "grind", "g_f0")):
            for b in BUILDS_USED:
                r = sel(b, vlo, vhi, mode)
                E = eps(r)
                if len(E) < 4:
                    continue
                per = [np.array([x[fld] for x in e], float) for e in E]
                rr = []
                for _ in range(NBOOT):
                    idx = RNG.permutation(len(per))
                    h = len(per) // 2
                    a = np.concatenate([per[i] for i in idx[:h]])
                    c = np.concatenate([per[i] for i in idx[h:]])
                    a, c = a[np.isfinite(a)], c[np.isfinite(c)]
                    if len(a) and len(c):
                        rr.append(np.median(a) / np.median(c))
                rr = np.array(rr)
                lo, md, hi = np.percentile(rr, [2.5, 50, 97.5])
                print(f"   {vlo:4.1f}-{vhi:<4.1f} {mlab:8s} {b:9s} {len(E):3d} {len(r):4d} "
                      f"{lo:11.4f} {md:7.4f} {hi:8.4f} "
                      f"{'|1-r| > ' + f'{max(abs(1 - lo), abs(1 - hi)):.3f}':>22s}")
        print()


# ---------------------------------------------------------------- S3 ---------------------------
def s3_standardised():
    hdr("S3.  SPEED-STANDARDISED f0 -- the correction that flips the reported ratchet direction")
    print("   🛑 The ratchet frequency RISES with speed. Route 37's engaged creep is weighted to")
    print("   1-2 m/s, route 2c's to 2-4 m/s, so pooling compares speed histograms. Below: each")
    print("   build's f0 per bin, then recombined on a COMMON weight = V59's window counts.\n")
    W = {}
    for vlo, vhi in BINS:
        W[(vlo, vhi)] = len(sel("V59 r2c", vlo, vhi, "r"))
    tot = sum(W.values())
    print("   common weights (V59 ratchet window counts): "
          + "  ".join(f"{a}-{b}: {W[(a, b)]}" for a, b in BINS) + f"   total {tot}")

    for mode, mlab, fld in (("r", "RATCHET", "r_f0"), ("g", "GRINDING raw", "g_f0"),
                            ("n", "GRINDING notched", "n_f0")):
        print(f"\n   ==== {mlab} ====")
        print(f"   {'build':9s} " + "".join(f"{f'{a}-{b} m/s':>22s}" for a, b in BINS)
              + f"{'STANDARDISED':>22s}")
        std = {}
        for b in BUILDS_USED:
            cells, num, den, draws = [], 0.0, 0.0, []
            per_bin = {}
            for vlo, vhi in BINS:
                r = sel(b, vlo, vhi, mode)
                m, lo, hi, n, ne = boot_f0(r, fld)
                per_bin[(vlo, vhi)] = (r, fld)
                cells.append(f"{m:5.2f}[{lo:5.2f},{hi:5.2f}]n{n}" if np.isfinite(m) else
                             f"{'--':>22s}")
                if np.isfinite(m):
                    num += W[(vlo, vhi)] * m
                    den += W[(vlo, vhi)]
            point = num / den if den else np.nan
            # bootstrap the standardised value: resample episodes inside each bin independently
            for _ in range(NBOOT):
                nu, de = 0.0, 0.0
                for vlo, vhi in BINS:
                    r, f_ = per_bin[(vlo, vhi)]
                    E = eps(r)
                    if not E:
                        continue
                    pp = [np.array([x[f_] for x in e], float) for e in E]
                    vv = np.concatenate([pp[i] for i in RNG.integers(0, len(pp), len(pp))])
                    vv = vv[np.isfinite(vv)]
                    if len(vv):
                        nu += W[(vlo, vhi)] * np.median(vv)
                        de += W[(vlo, vhi)]
                if de:
                    draws.append(nu / de)
            d = np.array(draws)
            std[b] = (point, np.percentile(d, 2.5), np.percentile(d, 97.5)) if len(d) else \
                (np.nan,) * 3
            print(f"   {b:9s} " + "".join(f"{c:>22s}" for c in cells)
                  + f"{f'{std[b][0]:5.2f}[{std[b][1]:5.2f},{std[b][2]:5.2f}]':>22s}")
        if all(np.isfinite(std[b][0]) for b in BUILDS_USED):
            f59, f61, f62 = (std["V59 r2c"][0], std["V61 r31"][0], std["V62 r37"][0])
            print(f"   ratios vs V59:  V61 {f61 / f59:.4f}   V62 {f62 / f59:.4f}")
        yield_ = std
    return


# ---------------------------------------------------------------- S4 ---------------------------
def s4_prediction():
    hdr("S4.  THE THREE-POINT TEST -- f(V62) = sqrt(2*f(V59)^2 - f(V61)^2), with propagated error")
    print("   🛑 V61's engaged arm exists ONLY at 1-2 m/s (its whole route is parking-lot creep at")
    print("   1.08-1.52 m/s), so the three-point fit can be made in that bin and nowhere else. Any")
    print("   V61 number pooled across speed is a 1-2 m/s number wearing a different label.\n")
    for vlo, vhi in BINS:
        print(f"   |v| {vlo}-{vhi} m/s")
        for mode, mlab, fld in (("r", "RATCHET", "r_f0"), ("g", "GRINDING raw", "g_f0"),
                                ("n", "GRINDING notched", "n_f0")):
            got = {}
            for b in BUILDS_USED:
                r = sel(b, vlo, vhi, mode)
                E = eps(r)
                got[b] = ([np.array([x[fld] for x in e], float) for e in E], len(r), len(E))
            if not all(got[b][0] for b in BUILDS_USED):
                have = ", ".join(f"{b.split()[0]}={got[b][1]}" for b in BUILDS_USED)
                print(f"     {mlab:18s} CANNOT TEST -- windows: {have}")
                continue
            pt = {}
            for b in BUILDS_USED:
                v = np.concatenate(got[b][0])
                pt[b] = float(np.median(v[np.isfinite(v)]))
            arg = 2 * pt["V59 r2c"] ** 2 - pt["V61 r31"] ** 2
            pred = np.sqrt(arg) if arg > 0 else np.nan
            pdraw, mdraw = [], []
            for _ in range(NBOOT):
                m = {}
                for b in BUILDS_USED:
                    pp = got[b][0]
                    v = np.concatenate([pp[i] for i in RNG.integers(0, len(pp), len(pp))])
                    v = v[np.isfinite(v)]
                    m[b] = np.median(v) if len(v) else np.nan
                a = 2 * m["V59 r2c"] ** 2 - m["V61 r31"] ** 2
                if np.isfinite(a) and a > 0:
                    pdraw.append(np.sqrt(a))
                    mdraw.append(m["V62 r37"])
            pdraw, mdraw = np.array(pdraw), np.array(mdraw)
            plo, phi = np.percentile(pdraw, [2.5, 97.5])
            mlo, mhi = np.percentile(mdraw, [2.5, 97.5])
            # difference distribution -- the correct test, since both sides carry error
            diff = mdraw - pdraw
            dlo, dhi = np.percentile(diff, [2.5, 97.5])
            verdict = "CONSISTENT" if (dlo <= 0 <= dhi) else "FALSIFIED"
            print(f"     {mlab:18s} V61 {pt['V61 r31']:5.2f} (n={got['V61 r31'][1]}/"
                  f"{got['V61 r31'][2]}ep)  V59 {pt['V59 r2c']:5.2f} (n={got['V59 r2c'][1]}/"
                  f"{got['V59 r2c'][2]}ep)")
            print(f"     {'':18s} predicted {pred:5.2f} [{plo:5.2f},{phi:5.2f}]   measured V62 "
                  f"{pt['V62 r37']:5.2f} [{mlo:5.2f},{mhi:5.2f}] (n={got['V62 r37'][1]}/"
                  f"{got['V62 r37'][2]}ep)")
            print(f"     {'':18s} measured - predicted = {np.median(diff):+5.2f} Hz "
                  f"[{dlo:+5.2f},{dhi:+5.2f}]   ==> {verdict}")
        print()


# ---------------------------------------------------------------- S5 ---------------------------
def s5_v61_leg():
    hdr("S5.  DOES THE V61 LEG ITSELF HOLD?  the 'same fraction on both modes' evidence")
    print("   The record's structural claim is V61/V59 = x0.865 (grinding) and x0.849 (ratchet) --")
    print("   two independent modes, one fraction. Re-derived here speed-matched at 1-2 m/s, which")
    print("   is the only bin V61 has, with episode-bootstrap CIs on the RATIO.\n")
    for vlo, vhi in [(1.0, 2.0)]:
        for mode, mlab, fld in (("g", "GRINDING", "g_f0"), ("n", "GRINDING notched", "n_f0"),
                                ("r", "RATCHET", "r_f0")):
            a = sel("V61 r31", vlo, vhi, mode)
            c = sel("V59 r2c", vlo, vhi, mode)
            if not a or not c:
                print(f"   {mlab:18s} n=0")
                continue
            pa = [np.array([x[fld] for x in e], float) for e in eps(a)]
            pc = [np.array([x[fld] for x in e], float) for e in eps(c)]
            point = np.median(np.concatenate(pa)) / np.median(np.concatenate(pc))
            dr = []
            for _ in range(NBOOT):
                va = np.concatenate([pa[i] for i in RNG.integers(0, len(pa), len(pa))])
                vc = np.concatenate([pc[i] for i in RNG.integers(0, len(pc), len(pc))])
                dr.append(np.median(va) / np.median(vc))
            lo, hi = np.percentile(dr, [2.5, 97.5])
            print(f"   {mlab:18s} V61/V59 = {point:.4f} [{lo:.4f}, {hi:.4f}]   "
                  f"n {len(a)}win/{len(eps(a))}ep vs {len(c)}win/{len(eps(c))}ep")
    print("\n   If the two fractions' CIs overlap, the 'same fraction' claim survives; if the")
    print("   ratchet ratio's CI is wide enough to cover almost anything, the claim was never")
    print("   as sharp as it reads.")


def main():
    s1_estimators()
    s2_floor()
    s3_standardised()
    s4_prediction()
    s5_v61_leg()


if __name__ == "__main__":
    main()
