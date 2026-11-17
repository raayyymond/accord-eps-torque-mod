"""Simulate the alias-test-2 statistic for a pure tone of true frequency f sampled at 100 Hz (angle quantised 0.1 deg,
rate quantised 1 deg/s, optional rate lag), to calibrate the sign of corr(d angle/dt, interval-mean rate)."""
import numpy as np
from scipy import signal
b, a = signal.butter(4, 10 / 50, "high")
rng = np.random.default_rng(0)
print("true f (Hz) | rate amp | rate lag ms | corr p50 | rms ratio | as-sampled f")
for amp in (13, 40):
    for lag in (0, 5):
        for f in (14, 16, 18, 30, 70, 82, 84, 86, 114, 116, 118):
            cs, rr = [], []
            for trial in range(20):
                ph = rng.uniform(0, 2 * np.pi); off = rng.uniform(-5, 5)
                t = np.arange(64) / 100.0
                ang = off + amp / (2 * np.pi * f) * np.sin(2 * np.pi * f * t + ph)
                rate = amp * np.cos(2 * np.pi * f * (t - lag / 1000) + ph)
                angq = np.round(ang / 0.1) * 0.1; rq = np.round(rate)
                da = np.r_[0, np.diff(angq)] / 0.01; rm = np.r_[rq[0], (rq[1:] + rq[:-1]) / 2]
                x, y = signal.filtfilt(b, a, da), signal.filtfilt(b, a, rm)
                cs.append(np.corrcoef(x, y)[0, 1]); rr.append(x.std() / y.std())
            fa = abs(f - 100 * round(f / 100))
            print("  %5.0f      %4d      %3d        %+.2f     %.2f      %.0f" % (f, amp, lag, np.nanmedian(cs), np.median(rr), fa))
