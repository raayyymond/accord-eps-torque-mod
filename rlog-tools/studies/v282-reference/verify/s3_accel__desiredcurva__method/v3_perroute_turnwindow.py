"""Adversarial check on the 'pooled turn windows at 1.5-3.5 Hz' number in s3_pass3.py: is the pooled
TQ figure (des 48.0 / meas 16.0 deg/s, coh 0.07) driven by all torque routes, or dominated by one or two?
Recomputes the same per-turn-event band-rms, but reports it PER ROUTE (not pooled across routes) so route-
to-route consistency (and CI over routes) can be checked directly, matching the reviewer instruction to
check whether CIs are over events AND routes.
"""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import s3turns as T
import v282cmp as V

rows = {}
for rk, meta in V.ROUTES.items():
    R = T.prep(rk)
    evs, _ = T.find_turns(R)
    adr = V.deriv(R["ad"])
    n = len(R["t"])
    xx = yy = xy = 0
    sec = 0.0
    fgrid = None
    for e in evs:
        mask = np.zeros(n, bool); mask[e["w0"]:e["w1"]] = True; mask &= ~R["pressed"]
        for a, b in V.runs(mask, R["t"], min_s=2.56):
            x = adr[a:b] - adr[a:b].mean(); y = R["sr"][a:b] - R["sr"][a:b].mean()
            f, pxx = signal.welch(x, V.FS, nperseg=256, noverlap=128)
            _, pyy = signal.welch(y, V.FS, nperseg=256, noverlap=128)
            _, pxy = signal.csd(x, y, V.FS, nperseg=256, noverlap=128)
            w = len(x)
            xx = pxx * w if isinstance(xx, int) else xx + pxx * w
            yy = pyy * w if isinstance(yy, int) else yy + pyy * w
            xy = pxy * w if isinstance(xy, int) else xy + pxy * w
            sec += w / V.FS
            fgrid = f
    if sec == 0:
        print(f"{rk:24s} {meta['group']:7s} n_events={len(evs):3d}  no >=2.56s hands-off windows in turns")
        continue
    Xn, Yn, XYn = xx / sec / V.FS, yy / sec / V.FS, xy / sec / V.FS
    df = fgrid[1] - fgrid[0]
    m = (fgrid >= 1.5) & (fgrid < 3.5)
    des = float(np.sqrt(np.sum(Xn[m]) * df))
    meas = float(np.sqrt(np.sum(Yn[m]) * df))
    coh = float(np.sum(np.abs(XYn[m]) ** 2) / max(np.sum(Xn[m] * Yn[m]), 1e-12))
    rows[rk] = dict(group=meta["group"], n_events=len(evs), sec=sec, des=des, meas=meas, coh=coh)
    print(f"{rk:24s} {meta['group']:7s} n_events={len(evs):3d} sec={sec:6.1f}  des={des:6.2f}  meas={meas:6.2f}  coh={coh:.3f}")
    del R

print("\n=== group medians/ranges of the per-route des-rms (1.5-3.5 Hz, turn windows) ===")
for g in ["V282", "V282old", "T64", "T64B", "T5", "T4"]:
    vals = [o["des"] for o in rows.values() if o["group"] == g]
    if vals:
        print(f"  {g:8s} n_routes={len(vals)}  des_rms per route = {[round(x,1) for x in vals]}")
