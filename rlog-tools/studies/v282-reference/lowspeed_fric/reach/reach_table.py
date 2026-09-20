"""reach stage 2: the reach table + validation + slope-vs-stiffness + the highway check."""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import k_of_v, band, HOLD_LEVEL_BP, HOLD_LEVEL_V  # noqa: E402
from ss_load import boot_ci                                   # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
D = np.load(OUT + '/reach_rows.npz', allow_pickle=True)
R = list(D['rows']); CANDS = [tuple(c) for c in D['cands']]
NC = len(CANDS)
F_TODAY = 0.015
SHORT = {'2-8': 0.033, '8-15': 0.026}

col = lambda k: np.array([r[k] for r in R])
mat = lambda k: np.stack([r[k] for r in R])
v = col('v'); route = col('route'); kind = col('kind'); aa_abs = col('abs_aa'); dwell = col('dwell_s')
z0 = mat('z0'); zbk = mat('zbk'); dt = mat('dt_early'); tr = mat('tr_early'); ever = mat('ever')
z0t = col('z0_today')[:, None]; zbkt = col('zbk_today')[:, None]
cmd_bk = col('cmd_bk'); cmd_i0 = col('cmd_i0')
dz = zbk - z0
ex = zbk - zbkt
dzt = (zbkt - z0t)[:, 0]

res = {}

# ---------- validation ----------
i_base = {g: CANDS.index((0.015, 3.0, g)) for g in ['g6_10', 'g8_12', 'g10_12', 'flat']}
val = {}
for g, ci in i_base.items():
    lim = {'g6_10': 6.0, 'g8_12': 8.0, 'g10_12': 8.0, 'flat': 8.0}[g]
    m = v < lim
    val[f'baseline_{g}_max_abs_err_z0_below_{lim}'] = float(np.max(np.abs(z0[m, ci] - z0t[m, 0])))
    val[f'baseline_{g}_max_abs_err_zbk_below_{lim}'] = float(np.max(np.abs(zbk[m, ci] - zbkt[m, 0])))
for lo, hi in [(2, 8), (8, 15)]:
    m = (v >= lo) & (v < hi)
    val[f'today_dz_mean_{lo}-{hi}'] = float(np.mean(dzt[m]))
    val[f'today_zbk_mean_{lo}-{hi}'] = float(np.mean(zbkt[m, 0]))
    val[f'today_z0_mean_{lo}-{hi}'] = float(np.mean(z0t[m, 0]))
    val[f'today_frac_z0_at_ceiling_{lo}-{hi}'] = float(np.mean(np.abs(z0t[m, 0]) > 0.0149))
    val[f'logged_cmd_build_mean_{lo}-{hi}'] = float(np.mean((cmd_bk - cmd_i0)[m]))
    val[f'n_{lo}-{hi}'] = int(m.sum())
res['validation'] = val

# ---------- slope vs hold stiffness ----------
def slope_rows():
    out = {}
    for (f, b, g) in CANDS:
        out[f'{f:.3f}|{b:.1f}'] = f / b
    return out


VS = [2.0, 4.0, 6.0, 8.0, 15.0, 19.0, 22.0, 26.0]
kk = {x: float(k_of_v(x)) for x in VS}
klev = {x: float(k_of_v(x) * np.interp(x, HOLD_LEVEL_BP, HOLD_LEVEL_V)) for x in VS}
res['stiffness'] = dict(k=kk, k_level=klev, band_today={str(x): float(band(x, True)) for x in VS},
                        slope_today={str(x): F_TODAY / float(band(x, True)) for x in VS})

# ---------- reach per candidate ----------
tab = []
for ci, (f, b, g) in enumerate(CANDS):
    row = dict(f=f, band=b, gate=g, slope=f / b)
    # over-delivery ratios at the candidate's own effective parameters
    for x in [2.0, 4.0, 6.0, 8.0]:
        gv = 0.0 if g == 'flat' else float(np.clip((x - {'g6_10': 6.0, 'g8_12': 8.0, 'g10_12': 10.0}[g]) /
                                                   ({'g6_10': 4.0, 'g8_12': 4.0, 'g10_12': 2.0}[g]), 0, 1))
        fe = f + gv * (F_TODAY - f); be = b + gv * (float(band(x, True)) - b)
        row[f'slope_{int(x)}'] = fe / be
        row[f'slope_over_k_{int(x)}'] = (fe / be) / kk[x]
        row[f'slope_over_klev_{int(x)}'] = (fe / be) / klev[x]
    row['highway_untouched'] = bool(g != 'flat')
    for x in [15.0, 19.0, 26.0]:
        if g == 'flat':
            row[f'slope_{int(x)}'] = f / b
            row[f'slope_over_klev_{int(x)}'] = (f / b) / klev[x]
        else:
            row[f'slope_{int(x)}'] = F_TODAY / float(band(x, True))
            row[f'slope_over_klev_{int(x)}'] = row[f'slope_{int(x)}'] / klev[x]
    for lo, hi in [(2, 8), (8, 15)]:
        m = (v >= lo) & (v < hi)
        s = SHORT[f'{lo}-{hi}']
        row[f'dz_{lo}_{hi}'] = float(np.median(dz[m, ci]))
        row[f'ex_{lo}_{hi}'] = float(np.median(ex[m, ci]))
        row[f'zbk_{lo}_{hi}'] = float(np.median(zbk[m, ci]))
        row[f'z0_{lo}_{hi}'] = float(np.median(z0[m, ci]))
        row[f'reach_acc_{lo}_{hi}'] = float(np.median(dz[m, ci]) / s)
        row[f'reach_lvl_{lo}_{hi}'] = float(np.median(zbk[m, ci]) / s)
        row[f'reach_ex_{lo}_{hi}'] = float(np.median(ex[m, ci]) / s)
        row[f'dt_{lo}_{hi}'] = float(np.median(dt[m, ci]))
        row[f'dt_p90_{lo}_{hi}'] = float(np.percentile(dt[m, ci], 90))
        row[f'tr_{lo}_{hi}'] = float(np.median(tr[m, ci]))
        row[f'nohit_{lo}_{hi}'] = float(np.mean(~ever[m, ci]))
    tab.append(row)
res['table'] = tab

# ---------- finalists: CI + breakdowns ----------
def detail(ci):
    d = {'cand': CANDS[ci]}
    for lo, hi in [(2, 5), (5, 8), (2, 8), (8, 15)]:
        m = (v >= lo) & (v < hi)
        if m.sum() < 5:
            continue
        s = SHORT['2-8' if hi <= 8 else '8-15']
        d[f'{lo}-{hi}'] = dict(
            n=int(m.sum()),
            z0=boot_ci(z0[m, ci], route[m], np.median), zbk=boot_ci(zbk[m, ci], route[m], np.median),
            dz=boot_ci(dz[m, ci], route[m], np.median), ex=boot_ci(ex[m, ci], route[m], np.median),
            reach_acc=boot_ci(dz[m, ci] / s, route[m], np.median),
            reach_ex=boot_ci(ex[m, ci] / s, route[m], np.median),
            dt_early=boot_ci(dt[m, ci], route[m], np.median),
            dt_early_p90=float(np.percentile(dt[m, ci], 90)),
            travel_early=boot_ci(tr[m, ci], route[m], np.median),
            frac_dt_ge_100ms=float(np.mean(dt[m, ci] >= 0.10)),
            frac_no_earlier=float(np.mean(~ever[m, ci])))
        for kd in ['rev', 'cont', 'rest']:
            mm = m & (kind == kd)
            if mm.sum() >= 8:
                d[f'{lo}-{hi}|{kd}'] = dict(n=int(mm.sum()), dz=float(np.median(dz[mm, ci])),
                                            ex=float(np.median(ex[mm, ci])),
                                            reach_acc=float(np.median(dz[mm, ci]) / s),
                                            reach_ex=float(np.median(ex[mm, ci]) / s),
                                            dt=float(np.median(dt[mm, ci])))
        for an, am in (('aa<5', aa_abs < 5), ('aa>=5', aa_abs >= 5)):
            mm = m & am
            if mm.sum() >= 8:
                d[f'{lo}-{hi}|{an}'] = dict(n=int(mm.sum()), dz=float(np.median(dz[mm, ci])),
                                            ex=float(np.median(ex[mm, ci])), dt=float(np.median(dt[mm, ci])))
    return d


res['detail'] = {}
FIN = [(0.015, 3.0, 'g8_12'), (0.033, 3.0, 'g8_12'), (0.033, 2.0, 'g8_12'), (0.030, 2.0, 'g8_12'),
       (0.030, 3.0, 'g8_12'), (0.036, 2.5, 'g8_12'), (0.045, 3.0, 'g8_12'), (0.025, 1.5, 'g8_12'),
       (0.033, 3.0, 'g6_10'), (0.033, 3.0, 'g10_12'), (0.033, 3.0, 'flat'), (0.020, 3.0, 'g8_12')]
for c in FIN:
    res['detail'][str(c)] = detail(CANDS.index(c))

json.dump(res, open(OUT + '/reach_table.json', 'w'), indent=1, default=float)
print(json.dumps(res['validation'], indent=1))
print(json.dumps(res['stiffness'], indent=1))
