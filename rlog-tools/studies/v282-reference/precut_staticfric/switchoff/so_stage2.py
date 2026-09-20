"""Stage 2: the five switch-off questions, answered on the logged episodes.  -> out/so_switchoff.json

Q1  fraction of RETURN episodes preceded, within the switch's realised settling time, by a substantially
    non-zero z_out; the realised dz and its duration (not assumed to be a clean step).
Q2  how much of the inward requirement hw the realised switch-off supplies, per episode.
Q3  does the switch-off by itself carry the command across the inward release edge?
Q4  reverse contamination: is the switch-ON late vs the 55-75 ms loop delay + the 0.10 s rate filter?
Q5  the null control's remaining power.
"""
import sys, glob, json
import numpy as np
from solib import OUT, LEVEL, boot_ci
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')

ROWS, SLIP, DUTY, WZ, WU = [], [], {}, [], []
for f in sorted(glob.glob(OUT + '/*_so.npz')):
    D = np.load(f, allow_pickle=True)
    ROWS += list(D['rows']); SLIP += list(D['slipend'])
    rk = f.replace('\\', '/').split('/')[-1][:-7]
    DUTY[rk] = D['duty'].item()
    WZ.append(D['wz']); WU.append(D['wu'])
WZ = np.concatenate(WZ); WU = np.concatenate(WU)
N = len(ROWS)
col = lambda k: np.array([r[k] for r in ROWS], dtype=float) if not isinstance(ROWS[0][k], str) else np.array([r[k] for r in ROWS])
route = col('route'); grp = col('group'); v = col('v'); ret = col('ret').astype(bool)
hw = col('hw'); g = col('g'); dz = col('dz'); pk = col('zo_peak'); fall = col('fall_s')
t_on = col('t_on'); t_off = col('t_off')
onlead_i0 = col('on_lead_i0_s'); onlead_bk = col('on_lead_bk_s')
offlead_i0 = col('off_lead_i0_s'); offlead_bk = col('off_lead_bk_s')
dwell = col('dwell_s'); kind = col('kind'); absaa = col('abs_aa')
R = {}
R['n'] = dict(total=N, returns=int(ret.sum()), departs=int((~ret).sum()),
              by_route={rk: dict(n=int((route == rk).sum()), ret=int((ret & (route == rk)).sum())) for rk in sorted(set(route))})
R['duty'] = DUTY

P = lambda x, q: float(np.percentile(x, q)) if len(x) else None
def dist(x, name=''):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return None
    return dict(n=len(x), p10=P(x, 10), p25=P(x, 25), p50=P(x, 50), p75=P(x, 75), p90=P(x, 90),
                mean=float(np.mean(x)), min=float(np.min(x)), max=float(np.max(x)))

BANDS = [('2-8', 2, 8), ('8-12', 8, 12), ('2-12', 2, 12), ('12+', 12, 99)]

# =============== Q1: is a return preceded by a substantially non-zero z_out? ===============
R['Q1_preceded'] = {}
for nm, lo, hi in BANDS:
    m = ret & (v >= lo) & (v < hi)
    if m.sum() == 0:
        continue
    d = dict(n=int(m.sum()))
    # "substantially on" at several thresholds, over several lookback windows before the DWELL START
    for thr_f in (0.25, 0.5, 0.75):
        for win_s in (0.1, 0.2, 0.5, 1.0, 3.0):
            # t_on is the last index with zo_s >= 0.5*LEVEL in [i0-3s, bk]; for other thresholds use the peak
            if thr_f == 0.5:
                ok = m & np.isfinite(onlead_i0) & (onlead_i0 <= win_s)
            else:
                ok = m & (pk >= thr_f * LEVEL) & np.isfinite(onlead_i0) & (onlead_i0 <= win_s)
            d[f'frac_on{int(thr_f*100)}_within_{win_s}s'] = float(ok.sum() / m.sum())
    d['frac_any_on50_within_3s'] = float((m & (t_on >= 0)).sum() / m.sum())
    d['peak_zo_pre'] = dist(pk[m])
    d['realised_dz'] = dist(dz[m & (t_on >= 0)])
    d['z_hold'] = dist(col('z_hold')[m & (t_on >= 0)])
    d['dz_first_100ms'] = dist(col('dz100')[m & (t_on >= 0)])
    d['dz_first_200ms'] = dist(col('dz200')[m & (t_on >= 0)])
    d['fall_90to10_s'] = dist(fall[m & (t_on >= 0)])
    d['on_lead_to_dwell_start_s'] = dist(onlead_i0[m & (t_on >= 0)])
    d['on_lead_to_breakaway_s'] = dist(onlead_bk[m & (t_on >= 0)])
    d['off_lead_to_dwell_start_s'] = dist(offlead_i0[m & (t_on >= 0)])
    d['zo_still_on_at_dwell_start'] = dist(col('zo_i0')[m])
    d['zo_max_inside_dwell'] = dist(col('zo_max_in_dwell')[m])
    d['frac_zo_i0_gt_25pct'] = float(np.mean(col('zo_i0')[m] > 0.25 * LEVEL))
    d['frac_zo_maxdwell_gt_25pct'] = float(np.mean(col('zo_max_in_dwell')[m] > 0.25 * LEVEL))
    d['frac_zo_maxdwell_gt_50pct'] = float(np.mean(col('zo_max_in_dwell')[m] > 0.5 * LEVEL))
    R['Q1_preceded'][nm] = d

# =============== Q2: share of the inward requirement hw that the switch-off supplies ===============
R['Q2_share'] = {}
trav = col('trav_log')
for nm, lo, hi in BANDS:
    m = ret & (v >= lo) & (v < hi) & (t_on >= 0)
    if m.sum() < 3:
        continue
    frac_hw = dz[m] / hw[m]
    tot = trav[m] + dz[m]           # counterfactual inward command travel t_on -> breakaway
    share = np.where(np.abs(tot) > 1e-9, dz[m] / tot, np.nan)
    R['Q2_share'][nm] = dict(n=int(m.sum()), hw=float(np.median(hw[m])),
                             dz_over_hw=dist(frac_hw),
                             dz_over_hw_ci=boot_ci(frac_hw, route[m], np.median),
                             logged_inward_travel_t_on_to_bk=dist(trav[m]),
                             dz_share_of_cf_travel=dist(share),
                             frac_dz_over_hw_gt_0p3=float(np.mean(frac_hw > 0.3)),
                             frac_dz_over_hw_gt_0p5=float(np.mean(frac_hw > 0.5)))

# =============== Q3: can the switch-off alone carry the command across the inward edge? ===============
# Structural: u_s' = u_s + zo_s with zo_s >= 0 whenever sign(angle_des)==s, so the counterfactual command
# never sits INSIDE-of-logged; the switch-off returns it TO the logged trajectory.  Check that numerically,
# then count the episodes where the counterfactual crosses -hw and the logged one does not.
zo_neg = np.array([r['zo_peak'] for r in ROWS])  # placeholder (peak is >=0 by construction of max)
R['Q3_cross'] = {}
for nm, lo, hi in BANDS:
    m = ret & (v >= lo) & (v < hi)
    if m.sum() < 3:
        continue
    lc = col('logged_cross_in').astype(bool)[m]; cc = col('cf_cross_in').astype(bool)[m]
    mm = m & (t_on >= 0)
    R['Q3_cross'][nm] = dict(n=int(m.sum()),
        logged_crosses_inward_edge=int(lc.sum()), cf_crosses_inward_edge=int(cc.sum()),
        cf_crosses_but_logged_does_not=int(np.sum(cc & ~lc)),
        logged_crosses_but_cf_does_not=int(np.sum(lc & ~cc)),
        margin_at_switch_on_t_on=dist(col('marg_on')[mm]),
        margin_at_switch_off_complete=dist(col('marg_off')[mm]),
        margin_at_dwell_start=dist(col('marg_i0')[m]),
        frac_margin_at_t_on_below_dz=float(np.mean(col('marg_on')[mm] < dz[mm])),
        frac_margin_at_t_on_negative=float(np.mean(col('marg_on')[mm] < 0)))
# where in the dwell does the switch-off land (for the episodes where it lands inside)?
m = ret & (t_on >= 0) & (v < 12)
inside = m & (t_off >= col('i0')) & (t_off <= col('i1'))
R['Q3_cross']['switchoff_inside_dwell'] = dict(
    n_ret_v_lt_12=int(m.sum()), n_off_inside_dwell=int(inside.sum()),
    frac=float(inside.sum() / max(m.sum(), 1)),
    rel_pos_in_dwell=dist(((t_off - col('i0')) / np.maximum(col('i1') - col('i0'), 1))[inside]),
    dz_when_inside=dist(dz[inside]))

# =============== Q3b: the slip-end premise (does an outward slip end at the far edge?) ===============
sl = {k: np.array([s[k] for s in SLIP], dtype=object if isinstance(SLIP[0][k], str) else float) for k in SLIP[0]}
sret = sl['ret'].astype(bool); sv = sl['v'].astype(float)
R['Q3b_slip_end'] = {}
for nm, lo, hi in BANDS[:3]:
    for lbl, mm in (('depart', ~sret), ('return', sret)):
        m = mm & (sv >= lo) & (sv < hi)
        if m.sum() < 5:
            continue
        R['Q3b_slip_end'][f'{nm}|{lbl}'] = dict(n=int(m.sum()), hw=float(np.median(sl['hw'][m].astype(float))),
            us_at_breakaway=dist(sl['us_bk'][m].astype(float)),
            us_at_slip_end=dist(sl['us_end'][m].astype(float)),
            zo_s_at_slip_end=dist(sl['zo_end'][m].astype(float)),
            frac_zo_end_gt_50pct=float(np.mean(sl['zo_end'][m].astype(float) > 0.5 * LEVEL)),
            slip_deg=dist(sl['slip'][m].astype(float)))

# =============== Q4: switch-ON timing on DEPART episodes ===============
R['Q4_switch_on'] = {}
for nm, lo, hi in BANDS[:3]:
    m = (~ret) & (v >= lo) & (v < hi)
    if m.sum() < 3:
        continue
    d = dict(n=int(m.sum()),
             zo_at_bk_minus_65ms=dist(col('zo_bk_delayed')[m]),
             zo_at_bk_minus_30ms=dist(col('zo_bk3')[m]),
             zo_at_bk=dist(col('zo_bk')[m]),
             frac_zo_at_bk65_gt_50pct=float(np.mean(col('zo_bk_delayed')[m] > 0.5 * LEVEL)),
             frac_zo_at_bk65_gt_25pct=float(np.mean(col('zo_bk_delayed')[m] > 0.25 * LEVEL)),
             frac_zo_at_bk65_near_zero=float(np.mean(col('zo_bk_delayed')[m] < 0.05 * LEVEL)),
             on50_rel_bk_s=dist(col('on50_rel_bk_s')[m]),
             frac_on50_before_bk_minus_65ms=float(np.mean(col('on50_rel_bk_s')[m] < -0.065)),
             cf_out_rel_bk_s=dist(col('cf_out_rel_bk_s')[m]),
             lg_out_rel_bk_s=dist(col('lg_out_rel_bk_s')[m]))
    both = m & np.isfinite(col('cf_out_rel_bk_s')) & np.isfinite(col('lg_out_rel_bk_s'))
    adv = (col('lg_out_rel_bk_s') - col('cf_out_rel_bk_s'))[both]
    d['advance_of_release_s'] = dist(adv)
    d['n_both_release_windows'] = int(both.sum())
    R['Q4_switch_on'][nm] = d

json.dump(R, open(OUT + '/so_switchoff.json', 'w'), indent=1, default=float)
print(json.dumps({k: R[k] for k in ['n', 'Q1_preceded', 'Q2_share']}, indent=1, default=float)[:7000])
