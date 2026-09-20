"""A7: verify the frame by the channel identity, and attack MY OWN low-angle result.

(a) The channel identity cmd == P+I+hold_ff+move+z+rl+dob is only satisfied if every channel's SIGN is
    right.  Quantify what a dob sign flip would do to it -- that is the independent check of the +left
    convention the whole analysis rests on.
(b) My finding "the outward offset vanishes at |aa| < 1 deg" could be sign-label noise: aa LSB is 0.1 deg
    and sign(aa) is evaluated at breakaway.  Re-run with (i) |aa| > 0.5 only, (ii) sign taken from the
    dwell-mean angle, (iii) sign taken from angle_des.  Label noise ATTENUATES, so if the low bin stays
    near zero under a cleaner sign it is not an artefact.
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP); ar = np.arange(N); IDX = PRE - 3
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
m28 = TQ & (v >= 2) & (v < 8)
out = {}

ch = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']
S = sum(W[k] for k in ch)
r_ok = (W['cmd'] - S)[m28][:, IDX]
r_flip = (W['cmd'] - (S - 2 * W['dob']))[m28][:, IDX]
r_nodob = (W['cmd'] - (S - W['dob']))[m28][:, IDX]
print('(a) identity residual rms at breakaway, torque 2-8:')
print('   as extracted        ', round(float(np.sqrt(np.mean(r_ok ** 2))), 6))
print('   with dob SIGN FLIPPED', round(float(np.sqrt(np.mean(r_flip ** 2))), 6))
print('   with dob DROPPED     ', round(float(np.sqrt(np.mean(r_nodob ** 2))), 6))
print('   |dob| rms            ', round(float(np.sqrt(np.mean(W['dob'][m28, IDX] ** 2))), 6))
out['identity'] = dict(rms_as_extracted=round(float(np.sqrt(np.mean(r_ok ** 2))), 6),
                       rms_dob_flipped=round(float(np.sqrt(np.mean(r_flip ** 2))), 6),
                       rms_dob_dropped=round(float(np.sqrt(np.mean(r_nodob ** 2))), 6),
                       dob_rms=round(float(np.sqrt(np.mean(W['dob'][m28, IDX] ** 2))), 6))

print('\n(b) low-angle bin under three sign definitions')
d0c = np.maximum(c('w_d0'), 0)
sign_defs = {
    'sign(aa) at breakaway (study)': np.sign(W['aa'][:, PRE]),
    'sign(mean aa over the dwell)': np.sign(np.array([W['aa'][i, d0c[i]:PRE].mean() for i in range(N)])),
    'sign(angdes) at breakaway': np.sign(W['angdes'][ar, IDX]),
}
rows = {}
for lab, sg in sign_defs.items():
    tw = (sj == -sg)
    y = (W['cmd'][ar, IDX] - holdlev[ar, IDX]) * sg
    aab = np.abs(W['aa'][ar, IDX])

    def med_c(ii):
        a = ii[~tw[ii]]; t = ii[tw[ii]]
        if len(a) < 3 or len(t) < 3:
            return np.array([np.nan, np.nan])
        return np.array([(np.median(y[a]) + np.median(y[t])) / 2.0, (np.median(y[a]) - np.median(y[t])) / 2.0])
    print(f'  --- {lab} (agrees with study on {np.mean(sg[m28] == np.sign(W["aa"][:, PRE])[m28]) * 100:.0f}% of episodes)')
    for a0, a1 in [(0, 0.5), (0.5, 1), (1, 2), (2, 4), (4, 1e9)]:
        mm = m28 & (aab >= a0) & (aab < a1)
        if (mm & ~tw).sum() < 3 or (mm & tw).sum() < 3:
            print(f'     |aa| {a0}-{a1}: n={int(mm.sum())} too few'); continue
        est, lo, hi, bs = boot_routes(med_c, route, mm, nb=600, seed=4)
        lo = np.nanpercentile(bs, 2.5, axis=0); hi = np.nanpercentile(bs, 97.5, axis=0)
        rows[f'{lab}|{a0}-{a1}'] = [int(mm.sum()), round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)],
                                    round(float(est[1]), 5)]
        print(f'     |aa| {a0:>4}-{a1:<4} n={int(mm.sum()):3d} centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  hw {est[1]:+.5f}')
out['lowangle_sign_robustness'] = rows
json.dump(out, open('out/a7_checks.json', 'w'), indent=1)
