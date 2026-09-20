"""b07: ranked feeders for merged bins (<3, 3-8, <8, 8-15) at tau 30 ms (+0/60 sensitivity), block bootstrap CIs,
per-route values; share of band-rate energy per bin; figure."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import bs
rows = json.load(open(bs.OUT + 'b02_rows.json'))
TERMS = ['u_e4', 'u_log', 'p_log', 'i_log', 'f_log', 'dob_log', 'move', 'rl_ff', 'p_sp', 'hold', 'hyst', 'p_meas', 'rl_fb', 'ffwd', 'fbk', 'ctrl']
MB = {'<3': ['<3'], '3-6': ['3-6'], '6-8': ['6-8'], '3-8': ['3-6', '6-8'], '<8': ['<3', '3-6', '6-8'], '8-15': ['8-15']}
GR = {'rev64': ('T64', 'T64B'), 'obs-on': ('T64', 'T64B', 'T5'), 'T4': ('T4',)}
rng = np.random.default_rng(1)


def est(sub):
    rr = sum(r['rr'] for r in sub)
    return {k: [-sum(r[k][i] for r in sub) / rr for i in range(3)] for k in TERMS}


RES = {}; L = []
for gn, gs in GR.items():
    allE = sum(r['rr'] for r in rows if r['g'] in gs and r['bin'] in MB['<8'])
    for mb, bins in MB.items():
        sub = [r for r in rows if r['g'] in gs and r['bin'] in bins]
        E = est(sub); B = [est([sub[i] for i in rng.integers(0, len(sub), len(sub))]) for _ in range(1000)]
        ci = {k: [float(np.percentile([b[k][1] for b in B], q)) for q in (2.5, 97.5)] for k in TERMS}
        pr = {}
        for rk in sorted(set(r['route'] for r in sub)):
            s2 = [r for r in sub if r['route'] == rk]
            if sum(r['secs'] for r in s2) >= 15:
                pr[rk[:8]] = {k: v[1] for k, v in est(s2).items()}
        eshare = sum(r['rr'] for r in sub) / allE if mb != '8-15' else None
        secs = sum(r['secs'] for r in sub)
        RES[f'{gn}|{mb}'] = dict(est=E, ci30=ci, per_route30=pr, energy_share_of_lt8=eshare, secs=secs)
        L.append(f"\n== {gn} {mb}: {secs:.0f} s, share of <8 m/s band-rate energy {eshare if eshare is None else round(eshare, 3)}")
        rank = sorted([k for k in TERMS if k not in ('u_e4', 'u_log', 'ffwd', 'fbk', 'ctrl', 'f_log', 'p_log')], key=lambda k: E[k][1])
        for k in ['ctrl', 'u_e4', 'u_log', 'ffwd', 'fbk', 'p_log', 'i_log', 'f_log'] + rank:
            if k == 'i_log' and k in rank:
                pass
            L.append(f"   {k:8s} @0 {E[k][0]*1e4:+6.2f}  @30 {E[k][1]*1e4:+6.2f} [{ci[k][0]*1e4:+6.2f},{ci[k][1]*1e4:+6.2f}]  @60 {E[k][2]*1e4:+6.2f}  routes " +
                     ' '.join(f"{v[k]*1e4:+.2f}" for v in pr.values()))
open(bs.OUT + 'b07_rank.txt', 'w').write('b_eq x1e-4 output per deg/s; >0 damps <0 feeds; tau 30 ms primary\n' + '\n'.join(L))
json.dump(RES, open(bs.OUT + 'b07_rank.json', 'w'), indent=1)
print('\n'.join(L))

# figure
S5 = json.load(open(bs.OUT + 'b05_summary.json'))
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
terms = ['move', 'rl_ff', 'p_sp', 'hold', 'hyst', 'dob_log', 'i_log', 'p_meas', 'rl_fb', 'u_e4']
lab = ['move\n(plan)', 'rate-loop\nref (plan)', 'P on\nsetpoint', 'hold\n(plan)', 'friction\nhyst', 'observer\n(logged)', 'I', 'P on\nmeas', 'rate-loop\nmeas', 'whole cmd\n(0xE4)']
cols = {'<3': '#9ecae1', '3-8': '#3182bd', '8-15': '#e6550d'}
w = 0.27
for i, mb in enumerate(['<3', '3-8', '8-15']):
    r = RES[f'rev64|{mb}']
    y = np.array([r['est'][k][1] for k in terms]) * 1e4
    lo = y - np.array([r['ci30'][k][0] for k in terms]) * 1e4; hi = np.array([r['ci30'][k][1] for k in terms]) * 1e4 - y
    ax[0].bar(np.arange(len(terms)) + (i - 1) * w, y, w, yerr=[lo, hi], color=cols[mb], label=f'{mb} m/s', capsize=2)
ax[0].axhline(0, color='k', lw=0.8)
ax[0].set_xticks(np.arange(len(terms))); ax[0].set_xticklabels(lab, fontsize=7)
ax[0].set_ylabel('b_eq @ 30 ms  (x1e-4 output per deg/s)\n>0 damps the wheel, <0 feeds it')
ax[0].set_title('rev 6.4 (6c, 6d, 6e): which term feeds the 1.5-3.5 Hz wheel rate')
ax[0].legend(fontsize=8)
bins = ['<3', '3-6', '6-8', '8-15']
x = np.arange(len(bins))
for j, (g, c) in enumerate((('rev64', '#3182bd'), ('V282', '#31a354'))):
    coh = [S5[f'{g}|{b}']['coh_rate'] for b in bins]; inc = [S5[f'{g}|{b}']['incoh_rate'] for b in bins]
    ax[1].bar(x + (j - 0.5) * 0.38, coh, 0.38, color=c, label=f'{g}: coherent with planner')
    ax[1].bar(x + (j - 0.5) * 0.38, inc, 0.38, bottom=coh, color=c, alpha=0.4, hatch='//', label=f'{g}: not coherent')
    for xi, b in enumerate(bins):
        ax[1].text(xi + (j - 0.5) * 0.38, coh[xi] + inc[xi] + 0.2, f"|H| {S5[f'{g}|{b}']['H']:.2f}", ha='center', fontsize=7)
ax[1].set_xticks(x); ax[1].set_xticklabels([f'{b} m/s' for b in bins])
ax[1].set_ylabel('1.5-3.5 Hz steering rate, deg/s (stacked: coh + incoh, not additive in power)')
ax[1].set_title('Shake split: planner-driven vs not; |H| = wheel rate / desired angle rate')
ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(bs.OUT + 'b07_shake_feeders.png', dpi=130)
print('fig saved')
