"""Breakaway command vs direction: cmd(bk-30ms) = k*aa + Fa*sj + d*sj*toward + c, route-cluster bootstrap.
away-from-centre breakaway level = Fa ; toward-centre = Fa + d ; friction half-width = Fa + d/2 ; centring offset = -d/2 (x sign(aa)).
Also the same fit for V282 (its command is a rate request, reported for shape only)."""
import json, numpy as np
from ss_load import *
EP, W, EX, VAL = load_all(); N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route'); d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
toward = (sj == -np.sign(W['aa'][:, PRE])).astype(float)

def fit(m, idx):
    X = np.vstack([W['aa'][ar, idx], sj, sj * toward, np.ones(N)]).T[m]
    c = np.linalg.lstsq(X, W['cmd'][ar, idx][m], rcond=None)[0]
    return np.array([c[1], c[1] + c[2], c[1] + c[2] / 2, -c[2] / 2, c[0]])   # away, toward, halfwidth, centring offset, k

res = {}; rng = np.random.default_rng(3)
for gname, gm in (('torque', TQ), ('V282', g == 'V282')):
    for lo, hi in [(2, 8), (8, 15)]:
        m = gm & (v >= lo) & (v < hi); u = np.unique(route[m])
        for when, idx in (('breakaway', np.full(N, PRE - 3)), ('dwell_start', d0)):
            est = fit(m, idx); bs = []
            for _ in range(1000):
                pick = rng.choice(u, len(u)); mm = np.zeros(N, bool)
                for c in pick:
                    mm |= m & (route == c)
                bs.append(fit(mm, idx))
            bs = np.array(bs)
            res[f'{gname}|{lo}-{hi}|{when}'] = {nm: [float(est[q]), np.percentile(bs[:, q], [2.5, 97.5]).tolist()]
                                              for q, nm in enumerate(['away', 'toward', 'halfwidth', 'centring_offset', 'k'])}
            res[f'{gname}|{lo}-{hi}|{when}']['n'] = int(m.sum()); res[f'{gname}|{lo}-{hi}|{when}']['n_toward'] = int(toward[m].sum())
json.dump(res, open(OUT + '/ss_centring_fit.json', 'w'), indent=1)
for k, x in res.items():
    print(k, {a: ([round(b[0], 4), [round(q, 4) for q in b[1]]] if isinstance(b, list) else b) for a, b in x.items()})
