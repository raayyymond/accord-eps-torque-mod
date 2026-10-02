"""rr2_f12_differential.py -- RE-REFUTER (fork lens) check of rev 2's F12(a)/(b) claim: 'identical raw on every frame
OUTSIDE V298's O1 episodes'.  Recursive replay of BOTH limiters on route 79's fork frame axis (inputs exactly as
m4_common.limiter_reconstruct: carControl i-1 pairing, carState i-1), V298 = Dom 2712e1336 _update_angle (O1 on,
restart-from-wheel on release), REV2 = the same with the override deleted (F3).  Counts latActive frames outside O1
where the 0xE4 raw differs, and the post-release windows.  Open loop (the wheel is r79's): BELIEF for what the car would
have done, EVIDENCE for what the code computes on these inputs.  Read-only; prints wall."""
import sys, time, math
from pathlib import Path
import numpy as np
T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "v298_flight"))
import m4_common as M  # noqa: E402
F = M.fork_cache()
R = M.limiter_reconstruct(F)
lat, des, th, rate, tq, v, dmax, emax, amax = (R[k] for k in ("lat", "des", "th", "rate", "tq", "v", "dmax", "emax", "amax"))
co = R["co"]; n = len(lat)
ON, OFF, LEAD = M.OVR_ON, M.OVR_OFF, M.OVR_LEAD
def run(override):
    out = np.empty(n); ovr_arr = np.zeros(n, bool); last = None; ovr = False
    for i in range(n):
        was = ovr
        ovr = (tq[i] > (OFF if ovr else ON)) if (lat[i] and override) else False
        al = th[i] if (last is None or (was and not ovr)) else last
        a = min(max(des[i], al - dmax[i]), al + dmax[i]); a = min(max(a, -amax[i]), amax[i])
        if not lat[i]:
            a = th[i]
        else:
            if ovr:
                a = th[i] + rate[i] * LEAD
            a = min(max(a, th[i] - emax[i]), th[i] + emax[i]); a = min(max(a, -400.0), 400.0)
        out[i] = a; ovr_arr[i] = ovr; last = a
    return out, ovr_arr
old, ovr = run(True); new, _ = run(False)
raw = lambda a: np.floor(-10.0 * a + 0.5)  # noqa: E731
rawc = raw(co)
print(f"self-check: V298 recursive replay raw == published co raw on latActive frames {np.mean(raw(old)[lat]==rawc[lat]):.4f}"
      f" (limiter_reconstruct non-recursive res==0: {np.mean(np.abs(R['res'][lat])<1e-3):.4f})")
outside = lat & ~ovr
d = raw(old) != raw(new)
print(f"latActive {lat.sum()}, O1 frames {(lat&ovr).sum()}, outside-O1 {outside.sum()}")
print(f"outside-O1 frames where V298 raw != REV2 raw: {(d&outside).sum()} = {np.mean(d[outside])*100:.2f} %")
# post-release windows: frames after each O1 release until the two agree
rel = np.where(np.r_[False, ovr[:-1] & ~ovr[1:]] & lat)[0]
lens = []
for r in rel:
    k = r
    while k < n and d[k] and not ovr[k]:
        k += 1
    lens.append(k - r)
lens = np.array(lens)
print(f"O1 releases {len(rel)}; post-release disagreement length (frames) p50 {np.median(lens):.0f} p90 {np.percentile(lens,90):.0f} max {lens.max()}")
gap = np.abs(new - th)[rel]; gap_old = np.abs(old - th)[rel]
print(f"|setpoint - wheel| at the release frame: REV2 p50 {np.median(gap):.2f} p90 {np.percentile(gap,90):.2f} max {gap.max():.2f} deg;"
      f" V298 p50 {np.median(gap_old):.2f} max {gap_old.max():.2f}")
cmp_rec = np.mean((raw(new) == rawc)[outside])
print(f"(b)-style: REV2 raw == recorded torqueOutputCan-equivalent (co raw) on outside-O1 frames {cmp_rec*100:.3f} %")
print(f"wall {time.time()-T0:.2f} s")

# --- F3 as worded vs the no-override hold gap (appended): at each hand-episode end (V298 O1 release), the REV2 gap
# |theta_sp - theta| IS F3's quantity at t = 0 of its 1.5-s window.  Open loop on r79 (BELIEF for the closed loop).
vr = v[rel]
g8 = (vr >= 8.0)
print(f"F3 check: releases at v >= 8 m/s: {g8.sum()}; of them REV2 gap > 8 deg AT the release frame: {(gap[g8] > 8).sum()} "
      f"(V298: {(gap_old[g8] > 8).sum()}); gap there p50 {np.median(gap[g8]) if g8.any() else float('nan'):.1f} deg")
print(f"wall (incl. F3) {time.time()-T0:.2f} s")
