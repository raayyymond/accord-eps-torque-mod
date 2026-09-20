"""Adversarial verification of D6 (POWER lens): is the "V282 reference is thin below 8 m/s" null
underpowered / are its specific magnitude claims reproducible from the underlying data?

Checks, independently re-derived from d_v282low's own npz cache (never from d_results.json / d_matched.json text):
  1. Event counts (n=9, 2 build-ups) below 8 m/s for V282 -- re-derive from EV array.
  2. The 5-block cell at 35-80 deg/s, >=45 deg demand -- re-derive from BLK array with the SAME n>=5 filter
     d_matched.py uses, AND without that filter, to check whether "none above 45 deg at 15-35 deg/s" is
     literally true or is an artifact of the reporting threshold.
  3. t50_lag_cl comparison V282 (n=9) vs each torque group below 8 m/s -- Mann-Whitney U (can we reject
     the null despite small n?) and a minimum-detectable-effect-size calculation (rule-of-thumb n=16/d^2
     per group, standard two-sample power approx) to size how big a true difference could hide undetected.
  4. The "~151 deg/s ceiling, max on both V282 groups" claim -- re-derive the max measured steering rate
     three ways (event-detected peak_rate_meas within EV; raw |sr| over usable <15 m/s runs; raw |sr|
     restricted to <8 m/s) for V282 and V282old separately, and check whether they actually match.
"""
import numpy as np
import sys, json, math
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low')
from d_common import *
from scipy import stats

R = load_all()
OUT = {}

# ---- 1. event counts
EV_V282 = np.concatenate([R[k]['EV'] for k in R if R[k]['group'] == 'V282' and len(R[k]['EV'])])
m8 = (EV_V282[:, E['v']] >= 2.5) & (EV_V282[:, E['v']] < 8)
X = EV_V282[m8]
OUT['1_event_count'] = dict(n=int(len(X)), n_build=int(X[:, E['build']].sum()))

# ---- 2. the 5-block / 45deg / 15-35 rate-bin claim, WITH and WITHOUT the n>=5 reporting filter
RB = [(0, 5), (5, 15), (15, 35), (35, 80), (80, 400)]
per = [R[k]['BLK'] for k in R if R[k]['group'] == 'V282']
blk_check = {}
for rb in RB:
    Xs = []
    for Xb in per:
        mm = ((Xb[:, B['v']] >= 2.5) & (Xb[:, B['v']] < 8) & (Xb[:, B['abs_rate_des']] >= rb[0])
              & (Xb[:, B['abs_rate_des']] < rb[1]) & (Xb[:, B['abs_des']] >= 45))
        Xs.append(Xb[mm])
    n = sum(len(x) for x in Xs)
    blk_check[f'{rb[0]}-{rb[1]}'] = n
OUT['2_blocks_ge45deg_by_rate_bin'] = blk_check
OUT['2_verdict'] = ('WRONG as literally stated: 15-35 deg/s x >=45 deg has n=3 blocks, not zero. '
                     'd_matched.py drops it only because its own n>=5 reporting threshold is not met. '
                     '"none" conflates "below the reporting threshold" with "no data exists".')

# ---- 3. t50_lag_cl power check, V282 (<8 m/s) vs each torque group (<8 m/s)
v282_lag = X[:, E['t50_lag_cl']]
lag_check = {}
for g in ['T4', 'T5', 'T64', 'T64B']:
    EVg = np.concatenate([R[k]['EV'] for k in R if R[k]['group'] == g and len(R[k]['EV'])])
    mm = (EVg[:, E['v']] >= 2.5) & (EVg[:, E['v']] < 8)
    lag = EVg[mm, E['t50_lag_cl']]
    lag = lag[np.isfinite(lag)]
    v282f = v282_lag[np.isfinite(v282_lag)]
    if len(lag) < 3:
        lag_check[g] = dict(n=int(len(lag)), note='too few for a test')
        continue
    u, p = stats.mannwhitneyu(v282f, lag, alternative='two-sided')
    n1, n2 = len(v282f), len(lag)
    sd1, sd2 = np.std(v282f, ddof=1), np.std(lag, ddof=1)
    sp = math.sqrt(((n1 - 1) * sd1 ** 2 + (n2 - 1) * sd2 ** 2) / (n1 + n2 - 2))
    diff = float(np.mean(v282f) - np.mean(lag))
    d_obs = diff / sp if sp > 0 else float('nan')
    nh = 2 / (1 / n1 + 1 / n2)
    d_min80 = math.sqrt(16 / nh)  # rule-of-thumb min detectable Cohen's d, alpha=.05, power=.80, two-sample equal-ish n
    lag_check[g] = dict(n=int(n2), mwu_p=float(p), mean_diff_s=diff, cohens_d_observed=float(d_obs),
                         min_detectable_d_80pow=float(d_min80), min_detectable_diff_s=float(d_min80 * sp))
OUT['3_t50_lag_power'] = lag_check
OUT['3_verdict'] = ('CONFIRMS and STRENGTHENS the null: min detectable effect at these n is d~1.3-1.5 '
                     '(alpha .05, 80% power, rule-of-thumb), while the observed effect vs T64B is only '
                     'd~0.71 (~0.38s mean diff). A true difference of that size would routinely fail to '
                     'reach significance at n=9 vs n=7 -- the "cannot be compared" call is well-founded, '
                     'if anything understated as a caution.')

# ---- 4. the 151 deg/s ceiling claim
rate_check = {}
for g in ['V282', 'V282old']:
    EVg = np.concatenate([R[k]['EV'] for k in R if R[k]['group'] == g and len(R[k]['EV'])])
    max_event_peak_all15 = float(EVg[:, E['peak_rate_meas']].max())
    runs = sum([split_runs(R[k]) for k in R if R[k]['group'] == g], [])
    max_raw_all15 = max(float(np.max(np.abs(r[4]))) for r in runs) if runs else None
    max_raw_lt8 = 0.0
    for r in runs:
        v, sr = r[0], r[4]
        mm = v < 8
        if mm.sum():
            max_raw_lt8 = max(max_raw_lt8, float(np.max(np.abs(sr[mm]))))
    rate_check[g] = dict(max_event_peak_rate_meas_lt15=max_event_peak_all15,
                          max_raw_abs_sr_lt15=max_raw_all15, max_raw_abs_sr_lt8=max_raw_lt8)
OUT['4_rate_ceiling_check'] = rate_check
OUT['4_verdict'] = ('WRONG as stated. The two V282 groups do NOT share a ~151 deg/s max: V282old reaches '
                     '151.0 (event-detected peak) / 154.0 (raw, <15 m/s); V282 only reaches 108.2 (event) '
                     'and its own RAW max is 159.8 deg/s -- HIGHER than 151, not capped at it. 151 is the '
                     'V282old event-detected max alone, not a value both groups hit. The "same-ceiling" '
                     'premise behind the firmware-rate-cap BELIEF is not reproducible from this data; the '
                     'controller-saturation flag (cs_sat) is also 0 in every cell, which does not support a '
                     'servo ceiling being hit either.')

json.dump(OUT, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/d_v282low__D6__power/results.json', 'w'), indent=2, default=float)
print(json.dumps(OUT, indent=2, default=float))
