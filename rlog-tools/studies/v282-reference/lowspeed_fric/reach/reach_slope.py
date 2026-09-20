"""reach stage 5:
(a) the reach-vs-slope law and the CEILING-INERTNESS test (is the ceiling inert at constant slope?)
(b) k-proportional band families below 8 m/s -- slope(v) = M * k(v), the only family that keeps the
    over-delivery ratio flat in speed; replayed exactly, M in {1.0, 1.4, 1.8, 2.4, 3.6}
(c) the low-speed dwell speed histogram (where the reach has to be bought)
(d) the dwell-phase command build RATE (torque/s), which converts a torque offset into dwell seconds
"""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run, k_of_v, HOLD_LEVEL_BP, HOLD_LEVEL_V  # noqa: E402
from ss_load import boot_ci                                                          # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
SS = BASE + '/lowspeed/a_stickslip/out'
F_TODAY = 0.015
TQ = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
      '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
SHORT = {'2-8': 0.033, '8-15': 0.026}
res = {}

# ---------- (a) law + ceiling inertness, from the stage-1 grid ----------
D = np.load(OUT + '/reach_rows.npz', allow_pickle=True)
R0 = list(D['rows']); CANDS = [tuple(c) for c in D['cands']]
v0 = np.array([r['v'] for r in R0]); rt0 = np.array([r['route'] for r in R0])
aa0 = np.array([r['aa'] for r in R0]); sj0 = np.array([r['sj'] for r in R0])
tw0 = (sj0 == -np.sign(aa0))
Z0 = np.stack([r['z0'] for r in R0]); ZB = np.stack([r['zbk'] for r in R0])
DT = np.stack([r['dt_early'] for r in R0])
m28 = (v0 >= 2) & (v0 < 8)
sl = np.array([c[0] / c[1] for c in CANDS]); gt = np.array([c[2] for c in CANDS])
gm = (gt == 'g8_12')
racc = np.array([np.median((ZB - Z0)[m28, ci]) / 0.033 for ci in range(len(CANDS))])
A = np.polyfit(sl[gm], racc[gm], 1)
res['law'] = dict(fit_slope=float(A[0]), fit_intercept=float(A[1]),
                  r2=float(1 - np.var(racc[gm] - np.polyval(A, sl[gm])) / np.var(racc[gm])),
                  slope_for_reach_1p0=float((1.0 - A[1]) / A[0]), slope_for_reach_0p5=float((0.5 - A[1]) / A[0]),
                  slope_today=F_TODAY / 3.0, reach_today=float(racc[CANDS.index((0.015, 3.0, 'g8_12'))]))
iso = {}
for tgt in [0.005, 0.0075, 0.010, 0.015]:
    grp = [ci for ci in range(len(CANDS)) if gt[ci] == 'g8_12' and abs(sl[ci] - tgt) < 1e-6]
    iso[f'slope_{tgt}'] = [dict(f=CANDS[ci][0], band=CANDS[ci][1], reach_acc=float(racc[ci]),
                                z0_away=float(np.median(Z0[m28 & ~tw0, ci])),
                                zbk_away=float(np.median(ZB[m28 & ~tw0, ci])),
                                dt50=float(np.median(DT[m28, ci]))) for ci in grp]
res['ceiling_inertness_at_constant_slope'] = iso

# ---------- (b) k-proportional families + (c),(d) ----------
MS = [1.0, 1.4, 1.8, 2.4, 3.6]
FS_ = [0.020, 0.027, 0.033]
VAR = [('flat_today', None, F_TODAY)] + [(f'kprop_M{M}', M, f) for f in FS_ for M in MS]
rows = []
for rk in TQ:
    S_ = V.load(rk); p, fs = params(rk)
    v = np.nan_to_num(S_['v']); vv = np.maximum(v, 1.0); act = S_['active']
    sR = np.nan_to_num(S_['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S_['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    d_ang = np.r_[0.0, np.diff(angdes)]; d_ang[~act] = 0.0; d_ang[np.r_[True, ~act[:-1]]] = 0.0
    cmd = np.nan_to_num(S_['out'])
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    b_today = band(v, sched)
    zt = hyst_run(d_ang, F_TODAY, b_today, act)
    kv = k_of_v(v)
    g = np.clip((v - 8.0) / 4.0, 0.0, 1.0)        # gate: candidate below 8, today's by 12
    ZC = []
    for (nm, M, f) in VAR:
        if M is None:
            ZC.append(zt); continue
        sl_c = M * kv                              # torque per deg
        b_c = f / np.maximum(sl_c, 1e-6)
        fe = f + g * (F_TODAY - f); be = b_c + g * (b_today - b_c)
        z = np.zeros(len(d_ang)); zz = 0.0
        for n in range(len(d_ang)):
            if not act[n]:
                zz = 0.0
            else:
                zz = min(max(zz + d_ang[n] * fe[n] / max(be[n], 1e-3), -fe[n]), fe[n])
            z[n] = zz
        ZC.append(z)
    ZC = np.stack(ZC, 1)
    EP = list(np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)['EP'])
    for e in EP:
        i0 = int(e['i0']); bk = int(e['bk']); b3 = max(bk - 3, i0); sj = float(e['sjump'])
        thr = cmd[b3] * sj
        alt = (cmd[i0:b3 + 1] * sj)[:, None] + (ZC[i0:b3 + 1] * sj - (zt[i0:b3 + 1] * sj)[:, None])
        hit = alt >= thr; L = hit.shape[0]
        ever = hit.any(0); first = np.where(ever, hit.argmax(0), L - 1)
        ad = angdes[i0:b3 + 1] * sj
        # dwell-phase command build rate (torque/s), sign-aligned, over the stuck phase [i0, b3]
        dur = max((b3 - i0) / 100.0, 0.01)
        rate = (cmd[b3] * sj - cmd[i0] * sj) / dur
        rows.append(dict(route=rk, v=float(e['v']), aa=float(e['aa']), sj=sj, kind=str(e['kind']),
                         dwell_s=float(e['dwell_s']), slip=float(e['slip']), abs_aa=float(e['abs_aa']),
                         build_rate=float(rate), dwell_travel=float(ad[L - 1] - ad[0]),
                         z0=ZC[i0].astype(np.float32) * sj, zbk=ZC[b3].astype(np.float32) * sj,
                         zbk_today=float(zt[b3] * sj),
                         dt=((L - 1 - first) / 100.0).astype(np.float32),
                         tr=(ad[L - 1] - ad[first]).astype(np.float32), ever=ever))
    del S_, ZC
    print('done', rk, flush=True)

cf = lambda k: np.array([r[k] for r in rows]); mf = lambda k: np.stack([r[k] for r in rows])
v = cf('v'); route = cf('route'); aa = cf('aa'); sj = cf('sj'); tw = (sj == -np.sign(aa))
z0 = mf('z0'); zb = mf('zbk'); dt = mf('dt'); tr = mf('tr'); ev = mf('ever'); zbt = cf('zbk_today')
br = cf('build_rate'); dwtr = cf('dwell_travel'); dws = cf('dwell_s')
N = len(rows)

m = (v >= 2) & (v < 8)
res['episode_speeds'] = dict(
    n=int(m.sum()),
    pct=[float(x) for x in np.percentile(v[m], [10, 25, 50, 75, 90])],
    frac_2_4=float(np.mean(v[m] < 4)), frac_4_6=float(np.mean((v[m] >= 4) & (v[m] < 6))),
    frac_6_8=float(np.mean(v[m] >= 6)),
    k_at_median=float(k_of_v(np.median(v[m]))),
    klev_at_median=float(k_of_v(np.median(v[m])) * np.interp(np.median(v[m]), HOLD_LEVEL_BP, HOLD_LEVEL_V)))
res['dwell_build_rate'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for dn, dm in (('all', np.ones(N, bool)), ('away', ~tw), ('toward', tw)):
        mm = (v >= lo) & (v < hi) & dm
        res['dwell_build_rate'][f'{lo}-{hi}|{dn}'] = dict(
            n=int(mm.sum()), rate_p50=boot_ci(br[mm], route[mm], np.median),
            rate_p25=float(np.percentile(br[mm], 25)), rate_p75=float(np.percentile(br[mm], 75)),
            travel_p50=float(np.median(dwtr[mm])), dwell_p50=float(np.median(dws[mm])),
            sec_per_0p020=float(0.020 / max(np.median(br[mm]), 1e-9)))
res['kprop'] = {}
for ci, (nm, M, f) in enumerate(VAR):
    d = dict(name=nm, M=M, f=f)
    for x in [2.0, 4.0, 6.0, 8.0]:
        s_ = (M * float(k_of_v(x))) if M else F_TODAY / 3.0
        d[f'slope_{int(x)}'] = s_
        d[f'band_{int(x)}'] = (f / s_) if M else 3.0
        d[f'over_k_{int(x)}'] = s_ / float(k_of_v(x))
        d[f'over_klev_{int(x)}'] = s_ / float(k_of_v(x) * np.interp(x, HOLD_LEVEL_BP, HOLD_LEVEL_V))
    for lo, hi in [(2, 8), (8, 15)]:
        s = SHORT[f'{lo}-{hi}']
        for dn, dm in (('all', np.ones(N, bool)), ('away', ~tw), ('toward', tw)):
            mm = (v >= lo) & (v < hi) & dm
            if mm.sum() < 6:
                continue
            d[f'{lo}-{hi}|{dn}'] = dict(n=int(mm.sum()), z0=float(np.median(z0[mm, ci])),
                zbk=float(np.median(zb[mm, ci])), dz=float(np.median(zb[mm, ci] - z0[mm, ci])),
                ex=float(np.median(zb[mm, ci] - zbt[mm])),
                reach_acc=float(np.median(zb[mm, ci] - z0[mm, ci]) / s),
                dt=float(np.median(dt[mm, ci])), dt_p90=float(np.percentile(dt[mm, ci], 90)),
                dt_ci=boot_ci(dt[mm, ci], route[mm], np.median),
                tr=float(np.median(tr[mm, ci])), nohit=float(np.mean(~ev[mm, ci])))
    res['kprop'][nm + f'|f{f}'] = d
json.dump(res, open(OUT + '/reach_slope.json', 'w'), indent=1, default=float)
print(json.dumps(res['law'], indent=1))
print(json.dumps(res['ceiling_inertness_at_constant_slope'], indent=1))
print(json.dumps(res['episode_speeds'], indent=1))
print(json.dumps(res['dwell_build_rate'], indent=1))
