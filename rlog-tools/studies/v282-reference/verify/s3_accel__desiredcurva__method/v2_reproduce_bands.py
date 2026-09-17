"""Independent re-derivation of s3_refloop.py's 'des' (desired angle-rate rms in band) numbers, from
v282cmp caches only (does not import s3turns, to be a genuinely separate re-derivation of the same
physical quantity). Also: (a) checks whether the magnitude claim is sensitive to the estimator (plain
band-limited rms of the desired-rate SIGNAL itself needs no coherence/H at all -- it's just Parseval on
one signal, so the phasor-averaging warning in v282cmp.band_H doesn't even apply here), (b) reports a
route-level bootstrap CI on the group ratio, since n=3 (V282) vs n=5 (torque) routes is small.
"""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V
from scipy import signal

# --- same physical model as s3turns.py, re-typed independently to catch a transcription bug ---
M = 3279 * 0.45359237 + 136.0
WB = 2.83
AF = 0.39 * WB
AR = WB - AF
TSF = 0.8467
_M0, _WB0 = 1326. + 136., 2.70
_AF0 = _WB0 * 0.4
_AR0 = _WB0 - _AF0
CF = 192150 * TSF * M / _M0 * (AR / WB) / (_AR0 / _WB0)
CR = 202500 * TSF * M / _M0 * (AF / WB) / (_AF0 / _WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR_FIX = 16.33


def curv_to_angle(k, v):
    return -np.degrees(k * SR_FIX * WB * (1.0 - SF * v ** 2))


BANDS = [(1.0, 2.0), (2.0, 3.0)]
rows = {}
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    v = np.nan_to_num(S["v"])
    vv = np.maximum(v, 0.5)
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    sr = np.nan_to_num(S["sr"])
    u = V.usable(S, 2.5, 8.0)
    t = S["t"]
    segs = V.runs(u, t, min_s=5.12)
    Xsum = Ysum = None
    fr = None
    nsamp = 0
    for a, b in segs:
        x = V.deriv(ad[a:b])
        y = sr[a:b]
        f, p = signal.welch(x - x.mean(), V.FS, nperseg=512)
        _, q = signal.welch(y - y.mean(), V.FS, nperseg=512)
        w = b - a
        Xsum = p * w if Xsum is None else Xsum + p * w
        Ysum = q * w if Ysum is None else Ysum + q * w
        fr = f
        nsamp += w
    if nsamp == 0:
        print(f"{rk:24s} {meta['group']:7s}  no usable runs >=5.12s in 2.5-8 m/s")
        continue
    X = Xsum / nsamp
    Y = Ysum / nsamp
    df = fr[1] - fr[0]
    out = dict(group=meta["group"], sec=nsamp / V.FS)
    for lo, hi in BANDS:
        m = (fr >= lo) & (fr < hi)
        des_rms = float(np.sqrt(np.sum(X[m]) * df))
        meas_rms = float(np.sqrt(np.sum(Y[m]) * df))
        out[f"{lo}-{hi}_des"] = des_rms
        out[f"{lo}-{hi}_meas"] = meas_rms
    rows[rk] = out
    print(f"{rk:24s} {meta['group']:7s} sec={out['sec']:7.1f}  " +
          "  ".join(f"{lo}-{hi}: des={out[f'{lo}-{hi}_des']:6.2f} meas={out[f'{lo}-{hi}_meas']:6.2f}"
                     for lo, hi in BANDS))
    del S

print()
print("=== group summaries (unweighted mean over routes, and duration-weighted mean) ===")
for lo, hi in BANDS:
    key = f"{lo}-{hi}_des"
    groups = {}
    for rk, o in rows.items():
        groups.setdefault(o["group"], []).append((o[key], o["sec"]))
    print(f"--- band {lo}-{hi} Hz, desired angle-rate rms (deg/s) ---")
    for g, vals in groups.items():
        arr = np.array([v_ for v_, s in vals])
        secs = np.array([s for v_, s in vals])
        uw = arr.mean()
        wmean = np.average(arr, weights=secs)
        print(f"  {g:8s} n={len(arr)}  routes={[f'{a:.1f}' for a in arr]}  unweighted_mean={uw:.2f}  duration_weighted_mean={wmean:.2f}")

    # bootstrap: resample routes within V282 (primary) and each torque group, ratio of means
    rng = np.random.default_rng(0)
    v282_vals = np.array([v_ for v_, s in groups.get("V282", [])])
    torque_vals = np.array([v_ for g_ in ("T64", "T64B", "T5", "T4") for v_, s in groups.get(g_, [])])
    if len(v282_vals) and len(torque_vals):
        boot = []
        for _ in range(20000):
            a = rng.choice(v282_vals, size=len(v282_vals), replace=True)
            b = rng.choice(torque_vals, size=len(torque_vals), replace=True)
            boot.append(b.mean() / max(a.mean(), 1e-9))
        boot = np.sort(boot)
        lo_ci, hi_ci = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]
        print(f"  route-level bootstrap (resample-with-replacement within group, n=20000): "
              f"ratio torque_mean/V282_mean point={torque_vals.mean()/v282_vals.mean():.2f}  95% CI [{lo_ci:.2f}, {hi_ci:.2f}]")
        # fraction of bootstrap draws where ratio < 1 (i.e. sign check: does it ever flip?)
        print(f"  P(ratio <= 1) in bootstrap = {np.mean(boot <= 1.0):.3f}   P(ratio <= 2) = {np.mean(boot<=2.0):.3f}")
    print()
