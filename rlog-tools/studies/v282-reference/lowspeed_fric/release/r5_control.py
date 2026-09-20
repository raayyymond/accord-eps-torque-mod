"""Stage 5: positive control on the rate-FF gain estimator before its V282 number is allowed to count.

The claim under test is "V282's feedforward carried a much larger DESIRED-RATE (lead) term, and that
is the fall-back torque mode lacks".  The estimator is a delta-regression:

    dF(300 ms after breakaway)  ~  gh * d(hold_map)  +  gr * d(rate_des)  +  c

On the TORQUE routes the true gr is known -- the extractor's `move` channel is
AccordFFRateGain / G(v) per deg/s, and the `hold_ff` channel is the map itself (gh == 1).  So the
estimator must recover them there before its V282 answer is used.  Second control: run the same
regression on the torque group's `move` channel alone as the dependent variable.
-> out/r5_control.json
"""
import numpy as np, json
from rel_lib import *
from sslib import hold_torque

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route')
TQ = np.isin(g, TQG); V2 = g == 'V282'
ang = W['angdes']
d = np.diff(ang, axis=1, prepend=ang[:, :1])
a_ = 0.01 / (FF_RATE_RC + 0.01); s = np.zeros(N); rate = np.empty_like(ang)
for j in range(ang.shape[1]):
    s = s + a_ * (d[:, j] / 0.01 - s); rate[:, j] = s
hold0 = np.empty_like(ang)
for i in range(N):
    hold0[i] = hold_torque(ang[i], W['v'][i], False)
S = lambda x: x * sj[:, None]
R = {}


def fit(dep, m, L=30):
    y = (S(dep)[:, PRE + L] - S(dep)[:, PRE])[m]
    X = np.vstack([(S(hold0)[:, PRE + L] - S(hold0)[:, PRE])[m],
                   (S(rate)[:, PRE + L] - S(rate)[:, PRE])[m], np.ones(m.sum())]).T
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    # route-cluster bootstrap
    u = np.unique(rt[m]); rng = np.random.default_rng(3); ii = np.where(m)[0]; bs = []
    for _ in range(600):
        pick = rng.choice(u, len(u)); jj = np.concatenate([ii[rt[m] == c] for c in pick])
        mm = np.zeros(N, bool); mm[jj] = True
        yy = (S(dep)[:, PRE + L] - S(dep)[:, PRE])[mm]
        XX = np.vstack([(S(hold0)[:, PRE + L] - S(hold0)[:, PRE])[mm],
                        (S(rate)[:, PRE + L] - S(rate)[:, PRE])[mm], np.ones(mm.sum())]).T
        bs.append(np.linalg.lstsq(XX, yy, rcond=None)[0])
    bs = np.array(bs)
    return dict(gh=round(float(b[0]), 3), gr=round(float(b[1]), 6),
                gh_ci=[round(x, 3) for x in np.percentile(bs[:, 0], [2.5, 97.5])],
                gr_ci=[round(x, 6) for x in np.percentile(bs[:, 1], [2.5, 97.5])],
                r2=round(float(1 - np.var(y - X @ b) / np.var(y)), 3), n=int(m.sum()))


for lo, hi in [(2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi)
    truth_gr = float(np.mean(0.5 / np.interp(v[m], G_BP, G_V)))
    R[f'control_torque_move_only|{lo}-{hi}'] = dict(**fit(W['move'], m), truth_gr=round(truth_gr, 6),
                                                    truth_gh=0.0, verdict_note='dependent = the move channel alone')
    R[f'control_torque_holdmove|{lo}-{hi}'] = dict(**fit(W['hold_ff'] + W['move'], m), truth_gr=round(truth_gr, 6),
                                                   truth_gh=1.0, verdict_note='dependent = hold+move (the plant FF)')
    R[f'torque_F|{lo}-{hi}'] = dict(**fit(W['F'], m), truth_gr=round(truth_gr, 6), truth_gh=1.0,
                                    verdict_note='dependent = the whole F (adds z, rl, dob -- unmodelled)')
    R[f'V282_F|{lo}-{hi}'] = dict(**fit(W['F'], V2 & (v >= lo) & (v < hi)), truth_gr=None, truth_gh=None,
                                  verdict_note='the claim: gr much larger than the torque routes')
json.dump(R, open(OUT + '/r5_control.json', 'w'), indent=1, default=float)
print(json.dumps(R, indent=1))
