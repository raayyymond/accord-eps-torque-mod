"""Adversarial verification of finding 'dwell-count-not-a-separator-jumps-bigger', CONFOUND lens.

Independently re-derives the dwell-then-jump count and jump-magnitude comparison from the s4_texture
per-route npz cache (DJ arrays + row-level travel/activity), then stress-tests it for confounds:
  1. reproduce the reported numbers (sanity check the pipeline is read correctly)
  2. leave-one-route-out on V282 (drop 0000006c--2bc842dbac, the 62-segment route)
  3. demand-amplitude + speed matched comparison (cell = speed x |angle| x activity band, same cells
     as s4_compare.py) instead of speed-band-only, for BOTH the count-per-travel and the jump size
  4. per-route breakdown so a single route's dominance is visible directly
Does not touch v282cmp.py or the s4_texture pipeline; reads their cached npz only.
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__dwellcountno__confound'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
rng = np.random.default_rng(11)

routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}

# DJ columns (from s4_extract.dwell-then-jump loop): v, |sa|, dwell_s, jump, pre, rate_after_peak, act(mean |sr_lp05|)
DJCOL = dict(v=0, ang=1, dwell=2, jump=3, pre=4, rate_after=5, act=6)


def load(rk):
    D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
    keys = [str(k) for k in D['keys']]
    cols = {k: D['rows'][:, i] for i, k in enumerate(keys)}
    return dict(DJ=D['DJ'], cols=cols)


R = {rk: load(rk) for g in GROUPS for rk in routes[g]}


def travel_in_band(rk, s0, s1, a0=None, a1=None, act0=None, act1=None):
    c = R[rk]['cols']
    m = (c['v'] >= s0) & (c['v'] < s1)
    if a0 is not None:
        m &= (c['ang90'] >= a0) & (c['ang90'] < a1)
    if act0 is not None:
        m &= (c['act'] >= act0) & (c['act'] < act1)
    return float(c['travel'][m].sum())


def dj_count_in_band(rk, s0, s1, a0=None, a1=None, act0=None, act1=None):
    DJ = R[rk]['DJ']
    if DJ.shape[0] == 0:
        return np.array([]), np.array([])
    v, ang, act = DJ[:, DJCOL['v']], DJ[:, DJCOL['ang']], DJ[:, DJCOL['act']]
    m = (v >= s0) & (v < s1)
    if a0 is not None:
        m &= (ang >= a0) & (ang < a1)
    if act0 is not None:
        m &= (act >= act0) & (act < act1)
    return DJ[m, DJCOL['jump']], DJ[m, DJCOL['dwell']]


def boot_ratio_routes(nums, dens, B=3000):
    """route-cluster bootstrap of sum(nums)/sum(dens), nums/dens = per-route arrays (scalars)."""
    nums = np.asarray(nums, float); dens = np.asarray(dens, float)
    est = nums.sum() / max(dens.sum(), 1e-9)
    reps = []
    for _ in range(B):
        k = rng.integers(0, len(nums), len(nums))
        reps.append(nums[k].sum() / max(dens[k].sum(), 1e-9))
    return est, [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]


def group_rate(group, s0, s1, exclude=()):
    rks = [rk for rk in routes[group] if rk not in exclude]
    nums, dens, per_route = [], [], {}
    for rk in rks:
        j, _ = dj_count_in_band(rk, s0, s1)
        trav = travel_in_band(rk, s0, s1)
        nums.append(len(j)); dens.append(trav / 100.0)
        per_route[rk] = dict(n=len(j), travel_deg=trav, rate=len(j) / max(trav / 100.0, 1e-9))
    est, ci = boot_ratio_routes(nums, dens)
    return dict(est=est, ci=ci, n=int(sum(nums)), routes=rks, per_route=per_route)


print("=== STEP 1: reproduce dj_per100deg, speed-band only (sanity check vs finding's quoted numbers) ===")
step1 = {}
for (s0, s1) in [(0, 15), (15, 40)]:
    step1[f'{s0}_{s1}'] = {}
    for g in GROUPS:
        r = group_rate(g, s0, s1)
        step1[f'{s0}_{s1}'][g] = r
        print(f"  v[{s0},{s1}) {g:8s} rate={r['est']:.3f} CI={np.round(r['ci'],3).tolist()} n={r['n']}")
        for rk, pr in r['per_route'].items():
            print(f"      {rk:24s} n={pr['n']:4d} travel={pr['travel_deg']:8.0f}deg rate={pr['rate']:.3f}")

print("\n=== STEP 2: leave-one-route-out -- V282 WITHOUT 0000006c--2bc842dbac (the 62-seg route) ===")
step2 = {}
for (s0, s1) in [(0, 15), (15, 40)]:
    r_full = group_rate('V282', s0, s1)
    r_loo = group_rate('V282', s0, s1, exclude=('0000006c--2bc842dbac',))
    step2[f'{s0}_{s1}'] = dict(full=r_full['est'], full_ci=r_full['ci'], loo=r_loo['est'], loo_ci=r_loo['ci'],
                                loo_n=r_loo['n'], loo_routes=r_loo['routes'])
    print(f"  v[{s0},{s1}) V282 full={r_full['est']:.3f} {r_full['ci']}  LOO(no r6c)={r_loo['est']:.3f} {r_loo['ci']} (n={r_loo['n']}, routes={r_loo['routes']})")
    for g in ['T64', 'T64B', 'T5', 'T4']:
        r = group_rate(g, s0, s1)
        ratio_full = r['est'] / max(r_full['est'], 1e-9)
        ratio_loo = r['est'] / max(r_loo['est'], 1e-9)
        print(f"      {g:5s} rate={r['est']:.3f}  ratio-vs-V282-full={ratio_full:.3f}  ratio-vs-V282-LOO={ratio_loo:.3f}")
        step2[f'{s0}_{s1}'][g] = dict(rate=r['est'], ratio_full=ratio_full, ratio_loo=ratio_loo)

print("\n=== STEP 3: jump p90 leave-one-out (V282 without r6c) ===")
step3 = {}
for (s0, s1) in [(0, 15)]:
    j_full, _ = dj_count_in_band_all = (np.concatenate([dj_count_in_band(rk, s0, s1)[0] for rk in routes['V282']]) if routes['V282'] else np.array([]), None)
    j_loo = np.concatenate([dj_count_in_band(rk, s0, s1)[0] for rk in routes['V282'] if rk != '0000006c--2bc842dbac'])
    p90_full = float(np.percentile(j_full, 90)) if len(j_full) else np.nan
    p90_loo = float(np.percentile(j_loo, 90)) if len(j_loo) else np.nan
    step3[f'{s0}_{s1}'] = dict(p90_full=p90_full, n_full=len(j_full), p90_loo=p90_loo, n_loo=len(j_loo))
    print(f"  v[{s0},{s1}) V282 jump p90 full={p90_full:.3f} (n={len(j_full)})  LOO(no r6c)={p90_loo:.3f} (n={len(j_loo)})")
    for g in ['T64', 'T64B', 'T5', 'T4']:
        jg = np.concatenate([dj_count_in_band(rk, s0, s1)[0] for rk in routes[g]])
        p90g = float(np.percentile(jg, 90)) if len(jg) else np.nan
        print(f"      {g:5s} jump p90={p90g:.3f} n={len(jg)}  ratio-vs-full={p90g/max(p90_full,1e-9):.2f}  ratio-vs-LOO={p90g/max(p90_loo,1e-9):.2f}")
        step3[f'{s0}_{s1}'][g] = dict(p90=p90g, n=len(jg))

print("\n=== STEP 4: speed x angle x activity MATCHED comparison (cell = same bins as s4_compare.py) ===")
SPD = [0, 8, 15, 22, 40]
ANG = [0, 5, 15, 45, 1e9]
ACT = [0, 1.0, 3.0, 10.0, 1e9]
MIN = 2  # routes are few; relax vs s4_compare's MIN=3 but report n_cells used


def cell_of(v, a, act):
    s = np.digitize(v, SPD) - 1
    ai = np.digitize(a, ANG) - 1
    m = np.digitize(act, ACT) - 1
    return s * 100 + ai * 10 + m


def matched_rate_and_jump(group_rks, exclude=()):
    """Per cell: dwell count / travel(100deg) in that cell, aggregated with route-cluster weight; and jump median.
    Returns dict cell -> (rate, jump_median, n_dj, travel_deg)."""
    rks = [rk for rk in group_rks if rk not in exclude]
    agg = {}
    for rk in rks:
        DJ = R[rk]['DJ']; c = R[rk]['cols']
        if DJ.shape[0]:
            cellsDJ = cell_of(DJ[:, DJCOL['v']], DJ[:, DJCOL['ang']], DJ[:, DJCOL['act']])
        else:
            cellsDJ = np.array([])
        cellsRow = cell_of(c['v'], c['ang90'], c['act'])
        for cl in np.unique(np.concatenate([cellsDJ, cellsRow])) if len(cellsRow) else []:
            if cl not in agg:
                agg[cl] = dict(n=0, travel=0.0, jumps=[])
            mtrav = cellsRow == cl
            agg[cl]['travel'] += float(c['travel'][mtrav].sum())
            if len(cellsDJ):
                mdj = cellsDJ == cl
                agg[cl]['n'] += int(mdj.sum())
                agg[cl]['jumps'].extend(DJ[mdj, DJCOL['jump']].tolist())
    return agg


def matched_effect(agg_g, agg_v, min_travel_deg=50.0):
    """cells present with >=min_travel_deg travel on both sides. Returns weighted log-ratio of rate (count/100deg)
    and weighted log-ratio of median jump, weight = min(travel_g, travel_v)."""
    common = set(agg_g) & set(agg_v)
    num_rate = den_rate = 0.0
    num_jump = den_jump = 0.0
    ncell = 0
    for cl in common:
        g, v = agg_g[cl], agg_v[cl]
        if g['travel'] < min_travel_deg or v['travel'] < min_travel_deg:
            continue
        rg = g['n'] / (g['travel'] / 100.0); rv = v['n'] / (v['travel'] / 100.0)
        w = min(g['travel'], v['travel'])
        num_rate += w * (np.log(rg + 0.01) - np.log(rv + 0.01)); den_rate += w
        if len(g['jumps']) >= 2 and len(v['jumps']) >= 2:
            jg, jv = np.median(g['jumps']), np.median(v['jumps'])
            w2 = min(len(g['jumps']), len(v['jumps']))
            num_jump += w2 * (np.log(jg + 1e-3) - np.log(jv + 1e-3)); den_jump += w2
        ncell += 1
    rate_ratio = float(np.exp(num_rate / den_rate)) if den_rate > 0 else np.nan
    jump_ratio = float(np.exp(num_jump / den_jump)) if den_jump > 0 else np.nan
    return dict(rate_ratio=rate_ratio, jump_ratio=jump_ratio, n_cells=ncell, den_rate=den_rate, den_jump=den_jump)


step4 = {}
agg_v_full = matched_rate_and_jump(routes['V282'])
agg_v_loo = matched_rate_and_jump(routes['V282'], exclude=('0000006c--2bc842dbac',))
for g in ['T64', 'T64B', 'T5', 'T4']:
    agg_g = matched_rate_and_jump(routes[g])
    eff_full = matched_effect(agg_g, agg_v_full)
    eff_loo = matched_effect(agg_g, agg_v_loo)
    step4[g] = dict(vs_full=eff_full, vs_loo=eff_loo)
    print(f"  {g:5s} vs V282-full: rate_ratio={eff_full['rate_ratio']:.3f} jump_ratio={eff_full['jump_ratio']:.3f} n_cells={eff_full['n_cells']}")
    print(f"        vs V282-LOO : rate_ratio={eff_loo['rate_ratio']:.3f} jump_ratio={eff_loo['jump_ratio']:.3f} n_cells={eff_loo['n_cells']}")

print("\n=== STEP 5: bootstrap CI on matched rate_ratio and jump_ratio (route-cluster, V282 LOO baseline) ===")
step5 = {}
B = 800
for g in ['T64', 'T64B', 'T5', 'T4']:
    reps_rate, reps_jump = [], []
    Grks = routes[g]; Vrks = [rk for rk in routes['V282'] if rk != '0000006c--2bc842dbac']
    for _ in range(B):
        gpick = list(rng.choice(Grks, len(Grks), replace=True))
        vpick = list(rng.choice(Vrks, len(Vrks), replace=True)) if len(Vrks) else Vrks
        agg_g = matched_rate_and_jump(gpick)
        agg_v = matched_rate_and_jump(vpick)
        eff = matched_effect(agg_g, agg_v)
        if np.isfinite(eff['rate_ratio']):
            reps_rate.append(eff['rate_ratio'])
        if np.isfinite(eff['jump_ratio']):
            reps_jump.append(eff['jump_ratio'])
    ci_rate = [float(np.percentile(reps_rate, 2.5)), float(np.percentile(reps_rate, 97.5))] if len(reps_rate) > 30 else [np.nan, np.nan]
    ci_jump = [float(np.percentile(reps_jump, 2.5)), float(np.percentile(reps_jump, 97.5))] if len(reps_jump) > 30 else [np.nan, np.nan]
    step5[g] = dict(rate_ratio_ci=ci_rate, n_rate_reps=len(reps_rate), jump_ratio_ci=ci_jump, n_jump_reps=len(reps_jump))
    print(f"  {g:5s} matched rate_ratio 95%CI(route-boot, LOO baseline) = {np.round(ci_rate,3).tolist()} (n={len(reps_rate)})")
    print(f"        matched jump_ratio 95%CI(route-boot, LOO baseline) = {np.round(ci_jump,3).tolist()} (n={len(reps_jump)})")

json.dump(dict(step1={k: {kk: (vv if kk != 'per_route' else {r: p for r, p in vv.items()}) for kk, vv in v.items()} for k, v in step1.items()},
               step2=step2, step3=step3, step4=step4, step5=step5),
          open(f'{OUT}/verify_dj_results.json', 'w'), indent=1, default=float)
print("\nwrote", f'{OUT}/verify_dj_results.json')
