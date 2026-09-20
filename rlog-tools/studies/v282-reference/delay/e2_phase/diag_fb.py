"""CAUSAL feedback share of the command, resolved in frequency.

Fit, on RAW (unfiltered) signals and strictly past lags, u_t = sum_{L=1..40} [a_L * angle_{t-L} + r_L * rate_{t-L}] + c,
per speed bin (this is common.innovation with INNOV_ULAGS=0). Then take Welch spectra of u and of the residual e
inside each speed bin's valid stretch and report, per frequency, 1 - S_ee/S_uu = the fraction of the command's power
at that frequency that is explained by PAST MEASUREMENT alone. No acausal filtering anywhere.

A large value in the 2-8 Hz fit band means the command there is (past) measurement feedback, so S_uy/S_uu cannot
identify the plant: it is driven toward -1/C.

usage: python diag_fb.py route [route ...]
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
import common as C

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
BAND = (2.0, 8.0)


def welch_on_runs(x, m, nps=256):
    """Welch PSD using only contiguous valid runs of at least nps samples."""
    acc = None; n = 0
    i, N = 0, len(m)
    while i < N:
        if not m[i]:
            i += 1; continue
        j = i
        while j < N and m[j]:
            j += 1
        if j - i >= nps:
            f, P = signal.welch(x[i:j], C.FS, nperseg=nps, noverlap=nps // 2, detrend="linear")
            acc = P * (j - i) if acc is None else acc + P * (j - i)
            n += j - i
        i = j
    return (f, acc / n) if n else (None, None)


if __name__ == "__main__":
    res = {}
    for route in sys.argv[1:]:
        R = C.load_route(route); mask = C.handsoff_mask(R)
        e = C.innovation(R, mask, use_u=False)          # residual of u on past angle+rate only, per speed bin
        for lo, hi in C.SPEED_BINS:
            m = mask & (R["v"] >= lo) & (R["v"] < hi) & (e != 0.0)
            if m.sum() < 1000:
                continue
            f, Suu = welch_on_runs(R["u"], m)
            _, See = welch_on_runs(e, m)
            if Suu is None:
                continue
            share = 1.0 - See / Suu
            inb = (f >= BAND[0]) & (f <= BAND[1])
            row = dict(n_s=float(m.sum() / C.FS),
                       share_band=float(1.0 - See[inb].sum() / Suu[inb].sum()),
                       share_by_f=[(round(float(ff), 2), round(float(s), 3)) for ff, s in zip(f[inb], share[inb])])
            res[f"{route}|v{lo:.0f}-{hi:.0f}"] = row
            print(f"{route} v{lo:.0f}-{hi:.0f} {row['n_s']:6.0f}s  feedback share of u over 2-8 Hz = {row['share_band']:.3f}",
                  flush=True)
            print("    by f:", row["share_by_f"], flush=True)
        del R, e
    (OUT / "diag_fb.json").write_text(json.dumps(res, indent=1, default=float))
