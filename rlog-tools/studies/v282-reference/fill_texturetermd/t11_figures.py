"""t11: figures (PNG) from the JSON outputs of t04-t10.  Categorical colours = the dataviz reference palette in fixed order."""
import sys, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
O = ttd.OUT
PAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#52514e']
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e6e5e0',
                     'grid.linewidth': 0.6, 'lines.linewidth': 2})

# ---- F1: work on the wheel (b_eq) vs assumed round-trip delay, per term, 3 strata
T = json.load(open(O + 't04_term_table.json'))
D = [0, 30, 42, 47, 59, 60, 80, 90, 120, 150]
terms = [('rl_fb', 'rate loop (measured part)'), ('dob', 'disturbance observer'), ('p_meas', 'P on measured angle'),
         ('ff', 'feedforward (planner-only terms)'), ('u_e4', 'delivered command (total)')]
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for ax, (sn, title) in zip(axs, [('lt15_large', '<15 m/s, |angle| >= 15 deg'), ('v8_15', '8-15 m/s, all angles'), ('ge15', '>= 15 m/s')]):
    m = T[sn]['ALL']
    ax.axvspan(42, 59, color='#eceae4', zorder=0)
    ax.axhline(0, color='#52514e', lw=0.8)
    for c, (k, lab) in zip(PAL, terms):
        y = [m[k][f'beq_{d}'] * 1e4 for d in D]
        ax.plot(D, y, color=c, label=lab, marker='o', ms=3)
    ax.set_title(f"{title}  ({m['nw']} windows, {m['n_runs']} runs)")
    ax.set_xlabel('assumed command -> wheel round trip (ms)')
axs[0].set_ylabel('equivalent damping b_eq (1e-4 torque per deg/s)\n> 0 damps the 1.5-3.5 Hz wheel rate, < 0 feeds it')
axs[0].text(44, axs[0].get_ylim()[1] * 0.9, 'measured delay\n42-59 ms (t05)', fontsize=8, color='#52514e')
axs[2].legend(loc='lower left', frameon=False, fontsize=8)
fig.suptitle('Which fork term feeds or damps the 2-3 Hz wheel texture (torque mode, 5 routes pooled)', fontsize=11)
fig.tight_layout(); fig.savefig(O + 'fig1_work_vs_delay.png', dpi=130); plt.close(fig)

# ---- F2: share of command band power and coherence with wheel rate, per term, per stratum
names = ['hold', 'move', 'hyst', 'rl_ff', 'p_sp', 'p_meas', 'i', 'rl_fb', 'dob']
strata = [('lt15_small', '<15 m/s small angle'), ('lt15_large', '<15 m/s |angle|>=15'), ('turns_s3', 's3 turns'), ('v8_15', '8-15 m/s'), ('ge15', '>=15 m/s')]
fig, axs = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True)
w = 0.16; x = np.arange(len(names))
for i, (sn, lab) in enumerate(strata):
    m = T[sn]['ALL']
    axs[0].bar(x + (i - 2) * w, [m[n]['share'] for n in names], w * 0.9, color=PAL[i], label=lab)
    axs[1].bar(x + (i - 2) * w, [m[n]['coh'] for n in names], w * 0.9, color=PAL[i])
axs[0].axhline(0, color='#52514e', lw=0.8)
axs[0].set_ylabel('share of command band power\n(projection, sums to 1)')
axs[1].set_ylabel('coherence with wheel rate\n(1.5-3.5 Hz)')
axs[1].set_xticks(x); axs[1].set_xticklabels(['hold\n(FF)', 'move\n(FF)', 'friction hyst\n(FF)', 'rate loop ref\n(FF)', 'P on setpoint\n(FF)',
                                               'P on angle\n(FB)', 'I\n(FB)', 'rate loop meas\n(FB)', 'observer\n(FB)'])
axs[0].legend(ncol=5, frameon=False, fontsize=8, loc='upper left')
fig.suptitle('Fork command in 1.5-3.5 Hz: who carries the band power, and who is locked to the wheel', fontsize=11)
fig.tight_layout(); fig.savefig(O + 'fig2_share_coherence.png', dpi=130); plt.close(fig)

# ---- F3: IV plant FRF
P = json.load(open(O + 't05_iv_plant.json'))
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for c, sn in zip(PAL, ('v3_8', 'lt15_large', 'turns_s3')):
    q = P[sn]; f = np.array(q['f']); om = 2 * np.pi * f
    Hm = 1j * om * np.exp(-1j * om * q['d']) / (q['k'] - q['J'] * om ** 2 + 1j * om * q['b'])
    axs[0].plot(f, q['H_mag'], 'o', color=c, ms=4); axs[0].plot(f, np.abs(Hm), color=c, label=f"{sn}: d {q['d']*1000:.0f} ms, J {q['J']:.1e}, b {q['b']:.1e}")
    axs[1].plot(f, q['H_ph'], 'o', color=c, ms=4); axs[1].plot(f, np.degrees(np.angle(Hm)), color=c)
axs[0].set_ylabel('|rate / torque| (deg/s per unit command)'); axs[1].set_ylabel('phase (deg)')
for ax in axs:
    ax.set_xlabel('Hz'); ax.axvspan(1.5, 3.5, color='#eceae4', zorder=0)
axs[0].legend(frameon=False, fontsize=7)
fig.suptitle('Torque -> wheel-rate plant, identified with the feedforward as instrument (dots) and fitted (lines)', fontsize=11)
fig.tight_layout(); fig.savefig(O + 'fig3_iv_plant.png', dpi=130); plt.close(fig)

# ---- F4: replay correlation vs delay
Rb = json.load(open(O + 't06b_linear_replay.json'))
fig, axs = plt.subplots(1, 4, figsize=(14, 3.8), sharey=True)
for ax, sn in zip(axs, ('lt15_large', 'lt15_small', 'v8_15', 'ge15')):
    q = Rb[sn]['ALL']; d = np.arange(21) * 10
    ax.axvspan(42, 59, color='#eceae4', zorder=0); ax.axhline(0, color='#52514e', lw=0.8)
    for c, (k, lab) in zip(PAL, (('J1e-4_b1.2e-3|u_e4', 'delivered command'), ('J1e-4_b1.2e-3|ff', 'feedforward only'), ('J1e-4_b1.2e-3|fb', 'feedback only'))):
        ax.plot(d, q[k]['corr'], color=c, label=lab)
    ax.set_title(f"{sn} ({q['sec']:.0f} s)"); ax.set_xlabel('replay delay (ms)')
axs[0].set_ylabel('corr(replayed, measured) 1.5-3.5 Hz wheel rate'); axs[0].legend(frameon=False, fontsize=8)
fig.suptitle('Open-loop replay of the logged command through the identified plant', fontsize=11)
fig.tight_layout(); fig.savefig(O + 'fig4_replay_vs_delay.png', dpi=130); plt.close(fig)

# ---- F5: mode frequency spectra
try:
    M = json.load(open(O + 't08_mode_freq_zeta.json'))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for c, (bn, q) in zip(PAL, M['data'].items()):
        f = np.array(q['f']); Pp = np.array(q['P']); s = (f > 0.8) & (f < 6)
        ax.semilogy(f[s], Pp[s] * f[s], color=c, lw=1.5, label=f"{bn} m/s: raw peak {q['raw_peak']:.2f} Hz [{q['raw_ci'][0]:.2f}, {q['raw_ci'][1]:.2f}]")
    ax.axvspan(1.5, 3.5, color='#eceae4', zorder=0)
    ax.set_xlabel('Hz (resolution 0.098 Hz)'); ax.set_ylabel('f x PSD of wheel rate')
    ax.legend(frameon=False, fontsize=8)
    ax.set_title('Wheel-rate spectrum per speed bin, torque-mode routes pooled')
    fig.tight_layout(); fig.savefig(O + 'fig5_mode_spectra.png', dpi=130); plt.close(fig)
except FileNotFoundError:
    pass

# ---- F6: natural experiment
try:
    N = json.load(open(O + 't10_natural_expt.json'))
    fig, axs = plt.subplots(1, 2, figsize=(12, 4))
    for ax, vs in zip(axs, ('lt15', 'ge15')):
        cons = list(N[vs].keys()); keys = [('r', 'wheel rate'), ('setpoint', 'setpoint'), ('ff', 'FF torque'), ('fb', 'FB torque')]
        x = np.arange(len(cons)); w = 0.2
        for i, (k, lab) in enumerate(keys):
            vals = [N[vs][c][k]['ratio'] or np.nan for c in cons]
            lo = [N[vs][c][k]['ci'][0] if N[vs][c][k]['ci'] else np.nan for c in cons]
            hi = [N[vs][c][k]['ci'][1] if N[vs][c][k]['ci'] else np.nan for c in cons]
            ax.bar(x + (i - 1.5) * w, vals, w * 0.9, color=PAL[i], label=lab,
                   yerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)], ecolor='#52514e', capsize=2)
        ax.axhline(1, color='#52514e', lw=0.8); ax.set_xticks(x); ax.set_xticklabels(cons)
        ax.set_title(f'{vs}: band (1.5-3.5 Hz) rms ratio at matched cells'); ax.set_yscale('log')
    axs[0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(O + 'fig6_natural_experiment.png', dpi=130); plt.close(fig)
except FileNotFoundError:
    pass

# ---- F7: linearised closed-loop modes
try:
    L = json.load(open(O + 't07_linear_loop.json'))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for c, lab in zip(PAL, ('flown', 'no_dob', 'no_rl', 'no_p', 'rl0006', 'open')):
        vs, fr, zz = [], [], []
        for v, row in L['IV_bhi'].items():
            ms = [m for m in row[lab] if 1.5 <= m[0] <= 4.5]
            if ms:
                vs.append(float(v)); fr.append(ms[0][0]); zz.append(ms[0][1])
        axs[0].plot(vs, fr, marker='o', color=c, label=lab); axs[1].plot(vs, zz, marker='o', color=c)
    axs[0].set_ylabel('least-damped mode in 1.5-4.5 Hz (Hz)'); axs[1].set_ylabel('damping ratio'); axs[1].axhline(0, color='#52514e', lw=0.8)
    for ax in axs:
        ax.set_xlabel('speed (m/s)')
    axs[0].legend(frameon=False, fontsize=8)
    fig.suptitle('MODEL (belief): linearised fork feedback on the IV plant, per-term ablation', fontsize=11)
    fig.tight_layout(); fig.savefig(O + 'fig7_linear_loop_modes.png', dpi=130); plt.close(fig)
except FileNotFoundError:
    pass
print('figures written')
