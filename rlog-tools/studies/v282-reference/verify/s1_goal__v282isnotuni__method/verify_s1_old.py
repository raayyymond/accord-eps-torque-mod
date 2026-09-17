import sys, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60)]
for route in ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]:
    S = V.load(route)
    m = V.usable(S, 15.0)
    rs = V.runs(m, S["t"], min_s=20.0)
    model = np.nan_to_num(S["model"]); pose = np.nan_to_num(S["la_pose"])
    segs = [(model[a:b], pose[a:b]) for a, b in rs if b - a >= 256]
    sec = sum(b-a for a,b in rs)/V.FS
    print(f"{route} nruns_used={len(segs)} sec={sec:.0f}")
    for f1, f2 in BANDS:
        r = V.band_H(segs, f1, f2)
        print(f"  {f1}-{f2}: H={r['H']:.3f} coh={r['coh']:.2f}" if r else f"  {f1}-{f2}: n/a")
    del S
