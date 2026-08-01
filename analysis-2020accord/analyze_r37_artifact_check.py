#!/usr/bin/env python3
"""Is the ~42 Hz line in r37 seg1 real, or a resampling / dropout artifact?

`tq` is 0x18F (~100 Hz) held-last onto the 0x14A arrival grid (~100.5 Hz). Two near-equal rates
zero-order-held against each other inject a sample-repeat/skip error, and a near-Nyquist line is
exactly what that would look like. Three independent tests:

  A. 0x18F and 0x14A native arrival statistics inside the window -- gaps, jitter, repeat runs.
  B. Repeated-sample fraction of `tq` (a ZOH artifact repeats samples; a real 42 Hz oscillation
     does not).
  C. Harmonic test: 42 Hz vs 2x the 21 Hz fundamental in the SAME window, plus the same free
     spectrum computed on the NATIVE 0x18F sequence (its own index grid, no resampling at all).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402

C.CACHE = C.ROOT / "_cache_r37"
PFX = "r37s"


def show(s, lo, hi):
    d = C.load(s, C.CACHE, PFX)
    fs = C.fs_of(d)
    m = (d["t"] >= lo) & (d["t"] <= hi)
    a, b = int(np.flatnonzero(m)[0]), int(np.flatnonzero(m)[-1]) + 1
    tq = d["tq"][a:b]
    t = d["t"][a:b]
    print(f"\n=== seg{s} t {lo}..{hi}  n={b-a}  fs={fs:.3f}  Nyquist={fs/2:.2f} ===")

    # ---- A. native arrival statistics ----------------------------------------------------
    for nm in ("raw18F", "raw14A"):
        r = d[nm]
        r = r[(r >= lo) & (r <= hi)]
        dt = np.diff(r)
        print(f"  {nm}: n={len(r)}  rate={1/np.median(dt):.3f} Hz  "
              f"dt med={1000*np.median(dt):.2f} ms  p1={1000*np.percentile(dt,1):.2f}  "
              f"p99={1000*np.percentile(dt,99):.2f}  max={1000*dt.max():.2f}  "
              f"gaps>15ms={int((dt>0.015).sum())}")

    # ---- B. repeated-sample structure -----------------------------------------------------
    rep = (np.diff(tq) == 0)
    print(f"  tq repeated-consecutive-sample fraction: {100*rep.mean():.2f}%  "
          f"(a ZOH of a 100 Hz stream onto a 100.5 Hz grid repeats ~0.5% of samples)")
    print(f"  tq range {tq.min():.0f}..{tq.max():.0f}  "
          f"|diff| med={np.median(np.abs(np.diff(tq))):.1f} max={np.abs(np.diff(tq)).max():.0f}")
    j = int(np.argmax(np.abs(np.diff(tq))))
    print(f"  largest single-sample jump: {np.abs(np.diff(tq))[j]:.0f} counts at t={t[j]:.3f}")

    # ---- C. spectrum on the RESAMPLED grid vs the NATIVE 0x18F sequence --------------------
    nf = 256
    f = np.fft.rfftfreq(nf, 1 / fs)
    for i0 in range(0, len(tq) - nf + 1, nf // 2):
        P = C.periodogram(tq[i0:i0 + nf], fs, nf)
        if P is None:
            continue
        f21, p21 = C.peak_prom(f, P, 18.0, 26.0)
        f42, p42 = C.peak_prom(f, P, 35.0, 47.0)
        # power ratio of the two, and whether 42 is within 0.6 Hz of 2*f21
        near = abs(f42 - 2 * f21) if np.isfinite(f21) and np.isfinite(f42) else np.nan
        j21 = int(np.argmin(np.abs(f - f21))) if np.isfinite(f21) else 0
        j42 = int(np.argmin(np.abs(f - f42))) if np.isfinite(f42) else 0
        print(f"   t={t[i0]:6.2f}  f21={f21:6.2f} p={p21:7.2f}   f42={f42:6.2f} p={p42:7.2f}   "
              f"|f42-2*f21|={near:5.2f} Hz   P42/P21={P[j42]/max(P[j21],1e-30):8.4f}")


if __name__ == "__main__":
    show(1, 6.0, 14.0)
    show(1, 8.0, 13.0)
