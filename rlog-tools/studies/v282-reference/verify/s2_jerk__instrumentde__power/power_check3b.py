"""Part 3b: reproduce the finding's OWN quoted synthetic-tanh-step test for event_metrics lag bias
exactly (no extra first-order lag layered on -- that was my own addition in power_check3.py and
changed the picture). Sweep window length and step position within the window (this is the actual
lever behind "shrinking overlap" bias) to find where the bias is severe vs mild -- i.e. is the
finding's own quoted numbers reproducible, and how general is "any stream quoting event_metrics lag
on steps reads ~0"?
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

FS = V.FS

def tanh_step(true_lag_s, win_s, step_frac=0.33, gain=0.9, steep=3.0):
    """A single tanh transition inside a window of length win_s, with the (undelayed) step centered at
    step_frac of the window. This matches 'a step in the middle-ish of an event window', which is what
    an actual jerk-event pre/post window looks like."""
    n = int(win_s * FS)
    t = (np.arange(n) - int(step_frac * n)) / FS
    x = np.tanh(steep * t)
    y = gain * np.tanh(steep * (t - true_lag_s))
    return x, y

report = []
# reproduce the exact quoted numbers first: default event_metrics maxlag 0.8s, what window did the
# claim likely use? Try a few plausible window lengths / step positions bracketing typical event use.
for win_s in (2.0, 3.5, 4.5, 6.0):
    for step_frac in (0.2, 0.33, 0.5):
        row = dict(win_s=win_s, step_frac=step_frac, cases=[])
        for true_lag in (0.10, 0.25, 0.40):
            x, y = tanh_step(true_lag, win_s, step_frac)
            S = dict(model=x, la_act=y)
            em = V.event_metrics(S, 0, len(x), ach_key='la_act', maxlag_s=0.8)
            row['cases'].append(dict(true_lag=true_lag, est_lag=round(em['lag'], 3), gain=round(em['gain'], 3)))
        report.append(row)

print(json.dumps(report, indent=1))
with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__power/c_lag_bias_window_sweep.json', 'w') as f:
    json.dump(report, f, indent=1)
