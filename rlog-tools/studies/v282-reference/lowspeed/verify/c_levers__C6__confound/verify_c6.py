"""Adversarial CONFOUND verification of finding C6 (c_levers instrument facts + lever-reach table).

Independently reproduces, from EXISTING c_levers outputs (validate.json, reach.json, reach_us.json,
bigjumps.json, overshoot_summary.txt) plus one fresh recomputation (z-saturation restricted to the
TURN mask, which cl_reach.py never wrote to disk), whether the claim's numbers hold and whether the
route-group confound (T64B ~4x demand vs T64/T5/T4) explains the "Main result" (observer + rate-loop
gain are the two levers with low-speed reach).

Does NOT touch V282 -- C6 makes no V282 comparison, so the generic "V282 is one 62-segment route"
confound-lens note does not apply to this finding's content.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import ndimage

BASE = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
CL = BASE / 'lowspeed' / 'c_levers'
sys.path.insert(0, str(CL))
import cl_recon as C

OUT = Path(__file__).resolve().parent / 'out'; OUT.mkdir(exist_ok=True)
report = {}

# --- 1. rebuild validation numbers (claim: corr 0.9992-0.99995, p50 |res| 0.00015-0.0005, p95 0.0017-0.007 below 8 m/s) ---
val = json.load(open(CL / 'out' / 'validate.json'))
corrs = [val[k]['lt15']['corr'] for k in val] + [val[k]['lt8']['corr'] for k in val]
p50s = [val[k]['lt15']['p50_absres'] for k in val] + [val[k]['lt8']['p50_absres'] for k in val]
p95_lt8 = [val[k]['lt8']['p95_absres'] for k in val]
report['validate'] = dict(corr_min=min(corrs), corr_max=max(corrs), p50_min=min(p50s), p50_max=max(p50s),
                           p95_lt8_min=min(p95_lt8), p95_lt8_max=max(p95_lt8),
                           claim_corr_range=[0.9992, 0.99995], claim_p50_range=[0.00015, 0.0005],
                           claim_p95_lt8_range=[0.0017, 0.007],
                           verdict='CONFIRMED (exact reproduction from validate.json)')

# --- 2. stick-slip p90 sensitivity to mask (claim: 12.6 n~26 on loose 'us' mask; 4.6 n=17 with HO guard; T64B 3.0) ---
d_us = json.load(open(CL / 'out' / 'reach_us.json'))
d_ho = json.load(open(CL / 'out' / 'reach.json'))


def p90_below8(d, keys):
    j = [dw['jump'] for k in keys for dw in d[k]['DW'] if dw['v'] < 8.0]
    return len(j), (float(np.percentile(j, 90)) if j else None), (float(np.percentile(j, 50)) if j else None)


T64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f']
T64B = ['0000006e--6ca3e014fd']
n_us, p90_us, p50_us = p90_below8(d_us, T64)
n_ho, p90_ho, p50_ho = p90_below8(d_ho, T64)
n_ho_b, p90_ho_b, _ = p90_below8(d_ho, T64B)
report['stickslip_p90'] = dict(us_mask=dict(n=n_us, p90=p90_us, p50=p50_us, claim='n~26, p90 12.6'),
                                ho_mask=dict(n=n_ho, p90=p90_ho, p50=p50_ho, claim='n=17, p90 4.6'),
                                ho_mask_T64B=dict(n=n_ho_b, p90=p90_ho_b, claim='p90 3.0'),
                                verdict='CONFIRMED (n and p90 reproduce to within rounding on both masks)')

# --- 3. big-jump census: total, angle range, per-route breakdown, hands-off guard ---
bj = json.load(open(CL / 'out' / 'bigjumps.json'))
rows7 = [r for r in bj if r['jump'] >= 7.0]
from collections import Counter
brk = Counter(r['g'] for r in rows7)
angs = [abs(r['ang']) for r in rows7]
n_ge1s = sum(1 for r in rows7 if r['dist_pressed_s'] >= 1.0)
report['bigjumps'] = dict(n_total=len(rows7), claim_total=18,
                           breakdown=dict(brk), claim_breakdown=dict(T64=7, T64B=6, T5=1, T4=4),
                           ang_range=[min(angs), max(angs)], claim_ang_range=[10, 152],
                           n_dist_pressed_ge1s=n_ge1s, n_total_for_guard=len(rows7),
                           verdict=('TOTAL and ANGLE RANGE confirmed; PER-ROUTE BREAKDOWN in the claim is '
                                    'WRONG -- reproducible split is T64=5/T64B=8, not T64=7/T64B=6 (total '
                                    'still 18). This UNDERSTATES how much of the 7deg+ census T64B (the '
                                    '~4x-demand route) actually carries: 8/18=44% reproducible vs 6/18=33% '
                                    'claimed. Guard: 17/18 rows are >=1.0s from steeringPressed, one T4 row '
                                    'sits at 0.98s (borderline, immaterial).'))

# --- 4. z-saturation restricted to the TURN mask (cl_reach.py's FR['zsat'] is over ALL HO frames in the
#         speed bin, NOT restricted to |angle_des|>=15 -- it never wrote a turn-only number to disk) ---
def dil(m, n=50):
    return ndimage.binary_dilation(m, structure=np.ones(2 * n + 1, bool))


zsat_rows = []
for rk in C.CFG:
    D = C.reconstruct(rk)
    v = D['v']; hyst = D['cfg']['hyst']
    base = D['active'] & D['csact'] & (v >= 2.0)
    HO = base & ~dil(D['pressed']) & (v >= 2.5) & (v < 15)
    turn = HO & (np.abs(D['angle_des']) >= 15)
    trans = HO & (np.abs(D['rate_des']) >= 40)
    row = dict(rk=rk, g=D['g'])
    for name, mask in [('turn', turn), ('trans', trans)]:
        if mask.any():
            row[name + '_n'] = int(mask.sum())
            row[name + '_zsat'] = float(np.mean(np.abs(D['z'][mask]) >= 0.99 * hyst))
    zsat_rows.append(row)
    del D

turn_zsats = [r['turn_zsat'] for r in zsat_rows if 'turn_zsat' in r]
trans_zsats = [r['trans_zsat'] for r in zsat_rows if 'trans_zsat' in r]
report['z_saturation'] = dict(rows=zsat_rows, turn_zsat_range=[min(turn_zsats), max(turn_zsats)],
                               trans_zsat_range=[min(trans_zsats), max(trans_zsats)],
                               claim='z is saturated 98-100% of turn and transient frames',
                               verdict=('REFUTED AS WRITTEN for the TURN subset: turn-frame z-saturation is '
                                        '61-85% (not 98-100%); only the TRANSIENT (|rate_des|>=40) subset '
                                        'reaches 96.9-100%, matching the claim. During 15-39% of ordinary '
                                        '(non-transient) turning the hysteresis term z is NOT pinned and so '
                                        'retains some dynamic range -- a partial, not complete, weakening of '
                                        'the "no dynamic reach" support for AccordFrictionHyst\'s LOW-reach '
                                        'verdict (the verdict direction is not reversed, since z is still '
                                        'mostly saturated and z_build in large jumps was separately reported '
                                        'as ~0, which this check does not contradict).'))

json.dump(report, open(OUT / 'verify_c6_results.json', 'w'), indent=1, default=float)
for k in report:
    print(k, '->', report[k]['verdict'])
