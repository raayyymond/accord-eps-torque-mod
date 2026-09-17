"""Part 3: (c) event_metrics lag-bias claim -- is it a universal deterministic bias (as claimed), or
could realistic noise / event geometry sometimes recover the true lag (i.e. is "any stream quoting
event_metrics lag on steps reads ~0" over-general)? Also test with the ACTUAL window geometry used by
s2_extract.py (pre=1.0s, post=2.5s, step at offset NPRE=100 samples into a 350-sample window), not just
the generic tanh-centered-at-500-of-750 used in v282cmp._self_test.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

rng = np.random.default_rng(0)
FS = V.FS

def make_step(true_lag_s, n_pre_s=1.0, n_post_s=2.5, tau=0.15, gain=0.9, noise_rel=0.0, seed=0):
    """model step at t=0 (index n_pre), achieved = gain*model delayed by true_lag_s with a first-order
    lag tau (not an instant tanh -- closer to a real actuator), plus additive noise on 'achieved'."""
    npre, npost = int(n_pre_s * FS), int(n_post_s * FS)
    n = npre + npost
    t = (np.arange(n) - npre) / FS
    x = np.tanh(t / 0.05)  # near-instant model step (desired accel jumps fast)
    # achieved: same shape, delayed + first-order lag, scaled
    td = t - true_lag_s
    y = np.tanh(td / 0.05)
    # apply an exponential smoothing (first order lag) to y to mimic real actuator dynamics
    alpha = 1 - np.exp(-1 / (tau * FS))
    ys = np.zeros_like(y)
    ys[0] = y[0]
    for k in range(1, n):
        ys[k] = ys[k - 1] + alpha * (y[k] - ys[k - 1])
    ys = gain * ys
    rng_l = np.random.default_rng(seed)
    if noise_rel > 0:
        ys = ys + rng_l.standard_normal(n) * noise_rel
    return x, ys, npre

results = []
for true_lag in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
    for noise_rel in (0.0, 0.02, 0.05, 0.10, 0.20):
        ests = []
        for seed in range(8):
            x, y, npre = make_step(true_lag, noise_rel=noise_rel, seed=seed)
            S = dict(model=x, la_act=y)
            em = V.event_metrics(S, 0, len(x), ach_key='la_act', maxlag_s=0.8)
            ests.append(em['lag'])
        results.append(dict(true_lag=true_lag, noise_rel=noise_rel,
                             mean_est=float(np.mean(ests)), std_est=float(np.std(ests)),
                             bias=float(np.mean(ests) - true_lag)))

print(json.dumps(results, indent=1))
with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__instrumentde__power/c_lag_bias_sweep.json', 'w') as f:
    json.dump(results, f, indent=1)

# summarize: at what true_lag / noise does the bias become small (<20% of true lag)?
print("\nSummary: bias as fraction of true_lag (true_lag>0 only)")
for r in results:
    if r['true_lag'] > 0:
        frac = r['bias'] / r['true_lag']
        print(f"  true_lag={r['true_lag']:.2f} noise_rel={r['noise_rel']:.2f}  est={r['mean_est']:.3f} bias_frac={frac:+.2f}")
