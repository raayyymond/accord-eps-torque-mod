"""Split-half stability check on the longest V282 route (6c) and longest T64 route (6c-T64), using the
same v282cmp.band_H estimator as the main verify script, alternating runs into two halves."""
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60)]

for route in ["0000006c--2bc842dbac", "0000006c--68c6e94b17"]:
    S = V.load(route)
    m = V.usable(S, 15.0)
    rs = V.runs(m, S["t"], min_s=20.0)
    model = np.nan_to_num(S["model"]); pose = np.nan_to_num(S["la_pose"])
    segs = [(model[a:b], pose[a:b]) for a, b in rs if b - a >= 256]
    h1 = segs[0::2]; h2 = segs[1::2]
    print(f"{route} ({V.ROUTES[route]['group']}) nruns={len(segs)} half1={len(h1)} half2={len(h2)}")
    for f1, f2 in BANDS:
        r1 = V.band_H(h1, f1, f2); r2 = V.band_H(h2, f1, f2); rall = V.band_H(segs, f1, f2)
        print(f"  {f1}-{f2}: all={rall['H']:.3f}  half1={r1['H']:.3f} (sec {r1['sec']:.0f})  half2={r2['H']:.3f} (sec {r2['sec']:.0f})  diff={abs(r1['H']-r2['H']):.3f}")
    del S
