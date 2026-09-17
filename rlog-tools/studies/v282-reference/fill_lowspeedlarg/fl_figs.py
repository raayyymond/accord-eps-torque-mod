"""Figures: census heatmap (hands-off seconds per group x demand cell x speed) and the frame-level 1.8-3 Hz texture."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_lowspeedlarg'
C = json.load(open(f'{HERE}/out/census.json'))
FT = json.load(open(f'{HERE}/out/frame_texture.json'))
GROUPS = ['V282', 'V282old', 'V282pool', 'T64', 'T64B', 'T5', 'T4']
CELLS = ['A15', 'A45', 'A90', 'R10', 'R40']
CL = ['|angle|>=15', '>=45', '>=90', 'rate 10-40', 'rate >40']
VBN = ['2.5-5', '5-8', '8-15']
INK = '#0b0b0b'; INK2 = '#52514e'

fig, axes = plt.subplots(2, 4, figsize=(22, 10), facecolor='#fcfcfb')
norm = LogNorm(1, 1000)
for ax, g in zip(axes.flat, GROUPS):
    M = np.array([[max(C[g][f'{c}_{v}']['ho_s'], 0.5) for c in CELLS] for v in VBN])
    ax.imshow(M, cmap='Blues', norm=norm, aspect='auto', origin='lower')
    for i, v in enumerate(VBN):
        for j, c in enumerate(CELLS):
            d = C[g][f'{c}_{v}']
            dark = d['ho_s'] > 60
            txt = f"{d['ho_s']:.0f} s\n{d['n_routes']} rt  {d['events_ho']} ev\nhands-off {d['hands_off_frac']:.0%}"
            if g.startswith('V282') and not d['reference_ok']:
                txt += '\n(not a ref)'
            ax.text(j, i, txt, ha='center', va='center', fontsize=7.5, color='white' if dark else INK)
            if g.startswith('V282') and d['reference_ok']:
                ax.add_patch(plt.Rectangle((j - 0.47, i - 0.47), 0.94, 0.94, fill=False, edgecolor=INK, lw=2.0))
    ax.set_xticks(range(5)); ax.set_xticklabels(CL, fontsize=8, color=INK2)
    ax.set_yticks(range(3)); ax.set_yticklabels([f'{v} m/s' for v in VBN], fontsize=9, color=INK2)
    ax.set_title(g + ('  (reference)' if g.startswith('V282') else '  (torque mode)'), fontsize=11, color=INK, loc='left')
    for s in ax.spines.values():
        s.set_visible(False)
ax = axes.flat[-1]; ax.axis('off')
ax.text(0, 0.9, 'Hands-off census below 15 m/s', fontsize=13, color=INK, weight='bold', transform=ax.transAxes)
ax.text(0, 0.05, 'Cells are DEMAND-defined (model curvature as wheel angle,\nfixed sR 16.33; demanded steer rate).\n'
        'Hands-off = engaged, steeringPressed dilated +/-0.5 s removed.\n'
        'rt = routes with >= 2 s;  ev = turn events (angle cells) or\nrate-transient events (rate cells) with >= 70 % hands-off.\n'
        'hands-off % = hands-off s / unpressed engaged s.\n'
        'Reference panels: outlined = usable reference (>= 30 s, >= 2 routes);\n'
        'otherwise labelled NOT A REFERENCE.', fontsize=9.5, color=INK2, transform=ax.transAxes, va='bottom')
fig.tight_layout()
fig.savefig(f'{HERE}/out/census_heatmap.png', dpi=110, facecolor=fig.get_facecolor())

# texture figure
SER = [('V282', '#2a78d6'), ('V282old', '#4a3aa7'), ('T64', '#eb6834'), ('T64B', '#e87ba4'), ('T5', '#eda100'), ('T4', '#1baf7a')]
TC = ['A0', 'A15', 'A45', 'A90', 'R10', 'R40']
TL = ['quiet\n|ang|<15', '|ang|\n>=15', '>=45', '>=90', 'rate\n10-40', 'rate\n>40']
fig, axes = plt.subplots(1, 3, figsize=(18, 5.8), sharey=True, facecolor='#fcfcfb')
for ax, v in zip(axes, VBN):
    for k, (g, col) in enumerate(SER):
        xs, ys = [], []
        for j, c in enumerate(TC):
            d = FT[f'{c}_{v}']['groups'][g]
            if 'mode_rms' in d and d['sec'] >= 5:
                xs.append(j + (k - 2.5) * 0.12); ys.append(d['mode_rms'])
        ax.plot(xs, ys, 'o', ms=8, color=col, label=g, mec='#fcfcfb', mew=1.5)
    ax.set_yscale('log'); ax.set_xticks(range(len(TC))); ax.set_xticklabels(TL, fontsize=9, color=INK2)
    ax.set_title(f'{v} m/s', loc='left', color=INK, fontsize=11)
    ax.grid(axis='y', color='#e4e3df', lw=0.8); ax.set_axisbelow(True)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
axes[0].set_ylabel('rms steer rate 1.8-3 Hz, deg/s (hands-off frames)', color=INK2)
axes[0].legend(frameon=False, fontsize=9, ncol=2)
fig.suptitle('The 1.8-3 Hz wheel texture below 15 m/s: V282 and V282old agree; every torque rev sits 4-15x above them (cells with >= 5 s shown)',
             color=INK, fontsize=12, x=0.01, ha='left')
fig.tight_layout()
fig.savefig(f'{HERE}/out/texture_1p8_3hz.png', dpi=110, facecolor=fig.get_facecolor())
print('ok')
