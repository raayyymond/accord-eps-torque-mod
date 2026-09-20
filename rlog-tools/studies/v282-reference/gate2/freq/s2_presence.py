"""STEP 2 -- episodic detection. A limit cycle is a BURST; a 700 s Welch average buries it.

Sliding 8 s windows (hop 1 s) over the whole route. A window is scored only if the engaged
hands-off mask holds for the WHOLE window.

PROMINENCE IS MEASURED AGAINST A LOCAL LOG-FREQUENCY BASELINE, not a band median. Vehicle
spectra are steep red noise (~f^-3..f^-4); a peak/band-median ratio makes every smooth
red-noise window look like a 1000x "tone". The baseline here is a running median of log PSD
over a multiplicative window (a factor of ~2.2 in f), so a pure power law whitens to ~1.0
and only genuinely NARROW features score.

python s2_presence.py <route_key> [vmin]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import ROUTES, load, engaged_mask, FS, HERE

WIN_S, HOP_S = 8.0, 1.0
LO, HI = 1.2, 8.0
FIT_LO, FIT_HI = 0.6, 16.0          # band the baseline is estimated over
LOGW = 0.35                          # +-0.35 decades -> factor 2.24 window
CHS = ["rate", "err", "cmd", "angle", "dtq", "la_act", "out", "yaw"]


def log_baseline(f, lg, lo=FIT_LO, hi=FIT_HI, logw=LOGW):
    """Running median of log-PSD in log-frequency. Returns baseline on the same grid."""
    m = (f >= lo) & (f <= hi)
    lf = np.log10(f[m])
    y = lg[m]
    base = np.empty_like(y)
    for i, x0 in enumerate(lf):
        w = np.abs(lf - x0) <= logw
        base[i] = np.median(y[w])
    out = np.full_like(lg, np.nan)
    out[m] = base
    return out, m


def window_spectrum(x, nper, w, f):
    seg = sig.detrend(x, type="linear")
    F = np.fft.rfft(seg * w)
    P = (np.abs(F) ** 2) / (FS * (w ** 2).sum())
    P[1:-1] *= 2
    return P


def window_peaks(x, tabs, mask_ok, win_s=WIN_S, hop_s=HOP_S):
    nper, hop = int(win_s * FS), int(hop_s * FS)
    w = sig.get_window("hann", nper)
    f = np.fft.rfftfreq(nper, 1 / FS)
    df = f[1] - f[0]
    sel = (f >= LO) & (f <= HI)
    isel = np.flatnonzero(sel)
    out = []
    for i in range(0, len(x) - nper + 1, hop):
        if not mask_ok[i:i + nper].all():
            continue
        P = window_spectrum(x[i:i + nper], nper, w, f)
        lg = np.log(P + 1e-300)
        base, bm = log_baseline(f, lg)
        wh = np.where(bm, lg - base, -np.inf)          # whitened log PSD
        j = isel[np.argmax(wh[isel])]
        y0, y1, y2 = wh[j - 1], wh[j], wh[j + 1]
        den = y0 - 2 * y1 + y2
        d = float(np.clip(0.5 * (y0 - y2) / den, -1, 1)) if den < 0 else 0.0
        fpk = f[j] + d * df
        prom = float(np.exp(wh[j]))
        bandm = (f > fpk * 0.88) & (f < fpk * 1.12)
        amp = float(np.sqrt(2.0 * np.trapezoid(P[bandm], f[bandm])))   # sinusoid amplitude
        out.append((tabs[i + nper // 2], fpk, prom, amp, float(np.trapezoid(P[sel], f[sel]))))
    return np.array(out) if out else np.zeros((0, 5))


if __name__ == "__main__":
    key = sys.argv[1]
    vmin = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    res = {}
    print(f"{key} {D['route']}  mask {m.sum()/FS:.0f} s")
    for ch in CHS:
        if ch not in D:
            continue
        A = window_peaks(D[ch], D["t"], m)
        res[ch] = A
        if not len(A):
            print(f"  {ch}: no full windows"); continue
        pr = A[:, 2]
        print(f"  {ch:7s} n={len(A):4d}  prom p50={np.median(pr):5.1f} p90={np.percentile(pr,90):6.1f} "
              f"max={pr.max():7.1f}   top6:")
        for j in np.argsort(pr)[::-1][:6]:
            print(f"        t={A[j,0]:7.1f}s f={A[j,1]:5.2f}Hz x{pr[j]:7.1f} amp={A[j,3]:.4g}")
    np.savez_compressed(HERE / f"s2_{key}_v{vmin:.0f}.npz",
                        vego=D["vego"], t=D["t"], mask=m, **{f"pk_{k}": v for k, v in res.items()})
    print("wrote", HERE / f"s2_{key}_v{vmin:.0f}.npz")
