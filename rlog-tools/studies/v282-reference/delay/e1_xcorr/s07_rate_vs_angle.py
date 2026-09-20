"""Is the 0x14A rate signal the derivative of the 0x14A angle, or a filtered/delayed version of it?
xcorr of band-passed (1-6 Hz) rate against band-passed d/dt(angle), same blocks; sinc peak; per route.
A positive lag = the rate signal LAGS the angle derivative (an internal EPS rate filter)."""
import numpy as np
import xc_lib as X
for route in X.TORQUE_ROUTES + X.V282_ROUTES:
    R = X.load_route(route); G = X.grid_route(R); del R
    B = np.load(X.HERE / "_cache" / f"real_blocks_{route}.npz")
    xc = X.XC()
    for ts, bi in zip(B["tstart"], B["bin"]):
        k = int(round((ts - G["t"][0]) / X.DT))
        xc.add(np.gradient(G["sa"][k:k + 1200]) * X.FS, G["sr"][k:k + 1200], int(bi), route)
    cur = xc.curve()
    p, s, v = X.peak(cur, +1, -50, 100)
    # amplitude ratio (rate / dangle) in band
    print(f"{route}  rate lags d/dt(angle) by sinc {s:5.1f} ms (parabolic {p:5.1f}), corr {v:.3f}")
    del G
