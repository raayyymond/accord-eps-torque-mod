import sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

M = 3279 * 0.45359237 + 136.0; WB = 2.83; AF = 0.39 * WB; AR = WB - AF; TSF = 0.8467
_M0, _WB0 = 1326. + 136., 2.70; _AF0 = _WB0 * 0.4; _AR0 = _WB0 - _AF0
CF = 192150 * TSF * M / _M0 * (AR / WB) / (_AR0 / _WB0)
CR = 202500 * TSF * M / _M0 * (AF / WB) / (_AF0 / _WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR_FIX = 16.33
def curv_to_angle(k, v):
    return -np.degrees(k * SR_FIX * WB * (1.0 - SF * v ** 2))

GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
peaks = {"V282": [], "V282old": [], "TQ": []}

for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    v = np.nan_to_num(S["v"]); vv = np.maximum(v, 0.5)
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    adl = V.lowpass(ad, 1.0)
    mask = S["active"] & ~S["pressed"] & (v >= 2.5) & (v < 15) & (np.abs(adl) >= 25.0)
    sr = np.nan_to_num(S["sr"])
    G = GM[meta["group"]]
    for a, b in V.runs(mask, S["t"], min_s=5.12):
        x = sr[a:b] - np.mean(sr[a:b])
        nps = min(512, len(x))
        f, p = signal.welch(x, V.FS, nperseg=nps, noverlap=nps//2)
        m = (f >= 1.5) & (f <= 5.0)
        if m.sum() < 2: continue
        fpk = f[m][np.argmax(p[m])]
        peaks[G].append(fpk)
    del S

for g in ("V282", "V282old", "TQ"):
    x = np.array(peaks[g])
    if len(x)==0:
        print(g, "no windows"); continue
    print(f"{g:8s} n={len(x):3d} median peak freq (1.5-5Hz, on STRICT >=2.0s hold-dominated windows) = {np.median(x):.2f} Hz  IQR[{np.percentile(x,25):.2f},{np.percentile(x,75):.2f}]")
