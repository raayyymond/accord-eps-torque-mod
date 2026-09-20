"""Stage 6: (i) where in the demand's own arc the release happens (confound check on the
fall-back attribution), (ii) the combined existing-toggle stack on T64 (the flown rev), evaluated on
T64's OWN logged episodes -- structural reach in the COMMAND, not a predicted outcome.
-> out/r6_stack.json  + fig_release.png
"""
import numpy as np, json
import scipy.signal as ss
from rel_lib import *

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route'); aa_abs = col('abs_aa'); dr = col('dem_rate')
TQ = np.isin(g, TQG); V2 = g == 'V282'; T64 = g == 'T64'
ang = W['angdes']; d = np.diff(ang, axis=1, prepend=ang[:, :1])
a_ = 0.01 / (FF_RATE_RC + 0.01); s = np.zeros(N); rate = np.empty_like(ang)
for j in range(ang.shape[1]):
    s = s + a_ * (d[:, j] / 0.01 - s); rate[:, j] = s
S = {k: W[k] * sj[:, None] for k in ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'aa', 'angdes')}
Sr = rate * sj[:, None]
R = {}

# (i) release position in the demand's arc
R['demand_arc'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('V282', V2), ('TORQUE', TQ)):
        m = gm & (v >= lo) & (v < hi)
        pk = np.max(Sr[:, PRE - 100:PRE + 50], 1)
        frac = Sr[:, PRE] / np.where(np.abs(pk) > 1.0, pk, np.nan)
        ok = m & np.isfinite(frac)
        R['demand_arc'][f'{gname}|{lo}-{hi}'] = dict(
            n=int(ok.sum()),
            rate_des_at_bk=round(float(np.median(Sr[ok, PRE])), 3),
            rate_des_peak_in_window=round(float(np.median(pk[ok])), 3),
            release_at_frac_of_peak_rate=round(float(np.median(frac[ok])), 3),
            d_rate_des_300ms=round(float(np.median((Sr[:, PRE + 30] - Sr[:, PRE])[ok])), 3),
            d_rate_des_300ms_over_rate_at_bk=round(float(np.median(((Sr[:, PRE + 30] - Sr[:, PRE]) / np.maximum(Sr[:, PRE], 0.5))[ok])), 3))

# (ii) combined stack on T64's own episodes
R['stack_T64'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    m = T64 & (v >= lo) & (v < hi)
    dcmd = float(np.mean((S['cmd'][:, PRE + 30] - S['cmd'][:, PRE])[m]))
    dmove = float(np.mean((S['move'][:, PRE + 30] - S['move'][:, PRE])[m]))
    ddob = float(np.mean((S['dob'][:, PRE + 30] - S['dob'][:, PRE])[m]))
    drl = float(np.mean((S['rl'][:, PRE + 30] - S['rl'][:, PRE])[m]))
    mv0 = float(np.mean(S['move'][m, PRE]))
    mv_dwell = float(np.mean((S['move'][:, PRE] - S['move'][np.arange(N), np.maximum(np.array([e['w_d0'] for e in EP]), 0)])[m]))
    v282 = V2 & (v >= lo) & (v < hi)
    dcmd_v282 = float(np.mean((S['cmd'][:, PRE + 30] - S['cmd'][:, PRE])[v282]))
    rows = {}
    for nm, delta, extra in (
            ('ARM-D  AccordDobHz 0', -ddob, {}),
            ('+ AccordFFRateGain 0.5->1.0', -ddob + 1.0 * dmove, dict(adds_at_breakaway=round(1.0 * mv0, 5))),
            ('+ AccordFFRateGain 0.5->2.0', -ddob + 3.0 * dmove, dict(adds_at_breakaway=round(3.0 * mv0, 5))),
            ('+ AccordFFRateGain 0.5->2.0 + RateLoopGain 0.0015', -ddob + 3.0 * dmove + 0.5 * drl,
             dict(adds_at_breakaway=round(3.0 * mv0, 5)))):
        rows[nm] = dict(dcmd_300ms_after=round(dcmd + delta, 5), reach=round(-delta, 5),
                        share_of_gap_to_V282=round(-delta / (dcmd - dcmd_v282), 3), **extra)
    rows['_measured'] = dict(dcmd_300ms_T64=round(dcmd, 5), dcmd_300ms_V282=round(dcmd_v282, 5),
                             gap=round(dcmd - dcmd_v282, 5), n_T64=int(m.sum()), n_V282=int(v282.sum()),
                             move_level_at_bk=round(mv0, 5), d_move_300ms=round(dmove, 5),
                             d_dob_300ms=round(ddob, 5), d_rl_300ms=round(drl, 5))
    R['stack_T64'][f'{lo}-{hi}'] = rows
json.dump(R, open(OUT + '/r6_stack.json', 'w'), indent=1, default=float)
print(json.dumps(R, indent=1))

# ---------------- figure ----------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
b5, a5 = ss.butter(2, 5.0 / 50.0)
t = (np.arange(230) - PRE) * 0.01
fig, ax = plt.subplots(2, 2, figsize=(12.5, 8.0))
for c, (lo, hi) in enumerate([(2, 8), (8, 15)]):
    mT = T64 & (v >= lo) & (v < hi); mV = V2 & (v >= lo) & (v < hi)
    A = ax[0, c]
    A.plot(t, np.mean(S['cmd'][mT], 0), 'k-', lw=2.2, label='T64 cmd')
    A.plot(t, np.mean(S['cmd'][mV], 0), 'k--', lw=2.2, label='V282 cmd')
    for k, cl in (('hold_ff', '#1f77b4'), ('move', '#ff7f0e'), ('z', '#2ca02c'), ('rl', '#d62728'), ('dob', '#9467bd'), ('P', '#8c564b')):
        A.plot(t, np.mean(S[k][mT], 0), color=cl, lw=1.4, label=f'T64 {k}')
    A.axvline(0, color='0.4', lw=0.8); A.axvspan(0, 0.065, color='0.85', zorder=0)
    A.set_xlim(-0.6, 0.8); A.set_title(f'{lo}-{hi} m/s  (T64 n={mT.sum()}, V282 n={mV.sum()})')
    A.set_ylabel('torque, sign-aligned'); A.grid(alpha=.3)
    if c == 0:
        A.legend(fontsize=7, ncol=2, loc='upper left')
    B = ax[1, c]
    srT = ss.filtfilt(b5, a5, W['sr'], axis=1) * sj[:, None]
    B.plot(t, np.mean(srT[mT], 0), 'k-', lw=2, label='T64 wheel rate')
    B.plot(t, np.mean(srT[mV], 0), 'k--', lw=2, label='V282 wheel rate')
    B.plot(t, np.mean(Sr[mT], 0), '-', color='#ff7f0e', lw=1.4, label='T64 desired rate')
    B.plot(t, np.mean(Sr[mV], 0), '--', color='#ff7f0e', lw=1.4, label='V282 desired rate')
    B.axvline(0, color='0.4', lw=0.8); B.axvspan(0, 0.065, color='0.85', zorder=0)
    B.set_xlim(-0.6, 0.8); B.set_xlabel('s from breakaway'); B.set_ylabel('deg/s'); B.grid(alpha=.3)
    if c == 0:
        B.legend(fontsize=7)
fig.suptitle('Release: the torque-mode command keeps rising (hold + observer + z); only move and the rate loop retreat.\n'
             'grey band = the 55-75 ms loop delay, already committed at breakaway', fontsize=10)
fig.tight_layout()
fig.savefig(OUT + '/fig_release.png', dpi=110)
print('wrote', OUT + '/fig_release.png')
