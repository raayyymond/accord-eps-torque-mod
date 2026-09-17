"""s5_10: summary figure from the s5 JSON results."""
import json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
O = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
F = json.load(open(O + 's5_01_actuator_frf.json')); E = json.load(open(O + 's5_08_event_rate_spectrum.json'))
M = json.load(open(O + 's5_07_matched.json'))
fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
for g, st, c in (('V282', '15-22', 'C0'), ('V282', '8-15', 'C2')):
    b = F[g][st]['bins']; f = [x['f'] for x in b]
    ax[0].plot(f, [x['rate_ph'] for x in b], 'o-', color=c, label=f'V282 {st}: phase(rate/cmd)')
for g, st, c in (('T64', '3-8', 'C1'),):
    b = F[g][st]['bins']; f = [x['f'] for x in b]
    ax[0].plot(f, [x['rate_ph'] for x in b], 's-', color=c, label=f'T64 {st}: phase(rate/cmd)')
ax[0].plot([0, 5], [0, -360 * 5 * 0.06], 'k:', label='pure 60 ms delay')
ax[0].set_xlabel('Hz'); ax[0].set_ylabel('deg'); ax[0].set_title('Effective actuator phase (IV FRF, r = model demand)'); ax[0].legend(fontsize=7)
bands = ['1.5-3.5', '3.5-6', '6-10']; x = np.arange(3); w = 0.16
for i, g in enumerate(['V282', 'T64', 'T64B', 'T5', 'T4']):
    k = f'{g}|(8, 15)'
    ax[1].bar(x + (i - 2) * w, [E[k]['rate_rms_by_band'][b] for b in bands], w, label=f"{g} n={E[k]['n']}")
ax[1].set_xticks(x); ax[1].set_xticklabels([b + ' Hz' for b in bands]); ax[1].set_ylabel('steering-rate RMS, deg/s')
ax[1].set_title('High-jerk events 8-15 m/s: wheel-rate texture'); ax[1].legend(fontsize=7)
groups = ['T64', 'T64B', 'T5', 'T4']
for j, (met, lab) in enumerate((('ang_lag', 'angle lag s'),)):
    for i, vb in enumerate(['8-15', '15-99']):
        t = [M[f'{g}|v{vb}'][met]['torque'] for g in groups]; r = [M[f'{g}|v{vb}'][met]['v282'] for g in groups]
        xx = np.arange(4) + i * 5
        ax[2].bar(xx - 0.2, r, 0.4, color='C0', label='matched V282' if i == 0 else None)
        ax[2].bar(xx + 0.2, t, 0.4, color='C3', label='torque mode' if i == 0 else None)
    ax[2].set_xticks(list(np.arange(4)) + list(np.arange(4) + 5)); ax[2].set_xticklabels([g + '\n8-15' for g in groups] + [g + '\n>=15' for g in groups], fontsize=7)
ax[2].set_ylabel('desired angle -> wheel angle lag, s'); ax[2].set_title('Matched events: lag (speed + demand-rate matched)'); ax[2].legend(fontsize=7)
plt.tight_layout(); plt.savefig(O + 's5_summary.png', dpi=110)
print('ok')
