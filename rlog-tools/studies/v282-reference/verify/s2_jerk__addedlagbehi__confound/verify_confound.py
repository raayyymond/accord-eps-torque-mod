"""Adversarial CONFOUND check on s2_jerk finding 'added-lag-behind-model'.

Re-tests: T64 (and T5/T4) lag more than V282 behind the model in jerk events, using:
  (a) the SAME matching already in s2_common.match() (type x speed-bin exact, log calipers on jerk/step/speed)
      -- this already IS demand-amplitude + speed matching, so we reuse it and additionally report matched
      medians per side to confirm the calipers actually landed close.
  (b) explicit exclusion of the dominant V282 route 0000006c--2bc842dbac (231/275 of V282's hi>=15 events,
      84%) -- does the sign and rough size of the gap survive with ONLY the two minority V282 routes?
  (c) leave-one-route-out already computed in s2_analyze.py is re-derived here per-route (not just min/max)
      so each route's individual pull is visible.
  (d) la_pose as the fully independent achieved signal (la_yaw is unusable -- carState.yawRate==0 on this
      car, confirmed in s2_extract.py comment) -- already stored as pose.slag, re-pulled here explicitly.
  (e) a second, coarser amplitude-matching scheme (speed-bin x step-quintile, not log-caliper NN) as a
      cross-check that the caliper matching in s2_common.match() is not accidentally selecting biased pairs.

Run: python verify_confound.py
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, match, boot_diff, vbin, VBINS

OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__addedlagbehi__confound'
DOM_ROUTE = '0000006c--2bc842dbac'

rows, tr = load_all()
ALL_V282 = [r for r in rows if r['group'] == 'V282']
V282_NODOM = [r for r in ALL_V282 if r['route'] != DOM_ROUTE]
print(f'V282 total events {len(ALL_V282)}, excluding {DOM_ROUTE}: {len(V282_NODOM)} '
      f'(from routes {sorted(set(r["route"] for r in V282_NODOM))})')

STRATA = {'hi>=15': [2, 3], 'v8-15': [1]}
METRICS = ['act.slag', 'pose.slag']


def report(name, ref, tq_group):
    TQ = [r for r in rows if r['group'] in tq_group]
    pairs = match(ref, TQ)
    out = {}
    for sn, vbs in STRATA.items():
        P = [p for p in pairs if p[1]['vb'] in vbs]
        d = {'n_pairs': len(P)}
        if len(P) < 4:
            out[sn] = d
            continue
        # matched-pair amplitude sanity: median step/jerk/v on each side should be close
        d['match_check_ref_v_tq'] = {
            'jerk': (float(np.median([p[0]['jerk'] for p in P])), float(np.median([p[1]['jerk'] for p in P]))),
            'step': (float(np.median([p[0]['step'] for p in P])), float(np.median([p[1]['step'] for p in P]))),
            'v': (float(np.median([p[0]['v'] for p in P])), float(np.median([p[1]['v'] for p in P]))),
        }
        for m in METRICS:
            b = boot_diff(P, m)
            # per-route pull (not just min/max) -- both sides
            per_route = {}
            for side, tag in ((0, 'ref'), (1, 'tq')):
                for rt in sorted(set(p[side]['route'] for p in P)):
                    PP = [p for p in P if p[side]['route'] != rt]
                    if len(PP) < 3:
                        continue
                    dd = [p[1].get(m, np.nan) - p[0].get(m, np.nan) for p in PP]
                    per_route[f'excl_{tag}:{rt}'] = round(float(np.nanmedian(dd)), 3)
            d[m] = dict(ref=float(np.nanmedian([p[0].get(m, np.nan) for p in P])),
                         tq=float(np.nanmedian([p[1].get(m, np.nan) for p in P])),
                         diff=b['med'], ci_ev=[round(x, 3) for x in b['ci_ev']], ci_rt=[round(x, 3) for x in b['ci_rt']],
                         n=b['n'], per_route_loro=per_route)
        out[sn] = d
    print(f'\n##### {name}')
    for sn, d in out.items():
        print(f'  -- {sn}: n_pairs {d.get("n_pairs")}', d.get('match_check_ref_v_tq'))
        for m in METRICS:
            if m not in d:
                continue
            x = d[m]
            print(f'     {m:12s} ref {x["ref"]:+.3f} tq {x["tq"]:+.3f} diff {x["diff"]:+.3f} '
                  f'evCI {x["ci_ev"]} rtCI {x["ci_rt"]} n={x["n"]}')
            print(f'        per-route LORO: {x["per_route_loro"]}')
    return out


results = {}
print('=' * 70)
print('PART A: baseline (full V282, as in the finding) -- sanity reproduction')
results['A_full_V282_vs_T64'] = report('A: full V282 vs T64', ALL_V282, ['T64'])

print('=' * 70)
print('PART B: V282 WITHOUT the dominant route 0000006c--2bc842dbac (231/275 = 84% of hi>=15 V282 events)')
results['B_V282_nodom_vs_T64'] = report('B: V282 minus dominant route vs T64', V282_NODOM, ['T64'])
results['B_V282_nodom_vs_T64B'] = report('B: V282 minus dominant route vs T64+T64B', V282_NODOM, ['T64', 'T64B'])
results['B_V282_nodom_vs_T5'] = report('B: V282 minus dominant route vs T5', V282_NODOM, ['T5'])
results['B_V282_nodom_vs_T4'] = report('B: V282 minus dominant route vs T4', V282_NODOM, ['T4'])

# ---------- PART C: coarse speed-bin x step-quintile matching (independent of s2_common.match's log-caliper NN)
print('=' * 70)
print('PART C: coarse speed-bin x step-tercile stratified comparison (no NN matching at all)')


def stratified(name, ref, tq_group):
    TQ = [r for r in rows if r['group'] in tq_group]
    out = {}
    for sn, vbs in STRATA.items():
        Rr = [r for r in ref if r['vb'] in vbs and r.get('step', 0) >= 0.2]
        Tt = [r for r in TQ if r['vb'] in vbs and r.get('step', 0) >= 0.2]
        if len(Rr) < 6 or len(Tt) < 6:
            continue
        steps_all = sorted([r['step'] for r in Rr] + [r['step'] for r in Tt])
        terc = [steps_all[len(steps_all) // 3], steps_all[2 * len(steps_all) // 3]]

        def tercile(s):
            return 0 if s < terc[0] else (1 if s < terc[1] else 2)

        for tc in (0, 1, 2):
            Rc = [r for r in Rr if tercile(r['step']) == tc]
            Tc = [r for r in Tt if tercile(r['step']) == tc]
            if len(Rc) < 3 or len(Tc) < 3:
                continue
            for m in METRICS:
                rv = np.array([r.get(m, np.nan) for r in Rc], float)
                tv = np.array([r.get(m, np.nan) for r in Tc], float)
                rv, tv = rv[np.isfinite(rv)], tv[np.isfinite(tv)]
                if len(rv) < 3 or len(tv) < 3:
                    continue
                key = f'{sn}|step_tercile{tc}|{m}'
                out[key] = dict(n_ref=len(rv), n_tq=len(tv), ref_med=round(float(np.median(rv)), 3),
                                 tq_med=round(float(np.median(tv)), 3), diff=round(float(np.median(tv) - np.median(rv)), 3),
                                 ref_step_med=round(float(np.median([r['step'] for r in Rc])), 3),
                                 tq_step_med=round(float(np.median([r['step'] for r in Tc])), 3),
                                 ref_v_med=round(float(np.median([r['v'] for r in Rc])), 1),
                                 tq_v_med=round(float(np.median([r['v'] for r in Tc])), 1))
    print(f'\n##### {name} (unmatched, stratified by speed-bin x step-tercile, medians only, no CI)')
    for k, v in out.items():
        print(f'  {k:35s} {v}')
    return out


results['C_stratified_full_vs_T64'] = stratified('C: full V282 vs T64', ALL_V282, ['T64'])
results['C_stratified_nodom_vs_T64'] = stratified('C: V282-nodom vs T64', V282_NODOM, ['T64'])

json.dump(results, open(f'{OUTDIR}/verify_results.json', 'w'), indent=1, default=float)
print('\nWrote', f'{OUTDIR}/verify_results.json')
