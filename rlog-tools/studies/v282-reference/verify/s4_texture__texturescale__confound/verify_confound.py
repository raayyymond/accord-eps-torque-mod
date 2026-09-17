"""ADVERSARIAL CONFOUND CHECK for s4_texture finding 'texture-scales-with-angle-and-transient-size'.

Claim: below 15 m/s, matched-block mode_rms(sr, 1.8-3.0 Hz) ratio torque/V282 grows from ~2.8-3.8x ('all')
to ~5.3-9.3x when restricted to |angle|>=15 deg, and desired-jerk-event 2-3 Hz rms post-event grows from
~0.30 (10-40 deg/s wheel transients) to ~3-6x that at >40 deg/s, on BOTH matched speed and demand size.

This script re-uses s4_texture/data/<route>.npz (same extraction, nothing re-derived) and s4_texture/s4_extra.json
event bins, but:
  (A) restricts the V282 side of the matched-block comparison (mode_rms, strata all/lt15/lt15_ang15/lt15_act3)
      to MINOR routes only (drops 0000006c--2bc842dbac, which is 62 segments / most V282 blocks) -- does the
      angle-growth pattern survive?
  (B) per-V282-route x per-torque-route matched-effect matrix for lt15_ang15 and lt15_act3 (the angle/activity-
      restricted strata that carry the headline x5-x9 numbers) -- is any single V282 route driving it?
  (C) re-does the event-bin analysis (desired-jerk04 events, mode-band rms after the event) with the V282 side
      restricted to minor routes, and separately checks whether >40 deg/s events are dominated by one route.
  (D) recomputes event 'gain' using achieved lateral accel from la_yaw (carState yaw*v, independent of the
      la_act channel whose definition may differ between fork versions) instead of la_act, for the >=15 deg/s
      wheel-rate event bin, to check the 'tracking gain ~1.0, not a gain deficit' sub-claim survives the
      la_act/la_yaw confound the brief calls out.
  (E) sanity: is the angle/rate-size growth itself just re-deriving the SPEED effect (angle and low speed
      correlate)? Re-run (A) within the lt15 stratum only (so speed is already fixed) -- angle is the only
      thing left varying.
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture')
import s4_compare as SC

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__texturescale__confound/confound_results.json'

R = SC.load_all()
V282_ROUTES = [rk for rk in R if R[rk]['group'] == 'V282']
DOMINANT = '0000006c--2bc842dbac'
MINOR = [rk for rk in V282_ROUTES if rk != DOMINANT]
T64_ROUTES = [rk for rk in R if R[rk]['group'] == 'T64']
ALL_TOR = ['T64', 'T64B', 'T5', 'T4']
print('V282 routes:', V282_ROUTES)
print('dominant blocks (all stratum):', (R[DOMINANT]['cols']['v']).shape[0])
print('minor route blocks:', {rk: R[rk]['cols']['v'].shape[0] for rk in MINOR})

rng = np.random.default_rng(17)


def bootstrap_subset(Vrks, Grks, metric, stratum, log=True, B=800):
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


def matched_pair(vrk, grk, metric, stratum, log=True):
    Gd = [SC.prep(R, grk, metric, stratum)]
    Vd = [SC.prep(R, vrk, metric, stratum)]
    return SC.matched_effect(Gd, Vd, metric, log=log)


results = {}

# --- (A) minor-only vs dominant-only vs pooled, for the strata that carry the headline numbers ---
results['A_minor_vs_dominant'] = {}
for st_name in ['all', 'lt15', 'lt15_ang15', 'lt15_act3']:
    st_fn = SC.STRATA[st_name]
    row = {}
    for g in ALL_TOR:
        Grks = [rk for rk in R if R[rk]['group'] == g]
        pooled = bootstrap_subset(V282_ROUTES, Grks, 'mode_rms', st_fn)
        minor = bootstrap_subset(MINOR, Grks, 'mode_rms', st_fn)
        dom = bootstrap_subset([DOMINANT], Grks, 'mode_rms', st_fn)
        row[g] = dict(pooled=pooled, minor_only=minor, dominant_only=dom)
    results['A_minor_vs_dominant'][st_name] = row
    print(f"\n=== stratum {st_name} ===")
    for g in ALL_TOR:
        r = row[g]
        print(f"  {g:5s} pooled={r['pooled']['est']:.2f}[{r['pooled']['ci'][0]:.2f},{r['pooled']['ci'][1]:.2f}] w{r['pooled']['w']}  "
              f"minor={r['minor_only']['est']:.2f}[{r['minor_only']['ci'][0]:.2f},{r['minor_only']['ci'][1]:.2f}] w{r['minor_only']['w']}  "
              f"dom={r['dominant_only']['est']:.2f}[{r['dominant_only']['ci'][0]:.2f},{r['dominant_only']['ci'][1]:.2f}] w{r['dominant_only']['w']}")

# --- (B) per-V282-route x per-torque-route matrix, lt15_ang15 and lt15_act3 ---
results['B_route_pair_matrix'] = {}
for st_name in ['lt15_ang15', 'lt15_act3']:
    st_fn = SC.STRATA[st_name]
    mat = {}
    for vrk in V282_ROUTES:
        mat[vrk] = {}
        for g in ALL_TOR:
            for grk in [rk for rk in R if R[rk]['group'] == g]:
                e, n = matched_pair(vrk, grk, 'mode_rms', st_fn)
                mat[vrk][grk] = dict(est=e, w=n)
    results['B_route_pair_matrix'][st_name] = mat
    print(f"\n=== (B) route-pair matrix, {st_name}, mode_rms ===")
    for vrk in V282_ROUTES:
        print(' ', vrk, {grk: (round(v['est'], 2) if np.isfinite(v['est']) else None, v['w']) for grk, v in mat[vrk].items()})

# --- (C) event bins, minor-only V282, mirroring s4_extra.py's EB bins ---
def evs_by_routekeys(rkeys, kind='jerk04'):
    """filter EV lists directly by ROUTE KEY membership (not group label) -- lets us pick arbitrary route subsets."""
    return [dict(e, route=rk) for rk in rkeys for e in R[rk]['EV'] if e['kind'] == kind]

EB = [(0, 15, 0, 10), (0, 15, 10, 40), (0, 15, 40, 1e9), (15, 40, 0, 10), (15, 40, 10, 1e9)]
results['C_events_minor_only'] = {}
for grp, label in [(V282_ROUTES, 'V282_pooled'), (MINOR, 'V282_minor'), ([DOMINANT], 'V282_dominant'),
                    ([rk for rk in R if R[rk]['group'] == 'V282old'], 'V282old')] + \
                   [([rk for rk in R if R[rk]['group'] == g], g) for g in ALL_TOR]:
    for s0, s1, r0, r1 in EB:
        E = [e for e in evs_by_routekeys(grp) if s0 <= e['v'] < s1 and r0 <= e['rate_max'] < r1]
        key = f'v{s0}-{s1}_rate{r0}-{int(min(r1,999))}'
        if len(E) == 0:
            results['C_events_minor_only'].setdefault(label, {})[key] = dict(n=0)
            continue
        md = np.array([e['md_post'] for e in E]); rk = np.array([e['route'] for e in E])
        ur = np.unique(rk)
        reps = []
        for _ in range(2000):
            pick = rng.choice(ur, len(ur))
            xs = np.concatenate([rng.choice(md[rk == r], (rk == r).sum()) for r in pick])
            reps.append(np.median(xs))
        o = dict(n=len(E), routes=int(len(ur)), route_list=[str(r) for r in ur], md_post_med=float(np.median(md)),
                  ci=[float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))])
        results['C_events_minor_only'].setdefault(label, {})[key] = o
print("\n=== (C) event md_post medians (jerk04), minor-only V282 vs pooled vs dominant-only ===")
for label in ['V282_pooled', 'V282_minor', 'V282_dominant', 'V282old', 'T64', 'T64B', 'T5', 'T4']:
    row = results['C_events_minor_only'].get(label, {})
    print(' ', label, {k: (round(v['md_post_med'], 3), v['n'], v['routes']) if v.get('n') else 'n=0' for k, v in row.items()})

# --- (D) gain: la_act vs the INDEPENDENT achieved-accel channel.
# NOTE: v282cmp.py's la_yaw = carState.yawRate*v is ALL-ZERO in every cached route (cs_yaw never populated at
# cache-build time -- confirmed by direct npz inspection, min=max=0.0 over 90791 samples on 00000064). la_yaw is
# therefore UNUSABLE as an independent cross-check with this cache. la_pose (livePose yaw*v, device-frame) IS
# populated and IS the independent channel s4_extract.py already computed event metrics against (gain_pose,
# jerk_rough_pose, stored per-event in the cached EV list) -- use that instead and say so.
results['D_gain_la_yaw'] = {}
results['D_note'] = ("v282cmp.la_yaw is all-zero in every cached route (cs_yaw never populated) -- unusable. "
                      "Used la_pose (livePose yaw*v) instead, via the gain_pose field s4_extract.py already computed.")
for g in ['V282'] + ALL_TOR:
    Grks = [rk for rk in R if R[rk]['group'] == g]
    for r0, r1, lbl in [(10, 40, '10_40'), (40, 1e9, 'gt40')]:
        E = [e for rk in Grks for e in R[rk]['EV'] if e['kind'] == 'jerk04' and 0 <= e['v'] < 15 and r0 <= e['rate_max'] < r1]
        if not E:
            continue
        gains_act = [e['gain'] for e in E]
        gains_pose = [e['gain_pose'] for e in E]
        results['D_gain_la_yaw'].setdefault(g, {})[lbl] = dict(
            n=len(E), gain_act_med=float(np.nanmedian(gains_act)), gain_pose_med=float(np.nanmedian(gains_pose)),
            gain_act_all=[round(float(x), 3) for x in gains_act], gain_pose_all=[round(float(x), 3) for x in gains_pose])
print("\n=== (D) event gain: la_act vs la_pose (la_yaw is unusable -- see D_note), <15 m/s, by wheel rate_max bin ===")
for g, row in results['D_gain_la_yaw'].items():
    for lbl, o in row.items():
        print(' ', g, lbl, 'n', o['n'], 'gain_act', round(o['gain_act_med'], 2), 'gain_pose', round(o['gain_pose_med'], 2))

json.dump(results, open(OUT, 'w'), indent=1, default=str)
print('\nwrote', OUT)
