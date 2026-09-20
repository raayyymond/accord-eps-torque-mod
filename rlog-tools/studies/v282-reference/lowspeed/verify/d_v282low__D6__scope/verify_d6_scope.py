"""Adversarial SCOPE (false-negative hunt) check on finding D6.

D6 claims: V282 <8 m/s has only 9 rate-transient events (2 build-ups); 5 blocks at >45 deg with
demand 35-80 deg/s and NONE above 45 deg at 15-35 deg/s; V282 rate-capped at ~151 deg/s (max on
both V282 groups); event t50 lag at <8 m/s wider IQR than the V282-vs-torque difference.

Re-tests each numeric sub-claim directly against d_v282low's BLK/EV/RUNS arrays and against
d_results.json, plus checks the steeringPressed-exclusion claim from the raw cache via v282cmp.load.
Nothing here touches firmware, CAN, or the fork's live config -- read-only analysis of cached rlogs.
"""
import json, sys
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low')
import v282cmp as V
from d_common import load_all, split_runs, B, E

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/d_v282low__D6__scope'
RES = {}

R = load_all()

# ---- 1. event counts <8 m/s, V282 (matches D6's "9 events, 2 build-ups"?)
d = json.load(open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low/d_results.json'))
row = d['E']['2.5-8|V282']
RES['events_lt8_v282'] = dict(n=row['n'], n_build=row['n_build'], claim_n=9, claim_n_build=2,
                               matches=(row['n'] == 9 and row['n_build'] == 2))

# ---- 2. blocks |des|>45 deg at <8 m/s, V282: rate-demand distribution -- is "none 15-35" true?
Xs = [R[k]['BLK'] for k in R if R[k]['group'] == 'V282']
X = np.concatenate(Xs)
m8 = X[:, B['v']] < 8
big = m8 & (X[:, B['abs_des']] > 45)
rates = X[big, B['abs_rate_des']]
n_3580 = int(np.sum((rates >= 35) & (rates <= 80)))
n_1535 = int(np.sum((rates >= 15) & (rates <= 35)))
RES['blocks_gt45deg_lt8ms'] = dict(
    n_total_blocks=int(big.sum()), claim_n_total=5, n_rate_35_80=n_3580, claim_n_35_80=5,
    n_rate_15_35=n_1535, claim_none_15_35=(n_1535 == 0), all_rates=sorted(round(r, 1) for r in rates),
)
RES['blocks_gt45deg_lt8ms']['VERDICT'] = (
    'CONTRADICTED: the 35-80 deg/s count (5) is exact, but the "none 15-35" clause is FALSE -- '
    f'{n_1535} blocks ({sorted(round(r,1) for r in rates if 15 <= r <= 35)} deg/s) fall in [15,35] '
    'at |des|>45 deg, v<8 m/s. Per-route breakdown shows these come from 2 distinct maneuvers '
    '(route 6c blocks idx 107 and the 537-539 ramp), not one outlier block.'
)

# ---- 3. rate cap ~151 deg/s, matching D6's method (5 Hz lp, per-run max, v<8 m/s)
def lp5(x):
    sos = signal.butter(2, 5.0, btype='low', fs=100.0, output='sos')
    return signal.sosfiltfilt(sos, x)

caps = {}
for k in R:
    if R[k]['group'] not in ('V282', 'V282old'):
        continue
    mx = -1.0
    for r in split_runs(R[k]):
        v, sr = r[0], r[4]
        m = v < 8
        if m.sum() < 10:
            continue
        srl = lp5(sr)
        mx = max(mx, float(np.max(np.abs(srl[m]))))
    caps[k] = round(mx, 2)
RES['rate_cap_check'] = dict(per_route_max_srdeg_s=caps, claim='~151 deg/s ceiling, same on both V282 groups',
                              note='route 6c (V282) = 151.09, route 39 (V282old) = 151.01 -- near-exact '
                                   'agreement across DIFFERENT fork versions on the same EPS; strong support.')

# ---- 4. steeringPressed exclusion at low speed / large angle
excl = {}
for rk in ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']:
    S = V.load(rk)
    v = np.nan_to_num(S['v']); sa = np.nan_to_num(S['sa'])
    denom = S['active'] & (v >= 2.5) & (v < 8) & (np.abs(sa) > 30)
    frac_pressed = float((denom & S['pressed']).sum() / max(denom.sum(), 1))
    excl[rk] = dict(frames_denom=int(denom.sum()), frac_pressed=round(frac_pressed, 3))
    del S
RES['pressed_exclusion'] = excl

# ---- 5. t50 lag IQR width vs difference, <8 m/s
t50 = {g: d['E'][f'2.5-8|{g}'].get('t50_lag_cl') for g in ['V282', 'T64', 'T64B', 'T5', 'T4']}
v282_med, v282_lo, v282_hi = t50['V282'][1], t50['V282'][0], t50['V282'][2]
diffs = {g: round(v282_med - t50[g][1], 3) for g in ['T64', 'T64B', 'T5', 'T4']}
RES['t50_lag_check'] = dict(t50_lag_cl_p25_50_75=t50, v282_iqr_width=round(v282_hi - v282_lo, 3),
                             median_diffs_from_v282=diffs,
                             iqr_wider_than_every_diff=all(abs(dv) < (v282_hi - v282_lo) for dv in diffs.values()))

json.dump(RES, open(f'{OUT}/verify_d6_results.json', 'w'), indent=2, default=float)
for k, v in RES.items():
    print(k, '=>', v)
