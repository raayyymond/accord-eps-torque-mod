"""a_stickslip stage 2: mechanism, breakaway torque, 2F/k test, V282 matched comparison.  -> out/ss_analyze.json
All torque quantities in +left output units, sign-aligned with the jump (sj): + = pushing the way the wheel then jumped.
Delivered command at breakaway = cmd 30 ms (3 frames) before the breakaway frame (measured cmd->wheel-accel latency).
"""
import json, sys, numpy as np
from ss_load import *
from sslib import k_of_v

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); d0 = np.maximum(col('w_d0'), 0);   # 35/978 dwells longer than the 1.5 s window start at the window edge
d1 = col('w_d1'); kind = col('kind')
slip = col('slip'); j30 = col('j30'); aa_abs = col('abs_aa'); dr = col('dem_rate'); route = col('route'); dwell = col('dwell_s')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
ar = np.arange(N)
A = lambda k, idx: W[k][ar, idx] * sj                     # sign-aligned sample
R = {}
SB = [(2, 8), (8, 15)]

# ---------- 1. what accumulates through the dwell (torque routes) ----------
terms = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']
R['accumulation'] = {}
for lo, hi in SB:
    for sub, extra in (('all', np.ones(N, bool)), ('rev', kind == 'rev'), ('cont', kind == 'cont'), ('rest', kind == 'rest')):
        m = TQ & (v >= lo) & (v < hi) & extra
        if m.sum() < 8:
            continue
        d = {}
        for k in ['cmd', 'F'] + terms + ['hold_aa']:
            a0 = A(k, d0); a1 = A(k, np.full(N, BK)); aL = A(k, np.full(N, BK - 10))
            d[k] = dict(start=float(np.mean(a0[m])), bk=float(np.mean(a1[m])), change=boot_ci(a1[m] - a0[m], route[m], np.mean),
                        last100=float(np.mean((a1 - aL)[m])))
        net0 = (A('cmd', d0) - A('hold_aa', d0))[m]; net1 = (A('cmd', np.full(N, BK)) - A('hold_aa', np.full(N, BK)))[m]
        # dwell-average net (the steady command during the stick)
        netd = np.array([np.mean((W['cmd'][i, d0[i]:d1[i] + 1] - W['hold_aa'][i, d0[i]:d1[i] + 1]) * sj[i]) for i in np.where(m)[0]])
        # which term supplied the largest share of the last 100 ms increment
        inc = np.vstack([(A(k, np.full(N, BK)) - A(k, np.full(N, BK - 10)))[m] for k in terms])
        last = {terms[q]: float(np.mean(np.argmax(inc, 0) == q)) for q in range(len(terms))}
        incd = np.vstack([(A(k, np.full(N, BK)) - A(k, d0))[m] for k in terms])
        dom = {terms[q]: float(np.mean(np.argmax(incd, 0) == q)) for q in range(len(terms))}
        R['accumulation'][f'{lo}-{hi}|{sub}'] = dict(n=int(m.sum()), terms=d,
            net_start=boot_ci(net0, route[m], np.median), net_bk=boot_ci(net1, route[m], np.median), net_dwell_mean=boot_ci(netd, route[m], np.median),
            net_swing=boot_ci(net1 - net0, route[m], np.median),
            largest_last100=last, largest_over_dwell=dom, dwell_s=float(np.median(dwell[m])))

# ---------- 2. breakaway torque, hold-map free: cmd_bk = k' * aa + Fs * sj + c  (route-cluster bootstrap) ----------
def fitF(m, idx):
    aa = W['aa'][ar, idx][m]; c = W['cmd'][ar, idx][m]; s = sj[m]
    X = np.vstack([aa, s, np.ones(m.sum())]).T
    return np.linalg.lstsq(X, c, rcond=None)[0]


def boot_fit(m, idx, nb=1000):
    rr = route[m]; u = np.unique(rr); rng = np.random.default_rng(1); ii_all = np.where(m)[0]; bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u)); ii = np.concatenate([ii_all[rr == c] for c in pick])
        mm = np.zeros(N, bool); mm[ii] = True
        if mm.sum() > 6:
            bs.append(fitF(mm, idx if np.ndim(idx) == 0 else idx))
    bs = np.array(bs); est = fitF(m, idx)
    return dict(k_prime=float(est[0]), F=float(est[1]), c=float(est[2]), F_ci=np.percentile(bs[:, 1], [2.5, 97.5]).tolist(),
                k_ci=np.percentile(bs[:, 0], [2.5, 97.5]).tolist(), n=int(m.sum()), fork_k=float(np.mean(k_of_v(v[m]))))


R['breakaway_fit'] = {}
for lo, hi in [(2, 5), (5, 8), (2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi)
    if m.sum() >= 10:
        R['breakaway_fit'][f'{lo}-{hi}'] = dict(at_breakaway=boot_fit(m, np.full(N, BK)), at_dwell_start=boot_fit(m, d0))

# ---------- 3. 2F/k test ----------
R['two_F_over_k'] = {}
for lo, hi in [(2, 5), (5, 8), (2, 8), (8, 15)]:
    for sub, extra in (('all', np.ones(N, bool)), ('rev', kind == 'rev'), ('cont', kind == 'cont'), ('rest', kind == 'rest')):
        m = TQ & (v >= lo) & (v < hi) & extra
        if m.sum() < 6:
            continue
        kk = k_of_v(v[m])
        net1 = (A('cmd', np.full(N, BK)) - A('hold_aa', np.full(N, BK)))[m]
        R['two_F_over_k'][f'{lo}-{hi}|{sub}'] = dict(
            n=int(m.sum()), twoF_k_F020=float(np.median(0.04 / kk)),
            slip_p50=boot_ci(slip[m], route[m], np.median), slip_p90=boot_ci(slip[m], route[m], lambda x: np.percentile(x, 90)),
            j30_p90=boot_ci(j30[m], route[m], lambda x: np.percentile(x, 90)),
            ratio_slip_to_2Fk_p50=boot_ci(slip[m] * kk / 0.04, route[m], np.median),
            ratio_slip_to_2Fk_p90=boot_ci(slip[m] * kk / 0.04, route[m], lambda x: np.percentile(x, 90)),
            frac_slip_ge_2Fk=float(np.mean(slip[m] >= 0.04 / kk)),
            corr_slip_vs_1_over_k=float(np.corrcoef(slip[m], 1 / kk)[0, 1]) if m.sum() > 5 else None,
            corr_slip_vs_netbk_over_k=float(np.corrcoef(slip[m], net1 / kk)[0, 1]),
            corr_slip_vs_dwell=float(np.corrcoef(slip[m], dwell[m])[0, 1]),
            corr_slip_vs_absaa=float(np.corrcoef(slip[m], aa_abs[m])[0, 1]))

# ---------- 4. after breakaway: does the command retreat or keep pushing? ----------
R['post_breakaway'] = {}
for lo, hi in SB:
    for grp_name, gm in (('torque', TQ), ('V282', g == 'V282')):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 6:
            continue
        c0 = A('cmd', np.full(N, BK))
        out = {}
        for dt_ in (10, 20, 30, 50):
            out[f'cmd_change_+{dt_*10-30}ms'] = float(np.median((A('cmd', np.full(N, BK + dt_)) - c0)[m]))
            out[f'P_change_+{dt_*10-30}ms'] = float(np.median((A('P', np.full(N, BK + dt_)) - A('P', np.full(N, BK)))[m]))
        out['angle_travel_+300ms'] = float(np.median((A('aa', np.full(N, PRE + 30)) - A('aa', np.full(N, PRE)))[m]))
        R['post_breakaway'][f'{grp_name}|{lo}-{hi}'] = out

# ---------- 5. matched V282 vs torque (nearest neighbour on v, |aa|, demand rate) ----------
def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = np.argmin(dist)
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


R['matched'] = {}
for lo, hi in SB:
    for tg in ['T64', 'T64B', 'T4', 'T5', 'TORQUE_ALL']:
        tm = (TQ if tg == 'TORQUE_ALL' else g == tg) & (v >= lo) & (v < hi)
        rm = (g == 'V282') & (v >= lo - 1) & (v < hi + 1)
        P_ = match(tm, rm)
        if len(P_) < 5:
            continue
        ti = np.array([p[0] for p in P_]); ri = np.array([p[1] for p in P_])
        lr = np.log((slip[ti] + 0.3) / (slip[ri] + 0.3))
        R['matched'][f'{tg}|{lo}-{hi}'] = dict(
            n_pairs=len(P_), n_torque=int(tm.sum()), torque_slip_p50=float(np.median(slip[ti])), v282_slip_p50=float(np.median(slip[ri])),
            torque_slip_p90=float(np.percentile(slip[ti], 90)), v282_slip_p90=float(np.percentile(slip[ri], 90)),
            torque_j30_p90=float(np.percentile(j30[ti], 90)), v282_j30_p90=float(np.percentile(j30[ri], 90)),
            slip_ratio_geo=boot_ci(lr, route[ti], lambda x: float(np.exp(np.mean(x)))),
            frac_slip_gt3_torque=float(np.mean(slip[ti] > 3)), frac_slip_gt3_v282=float(np.mean(slip[ri] > 3)),
            dwell_p50_torque=float(np.median(dwell[ti])), dwell_p50_v282=float(np.median(dwell[ri])))

# ---------- 6. episode rate per 100 s of hands-off demand-moving time ----------
R['rate'] = {}
for grp_name in ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']:
    rks = sorted(set(route[g == grp_name]))
    for vb, (lo, hi) in enumerate([(2, 5), (5, 8), (8, 15)]):
        ex = sum(EX[r][f'{vb}_{a}']['moving_sec'] for r in rks for a in range(4))
        m = (g == grp_name) & (v >= lo) & (v < hi)
        big = m & (slip >= 3)
        R['rate'][f'{grp_name}|{lo}-{hi}'] = dict(moving_s=ex, n=int(m.sum()), per100s=100 * m.sum() / max(ex, 1e-9),
                                                 slip_ge3_per100s=100 * big.sum() / max(ex, 1e-9))
# ---------- 7. catch-up after breakaway vs the lag the dwell built (the 2F/k test done on the GAP) ----------
R['gap_test'] = {}
gapdes = A('angdes', np.full(N, PRE)) - A('aa', np.full(N, PRE))          # fork desired angle minus wheel, at breakaway
dwell_dem = A('angdes', np.full(N, PRE)) - A('angdes', d0)                 # desired-angle travel during the dwell
catch30 = A('aa', np.full(N, PRE + 30)) - A('aa', np.full(N, PRE))
dem30 = A('angdes', np.full(N, PRE + 30)) - A('angdes', np.full(N, PRE))
over30 = catch30 - dem30 - gapdes                                           # >0: wheel passes the desired angle within 300 ms
pk = np.max(np.abs(W['sr'][:, PRE:PRE + 40]), 1)
for lo, hi in [(2, 8), (8, 15)]:
    for aname, am in (('aa<5', aa_abs < 5), ('aa>=5', aa_abs >= 5), ('all', np.ones(N, bool))):
        for grp_name, gm in (('torque', TQ), ('V282', g == 'V282')):
            m = gm & (v >= lo) & (v < hi) & am
            if m.sum() < 5:
                continue
            kk = k_of_v(v[m])
            R['gap_test'][f'{grp_name}|{lo}-{hi}|{aname}'] = dict(n=int(m.sum()),
                twoF_over_k_F020=float(np.median(0.04 / kk)),
                gap_bk=boot_ci(gapdes[m], route[m], np.median), gap_bk_p90=float(np.percentile(gapdes[m], 90)),
                dwell_demand_travel=boot_ci(dwell_dem[m], route[m], np.median),
                catch30=boot_ci(catch30[m], route[m], np.median), catch30_p90=float(np.percentile(catch30[m], 90)),
                overshoot30_p50=float(np.median(over30[m])), overshoot30_p90=float(np.percentile(over30[m], 90)),
                frac_pass_desired_30=float(np.mean(over30[m] > 0)),
                peak_rate_40=boot_ci(pk[m], route[m], np.median), dwell_s=boot_ci(dwell[m], route[m], np.median),
                gap_over_2Fk_p50=float(np.median(gapdes[m] * kk / 0.04)), catch30_over_2Fk_p90=float(np.percentile(catch30[m] * kk / 0.04, 90)))

# ---------- 8. breakaway fit split by kind ----------
R['breakaway_fit_kind'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for kd in ['rev', 'cont', 'rest']:
        m = TQ & (v >= lo) & (v < hi) & (kind == kd)
        if m.sum() >= 12:
            R['breakaway_fit_kind'][f'{lo}-{hi}|{kd}'] = dict(at_breakaway=boot_fit(m, np.full(N, BK)), at_dwell_start=boot_fit(m, d0))
R['validation_z'] = VAL
json.dump(R, open(OUT + '/ss_analyze.json', 'w'), indent=1, default=float)
print(json.dumps({k: R[k] for k in ['breakaway_fit', 'post_breakaway', 'rate']}, indent=1, default=lambda x: round(float(x), 4)))
