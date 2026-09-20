"""A9 - VERIFY THE CRUX MYSELF: did r73, which flew the relay at 19x r71's, show r71's object?

r71's label is a 2.34 Hz, +/-6 deg limit cycle on hard curves above 20 m/s.  Measured here on each
route's own log: steering-rate spectrum, engaged hands-off >= 15 m/s, in the 2.0-2.8 Hz band that
holds r71's object and in the 3.5-4.5 Hz band the fork's own commit note attributes to r73.
"""
import os
import numpy as np
from scipy import signal

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
ROUTES = [("V282", "0000006c--2bc842dbac"), ("r70", "00000070--717f5a7866"),
          ("r71 *LC*", "00000071--f2c9d073a3"), ("r72", "00000072--8001fc3048"),
          ("r73 relay19x", "00000073--79fd149dd8"), ("rev6.4", "0000006d--05e83bb04f"),
          ("rev5", "00000076--d0b7ea7e4d")]

print(f"{'route':14} {'F relay':>8} {'s':>6} {'rate RMS 2.0-2.8':>17} {'3.5-4.5':>9} {'peak f 1.5-5':>13} "
      f"{'peak/median':>12} {'p99 |angle| swing 2-3Hz deg':>28}")
print("-" * 118)
F = {"0000006c--2bc842dbac": 0.01, "00000070--717f5a7866": 0.0, "00000071--f2c9d073a3": 0.011,
     "00000072--8001fc3048": 0.0, "00000073--79fd149dd8": 0.212, "0000006d--05e83bb04f": "off",
     "00000076--d0b7ea7e4d": 0.0}
for name, key in ROUTES:
    z = np.load(os.path.join(CACHE, key + ".npz"))
    t = z["t_cs"]
    ok = z["cs_active"] > 0.5
    v = np.interp(t, z["t_cst"], z["vego"])
    sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    sr = np.interp(t, z["t_cst"], z["sr_deg"])
    sa = np.interp(t, z["t_cst"], z["sa_deg"])
    del z
    m = ok & ~sp & (v >= 15.0)
    d = np.diff(m.astype(int))
    st = np.flatnonzero(d == 1) + 1
    en = np.flatnonzero(d == -1) + 1
    if m[0]:
        st = np.r_[0, st]
    if m[-1]:
        en = np.r_[en, len(m)]
    P = 0.0
    W = 0.0
    swings = []
    for s, e in zip(st, en):
        if e - s < 1024:
            continue
        x = sr[s:e] - sr[s:e].mean()
        f, p = signal.welch(x, fs=100.0, nperseg=1024)
        P = P + p * (e - s)
        W += (e - s)
        b, a = signal.butter(2, [2.0 / 50, 3.0 / 50], "band")
        yy = signal.filtfilt(b, a, sa[s:e] - sa[s:e].mean())
        swings.append(np.abs(yy))
    if W == 0:
        continue
    P = P / W
    df = f[1] - f[0]
    b1 = (f >= 2.0) & (f <= 2.8)
    b2 = (f >= 3.5) & (f <= 4.5)
    bb = (f >= 1.5) & (f <= 5.0)
    sw = np.concatenate(swings)
    print(f"{name:14} {str(F[key]):>8} {W/100:6.0f} {np.sqrt(P[b1].sum()*df):17.4f} "
          f"{np.sqrt(P[b2].sum()*df):9.4f} {f[bb][np.argmax(P[bb])]:13.2f} "
          f"{P[bb].max()/np.median(P[bb]):12.2f} {np.percentile(sw,99):28.3f}")
