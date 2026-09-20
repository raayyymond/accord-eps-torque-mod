"""risk stream figure: where the extra torque lands, and what leaks to the highway."""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
DIR = json.load(open(f'{OUT}/r_direction.json'))
CEN = json.load(open(f'{OUT}/r_census.json'))
EPI = json.load(open(f'{OUT}/r_episodes.json'))['res']
C = ['C0_flown', 'C5_half_k12', 'C2_lvl033_k12', 'C4_reach_k12', 'C6_reach_k68', 'C3_band110', 'C1_toggle_030']
LB = ['flown\n0.015/3.0', 'C5 half\n0.024/2.7', 'C2 ceil\n0.033/3.0', 'C4 reach\n0.033/2.4', 'C6 k6-8\n0.033/2.4', 'C3 slope\n0.015/1.1', 'C1 toggle\n0.030 flat']
x = np.arange(len(C))
fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.6))

# --- panel 1: delivery error by direction, sliding frames, 2-8 m/s
a = ax[0]
und = [DIR[f'2-8|{c}']['under_away_p50'] for c in C]
ovr = [DIR[f'2-8|{c}']['over_tow_p50'] for c in C]
a.bar(x - 0.19, und, 0.36, color='#3b6ea5', label='DEPART: still SHORT of release (42% of frames)')
a.bar(x + 0.19, ovr, 0.36, color='#c0504d', label='RETURN: OVER the release edge (58%)')
a.axhline(0, color='k', lw=0.8)
for i, (u, o) in enumerate(zip(und, ovr)):
    a.text(i - 0.19, u + 0.0012, f'{u:.3f}', ha='center', fontsize=7.5)
    a.text(i + 0.19, o + 0.0012, f'{o:.3f}', ha='center', fontsize=7.5)
a.set_title('Sliding frames, 2-8 m/s hands-off: the error is REDISTRIBUTED, not removed\n'
            'measured stuck band = hold + 0.020*sign(angle) +/- 0.033', fontsize=9.5)
a.set_ylabel('median delivery error, unit torque')
a.set_xticks(x); a.set_xticklabels(LB, fontsize=7.5); a.legend(fontsize=7.5); a.grid(axis='y', alpha=0.3)

# --- panel 2: extra settled angle bought on returns (over / k' measured)
a = ax[1]
for bn, col, lab in (('2-5', '#8d4e85', '2-5 m/s  k\'=0.0048'), ('5-8', '#4e8d6b', '5-8 m/s  k\'=0.0080')):
    a.plot(x, [DIR[f'{bn}|{c}']['extra_ang_p50'] for c in C], 'o-', color=col, label=lab)
a.axhline(0, color='k', lw=0.8)
a.set_title('What over-delivery buys on a RETURN: extra settled angle\n'
            'T64 return episodes ALREADY overshoot p90 3.20 deg (V282 1.06)', fontsize=9.5)
a.set_ylabel('deg past the release point (over / k\' measured)')
a.set_xticks(x); a.set_xticklabels(LB, fontsize=7.5); a.legend(fontsize=8); a.grid(alpha=0.3)

# --- panel 3: highway leak
a = ax[2]
bins = ['8-15', '15-22', '22+']
w = 0.26
for j, bn in enumerate(bins):
    vals = [CEN[r]['bins'][bn]['cand'][c]['dz_rms'] for c in C for r in CEN if bn in CEN[r]['bins']]
    v = [np.mean([CEN[r]['bins'][bn]['cand'][c]['dz_rms'] for r in CEN if bn in CEN[r]['bins']]) for c in C]
    a.bar(x + (j - 1) * w, v, w, label=f'{bn} m/s')
a.set_title('Highway leak: rms |z_cand - z_flown| above the knot\n'
            'C1 leaks by construction; C2/C4/C5 leak via the CARRIED STATE; C6 is clean >=15', fontsize=9.5)
a.set_ylabel('rms dz, unit torque')
a.set_xticks(x); a.set_xticklabels(LB, fontsize=7.5); a.legend(fontsize=8); a.grid(axis='y', alpha=0.3)

fig.suptitle('Raising the low-speed friction-hysteresis term: what breaks  (lowspeed_fric/risk, logged drives, no closed-loop prediction)',
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(f'{OUT}/r_fig_risk.png', dpi=130)
print('wrote', f'{OUT}/r_fig_risk.png')
