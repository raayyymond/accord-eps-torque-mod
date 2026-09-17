"""Adversarial CONFOUND check on s3_accel finding 'unwind-is-feedforward-release-plus-45ms-lag'.

Re-tests with:
 (a) per-event (not ensemble-band) command numbers, clustered bootstrap CI by ROUTE
 (b) leave-one-route-out, especially the dominant V282 route 0000006c--2bc842dbac (16/27 V282 events)
 (c) the 'torque' group un-merged into its four fork revisions (T64/T64B/T5/T4 -- different LAF/Kp/configs)
 (d) speed+amplitude MATCHED strata (same v,P bins present in both V282 and torque)
 (e) lag re-checked with ap (independent livePose yaw) as well as aa (steering-angle sensor)
 (f) driver-torque pressed-frame contamination check
"""
import json, pickle, sys
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
VOUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__unwindisfeed__confound/'

GM = {'V282': 'V282', 'V282old': 'V282old', 'T64': 'torque', 'T64B': 'torque', 'T5': 'torque', 'T4': 'torque'}
DOMINANT_V282 = '0000006c--2bc842dbac'

TE = json.load(open(OUT + 'turn_events.json'))
rows = TE['rows']
P2 = json.load(open(OUT + 's3_pass2.json'))
p2rows = P2['rows']
E = pickle.load(open(OUT + 'ensemble.pkl', 'rb'))
grid = E['grid']

rng = np.random.default_rng(12345)


def cluster_boot(vals, clusters, fn=np.median, n=4000):
    """Resample clusters (routes) with replacement, then all events within, compute fn. Returns (point, lo, hi)."""
    vals = np.asarray(vals, float)
    clusters = np.asarray(clusters)
    uniq = np.unique(clusters)
    if len(uniq) < 2:
        # can't cluster-bootstrap with 1 route; fall back to event-level bootstrap
        idx_by = {c: np.where(clusters == c)[0] for c in uniq}
        out = []
        for _ in range(n):
            idx = rng.choice(len(vals), len(vals), replace=True)
            out.append(fn(vals[idx]))
        out = np.array(out)
        return float(fn(vals)), float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))
    idx_by = {c: np.where(clusters == c)[0] for c in uniq}
    out = []
    for _ in range(n):
        picks = rng.choice(uniq, len(uniq), replace=True)
        idx = np.concatenate([idx_by[c] for c in picks])
        out.append(fn(vals[idx]))
    out = np.array(out)
    return float(fn(vals)), float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


# ---------------------------------------------------------------------------
# (a)+(b)+(c) per-event command windows at unwind anchor, from ensemble.pkl directly (not the band aggregate)
def window_mean(tr_arr, t0, t1):
    m = (grid >= t0) & (grid < t1)
    seg = tr_arr[m]
    return float(np.nanmean(seg)) if np.isfinite(seg).any() else np.nan


ev_cmd = []
for e in E['ens']:
    tr = e['tr']['h1']
    row = dict(group=e['group'], gmerge=GM[e['group']], rk=e['rk'], v=e['v'], P=e['P'])
    for win_name, (t0, t1) in dict(hold=(-1, 0), early=(0, 1.5), late=(2, 4)).items():
        row[f'out_{win_name}'] = window_mean(tr['out'], t0, t1)
        row[f'pi_{win_name}'] = window_mean(tr['pi'], t0, t1)
        row[f'f_{win_name}'] = window_mean(tr['f'], t0, t1)
    ev_cmd.append(row)

report = {}

print('=== (a) per-event command, clustered-by-route bootstrap, ALL DATA ===')
for g in ['V282', 'V282old', 'torque']:
    sub = [r for r in ev_cmd if r['gmerge'] == g]
    rks = [r['rk'] for r in sub]
    n_routes = len(set(rks))
    line = {'n_events': len(sub), 'n_routes': n_routes}
    for win in ('hold', 'early', 'late'):
        vals = [r[f'out_{win}'] for r in sub]
        pt, lo, hi = cluster_boot(vals, rks)
        line[f'out_{win}'] = (pt, lo, hi)
    print(g, line)
    report[f'a_all_{g}'] = line

print()
print('=== (a2) torque UN-MERGED by fork revision ===')
for g in ['T64', 'T64B', 'T5', 'T4']:
    sub = [r for r in ev_cmd if r['group'] == g]
    if not sub:
        continue
    rks = [r['rk'] for r in sub]
    line = {'n_events': len(sub), 'n_routes': len(set(rks))}
    for win in ('hold', 'early', 'late'):
        vals = [r[f'out_{win}'] for r in sub]
        pt, lo, hi = cluster_boot(vals, rks)
        line[f'out_{win}'] = (pt, lo, hi)
    print(g, line)
    report[f'a2_{g}'] = line

print()
print('=== (b) LEAVE-ONE-ROUTE-OUT: drop dominant V282 route', DOMINANT_V282, '(16/27 V282 events) ===')
sub = [r for r in ev_cmd if r['gmerge'] == 'V282' and r['rk'] != DOMINANT_V282]
rks = [r['rk'] for r in sub]
line = {'n_events': len(sub), 'n_routes': len(set(rks)), 'routes': sorted(set(rks))}
for win in ('hold', 'early', 'late'):
    vals = [r[f'out_{win}'] for r in sub]
    pt, lo, hi = cluster_boot(vals, rks)
    line[f'out_{win}'] = (pt, lo, hi)
print('V282 (minus dominant route)', line)
report['b_v282_minus_dominant'] = line

print()
print('=== (b2) leave-one-route-out sweep: drop each V282 route in turn, out_early ===')
for held_out in sorted(set(r['rk'] for r in ev_cmd if r['gmerge'] == 'V282')):
    sub = [r for r in ev_cmd if r['gmerge'] == 'V282' and r['rk'] != held_out]
    vals = [r['out_early'] for r in sub]
    print(f'  drop {held_out}: n={len(sub)} median_out_early={np.median(vals):.3f}')

print()
print('=== (b3) leave-one-route-out sweep: drop each torque route in turn, out_early ===')
for held_out in sorted(set(r['rk'] for r in ev_cmd if r['gmerge'] == 'torque')):
    sub = [r for r in ev_cmd if r['gmerge'] == 'torque' and r['rk'] != held_out]
    vals = [r['out_early'] for r in sub]
    print(f'  drop {held_out}: n={len(sub)} median_out_early={np.median(vals):.3f}')

# ---------------------------------------------------------------------------
# (d) speed+amplitude matched strata
print()
print('=== (d) speed x amplitude matched strata (v bin x P bin), out_early median per group ===')
VBINS = [(2.5, 5), (5, 8), (8, 15)]
PBINS = [(25, 60), (60, 150), (150, 400)]
matched_rows = []
for vlo, vhi in VBINS:
    for plo, phi in PBINS:
        cell = {}
        for g in ['V282', 'torque']:
            sub = [r for r in ev_cmd if r['gmerge'] == g and vlo <= r['v'] < vhi and plo <= r['P'] < phi]
            cell[g] = sub
        nv, nt = len(cell['V282']), len(cell['torque'])
        if nv >= 2 and nt >= 2:
            mv = np.median([r['out_early'] for r in cell['V282']])
            mt = np.median([r['out_early'] for r in cell['torque']])
            print(f'  v[{vlo},{vhi}) P[{plo},{phi}): V282 n={nv} med={mv:.3f}  torque n={nt} med={mt:.3f}  diff={mt-mv:+.3f}')
            matched_rows.append(dict(vlo=vlo, vhi=vhi, plo=plo, phi=phi, n_v282=nv, n_torque=nt,
                                      med_v282=float(mv), med_torque=float(mt)))
        else:
            print(f'  v[{vlo},{vhi}) P[{plo},{phi}): V282 n={nv}  torque n={nt}  (insufficient for match)')
report['d_matched_strata'] = matched_rows

# regression-adjusted check: out_early ~ is_torque + v + P, cluster-robust via bootstrap-by-route on residual coefficient
print()
print('=== (d2) OLS out_early ~ is_torque + v + P (V282 vs torque only), route-clustered bootstrap on is_torque coef ===')
sub = [r for r in ev_cmd if r['gmerge'] in ('V282', 'torque') and np.isfinite(r['out_early'])]
X = np.array([[1.0, 1.0 if r['gmerge'] == 'torque' else 0.0, r['v'], r['P']] for r in sub])
y = np.array([r['out_early'] for r in sub])
rks_d2 = np.array([r['rk'] for r in sub])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
print('  coefs [const, is_torque, v, P] =', beta)


def coef_torque(idx):
    Xs, ys = X[idx], y[idx]
    b, *_ = np.linalg.lstsq(Xs, ys, rcond=None)
    return b[1]


uniq_rk = np.unique(rks_d2)
idx_by = {c: np.where(rks_d2 == c)[0] for c in uniq_rk}
boots = []
for _ in range(4000):
    picks = rng.choice(uniq_rk, len(uniq_rk), replace=True)
    idx = np.concatenate([idx_by[c] for c in picks])
    boots.append(coef_torque(idx))
boots = np.array(boots)
print(f'  is_torque coef on out_early: {beta[1]:.3f}  CI [{np.percentile(boots,2.5):.3f}, {np.percentile(boots,97.5):.3f}]  (route-clustered bootstrap)')
report['d2_ols_is_torque_coef'] = dict(point=float(beta[1]), lo=float(np.percentile(boots, 2.5)), hi=float(np.percentile(boots, 97.5)))

# ---------------------------------------------------------------------------
# (e) lag re-check with aa AND ap, clustered by route, with/without dominant route, stratified by v and P bins
print()
print('=== (e) best-lag (aa=steering-angle-sensor, ap=independent livePose yaw), route-clustered bootstrap ===')
for key in ('aa_bestlag', 'ap_bestlag'):
    for g in ['V282', 'torque']:
        sub = [r for r in p2rows if GM[r['group']] == g and np.isfinite(r[key])]
        rks = [r['rk'] for r in sub]
        vals = [r[key] for r in sub]
        pt, lo, hi = cluster_boot(vals, rks)
        print(f'  {key} {g}: n={len(sub)} routes={len(set(rks))} median={pt:.3f} CI[{lo:.3f},{hi:.3f}]')
        report[f'e_{key}_{g}'] = dict(n=len(sub), median=pt, lo=lo, hi=hi)
    # difference, route-clustered bootstrap over the pooled event set (cluster id prefixed by group to keep V282/torque routes separate but resample jointly)
    subv = [r for r in p2rows if GM[r['group']] == 'V282' and np.isfinite(r[key])]
    subt = [r for r in p2rows if GM[r['group']] == 'torque' and np.isfinite(r[key])]
    rksv = np.array([r['rk'] for r in subv]); valsv = np.array([r[key] for r in subv])
    rkst = np.array([r['rk'] for r in subt]); valst = np.array([r[key] for r in subt])
    uv, ut = np.unique(rksv), np.unique(rkst)
    idxv = {c: np.where(rksv == c)[0] for c in uv}
    idxt = {c: np.where(rkst == c)[0] for c in ut}
    diffs = []
    for _ in range(4000):
        pv = rng.choice(uv, len(uv), replace=True)
        pt_ = rng.choice(ut, len(ut), replace=True)
        iv = np.concatenate([idxv[c] for c in pv])
        it = np.concatenate([idxt[c] for c in pt_])
        diffs.append(np.median(valst[it]) - np.median(valsv[iv]))
    diffs = np.array(diffs)
    d_pt = np.median(valst) - np.median(valsv)
    print(f'  {key} torque-V282 diff: {d_pt:.3f} CI[{np.percentile(diffs,2.5):.3f},{np.percentile(diffs,97.5):.3f}]')
    report[f'e_{key}_diff'] = dict(point=float(d_pt), lo=float(np.percentile(diffs, 2.5)), hi=float(np.percentile(diffs, 97.5)))

    # without dominant V282 route
    subv2 = [r for r in subv if r['rk'] != DOMINANT_V282]
    if subv2:
        print(f'  {key} V282 WITHOUT dominant route: n={len(subv2)} median={np.median([r[key] for r in subv2]):.3f}')

print()
print('=== (e2) lag stratified by P-bin (angle) and v-bin (yaw proxy), aa_bestlag ===')
for binname, bins, field in (('P', PBINS, 'P'), ('v', VBINS, 'v')):
    for lo_, hi_ in bins:
        line = {}
        for g in ['V282', 'torque']:
            sub = [r for r in p2rows if GM[r['group']] == g and lo_ <= r[field] < hi_ and np.isfinite(r['aa_bestlag'])]
            if sub:
                line[g] = (len(sub), float(np.median([r['aa_bestlag'] for r in sub])))
        print(f'  {binname}[{lo_},{hi_}): {line}')

# ---------------------------------------------------------------------------
# (f) driver-torque unwind, route-clustered, with pressed-frame contamination check
print()
print('=== (f) drv_unwind (sub-threshold driver torque during unwind), route-clustered bootstrap ===')
for g in ['V282', 'torque']:
    sub = [r for r in rows if GM[r['group']] == g and np.isfinite(r['drv_unwind'])]
    rks = [r['rk'] for r in sub]
    vals = [r['drv_unwind'] for r in sub]
    press = [r['press_unwind'] for r in sub]
    pt, lo, hi = cluster_boot(vals, rks)
    print(f'  {g}: n={len(sub)} median={pt:.1f} CI[{lo:.1f},{hi:.1f}]  press_unwind median={np.median(press):.4f} max={np.max(press):.4f} frac_events_with_press>0={np.mean(np.array(press)>0):.2f}')
    report[f'f_drv_unwind_{g}'] = dict(n=len(sub), median=pt, lo=lo, hi=hi, press_median=float(np.median(press)))

# without dominant V282 route
sub = [r for r in rows if GM[r['group']] == 'V282' and r['rk'] != DOMINANT_V282 and np.isfinite(r['drv_unwind'])]
if sub:
    print(f'  V282 minus dominant route: n={len(sub)} median={np.median([r["drv_unwind"] for r in sub]):.1f}')

# ---------------------------------------------------------------------------
# (g) hold_share_f / (p+i) numbers, route-clustered
print()
print('=== (g) hold_share P+I (feedback share of |out| during HOLD), route-clustered bootstrap ===')
for g in ['V282', 'torque']:
    sub = [r for r in rows if GM[r['group']] == g and np.isfinite(r['hold_share_p']) and np.isfinite(r['hold_share_i'])]
    rks = [r['rk'] for r in sub]
    pi_share = [r['hold_share_p'] + r['hold_share_i'] for r in sub]
    pt, lo, hi = cluster_boot(pi_share, rks)
    print(f'  {g}: n={len(sub)} median P+I share={pt:.3f} CI[{lo:.3f},{hi:.3f}]')
    report[f'g_pi_share_{g}'] = dict(n=len(sub), median=pt, lo=lo, hi=hi)

json.dump(report, open(VOUT + 'verify_out.json', 'w'), indent=1, default=float)
print()
print('wrote', VOUT + 'verify_out.json')
