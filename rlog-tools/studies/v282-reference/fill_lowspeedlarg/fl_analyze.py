"""fill_lowspeedlarg -- census, demand validity, per-cell torque-vs-V282 comparisons with route-cluster bootstrap + MDE.

Reads data/<route>.npz from fl_extract.py.  Writes out/census.json, out/demand_validity.json, out/compare.json,
out/compare_table.csv.  (figures: fl_figs.py)

Cells (all below 15 m/s, split 2.5-5 / 5-8 / 8-15 by block-median / event speed):
  ANGLE family  A15 / A45 / A90 : DEMAND |angle| >= 15 / 45 / 90 deg (cumulative).  Blocks: median |adl|; turns: peak P.
  RATE family   R10 (10-40) / R40 (>40) deg/s of DEMANDED steer rate.  Blocks: max |adr| in block; rate events: peak |adr|.
Census seconds are frame-level HO seconds with the same demand thresholds (angle: frame |adl|; rate: frame |adr|).
NOT A REFERENCE: reference group has < 30 HO s in the cell or < 2 routes contributing >= 2 s (census), or, for an event
metric, < 3 hands-off events or < 2 routes with events.
Bootstrap: two-level route-cluster (resample routes within group, then units within each drawn route), B = 1000.
MDE(80 % power, alpha 0.05 two-sided) = 2.80 x bootstrap SE of the difference.
"""
import sys, json, os, csv
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE)
import v282cmp as V

HERE = BASE + '/fill_lowspeedlarg'
DATA = HERE + '/data'; OUT = HERE + '/out'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)
B = 1000
VB = [2.5, 5.0, 8.0, 15.0]; VBN = ['2.5-5', '5-8', '8-15']
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
DOM = '0000006c--2bc842dbac'
COV = 0.7

# ---------------------------------------------------------------- load
RT = {}
for rk, m in V.ROUTES.items():
    D = np.load(f'{DATA}/{rk}.npz', allow_pickle=False)
    meta = json.loads(str(D['meta']))
    bl = json.loads(str(D['BL']))
    run = 0; prev = None
    for b in bl:
        if prev is None or b['i0'] - prev != 128:
            run += 1
        b['run'] = run; prev = b['i0']
    RT[rk] = dict(group=m['group'], meta=meta, cen={k[4:]: D[k] for k in D.files if k.startswith('cen_')},
                  BL=bl, DJ=D['DJ'], TE=json.loads(str(D['TE'])), RT=json.loads(str(D['RT'])))
GR = {g: [rk for rk, R in RT.items() if R['group'] == g] for g in GROUPS}
GR['V282pool'] = GR['V282'] + GR['V282old']


def vbin(v):
    return int(np.clip(np.searchsorted(VB, v, side='right') - 1, 0, 2)) if VB[0] <= v < VB[-1] else -1


CELLS = [('A15', 'ang', 15, 1e9), ('A45', 'ang', 45, 1e9), ('A90', 'ang', 90, 1e9), ('R10', 'rate', 10, 40), ('R40', 'rate', 40, 1e9)]


def cen_seconds(H, fam, lo, sb):
    """H: (3 speed, 4 angle [0,15,45,90), 3 rate [0,10,40)).  cumulative angle / banded rate."""
    if fam == 'ang':
        return float(H[sb, {15: 1, 45: 2, 90: 3}[lo]:, :].sum())
    return float(H[sb, :, {10: 1, 40: 2}[lo]].sum())


def in_cell_block(b, fam, lo, hi, sb):
    return vbin(b['v']) == sb and ((lo <= b['dang'] < hi) if fam == 'ang' else (lo <= b['drate_max'] < hi))


def in_cell_turn(e, fam, lo, hi, sb):
    return fam == 'ang' and vbin(e['v']) == sb and lo <= e['P'] < hi


def in_cell_rate(e, fam, lo, hi, sb):
    return fam == 'rate' and vbin(e['v']) == sb and lo <= e['peak_rate'] < hi


# ---------------------------------------------------------------- (1) census
census = {}
for g in GROUPS + ['V282pool']:
    members = GR[g]
    gc = {}
    for cname, fam, lo, hi in CELLS:
        for sb in range(3):
            per = {rk: cen_seconds(RT[rk]['cen']['ho_dem'], fam, lo, sb) for rk in members}
            raw = sum(cen_seconds(RT[rk]['cen']['raw_dem'], fam, lo, sb) for rk in members)
            ho2 = sum(cen_seconds(RT[rk]['cen']['ho2_dem'], fam, lo, sb) for rk in members)
            ach = sum(cen_seconds(RT[rk]['cen']['ho_ach'], fam, lo, sb) for rk in members)
            src, keyc, fn = ('TE', 'cov_all', in_cell_turn) if fam == 'ang' else ('RT', 'cov', in_cell_rate)
            ev = {rk: sum(1 for e in RT[rk][src] if fn(e, fam, lo, hi, sb)) for rk in members}
            evho = {rk: sum(1 for e in RT[rk][src] if fn(e, fam, lo, hi, sb) and e[keyc] >= COV) for rk in members}
            ho = sum(per.values()); nr = sum(1 for x in per.values() if x >= 2.0)
            gc[f'{cname}_{VBN[sb]}'] = dict(ho_s=ho, raw_s=raw, ho2_s=ho2, ach_ho_s=ach, n_routes=nr, per_route_s=per,
                                            events_all=sum(ev.values()), events_ho=sum(evho.values()), per_route_events_ho=evho,
                                            n_routes_events_ho=sum(1 for x in evho.values() if x > 0),
                                            hands_off_frac=ho / max(raw, 1e-9), reference_ok=bool(ho >= 30 and nr >= 2),
                                            share_dom=(per[DOM] / max(ho, 1e-9)) if DOM in per else None)
    census[g] = gc
json.dump(census, open(f'{OUT}/census.json', 'w'), indent=1)
print('census written', flush=True)


# ---------------------------------------------------------------- bootstrap machinery (vectorised)
def vals(us, kind, f):
    if kind == 'med':
        x = np.array([f(u) for u in us], float)
        return x[np.isfinite(x)][:, None] if len(x) else np.zeros((0, 1))
    x = np.array([f(u) for u in us], float).reshape(-1, 2)
    return x[np.all(np.isfinite(x), 1)]


def stat(X, kind, scale):
    if len(X) == 0:
        return np.nan
    if kind == 'med':
        return float(np.median(X[:, 0]))
    return float(scale * X[:, 0].sum() / X[:, 1].sum()) if X[:, 1].sum() > 0 else np.nan


def boot(arrs, kind, scale=1.0):
    arrs = [a for a in arrs if len(a)]
    est = stat(np.concatenate(arrs), kind, scale)
    reps = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(arrs), len(arrs))
        reps[b] = stat(np.concatenate([arrs[p][rng.integers(0, len(arrs[p]), len(arrs[p]))] for p in pick]), kind, scale)
    return est, reps


def M(key, norm=None):
    return ('med', (lambda u: u[key] / u[norm]) if norm else (lambda u: u[key]), 1.0)


def MX(key):
    return ('med', lambda u: u[key] - u['_d'], 1.0)


MET = [
    ('mode_ratio_1.8-3Hz', 4, 'BL', ('med', lambda u: u['mode_rms'] / (u['lf_rms'] + 2.0), 1.0), 'rms steer rate 1.8-3 Hz / (rms rate <1 Hz + 2 deg/s), 1.28 s block median'),
    ('hf_ratio_2-10Hz', 4, 'BL', ('med', lambda u: u['hf_rms'] / (u['lf_rms'] + 2.0), 1.0), 'rms steer rate 2-10 Hz / (rms rate <1 Hz + 2 deg/s), block median'),
    ('mode_rms_1.8-3Hz', 4, 'BL', M('mode_rms'), 'rms steer rate 1.8-3 Hz deg/s, block median'),
    ('hf_rms_2-10Hz', 4, 'BL', M('hf_rms'), 'rms steer rate 2-10 Hz deg/s, block median'),
    ('travel_conc', 4, 'BL', M('conc'), 'share of angle travel done by the fastest 10 % of frames, block median'),
    ('dwelljump_per100deg', 4, 'BL', ('ratio', lambda u: (u['n_dj'], u['travel']), 100.0), 'dwell-then-jump count per 100 deg of travel'),
    ('turn_lag_build_excess', 3, 'TE', MX('lag_build'), '50%-crossing lag on build minus route learned delay, s'),
    ('turn_lag_unwind_excess', 3, 'TE', MX('lag_unwind'), '50%-crossing lag on unwind minus route learned delay, s'),
    ('turn_lag_build', 3, 'TE', M('lag_build'), '50%-crossing lag on build, s (raw)'),
    ('turn_lag_unwind', 3, 'TE', M('lag_unwind'), '50%-crossing lag on unwind, s (raw)'),
    ('turn_gain_build', 3, 'TE', M('gain_build'), 'incremental gain wheel vs demand angle on build, lag aligned'),
    ('turn_gain_hold', 3, 'TE', M('gain_hold'), 'wheel / demand angle during hold'),
    ('turn_gain_unwind', 3, 'TE', M('gain_unwind'), 'incremental gain on unwind, lag aligned'),
    ('turn_caster_bias', 3, 'TE', M('caster_bias'), '(build err + unwind err)/2 / P, un-aligned; + = more turn than asked'),
    ('turn_caster_bias_pose', 3, 'TE', M('caster_bias_pose'), 'same with the livePose curvature angle'),
    ('turn_ret_overshoot', 3, 'TE', M('ret_over'), 'return-to-centre overshoot past the demand / P'),
    ('turn_settle_s', 3, 'TE', M('settle_s'), 'settle time after the demand returns (tol max(0.1P, 3 deg)), s'),
    ('turn_hf_rms', 4, 'TE', M('hf_rms'), 'rms steer rate 2-10 Hz over the turn, deg/s'),
    ('turn_mode_rms', 4, 'TE', M('mode_rms'), 'rms steer rate 1.8-3 Hz over the turn, deg/s'),
    ('rate_lag_excess', 5, 'RT', MX('rate_lag'), 'xcorr lag demanded->achieved steer rate minus route learned delay, s'),
    ('rate_lag', 5, 'RT', M('rate_lag'), 'xcorr lag demanded->achieved steer rate, s (raw)'),
    ('rate_gain', 5, 'RT', M('rate_gain'), 'slope achieved vs demanded rate, lag aligned'),
    ('rate_peak_ratio', 5, 'RT', M('rate_peak_ratio'), 'peak achieved / peak demanded rate'),
    ('rate_overrun', 5, 'RT', M('rate_overrun'), 'max (achieved - demanded) rate after demand falls < 25 % of peak, / peak'),
    ('rate_rough', 5, 'RT', M('rough'), 'rms (achieved - demanded rate) 1-5 Hz / peak demanded rate'),
    ('rate_travel_ratio', 5, 'RT', M('travel_ratio'), 'achieved / demanded angle change over the transient'),
    ('rate_conc', 5, 'RT', M('conc'), 'travel concentration inside the event window'),
    ('rate_hf_per_peak', 5, 'RT', M('hf_rms', 'peak_rate'), 'rms 2-10 Hz steer rate / peak demanded rate'),
    ('rate_mode_per_peak', 5, 'RT', M('mode_rms', 'peak_rate'), 'rms 1.8-3 Hz steer rate / peak demanded rate'),
]


def units(group_routes, src, fam, lo, hi, sb, drop=()):
    out = {}
    for rk in group_routes:
        if rk in drop:
            continue
        R = RT[rk]; d = R['meta']['d']
        if src == 'BL':
            us = [b for b in R['BL'] if in_cell_block(b, fam, lo, hi, sb)]
        elif src == 'TE':
            us = [dict(e, _d=d) for e in R['TE'] if in_cell_turn(e, fam, lo, hi, sb) and e['cov_all'] >= COV]
        else:
            us = [dict(e, _d=d) for e in R['RT'] if in_cell_rate(e, fam, lo, hi, sb) and e['cov'] >= COV]
        out[rk] = us
    return out


# ---------------------------------------------------------------- (2) demand validity
# statistic: amplitude-matched mean difference of log(rms desiredCurvature 1-5 Hz) per 1.28 s block (v >= 2.5 m/s floor),
# strata = pooled quartiles of mean |desiredCurvature < 1 Hz| inside the cell.  Null: permute GROUP LABELS OF WHOLE RUNS
# (a run = contiguous hands-off blocks), 2000 permutations.  Plus route-cluster bootstrap CI and an MDE.
def dv_prep(ua, ub, edges):
    y, q, run, side, rte = [], [], [], [], []
    rid = 0
    for s_, grp in ((0, ua), (1, ub)):
        for rk, us in grp.items():
            rmap = {}
            for bb in us:
                if bb['run'] not in rmap:
                    rmap[bb['run']] = rid; rid += 1
                y.append(np.log(bb['curv_hf'] + 1e-7))
                q.append(int(np.clip(np.searchsorted(edges, bb['curv_lfabs'], side='right') - 1, 0, 3)))
                run.append(rmap[bb['run']]); side.append(s_); rte.append(rk)
    return np.array(y), np.array(q), np.array(run), np.array(side), np.array(rte)


def dv_stat(y, q, lab):
    diffs, ws = [], []
    for k in range(4):
        m = q == k
        a, c = y[m & (lab == 0)], y[m & (lab == 1)]
        if len(a) >= 3 and len(c) >= 3:
            diffs.append(a.mean() - c.mean()); ws.append(min(len(a), len(c)))
    return float(np.average(diffs, weights=ws)) if diffs else np.nan


demand = {}
for tg, ref in [(t, r) for t in ['T64', 'T64B', 'T5', 'T4'] for r in ['V282', 'V282pool']] + [('V282old', 'V282')]:
    for cname, fam, lo, hi in CELLS:
        for sb in range(3):
            ua = units(GR[tg], 'BL', fam, lo, hi, sb); ub = units(GR[ref], 'BL', fam, lo, hi, sb)
            nA = sum(len(u) for u in ua.values()); nB = sum(len(u) for u in ub.values())
            key = f'{tg}-{ref}_{cname}_{VBN[sb]}'
            if nA < 10 or nB < 10:
                demand[key] = dict(n_blocks=(nA, nB), ratio=None); continue
            edges = np.percentile([bb['curv_lfabs'] for u in list(ua.values()) + list(ub.values()) for bb in u], [0, 25, 50, 75, 100])
            edges[-1] += 1
            y, q, run, side, rte = dv_prep(ua, ub, edges)
            st = dv_stat(y, q, side)
            run_side = np.zeros(run.max() + 1, int); run_side[run] = side
            null = np.array([dv_stat(y, q, rng.permutation(run_side)[run]) for _ in range(2000)])
            null = null[np.isfinite(null)]
            pval = float((np.sum(np.abs(null) >= abs(st)) + 1) / (len(null) + 1)) if np.isfinite(st) else None
            ka = [k for k in ua if ua[k]]; kb = [k for k in ub if ub[k]]
            reps = []
            for _ in range(400):
                pa = rng.choice(ka, len(ka)); pb = rng.choice(kb, len(kb))
                idx = np.concatenate([np.where((rte == k) & (side == 0))[0] for k in pa] + [np.where((rte == k) & (side == 1))[0] for k in pb])
                reps.append(dv_stat(y[idx], q[idx], side[idx]))
            reps = np.array(reps); reps = reps[np.isfinite(reps)]
            demand[key] = dict(n_blocks=(nA, nB), n_runs=(int(run_side.size - run_side.sum()), int(run_side.sum())),
                               routes=(len(ka), len(kb)), log_ratio=st, ratio=float(np.exp(st)) if np.isfinite(st) else None,
                               p_perm_run=pval,
                               ci_route=[float(np.exp(np.percentile(reps, 2.5))), float(np.exp(np.percentile(reps, 97.5)))] if len(reps) > 20 else None,
                               mde_ratio=float(np.exp(2.8 * np.std(reps))) if len(reps) > 20 else None)
json.dump(demand, open(f'{OUT}/demand_validity.json', 'w'), indent=1)
print('demand validity: ratio of 1-5 Hz desired-curvature rms (target/ref), amplitude matched; p = run-label permutation')
for k, d in demand.items():
    if d.get('ratio') is None:
        continue
    print(f"  {k:34s} ratio {d['ratio']:.2f} p {d['p_perm_run']:.3f} routeCI {np.round(d['ci_route'], 2) if d['ci_route'] else None} "
          f"MDE x{d['mde_ratio'] if d['mde_ratio'] is None else round(d['mde_ratio'], 2)} blocks {d['n_blocks']} runs {d['n_runs']}", flush=True)

# ---------------------------------------------------------------- (3) comparisons
REFS = ['V282', 'V282old', 'V282pool', 'V282_LOO']
TARGETS = ['T64', 'T64B', 'T5', 'T4']
compare = {}
rows = []
for cname, fam, lo, hi in CELLS:
    for sb in range(3):
        cell = f'{cname}_{VBN[sb]}'
        for mname, note, src, (kind, fx, scale), desc in MET:
            if (src == 'TE' and fam != 'ang') or (src == 'RT' and fam != 'rate'):
                continue
            est = {}
            for g in GROUPS + ['V282pool', 'V282_LOO']:
                routes_ = GR['V282'] if g == 'V282_LOO' else GR[g]
                drop = (DOM,) if g == 'V282_LOO' else ()
                U = units(routes_, src, fam, lo, hi, sb, drop)
                arrs = [vals(u, kind, fx) for u in U.values()]
                n = int(sum(len(x) for x in arrs)); nr = int(sum(1 for x in arrs if len(x)))
                if n < (3 if src != 'BL' else 5):
                    est[g] = dict(n=n, n_routes=nr, est=None, reps=None); continue
                e_, reps = boot(arrs, kind, scale)
                est[g] = dict(n=n, n_routes=nr, est=e_, reps=reps)
            refc = {r: census['V282' if r == 'V282_LOO' else r][cell] for r in REFS}
            cres = dict(note=note, src=src, desc=desc,
                        groups={g: dict(n=v['n'], n_routes=v['n_routes'], est=v['est'],
                                        ci=[float(np.nanpercentile(v['reps'], 2.5)), float(np.nanpercentile(v['reps'], 97.5))] if v['reps'] is not None else None)
                                for g, v in est.items()},
                        diffs={})
            for t, r in [(t, r) for t in TARGETS for r in REFS] + [('V282old', 'V282')]:
                a, b = est.get(t), est.get(r)
                if not a or not b or a['est'] is None or b['est'] is None:
                    cres['diffs'][f'{t}-{r}'] = None; continue
                dr = a['reps'] - b['reps']; dr = dr[np.isfinite(dr)]
                if len(dr) < 50:
                    cres['diffs'][f'{t}-{r}'] = None; continue
                se = float(np.std(dr)); diff = float(a['est'] - b['est'])
                ci = [float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))]
                need_routes = 1 if r == 'V282_LOO' else 2
                cen_ok = refc[r]['reference_ok'] if r != 'V282_LOO' else (refc[r]['ho_s'] - (refc[r]['per_route_s'].get(DOM, 0)) >= 30)
                ref_ok = bool(cen_ok and b['n'] >= 3 and b['n_routes'] >= need_routes)
                d_ = dict(diff=diff, ci=ci, se=se, mde80=2.8 * se, effect_over_mde=float(abs(diff) / (2.8 * se)) if se > 0 else None,
                          excludes0=bool(ci[0] > 0 or ci[1] < 0), ref_ok=ref_ok, target_routes=a['n_routes'])
                cres['diffs'][f'{t}-{r}'] = d_
                rows.append(dict(cell=cell, metric=mname, note=note, pair=f'{t}-{r}', target_est=a['est'], ref_est=b['est'],
                                 n_target=a['n'], routes_target=a['n_routes'], n_ref=b['n'], routes_ref=b['n_routes'],
                                 diff=diff, ci_lo=ci[0], ci_hi=ci[1], mde80=2.8 * se,
                                 effect_over_mde=abs(diff) / (2.8 * se) if se > 0 else np.nan,
                                 excludes0=d_['excludes0'], ref_ok=ref_ok))
            compare[f'{cell}|{mname}'] = cres
        print('done cell', cell, flush=True)

json.dump(compare, open(f'{OUT}/compare.json', 'w'), indent=1, default=float)
with open(f'{OUT}/compare_table.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
print('rows', len(rows))
