"""Torque vs V282 ratios with a two-sample route-cluster bootstrap (5 torque routes, 3 V282 routes), + centring check."""
import json, numpy as np
from ss_load import *
EP, W, EX, VAL = load_all(); N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route'); kind = col('kind'); aa_abs = col('abs_aa'); dwell = col('dwell_s')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4']); RF = g == 'V282'
A = lambda k, i: W[k][ar, i] * sj
gap = A('angdes', np.full(N, PRE)) - A('aa', np.full(N, PRE))
gap_model = A('ad', np.full(N, PRE)) - A('aa', np.full(N, PRE))        # group-identical demand
catch30 = A('aa', np.full(N, PRE + 30)) - A('aa', np.full(N, PRE))
pk = np.max(np.abs(W['sr'][:, PRE:PRE + 40]), 1)
metrics = dict(dwell_s=dwell, gap_model_deg=gap_model, catch30_deg=catch30, peak_rate_dps=pk)
rng = np.random.default_rng(7); out = {}
for lo, hi in [(2, 8), (8, 15)]:
    for aname, am in (('all', np.ones(N, bool)), ('aa>=5', aa_abs >= 5)):
        mt = TQ & (v >= lo) & (v < hi) & am; mr = RF & (v >= lo) & (v < hi) & am
        ut, ur = np.unique(route[mt]), np.unique(route[mr])
        for nm, x in metrics.items():
            for stat, fn in (('p50', np.median), ('p90', lambda y: np.percentile(y, 90))):
                est = fn(x[mt]) / fn(x[mr]); bs = []
                for _ in range(1000):
                    it = np.concatenate([np.where(mt & (route == c))[0] for c in rng.choice(ut, len(ut))])
                    ir = np.concatenate([np.where(mr & (route == c))[0] for c in rng.choice(ur, len(ur))])
                    if len(it) > 3 and len(ir) > 3:
                        bs.append(fn(x[it]) / fn(x[ir]))
                out[f'{lo}-{hi}|{aname}|{nm}|{stat}'] = dict(torque=float(fn(x[mt])), v282=float(fn(x[mr])), ratio=float(est),
                    ci=np.percentile(bs, [2.5, 97.5]).tolist(), n_t=int(mt.sum()), n_r=int(mr.sum()))
# centring: is the jump toward the centre?  and breakaway fit with a centring-asymmetry term
aa_bk = W['aa'][:, PRE]; toward = sj == -np.sign(aa_bk)
cent = {}
for lo, hi in [(2, 8), (8, 15)]:
    for kd in ['rev', 'cont', 'rest']:
        m = TQ & (v >= lo) & (v < hi) & (kind == kd)
        cent[f'{lo}-{hi}|{kd}'] = dict(n=int(m.sum()), frac_toward_centre=float(np.mean(toward[m])))
    m = TQ & (v >= lo) & (v < hi)
    X = np.vstack([W['aa'][:, PRE - 3], sj, sj * toward, np.ones(N)]).T[m]
    c = np.linalg.lstsq(X, W['cmd'][:, PRE - 3][m], rcond=None)[0]
    X0 = np.vstack([W['aa'][ar, np.maximum(col('w_d0'), 0)], sj, sj * toward, np.ones(N)]).T[m]
    c0 = np.linalg.lstsq(X0, W['cmd'][ar, np.maximum(col('w_d0'), 0)][m], rcond=None)[0]
    cent[f'{lo}-{hi}|fit_bk k,F_away,F_toward_minus_away,c'] = c.tolist()
    cent[f'{lo}-{hi}|fit_start k,F_away,F_toward_minus_away,c'] = c0.tolist()
out['centring'] = cent
json.dump(out, open(OUT + '/ss_ratios.json', 'w'), indent=1)
for k, x in out.items():
    if k != 'centring':
        print(k, {a: (round(b, 3) if isinstance(b, float) else ([round(q, 2) for q in b] if isinstance(b, list) else b)) for a, b in x.items()})
for k, x in cent.items():
    print(k, x if isinstance(x, dict) else np.round(x, 4))
