"""Verify the phasor-lag formula used in s1_analyze.py (lines ~147-151) against synthetic data with a
KNOWN lag, reproducing the exact steps: build pD = x delayed by LD samples then delayed further by an
extra residual delay dtau_true, take Hilbert analytic signals of x and pD restricted to one band, and
check that
    lag_est = ld_assumed - angle( sum(pD_analytic * conj(x_analytic)) / sum(|x_analytic|^2) ) / (2*pi*fc)
recovers ld_assumed + dtau_true, for several bands and several true delays (including delays that are
NOT small vs 1/fc, to probe the narrowband-phase-only-vs-broadband-mix assumption implicit in using a
single fc = sqrt(f1*f2) for a phase-to-time conversion across the whole band).
"""
import numpy as np
from scipy import signal

FS = 100.0
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.50)]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def frac_delay(x, tau_samples):
    """Delay x by a (possibly fractional) number of samples via FFT phase shift (exact for periodic-ish
    windowed signal; fine for this synthetic check)."""
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1 / FS)
    ph = np.exp(-1j * 2 * np.pi * freqs * (tau_samples / FS))
    return np.fft.irfft(X * ph, n)


def run_case(f1, f2, ld_assumed_s, dtau_true_s, seed, T=120.0, band_energy_shape=None):
    rng = np.random.default_rng(seed)
    n = int(T * FS)
    t = np.arange(n) / FS
    # broadband-ish desired signal, energy concentrated near the band under test plus some out-of-band
    # content (as a real model-lat-accel signal has), so the estimator sees what it sees in practice.
    white = rng.standard_normal(n)
    x_full = bp(white, max(f1 * 0.5, 0.02), min(f2 * 2.0, 3.0)) * 2.0  # broader than test band
    x_full += 0.3 * bp(rng.standard_normal(n), 0.02, 5.0)
    LD = int(round(ld_assumed_s * FS))
    total_delay_s = ld_assumed_s + dtau_true_s
    y_full = frac_delay(x_full, total_delay_s * FS)
    # pD as s1_reduce builds it: shift y by LD samples forward in the "at()" sense -> y sampled at t+LD,
    # i.e. pD(t) = y(t + LD/FS). Since y(t) = x(t - total_delay), pD(t) = x(t + LD/FS - total_delay)
    #            = x(t - dtau_true).  (residual delay only)
    def at(y, L):
        ii = np.arange(len(y))
        return y[np.minimum(ii + L, len(y) - 1)]
    pD_full = at(y_full, LD)
    trim = int(0.5 / f1 * FS)
    xb = bp(x_full, f1, f2)[trim:-trim]
    pDb = bp(pD_full, f1, f2)[trim:-trim]
    xa = signal.hilbert(xb.astype(np.float64))
    pDa = signal.hilbert(pDb.astype(np.float64))
    den = float(np.sum(np.abs(xa) ** 2))
    hc = complex(np.sum(pDa * np.conj(xa))) / den
    fc = float(np.sqrt(f1 * f2))
    lag_est = ld_assumed_s - np.angle(hc) / (2 * np.pi * fc)
    Hc = abs(hc)
    return lag_est, Hc, total_delay_s


print("band            ld_s  dtau_true  true_total  lag_est   err_ms   |Hc|")
bad = []
for (f1, f2) in BANDS[:4]:
    for ld_assumed_s in (0.20, 0.30):
        for dtau_true_s in (0.0, 0.05, 0.10, 0.20, 0.30, -0.10):
            lag_est, Hc, true_total = run_case(f1, f2, ld_assumed_s, dtau_true_s, seed=hash((f1, ld_assumed_s, dtau_true_s)) % 2**31)
            err_ms = (lag_est - true_total) * 1000
            flag = "  <-- BAD" if abs(err_ms) > 15 else ""
            if abs(err_ms) > 15:
                bad.append((f1, f2, ld_assumed_s, dtau_true_s, err_ms))
            print(f"{f1:.2f}-{f2:.2f}  {ld_assumed_s:.2f}  {dtau_true_s:+.2f}      {true_total:.3f}      {lag_est:.3f}   {err_ms:+7.1f}   {Hc:.3f}{flag}")

print()
print(f"{len(bad)} cases with |err| > 15 ms")
for b in bad:
    print("  ", b)
