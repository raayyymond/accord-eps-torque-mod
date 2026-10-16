# -*- coding: utf-8 -*-
"""high_angle_probe.py -- zoom on named high-angle windows: is the 0x18F bar a HAND or the wheel's own REACTION
(bar ~ -J theta_ddot), what frequency, phase of tap vs wheel, freeze (|bar| > 1229) toggling, fork clip/rate status.
    python high_angle_probe.py <route> t0:t1 [t0:t1 ...]     (t relative to the route's first wire frame, as high_angle_hunt)
ANALYSIS ONLY (2026-10-15)."""
import sys, io, contextlib, json
from pathlib import Path
import numpy as np
from scipy import signal
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()] + [Path(__file__).resolve().parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import high_angle_hunt as H
FS = 100.0
route = sys.argv[1]
R = H.load(route)
W = R["W"]
t = W["t"] - W["t"][0]
th, sp, T, bar = W["theta"], W["theta_sp"], W["T100"], W["bar"]
if not R["tap"]:                                  # release firmware: 0x1AB is Honda's motor torque, not the lane tap
    T = np.full_like(th, np.nan)
    print("LANE TAP: NOT AVAILABLE on release firmware (no tap) -- the T mean / sd / phase columns below are nan")
lp = signal.butter(2, 8.0, fs=FS, output="sos")
ths = signal.sosfiltfilt(lp, th)
acc = np.gradient(np.gradient(ths)) * FS * FS            # deg/s^2
cc = R.get("cc", np.full_like(th, np.nan))
for w in sys.argv[2:]:
    a, b = (float(x) for x in w.split(":"))
    s = (t >= a) & (t < b)
    y = bar[s] - np.mean(bar[s])
    x = acc[s] - np.mean(acc[s])
    k = np.dot(x, y) / np.dot(x, x)
    r2 = 1 - np.sum((y - k * x) ** 2) / np.sum(y ** 2)
    bp = signal.butter(2, [1.0, 5.0], btype="band", fs=FS, output="sos")
    S = np.flatnonzero(s); pad = slice(max(S[0] - 300, 0), S[-1] + 300)
    off = S[0] - pad.start
    def B(x):
        return signal.sosfiltfilt(bp, np.nan_to_num(x[pad]))[off:off + len(S)]
    thd = B(th); spd = B(sp); Td = B(T); ccd = B(cc)
    f, p = signal.periodogram(thd * np.hanning(len(thd)), fs=FS, nfft=2048)
    m = (f > 0.8) & (f < 6); fpk = f[m][np.argmax(p[m])]
    # phase of T vs theta at fpk (cross-spectrum)
    fx, pxy = signal.csd(thd, Td, fs=FS, nperseg=min(len(thd), 128), nfft=2048)
    ph = np.degrees(np.angle(pxy[np.argmin(np.abs(fx - fpk))]))
    fz = np.abs(bar[s]) > 1229
    print("%s %6.1f-%6.1f s  v %4.1f  theta %6.1f  sp %6.1f  cc %6.1f | wheel pp %5.2f rms %4.2f  sp pp %5.2f rms %4.2f  cc rms %4.2f  "
          "f_wheel %.2f Hz | bar mean %6.0f sd %5.0f  bar~k*acc R2 %.2f k %.3f word/(deg/s2) | T mean %5.1f sd %5.1f LSB, "
          "phase T-vs-theta %+4.0f deg | freeze>1229 duty %.2f toggles/s %.1f | sp-th mean %+5.1f" % (
          route.split("_")[1][:12], a, b, np.median(W["vego"][s]), np.mean(th[s]), np.mean(sp[s]), np.nanmean(cc[s]),
          np.ptp(thd), np.std(thd), np.ptp(spd), np.std(spd), np.std(ccd), fpk,
          np.mean(bar[s]), np.std(bar[s]), r2, k, np.mean(T[s]), np.std(T[s]), ph, np.mean(fz),
          np.sum(np.diff(fz.astype(int)) == 1) / (b - a), np.mean(sp[s] - th[s])))
