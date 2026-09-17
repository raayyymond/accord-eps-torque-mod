"""s5_02: the V293 (torque-mode) plant, identified from engaged hands-off drive data, and VALIDATED by output-error replay.

Equation-error fit per speed stratum, delay scanned:
    u(t - d) = J*acc + b*rate + s*hold0(theta, v) + F*tanh(rate / 2 deg/s) + c_stretch
u = delivered command = -e4/4089 (after the Honda +-0.03/frame limiter), theta = sa - angleOffset lowpassed 10 Hz,
rate/acc = derivatives of it (10 Hz lowpass each), hold0 = the fork's UNLEVELLED saturating hold map (so s = the level the
car actually needs).  Data: T64 + T64B + T5 + T4 (all V293), usable (engaged, not pressed), stretches >= 3 s.
Validation: 1.0 s output-error replay of the fitted plant from the measured initial state, driven by the logged u, vs the
"angle stays put" baseline; the fit is only used if it beats the baseline.
"""
import json, sys, math
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
import s5ctl as C  # noqa: E402

FS = 100.0
DELAYS = list(range(0, 17))  # frames of u lead removed (u sampled on the controlsState clock)
sos10 = signal.butter(2, 10.0, fs=FS, output='sos')
data = {st: [] for st in L.STRATA}
for g in ('T64', 'T64B', 'T5', 'T4'):
    for rk in L.GROUPS[g]:
        S = L.V.load(rk)
        u_all = -S['e4'] / 4089.0
        th_all = S['sa'] - np.nan_to_num(S['aoff'])
        for st in L.STRATA:
            m = L.V.usable(S, st[0], st[1]) & np.isfinite(u_all) & np.isfinite(th_all)
            for a, b in L.V.runs(m, S['t'], min_s=3.0):
                th = signal.sosfiltfilt(sos10, th_all[a:b])
                rate = np.gradient(th) * FS
                acc = signal.sosfiltfilt(sos10, np.gradient(rate) * FS)
                v = S['v'][a:b]
                h0 = np.array([C.hold_torque(x, y, False) for x, y in zip(th, v)])
                data[st].append(dict(g=g, u=u_all[a:b].copy(), th=th, rate=rate, acc=acc, h0=h0, v=v.copy(),
                                     th_raw=th_all[a:b].copy()))
        del S

res = {}
for st, segs in data.items():
    best = None; prof = []
    for dN in DELAYS:
        X, Y, groups = [], [], []
        for k, s in enumerate(segs):
            n = len(s['u'])
            if n <= dN + 20:
                continue
            y = s['u'][:n - dN]          # u(t - d) aligned with state at t
            sl = slice(dN, n)
            cols = [s['acc'][sl], s['rate'][sl], s['h0'][sl], np.tanh(s['rate'][sl] / 2.0)]
            X.append(np.column_stack(cols)); Y.append(y); groups.append(np.full(len(y), k))
        X = np.vstack(X); Y = np.concatenate(Y); grp = np.concatenate(groups)
        # per-stretch bias: demean within stretch
        for k in np.unique(grp):
            mk = grp == k
            X[mk] -= X[mk].mean(0); Y[mk] -= Y[mk].mean()
        coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
        r2 = 1 - np.sum((Y - X @ coef) ** 2) / np.sum(Y ** 2)
        prof.append((dN, round(float(r2), 4), float(coef[0]), float(coef[1]), float(coef[3])))
        if best is None or r2 > best['r2']:
            best = dict(d=dN / FS, J=float(coef[0]), b=float(coef[1]), s=float(coef[2]), F=float(coef[3]), r2=float(r2),
                        n=int(len(Y)))
    # bootstrap over stretches at the best delay
    dN = int(round(best['d'] * FS)); rng = np.random.default_rng(1); boots = []
    usable_segs = [s for s in segs if len(s['u']) > dN + 20]
    for _ in range(200):
        pick = rng.integers(0, len(usable_segs), len(usable_segs))
        X, Y = [], []
        for k in pick:
            s = usable_segs[k]; n = len(s['u']); sl = slice(dN, n)
            x = np.column_stack([s['acc'][sl], s['rate'][sl], s['h0'][sl], np.tanh(s['rate'][sl] / 2.0)]); y = s['u'][:n - dN]
            X.append(x - x.mean(0)); Y.append(y - y.mean())
        c, *_ = np.linalg.lstsq(np.vstack(X), np.concatenate(Y), rcond=None)
        boots.append(c)
    boots = np.array(boots)
    ci = {nm: [float(np.percentile(boots[:, i], 2.5)), float(np.percentile(boots[:, i], 97.5))] for i, nm in enumerate(('J', 'b', 's', 'F'))}
    best['delay_profile'] = prof
    print('  delay profile (frames, r2, J, b, F):', [(p[0], p[1]) for p in prof])
    best['ci'] = ci; best['stretches'] = len(usable_segs); best['sec'] = sum(len(s['u']) for s in usable_segs) / FS

    # output-error replay validation, 1.0 s windows, semi-implicit Euler at 1 kHz substeps
    H = 100; errs_fit = []; errs_hold = []; errs_nof = []
    for s in usable_segs:
        n = len(s['u'])
        for w0 in range(dN + 5, n - H, 50):
            for tag, par, store in (('fit', best, errs_fit), ('nofric', dict(best, F=0.0), errs_nof)):
                th = s['th'][w0]; om = s['rate'][w0]
                c0 = s['u'][w0 - dN] - (par['J'] * s['acc'][w0] + par['b'] * om + par['s'] * s['h0'][w0] + par['F'] * math.tanh(om / 2.0))
                tr = np.empty(H)
                for j in range(H):
                    uu = s['u'][w0 + j - dN] - c0
                    for _ in range(10):
                        acc = (uu - par['b'] * om - par['s'] * C.hold_torque(th, float(s['v'][w0 + j]), False) - par['F'] * math.tanh(om / 2.0)) / max(par['J'], 1e-6)
                        om += acc * 0.001; th += om * 0.001
                    tr[j] = th
                store.append(float(np.sqrt(np.mean((tr - s['th'][w0:w0 + H]) ** 2))))
            errs_hold.append(float(np.sqrt(np.mean((s['th'][w0] - s['th'][w0:w0 + H]) ** 2))))
    best['replay_1s_rms_deg'] = dict(fit=float(np.median(errs_fit)), no_friction=float(np.median(errs_nof)),
                                     hold_baseline=float(np.median(errs_hold)), windows=len(errs_fit))
    wn = math.sqrt(max(best['s'], 1e-6) * float(np.interp(np.mean(st), C.HOLD_V_BP, C.HOLD_K_V)) / max(best['J'], 1e-9))
    best['mode_hz'] = wn / (2 * math.pi)
    best['zeta'] = best['b'] / (2 * math.sqrt(max(best['J'], 1e-9) * max(best['s'], 1e-6) * float(np.interp(np.mean(st), C.HOLD_V_BP, C.HOLD_K_V))))
    res[f'{st[0]:.0f}-{st[1]:.0f}'] = best
    print(f'{st}', json.dumps(best), flush=True)
json.dump(res, open(L.OUT + 's5_02_plant_ident.json', 'w'), indent=1)
