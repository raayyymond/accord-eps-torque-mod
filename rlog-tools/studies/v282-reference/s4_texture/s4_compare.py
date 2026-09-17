"""s4_texture -- matched comparison of texture metrics, V282 vs torque-mode groups, with two-level bootstrap CIs.

Matching: every block is put in a cell = speed band x angle band x activity band. The effect of group G vs V282 on
metric m is exp( sum_c w_c * [log median_G,c(m) - log median_V282,c(m)] ), w_c = min(n_G,c, n_V,c), cells with
fewer than MIN blocks on either side dropped. So speed, angle and motion amplitude are held equal.
CI: 2000 bootstrap replicates, resampling ROUTES within each group, then BLOCKS within each route (cluster
bootstrap). A 'block-only' CI (routes fixed) is also reported -- the route CI is the honest one.
"""
import sys, json, glob
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
OUTJ = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/s4_compare.json'
SPD = [0, 8, 15, 22, 40]
ANG = [0, 5, 15, 45, 1e9]
ACT = [0, 1.0, 3.0, 10.0, 1e9]
MIN = 3
rng = np.random.default_rng(7)


def load_all():
    R = {}
    for rk, meta in V.ROUTES.items():
        D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
        keys = [str(k) for k in D['keys']]
        rows = D['rows']
        R[rk] = dict(group=meta['group'], cols={k: rows[:, i] for i, k in enumerate(keys)},
                     DJ=D['DJ'], FR=D['FR'], EV=json.loads(str(D['EV'])))
    return R


def cells(c):
    s = np.digitize(c['v'], SPD) - 1
    a = np.digitize(c['ang90'], ANG) - 1
    m = np.digitize(c['act'], ACT) - 1
    return s * 100 + a * 10 + m


def matched_effect(Gb, Vb, metric, sel=None, log=True):
    """Gb, Vb: lists of (cell array, metric array, sel mask). Returns ratio (or difference if log=False)."""
    gc = np.concatenate([x[0] for x in Gb]); gm = np.concatenate([x[1] for x in Gb])
    vc = np.concatenate([x[0] for x in Vb]); vm = np.concatenate([x[1] for x in Vb])
    num = den = 0.0
    for c in np.intersect1d(np.unique(gc), np.unique(vc)):
        a = gm[(gc == c) & np.isfinite(gm)]; b = vm[(vc == c) & np.isfinite(vm)]
        if len(a) < MIN or len(b) < MIN:
            continue
        ma, mb = np.median(a), np.median(b)
        w = min(len(a), len(b))
        if log:
            if ma <= 0 or mb <= 0:
                ma, mb = ma + 1e-3, mb + 1e-3
            num += w * (np.log(ma) - np.log(mb))
        else:
            num += w * (ma - mb)
        den += w
    if den == 0:
        return np.nan, 0
    return (float(np.exp(num / den)) if log else float(num / den)), int(den)


def prep(R, rk, metric, stratum):
    c = R[rk]['cols']
    m = c[metric].copy()
    s = stratum(c)
    return cells(c)[s], m[s]


def effect_with_ci(R, group, metric, stratum, log=True, B=1000):
    Gr = [rk for rk in R if R[rk]['group'] == group]
    Vr = [rk for rk in R if R[rk]['group'] == 'V282']
    Gd = {rk: prep(R, rk, metric, stratum) for rk in Gr}
    Vd = {rk: prep(R, rk, metric, stratum) for rk in Vr}
    est, n = matched_effect(list(Gd.values()), list(Vd.values()), metric, log=log)
    reps, reps_b = [], []
    for _ in range(B):
        for mode, out in (('route', reps), ('block', reps_b)):
            def rs(dd, keys):
                ks = list(rng.choice(keys, len(keys), replace=True)) if mode == 'route' else keys
                o = []
                for k in ks:
                    cc, mm = dd[k]
                    if len(cc) == 0:
                        continue
                    i = rng.integers(0, len(cc), len(cc))
                    o.append((cc[i], mm[i]))
                return o
            g = rs(Gd, Gr); vv = rs(Vd, Vr)
            if not g or not vv:
                continue
            e, _ = matched_effect(g, vv, metric, log=log)
            if np.isfinite(e):
                out.append(e)
    ci = [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))] if len(reps) > 50 else [np.nan, np.nan]
    cib = [float(np.percentile(reps_b, 2.5)), float(np.percentile(reps_b, 97.5))] if len(reps_b) > 50 else [np.nan, np.nan]
    # per-route effects (each torque route vs pooled V282) -- route consistency
    per = {rk: matched_effect([Gd[rk]], list(Vd.values()), metric, log=log)[0] for rk in Gr}
    return dict(est=est, w=n, ci_route=ci, ci_block=cib, per_route=per)


STRATA = {
    'all': lambda c: np.ones(len(c['v']), bool),
    'lt15': lambda c: c['v'] < 15,
    'ge15': lambda c: c['v'] >= 15,
    'lt15_ang15': lambda c: (c['v'] < 15) & (c['ang90'] >= 15),
    'lt15_act3': lambda c: (c['v'] < 15) & (c['act'] >= 3),
    'ge15_straight': lambda c: (c['v'] >= 15) & (c['ang90'] < 5),
}
METRICS = ['hf_ratio', 'hf_rms', 'hf_sa_ratio', 'hf_sa_rms', 'mode_rms', 'conc', 'stall', 'jerk_rough', 'jerk_act',
           'slew_hit', 'mjerk', 'lf_rms']
GROUPS = ['V282old', 'T64', 'T64B', 'T5', 'T4']

if __name__ == '__main__':
    R = load_all()
    res = {}
    for st, fn in STRATA.items():
        res[st] = {}
        for g in GROUPS:
            res[st][g] = {}
            for m in METRICS:
                log = m not in ('stall', 'slew_hit')
                r = effect_with_ci(R, g, m, fn, log=log, B=400)
                res[st][g][m] = r
            print(st, g, ' '.join(f"{m}={res[st][g][m]['est']:.3g}[{res[st][g][m]['ci_route'][0]:.3g},{res[st][g][m]['ci_route'][1]:.3g}]" for m in METRICS), 'w', res[st][g]['hf_ratio']['w'], flush=True)
    json.dump(res, open(OUTJ, 'w'), indent=1)
