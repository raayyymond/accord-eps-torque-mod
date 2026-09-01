#!/usr/bin/env python3
"""2-4 Hz SHAPE and SPEED-MATCHED re-score -- the control for the confound that sank the
raw ranking in `rescore_2to4hz_all_routes.py`.

WHAT WENT WRONG IN THE RAW PASS (and why this file exists):
  Raw engaged 2-4 Hz steering-rate power spans 500x across the corpus and its ranking is
  ordered almost perfectly by ROUTE REGIME, not by build: the top six are r80/r82/r6f/r70/
  r81/r71 -- the short parking-lot routes with hand-turning -- and the bottom is the long
  highway routes.  2-4 Hz power is the tail of the 1/f steering spectrum, so ANY route with
  more low-frequency wheel motion scores higher.  A cross-build claim off that number would
  be an artefact.  Two fixes here:

  1. SPEED STRATA.  Score inside speed bins so engaged/manual and cross-route comparisons
     are made at a matched operating point.  (`accord-engaged-manual-speed-confound-quantified`
     is the kit's record of this confound at 6-9 Hz; it is far worse at 2-4 Hz.)

  2. A SHAPE STATISTIC, not a level.  `excess` = mean PSD over 2-4 Hz divided by the
     log-linear interpolation of the PSD between the SHOULDERS (1.0-1.6 Hz and 5.0-6.0 Hz).
     A pure 1/f^n tail gives excess ~= 1.0 by construction, whatever the driving regime.
     excess >> 1 means there is genuinely EXTRA energy sitting in 2-4 Hz -- a resonance.
     This is the statistic that will read V276's log; the level will not.

  3. INTERIOR-PEAK TEST.  The raw pass reported the "peak" at 1.56 Hz -- the first bin of its
     own search window -- in 31 of 34 routes.  That is not a peak, it is a monotone decay.
     Here a peak counts only if it is a strict local maximum with both shoulders inside the
     search range, and its Q comes from the half-power width of the EXCESS, not of the PSD.

Usage:  python rlog-tools/studies/osc-2to4/band_excess_2to4_speed_matched.py [--json OUT]
"""
import numpy as np, glob, os, sys, json
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view

FS, NPS, NOV = 100.0, 512, 256
BAND = (2.0, 4.0)
SHOULDER_LO, SHOULDER_HI = (1.0, 1.6), (5.0, 6.0)
REF = (6.0, 9.0)
CACHE_ROOTS = ("_scratch/cache", "analysis-2020accord/_scratch/cache")
BUILD_OVERRIDE = {"r71": "V87", "r73": "V88", "r75": "V89", "r76": "V89"}
# m/s.  LOW = parking lot / creep, MID = surface street, HIGH = highway.
SPEED_BINS = (("LOW", 1.0, 8.0), ("MID", 8.0, 18.0), ("HIGH", 18.0, 99.0))


def runs_of(mask, minlen):
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.concatenate(([0], m, [0])))
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))
            if b - a >= minlen]


def welch_runs(x, segs):
    P, W, f = None, 0.0, None
    for a, b in segs:
        s = np.nan_to_num(np.asarray(x[a:b], float))
        f, p = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NOV)
        w = float(b - a)
        P = p * w if P is None else P + p * w
        W += w
    return (f, P / W) if W else (None, None)


def csd_runs(x, y, segs):
    A = B = C = None; W = 0.0; f = None
    for a, b in segs:
        u = np.nan_to_num(np.asarray(x[a:b], float)); u -= u.mean()
        v = np.nan_to_num(np.asarray(y[a:b], float)); v -= v.mean()
        f, pxy = signal.csd(u, v, FS, nperseg=NPS, noverlap=NOV)
        _, pxx = signal.welch(u, FS, nperseg=NPS, noverlap=NOV)
        _, pyy = signal.welch(v, FS, nperseg=NPS, noverlap=NOV)
        w = float(b - a)
        A = pxy * w if A is None else A + pxy * w
        B = pxx * w if B is None else B + pxx * w
        C = pyy * w if C is None else C + pyy * w
        W += w
    return None if not W else (f, A / W, B / W, C / W)


def excess_curve(f, P):
    """PSD divided by the log-log straight line through the two shoulder medians.
    A pure power-law tail maps to ~1.0 everywhere between the shoulders."""
    lo = np.median(P[(f >= SHOULDER_LO[0]) & (f < SHOULDER_LO[1])])
    hi = np.median(P[(f >= SHOULDER_HI[0]) & (f < SHOULDER_HI[1])])
    flo = np.mean(f[(f >= SHOULDER_LO[0]) & (f < SHOULDER_LO[1])])
    fhi = np.mean(f[(f >= SHOULDER_HI[0]) & (f < SHOULDER_HI[1])])
    if not (lo > 0 and hi > 0):
        return None
    n = np.log(hi / lo) / np.log(fhi / flo)          # local spectral slope
    with np.errstate(divide="ignore", invalid="ignore"):
        base = lo * (np.maximum(f, 1e-9) / flo) ** n
    return P / np.maximum(base, 1e-30)


def interior_peak(f, E, lo=1.6, hi=5.0):
    """Strict interior local max of the EXCESS curve inside (lo,hi).  Returns
    (fc, excess_at_peak, Q) or NaNs.  Q from the half-maximum width of (E-1)."""
    m = (f > lo) & (f < hi)
    idx = np.flatnonzero(m)
    if len(idx) < 3:
        return (np.nan, np.nan, np.nan)
    best = None
    for i in idx:
        if 0 < i < len(E) - 1 and E[i] >= E[i - 1] and E[i] >= E[i + 1]:
            if best is None or E[i] > E[best]:
                best = i
    if best is None:
        return (np.nan, np.nan, np.nan)
    amp = E[best] - 1.0
    if amp <= 0:
        return (float(f[best]), float(E[best]), np.nan)
    half = 1.0 + amp / 2.0
    a = best
    while a > 0 and E[a] > half:
        a -= 1
    b = best
    while b < len(E) - 1 and E[b] > half:
        b += 1
    bw = f[b] - f[a]
    return (float(f[best]), float(E[best]), float(f[best] / bw) if bw > 0 else np.nan)


def bandmean(f, P, band):
    m = (f >= band[0]) & (f < band[1])
    return float(np.mean(P[m])) if m.sum() else float("nan")


def load(fp):
    z = np.load(fp, allow_pickle=True)
    need = ("cs_v", "cc_lat", "ang", "rate_f", "tq")
    if any(k not in z.files for k in need):
        return None
    d = {k: np.nan_to_num(np.asarray(z[k], float)) for k in need}
    for k in ("co_req", "e4tq"):
        d[k] = np.nan_to_num(np.asarray(z[k], float)) if k in z.files else None
    tag = os.path.basename(os.path.dirname(fp))
    d["_tag"] = tag
    d["_build"] = BUILD_OVERRIDE.get(tag, str(z["probe_build"][0]) if "probe_build" in z.files else "?")
    return d


def score(d):
    v, lat = d["cs_v"], d["cc_lat"]
    w = 501
    pad = np.pad(np.abs(d["ang"]), (w // 2, w - 1 - w // 2), mode="edge")
    ang_med = np.median(sliding_window_view(pad, w), axis=-1)[: len(d["ang"])]
    straight = ang_med < 5.0
    out = {"route": d["_tag"], "build": d["_build"], "cells": {}}
    for nm, lo, hi in SPEED_BINS:
        inb = (v >= lo) & (v < hi)
        for arm, am in (("ENG", lat > 0.5), ("MAN", lat < 0.5)):
            for sub, sm in (("ALL", np.ones_like(inb, bool)), ("STR", straight)):
                segs = runs_of(inb & am & sm, NPS)
                n = sum(b - a for a, b in segs)
                key = "%s.%s.%s" % (nm, arm, sub)
                cell = {"secs": n / FS, "n_runs": len(segs)}
                if n >= 2 * NPS:
                    for ch in ("rate_f", "ang", "tq", "co_req", "e4tq"):
                        if d.get(ch) is None:
                            continue
                        f, P = welch_runs(d[ch], segs)
                        E = excess_curve(f, P)
                        c = {"pow24": bandmean(f, P, BAND), "pow69": bandmean(f, P, REF)}
                        if E is not None:
                            c["excess24"] = bandmean(f, E, BAND)
                            pf, pe, pq = interior_peak(f, E)
                            c.update(peak_f=pf, peak_excess=pe, peak_Q=pq)
                        cell[ch] = c
                    if d.get("e4tq") is not None:
                        r = csd_runs(d["e4tq"], d["rate_f"], segs)
                        if r:
                            f, Pxy, Pxx, Pyy = r
                            bm = (f >= BAND[0]) & (f < BAND[1])
                            rm = (f >= REF[0]) & (f < REF[1])
                            coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
                            cell["coh24"] = float(np.mean(coh[bm]))
                            cell["coh69"] = float(np.mean(coh[rm]))
                            wgt = np.abs(Pxy[bm])
                            cell["ph24"] = float(np.degrees(np.angle(np.sum(Pxy[bm] * wgt))))
                            # |rate/cmd| gain in band -- the loop gain the operator can feel
                            cell["gain24"] = float(np.sqrt(np.mean(Pyy[bm]) / max(np.mean(Pxx[bm]), 1e-30)))
                            cell["gain69"] = float(np.sqrt(np.mean(Pyy[rm]) / max(np.mean(Pxx[rm]), 1e-30)))
                out["cells"][key] = cell
    return out


def main():
    files = []
    for root in CACHE_ROOTS:
        for fp in sorted(glob.glob(os.path.join(root, "*", "*.npz"))):
            tag = os.path.basename(os.path.dirname(fp))
            if os.path.basename(fp) == tag + ".npz":
                files.append(fp)
    res = [score(d) for d in (load(fp) for fp in files) if d is not None]

    def c(r, k):
        return r["cells"].get(k, {})

    def gv(r, k, ch, f_):
        x = c(r, k).get(ch)
        return x.get(f_, float("nan")) if isinstance(x, dict) else float("nan")

    for nm, lo, hi in SPEED_BINS:
        print("\n" + "=" * 128)
        print("SPEED STRATUM %s  (%.0f-%.0f m/s = %.0f-%.0f km/h)   channel = rate_f (0x18F steering rate)"
              % (nm, lo, hi, lo * 3.6, hi * 3.6))
        print("  excess24 = mean PSD(2-4) / power-law baseline through the 1.0-1.6 and 5-6 Hz shoulders.")
        print("  ~1.0 = no resonance, just the 1/f tail.  >1 = real energy parked in 2-4 Hz.")
        print("=" * 128)
        h = ("%-5s %-10s | %6s %7s %7s %6s %6s %6s | %6s %7s %7s | %6s %6s %7s" %
             ("route", "build", "engS", "pow24E", "exc24E", "pkf", "pkexc", "pkQ",
              "manS", "exc24M", "E/M", "coh24", "coh69", "gain24"))
        print(h); print("-" * len(h))
        for r in sorted(res, key=lambda r: r["build"]):
            kE, kM = "%s.ENG.ALL" % nm, "%s.MAN.ALL" % nm
            eE, eM = gv(r, kE, "rate_f", "excess24"), gv(r, kM, "rate_f", "excess24")
            if not np.isfinite(eE) and not np.isfinite(eM):
                continue
            print("%-5s %-10s | %6.0f %7.3f %7.3f %6.2f %6.2f %6.2f | %6.0f %7.3f %7.3f | %6.3f %6.3f %7.4g" %
                  (r["route"], r["build"], c(r, kE).get("secs", 0),
                   gv(r, kE, "rate_f", "pow24"), eE,
                   gv(r, kE, "rate_f", "peak_f"), gv(r, kE, "rate_f", "peak_excess"),
                   gv(r, kE, "rate_f", "peak_Q"),
                   c(r, kM).get("secs", 0), eM, eE / eM if eM else np.nan,
                   c(r, kE).get("coh24", np.nan), c(r, kE).get("coh69", np.nan),
                   c(r, kE).get("gain24", np.nan)))

    print("\n" + "=" * 128)
    print("THE DISCRIMINATOR, SPEED-MATCHED (MID + HIGH, ENGAGED): is the COMMAND itself tilted into 2-4 Hz?")
    print("  cmd_exc24 = the SAME excess statistic computed on the wire command e4tq and on co_req.")
    print("  cmd_exc24 ~ 1 while rate_exc24 >> 1  =>  EPS INNER loop (firmware).")
    print("  cmd_exc24 >> 1 too, and coh24 high   =>  openpilot OUTER loop (comma side).")
    print("=" * 128)
    h2 = ("%-5s %-10s %-4s | %7s %8s %8s %8s | %6s %7s %8s" %
          ("route", "build", "spd", "secs", "rateExc", "e4Exc", "coreqExc", "coh24", "ph24", "gain24"))
    print(h2); print("-" * len(h2))
    for r in sorted(res, key=lambda r: r["build"]):
        for nm in ("MID", "HIGH"):
            k = "%s.ENG.ALL" % nm
            if not np.isfinite(gv(r, k, "rate_f", "excess24")):
                continue
            print("%-5s %-10s %-4s | %7.0f %8.3f %8.3f %8.3f | %6.3f %7.1f %8.4g" %
                  (r["route"], r["build"], nm, c(r, k).get("secs", 0),
                   gv(r, k, "rate_f", "excess24"), gv(r, k, "e4tq", "excess24"),
                   gv(r, k, "co_req", "excess24"), c(r, k).get("coh24", np.nan),
                   c(r, k).get("ph24", np.nan), c(r, k).get("gain24", np.nan)))

    print("\n" + "=" * 128)
    print("CORPUS BASELINE DISTRIBUTION  (ENGAGED, MID+HIGH, >=60 s in cell) -- place V276 against THIS")
    print("=" * 128)
    for ch in ("rate_f", "ang", "e4tq", "co_req"):
        vals = [gv(r, "%s.ENG.ALL" % nm, ch, "excess24") for r in res for nm in ("MID", "HIGH")
                if c(r, "%s.ENG.ALL" % nm).get("secs", 0) >= 60]
        vals = np.array([v for v in vals if np.isfinite(v)])
        if len(vals):
            print("  excess24 %-8s n=%2d   p05 %5.2f  p25 %5.2f  p50 %5.2f  p75 %5.2f  p95 %5.2f  max %5.2f"
                  % (ch, len(vals), *np.percentile(vals, [5, 25, 50, 75, 95]), vals.max()))
    for st in ("coh24", "coh69", "gain24", "gain69"):
        vals = [c(r, "%s.ENG.ALL" % nm).get(st, np.nan) for r in res for nm in ("MID", "HIGH")
                if c(r, "%s.ENG.ALL" % nm).get("secs", 0) >= 60]
        vals = np.array([v for v in vals if np.isfinite(v)])
        if len(vals):
            print("  %-17s n=%2d   p05 %6.3f  p25 %6.3f  p50 %6.3f  p75 %6.3f  p95 %6.3f  max %6.3f"
                  % (st, len(vals), *np.percentile(vals, [5, 25, 50, 75, 95]), vals.max()))
    n_pk = sum(1 for r in res for nm in ("MID", "HIGH")
               if c(r, "%s.ENG.ALL" % nm).get("secs", 0) >= 60
               and np.isfinite(gv(r, "%s.ENG.ALL" % nm, "rate_f", "peak_f")))
    n_tot = sum(1 for r in res for nm in ("MID", "HIGH")
                if c(r, "%s.ENG.ALL" % nm).get("secs", 0) >= 60)
    print("  INTERIOR 2-4 Hz PEAK present in %d of %d qualifying engaged cells" % (n_pk, n_tot))

    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(res, open(p, "w"), indent=1, default=float)
        print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
