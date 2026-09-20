"""STEP 1 -- blind spectral survey. No target frequency is assumed anywhere in this file.

For each route and each channel, Welch-average over engaged hands-off runs and dump the
PSD to npz, plus a printed table of the 5 strongest narrow peaks in 1-12 Hz ranked by
prominence over a local baseline.

python s1_survey.py [vmin]
"""
import sys
import numpy as np
from freq_lib import (ROUTES, load, engaged_mask, concat_welch, peak_in_band, runs, FS, HERE)

VMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
CHS = ["rate", "angle", "err", "out", "cmd", "dtq", "la_act", "yaw", "pterm", "fterm"]
ORDER = ["r71", "r72", "r73", "r74", "r75", "v282a", "v282b", "v282c"]


def narrow_peaks(f, P, lo=1.0, hi=12.0, n=5):
    """Rank bins by P / (running median baseline) -- a prominence measure that does not
    care about the absolute level, so route-to-route driving differences drop out."""
    m = (f >= lo * 0.6) & (f <= hi * 1.4)
    fb, Pb = f[m], P[m]
    lg = np.log(Pb + 1e-300)
    # baseline = median filter, width ~1.2 Hz
    w = max(5, int(1.2 / (f[1] - f[0])) | 1)
    pad = w // 2
    lgp = np.pad(lg, pad, mode="edge")
    base = np.array([np.median(lgp[i:i + w]) for i in range(len(lg))])
    prom = lg - base
    keep = (fb >= lo) & (fb <= hi)
    idx = np.flatnonzero(keep)
    order = idx[np.argsort(prom[idx])[::-1]]
    out, used = [], []
    for j in order:
        if any(abs(fb[j] - u) < 0.5 for u in used):
            continue
        used.append(fb[j])
        out.append((float(fb[j]), float(np.exp(prom[j])), float(Pb[j])))
        if len(out) >= n:
            break
    return out


if __name__ == "__main__":
    res = {}
    for k in ORDER:
        D = load(k)
        m = engaged_mask(D, vmin=VMIN)
        print(f"\n=== {k}  {D['route']}   engaged hands-off{'' if VMIN==0 else f' v>={VMIN}'}"
              f" = {m.sum()/FS:.0f} s in {len(runs(m, min_s=8))} runs")
        for ch in CHS:
            f, P, secs = concat_welch(D, ch, m, nper=2048, min_s=8.0)
            if f is None:
                continue
            res[f"{k}|{ch}|f"] = f
            res[f"{k}|{ch}|P"] = P
            pk = narrow_peaks(f, P)
            s = "  ".join(f"{a:5.2f}Hz x{b:4.1f}" for a, b, _ in pk)
            print(f"   {ch:7s} {secs:5.0f}s   {s}")
        del D
    np.savez_compressed(HERE / f"s1_psd_v{VMIN:.0f}.npz", **res)
    print("\nwrote", HERE / f"s1_psd_v{VMIN:.0f}.npz")
