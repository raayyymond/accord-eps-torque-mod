"""ADVERSARIAL CONFOUND CHECK for s4_texture finding 'wheel-2-3hz-texture-is-the-separator'.

Re-uses s4_texture/data/<route>.npz (already extracted by s4_extract.py -- same block/cell/metric
definitions, nothing re-derived). Re-implements matched_effect/bootstrap from s4_compare.py but lets the
V282 route pool be restricted, so we can:
  (A) leave-one-route-out on the V282 side, especially WITHOUT 0000006c--2bc842dbac (554/752 = 74% of all
      V282 blocks) -- does the x2.6-2.8 (T64 'all', mode_rms) survive on the two minority routes alone?
  (B) use ONLY 2bc842dbac as the V282 reference -- does the dominant route alone reproduce the pooled figure,
      or is it an outlier that the pooling is hiding?
  (C) per-route-pair effect matrix (every V282 route x every T64 route) -- the strongest single test of
      whether a road/day/route artifact could produce the ratio.
  (D) same on hf_ratio (the other headline metric) for the 'all' stratum.
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import s4_compare as SC

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__wheel23hztex__confound/confound_results.json'

R = SC.load_all()
V282_ROUTES = [rk for rk in R if R[rk]['group'] == 'V282']
DOMINANT = '0000006c--2bc842dbac'
MINOR = [rk for rk in V282_ROUTES if rk != DOMINANT]
print('V282 routes:', V282_ROUTES, 'dominant blocks', R[DOMINANT]['cols']['v'].shape[0])
print('minor routes blocks', {rk: R[rk]['cols']['v'].shape[0] for rk in MINOR})

rng = np.random.default_rng(11)


def matched_effect_subset(Vrks, Grk, metric, stratum, log=True):
    """matched_effect between ONE torque route (Grk) and a chosen subset of V282 routes (Vrks)."""
    Gd = [SC.prep(R, Grk, metric, stratum)]
    Vd = [SC.prep(R, rk, metric, stratum) for rk in Vrks]
    return SC.matched_effect(Gd, Vd, metric, log=log)


def bootstrap_subset(Vrks, Grks, metric, stratum, log=True, B=600):
    """Full bootstrap (route-resample within each side, then block-resample), V282 side restricted to Vrks."""
    Gd = {rk: SC.prep(R, rk, metric, stratum) for rk in Grks}
    Vd = {rk: SC.prep(R, rk, metric, stratum) for rk in Vrks}
    est, n = SC.matched_effect(list(Gd.values()), list(Vd.values()), metric, log=log)
    reps = []
    for _ in range(B):
        def rs(dd, keys):
            ks = list(rng.choice(keys, len(keys), replace=True)) if len(keys) > 1 else keys
            o = []
            for k in ks:
                cc, mm = dd[k]
                if len(cc) == 0:
                    continue
                i = rng.integers(0, len(cc), len(cc))
                o.append((cc[i], mm[i]))
            return o
        g = rs(Gd, Grks); vv = rs(Vd, Vrks)
        if not g or not vv:
            continue
        e, _ = SC.matched_effect(g, vv, metric, log=log)
        if np.isfinite(e):
            reps.append(e)
    ci = [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))] if len(reps) > 50 else [np.nan, np.nan]
    return dict(est=est, w=n, ci=ci, n_reps=len(reps))


T64_ROUTES = [rk for rk in R if R[rk]['group'] == 'T64']
ALL_GROUPS = ['T64', 'T64B', 'T5', 'T4']

results = {}

# --- (A) leave-dominant-route-out: V282 side = minor routes only ---
results['A_minor_only_vs_dominant_only'] = {}
for metric in ['mode_rms', 'hf_ratio']:
    log = True
    row = {}
    for st_name, st_fn in SC.STRATA.items():
        pooled = bootstrap_subset(V282_ROUTES, T64_ROUTES, metric, st_fn, log=log)
        minor = bootstrap_subset(MINOR, T64_ROUTES, metric, st_fn, log=log)
        dom = bootstrap_subset([DOMINANT], T64_ROUTES, metric, st_fn, log=log)
        row[st_name] = dict(pooled=pooled, minor_only=minor, dominant_only=dom)
    results['A_minor_only_vs_dominant_only'][metric] = row

# --- (B) full route-pair matrix (every V282 route x every T64 route), 'all' stratum ---
results['B_route_pair_matrix'] = {}
for metric in ['mode_rms', 'hf_ratio']:
    mat = {}
    for vrk in V282_ROUTES:
        mat[vrk] = {}
        for grk in T64_ROUTES:
            e, n = matched_effect_subset([vrk], grk, metric, SC.STRATA['all'], log=True)
            mat[vrk][grk] = dict(est=e, w=n)
    results['B_route_pair_matrix'][metric] = mat

# --- (C) each torque group vs minor-only V282 (all groups, all strata), mode_rms + hf_ratio ---
results['C_all_groups_minor_only'] = {}
for metric in ['mode_rms', 'hf_ratio']:
    row = {}
    for g in ALL_GROUPS:
        Grks = [rk for rk in R if R[rk]['group'] == g]
        st_row = {}
        for st_name, st_fn in SC.STRATA.items():
            st_row[st_name] = bootstrap_subset(MINOR, Grks, metric, st_fn, log=True)
        row[g] = st_row
    results['C_all_groups_minor_only'][metric] = row

json.dump(results, open(OUT, 'w'), indent=1, default=float)
print('wrote', OUT)

# console summary
print("\n=== (A) mode_rms / hf_ratio: pooled vs minor-only vs dominant-only V282 reference ===")
for metric in ['mode_rms', 'hf_ratio']:
    for st in ['all', 'lt15', 'ge15', 'ge15_straight']:
        r = results['A_minor_only_vs_dominant_only'][metric][st]
        print(f"{metric:10s} {st:14s} pooled={r['pooled']['est']:.3f}[{r['pooled']['ci'][0]:.3f},{r['pooled']['ci'][1]:.3f}] w{r['pooled']['w']}  "
              f"minor_only={r['minor_only']['est']:.3f}[{r['minor_only']['ci'][0]:.3f},{r['minor_only']['ci'][1]:.3f}] w{r['minor_only']['w']}  "
              f"dominant_only={r['dominant_only']['est']:.3f}[{r['dominant_only']['ci'][0]:.3f},{r['dominant_only']['ci'][1]:.3f}] w{r['dominant_only']['w']}")

print("\n=== (B) route-pair matrix, 'all' stratum, mode_rms ===")
for vrk in V282_ROUTES:
    print(vrk, {grk: round(results['B_route_pair_matrix']['mode_rms'][vrk][grk]['est'], 3) for grk in T64_ROUTES})
print("\n=== (B) route-pair matrix, 'all' stratum, hf_ratio ===")
for vrk in V282_ROUTES:
    print(vrk, {grk: round(results['B_route_pair_matrix']['hf_ratio'][vrk][grk]['est'], 3) for grk in T64_ROUTES})

print("\n=== (C) all torque groups vs MINOR-ONLY V282 reference, mode_rms ===")
for g in ALL_GROUPS:
    for st in ['all', 'lt15', 'ge15']:
        r = results['C_all_groups_minor_only']['mode_rms'][g][st]
        print(f"{g:6s} {st:12s} est={r['est']:.3f}  ci=[{r['ci'][0]:.3f},{r['ci'][1]:.3f}]  w={r['w']}")
