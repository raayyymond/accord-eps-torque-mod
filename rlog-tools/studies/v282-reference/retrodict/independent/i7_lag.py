# -*- coding: utf-8 -*-
"""i7 -- how much LAG is really between the logged command and the wheel, measured three ways.

The 0.20-1.0 Hz plant phase (i6) reads like ~0.3-0.4 s of excess lag with a FLAT magnitude, which is
too much for the fork's 55-75 ms budget and is not a minimum-phase pole.  Before that is believed it
has to survive an independent, time-domain measurement, so this script measures:

  (a) out -> 0xE4 command            (controlsState.output vs the CAN frame actually sent)
  (b) out -> steering RATE           (peak of the cross-correlation, band-limited)
  (c) out -> steering ANGLE
on engaged, hands-off stretches, per speed bin.  A transport delay shows as a lag that is the SAME at
every band; a lag POLE shows as a lag that shrinks with frequency.  Both are reported.

ANALYSIS ONLY.  python i7_lag.py <route> [...]
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
BANDS = [(0.10, 0.40), (0.30, 0.80), (0.60, 1.50), (1.20, 3.00)]
MAXLAG = int(0.8 * FS)


def xlag(x, y, band):
    sos = signal.butter(4, band, btype="band", fs=FS, output="sos")
    a = signal.sosfiltfilt(sos, x - x.mean())
    b = signal.sosfiltfilt(sos, y - y.mean())
    a /= max(a.std(), 1e-12)
    b /= max(b.std(), 1e-12)
    c = signal.correlate(b, a, mode="full") / len(a)
    lags = signal.correlation_lags(len(b), len(a), mode="full")
    k = (np.abs(lags) <= MAXLAG)
    c, lags = c[k], lags[k]
    j = int(np.argmax(c))
    # parabolic refine
    if 0 < j < len(c) - 1:
        d = 0.5 * (c[j - 1] - c[j + 1]) / max(c[j - 1] - 2 * c[j] + c[j + 1], 1e-12)
        d = float(np.clip(d, -1, 1))
    else:
        d = 0.0
    return (lags[j] + d) / FS, float(c[j])


def run(route):
    S = V.load(route)
    m = S["active"] & ~S["pressed"] & ~S["sat"]
    for key in ("out", "sr", "sa", "e4"):
        m &= np.isfinite(S[key])
    print(f"\n=== {route} ===")
    for lo, hi, tag in ((15.0, 99.0, ">=15 m/s"), (5.0, 15.0, "5-15 m/s")):
        mm = m & (S["v"] >= lo) & (S["v"] < hi)
        segs = [(a, b) for a, b in V.runs(mm, S["t"], min_s=40.0)]
        if not segs:
            continue
        print(f"  {tag}: {len(segs)} runs, {sum(b-a for a, b in segs)/FS:.0f} s")
        print(f"    {'band':12s} {'out->e4':>16s} {'out->rate':>16s} {'out->angle':>16s}")
        for band in BANDS:
            res = []
            for tgt in ("e4", "sr", "sa"):
                ls, cs, wt = [], [], []
                for a, b in segs:
                    if b - a < 8 * FS:
                        continue
                    L, C = xlag(np.nan_to_num(S["out"][a:b]), np.nan_to_num(S[tgt][a:b]), band)
                    ls.append(L); cs.append(C); wt.append(b - a)
                if not ls:
                    res.append((np.nan, np.nan))
                    continue
                res.append((float(np.average(ls, weights=wt)), float(np.average(cs, weights=wt))))
            print(f"    {band[0]:.2f}-{band[1]:.2f} Hz " +
                  " ".join(f"{r[0]*1000:+7.0f} ms r{r[1]:+.2f}" for r in res))
    del S


if __name__ == "__main__":
    for r in sys.argv[1:]:
        run(r)
