"""Stage 2: WHY does V282's F fall back?  Empirical split of F into a level part and a rate part.

V282's F is the same plant feedforward (AccordRatePlantFF=1) but its constant tables differ from
today's, so instead of assuming the tables I fit, PER ROUTE, over the hands-off dwell windows:

    F ~ a * hold_map(angdes, v)  +  b * rate_des  +  c

with rate_des = the 0.10 s-filtered d(angdes)/dt (the fork's own move-term input, window-local) and
hold_map = the shipped saturating map at level=False.  a and b are free, so the fit does not inherit
either table.  Then dF over the 0.5 s after release is split into a*d(hold) + b*d(rate) + residual.

Also: the mean (additive) attribution of dF for the torque group using the extractor's real
sub-channels, so the parts sum to the whole.
-> out/r2_fsplit.json
"""
import numpy as np, json
from rel_lib import *
from sslib import hold_torque

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route'); aa_abs = col('abs_aa')
TQ = np.isin(g, TQG); V2 = g == 'V282'
hold_w, move_w, _ = rebuild_v282_ff(W, EP, P)         # hold_w = shipped map at the route's own level flag

# window-local rate_des (same filter as the extractor, settled over the 150-frame lead-in)
ang = W['angdes']; d = np.diff(ang, axis=1, prepend=ang[:, :1])
a_ = 0.01 / (FF_RATE_RC + 0.01); s = np.zeros(N); rate = np.empty_like(ang)
for j in range(ang.shape[1]):
    s = s + a_ * (d[:, j] / 0.01 - s); rate[:, j] = s
# level=False map, so the fitted a absorbs any level/spring scale
hold0 = np.empty_like(ang)
for i in range(N):
    hold0[i] = hold_torque(ang[i], W['v'][i], False)

R = {}
FIT = {}
for rk in sorted(set(rt)):
    m = rt == rk
    y = W['F'][m].ravel()
    X = np.vstack([hold0[m].ravel(), rate[m].ravel(), np.ones(y.size)]).T
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    pred = X @ b
    FIT[rk] = b
    R[rk] = dict(group=str(g[m][0]), a_hold=round(float(b[0]), 4), b_rate=round(float(b[1]), 6), c=round(float(b[2]), 5),
                 resid_rms=round(float(np.sqrt(np.mean((y - pred) ** 2))), 5), F_rms=round(float(np.sqrt(np.mean(y ** 2))), 5),
                 r2=round(float(1 - np.var(y - pred) / np.var(y)), 3),
                 torque_per_degps=round(float(b[1]), 6))
OUT_J = {'per_route_fit': R}

# ---- split dF after release ----
A = np.array([FIT[r][0] for r in rt])[:, None]
B = np.array([FIT[r][1] for r in rt])[:, None]
Sh = hold0 * sj[:, None] * A; Sr = rate * sj[:, None] * B; SF = W['F'] * sj[:, None]
Sres = SF - Sh - Sr
OUT_J['dF_split'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('V282', V2), ('TORQUE', TQ), ('T64', g == 'T64'), ('T4', g == 'T4')):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 8:
            continue
        row = {}
        for L in (20, 30, 50):
            row[f'+{L*10}ms'] = dict(
                dF=round(float(np.mean((SF[:, PRE + L] - SF[:, PRE])[m])), 5),
                d_holdpart=round(float(np.mean((Sh[:, PRE + L] - Sh[:, PRE])[m])), 5),
                d_ratepart=round(float(np.mean((Sr[:, PRE + L] - Sr[:, PRE])[m])), 5),
                d_resid=round(float(np.mean((Sres[:, PRE + L] - Sres[:, PRE])[m])), 5))
        row['rate_part_level_at_bk'] = round(float(np.mean(Sr[m, PRE])), 5)
        row['rate_gain_torque_per_degps'] = round(float(np.mean(B[m, 0])), 6)
        row['n'] = int(m.sum())
        OUT_J['dF_split'][f'{gname}|{lo}-{hi}'] = row

# ---- additive mean attribution of dF for the torque group with the REAL sub-channels ----
SUB = ['hold_ff', 'move', 'z', 'rl', 'dob']
OUT_J['torque_dF_mean_attribution'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('TORQUE', TQ), ('T64', g == 'T64'), ('T64B', g == 'T64B'), ('T4', g == 'T4'), ('T5', g == 'T5')):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 8:
            continue
        row = {'n': int(m.sum())}
        for L in (30, 50):
            SS = {k: W[k] * sj[:, None] for k in SUB + ['F', 'cmd', 'P', 'I']}
            parts = {k: round(float(np.mean((SS[k][:, PRE + L] - SS[k][:, PRE])[m])), 5) for k in SUB}
            parts['SUM'] = round(sum(parts.values()), 5)
            parts['dF_actual'] = round(float(np.mean((SS['F'][:, PRE + L] - SS['F'][:, PRE])[m])), 5)
            parts['dP'] = round(float(np.mean((SS['P'][:, PRE + L] - SS['P'][:, PRE])[m])), 5)
            parts['dI'] = round(float(np.mean((SS['I'][:, PRE + L] - SS['I'][:, PRE])[m])), 5)
            parts['dcmd'] = round(float(np.mean((SS['cmd'][:, PRE + L] - SS['cmd'][:, PRE])[m])), 5)
            row[f'+{L*10}ms'] = parts
        OUT_J['torque_dF_mean_attribution'][f'{gname}|{lo}-{hi}'] = row

# ---- is the demand itself doing something different?  d(angdes) and d(rate_des) after release ----
OUT_J['demand_after_release'] = {}
Sa = ang * sj[:, None]; Srr = rate * sj[:, None]
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('V282', V2), ('TORQUE', TQ)):
        m = gm & (v >= lo) & (v < hi)
        OUT_J['demand_after_release'][f'{gname}|{lo}-{hi}'] = dict(
            n=int(m.sum()),
            rate_des_at_bk=round(float(np.median(Srr[m, PRE])), 3),
            **{f'd_angdes_+{L*10}ms': round(float(np.median((Sa[:, PRE + L] - Sa[:, PRE])[m])), 3) for L in (30, 50)},
            **{f'd_rate_des_+{L*10}ms': round(float(np.median((Srr[:, PRE + L] - Srr[:, PRE])[m])), 3) for L in (30, 50)})
json.dump(OUT_J, open(OUT + '/r2_fsplit.json', 'w'), indent=1, default=float)
print(json.dumps(OUT_J, indent=1))
