"""Judge (goal-and-operator-notes) second-method check of S3's bar-sign finding, route 79.
Different frame set from s3_bar_sign.py: ALL latActive hands-off frames with |tap| >= 10 LSB and |today's bar| >= 0.1,
angle taken from the WIRE 0x14A (key 'ang'), not carState. Read-only; vectorised; prints wall time."""
import time
from pathlib import Path
import numpy as np
T0 = time.time()
C = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
W = np.load(C / "r79_a1f5d2_al.npz"); F = np.load(C / "r79_fork.npz")
raw = ((W["b0"] & 3) << 8) | W["b1"]
s10 = np.where(raw & 0x200, -1, 1) * (raw & 0x1FF)
tcs, v, press = F["t_cs"], F["cs_vego"], F["cs_press"].astype(bool)
lat = np.interp(tcs, F["t_cc"], F["cc_latActive"].astype(float)) > 0.5
tap = s10[np.clip(np.searchsorted(W["t1ab"], tcs), 0, len(W["t1ab"]) - 1)]
angw = np.interp(tcs, W["t14"], W["ang"])
dk = np.interp(tcs, F["t_ctl"], F["ctl_dcurv"]); roll = np.interp(tcs, F["t_lp"], F["lp_roll"])
cur = np.clip((dk * v**2 - roll * 9.81 * np.interp(v, [5, 15], [0, 1])) / 0.3247, -1, 1)
m = lat & ~press & (np.abs(tap) >= 10) & (np.abs(cur) >= 0.1) & (v > 3)
print(f"frames {m.sum()}")
print(f"sign(tap)==sign(wire angle, +left?) {np.mean(np.sign(tap[m])==np.sign(angw[m])):.3f}")
for nm, b in (("D1 +tap/307.6", tap / 307.6), ("D2/D5 as written -tap/307.6", -tap / 307.6)):
    print(f"{nm:28s} sign agree w/ today's bar {np.mean(np.sign(b[m])==np.sign(cur[m])):.3f}  "
          f"corr {np.corrcoef(b[m], cur[m])[0,1]:+.3f}")
print(f"wall {time.time()-T0:.2f} s")
