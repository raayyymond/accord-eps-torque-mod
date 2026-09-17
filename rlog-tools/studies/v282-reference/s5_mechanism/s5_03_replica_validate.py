"""s5_03: OPEN-LOOP validation of the controller replica (s5ctl.Ctl) against the LOGGED P, I, F, output on every torque route.
Inputs are the logged setpoint (cs_la_des), measured angle/rate, v, liveParameters roll/sR/stiffness/angleOffset.
Gate for closed-loop use: corr(out) >= 0.98 and corr(F) >= 0.98 on usable frames >= 5 m/s, per route.
Also checks la_from_angle against the logged measurement (cs_la_act).
Saves per-route npz of the replica components (for s5_04 event decomposition).
"""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
import s5ctl as C  # noqa: E402

res = {}
for g in ('T64', 'T64B', 'T5', 'T4'):
    for rk in L.GROUPS[g]:
        S = L.V.load(rk)
        D = np.load(L.V.CACHE / f'{rk}.npz')
        stiff = np.interp(S['t'], D['t_lp'], D['stiff'])
        n = len(S['t'])
        comp = {k: np.full(n, np.nan) for k in ('out', 'p', 'i', 'f', 'hold', 'move', 'hyst', 'rl', 'dob', 'ad', 'meas')}
        act = S['active'] & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['v'])
        roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
        for a, b in L.V.runs(act, S['t'], min_s=1.0):
            ad0 = C.angle_from_la(float(S['setpoint'][a]), float(S['v'][a]), roll[a], sR[a], stiff[a])
            ctl = C.Ctl(C.GROUP_REV[g], rate0=float(S['sr'][a]), angle_des0=ad0)
            for j in range(a, b):
                v = float(S['v'][j])
                meas = C.la_from_angle(float(S['sa'][j]), aoff[j], v, roll[j], sR[j], stiff[j])
                u, cp = ctl.step(float(S['setpoint'][j]), float(S['la_act'][j]), float(S['sa'][j]), float(S['sr'][j]), v,
                                 roll[j], sR[j], stiff[j], aoff[j], pressed=bool(S['pressed'][j]), u_left_logged=float(S['out'][j]))
                comp['out'][j] = u; comp['meas'][j] = meas
                for k in ('p', 'i', 'f', 'hold', 'move', 'hyst', 'rl', 'dob', 'ad'):
                    comp[k][j] = cp[k]
        m = L.V.usable(S, 5.0) & np.isfinite(comp['out'])
        r = dict(frames=int(m.sum()))
        for k, lg in (('out', 'out'), ('p', 'p'), ('i', 'i'), ('f', 'f'), ('meas', 'la_act')):
            x, y = comp[k][m], S[lg][m]
            r[k] = dict(corr=float(np.corrcoef(x, y)[0, 1]), slope=float(np.dot(x, y) / max(np.dot(x, x), 1e-12)),
                        resid=float(np.std(y - x) / max(np.std(y), 1e-12)))
        res[rk] = dict(group=g, **r)
        print(g, rk, r['frames'], {k: (round(r[k]['corr'], 4), round(r[k]['slope'], 3), round(r[k]['resid'], 3)) for k in ('out', 'p', 'i', 'f', 'meas')}, flush=True)
        np.savez_compressed(L.OUT + f'_replica_{rk}.npz', t=S['t'], **comp)
        del S, D, comp
json.dump(res, open(L.OUT + 's5_03_replica_validate.json', 'w'), indent=1)
