"""Adversarial POWER check on finding s2_jerk/instrument-defects-la-yaw-zero-event-metrics-lag-biased.

Runs one route at a time (RAM discipline). Does NOT edit v282cmp.py.
"""
import sys, json, gc
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__power'

results = {}

# ---------- (a) la_yaw all-zero: check across ALL routes, count samples ----------
yaw_report = {}
for rk in V.ROUTES:
    try:
        S = V.load(rk)
    except FileNotFoundError:
        continue
    u = V.usable(S)
    yy = np.nan_to_num(S['la_yaw'][u])
    n = len(yy)
    nz = int(np.sum(yy != 0))
    yaw_report[rk] = dict(n=n, nonzero=nz, maxabs=float(np.max(np.abs(yy))) if n else None)
    del S, yy
    gc.collect()
results['a_la_yaw'] = yaw_report
print('(a) la_yaw nonzero census:', json.dumps(yaw_report, indent=1))

# total sample count -> power to detect a rate signal at some minimum resolution
total_n = sum(v['n'] for v in yaw_report.values())
print(f'(a) total usable samples across {len(yaw_report)} routes: {total_n}')
