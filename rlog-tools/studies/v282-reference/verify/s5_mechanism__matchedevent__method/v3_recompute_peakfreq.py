"""Independent re-derivation of s5_08_event_rate_spectrum.json's peak_hz / 1.5-3.5 Hz band RMS claim.
No s5_08_event_rate_spectrum.py exists in s5_mechanism/ (the .json has no generating script on disk) so this
number was previously un-auditable from source. Recompute from scratch: for each group/stratum, concatenate
band-passed (0.5-15 Hz) steering-rate segments from all jerk_events windows [-1.5,+3.0]s (v282cmp default
thr=0.5, vmin=3), take a pooled Welch PSD of steer RATE, report the peak freq in 1-4 Hz and RMS in 1.5-3.5 Hz.
"""
import json
import numpy as np
from scipy import signal
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L

V = L.V
FS = V.FS


def band_rms(x, f1, f2):
    sos = signal.butter(4, [f1, f2], btype='band', fs=FS, output='sos')
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos, x) ** 2)))


res = {}
for g, routes in L.GROUPS.items():
    segs = {(3, 8): [], (8, 15): [], (15, 99): []}
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
        cat = np.concatenate(lst)
        nps = min(1024, len(cat))
        f, p = signal.welch(cat, fs=FS, nperseg=nps)
        band = (f >= 1.0) & (f <= 4.0)
        pk = f[band][np.argmax(p[band])]
        rms15_35 = band_rms(cat, 1.5, 3.5)
        # per-event RMS median (closer to what s5_08 likely reports -- a per-event stat, not one pooled RMS)
        per_ev = [band_rms(x, 1.5, 3.5) for x in lst]
        key = f'{g}|{lo}-{hi}'
        res[key] = dict(n=len(lst), peak_hz=float(pk), pooled_rms=rms15_35, per_event_median=float(np.median(per_ev)))
        print(key, res[key])

json.dump(res, open('v3_recompute_peakfreq.json', 'w'), indent=1)
