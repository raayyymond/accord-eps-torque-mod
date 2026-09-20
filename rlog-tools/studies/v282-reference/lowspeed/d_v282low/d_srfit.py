"""Empirical steering ratio vs |angle| from the car itself (all groups, same car): SRe = (sa - aoff) / deg(-kappa*L*(1-sf v^2)),
kappa = livePose yaw rate / v (sign-matched to the model convention, verified -1 vs steeringAngleDeg). Steady frames only:
|steer rate| < 5 deg/s (1 Hz lp), 4 <= v < 15, |sa - aoff| >= 3 deg."""
import sys, json; sys.path.insert(0,'../..')
import v282cmp as V, numpy as np
from d_extract import fillnan, SF, L, HERE, lp
EDG = np.array([3, 6, 10, 20, 35, 60, 90, 130, 180, 270, 400])
out = {}
for rk, m in V.ROUTES.items():
    S = V.load(rk)
    v = fillnan(S['v']); sa = fillnan(S['sa']); aoff = fillnan(S['aoff']); wz = fillnan(S['la_pose']) / np.maximum(v, .1) ** 2
    sr1 = lp(fillnan(S['sr']), 1.0, 2); wz = lp(wz, 1.0, 2)
    u = V.usable(S, 4, 15) & (np.abs(sr1) < 5) & (np.abs(sa - aoff) >= 3)
    den = np.degrees(-wz * L * (1 - SF * v ** 2))
    r = (sa - aoff)[u] / den[u]
    b = np.digitize(np.abs(sa - aoff)[u], EDG) - 1
    out[rk] = [[float(np.median(r[b == k])) if (b == k).sum() > 50 else None, int((b == k).sum())] for k in range(len(EDG) - 1)]
    print(m['group'], rk, [None if x[0] is None else round(x[0], 2) for x in out[rk]])
    del S
json.dump(dict(edges=EDG.tolist(), sr=out), open(f'{HERE}/data/srfit.json', 'w'), indent=1)
