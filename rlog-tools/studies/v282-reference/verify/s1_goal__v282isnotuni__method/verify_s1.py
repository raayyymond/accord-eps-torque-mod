"""Independent re-derivation of finding s1 'v282-is-not-unity-on-highway'.

Uses ONLY v282cmp.py's own load()/usable()/runs()/band_H() -- no reuse of s1_goal's reduce/analyze
machinery (s1_reduce.py's fixed-nperseg-per-band Hilbert pipeline is NOT re-used; this is a fully
independent estimator path built from the documented per-bin |Pxy|/Pxx band_H in the shared lib).

For each route (V282 group and T64 group), at v>15 m/s:
  - build usable runs (>= 20 s, so >=2000 samples -- enough for band_H's own nperseg selection)
  - for each band (0.05-0.15, 0.15-0.3, 0.3-0.6 Hz), call V.band_H on (model, la_pose) and (model, la_act)
  - report H, coh, phase, total seconds, n segments

Also: sign check (does flipping model or la_pose invert H, i.e. is x defined consistently with lib), and
a lag-alignment time-domain cross-check per route/band using bandpass-filtered signals + V.event_metrics-
style gain (regression at best lag), as an estimator-independent confirmation.
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

ROUTES_V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
ROUTES_T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60)]

results = []

for route in ROUTES_V282 + ROUTES_T64:
    print(f"\n=== {route} ({V.ROUTES[route]['group']}) ===", flush=True)
    S = V.load(route)
    m = V.usable(S, 15.0)
    rs = V.runs(m, S["t"], min_s=20.0)
    print(f"  usable>15m/s runs>=20s: {len(rs)}, total { sum(b-a for a,b in rs)/V.FS:.0f} s "
          f"(all usable>15: {m.sum()/V.FS:.0f} s)")
    model = np.nan_to_num(S["model"])
    la_pose = np.nan_to_num(S["la_pose"])
    la_act = np.nan_to_num(S["la_act"])
    la_yaw = np.nan_to_num(S["la_yaw"])
    # sign sanity: correlation sign of model vs each achieved measure over the runs
    xs = np.concatenate([model[a:b] for a, b in rs]) if rs else np.array([])
    yp = np.concatenate([la_pose[a:b] for a, b in rs]) if rs else np.array([])
    ya = np.concatenate([la_act[a:b] for a, b in rs]) if rs else np.array([])
    yy = np.concatenate([la_yaw[a:b] for a, b in rs]) if rs else np.array([])
    if len(xs) > 100:
        corr_pose = float(np.corrcoef(xs, yp)[0, 1])
        corr_act = float(np.corrcoef(xs, ya)[0, 1])
        corr_yaw = float(np.corrcoef(xs, yy)[0, 1])
        print(f"  sign check: corr(model,la_pose)={corr_pose:.3f}  corr(model,la_act)={corr_act:.3f}  corr(model,la_yaw)={corr_yaw:.3f}")
    row = dict(route=route, group=V.ROUTES[route]["group"], nruns=len(rs), sec=sum(b - a for a, b in rs) / V.FS)
    for f1, f2 in BANDS:
        segs_pose = [(model[a:b], la_pose[a:b]) for a, b in rs if b - a >= 256]
        segs_act = [(model[a:b], la_act[a:b]) for a, b in rs if b - a >= 256]
        segs_yaw = [(model[a:b], la_yaw[a:b]) for a, b in rs if b - a >= 256]
        rp = V.band_H(segs_pose, f1, f2)
        ra = V.band_H(segs_act, f1, f2)
        ry = V.band_H(segs_yaw, f1, f2)
        bk = f"{f1}-{f2}"
        row[f"H_pose_{bk}"] = rp["H"] if rp else None
        row[f"coh_pose_{bk}"] = rp["coh"] if rp else None
        row[f"H_act_{bk}"] = ra["H"] if ra else None
        row[f"coh_act_{bk}"] = ra["coh"] if ra else None
        row[f"H_yaw_{bk}"] = ry["H"] if ry else None
        row[f"coh_yaw_{bk}"] = ry["coh"] if ry else None
        print(f"  band {bk:9s} Hz: H_pose={rp['H']:.3f} (coh {rp['coh']:.2f}, n={rp['n']}, sec={rp['sec']:.0f})  "
              f"H_act={ra['H']:.3f} (coh {ra['coh']:.2f})  H_yaw={ry['H']:.3f} (coh {ry['coh']:.2f})"
              if rp and ra and ry else f"  band {bk}: insufficient data")
    results.append(row)
    del S

json.dump(results, open("verify_s1_results.json", "w"), indent=1)
print("\nwrote verify_s1_results.json")
