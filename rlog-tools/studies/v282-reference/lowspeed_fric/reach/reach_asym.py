"""reach stage 3: the ASYMMETRY.

A. Reach split by direction (away from centre vs back toward it) and by dwell kind.
B. Structure test on the breakaway command: which additive structure explains the measured
   away 0.053 / toward 0.014 split?  Candidates, all fitted on the SAME episodes with route-cluster
   bootstrap, residual rms reported:
     M0  cmd            = k*aa + Fa*sj + d*sj*toward + c          (the existing fit)
     M1  cmd - z_today  = k*aa + Fa*sj + d*sj*toward + c          (is z itself the asymmetry?)
     M2  cmd - hold_aa  =        Fa*sj + d*sj*toward + c          (fork's own nonlinear hold, no free k)
     M3  cmd - hold_aa - 0.020*sign(aa) = Fa*sj + d*sj*toward + c (hold + the fork's static intercept)
   If M3's d collapses to 0 while M2's does not, the missing intercept IS the asymmetry.
C. Is the big snap the away-from-centre one?  slip / j30 / dwell by direction.
D. The CENTRED operator: z_eff = S*sign(angle_des) + clip(accum, -f, +f), replayed exactly like stage 1,
   S = 0 (today's family) and S = 0.020 (the fork's own intercept).  Reported with the same
   earlier-crossing arithmetic, split by direction.
"""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run, hold_torque, k_of_v  # noqa: E402
from ss_load import boot_ci                                          # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
SS = BASE + '/lowspeed/a_stickslip/out'
D = np.load(OUT + '/reach_rows.npz', allow_pickle=True)
R = list(D['rows']); CANDS = [tuple(c) for c in D['cands']]
F_TODAY = 0.015
S_INT = 0.020
GATES = {'g6_10': (6.0, 10.0), 'g8_12': (8.0, 12.0), 'g10_12': (10.0, 12.0), 'flat': (99.0, 99.1)}
TQ_ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
             '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
SHORT = {'2-8': 0.033, '8-15': 0.026}
res = {}

col = lambda k: np.array([r[k] for r in R])
mat = lambda k: np.stack([r[k] for r in R])
v = col('v'); route = col('route'); kind = col('kind'); aa = col('aa'); sj = col('sj')
slip = col('slip'); j30 = col('j30'); dwell = col('dwell_s'); aa_abs = col('abs_aa')
toward = (sj == -np.sign(aa))
z0 = mat('z0'); zbk = mat('zbk'); dt = mat('dt_early'); tr = mat('tr_early'); ever = mat('ever')
z0t = col('z0_today'); zbkt = col('zbk_today')
dz = zbk - z0; ex = zbk - zbkt[:, None]

# ---------- A. reach split by direction ----------
res['direction_counts'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = (v >= lo) & (v < hi)
    res['direction_counts'][f'{lo}-{hi}'] = dict(n=int(m.sum()), n_toward=int(toward[m].sum()),
                                                 n_away=int((~toward[m]).sum()),
                                                 frac_toward=float(np.mean(toward[m])))
    for kd in ['rev', 'cont', 'rest']:
        res['direction_counts'][f'{lo}-{hi}|{kd}'] = dict(
            n=int((m & (kind == kd)).sum()), frac_toward=float(np.mean(toward[m & (kind == kd)])) if (m & (kind == kd)).sum() else None)

SEL = [(0.015, 3.0, 'g8_12'), (0.020, 3.0, 'g8_12'), (0.025, 2.0, 'g8_12'), (0.030, 2.0, 'g8_12'),
       (0.033, 2.0, 'g8_12'), (0.033, 3.0, 'g8_12'), (0.036, 2.0, 'g8_12'), (0.045, 1.5, 'g8_12'),
       (0.033, 1.5, 'g8_12'), (0.033, 2.5, 'g8_12')]
res['by_direction'] = {}
for c in SEL:
    ci = CANDS.index(c); d = {}
    for lo, hi in [(2, 8), (8, 15)]:
        s = SHORT[f'{lo}-{hi}']
        for dn, dm in (('away', ~toward), ('toward', toward)):
            m = (v >= lo) & (v < hi) & dm
            if m.sum() < 6:
                continue
            d[f'{lo}-{hi}|{dn}'] = dict(n=int(m.sum()),
                z0=float(np.median(z0[m, ci])), zbk=float(np.median(zbk[m, ci])),
                dz=float(np.median(dz[m, ci])), ex=float(np.median(ex[m, ci])),
                need=0.053 if dn == 'away' else 0.014,
                zbk_over_need=float(np.median(zbk[m, ci]) / (0.053 if dn == 'away' else 0.014)),
                reach_acc=float(np.median(dz[m, ci]) / s),
                dt=float(np.median(dt[m, ci])), dt_p90=float(np.percentile(dt[m, ci], 90)),
                tr=float(np.median(tr[m, ci])), nohit=float(np.mean(~ever[m, ci])),
                frac_z0_sat=float(np.mean(z0[m, ci] > 0.98 * c[0])))
        for kd in ['rev', 'cont', 'rest']:
            m = (v >= lo) & (v < hi) & (kind == kd)
            if m.sum() < 8:
                continue
            d[f'{lo}-{hi}|{kd}'] = dict(n=int(m.sum()), z0=float(np.median(z0[m, ci])),
                                        zbk=float(np.median(zbk[m, ci])), dz=float(np.median(dz[m, ci])),
                                        ex=float(np.median(ex[m, ci])), dt=float(np.median(dt[m, ci])),
                                        frac_z0_sat=float(np.mean(z0[m, ci] > 0.98 * c[0])))
    res['by_direction'][str(c)] = d

# ---------- C. is the big snap the away-from-centre one? ----------
res['snap_by_direction'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for dn, dm in (('away', ~toward), ('toward', toward)):
        m = (v >= lo) & (v < hi) & dm
        res['snap_by_direction'][f'{lo}-{hi}|{dn}'] = dict(n=int(m.sum()),
            slip_p50=boot_ci(slip[m], route[m], np.median),
            slip_p90=boot_ci(slip[m], route[m], lambda x: np.percentile(x, 90)),
            j30_p90=boot_ci(j30[m], route[m], lambda x: np.percentile(x, 90)),
            dwell_p50=float(np.median(dwell[m])), abs_aa_p50=float(np.median(aa_abs[m])),
            frac_slip_gt3=float(np.mean(slip[m] > 3)))

# ---------- B. structure test: needs hold_aa and z_today at bk-3, per episode ----------
HOLD = np.zeros(len(R)); ZT = np.zeros(len(R)); AAbk = np.zeros(len(R)); CMD = np.zeros(len(R))
VBK = np.zeros(len(R)); i = 0
for rk in TQ_ROUTES:
    S = V.load(rk); p, fs = params(rk)
    vv_ = np.maximum(np.nan_to_num(S['v']), 1.0); v_ = np.nan_to_num(S['v']); act = S['active']
    sR = np.nan_to_num(S['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv_ ** 2 * sR * T.WB * (1 - T.SF * v_ ** 2))
    d_ang = np.r_[0.0, np.diff(angdes)]; d_ang[~act] = 0.0; d_ang[np.r_[True, ~act[:-1]]] = 0.0
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    zt = hyst_run(d_ang, F_TODAY, band(v_, sched), act)
    aa_ = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    cmd = np.nan_to_num(S['out'])
    hold_aa = hold_torque(aa_, v_, False)          # unlevelled (level enters only above 12.5 -> irrelevant <=12.5)
    EP = list(np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)['EP'])
    for e in EP:
        b3 = int(e['bk']) - 3
        HOLD[i] = hold_aa[b3]; ZT[i] = zt[b3]; AAbk[i] = aa_[b3]; CMD[i] = cmd[b3]; VBK[i] = v_[b3]; i += 1
    del S
assert i == len(R)
assert np.max(np.abs(CMD * sj - col('cmd_bk'))) < 1e-9, 'episode order mismatch'
assert np.max(np.abs(ZT * sj - zbkt)) < 1e-9

N = len(R)


def fit_boot(y, X, m, nb=1000, seed=5):
    rng = np.random.default_rng(seed); rr = route[m]; u = np.unique(rr)
    est = np.linalg.lstsq(X[m], y[m], rcond=None)[0]
    resid = y[m] - X[m] @ est
    bs = []
    ii_all = np.where(m)[0]
    for _ in range(nb):
        pick = rng.choice(u, len(u)); ii = np.concatenate([ii_all[rr == c] for c in pick])
        bs.append(np.linalg.lstsq(X[ii], y[ii], rcond=None)[0])
    bs = np.array(bs)
    return est, bs, float(np.sqrt(np.mean(resid ** 2)))


res['structure'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = (v >= lo) & (v < hi)
    ones = np.ones(N); tw = sj * toward.astype(float)
    models = {
        'M0 cmd ~ k*aa + Fa*sj + d*sj*toward + c': (CMD, np.vstack([AAbk, sj, tw, ones]).T, ['k', 'Fa', 'd', 'c']),
        'M1 (cmd - z_today) ~ same': (CMD - ZT, np.vstack([AAbk, sj, tw, ones]).T, ['k', 'Fa', 'd', 'c']),
        'M2 (cmd - hold_aa) ~ Fa*sj + d*sj*toward + c': (CMD - HOLD, np.vstack([sj, tw, ones]).T, ['Fa', 'd', 'c']),
        'M3 (cmd - hold_aa - 0.020*sign(aa)) ~ Fa*sj + d*sj*toward + c':
            (CMD - HOLD - S_INT * np.sign(AAbk), np.vstack([sj, tw, ones]).T, ['Fa', 'd', 'c']),
        'M2k (cmd - hold_aa) ~ k*aa + Fa*sj + d*sj*toward + c': (CMD - HOLD, np.vstack([AAbk, sj, tw, ones]).T, ['k', 'Fa', 'd', 'c']),
        'M4 (cmd - hold_aa) ~ Fa*sj + S*(-sign(aa)) + c  [S fitted]':
            (CMD - HOLD, np.vstack([sj, -np.sign(AAbk), ones]).T, ['Fa', 'S', 'c']),
    }
    out = {}
    for name, (y, X, nm) in models.items():
        est, bs, rms = fit_boot(y, X, m)
        d = {nm[q]: [float(est[q]), np.percentile(bs[:, q], [2.5, 97.5]).tolist()] for q in range(len(nm))}
        if 'Fa' in nm and 'd' in nm:
            ia, idd = nm.index('Fa'), nm.index('d')
            d['away'] = float(est[ia]); d['toward'] = float(est[ia] + est[idd])
            d['halfwidth'] = float(est[ia] + est[idd] / 2); d['centring_offset'] = float(-est[idd] / 2)
            d['centring_offset_ci'] = np.percentile(-bs[:, idd] / 2, [2.5, 97.5]).tolist()
        d['resid_rms'] = rms; d['n'] = int(m.sum())
        out[name] = d
    res['structure'][f'{lo}-{hi}'] = out
json.dump(res, open(OUT + '/reach_asym.json', 'w'), indent=1, default=float)
print('wrote reach_asym.json')
for k_, vv2 in res['structure'].items():
    print('==', k_)
    for nm, d in vv2.items():
        ks = {a: (round(b[0], 4) if isinstance(b, list) else round(b, 4)) for a, b in d.items() if a not in ('n', 'centring_offset_ci')}
        print('  ', nm, ks)
