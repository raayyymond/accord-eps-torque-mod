"""s4_texture extra: (a) matched event texture (2-3 Hz wheel-rate rms after desired-jerk events) binned by speed and
by the transient's own peak steering rate; (b) T64B vs T64 and T4/T5 vs T64 matched block effects (reference = T64)."""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import v282cmp as V
import s4_compare as C
rng = np.random.default_rng(3)
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture'
R = C.load_all()
out = {}
# (a) events
TOR = ['T64', 'T64B', 'T5', 'T4']
def evs(groups, kind='jerk04'):
    return [dict(e, route=rk, group=R[rk]['group']) for rk in R if R[rk]['group'] in groups for e in R[rk]['EV'] if e['kind'] == kind]
EB = [(0, 15, 0, 10), (0, 15, 10, 40), (0, 15, 40, 1e9), (15, 40, 0, 10), (15, 40, 10, 1e9)]
for grp in [['V282'], ['V282old'], ['T64'], TOR]:
    nm = '+'.join(grp)
    for s0, s1, r0, r1 in EB:
        E = [e for e in evs(grp) if s0 <= e['v'] < s1 and r0 <= e['rate_max'] < r1]
        if len(E) == 0:
            continue
        md = np.array([e['md_post'] for e in E]); rk = np.array([e['route'] for e in E])
        rel = md / np.array([e['rate_max'] for e in E])
        reps = []
        ur = np.unique(rk)
        for _ in range(2000):
            pick = rng.choice(ur, len(ur))
            xs = np.concatenate([rng.choice(md[rk == r], (rk == r).sum()) for r in pick]); reps.append(np.median(xs))
        o = dict(n=len(E), routes=len(ur), md_post_med=float(np.median(md)), ci=[float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))],
                 rel_med=float(np.median(rel)), ratemax_med=float(np.median([e['rate_max'] for e in E])), angmax_med=float(np.median([e['ang_max'] for e in E])),
                 jerk_rough_pose_med=float(np.median([e['jerk_rough_pose'] for e in E])), gain_med=float(np.nanmedian([e['gain'] for e in E])))
        out.setdefault('events', {}).setdefault(nm, {})[f'v{s0}-{s1}_rate{r0}-{int(min(r1,999))}'] = o
        print(nm, f'v{s0}-{s1} rate{r0}-{r1}', {k: (np.round(v, 3) if not isinstance(v, list) else np.round(v, 2)) for k, v in o.items()})
# (b) T64 as reference
def eff(g, ref, metric, fn, log=True, B=400):
    Gr = [rk for rk in R if R[rk]['group'] == g]; Vr = [rk for rk in R if R[rk]['group'] == ref]
    Gd = {rk: C.prep(R, rk, metric, fn) for rk in Gr}; Vd = {rk: C.prep(R, rk, metric, fn) for rk in Vr}
    est, w = C.matched_effect(list(Gd.values()), list(Vd.values()), metric, log=log)
    reps = []
    for _ in range(B):
        def rs(dd):
            o = []
            for k in dd:  # blocks only (T64B/T5/T4 are single routes)
                cc, mm = dd[k]; i = rng.integers(0, len(cc), len(cc)); o.append((cc[i], mm[i]))
            return o
        e, _ = C.matched_effect(rs(Gd), rs(Vd), metric, log=log)
        if np.isfinite(e): reps.append(e)
    return dict(est=est, w=w, ci_block=[float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))])
for g in ['T64B', 'T5', 'T4']:
    for st in ['all', 'lt15', 'ge15']:
        for m in ['mode_rms', 'hf_ratio', 'hf_sa_rms']:
            r = eff(g, 'T64', m, C.STRATA[st])
            out.setdefault('vsT64', {}).setdefault(g, {}).setdefault(st, {})[m] = r
            print('vsT64', g, st, m, np.round(r['est'], 2), np.round(r['ci_block'], 2), r['w'])
json.dump(out, open(f'{HERE}/s4_extra.json', 'w'), indent=1)
