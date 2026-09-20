"""reach validation: (a) the vectorised float32 replay reproduces an INDEPENDENT float64 scalar run of the
fork operator for specific candidates, on one route; (b) the baseline candidate (0.015, 3.0) reproduces the
as-flown z where the speed gate is provably inactive over the whole accumulation memory."""
import os, sys
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
D = np.load(OUT + '/reach_rows.npz', allow_pickle=True)
R = list(D['rows']); CANDS = [tuple(c) for c in D['cands']]
GATES = {'g6_10': (6.0, 10.0), 'g8_12': (8.0, 12.0), 'g10_12': (10.0, 12.0), 'flat': (99.0, 99.1)}
F_TODAY = 0.015
RK = '0000006e--6ca3e014fd'   # T64B, 152 episodes, the largest low-speed set

S = V.load(RK); p, fs = params(RK)
v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0); act = S['active']
sR = np.nan_to_num(S['sR'], nan=16.33)
angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
d_ang = np.r_[0.0, np.diff(angdes)]; d_ang[~act] = 0.0; d_ang[np.r_[True, ~act[:-1]]] = 0.0
sched = p.get('AccordFrictionHystBand', '0') == '1'
b_today = band(v, sched)


def scalar_run(f, b, gn):
    """Independent float64 scalar implementation, written from honda_accord_friction_hysteresis directly."""
    v0, v1 = GATES[gn]
    g = np.clip((v - v0) / (v1 - v0), 0.0, 1.0)
    fe = f + g * (F_TODAY - f)
    be = b + g * (b_today - b)
    z = np.zeros(len(d_ang)); zz = 0.0
    for n in range(len(d_ang)):
        if not act[n] or fe[n] <= 0:
            zz = 0.0
        else:
            zz = zz + d_ang[n] * fe[n] / max(be[n], 1e-3)
            zz = min(max(zz, -fe[n]), fe[n])
        z[n] = zz
    return z


rows = [r for r in R if r['route'] == RK]
EPD = np.load(BASE + f'/lowspeed/a_stickslip/out/{RK}_ss.npz', allow_pickle=True)
EP = [e for e in EPD['EP']]
assert len(EP) == len(rows)
print('route', RK, 'episodes', len(rows), 'sched', sched)

for cand in [(0.015, 3.0, 'g8_12'), (0.033, 2.0, 'g8_12'), (0.045, 1.0, 'g6_10'), (0.030, 3.0, 'flat')]:
    ci = CANDS.index(cand)
    z = scalar_run(*cand)
    e0 = []; ebk = []
    for r, e in zip(rows, EP):
        sj = float(e['sjump']); i0 = int(e['i0']); b3 = int(e['bk']) - 3
        e0.append(abs(z[i0] * sj - r['z0'][ci])); ebk.append(abs(z[b3] * sj - r['zbk'][ci]))
    print(f'{cand}  max|dz0| {max(e0):.3e}  max|dzbk| {max(ebk):.3e}')

# baseline where the gate is provably inactive over the memory: v stays < v_full for 3 s before bk
zt = hyst_run(d_ang, F_TODAY, b_today, act)
for gn, vf in (('g6_10', 6.0), ('g8_12', 8.0)):
    ci = CANDS.index((0.015, 3.0, gn))
    ok0, okb, n = [], [], 0
    for r, e in zip(rows, EP):
        i0 = int(e['i0']); b3 = int(e['bk']) - 3; sj = float(e['sjump'])
        if np.max(v[max(i0 - 300, 0):b3 + 1]) < vf:
            n += 1
            ok0.append(abs(zt[i0] * sj - r['z0'][ci])); okb.append(abs(zt[b3] * sj - r['zbk'][ci]))
    print(f'baseline {gn}: n={n} gate-clean episodes, max|dz0| {max(ok0):.3e}  max|dzbk| {max(okb):.3e}')
