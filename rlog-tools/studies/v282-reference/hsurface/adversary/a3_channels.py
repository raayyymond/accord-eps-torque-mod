"""ADVERSARY A3 - is the OUTPUT channel the same measurement in both builds, and does the jerk-event contrast
survive a change of channel?

Two things to break:
 1. `torqueState.actualLateralAccel` looked identical to `controlsState.curvature * v^2` in A2. If so it is an
    ANGLE-derived channel, scaled by the fork's steer-ratio map - and that map CHANGED between the V282 routes
    (16.33 at 0f98d8c7, 16.84 at 57410c3b) and again for the torque routes. A channel whose scale is a fork
    constant cannot carry a cross-build gain comparison.
 2. v282cmp.event_metrics defaults to ach_key="la_act". If the published high-jerk event gains (V282 0.95-0.99
    vs T64 1.29) were taken on that default, they are on the angle channel. Recompute both channels, same events.

usage: python a3_channels.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import load_route, my_runs, GROUP, FS


def lp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, btype="low", fs=FS, output="sos"), x)


def my_jerk_events(S, thr=0.8, vmin=15.0, pre=1.5, post=3.0, min_sep=2.0):
    """My own event finder: local peaks of |d/dt (2 Hz lowpassed model lat accel)|, whole window engaged and
    contiguous. Same definition in words as the study's, written from the words not the code."""
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= vmin)
    x = np.nan_to_num(S["x_model"])
    j = np.gradient(lp(x, 2.0)) * FS
    pk, _ = signal.find_peaks(np.abs(j), height=thr, distance=int(min_sep * FS))
    a, b = int(pre * FS), int(post * FS)
    ev = []
    for k in pk:
        if k - a < 0 or k + b >= len(x):
            continue
        sl = slice(k - a, k + b)
        if not m[sl].all() or np.any(np.diff(S["t"][sl]) > 0.04):
            continue
        ev.append((k - a, k + b))
    return ev, j


def gain_lag(x, y, maxlag=80):
    """Lag by max cross-covariance, then the least-squares gain at that lag. Deliberately the same recipe the
    study uses, so a difference between channels cannot be blamed on the recipe."""
    best, lag = -np.inf, 0
    for k in range(maxlag + 1):
        xa, ya = x[:len(x) - k], y[k:]
        c = float(np.dot(xa - xa.mean(), ya - ya.mean()))
        if c > best:
            best, lag = c, k
    xa, ya = x[:len(x) - lag], y[lag:]
    g = float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9))
    err = float(np.sqrt(np.mean((y - x) ** 2)) / max(np.sqrt(np.mean(x ** 2)), 1e-9))
    err_al = float(np.sqrt(np.mean((ya - xa) ** 2)) / max(np.sqrt(np.mean(xa ** 2)), 1e-9))
    return g, lag / FS, err, err_al


print("=== 1) is actualLateralAccel just curvature * v^2 ? (max abs difference on engaged frames) ===")
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    d = np.abs(S["y_act"][m] - S["y_curv"][m])
    dp = np.abs(S["y_act"][m] - S["y_pose"][m])
    print(f"  {r} {g:8s} max|act - curv*v^2| {np.nanmax(d):.3e}   rms|act - pose| {np.sqrt(np.nanmean(dp**2)):.4f}"
          f"   rms act {np.sqrt(np.nanmean(S['y_act'][m]**2)):.3f}")
    del S

print("\n=== 2) high-jerk event metrics, SAME events, two output channels ===")
print(f"{'group':8s} {'route':22s} {'nev':>4s} | {'gain_act':>8s} {'lag_act':>7s} {'err_act':>7s} | "
      f"{'gain_pose':>9s} {'lag_pose':>8s} {'err_pose':>8s} | {'errAl_pose':>10s}")
agg = {}
for r, g in GROUP.items():
    S = load_route(r)
    ev, _ = my_jerk_events(S)
    if not ev:
        del S
        continue
    rows = []
    for i0, i1 in ev:
        x = np.nan_to_num(S["x_model"][i0:i1])
        rows.append((gain_lag(x, np.nan_to_num(S["y_act"][i0:i1])),
                     gain_lag(x, np.nan_to_num(S["y_pose"][i0:i1]))))
    ga = np.median([a[0] for a, _ in rows]); la = np.median([a[1] for a, _ in rows]); ea = np.median([a[2] for a, _ in rows])
    gp = np.median([b[0] for _, b in rows]); lpg = np.median([b[1] for _, b in rows]); ep = np.median([b[2] for _, b in rows])
    eap = np.median([b[3] for _, b in rows])
    print(f"{g:8s} {r:22s} {len(ev):4d} | {ga:8.3f} {la:7.3f} {ea:7.3f} | {gp:9.3f} {lpg:8.3f} {ep:8.3f} | {eap:10.3f}")
    agg.setdefault(g, []).append((len(ev), ga, gp, la, lpg, ea, ep, eap))
    del S

print("\n  group medians (route-median of route medians):")
for g, v in agg.items():
    a = np.array(v)
    print(f"  {g:8s} nev {int(a[:,0].sum()):4d}  gain_act {np.median(a[:,1]):.3f}  gain_pose {np.median(a[:,2]):.3f}"
          f"  lag_act {np.median(a[:,3]):.3f}  lag_pose {np.median(a[:,4]):.3f}"
          f"  err_pose {np.median(a[:,6]):.3f}  errAligned_pose {np.median(a[:,7]):.3f}")
