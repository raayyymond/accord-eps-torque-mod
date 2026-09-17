"""Adversarial check: is the pre-jerk-peak wrong-way motion specifically carryover from a PRECEDING
detected jerk EVENT (min_sep=2.0s apart), or does it show up just as strongly on ISOLATED events with
no other detected event nearby? If isolated events show it too, "carries the previous event's overshoot"
is not the right causal story -- it's just generic slow-settling/lag, unrelated to a discrete prior event.

Uses the same rows/traces as s2_stickslip.py / s2_pre_check.py (s2_jerk/_out/events_*.npz), plus each
row's own 't' (event time) and 'route' to compute time-since-prior-event-in-same-route.
"""
import numpy as np, warnings
warnings.filterwarnings('ignore')
from scipy import signal
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all

rows, tr = load_all()
sos = signal.butter(2, 3.0, fs=100, output='sos')

# time since the previous event IN THE SAME ROUTE (any type/speed), and gap to next
by_route = {}
for r in rows:
    by_route.setdefault(r['route'], []).append(r)
for rt, rr in by_route.items():
    rr.sort(key=lambda x: x['t'])
    for i, r in enumerate(rr):
        r['gap_prev'] = (r['t'] - rr[i-1]['t']) if i > 0 else np.inf

CLOSE, FAR = 3.5, 6.0  # s: "close-following" vs "isolated" (event window is [-1.0,+2.5]s -> anything <=3.5s prior could tail into this event's pre-window)

for g in ['T64', 'T64B', 'T5', 'T4', 'V282']:
    for typ in ('onset', 'release'):
        R = [r for r in rows if r['group'] == g and r['vb'] in (2, 3) and r['type'] == typ and abs(r['a1'] - r['a0']) >= 0.2]
        close = [r for r in R if r['gap_prev'] <= CLOSE]
        far = [r for r in R if r['gap_prev'] > FAR]
        def stats(RR):
            if len(RR) < 3:
                return None
            ms, as_, wrong = [], [], 0
            for r in RR:
                Dd = abs(r['a1'] - r['a0']); u = r['uid']
                m = tr['model'][u] / Dd; a = signal.sosfiltfilt(sos, tr['la_act'][u]) / Dd
                sm = np.polyfit(np.arange(60) / 100, m[0:60], 1)[0]
                sa = np.polyfit(np.arange(60) / 100, a[0:60], 1)[0]
                ms.append(sm); as_.append(sa); wrong += (sa < -0.2 and sm > -0.05)
            return dict(n=len(RR), model=np.median(ms), achieved=np.median(as_), wrong=wrong / len(RR))
        sc, sf = stats(close), stats(far)
        print(f"{g:5s} {typ:8s} ALL n={len(R):3d}  CLOSE(<= {CLOSE}s) {sc}  FAR(> {FAR}s) {sf}")
