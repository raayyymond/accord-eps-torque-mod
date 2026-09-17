"""Corrected version of s3_pass3.py's pooled 1.5-3.5 Hz turn-window statistic: same method, but any
sub-window whose instantaneous speed dips below 2.0 m/s anywhere inside it is dropped first (guards
against the curvature->angle singularity near v->0 found in route 0000006c--68c6e94b17's 4th event).
"""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import s3turns as T
import v282cmp as V

GM = {"V282": "V282", "V282old": "V282old"}
acc = {}
dropped = []
for rk, meta in V.ROUTES.items():
    R = T.prep(rk)
    G = GM.get(R["group"], "TQ")
    evs, _ = T.find_turns(R)
    adr = V.deriv(R["ad"])
    n = len(R["t"])
    for e in evs:
        mask = np.zeros(n, bool); mask[e["w0"]:e["w1"]] = True; mask &= ~R["pressed"]
        for a, b in V.runs(mask, R["t"], min_s=2.56):
            vmin = R["v"][a:b].min()
            if vmin < 2.0:
                dropped.append((rk, G, e["t"], vmin))
                continue
            x = adr[a:b] - adr[a:b].mean(); y = R["sr"][a:b] - R["sr"][a:b].mean()
            f, pxx = signal.welch(x, V.FS, nperseg=256, noverlap=128)
            _, pyy = signal.welch(y, V.FS, nperseg=256, noverlap=128)
            _, pxy = signal.csd(x, y, V.FS, nperseg=256, noverlap=128)
            A = acc.setdefault(G, dict(f=f, xx=0 * pxx, yy=0 * pxx, xy=0 * pxy, sec=0.0))
            w = len(x); A["xx"] += pxx * w; A["yy"] += pyy * w; A["xy"] += pxy * w; A["sec"] += w / V.FS
    del R

print("dropped windows (vmin<2.0 m/s inside a turn-event sub-window):")
for d in dropped:
    print("  ", d)

print("\ncorrected pooled 1.5-3.5 Hz (speed-floor guarded):")
for G, A in acc.items():
    f = A["f"]; xx, yy, xy = A["xx"] / A["sec"] / V.FS, A["yy"] / A["sec"] / V.FS, A["xy"] / A["sec"] / V.FS
    df = f[1] - f[0]
    m = (f >= 1.5) & (f < 3.5)
    des = float(np.sqrt(np.sum(xx[m]) * df)); meas = float(np.sqrt(np.sum(yy[m]) * df))
    coh = float(np.sum(np.abs(xy[m]) ** 2) / max(np.sum(xx[m] * yy[m]), 1e-12))
    print(f"  {G:8s} sec={A['sec']:6.1f}  des={des:6.2f} meas={meas:6.2f} coh={coh:.3f}")
