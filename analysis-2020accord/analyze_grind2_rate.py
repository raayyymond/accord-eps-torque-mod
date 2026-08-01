#!/usr/bin/env python3
"""BURST RATE per second of exposure, with Poisson CIs -- and the band-specificity test on rates.

Two things this fixes relative to earlier passes:

  EVENTS, NOT BLOCKS. A rate needs a countable event. Blocks are a ~10.2 s bootstrap unit, not an
  event, and mixing a WHOLE-ROUTE block count with a CORNER exposure gives a rate that is wrong in
  both numerator and denominator. Here an EVENT is a contiguous run of the 30-49 Hz envelope above
  threshold, with runs separated by < 1.0 s MERGED into one train -- V65/r3a seg 3 fires six times
  in 1.2 s and that is one physical event, not six.

  MATCHED NUMERATOR AND DENOMINATOR. Every rate below counts events whose midpoint lies inside the
  same population that supplies the exposure seconds. Corner rates use corner events over corner
  seconds; route rates use route events over route seconds.

🛑 LEAKAGE, AND A CORRECTION. A first version detected events on a brick-wall band-pass over the
WHOLE 60 s segment, on the assumption that 6,000 samples give enough stopband rejection for the
detrend/taper problem to vanish. THAT WAS WRONG, and it manufactured three events in the Kd<=1 arm:

    V61 r31 s2 t= 0.00  segment env 1727 -> leakage-controlled window env  360, zig 1, f0 25.3 Hz
    V61 r31 s2 t=59.96  segment env 1655 -> leakage-controlled window env  209, zig 0, f0 32.8 Hz
    V59 r2c s1 t=43.09  segment env  597 -> leakage-controlled window env  462, zig 1, f0 29.8 Hz

Two of the three sit exactly on the segment's FFT wraparound (t=0.00 and t=59.96 of a 60 s segment)
and all three carry a large 18-22 Hz component (2964 / 88 / 1630 counts) with the band peak pinned
to the band EDGE. They are V61's and V59's own low-frequency mode leaking, not grind #2. For
contrast, the five largest Kd=2 events have window env 2843-4044, zig 41-84, and f0 42.0-46.3 Hz
squarely INTERIOR.

Every candidate event is therefore QUALIFIED by recomputing the leakage-controlled, detrended,
Hann-tapered window envelope at its own peak and requiring that to clear the threshold too. The
segment filter is used only to locate candidates in time.

Usage:  python analyze_grind2_rate.py
"""
import json
import sys
from math import comb, log
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load, sustained  # noqa: E402

OUTJSON = HERE / "_grind2_rate.json"
V_MAX, EFF_MIN, ANG_MIN = 4.0, 1200.0, 100.0
MERGE = 1.0          # s -- runs closer than this are one physical train
MINDUR = 0.05        # s -- shorter than 3 samples of the band's own period is not an event

ARMS = [("Kd<=1 pooled", ["V61/r31", "V59/r2c", "V64/r35"], False),
        ("  V61 r31", ["V61/r31"], False),
        ("  V59 r2c", ["V59/r2c"], False),
        ("  V64 r35", ["V64/r35"], False),
        ("V62 r37 (CLEAN 2x)", ["V62/r37"], False),
        ("V65 r3a [PROVOKED]", ["V65/r3a"], True),
        ("V65 r3b [PROVOKED]", ["V65/r3b"], True),
        ("V65 3a+3b [PROVOKED]", ["V65/r3a", "V65/r3b"], True)]


def band_env(x, fs, lo, hi):
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


def poisson_ci(n, T):
    """Exact (Garwood) Poisson rate CI."""
    from scipy.stats import chi2
    lo = chi2.ppf(0.025, 2 * n) / 2 if n > 0 else 0.0
    hi = chi2.ppf(0.975, 2 * n + 2) / 2
    return n / T, lo / T, hi / T


def poisson_ratio_test(n1, T1, n2, T2):
    """Exact conditional (binomial) test of rate2 == rate1. Returns (ratio, two-sided p)."""
    n = n1 + n2
    if n == 0:
        return np.nan, 1.0
    p = T2 / (T1 + T2)
    pk = [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]
    obs = pk[n2]
    pv = float(sum(v for v in pk if v <= obs * (1 + 1e-9)))
    r1 = n1 / T1 if T1 else np.nan
    r2 = n2 / T2 if T2 else np.nan
    return (r2 / r1 if r1 else np.inf), min(pv, 1.0)


def scan(build, lo, hi, thr):
    """(events, corner_seconds, route_seconds) for one build in one band."""
    B = G.BUILDS[build]
    ev, cor, tot = [], 0.0, 0.0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        dt = 1.0 / fs
        t = np.asarray(d["t"], float)
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        inc = (np.abs(d["cs_v"]) < V_MAX) & (eff >= EFF_MIN) & (np.abs(d["ang"]) >= ANG_MIN)
        tot += len(t) * dt
        cor += float(inc.sum()) * dt
        e = band_env(d["tq"], fs, lo, hi)
        hot = e > thr
        if not hot.any():
            continue
        idx = np.flatnonzero(hot)
        runs, a = [], idx[0]
        for i in range(1, len(idx)):
            if t[idx[i]] - t[idx[i - 1]] > MERGE:
                runs.append((a, idx[i - 1]))
                a = idx[i]
        runs.append((a, idx[-1]))
        taper = np.hanning(256) + 1e-3
        cw = slice(51, 205)
        for a0, b0 in runs:
            if t[b0] - t[a0] < MINDUR and b0 - a0 < 3:
                continue
            # QUALIFY with the leakage-controlled estimator at the event's own peak
            pk = int(a0 + np.argmax(e[a0:b0 + 1]))
            w0 = min(max(0, pk - 128), len(t) - 256)
            if w0 < 0:
                continue
            xw = np.asarray(d["tq"][w0:w0 + 256], float)
            if G.win_env(xw, fs, lo, hi, taper, cw) <= thr:
                continue
            ev.append(dict(seg=int(s), t0=float(t[a0]), dur=float(t[b0] - t[a0]),
                           peak=float(e[a0:b0 + 1].max()), zig=G.zigzag(xw, 800.0)[0],
                           corner=bool(inc[a0:b0 + 1].any())))
    return ev, cor, tot


def main():
    out = {}
    G.hdr("BAND THRESHOLDS.  Self-scaling: each band's threshold is that band's own MAXIMUM over\n"
          "every Kd<=1 window (632 windows, three routes). By construction the low-dose arm has\n"
          "at most one event per band, so the test asks only whether the HIGH dose exceeds what the\n"
          "controls ever produced. Applied identically to every band, including the controls.")
    import pickle
    with open(HERE.parent / "_cache_grind2_records.pkl", "rb") as fh:
        store = pickle.load(fh)
    k1w = [r for b in ["V61/r31", "V59/r2c", "V64/r35"] for r in store[b]]
    THR = {}
    for bnd in ("1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49", "30-49"):
        THR[bnd] = float(G.col(k1w, "e_" + bnd).max())
    THR["30-49 (fixed 400)"] = 400.0
    for k, v in THR.items():
        print(f"    {k:20s} {v:9.1f} counts")

    for bnd, band in (("30-49 (fixed 400)", (30.0, 49.0)), ("30-49", (30.0, 49.0)),
                      ("40-49", (40.0, 49.0)), ("24-28", (24.0, 28.0)),
                      ("10-16", (10.0, 16.0)), ("18-22", (18.0, 22.0)), ("6-9", (6.0, 9.0)),
                      ("1-4", (1.0, 4.0))):
        thr = THR[bnd]
        G.hdr(f"BAND {bnd} Hz   threshold {thr:.1f} counts   "
              f"{'<-- GRIND #2' if bnd.startswith('30-49') or bnd == '40-49' else '<-- CONTROL BAND'}")
        res = {}
        print(f"  {'arm':22s} {'corner s':>9s} {'corner ev':>9s} {'per 100 s':>22s} | "
              f"{'route s':>8s} {'route ev':>8s} {'per 100 s':>22s} | {'max':>8s}")
        cache = {}
        for lbl, builds, prov in ARMS:
            EV, C, T = [], 0.0, 0.0
            for b in builds:
                if (b, bnd) not in cache:
                    cache[(b, bnd)] = scan(b, *band, thr)
                e, c, t = cache[(b, bnd)]
                EV += e
                C += c
                T += t
            nc = sum(1 for e in EV if e["corner"])
            nr = len(EV)
            rc = poisson_ci(nc, C / 100.0)
            rr = poisson_ci(nr, T / 100.0)
            mx = max((e["peak"] for e in EV), default=0.0)
            res[lbl.strip()] = dict(corner_s=C, corner_ev=nc, route_s=T, route_ev=nr, max=mx,
                                    rate_corner=list(rc), rate_route=list(rr))
            print(f"  {lbl:22s} {C:9.1f} {nc:9d} {rc[0]:7.3f} [{rc[1]:6.3f},{rc[2]:7.3f}] | "
                  f"{T:8.1f} {nr:8d} {rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:7.3f}] | {mx:8.1f}")

        # exact Poisson rate-ratio tests
        base = res["Kd<=1 pooled"]
        print()
        for lbl in ("V62 r37 (CLEAN 2x)", "V65 3a+3b [PROVOKED]"):
            r = res[lbl]
            for scope, kn, ks in (("CORNER", "corner_ev", "corner_s"),
                                  ("ROUTE ", "route_ev", "route_s")):
                ratio, p = poisson_ratio_test(base[kn], base[ks], r[kn], r[ks])
                print(f"  {scope} {lbl:22s} {r[kn]:3d} ev / {r[ks]:6.1f} s  vs  "
                      f"{base[kn]:3d} ev / {base[ks]:6.1f} s   rate ratio "
                      f"{ratio if np.isfinite(ratio) else float('inf'):8.2f}x   exact Poisson "
                      f"p = {p:.4g}")
        out[bnd] = res

    # ------------------------------------------------------------------ summary ----------------
    G.hdr("BAND-SPECIFICITY SUMMARY -- the decisive test.  Corner-conditioned event RATE ratio,\n"
          "V62 r37 (clean, unprovoked) vs pooled Kd<=1, per band. If the control bands move too,\n"
          "this is generic roughness.")
    print(f"  {'band':20s} {'thr':>8s} | {'Kd<=1 ev/100s':>14s} {'V62 r37 ev/100s':>16s} "
          f"{'ratio':>9s} {'p':>9s}")
    for bnd in ("1-4", "6-9", "10-16", "18-22", "24-28", "30-49", "40-49"):
        b0 = out[bnd]["Kd<=1 pooled"]
        b2 = out[bnd]["V62 r37 (CLEAN 2x)"]
        ratio, p = poisson_ratio_test(b0["corner_ev"], b0["corner_s"],
                                      b2["corner_ev"], b2["corner_s"])
        tag = " <-- GRIND #2" if bnd in ("30-49", "40-49") else ""
        print(f"  {bnd:20s} {THR[bnd]:8.1f} | {b0['rate_corner'][0]:14.3f} "
              f"{b2['rate_corner'][0]:16.3f} "
              f"{(ratio if np.isfinite(ratio) else 999):9.2f} {p:9.4g}{tag}")
    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
