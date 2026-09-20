"""A3 - how much error can the 0.20 Hz plant anchor carry to 2.3-2.6 Hz?

The retrodiction anchors gain and phase on the MEASURED complex plant at 0.20 Hz and then
extrapolates a decade up with J*th'' + b*th' + k(v)*th.  Between the anchor and the verdict
the model passes through the resonance, where |P| is set by b -- which the anchor cannot see
(at 0.20 Hz the plant is pure stiffness, |P| -> 1/k).

Measured here, per route: the empirical transfer u -> measured wheel angle with coherence,
at the anchor and in the 1.5-4 Hz decision band, and the RATIO |T(f)|/|T(0.20)|.  That ratio
is exactly what the model has to predict, so the spread between the measured ratio and the
model's ratio across the admissible b is the extrapolation error.
"""
import json
import os
import numpy as np
from scipy import signal

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
OUT = os.path.dirname(__file__)

ROUTES = ["0000006c--2bc842dbac", "00000070--717f5a7866", "00000071--f2c9d073a3",
          "00000072--8001fc3048", "00000073--79fd149dd8", "0000006d--05e83bb04f",
          "00000076--d0b7ea7e4d"]

FS = 100.0


def transfer(u, y, fs=FS, nper=2048):
    f, Pyu = signal.csd(u, y, fs=fs, nperseg=nper, noverlap=nper // 2)
    _, Puu = signal.welch(u, fs=fs, nperseg=nper, noverlap=nper // 2)
    _, Pyy = signal.welch(y, fs=fs, nperseg=nper, noverlap=nper // 2)
    T = Pyu / Puu
    coh = np.abs(Pyu) ** 2 / (Puu * Pyy)
    return f, T, coh


res = {}
for key in ROUTES:
    z = np.load(os.path.join(CACHE, key + ".npz"))
    t = z["t_cs"]
    act = z["cs_active"] > 0.5
    out = z["cs_out"]
    tc = z["t_cst"]
    v = np.interp(t, tc, z["vego"])
    sp = np.interp(t, tc, z["spress"]) > 0.5
    sa = np.interp(t, tc, z["sa_deg"])
    del z
    ok = act & ~sp & (v >= 15.0)
    # longest contiguous engaged hands-off fast run
    d = np.diff(ok.astype(int))
    starts = np.flatnonzero(d == 1) + 1
    ends = np.flatnonzero(d == -1) + 1
    if ok[0]:
        starts = np.r_[0, starts]
    if ok[-1]:
        ends = np.r_[ends, len(ok)]
    segs = [(s, e) for s, e in zip(starts, ends) if e - s > 4096]
    if not segs:
        print(key, "no long run")
        continue
    Ts, Cs, W = [], [], []
    for s, e in segs:
        u = out[s:e] - np.mean(out[s:e])
        y = sa[s:e] - np.mean(sa[s:e])
        f, T, coh = transfer(u, y)
        Ts.append(T * (e - s))
        Cs.append(coh * (e - s))
        W.append(e - s)
    W = float(sum(W))
    T = sum(Ts) / W
    coh = sum(Cs) / W

    def at(fh):
        i = int(np.argmin(np.abs(f - fh)))
        return T[i], coh[i], f[i]

    T02, c02, f02 = at(0.20)
    band = (f >= 1.5) & (f <= 4.0)
    res[key] = dict(f=f[band].tolist(), absT=np.abs(T[band]).tolist(),
                    coh=coh[band].tolist(), T02=abs(T02), coh02=float(c02),
                    ratio=(np.abs(T[band]) / abs(T02)).tolist(),
                    nsec=W / FS)
    print(f"\n{key}   {W/FS:6.0f} s engaged hands-off >=15 m/s   |T(0.20)| = {abs(T02):.4g} deg/torque  coh {c02:.3f}")
    for fh in (1.5, 2.0, 2.34, 2.5, 3.0, 3.5, 4.0):
        Tf, cf, ff_ = at(fh)
        print(f"   f={ff_:5.2f} Hz  |T| {abs(Tf):9.4g}  ratio-to-anchor {abs(Tf)/abs(T02):8.4f}  coh {cf:.3f}")

json.dump(res, open(os.path.join(OUT, "a3_plant_transfer.json"), "w"))
