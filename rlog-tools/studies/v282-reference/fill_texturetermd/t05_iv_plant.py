"""t05: the torque -> wheel-rate FRF at 0.8-5 Hz, identified with the fork's FEEDFORWARD as the instrument.

Why this instrument: FF (hold, move, hyst, rl_ff, p_sp) is computed from the planner setpoint only -- no measured wheel
state enters it (code: latcontrol_torque.py 84766cdc, angle_des from setpoint; hysteresis on d(angle_des); rl_ff = g*adr).
So S_ff,rate / S_ff,u is not biased by the feedback loop (IV), provided the planner's 2-3 Hz content does not itself
respond to the wheel (camera->model path; checked by the sign of the group delay in t04, FF LEADS rate by ~0.1 s).
Fit: rate/u = j w e^{-j w d} / (k - J w^2 + j w b), weights = coherence(ff, rate), per stratum; bootstrap over runs.
Output: the effective ROUND-TRIP delay d that the work metric in t04 needs, and J, b, k at 2-3 Hz.
"""
import sys, json
import numpy as np
from scipy import optimize
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402

D = np.load(ttd.OUT + 't03_win.npz')
f = D['f']; om = 2 * np.pi * f
Xr = D['X_r']; Xu = D['X_u_e4']; Xz = D['X_ff']
L = {k: D['L_' + k] for k in ('route', 'run', 'v', 'absang', 'turn')}
v, aa = L['v'], L['absang']
STRATA = {'v3_8': (v >= 3) & (v < 8), 'v8_15_largeang': (v >= 8) & (v < 15) & (aa >= 15), 'lt15_large': (v >= 3) & (v < 15) & (aa >= 15),
          'turns_s3': L['turn'], 'v8_15': (v >= 8) & (v < 15)}
FB = (f >= 0.7) & (f <= 5.1)


def frf(idx):
    Szr = np.sum(np.conj(Xz[idx]) * Xr[idx], 0); Szu = np.sum(np.conj(Xz[idx]) * Xu[idx], 0)
    Szz = np.sum(np.abs(Xz[idx]) ** 2, 0); Srr = np.sum(np.abs(Xr[idx]) ** 2, 0); Suu = np.sum(np.abs(Xu[idx]) ** 2, 0)
    H = Szr / Szu
    coh_zr = np.abs(Szr) ** 2 / (Szz * Srr); coh_zu = np.abs(Szu) ** 2 / (Szz * Suu)
    return H, coh_zr, coh_zu


def fit(H, w):
    def model(p):
        k, J, b, d = p
        return 1j * om * np.exp(-1j * om * d) / (k - J * om ** 2 + 1j * om * b)

    def res(p):
        m = model(p)
        e = np.log(H / m)          # log-complex error: magnitude and phase on equal footing
        return np.concatenate([np.real(e) * w, np.imag(e) * w])
    best = None
    for d0 in (0.03, 0.06, 0.1, 0.15):
        for J0 in (2e-5, 5e-5, 1e-4):
            try:
                r = optimize.least_squares(res, [0.2, J0, 5e-4, d0], bounds=([0, 0, -5e-3, 0], [5, 1e-3, 5e-2, 0.4]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    return best.x, float(best.cost)


RES = {}
for sn, sm in STRATA.items():
    idx = np.where(sm)[0]
    if len(idx) < 30:
        continue
    H, czr, czu = frf(idx)
    w = np.sqrt(np.clip(czr[FB], 0, 1)) * (f[FB] >= 0.7)
    p, cost = fit(H[FB], w)
    # bootstrap over runs
    runs = L['run'][idx]; ur = np.unique(runs); bym = {u: idx[runs == u] for u in ur}
    rng = np.random.default_rng(3); PB = []
    for _ in range(150):
        ii = np.concatenate([bym[u] for u in rng.choice(ur, len(ur))])
        Hb, czb, _ = frf(ii)
        try:
            pb, _ = fit(Hb[FB], np.sqrt(np.clip(czb[FB], 0, 1)))
            PB.append(pb)
        except Exception:
            pass
    PB = np.array(PB)
    ci = {n: [float(np.percentile(PB[:, i], 2.5)), float(np.percentile(PB[:, i], 97.5))] for i, n in enumerate(('k', 'J', 'b', 'd'))}
    k, J, b, d = p
    fn = np.sqrt(k / J) / (2 * np.pi) if J > 0 else float('nan')
    zeta = b / (2 * np.sqrt(k * J)) if J > 0 and k > 0 else float('nan')
    RES[sn] = dict(nw=int(len(idx)), n_runs=int(len(ur)), k=k, J=J, b=b, d=d, f_open=float(fn), zeta_open=float(zeta), ci=ci,
                   f=f[FB].tolist(), H_mag=np.abs(H[FB]).tolist(), H_ph=np.degrees(np.angle(H[FB])).tolist(),
                   coh_ff_rate=czr[FB].tolist(), coh_ff_u=czu[FB].tolist(), cost=cost)
    print(f"{sn:16s} nw {len(idx):5d} runs {len(ur):3d}  k {k:.4f} J {J:.2e} b {b:+.2e} d {d*1000:5.1f} ms  f_open {fn:.2f} Hz zeta {zeta:+.2f}   "
          f"CI d [{ci['d'][0]*1000:.0f},{ci['d'][1]*1000:.0f}] ms  J [{ci['J'][0]:.1e},{ci['J'][1]:.1e}] b [{ci['b'][0]:+.1e},{ci['b'][1]:+.1e}] k [{ci['k'][0]:.3f},{ci['k'][1]:.3f}]")
    print('    f   ', ' '.join(f'{x:6.2f}' for x in f[FB]))
    print('    |H| ', ' '.join(f'{x:6.0f}' for x in np.abs(H[FB])))
    print('    ph  ', ' '.join(f'{x:+6.0f}' for x in np.degrees(np.angle(H[FB]))))
    print('    cohZr', ' '.join(f'{x:6.2f}' for x in czr[FB]))
json.dump(RES, open(ttd.OUT + 't05_iv_plant.json', 'w'), indent=1)
