"""Adversarial cross-check: la_pose_rough came back near-flat (V282 vs torque ratio 1.0-1.4x) while the wheel-side
'hf' (steering-rate 2-10Hz RMS) showed 2.3-5.4x. But la_pose (livePose, ~20 Hz) cannot resolve 2-10 Hz content
(Nyquist ~10 Hz, and locationd itself low-pass filters well below that) -- so its flatness may be an INSTRUMENT
ceiling, not independent disconfirmation. la_yaw (carState yaw rate x v, on the ~100 Hz controlsState clock) CAN
resolve 2-10 Hz. Recompute a steer_hf-style band RMS on la_yaw over the same jerk-event windows, one route at a
time, and compare V282 vs torque -- does the vehicle-motion (not just wheel-angle) texture actually track the
'hf' elevation, or does it look like la_pose (flat)?
"""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V  # noqa: E402

ROUTES = {
    'V282': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac'],
    'T64':  ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T64B': ['0000006e--6ca3e014fd'],
    'T5':   ['00000076--d0b7ea7e4d'],
    'T4':   ['00000075--6c8687d5bd'],
}

rows = []
for g, rks in ROUTES.items():
    for rk in rks:
        S = V.load(rk)
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        for e in ev:
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if i0 < 0 or i1 >= len(S['t']):
                continue
            if not np.isfinite(S['la_yaw'][i0:i1]).all() or not np.isfinite(S['sr'][i0:i1]).all():
                continue
            hf_wheel = V.steer_hf(S, i0, i1)                    # same def as s5_04 (steering RATE, 2-10 Hz)
            hf_yaw = V.steer_hf(dict(sr=S['la_yaw']), i0, i1)   # reuse steer_hf's band-RMS machinery on la_yaw
            rows.append(dict(g=g, rk=rk, v=e['v'], hf_wheel=hf_wheel, hf_yaw=hf_yaw))
        del S
        print(g, rk, 'events', len(ev), flush=True)

json.dump(rows, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__feedbackceil__confound/v3_layaw_rows.json', 'w'))

print('\n=== hf_wheel vs hf_yaw, by group and speed band (median, matched roughly to s5_04 strata) ===')
for vb in ((3, 8), (8, 15), (15, 99)):
    print(f'-- v {vb} --')
    for g in ROUTES:
        sel = [r for r in rows if r['g'] == g and vb[0] <= r['v'] < vb[1]]
        if len(sel) < 3:
            print(f'  {g:6s} n={len(sel)} (too few)')
            continue
        hw = np.array([r['hf_wheel'] for r in sel]); hy = np.array([r['hf_yaw'] for r in sel])
        print(f"  {g:6s} n={len(sel):3d}  hf_wheel_med={np.median(hw):7.3f}  hf_yaw_med={np.median(hy):7.4f}")
