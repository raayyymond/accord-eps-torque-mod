"""A8: the one picture the verdict rests on -- centre vs |angle| (rises) against half-width vs |angle|
(flat), with the candidate's own delivered shape level*max(0,s_a*s_r)*s_a overlaid."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP); ar = np.arange(N); IDX = PRE - 3
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
sgn = np.sign(W['aa'][:, PRE]); toward = (sj == -sgn)
y = (W['cmd'][ar, IDX] - holdlev[ar, IDX]) * sgn
absaa = np.abs(W['aa'][ar, IDX])
BINS = [(0, 1), (1, 2), (2, 4), (4, 8), (8, 40)]


def med_c(ii):
    a = ii[~toward[ii]]; t = ii[toward[ii]]
    if len(a) < 3 or len(t) < 3:
        return np.array([np.nan, np.nan])
    return np.array([(np.median(y[a]) + np.median(y[t])) / 2.0, (np.median(y[a]) - np.median(y[t])) / 2.0])


fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4))
for ax, (lo_, hi_, ttl) in zip(axs, [(2, 8, 'torque mode, 2-8 m/s  (n=145)'), (8, 15, 'torque mode, 8-15 m/s  (n=366)')]):
    m = TQ & (v >= lo_) & (v < hi_)
    X, C, CL, CH, H, HL, HH = [], [], [], [], [], [], []
    for a0, a1 in BINS:
        mm = m & (absaa >= a0) & (absaa < a1)
        if (mm & ~toward).sum() < 3 or (mm & toward).sum() < 3:
            continue
        est, _, _, bs = boot_routes(med_c, route, mm, nb=600, seed=3)
        q = np.nanpercentile(bs, [2.5, 97.5], axis=0)
        X.append(np.median(absaa[mm])); C.append(est[0]); CL.append(q[0, 0]); CH.append(q[1, 0])
        H.append(est[1]); HL.append(q[0, 1]); HH.append(q[1, 1])
    X = np.array(X)
    ax.errorbar(X, C, yerr=[np.array(C) - np.array(CL), np.array(CH) - np.array(C)], fmt='o-', color='#c0392b',
                capsize=3, label='band CENTRE  (outward offset)')
    ax.errorbar(X, H, yerr=[np.array(H) - np.array(HL), np.array(HH) - np.array(H)], fmt='s--', color='#2471a3',
                capsize=3, label='band HALF-WIDTH')
    a = np.linspace(0.05, 25, 400)
    sa = np.tanh(a / 1.0)
    ax.plot(a, 0.020 * np.maximum(0, sa * 1.0) * sa, color='#117a65', lw=2,
            label=r'candidate delivered: $0.020\,s_a^2$ (s_r=1)')
    ax.axhline(0.020, color='#117a65', ls=':', lw=1)
    ax.set_xscale('log'); ax.set_xlabel('|steering angle| at breakaway, deg')
    ax.set_ylabel('torque (output units), outward +')
    ax.set_title(ttl, fontsize=10); ax.grid(alpha=0.3); ax.axhline(0, color='k', lw=0.6)
    ax.legend(fontsize=8, loc='upper left')
fig.suptitle('The outward offset is NOT a flat Coulomb intercept: the CENTRE rises ~8x with angle while the '
             'HALF-WIDTH is flat\n(median-based, route-cluster bootstrap CIs, hold map at the route\'s own '
             'AccordHoldLevel)', fontsize=9.5)
fig.tight_layout(rect=[0, 0, 1, 0.90])
fig.savefig('out/fig_centre_vs_angle.png', dpi=130)
print('wrote out/fig_centre_vs_angle.png')
