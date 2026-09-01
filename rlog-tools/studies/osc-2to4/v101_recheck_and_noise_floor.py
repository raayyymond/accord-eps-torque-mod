#!/usr/bin/env python3
"""Two controls the 2-4 Hz baseline needs before anyone reads V276's log against it.

(A) THE V101 RE-CHECK.  V101 flew 8x LKAS gain and was rejected for "grinding/vibration at
    all speeds, only while LKAS commands" -- the SAME grammatical shape as the V276 report,
    but recorded in the 22-30 Hz band because 2-4 Hz was never scored.  Was V101's rejection
    a 2-4 Hz event misfiled?  Here: V101 (route r95) band profile 1-40 Hz against the pooled
    corpus, engaged, speed-matched, on the response AND on the command.

(B) THE NOISE FLOOR.  A cross-build number is worthless without knowing what the SAME build
    scores against ITSELF.  Per-route bootstrap over contiguous engaged runs (runs are the
    resampling unit -- `accord-cluster-bootstrap-route-is-the-unit`), giving the within-route
    95% interval on excess24, coh24 and gain24.  That interval is the resolution limit: a
    V276 reading inside it is NOT a detection.

(C) THE ONE CORPUS PRECEDENT.  r66/V80 HIGH is the only cell in 48 that looks like the V276
    report (rate excess 6.5, command excess 9.4, coh24 0.97).  It has 33 s.  Checked here for
    whether it is a sustained oscillation or a single transient.

Usage:  python rlog-tools/studies/osc-2to4/v101_recheck_and_noise_floor.py
"""
import numpy as np, glob, os, sys
from scipy import signal

FS, NPS, NOV = 100.0, 512, 256
CACHE_ROOTS = ("_scratch/cache", "analysis-2020accord/_scratch/cache")
BUILD_OVERRIDE = {"r71": "V87", "r73": "V88", "r75": "V89", "r76": "V89"}
SHOULDER_LO, SHOULDER_HI = (1.0, 1.6), (5.0, 6.0)
BAND = (2.0, 4.0)
PROFILE = [(1, 2), (2, 3), (3, 4), (4, 6), (6, 9), (9, 12), (12, 16), (16, 22), (22, 30), (30, 40)]


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


def excess24(f, P):
    lo = np.median(P[(f >= SHOULDER_LO[0]) & (f < SHOULDER_LO[1])])
    hi = np.median(P[(f >= SHOULDER_HI[0]) & (f < SHOULDER_HI[1])])
    flo = np.mean(f[(f >= SHOULDER_LO[0]) & (f < SHOULDER_LO[1])])
    fhi = np.mean(f[(f >= SHOULDER_HI[0]) & (f < SHOULDER_HI[1])])
    if not (lo > 0 and hi > 0):
        return np.nan
    n = np.log(hi / lo) / np.log(fhi / flo)
    base = lo * (np.maximum(f, 1e-9) / flo) ** n
    E = P / np.maximum(base, 1e-30)
    m = (f >= BAND[0]) & (f < BAND[1])
    return float(np.mean(E[m]))


def coh_gain(x, y, segs):
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
    if not W:
        return np.nan, np.nan
    A, B, C = A / W, B / W, C / W
    m = (f >= BAND[0]) & (f < BAND[1])
    coh = float(np.mean(np.abs(A[m]) ** 2 / np.maximum(B[m] * C[m], 1e-30)))
    gain = float(np.sqrt(np.mean(C[m]) / max(np.mean(B[m]), 1e-30)))
    return coh, gain


def load(fp):
    z = np.load(fp, allow_pickle=True)
    need = ("cs_v", "cc_lat", "ang", "rate_f", "tq")
    if any(k not in z.files for k in need):
        return None
    d = {k: np.nan_to_num(np.asarray(z[k], float)) for k in need}
    d["e4tq"] = np.nan_to_num(np.asarray(z["e4tq"], float)) if "e4tq" in z.files else None
    tag = os.path.basename(os.path.dirname(fp))
    d["_tag"] = tag
    d["_build"] = BUILD_OVERRIDE.get(tag, str(z["probe_build"][0]) if "probe_build" in z.files else "?")
    return d


def all_routes():
    for root in CACHE_ROOTS:
        for fp in sorted(glob.glob(os.path.join(root, "*", "*.npz"))):
            tag = os.path.basename(os.path.dirname(fp))
            if os.path.basename(fp) == tag + ".npz":
                d = load(fp)
                if d is not None:
                    yield d


def eng_segs(d, vlo=8.0, vhi=99.0):
    return runs_of((d["cc_lat"] > 0.5) & (d["cs_v"] >= vlo) & (d["cs_v"] < vhi), NPS)


# ----------------------------------------------------------------- (A) V101
print("=" * 120)
print("(A) V101 RE-CHECK -- was the '8x gain / grinding at all speeds, only while LKAS")
print("    commands' rejection actually a 2-4 Hz event?   route r95, engaged, v >= 8 m/s.")
print("    Each cell is the band's mean PSD as a FRACTION of the route's own 1-40 Hz total,")
print("    so routes with different absolute motion are comparable.")
print("=" * 120)
rows = []
for d in all_routes():
    segs = eng_segs(d)
    if sum(b - a for a, b in segs) < 60 * FS:
        continue
    f, P = welch_runs(d["rate_f"], segs)
    tot = np.trapezoid(P[(f >= 1) & (f < 40)], f[(f >= 1) & (f < 40)])
    frac = []
    for lo, hi in PROFILE:
        m = (f >= lo) & (f < hi)
        frac.append(float(np.trapezoid(P[m], f[m]) / tot))
    rows.append((d["_tag"], d["_build"], frac))
hdr = "%-5s %-10s | %s" % ("route", "build", " ".join("%7s" % ("%d-%d" % b) for b in PROFILE))
print(hdr); print("-" * len(hdr))
for tag, b, fr in sorted(rows, key=lambda r: r[1]):
    mark = "  <== V101" if tag == "r95" else ("  <== stock" if tag == "r97" else "")
    print("%-5s %-10s | %s%s" % (tag, b, " ".join("%7.4f" % x for x in fr), mark))
M = np.array([r[2] for r in rows])
print("-" * len(hdr))
print("%-5s %-10s | %s" % ("", "CORPUS p50", " ".join("%7.4f" % x for x in np.median(M, 0))))
print("%-5s %-10s | %s" % ("", "CORPUS p95", " ".join("%7.4f" % x for x in np.percentile(M, 95, 0))))
v101 = [r for r in rows if r[0] == "r95"]
if v101:
    z = (np.array(v101[0][2]) - np.median(M, 0)) / np.maximum(M.std(0), 1e-12)
    print("%-5s %-10s | %s" % ("", "V101 z-score", " ".join("%+7.2f" % x for x in z)))
    print("\n  READ: V101's rejection band, if 2-4 Hz, must show a POSITIVE z in the 2-3 and 3-4")
    print("  columns.  A positive z only at 16-22 / 22-30 says the original filing was right.")

# ------------------------------------------------------- (B) within-route noise floor
print("\n" + "=" * 120)
print("(B) WITHIN-ROUTE NOISE FLOOR -- bootstrap over contiguous engaged runs (the run is the")
print("    resampling unit).  A V276 reading inside these intervals is NOT a detection.")
print("=" * 120)
rng = np.random.default_rng(20260901)
h = "%-5s %-10s %6s %5s | %-22s | %-22s | %-22s" % ("route", "build", "secs", "runs",
                                                    "excess24 [95% CI]", "coh24 [95% CI]", "gain24 [95% CI]")
print(h); print("-" * len(h))
floors = {"excess24": [], "coh24": [], "gain24": []}
for d in all_routes():
    segs = eng_segs(d)
    n = sum(b - a for a, b in segs)
    if n < 120 * FS or len(segs) < 6 or d["e4tq"] is None:
        continue
    boots = {"excess24": [], "coh24": [], "gain24": []}
    for _ in range(200):
        pick = [segs[i] for i in rng.integers(0, len(segs), len(segs))]
        f, P = welch_runs(d["rate_f"], pick)
        boots["excess24"].append(excess24(f, P))
        c, g = coh_gain(d["e4tq"], d["rate_f"], pick)
        boots["coh24"].append(c); boots["gain24"].append(g)
    f, P = welch_runs(d["rate_f"], segs)
    pt = {"excess24": excess24(f, P)}
    pt["coh24"], pt["gain24"] = coh_gain(d["e4tq"], d["rate_f"], segs)
    cells = []
    for k in ("excess24", "coh24", "gain24"):
        a = np.array(boots[k]); lo, hi = np.percentile(a[np.isfinite(a)], [2.5, 97.5])
        cells.append("%6.3f [%6.3f,%6.3f]" % (pt[k], lo, hi))
        floors[k].append(hi / max(lo, 1e-9))
    print("%-5s %-10s %6.0f %5d | %s | %s | %s" % (d["_tag"], d["_build"], n / FS, len(segs), *cells))
print("-" * len(h))
for k in ("excess24", "coh24", "gain24"):
    a = np.array(floors[k])
    if len(a):
        print("  RESOLUTION on %-9s : within-route 95%% CI spans a factor of p50 %.2fx (max %.2fx)"
              % (k, np.median(a), a.max()))

# --------------------------------------------------- (C) the one corpus precedent
print("\n" + "=" * 120)
print("(C) THE ONLY CORPUS CELL THAT RESEMBLES THE V276 REPORT: r66 / V80, engaged, v >= 18 m/s")
print("=" * 120)
for d in all_routes():
    if d["_tag"] != "r66":
        continue
    segs = eng_segs(d, 18.0, 99.0)
    print("    %d qualifying runs, %.1f s total: %s"
          % (len(segs), sum(b - a for a, b in segs) / FS,
             ", ".join("%.1fs" % ((b - a) / FS) for a, b in segs)))
    for i, (a, b) in enumerate(segs):
        f, P = welch_runs(d["rate_f"], [(a, b)])
        fe, Pe = welch_runs(d["e4tq"], [(a, b)])
        print("      run %d  t=%.0f-%.0f s   rate excess24 %6.2f   e4tq excess24 %6.2f"
              % (i, a / FS, b / FS, excess24(f, P), excess24(fe, Pe)))
    print("    READ: if ONE run carries the whole effect, this is a transient, not a")
    print("    sustained oscillation, and V80 is NOT a precedent for the V276 symptom.")
