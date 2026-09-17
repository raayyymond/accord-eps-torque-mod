"""Matched (speed x activity) comparison of AR-pole zeta and e4->sr coherence, per-route bootstrap,
leave-dominant-route-out, route-pair matrix, and same-EPS control comparisons (V282 vs V282old;
T64 vs T64B/T5/T4) -- the confound test for 'lightly-damped-3hz-closed-loop-mode'.
"""
import sys, glob, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__lightlydampe__confound'
rng = np.random.default_rng(13)

# columns: vv, act, sband, aband, cell, f_ld, z_ld, coh183, e4_share, sr_share, npoles
COLS = ['vv', 'act', 'sband', 'aband', 'cell', 'f_ld', 'z_ld', 'coh183', 'e4_share', 'sr_share', 'npoles']

DATA = {}
for f in glob.glob(f'{HERE}/data_*.npz'):
    d = np.load(f, allow_pickle=True)
    DATA[str(d['route'])] = dict(group=str(d['group']), R=d['R'])

GROUPS = {g: [rk for rk, d in DATA.items() if d['group'] == g] for g in set(d['group'] for d in DATA.values())}
print('routes per group:', {g: len(v) for g, v in GROUPS.items()})
DOMINANT = '0000006c--2bc842dbac'


def col(R, name):
    return R[:, COLS.index(name)]


def matched_diff(Grks, Vrks, metric='z_ld', min_n=3):
    """weighted matched additive difference median_G,cell - median_V,cell, weight=min(n_G,n_V) per cell."""
    Gc = np.concatenate([col(DATA[r]['R'], 'cell') for r in Grks]) if Grks else np.array([])
    Gm = np.concatenate([col(DATA[r]['R'], metric) for r in Grks]) if Grks else np.array([])
    Vc = np.concatenate([col(DATA[r]['R'], 'cell') for r in Vrks]) if Vrks else np.array([])
    Vm = np.concatenate([col(DATA[r]['R'], metric) for r in Vrks]) if Vrks else np.array([])
    num = den = 0.0
    ncells = 0
    for c in np.intersect1d(np.unique(Gc[np.isfinite(Gc)]), np.unique(Vc[np.isfinite(Vc)])):
        a = Gm[(Gc == c) & np.isfinite(Gm)]; b = Vm[(Vc == c) & np.isfinite(Vm)]
        if len(a) < min_n or len(b) < min_n:
            continue
        w = min(len(a), len(b))
        num += w * (np.median(a) - np.median(b)); den += w; ncells += 1
    if den == 0:
        return np.nan, 0, 0
    return float(num / den), int(den), ncells


def boot_matched(Grks, Vrks, metric='z_ld', B=800):
    est, w, nc = matched_diff(Grks, Vrks, metric)
    reps = []
    for _ in range(B):
        gk = list(rng.choice(Grks, len(Grks), replace=True)) if len(Grks) > 1 else Grks
        vk = list(rng.choice(Vrks, len(Vrks), replace=True)) if len(Vrks) > 1 else Vrks
        # piece-resample within each chosen route too
        Gd, Vd = [], []
        for r in gk:
            Rr = DATA[r]['R']; i = rng.integers(0, len(Rr), len(Rr))
            Gd.append(Rr[i])
        for r in vk:
            Rr = DATA[r]['R']; i = rng.integers(0, len(Rr), len(Rr))
            Vd.append(Rr[i])
        Gc = np.concatenate([col(x, 'cell') for x in Gd]) if Gd else np.array([])
        Gm = np.concatenate([col(x, metric) for x in Gd]) if Gd else np.array([])
        Vc = np.concatenate([col(x, 'cell') for x in Vd]) if Vd else np.array([])
        Vm = np.concatenate([col(x, metric) for x in Vd]) if Vd else np.array([])
        num = den = 0.0
        for c in np.intersect1d(np.unique(Gc[np.isfinite(Gc)]), np.unique(Vc[np.isfinite(Vc)])):
            a = Gm[(Gc == c) & np.isfinite(Gm)]; b = Vm[(Vc == c) & np.isfinite(Vm)]
            if len(a) < 3 or len(b) < 3:
                continue
            w = min(len(a), len(b))
            num += w * (np.median(a) - np.median(b)); den += w
        if den > 0:
            reps.append(num / den)
    ci = [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))] if len(reps) > 50 else [np.nan, np.nan]
    return dict(est=est, w=w, ncells=nc, ci=ci, n_reps=len(reps))


def stratum_filter(Rr, st):
    v = col(Rr, 'vv')
    if st == 'all':
        return np.ones(len(v), bool)
    if st == 'lt15':
        return v < 15
    if st == 'ge15':
        return v >= 15
    raise ValueError(st)


class FR:
    """wrap route->filtered-copy so matched_diff/boot_matched (which read DATA[r]['R']) can use a stratum."""


def with_stratum(routes_map, st):
    """returns a dict route->R filtered to stratum st, monkeypatched into a temp DATA-like scope."""
    return {r: DATA[r]['R'][stratum_filter(DATA[r]['R'], st)] for r in routes_map}


def matched_diff_sub(Grks, Vrks, RR, metric='z_ld', min_n=3):
    Gc = np.concatenate([col(RR[r], 'cell') for r in Grks]) if Grks else np.array([])
    Gm = np.concatenate([col(RR[r], metric) for r in Grks]) if Grks else np.array([])
    Vc = np.concatenate([col(RR[r], 'cell') for r in Vrks]) if Vrks else np.array([])
    Vm = np.concatenate([col(RR[r], metric) for r in Vrks]) if Vrks else np.array([])
    num = den = 0.0; ncells = 0
    for c in np.intersect1d(np.unique(Gc[np.isfinite(Gc)]), np.unique(Vc[np.isfinite(Vc)])):
        a = Gm[(Gc == c) & np.isfinite(Gm)]; b = Vm[(Vc == c) & np.isfinite(Vm)]
        if len(a) < min_n or len(b) < min_n:
            continue
        w = min(len(a), len(b))
        num += w * (np.median(a) - np.median(b)); den += w; ncells += 1
    if den == 0:
        return np.nan, 0, 0
    return float(num / den), int(den), ncells


def boot_matched_strat(Grks, Vrks, st, metric='z_ld', B=600):
    RR_full = {r: DATA[r]['R'] for r in set(Grks) | set(Vrks)}
    RRst = {r: RR_full[r][stratum_filter(RR_full[r], st)] for r in RR_full}
    est, w, nc = matched_diff_sub(Grks, Vrks, RRst, metric)
    reps = []
    for _ in range(B):
        gk = list(rng.choice(Grks, len(Grks), replace=True)) if len(Grks) > 1 else Grks
        vk = list(rng.choice(Vrks, len(Vrks), replace=True)) if len(Vrks) > 1 else Vrks
        RRb = {}
        for r in gk + vk:
            Rr = RRst[r]
            if len(Rr) == 0:
                RRb[r] = Rr; continue
            i = rng.integers(0, len(Rr), len(Rr)); RRb[r] = Rr[i]
        e, _, _ = matched_diff_sub(gk, vk, RRb, metric)
        if np.isfinite(e):
            reps.append(e)
    ci = [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))] if len(reps) > 50 else [np.nan, np.nan]
    return dict(est=est, w=w, ncells=nc, ci=ci, n_reps=len(reps))


V282 = GROUPS.get('V282', [])
V282old = GROUPS.get('V282old', [])
MINOR = [r for r in V282 if r != DOMINANT]
T64 = GROUPS.get('T64', [])
ALL_T = GROUPS.get('T64', []) + GROUPS.get('T64B', []) + GROUPS.get('T5', []) + GROUPS.get('T4', [])
ALL_T_GROUPS = ['T64', 'T64B', 'T5', 'T4']

results = {}

# === (1) headline: matched dzeta (torque - V282), all torque pooled, per stratum, pooled V282 vs minor-only vs dominant-only
print('\n=== (1) matched Delta-zeta (all torque pooled - V282), by stratum ===')
results['headline_zeta'] = {}
for st in ['all', 'lt15', 'ge15']:
    pooled = boot_matched_strat(ALL_T, V282, st)
    minor = boot_matched_strat(ALL_T, MINOR, st)
    dom = boot_matched_strat(ALL_T, [DOMINANT], st)
    results['headline_zeta'][st] = dict(pooled=pooled, minor_only=minor, dominant_only=dom)
    print(f"{st:6s} pooled dz={pooled['est']:+.3f}[{pooled['ci'][0]:+.3f},{pooled['ci'][1]:+.3f}] w{pooled['w']} nc{pooled['ncells']}  "
          f"minor dz={minor['est']:+.3f}[{minor['ci'][0]:+.3f},{minor['ci'][1]:+.3f}] w{minor['w']}  "
          f"dominant dz={dom['est']:+.3f}[{dom['ci'][0]:+.3f},{dom['ci'][1]:+.3f}] w{dom['w']}")

# === (2) same test on coherence 1.8-3 Hz and on variance shares (sanity: should track the original pooled numbers)
print('\n=== (2) matched Delta-coherence and Delta-variance-share (torque - V282) ===')
results['headline_other'] = {}
for metric in ['coh183', 'sr_share', 'e4_share']:
    row = {}
    for st in ['all', 'lt15', 'ge15']:
        row[st] = boot_matched_strat(ALL_T, V282, st, metric=metric)
    results['headline_other'][metric] = row
    print(metric, {st: (round(row[st]['est'], 4), [round(x, 4) for x in row[st]['ci']]) for st in row})

# === (3) route-pair matrix (every V282 route x every T64-family route), all-stratum matched dzeta
print('\n=== (3) route-pair matrix, dzeta, all stratum ===')
results['route_pair_matrix_zeta'] = {}
for vrk in V282:
    results['route_pair_matrix_zeta'][vrk] = {}
    for grk in ALL_T:
        e, w, nc = matched_diff([grk], [vrk], 'z_ld')
        results['route_pair_matrix_zeta'][vrk][grk] = dict(est=e, w=w, nc=nc)
    print(vrk, {g: (round(results['route_pair_matrix_zeta'][vrk][g]['est'], 3) if np.isfinite(results['route_pair_matrix_zeta'][vrk][g]['est']) else None,
                     results['route_pair_matrix_zeta'][vrk][g]['w']) for g in ALL_T})

# === (4) per-torque-group vs MINOR-only V282, all metrics, all strata -- robustness of each revision's result
print('\n=== (4) each torque group vs MINOR-only V282 reference ===')
results['per_group_minor_only'] = {}
for g in ALL_T_GROUPS:
    Grks = GROUPS.get(g, [])
    if not Grks:
        continue
    row = {}
    for st in ['all', 'lt15', 'ge15']:
        row[st] = boot_matched_strat(Grks, MINOR, st)
    results['per_group_minor_only'][g] = row
    print(g, {st: (round(row[st]['est'], 3), [round(x, 3) for x in row[st]['ci']], row[st]['w']) for st in row})

# === (5) CONTROL comparisons: same-EPS-family pairs that SHOULD show ~0 if route/fork/day noise alone
# explained a gap this size.  V282 vs V282old (both V282 EPS, different fork/day/road).  T64 vs each other
# torque revision (all V293 EPS, different fork revs/days/roads).
print('\n=== (5) CONTROLS: same-EPS-family route/fork/day gaps ===')
results['controls'] = {}
c1 = boot_matched_strat(V282old, V282, 'all')
results['controls']['V282old_vs_V282'] = c1
print('V282old vs V282 (both V282 EPS):', c1['est'], c1['ci'], 'w', c1['w'])
for g in ['T64B', 'T5', 'T4']:
    Grks = GROUPS.get(g, [])
    if not Grks:
        continue
    c = boot_matched_strat(Grks, T64, 'all')
    results['controls'][f'{g}_vs_T64'] = c
    print(f'{g} vs T64 (both V293 EPS):', c['est'], c['ci'], 'w', c['w'])

# === (6) leave-dominant-out on the CONTROL too (V282old vs MINOR V282) -- does the ~0 control survive?
c2 = boot_matched_strat(V282old, MINOR, 'all')
results['controls']['V282old_vs_V282minor'] = c2
print('V282old vs V282(minor only):', c2['est'], c2['ci'], 'w', c2['w'])

# === (7) cell-count diagnostics: how much speed x activity overlap actually exists between V282 and torque
print('\n=== (7) overlap diagnostics ===')
diag = {}
for name, Grks, Vrks in [('all_torque_vs_V282', ALL_T, V282), ('all_torque_vs_V282minor', ALL_T, MINOR)]:
    Gc = np.concatenate([col(DATA[r]['R'], 'cell') for r in Grks])
    Vc = np.concatenate([col(DATA[r]['R'], 'cell') for r in Vrks])
    common = np.intersect1d(np.unique(Gc), np.unique(Vc))
    diag[name] = dict(G_cells=sorted(set(Gc.tolist())), V_cells=sorted(set(Vc.tolist())), common=common.tolist(),
                       G_n=len(Gc), V_n=len(Vc))
    print(name, 'G cells', sorted(set(Gc.tolist())), 'V cells', sorted(set(Vc.tolist())), 'common', common.tolist())
results['overlap'] = diag

json.dump(results, open(f'{HERE}/verify_results.json', 'w'), indent=1, default=float)
print('\nwrote', f'{HERE}/verify_results.json')
