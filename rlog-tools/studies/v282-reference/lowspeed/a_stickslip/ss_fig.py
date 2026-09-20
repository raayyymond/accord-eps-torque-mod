"""Figure: what accumulates through a dwell, below 8 m/s.  Ensemble means, sign-aligned with the jump, t = 0 at breakaway.
Left: torque-mode routes, cumulative change of each command term since 0.5 s before breakaway (stacked lines, one axis, torque units).
Middle: wheel angle and fork desired angle relative to the wheel at breakaway, torque vs V282 (deg).
Right: breakaway command vs direction (bootstrap fit): the band the stuck command must cross."""
import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from ss_load import *
EP, W, EX, VAL = load_all(); N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump')[:, None]
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4']) & (v < 8); RF = (g == 'V282') & (v < 8)
t = (np.arange(W['cmd'].shape[1]) - PRE) / 100.0; r0 = PRE - 50
C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
for q, (k, lab) in enumerate([('hold_ff', 'hold FF k(v)*angle_des'), ('z', 'friction hysteresis z'), ('P', 'P'), ('move', 'move FF'),
                              ('dob', 'observer (-logged)'), ('rl', 'rate loop'), ('I', 'I')]):
    y = np.mean(((W[k] - W[k][:, [r0]]) * sj)[TQ], 0)
    ax[0].plot(t, y, color=C[q], lw=2, label=lab)
ax[0].plot(t, np.mean(((W['cmd'] - W['cmd'][:, [r0]]) * sj)[TQ], 0), color='#333333', lw=2.5, label='total command')
ax[0].axvline(-0.03, color='#999999', lw=1, ls='--'); ax[0].axhline(0, color='#cccccc', lw=1)
ax[0].set_xlim(-0.5, 0.8); ax[0].set_xlabel('s from breakaway'); ax[0].set_ylabel('change since -0.5 s, torque units (+ = jump direction)')
ax[0].set_title(f'Torque mode <8 m/s (n={TQ.sum()}): what builds the release'); ax[0].legend(fontsize=8, frameon=False)
for msk, nm, c in ((TQ, 'torque mode', C[1]), (RF, 'V282', C[0])):
    ax[1].plot(t, np.mean((W['aa'] - W['aa'][:, [PRE]]) * sj, 0)[msk] if False else np.mean(((W['aa'] - W['aa'][:, [PRE]]) * sj)[msk], 0), color=c, lw=2, label=f'{nm} wheel (n={msk.sum()})')
    ax[1].plot(t, np.mean(((W['angdes'] - W['aa'][:, [PRE]]) * sj)[msk], 0), color=c, lw=1.5, ls='--', label=f'{nm} fork desired angle')
ax[1].axvline(0, color='#999999', lw=1, ls='--'); ax[1].set_xlim(-1.0, 0.8); ax[1].set_ylim(-4, 6)
ax[1].set_xlabel('s from breakaway'); ax[1].set_ylabel('deg relative to wheel at breakaway'); ax[1].set_title('Wheel vs desired angle through the dwell, <8 m/s')
ax[1].legend(fontsize=8, frameon=False)
R = json.load(open(OUT + '/ss_centring_fit.json'))
labels = []; xs = 0
for sb in ['2-8', '8-15']:
    for when, mk in (('dwell_start', 'o'), ('breakaway', 's')):
        e = R[f'torque|{sb}|{when}']
        for q, key in enumerate(['away', 'toward']):
            val, ci = e[key]
            ax[2].errorbar(xs + q * 0.3, val, yerr=[[val - ci[0]], [ci[1] - val]], fmt=mk, color=C[q], ms=8, capsize=3,
                           label=(f'{key} from centre' if (sb == '2-8' and when == 'breakaway') else None))
        labels.append((xs + 0.15, f'{sb} m/s\n{when.replace("_", " ")}')); xs += 1
ax[2].axhline(0, color='#cccccc', lw=1); ax[2].set_xticks([l[0] for l in labels]); ax[2].set_xticklabels([l[1] for l in labels], fontsize=8)
ax[2].set_ylabel('command minus fitted linear spring, torque (+ = jump dir)'); ax[2].set_title('Command level: dwell start vs breakaway (95% CI)')
ax[2].legend(fontsize=8, frameon=False)
plt.tight_layout(); plt.savefig(OUT + '/ss_fig_dwell_mechanism.png', dpi=110); print('ok')
