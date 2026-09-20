"""Stage 0: re-derive the release band (do NOT relay the briefed numbers) and keep the INTERCEPT,
which the briefed 5-number summary drops but the margin arithmetic needs.

Model, at a chosen sample index, over torque-route episodes in a speed band:
    cmd = k*aa + Fa*sj + d*sj*toward + c
with sj = sign of the jump, toward = 1 if the jump is toward centre.  Rewritten in the OUTWARD-signed
release variable (s = sign(aa)):
    u_s(t) = (cmd(t) - k*aa(t) - c)*s - off      where off = centring offset = -d/2
    outward release at u_s = +hw ;  inward release at u_s = -hw ;  hw = Fa + d/2
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
from ss_load import load_all, PRE, boot_ci as ss_boot
from solib import OUT, TORQUE_GROUPS

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, TORQUE_GROUPS)
aa_bk = W['aa'][:, PRE]
toward = (sj == -np.sign(aa_bk)).astype(float)


def fit(m, idx):
    X = np.vstack([W['aa'][ar, idx], sj, sj * toward, np.ones(N)]).T[m]
    y = W['cmd'][ar, idx][m]
    c = np.linalg.lstsq(X, y, rcond=None)[0]
    k, Fa, d, c0 = c
    return dict(k=k, away=Fa, toward=Fa + d, hw=Fa + d / 2, off=-d / 2, c=c0,
                resid_rms=float(np.sqrt(np.mean((y - X @ c) ** 2))))


res = {}
rng = np.random.default_rng(3)
for lo, hi in [(2, 8), (8, 15), (2, 5), (5, 8)]:
    m = TQ & (v >= lo) & (v < hi)
    u = np.unique(route[m])
    for when, idx in (('breakaway', np.full(N, PRE - 3)), ('dwell_start', d0)):
        est = fit(m, idx)
        keys = list(est)
        bs = []
        for _ in range(1000):
            pick = rng.choice(u, len(u)); mm = np.zeros(N, bool)
            for c in pick:
                mm |= m & (route == c)
            bs.append([fit(mm, idx)[q] for q in keys])
        bs = np.array(bs)
        res[f'{lo}-{hi}|{when}'] = {q: [float(est[q]), [float(x) for x in np.percentile(bs[:, j], [2.5, 97.5])]]
                                    for j, q in enumerate(keys)}
        res[f'{lo}-{hi}|{when}']['n'] = int(m.sum())
        res[f'{lo}-{hi}|{when}']['n_toward'] = int(toward[m].sum())
        res[f'{lo}-{hi}|{when}']['n_routes'] = int(len(u))

# per-route episode / return counts (for the null-control power question)
res['per_route'] = {}
for rk in sorted(set(route[TQ])):
    for lo, hi in [(2, 8), (2, 15)]:
        m = (route == rk) & (v >= lo) & (v < hi)
        res['per_route'][f'{rk}|{lo}-{hi}'] = dict(n=int(m.sum()), n_return=int(toward[m].sum()),
                                                  n_depart=int((1 - toward)[m].sum()),
                                                  group=str(g[m][0]) if m.sum() else '')
json.dump(res, open(OUT + '/so_band.json', 'w'), indent=1)
for k, x in res.items():
    if k == 'per_route':
        continue
    print(k, {a: ([round(b[0], 5), [round(q, 5) for q in b[1]]] if isinstance(b, list) else b) for a, b in x.items()})
print()
for k, x in res['per_route'].items():
    print(k, x)
