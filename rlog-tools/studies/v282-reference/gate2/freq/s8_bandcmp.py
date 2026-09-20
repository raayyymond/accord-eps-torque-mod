"""STEP 8 -- band-power comparison across routes, with block-bootstrap CIs.

Non-overlapping 8 s windows inside the engaged / hands-off / v>=vmin mask. Per window:
band power of `rate` (deg/s)^2, and the same divided by 0.5-15 Hz total (the shape-only
version, which removes "this route was driven harder"). Route statistic = mean over windows.
CI = moving-block bootstrap (blocks of 4 consecutive windows, 4000 draws) because bursts are
serially correlated, so an i.i.d. bootstrap would understate the CI badly.

python s8_bandcmp.py [vmin] [channel]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import ROUTES, load, engaged_mask, runs, FS, HERE

WIN_S = 8.0
BANDS = [("2.0-2.6", 2.0, 2.6), ("2.0-2.7", 2.0, 2.7), ("1.7-1.9", 1.7, 1.9),
         ("2.4-2.8", 2.4, 2.8), ("4.0-6.5", 4.0, 6.5), ("4.0-5.5", 4.0, 5.5),
         ("2.8-3.6", 2.8, 3.6), ("0.5-15", 0.5, 15.0)]
ORDER = ["r71", "r73", "r72", "r75", "v282a", "v282b", "v282c"]
RNG = np.random.default_rng(1071073)


def windows(key, vmin, ch="rate"):
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    nper = int(WIN_S * FS)
    w = sig.get_window("hann", nper)
    f = np.fft.rfftfreq(nper, 1 / FS)
    rows = []
    for a, b in runs(m, min_s=WIN_S):
        for i in range(a, b - nper + 1, nper):
            seg = sig.detrend(D[ch][i:i + nper], type="linear")
            P = np.abs(np.fft.rfft(seg * w)) ** 2 / (FS * (w ** 2).sum())
            P[1:-1] *= 2
            bp = [float(np.trapezoid(P[(f >= lo) & (f <= hi)], f[(f >= lo) & (f <= hi)]))
                  for _, lo, hi in BANDS]
            rows.append(bp)
    del D
    return np.array(rows)


def block_boot(x, n=4000, blk=4):
    x = np.asarray(x, float)
    N = len(x)
    if N < blk + 1:
        return np.nan, np.nan
    nb = int(np.ceil(N / blk))
    out = np.empty(n)
    starts_max = N - blk
    for k in range(n):
        s = RNG.integers(0, starts_max + 1, nb)
        idx = (s[:, None] + np.arange(blk)[None, :]).ravel()[:N]
        out[k] = x[idx].mean()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def ratio_boot(x, y, n=4000, blk=4):
    """CI on mean(x)/mean(y) by independent block bootstrap of each."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < blk + 1 or len(y) < blk + 1:
        return np.nan, np.nan
    r = np.empty(n)
    for k in range(n):
        nbx = int(np.ceil(len(x) / blk)); nby = int(np.ceil(len(y) / blk))
        sx = RNG.integers(0, len(x) - blk + 1, nbx)
        sy = RNG.integers(0, len(y) - blk + 1, nby)
        ix = (sx[:, None] + np.arange(blk)[None, :]).ravel()[:len(x)]
        iy = (sy[:, None] + np.arange(blk)[None, :]).ravel()[:len(y)]
        r[k] = x[ix].mean() / max(y[iy].mean(), 1e-30)
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


if __name__ == "__main__":
    vmin = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    ch = sys.argv[2] if len(sys.argv) > 2 else "rate"
    W = {k: windows(k, vmin, ch) for k in ORDER}
    print(f"BAND POWER of {ch}, engaged hands-off v>={vmin} m/s, {WIN_S:.0f}s windows, "
          f"mean +- block-bootstrap 95% CI\n")
    for bi, (name, lo, hi) in enumerate(BANDS):
        if name == "0.5-15":
            continue
        print(f"-- band {name} Hz --   {'route':7s} {'n':>4s} {'mean power':>22s} "
              f"{'rms deg/s':>9s} {'share of 0.5-15':>16s}")
        for k in ORDER:
            A = W[k]
            if not len(A):
                print(f"{'':22s}{k:7s}  no windows"); continue
            x = A[:, bi]
            lo95, hi95 = block_boot(x)
            sh = A[:, bi] / np.maximum(A[:, -1], 1e-30)
            s_lo, s_hi = block_boot(sh)
            print(f"{'':22s}{k:7s} {len(A):4d} {x.mean():9.4g} [{lo95:8.4g},{hi95:8.4g}] "
                  f"{np.sqrt(x.mean()):9.3f} {sh.mean():7.4f} [{s_lo:.4f},{s_hi:.4f}]")
        print()
    # explicit ratios the gate cares about
    print("RATIOS (mean band power), block-bootstrap 95% CI")
    pairs = [("r73", "r72"), ("r71", "r72"), ("r71", "r75"), ("r73", "r75"),
             ("r71", "v282c"), ("r73", "v282c"), ("r75", "r72")]
    for bi, (name, lo, hi) in enumerate(BANDS):
        if name == "0.5-15":
            continue
        for a, b in pairs:
            if not len(W[a]) or not len(W[b]):
                continue
            x, y = W[a][:, bi], W[b][:, bi]
            r = x.mean() / max(y.mean(), 1e-30)
            rl, rh = ratio_boot(x, y)
            print(f"   {name:8s} {a:6s}/{b:6s} = {r:8.2f}x  [{rl:7.2f},{rh:8.2f}]")
        print()
    np.savez_compressed(HERE / f"s8_band_{ch}_v{vmin:.0f}.npz",
                        bands=np.array([b[0] for b in BANDS]), **W)
