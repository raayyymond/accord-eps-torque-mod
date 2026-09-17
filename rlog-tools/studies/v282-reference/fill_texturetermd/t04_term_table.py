"""t04: per-term table in 1.5-3.5 Hz: band share of the command, coherence with the wheel rate, phase vs rate, group
delay, and the delayed-torque WORK on the wheel expressed as an equivalent viscous coefficient b_eq (torque per deg/s;
>0 damps, <0 pumps), per stratum, per route group and pooled, with run-block bootstrap CIs.

Controls built in:
  * rl_fb IS a first-order-filtered copy of the rate x gain -> coherence must read ~1 and phase ~ -0.6..-1.4 deg*... (+sign
    torque +left = +g*rate; the fork subtracts it: rl_fb as +left torque = -g*rm -> phase ~180 deg).  POSITIVE CONTROL.
  * shuffled-window pairing -> coherence floor.  NEGATIVE CONTROL.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402

D = np.load(ttd.OUT + 't03_win.npz')
f = D['f']; om = 2 * np.pi * f
BANDB = (f >= 1.5) & (f <= 3.55)
GDB = (f >= 1.1) & (f <= 4.4)
NAMES = ttd.TERMS + ['ff', 'fb', 'total', 'u_log', 'u_e4', 'setpoint', 'rd']
X = {k: D['X_' + k] for k in NAMES + ['r']}
L = {k: D['L_' + k] for k in ('route', 'run', 'v', 'absang', 'turn', 'limfrac')}
groups = {'T64': [0, 1], 'T64B': [2], 'T5': [3], 'T4': [4], 'ALL': [0, 1, 2, 3, 4]}
v, aa = L['v'], L['absang']
STRATA = {
    'lt15_small': (v >= 3) & (v < 15) & (aa < 15),
    'lt15_large': (v >= 3) & (v < 15) & (aa >= 15),
    'turns_s3': L['turn'],
    'v3_8': (v >= 3) & (v < 8),
    'v8_15': (v >= 8) & (v < 15),
    'ge15': v >= 15,
}
DELAYS = [0.0, 0.03, 0.042, 0.047, 0.059, 0.06, 0.08, 0.09, 0.12, 0.15]


def metrics(idx):
    R = X['r'][idx]
    Srr = np.sum(np.abs(R) ** 2, 0)
    T = X['total'][idx]; Stt = np.sum(np.abs(T) ** 2, 0)
    out = dict(nw=int(len(idx)), rate_rms_band=float(np.sqrt(Srr[BANDB].sum() / max(len(idx), 1)) * np.sqrt(2) / 256 * np.sqrt(8 / 3)))
    wr = Srr[BANDB]
    for n in NAMES:
        Xn = X[n][idx]
        Sxr = np.sum(np.conj(R) * Xn, 0); Sxx = np.sum(np.abs(Xn) ** 2, 0); Stx = np.sum(np.conj(T) * Xn, 0)
        coh = np.abs(Sxr) ** 2 / np.maximum(Sxx * Srr, 1e-30)
        ph = np.unwrap(np.angle(Sxr[GDB]))
        gd = -np.polyfit(om[GDB], ph, 1, w=np.sqrt(Srr[GDB]))[0]
        r = dict(share=float(np.real(Stx[BANDB].sum()) / Stt[BANDB].sum()),
                 coh=float(np.average(coh[BANDB], weights=wr)),
                 phase=float(np.degrees(np.angle(Sxr[BANDB].sum()))), gd=float(gd),
                 rel_rms=float(np.sqrt(Sxx[BANDB].sum() / Stt[BANDB].sum())))
        for d in DELAYS:
            r[f'beq_{int(d*1000)}'] = float(-np.real(np.sum(Sxr[BANDB] * np.exp(-1j * om[BANDB] * d))) / wr.sum())
        out[n] = r
    return out


def boot(idx, nb=300, seed=0):
    rng = np.random.default_rng(seed)
    runs = L['run'][idx]; ur = np.unique(runs)
    bym = {u: idx[runs == u] for u in ur}
    res = []
    for _ in range(nb):
        pick = rng.choice(ur, len(ur))
        res.append(metrics(np.concatenate([bym[u] for u in pick])))
    return res


def shuffle_floor(idx, seed=1):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(idx)
    R = X['r'][perm]; Srr = np.sum(np.abs(R) ** 2, 0); wr = Srr[BANDB]
    o = {}
    for n in ('dob', 'rl_fb', 'p_meas', 'hold', 'total'):
        Xn = X[n][idx]; Sxr = np.sum(np.conj(R) * Xn, 0); Sxx = np.sum(np.abs(Xn) ** 2, 0)
        o[n] = float(np.average(np.abs(Sxr[BANDB]) ** 2 / np.maximum(Sxx[BANDB] * wr, 1e-30), weights=wr))
    return o


RES = {}
for sn, sm in STRATA.items():
    RES[sn] = {}
    for gn, rr in groups.items():
        idx = np.where(sm & np.isin(L['route'], rr))[0]
        if len(idx) < 8:
            continue
        m = metrics(idx)
        m['floor'] = shuffle_floor(idx)
        m['n_runs'] = int(len(np.unique(L['run'][idx])))
        if gn in ('ALL', 'T64', 'T4', 'T64B', 'T5'):
            B = boot(idx, nb=200)
            ci = {}
            for n in NAMES:
                ci[n] = {k: [float(np.percentile([b[n][k] for b in B], 2.5)), float(np.percentile([b[n][k] for b in B], 97.5))]
                         for k in ('share', 'coh', 'phase', 'gd', 'beq_47', 'beq_42', 'beq_59', 'beq_60', 'beq_80', 'beq_120')}
            m['ci'] = ci
        RES[sn][gn] = m
json.dump(RES, open(ttd.OUT + 't04_term_table.json', 'w'), indent=1)

for sn in STRATA:
    for gn in ('ALL', 'T64', 'T64B', 'T5', 'T4'):
        if gn not in RES[sn]:
            continue
        m = RES[sn][gn]
        print(f"\n=== {sn} / {gn}: windows {m['nw']} runs {m['n_runs']}  rate band rms ~{m['rate_rms_band']:.2f} deg/s  coh floor(dob,total) {m['floor']['dob']:.3f},{m['floor']['total']:.3f}")
        print(f"   {'term':9s} {'share':>7s} {'coh':>6s} {'phase':>7s} {'gd_s':>7s} {'b_eq@0':>9s} {'b_eq@60ms':>10s} {'b_eq@120':>9s}  CI(share) CI(beq60)")
        for n in NAMES:
            r = m[n]; ci = m.get('ci', {}).get(n, {})
            cs = ci.get('share', [np.nan, np.nan]); cb = ci.get('beq_60', [np.nan, np.nan])
            print(f"   {n:9s} {r['share']:+7.3f} {r['coh']:6.3f} {r['phase']:+7.1f} {r['gd']:+7.3f} {r['beq_0']:+9.2e} {r['beq_60']:+10.2e} {r['beq_120']:+9.2e}  [{cs[0]:+.2f},{cs[1]:+.2f}] [{cb[0]:+.1e},{cb[1]:+.1e}]")
