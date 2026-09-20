"""Follow-up to verify_f6.py: F6's rise-attribution pools T64+T64B+T5+T4 ('TQ').  T4 = rev 4
(route 00000075--6c8687d5bd) has AccordDobHz=None in its own fork params and its logged dob channel
is EXACTLY zero on every frame (checked directly against fill_straightroad/cache/<rk>_fsr.npz) --
rev 4 shipped before the disturbance observer existed (memory: DOB shipped in rev 5, 2026-09-15).
Pooling a route that structurally cannot carry the dob term with routes that do dilutes the observer's
apparent share downward.  Recompute the accumulation fractions restricted to DOB_PRESENT = T64,T64B,T5
(the T64B-demand confound the orchestrator named is ALSO removable by further dropping T64B; both are
shown in verify_f6.py -- this file isolates the DOB_PRESENT vs T4-included effect only)."""
import sys, json, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
from ss_load import load_all, boot_ci

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); d0 = np.maximum(col('w_d0'), 0); route = col('route')
PRE = 150; BK = PRE - 3; ar = np.arange(N)
A = lambda k, idx: W[k][ar, idx] * sj
terms = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']

TQ_ALL = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
DOB_PRESENT = np.isin(g, ['T64', 'T64B', 'T5'])   # T4 excluded: dob is structurally 0 on every T4 frame

out = {}
for lo, hi in [(2, 8), (8, 15)]:
    for label, mask in [('TQ_ALL_incl_T4_no_observer', TQ_ALL), ('DOB_PRESENT_T64_T64B_T5', DOB_PRESENT)]:
        m = mask & (v >= lo) & (v < hi)
        n = int(m.sum())
        cmd_change = float(np.mean((A('cmd', np.full(N, BK)) - A('cmd', d0))[m]))
        row = dict(n=n, cmd_change=cmd_change)
        for k in terms:
            chg = (A(k, np.full(N, BK)) - A(k, d0))[m]
            est, ci = boot_ci(chg, route[m], np.mean)
            row[k] = dict(change=est, frac_of_cmd=est / cmd_change, frac_ci=[ci[0] / cmd_change, ci[1] / cmd_change])
        out[f'{lo}-{hi}|{label}'] = row
        print(f'{lo}-{hi} {label}: n={n} dob frac={100*row["dob"]["frac_of_cmd"]:.1f}%  '
              f'CI=[{100*row["dob"]["frac_ci"][0]:.1f},{100*row["dob"]["frac_ci"][1]:.1f}]')

json.dump(out, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/a_stickslip__F6__confound/verify_f6_dob_present.json', 'w'), indent=1, default=float)
