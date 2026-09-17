"""s4_texture -- matched spectra, wheel-mode peak, dwell-then-jump, rate limiter, and event excitation.

Spectra: per group, per matching cell (speed x angle x activity, same as s4_compare), mean periodogram; the ratio
spectrum G/V282 is exp(weighted mean over cells of log(meanP_G,c / meanP_V,c)), w = min(n). Route-cluster bootstrap.
"""
import sys, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import v282cmp as V
from s4_compare import SPD, ANG, ACT, D_DIR

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture'
rng = np.random.default_rng(11)
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
COL = dict(V282='#1f5fbf', V282old='#7fa7e0', T64='#c0392b', T64B='#e67e22', T5='#8e44ad', T4='#7f8c8d')


def load(rk, key):
    D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
    keys = [str(k) for k in D['keys']]
    c = {k: D['rows'][:, i] for i, k in enumerate(keys)}
    cell = (np.digitize(c['v'], SPD) - 1) * 100 + (np.digitize(c['ang90'], ANG) - 1) * 10 + (np.digitize(c['act'], ACT) - 1)
    return dict(f=D['f'], P=D[key].astype(np.float64), cell=cell, c=c, DJ=D['DJ'], FR=D['FR'], EV=json.loads(str(D['EV'])))


def ratio_spec(Gd, Vd, sel_fn, minn=3):
    """Gd/Vd: list of (cell, P, sel). Returns ratio spectrum and weight."""
    gc = np.concatenate([d[0][d[2]] for d in Gd]); gP = np.concatenate([d[1][d[2]] for d in Gd])
    vc = np.concatenate([d[0][d[2]] for d in Vd]); vP = np.concatenate([d[1][d[2]] for d in Vd])
    num = 0; den = 0
    for c in np.intersect1d(np.unique(gc), np.unique(vc)):
        a = gP[gc == c]; b = vP[vc == c]
        if len(a) < minn or len(b) < minn:
            continue
        w = min(len(a), len(b))
        num = num + w * (np.log(a.mean(0) + 1e-12) - np.log(b.mean(0) + 1e-12)); den += w
    return (np.exp(num / den) if den else None), den


def main():
    out = {}
    routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}
    strata = {'lt15': lambda c: c['v'] < 15, 'ge15': lambda c: c['v'] >= 15,
              'lt15_ang15': lambda c: (c['v'] < 15) & (c['ang90'] >= 15)}
    fig, axs = plt.subplots(3, 3, figsize=(16, 12))
    for col, key in enumerate(['P_sr', 'P_sa', 'P_pose']):
        L = {rk: load(rk, key) for g in GROUPS for rk in routes[g]}
        f = next(iter(L.values()))['f']
        for row, (st, fn) in enumerate(strata.items()):
            ax = axs[row, col]
            Vd = [(L[rk]['cell'], L[rk]['P'], fn(L[rk]['c'])) for rk in routes['V282']]
            for g in GROUPS[1:]:
                Gd = [(L[rk]['cell'], L[rk]['P'], fn(L[rk]['c'])) for rk in routes[g]]
                r, w = ratio_spec(Gd, Vd, fn)
                if r is None:
                    continue
                # route-cluster bootstrap band
                reps = []
                for _ in range(200):
                    gk = rng.choice(len(Gd), len(Gd)); vk = rng.choice(len(Vd), len(Vd))
                    def rs(dl, ks):
                        o = []
                        for k in ks:
                            cc, PP, ss = dl[k]; idx = np.flatnonzero(ss)
                            if len(idx) == 0:
                                continue
                            i = rng.choice(idx, len(idx))
                            m = np.zeros(len(cc), bool)
                            o.append((cc[i], PP[i], np.ones(len(i), bool)))
                        return o
                    rr, _ = ratio_spec(rs(Gd, gk), rs(Vd, vk), fn)
                    if rr is not None:
                        reps.append(rr)
                lo, hi = (np.percentile(reps, 2.5, axis=0), np.percentile(reps, 97.5, axis=0)) if len(reps) > 20 else (r, r)
                s = (f >= 0.4) & (f <= (15 if key != 'P_pose' else 8))
                ax.semilogy(f[s], r[s], color=COL[g], label=f'{g} (w={w})', lw=1.6 if g in ('T64', 'V282old') else 1)
                if g in ('T64', 'V282old'):
                    ax.fill_between(f[s], lo[s], hi[s], color=COL[g], alpha=0.15)
                bands = {}
                for nm, (f1, f2) in {'0.5-1.5': (0.5, 1.5), '1.5-1.8': (1.5, 1.8), '1.8-3.0': (1.8, 3.0), '3-5': (3, 5), '5-8': (5, 8), '8-15': (8, 15)}.items():
                    b = (f >= f1) & (f < f2)
                    if key == 'P_pose' and f2 > 8:
                        continue
                    bands[nm] = dict(est=float(np.exp(np.mean(np.log(r[b])))), lo=float(np.exp(np.mean(np.log(lo[b])))), hi=float(np.exp(np.mean(np.log(hi[b])))))
                pk = (f >= 1.0) & (f <= 5)
                ipk = np.argmax(r[pk]); fpk = float(f[pk][ipk])
                out.setdefault(key, {}).setdefault(st, {})[g] = dict(w=int(w), bands=bands, ratio_peak_hz=fpk, ratio_peak=float(r[pk][ipk]))
            ax.axhline(1, color='k', lw=0.5); ax.axvspan(2.0, 2.7, color='y', alpha=0.15)
            ax.set_title(f'{key} ratio vs V282, {st} (matched speed x angle x activity)')
            ax.set_xlabel('Hz'); ax.grid(alpha=0.3)
            if row == 0 and col == 0:
                ax.legend(fontsize=8)
        # absolute pooled PSDs for the rate (mode shape), per group, in lt15 and ge15
        if key == 'P_sr':
            fig2, ax2 = plt.subplots(1, 2, figsize=(13, 5))
            for j, st in enumerate(['lt15', 'ge15']):
                for g in GROUPS:
                    P = np.concatenate([L[rk]['P'][strata[st](L[rk]['c'])] for rk in routes[g]])
                    s = (f >= 0.4) & (f <= 15)
                    ax2[j].semilogy(f[s], P.mean(0)[s], color=COL[g], label=f'{g} n={len(P)}')
                    # peak in 1.5-3.5 Hz of the mean PSD and half-power width
                    pm = P.mean(0); b = (f >= 1.2) & (f <= 4.0)
                    k = np.argmax(pm[b]); fp = f[b][k]
                    base = np.exp(np.mean(np.log(np.r_[pm[(f >= 0.9) & (f < 1.2)], pm[(f > 4.0) & (f <= 5.0)]])))
                    out.setdefault('rate_psd_peak', {}).setdefault(st, {})[g] = dict(f_peak=float(fp), prominence=float(pm[b][k] / base))
                ax2[j].axvspan(2.0, 2.7, color='y', alpha=0.15); ax2[j].set_title(f'steering-rate PSD (deg/s)^2/Hz, {st} (unmatched)')
                ax2[j].legend(fontsize=8); ax2[j].grid(alpha=0.3); ax2[j].set_xlabel('Hz')
            fig2.tight_layout(); fig2.savefig(f'{HERE}/fig_rate_psd_abs.png', dpi=110); plt.close(fig2)
        del L
    fig.tight_layout(); fig.savefig(f'{HERE}/fig_ratio_spectra.png', dpi=110); plt.close(fig)
    json.dump(out, open(f'{HERE}/s4_spectra.json', 'w'), indent=1)
    for key in out:
        for st in out[key]:
            for g, r in out[key][st].items():
                if 'bands' in r:
                    print(key, st, g, 'w', r['w'], 'peak', round(r['ratio_peak_hz'], 2), round(r['ratio_peak'], 2),
                          ' '.join(f"{b}:{x['est']:.2f}[{x['lo']:.2f},{x['hi']:.2f}]" for b, x in r['bands'].items()))
                else:
                    print(key, st, g, r)


if __name__ == '__main__':
    main()
