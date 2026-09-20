"""Stage 3: the sign-reversal channel and the NULL CONTROL's remaining power.  -> out/so_power.json

(a) The channel the objection did not name: on a RETURN that crosses centre, z_out does not merely switch
    off -- it RE-ARMS with the opposite sign, which in the episode's own outward-signed frame is an INWARD
    torque of up to the full dose.  Measured as min(zo_s) over the episode.
(b) Contamination tiers, and how many clean returns survive per route.
(c) FAIL clause 1 (return dwell p50, return os30_p90 must not move): the minimum detectable effect at the
    surviving n, both within-route and for the realistic single-new-route comparison.
    os30 recomputed here exactly as ss_analyze section 7 does it (sign-aligned overshoot at +300 ms).
"""
import sys, glob, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
from ss_load import load_all, PRE
from solib import OUT, LEVEL, boot_ci

# --- my rows (same route order, same within-route order as ss_load) ---
ROWS = []
for f in sorted(glob.glob(OUT + '/*_so.npz')):
    ROWS += list(np.load(f, allow_pickle=True)['rows'])
EP, W, EX, VAL = load_all()
# align: ss_load carries ALL routes (V282 too); keep only the ones I have, matching on (route, bk)
key_mine = {(r['route'], r['bk']): i for i, r in enumerate(ROWS)}
sel, mine_i = [], []
for j, e in enumerate(EP):
    kk = (e['route'], e['bk'])
    if kk in key_mine:
        sel.append(j); mine_i.append(key_mine[kk])
sel = np.array(sel); mine_i = np.array(mine_i)
assert len(sel) == len(ROWS), f'alignment {len(sel)} vs {len(ROWS)}'
R = {'align': dict(n_matched=int(len(sel)), n_my_rows=len(ROWS), n_ss_episodes=len(EP))}

sj = np.array([EP[j]['sjump'] for j in sel])
# os30 exactly as ss_analyze section 7 (sign-aligned with the jump)
A = lambda ch, i: W[ch][sel, i] * sj
gapdes = A('angdes', PRE) - A('aa', PRE)
catch30 = A('aa', PRE + 30) - A('aa', PRE)
dem30 = A('angdes', PRE + 30) - A('angdes', PRE)
os30 = catch30 - dem30 - gapdes

col = lambda k: np.array([ROWS[i][k] for i in mine_i], dtype=float)
scol = lambda k: np.array([ROWS[i][k] for i in mine_i])
route = scol('route'); grp = scol('group'); v = col('v'); ret = col('ret').astype(bool)
dwell = col('dwell_s'); hw = col('hw'); dz = col('dz'); t_on = col('t_on')
onlead_i0 = col('on_lead_i0_s'); offlead_i0 = col('off_lead_i0_s')
zo_max_dw = col('zo_max_in_dwell'); zo_min_bk = col('zo_min_i0_bk'); zo_min_se = col('zo_min_i0_slipend')
zo_i0 = col('zo_i0')
P = lambda x, q: float(np.percentile(x, q))
def dist(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return None if not len(x) else dict(n=len(x), p10=P(x, 10), p50=P(x, 50), p90=P(x, 90), mean=float(np.mean(x)))

# ================= (a) the sign-reversal channel =================
R['sign_reversal'] = {}
for nm, lo, hi in (('2-8', 2, 8), ('8-12', 8, 12), ('2-12', 2, 12)):
    m = ret & (v >= lo) & (v < hi)
    R['sign_reversal'][nm] = dict(n=int(m.sum()),
        min_zo_s_i0_to_bk=dist(zo_min_bk[m]), min_zo_s_i0_to_slipend=dist(zo_min_se[m]),
        frac_inward_ge_25pct_by_bk=float(np.mean(zo_min_bk[m] <= -0.25 * LEVEL)),
        frac_inward_ge_50pct_by_bk=float(np.mean(zo_min_bk[m] <= -0.50 * LEVEL)),
        frac_inward_ge_25pct_by_slipend=float(np.mean(zo_min_se[m] <= -0.25 * LEVEL)),
        frac_inward_ge_50pct_by_slipend=float(np.mean(zo_min_se[m] <= -0.50 * LEVEL)),
        inward_share_of_hw_p50=float(np.median(-zo_min_se[m] / hw[m])),
        inward_share_of_hw_p90=float(np.percentile(-zo_min_se[m] / hw[m], 90)))
# does every cf-crosses-but-logged-does-not episode have zo_s < 0?  (the structural check)
cf = col('cf_cross_in').astype(bool); lg = col('logged_cross_in').astype(bool)
odd = ret & cf & ~lg
R['sign_reversal']['structural_check'] = dict(
    n_cf_cross_not_logged=int(odd.sum()),
    all_have_negative_zo=bool(np.all(zo_min_bk[odd] < 0)) if odd.sum() else None,
    min_zo_of_those=dist(zo_min_bk[odd]))

# ================= (b) contamination tiers =================
C1 = np.isfinite(onlead_i0) & (onlead_i0 <= 0.5) & (onlead_i0 >= -1.0)   # the switch-off lands on the episode
C2 = zo_max_dw > 0.25 * LEVEL                                            # still on inside the dwell
C3 = zo_min_se <= -0.25 * LEVEL                                          # re-armed inward (centre crossing)
C4 = t_on >= 0                                                           # any >=50% dose in the 3 s before
TIER = {'C1_switchoff_on_episode': C1, 'C2_on_inside_dwell': C2, 'C3_rearmed_inward': C3,
        'C1|C2': C1 | C2, 'C1|C2|C3': C1 | C2 | C3, 'C1|C2|C3|C4': C1 | C2 | C3 | C4}
R['tiers'] = {}
for nm, lo, hi in (('2-8', 2, 8), ('8-12', 8, 12), ('2-12', 2, 12)):
    m = ret & (v >= lo) & (v < hi)
    d = dict(n_returns=int(m.sum()))
    for tn, tm in TIER.items():
        d[tn] = dict(contaminated=int((m & tm).sum()), clean=int((m & ~tm).sum()),
                     frac_clean=float((m & ~tm).sum() / max(m.sum(), 1)))
    R['tiers'][nm] = d
R['tiers_per_route'] = {}
for rk in sorted(set(route)):
    for nm, lo, hi in (('2-8', 2, 8), ('2-12', 2, 12)):
        m = ret & (route == rk) & (v >= lo) & (v < hi)
        R['tiers_per_route'][f'{rk}|{nm}'] = dict(group=str(grp[m][0]) if m.sum() else '', n_returns=int(m.sum()),
            clean_C1=int((m & ~C1).sum()), clean_C1C2C3=int((m & ~(C1 | C2 | C3)).sum()),
            clean_all=int((m & ~(C1 | C2 | C3 | C4)).sum()))

# ================= (c) FAIL clause 1 power =================
def mde_within(x, n_sub, stat, nb=4000, seed=1):
    """Null distribution of the statistic under resampling n_sub episodes from the same pool ->
    the two-sided 95 % detection threshold, and the 80 %-power MDE for a location shift."""
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    rng = np.random.default_rng(seed)
    base = stat(x)
    draws = np.array([stat(x[rng.integers(0, len(x), n_sub)]) for _ in range(nb)])
    sd = float(np.std(draws))
    thr = float(np.percentile(np.abs(draws - base), 95))
    return dict(n_pool=len(x), n_sub=n_sub, base=float(base), sd_of_stat=sd,
                detect_thr_95=thr, mde_80pct_power=float(thr + 0.842 * sd))


p50 = lambda x: float(np.median(x))
p90 = lambda x: float(np.percentile(x, 90))
R['clause1_power'] = {}
for nm, lo, hi in (('2-8', 2, 8), ('2-12', 2, 12)):
    m = ret & (v >= lo) & (v < hi)
    pool_dw = dwell[m]; pool_os = os30[m]
    d = dict(n_pool=int(m.sum()), dwell_p50=p50(pool_dw), os30_p90=p90(pool_os),
             dwell_p50_ci=boot_ci(pool_dw, route[m], p50), os30_p90_ci=boot_ci(pool_os, route[m], p90))
    for n_sub in (7, 9, 11, 20, 29, 37, 50, int(m.sum())):
        if n_sub > m.sum():
            continue
        d[f'dwell_p50|n={n_sub}'] = mde_within(pool_dw, n_sub, p50)
        d[f'os30_p90|n={n_sub}'] = mde_within(pool_os, n_sub, p90)
    # clean subsets
    for tn, tm in (('clean_C1', ~C1), ('clean_C1C2C3', ~(C1 | C2 | C3)), ('clean_all', ~(C1 | C2 | C3 | C4))):
        mm = m & tm
        if mm.sum() >= 5:
            d[f'{tn}|n'] = int(mm.sum())
            d[f'{tn}|dwell_p50'] = p50(dwell[mm]); d[f'{tn}|os30_p90'] = p90(os30[mm])
            d[f'{tn}|dwell_mde'] = mde_within(dwell[mm], int(mm.sum()), p50)
            d[f'{tn}|os30_mde'] = mde_within(os30[mm], int(mm.sum()), p90)
    # per-route statistics = the route-to-route noise a single new drive must beat
    pr = {}
    for rk in sorted(set(route[m])):
        mm = m & (route == rk)
        if mm.sum() >= 5:
            pr[rk] = dict(n=int(mm.sum()), group=str(grp[mm][0]), dwell_p50=p50(dwell[mm]), os30_p90=p90(os30[mm]),
                          n_clean_C1=int((mm & ~C1).sum()))
    d['per_route'] = pr
    if len(pr) >= 3:
        dv = np.array([x['dwell_p50'] for x in pr.values()]); ov = np.array([x['os30_p90'] for x in pr.values()])
        d['between_route_spread'] = dict(n_routes=len(pr), dwell_p50_min=float(dv.min()), dwell_p50_max=float(dv.max()),
                                         dwell_p50_sd=float(np.std(dv, ddof=1)), os30_p90_min=float(ov.min()),
                                         os30_p90_max=float(ov.max()), os30_p90_sd=float(np.std(ov, ddof=1)))
    R['clause1_power'][nm] = d

# depart-side effect scale, for the equivalence comparison: what the term is MEANT to do
R['depart_reference'] = {}
for nm, lo, hi in (('2-8', 2, 8), ('2-12', 2, 12)):
    m = (~ret) & (v >= lo) & (v < hi)
    R['depart_reference'][nm] = dict(n=int(m.sum()), dwell_p50=p50(dwell[m]), os30_p90=p90(os30[m]),
                                     dwell_p50_ci=boot_ci(dwell[m], route[m], p50),
                                     hw=float(np.median(hw[m])), dz_over_hw_intent=float(np.median(dz[m] / hw[m])))
json.dump(R, open(OUT + '/so_power.json', 'w'), indent=1, default=float)
print(json.dumps(R, indent=1, default=float)[:1200])
