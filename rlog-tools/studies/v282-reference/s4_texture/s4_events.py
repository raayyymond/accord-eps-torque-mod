"""s4_texture -- dwell-then-jump rates, rate-limiter binding by angle/events, event excitation of the 2-3 Hz band,
command->wheel coherence, and an AR pole estimate of the wheel mode.  One route at a time for the cache-heavy parts."""
import sys, json
import numpy as np
from scipy import signal, linalg

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import v282cmp as V
from s4_compare import D_DIR

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
rng = np.random.default_rng(5)
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}


def boot_ratio(per_route_num, per_route_den, B=2000):
    """ratio of sums with route-cluster bootstrap. inputs: lists (one per route) of arrays of per-item values."""
    num = np.array([x.sum() for x in per_route_num]); den = np.array([x for x in per_route_den])
    est = num.sum() / max(den.sum(), 1e-9)
    reps = []
    for _ in range(B):
        k = rng.integers(0, len(num), len(num))
        reps.append(num[k].sum() / max(den[k].sum(), 1e-9))
    return float(est), [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]


def ar_poles(x, p=10, fs=25.0):
    """Burg-free least-squares AR(p) fit; returns (f_hz, zeta) of complex poles."""
    x = x - x.mean()
    Y = x[p:]; X = np.column_stack([x[p - k - 1:len(x) - k - 1] for k in range(p)])
    a, *_ = np.linalg.lstsq(X, Y, rcond=None)
    z = np.roots(np.r_[1, -a])
    s = np.log(z.astype(complex)) * fs
    out = []
    for si in s:
        if si.imag > 0:
            wn = abs(si); out.append((wn / (2 * np.pi), -si.real / wn))
    return out


def main():
    res = {}
    SPB = [(0, 8), (8, 15), (15, 22), (22, 40)]
    ANB = [(0, 5), (5, 15), (15, 45), (45, 1e9)]
    for g in GROUPS:
        R = {}
        for rk in routes[g]:
            D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
            keys = [str(k) for k in D['keys']]
            c = {k: D['rows'][:, i] for i, k in enumerate(keys)}
            R[rk] = dict(c=c, DJ=D['DJ'], FR=D['FR'], EV=json.loads(str(D['EV'])))
        gres = {}
        # --- dwell-then-jump per 100 deg of travel, by speed band (travel from blocks; DJ are from the same runs)
        for (s0, s1) in [(0, 15), (15, 40), (0, 8), (8, 15)]:
            nums, dens, jumps = [], [], []
            for rk, d in R.items():
                DJ = d['DJ']; m = (DJ[:, 0] >= s0) & (DJ[:, 0] < s1)
                nums.append(np.ones(m.sum())); dens.append(d['c']['travel'][(d['c']['v'] >= s0) & (d['c']['v'] < s1)].sum() / 100.0)
                jumps.append(DJ[m, 3])
            est, ci = boot_ratio(nums, dens)
            J = np.concatenate(jumps) if jumps else np.array([])
            gres[f'dj_per100deg_{s0}_{s1}'] = dict(est=est, ci=ci, n=int(sum(len(x) for x in nums)), travel_deg=float(sum(dens) * 100),
                                                   jump_p50=float(np.median(J)) if len(J) else None,
                                                   jump_p90=float(np.percentile(J, 90)) if len(J) else None,
                                                   per_route=[float(len(n) / max(dd, 1e-9)) for n, dd in zip(nums, dens)])
        # --- rate limiter binding and saturation by speed x angle (frames)
        FRs = {rk: d['FR'] for rk, d in R.items()}
        lim = {}
        for (s0, s1) in [(0, 15), (15, 40)]:
            for (a0, a1) in ANB:
                nums, dens, sat = [], [], []
                for rk, F in FRs.items():
                    m = (F[0] >= s0) & (F[0] < s1) & (F[1] >= a0) & (F[1] < a1)
                    nums.append((F[2][m] >= 120).astype(float)); dens.append(float(m.sum())); sat.append((F[3][m] >= 4000).sum())
                est, ci = boot_ratio(nums, dens)
                lim[f'v{s0}-{s1}_a{a0}-{int(min(a1, 999))}'] = dict(frames=int(sum(dens)), rate_limited=est, ci=ci,
                                                                     saturated=float(sum(sat) / max(sum(dens), 1)))
        gres['rate_limiter'] = lim
        # --- events: 2-3 Hz excitation and limiter binding
        ev = [dict(e, route=rk) for rk, d in R.items() for e in d['EV']]
        for kind in ['jerk04', 'jerk08', 'acc10']:
            for (s0, s1) in [(0, 15), (15, 40)]:
                E = [e for e in ev if e['kind'] == kind and s0 <= e['v'] < s1]
                if not E:
                    gres[f'ev_{kind}_{s0}_{s1}'] = dict(n=0); continue
                arr = lambda k: np.array([e[k] for e in E], float)
                rks = np.array([e['route'] for e in E])
                def bmed(x):
                    x = np.asarray(x); ur = np.unique(rks); reps = []
                    for _ in range(1000):
                        pick = rng.choice(ur, len(ur))
                        xs = np.concatenate([rng.choice(x[rks == r], (rks == r).sum()) for r in pick])
                        xs = xs[np.isfinite(xs)]
                        if len(xs): reps.append(np.median(xs))
                    return float(np.nanmedian(x)), [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]
                o = dict(n=len(E), n_routes=int(len(np.unique(rks))))
                for k in ['md_post', 'hf_post', 'hf_ratio', 'slew_hit', 'stall', 'jerk_rough', 'jerk_rough_pose', 'ang_max', 'rate_max', 'la_peak', 'gain', 'lag']:
                    o[k] = bmed(arr(k))
                if kind != 'acc10':
                    o['md_post_over_pre'] = bmed(arr('md_post') / np.maximum(arr('md_pre'), 0.3))
                    o['jerk'] = bmed(arr('jerk'))
                o['frac_events_any_ratelimit'] = float(np.mean(arr('slew_hit') > 0))
                gres[f'ev_{kind}_{s0}_{s1}'] = o
        res[g] = gres
        print(g, json.dumps({k: (v if k != 'rate_limiter' else None) for k, v in gres.items() if k.startswith('dj')}, default=str)[:900])
        print('  limiter', {k: (round(v['rate_limited'] * 100, 3), v['frames']) for k, v in lim.items()})
        for k, v in gres.items():
            if k.startswith('ev_') and v.get('n'):
                print('  ', k, 'n', v['n'], 'md_post', np.round(v['md_post'][0], 2), 'post/pre', np.round(v.get('md_post_over_pre', [np.nan])[0], 2),
                      'hf_ratio', np.round(v['hf_ratio'][0], 3), 'slew', np.round(v['slew_hit'][0], 4), 'anyRL', round(v['frac_events_any_ratelimit'], 2),
                      'jr_pose', np.round(v['jerk_rough_pose'][0], 3), 'angmax', np.round(v['ang_max'][0], 1), 'ratemax', np.round(v['rate_max'][0], 1), 'jerk', np.round(v.get('jerk', [np.nan])[0], 2))
        del R, FRs
    # --- per-route: command->wheel coherence at 2-3 Hz, command variance share 1.5-5 Hz, AR mode poles (torque + V282)
    cohres = {}
    for g in GROUPS:
        for rk in routes[g]:
            S = V.load(rk); u = V.usable(S); t = S['t']
            e4 = np.nan_to_num(S['e4']); sr = np.nan_to_num(S['sr']); v = np.nan_to_num(S['v'])
            Pxx = Pyy = Pxy = None; poles = {'lt15': [], 'ge15': []}; share = []
            for a, b in V.runs(u, t, min_s=10.24):
                x = e4[a:b] - e4[a:b].mean(); y = sr[a:b] - sr[a:b].mean()
                f, pxx = signal.welch(x, 100, nperseg=512); _, pyy = signal.welch(y, 100, nperseg=512); _, pxy = signal.csd(x, y, 100, nperseg=512)
                w = b - a
                Pxx = pxx * w if Pxx is None else Pxx + pxx * w; Pyy = pyy * w if Pyy is None else Pyy + pyy * w; Pxy = pxy * w if Pxy is None else Pxy + pxy * w
                # AR poles on 10 s pieces, decimated to 25 Hz
                for k0 in range(0, b - a - 1000 + 1, 1000):
                    seg = sr[a + k0:a + k0 + 1000]
                    vv = np.median(v[a + k0:a + k0 + 1000])
                    ds = signal.decimate(seg, 4, zero_phase=True)
                    for fh, z in ar_poles(ds):
                        if 1.5 <= fh <= 4.0:
                            poles['lt15' if vv < 15 else 'ge15'].append((fh, z))
            s1 = (f >= 1.8) & (f < 3.0); s2 = (f >= 1.5) & (f < 5.0); s0 = (f >= 0.05) & (f < 1.5)
            coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
            o = dict(group=g, coh_e4_sr_1p8_3=float(np.mean(coh[s1])), e4_var_share_1p5_5=float(Pxx[s2].sum() / Pxx[(f >= 0.05) & (f < 20)].sum()),
                     sr_var_share_1p5_5=float(Pyy[s2].sum() / Pyy[(f >= 0.05) & (f < 20)].sum()))
            for st, pl in poles.items():
                if len(pl) >= 5:
                    P = np.array(pl)
                    # the least-damped pole per piece is what rings; report the distribution of all 1.5-4 Hz poles
                    o[f'ar_{st}'] = dict(n=len(P), f_med=float(np.median(P[:, 0])), zeta_p25=float(np.percentile(P[:, 1], 25)),
                                         zeta_med=float(np.median(P[:, 1])), frac_zeta_lt_0p2=float(np.mean(P[:, 1] < 0.2)))
            cohres[rk] = o
            print(rk, o, flush=True)
            del S
    res['per_route'] = cohres
    json.dump(res, open(f'{HERE}/s4_events.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
