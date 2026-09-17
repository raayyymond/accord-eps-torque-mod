"""ADVERSARIAL VERIFICATION of s2_jerk finding 'texture-not-event-triggered-ring'.
Lens: ALTMETHOD (false-negative hunt). Does not touch the original s2_jerk scripts or OUT dir;
re-uses the already-extracted event traces (events_*.npz) so no route reload is needed.

Original method: 4th-order Butterworth 1.5-3.5 Hz band, filtfilt with 1 s padding, RMS over TWO
FIXED windows: pre [-1.0,0] s and post [0,+2.5] s. Ratio-of-medians, matched pairs, bootstrap.

Alt methods tried here, each genuinely different from the original:
 (A) FINE TIME RESOLUTION: 0.25 s sliding-bin envelope (Hilbert, not RMS-of-bandpass) across the
     whole -1.0..+2.5 s window, instead of 2 coarse windows -- catches a burst the coarse post
     window would dilute against its own tail.
 (B) TAIL-FOCUSED: narrow immediate-post [0,0.5] s vs narrow tail [1.5,2.5] s vs narrow pre
     [-0.5,0] s (not the original's full pre[-1,0]/post[0,2.5]).
 (C) NONLINEAR: reversal rate (sign changes of d(sr)/dt) per second in the SAME windows -- an
     amplitude-independent texture definition, not RMS.
 (D) qualitative: representative single-event raw+bandpassed traces, largest-jerk in each group.

All CIs: paired (matched-pair) event+route-cluster bootstrap, same recipe as s2_common.boot_diff.
"""
import sys, json, os
import numpy as np
from scipy import signal
import warnings
warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, match, vbin, boot_diff  # noqa

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__texturenotev__altmethod'
os.makedirs(OUT, exist_ok=True)

rows, tr = load_all()
REF = [r for r in rows if r['group'] == 'V282']
TQ = [r for r in rows if r['group'] == 'T64']
pairs = match(REF, TQ)
print(f'matched pairs total: {len(pairs)}')

FS = 100.0
t = (np.arange(tr['sr'].shape[1]) - 100) / FS  # -1.0 .. +2.49
SOS = signal.butter(4, [1.5, 3.5], btype='band', fs=FS, output='sos')

strata = {'8-15 m/s': [1], '>=15 m/s': [2, 3]}

# ---------------- (A) fine time-resolution envelope, all matched pairs, no D>=.2 filter (keep n same as finding) ----------------
BIN = 25  # 0.25 s
nb = tr['sr'].shape[1] // BIN
bin_t = (np.arange(nb) * BIN + BIN / 2 - 100) / FS


def envelope_bins(sr_trace):
    """Reflect-pad (different edge handling than the original's fixed 100-sample route padding, since we
    only have the stored 350-sample window here), bandpass, Hilbert envelope, bin-mean."""
    x = np.asarray(sr_trace, float)
    xp = np.pad(x, 200, mode='reflect')
    bp = signal.sosfiltfilt(SOS, xp)[200:-200]
    env = np.abs(signal.hilbert(bp))
    return env[:nb * BIN].reshape(nb, BIN).mean(1)


def reversal_rate_bins(sr_trace):
    """sign changes of d(sr)/dt per second, per 0.25s bin -- amplitude-independent nonlinear texture stat."""
    x = np.asarray(sr_trace, float)
    d = np.diff(x)
    sgn = np.sign(d)
    sgn[sgn == 0] = 1
    rev = np.zeros(len(x)); rev[1:-1] = (sgn[1:] != sgn[:-1]).astype(float)
    return rev[:nb * BIN].reshape(nb, BIN).sum(1) * (FS / BIN)  # events/s in this bin


env_cache = {}
rev_cache = {}
for r in rows:
    u = r['uid']
    env_cache[u] = envelope_bins(tr['sr'][u])
    rev_cache[u] = reversal_rate_bins(tr['sr'][u])

fig, ax = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
C = {'V282': '#2a6fdb', 'T64': '#d9480f'}
summary_bins = {}
for j, (sn, vbs) in enumerate(strata.items()):
    P = [p for p in pairs if p[1]['vb'] in vbs]
    for g, side in (('V282', 0), ('T64', 1)):
        U = [p[side]['uid'] for p in P]
        E = np.array([env_cache[u] for u in U])
        Rv = np.array([rev_cache[u] for u in U])
        med_e = np.median(E, 0); lo_e = np.percentile(E, 25, 0); hi_e = np.percentile(E, 75, 0)
        med_r = np.median(Rv, 0); lo_r = np.percentile(Rv, 25, 0); hi_r = np.percentile(Rv, 75, 0)
        ax[0, j].plot(bin_t, med_e, color=C[g], lw=2, label=f'{g} n={len(U)}')
        ax[0, j].fill_between(bin_t, lo_e, hi_e, color=C[g], alpha=.15)
        ax[1, j].plot(bin_t, med_r, color=C[g], lw=2, label=f'{g} n={len(U)}')
        ax[1, j].fill_between(bin_t, lo_r, hi_r, color=C[g], alpha=.15)
    ax[0, j].set_title(f'{sn}: 1.5-3.5Hz Hilbert envelope, 0.25s bins (fine time resolution, matched pairs)')
    ax[1, j].set_title(f'{sn}: reversal rate (nonlinear, amplitude-free texture stat)')
    for a_ in ax[:, j]:
        a_.axvline(0, color='k', lw=.5); a_.grid(alpha=.3); a_.legend(fontsize=7)
ax[0, 0].set_ylabel('envelope deg/s'); ax[1, 0].set_ylabel('reversals / s'); ax[1, 0].set_xlabel('s from jerk peak')
fig.tight_layout(); fig.savefig(f'{OUT}/fig1_fine_envelope_reversal.png', dpi=110); plt.close(fig)

# ---------------- narrow-window paired stats: pre[-0.5,0], post-immediate[0,0.5], tail[1.5,2.5] ----------------
def win_mean(bins_arr, t0, t1):
    m = (bin_t >= t0) & (bin_t < t1)
    return bins_arr[m].mean()


for j, (sn, vbs) in enumerate(strata.items()):
    P = [p for p in pairs if p[1]['vb'] in vbs]
    rows_env = []
    for r0, r1 in P:
        d0 = dict(route=r0['route'], v_pre=win_mean(env_cache[r0['uid']], -0.5, 0), v_post0=win_mean(env_cache[r0['uid']], 0, 0.5),
                  v_tail=win_mean(env_cache[r0['uid']], 1.5, 2.5), rr_pre=win_mean(rev_cache[r0['uid']], -0.5, 0),
                  rr_post0=win_mean(rev_cache[r0['uid']], 0, 0.5), rr_tail=win_mean(rev_cache[r0['uid']], 1.5, 2.5))
        d1 = dict(route=r1['route'], v_pre=win_mean(env_cache[r1['uid']], -0.5, 0), v_post0=win_mean(env_cache[r1['uid']], 0, 0.5),
                  v_tail=win_mean(env_cache[r1['uid']], 1.5, 2.5), rr_pre=win_mean(rev_cache[r1['uid']], -0.5, 0),
                  rr_post0=win_mean(rev_cache[r1['uid']], 0, 0.5), rr_tail=win_mean(rev_cache[r1['uid']], 1.5, 2.5))
        rows_env.append((d0, d1))
    out = {'n_pairs': len(P)}
    for key in ('v_pre', 'v_post0', 'v_tail', 'rr_pre', 'rr_post0', 'rr_tail'):
        b = boot_diff(rows_env, key)
        ref = np.median([d0[key] for d0, d1 in rows_env]); tq = np.median([d1[key] for d0, d1 in rows_env])
        out[key] = dict(ref=float(ref), tq=float(tq), diff=b['med'], ci_ev=b['ci_ev'], ci_rt=b['ci_rt'], n=b['n'])
    # within-T64: is post0 or tail bigger than pre, and is tail bigger than post0 (dwell-then-snap check)?
    for key_a, key_b, lbl in (('v_post0', 'v_pre', 'post0_minus_pre'), ('v_tail', 'v_pre', 'tail_minus_pre'),
                               ('v_tail', 'v_post0', 'tail_minus_post0')):
        for g, side in (('V282', 0), ('T64', 1)):
            xs = [rows_env[i][side][key_a] - rows_env[i][side][key_b] for i in range(len(rows_env))]
            xs = np.array(xs); rng = np.random.default_rng(2)
            be = [np.median(xs[rng.integers(0, len(xs), len(xs))]) for _ in range(3000)]
            out[f'{g}.{lbl}'] = dict(med=float(np.median(xs)), ci=[float(x) for x in np.percentile(be, [2.5, 97.5])], n=len(xs))
    summary_bins[sn] = out
    print(f'\n== {sn} n_pairs={len(P)} ==')
    for key in ('v_pre', 'v_post0', 'v_tail', 'rr_pre', 'rr_post0', 'rr_tail'):
        x = out[key]
        print(f'  {key:10s} ref {x["ref"]:7.3f} tq {x["tq"]:7.3f} diff {x["diff"]:+7.3f} evCI {tuple(round(v,3) for v in x["ci_ev"])} n={x["n"]}')
    for g in ('V282', 'T64'):
        for lbl in ('post0_minus_pre', 'tail_minus_pre', 'tail_minus_post0'):
            x = out[f'{g}.{lbl}']
            print(f'  {g:5s} {lbl:18s} med {x["med"]:+7.3f} ci {tuple(round(v,3) for v in x["ci"])} n={x["n"]}')

json.dump(summary_bins, open(f'{OUT}/summary_bins.json', 'w'), indent=1, default=float)

# ---------------- (D) qualitative: largest-jerk representative single events ----------------
fig, ax = plt.subplots(2, 3, figsize=(14, 6), sharex=True, sharey='row')
for j, (sn, vbs) in enumerate((('>=15 hi-jerk V282', [2, 3]),)):
    pass
picks = []
for g, vbs, n in (('V282', [2, 3], 3), ('T64', [2, 3], 3)):
    R = sorted([r for r in rows if r['group'] == g and r['vb'] in vbs], key=lambda r: -r['jerk'])[:n]
    picks.append((g, R))
fig, ax = plt.subplots(2, 3, figsize=(14, 6), sharex=True)
for col in range(3):
    for gi, (g, R) in enumerate(picks):
        if col >= len(R):
            continue
        r = R[col]; u = r['uid']
        raw = tr['sr'][u]
        xp = np.pad(raw, 200, mode='reflect'); bp = signal.sosfiltfilt(SOS, xp)[200:-200]
        ax[0, col].plot(t, raw, color=C[g], lw=1.2, alpha=.6, label=f'{g} raw' if col == 0 else None)
        ax[1, col].plot(t, bp, color=C[g], lw=1.2, label=f'{g} bp 1.5-3.5' if col == 0 else None)
    ax[0, col].axvline(0, color='k', lw=.5); ax[1, col].axvline(0, color='k', lw=.5)
    ax[0, col].grid(alpha=.3); ax[1, col].grid(alpha=.3)
    ax[0, col].set_title(f'largest-jerk #{col+1} (V282 & T64, independent picks)')
ax[0, 0].set_ylabel('sr deg/s (raw)'); ax[1, 0].set_ylabel('sr deg/s (1.5-3.5Hz)')
ax[0, 0].legend(fontsize=7); ax[1, 0].legend(fontsize=7)
fig.tight_layout(); fig.savefig(f'{OUT}/fig2_representative_largest_jerk.png', dpi=110); plt.close(fig)

print('\nsaved:', OUT)
