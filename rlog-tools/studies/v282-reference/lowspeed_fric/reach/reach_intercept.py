"""reach stage 4: the CENTRED operator and the last-motion test.

(1) last-motion test: does the measured asymmetry key on sign(angle) or on the sign of the wheel's LAST
    ACTUAL motion (s_prev, recoverable from the episode 'kind')?  Both entered in one fit.
(2) centred-operator replay: z_eff = S * tanh(angle_des / dz_int) + clip(accum, -f, +f), exact scalar run
    of the fork operator with the intercept added, S in {0, 0.020, 0.025}, dz_int a centre blend in deg.
    Same earlier-crossing arithmetic as stage 1, split away / toward.
(3) centre-crossing census: how often angle_des changes sign at <8 m/s (the intercept's own step risk).
"""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run, hold_torque  # noqa: E402
from ss_load import boot_ci                                  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
SS = BASE + '/lowspeed/a_stickslip/out'
F_TODAY = 0.015
GATES = {'g6_10': (6.0, 10.0), 'g8_12': (8.0, 12.0), 'flat': (99.0, 99.1)}
TQ = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
      '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
SHORT = {'2-8': 0.033, '8-15': 0.026}
# (ceiling, band, gate, intercept S, centre blend deg)
VAR = [(0.015, 3.0, 'g8_12', 0.000, 1.0),      # today
       (0.015, 3.0, 'g8_12', 0.020, 1.0),      # today + the fork's own intercept
       (0.020, 3.0, 'g8_12', 0.020, 1.0),
       (0.015, 2.0, 'g8_12', 0.020, 1.0),
       (0.020, 2.0, 'g8_12', 0.020, 1.0),
       (0.025, 2.0, 'g8_12', 0.020, 1.0),
       (0.015, 3.0, 'g8_12', 0.025, 1.0),
       (0.020, 2.0, 'g8_12', 0.020, 2.0),
       (0.033, 2.0, 'g8_12', 0.000, 1.0),      # the best symmetric reach candidate, for comparison
       (0.033, 3.0, 'g8_12', 0.000, 1.0),
       (0.045, 1.5, 'g8_12', 0.000, 1.0),
       (0.020, 2.0, 'g6_10', 0.020, 1.0)]
NV = len(VAR)
rows = []
cross = {}

for rk in TQ:
    S_ = V.load(rk); p, fs = params(rk)
    v = np.nan_to_num(S_['v']); vv = np.maximum(v, 1.0); act = S_['active']
    sR = np.nan_to_num(S_['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S_['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    d_ang = np.r_[0.0, np.diff(angdes)]; d_ang[~act] = 0.0; d_ang[np.r_[True, ~act[:-1]]] = 0.0
    cmd = np.nan_to_num(S_['out'])
    aa_ = np.nan_to_num(S_['sa']) - np.nan_to_num(S_['aoff'])
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    b_today = band(v, sched)
    zt = hyst_run(d_ang, F_TODAY, b_today, act)
    pressd = S_['pressed']
    # centre-crossing census, hands-off, engaged, <8 m/s
    mm = act & ~pressd & (v >= 2) & (v < 8)
    sgn = np.sign(angdes); sgn[np.abs(angdes) < 0.25] = 0
    ch = np.sum((sgn[1:] * sgn[:-1] < 0) & mm[1:])
    cross[rk] = dict(sec=float(mm.sum() / 100), sign_flips=int(ch),
                     flips_per_100s=float(100 * ch / max(mm.sum() / 100, 1e-9)),
                     frac_time_absangdes_lt_1deg=float(np.mean(np.abs(angdes[mm]) < 1.0)),
                     frac_time_absangdes_lt_2deg=float(np.mean(np.abs(angdes[mm]) < 2.0)))
    ZC = []
    for (f, b, gn, Si, dzi) in VAR:
        v0, v1 = GATES[gn]
        g = np.clip((v - v0) / (v1 - v0), 0.0, 1.0)
        fe = f + g * (F_TODAY - f)
        be = b + g * (b_today - b)
        se = Si * (1.0 - g)
        z = np.zeros(len(d_ang)); zz = 0.0
        for n in range(len(d_ang)):
            if not act[n]:
                zz = 0.0
            else:
                zz = min(max(zz + d_ang[n] * fe[n] / max(be[n], 1e-3), -fe[n]), fe[n])
            z[n] = zz
        ZC.append(z + se * np.tanh(angdes / dzi))
    ZC = np.stack(ZC, 1)
    EP = list(np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)['EP'])
    for e in EP:
        i0 = int(e['i0']); bk = int(e['bk']); b3 = max(bk - 3, i0); sj = float(e['sjump'])
        z0 = ZC[i0] * sj; zbk = ZC[b3] * sj
        thr = cmd[b3] * sj
        alt = (cmd[i0:b3 + 1] * sj)[:, None] + (ZC[i0:b3 + 1] * sj - (zt[i0:b3 + 1] * sj)[:, None])
        hit = alt >= thr; L = hit.shape[0]
        ever = hit.any(0); first = np.where(ever, hit.argmax(0), L - 1)
        ad = angdes[i0:b3 + 1] * sj
        kd = str(e['kind'])
        rows.append(dict(route=rk, v=float(e['v']), aa=float(e['aa']), sj=sj, kind=kd,
                         abs_aa=float(e['abs_aa']), slip=float(e['slip']), dwell_s=float(e['dwell_s']),
                         sgn_angdes=float(np.sign(angdes[b3])),
                         s_prev=(sj if kd == 'cont' else (-sj if kd == 'rev' else 0.0)),
                         cmd_bk=float(thr), hold_aa=float(hold_torque(aa_[b3], v[b3], False)),
                         z0=z0.astype(np.float32), zbk=zbk.astype(np.float32),
                         zbk_today=float(zt[b3] * sj),
                         dt=((L - 1 - first) / 100.0).astype(np.float32),
                         tr=(ad[L - 1] - ad[first]).astype(np.float32), ever=ever))
    del S_, ZC
    print('done', rk, flush=True)

res = dict(variants=[list(x) for x in VAR], crossings=cross)
colf = lambda k: np.array([r[k] for r in rows])
matf = lambda k: np.stack([r[k] for r in rows])
v = colf('v'); route = colf('route'); aa = colf('aa'); sj = colf('sj'); kind = colf('kind')
sprev = colf('s_prev'); cmdb = colf('cmd_bk'); hold = colf('hold_aa'); sgad = colf('sgn_angdes')
toward = (sj == -np.sign(aa))
z0 = matf('z0'); zbk = matf('zbk'); dt = matf('dt'); tr = matf('tr'); ever = matf('ever')
zbkt = colf('zbk_today')
N = len(rows)
res['agree_sign_aa_vs_sprev'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = (v >= lo) & (v < hi)
    res['agree_sign_aa_vs_sprev'][f'{lo}-{hi}'] = dict(
        n=int(m.sum()), frac_sprev_nonzero=float(np.mean(sprev[m] != 0)),
        frac_agree=float(np.mean(np.sign(aa[m])[sprev[m] != 0] == sprev[m][sprev[m] != 0])),
        frac_sign_angdes_eq_sign_aa=float(np.mean(sgad[m] == np.sign(aa[m]))))

# --- last-motion test ---
def fitb(y, X, m, nb=1000, seed=7):
    rng = np.random.default_rng(seed); rr = route[m]; u = np.unique(rr); ii_all = np.where(m)[0]
    est = np.linalg.lstsq(X[m], y[m], rcond=None)[0]
    rms = float(np.sqrt(np.mean((y[m] - X[m] @ est) ** 2)))
    bs = [np.linalg.lstsq(X[np.concatenate([ii_all[rr == c] for c in rng.choice(u, len(u))])],
                          y[np.concatenate([ii_all[rr == c] for c in rng.choice(u, len(u))])], rcond=None)[0]
          for _ in range(0)]
    bs = []
    for _ in range(nb):
        ii = np.concatenate([ii_all[rr == c] for c in rng.choice(u, len(u))])
        bs.append(np.linalg.lstsq(X[ii], y[ii], rcond=None)[0])
    return est, np.array(bs), rms


res['last_motion'] = {}
y = cmdb * sj - hold          # cmd_bk was stored sign-aligned; hold_aa is raw -> undo the alignment
ones = np.ones(N)
for lo, hi in [(2, 8), (8, 15)]:
    m = (v >= lo) & (v < hi)
    out = {}
    for nm, X, names in [
        ('A: Fa*sj + A1*sign(aa) + c', np.vstack([sj, np.sign(aa), ones]).T, ['Fa', 'A_aa', 'c']),
        ('B: Fa*sj + A2*s_prev + c', np.vstack([sj, sprev, ones]).T, ['Fa', 'A_prev', 'c']),
        ('C: Fa*sj + A1*sign(aa) + A2*s_prev + c', np.vstack([sj, np.sign(aa), sprev, ones]).T, ['Fa', 'A_aa', 'A_prev', 'c']),
    ]:
        est, bs, rms = fitb(y, X, m)
        out[nm] = dict(**{names[q]: [float(est[q]), np.percentile(bs[:, q], [2.5, 97.5]).tolist()] for q in range(len(names))},
                       resid_rms=rms, n=int(m.sum()))
    res['last_motion'][f'{lo}-{hi}'] = out

# --- variant reach ---
res['variant_reach'] = {}
for ci, var in enumerate(VAR):
    d = {}
    for lo, hi in [(2, 8), (8, 15)]:
        s = SHORT[f'{lo}-{hi}']
        for dn, dm in (('all', np.ones(N, bool)), ('away', ~toward), ('toward', toward)):
            m = (v >= lo) & (v < hi) & dm
            if m.sum() < 6:
                continue
            d[f'{lo}-{hi}|{dn}'] = dict(n=int(m.sum()),
                z0=float(np.median(z0[m, ci])), zbk=float(np.median(zbk[m, ci])),
                dz=float(np.median(zbk[m, ci] - z0[m, ci])),
                ex=float(np.median(zbk[m, ci] - zbkt[m])),
                reach_acc=float(np.median(zbk[m, ci] - z0[m, ci]) / s),
                reach_ex=float(np.median(zbk[m, ci] - zbkt[m]) / s),
                dt=float(np.median(dt[m, ci])), dt_p90=float(np.percentile(dt[m, ci], 90)),
                dt_ci=boot_ci(dt[m, ci], route[m], np.median),
                tr=float(np.median(tr[m, ci])), nohit=float(np.mean(~ever[m, ci])),
                frac_dt_ge_100ms=float(np.mean(dt[m, ci] >= 0.10)))
    res['variant_reach'][str(var)] = d

json.dump(res, open(OUT + '/reach_intercept.json', 'w'), indent=1, default=float)
print(json.dumps(res['crossings'], indent=1))
print(json.dumps(res['agree_sign_aa_vs_sprev'], indent=1))
for k_, vv2 in res['last_motion'].items():
    print('==', k_)
    for nm, dd in vv2.items():
        print('  ', nm, {a: (round(b[0], 4) if isinstance(b, list) else round(b, 4)) for a, b in dd.items() if a != 'n'})
