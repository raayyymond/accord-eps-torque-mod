"""Adversarial CONFOUND check on s5_mechanism claim 'v282-was-a-rate-servo'.

The claim rests on a per-GROUP IV FRF (u=cs_out -> rate=steering rate, instrument r=model desired accel)
that is FLAT-PHASE (+25 to -9 deg) for V282 across 0.39-1.95 Hz in all 4 speed strata, vs a phase that
rolls off fast for T64/T4/T5 (torque mode). The V282 group pools 3 routes, but route 0000006c--2bc842dbac
is a 29.5 MB cache (62 segments) vs 6.5-6.8 MB for the other two -- roughly 4.5x the data. If the flat-phase
signature is a property of ONE route and not the other two, "V282 was a rate servo" is a route artifact,
not a firmware property.

This script recomputes the SAME estimator (v282cmp + the s5lib IV-FRF accumulator, unmodified) but keeps
per-route accumulators separate, so it can report:
 (a) each V282 route's OWN phase/coherence at 0.39-1.95 Hz per stratum (no pooling)
 (b) the group figure with 2bc842dbac LEFT OUT (leave-one-route-out, the dominant route specifically)
 (c) input-demand power (Srr, proportional to model-demand variance) per route per stratum, to check the
     amplitude-matching precondition before trusting any phase comparison
 (d) the same three things for the torque-mode groups (T64/T4/T5), which are already many separate routes,
     as a sanity check that torque-mode conclusions are not single-route artifacts either.

One route loaded at a time; only small per-route summary dicts are kept.
"""
import gc, json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import v282cmp as V  # noqa: E402
import s5lib as L    # noqa: E402

NPS = 256
BAND = (0.39, 1.95)
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__v282wasarate__confound/'

GROUPS = {
    'V282': ['0000006c--2bc842dbac', '00000064--ce6b0b0ebb', '00000065--b9f78988bd'],
    'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T4': ['00000075--6c8687d5bd'],
    'T5': ['00000076--d0b7ea7e4d'],
}

per_route = {}  # route -> stratum -> acc

for g, routes in GROUPS.items():
    for rk in routes:
        S = V.load(rk)
        th = S['sa'] - np.nan_to_num(S['aoff'])
        per_route[rk] = {}
        for st in L.STRATA:
            acc = {}
            for a, b in L.stretches(S, st[0], st[1], min_s=2 * NPS / L.FS):
                r = np.nan_to_num(S['model'][a:b]); u = S['out'][a:b]
                L.frf_accumulate(acc, r, u, dict(rate=S['sr'][a:b]), NPS)
            per_route[rk][f'{st[0]:.0f}-{st[1]:.0f}'] = acc
        del S, th
        gc.collect()


def band_phase_coh(acc, name, f1, f2):
    if acc.get('sec', 0) < 5:
        return None
    R = L.frf_result(acc, name)
    f = R['f']; sel = (f >= f1) & (f < f2)
    if sel.sum() < 1:
        return None
    Hb = R['H_iv'][sel]
    w = (R['coh_ru'] * R['coh_ry'])[sel]
    w = np.maximum(w, 1e-6)
    ph = float(np.degrees(np.angle(np.sum(Hb * w))))  # weighted phasor angle across the band
    mag = float(np.average(np.abs(Hb), weights=w))
    coh_ru = float(np.average(R['coh_ru'][sel]))
    coh_ry = float(np.average(R['coh_ry'][sel]))
    return dict(sec=round(acc['sec'], 1), n=acc['n'], mag=round(mag, 1), phase_deg=round(ph, 1),
                coh_ru=round(coh_ru, 3), coh_ry=round(coh_ry, 3),
                Srr_mean=float(np.mean(np.abs(acc['Srr']))))


report = {'band_Hz': BAND, 'per_route': {}, 'group_pooled': {}, 'group_leave_2bc842dbac_out': {}}

for rk, byst in per_route.items():
    report['per_route'][rk] = {}
    for st, acc in byst.items():
        r = band_phase_coh(acc, 'rate', *BAND)
        report['per_route'][rk][st] = r

# pooled group (reproduces s5_01's own numbers, as a check the harness here matches)
for g, routes in GROUPS.items():
    report['group_pooled'][g] = {}
    for st_key in [f'{a:.0f}-{b:.0f}' for a, b in L.STRATA]:
        pooled = {}
        for rk in routes:
            acc = per_route[rk][st_key]
            if acc.get('sec', 0) < 5:
                continue
            for k, v in acc.items():
                if k in ('sec', 'n'):
                    pooled[k] = pooled.get(k, 0) + v
                elif k != 'f':
                    pooled[k] = pooled.get(k, 0) + v
                else:
                    pooled['f'] = v
        report['group_pooled'][g][st_key] = band_phase_coh(pooled, 'rate', *BAND) if pooled else None

# V282 with the dominant route (2bc842dbac) left out
for st_key in [f'{a:.0f}-{b:.0f}' for a, b in L.STRATA]:
    pooled = {}
    for rk in ['00000064--ce6b0b0ebb', '00000065--b9f78988bd']:
        acc = per_route[rk][st_key]
        if acc.get('sec', 0) < 5:
            continue
        for k, v in acc.items():
            if k != 'f':
                pooled[k] = pooled.get(k, 0) + v
            else:
                pooled['f'] = v
    report['group_leave_2bc842dbac_out'][st_key] = band_phase_coh(pooled, 'rate', *BAND) if pooled else None

json.dump(report, open(OUT + 'route_loo_result.json', 'w'), indent=1)

print(f"=== band {BAND} Hz, per-ROUTE u->rate phase (deg), coherence, demand power Srr ===")
for rk, byst in report['per_route'].items():
    print(rk)
    for st, r in byst.items():
        if r is None:
            print(f"   {st:8s}  (insufficient data)")
        else:
            print(f"   {st:8s}  sec={r['sec']:6.1f} n={r['n']:3d} mag={r['mag']:7.1f} phase={r['phase_deg']:7.1f} "
                  f"coh_ru={r['coh_ru']:.2f} coh_ry={r['coh_ry']:.2f} Srr={r['Srr_mean']:.4f}")

print("\n=== V282 POOLED (all 3 routes) vs LEAVE-2bc842dbac-OUT ===")
for st_key in report['group_pooled']['V282']:
    p = report['group_pooled']['V282'][st_key]
    q = report['group_leave_2bc842dbac_out'][st_key]
    ps = f"phase={p['phase_deg']:6.1f} coh_ry={p['coh_ry']:.2f} sec={p['sec']:5.0f}" if p else "  (insuff)"
    qs = f"phase={q['phase_deg']:6.1f} coh_ry={q['coh_ry']:.2f} sec={q['sec']:5.0f}" if q else "  (insuff)"
    print(f"  {st_key:8s}  pooled: {ps}   |  w/o dominant route: {qs}")

print("\n=== torque-mode groups pooled (sanity: single-route artifact?) ===")
for g in ('T64', 'T4', 'T5'):
    print(g)
    for st_key in report['group_pooled'][g]:
        p = report['group_pooled'][g][st_key]
        print(f"   {st_key:8s} ", (f"phase={p['phase_deg']:6.1f} coh_ry={p['coh_ry']:.2f} sec={p['sec']:5.0f}" if p else "(insuff)"))
