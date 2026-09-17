"""s2_jerk stage 2: match V282 vs torque-mode events (type x speed bin, NN on jerk/step/speed), paired differences with
event bootstrap, torque-route cluster bootstrap, and leave-one-route-out (both sides) sensitivity. -> _out/s2_results.json"""
import json, numpy as np, warnings
warnings.filterwarnings('ignore')
from s2_common import *
rows, tr = load_all()
for r in rows:
    for k in ('act.settle', 'pose.settle'):
        if k in r and not np.isfinite(r[k]): r[k] = 2.5       # never settled inside the window -> cap at window end
    if 'act.settle' in r: r['act.settled'] = float(r['act.settle'] < 2.5)
    r['sr_ring_ratio'] = r['sr_ring_post'] / max(r['sr_ring_pre'], 1e-6)
REF = [r for r in rows if r['group'] == 'V282']
METRICS = ['act.slag', 'pose.slag', 'act.sgain', 'pose.sgain', 'act.scorr', 'act.d10', 'act.d50', 'act.d90', 'pose.d50',
           'act.bias_0_20', 'act.bias_20_60', 'act.bias_60_150', 'act.bias_150_300',
           'act.err_0_20', 'act.err_20_60', 'act.err_60_150', 'act.err_150_300',
           'act.step_over', 'pose.step_over', 'act.settle', 'act.settled',
           'la_act.gain', 'la_pose.gain', 'la_act.peak_ratio', 'la_pose.peak_ratio',
           'la_act.jerk_rough', 'la_pose.jerk_rough', 'la_act.jerk_des_rms', 'la_act.rms_err',
           'sr_ring_pre', 'sr_ring_post', 'sr_ring_ratio', 'hf_2_10', 'sa_pk_rate', 'act.ring_post']
STRATA = {'lo<15': [0, 1], 'hi>=15': [2, 3], 'v3-8': [0], 'v8-15': [1], 'v15-22': [2], 'v22+': [3]}
res = {}
for tqg in (['T64'], ['T64', 'T64B'], ['T5'], ['T4']):
    name = '+'.join(tqg); TQ = [r for r in rows if r['group'] in tqg]
    pairs_all = match(REF, TQ)
    res[name] = {'n_tq_events': len(TQ), 'n_matched': len(pairs_all)}
    for sn, vbs in STRATA.items():
        P = [p for p in pairs_all if p[1]['vb'] in vbs]
        from collections import Counter
        d = dict(n_pairs=len(P), n_tq=sum(r['vb'] in vbs for r in TQ), n_ref=sum(r['vb'] in vbs for r in REF),
                 types=dict(Counter(p[1]['type'] for p in P)),
                 match_check=dict(jerk=[float(np.median([p[0]['jerk'] for p in P])) if P else None, float(np.median([p[1]['jerk'] for p in P])) if P else None],
                                  step=[float(np.median([p[0]['step'] for p in P])) if P else None, float(np.median([p[1]['step'] for p in P])) if P else None],
                                  v=[float(np.median([p[0]['v'] for p in P])) if P else None, float(np.median([p[1]['v'] for p in P])) if P else None]))
        for m in METRICS:
            b = boot_diff(P, m)
            ref_med = float(np.nanmedian([p[0].get(m, np.nan) for p in P])) if P else np.nan
            tq_med = float(np.nanmedian([p[1].get(m, np.nan) for p in P])) if P else np.nan
            # leave-one-route-out on BOTH sides
            lo = []
            for rt in set([p[0]['route'] for p in P] + [p[1]['route'] for p in P]):
                PP = [p for p in P if p[0]['route'] != rt and p[1]['route'] != rt]
                dd = [p[1].get(m, np.nan) - p[0].get(m, np.nan) for p in PP]
                if len(PP) >= 3: lo.append(float(np.nanmedian(dd)))
            d[m] = dict(ref=ref_med, tq=tq_med, diff=b['med'], ci_ev=b['ci_ev'], ci_rt=b['ci_rt'], n=b['n'],
                        loro=(min(lo), max(lo)) if lo else None)
        res[name][sn] = d
json.dump(res, open(f'{OUT}/s2_results.json', 'w'), indent=1, default=float)
for name in res:
    print(f"\n##### V282 vs {name}: tq events {res[name]['n_tq_events']} matched {res[name]['n_matched']}")
    for sn in ('lo<15', 'hi>=15', 'v8-15', 'v15-22', 'v22+'):
        d = res[name][sn]
        print(f"  -- {sn}: pairs {d['n_pairs']} (tq {d['n_tq']}, ref {d['n_ref']}) types {d['types']} match j/step/v {d['match_check']}")
        if d['n_pairs'] < 4: continue
        for m in METRICS:
            x = d[m]
            if x['n'] < 3: continue
            print(f"     {m:20s} ref {x['ref']:7.3f} tq {x['tq']:7.3f}  d {x['diff']:+7.3f} evCI [{x['ci_ev'][0]:+.3f},{x['ci_ev'][1]:+.3f}] rtCI [{x['ci_rt'][0]:+.3f},{x['ci_rt'][1]:+.3f}] loro {x['loro'] and tuple(round(y,3) for y in x['loro'])} n={x['n']}")
