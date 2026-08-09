#!/usr/bin/env python3
"""V86 PRE-REGISTERED FREQUENCY TEST.  `0xC40D4` 573 -> 286 (command EMA alpha 0.1399 -> 0.0698).

PRE-REGISTRATION (docs/STATE.md, fixed BEFORE the flight):
    f(V86)/f(V85) in [0.797, 0.875]  (median 0.843)  ->  peak in [6.2, 6.9] Hz
    CONFIRMED  : peak in [6.2, 6.9] Hz AND ratio CI excludes 1.00
    FALSIFIED  : it stays at 7.79 Hz
    AMBIGUOUS  : the ratcheting is too weak to locate a peak

THE INSTRUMENT IS THE CORPUS'S.  Windowing / periodogram / prominence spectrum / free 5-12 Hz
argmax are `relay_fingerprint_r6e.py`'s, imported verbatim (NW=1024 @ ~101 Hz -> 0.0987 Hz bins;
a 0.843x shift off 8.2 Hz is ~13 bins).  What this file adds:
  * SPEED MATCHING to the three bins route 6f actually occupies (0.5-1.5, 1.5-2.78, 2.78-5.0 m/s)
  * a BLOCK bootstrap (blk = ~10.13 s contiguous block) because 6f is n=1 episode
  * route 70 = V86B as a contemporaneous negative control (same V85 base, 0xC40D4 UNCHANGED)
  * an INJECTION power check: can a 0.843x-shifted line of the measured amplitude be recovered?
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402
import _r31_common as C31        # noqa: E402

CIRC = 2.0805
MACRO = 7.79                     # the recorded macro-ratchet line
NW = 1024                        # corpus window: 10.13 s @ 101.04 Hz -> 0.0987 Hz bins
HOPW = 512
FLO, FHI = 5.0, 12.0             # the free search band
VLO, VHI = 0.5, 5.0              # the speed range route 6f actually occupies
VBINS = [(0.5, 1.5), (1.5, 2.78), (2.78, 5.0)]
PREREG_LO, PREREG_HI = 6.2, 6.9
RATIO_LO, RATIO_HI = 0.797, 0.875
RNG = np.random.default_rng(86_7790)

ROUTES = {
    "V86/r6f":  ("_cache_r6f",  "r6fs",  list(range(4))),
    "V85/r6e":  ("_cache_r6e",  "r6es",  list(range(7))),      # seg 7 parked
    "V86B/r70": ("_cache_r70",  "r70s",  list(range(4))),
    "V84/r6d":  ("_cache_r6d",  "r6ds",  list(range(11))),
    "V81/r67":  ("_cache_r67x", "r67xs", list(range(13))),
}
OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


# ---------------------------------------------------------------------------------------------
#  windowing -- RF.windows with the signal made selectable and speed spread recorded
# ---------------------------------------------------------------------------------------------
def windows(route, cache, pfx, segs, engaged=True, sig="tq", nw=NW, hopw=HOPW):
    b_lf = butter(2, [0.5, 4.0], btype="band", fs=101.0)
    b_bp = butter(2, [6.0, 9.0], btype="band", fs=101.0)
    out = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, ROOT / cache, pfx)
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        x = np.asarray(d[sig], float)
        v = np.asarray(d["cs_v"], float)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        mask = lat if engaged else ~lat
        for a, b in C31.runs_of(mask, t, nw):
            x_lf = filtfilt(*b_lf, x[a:b])
            x_bp = filtfilt(*b_bp, x[a:b])
            env = np.abs(hilbert(x_bp))
            for j0 in range(0, (b - a) - nw + 1, hopw):
                sl = slice(j0, j0 + nw)
                seg = x[a:b][sl]
                if not np.all(np.isfinite(seg)):
                    continue
                vv = v[a:b][sl]
                out.append(dict(build=route, seg=int(s), t0=float(t[a:b][sl][0]),
                                blk=f"{s}:{a}:{j0 // (hopw * 2)}", ep=f"{s}:{a}",
                                v=float(np.median(vv)), vlo=float(np.min(vv)),
                                vhi=float(np.max(vv)), fs=float(fs),
                                x=seg, x_lf=x_lf[sl], env=env[sl]))
    return out


def spectra(recs, nw=NW):
    for r in recs:
        P = C31.periodogram(r["x"], r["fs"], nfft=nw, detrend=True)
        f = np.fft.rfftfreq(nw, 1.0 / r["fs"])
        R = G.prom_spectrum(f, P, halfwin=3.0, exclude=0.6)
        r["f"], r["P"], r["R"] = f, P, R
        m = (f >= FLO) & (f <= FHI) & np.isfinite(R)
        r["f_free"] = float(f[np.argmax(np.where(m, R, -np.inf))]) if m.any() else np.nan
        r["p_free"] = float(np.nanmax(np.where(m, R, np.nan))) if m.any() else np.nan
        # local floor level at the argmax -- so AMPLITUDE and FLOOR are separable
        if np.isfinite(r["f_free"]):
            j = int(np.argmin(np.abs(f - r["f_free"])))
            r["P_at"] = float(P[j])
            r["floor_at"] = float(P[j] / R[j]) if R[j] > 0 else np.nan
        else:
            r["P_at"] = r["floor_at"] = np.nan
        # centroid: assumption-free peak location, prominence-above-1 weighted, 5-11 Hz
        mc = (f >= 5.0) & (f <= 11.0) & np.isfinite(R)
        w = np.clip(R[mc] - 1.0, 0.0, None)
        r["cent"] = float(np.sum(f[mc] * w) / np.sum(w)) if np.sum(w) > 0 else np.nan
    return recs


def order_clean(rs, lo=FLO, hi=FHI, orders=(1, 2, 3, 4)):
    """Drop any window whose wheel order k lands inside the search band."""
    return [r for r in rs if not any(lo <= k * r["v"] / CIRC <= hi for k in orders)]


def in_speed(rs, lo=VLO, hi=VHI):
    return [r for r in rs if lo <= r["v"] < hi]


# ---------------------------------------------------------------------------------------------
#  BLOCK bootstrap.  6f is ONE engaged episode -> an episode bootstrap has n=1 and is impossible.
#  Resampling unit = `blk`, a ~10.13 s CONTIGUOUS block (2 half-overlapped windows).  Legitimacy
#  is checked in `autocorr_check()`: the per-window statistic must decorrelate within one block.
# ---------------------------------------------------------------------------------------------
def block_boot(vals, units, stat=np.median, nboot=4000, rng=None):
    rng = rng or RNG
    vals = np.asarray(vals, float)
    ok = np.isfinite(vals)
    vals, units = vals[ok], np.asarray(units)[ok]
    if len(vals) < 4:
        return np.nan, np.nan, np.nan, len(vals), 0
    groups = {}
    for v, u in zip(vals, units):
        groups.setdefault(u, []).append(v)
    keys = list(groups)
    draws = np.empty(nboot)
    for k in range(nboot):
        idx = rng.integers(0, len(keys), len(keys))
        draws[k] = stat(np.concatenate([groups[keys[i]] for i in idx]))
    return (float(stat(vals)), float(np.percentile(draws, 2.5)),
            float(np.percentile(draws, 97.5)), len(vals), len(keys))


def strat_block_boot_ratio(A, B, key="f_free", nboot=4000, rng=None):
    """Ratio of speed-STRATIFIED medians, each arm block-bootstrapped independently.

    Within each speed bin, take the median of `key`; combine bins by the weight the bins carry
    in the SMALLER arm (so the comparison is matched, not pooled)."""
    rng = rng or RNG

    def grp(rs):
        g = {}
        for r in rs:
            if np.isfinite(r[key]):
                g.setdefault(r["blk"], []).append(r)
        return g

    gA, gB = grp(A), grp(B)
    kA, kB = list(gA), list(gB)

    def strat_med(rs, w):
        num = den = 0.0
        for i, (lo, hi) in enumerate(VBINS):
            m = [r[key] for r in rs if lo <= r["v"] < hi]
            if len(m) == 0 or w[i] == 0:
                continue
            num += w[i] * np.median(m)
            den += w[i]
        return num / den if den > 0 else np.nan

    # weights: engaged-window counts of the smaller arm, on the shared bins
    def counts(rs):
        return np.array([sum(1 for r in rs if lo <= r["v"] < hi) for lo, hi in VBINS], float)

    flatA = [r for k in kA for r in gA[k]]
    flatB = [r for k in kB for r in gB[k]]
    cA, cB = counts(flatA), counts(flatB)
    w = np.minimum(cA, cB)
    w = np.where((cA > 0) & (cB > 0), w, 0.0)

    pt = (strat_med(flatA, w), strat_med(flatB, w))
    draws = []
    for _ in range(nboot):
        ra = [r for i in rng.integers(0, len(kA), len(kA)) for r in gA[kA[i]]]
        rb = [r for i in rng.integers(0, len(kB), len(kB)) for r in gB[kB[i]]]
        a, b = strat_med(ra, w), strat_med(rb, w)
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            draws.append(a / b)
    draws = np.array(draws)
    return dict(fA=pt[0], fB=pt[1], ratio=pt[0] / pt[1] if pt[1] else np.nan,
                lo=float(np.percentile(draws, 2.5)), hi=float(np.percentile(draws, 97.5)),
                nA=len(flatA), nB=len(flatB), blkA=len(kA), blkB=len(kB),
                weights=[float(x) for x in w], cA=[float(x) for x in cA],
                cB=[float(x) for x in cB], ndraw=len(draws))


# ---------------------------------------------------------------------------------------------
#  §0  AUTOCORRELATION -- the legitimacy check for the block bootstrap
# ---------------------------------------------------------------------------------------------
def autocorr_check(rs, key="f_free", label=""):
    """Lag-1..3 autocorrelation of the per-window statistic in window units (hop = 5.07 s).

    A block bootstrap over ~10.13 s blocks is legitimate iff the statistic has decorrelated by
    ~2 hops.  Windows overlap 50%, so lag-1 correlation is expected and is NOT evidence against;
    lag-2 (the first NON-overlapping pair) is the one that must be small."""
    by = {}
    for r in rs:
        by.setdefault(r["ep"], []).append(r)
    ac = {1: [], 2: [], 3: []}
    for ep, v in by.items():
        v = sorted(v, key=lambda r: r["t0"])
        a = np.array([r[key] for r in v], float)
        a = a[np.isfinite(a)]
        if len(a) < 5:
            continue
        a = a - a.mean()
        d = np.sum(a * a)
        for L in (1, 2, 3):
            if len(a) > L and d > 0:
                ac[L].append(float(np.sum(a[:-L] * a[L:]) / d))
    print(f"    {label:14s} lag1 {np.mean(ac[1]) if ac[1] else np.nan:+.3f}  "
          f"lag2 {np.mean(ac[2]) if ac[2] else np.nan:+.3f}  "
          f"lag3 {np.mean(ac[3]) if ac[3] else np.nan:+.3f}   (n_ep={len(by)})")
    return {L: (float(np.mean(ac[L])) if ac[L] else None) for L in (1, 2, 3)}


# ---------------------------------------------------------------------------------------------
#  mean spectrum, speed-matched
# ---------------------------------------------------------------------------------------------
def matched_mean_spectrum(rs, weights, kind="R"):
    """Per-speed-bin mean of the (prominence | power) spectrum, recombined on shared weights."""
    f = rs[0]["f"]
    acc = np.zeros_like(f)
    den = 0.0
    for i, (lo, hi) in enumerate(VBINS):
        m = [r for r in rs if lo <= r["v"] < hi]
        if not m or weights[i] == 0:
            continue
        S = np.nanmean([r[kind] for r in m], axis=0)
        acc += weights[i] * S
        den += weights[i]
    return f, (acc / den if den > 0 else acc * np.nan)


def prom_at(r, f_target, half=0.5):
    if not np.isfinite(f_target):
        return np.nan
    m = (np.abs(r["f"] - f_target) <= half) & np.isfinite(r["R"])
    return float(np.nanmax(r["R"][m])) if m.any() else np.nan


def band_amp(r, fc, half=1.0):
    """p99 Hilbert envelope in fc+-half Hz, counts -- ABSOLUTE, floor-independent."""
    b = butter(2, [max(fc - half, 0.4), fc + half], btype="band", fs=r["fs"])
    return float(np.percentile(np.abs(hilbert(filtfilt(*b, r["x"]))), 99))
