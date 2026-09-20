"""A1: what the 145 episodes actually are, and whether direction is confounded with angle/speed/route.
A sign(aa)-coefficient fit can only mean "friction" if away and toward episodes are drawn from the
SAME (|aa|, v, route) population.  If they are not, any misspecification of the aa term aliases into it.
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
aa_bk = W['aa'][:, PRE]
sgn = np.sign(aa_bk)
toward = (sj == -sgn)
N = len(EP)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
kind = c('kind'); dwell = c('dwell_s'); w_d0 = c('w_d0'); w_d1 = c('w_d1')

out = {}
print('total episodes', N, 'torque', int(TQ.sum()))
for lab, m in (('torque 2-8', TQ & (v >= 2) & (v < 8)), ('torque 8-15', TQ & (v >= 8) & (v < 15)),
               ('V282 2-8', (g == 'V282') & (v >= 2) & (v < 8))):
    n = int(m.sum())
    A, T_ = m & ~toward, m & toward
    row = dict(n=n, n_away=int(A.sum()), n_toward=int(T_.sum()),
               routes={str(r): int((m & (route == r)).sum()) for r in np.unique(route[m])},
               routes_away={str(r): int((A & (route == r)).sum()) for r in np.unique(route[m])},
               absaa_away=[round(float(x), 2) for x in np.percentile(np.abs(aa_bk[A]), [10, 50, 90])],
               absaa_toward=[round(float(x), 2) for x in np.percentile(np.abs(aa_bk[T_]), [10, 50, 90])],
               v_away=[round(float(x), 2) for x in np.percentile(v[A], [10, 50, 90])],
               v_toward=[round(float(x), 2) for x in np.percentile(v[T_], [10, 50, 90])],
               n_absaa_lt_0p3=int((np.abs(aa_bk[m]) < 0.3).sum()),
               n_absaa_lt_1=int((np.abs(aa_bk[m]) < 1.0).sum()),
               kind={k: int((m & (kind == k)).sum()) for k in np.unique(kind[m])},
               kind_away={k: int((A & (kind == k)).sum()) for k in np.unique(kind[m])},
               dwell_s=[round(float(x), 3) for x in np.percentile(dwell[m], [10, 50, 90])],
               n_wd0_clipped=int((w_d0[m] < 0).sum()), n_wd0_eq0=int((w_d0[m] == 0).sum()),
               wd0=[int(x) for x in np.percentile(w_d0[m], [5, 50, 95])])
    # point-biserial correlations: is direction predicted by angle / speed?
    for nm, x in (('absaa', np.abs(aa_bk)), ('v', v), ('dwell', dwell)):
        row[f'corr_toward_{nm}'] = round(float(np.corrcoef(toward[m].astype(float), x[m])[0, 1]), 3)
    out[lab] = row
    print('==', lab); print(json.dumps(row, indent=1))

# how many torque 2-8 episodes have a hold-map level factor of 1.15 vs 1.0 (HoldLevel off on T64B)
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
print('torque 2-8 with HoldLevel on:', int((TQ & (v >= 2) & (v < 8) & lev).sum()), 'off:',
      int((TQ & (v >= 2) & (v < 8) & ~lev).sum()))
out['holdlevel_on_2_8'] = int((TQ & (v >= 2) & (v < 8) & lev).sum())
out['holdlevel_off_2_8'] = int((TQ & (v >= 2) & (v < 8) & ~lev).sum())
json.dump(out, open('out/a1_census.json', 'w'), indent=1)
