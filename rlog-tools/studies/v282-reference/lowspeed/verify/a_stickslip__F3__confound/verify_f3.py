"""Adversarial CONFOUND check on finding F3 (a_stickslip / lowspeed).

Lens: does the claimed torque-vs-V282 dwell/lag/catch-up/peak-rate ranking survive when:
  (a) the dominant single V282 route (0000006c--2bc842dbac, 62 segs, 230/309 = 74% of all
      V282 episodes in this table) is pulled out, leaving only 64+65 (79 episodes)?
  (b) the 4x-demand torque route T64B (0000006e--6ca3e014fd) is pulled out of the torque pool?
  (c) both at once, and also route-by-route (not just group-vs-group)?

Reuses ss_ratios.py's EXACT metric definitions (dwell_s, gap_model_deg [=lag at breakaway vs the
group-identical model demand], catch30_deg, peak_rate_dps) computed from the same per-episode
window arrays (out/<rk>_ss.npz via ss_load.load_all()). Only the route membership changes.

Run from rlog-tools/studies/v282-reference/lowspeed/a_stickslip/ (imports ss_load which is
relative to that dir).
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
from ss_load import load_all, PRE

EP, W, EX, VAL = load_all()
N = len(EP)
ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route'); aa_abs = col('abs_aa'); dwell = col('dwell_s')
A = lambda k, i: W[k][ar, i] * sj
gap_model = A('ad', np.full(N, PRE)) - A('aa', np.full(N, PRE))
catch30 = A('aa', np.full(N, PRE + 30)) - A('aa', np.full(N, PRE))
pk = np.max(np.abs(W['sr'][:, PRE:PRE + 40]), 1)
metrics = dict(dwell_s=dwell, gap_model_deg=gap_model, catch30_deg=catch30, peak_rate_dps=pk)

DOMINANT_V282 = '0000006c--2bc842dbac'
V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
T64B = '0000006e--6ca3e014fd'
TORQUE_GROUPS_FULL = ['T64', 'T64B', 'T5', 'T4']

rng = np.random.default_rng(7)


def ratio_ci(mt_mask, mr_mask, x, nboot=1000, seed=7):
    ut, ur = np.unique(route[mt_mask]), np.unique(route[mr_mask])
    rngl = np.random.default_rng(seed)
    if len(x[mt_mask]) < 4 or len(x[mr_mask]) < 4:
        return None
    p50t, p50r = np.median(x[mt_mask]), np.median(x[mr_mask])
    p90t, p90r = np.percentile(x[mt_mask], 90), np.percentile(x[mr_mask], 90)
    bs50, bs90 = [], []
    for _ in range(nboot):
        it = np.concatenate([np.where(mt_mask & (route == c))[0] for c in rngl.choice(ut, len(ut))]) if len(ut) else np.array([], int)
        ir = np.concatenate([np.where(mr_mask & (route == c))[0] for c in rngl.choice(ur, len(ur))]) if len(ur) else np.array([], int)
        if len(it) > 3 and len(ir) > 3:
            bs50.append(np.median(x[it]) / np.median(x[ir]))
            bs90.append(np.percentile(x[it], 90) / np.percentile(x[ir], 90))
    out = dict(n_t=int(mt_mask.sum()), n_r=int(mr_mask.sum()), t_routes=ut.tolist(), r_routes=ur.tolist(),
               p50_t=float(p50t), p50_r=float(p50r), p50_ratio=float(p50t / p50r) if p50r else None,
               p90_t=float(p90t), p90_r=float(p90r), p90_ratio=float(p90t / p90r) if p90r else None)
    if bs50:
        out['p50_ci'] = np.percentile(bs50, [2.5, 97.5]).tolist()
    if bs90:
        out['p90_ci'] = np.percentile(bs90, [2.5, 97.5]).tolist()
    return out


def run_variant(lo, hi, tq_groups, vr_routes, label):
    mt = np.isin(g, tq_groups) & (v >= lo) & (v < hi)
    mr = np.isin(route, vr_routes) & (v >= lo) & (v < hi)
    print(f'\n--- {label}  v[{lo},{hi})  n_t={mt.sum()} n_r={mr.sum()} ---')
    res = {}
    for nm, x in metrics.items():
        r = ratio_ci(mt, mr, x)
        res[nm] = r
        if r:
            print(f'  {nm:16s} p50 {r["p50_t"]:.3f}/{r["p50_r"]:.3f}=x{r["p50_ratio"]:.2f} {r.get("p50_ci")}   '
                  f'p90 {r["p90_t"]:.3f}/{r["p90_r"]:.3f}=x{r["p90_ratio"]:.2f} {r.get("p90_ci")}')
        else:
            print(f'  {nm:16s} insufficient n')
    return res


results = {}

print('=== episode counts per route (weight check) ===')
for rk in sorted(set(route)):
    for lo, hi, lab in [(2, 8, '2-8'), (8, 15, '8-15')]:
        m = (route == rk) & (v >= lo) & (v < hi)
        if m.sum():
            print(f'{rk:28s} {g[route==rk][0]:8s} {lab}: n={m.sum()}')

# (0) baseline: reproduce ss_ratios.py's full-group numbers for 2-8 and 8-15, 'all' angle
for lo, hi in [(2, 8), (8, 15)]:
    results[f'baseline_{lo}-{hi}'] = run_variant(lo, hi, TORQUE_GROUPS_FULL, V282_ROUTES, f'BASELINE full groups {lo}-{hi}')

# (a) exclude the dominant V282 route
for lo, hi in [(2, 8), (8, 15)]:
    results[f'exclV282dom_{lo}-{hi}'] = run_variant(lo, hi, TORQUE_GROUPS_FULL,
                                                      [r for r in V282_ROUTES if r != DOMINANT_V282],
                                                      f'EXCL dominant V282 route {lo}-{hi}')

# (b) exclude T64B (4x demand) from torque
for lo, hi in [(2, 8), (8, 15)]:
    results[f'exclT64B_{lo}-{hi}'] = run_variant(lo, hi, [x for x in TORQUE_GROUPS_FULL if x != 'T64B'],
                                                   V282_ROUTES, f'EXCL T64B {lo}-{hi}')

# (c) both exclusions at once
for lo, hi in [(2, 8), (8, 15)]:
    results[f'exclBoth_{lo}-{hi}'] = run_variant(lo, hi, [x for x in TORQUE_GROUPS_FULL if x != 'T64B'],
                                                   [r for r in V282_ROUTES if r != DOMINANT_V282],
                                                   f'EXCL BOTH {lo}-{hi}')

# (d) independent single-route comparison: T4 (different day/road, not part of the 6c/6d/6e cluster,
#     and not part of the b_shake T64B either) vs V282 excl-dominant (64+65 only)
for lo, hi in [(2, 8), (8, 15)]:
    results[f'T4_vs_V282excl_{lo}-{hi}'] = run_variant(lo, hi, ['T4'],
                                                         [r for r in V282_ROUTES if r != DOMINANT_V282],
                                                         f'T4 alone vs V282 excl-dominant {lo}-{hi}')

# (e) T4 vs the dominant V282 route ALONE (does the direction hold road-to-road, single vs single?)
for lo, hi in [(2, 8), (8, 15)]:
    results[f'T4_vs_6c_{lo}-{hi}'] = run_variant(lo, hi, ['T4'], [DOMINANT_V282], f'T4 alone vs 6c alone {lo}-{hi}')

json.dump(results, open(os.path.join(os.path.dirname(__file__), 'out_f3_confound.json'), 'w'), indent=1)
print('\nwrote', os.path.join(os.path.dirname(__file__), 'out_f3_confound.json'))
