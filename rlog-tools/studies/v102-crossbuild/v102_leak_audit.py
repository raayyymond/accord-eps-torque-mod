#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_leak_audit.py -- AUDIT MY OWN LEAKAGE CLAIM.  `route-stock` found a real anomaly in it.

THE CHALLENGE.  I claimed the 3x V102 fork is Hann leakage over the 25.5 Hz edge, evidenced by the
disagreement collapsing when the band widens.  `route-stock` points out that in MY OWN numbers
V102 goes 2.982 (21.5-25.5) -> 2.220 (20-28), i.e. **DOWN when the numerator band WIDENS**, with
the denominator fixed at 2.5-4.5.  For a band-RMS ratio that is impossible, so either my statistic
is a per-Hz density or something else is going on.  It is neither obvious nor safe to argue this;
it gets measured.

  TEST A  MONOTONICITY.  Per-window, does widening the numerator raise the ratio?  And does the
          WHOLE-RUN band-RMS rise with bandwidth (Parseval says it must)?  If total rises while
          the MEDIAN falls, the statistic is being moved by TIME REDISTRIBUTION, not by units.
          🛑 A brick-wall band-pass has a sinc impulse response whose width goes as 1/BW.  A
          NARROW band smears a bursty line over a LONGER time, so MORE 1 s windows contain some
          of it and the MEDIAN window RMS RISES.  Widen the band and the bursts re-compact, so
          fewer windows carry energy and the median FALLS even though the total rises.  That is a
          property of MY estimator, and it inflates the median for BURSTY NARROWBAND signals.

  TEST B  THE DIRECT LEAKAGE MEASUREMENT, independent of both estimators.  For each arm take the
          long engaged stretches, compute TRUE band power with a long FFT (df ~ 0.01 Hz, leakage
          negligible), and compare against the mean of 1 s Hann band-POWER over the same samples.
          ratio = Hann / true.  Broadband => ~1.  A line near the band edge => < 1.
          **This is the claim.  If V102's ratio is not markedly below the others, I was wrong.**

  TEST C  BURSTINESS.  If TEST A's mechanism is right, V102's 21.5-25.5 content should be far more
          intermittent than the other arms'.  Measured as the ratio p90/p50 of 1 s band power.

  TEST D  THE HANDS DEFINITIONS.  My "88 %" was |median driver torque| >= 400 ct per window;
          route-stock's 39.9 % is openpilot's `steeringPressed`.  Both are computed here so the
          label stops being ambiguous.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L      # noqa: E402
import score_v102_full as F  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for _r, _lab in (("96", "V102"), ("97", "V9b-STOCK")):
    if _r not in L.ROUTES:
        L.ROUTES[_r] = L._mk(_r, _lab, gain=0, clamp=0, leverB=False, idcode=0, bits="x")

ARMS = [("97", "STOCK 1x"), ("85", "V100 4x"), ("96", "V102 6x"), ("95", "V101 8x")]
CTL = (2.5, 4.5)


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def runs(route):
    """Long engaged stretches on the NATIVE grid, as `build_table` sees them."""
    z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[route], allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    WL = int(round(1.0 * FS))
    out = []
    for a, b in F.runs_break(lat, t, WL):
        out.append((np.asarray(z["tq"], float)[a:b], FS, WL))
    return out


# ---------------------------------------------------------------- TEST A
hdr("TEST A -- MONOTONICITY of my own estimator.  numerator band widens, denominator FIXED.")
print("  %-10s %-22s %10s %10s %10s   %s"
      % ("arm", "numerator band", "MEDIAN", "MEAN", "WHOLE-RUN", "% windows that ROSE vs 21.5-25.5"))
BANDS = [(21.5, 25.5), (20.0, 28.0), (18.0, 30.0)]
for rt, lab in ARMS:
    base = None
    for bd in BANDS:
        per, whole_num, whole_den = [], 0.0, 0.0
        for x, FS, WL in runs(rt):
            n_ = F.bp(x, 0, len(x), FS, *bd)
            d_ = F.bp(x, 0, len(x), FS, *CTL)
            whole_num += float(np.sum(n_ ** 2))
            whole_den += float(np.sum(d_ ** 2))
            for i in range(0, len(x) - WL + 1, WL):
                sl = slice(i, i + WL)
                den = np.sqrt(np.mean(d_[sl] ** 2))
                if den > 0:
                    per.append(np.sqrt(np.mean(n_[sl] ** 2)) / den)
        per = np.array(per)
        if base is None:
            base = per
            rose = float("nan")
        else:
            rose = 100.0 * float(np.mean(per > base))
        print("  %-10s %-22s %10.3f %10.3f %10.3f   %s"
              % (lab, "%.1f-%.1f Hz" % bd, np.median(per), np.mean(per),
                 np.sqrt(whole_num / whole_den),
                 "--" if np.isnan(rose) else "%.1f %%" % rose))
print("""
  READING: the WHOLE-RUN column is a true Parseval band-RMS ratio and MUST rise with bandwidth.
  If it rises while the MEDIAN falls, my statistic is not a density -- it is being moved by TIME
  REDISTRIBUTION, and the median is the fragile part, not the units.""")

# ---------------------------------------------------------------- TEST B
hdr("TEST B -- 🛑 THE DIRECT LEAKAGE MEASUREMENT.  Hann 1 s band POWER / TRUE band power.\n"
    "         True power from a long FFT over the same samples (df ~0.01 Hz).  This is THE test.")
print("  %-10s %10s %12s %12s %10s   %s"
      % ("arm", "n runs", "Hann 1s", "TRUE(longFFT)", "RATIO", "verdict"))
for rt, lab in ARMS:
    hann_tot, true_tot, nrun = 0.0, 0.0, 0
    win = np.hanning(100)
    scale = np.mean(win ** 2)
    for x, FS, WL in runs(rt):
        if len(x) < 4000:
            continue
        nrun += 1
        f = np.fft.rfftfreq(len(x), 1.0 / FS)
        X = np.fft.rfft(x - x.mean())
        p = (np.abs(X) ** 2) * 2.0 / (len(x) ** 2)
        true_tot += float(p[(f >= 21.5) & (f < 25.5)].sum()) * (len(x) // 100)
        for i in range(0, len(x) - 100 + 1, 100):
            s = x[i:i + 100]
            r = np.arange(100.0)
            c = np.polyfit(r, s, 1)
            y = (s - (c[0] * r + c[1])) * win
            Y = np.fft.rfft(y)
            ff = np.fft.rfftfreq(100, 1.0 / FS)
            pp = (np.abs(Y) ** 2) * 2.0 / (100 ** 2) / scale
            hann_tot += float(pp[(ff >= 21.5) & (ff < 25.5)].sum())
    if not nrun:
        continue
    ratio = hann_tot / max(true_tot, 1e-30)
    v = ("🛑 LOSES %.0f %% -- leakage" % (100 * (1 - ratio))) if ratio < 0.75 else \
        ("~unbiased" if ratio > 0.9 else "loses %.0f %%" % (100 * (1 - ratio)))
    print("  %-10s %10d %12.4g %12.4g %10.3f   %s" % (lab, nrun, hann_tot, true_tot, ratio, v))

# ---------------------------------------------------------------- TEST C
hdr("TEST C -- BURSTINESS of the 21.5-25.5 Hz content (1 s band power, p90/p50 and p99/p50).")
print("  %-10s %10s %10s %10s   %s" % ("arm", "p50", "p90/p50", "p99/p50", "reading"))
for rt, lab in ARMS:
    vals = []
    for x, FS, WL in runs(rt):
        n_ = F.bp(x, 0, len(x), FS, 21.5, 25.5)
        for i in range(0, len(x) - WL + 1, WL):
            vals.append(float(np.mean(n_[i:i + WL] ** 2)))
    v = np.array(vals)
    q = np.percentile(v, [50, 90, 99])
    print("  %-10s %10.4g %10.2f %10.2f   %s"
          % (lab, q[0], q[1] / q[0], q[2] / q[0],
             "BURSTY" if q[1] / q[0] > 6 else "moderately bursty" if q[1] / q[0] > 3 else "steady"))

# ---------------------------------------------------------------- TEST D
hdr("TEST D -- THE HANDS DEFINITIONS.  Mine was a TORQUE THRESHOLD; route-stock's is `press`.")
print("  %-10s %10s %14s %14s %12s %12s"
      % ("arm", "eng win", "|tq|p50>=400 ct", "press>0.5", "|tq| p50", "|tq| p90"))
for rt, lab in ARMS:
    z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[rt], allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    dtq = np.abs(np.asarray(z["cs_tq"], float))
    pr = np.asarray(z["cs_press"], float) if "cs_press" in z else np.zeros(len(t))
    WL = int(round(1.0 * FS))
    a1, a2, tq = [], [], []
    for a, b in F.runs_break(lat, t, WL):
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            m = float(np.median(dtq[a:b][sl]))
            a1.append(m >= 400)
            a2.append(float(np.mean(pr[a:b][sl])) > 0.5)
            tq.append(m)
    a1, a2, tq = np.array(a1), np.array(a2), np.array(tq)
    print("  %-10s %10d %13.1f %% %13.1f %% %12.0f %12.0f"
          % (lab, len(a1), 100 * a1.mean(), 100 * a2.mean(),
             np.median(tq), np.percentile(tq, 90)))
