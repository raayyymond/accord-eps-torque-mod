"""s2_jerk stage 3: ensemble traces over MATCHED pairs, representative pairs, windowed bias bars, event steering-rate PSD,
and the command-vs-plant lag split (model->out, out->la_act) from the stored event traces.  -> PNG + _out/s2_split.json"""
import json, numpy as np, warnings
warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import signal
from s2_common import *
FIG = OUT.replace('/_out', '')
rows, tr = load_all()
for r in rows:
    if 'act.settle' in r and not np.isfinite(r['act.settle']):
        r['act.settle'] = 2.5
REF = [r for r in rows if r['group'] == 'V282']
t = (np.arange(tr['model'].shape[1]) - 100) / 100.0
C = {'V282': '#2a6fdb', 'T64': '#d9480f', 'T64B': '#e8a33d', 'T5': '#7a5195', 'T4': '#2f9e44'}


def lp(x, fc=3.0):
    return signal.sosfiltfilt(signal.butter(2, fc, fs=100, output='sos'), x, axis=-1)


def D(r):
    return max(abs(r['a1'] - r['a0']), 1e-3)


def lag_in_trace(x, y, lo=-60, hi=80):
    """lag of y behind x within a stored 350-sample event trace (fixed y segment [80,270], x shifted)."""
    yy = y[80:270] - y[80:270].mean(); best = (-2, 0)
    for L in range(lo, hi + 1):
        a, b = 80 - L, 270 - L
        if a < 0 or b > len(x):
            continue
        xx = x[a:b] - x[a:b].mean(); den = np.sqrt(np.dot(xx, xx) * np.dot(yy, yy))
        c = np.dot(xx, yy) / den if den > 0 else 0
        if c > best[0]:
            best = (c, L)
    return best[1] / 100.0, best[0]


pairs = match(REF, [r for r in rows if r['group'] == 'T64'])
strata = {'8-15 m/s': [1], '>=15 m/s': [2, 3]}

# ---------- fig 1 matched ensembles
fig, ax = plt.subplots(5, 2, figsize=(12, 15), sharex=True)
ens = {}
for j, (sn, vbs) in enumerate(strata.items()):
    P = [p for p in pairs if p[1]['vb'] in vbs and D(p[1]) >= 0.2]
    for side, g in ((0, 'V282'), (1, 'T64')):
        U = [p[side]['uid'] for p in P]; dd = np.array([D(p[side]) for p in P])[:, None]
        m = tr['model'][U] / dd; a = lp(tr['la_act'][U]) / dd; po = lp(tr['la_pose'][U]) / dd
        ax[0, j].plot(t, m.mean(0), color=C[g], ls=':', lw=1.5, label=f'{g} model demand')
        ax[0, j].plot(t, a.mean(0), color=C[g], lw=2, label=f'{g} achieved (la_act = angle)')
        ax[0, j].plot(t, po.mean(0), color=C[g], lw=1, ls='--', label=f'{g} achieved (livePose yaw x v)')
        ax[1, j].plot(t, (a - m).mean(0), color=C[g], lw=2, label=g)
        ax[1, j].fill_between(t, np.percentile(a - m, 25, 0), np.percentile(a - m, 75, 0), color=C[g], alpha=.15)
        ax[2, j].plot(t, (tr['sa'][U] / dd).mean(0), color=C[g], lw=2, label=g)
        ax[3, j].plot(t, (tr['sr'][U] / dd).mean(0), color=C[g], lw=2, label=f'{g} mean')
        ax[3, j].plot(t, np.sqrt(((tr['sr'][U] - lp(tr['sr'][U], 1.0)) ** 2).mean(0)) / np.median(dd), color=C[g], lw=.8, ls='--',
                      label=f'{g} rms of >1 Hz part')
        o = lp(tr['out'][U]) / dd; o = o / max(np.abs(o.mean(0)[250:]).max(), 1e-6)
        ax[4, j].plot(t, o.mean(0), color=C[g], lw=2, label=f'{g} command (out, / own late level)')
        ens[f'{g}|{sn}'] = dict(n=len(U), t=t[::10].tolist(), model=m.mean(0)[::10].tolist(), act=a.mean(0)[::10].tolist(),
                                pose=po.mean(0)[::10].tolist(), err=(a - m).mean(0)[::10].tolist())
    ax[0, j].set_title(f'{sn}: matched pairs n={len(P)} (sign-normalised, / demanded step)')
    ax[0, j].set_ylabel('lat accel / step'); ax[1, j].set_ylabel('achieved - demand (/step)\nmean + IQR')
    ax[2, j].set_ylabel('steer angle deg / (m/s2 step)'); ax[3, j].set_ylabel('steer rate deg/s / step')
    ax[4, j].set_ylabel('command, normalised'); ax[4, j].set_xlabel('s from desired-jerk peak')
    for a_ in ax[:, j]:
        a_.axvline(0, color='k', lw=.5); a_.grid(alpha=.3)
    ax[1, j].axhline(0, color='k', lw=.5)
ax[0, 0].legend(fontsize=7); ax[3, 0].legend(fontsize=7); ax[4, 0].legend(fontsize=7)
fig.suptitle('High desired-jerk events: V282 (rate-servo EPS) vs rev 6.4 torque mode, matched type x speed bin x jerk x step')
fig.tight_layout(); fig.savefig(f'{FIG}/s2_fig1_matched_ensembles.png', dpi=110); plt.close(fig)

# ---------- fig 2 windowed error, every group (unmatched, stratified) with route x event bootstrap
wins = [('0_20', '0-0.2'), ('20_60', '0.2-0.6'), ('60_150', '0.6-1.5'), ('150_300', '1.5-2.5')]
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
summary = {}
for j, (sn, vbs) in enumerate(strata.items()):
    x0 = np.arange(len(wins)); w = 0.16
    for q, g in enumerate(['V282', 'T64', 'T64B', 'T5', 'T4']):
        R = [r for r in rows if r['group'] == g and r['vb'] in vbs]
        meds, lo_, hi_, cis = [], [], [], []
        for k, _ in wins:
            b = boot_group(R, f'act.bias_{k}')
            meds.append(b['med']); lo_.append(b['med'] - b['ci'][0]); hi_.append(b['ci'][1] - b['med']); cis.append(b['ci'])
        summary[f'{g}|{sn}'] = dict(n=len(R), bias=meds, ci=cis)
        ax[j].bar(x0 + (q - 2) * w, meds, w, yerr=[lo_, hi_], color=C[g], label=f'{g} (n={len(R)})', capsize=2)
    ax[j].set_xticks(x0); ax[j].set_xticklabels([f'{l} s' for _, l in wins]); ax[j].axhline(0, color='k', lw=.6)
    ax[j].set_title(f'{sn}: median (achieved - demand)/step after the jerk peak\nCI = route-cluster x event bootstrap', fontsize=10)
    ax[j].grid(alpha=.3, axis='y')
ax[0].set_ylabel('(la_act - model) / step'); ax[0].legend(fontsize=8)
fig.tight_layout(); fig.savefig(f'{FIG}/s2_fig2_error_by_window.png', dpi=110); plt.close(fig)

# ---------- fig 3 representative matched pairs
picks = []
for vbs, typ in (([2, 3], 'onset'), ([2, 3], 'release'), ([1], 'onset'), ([1], 'release')):
    cand = [p for p in pairs if p[1]['vb'] in vbs and p[1]['type'] == typ and D(p[1]) >= 0.2]
    if not cand:
        continue
    med = np.median([p[1]['act.slag'] for p in cand]); medg = np.median([p[1]['act.sgain'] for p in cand])
    picks.append(min(cand, key=lambda p: abs(p[1]['act.slag'] - med) / .1 + abs(p[1]['act.sgain'] - medg) / .2
                     + abs(np.log(p[0]['jerk'] / p[1]['jerk']))))
fig, ax = plt.subplots(3, len(picks), figsize=(4.2 * len(picks), 9), sharex=True)
for c, (r0, r1) in enumerate(picks):
    for r, g in ((r0, 'V282'), (r1, 'T64')):
        u = r['uid']
        ax[0, c].plot(t, tr['model'][u], color=C[g], ls=':', lw=1.5)
        ax[0, c].plot(t, tr['la_act'][u], color=C[g], lw=1.8,
                      label=f"{g} {r['route']} idx {r['k']} v={r['v']:.1f} lag {r['act.slag']:.2f} gain {r['act.sgain']:.2f}")
        ax[1, c].plot(t, tr['sa'][u], color=C[g], lw=1.8); ax[2, c].plot(t, tr['sr'][u], color=C[g], lw=1.2)
    ax[0, c].set_title(f"{r1['type']}  T64 v={r1['v']:.0f} jerk {r1['jerk']:.2f} step {r1['step']:.2f}\n"
                       f"V282 v={r0['v']:.0f} jerk {r0['jerk']:.2f} step {r0['step']:.2f}", fontsize=9)
    ax[0, c].legend(fontsize=5)
    for a_ in ax[:, c]:
        a_.grid(alpha=.3); a_.axvline(0, color='k', lw=.5)
ax[0, 0].set_ylabel('lat accel m/s2 rel. (dotted = model)'); ax[1, 0].set_ylabel('steer angle deg rel.'); ax[2, 0].set_ylabel('steer rate deg/s')
fig.suptitle('Representative matched pairs (torque event nearest its stratum median lag and gain), sign-normalised')
fig.tight_layout(); fig.savefig(f'{FIG}/s2_fig3_representative_pairs.png', dpi=110); plt.close(fig)
reps = [dict(ref=(p[0]['route'], p[0]['k'], p[0]['t']), tq=(p[1]['route'], p[1]['k'], p[1]['t']), type=p[1]['type'],
             v=(p[0]['v'], p[1]['v'])) for p in picks]

# ---------- fig 4 steering-rate PSD in the event + lag split
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
split = {}
for j, (sn, vbs) in enumerate(strata.items()):
    for g in ['V282', 'T64', 'T64B', 'T5', 'T4']:
        R = [r for r in rows if r['group'] == g and r['vb'] in vbs and D(r) >= 0.2]
        U = [r['uid'] for r in R]
        if len(U) < 3:
            continue
        x = tr['sr'][U, 100:]; x = signal.detrend(x, axis=-1)
        f, p = signal.welch(x, fs=100, nperseg=128, axis=-1)
        pm = p.mean(0); ax[j].semilogy(f, pm, color=C[g], label=f'{g} n={len(U)}')
        band = (f >= 1.2) & (f <= 4.0); fpk = float(f[band][np.argmax(pm[band])])
        l_cmd = [lag_in_trace(tr['model'][u], lp(tr['out'][u])) for u in U]
        l_pl = [lag_in_trace(lp(tr['out'][u]), lp(tr['la_act'][u])) for u in U]
        l_tot = [lag_in_trace(tr['model'][u], lp(tr['la_act'][u])) for u in U]
        l_sp = [lag_in_trace(tr['model'][u], lp(tr['setpoint'][u])) for u in U]
        med = lambda L: float(np.median([a for a, c in L if c > .5])) if any(c > .5 for _, c in L) else float('nan')
        split[f'{g}|{sn}'] = dict(n=len(U), psd_peak_1p2_4Hz=fpk, psd_1p5_3p5=float(pm[(f >= 1.5) & (f <= 3.5)].sum() * (f[1] - f[0])),
                                  lag_model_to_setpoint=med(l_sp), lag_model_to_cmd=med(l_cmd), lag_cmd_to_angle=med(l_pl),
                                  lag_model_to_angle=med(l_tot), n_cmd=int(sum(c > .5 for _, c in l_cmd)), n_pl=int(sum(c > .5 for _, c in l_pl)))
    ax[j].set_xlim(0, 10); ax[j].set_title(f'{sn}: steering-rate PSD, 0 to +2.5 s after jerk peak'); ax[j].set_xlabel('Hz')
    ax[j].grid(alpha=.3); ax[j].legend(fontsize=8)
ax[0].set_ylabel('(deg/s)^2/Hz'); fig.tight_layout(); fig.savefig(f'{FIG}/s2_fig4_event_steer_rate_psd.png', dpi=110); plt.close(fig)
json.dump(dict(split=split, window_bias=summary, reps=reps, ensembles=ens), open(f'{OUT}/s2_split.json', 'w'), indent=1, default=float)
for k, v in split.items():
    print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
for k, v in summary.items():
    print(k, v['n'], [round(x, 3) for x in v['bias']])
print(reps)
