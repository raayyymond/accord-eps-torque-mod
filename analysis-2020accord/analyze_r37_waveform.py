#!/usr/bin/env python3
"""Waveform shape of the ~7.4 Hz ratchet: friction limit cycle (stick-slip) or linear resonance?

Deliverable 4. A linear resonance rings sinusoidally; a friction limit cycle is an asymmetric
sawtooth -- slow elastic build-up, fast slip collapse. The distinction constrains the fix: a
resonance is attacked with damping/notch, a stick-slip cycle with the friction-compensation or
deadband term.

Metrics, all on the raw bar high-passed above 4 Hz (removes the driver's own input, keeps the
harmonics that carry the shape -- a 6-9 Hz BANDPASS would sinusoidalise any waveform by
construction and is therefore useless for this question):

  CREST      peak / RMS.  Pure sinusoid 1.414; sawtooth ~1.73; impulsive stick-slip > 2.
  RISE FRAC  fraction of samples with d/dt > 0.  Sinusoid 0.50; slow-build/fast-collapse >> 0.5.
  DSKEW      skewness of d/dt.  Sinusoid 0; asymmetric collapse gives |skew| >> 0.
  CYCLE      ensemble mean cycle, peak-aligned, in counts -- printed so the shape is visible.

Alignment uses the 6-9 Hz bandpass ONLY to find cycle boundaries; the averaged waveform is the
high-passed raw signal, so harmonic content survives.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.stats import skew

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402


def hp(x, fs, fc=4.0):
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f < fc] = 0
    return np.fft.irfft(X, n=len(x))


def shape(x, fs, lab, show_cycle=True):
    """Waveform metrics on one contiguous stretch."""
    y = hp(x, fs)
    b = L.bandpass(x, fs, 6.0, 9.0)
    d = np.diff(y)
    crest = float(np.max(np.abs(y)) / max(np.sqrt(np.mean(y ** 2)), 1e-9))
    rise = float(np.mean(d > 0))
    ds = float(skew(d))
    ys = float(skew(y))
    # cycle boundaries from the bandpass's upward zero crossings
    zc = np.flatnonzero((b[:-1] <= 0) & (b[1:] > 0))
    print(f"  {lab:34s} n={len(x):5d}  RMS={np.sqrt(np.mean(y**2)):7.1f}  "
          f"crest={crest:5.2f}  rise_frac={rise:5.3f}  skew(dx/dt)={ds:+6.2f}  "
          f"skew(x)={ys:+6.2f}  cycles={len(zc)-1}")
    if not show_cycle or len(zc) < 4:
        return
    per = np.median(np.diff(zc))
    n = int(round(per))
    if n < 6:
        return
    acc, k = np.zeros(n), 0
    for a in zc[:-1]:
        if a + n <= len(y):
            acc += y[a:a + n]
            k += 1
    if k < 3:
        return
    cyc = acc / k
    amp = np.max(np.abs(cyc)) or 1.0
    print(f"      ensemble mean cycle over {k} cycles, period {per:.1f} samples "
          f"({fs/per:.2f} Hz), peak {np.max(np.abs(cyc)):.0f} counts:")
    for i, vv in enumerate(cyc):
        pos = int(round(30 + 28 * vv / amp))
        print(f"      {i:3d} {100*i/n:5.1f}% {vv:+8.1f} |" + " " * pos + "*")
    ipk = int(np.argmax(cyc))
    itr = int(np.argmin(cyc))
    print(f"      peak at {100*ipk/n:.0f}% of cycle, trough at {100*itr/n:.0f}%  ->  "
          f"build {100*abs(ipk-itr)/n:.0f}% / collapse {100*(n-abs(ipk-itr))/n:.0f}%")


def main():
    cache, pfx = C.ROOT / "_cache_r37", "r37s"

    print("=" * 120)
    print("A. THE TWO OPERATOR INSTANTS -- waveform of the raw bar, high-passed >4 Hz")
    print("=" * 120)
    for s, t0, t1, lab in ((1, 10.24, 11.17, "INSTANT 1  seg1 10.24-11.17 s (10:12:15)"),
                           (1, 8.00, 13.00, "  instant 1, widened 8-13 s"),
                           (12, 17.76, 19.09, "INSTANT 2  seg12 17.76-19.09 s (10:23:24)"),
                           (12, 16.00, 21.00, "  instant 2, widened 16-21 s")):
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        m = (d["t"] >= t0) & (d["t"] <= t1)
        shape(d["tq"][m], fs, lab, show_cycle=(t1 - t0) > 2)
        print()

    print("=" * 120)
    print("B. A CANONICAL RATCHET EPISODE -- seg 13 parking lot, the largest on the route")
    print("=" * 120)
    d = C.load(13, cache, pfx)
    fs = C.fs_of(d)
    for t0, t1 in ((0.0, 6.0), (12.0, 18.0), (25.0, 32.0)):
        m = (d["t"] >= t0) & (d["t"] <= t1)
        shape(d["tq"][m], fs, f"seg13 {t0:.0f}-{t1:.0f} s", show_cycle=(t0 == 0.0))
        print()

    print("=" * 120)
    print("C. CONTROL WAVEFORMS -- a pure tone and a sawtooth at the same f0/fs, for calibration")
    print("=" * 120)
    fs = 100.5
    t = np.arange(600) / fs
    for lab, sig in (("synthetic SINE 7.4 Hz", 900 * np.sin(2 * np.pi * 7.4 * t)),
                     ("synthetic SAWTOOTH 7.4 Hz",
                      900 * (2 * ((7.4 * t) % 1.0) - 1)),
                     ("synthetic STICK-SLIP 7.4 Hz (slow build, fast collapse)",
                      900 * (1 - 2 * np.clip(((7.4 * t) % 1.0) / 0.15, 0, 1)) * -1
                      + 900 * (2 * ((7.4 * t) % 1.0) - 1) * 0)):
        shape(sig, fs, lab, show_cycle=False)

    print("\n" + "=" * 120)
    print("D. IS THE SHAPE BUILD-DEPENDENT? same metric, engaged creep episodes, every route")
    print("=" * 120)
    for nm, ca, pf, sg in L.ROUTES:
        vals = []
        for s in sg:
            p = ca / f"{pf}{s}.npz"
            if not p.exists():
                continue
            dd = C.load(s, ca, pf)
            fss = C.fs_of(dd)
            g = (dd["cs_gear"] == 2.0) if "cs_gear" in dd else np.ones(len(dd["t"]), bool)
            mk = (dd["cc_lat"] > 0.5) & g & (dd["cs_v"] > 0.3) & (dd["cs_v"] < 2.5)
            for a, b in C.runs_of(mk, dd["t"], 256):
                y = hp(dd["tq"][a:b], fss)
                if np.sqrt(np.mean(y ** 2)) < 100:      # only episodes with real energy
                    continue
                dv = np.diff(y)
                vals.append((float(np.max(np.abs(y)) / np.sqrt(np.mean(y ** 2))),
                             float(np.mean(dv > 0)), float(skew(dv)), float(skew(y))))
        if not vals:
            print(f"  {nm:14s} (no episode with RMS>100)")
            continue
        a = np.array(vals)
        print(f"  {nm:14s} nep={len(vals):3d} | crest {np.median(a[:,0]):5.2f} | "
              f"rise_frac {np.median(a[:,1]):5.3f} | skew(dx/dt) {np.median(a[:,2]):+6.2f} | "
              f"skew(x) {np.median(a[:,3]):+6.2f}")


if __name__ == "__main__":
    main()
