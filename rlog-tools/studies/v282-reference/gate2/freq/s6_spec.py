"""STEP 6 -- print the whitened spectrum of a window, so the object is read off directly.

Whitening = log PSD minus a running median of log PSD in log-frequency (factor-2.2 window).
A pure power law whitens flat; only narrow features stand up. Printed as an ASCII bar chart
so no plotting is needed to see whether there is ONE object or several.

python s6_spec.py <route> <t0> <t1> [channels]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS


def whitened(x, nfft=None, logw=0.35):
    x = sig.detrend(np.asarray(x), type="linear")
    n = len(x)
    w = np.hanning(n)
    P = np.abs(np.fft.rfft(x * w)) ** 2 / (FS * (w ** 2).sum())
    P[1:-1] *= 2
    f = np.fft.rfftfreq(n, 1 / FS)
    m = (f >= 0.5) & (f <= 20.0)
    lf, lg = np.log10(f[m]), np.log(P[m] + 1e-300)
    base = np.array([np.median(lg[np.abs(lf - x0) <= logw]) for x0 in lf])
    return f[m], P[m], np.exp(lg - base)


def main(key, t0, t1, chs):
    D = load(key)
    t = D["t"]
    m = (t >= t0) & (t <= t1)
    eng = engaged_mask(D)
    print(f"== {key} {D['route']} {t0:.0f}-{t1:.0f}s  eng-handsoff {eng[m].mean()*100:.0f}%  "
          f"v {D['vego'][m].mean():.1f} m/s  |ang| {np.abs(D['angle'][m]).max():.0f} deg")
    for ch in chs:
        f, P, W = whitened(D[ch][m])
        sel = (f >= 1.0) & (f <= 9.0)
        ff, WW, PP = f[sel], W[sel], P[sel]
        # bin to 0.25 Hz for printing
        edges = np.arange(1.0, 9.001, 0.25)
        print(f"  -- {ch}  (rms {D[ch][m].std():.4g}; whitened peak "
              f"{ff[np.argmax(WW)]:.2f} Hz x{WW.max():.0f})")
        for i in range(len(edges) - 1):
            b = (ff >= edges[i]) & (ff < edges[i + 1])
            if not b.any():
                continue
            v = WW[b].max()
            amp = np.sqrt(2 * np.trapezoid(PP[b], ff[b])) if b.sum() > 1 else 0.0
            bar = "#" * int(min(60, 12 * np.log10(max(v, 1.0)) * 2))
            print(f"     {edges[i]:5.2f} x{v:7.1f} A={amp:8.3g} {bar}")


if __name__ == "__main__":
    a = sys.argv
    chs = a[4].split(",") if len(a) > 4 else ["rate", "cmd", "err"]
    main(a[1], float(a[2]), float(a[3]), chs)
