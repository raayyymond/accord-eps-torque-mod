import sys, gc
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    u = V.usable(S)
    ld = S['lat_delay'][u]
    ld = ld[np.isfinite(ld)]
    print(f"{rk:24s} {meta['group']:8s} lat_delay median={np.median(ld):.3f} n={len(ld)} (min {np.min(ld):.3f} max {np.max(ld):.3f})")
    del S, u, ld
    gc.collect()
