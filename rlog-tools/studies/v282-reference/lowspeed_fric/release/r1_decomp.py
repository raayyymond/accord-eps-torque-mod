"""Stage 1: decompose the command through the 0.5 s AFTER breakaway.

All channels are the LOGGED ones (cmd = P + I + F holds to 3e-9 in both groups, checked in
r0_verify).  For the torque group F is further split with the extractor's validated sub-channels
(hold_ff, move, z, rl, dob).  For V282 the sub-split is NOT attempted: its F is the same
demand-driven plant feedforward (AccordRatePlantFF=1) but under an older constant table, and a
window-local rebuild does not reproduce it (r0_verify: hold coef 0.31-0.48, move coef 3.7-4.3).
So V282's F is reported whole, and its demand-vs-wheel dependence is tested empirically below.

Sign convention: every torque is multiplied by sj (the sign of the jump), so + = pushing the way
the wheel then went.  t=0 is the breakaway frame (index PRE=150).

-> out/r1_decomp.json
"""
import numpy as np, json
from rel_lib import *

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route'); aa_abs = col('abs_aa')
dr = col('dem_rate'); kind = col('kind'); dwell = col('dwell_s')
TQ = np.isin(g, TQG); V2 = g == 'V282'
ar = np.arange(N)

TERMS_ALL = ['cmd', 'P', 'I', 'F']
TERMS_TQ = ['hold_ff', 'move', 'z', 'rl', 'dob']
S = {k: W[k] * sj[:, None] for k in ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'angdes', 'ad', 'sr')}
LAGS = [10, 20, 30, 50]        # frames after breakaway = 0.1 .. 0.5 s
R = {'note': dict(t0='breakaway frame (PRE=150)', units='output torque [-1,1], +left, sign-aligned to the jump',
                  D_loop_ms='55-75 (REPORT 2026-09-19); command-clock deltas are reported, the transport shifts the clock only')}


def desc(x, cl):
    m, ci = boot_ci(x, cl, np.median)
    return dict(p50=round(float(m), 5), ci=[round(c, 5) for c in ci], mean=round(float(np.mean(x)), 5), n=int(len(x)))


# ---------- 1. raw per-group deltas ----------
R['delta_by_group'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in [('V282', V2), ('TORQUE', TQ), ('T64', g == 'T64'), ('T64B', g == 'T64B'), ('T4', g == 'T4'), ('T5', g == 'T5')]:
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 8:
            continue
        d = {}
        for k in TERMS_ALL + (TERMS_TQ if gm is not V2 else []):
            if k in TERMS_TQ and not np.isin(g[m], TQG).all():
                continue
            d[k] = {f'+{L*10}ms': desc((S[k][:, PRE + L] - S[k][:, PRE])[m], rt[m]) for L in LAGS}
        d['level_at_bk'] = {k: round(float(np.median(S[k][m, PRE])), 5) for k in TERMS_ALL + TERMS_TQ}
        # net driving torque above the spring at the ACTUAL angle
        net = S['cmd'] - S['hold_aa']
        d['net_cmd_minus_hold_at_actual'] = {f'+{L*10}ms': desc((net[:, PRE + L] - net[:, PRE])[m], rt[m]) for L in LAGS}
        d['net_level_at_bk'] = desc(net[m, PRE], rt[m])
        # excess over the measured Coulomb level F=0.020: the integral that keeps the wheel accelerating
        for Fc in (0.020,):
            exc = np.maximum(net[:, PRE:PRE + 31] - Fc, 0.0).sum(1) * 0.01
            d[f'excess_impulse_300ms_F{Fc}'] = desc(exc[m], rt[m])
            exc5 = np.maximum(net[:, PRE:PRE + 51] - Fc, 0.0).sum(1) * 0.01
            d[f'excess_impulse_500ms_F{Fc}'] = desc(exc5[m], rt[m])
        R['delta_by_group'][f'{gname}|{lo}-{hi}'] = d

# ---------- 2. matched pairs (same matcher as ss_analyze) ----------
def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = int(np.argmin(dist))
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


R['matched'] = {}
PAIRS = {}
for lo, hi in [(2, 8), (8, 15)]:
    for aname, am in (('all', np.ones(N, bool)), ('aa<5', aa_abs < 5), ('aa>=5', aa_abs >= 5)):
        tm = TQ & (v >= lo) & (v < hi) & am
        rm = V2 & (v >= lo - 1) & (v < hi + 1) & am
        pr = match(tm, rm)
        if len(pr) < 6:
            continue
        ti = np.array([p[0] for p in pr]); ri = np.array([p[1] for p in pr])
        PAIRS[f'{lo}-{hi}|{aname}'] = (ti, ri)
        d = dict(n_pairs=len(pr), v_t=round(float(np.median(v[ti])), 2), v_r=round(float(np.median(v[ri])), 2),
                 aa_t=round(float(np.median(aa_abs[ti])), 2), aa_r=round(float(np.median(aa_abs[ri])), 2),
                 dwell_t=round(float(np.median(dwell[ti])), 3), dwell_r=round(float(np.median(dwell[ri])), 3))
        for k in TERMS_ALL:
            dt_ = {f'+{L*10}ms': dict(torque=desc((S[k][:, PRE + L] - S[k][:, PRE])[ti], rt[ti]),
                                      v282=desc((S[k][:, PRE + L] - S[k][:, PRE])[ri], rt[ri]),
                                      diff=desc(((S[k][:, PRE + L] - S[k][:, PRE])[ti] - (S[k][:, PRE + L] - S[k][:, PRE])[ri]), rt[ti]))
                   for L in LAGS}
            d[k] = dt_
        net = S['cmd'] - S['hold_aa']
        d['net'] = {f'+{L*10}ms': dict(torque=desc((net[:, PRE + L] - net[:, PRE])[ti], rt[ti]),
                                       v282=desc((net[:, PRE + L] - net[:, PRE])[ri], rt[ri]))
                    for L in LAGS}
        d['net_at_bk'] = dict(torque=desc(net[ti, PRE], rt[ti]), v282=desc(net[ri, PRE], rt[ri]))
        for Fc in (0.020,):
            for T_ in (31, 51):
                exc = np.maximum(net[:, PRE:PRE + T_] - Fc, 0.0).sum(1) * 0.01
                d[f'excess_impulse_{(T_-1)*10}ms'] = dict(torque=desc(exc[ti], rt[ti]), v282=desc(exc[ri], rt[ri]),
                                                          ratio=round(float(np.median(exc[ti]) / max(np.median(exc[ri]), 1e-9)), 3))
        # P strength in torque units, per unit lat-accel error
        d['P_torque_per_lataccel_err'] = dict(torque=round(1.0 / 14.0, 4), v282=round(0.9 / 6.0, 4), ratio_v282_over_torque=round((0.9 / 6.0) / (1.0 / 14.0), 3))
        R['matched'][f'{lo}-{hi}|{aname}'] = d

# ---------- 3. does F know the wheel moved?  partial regression of dF on d(angdes) and d(aa) ----------
R['F_depends_on'] = {}
for gname, gm in (('V282', V2), ('TORQUE', TQ)):
    for L in (20, 30, 50):
        m = gm & (v >= 2) & (v < 15)
        dF = (S['F'][:, PRE + L] - S['F'][:, PRE])[m]
        dA = (S['angdes'][:, PRE + L] - S['angdes'][:, PRE])[m]
        dW = (S['aa'][:, PRE + L] - S['aa'][:, PRE])[m]
        X = np.vstack([dA, dW, np.ones(len(dF))]).T
        b = np.linalg.lstsq(X, dF, rcond=None)[0]
        r2 = 1 - np.var(dF - X @ b) / np.var(dF)
        Xa = np.vstack([dA, np.ones(len(dF))]).T
        ba = np.linalg.lstsq(Xa, dF, rcond=None)[0]
        r2a = 1 - np.var(dF - Xa @ ba) / np.var(dF)
        R['F_depends_on'][f'{gname}|+{L*10}ms'] = dict(n=int(m.sum()), coef_d_angdes=round(float(b[0]), 5), coef_d_wheel=round(float(b[1]), 5),
                                                       r2_both=round(float(r2), 3), r2_angdes_only=round(float(r2a), 3),
                                                       delta_r2_from_wheel=round(float(r2 - r2a), 4))
json.dump(R, open(OUT + '/r1_decomp.json', 'w'), indent=1, default=float)
np.savez_compressed(OUT + '/pairs.npz', **{k: np.array(vv) for k, vv in PAIRS.items()})
print(json.dumps({k: R[k] for k in ['F_depends_on']}, indent=1))
print(json.dumps(R['matched'].get('2-8|all', {}), indent=1)[:4000])
