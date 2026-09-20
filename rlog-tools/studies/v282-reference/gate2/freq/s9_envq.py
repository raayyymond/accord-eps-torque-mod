"""STEP 9 -- pointwise-masked envelope quantiles. Complements STEP 8.

STEP 8 needs 8 s of UNBROKEN engaged/hands-off/speed mask, which silently drops the very
episodes that matter (several r73 bursts sit in runs the driver touched at one end). Here the
bandpass + analytic envelope are computed on the whole route (so no edge effects inside the
episode) and only then sampled at the masked instants, and quantiles are taken. A limit cycle
shows up as a fat upper tail, which the median cannot see and the mean over-weights.

python s9_envq.py [vmin]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS, HERE

BANDS = [("2.0-2.6", 2.0, 2.6), ("2.4-2.8", 2.4, 2.8), ("2.8-3.6", 2.8, 3.6),
         ("4.0-6.5", 4.0, 6.5), ("4.0-5.5", 4.0, 5.5), ("1.7-1.9", 1.7, 1.9)]
ORDER = ["r71", "r73", "r72", "r75", "v282a", "v282b", "v282c"]
RNG = np.random.default_rng(99)


def env(x, lo, hi):
    b, a = sig.butter(3, [lo / (FS / 2), hi / (FS / 2)], btype="band")
    return np.abs(sig.hilbert(sig.filtfilt(b, a, sig.detrend(x, type="constant"))))


if __name__ == "__main__":
    vmin = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    ch = "rate"
    R = {}
    for k in ORDER:
        D = load(k)
        m = engaged_mask(D, vmin=vmin)
        eb = env(D[ch], 0.5, 15.0)[m]
        R[k] = {"n": int(m.sum()), "bb99": float(np.percentile(eb, 99))}
        for nm, lo, hi in BANDS:
            e = env(D[ch], lo, hi)[m]
            R[k][nm] = (float(np.percentile(e, 50)), float(np.percentile(e, 95)),
                        float(np.percentile(e, 99)), float(np.percentile(e, 99.9)), float(e.max()))
        del D
    print(f"BANDPASS ENVELOPE of steeringRateDeg (deg/s), engaged hands-off v>={vmin}, "
          f"pointwise mask\n")
    for nm, lo, hi in BANDS:
        print(f"-- {nm} Hz --  {'route':7s} {'sec':>6s} {'p50':>7s} {'p95':>7s} {'p99':>8s} "
              f"{'p99.9':>8s} {'max':>8s}  {'p99/bb99':>8s}")
        for k in ORDER:
            a = R[k][nm]
            print(f"{'':14s}{k:7s} {R[k]['n']/FS:6.0f} {a[0]:7.3f} {a[1]:7.3f} {a[2]:8.3f} "
                  f"{a[3]:8.3f} {a[4]:8.2f}  {a[2]/R[k]['bb99']:8.3f}")
        print()
