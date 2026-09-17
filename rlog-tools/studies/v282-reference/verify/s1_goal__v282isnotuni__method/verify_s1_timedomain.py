"""Time-domain cross-check of s1 magnitude via bandpass + best-lag regression gain (independent of the
spectral |H| estimator: no Welch/CSD, just filtfilt bandpass, cross-correlation lag search, OLS gain).
"""
import sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

ROUTES = {
    "V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
    "T64": ["0000006c--68c6e94b17", "0000006d--05e83bb04f"],
}
BANDS = {"low(0.05-0.3)": (0.05, 0.30), "high(0.3-0.6)": (0.30, 0.60)}

def bp(x, f1, f2):
    sos = signal.butter(4, [f1, f2], btype="band", fs=V.FS, output="sos")
    return signal.sosfiltfilt(sos, x)

def best_lag_gain(x, y, maxlag_s=0.6):
    L = int(maxlag_s * V.FS)
    n = len(x)
    best, lag = -np.inf, 0
    for k in range(-L, L + 1):
        if k >= 0:
            xa, ya = x[: n - k], y[k:]
        else:
            xa, ya = x[-k:], y[: n + k]
        if len(xa) < 200:
            continue
        c = float(np.dot(xa, ya))
        if c > best:
            best, lag = c, k
    if lag >= 0:
        xa, ya = x[: n - lag], y[lag:]
    else:
        xa, ya = x[-lag:], y[: n + lag]
    gain = float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9))
    return gain, lag / V.FS

for grp, routes in ROUTES.items():
    for bname, (f1, f2) in BANDS.items():
        gains = []
        for route in routes:
            S = V.load(route)
            m = V.usable(S, 15.0)
            rs = V.runs(m, S["t"], min_s=20.0)
            model = np.nan_to_num(S["model"]); pose = np.nan_to_num(S["la_pose"])
            gs = []
            for a, b in rs:
                x = bp(model[a:b], f1, f2); y = bp(pose[a:b], f1, f2)
                g, lag = best_lag_gain(x, y)
                gs.append((g, lag, b - a))
            if gs:
                wsum = sum(w for _, _, w in gs)
                gwm = sum(g * w for g, _, w in gs) / wsum
                lwm = sum(l * w for _, l, w in gs) / wsum
                gains.append(gwm)
                print(f"  {grp:6s} {route:22s} {bname:15s} gain={gwm:.3f} lag={lwm*1000:.0f}ms nruns={len(gs)}")
            del S
        if gains:
            print(f"{grp:6s} {bname:15s} MEAN across routes = {np.mean(gains):.3f}\n")
