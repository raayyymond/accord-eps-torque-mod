"""rev_1ab_gap.py -- route 79: 0x1AB (bus 1) inter-frame gaps on the cache, to size the fork's 100 ms staleness rule; and
the 0x18F (STEER_STATUS) gaps the rule uses as its clock.  Read-only; vectorised; wall printed."""
import time
from pathlib import Path
import numpy as np
T0 = time.time()
C = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
W = np.load(C / "r79_a1f5d2_al.npz")
for nm in ("t1ab", "t18"):
    t = np.asarray(W[nm], float)
    d = np.diff(t) * 1000.0
    big = d[d > 100.0]
    print(f"{nm}: n {len(t)}  dt p50 {np.median(d):.1f} ms  p99.9 {np.percentile(d, 99.9):.1f}  max {d.max():.1f}  "
          f"gaps > 40 ms {int((d > 40).sum())}  > 100 ms {len(big)} (the largest {np.sort(big)[-5:].round(0).tolist()})")
print(f"wall {time.time() - T0:.2f} s")
