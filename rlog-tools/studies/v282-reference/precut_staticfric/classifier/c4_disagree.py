"""classifier stage 4: READ the disagreements, and test the contrast the FAIL clause rests on.

(a) Every disagreement cell of E/R/D/T characterised by the physics available in the log:
    where the wheel is, where the demand is, which way each is moving, whether the demand crossed
    centre inside the dwell.
(b) The OUTWARD question in the WHEEL's frame: dose_out = sign(aa_bk) * z(b3).  The term's s_a is odd in
    the DEMAND's angle, so whenever angdes and aa sit on opposite sides of centre a firing term pushes the
    wheel TOWARD / THROUGH centre, i.e. it doses a return.
(c) Paired route-cluster bootstrap of the contrast the pre-registration uses:
       delta = os30_p90(return) - os30_p90(depart),  per classifier, resampling routes jointly.
(d) A leverage bound on the return-class statistics: re-percentile the return class after replacing the
    DOSED episodes' values with the depart class's own distribution.  This is ARITHMETIC LEVERAGE, not a
    prediction of what the car would do.
"""
import os, json, glob, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
PRE = 150
TAG = os.environ.get('TAG', 'A')
LEVEL = 0.020
rows = json.load(open(f'{OUT}/c1_rows.json'))
key = {(r['route'], r['i0'], r['bk']): q for q, r in enumerate(rows)}
N = len(rows)
os30 = np.full(N, np.nan)
for f in sorted(glob.glob(f'{SS}/out/*_ss.npz')):
    D = np.load(f, allow_pickle=True); EP = list(D['EP'])
    if not EP:
        continue
    aa = D['aa']; ad = D['ad']
    for q, e in enumerate(EP):
        kk = (e['route'], int(e['i0']), int(e['bk']))
        if kk in key:
            os30[key[kk]] = float(e['sjump']) * (aa[q, PRE + 30] - ad[q, PRE + 30])
    del D

col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); aa_bk = colf('aa_bk'); aa_i0 = colf('aa_i0'); sj = colf('sj'); sdem = colf('sdem')
dwell = colf('dwell_s'); slip = colf('slip'); kind = col('kind'); route = col('route'); dem = colf('dem')
ang_bk = colf(f'angdes_bk_{TAG}'); ang_i0 = colf(f'angdes_i0_{TAG}'); rd_bk = colf(f'rd_bk_{TAG}')
gate_bk = colf(f'gate_bk_{TAG}'); gate_frac = colf(f'gate_frac_{TAG}'); zc = colf(f'zc_{TAG}')
dose_bk = colf(f'dose_bk_{TAG}'); dose_out = colf(f'dose_out_{TAG}'); sw = colf(f'angdes_swing_{TAG}')
sgn_aa = np.sign(aa_bk)
dep = {'E': sj == sgn_aa, 'R': (sgn_aa == sdem) | (np.abs(aa_bk) < 0.5),
       'D': np.sign(ang_bk) == sgn_aa, 'T': gate_bk > 1e-3, 'Tm': gate_frac >= 0.5}
DOSED = np.abs(dose_bk) >= 0.25 * LEVEL
LOW = (v >= 2) & (v < 8)
R = {'tag': TAG}

# ---------------- (a) characterise the cells ----------------
def describe(m):
    return dict(n=int(m.sum()), v_p50=float(np.median(v[m])), abs_aa_p50=float(np.median(np.abs(aa_bk[m]))),
                frac_absaa_lt_05=float(np.mean(np.abs(aa_bk[m]) < 0.5)),
                frac_absaa_lt_2=float(np.mean(np.abs(aa_bk[m]) < 2.0)),
                abs_angdes_p50=float(np.median(np.abs(ang_bk[m]))),
                frac_absangdes_lt_1=float(np.mean(np.abs(ang_bk[m]) < 1.0)),
                frac_opposite_sides=float(np.mean(np.sign(ang_bk[m]) != sgn_aa[m])),
                frac_demand_crossed_centre=float(np.mean(zc[m] > 0)),
                rd_bk_p50=float(np.median(rd_bk[m])), abs_rd_p50=float(np.median(np.abs(rd_bk[m]))),
                frac_absrd_lt_1=float(np.mean(np.abs(rd_bk[m]) < 1.0)),
                frac_sdem_eq_sj=float(np.mean(sdem[m] == sj[m])),
                frac_rd_sign_eq_sdem=float(np.mean(np.sign(rd_bk[m]) == sdem[m])),
                angdes_swing_p50=float(np.median(sdem[m] * sw[m])),
                kind=dict(rest=float(np.mean(kind[m] == 'rest')), cont=float(np.mean(kind[m] == 'cont')),
                          rev=float(np.mean(kind[m] == 'rev'))),
                dose_bk_p50=float(np.median(dose_bk[m])), dose_out_p50=float(np.median(dose_out[m])),
                dwell_p50=float(np.median(dwell[m])), os30_p50=float(np.median(os30[m])),
                os30_p90=float(np.percentile(os30[m], 90)), slip_p50=float(np.median(slip[m])),
                routes=int(len(set(route[m]))))


CELLS = {}
for a, b in [('E', 'T'), ('R', 'T'), ('E', 'R'), ('D', 'T'), ('R', 'D')]:
    for la, A in (('dep', dep[a]), ('ret', ~dep[a])):
        for lb, B in (('dep', dep[b]), ('ret', ~dep[b])):
            m = LOW & A & B
            if m.sum() >= 1:
                CELLS[f'{a}{la}|{b}{lb}'] = describe(m)
R['cells'] = CELLS
KEYS = ['n', 'routes', 'v_p50', 'abs_aa_p50', 'frac_absaa_lt_05', 'abs_angdes_p50', 'frac_opposite_sides',
        'frac_demand_crossed_centre', 'abs_rd_p50', 'frac_absrd_lt_1', 'frac_sdem_eq_sj',
        'dose_bk_p50', 'dose_out_p50', 'dwell_p50', 'os30_p50', 'os30_p90', 'slip_p50']
print('=== DISAGREEMENT CELLS (2-8 m/s) ===')
print(f'{"cell":16s}' + ''.join(f'{k[:11]:>12s}' for k in KEYS))
for k, d in CELLS.items():
    print(f'{k:16s}' + ''.join(f'{d[x]:12.3f}' if isinstance(d[x], float) else f'{d[x]:12d}' for x in KEYS))

# ---------------- (b) the outward question in the WHEEL's frame ----------------
R['outward'] = {}
for bn, v0, v1 in (('2-5', 2, 5), ('5-8', 5, 8), ('2-8', 2, 8), ('8-15', 8, 15)):
    m = (v >= v0) & (v < v1)
    f = m & dep['T']
    R['outward'][bn] = dict(
        n=int(m.sum()), n_fires=int(f.sum()),
        frac_fires=float(np.mean(dep['T'][m])),
        among_firing_frac_pushes_wheel_INWARD=float(np.mean(dose_out[f] < 0)),
        among_firing_frac_pushes_wheel_OUTWARD=float(np.mean(dose_out[f] > 0)),
        among_firing_dose_out_p50=float(np.median(dose_out[f])),
        among_firing_dose_out_p10=float(np.percentile(dose_out[f], 10)),
        among_firing_frac_opposite_sides=float(np.mean(np.sign(ang_bk[f]) != sgn_aa[f])),
        among_firing_frac_wheel_near_centre=float(np.mean(np.abs(aa_bk[f]) < 2.0)),
        # time-weighted version over every hands-off frame in the bin is stage 5
    )
print('\n=== (b) DOES A FIRING TERM PUSH THE WHEEL OUTWARD? (episode release samples) ===')
print(json.dumps(R['outward'], indent=1))

# ---------------- (c) paired bootstrap of the contrast ----------------
def paired(cl, fn, nb=4000, seed=1):
    m = LOW
    u = np.unique(route[m]); rng = np.random.default_rng(seed)
    idx = {c: np.where(m & (route == c))[0] for c in u}
    A = dep[cl]
    est = fn(os30[m & A]), fn(os30[m & ~A])
    bs = []
    for _ in range(nb):
        ii = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
        a = os30[ii][A[ii]]; b = os30[ii][~A[ii]]
        if len(a) > 4 and len(b) > 4:
            bs.append(fn(b) - fn(a))
    bs = np.array(bs)
    return dict(depart=float(est[0]), ret=float(est[1]), delta=float(est[1] - est[0]),
                delta_ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                frac_delta_gt0=float(np.mean(bs > 0)), nb=len(bs))


p90 = lambda x: np.percentile(x, 90)
R['contrast'] = {}
for cl in ['E', 'R', 'D', 'T', 'Tm']:
    R['contrast'][f'{cl}|os30_p90'] = paired(cl, p90)
    R['contrast'][f'{cl}|os30_p50'] = paired(cl, np.median)
print('\n=== (c) PAIRED ROUTE-CLUSTER BOOTSTRAP: return - depart ===')
for k, d in R['contrast'].items():
    print(f'{k:16s} depart {d["depart"]:7.3f}  return {d["ret"]:7.3f}  delta {d["delta"]:+7.3f} '
          f'[{d["delta_ci"][0]:+7.3f},{d["delta_ci"][1]:+7.3f}]  P(delta>0) {d["frac_delta_gt0"]:.3f}')

# ---------------- (d) arithmetic leverage bound ----------------
R['leverage_bound'] = {}
for cl in ['R', 'E']:
    m = LOW & ~dep[cl]
    dm = LOW & dep[cl]
    for stat, fn, tgt in (('dwell_p50', np.median, dwell), ('os30_p90', p90, os30), ('os30_p50', np.median, os30)):
        x = tgt[m].copy(); d = DOSED[m]
        base = float(fn(x))
        # replace every dosed return episode's value with the depart class's matching quantile
        rng = np.random.default_rng(5)
        sub = rng.choice(tgt[dm], size=int(d.sum()), replace=True)
        x2 = x.copy(); x2[d] = sub
        # and the extreme case: every dosed return episode takes the depart class's p50 exactly
        x3 = x.copy(); x3[d] = float(np.median(tgt[dm]))
        R['leverage_bound'][f'{cl}|{stat}'] = dict(
            n=int(m.sum()), n_dosed=int(d.sum()), base=base,
            if_dosed_resampled_from_depart=float(fn(x2)),
            if_dosed_all_at_depart_median=float(fn(x3)),
            if_dosed_dropped=float(fn(x[~d])))
print('\n=== (d) ARITHMETIC LEVERAGE of the dosed episodes on the return statistics ===')
print(json.dumps(R['leverage_bound'], indent=1))
json.dump(R, open(f'{OUT}/c4_disagree_{TAG}.json', 'w'), indent=1)
