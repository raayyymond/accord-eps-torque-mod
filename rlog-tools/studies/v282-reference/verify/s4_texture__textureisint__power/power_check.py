"""POWER-lens adversarial check on finding s4_texture 'texture-is-in-the-wheel-not-in-vehicle-yaw'.

Two things:
 (1) Retrospective MDE for the two vehicle-yaw-side metrics the finding leans on:
     jerk_rough (livePose-derived jerk, time-domain, ge15 stratum, T64 vs V282)
     P_pose band-power 1.8-3.0 Hz (spectral, ge15 stratum, T64 vs V282)
     Method: shift-resample power simulation. Rescale the T64 (treatment) block values by a
     trial multiplicative factor so the *expected* matched-effect equals a hypothetical true
     ratio rho, then re-run the SAME two-level (route+block) cluster bootstrap the original
     s4_compare.py uses, many times, and record the fraction of runs whose 95% CI excludes 1.
     That fraction IS the retrospective power for detecting a true effect of size rho, using
     THIS data (this n, this noise). Report rho at 80% power (rho80) for each metric.
 (2) Verify the 'cs_yaw is identically 0' claim across every cached route (not just the two
     named), since the finding's whole 'weak instrument' framing rests on la_yaw being unusable.
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import v282cmp as V
from s4_compare import SPD, ANG, ACT, MIN, D_DIR

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__textureisint__power'
rng = np.random.default_rng(2026)


def load_route(rk):
    D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
    keys = [str(k) for k in D['keys']]
    rows = D['rows']
    c = {k: rows[:, i] for i, k in enumerate(keys)}
    f = D['f']
    band = (f >= 1.8) & (f < 3.0)
    c['pband18_30'] = D['P_pose'][:, band].mean(axis=1).astype(np.float64)
    cell = (np.digitize(c['v'], SPD) - 1) * 100 + (np.digitize(c['ang90'], ANG) - 1) * 10 + (np.digitize(c['act'], ACT) - 1)
    return c, cell


def matched_effect(Gb, Vb):
    """Gb, Vb: lists of (cell array, metric array). Log-ratio, median per cell, weight=min(n)."""
    gc = np.concatenate([x[0] for x in Gb]); gm = np.concatenate([x[1] for x in Gb])
    vc = np.concatenate([x[0] for x in Vb]); vm = np.concatenate([x[1] for x in Vb])
    num = den = 0.0
    for c in np.intersect1d(np.unique(gc), np.unique(vc)):
        a = gm[(gc == c) & np.isfinite(gm)]; b = vm[(vc == c) & np.isfinite(vm)]
        if len(a) < MIN or len(b) < MIN:
            continue
        ma, mb = np.median(a), np.median(b)
        w = min(len(a), len(b))
        if ma <= 0 or mb <= 0:
            ma, mb = ma + 1e-3, mb + 1e-3
        num += w * (np.log(ma) - np.log(mb)); den += w
    if den == 0:
        return np.nan, 0
    return float(np.exp(num / den)), int(den)


def stratum_ge15(c):
    return c['v'] >= 15


def prep(c, cell, metric, sel):
    m = c[metric][sel]
    return cell[sel], m


def bootstrap_ci(Gd, Vd, B=300):
    """Gd, Vd: dict rk -> (cell, metric). Two-level cluster bootstrap (route then block). Returns 95% CI."""
    Gr = list(Gd.keys()); Vr = list(Vd.keys())
    reps = []
    for _ in range(B):
        def rs(dd, keys):
            ks = list(rng.choice(keys, len(keys), replace=True))
            o = []
            for k in ks:
                cc, mm = dd[k]
                if len(cc) == 0:
                    continue
                i = rng.integers(0, len(cc), len(cc))
                o.append((cc[i], mm[i]))
            return o
        g = rs(Gd, Gr); v = rs(Vd, Vr)
        if not g or not v:
            continue
        e, _ = matched_effect(g, v)
        if np.isfinite(e):
            reps.append(e)
    if len(reps) < 50:
        return None, None, len(reps)
    lo, hi = np.percentile(reps, 2.5), np.percentile(reps, 97.5)
    return lo, hi, len(reps)


def power_curve(Gd0, Vd, metric_name, rhos, B_ci=250, n_trials=60):
    """For each candidate true ratio rho, rescale G's metric values so E[matched_effect]~rho,
    then repeat: draw a bootstrap CI, check if it excludes 1. Power = fraction excluding 1 over n_trials."""
    # baseline (unscaled) observed effect, to compute rescale factor
    e0, w0 = matched_effect(list(Gd0.values()), list(Vd.values()))
    print(f'  [{metric_name}] baseline observed effect={e0:.3f} w={w0}')
    out = []
    for rho in rhos:
        scale = rho / e0
        Gd = {rk: (c, m * scale) for rk, (c, m) in Gd0.items()}
        hits = 0; n_ok = 0
        for _ in range(n_trials):
            # resample once at "data" level to get a fresh synthetic draw (route+block resample),
            # THEN bootstrap CI around that draw -- this approximates rerunning the whole
            # experiment n_trials times under a true effect of rho, using only the data we have.
            def draw(dd):
                keys = list(dd.keys())
                ks = list(rng.choice(keys, len(keys), replace=True))
                o = {}
                for i, k in enumerate(ks):
                    cc, mm = dd[k]
                    idx = rng.integers(0, len(cc), len(cc))
                    o[f'{k}#{i}'] = (cc[idx], mm[idx])
                return o
            Gdraw = draw(Gd); Vdraw = draw(Vd)
            lo, hi, nreps = bootstrap_ci(Gdraw, Vdraw, B=B_ci)
            if lo is None:
                continue
            n_ok += 1
            if lo > 1.0 or hi < 1.0:
                hits += 1
        power = hits / n_ok if n_ok else np.nan
        out.append(dict(rho=rho, power=power, n_ok=n_ok))
        print(f'    rho={rho:.2f} power={power:.2f} (n_ok={n_ok})')
    return out


def find_rho_at_power(curve, target=0.8):
    rhos = [p['rho'] for p in curve]; pows = [p['power'] for p in curve]
    for i in range(1, len(rhos)):
        if pows[i - 1] < target <= pows[i]:
            r0, r1 = rhos[i - 1], rhos[i]; p0, p1 = pows[i - 1], pows[i]
            frac = (target - p0) / (p1 - p0) if p1 != p0 else 0
            return r0 + frac * (r1 - r0)
    if pows and pows[0] >= target:
        return rhos[0]
    return None


def main():
    T64_routes = ['0000006c--68c6e94b17', '0000006d--05e83bb04f']
    V282_routes = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']

    Gc = {rk: load_route(rk) for rk in T64_routes}
    Vc = {rk: load_route(rk) for rk in V282_routes}

    results = {}
    for metric in ['jerk_rough', 'pband18_30']:
        print(f'\n=== metric {metric}, stratum ge15, T64 vs V282 ===')
        Gd0 = {rk: prep(c, cell, metric, stratum_ge15(c)) for rk, (c, cell) in Gc.items()}
        Vd = {rk: prep(c, cell, metric, stratum_ge15(c)) for rk, (c, cell) in Vc.items()}
        e0, w0 = matched_effect(list(Gd0.values()), list(Vd.values()))
        lo0, hi0, nreps0 = bootstrap_ci(Gd0, Vd, B=1000)
        print(f'  observed: est={e0:.3f} ci95=[{lo0:.3f},{hi0:.3f}] w={w0} nreps={nreps0}')
        rhos = [1.0, 1.15, 1.3, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]
        curve = power_curve(Gd0, Vd, metric, rhos, B_ci=200, n_trials=50)
        rho80 = find_rho_at_power(curve, 0.8)
        rho50 = find_rho_at_power(curve, 0.5)
        results[metric] = dict(observed_est=e0, observed_ci95=[lo0, hi0], w=w0, curve=curve,
                                rho_at_80pct_power=rho80, rho_at_50pct_power=rho50)
        print(f'  ==> rho for 80% power = {rho80}, rho for 50% power = {rho50}')

    # (2) cs_yaw all-zero check, on the RAW cache (V.load() only exposes la_yaw = interp(cs_yaw)*v,
    # never the raw carState.yawRate field), across EVERY cached route (not just the two named).
    print('\n=== cs_yaw all-zero check, raw cache, all routes ===')
    import glob, os
    cs_yaw_report = {}
    for p in sorted(glob.glob(str(V.CACHE) + '/*.npz')):
        rk = os.path.basename(p)[:-4]
        D = np.load(p, allow_pickle=True)
        if 'cs_yaw' not in D.files:
            cs_yaw_report[rk] = dict(present=False)
            continue
        y = D['cs_yaw']
        finite = np.isfinite(y)
        allzero = bool(np.all(y[finite] == 0)) if finite.any() else None
        cs_yaw_report[rk] = dict(present=True, n=int(len(y)), n_finite=int(finite.sum()),
                                  n_nonzero=int(np.sum(y[finite] != 0)) if finite.any() else 0,
                                  all_zero=allzero, in_ROUTES=rk in V.ROUTES)
        print(f'  {rk}: n={len(y)} n_finite={int(finite.sum())} all_zero={allzero} in_ROUTES={rk in V.ROUTES}')

    results['cs_yaw_check'] = cs_yaw_report
    json.dump(results, open(f'{OUT}/power_results.json', 'w'), indent=1, default=str)
    print(f'\nwrote {OUT}/power_results.json')


if __name__ == '__main__':
    main()
