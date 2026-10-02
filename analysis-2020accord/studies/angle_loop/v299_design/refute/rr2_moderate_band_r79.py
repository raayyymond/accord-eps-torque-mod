"""rr2_moderate_band_r79.py -- how much of route 79's real driving sits in the band rev 2 leaves un-yielded
(600 < |wire| <= 1200, latActive, not steeringPressed), and, open loop, where the no-override setpoint would have sat
relative to the hand (REV2 limiter, as rr2_f12_differential).  EVIDENCE: the hand words and the code arithmetic on r79's
inputs.  BELIEF: anything about what the closed loop would have done (the wheel is r79's, not V299's).  Prints wall."""
import sys, time
from pathlib import Path
import numpy as np
T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "v298_flight"))
import m4_common as M  # noqa: E402
F = M.fork_cache(); R = M.limiter_reconstruct(F)
lat, des, th, v, dmax, emax, amax = (R[k] for k in ("lat", "des", "th", "v", "dmax", "emax", "amax"))
n = len(lat)
sh = lambda x: np.r_[x[:1], x[:-1]].astype(float)  # noqa: E731
tqs = sh(F["cs_tq"]); press = sh(F["cs_press"]).astype(bool)
new = np.empty(n); last = None
for i in range(n):
    al = th[i] if last is None else last
    a = min(max(des[i], al - dmax[i]), al + dmax[i]); a = min(max(a, -amax[i]), amax[i])
    if not lat[i]: a = th[i]
    else: a = min(max(a, th[i] - emax[i]), th[i] + emax[i])
    new[i] = a; last = a
band = lat & ~press & (np.abs(tqs) > 600)
dt = np.median(np.diff(R["t"]))
def runs(m):
    e = np.diff(np.r_[0, m.astype(np.int8), 0]); s = np.where(e == 1)[0]; f = np.where(e == -1)[0]; return s, f
s, f = runs(band); L = (f - s) * dt
print(f"frame dt {dt*1e3:.1f} ms; latActive {lat.sum()*dt:.0f} s; moderate band (600<|wire|, not pressed) {band.sum()*dt:.1f} s in {len(s)} runs")
print(f"runs > 0.3 s: {np.sum(L>0.3)} (total {L[L>0.3].sum():.1f} s); > 1 s: {np.sum(L>1.0)}")
err = new - th                      # + = setpoint left of wheel (cs_ang + left)
# carState steeringTorque sign: + = driver torque to the left (opendbc convention)
opp = band & (np.sign(err) == -np.sign(tqs)) & (np.abs(err) > 1.0)
print(f"band frames where the REV2 setpoint sits > 1 deg on the side OPPOSITE the hand: {opp.sum()*dt:.1f} s "
      f"({np.mean(opp[band])*100:.0f} % of band); |err| there p50 {np.median(np.abs(err[opp])):.1f} p90 {np.percentile(np.abs(err[opp]),90):.1f} deg")
so, fo = runs(opp); Lo = (fo - so) * dt
print(f"opposing runs > 0.3 s (F7b's duration clause; the 40 %-of-rail clause needs the closed loop): {np.sum(Lo>0.3)}")
print(f"wall {time.time()-T0:.2f} s")
