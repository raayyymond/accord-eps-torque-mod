"""STEP 12 -- the object spectrum per route, and the frequency of each route's own object
with a bootstrap CI, computed WITHOUT being told a band.

For every 4 s window whose engaged / hands-off / v>=vmin mask holds throughout:
  whitened spectrum (log PSD minus running median of log PSD in log-f).
Two summaries per route:
  (1) EXCESS SPECTRUM: the mean of (whitened - 1) over windows, weighted by each window's
      in-band amplitude^2, i.e. where the route's oscillatory energy actually is;
  (2) OBJECT FREQUENCY: the amplitude^2-weighted mean of the per-window whitened peak,
      restricted to windows whose peak prominence exceeds PROM_MIN, with a weighted
      bootstrap CI over windows.

python s12_objspec.py [vmin] [prom_min]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS, HERE

WIN_S, HOP_S = 4.0, 1.0
LO, HI = 1.5, 9.0
LOGW = 0.35
ORDER = ["r71", "r73", "r72", "r75", "v282a", "v282b", "v282c"]
RNG = np.random.default_rng(2026)


def run(key, vmin, prom_min):
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    x = D["rate"]
    nper, hop = int(WIN_S * FS), int(HOP_S * FS)
    w = sig.get_window("hann", nper)
    f = np.fft.rfftfreq(nper, 1 / FS)
    fm = (f >= 0.6) & (f <= 20.0)
    lf = np.log10(f[fm])
    nb = [np.abs(lf - x0) <= LOGW for x0 in lf]
    sel = (f[fm] >= LO) & (f[fm] <= HI)
    isel = np.flatnonzero(sel)
    Wacc = np.zeros(fm.sum()); Wn = 0
    pk, wt, pr = [], [], []
    for i in range(0, len(x) - nper + 1, hop):
        if not m[i:i + nper].all():
            continue
        P = np.abs(np.fft.rfft(sig.detrend(x[i:i + nper], type="linear") * w)) ** 2 \
            / (FS * (w ** 2).sum())
        P[1:-1] *= 2
        Pm = P[fm]
        lg = np.log(Pm + 1e-300)
        base = np.array([np.median(lg[b]) for b in nb])
        wh = np.exp(lg - base)
        Wacc += wh; Wn += 1
        j = isel[np.argmax(wh[isel])]
        fpk = f[fm][j]
        bm = (f[fm] > fpk * 0.86) & (f[fm] < fpk * 1.14)
        amp2 = 2 * float(np.trapezoid(Pm[bm], f[fm][bm]))
        pk.append(fpk); wt.append(amp2); pr.append(float(wh[j]))
    del D
    return f[fm], Wacc / max(Wn, 1), Wn, np.array(pk), np.array(wt), np.array(pr)


def wboot(v, w, n=4000):
    if len(v) < 4:
        return np.nan, np.nan
    r = np.empty(n)
    for k in range(n):
        i = RNG.integers(0, len(v), len(v))
        r[k] = np.average(v[i], weights=w[i]) if w[i].sum() > 0 else np.nan
    return float(np.nanpercentile(r, 2.5)), float(np.nanpercentile(r, 97.5))


if __name__ == "__main__":
    vmin = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    prom_min = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    print(f"OBJECT SPECTRUM -- steeringRateDeg, engaged hands-off v>={vmin}, {WIN_S:.0f}s windows\n")
    store = {}
    for k in ORDER:
        f, W, n, pk, wt, pr = run(k, vmin, prom_min)
        store[k] = (f, W, pk, wt, pr)
        good = pr >= prom_min
        if good.sum() >= 4:
            fw = float(np.average(pk[good], weights=wt[good]))
            lo, hi = wboot(pk[good], wt[good])
            o = np.argsort(pk[good]); cw = np.cumsum(wt[good][o]) / wt[good].sum()
            med = float(np.interp(0.5, cw, pk[good][o]))
            q1 = float(np.interp(0.25, cw, pk[good][o])); q3 = float(np.interp(0.75, cw, pk[good][o]))
            print(f"{k:7s} {n:4d} win  {good.sum():4d} with object   "
                  f"OBJECT f = {fw:5.2f} Hz  95% CI [{lo:5.2f},{hi:5.2f}]   "
                  f"amp-wt median {med:5.2f} IQR [{q1:5.2f},{q3:5.2f}]   "
                  f"sum A^2 {wt[good].sum():9.1f}")
        else:
            print(f"{k:7s} {n:4d} win  {good.sum():4d} with object   -- too few to pin")
    print("\nEXCESS SPECTRUM (mean whitened PSD, 1.0 = pure power-law background):")
    f = store["r71"][0]
    grid = np.arange(1.5, 7.01, 0.25)
    print(f"{'Hz':>5s} " + " ".join(f"{k:>7s}" for k in ORDER))
    for g in grid:
        j = int(np.argmin(np.abs(f - g)))
        print(f"{f[j]:5.2f} " + " ".join(f"{store[k][1][j]:7.2f}" for k in ORDER))
