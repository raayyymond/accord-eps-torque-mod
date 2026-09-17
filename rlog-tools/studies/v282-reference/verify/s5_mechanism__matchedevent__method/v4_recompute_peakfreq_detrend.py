"""v3 pooled the raw concatenated steer-rate segments and found peak_hz pulled to ~1.0-1.4 Hz (the jerk-event's
own low-freq maneuver content, not a resonance) -- disagreeing badly with s5_08_event_rate_spectrum.json for
several strata (T64B|8-15: mine 1.07 vs s5_08's 3.13; T4|8-15: mine 1.07 vs s5_08's 2.73). Retry per-EVENT Welch
(detrend='linear' removes each window's own ramp) averaged across events -- the standard event-PSD method --
to see if that recovers s5_08's reported peak frequencies.
"""
import json
import numpy as np
from scipy import signal
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L

V = L.V
FS = V.FS

res = {}
for g, routes in L.GROUPS.items():
    segs = {(8, 15): [], (15, 99): []}
    for rk in routes:
        S = V.load(rk)
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        for e in ev:
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if not np.isfinite(S['sr'][i0:i1]).all():
                continue
            for lo, hi in segs:
                if lo <= e['v'] < hi:
                    segs[(lo, hi)].append(np.nan_to_num(S['sr'][i0:i1]))
        del S
    for (lo, hi), lst in segs.items():
        if len(lst) < 3:
            continue
        nps = len(lst[0])
        Psum = None
        for x in lst:
            f, p = signal.welch(x, fs=FS, nperseg=nps, detrend='linear')
            Psum = p if Psum is None else Psum + p
        Pavg = Psum / len(lst)
        band = (f >= 1.0) & (f <= 5.0)
        pk = f[band][np.argmax(Pavg[band])]
        key = f'{g}|{lo}-{hi}'
        res[key] = dict(n=len(lst), peak_hz=float(pk))
        print(key, res[key])

json.dump(res, open('v4_recompute_peakfreq_detrend.json', 'w'), indent=1)
