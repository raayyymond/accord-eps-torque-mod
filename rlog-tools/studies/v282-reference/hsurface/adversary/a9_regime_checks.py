"""ADVERSARY A9 - three regime checks that decide whether the amplitude story can be told on THESE windows.

 1. DOES THE ACTUATOR RAIL IN THE WINDOWS |H| IS MEASURED ON? The amplitude-dependence mechanism on the table is
    the command railing at full scale. That was measured below 8 m/s. The |H| windows are >=15 m/s. If |output|
    never approaches 1 there, saturation cannot be the mechanism for any highway amplitude effect.
 2. IS THE OUTPUT CHANNEL CONTAMINATED BY ROAD BANK, DIFFERENTLY PER GROUP? y = yaw x v answers to bank as well
    as to steering; a group driven on more crowned roads would read a different gain.
 3. HOW FLAT IS THE BUILD GAP ACROSS AMPLITUDE? If the V282->T64 offset is the same in every amplitude stratum,
    the existing routes cannot support any amplitude-dependent ranking, whatever the per-stratum |H| does.

usage: python a9_regime_checks.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import load_route, my_runs, windows, band_stats, GROUP, FS

NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)

print("=== 1) command magnitude in the |H| windows (engaged, hands off, >=15 m/s, runs >=41 s) ===")
print(f"{'route':22s} {'grp':8s} {'n_s':>7s} {'|out| p50':>9s} {'p95':>6s} {'p99.9':>6s} {'max':>6s} "
      f"{'frac>0.9':>9s} {'satflag':>8s} | {'<8 m/s: frac>0.9':>17s} {'max':>6s}")
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    keep = np.zeros(len(m), bool)
    for a, b in my_runs(m, S["t"], 41.0):
        keep[a:b] = True
    o = np.abs(np.nan_to_num(S["out"][keep]))
    lo = S["lat_active"] & ~S["pressed"] & (S["v"] < 8.0)
    ol = np.abs(np.nan_to_num(S["out"][lo]))
    print(f"{r:22s} {g:8s} {keep.sum()/FS:7.0f} {np.percentile(o,50):9.3f} {np.percentile(o,95):6.3f} "
          f"{np.percentile(o,99.9):6.3f} {o.max():6.3f} {np.mean(o>0.9):9.5f} {np.mean(S['sat'][keep]):8.4f} | "
          f"{np.mean(ol>0.9) if len(ol) else float('nan'):17.5f} {ol.max() if len(ol) else float('nan'):6.3f}")
    del S

print("\n=== 2) in-band road-bank power in the same windows (liveParameters.roll, rad; 1 deg = 0.0175) ===")
sos = signal.butter(4, [0.08, 0.60], btype="band", fs=FS, output="sos")
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    keep = np.zeros(len(m), bool)
    for a, b in my_runs(m, S["t"], 41.0):
        keep[a:b] = True
    if keep.sum() < 2000:
        del S; continue
    roll = np.nan_to_num(S["roll"])
    rb = signal.sosfiltfilt(sos, roll)[keep]
    # the lateral accel a bank of that size contributes, for scale against the in-band demand RMS
    print(f"  {r:22s} {g:8s} roll rms {np.std(roll[keep]):.5f} rad ({np.degrees(np.std(roll[keep])):.2f} deg)  "
          f"in-band 0.08-0.6 Hz rms {np.std(rb):.5f} rad = {9.81*np.std(rb):.4f} m/s^2 equivalent")
    del S

print("\n=== 3) the build gap across amplitude strata (band 0.08-0.25 and 0.15-0.30 Hz) ===")
wins = []
for r, g in GROUP.items():
    if g not in ("V282", "T64"):
        continue
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    x_all, y_all = np.nan_to_num(S["x_model"]), np.nan_to_num(S["y_pose"])
    for a, b in my_runs(m, S["t"], 41.0):
        for pxx, pyy, pxy, s in windows(x_all[a:b], y_all[a:b], NPS, NPS // 2):
            wins.append(dict(g=g, r=r, W=dict(pxx=pxx, pyy=pyy, pxy=pxy),
                             v=float(np.median(S["v"][a + s:a + s + NPS]))))
    del S
for f1, f2 in [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]:
    for w in wins:
        w["a"] = band_stats([w["W"]], f, f1, f2)["in_rms"]
    qs = np.percentile([w["a"] for w in wins], [25, 50, 75])
    print(f"  band {f1}-{f2} Hz, quartile edges {qs[0]:.4f}/{qs[1]:.4f}/{qs[2]:.4f} m/s^2")
    edges = [-1] + list(qs) + [1e9]
    for i in range(4):
        row = f"    Q{i+1}"
        got = {}
        for g in ("V282", "T64"):
            Ws = [w["W"] for w in wins if w["g"] == g and edges[i] <= w["a"] < edges[i + 1]]
            st = band_stats(Ws, f, f1, f2)
            got[g] = st
            row += f"  {g} n{len(Ws):3d} " + (f"H {st['H_mag']:5.3f} nrmse {st['nrmse']:5.3f}" if st else "H   --  nrmse   -- ")
        if got["V282"] and got["T64"]:
            row += f"   gap dH {got['T64']['H_mag']-got['V282']['H_mag']:+.3f}  " \
                   f"dNRMSE {got['T64']['nrmse']-got['V282']['nrmse']:+.3f}"
        print(row)
    print()
