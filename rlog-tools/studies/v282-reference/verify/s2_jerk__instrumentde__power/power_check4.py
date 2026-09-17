"""Part 4: reconcile the finding's low-speed (<8 m/s) event census and do a power calc for the "leaves
6 V282 and 7 T64 usable events" number. Also check: does the pressed-fraction claim rely on RAW peaks
(before the jerk_events() full-window usable() check), or on already-window-filtered events? Compute
both, per route, at <8 m/s, and derive minimum detectable effect size given the resulting N.
"""
import sys, json, gc
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

FS = V.FS
report = {}
for rk in V.ROUTES:
    try:
        S = V.load(rk)
    except FileNotFoundError:
        continue
    meta = S['meta']
    m_engaged_nopress_lt8 = V.usable(S, 0, 8.0)  # active & ~pressed & v<8
    model = np.nan_to_num(S['model'])
    j = V.deriv(V.lowpass(model, 2.0))
    aj = np.abs(j)

    # RAW peaks (>=0.4 as in s2_extract, min_sep 2s) at v<8, active (any lat_active), regardless of pressed,
    # then separately check how many of THOSE peaks have steeringPressed exactly at the peak sample.
    active_only = S['active']
    v_lt8 = (S['v'] >= 3.0) & (S['v'] < 8.0)
    cand_mask = active_only & v_lt8
    pk, _ = signal.find_peaks(aj, height=0.4, distance=int(2.0 * FS))
    pk = [k for k in pk if cand_mask[k]]
    n_raw = len(pk)
    n_pressed_at_peak = int(sum(1 for k in pk if S['pressed'][k]))

    # Now the FULL jerk_events() usable-window filter (as s2_extract actually calls it): thr=0.4, vmin=3.0,
    # pre=1.0, post=2.5, whole window must be usable() (active & ~pressed & v in [vmin,vmax)) and contiguous.
    ev, _ = V.jerk_events(S, jerk_thr=0.4, vmin=3.0, pre=1.0, post=2.5, min_sep=2.0)
    ev_lt8 = [e for e in ev if e['v'] < 8.0]
    n_windowed_usable = len(ev_lt8)

    report[rk] = dict(group=meta['group'], n_raw_peaks_active_v3_8=n_raw,
                       n_pressed_at_peak=n_pressed_at_peak,
                       n_notpressed_at_peak=n_raw - n_pressed_at_peak,
                       n_full_window_usable_events_v_lt8=n_windowed_usable)
    del S, model, j, aj, active_only, v_lt8, cand_mask
    gc.collect()

print(json.dumps(report, indent=1))
with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__power/d_lowspeed_census.json', 'w') as f:
    json.dump(report, f, indent=1)

# aggregate by group
from collections import defaultdict
agg = defaultdict(lambda: dict(raw=0, pressed=0, windowed=0))
for rk, r in report.items():
    g = r['group']
    agg[g]['raw'] += r['n_raw_peaks_active_v3_8']
    agg[g]['pressed'] += r['n_pressed_at_peak']
    agg[g]['windowed'] += r['n_full_window_usable_events_v_lt8']
print(json.dumps(agg, indent=1))
