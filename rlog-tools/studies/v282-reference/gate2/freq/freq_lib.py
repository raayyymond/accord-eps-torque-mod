"""gate2/freq -- independent wire measurement of the two claimed oscillation objects.

Shares NO code with the repair stream. Everything here is measured from the cached rlog
signals; no model, no fork constant is used to find a frequency.

python freq_lib.py           # self-test / channel inventory
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal as sig

CACHE = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref")
HERE = Path(__file__).resolve().parent
FS = 100.0

ROUTES = {
    "r71": "00000071--f2c9d073a3",   # POSITIVE claim: limit cycle 2.34 Hz, SteerFriction 0.011
    "r72": "00000072--8001fc3048",   # matched control for r73, SteerFriction 0.0
    "r73": "00000073--79fd149dd8",   # POSITIVE claim: chatter 4.0-6.5 Hz, back-filled 0.2120
    "r74": "00000074--2bf17ca67d",   # rev 6.4 / guard live
    "r75": "00000075--6c8687d5bd",   # rev 6.4 / guard live
    "v282a": "00000064--ce6b0b0ebb",
    "v282b": "00000065--b9f78988bd",
    "v282c": "0000006c--2bc842dbac",
    "r70": "00000070--717f5a7866",   # V293 torque mode, context only
    "r76": "00000076--d0b7ea7e4d",   # rev 5, context only
}

# channel -> (npz key, time key, unit)
CH = {
    "rate":   ("sr_deg", "t_cst", "deg/s"),
    "angle":  ("sa_deg", "t_cst", "deg"),
    "dtq":    ("storque", "t_cst", "counts"),     # driver torque / torsion-bar twist
    "vego":   ("vego", "t_cst", "m/s"),
    "err":    ("cs_err", "t_cs", "m/s^2"),        # torque-controller error (lat accel units)
    "pterm":  ("cs_p", "t_cs", "-"),
    "iterm":  ("cs_i", "t_cs", "-"),
    "fterm":  ("cs_f", "t_cs", "-"),
    "out":    ("cs_out", "t_cs", "-"),            # controller output, normalised torque
    "la_act": ("cs_la_act", "t_cs", "m/s^2"),
    "la_des": ("cs_la_des", "t_cs", "m/s^2"),
    "curv_d": ("cs_des_curv", "t_cs", "1/m"),
    "cmd":    ("e4_cmd", "t_e4", "counts"),       # CAN STEERING_CONTROL torque command
    "yaw":    ("pose_wz", "t_pose", "rad/s"),     # ~20 Hz
}


def load(route_key):
    """Return dict of uniformly-resampled 100 Hz channels + masks on one time base."""
    rid = ROUTES[route_key]
    z = np.load(CACHE / f"{rid}.npz")
    t0 = max(z["t_cst"][0], z["t_cs"][0])
    t1 = min(z["t_cst"][-1], z["t_cs"][-1])
    t = np.arange(t0, t1, 1.0 / FS)
    D = {"t": t, "route": rid, "key": route_key}
    for name, (k, tk, _u) in CH.items():
        if k not in z.files or tk not in z.files:
            continue
        tt, vv = z[tk], z[k]
        if len(tt) != len(vv) or len(tt) < 10:
            continue
        D[name] = np.interp(t, tt, vv)
    # masks: nearest-neighbour hold (they are discrete)
    for name, k, tk in (("lat_active", "lat_active", "t_cc"), ("spress", "spress", "t_cst"),
                        ("active", "cs_active", "t_cs"), ("e4_req", "e4_req", "t_e4"),
                        ("sat", "cs_sat", "t_cs")):
        if k in z.files:
            D[name] = np.interp(t, z[tk], z[k]) > 0.5
    z.close()
    return D


def runs(mask, fs=FS, min_s=8.0):
    """Contiguous True runs of at least min_s seconds -> list of (i0, i1) slices."""
    m = np.concatenate(([False], mask.astype(bool), [False]))
    d = np.diff(m.astype(np.int8))
    starts = np.flatnonzero(d == 1)
    stops = np.flatnonzero(d == -1)
    out = [(a, b) for a, b in zip(starts, stops) if (b - a) >= min_s * fs]
    return out


def engaged_mask(D, vmin=0.0, hands_off=True):
    m = D["lat_active"].copy()
    if "e4_req" in D:
        m &= D["e4_req"]
    if hands_off and "spress" in D:
        m &= ~D["spress"]
    if vmin > 0:
        m &= D["vego"] >= vmin
    return m


def welch(x, fs=FS, nper=2048, detrend="linear"):
    nper = min(nper, len(x))
    f, P = sig.welch(x, fs=fs, nperseg=nper, noverlap=nper // 2,
                     window="hann", detrend=detrend, scaling="density")
    return f, P


def band_power(f, P, lo, hi):
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return 0.0
    return float(np.trapezoid(P[m], f[m]))


def concat_welch(D, ch, mask, nper=2048, min_s=8.0):
    """Welch-average over every qualifying run of `mask`; returns (f, P, total_seconds)."""
    if ch not in D:
        return None, None, 0.0
    x = D[ch]
    acc, wsum, secs = None, 0.0, 0.0
    for a, b in runs(mask, min_s=max(min_s, nper / FS)):
        seg = x[a:b]
        if len(seg) < nper:
            continue
        f, P = welch(seg, nper=nper)
        w = len(seg)
        acc = P * w if acc is None else acc + P * w
        wsum += w
        secs += len(seg) / FS
    if acc is None:
        return None, None, 0.0
    return f, acc / wsum, secs


def spectro(x, fs=FS, win_s=8.0, hop_s=1.0, detrend="linear"):
    nper = int(win_s * fs)
    nov = nper - int(hop_s * fs)
    f, tt, S = sig.spectrogram(x, fs=fs, nperseg=nper, noverlap=nov, window="hann",
                               detrend=detrend, scaling="density", mode="psd")
    return f, tt, S


def peak_in_band(f, P, lo, hi, base_lo=None, base_hi=None):
    """Peak frequency (parabolic-interpolated) and prominence over a local log-baseline."""
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan, np.nan
    idx = np.flatnonzero(m)
    j = idx[np.argmax(P[idx])]
    # parabolic interpolation in log power
    if 0 < j < len(f) - 1:
        y0, y1, y2 = np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300)
        den = (y0 - 2 * y1 + y2)
        d = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        d = float(np.clip(d, -1, 1))
    else:
        d = 0.0
    df = f[1] - f[0]
    fpk = f[j] + d * df
    # baseline: median PSD over a wider band excluding +-20% of the peak
    if base_lo is None:
        base_lo, base_hi = max(0.3, lo * 0.5), hi * 1.8
    bm = (f >= base_lo) & (f <= base_hi) & (np.abs(f - fpk) > 0.25 * fpk)
    base = np.median(P[bm]) if bm.any() else np.nan
    return float(fpk), float(P[j]), float(P[j] / base) if base and base > 0 else np.nan


if __name__ == "__main__":
    for k in ("r71", "r72", "r73"):
        D = load(k)
        m = engaged_mask(D)
        print(k, D["route"], "span %.0f s" % (D["t"][-1] - D["t"][0]),
              "engaged hands-off %.0f s" % (m.sum() / FS),
              "runs>=30s", len(runs(m, min_s=30)))
