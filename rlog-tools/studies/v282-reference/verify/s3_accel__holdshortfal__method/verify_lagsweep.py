"""v2 methodology, lag sweep 0..0.5s, to test the 'robust across lag choice' sub-claim independently."""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

M = 3279 * 0.45359237 + 136.0; WB = 2.83; AF = 0.39 * WB; AR = WB - AF; TSF = 0.8467
M0, WB0 = 1326. + 136., 2.70; AF0 = WB0 * 0.4; AR0 = WB0 - AF0
CF = 192150 * TSF * M / M0 * (AR / WB) / (AR0 / WB0)
CR = 202500 * TSF * M / M0 * (AF / WB) / (AF0 / WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR = 16.33
def curv_to_angle(k, v): return -np.degrees(k * SR * WB * (1.0 - SF * v ** 2))
def lag_shift(x, t, lag_s): return np.interp(t + lag_s, t, x, left=np.nan, right=np.nan)

LAGS = [0.0, 0.1, 0.25, 0.4, 0.5]
rows = []
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    t = S["t"]; v = np.nan_to_num(S["v"]); vv = np.maximum(v, 0.5)
    active = S["active"]; pressed = S["pressed"]
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    aa = np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"])
    adl = V.lowpass(ad, 1.0)
    a = np.abs(adl)
    pk, _ = signal.find_peaks(a, height=25.0, prominence=8.0, distance=int(2.5 * V.FS))
    n = len(t)
    for kk in pk:
        P = a[kk]; s = float(np.sign(adl[kk]))
        if not (2.5 <= v[kk] < 15.0):
            continue
        thr = 0.85 * P
        i = kk
        while i > 0 and s * adl[i] >= thr: i -= 1
        j = kk
        while j < n - 1 and s * adl[j] >= thr: j += 1
        i += 1
        if j - i < 30 or i < 0 or j >= n: continue
        if not active[i:j].all(): continue
        if np.any(np.diff(t[i:j]) > 4.0 / V.FS): continue
        src = np.where(pressed, np.nan, aa)
        row = dict(rk=rk, group=meta["group"], P=float(P))
        for L in LAGS:
            ach = s * lag_shift(src, t, L)
            err = (ach - s * ad)[i:j] / P
            row[f"L{L}"] = float(np.nanmean(err)) if np.isfinite(err).sum() >= 5 else np.nan
        rows.append(row)
    del S

GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
for r in rows: r["G"] = GM[r["group"]]
print("group means by lag (simple mean, unstratified, all P bins pooled)")
for L in LAGS:
    line = f"L={L:.2f}"
    for G in ("V282", "TQ"):
        x = np.array([r[f"L{L}"] for r in rows if r["G"] == G], float)
        x = x[np.isfinite(x)]
        line += f"  {G} {np.mean(x):+.4f}(n{len(x)})"
    line += f"  diff {np.mean([r[f'L{L}'] for r in rows if r['G']=='TQ' and np.isfinite(r[f'L{L}'])]) - np.mean([r[f'L{L}'] for r in rows if r['G']=='V282' and np.isfinite(r[f'L{L}'])]):+.4f}"
    print(line)
