"""S3: which of the three proposed bar formulas keeps the CURRENT angle-mode bar's sign convention? (route 79)

Current bar (torque_bar.py angle branch) = clip((curvature*v^2 - roll*g*k(v) + (desiredCurvature - curvature)*v^2)
/ maxLateralAccel) = (desiredCurvature*v^2 - roll*g*k)/0.3247.  Proposed: D1 bar = +8*s10/2461 ; D2 steeringTorqueEps =
-8*s10, bar = +eps/2461 ; D5 steeringTorqueEps = -T (T = 8*s10), bar = +eps/2461.  s10 = sign-magnitude 10-bit
MOTOR_TORQUE (DBC 1|10@0+: raw = ((b0&3)<<8)|b1, bit 9 sign).  Also: are the fork fields D2 wants to reuse free on r79?
Vectorised; wall time printed.
"""
import time
from pathlib import Path
import numpy as np

T0 = time.time()
C = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280")
W = np.load(C / "r79_a1f5d2_al.npz")
F = np.load(C / "r79_fork.npz")
out = []
def say(s=""): out.append(s); print(s)

raw = ((W["b0"] & 3) << 8) | W["b1"]
s10 = np.where(raw & 0x200, -1, 1) * (raw & 0x1FF)
t1 = W["t1ab"]
# steady engaged holds, hands-off: from carState rows
tcs, ang, rate, press, v = F["t_cs"], F["cs_ang"], F["cs_rate"], F["cs_press"].astype(bool), F["cs_vego"]
lat = np.interp(tcs, F["t_cc"], F["cc_latActive"].astype(float)) > 0.5
hold = lat & ~press & (np.abs(ang) > 5) & (np.abs(ang) < 60) & (np.abs(rate) < 5) & (v > 3)
j = np.clip(np.searchsorted(t1, tcs), 0, len(t1) - 1)
tap = s10[j]
m = hold & (np.abs(tap) >= 3)
say(f"steady hands-off holds with |tap|>=3 LSB: {m.sum()} frames")
say(f"  sign(tap) == sign(angle) [+ = left]: {np.mean(np.sign(tap[m]) == np.sign(ang[m])):.4f}")
# current bar sign on the same frames
tc = F["t_ctl"]
dk = np.interp(tcs, tc, F["ctl_dcurv"])
roll = np.interp(tcs, F["t_lp"], F["lp_roll"])
cur = (dk * v ** 2 - roll * 9.81 * np.interp(v, [5, 15], [0, 1])) / 0.3247
mb = m & (np.abs(cur) > 0.05)
say(f"  sign(current bar) == sign(angle): {np.mean(np.sign(cur[mb]) == np.sign(ang[mb])):.4f}  (n {mb.sum()})")
for nm, bar in (("D1  +8*s10", 8.0 * tap), ("D2  -8*s10", -8.0 * tap), ("D5  -T", -8.0 * tap)):
    say(f"  {nm:12s}: sign agrees with the current bar on {np.mean(np.sign(bar[mb]) == np.sign(cur[mb])):.4f}")
# free fields D2 wants for its instrument
for k in ("co_tq", "ang_output", "cs_tqeps", "cc_tq"):
    x = F[k]
    say(f"  fork field {k}: nonzero on {np.count_nonzero(x)} of {x.size} rows")
say(f"  liveDelay ld_lat unique: {np.unique(F['ld_lat'])[:5]}")
say(f"\nwall {time.time() - T0:.1f} s")
Path(__file__).with_suffix(".txt").write_text("\n".join(out))
