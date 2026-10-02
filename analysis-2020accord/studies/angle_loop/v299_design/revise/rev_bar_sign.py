"""rev_bar_sign.py -- reconcile the two bar-sign findings on route 79 (judge: +tap/307.6 agrees with today's bar 0.854;
fork refuter: sign(tap) == sign(carState angle, + left) on 0.0 % of holds).  Same frames, three pairwise signs.
Read-only on the r79 caches; vectorised; wall printed."""
import time
from pathlib import Path
import numpy as np
T0 = time.time()
C = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
W = np.load(C / "r79_a1f5d2_al.npz"); F = np.load(C / "r79_fork.npz")
print("W keys", sorted(W.files)[:40]); print("F keys", [k for k in F.files if k.startswith(("cs_", "t_", "cc_", "ctl_", "co_"))][:60])
raw = ((W["b0"] & 3) << 8) | W["b1"]
s10 = np.where(raw & 0x200, -1, 1) * (raw & 0x1FF)
tcs, v, press = F["t_cs"], F["cs_vego"], F["cs_press"].astype(bool)
lat = np.interp(tcs, F["t_cc"], F["cc_latActive"].astype(float)) > 0.5
tap = s10[np.clip(np.searchsorted(W["t1ab"], tcs), 0, len(W["t1ab"]) - 1)]
angw = np.interp(tcs, W["t14"], W["ang"])
csang = F["cs_ang"] if "cs_ang" in F.files else None
dk = np.interp(tcs, F["t_ctl"], F["ctl_dcurv"]); roll = np.interp(tcs, F["t_lp"], F["lp_roll"])
cur = np.clip((dk * v**2 - roll * 9.81 * np.interp(v, [5, 15], [0, 1])) / 0.3247, -1, 1)
m = lat & ~press & (np.abs(tap) >= 10) & (np.abs(cur) >= 0.1) & (v > 3)
sg = lambda a, b: float(np.mean(np.sign(a[m]) == np.sign(b[m])))
print(f"frames {m.sum()}")
print(f"sign(tap)==sign(wire ang)     {sg(tap, angw):.3f}")
if csang is not None:
    print(f"sign(tap)==sign(cs_ang +left) {sg(tap, csang):.3f}")
    print(f"sign(cs_ang)==sign(wire ang)  {sg(csang, angw):.3f}")
    print(f"sign(cs_ang)==sign(today bar) {sg(csang, cur):.3f}")
print(f"sign(tap)==sign(today bar)    {sg(tap, cur):.3f}")
print(f"sign(wire ang)==sign(today bar){sg(angw, cur):.3f}")
print(f"wall {time.time()-T0:.2f} s")
