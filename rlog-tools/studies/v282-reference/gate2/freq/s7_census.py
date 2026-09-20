"""STEP 7 -- amplitude-weighted frequency census, per route, blind to any target band.

Every 4 s window (hop 0.5 s) whose engaged/hands-off/speed mask holds throughout is
whitened (running median of log PSD in log-f) and its single most prominent feature in
1.2-9 Hz is recorded, with the sinusoid amplitude carried by that feature. Windows whose
prominence is below PROM_MIN are discarded as "no object". The census is then the
amplitude^2-weighted histogram of those peak frequencies: it says where each route's
oscillatory energy actually lives, without ever being told where to look.

python s7_census.py [vmin] [channel]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import ROUTES, load, engaged_mask, FS, HERE

WIN_S, HOP_S = 4.0, 0.5
LO, HI = 1.2, 9.0
PROM_MIN = 8.0
LOGW = 0.35
ORDER = ["r71", "r73", "r72", "r75", "v282a", "v282b", "v282c"]
EDGES = np.array([1.2, 1.6, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 4.5, 5.0, 5.5, 6.5, 7.5, 9.0])


def census(key, vmin, ch="rate"):
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    x = D[ch]
    nper, hop = int(WIN_S * FS), int(HOP_S * FS)
    w = sig.get_window("hann", nper)
    f = np.fft.rfftfreq(nper, 1 / FS)
    fm = (f >= 0.5) & (f <= 20.0)
    lf = np.log10(f[fm])
    nb = [np.abs(lf - x0) <= LOGW for x0 in lf]
    sel = (f[fm] >= LO) & (f[fm] <= HI)
    isel = np.flatnonzero(sel)
    rows = []
    n_win = 0
    for i in range(0, len(x) - nper + 1, hop):
        if not m[i:i + nper].all():
            continue
        n_win += 1
        seg = sig.detrend(x[i:i + nper], type="linear")
        P = np.abs(np.fft.rfft(seg * w)) ** 2 / (FS * (w ** 2).sum())
        P[1:-1] *= 2
        Pm = P[fm]
        lg = np.log(Pm + 1e-300)
        base = np.array([np.median(lg[b]) for b in nb])
        wh = lg - base
        j = isel[np.argmax(wh[isel])]
        prom = float(np.exp(wh[j]))
        if prom < PROM_MIN:
            continue
        fpk = f[fm][j]
        bm = (f[fm] > fpk * 0.86) & (f[fm] < fpk * 1.14)
        amp = float(np.sqrt(2 * np.trapezoid(Pm[bm], f[fm][bm])))
        rows.append((D["t"][i + nper // 2], fpk, prom, amp, float(D["vego"][i:i + nper].mean()),
                     float(np.abs(D["angle"][i:i + nper]).max())))
    del D
    return np.array(rows) if rows else np.zeros((0, 6)), n_win


if __name__ == "__main__":
    vmin = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    ch = sys.argv[2] if len(sys.argv) > 2 else "rate"
    print(f"AMPLITUDE-WEIGHTED FREQUENCY CENSUS -- channel {ch}, engaged hands-off v>={vmin} m/s,"
          f" {WIN_S}s windows, prominence>={PROM_MIN}\n")
    hdr = "  ".join(f"{EDGES[i]:.1f}-{EDGES[i+1]:.1f}" for i in range(len(EDGES) - 1))
    print(f"{'route':7s} {'win':>5s} {'obj':>4s} {'sum A^2 (deg/s)^2':>17s}   {hdr}")
    out = {}
    for k in ORDER:
        R, nw = census(k, vmin, ch)
        out[k] = R
        if not len(R):
            print(f"{k:7s} {nw:5d} {0:4d}"); continue
        wgt = R[:, 3] ** 2
        tot = wgt.sum()
        h, _ = np.histogram(R[:, 1], bins=EDGES, weights=wgt)
        frac = h / max(tot, 1e-30)
        # normalise by observation time so routes of different length compare
        dens = tot / max(nw, 1)
        s = "  ".join(f"{v*100:6.1f}" for v in frac)
        print(f"{k:7s} {nw:5d} {len(R):4d} {dens:17.3f}   {s}")
    np.savez_compressed(HERE / f"s7_census_{ch}_v{vmin:.0f}.npz", **out)
    print(f"\n(row = % of that route's oscillatory A^2 in each Hz bin; 'sum A^2' is per scored window)")
    print("wrote", HERE / f"s7_census_{ch}_v{vmin:.0f}.npz")
