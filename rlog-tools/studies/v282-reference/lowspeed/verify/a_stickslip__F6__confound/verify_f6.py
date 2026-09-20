"""Adversarial verification of F6 (lever-reach BELIEF), lens CONFOUND.

F6 claims a rise-attribution split (hold ~28%, z ~26%, P 17%, move 14%, observer(dob) 9%, rate-loop 7%,
I ~0) across the pooled torque group (T64,T64B,T5,T4) at 2-8 m/s, and cites this to argue the observer
(ARM-D lever) contributes little pre-release (9%) and is largely irrelevant below 8 m/s.

Confounds named by the orchestrator:
  - T64B carries 4x the demand of T64/6c-6d (per CLAUDE.md route table) -> may not represent the flown
    rev-6.4 config's dwell dynamics; pooling it into TQ could bias the attribution.
  - The V282 reference is mostly ONE 62-segment route (0000006c--2bc842dbac) -> the V282 comparison
    numbers (slip ratio etc, used in the surrounding stream summary) could be dominated by one route.

This script re-derives R['accumulation']['2-8|all'] (a) as shipped (TQ = all 4 torque groups) and
(b) with T64B dropped, and separately re-derives the matched V282 slip comparison (a) as shipped and
(b) with the 62-seg V282 route dropped, restricted to a speed/angle/demand-matched pair set (nearest
neighbour, same code as ss_analyze.match). Everything below is EVIDENCE (recomputed from the same
out/*_ss.npz episode tables ss_extract.py already wrote) unless marked BELIEF.
"""
import sys, json, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
from ss_load import load_all, boot_ci
from sslib import k_of_v

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); d0 = np.maximum(col('w_d0'), 0)
route = col('route'); kind = col('kind'); aa_abs = col('abs_aa'); dr = col('dem_rate'); dwell = col('dwell_s')
slip = col('slip'); j30 = col('j30')
PRE = 150
BK = PRE - 3
ar = np.arange(N)
A = lambda k, idx: W[k][ar, idx] * sj
terms = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']

V282_62SEG = '0000006c--2bc842dbac'


def accumulation_fracs(mask, lo, hi, label):
    m = mask & (v >= lo) & (v < hi)
    n = int(m.sum())
    if n < 8:
        return dict(n=n, note='too few episodes')
    cmd_change = float(np.mean((A('cmd', np.full(N, BK)) - A('cmd', d0))[m]))
    out = dict(n=n, cmd_change=cmd_change, routes=sorted(set(route[m])))
    fracs = {}
    for k in terms:
        chg = float(np.mean((A(k, np.full(N, BK)) - A(k, d0))[m]))
        fracs[k] = dict(change=chg, frac_of_cmd=chg / cmd_change if cmd_change else float('nan'))
    out['fracs'] = fracs
    print(f'--- {label}  n={n} (2-8m/s excl. n/a) cmd_change={cmd_change:.5f}')
    for k in terms:
        print(f'    {k:8s} change={fracs[k]["change"]:+.5f}  frac_of_cmd={100*fracs[k]["frac_of_cmd"]:5.1f}%')
    return out


def match(tmask, rmask):
    """Verbatim copy of ss_analyze.match: nearest-neighbour on v, log(1+|aa|), log(dem_rate)."""
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        if len(ri) == 0:
            continue
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = np.argmin(dist)
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


def matched_slip(tmask, rmask, lo, hi, label):
    tm = tmask & (v >= lo) & (v < hi)
    rm = rmask & (v >= lo - 1) & (v < hi + 1)
    P_ = match(tm, rm)
    if len(P_) < 5:
        print(f'--- {label}: only {len(P_)} matched pairs, skipping')
        return dict(n_pairs=len(P_))
    ti = np.array([p[0] for p in P_]); ri = np.array([p[1] for p in P_])
    lr = np.log((slip[ti] + 0.3) / (slip[ri] + 0.3))
    ratio, ci = boot_ci(lr, route[ti], lambda x: float(np.exp(np.mean(x))))
    out = dict(n_pairs=len(P_), n_torque_pool=int(tm.sum()), n_v282_pool=int(rm.sum()),
               torque_routes=sorted(set(route[ti])), v282_routes=sorted(set(route[ri])),
               torque_slip_p50=float(np.median(slip[ti])), v282_slip_p50=float(np.median(slip[ri])),
               torque_slip_p90=float(np.percentile(slip[ti], 90)), v282_slip_p90=float(np.percentile(slip[ri], 90)),
               slip_ratio_geo=ratio, ci=list(ci))
    print(f'--- {label}: n_pairs={len(P_)} torque_routes={out["torque_routes"]} v282_routes={out["v282_routes"]}')
    print(f'    slip p50 torque={out["torque_slip_p50"]:.2f} v282={out["v282_slip_p50"]:.2f}'
          f'  ratio_geo={ratio:.2f} CI={[round(c,2) for c in ci]}')
    return out


R = {}
TQ_ALL = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
TQ_NO64B = np.isin(g, ['T64', 'T5', 'T4'])
V282_ALL = g == 'V282'
V282_NO62 = V282_ALL & (route != V282_62SEG)

print('=' * 70)
print('PART 1: rise-attribution fractions, 2-8 m/s, pooled torque group')
print('=' * 70)
R['accum_2_8_TQ_ALL'] = accumulation_fracs(TQ_ALL, 2, 8, 'TQ_ALL (as shipped, incl. T64B 4x-demand)')
R['accum_2_8_TQ_NO64B'] = accumulation_fracs(TQ_NO64B, 2, 8, 'TQ_NO_T64B (confound removed)')
# per-group breakdown so we can see whether T64B is an outlier driving the pooled number
for grp in ['T64', 'T64B', 'T5', 'T4']:
    R[f'accum_2_8_{grp}'] = accumulation_fracs(g == grp, 2, 8, f'{grp} only')

print()
print('=' * 70)
print('PART 2: matched V282-vs-torque slip ratio, with/without the 62-seg V282 route')
print('=' * 70)
for lo, hi in [(2, 8), (8, 15)]:
    R[f'matched_{lo}_{hi}_ALL'] = matched_slip(TQ_NO64B, V282_ALL, lo, hi, f'{lo}-{hi} v282=ALL (incl. 62-seg 6c)')
    R[f'matched_{lo}_{hi}_NO62'] = matched_slip(TQ_NO64B, V282_NO62, lo, hi, f'{lo}-{hi} v282=NO-62SEG')

print()
print('=' * 70)
print('PART 3: does T64B (4x demand) look like the other torque routes in this band?')
print('=' * 70)
for grp in ['T64', 'T64B', 'T5', 'T4']:
    m = (g == grp) & (v >= 2) & (v < 8)
    if m.sum() < 3:
        print(f'{grp}: n={int(m.sum())} too few'); continue
    print(f'{grp}: n={int(m.sum())} dem_rate p50={np.median(dr[m]):.3f} dwell p50={np.median(dwell[m]):.2f}s '
          f'slip p50={np.median(slip[m]):.2f} abs_aa p50={np.median(aa_abs[m]):.1f}')

json.dump(R, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/a_stickslip__F6__confound/verify_f6.json', 'w'), indent=1, default=float)
