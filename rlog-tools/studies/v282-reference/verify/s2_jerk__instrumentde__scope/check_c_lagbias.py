import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
import numpy as np

FS = V.FS

def make_step(dur_s, delay_s, gain, fs=FS, rise_tau=0.35):
    t = np.arange(0, dur_s, 1/fs)
    t0 = dur_s/2
    x = np.tanh((t - t0)/rise_tau)
    y = gain*np.tanh((t - t0 - delay_s)/rise_tau)
    return t, x, y

print("=== event_metrics on REALISTIC event-sized windows (matches s2_extract: pre=1.0s, post=2.5s => 3.5s window) ===")
for delay in (0.0, 0.10, 0.17, 0.25, 0.40):
    for gain_true in (0.95, 1.29):
        t, x, y = make_step(3.5, delay, gain_true)
        S = dict(model=x, la_act=y)
        em = V.event_metrics(S, 0, len(x), ach_key='la_act', maxlag_s=0.8)
        print(f"  delay={delay:.2f} gain_true={gain_true:.2f}  ->  event_metrics lag={em['lag']:.3f} gain={em['gain']:.3f}")

print()
print("=== same, on the ORIGINAL self-test window size (50s, matches v282cmp._self_test) ===")
for delay in (0.0, 0.10, 0.17, 0.25, 0.40):
    t, x, y = make_step(55.0, delay, 0.9)
    S = dict(model=x, la_act=y)
    em = V.event_metrics(S, 500, 5500, ach_key='la_act', maxlag_s=0.8)
    print(f"  delay={delay:.2f}  ->  event_metrics lag={em['lag']:.3f} gain={em['gain']:.3f}")
