# -*- coding: utf-8 -*-
"""studies/grind/task5_nyquist_shape.py -- the HIGH-FREQUENCY SHAPE test, done properly.

task5_rate_alias.py sec.2 found that the 45-49.5 Hz band sits ABOVE the 38-44 Hz band on every route
and in almost every regime.  A band-limited signal cannot do that; folded power piling up below Nyquist
can.  But so can three other things, and this script separates them:

  A  IS THE FRAME GRID SOUND?   sec.0 of the first script counted 2 % "gaps", but dt p01 = 0.0000 s and
     p99 = 0.0195 s is BATCH JITTER (two frames handed over in one logMonoTime), not loss.  The honest
     drop estimate is the count deficit against the wall clock.  Recomputed here.
  B  IS IT A DISCRETE LINE AT EXACTLY fs/2, OR A SHELF?   A component at exactly 50 Hz is the signature
     of a two-phase / alternating producer, NOT of broadband folding.  Scored two ways: a fine PSD, and
     the alternating-sign statistic  r_alt = corr(x[n], (-1)^n).
  C  IS IT SPECIFIC TO THE RATE?   The SAME 0x18F frame carries the driver torque (bytes 0:1), and
     0x14A carries the steering angle.  If all three rise toward Nyquist, the rise belongs to the
     logging/frame path.  If only the rate does, it belongs to gp-0x6a56's own source.
  D  ESTIMATOR NULL CONTROL.   The whole pipeline is run on (i) white noise and (ii) a synthetic
     BAND-LIMITED signal + the same LSB quantisation, so the reader can see what "no folding" looks
     like through this exact estimator.

Run: python rlog-tools/studies/grind/task5_nyquist_shape.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CPD = 8.0
TAGS = ("r34", "r35", "r36", "r37", "r38")
LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    for k in ("t18", "t14", "t1ab", "te4", "tcs"):
        D[k] = D[k] - t0
    return D


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def eng_mask(D, n):
    req = np.interp(D["t18"][:n], D["te4"], D["req"].astype(float)) > 0.5
    return (np.asarray(D["sca"], float)[:n] > 0.5) & req


def welch_runs(x, segs, nper):
    Ps, ntot = [], 0
    for a, b in segs:
        if b - a < nper:
            continue
        f, P = signal.welch(x[a:b] - np.mean(x[a:b]), fs=FS, nperseg=nper,
                            noverlap=nper // 2, window="hann", detrend="constant")
        Ps.append(P * (b - a)); ntot += b - a
    if not Ps:
        return None, None, 0
    return f, np.sum(Ps, 0) / ntot, ntot


# ---------------------------------------------------------------------------- A: honest drop estimate
def sec_a(D, tag):
    t = D["t18"]
    n = len(t)
    dur = t[-1] - t[0]
    exp = dur * FS + 1
    dt = np.diff(t)
    pr("  %s  n=%d  dur=%.1f s  expected@100Hz=%.0f  DEFICIT=%.0f (%.3f%%)"
       % (tag, n, dur, exp, exp - n, 100.0 * (exp - n) / exp))
    pr("        dt: frac==0 %.3f   frac in [0.008,0.012] %.3f   frac >0.015 %.3f   -> batch jitter, not loss"
       % (np.mean(dt <= 1e-9), np.mean((dt > 0.008) & (dt < 0.012)), np.mean(dt > 0.015)))
    # drift of arrival time against a perfect 100 Hz index: a genuine drop shows as a step
    resid = t - (t[0] + np.arange(n) / FS)
    pr("        arrival-time residual vs a perfect 100 Hz index: total drift %.3f s = %.1f frames"
       % (resid[-1] - resid[0], (resid[-1] - resid[0]) * FS))
    return (exp - n) / exp


# ------------------------------------------------------------------- B/C: fine shape and the controls
def alt_stat(x):
    """corr(x, (-1)^n): the amplitude at EXACTLY fs/2, normalised.  A two-phase alternating producer
    gives |r_alt| well above the ~1/sqrt(n) noise floor; broadband folding does not concentrate here."""
    x = np.asarray(x, float)
    x = x - x.mean()
    s = ((-1.0) ** np.arange(len(x)))
    r = float(np.dot(x, s) / (np.linalg.norm(x) * np.sqrt(len(x))))
    return r, 1.0 / np.sqrt(len(x))


def shape_row(name, x, segs, tag):
    f, P, ntot = welch_runs(np.asarray(x, float), segs, 4096)
    if P is None:
        pr("        %-22s (no run)" % name); return None
    ref = np.mean(P[(f >= 10) & (f < 15)])
    cols = []
    for lo, hi in [(20, 24), (27, 32), (33, 38), (38, 44), (44, 47), (47, 49.0), (49.0, 49.9)]:
        cols.append(np.mean(P[(f >= lo) & (f < hi)]) / ref)
    ras = [alt_stat(x[a:b]) for a, b in segs if b - a >= 4096]
    ra = float(np.mean([abs(r) for r, _ in ras])) if ras else np.nan
    fl = float(np.mean([s for _, s in ras])) if ras else np.nan
    pr("        %-22s %7d %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f | %.4f/%.4f"
       % ((name, ntot) + tuple(cols) + (ra, fl)))
    return f, P


def sec_bc(D, tag):
    n = min(len(D["rate"]), len(D["ang"]))
    eng = eng_mask(D, n)
    segs = runs(eng, 4096)
    if not segs:
        pr("  %s  no engaged run >= 4096" % tag); return
    rate = np.asarray(D["rate"], float)[:n]
    tq = np.asarray(D["tq"], float)[:n]
    ang = np.asarray(D["ang"], float)[:n]
    dang = np.diff(ang, prepend=ang[0])
    pr("  %s  ENGAGED.  PSD normalised to the 10-15 Hz band; last column = |corr(x,(-1)^n)| / its noise floor"
       % tag)
    pr("        %-22s %7s %8s %8s %8s %8s %8s %8s %8s | %s"
       % ("channel", "n", "20-24", "27-32", "33-38", "38-44", "44-47", "47-49", "49-49.9", "r_alt/floor"))
    shape_row("0x18F rate  (gp-0x6a56)", rate, segs, tag)
    shape_row("0x18F torque (same fr.)", tq, segs, tag)
    shape_row("0x14A angle", ang, segs, tag)
    shape_row("0x14A d(angle)", dang, segs, tag)
    # ---- estimator null controls, matched in length to the real segments
    rng = np.random.default_rng(7)
    tot = sum(b - a for a, b in segs)
    wn = np.round(rng.normal(0, np.std(rate), tot))
    b, a = signal.butter(6, 22.0 / (FS / 2), "low")
    bl = np.round(signal.filtfilt(b, a, rng.normal(0, 4 * np.std(rate), tot)))
    csegs = [(0, tot)]
    shape_row("NULL white noise", wn, csegs, tag)
    shape_row("NULL band-limited 22Hz", bl, csegs, tag)


def main():
    for tag in TAGS:
        pr()
        pr("=" * 118)
        pr("ROUTE %s" % tag)
        pr("=" * 118)
        D = load(tag)
        pr("-- A  frame-grid integrity")
        sec_a(D, tag)
        pr("-- B/C  near-Nyquist shape, same-frame and cross-frame controls, estimator nulls")
        sec_bc(D, tag)
    out = os.path.join(HERE, "_scratch", "task5_nyquist_shape.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES) + "\n")
    print("\nwrote %s" % out)


if __name__ == "__main__":
    main()
