"""s5_01: the EFFECTIVE ACTUATOR on each EPS, identified from engaged drive data.

u = cs_out (+left torque-command units, e4 = -~4089 u), y = steering angle (sa - liveParameters angleOffset) and rate.
Estimator: instrumental-variable FRF H = S_r,y / S_r,u with r = the MODEL's demanded lateral accel (external to the
steering loop), per speed stratum, per group; 2.56 s Welch segments (0.39 Hz bins), linear detrend.
Parametric fits on the IV FRF (0.3-4 Hz, weight = coh_ry * coh_ru):
   SPRING  (torque mode):  theta/u = e^{-jwd} / (k + j w b - J w^2)
   SERVO   (rate servo):   theta/u = G e^{-jwd} / ((j w + a)(1 + j w / wc))
Both forms are fitted to both EPS; the residual says which world each EPS is in.
"""
import json, sys
import numpy as np
from scipy import optimize
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402

NPS = 256
res = {}


def fit(f, H, w, form):
    s = 1j * 2 * np.pi * f
    def model(p):
        if form == 'spring':
            k, b, J, d = p
            return np.exp(-s * d) / (k + s * b + s * s * J)
        G, a, fc, d = p
        return G * np.exp(-s * d) / ((s + a) * (1 + s / (2 * np.pi * fc)))
    def resid(p):
        e = (model(p) - H) / np.maximum(np.abs(H), 1e-9)   # relative complex error
        return np.concatenate([np.sqrt(w) * e.real, np.sqrt(w) * e.imag])
    if form == 'spring':
        best = None
        for k0 in (0.003, 0.01, 0.03):
            for J0 in (1e-5, 1e-4, 1e-3):
                r = optimize.least_squares(resid, [k0, 1e-3, J0, 0.06], bounds=([1e-5, -0.05, 0.0, 0.0], [1.0, 0.2, 0.05, 0.4]))
                if best is None or r.cost < best.cost:
                    best = r
    else:
        best = None
        for G0 in (30, 100, 300):
            for fc0 in (1.0, 3.0, 8.0):
                r = optimize.least_squares(resid, [G0, 1.0, fc0, 0.05], bounds=([0.1, -5.0, 0.05, 0.0], [5000, 50.0, 50.0, 0.4]))
                if best is None or r.cost < best.cost:
                    best = r
    p = best.x
    rel = float(np.sqrt(np.sum(w * np.abs((model(p) - H) / np.abs(H)) ** 2) / np.sum(w)))
    return [float(x) for x in p], rel


for g, routes in L.GROUPS.items():
    accs = {st: {} for st in L.STRATA}
    for rk in routes:
        S = L.V.load(rk)
        th = S['sa'] - np.nan_to_num(S['aoff'])
        for st in L.STRATA:
            for a, b in L.stretches(S, st[0], st[1], min_s=2 * NPS / L.FS):
                r = np.nan_to_num(S['model'][a:b]); u = S['out'][a:b]
                L.frf_accumulate(accs[st], r, u, dict(th=th[a:b], rate=S['sr'][a:b]), NPS)
        del S
    res[g] = {}
    for st, acc in accs.items():
        if acc.get('sec', 0) < 20:
            res[g][f'{st[0]:.0f}-{st[1]:.0f}'] = dict(sec=acc.get('sec', 0))
            continue
        R = L.frf_result(acc, 'th'); Rr = L.frf_result(acc, 'rate')
        f = R['f']; sel = (f >= 0.3) & (f <= 4.0)
        w = (R['coh_ry'] * R['coh_ru'])[sel]
        out = dict(sec=round(acc['sec']), n=acc['n'])
        for form in ('spring', 'servo'):
            p, rel = fit(f[sel], R['H_iv'][sel], w, form)
            out[form] = dict(p=p, rel_err=rel)
        # table of the IV FRF at a few bins
        rows = []
        for fb in (0.39, 0.78, 1.17, 1.56, 1.95, 2.34, 2.73, 3.13, 3.52, 3.91, 4.69):
            i = int(np.argmin(np.abs(f - fb)))
            rows.append(dict(f=round(float(f[i]), 2), th_mag=float(np.abs(R['H_iv'][i])), th_ph=float(np.degrees(np.angle(R['H_iv'][i]))),
                             rate_mag=float(np.abs(Rr['H_iv'][i])), rate_ph=float(np.degrees(np.angle(Rr['H_iv'][i]))),
                             th_dir_mag=float(np.abs(R['H_dir'][i])), coh_ru=float(R['coh_ru'][i]), coh_ry=float(R['coh_ry'][i]),
                             coh_uy=float(R['coh_uy'][i])))
        out['bins'] = rows
        res[g][f'{st[0]:.0f}-{st[1]:.0f}'] = out
        print(f"{g:7s} {st[0]:4.0f}-{st[1]:<4.0f} {acc['sec']:6.0f}s  spring k={out['spring']['p'][0]:.4f} b={out['spring']['p'][1]:.4f} "
              f"J={out['spring']['p'][2]:.2e} d={out['spring']['p'][3]:.3f} rel={out['spring']['rel_err']:.2f} | servo G={out['servo']['p'][0]:.0f} "
              f"a={out['servo']['p'][1]:.2f} fc={out['servo']['p'][2]:.2f} d={out['servo']['p'][3]:.3f} rel={out['servo']['rel_err']:.2f}", flush=True)
        for rw in rows:
            print(f"      f={rw['f']:.2f} |th/u|={rw['th_mag']:7.1f} ph={rw['th_ph']:7.1f}  |rate/u|={rw['rate_mag']:7.0f} ph={rw['rate_ph']:7.1f} "
                  f"dir={rw['th_dir_mag']:6.1f} coh ru={rw['coh_ru']:.2f} ry={rw['coh_ry']:.2f} uy={rw['coh_uy']:.2f}")

json.dump(res, open(L.OUT + 's5_01_actuator_frf.json', 'w'), indent=1)
