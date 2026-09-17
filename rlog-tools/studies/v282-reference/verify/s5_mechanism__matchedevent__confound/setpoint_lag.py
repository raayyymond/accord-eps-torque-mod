"""Independently check: how much of the extra desired->wheel lag is the fork's OWN setpoint shaping
(model -> setpoint, i.e. cs_des_curv*v^2 -> cs_la_des) vs the plant (setpoint -> achieved)?
Computed directly from v282cmp.load(), not reused from any prior script."""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
import numpy as np

ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac',
          '0000006c--68c6e94b17', '0000006d--05e83bb04f',
          '0000006e--6ca3e014fd', '00000075--6c8687d5bd', '00000076--d0b7ea7e4d']

def lag_gain(x, y, maxlag=60):
    n = len(x); best, lag = -np.inf, 0
    for k in range(0, maxlag + 1):
        xa, ya = x[:n-k] - x[:n-k].mean(), y[k:] - y[k:].mean()
        c = float(np.dot(xa, ya)) / max(np.linalg.norm(xa)*np.linalg.norm(ya), 1e-9)
        if c > best:
            best, lag = c, k
    return lag / 100.0, best

for rk in ROUTES:
    S = V.load(rk)
    u = V.usable(S, 8.0)
    model = V.lowpass(np.nan_to_num(S['model']), 5.0)
    setp = V.lowpass(np.nan_to_num(S['setpoint']), 5.0)
    lags = []
    for a, b in V.runs(u, S['t'], min_s=3.0):
        if b - a < 100: continue
        l, c = lag_gain(model[a:b], setp[a:b])
        if c > 0.6:
            lags.append(l)
    if lags:
        print(f"{rk:24s} {S['meta'].get('group','?'):8s} n_runs={len(lags):3d} setpoint_lag_med={np.median(lags):.3f}")
    del S
